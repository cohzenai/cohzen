"""Tests for SQLiteExecutionStore persistence, queries, and constraints."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import pytest

from cz.execution.models import Event, Execution, Span
from cz.execution.processor import RedactionProcessor
from cz.execution.sqlite import SQLiteExecutionStore


@pytest.fixture
def temp_store(tmp_path: Path):
    db_file = tmp_path / "executions.db"
    return SQLiteExecutionStore(db_path=db_file)


def test_sqlite_create_and_get_execution(temp_store: SQLiteExecutionStore):
    now = datetime.now(timezone.utc)
    ex = Execution(
        id="a82f91",
        graph_id="customer_flow",
        status="running",
        started_at=now,
        metadata={"env": "test"},
    )
    temp_store.create_execution(ex)

    fetched = temp_store.get_execution("a82f91")
    assert fetched is not None
    assert fetched.id == "a82f91"
    assert fetched.graph_id == "customer_flow"
    assert fetched.status == "running"
    assert fetched.metadata == {"env": "test"}


def test_sqlite_finish_execution(temp_store: SQLiteExecutionStore):
    now = datetime.now(timezone.utc)
    ex = Execution(id="91be22", graph_id="customer_flow", started_at=now)
    temp_store.create_execution(ex)

    ended = datetime.now(timezone.utc)
    temp_store.finish_execution(
        execution_id="91be22",
        status="completed",
        ended_at=ended,
        duration_ms=1870.0,
    )

    fetched = temp_store.get_execution("91be22")
    assert fetched is not None
    assert fetched.status == "completed"
    assert fetched.duration_ms == 1870.0
    assert fetched.ended_at is not None


def test_sqlite_spans_lifecycle(temp_store: SQLiteExecutionStore):
    ex = Execution(id="ex_1", graph_id="workflow")
    temp_store.create_execution(ex)

    now = datetime.now(timezone.utc)
    span1 = Span(
        id="sp_planner",
        execution_id="ex_1",
        entity_id="node.planner",
        kind="node",
        name="planner",
        input={"query": "hello"},
        started_at=now,
    )
    temp_store.create_span(span1)

    span2 = Span(
        id="sp_llm",
        execution_id="ex_1",
        parent_id="sp_planner",
        entity_id="model.openai.gpt-4o",
        kind="llm",
        name="llm:gpt-4o",
        started_at=now,
    )
    temp_store.create_span(span2)

    temp_store.finish_span(
        span_id="sp_llm",
        status="completed",
        ended_at=datetime.now(timezone.utc),
        duration_ms=810.0,
        output="Planned steps",
    )
    temp_store.finish_span(
        span_id="sp_planner",
        status="completed",
        ended_at=datetime.now(timezone.utc),
        duration_ms=420.0,
        output={"state": "ready"},
    )

    spans = temp_store.get_spans("ex_1")
    assert len(spans) == 2
    assert spans[0].id == "sp_planner"
    assert spans[0].output == {"state": "ready"}
    assert spans[1].parent_id == "sp_planner"
    assert spans[1].duration_ms == 810.0


def test_sqlite_prefix_id_search(temp_store: SQLiteExecutionStore):
    ex = Execution(id="a82f91bc34", graph_id="customer_flow")
    temp_store.create_execution(ex)

    # Search with prefix
    found = temp_store.get_execution("a82f91")
    assert found is not None
    assert found.id == "a82f91bc34"


def test_sqlite_list_executions_order(temp_store: SQLiteExecutionStore):
    t1 = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 27, 11, 0, 0, tzinfo=timezone.utc)

    temp_store.create_execution(Execution(id="ex_old", graph_id="flow", started_at=t1))
    temp_store.create_execution(Execution(id="ex_new", graph_id="flow", started_at=t2))

    listed = temp_store.list_executions(limit=10)
    assert len(listed) == 2
    assert listed[0].id == "ex_new"
    assert listed[1].id == "ex_old"


def test_sqlite_redaction_integration(tmp_path: Path):
    db_file = tmp_path / "executions_redacted.db"
    store = SQLiteExecutionStore(db_path=db_file, processor=RedactionProcessor())

    ex = Execution(
        id="ex_secret",
        graph_id="flow",
        metadata={"api_key": "sk-12345678901234567890", "user": "test"},
    )
    store.create_execution(ex)

    span = Span(
        id="sp_secret",
        execution_id="ex_secret",
        kind="llm",
        name="llm:gpt-4o",
        input={"token": "bearer xyz", "prompt": "Hi"},
    )
    store.create_span(span)

    fetched_ex = store.get_execution("ex_secret")
    assert fetched_ex.metadata["api_key"] == "[REDACTED]"
    assert fetched_ex.metadata["user"] == "test"

    fetched_spans = store.get_spans("ex_secret")
    assert fetched_spans[0].input["token"] == "[REDACTED]"
    assert fetched_spans[0].input["prompt"] == "Hi"
