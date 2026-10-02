"""Tests for cz telemetry serialization utilities."""

from datetime import datetime, timezone
from pydantic import BaseModel

from cz.execution.serializer import extract_llm_generation, serialize_for_storage


class SampleState(BaseModel):
    query: str
    count: int = 1


class MockMessage:
    def __init__(self, content, msg_type="human", tool_calls=None):
        self.content = content
        self.type = msg_type
        self.tool_calls = tool_calls
        self.additional_kwargs = {}


class MockGeneration:
    def __init__(self, text, message=None):
        self.text = text
        self.message = message


class MockLLMResult:
    def __init__(self, generations, token_usage=None):
        self.generations = generations
        self.llm_output = {"token_usage": token_usage} if token_usage else {}


def test_serialize_primitives_and_datetimes():
    assert serialize_for_storage(42) == 42
    assert serialize_for_storage("test") == "test"
    assert serialize_for_storage(True) is True
    assert serialize_for_storage(None) is None

    dt = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    assert serialize_for_storage(dt) == dt.isoformat()


def test_serialize_pydantic_and_dicts():
    state = SampleState(query="What is LangGraph?", count=3)
    serialized = serialize_for_storage(state)
    assert isinstance(serialized, dict)
    assert serialized["query"] == "What is LangGraph?"
    assert serialized["count"] == 3


def test_serialize_langchain_message():
    msg = MockMessage(content="Hello AI", msg_type="human")
    res = serialize_for_storage(msg)
    assert isinstance(res, dict)
    assert res["role"] == "user"
    assert res["content"] == "Hello AI"


def test_extract_llm_generation():
    ai_msg = MockMessage(
        content="Searching docs",
        msg_type="ai",
        tool_calls=[{"name": "search", "args": {"q": "langgraph"}, "id": "call_1"}],
    )
    gen = MockGeneration(text="", message=ai_msg)
    llm_result = MockLLMResult(
        generations=[[gen]],
        token_usage={"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
    )

    data = extract_llm_generation(llm_result)
    assert data["token_usage"]["total_tokens"] == 23
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["name"] == "search"
    assert data["text"] == "Searching docs"
