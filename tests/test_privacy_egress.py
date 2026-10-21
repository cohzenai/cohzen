"""Privacy and zero-egress verification test for Cohzen CLI and runtime capture operations."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cz.cli.main import app
from cz.formatters.json_fmt import format_json
from cz.formatters.mermaid import format_mermaid
from cz.scanner.engine import scan_repository


def test_cli_scan_and_audit_perform_zero_network_egress(monkeypatch):
    """Verify that static scanning, formatters, and telemetry auditing make zero outbound network calls."""
    connections: list[tuple] = []

    def fail_on_connect(self, *args, **kwargs):
        connections.append(args)
        raise RuntimeError(f"Unexpected network egress attempt during scan: {args}")

    monkeypatch.setattr(socket.socket, "connect", fail_on_connect)

    sample_dir = Path(__file__).parent / "fixtures" / "sample_graphs"
    result = scan_repository(str(sample_dir))

    # Assert static analysis completed without network requests
    assert len(result.graphs) > 0
    assert len(connections) == 0

    # Assert formatting & serialization make zero network calls
    json_out = format_json(result)
    mermaid_out = format_mermaid(result)
    assert len(json_out) > 0
    assert len(mermaid_out) > 0
    assert len(connections) == 0


def test_runtime_capture_and_runs_cli_perform_zero_network_egress(tmp_path: Path, monkeypatch):
    """Verify that graph interception, async writer thread, SQLite persistence, and cz runs perform zero network egress."""
    pytest.importorskip("langgraph")
    from langgraph.graph import END, START, StateGraph

    from cz.execution.instrumentation import install, uninstall
    from cz.execution.sqlite import SQLiteExecutionStore
    from cz.execution.writer import AsyncExecutionStore

    connections: list[tuple] = []

    def fail_on_connect(self, *args, **kwargs):
        connections.append(args)
        raise RuntimeError(f"Unexpected network egress attempt during capture: {args}")

    monkeypatch.setattr(socket.socket, "connect", fail_on_connect)

    builder = StateGraph(dict)
    builder.add_node("process_step", lambda state: {"result": "success", "token": "secret-123"})
    builder.add_edge(START, "process_step")
    builder.add_edge("process_step", END)
    graph = builder.compile()

    db_path = tmp_path / ".cohzen" / "executions.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = AsyncExecutionStore(SQLiteExecutionStore(db_path))
    install(store=store)

    try:
        res = graph.invoke({"input_key": "input_val"})
        assert res == {"result": "success", "token": "secret-123"}
    finally:
        uninstall()

    assert store.flush(2.0)
    runs = store.list_executions()
    assert len(runs) == 1
    assert runs[0].status == "completed"

    # Invoke `cz runs` CLI command on the directory
    runner = CliRunner()
    cli_res = runner.invoke(app, ["runs", str(tmp_path)])
    assert cli_res.exit_code == 0
    assert "LangGraph" in cli_res.stdout or "✓" in cli_res.stdout

    # Assert zero network socket connections were attempted
    assert len(connections) == 0
