"""Command-line interface for Cohzen (cz)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cz import __version__
from cz.formatters.console import print_audit_report, print_console_report
from cz.formatters.json_fmt import format_json
from cz.formatters.mermaid import format_mermaid
from cz.scanner.engine import scan_repository

app = typer.Typer(
    name="cz",
    help="cz - Statically scan repositories to reconstruct LangGraph architecture and generate system manifests.",
    add_completion=False,
)
console = Console()


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    MERMAID = "mermaid"


@app.command(name="scan")
def scan(
    path: str = typer.Argument(
        ".",
        help="Path to repository or directory to scan (defaults to current directory)",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format: table (rich interactive terminal), json (system manifest), or mermaid (diagram)",
    ),
    mermaid: bool = typer.Option(
        False,
        "--mermaid",
        help="Shortcut to output Mermaid diagram (equivalent to -f mermaid)",
    ),
    json_output_flag: bool = typer.Option(
        False,
        "--json",
        help="Shortcut to output Cohzen Manifest JSON (equivalent to -f json)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to a specified file instead of stdout",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Display detailed debugging info during scan",
    ),
    view: bool = typer.Option(
        False,
        "--view",
        help="Open an interactive graphical visualizer in the default browser",
    ),
) -> None:
    """Scan a codebase to reconstruct LangGraph architecture and produce a system manifest."""
    if mermaid:
        format = OutputFormat.MERMAID
    elif json_output_flag:
        format = OutputFormat.JSON

    if format == OutputFormat.TABLE and not output and not view:
        with console.status(f"[bold cyan]Scanning repository for LangGraph architectures at {path}...[/bold cyan]"):
            result = scan_repository(path, verbose=verbose)
    else:
        result = scan_repository(path, verbose=verbose)

    if view:
        from cz.formatters.viewer import open_in_browser
        viewer_path = open_in_browser(result)
        console.print(f"[bold green]✔ Opened interactive architecture visualizer in browser ({viewer_path})[/bold green]")
        return

    # Format the result
    if format == OutputFormat.TABLE:
        if output:
            file_console = Console(record=True, width=120)
            print_console_report(result, console=file_console)
            output.write_text(file_console.export_text(), encoding="utf-8")
            console.print(f"[green]✔ Saved scan table report to {output}[/green]")
        else:
            print_console_report(result, console=console)

    elif format == OutputFormat.JSON:
        json_output = format_json(result)
        if output:
            output.write_text(json_output, encoding="utf-8")
            console.print(f"[green]✔ Saved JSON manifest to {output}[/green]")
        else:
            print(json_output)

    elif format == OutputFormat.MERMAID:
        mermaid_output = format_mermaid(result)
        if output:
            output.write_text(mermaid_output, encoding="utf-8")
            console.print(f"[green]✔ Saved Mermaid diagram to {output}[/green]")
        else:
            print(mermaid_output)


@app.command(name="audit")
def audit(
    path: str = typer.Argument(
        ".",
        help="Path to repository or directory to audit (defaults to current directory)",
    ),
    json_output_flag: bool = typer.Option(
        False,
        "--json",
        help="Output audit findings and coverage as JSON",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to a specified file instead of stdout",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Display detailed debugging info during scan",
    ),
) -> None:
    """Audit observability, tracing, and telemetry instrumentation across nodes and tools."""
    if not output and not json_output_flag:
        with console.status(f"[bold magenta]Auditing observability instrumentation at {path}...[/bold magenta]"):
            result = scan_repository(path, verbose=verbose)
    else:
        result = scan_repository(path, verbose=verbose)

    if json_output_flag:
        audit_json = result.observability.model_dump_json(indent=2) if result.observability else "{}"
        if output:
            output.write_text(audit_json, encoding="utf-8")
            console.print(f"[green]✔ Saved audit JSON to {output}[/green]")
        else:
            print(audit_json)
    else:
        if output:
            file_console = Console(record=True, width=120)
            print_audit_report(result, console=file_console)
            output.write_text(file_console.export_text(), encoding="utf-8")
            console.print(f"[green]✔ Saved audit report to {output}[/green]")
        else:
            print_audit_report(result, console=console)


@app.command(name="view")
def view_graph(
    path: str = typer.Argument(".", help="Path to repository or file to visualize"),
) -> None:
    """Scan and open an interactive graphical visualizer in your browser."""
    from cz.formatters.viewer import open_in_browser
    result = scan_repository(path)
    viewer_path = open_in_browser(result)
    console.print(f"[bold green]✔ Opened interactive architecture visualizer in browser ({viewer_path})[/bold green]")


@app.command(name="version")
def version() -> None:
    """Display the version of cz."""
    console.print(f"[bold cyan]cz[/bold cyan] version [green]{__version__}[/green]")


def main() -> None:
    """CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
