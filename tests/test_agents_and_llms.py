"""Tests for agent definitions, async functions, docstrings, LLM calls, prompts, and tracing."""

from pathlib import Path
import pytest

from cz.scanner import scan_python_file


def test_agent_sync_async_and_docstrings(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph
from langsmith import traceable

# 1. Sync agent with docstring and tracing
@traceable
def sync_agent(state):
    \"\"\"Sync agent documentation text.\"\"\"
    return {"result": 1}

# 2. Async agent with docstring and observe
def observe(fn): return fn

@observe
async def async_agent(state):
    \"\"\"Asynchronous worker agent.\"\"\"
    return {"result": 2}

workflow = StateGraph(dict)
workflow.add_node("sync", sync_agent)
workflow.add_node("async", async_agent)
"""
    file_path = tmp_path / "agents.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0

    agent_map = {a.name: a for a in res.agent_defs}
    assert "sync_agent" in agent_map
    assert "async_agent" in agent_map

    sync_a = agent_map["sync_agent"]
    assert sync_a.is_async is False
    assert "Sync agent documentation text." in sync_a.docstring
    assert sync_a.is_instrumented is True
    assert "traceable" in sync_a.telemetry_decorators
    assert sync_a.line_start < sync_a.line_end

    async_a = agent_map["async_agent"]
    assert async_a.is_async is True
    assert "Asynchronous worker agent." in async_a.docstring
    assert async_a.is_instrumented is True
    assert "observe" in async_a.telemetry_decorators


def test_llm_calls_and_prompts_detection(tmp_path: Path):
    code = """
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.graph import StateGraph

my_chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant.")
])

simple_prompt = PromptTemplate.from_template("Hello {name}")

def agent_with_calls(state):
    # 1. invoke
    res1 = model.invoke(state["messages"])
    # 2. stream
    res2 = llm.stream("test prompt")
    return {"out": res1}

async def agent_with_openai(state):
    # 3. ainvoke
    res = await model.ainvoke(state["messages"])
    # 4. client.chat.completions.create
    direct = client.chat.completions.create(model="gpt-4o", messages=[])
    return {"out": res}

wf = StateGraph(dict)
wf.add_node("worker1", agent_with_calls)
wf.add_node("worker2", agent_with_openai)
"""
    file_path = tmp_path / "llm_agent.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0

    # Check prompts
    prompt_map = {p.var_name: p for p in res.prompts}
    assert "my_chat_prompt" in prompt_map
    assert prompt_map["my_chat_prompt"].template_type == "ChatPromptTemplate"
    assert "simple_prompt" in prompt_map
    assert prompt_map["simple_prompt"].template_type == "PromptTemplate"

    # Check LLM calls
    agent_map = {a.name: a for a in res.agent_defs}
    worker1 = agent_map["agent_with_calls"]
    assert len(worker1.llm_calls) == 2
    assert worker1.llm_calls[0].caller_var == "model"
    assert worker1.llm_calls[0].method == "invoke"
    assert worker1.llm_calls[1].caller_var == "llm"
    assert worker1.llm_calls[1].method == "stream"

    worker2 = agent_map["agent_with_openai"]
    assert len(worker2.llm_calls) == 2
    methods = {c.method: c.caller_var for c in worker2.llm_calls}
    assert methods["ainvoke"] == "model"
    assert methods["create"] == "client.chat.completions"
