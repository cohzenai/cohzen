"""Tests for execution context, span hierarchy, and @observe decorator."""

import asyncio
from pathlib import Path
import pytest

from cz.execution.context import (
    execution_scope,
    get_current_execution,
    get_current_span,
    observe,
    set_global_store,
    span_scope,
)
from cz.execution.sqlite import SQLiteExecutionStore


@pytest.fixture
def clean_store(tmp_path: Path):
    store = SQLiteExecutionStore(db_path=tmp_path / "test_exec.db")
    set_global_store(store)
    return store


def test_execution_and_nested_span_scopes(clean_store: SQLiteExecutionStore):
    with execution_scope(graph_id="customer_flow") as ex:
        assert get_current_execution().id == ex.id
        assert get_current_span() is None

        with span_scope(name="planner", kind="node", entity_id="node.planner") as node_span:
            assert get_current_span().id == node_span.id
            assert node_span.execution_id == ex.id
            assert node_span.parent_id is None

            with span_scope(name="llm:gpt-4o", kind="llm", entity_id="model.openai.gpt-4o") as llm_span:
                assert get_current_span().id == llm_span.id
                assert llm_span.execution_id == ex.id
                assert llm_span.parent_id == node_span.id

            assert get_current_span().id == node_span.id

        assert get_current_span() is None

    assert get_current_execution() is None

    # Check persistence
    saved_ex = clean_store.get_execution(ex.id)
    assert saved_ex.status == "completed"
    assert saved_ex.duration_ms is not None

    spans = clean_store.get_spans(ex.id)
    assert len(spans) == 2
    assert spans[0].name == "planner"
    assert spans[0].kind == "node"
    assert spans[1].name == "llm:gpt-4o"
    assert spans[1].kind == "llm"
    assert spans[1].parent_id == spans[0].id


def test_execution_scope_failure_handling(clean_store: SQLiteExecutionStore):
    with pytest.raises(ValueError, match="Graph failed"):
        with execution_scope(graph_id="failing_flow") as ex:
            exec_id = ex.id
            raise ValueError("Graph failed")

    saved_ex = clean_store.get_execution(exec_id)
    assert saved_ex.status == "failed"
    assert "ValueError: Graph failed" in saved_ex.error


def test_span_scope_failure_handling(clean_store: SQLiteExecutionStore):
    with execution_scope(graph_id="flow") as ex:
        with pytest.raises(RuntimeError, match="Node error"):
            with span_scope(name="broken_node", kind="node"):
                raise RuntimeError("Node error")

    spans = clean_store.get_spans(ex.id)
    assert len(spans) == 1
    assert spans[0].status == "failed"
    assert "RuntimeError: Node error" in spans[0].error


def test_observe_decorator_sync(clean_store: SQLiteExecutionStore):
    @observe(name="custom_calculator", kind="node", entity_id="node.calculator")
    def calculate(a: int, b: int) -> int:
        return a + b

    with execution_scope(graph_id="calc_flow") as ex:
        res = calculate(10, 20)
        assert res == 30

    spans = clean_store.get_spans(ex.id)
    assert len(spans) == 1
    assert spans[0].name == "custom_calculator"
    assert spans[0].output == 30
    assert spans[0].entity_id == "node.calculator"


def test_observe_decorator_async(clean_store: SQLiteExecutionStore):
    @observe(name="async_fetcher", kind="tool", entity_id="tool.fetch")
    async def fetch_data(key: str) -> str:
        await asyncio.sleep(0.01)
        return f"result_{key}"

    async def main_flow():
        with execution_scope(graph_id="async_flow") as ex:
            res = await fetch_data("user123")
            assert res == "result_user123"
            return ex.id

    exec_id = asyncio.run(main_flow())

    spans = clean_store.get_spans(exec_id)
    assert len(spans) == 1
    assert spans[0].name == "async_fetcher"
    assert spans[0].kind == "tool"
    assert spans[0].output == "result_user123"


def test_record_reason_and_observe_reasoning(clean_store: SQLiteExecutionStore):
    from cz.execution.context import record_reason

    @observe(name="tool_lookup", kind="tool", reason=lambda q: f"Querying knowledge base for {q}")
    def lookup(q: str) -> str:
        return f"answer for {q}"

    with execution_scope(graph_id="reason_flow", reason="User asked about refund policy") as ex:
        with span_scope(name="planner_node", kind="node") as s:
            record_reason("Classified query as billing dispute requiring escalation")
            res = lookup("refund status")

    saved_ex = clean_store.get_execution(ex.id)
    assert saved_ex.reason == "User asked about refund policy"

    spans = clean_store.get_spans(ex.id)
    assert len(spans) == 2
    planner_span = next(s for s in spans if s.name == "planner_node")
    assert planner_span.reason == "Classified query as billing dispute requiring escalation"

    tool_span = next(s for s in spans if s.name == "tool_lookup")
    assert tool_span.reason == "Querying knowledge base for refund status"
