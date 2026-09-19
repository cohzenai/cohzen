"""Master repository scanning engine orchestrating framework, LLM, and observability plugins."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, List, Set

from cz.scanner.visitor import FileScanResult, parse_and_scan_file
from cz.scanner.models import (
    AgentDef,
    GraphInfo,
    PromptDef,
    ScanError,
    ScanResult,
    ToolDef,
    ToolNodeDef,
    ToolsBoundInfo,
)
from cz.detectors.base import BaseFrameworkScanner
from cz.detectors.registry import FrameworkRegistry
from cz.detectors.llm.registry import LLMRegistry
from cz.audit.registry import ObservabilityRegistry

DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "eggs",
    ".eggs",
    ".next",
    ".vscode",
    ".idea",
    "site-packages",
}


def _should_ignore_dir(dir_name: str) -> bool:
    """Check if directory name matches common build/dependency/cache ignore lists."""
    return dir_name in DEFAULT_IGNORED_DIRS or dir_name.endswith(".egg-info")


def scan_file(
    target_path: str,
    verbose: bool = False,
    framework_registry: FrameworkRegistry | None = None,
    llm_registry: LLMRegistry | None = None,
    observability_registry: ObservabilityRegistry | None = None,
) -> ScanResult:
    """Convenience helper scanning a single file."""
    return scan_repository(
        target_path=target_path,
        verbose=verbose,
        framework_registry=framework_registry,
        llm_registry=llm_registry,
        observability_registry=observability_registry,
    )


def scan_repository(
    target_path: str,
    verbose: bool = False,
    framework_registry: FrameworkRegistry | None = None,
    llm_registry: LLMRegistry | None = None,
    observability_registry: ObservabilityRegistry | None = None,
) -> ScanResult:
    """Recursively scan a repository or directory across all registered frameworks, LLMs, and tools."""
    start_time = time.perf_counter()
    path = Path(target_path).resolve()

    if framework_registry is None:
        framework_registry = FrameworkRegistry()
    if llm_registry is None:
        llm_registry = LLMRegistry()
    if observability_registry is None:
        observability_registry = ObservabilityRegistry()

    result = ScanResult(target_path=str(path))

    if not path.exists():
        result.errors.append(
            ScanError(
                file_path=str(path),
                error_type="NotFound",
                message=f"Target path does not exist: {path}",
            )
        )
        return result

    all_graphs: List[GraphInfo] = []
    all_agent_defs: List[AgentDef] = []
    all_tool_defs: List[ToolDef] = []
    all_tool_nodes: List[ToolNodeDef] = []
    all_tools_bound: List[ToolsBoundInfo] = []
    all_prompts: List[PromptDef] = []
    all_import_sources: Dict[str, str] = {}
    all_errors: List[ScanError] = []

    if path.is_file():
        result.files_scanned = 1
        if path.suffix.lower() == ".py":
            result.python_files_count = 1
            file_res = parse_and_scan_file(str(path), framework_registry, llm_registry, observability_registry)
            all_graphs.extend(file_res.graphs)
            all_agent_defs.extend(file_res.agent_defs)
            all_tool_defs.extend(file_res.tool_defs)
            all_tool_nodes.extend(file_res.tool_nodes)
            all_tools_bound.extend(file_res.tools_bound)
            all_prompts.extend(file_res.prompts)
            all_import_sources.update(file_res.import_sources)
            all_errors.extend(file_res.errors)
        repo_dir = path.parent
    else:
        repo_dir = path
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not _should_ignore_dir(d)]

            for file in files:
                result.files_scanned += 1
                if file.endswith(".py"):
                    result.python_files_count += 1
                    file_path = os.path.join(root, file)
                    file_res = parse_and_scan_file(file_path, framework_registry, llm_registry, observability_registry)
                    all_graphs.extend(file_res.graphs)
                    all_agent_defs.extend(file_res.agent_defs)
                    all_tool_defs.extend(file_res.tool_defs)
                    all_tool_nodes.extend(file_res.tool_nodes)
                    all_tools_bound.extend(file_res.tools_bound)
                    all_prompts.extend(file_res.prompts)
                    all_import_sources.update(file_res.import_sources)
                    all_errors.extend(file_res.errors)

    # Cross-reference: Link graph nodes to their corresponding AgentDef or ToolNodeDef
    # Prefer exact match within the same file, fallback to repository-wide name match
    file_agent_map: Dict[tuple[str, str], AgentDef] = {(a.file_path, a.name): a for a in all_agent_defs}
    repo_agent_map: Dict[str, AgentDef] = {a.name: a for a in all_agent_defs}

    file_tool_node_map: Dict[tuple[str, str], ToolNodeDef] = {(t.file_path, t.var_name): t for t in all_tool_nodes}
    repo_tool_node_map: Dict[str, ToolNodeDef] = {t.var_name: t for t in all_tool_nodes}

    for graph in all_graphs:
        for node in graph.nodes:
            if not node.agent_def:
                node.agent_def = (
                    file_agent_map.get((node.file_path, node.handler))
                    or file_agent_map.get((node.file_path, node.name))
                    or repo_agent_map.get(node.handler)
                    or repo_agent_map.get(node.name)
                )

            if not node.tool_node_def:
                node.tool_node_def = (
                    file_tool_node_map.get((node.file_path, node.handler))
                    or file_tool_node_map.get((node.file_path, node.name))
                    or repo_tool_node_map.get(node.handler)
                    or repo_tool_node_map.get(node.name)
                )

    # Cross-reference model tool bindings with agent calls
    model_tools_map: Dict[tuple[str, str], List[str]] = {(b.file_path, b.model_var): b.tools for b in all_tools_bound}
    repo_model_tools_map: Dict[str, List[str]] = {b.model_var: b.tools for b in all_tools_bound}

    for agent in all_agent_defs:
        for call in agent.llm_calls:
            bound_tools = (
                model_tools_map.get((agent.file_path, call.caller_var))
                or repo_model_tools_map.get(call.caller_var)
            )
            if bound_tools:
                for t in bound_tools:
                    if t not in agent.tools_bound:
                        agent.tools_bound.append(t)
                    if t not in call.tools_bound:
                        call.tools_bound.append(t)

    # Filter agent_definitions: keep those registered or containing LLM calls/bindings
    registered_handlers = {node.handler for g in all_graphs for node in g.nodes}
    registered_handlers.update({node.name for g in all_graphs for node in g.nodes})

    active_agent_defs = [
        a for a in all_agent_defs
        if a.name in registered_handlers or a.llm_calls or a.tools_bound or a.prompts_used or a.is_instrumented
    ]

    # Perform Observability Audit
    obs_audit = observability_registry.audit(repo_dir, active_agent_defs, all_tool_defs)

    # Frameworks detected
    frameworks = sorted(list({g.framework for g in all_graphs}))

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    result.scan_duration_ms = round(elapsed_ms, 2)
    result.frameworks_detected = frameworks
    result.graphs = all_graphs
    result.agent_definitions = active_agent_defs
    result.tool_definitions = all_tool_defs
    result.tool_nodes = all_tool_nodes
    result.tools_bound = all_tools_bound
    result.prompts = all_prompts
    result.import_sources = all_import_sources
    result.observability = obs_audit
    result.errors = all_errors

    return result
