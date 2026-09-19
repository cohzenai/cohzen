"""Console reporter using Rich to display LangGraph architecture,
node internals, LLM calls, tools, prompts, and decoupled observability audits.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cz.scanner.models import AgentDef, GraphInfo, ScanResult, ToolDef


def print_console_report(result: ScanResult, console: Console | None = None) -> None:
    """Renders a clean, high-signal terminal report of the LangGraph architecture scan using Rich."""
    if console is None:
        console = Console()

    # --- 1. Header Overview Panel ---
    summary_text = Text()
    summary_text.append("Scanned Target: ", style="bold cyan")
    summary_text.append(f"{result.target_path}\n", style="white")
    summary_text.append("Frameworks:     ", style="bold cyan")
    frameworks_str = ", ".join(f"[bold green]✓ {f}[/bold green]" for f in result.frameworks_detected) or "[bold green]✓ LangGraph[/bold green]"
    summary_text.append(Text.from_markup(f"{frameworks_str}\n"))
    summary_text.append("Files Examined: ", style="bold cyan")
    summary_text.append(f"{result.files_scanned} total ({result.python_files_count} Python files)\n", style="white")
    summary_text.append("Scan Duration:  ", style="bold cyan")
    summary_text.append(f"{result.scan_duration_ms:.2f} ms\n\n", style="green")

    summary_text.append("Graphs Detected: ", style="bold magenta")
    summary_text.append(f"{result.total_graphs}  ", style="bold white")
    summary_text.append("• Compiled: ", style="bold green")
    summary_text.append(f"{result.total_compiled}  ", style="bold white")
    summary_text.append("• Registered Nodes: ", style="bold yellow")
    summary_text.append(f"{result.total_nodes}  ", style="bold white")
    summary_text.append("• Edges/Routes: ", style="bold blue")
    summary_text.append(f"{result.total_edges}\n", style="bold white")

    # LLMs, Tools & Nodes
    total_llm_calls = sum(len(a.llm_calls) for a in result.agent_definitions)
    summary_text.append("Node Handlers:   ", style="bold cyan")
    summary_text.append(f"{len(result.agent_definitions)}  ", style="bold white")
    summary_text.append("• LLM Call Sites: ", style="bold red")
    summary_text.append(f"{total_llm_calls}  ", style="bold white")
    summary_text.append("• Tools Defined: ", style="bold yellow")
    summary_text.append(f"{len(result.tool_definitions)}  ", style="bold white")
    summary_text.append("• ToolNodes: ", style="bold magenta")
    summary_text.append(f"{len(result.tool_nodes)}", style="bold white")

    console.print(
        Panel(
            summary_text,
            title="[bold blue]Cohzen Architecture Scanner (v0.1)[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
    )

    if not result.graphs and not result.agent_definitions and not result.tool_definitions:
        console.print(
            Panel(
                "[yellow]No LangGraph definitions, nodes, or tools detected in the specified path.[/yellow]",
                border_style="yellow",
            )
        )
        return

    # --- 2. Graphs Detail ---
    for idx, graph in enumerate(result.graphs, start=1):
        rel_path = _get_relative_path(graph.file_path, result.target_path)

        # Graph Header
        graph_title = f"Graph #{idx}: [bold cyan]{graph.graph_var}[/bold cyan] ([dim]{graph.graph_class}[/dim])"
        if graph.state_schema:
            graph_title += f" [dim]StateSchema: {graph.state_schema}[/dim]"

        status_parts = []
        if graph.is_compiled and graph.compile_info:
            c = graph.compile_info
            compile_rel_path = _get_relative_path(c.file_path, result.target_path)
            status_parts.append(f"[bold green]✔ COMPILED[/bold green] -> variable: [bold white]{c.compiled_var}[/bold white] [dim]at {compile_rel_path}:{c.line_number}[/dim]")
            if c.checkpointer:
                status_parts.append(f"  Checkpointer: [magenta]{c.checkpointer}[/magenta]")
            if c.interrupt_before:
                status_parts.append(f"  Interrupt Before: [yellow]{', '.join(c.interrupt_before)}[/yellow]")
            if c.interrupt_after:
                status_parts.append(f"  Interrupt After: [yellow]{', '.join(c.interrupt_after)}[/yellow]")
            if c.store:
                status_parts.append(f"  Store: [cyan]{c.store}[/cyan]")
        else:
            status_parts.append(f"[bold red]✖ NOT COMPILED[/bold red] [dim](Defined at {rel_path}:{graph.line_number})[/dim]")

        console.print(
            Panel(
                Text.from_markup("\n".join(status_parts)),
                title=graph_title,
                subtitle=f"{rel_path}:{graph.line_number}",
                border_style="green" if graph.is_compiled else "yellow",
            )
        )

        # Visual Architecture Flow (Terminal Diagram)
        flow_panel = _build_terminal_graph_flow(graph, result, show_tracing=False)
        console.print(flow_panel)

        # Nodes Table
        if graph.nodes:
            nodes_table = Table(
                title="[bold yellow]Registered Nodes & Handlers[/bold yellow]",
                show_header=True,
                header_style="bold yellow",
                border_style="dim",
            )
            nodes_table.add_column("Node Name", style="bold white")
            nodes_table.add_column("Handler / Location", style="dim")
            nodes_table.add_column("LLM Calls & Models", style="cyan")
            nodes_table.add_column("Tools Bound / Attached", style="magenta")

            for node in graph.nodes:
                node_rel = _get_relative_path(node.file_path, result.target_path)
                def_loc = f"{node.handler} [dim]({node_rel}:{node.line_number})[/dim]"
                llm_summary = "-"
                tools_summary = "-"

                # Case A: Node linked to an AgentDef/NodeDef
                if node.agent_def:
                    agent = node.agent_def
                    agent_rel = _get_relative_path(agent.file_path, result.target_path)
                    if node.handler.startswith("lambda") or "lambda" in node.handler:
                        def_loc = f"[bold cyan]λ[/bold cyan] (inline lambda) [dim]({agent_rel}:{agent.line_start})[/dim]"
                    else:
                        def_loc = f"{node.handler} [dim]({agent_rel}:{agent.line_start}-{agent.line_end})[/dim]"

                    parts = []
                    for call in agent.llm_calls:
                        model_str = f" [{call.model_name}]" if call.model_name else ""
                        parts.append(f"{call.provider}{model_str} ({call.caller_var}.{call.method})")
                    if agent.prompts_used:
                        parts.append(f"Prompt: {', '.join(agent.prompts_used)}")
                    llm_summary = "\n".join(parts) if parts else "[dim]No LLM invoked[/dim]"

                    if agent.tools_bound:
                        tools_summary = f"bound: [{', '.join(agent.tools_bound)}]"

                # Case B: Node is a ToolNode
                elif node.tool_node_def or "ToolNode" in node.handler:
                    tdef = node.tool_node_def
                    tools_list = tdef.tools if tdef else []
                    tools_summary = f"[bold magenta]ToolNode[/bold magenta]({', '.join(tools_list)})"
                    llm_summary = "[dim]Tool Execution[/dim]"

                # Case C: External import or unlinked handler
                else:
                    pkg = result.import_sources.get(node.handler) or result.import_sources.get(node.name)
                    if pkg:
                        def_loc = f"{node.handler} [cyan](external: {pkg})[/cyan]"
                    elif node.handler.startswith("lambda") or "lambda" in node.handler:
                        def_loc = f"[bold cyan]λ[/bold cyan] (inline lambda) [dim]({node_rel}:{node.line_number})[/dim]"
                    else:
                        def_loc = f"{node.handler} [dim]({node_rel}:{node.line_number})[/dim]"

                nodes_table.add_row(
                    f"🤖 {node.name}",
                    def_loc,
                    llm_summary,
                    tools_summary,
                )
            console.print(nodes_table)

        # Edges & Routing Table
        if graph.edges:
            edges_table = Table(
                title="[bold blue]Graph Topology & Routing Edges[/bold blue]",
                show_header=True,
                header_style="bold blue",
                border_style="dim",
            )
            edges_table.add_column("Type", style="bold")
            edges_table.add_column("Source", style="cyan")
            edges_table.add_column("Direction", style="white", justify="center")
            edges_table.add_column("Target / Routing", style="green")
            edges_table.add_column("Location", style="dim")

            for edge in graph.edges:
                edge_rel = _get_relative_path(edge.file_path, result.target_path)
                type_style = "cyan"
                type_label = edge.edge_type.upper()
                arrow = "──>"

                if edge.edge_type == "conditional":
                    type_style = "bold magenta"
                    type_label = "CONDITIONAL"
                    arrow = "─?─>"
                elif edge.edge_type == "entry_point":
                    type_style = "bold green"
                    type_label = "ENTRY"
                elif edge.edge_type == "finish_point":
                    type_style = "bold red"
                    type_label = "FINISH"

                target_display = edge.target
                if edge.conditional_mapping:
                    mappings = ", ".join(f"'{k}' -> '{v}'" for k, v in edge.conditional_mapping.items())
                    target_display = f"fn: {edge.condition_fn} {{{mappings}}}"

                edges_table.add_row(
                    f"[{type_style}]{type_label}[/{type_style}]",
                    edge.source,
                    arrow,
                    target_display,
                    f"{edge_rel}:{edge.line_number}",
                )
            console.print(edges_table)

        console.print()

    # --- 3. Tool Definitions Inventory Table ---
    if result.tool_definitions:
        tools_table = Table(
            title="[bold yellow]🛠️ Detected Tool Functions (@tool)[/bold yellow]",
            show_header=True,
            header_style="bold yellow",
            border_style="dim",
        )
        tools_table.add_column("Tool Name", style="bold white")
        tools_table.add_column("Location", style="dim")
        tools_table.add_column("Docstring / Purpose", style="cyan")

        for tool in result.tool_definitions:
            tool_rel = _get_relative_path(tool.file_path, result.target_path)
            doc = (tool.docstring.split("\n")[0] if tool.docstring else "[dim]No docstring[/dim]")
            if len(doc) > 60:
                doc = doc[:57] + "..."

            pkg = result.import_sources.get(tool.name)
            tool_name_display = f"🔧 {tool.name}" + (f" [cyan]({pkg})[/cyan]" if pkg else "")

            tools_table.add_row(
                tool_name_display,
                f"{tool_rel}:{tool.line_start}-{tool.line_end}",
                doc,
            )
        console.print(tools_table)
        console.print()

    manifest = result.to_manifest()

    # --- 4. External Library Dependencies (Highlighted) ---
    if manifest.metadata.external_packages:
        ext_lines = []
        for n in manifest.nodes:
            if n.resolution.reason == "external_import" and n.resolution.package:
                ext_lines.append(f"  • Node [bold white]'{n.name}'[/bold white] handler imported from [bold cyan]'{n.resolution.package}'[/bold cyan]")
        for t in manifest.tools:
            if t.resolution.reason == "external_import" and t.resolution.package:
                ext_lines.append(f"  • Tool [bold white]'{t.name}'[/bold white] imported from [bold cyan]'{t.resolution.package}'[/bold cyan]")

        if ext_lines:
            console.print(
                Panel(
                    Text.from_markup("\n".join(ext_lines)),
                    title="[bold cyan]📦 External Library Dependencies (Highlighted)[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
            console.print()

    # --- 5. Analysis Limitations & Warnings ---
    if manifest.metadata.warnings:
        warn_panel_lines = [f"  [yellow]⚠ {w}[/yellow]" for w in manifest.metadata.warnings]
        console.print(
            Panel(
                Text.from_markup("\n".join(warn_panel_lines)),
                title="[bold yellow]Analysis Limitations (Static Scope)[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()

    # --- 5. Errors Table ---
    if result.errors:
        err_table = Table(
            title="[bold red]Scan Warnings & Errors[/bold red]",
            show_header=True,
            header_style="bold red",
            border_style="red",
        )
        err_table.add_column("File", style="white")
        err_table.add_column("Type", style="bold red")
        err_table.add_column("Message", style="yellow")

        for err in result.errors:
            err_rel = _get_relative_path(err.file_path, result.target_path)
            err_table.add_row(err_rel, err.error_type, err.message)
        console.print(err_table)

    unique_models = len(manifest.models)
    unique_tools = len(manifest.tools)

    counts_str = (
        f"[bold white]{result.total_graphs}[/bold white] graph(s)  •  "
        f"[bold white]{result.total_nodes}[/bold white] node(s)  •  "
        f"[bold white]{result.total_edges}[/bold white] edge(s)  •  "
        f"[bold white]{unique_tools}[/bold white] tool(s)  •  "
        f"[bold white]{unique_models}[/bold white] model(s)"
    )

    ext_suffix = ""
    if manifest.metadata.external_imports > 0:
        ext_suffix = f"  •  [cyan]{manifest.metadata.external_imports} external dependency(ies) highlighted[/cyan]"

    if manifest.metadata.warnings:
        status_line = f"[bold yellow]⚠ Architecture discovered ({len(manifest.metadata.warnings)} static limitation(s))[/bold yellow]"
    else:
        status_line = "[bold green]✓ Architecture discovered[/bold green]"

    console.print(Text.from_markup(
        f"{counts_str}\n{status_line}{ext_suffix}  [dim]• Run [bold cyan]cz audit[/bold cyan] to inspect observability coverage and telemetry.[/dim]\n"
    ))


def print_audit_report(result: ScanResult, console: Console | None = None) -> None:
    """Renders a dedicated, high-detail observability and telemetry audit report using Rich."""
    if console is None:
        console = Console()

    obs = result.observability
    if not obs:
        console.print("[yellow]No observability analysis available for this scan.[/yellow]")
        return

    # --- 1. Audit Header Panel ---
    from cz.audit.registry import ObservabilityRegistry
    obs_reg = ObservabilityRegistry()

    obs_lines: List[str] = [
        f"[bold cyan]Scanned Target:[/bold cyan]    {result.target_path}",
        f"[bold cyan]Files Examined:[/bold cyan]    {result.files_scanned} total ({result.python_files_count} Python files)",
        f"[bold cyan]Scan Duration:[/bold cyan]     {result.scan_duration_ms:.2f} ms\n",
    ]

    # Active Observability Tools Detected
    if obs.tools_detected:
        tools_str = ", ".join(f"[bold green]✔ {t}[/bold green]" for t in obs.tools_detected)
        obs_lines.append(f"[bold cyan]Observability Tools:[/bold cyan]  {tools_str}")
    else:
        obs_lines.append("[bold cyan]Observability Tools:[/bold cyan]  [yellow]None detected across manifests, env, or code[/yellow]")

    # Telemetry packages
    if obs.packages:
        pkgs_str = ", ".join(
            f"[bold green]{p.name}[/bold green]" + (f" [dim]({p.version_spec})[/dim]" if p.version_spec else "")
            for p in obs.packages
        )
        obs_lines.append(f"[bold cyan]Telemetry Packages:[/bold cyan]  {pkgs_str}")
    else:
        obs_lines.append("[bold cyan]Telemetry Packages:[/bold cyan]  [yellow]None detected in package manifests[/yellow]")

    # Telemetry environment variables
    if obs.env_vars:
        envs_str = ", ".join(f"[bold green]{e}[/bold green]" for e in obs.env_vars)
        obs_lines.append(f"[bold cyan]Environment Config:[/bold cyan]  {envs_str}")
    else:
        obs_lines.append("[bold cyan]Environment Config:[/bold cyan]  [yellow]No tracing environment variables found in .env files[/yellow]")

    # Coverage
    agent_color = "green" if obs.agent_instrumentation_pct >= 80 else "yellow" if obs.agent_instrumentation_pct > 0 else "red"
    tool_color = "green" if obs.total_tools == 0 or obs.instrumented_tools > 0 else "yellow"
    obs_lines.append(
        f"[bold cyan]Tracing Coverage:[/bold cyan]    Nodes: [{agent_color}]{obs.instrumented_agents}/{obs.total_agents} ({obs.agent_instrumentation_pct}%)[/{agent_color}]  •  Tools: [{tool_color}]{obs.instrumented_tools}/{obs.total_tools}[/{tool_color}]"
    )

    panel_color = "green" if obs.is_observability_configured and obs.agent_instrumentation_pct > 50 else "yellow"
    console.print(
        Panel(
            Text.from_markup("\n".join(obs_lines)),
            title="[bold magenta]Cohzen Observability & Telemetry Audit (v0.1)[/bold magenta]",
            border_style=panel_color,
            padding=(1, 2),
        )
    )

    # --- 2. Node Instrumentation Detail Table ---
    if result.agent_definitions:
        nodes_audit_table = Table(
            title="[bold cyan]Node Instrumentation Status[/bold cyan]",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )
        nodes_audit_table.add_column("Node / Function", style="bold white")
        nodes_audit_table.add_column("Location", style="dim")
        nodes_audit_table.add_column("Instrumentation Status", style="bold")
        nodes_audit_table.add_column("Observability Tool", style="bold")
        nodes_audit_table.add_column("Active Decorators", style="magenta")
        nodes_audit_table.add_column("LLM Calls", style="cyan")

        for agent in result.agent_definitions:
            rel_path = _get_relative_path(agent.file_path, result.target_path)
            loc = f"{rel_path}:{agent.line_start}-{agent.line_end}"

            if agent.is_instrumented:
                status_str = "[bold green]✔ Instrumented[/bold green]"
                tool_used = obs_reg.get_tool_for_decorators(agent.telemetry_decorators) or "Instrumented"
                tool_cell = f"[bold green]{tool_used}[/bold green]"
                decs_str = ", ".join(agent.telemetry_decorators) or "@traced"
            else:
                status_str = "[bold red]✖ Uninstrumented[/bold red]"
                tool_cell = "[dim]None[/dim]"
                decs_str = "[dim]None[/dim]"

            llm_summary = f"{len(agent.llm_calls)} call(s)" if agent.llm_calls else "[dim]None[/dim]"

            nodes_audit_table.add_row(
                f"🤖 {agent.name}",
                loc,
                status_str,
                tool_cell,
                decs_str,
                llm_summary,
            )
        console.print(nodes_audit_table)
        console.print()

    # --- 3. Tool Instrumentation Detail Table ---
    if result.tool_definitions:
        tools_audit_table = Table(
            title="[bold yellow]Tool Instrumentation Status[/bold yellow]",
            show_header=True,
            header_style="bold yellow",
            border_style="dim",
        )
        tools_audit_table.add_column("Tool Name", style="bold white")
        tools_audit_table.add_column("Location", style="dim")
        tools_audit_table.add_column("Tracing Status", style="bold")
        tools_audit_table.add_column("Observability Tool", style="bold")
        tools_audit_table.add_column("Decorators", style="magenta")

        for tool in result.tool_definitions:
            rel_path = _get_relative_path(tool.file_path, result.target_path)
            loc = f"{rel_path}:{tool.line_start}-{tool.line_end}"

            if tool.is_instrumented:
                status_str = "[bold green]✔ Instrumented[/bold green]"
                tool_used = obs_reg.get_tool_for_decorators(tool.telemetry_decorators) or "Instrumented"
                tool_cell = f"[bold green]{tool_used}[/bold green]"
                decs_str = ", ".join(tool.telemetry_decorators)
            else:
                status_str = "[dim]Untraced[/dim]"
                tool_cell = "[dim]None[/dim]"
                decs_str = "[dim]None[/dim]"

            tools_audit_table.add_row(
                f"🔧 {tool.name}",
                loc,
                status_str,
                tool_cell,
                decs_str,
            )
        console.print(tools_audit_table)
        console.print()

    # --- 4. Recommendations & Findings ---
    if obs.recommendations:
        rec_lines = [f"  [yellow]⚠ {rec}[/yellow]" for rec in obs.recommendations]
        console.print(
            Panel(
                Text.from_markup("\n".join(rec_lines)),
                title="[bold yellow]Audit Findings & Gaps[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )


def _get_relative_path(file_path: str, base_path: str) -> str:
    """Safely format file path relative to scan target for readability."""
    try:
        return str(Path(file_path).relative_to(base_path))
    except Exception:
        return os.path.basename(file_path)


def _build_terminal_graph_flow(graph: GraphInfo, scan_result: ScanResult | None = None, show_tracing: bool = False) -> Panel:
    """Builds an ASCII/Unicode visual flowchart representation of the LangGraph topology in the CLI."""
    from cz.formatters.mermaid import _format_checkpointer_label

    flow_lines: List[str] = []

    # 1. Checkpointer Persistence Banner
    if graph.is_compiled and graph.compile_info and graph.compile_info.checkpointer:
        cp_label = _format_checkpointer_label(graph.compile_info.checkpointer, graph.file_path)
        flow_lines.append(f"  [bold magenta]💾 Checkpointer: {cp_label}[/bold magenta] [dim](State Persistence)[/dim]")
        flow_lines.append("        [magenta]┆[/magenta]")
        flow_lines.append("        [magenta]▼[/magenta]")

    if graph.is_compiled and graph.compile_info and graph.compile_info.store:
        store_label = _format_checkpointer_label(graph.compile_info.store, graph.file_path)
        flow_lines.append(f"  [bold cyan]🗄️ Store: {store_label}[/bold cyan] [dim](Shared Memory)[/dim]")
        flow_lines.append("        [cyan]┆[/cyan]")
        flow_lines.append("        [cyan]▼[/cyan]")

    # 2. START Sentinel
    flow_lines.append("  [bold white on blue] ● START [/bold white on blue]")
    flow_lines.append("     │")
    flow_lines.append("     ▼")

    tool_defs_map: Dict[str, ToolDef] = {}
    if scan_result and scan_result.tool_definitions:
        tool_defs_map = {t.name: t for t in scan_result.tool_definitions}

    # 3. Nodes and connected routes
    for idx, node in enumerate(graph.nodes):
        is_tool = (
            bool(node.tool_node_def)
            or "toolnode" in node.handler.lower()
            or (node.name.lower() in ("tools", "tool_node") and not node.agent_def)
        )

        if is_tool:
            tools_list: List[str] = []
            if node.tool_node_def and node.tool_node_def.tools:
                tools_list = node.tool_node_def.tools
            elif "ToolNode(" in node.handler:
                inner = node.handler[node.handler.find("(") + 1 : node.handler.rfind(")")]
                tools_list = [t.strip() for t in inner.split(",") if t.strip()]
            tools_str = ", ".join(tools_list) if tools_list else "runtime tools"

            flow_lines.append(f"  ╔══ [bold yellow]🛠️ {node.name}[/bold yellow] [dim](ToolNode)[/dim] ═══════════════════════════════╗")
            flow_lines.append(f"  ║  [dim]Tools:[/dim] [bold white]{tools_str}[/bold white]")
            if show_tracing:
                inst_count = sum(1 for t in tools_list if tool_defs_map.get(t, None) and tool_defs_map[t].is_instrumented)
                obs_str = f"[bold green]✔ {inst_count}/{len(tools_list)} instrumented[/bold green]" if inst_count > 0 else "[dim]⚪ untraced[/dim]"
                flow_lines.append(f"  ║  [dim]Tracing:[/dim] {obs_str}")
            flow_lines.append("  ╚══════════════════════════════════════════════════════╝")
            if node.handler.startswith("lambda") or "lambda" in node.handler:
                handler_str = " [dim](λ inline)[/dim]"
            elif node.handler != node.name:
                handler_str = f" [dim]({node.handler})[/dim]"
            else:
                handler_str = ""
            interrupt_str = ""
            if graph.compile_info:
                if node.name in graph.compile_info.interrupt_before:
                    interrupt_str += " [bold yellow]⏸️ [Interrupt Before][/bold yellow]"
                if node.name in graph.compile_info.interrupt_after:
                    interrupt_str += " [bold yellow]⏸️ [Interrupt After][/bold yellow]"

            llm_summary = "[dim]None (logic/router)[/dim]"
            if node.agent_def and node.agent_def.llm_calls:
                call_parts: List[str] = []
                for c in node.agent_def.llm_calls:
                    if c.model_name:
                        call_parts.append(f"{c.provider}/{c.model_name}")
                    elif c.caller_var:
                        call_parts.append(f"{c.provider} ({c.caller_var}.{c.method})")
                    else:
                        call_parts.append(f"{c.provider} ({c.method})")
                llm_summary = f"[bold green]{', '.join(list(dict.fromkeys(call_parts)))}[/bold green]"

            tools_b = ""
            if node.agent_def and node.agent_def.tools_bound:
                from rich.markup import escape
                escaped_tools = escape(f"[{', '.join(node.agent_def.tools_bound)}]")
                tools_b = f"  │  [dim]🛠️ Tools:[/dim] [magenta]{escaped_tools}[/magenta]"

            flow_lines.append(f"  ┌── [bold cyan]🤖 {node.name}[/bold cyan]{handler_str}{interrupt_str} ──────────────────────┐")
            flow_lines.append(f"  │  [dim]🧠 LLM:[/dim] {llm_summary}")
            if tools_b:
                flow_lines.append(tools_b.rstrip())
            if show_tracing:
                obs_badge = "[bold red]✖ None[/bold red]"
                if node.agent_def and node.agent_def.is_instrumented:
                    decs = ", ".join(f"@{d}" for d in node.agent_def.telemetry_decorators) or "instrumented"
                    obs_badge = f"[bold green]✔ {decs}[/bold green]"
                flow_lines.append(f"  │  [dim]🔭 Tracing:[/dim] {obs_badge}")
            flow_lines.append("  └───────────────────────────────────────────────────────┘")

        # Routing edges from this node
        out_edges = [e for e in graph.edges if e.source in (node.name, node.handler)]
        if out_edges:
            for edge in out_edges:
                if edge.edge_type == "conditional":
                    if edge.conditional_mapping:
                        for cond_val, target in edge.conditional_mapping.items():
                            dest_label = "[bold white on red] ● END [/bold white on red]" if target in ("END", "__end__") else f"[bold]{target}[/bold]"
                            flow_lines.append(f"     ├── [magenta]? route: '{cond_val}'[/magenta] ──► {dest_label}")
                    else:
                        dest_label = "[bold white on red] ● END [/bold white on red]" if edge.target in ("END", "__end__") else f"[bold]{edge.target}[/bold]"
                        flow_lines.append(f"     ├── [magenta]? {edge.condition_fn or 'condition'}[/magenta] ──► {dest_label}")
                elif edge.edge_type == "finish_point" or edge.target in ("END", "__end__"):
                    flow_lines.append("     └──► [bold white on red] ● END [/bold white on red]")
                else:
                    if idx < len(graph.nodes) - 1 and edge.target in (graph.nodes[idx + 1].name, graph.nodes[idx + 1].handler):
                        flow_lines.append("     │")
                        flow_lines.append("     ▼")
                    else:
                        flow_lines.append(f"     └──► [bold cyan]{edge.target}[/bold cyan]")
        elif idx < len(graph.nodes) - 1:
            flow_lines.append("     │")
            flow_lines.append("     ▼")

    return Panel(
        Text.from_markup("\n".join(flow_lines)),
        title="[bold cyan]🌐 Architecture Flow (Nodes • Edges • Tools • Checkpointer • LLMs)[/bold cyan]",
        border_style="blue",
        padding=(1, 2),
    )
