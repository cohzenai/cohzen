"""Tests for CLI commands: cz init, cz runs, cz run (v0.2)."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typer.testing import CliRunner

from cz.cli.main import app
from cz.execution.models import Execution, Span
from cz.execution.sqlite import SQLiteExecutionStore

runner = CliRunner()
SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_graphs"


def test_cli_init_command(tmp_path: Path):
    # Prepare mock app directory with a simple Python file and git
    app_file = tmp_path / "app.py"
    app_file.write_text("from langgraph.graph import StateGraph\nbuilder = StateGraph(dict)\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Cohzen initialized at" in result.stdout
    assert ".cohzen/manifest.json" in result.stdout
    assert ".cohzen/executions.db" in result.stdout
    assert "sitecustomize.py" in result.stdout

    # Check artifacts created
    cohzen_dir = tmp_path / ".cohzen"
    assert cohzen_dir.is_dir()
    assert (cohzen_dir / "manifest.json").is_file()
    assert (cohzen_dir / "executions.db").is_file()
    assert (tmp_path / "sitecustomize.py").is_file()

    # Check gitignore
    gitignore = tmp_path / ".gitignore"
    assert gitignore.is_file()
    assert ".cohzen/" in gitignore.read_text(encoding="utf-8")

    # Re-run without force warns
    res_warn = runner.invoke(app, ["init", str(tmp_path)])
    assert res_warn.exit_code == 0
    assert "already initialized" in res_warn.stdout

    # Re-run with --force succeeds
    res_force = runner.invoke(app, ["init", str(tmp_path), "--force"])
    assert res_force.exit_code == 0
    assert "Cohzen initialized at" in res_force.stdout


def test_cli_runs_empty(tmp_path: Path):
    result = runner.invoke(app, ["runs", str(tmp_path)])
    assert result.exit_code == 0
    assert "No execution store found" in result.stdout


def test_cli_runs_and_run_detail(tmp_path: Path):
    # Setup store with test execution data matching user spec
    cohzen_dir = tmp_path / ".cohzen"
    cohzen_dir.mkdir(parents=True, exist_ok=True)
    db_path = cohzen_dir / "executions.db"
    store = SQLiteExecutionStore(db_path=db_path)

    # Execution a82f91
    now = datetime(2026, 9, 27, 20, 41, 12, tzinfo=timezone.utc)
    ex1 = Execution(
        id="a82f91",
        graph_id="customer_flow",
        status="completed",
        started_at=now,
        ended_at=now,
        duration_ms=2410.0,
    )
    store.create_execution(ex1)
    store.finish_execution("a82f91", status="completed", ended_at=now, duration_ms=2410.0)

    # Execution 91be22
    ex2 = Execution(
        id="91be22",
        graph_id="customer_flow",
        status="completed",
        started_at=datetime(2026, 9, 27, 20, 40, 51, tzinfo=timezone.utc),
        duration_ms=1870.0,
    )
    store.create_execution(ex2)

    # Execution 7b102e
    ex3 = Execution(
        id="7b102e",
        graph_id="customer_flow",
        status="failed",
        started_at=datetime(2026, 9, 27, 20, 39, 44, tzinfo=timezone.utc),
        duration_ms=3120.0,
        error="ValueError: Customer not found",
    )
    store.create_execution(ex3)

    # Spans for a82f91
    spans_data = [
        Span(id="sp1", execution_id="a82f91", entity_id="node.planner", kind="node", name="planner", status="completed", duration_ms=420.0),
        Span(id="sp2", execution_id="a82f91", parent_id="sp1", entity_id="model.openai.gpt-4o", kind="llm", name="llm:gpt-4o", status="completed", duration_ms=810.0),
        Span(id="sp3", execution_id="a82f91", parent_id="sp1", entity_id="tool.search", kind="tool", name="search", status="completed", duration_ms=210.0),
        Span(id="sp4", execution_id="a82f91", entity_id="node.writer", kind="node", name="writer", status="completed", duration_ms=930.0),
    ]
    for s in spans_data:
        store.create_span(s)
        store.finish_span(s.id, status=s.status, ended_at=now, duration_ms=s.duration_ms)

    # 1. Test `cz runs`
    res_runs = runner.invoke(app, ["runs", str(tmp_path)])
    assert res_runs.exit_code == 0
    assert "Cohzen Executions" in res_runs.stdout
    assert "a82f91" in res_runs.stdout
    assert "91be22" in res_runs.stdout
    assert "7b102e" in res_runs.stdout
    assert "customer_flow" in res_runs.stdout
    assert "2.41s" in res_runs.stdout
    assert "1.87s" in res_runs.stdout
    assert "3.12s" in res_runs.stdout

    # 2. Test `cz runs --json`
    res_runs_json = runner.invoke(app, ["runs", str(tmp_path), "--json"])
    assert res_runs_json.exit_code == 0
    runs_data = json.loads(res_runs_json.stdout)
    assert len(runs_data) == 3
    assert runs_data[0]["id"] == "a82f91"

    # 3. Test `cz run a82f91`
    res_run_detail = runner.invoke(app, ["run", "a82f91", "--path", str(tmp_path)])
    assert res_run_detail.exit_code == 0
    out = res_run_detail.stdout
    assert "Execution a82f91" in out
    assert "customer_flow" in out
    assert "completed" in out
    assert "2.41s" in out
    assert "planner" in out
    assert "420ms" in out
    assert "llm:gpt-4o" in out
    assert "810ms" in out
    assert "search" in out
    assert "210ms" in out
    assert "writer" in out
    assert "930ms" in out
    assert "LLM calls" in out
    assert "tool calls" in out.lower()
    assert "nodes" in out.lower()

    # 4. Test `cz run a82f91 --json`
    res_run_json = runner.invoke(app, ["run", "a82f91", "--path", str(tmp_path), "--json"])
    assert res_run_json.exit_code == 0
    detail_data = json.loads(res_run_json.stdout)
    assert detail_data["execution"]["id"] == "a82f91"
    assert len(detail_data["spans"]) == 4

    # 5. Test unknown execution ID
    res_unknown = runner.invoke(app, ["run", "nonexistent_id", "--path", str(tmp_path)])
    assert res_unknown.exit_code == 0
    assert "not found in store" in res_unknown.stdout
