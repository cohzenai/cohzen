"""Tests for CLI commands: cz init, cz runs, cz run (v0.2)."""

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from cz.cli.main import app
from cz.execution.models import Execution, Span
from cz.execution.sqlite import SQLiteExecutionStore

runner = CliRunner()
SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_graphs"


def test_cli_init_command(tmp_path: Path, monkeypatch):
    # Prepare mock app directory with a simple Python file and git
    app_file = tmp_path / "app.py"
    app_file.write_text(
        "from langgraph.graph import StateGraph\nbuilder = StateGraph(dict)\n",
        encoding="utf-8",
    )
    (tmp_path / ".git").mkdir()

    hook = tmp_path / "venv-site" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))
    result = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "Cohzen initialized at" in result.stdout
    assert ".cohzen/manifest.json" in result.stdout
    assert ".cohzen/executions.db" in result.stdout
    assert "Startup hook" in result.stdout

    # Check artifacts created
    cohzen_dir = tmp_path / ".cohzen"
    assert cohzen_dir.is_dir()
    assert (cohzen_dir / "manifest.json").is_file()
    assert (cohzen_dir / "executions.db").is_file()
    hook_content = hook.read_text(encoding="utf-8")
    assert "cz._startup" in hook_content
    assert "except Exception:" in hook_content

    # Check gitignore
    gitignore = tmp_path / ".gitignore"
    assert gitignore.is_file()
    assert ".cohzen/" in gitignore.read_text(encoding="utf-8")

    # Re-run is idempotent.
    res_repeat = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert res_repeat.exit_code == 0
    assert "Cohzen initialized at" in res_repeat.stdout


def test_cli_capture_runs_a_command_without_project_startup_edits(tmp_path: Path):
    script = tmp_path / "app.py"
    script.write_text("print('captured command ran')\n", encoding="utf-8")

    result = runner.invoke(app, ["capture", "--", sys.executable, str(script)])

    assert result.exit_code == 0
    assert "runs the supplied command" in result.stdout
    assert not (tmp_path / "sitecustomize.py").exists()


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
        Span(
            id="sp1",
            execution_id="a82f91",
            entity_id="node.planner",
            kind="node",
            name="planner",
            status="completed",
            duration_ms=420.0,
        ),
        Span(
            id="sp2",
            execution_id="a82f91",
            parent_id="sp1",
            entity_id="model.openai.gpt-4o",
            kind="llm",
            name="llm:gpt-4o",
            status="completed",
            duration_ms=810.0,
        ),
        Span(
            id="sp3",
            execution_id="a82f91",
            parent_id="sp1",
            entity_id="tool.search",
            kind="tool",
            name="search",
            status="completed",
            duration_ms=210.0,
        ),
        Span(
            id="sp4",
            execution_id="a82f91",
            entity_id="node.writer",
            kind="node",
            name="writer",
            status="completed",
            duration_ms=930.0,
        ),
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
    assert "START" in out
    assert "planner" in out
    assert "420ms" in out
    assert "llm:gpt-4o" in out
    assert "810ms" in out
    assert "search" in out
    assert "210ms" in out
    assert "writer" in out
    assert "930ms" in out
    assert "END" in out
    assert "LLM calls     1" in out
    assert "Tool calls    1" in out
    assert "Nodes         2" in out or "Nodes         4" in out

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


def test_cli_init_aborts_without_yes(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code != 0
    assert not (tmp_path / ".cohzen").exists()


def test_cli_init_migrates_legacy_sitecustomize_and_pth(tmp_path: Path, monkeypatch):
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "import os\n"
        "# Cohzen auto-instrumentation hook (generated by cz init)\n"
        "try:\n"
        "    import cz.execution\n"
        "    cz.execution.install()\n"
        "except Exception:\n"
        "    pass\n"
        "custom_value = 42\n",
        encoding="utf-8",
    )
    hook = tmp_path / "site-packages" / "cohzen_startup.pth"
    legacy_hook = tmp_path / "site-packages" / "cohzen.pth"
    legacy_hook.parent.mkdir(parents=True, exist_ok=True)
    legacy_hook.write_text("import cz.legacy\n", encoding="utf-8")

    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    result = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "Migrated legacy hook: cleaned" in result.stdout
    assert "Migrated legacy hook: removed" in result.stdout
    assert hook.is_file()
    assert not legacy_hook.exists()
    assert "cz.execution" not in sitecustomize.read_text(encoding="utf-8")
    assert "custom_value = 42" in sitecustomize.read_text(encoding="utf-8")


def test_cli_status_and_on_off_toggle(tmp_path: Path, monkeypatch):
    hook = tmp_path / "site-packages" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    res_pre = runner.invoke(app, ["status", str(tmp_path)])
    assert "not initialized" in res_pre.stdout

    runner.invoke(app, ["init", str(tmp_path), "--yes"])

    res_stat = runner.invoke(app, ["status", str(tmp_path)])
    assert res_stat.exit_code == 0
    assert "Enabled: True" in res_stat.stdout
    assert "Startup hook" in res_stat.stdout

    res_off = runner.invoke(app, ["off", str(tmp_path)])
    assert res_off.exit_code == 0
    assert "disabled" in res_off.stdout

    res_stat2 = runner.invoke(app, ["status", str(tmp_path)])
    assert "Enabled: False" in res_stat2.stdout

    res_on = runner.invoke(app, ["on", str(tmp_path)])
    assert res_on.exit_code == 0
    assert "enabled" in res_on.stdout

    res_stat3 = runner.invoke(app, ["status", str(tmp_path)])
    assert "Enabled: True" in res_stat3.stdout


def test_cli_deinit_aborts_without_yes(tmp_path: Path):
    cohzen_dir = tmp_path / ".cohzen"
    cohzen_dir.mkdir(parents=True)
    result = runner.invoke(app, ["deinit", str(tmp_path)])
    assert result.exit_code != 0
    assert cohzen_dir.exists()


def test_cli_deinit_removes_artifacts_and_startup_hook(tmp_path: Path, monkeypatch):
    hook = tmp_path / "site-packages" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert (tmp_path / ".cohzen").exists()
    assert hook.exists()

    result = runner.invoke(app, ["deinit", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "Cohzen deinitialized at" in result.stdout
    assert not (tmp_path / ".cohzen").exists()
    assert not hook.exists()
    gitignore = tmp_path / ".gitignore"
    if gitignore.exists():
        assert ".cohzen" not in gitignore.read_text(encoding="utf-8")


def test_cli_deinit_keep_data_retains_executions_db(tmp_path: Path, monkeypatch):
    hook = tmp_path / "site-packages" / "cohzen_startup.pth"
    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    runner.invoke(app, ["init", str(tmp_path), "--yes"])
    db_file = tmp_path / ".cohzen" / "executions.db"
    assert db_file.exists()

    result = runner.invoke(app, ["deinit", str(tmp_path), "--yes", "--keep-data"])
    assert result.exit_code == 0
    assert db_file.exists()
    assert not (tmp_path / ".cohzen" / "config.toml").exists()
    assert not (tmp_path / ".cohzen" / "manifest.json").exists()
    assert not hook.exists()


def test_migration_of_030_and_legacy_pth_hooks(tmp_path: Path, monkeypatch):
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    hook = site_packages / "cohzen_startup.pth"
    legacy_hook = site_packages / "cohzen.pth"

    # Write old 0.3.0 hook without try/except
    hook.write_text("import cz._startup; cz._startup.start()\n", encoding="utf-8")
    # Write legacy 0.2.0 hook
    legacy_hook.write_text("import cz.execution; cz.execution.install()\n", encoding="utf-8")

    cli_module = importlib.import_module("cz.cli.main")
    monkeypatch.setattr(cli_module, "_hook_path", lambda _python: (hook, None))

    # Run cz init: should overwrite hook with safe try/except and delete legacy_hook
    init_res = runner.invoke(app, ["init", str(tmp_path), "--yes"])
    assert init_res.exit_code == 0
    hook_content = hook.read_text(encoding="utf-8")
    assert "try:" in hook_content
    assert "except Exception:" in hook_content
    assert not legacy_hook.exists()

    # If an old legacy hook was recreated alongside
    legacy_hook.write_text("legacy hook", encoding="utf-8")

    # Run cz deinit: should delete both
    deinit_res = runner.invoke(app, ["deinit", str(tmp_path), "--yes"])
    assert deinit_res.exit_code == 0
    assert not hook.exists()
    assert not legacy_hook.exists()
