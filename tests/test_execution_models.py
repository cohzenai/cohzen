"""Tests for execution, span, and event data models."""

from datetime import datetime, timezone
import pytest

from cz.execution.models import Event, Execution, Span, generate_short_id


def test_generate_short_id():
    id1 = generate_short_id()
    id2 = generate_short_id()
    assert len(id1) == 8
    assert len(id2) == 8
    assert id1 != id2


def test_execution_model_defaults():
    ex = Execution(graph_id="customer_flow")
    assert ex.id is not None
    assert ex.graph_id == "customer_flow"
    assert ex.manifest_version == "0.1.0"
    assert ex.status == "running"
    assert ex.started_at is not None
    assert ex.ended_at is None
    assert ex.duration_ms is None
    assert ex.metadata == {}


def test_span_model_kinds_and_hierarchy():
    ex = Execution(graph_id="customer_flow")
    graph_span = Span(
        execution_id=ex.id,
        kind="graph",
        name="customer_flow",
    )
    node_span = Span(
        execution_id=ex.id,
        parent_id=graph_span.id,
        entity_id="node.planner",
        kind="node",
        name="planner",
    )
    llm_span = Span(
        execution_id=ex.id,
        parent_id=node_span.id,
        entity_id="model.openai.gpt-4o",
        kind="llm",
        name="llm:gpt-4o",
    )
    tool_span = Span(
        execution_id=ex.id,
        parent_id=node_span.id,
        entity_id="tool.search",
        kind="tool",
        name="search",
    )

    assert node_span.parent_id == graph_span.id
    assert llm_span.parent_id == node_span.id
    assert tool_span.parent_id == node_span.id
    assert llm_span.kind == "llm"
    assert tool_span.kind == "tool"


def test_event_model():
    ev = Event(
        execution_id="exec_1",
        span_id="span_1",
        kind="tool_call",
        data={"args": {"query": "test"}},
    )
    assert ev.id is not None
    assert ev.kind == "tool_call"
    assert ev.data["args"]["query"] == "test"
