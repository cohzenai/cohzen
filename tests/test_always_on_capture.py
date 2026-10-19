"""Tests for always-on capture redaction, payload bounds, and retention lifecycle."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from langgraph.graph import END, START, StateGraph

from cz.execution.instrumentation import install, uninstall
from cz.execution.models import Execution
from cz.execution.sqlite import SQLiteExecutionStore
from cz.project import load_config


@pytest.fixture
def project_fixture(tmp_path: Path):
    project = tmp_path / "app_project"
    cohzen_dir = project / ".cohzen"
    cohzen_dir.mkdir(parents=True)
    config_file = cohzen_dir / "config.toml"
    config_file.write_text(
        """enabled = true
capture_in_ci = true

[retention]
max_payload_bytes = 250
max_runs = 3
max_age_days = 7
""",
        encoding="utf-8",
    )
    return project


def test_always_on_redacts_secrets_in_all_persisted_tables(project_fixture: Path):
    db_path = project_fixture / ".cohzen" / "executions.db"
    install(project=project_fixture)

    builder = StateGraph(dict)

    def sensitive_step(state: dict) -> dict:
        return {
            "token": "secret_token_12345",
            "email": "user@example.com",
            "auth": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz",
            "openai": "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "public_info": "safe to store",
        }

    builder.add_node("process_sensitive", sensitive_step)
    builder.add_edge(START, "process_sensitive")
    builder.add_edge("process_sensitive", END)
    graph = builder.compile()

    secret_input = {
        "password": "mypassword123",
        "aws_key": "AKIAIOSFODNN7EXAMPLE",
        "phone": "+1 415-555-0123",
    }

    try:
        # App run receives pristine results
        result = graph.invoke(secret_input)
        assert result["token"] == "secret_token_12345"
        assert result["public_info"] == "safe to store"
    finally:
        from cz.execution.context import get_current_store

        store = get_current_store()
        if hasattr(store, "flush"):
            store.flush(2.0)
        uninstall()

    # Verify SQLite database does not contain raw secrets anywhere
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT * FROM executions").fetchall()
    spans = conn.execute("SELECT * FROM spans").fetchall()
    all_dump = " ".join(str(val) for r in (rows + spans) for val in r)
    conn.close()

    assert "mypassword123" not in all_dump
    assert "AKIAIOSFODNN7EXAMPLE" not in all_dump
    assert "user@example.com" not in all_dump
    assert "sk-proj-" not in all_dump
    assert "Bearer ey" not in all_dump
    assert "[REDACTED]" in all_dump
    assert "safe to store" in all_dump


def test_always_on_truncates_payloads_exceeding_max_payload_bytes(project_fixture: Path):
    db_path = project_fixture / ".cohzen" / "executions.db"
    install(project=project_fixture)

    builder = StateGraph(dict)
    builder.add_node("large_step", lambda state: {"huge": "A" * 1000})
    builder.add_edge(START, "large_step")
    builder.add_edge("large_step", END)
    graph = builder.compile()

    try:
        graph.invoke({"data": "B" * 1000})
    finally:
        from cz.execution.context import get_current_store

        store = get_current_store()
        if hasattr(store, "flush"):
            store.flush(2.0)
        uninstall()

    persisted = SQLiteExecutionStore(db_path)
    runs = persisted.list_executions()
    assert len(runs) >= 1
    spans = persisted.get_spans(runs[0].id)
    node_span = next(s for s in spans if s.name == "large_step")
    # Payload was truncated because max_payload_bytes = 250 in config.toml
    assert node_span.output.get("_cohzen_truncated") is True or "[TRUNCATED:" in str(node_span.output)


def test_always_on_retention_enforcement(project_fixture: Path):
    config = load_config(project_fixture)
    assert config["max_runs"] == 3
    assert config["max_age_days"] == 7

    db_path = project_fixture / ".cohzen" / "executions.db"
    store = SQLiteExecutionStore(
        db_path,
        retention=SQLiteExecutionStore(db_path).retention.__class__(
            max_runs=3,
            max_age_days=7,
            max_payload_bytes=250,
        ),
    )

    now = datetime.now(timezone.utc)
    # Add an expired run (older than 7 days)
    store.create_execution(Execution(id="expired", graph_id="flow", started_at=now - timedelta(days=10)))
    # Add 4 active runs (max_runs is 3)
    store.create_execution(Execution(id="run1", graph_id="flow", started_at=now - timedelta(days=3)))
    store.create_execution(Execution(id="run2", graph_id="flow", started_at=now - timedelta(days=2)))
    store.create_execution(Execution(id="run3", graph_id="flow", started_at=now - timedelta(days=1)))
    store.create_execution(Execution(id="run4", graph_id="flow", started_at=now))

    remaining_ids = [run.id for run in store.list_executions()]
    # "expired" was purged due to max_age_days, and "run1" was purged due to max_runs=3
    assert remaining_ids == ["run4", "run3", "run2"]
