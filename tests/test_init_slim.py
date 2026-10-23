"""Tests for cz init slim terminal output."""

from __future__ import annotations

import importlib
from pathlib import Path

from typer.testing import CliRunner

from cz.cli.main import app

runner = CliRunner()


def test_cz_init_shows_topology_and_omits_audit_and_flowchart(tmp_path: Path, monkeypatch):
    """cz init should display only graph topology & routing edges + init summary."""
    app_file = tmp_path / "app.py"
    app_file.write_text(
        """from langgraph.graph import StateGraph, START, END

builder = StateGraph(dict)
builder.add_node("step_a", lambda x: x)
builder.add_node("step_b", lambda x: x)
builder.add_edge(START, "step_a")
builder.add_edge("step_a", "step_b")
builder.add_edge("step_b", END)
graph = builder.compile()
""",
        encoding="utf-8",
    )
    (tmp_path / ".git").mkdir()

    hook = tmp_path / "venv-site" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    result = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert result.exit_code == 0

    # Must contain the topology table and init summary
    assert "Graph Topology & Routing Edges" in result.stdout
    assert "step_a" in result.stdout
    assert "step_b" in result.stdout
    assert "Cohzen initialized at" in result.stdout
    assert ".cohzen/manifest.json" in result.stdout
    assert ".cohzen/executions.db" in result.stdout

    # Must NOT contain verbose scan/audit panels
    assert "Cohzen Architecture Scanner" not in result.stdout
    assert "Architecture Flow" not in result.stdout
    assert "Registered Nodes & Handlers" not in result.stdout
    assert "Observability Audit" not in result.stdout
    assert "Node Instrumentation Status" not in result.stdout


def test_cz_init_with_no_edges(tmp_path: Path, monkeypatch):
    """cz init on a repo with no edges reports no edges detected gracefully."""
    app_file = tmp_path / "app.py"
    app_file.write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    hook = tmp_path / "venv-site" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    result = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "No graph edges detected in static scan." in result.stdout
    assert "Cohzen initialized at" in result.stdout
