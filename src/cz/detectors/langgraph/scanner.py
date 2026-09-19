"""LangGraph framework AST scanner."""

from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

from cz.scanner.utils import (
    ast_to_str,
    extract_dict_mapping,
    extract_list_of_strings,
)
from cz.scanner.models import CompileInfo, EdgeInfo, GraphInfo, NodeInfo, ToolNodeDef

KNOWN_GRAPH_CLASSES = {"StateGraph", "Graph", "MessageGraph"}


class LangGraphScanner:
    """Scanner detecting LangGraph graphs, compiled workflows, nodes, and edges."""

    def __init__(self, file_path: str = "") -> None:
        self.framework_name = "langgraph"
        self.file_path = file_path
        self.graphs: Dict[str, GraphInfo] = {}
        self.tool_nodes: Dict[str, ToolNodeDef] = {}
        self.var_lists: Dict[str, List[str]] = {}

    def reset(self, file_path: str) -> None:
        self.file_path = file_path
        self.graphs.clear()
        self.tool_nodes.clear()
        self.var_lists.clear()

    def _resolve_tools_list(self, raw_list: List[str]) -> List[str]:
        resolved: List[str] = []
        for item in raw_list:
            if item in self.var_lists:
                resolved.extend(self.var_lists[item])
            else:
                resolved.append(item)
        return resolved

    def _get_or_create_graph(self, var_name: str, line_number: int, graph_class: str = "StateGraph") -> GraphInfo:
        if var_name not in self.graphs:
            self.graphs[var_name] = GraphInfo(
                framework="langgraph",
                graph_var=var_name,
                graph_class=graph_class,
                file_path=self.file_path,
                line_number=line_number,
            )
        return self.graphs[var_name]

    def visit_assign(self, targets: List[ast.AST], value: ast.AST, lineno: int) -> None:
        # Track list assignments for tool alias resolution (e.g. tools = [tool_a, tool_b])
        if isinstance(value, (ast.List, ast.Tuple)):
            for target in targets:
                target_name = ast_to_str(target)
                self.var_lists[target_name] = extract_list_of_strings(value)
            return

        if not isinstance(value, ast.Call):
            return

        func_name = ast_to_str(value.func)

        # 1. StateGraph / Graph / MessageGraph instantiation
        matched_class = None
        for cls in KNOWN_GRAPH_CLASSES:
            if func_name == cls or func_name.endswith(f".{cls}"):
                matched_class = cls
                break

        if matched_class:
            schema_name = None
            if value.args:
                schema_name = ast_to_str(value.args[0])
            else:
                for kw in value.keywords:
                    if kw.arg == "state_schema":
                        schema_name = ast_to_str(kw.value)

            for target in targets:
                target_name = ast_to_str(target)
                graph = self._get_or_create_graph(target_name, lineno, matched_class)
                graph.state_schema = schema_name
            return

        # 2. Standalone ToolNode instantiation
        if func_name == "ToolNode" or func_name.endswith(".ToolNode"):
            raw_tools: List[str] = []
            if value.args:
                raw_tools = extract_list_of_strings(value.args[0])
            for kw in value.keywords:
                if kw.arg == "tools":
                    raw_tools = extract_list_of_strings(kw.value)

            tools_list = self._resolve_tools_list(raw_tools)
            target_name = ast_to_str(targets[0])
            tool_node_def = ToolNodeDef(
                var_name=target_name,
                tools=tools_list,
                file_path=self.file_path,
                line_number=lineno,
            )
            self.tool_nodes[target_name] = tool_node_def
            return

        # 3. .compile() assignment (e.g. app = workflow.compile(...))
        if isinstance(value.func, ast.Attribute) and value.func.attr == "compile":
            graph_var = ast_to_str(value.func.value)
            target_var = ", ".join(ast_to_str(t) for t in targets)
            self._record_compile(
                graph_var=graph_var,
                compiled_var=target_var,
                call_node=value,
                line_number=lineno,
            )

    def visit_call(self, call: ast.Call, lineno: int) -> None:
        # Unwrap chained calls like builder.add_node(...).add_edge(...)
        current = call
        chain: List[Tuple[str, ast.Call]] = []
        while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            method_name = current.func.attr
            chain.append((method_name, current))
            current = current.func.value

        base_var = ast_to_str(current)

        for method_name, call_node in reversed(chain):
            if not base_var:
                continue

            if method_name == "add_node":
                self._handle_add_node(base_var, call_node, lineno)
            elif method_name == "add_edge":
                self._handle_add_edge(base_var, call_node, lineno)
            elif method_name == "add_conditional_edges":
                self._handle_add_conditional_edges(base_var, call_node, lineno)
            elif method_name == "set_entry_point":
                self._handle_entry_point(base_var, call_node, lineno)
            elif method_name == "set_finish_point":
                self._handle_finish_point(base_var, call_node, lineno)
            elif method_name == "compile":
                self._record_compile(
                    graph_var=base_var,
                    compiled_var="<in-place>",
                    call_node=call_node,
                    line_number=lineno,
                )

    def visit_return(self, node: ast.Return) -> None:
        if node.value and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "compile":
                graph_var = ast_to_str(node.value.func.value)
                self._record_compile(
                    graph_var=graph_var,
                    compiled_var="<return>",
                    call_node=node.value,
                    line_number=node.lineno,
                )

    def _handle_add_node(self, graph_var: str, call: ast.Call, line_number: int) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        node_name = ""
        handler_name = ""
        inline_tool_node: Optional[ToolNodeDef] = None

        if len(call.args) >= 2:
            node_name = ast_to_str(call.args[0]).strip("'\"")
            second_arg = call.args[1]

            # Check if second arg is inline ToolNode(tools)
            if isinstance(second_arg, ast.Call) and "ToolNode" in ast_to_str(second_arg.func):
                raw_tools = extract_list_of_strings(second_arg.args[0]) if second_arg.args else []
                tools_list = self._resolve_tools_list(raw_tools)
                inline_tool_node = ToolNodeDef(
                    var_name=node_name,
                    tools=tools_list,
                    file_path=self.file_path,
                    line_number=line_number,
                )
                handler_name = f"ToolNode({', '.join(tools_list)})"
            else:
                handler_name = ast_to_str(second_arg)

        elif len(call.args) == 1:
            handler_name = ast_to_str(call.args[0])
            node_name = handler_name

        for kw in call.keywords:
            if kw.arg == "node":
                node_name = ast_to_str(kw.value).strip("'\"")
            elif kw.arg == "action":
                handler_name = ast_to_str(kw.value)

        if node_name or handler_name:
            node_info = NodeInfo(
                name=node_name or handler_name,
                handler=handler_name or node_name,
                file_path=self.file_path,
                line_number=line_number,
                tool_node_def=inline_tool_node,
            )
            graph.nodes.append(node_info)
            if inline_tool_node:
                self.tool_nodes[node_name] = inline_tool_node

    def _handle_add_edge(self, graph_var: str, call: ast.Call, line_number: int) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        start_key = ""
        end_key = ""

        if len(call.args) >= 2:
            start_key = ast_to_str(call.args[0]).strip("'\"")
            end_key = ast_to_str(call.args[1]).strip("'\"")
        elif len(call.args) == 1:
            start_key = ast_to_str(call.args[0]).strip("'\"")

        for kw in call.keywords:
            if kw.arg == "start_key":
                start_key = ast_to_str(kw.value).strip("'\"")
            elif kw.arg == "end_key":
                end_key = ast_to_str(kw.value).strip("'\"")

        if start_key and end_key:
            edge = EdgeInfo(
                source=start_key,
                target=end_key,
                edge_type="direct",
                file_path=self.file_path,
                line_number=line_number,
            )
            graph.edges.append(edge)

    def _handle_add_conditional_edges(self, graph_var: str, call: ast.Call, line_number: int) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        source = ""
        condition_fn = ""
        mapping: Dict[str, str] = {}

        if len(call.args) >= 1:
            source = ast_to_str(call.args[0]).strip("'\"")
        if len(call.args) >= 2:
            condition_fn = ast_to_str(call.args[1])
        if len(call.args) >= 3:
            third_arg = call.args[2]
            if isinstance(third_arg, ast.Dict):
                mapping = extract_dict_mapping(third_arg)
            elif isinstance(third_arg, (ast.List, ast.Tuple)):
                targets = extract_list_of_strings(third_arg)
                mapping = {t: t for t in targets}

        for kw in call.keywords:
            if kw.arg == "source":
                source = ast_to_str(kw.value).strip("'\"")
            elif kw.arg == "path":
                condition_fn = ast_to_str(kw.value)
            elif kw.arg == "path_map":
                if isinstance(kw.value, ast.Dict):
                    mapping = extract_dict_mapping(kw.value)
                elif isinstance(kw.value, (ast.List, ast.Tuple)):
                    targets = extract_list_of_strings(kw.value)
                    mapping = {t: t for t in targets}

        target_summary = f"branch({condition_fn})"
        if mapping:
            target_summary += f" -> [{', '.join(mapping.values())}]"

        edge = EdgeInfo(
            source=source,
            target=target_summary,
            edge_type="conditional",
            condition_fn=condition_fn,
            conditional_mapping=mapping,
            file_path=self.file_path,
            line_number=line_number,
        )
        graph.edges.append(edge)

    def _handle_entry_point(self, graph_var: str, call: ast.Call, line_number: int) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        target = ast_to_str(call.args[0]).strip("'\"") if call.args else "START"
        edge = EdgeInfo(
            source="START",
            target=target,
            edge_type="entry_point",
            file_path=self.file_path,
            line_number=line_number,
        )
        graph.edges.append(edge)

    def _handle_finish_point(self, graph_var: str, call: ast.Call, line_number: int) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        source = ast_to_str(call.args[0]).strip("'\"") if call.args else "END"
        edge = EdgeInfo(
            source=source,
            target="END",
            edge_type="finish_point",
            file_path=self.file_path,
            line_number=line_number,
        )
        graph.edges.append(edge)

    def _record_compile(
        self,
        graph_var: str,
        compiled_var: str,
        call_node: ast.Call,
        line_number: int,
    ) -> None:
        graph = self._get_or_create_graph(graph_var, line_number)
        graph.is_compiled = True

        checkpointer = None
        interrupt_before: List[str] = []
        interrupt_after: List[str] = []
        store = None

        for kw in call_node.keywords:
            if kw.arg == "checkpointer":
                checkpointer = ast_to_str(kw.value)
            elif kw.arg == "interrupt_before":
                interrupt_before = extract_list_of_strings(kw.value)
            elif kw.arg == "interrupt_after":
                interrupt_after = extract_list_of_strings(kw.value)
            elif kw.arg == "store":
                store = ast_to_str(kw.value)

        graph.compile_info = CompileInfo(
            compiled_var=compiled_var,
            file_path=self.file_path,
            line_number=line_number,
            checkpointer=checkpointer,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            store=store,
        )

    def get_graphs(self) -> List[GraphInfo]:
        return [
            g for g in self.graphs.values()
            if g.nodes or g.edges or g.is_compiled or g.state_schema or g.graph_class in KNOWN_GRAPH_CLASSES
        ]
