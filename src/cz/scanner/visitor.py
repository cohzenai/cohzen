"""Master AST visitor coordinating framework scanners, LLM detectors, and tool binding checkers."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from cz.scanner.utils import (
    ast_to_str,
    extract_list_of_strings,
    get_decorator_names,
)
from cz.scanner.models import (
    AgentDef,
    GraphInfo,
    LLMCallSite,
    PromptDef,
    ScanError,
    ToolDef,
    ToolNodeDef,
    ToolsBoundInfo,
)
from cz.detectors.registry import FrameworkRegistry
from cz.detectors.llm.registry import LLMRegistry
from cz.audit.registry import ObservabilityRegistry

KNOWN_PROMPT_CLASSES = ["ChatPromptTemplate", "PromptTemplate", "SystemMessage", "HumanMessage"]


@dataclass
class FileScanResult:
    """Consolidated results of AST analysis on a single Python file."""
    graphs: List[GraphInfo] = field(default_factory=list)
    agent_defs: List[AgentDef] = field(default_factory=list)
    tool_defs: List[ToolDef] = field(default_factory=list)
    tool_nodes: List[ToolNodeDef] = field(default_factory=list)
    tools_bound: List[ToolsBoundInfo] = field(default_factory=list)
    prompts: List[PromptDef] = field(default_factory=list)
    import_sources: Dict[str, str] = field(default_factory=dict)
    errors: List[ScanError] = field(default_factory=list)


class UnifiedASTVisitor(ast.NodeVisitor):
    """Orchestrates framework scanners, LLM detectors, and tool analyzers on a Python AST."""

    def __init__(
        self,
        file_path: str,
        framework_registry: FrameworkRegistry,
        llm_registry: LLMRegistry,
        observability_registry: ObservabilityRegistry,
    ) -> None:
        self.file_path = file_path
        self.framework_registry = framework_registry
        self.llm_registry = llm_registry
        self.observability_registry = observability_registry

        self.agent_defs: Dict[str, AgentDef] = {}
        self.tool_defs: Dict[str, ToolDef] = {}
        self.prompts: Dict[str, PromptDef] = {}
        self.tools_bound: List[ToolsBoundInfo] = []
        self.var_lists: Dict[str, List[str]] = {}
        self.import_sources: Dict[str, str] = {}
        self.known_decorators = self.observability_registry.get_all_known_decorators()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_as = alias.asname or alias.name
            self.import_sources[imported_as] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            imported_as = alias.asname or alias.name
            self.import_sources[imported_as] = module
        self.generic_visit(node)

    def _resolve_tools_list(self, raw_list: List[str]) -> List[str]:
        resolved: List[str] = []
        for item in raw_list:
            if item in self.var_lists:
                resolved.extend(self.var_lists[item])
            else:
                resolved.append(item)
        return resolved

    def visit_Assign(self, node: ast.Assign) -> None:
        self._inspect_assignment(node.targets, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self._inspect_assignment([node.target], node.value, node.lineno)
        self.generic_visit(node)

    def _inspect_assignment(self, targets: List[ast.AST], value: ast.AST, lineno: int) -> None:
        # Track list assignments for tool alias resolution
        if isinstance(value, (ast.List, ast.Tuple)):
            for target in targets:
                target_name = ast_to_str(target)
                self.var_lists[target_name] = extract_list_of_strings(value)

        # 1. Dispatch to framework scanners
        for scanner in self.framework_registry.get_all():
            scanner.visit_assign(targets, value, lineno)

        # 2. Check for tool binding via LLM registry (e.g. model.bind_tools)
        bound = self.llm_registry.detect_tools_bound(targets, value, self.file_path, lineno)
        if bound:
            bound.tools = self._resolve_tools_list(bound.tools)
            self.tools_bound.append(bound)
            if targets:
                assigned_name = ast_to_str(targets[0])
                if assigned_name and assigned_name != bound.model_var:
                    self.tools_bound.append(
                        ToolsBoundInfo(
                            model_var=assigned_name,
                            tools=bound.tools,
                            provider=bound.provider,
                            file_path=bound.file_path,
                            line_number=bound.line_number,
                        )
                    )

        # 3. Check for prompt templates
        if isinstance(value, ast.Call):
            func_name = ast_to_str(value.func)
            for prompt_cls in KNOWN_PROMPT_CLASSES:
                if prompt_cls in func_name:
                    target_name = ast_to_str(targets[0])
                    snippet = ast_to_str(value)
                    if len(snippet) > 80:
                        snippet = snippet[:77] + "..."
                    self.prompts[target_name] = PromptDef(
                        var_name=target_name,
                        template_type=prompt_cls,
                        snippet=snippet,
                        file_path=self.file_path,
                        line_number=lineno,
                    )
                    break

    def visit_Expr(self, node: ast.Expr) -> None:
        if isinstance(node.value, ast.Call):
            for scanner in self.framework_registry.get_all():
                scanner.visit_call(node.value, node.lineno)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        for scanner in self.framework_registry.get_all():
            scanner.visit_return(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_node":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Lambda):
                node_name = ast_to_str(node.args[0]).strip("'\"")
                lambda_agent = self._inspect_lambda(node.args[1], node_name, node.lineno)
                self.agent_defs[node_name] = lambda_agent
                self.agent_defs[ast_to_str(node.args[1])] = lambda_agent
        self.generic_visit(node)

    def _inspect_lambda(self, node: ast.Lambda, node_name: str, lineno: int) -> AgentDef:
        llm_calls: List[LLMCallSite] = []
        prompts_used: Set[str] = set()
        tools_bound: Set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_site = self.llm_registry.detect_call(child, self.file_path, getattr(child, "lineno", lineno))
                if call_site:
                    llm_calls.append(call_site)
                    if call_site.tools_bound:
                        tools_bound.update(call_site.tools_bound)
                if isinstance(child.func, ast.Attribute) and child.func.attr == "bind_tools":
                    if child.args:
                        raw_tools = extract_list_of_strings(child.args[0])
                        tools_bound.update(self._resolve_tools_list(raw_tools))
                    for kw in child.keywords:
                        if kw.arg == "tools":
                            raw_tools = extract_list_of_strings(kw.value)
                            tools_bound.update(self._resolve_tools_list(raw_tools))

            if isinstance(child, ast.Name) and child.id in self.prompts:
                prompts_used.add(child.id)

        raw_str = ast_to_str(node)
        line_start = getattr(node, "lineno", lineno)
        line_end = getattr(node, "end_lineno", line_start)

        return AgentDef(
            name=node_name,
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            is_async=False,
            docstring=f"Inline lambda: {raw_str}",
            llm_calls=llm_calls,
            prompts_used=sorted(list(prompts_used)),
            tools_bound=sorted(list(tools_bound)),
            is_instrumented=False,
            telemetry_decorators=[],
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._inspect_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._inspect_function(node, is_async=True)
        self.generic_visit(node)

    def _inspect_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        decorators = get_decorator_names(node.decorator_list)
        docstring = ast.get_docstring(node)
        line_start = node.lineno
        line_end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else line_start

        # Check telemetry instrumentation
        telemetry_decorators = [d for d in decorators if d in self.known_decorators or d in ("traceable", "observe")]
        is_instrumented = len(telemetry_decorators) > 0

        # Check if function is a @tool
        if "tool" in decorators:
            self.tool_defs[node.name] = ToolDef(
                name=node.name,
                file_path=self.file_path,
                line_start=line_start,
                line_end=line_end,
                docstring=docstring,
                has_tool_decorator=True,
                is_instrumented=is_instrumented,
                telemetry_decorators=telemetry_decorators,
            )
            return

        # Inspect body for LLM calls, prompts, and tool bindings
        llm_calls: List[LLMCallSite] = []
        prompts_used: Set[str] = set()
        tools_bound: Set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_site = self.llm_registry.detect_call(child, self.file_path, child.lineno)
                if call_site:
                    llm_calls.append(call_site)
                    if call_site.tools_bound:
                        tools_bound.update(call_site.tools_bound)

                # Check if bind_tools inside agent
                if isinstance(child.func, ast.Attribute) and child.func.attr == "bind_tools":
                    if child.args:
                        raw_tools = extract_list_of_strings(child.args[0])
                        tools_bound.update(self._resolve_tools_list(raw_tools))
                    for kw in child.keywords:
                        if kw.arg == "tools":
                            raw_tools = extract_list_of_strings(kw.value)
                            tools_bound.update(self._resolve_tools_list(raw_tools))

            if isinstance(child, ast.Name) and child.id in self.prompts:
                prompts_used.add(child.id)

        self.agent_defs[node.name] = AgentDef(
            name=node.name,
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            is_async=is_async,
            docstring=docstring,
            llm_calls=llm_calls,
            prompts_used=sorted(list(prompts_used)),
            tools_bound=sorted(list(tools_bound)),
            is_instrumented=is_instrumented,
            telemetry_decorators=telemetry_decorators,
        )


def parse_and_scan_file(
    file_path: str,
    framework_registry: FrameworkRegistry,
    llm_registry: LLMRegistry,
    observability_registry: ObservabilityRegistry,
) -> FileScanResult:
    """Parses a Python file and dispatches AST nodes to registries."""
    path = Path(file_path)
    if not path.is_file():
        return FileScanResult(
            errors=[ScanError(file_path=file_path, error_type="FileNotFound", message="File does not exist")]
        )

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return FileScanResult(
            errors=[ScanError(file_path=file_path, error_type="ReadError", message=str(e))]
        )

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return FileScanResult(
            errors=[
                ScanError(
                    file_path=file_path,
                    error_type="SyntaxError",
                    message=f"Syntax error at line {e.lineno}: {e.msg}",
                )
            ]
        )

    framework_registry.reset_all(file_path)

    visitor = UnifiedASTVisitor(
        file_path=file_path,
        framework_registry=framework_registry,
        llm_registry=llm_registry,
        observability_registry=observability_registry,
    )
    visitor.visit(tree)

    # Gather graphs and tool nodes from framework scanners
    all_graphs: List[GraphInfo] = []
    all_tool_nodes: List[ToolNodeDef] = []
    for scanner in framework_registry.get_all():
        all_graphs.extend(scanner.get_graphs())
        if hasattr(scanner, "tool_nodes"):
            all_tool_nodes.extend(list(scanner.tool_nodes.values()))

    return FileScanResult(
        graphs=all_graphs,
        agent_defs=list(visitor.agent_defs.values()),
        tool_defs=list(visitor.tool_defs.values()),
        tool_nodes=all_tool_nodes,
        tools_bound=visitor.tools_bound,
        prompts=list(visitor.prompts.values()),
        import_sources=visitor.import_sources,
        errors=[],
    )


def scan_python_file(file_path: str) -> FileScanResult:
    """Convenience wrapper parsing and scanning a single Python file using default registries."""
    return parse_and_scan_file(
        file_path,
        framework_registry=FrameworkRegistry(),
        llm_registry=LLMRegistry(),
        observability_registry=ObservabilityRegistry(),
    )

