"""Targeted regression tests for v0.3.2 bug fixes."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

from typer.testing import CliRunner

from cz import __version__
from cz.cli.main import app
from cz.execution.sqlite import SQLiteExecutionStore
from cz.scanner.engine import scan_repository

runner = CliRunner()


def test_syntax_error_reported_prominently(tmp_path: Path):
    """Bug fix: Syntax errors must not be silently reported as 'No graphs found'."""
    bad_file = tmp_path / "broken_agent.py"
    bad_file.write_text("def broken_func(\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    # Must report parsing & syntax error panel
    assert "Parsing & Syntax Errors" in result.stdout
    assert "SyntaxError" in result.stdout
    assert "broken_agent.py" in result.stdout
    # Must explain that syntax errors prevented graph discovery
    assert "contained syntax or parsing errors" in result.stdout


def test_empty_repo_audit_coverage_reports_na(tmp_path: Path):
    """Bug fix: Empty repo must report 'n/a, no nodes found' instead of 100% coverage."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    res = runner.invoke(app, ["audit", str(empty_dir)])
    assert res.exit_code == 0
    assert "n/a, no nodes found" in res.stdout
    assert "100.0%" not in res.stdout
    assert "(100%)" not in res.stdout

    scan_res = scan_repository(str(empty_dir))
    assert scan_res.observability is not None
    assert scan_res.observability.agent_instrumentation_pct is None


def test_cz_version_reads_package_metadata():
    """Bug fix: cz version must read from package metadata (single source of truth)."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "cz version" in result.stdout

    # Verify that __version__ matches metadata or fallback
    try:
        expected = importlib.metadata.version("cohzen")
    except Exception:
        expected = "unknown"

    assert expected in result.stdout
    assert __version__ == expected


def test_cz_capture_missing_command_one_line_error(tmp_path: Path):
    """Bug fix: Missing executable in cz capture must show clean one-line error, not 40-line traceback."""
    result = runner.invoke(app, ["capture", "--path", str(tmp_path), "--", "nonexistent_executable_binary_xyz_123"])
    assert result.exit_code == 127
    assert "Command not found: 'nonexistent_executable_binary_xyz_123'" in result.stdout
    assert "Traceback (most recent call last)" not in result.stdout


def test_cz_run_bad_id_exits_nonzero(tmp_path: Path):
    """Bug fix: cz run <bad_id> must exit non-zero (code 1) when execution is not found."""
    # Create empty store
    cohzen_dir = tmp_path / ".cohzen"
    cohzen_dir.mkdir(parents=True)
    db_path = cohzen_dir / "executions.db"
    SQLiteExecutionStore(db_path=db_path)

    result = runner.invoke(app, ["run", "bad_id_12345", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found in store" in result.stdout
