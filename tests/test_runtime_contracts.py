"""Contract tests for LangGraph compiled graph execution interception."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")
from langchain_core.callbacks import BaseCallbackHandler, CallbackManager
from langgraph.graph import END, START, StateGraph

from cz.execution.instrumentation import install, uninstall
from cz.execution.sqlite import SQLiteExecutionStore
from cz.execution.writer import AsyncExecutionStore


class TrackingCallbackHandler(BaseCallbackHandler):
    """User-supplied callback handler to verify non-interference and inheritance."""

    def __init__(self) -> None:
        super().__init__()
        self.starts: list[str] = []
        self.ends: list[str] = []

    def on_chain_start(self, serialized: dict[str, Any] | None, inputs: dict[str, Any], **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or "chain"
        self.starts.append(name)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        self.ends.append("end")


@pytest.fixture
def test_graph():
    builder = StateGraph(dict)
    builder.add_node("step_a", lambda state: {"val": state.get("val", 0) + 1})
    builder.add_node("step_b", lambda state: {"val": state.get("val", 0) * 2})
    builder.add_edge(START, "step_a")
    builder.add_edge("step_a", "step_b")
    builder.add_edge("step_b", END)
    return builder.compile()


@pytest.fixture
def runtime_store(tmp_path: Path):
    db_path = tmp_path / "contracts.db"
    store = AsyncExecutionStore(SQLiteExecutionStore(db_path))
    install(store=store)
    yield store
    uninstall()
    store.flush(2.0)


def test_callback_manager_preservation_and_non_mutation(runtime_store: AsyncExecutionStore, test_graph):
    user_handler = TrackingCallbackHandler()
    manager = CallbackManager([user_handler])
    initial_handler_count = len(manager.handlers)
    user_config = {"callbacks": manager, "configurable": {"user_flag": True}}

    result = test_graph.invoke({"val": 5}, user_config)

    assert result == {"val": 12}
    # Original user CallbackManager must not be mutated in-place
    assert len(manager.handlers) == initial_handler_count
    assert manager.handlers[0] is user_handler
    # User handler received lifecycle events
    assert len(user_handler.starts) > 0
    assert len(user_handler.ends) > 0

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    assert len(runs) == 1
    assert runs[0].status == "completed"


def test_positional_config_support_and_config_non_mutation(runtime_store: AsyncExecutionStore, test_graph):
    user_config = {"tags": ["tag_pos"], "configurable": {"k": "v"}}
    config_copy = dict(user_config)

    # 1. invoke with positional config
    res_sync = test_graph.invoke({"val": 3}, user_config)
    assert res_sync == {"val": 8}
    assert user_config == config_copy  # original dict not polluted with callbacks

    # 2. ainvoke with positional config
    res_async = asyncio.run(test_graph.ainvoke({"val": 3}, user_config))
    assert res_async == {"val": 8}
    assert user_config == config_copy

    # 3. stream with positional config
    chunks = list(test_graph.stream({"val": 3}, user_config))
    assert len(chunks) == 2
    assert user_config == config_copy

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    assert len(runs) == 3
    for run in runs:
        assert run.status == "completed"


def test_stream_cancellation_marks_execution_cancelled(runtime_store: AsyncExecutionStore, test_graph):
    # Synchronous stream cancellation
    stream = test_graph.stream({"val": 10})
    first_chunk = next(stream)
    assert first_chunk == {"step_a": {"val": 11}}
    stream.close()

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    assert len(runs) == 1
    assert runs[0].status == "cancelled"
    assert runs[0].error == "Stream cancelled by caller"


def test_async_stream_cancellation_marks_execution_cancelled(runtime_store: AsyncExecutionStore, test_graph):
    async def cancel_astream():
        astream = test_graph.astream({"val": 20})
        async for chunk in astream:
            assert chunk == {"step_a": {"val": 21}}
            break  # triggers GeneratorExit / aclose

    asyncio.run(cancel_astream())

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    assert len(runs) == 1
    assert runs[0].status == "cancelled"
    assert runs[0].error == "Stream cancelled by caller"


def test_nested_graph_execution_creates_single_root_execution(runtime_store: AsyncExecutionStore):
    # Child graph
    child_builder = StateGraph(dict)
    child_builder.add_node("child_step", lambda state: {"val": state.get("val", 0) + 10})
    child_builder.add_edge(START, "child_step")
    child_builder.add_edge("child_step", END)
    child_graph = child_builder.compile()

    # Parent graph invokes child graph
    parent_builder = StateGraph(dict)

    def call_child(state: dict) -> dict:
        return child_graph.invoke(state)

    parent_builder.add_node("parent_step", call_child)
    parent_builder.add_edge(START, "parent_step")
    parent_builder.add_edge("parent_step", END)
    parent_graph = parent_builder.compile()

    result = parent_graph.invoke({"val": 5})
    assert result == {"val": 15}

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    # Exactly one top-level execution recorded
    assert len(runs) == 1
    assert runs[0].status == "completed"
    spans = runtime_store.get_spans(runs[0].id)
    span_names = [s.name for s in spans]
    assert "parent_step" in span_names
    assert "child_step" in span_names


def test_thread_safety_with_concurrent_invocations(runtime_store: AsyncExecutionStore, test_graph):
    thread_count = 8

    def invoke_worker(num: int) -> dict:
        return test_graph.invoke({"val": num})

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(invoke_worker, range(thread_count)))

    assert len(results) == thread_count
    for num, res in enumerate(results):
        assert res == {"val": (num + 1) * 2}

    assert runtime_store.flush(3.0)
    runs = runtime_store.list_executions()
    assert len(runs) == thread_count
    for run in runs:
        assert run.status == "completed"


def test_exception_propagation_and_failure_recording(runtime_store: AsyncExecutionStore):
    builder = StateGraph(dict)

    def failing_step(state: dict) -> dict:
        raise ValueError("simulated step crash")

    builder.add_node("bad_node", failing_step)
    builder.add_edge(START, "bad_node")
    builder.add_edge("bad_node", END)
    graph = builder.compile()

    with pytest.raises(ValueError, match="simulated step crash"):
        graph.invoke({"val": 1})

    assert runtime_store.flush(2.0)
    runs = runtime_store.list_executions()
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert "ValueError: simulated step crash" in (runs[0].error or "")


def test_byte_identical_results_with_and_without_cohzen(tmp_path: Path, test_graph):
    sample_input = {"val": 42, "text": "hello", "nested": {"list": [1, 2, 3]}}

    # Run without Cohzen
    uninstall()
    plain_sync = test_graph.invoke(sample_input)
    plain_async = asyncio.run(test_graph.ainvoke(sample_input))
    plain_stream = list(test_graph.stream(sample_input))

    # Run with Cohzen installed
    store = AsyncExecutionStore(SQLiteExecutionStore(tmp_path / "ident.db"))
    install(store=store)
    try:
        cz_sync = test_graph.invoke(sample_input)
        cz_async = asyncio.run(test_graph.ainvoke(sample_input))
        cz_stream = list(test_graph.stream(sample_input))
    finally:
        uninstall()

    assert cz_sync == plain_sync
    assert cz_async == plain_async
    assert cz_stream == plain_stream


def test_runtime_capture_overhead_is_minimal(tmp_path: Path, test_graph):
    iterations = 20
    sample = {"val": 1}

    # Baseline without Cohzen
    uninstall()
    t0 = time.perf_counter()
    for _ in range(iterations):
        test_graph.invoke(sample)
    baseline_time = time.perf_counter() - t0

    # With Cohzen AsyncExecutionStore
    store = AsyncExecutionStore(SQLiteExecutionStore(tmp_path / "perf.db"))
    install(store=store)
    try:
        t1 = time.perf_counter()
        for _ in range(iterations):
            test_graph.invoke(sample)
        instrumented_time = time.perf_counter() - t1
    finally:
        uninstall()
        store.flush(2.0)

    # Average overhead per invocation should be well under 15ms
    per_call_overhead_ms = ((instrumented_time - baseline_time) / iterations) * 1000.0
    assert per_call_overhead_ms < 15.0
