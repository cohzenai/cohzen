"""Tests for CohzenCallbackHandler and instrumentation hooks."""

from pathlib import Path
import uuid
import pytest

from cz.execution.callbacks import CohzenCallbackHandler
from cz.execution.instrumentation import install, uninstall
from cz.execution.manifest_matcher import ManifestMatcher
from cz.execution.sqlite import SQLiteExecutionStore


@pytest.fixture
def temp_store(tmp_path: Path):
    return SQLiteExecutionStore(db_path=tmp_path / "cb_test.db")


def test_callback_handler_full_graph_flow(temp_store: SQLiteExecutionStore):
    matcher = ManifestMatcher()
    handler = CohzenCallbackHandler(store=temp_store, matcher=matcher, graph_id="customer_flow")

    graph_run_id = uuid.uuid4()
    node_run_id = uuid.uuid4()
    llm_run_id = uuid.uuid4()
    tool_run_id = uuid.uuid4()

    # 1. Graph starts
    handler.on_chain_start(
        serialized={"name": "customer_flow"},
        inputs={"customer_id": "cust_123"},
        run_id=graph_run_id,
        parent_run_id=None,
    )

    # 2. Node planner starts
    handler.on_chain_start(
        serialized=None,
        inputs={"customer_id": "cust_123"},
        run_id=node_run_id,
        parent_run_id=graph_run_id,
        metadata={"langgraph_node": "planner"},
    )

    # 3. LLM inside planner starts
    handler.on_chat_model_start(
        serialized={"name": "ChatOpenAI", "id": ["langchain", "chat_models", "openai", "ChatOpenAI"]},
        messages=[[{"role": "user", "content": "analyze"}]],
        run_id=llm_run_id,
        parent_run_id=node_run_id,
        invocation_params={"model": "gpt-4o"},
    )

    # 4. LLM ends
    class MockLLMResponse:
        llm_output = {"token_usage": {"total_tokens": 150}}
        generations = []

    handler.on_llm_end(
        response=MockLLMResponse(),
        run_id=llm_run_id,
        parent_run_id=node_run_id,
    )

    # 5. Tool search starts
    handler.on_tool_start(
        serialized={"name": "search"},
        input_str="account status",
        run_id=tool_run_id,
        parent_run_id=node_run_id,
    )

    # 6. Tool ends
    handler.on_tool_end(
        output="Active Premium Account",
        run_id=tool_run_id,
        parent_run_id=node_run_id,
    )

    # 7. Node planner ends
    handler.on_chain_end(
        outputs={"plan": "contact VIP support"},
        run_id=node_run_id,
        parent_run_id=graph_run_id,
    )

    # 8. Graph ends
    handler.on_chain_end(
        outputs={"final": "resolved"},
        run_id=graph_run_id,
        parent_run_id=None,
    )

    # Verify execution was created and finished
    executions = temp_store.list_executions()
    assert len(executions) == 1
    ex = executions[0]
    assert ex.graph_id == "customer_flow"
    assert ex.status == "completed"
    assert ex.duration_ms is not None

    # Verify spans hierarchy and kinds
    spans = temp_store.get_spans(ex.id)
    assert len(spans) == 4

    # Graph span
    graph_span = next(s for s in spans if s.kind == "graph")
    assert graph_span.name == "customer_flow"
    assert graph_span.status == "completed"

    # Node span
    node_span = next(s for s in spans if s.kind == "node")
    assert node_span.name == "planner"
    assert node_span.entity_id == "node.planner"
    assert node_span.parent_id == str(graph_run_id)

    # LLM span
    llm_span = next(s for s in spans if s.kind == "llm")
    assert llm_span.name == "llm:gpt-4o"
    assert llm_span.entity_id == "model.openai.gpt-4o"
    assert llm_span.parent_id == str(node_run_id)
    assert llm_span.metadata["token_usage"] == {"total_tokens": 150}

    # Tool span
    tool_span = next(s for s in spans if s.kind == "tool")
    assert tool_span.name == "search"
    assert tool_span.entity_id == "tool.search"
    assert tool_span.parent_id == str(node_run_id)
    assert tool_span.output == "Active Premium Account"


def test_install_and_uninstall_lifecycle(temp_store: SQLiteExecutionStore):
    install(store=temp_store)
    # Idempotent call
    install(store=temp_store)
    uninstall()
