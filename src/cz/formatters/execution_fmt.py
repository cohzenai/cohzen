"""Terminal formatters for executions, spans, and runs (v0.2)."""

from __future__ import annotations

from typing import List, Optional
from rich.console import Console
from rich.table import Table

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


def print_execution_detail(
    execution: Execution,
    spans: List[Span],
    console: Optional[Console] = None,
    verbose: bool = False,
) -> None:
    """Render the detailed flow graph and stats for `cz run <execution-id>`."""
    c = console or Console()

    c.print(f"\n[bold white]Execution {execution.id}[/bold white]")
    c.print("─" * 28)
    c.print(f"[bold]Graph[/bold]       {execution.graph_id}")
    status_text = (
        "[bold green]✓ completed[/bold green]"
        if execution.status == "completed"
        else (
            "[bold red]✗ failed[/bold red]"
            if execution.status == "failed"
            else "[bold yellow]● running[/bold yellow]"
        )
    )
    c.print(f"[bold]Status[/bold]      {status_text}")
    c.print(f"[bold]Duration[/bold]    {format_duration(execution.duration_ms)}")
    if execution.reason:
        c.print(f"[bold]Goal / Why[/bold]  [italic cyan]{execution.reason}[/italic cyan]")
    if execution.error:
        c.print(f"[bold red]Error[/bold red]       {execution.error}")
    c.print()

    # Filter out root graph span to show internal step sequence
    step_spans = [s for s in spans if s.kind != "graph"]
    # If no sub-spans, fallback to showing all spans
    if not step_spans and spans:
        step_spans = spans

    llm_count = sum(1 for s in spans if s.kind == "llm")
    tool_count = sum(1 for s in spans if s.kind == "tool")
    node_count = sum(1 for s in spans if s.kind == "node")

    if step_spans:
        c.print("[bold green]START[/bold green]")
        for span in step_spans:
            c.print("  [dim]│[/dim]")
            c.print("  [dim]▼[/dim]")

            # Styling by kind
            if span.kind == "llm":
                name_style = "[bold magenta]"
            elif span.kind == "tool":
                name_style = "[bold yellow]"
            else:
                name_style = "[bold white]"

            dur_str = format_duration(span.duration_ms)
            span_label = f"{name_style}{span.name}[/]"
            dots = " " * max(1, 32 - len(span.name))
            status_indicator = " [red]✗[/red]" if span.status == "failed" else ""
            c.print(f"{span_label}{dots}[cyan]{dur_str}[/cyan]{status_indicator}")

            if span.reason:
                c.print(f"      [dim]why:[/dim] [italic cyan]{span.reason}[/italic cyan]")

            if verbose:
                if span.entity_id:
                    c.print(f"      [dim]entity: {span.entity_id}[/dim]")
                if span.input:
                    c.print(f"      [dim]input: {str(span.input)[:120]}[/dim]")
                if span.output:
                    c.print(f"      [dim]output: {str(span.output)[:120]}[/dim]")
                if span.error:
                    c.print(f"      [bold red]error: {span.error}[/bold red]")

        c.print("  [dim]│[/dim]")
        c.print("  [dim]▼[/dim]")
        c.print("[bold green]END[/bold green]")
        c.print()

    # Metric summary
    c.print(f"[bold]LLM calls[/bold]     {llm_count}")
    c.print(f"[bold]Tool calls[/bold]    {tool_count}")
    c.print(f"[bold]Nodes[/bold]         {node_count}")
    c.print()
