"""Mermaid diagram generator for LangGraph workflows detected by cz.

Renders high-fidelity diagrams mirroring LangGraph's visual structure:
- Nodes (Agent handlers, roles, interrupt points)
- Edges (Direct, conditional routes with condition values, START / END sentinels)
- Tools (ToolNodes, bound tools, execution handlers)
- Checkpointers (State persistence, MemorySaver, SqliteSaver, Store)
- LLMs (Provider, model name, caller method for each agent)
- Observability (Tracing badges, @traceable, @observe, coverage, uninstrumented warnings)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional
from cz.scanner.models import GraphInfo, ScanResult, ToolDef


def _sanitize_id(name: str) -> str:
    """Sanitizes node names for Mermaid identifier syntax."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return sanitized if sanitized else "node"


def _escape_mermaid(text: str) -> str:
    """Escapes double quotes, special characters, and non-whitelisted angle brackets for Mermaid."""
    escaped = text.replace('"', "'").replace("\n", " ").strip()
    # Strip angle brackets from non-formatting tags like <return>, <dynamic>, <lambda>, <unknown>
    return re.sub(r"<(?!/?(?:b|i|br\b))[^>]*>", lambda m: m.group(0).replace("<", "").replace(">", ""), escaped)


def _format_checkpointer_label(checkpointer_str: str, file_path: str = "") -> str:
    """Resolves checkpointer class name from raw assignment or variable reference."""
    cp = checkpointer_str.replace("()", "").strip("'\"")
    if cp == "checkpointer" and file_path:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            match = re.search(r"checkpointer\s*=\s*([A-Za-z0-9_]+)", content)
            if match:
                return match.group(1)
        except Exception:
            pass
    return cp


def generate_graph_mermaid(graph: GraphInfo, scan_result: Optional[ScanResult] = None) -> str:
    """Generates enriched Mermaid flowchart markup for a LangGraph workflow."""
    lines: List[str] = [
        "%% ========================================================",
        f"%% LangGraph Architecture: {graph.graph_var} ({graph.graph_class})",
        f"%% State Schema: {graph.state_schema or 'Implicit/TypedDict'}",
        f"%% Defined at: {graph.file_path}:{graph.line_number}",
    ]

    # Tool definitions lookup for observability inspection
    tool_defs_map: Dict[str, ToolDef] = {}
    if scan_result and scan_result.tool_definitions:
        tool_defs_map = {t.name: t for t in scan_result.tool_definitions}

    if graph.is_compiled and graph.compile_info:
        cp_summary = graph.compile_info.checkpointer or "None"
        compiled_target = (graph.compile_info.compiled_var or "").replace("<", "").replace(">", "")
        lines.append(f"%% Compiled at line {graph.compile_info.line_number} -> {compiled_target} (Checkpointer: {cp_summary})")
    lines.append("%% ========================================================")
    lines.append("flowchart TD")

    # 1. Sentinels (LangGraph convention: __start__ and __end__)
    lines.append("    __start__([● START]):::sentinelNode")
    lines.append("    __end__([● END]):::sentinelNode")

    # 2. Checkpointer / State Persistence Node
    has_checkpointer = False
    if graph.is_compiled and graph.compile_info and graph.compile_info.checkpointer:
        has_checkpointer = True
        cp_label = _format_checkpointer_label(graph.compile_info.checkpointer, graph.file_path)
        cp_label = _escape_mermaid(cp_label)
        lines.append(f"    checkpointer[\"💾 Checkpointer<br/><b>{cp_label}</b><br/><i>State Persistence</i>\"]:::checkpointerNode")
        lines.append("    checkpointer -.->|state persistence| __start__")

    if graph.is_compiled and graph.compile_info and graph.compile_info.store:
        store_label = _format_checkpointer_label(graph.compile_info.store, graph.file_path)
        store_label = _escape_mermaid(store_label)
        lines.append(f"    store[\"🗄️ Store<br/><b>{store_label}</b><br/><i>Shared Memory</i>\"]:::checkpointerNode")
        lines.append("    store -.->|shared store| __start__")

    # 3. Nodes (Agents, ToolNodes, Routers)
    for node in graph.nodes:
        node_id = _sanitize_id(node.name)

        # Detect if this node represents a ToolNode / tool execution
        is_tool_node = (
            bool(node.tool_node_def)
            or "toolnode" in node.handler.lower()
            or (node.name.lower() in ("tools", "tool_node") and not node.agent_def)
        )

        if is_tool_node:
            # Resolve tools inside ToolNode
            tools_list: List[str] = []
            if node.tool_node_def and node.tool_node_def.tools:
                tools_list = node.tool_node_def.tools
            elif "ToolNode(" in node.handler:
                inner = node.handler[node.handler.find("(") + 1 : node.handler.rfind(")")]
                tools_list = [t.strip() for t in inner.split(",") if t.strip()]

            tools_str = ", ".join(tools_list) if tools_list else "runtime tools"
            tools_str = _escape_mermaid(tools_str)

            # Check observability on tools
            inst_count = 0
            for t_name in tools_list:
                t_def = tool_defs_map.get(t_name)
                if t_def and t_def.is_instrumented:
                    inst_count += 1

            if tools_list and inst_count > 0:
                obs_badge = f"🔭 Tracing: {inst_count}/{len(tools_list)} instrumented"
            else:
                obs_badge = "⚪ Tracing: uninstrumented"

            lines.append(
                f"    {node_id}[[\"🛠️ <b>{node.name}</b> (ToolNode)<br/>Tools: {tools_str}<br/>{obs_badge}\"]]:::toolNode"
            )
        else:
            # Standard Agent / Node representation
            label_parts: List[str] = [f"🤖 <b>{node.name}</b>"]

            if node.handler.startswith("lambda") or "lambda" in node.handler:
                label_parts.append("Handler: λ (inline lambda)")
            elif node.handler != node.name:
                label_parts.append(f"Handler: {_escape_mermaid(node.handler)}")

            if node.is_subgraph:
                label_parts.append("🔗 <i>Compiled Subgraph</i>")

            # Check for interrupt points
            if graph.compile_info:
                if node.name in graph.compile_info.interrupt_before:
                    label_parts.append("⏸️ <i>Interrupt Before</i>")
                if node.name in graph.compile_info.interrupt_after:
                    label_parts.append("⏸️ <i>Interrupt After</i>")

            # LLM invocations
            if node.agent_def and node.agent_def.llm_calls:
                llm_names: List[str] = []
                for call in node.agent_def.llm_calls:
                    if call.model_name:
                        llm_names.append(f"{call.provider}/{call.model_name}")
                    elif call.caller_var:
                        llm_names.append(f"{call.provider} ({call.caller_var}.{call.method})")
                    else:
                        llm_names.append(f"{call.provider} ({call.method})")
                unique_llms = list(dict.fromkeys(llm_names))
                label_parts.append(f"🧠 LLM: {', '.join(unique_llms)}")
            else:
                label_parts.append("🧠 LLM: None (logic/router)")

            # Tools bound directly to agent
            if node.agent_def and node.agent_def.tools_bound:
                tools_bound_str = ", ".join(node.agent_def.tools_bound)
                label_parts.append(f"🛠️ Tools: [{_escape_mermaid(tools_bound_str)}]")

            # Observability instrumentation status
            if node.agent_def and node.agent_def.is_instrumented:
                decs = ", ".join(f"@{d}" for d in node.agent_def.telemetry_decorators) or "instrumented"
                label_parts.append(f"🔭 Tracing: {_escape_mermaid(decs)}")
                node_class = "instrumentedAgent"
            else:
                label_parts.append("⚠️ Tracing: none")
                node_class = "uninstrumentedAgent"

            node_label = "<br/>".join(label_parts)
            lines.append(f"    {node_id}[\"{node_label}\"]:::{node_class}")

    # 4. Edges and Routing
    for edge in graph.edges:
        src_id = "__start__" if edge.source in ("START", "__start__") else _sanitize_id(edge.source)
        tgt_id = "__end__" if edge.target in ("END", "__end__") else _sanitize_id(edge.target)

        if edge.edge_type == "conditional":
            if edge.conditional_mapping:
                for cond_val, target_node in edge.conditional_mapping.items():
                    dest_id = "__end__" if target_node in ("END", "__end__") else _sanitize_id(target_node)
                    clean_cond = _escape_mermaid(cond_val)
                    lines.append(f"    {src_id} -.->|route: {clean_cond}| {dest_id}")
            else:
                clean_cond = _escape_mermaid(edge.condition_fn or "condition")
                lines.append(f"    {src_id} -.->|{clean_cond}| {tgt_id}")
        elif edge.edge_type == "entry_point":
            lines.append(f"    __start__ --> {tgt_id}")
        elif edge.edge_type == "finish_point":
            lines.append(f"    {src_id} --> __end__")
        else:
            lines.append(f"    {src_id} --> {tgt_id}")

    # 5. Styling Classes (LangGraph Theme)
    lines.append("")
    lines.append("    %% Styling Classes (LangGraph Theme)")
    lines.append("    classDef default fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,color:#0f172a;")
    lines.append("    classDef sentinelNode fill:#f1f5f9,stroke:#475569,stroke-width:2px,color:#1e293b,font-weight:bold;")
    lines.append("    classDef checkpointerNode fill:#faf5ff,stroke:#9333ea,stroke-width:2px,color:#581c87;")
    lines.append("    classDef toolNode fill:#fefce8,stroke:#ca8a04,stroke-width:2px,color:#713f12;")
    lines.append("    classDef instrumentedAgent fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d;")
    lines.append("    classDef uninstrumentedAgent fill:#fffbeb,stroke:#d97706,stroke-width:1.5px,stroke-dasharray: 4 2,color:#78350f;")

    return "\n".join(lines)


def format_mermaid(result: ScanResult) -> str:
    """Generates Mermaid markup for all detected graphs in the ScanResult."""
    if not result.graphs:
        return "%% No LangGraph workflows detected."

    sections: List[str] = []
    for graph in result.graphs:
        sections.append(generate_graph_mermaid(graph, scan_result=result))

    return "\n\n".join(sections)

