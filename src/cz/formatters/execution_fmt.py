"""Terminal formatters for executions, spans, waterfall, execution tree, and deep-dive inspection (v0.2)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from rich import box
from rich.console import Console, Group
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from cz.execution.models import Execution, Span


def format_duration(duration_ms: Optional[float]) -> str:
    """Format duration in human-readable milliseconds or seconds."""
    if duration_ms is None:
        return "—"
    if duration_ms < 1000:
        return f"{int(duration_ms)}ms"
    return f"{duration_ms / 1000.0:.2f}s"


def format_status_icon(status: str) -> str:
    """Return a colored unicode status icon."""
    if status == "completed":
        return "[bold green]✓[/bold green]"
    elif status == "failed":
        return "[bold red]✗[/bold red]"
    elif status == "running":
        return "[bold yellow]●[/bold yellow]"
    return status


def get_kind_badge(kind: str) -> str:
    """Return a styled kind badge."""
    if kind == "graph":
        return "[bold blue]GRAPH[/bold blue]"
    elif kind == "node":
        return "[bold cyan]NODE [/bold cyan]"
    elif kind == "llm":
        return "[bold magenta]LLM  [/bold magenta]"
    elif kind == "tool":
        return "[bold yellow]TOOL [/bold yellow]"
    return f"[dim]{kind.upper()[:5].ljust(5)}[/dim]"


def get_kind_color(kind: str) -> str:
    """Return color string for span kind."""
    if kind == "graph":
        return "blue"
    elif kind == "node":
        return "cyan"
    elif kind == "llm":
        return "magenta"
    elif kind == "tool":
        return "yellow"
    return "white"


def print_executions_table(
    executions: List[Execution],
    console: Optional[Console] = None,
) -> None:
    """Render the `cz runs` summary table."""
    c = console or Console()

    if not executions:
        c.print("[yellow]No executions found in Cohzen store.[/yellow]")
        c.print("[dim]Run your application normally to record executions, or run [bold]cz init[/bold] first.[/dim]")
        return

    c.print("\n[bold white]Cohzen Executions[/bold white]\n")

    table = Table(
        show_header=True,
        header_style="bold dim",
        box=None,
        pad_edge=False,
        show_edge=False,
    )
    table.add_column("ID", style="bold cyan", no_wrap=True, min_width=10)
    table.add_column("Graph", style="white", min_width=16)
    table.add_column("Status", min_width=8, justify="center")
    table.add_column("Duration", justify="right", style="cyan", min_width=10)
    table.add_column("Started", style="dim", min_width=12)

    for ex in executions:
        time_str = ex.started_at.strftime("%H:%M:%S")
        status_icon = format_status_icon(ex.status)
        dur_str = format_duration(ex.duration_ms)
        table.add_row(
            ex.id,
            ex.graph_id,
            status_icon,
            dur_str,
            time_str,
        )

    c.print(table)
    c.print()


def print_execution_waterfall(
    execution: Execution,
    spans: List[Span],
    console: Optional[Console] = None,
    bar_width: int = 36,
) -> None:
    """Render a timeline waterfall chart showing offsets, duration bars, and span kinds."""
    c = console or Console()

    if not spans:
        c.print("[yellow]No spans recorded for this execution.[/yellow]")
        return

    # Calculate base start time and total duration
    start_times = [s.started_at for s in spans]
    base_time = min([execution.started_at, *start_times])
    total_ms = execution.duration_ms
    if not total_ms or total_ms <= 0:
        max_end = max([s.ended_at or s.started_at for s in spans])
        total_ms = max(1.0, (max_end - base_time).total_seconds() * 1000.0)

    # Responsive bar width based on console width
    console_width = c.width if c.width else 100
    bar_width = max(16, min(36, console_width - 58))

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold dim",
        pad_edge=False,
        title=f"[bold]Execution Waterfall[/bold] [dim]({len(spans)} spans • total {format_duration(total_ms)})[/dim]",
        title_justify="left",
    )
    table.add_column("Span / Operation", min_width=20, no_wrap=True)
    table.add_column("Kind", justify="center", width=7, no_wrap=True)
    table.add_column("Offset", justify="right", width=7, style="dim", no_wrap=True)
    table.add_column("Duration", justify="right", width=8, style="bold cyan", no_wrap=True)
    table.add_column("Status", justify="center", width=6, no_wrap=True)
    table.add_column(f"Timeline [dim](0ms ──> {format_duration(total_ms)})[/dim]", no_wrap=True)

    # Build hierarchy map to display tree indents in waterfall
    parent_map: Dict[Optional[str], List[Span]] = {}
    for s in spans:
        parent_map.setdefault(s.parent_id, []).append(s)

    ordered_spans: List[Tuple[Span, int]] = []

    def _traverse(pid: Optional[str], depth: int = 0) -> None:
        children = parent_map.get(pid, [])
        children.sort(key=lambda x: x.started_at)
        for child in children:
            ordered_spans.append((child, depth))
            _traverse(child.id, depth + 1)

    # Roots are graph spans or spans with parent_id not in span IDs
    span_ids = {s.id for s in spans}
    root_spans = [s for s in spans if not s.parent_id or s.parent_id not in span_ids]
    if root_spans:
        root_spans.sort(key=lambda x: x.started_at)
        for r in root_spans:
            ordered_spans.append((r, 0))
            _traverse(r.id, 1)
    else:
        ordered_spans = [(s, 0) for s in sorted(spans, key=lambda x: x.started_at)]

    # De-duplicate while preserving order
    seen_ids = set()
    deduped_spans = []
    for sp, depth in ordered_spans:
        if sp.id not in seen_ids:
            seen_ids.add(sp.id)
            deduped_spans.append((sp, depth))

    for span, depth in deduped_spans:
        offset_ms = max(0.0, (span.started_at - base_time).total_seconds() * 1000.0)
        dur_ms = span.duration_ms or 0.0

        # Compute bar start and width
        start_ratio = min(1.0, max(0.0, offset_ms / total_ms))
        dur_ratio = min(1.0, max(0.0, dur_ms / total_ms))

        start_col = int(start_ratio * bar_width)
        bar_len = max(1, int(dur_ratio * bar_width))
        if start_col + bar_len > bar_width:
            bar_len = max(1, bar_width - start_col)

        color = get_kind_color(span.kind)
        if span.status == "failed":
            bar_color = "red"
        else:
            bar_color = color

        prefix_spaces = " " * start_col
        bar_chars = "█" * bar_len
        suffix_spaces = " " * max(0, bar_width - (start_col + bar_len))
        timeline_bar = f"[{bar_color}]{prefix_spaces}{bar_chars}{suffix_spaces}[/{bar_color}]"

        indent = "  " * depth
        tree_prefix = "└─ " if depth > 0 else ""
        name_styled = f"{indent}{tree_prefix}[{color}]{span.name}[/{color}]"
        badge = get_kind_badge(span.kind)
        offset_str = f"+{int(offset_ms)}ms"
        dur_str = format_duration(span.duration_ms)
        status_str = format_status_icon(span.status)

        table.add_row(
            name_styled,
            badge,
            offset_str,
            dur_str,
            status_str,
            f"[{timeline_bar}]",
        )

    c.print()
    c.print(table)
    c.print()


def print_execution_tree(
    execution: Execution,
    spans: List[Span],
    console: Optional[Console] = None,
) -> None:
    """Render a collapsible/hierarchical Rich tree of the execution."""
    c = console or Console()

    root_label = Text()
    root_label.append(f"Execution {execution.id} ", style="bold white")
    root_label.append(f"[{execution.graph_id}] ", style="bold cyan")
    root_label.append(f"({format_duration(execution.duration_ms)}) ", style="dim")
    root_label.append("✓ completed" if execution.status == "completed" else f"● {execution.status}", style="bold green" if execution.status == "completed" else "bold yellow")

    tree = Tree(root_label)

    # Build parent -> children map
    span_map = {s.id: s for s in spans}
    children_map: Dict[Optional[str], List[Span]] = {}
    for s in spans:
        children_map.setdefault(s.parent_id, []).append(s)

    def _add_children(parent_node: Any, parent_id: Optional[str]) -> None:
        children = children_map.get(parent_id, [])
        children.sort(key=lambda s: s.started_at)
        for child in children:
            color = get_kind_color(child.kind)
            icon = "●" if child.status == "completed" else "✗"
            icon_style = "green" if child.status == "completed" else "red"

            node_text = Text()
            node_text.append(f"{icon} ", style=f"bold {icon_style}")
            node_text.append(f"[{child.kind.upper()}] ", style=f"bold {color}")
            node_text.append(f"{child.name} ", style=f"bold white")
            node_text.append(f"({format_duration(child.duration_ms)})", style="cyan")

            if child.reason:
                node_text.append(f" — \"{child.reason[:60]}...\"", style="italic dim cyan")

            child_branch = parent_node.add(node_text)
            _add_children(child_branch, child.id)

    # Find root spans
    span_ids = set(span_map.keys())
    root_spans = [s for s in spans if not s.parent_id or s.parent_id not in span_ids]
    if root_spans:
        root_spans.sort(key=lambda s: s.started_at)
        for r in root_spans:
            # If the root span is the graph span itself, show its children directly under tree
            if r.kind == "graph":
                _add_children(tree, r.id)
            else:
                color = get_kind_color(r.kind)
                icon = "●" if r.status == "completed" else "✗"
                r_text = Text()
                r_text.append(f"{icon} ", style="bold green" if r.status == "completed" else "bold red")
                r_text.append(f"[{r.kind.upper()}] ", style=f"bold {color}")
                r_text.append(f"{r.name} ", style="bold white")
                r_text.append(f"({format_duration(r.duration_ms)})", style="cyan")
                r_branch = tree.add(r_text)
                _add_children(r_branch, r.id)
    else:
        for s in sorted(spans, key=lambda x: x.started_at):
            tree.add(f"[{get_kind_color(s.kind)}]{s.name}[/] ({format_duration(s.duration_ms)})")

    c.print(Panel(tree, title="[bold]Execution Tree Hierarchy[/bold]", border_style="dim", box=box.ROUNDED))
    c.print()


def _format_payload_panel(data: Any, title: str, style: str = "cyan") -> Panel:
    """Format input/output/messages payload into a syntax-highlighted panel."""
    if data is None:
        return Panel("[dim]None[/dim]", title=f"[bold]{title}[/bold]", border_style="dim")

    if isinstance(data, (dict, list)):
        try:
            json_str = json.dumps(data, indent=2, default=str)
            return Panel(JSON(json_str), title=f"[bold]{title}[/bold]", border_style=style)
        except Exception:
            pass

    return Panel(str(data), title=f"[bold]{title}[/bold]", border_style=style)


def print_execution_details(
    execution: Execution,
    spans: List[Span],
    console: Optional[Console] = None,
    node_filter: Optional[str] = None,
) -> None:
    """Print complete, un-truncated details for captured inputs, outputs, prompts, LLMs, and tools."""
    c = console or Console()

    target_spans = spans
    if node_filter:
        target_spans = [s for s in spans if node_filter.lower() in s.name.lower() or (s.entity_id and node_filter.lower() in s.entity_id.lower())]
        if not target_spans:
            c.print(f"[yellow]No spans matching filter '{node_filter}'[/yellow]")
            return

    c.print(f"\n[bold white]Execution Details & Captured Context ({len(target_spans)} items)[/bold white]\n")

    for idx, span in enumerate(target_spans, start=1):
        color = get_kind_color(span.kind)
        badge = get_kind_badge(span.kind)
        status_icon = format_status_icon(span.status)
        dur = format_duration(span.duration_ms)

        header_text = Text()
        header_text.append(f"#{idx} ", style="dim")
        header_text.append(f"{span.name} ", style=f"bold {color}")
        header_text.append(f"({badge}) ", style="bold")
        header_text.append(f"{dur} ", style="bold cyan")
        header_text.append(f"{status_icon}", style="bold")

        sections: List[Any] = []

        # Meta & identifiers
        meta_items = [f"[dim]ID:[/dim] {span.id}"]
        if span.entity_id:
            meta_items.append(f"[dim]Entity:[/dim] [white]{span.entity_id}[/white]")
        if span.parent_id:
            meta_items.append(f"[dim]Parent:[/dim] {span.parent_id}")
        sections.append(Text.from_markup(" • ".join(meta_items)))

        # Reason / Why
        if span.reason:
            sections.append(Panel(f"[italic cyan]{span.reason}[/italic cyan]", title="[bold]🧠 Rationale / Why[/bold]", border_style="cyan"))

        # Error
        if span.error:
            sections.append(Panel(f"[bold red]{span.error}[/bold red]", title="[bold]✗ Error[/bold]", border_style="red"))

        # Kind-specific details
        if span.kind == "llm":
            # Model & Invocation params
            llm_info = []
            if span.metadata.get("model"):
                llm_info.append(f"[bold]Model:[/bold] {span.metadata['model']}")
            if span.metadata.get("provider"):
                llm_info.append(f"[bold]Provider:[/bold] {span.metadata['provider']}")
            if span.metadata.get("token_usage"):
                tu = span.metadata["token_usage"]
                if isinstance(tu, dict):
                    llm_info.append(
                        f"[bold]Tokens:[/bold] prompt={tu.get('prompt_tokens', tu.get('prompt', '—'))}, "
                        f"completion={tu.get('completion_tokens', tu.get('completion', '—'))}, "
                        f"total={tu.get('total_tokens', tu.get('total', '—'))}"
                    )
            if llm_info:
                sections.append(Panel(Text.from_markup(" • ".join(llm_info)), title="[bold]🤖 Model Parameters & Usage[/bold]", border_style="magenta"))

            # Prompt / Input Messages
            sections.append(_format_payload_panel(span.input, "📥 Input Messages / Prompt", style="magenta"))

            # Generation Output
            sections.append(_format_payload_panel(span.output, "📤 LLM Response / Tool Calls", style="green"))

        elif span.kind == "tool":
            sections.append(_format_payload_panel(span.input, f"🛠️ Tool Input Arguments ({span.name})", style="yellow"))
            sections.append(_format_payload_panel(span.output, f"📤 Tool Result", style="green"))

        else:
            # Node or Graph span
            sections.append(_format_payload_panel(span.input, f"📥 Input State ({span.name})", style="cyan"))
            sections.append(_format_payload_panel(span.output, f"📤 Output State Update", style="green"))

        # Extra Metadata
        filtered_meta = {k: v for k, v in span.metadata.items() if k not in ("token_usage", "model", "provider", "invocation_params")}
        if filtered_meta:
            sections.append(Panel(JSON(json.dumps(filtered_meta, indent=2, default=str)), title="[dim]Context Metadata[/dim]", border_style="dim"))

        c.print(Panel(Group(*sections), title=header_text, border_style=color, box=box.ROUNDED))
        c.print()


def print_execution_detail(
    execution: Execution,
    spans: List[Span],
    console: Optional[Console] = None,
    verbose: bool = False,
    show_waterfall: bool = True,
    show_tree: bool = True,
    show_details: bool = False,
    node_filter: Optional[str] = None,
) -> None:
    """Render the detailed flow graph, waterfall, tree, and stats for `cz run <execution-id>`."""
    c = console or Console()

    c.print(f"\n[bold white]Execution {execution.id}[/bold white]")
    c.print("━" * 40)
    c.print(f"[bold]Target Graph[/bold]   {execution.graph_id}")
    status_text = (
        "[bold green]✓ completed[/bold green]"
        if execution.status == "completed"
        else (
            "[bold red]✗ failed[/bold red]"
            if execution.status == "failed"
            else "[bold yellow]● running[/bold yellow]"
        )
    )
    c.print(f"[bold]Status[/bold]         {status_text}")
    c.print(f"[bold]Duration[/bold]       {format_duration(execution.duration_ms)}")
    c.print(f"[bold]Started At[/bold]     {execution.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if execution.reason:
        c.print(f"[bold]Goal / Why[/bold]     [italic cyan]{execution.reason}[/italic cyan]")
    if execution.error:
        c.print(f"[bold red]Error[/bold red]          {execution.error}")

    llm_count = sum(1 for s in spans if s.kind == "llm")
    tool_count = sum(1 for s in spans if s.kind == "tool")
    node_count = sum(1 for s in spans if s.kind == "node")
    c.print(f"[bold]Breakdown[/bold]      [cyan]{node_count} nodes[/cyan] • [magenta]{llm_count} LLM calls[/magenta] • [yellow]{tool_count} tool calls[/yellow]")
    c.print("━" * 40)

    # 1. Timeline Waterfall
    if show_waterfall:
        print_execution_waterfall(execution, spans, console=c)

    # 2. Hierarchical Tree
    if show_tree and not show_details and not verbose:
        print_execution_tree(execution, spans, console=c)

    # 3. Full Details
    if show_details or verbose or node_filter:
        print_execution_details(execution, spans, console=c, node_filter=node_filter)
