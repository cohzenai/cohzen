"""Targeted regression tests for v0.3.3 bug fixes and improvements.

Fixes covered:
- agent_instrumentation_pct returns None (JSON null) when total_agents == 0.
- --min-coverage is skipped with an INFO line on empty repos (exit 0 by default).
- --fail-on-empty exits 1 when no agent nodes are found.
- Version fallback is "unknown", not a hardcoded version string.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cz.cli.main import app
from cz.scanner.engine import scan_repository

runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. agent_instrumentation_pct == None (JSON null) for zero-node repos
# ---------------------------------------------------------------------------


def test_agent_instrumentation_pct_is_none_for_empty_repo(tmp_path: Path) -> None:
    """agent_instrumentation_pct must be None (not 0.0) when total_agents == 0."""
    scan_res = scan_repository(str(tmp_path))
    assert scan_res.observability is not None
    assert scan_res.observability.total_agents == 0
    assert scan_res.observability.agent_instrumentation_pct is None


def test_audit_json_agent_instrumentation_pct_null_for_empty_repo(tmp_path: Path) -> None:
    """cz audit --json must emit null (not 0.0) for agent_instrumentation_pct on empty repos."""
    result = runner.invoke(app, ["audit", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "agent_instrumentation_pct" in data
    assert data["agent_instrumentation_pct"] is None, (
        f"Expected null, got {data['agent_instrumentation_pct']!r}"
    )


def test_audit_terminal_still_shows_na_for_empty_repo(tmp_path: Path) -> None:
    """Terminal audit must still show 'n/a, no nodes found' for empty repos (regression guard)."""
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "n/a, no nodes found" in result.output
    assert "100.0%" not in result.output
    assert "(100%)" not in result.output


# ---------------------------------------------------------------------------
# 2. --min-coverage gate: skip with INFO line + exit 0 on empty repos
# ---------------------------------------------------------------------------


def test_min_coverage_skipped_on_empty_repo_exits_zero(tmp_path: Path) -> None:
    """--min-coverage must be skipped (exit 0, INFO line) when no nodes are found."""
    result = runner.invoke(app, ["audit", str(tmp_path), "--min-coverage", "80"])
    assert result.exit_code == 0, (
        f"Expected exit 0, got {result.exit_code}.\n{result.output}"
    )
    assert "--min-coverage skipped" in result.output or "INFO" in result.output, (
        "Expected an INFO line explaining the skip, got:\n" + result.output
    )


# ---------------------------------------------------------------------------
# 3. --fail-on-empty gate: exit 1 when no agent nodes found
# ---------------------------------------------------------------------------


def test_fail_on_empty_exits_nonzero_for_empty_repo(tmp_path: Path) -> None:
    """--fail-on-empty must exit 1 when no agent nodes are found."""
    result = runner.invoke(app, ["audit", str(tmp_path), "--fail-on-empty"])
    assert result.exit_code == 1, (
        f"Expected exit 1 with --fail-on-empty on empty repo, got {result.exit_code}.\n{result.output}"
    )
    assert "CI Gate Failure" in result.output or "No agent nodes found" in result.output, (
        "Expected a CI Gate Failure message, got:\n" + result.output
    )


def test_fail_on_empty_and_min_coverage_both_on_empty_repo(tmp_path: Path) -> None:
    """Both --fail-on-empty and --min-coverage on an empty repo should exit 1."""
    result = runner.invoke(
        app, ["audit", str(tmp_path), "--fail-on-empty", "--min-coverage", "80"]
    )
    assert result.exit_code == 1, result.output


def test_fail_on_empty_exits_zero_when_nodes_found() -> None:
    """--fail-on-empty must not trigger when agent nodes ARE found."""
    example_path = Path(__file__).parent.parent / "examples" / "langgraph-tools"
    if not example_path.exists():
        pytest.skip("langgraph-tools example not present")
    result = runner.invoke(app, ["audit", str(example_path), "--fail-on-empty"])
    # Should not fail with the empty-nodes failure message
    assert "No agent nodes found" not in result.output, (
        f"--fail-on-empty incorrectly triggered on non-empty repo.\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 4. Version fallback is "unknown", not a hardcoded version string
# ---------------------------------------------------------------------------


def test_version_fallback_is_not_hardcoded() -> None:
    """The version fallback in __init__.py must be 'unknown', not a stale hardcoded string.

    This test inspects the source to verify the fallback literal — the runtime
    __version__ is legitimately a real version string when the package is installed.
    """
    import importlib.util

    spec = importlib.util.find_spec("cz")
    assert spec is not None
    init_path = Path(spec.origin)  # type: ignore[arg-type]
    source = init_path.read_text(encoding="utf-8")

    # The except-branch fallback must say "unknown", not a hardcoded version
    assert '__version__ = "unknown"' in source, (
        f"Version fallback in {init_path} is not 'unknown'. "
        "It must be 'unknown' so stale hardcoded strings can't drift."
    )
    assert '__version__ = "0.3.2"' not in source, (
        "Hardcoded fallback '0.3.2' found in __init__.py — must be 'unknown'."
    )
    assert '__version__ = "0.3.1"' not in source, (
        "Hardcoded fallback '0.3.1' found in __init__.py — must be 'unknown'."
    )
