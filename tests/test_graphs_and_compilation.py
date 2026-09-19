"""Tests for LangGraph class detection, state schemas, and compilation configurations."""

import ast
from pathlib import Path
import pytest

from cz.scanner import scan_python_file


def test_graph_classes_and_schemas(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph, Graph, MessageGraph
from typing import TypedDict

class MyState(TypedDict):
    val: int

# 1. StateGraph with positional arg
sg1 = StateGraph(MyState)

# 2. StateGraph with keyword arg
sg2 = StateGraph(state_schema=MyState)

# 3. Graph
g = Graph()

# 4. MessageGraph
mg = MessageGraph()
"""
    file_path = tmp_path / "graphs.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0
    assert len(res.graphs) == 4

    graph_map = {g.graph_var: g for g in res.graphs}
    assert graph_map["sg1"].graph_class == "StateGraph"
    assert graph_map["sg1"].state_schema == "MyState"
    assert graph_map["sg1"].is_compiled is False

    assert graph_map["sg2"].graph_class == "StateGraph"
    assert graph_map["sg2"].state_schema == "MyState"

    assert graph_map["g"].graph_class == "Graph"
    assert graph_map["mg"].graph_class == "MessageGraph"


def test_compilation_call_patterns(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(dict)
builder.add_node("step", lambda x: x)

# Assigned compilation with checkpointer and interrupts
app = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["step"],
    interrupt_after=["step"],
    store="my_store"
)

# Return compilation
def get_graph():
    wf = StateGraph(dict)
    return wf.compile()
"""
    file_path = tmp_path / "compilations.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0
    assert len(res.graphs) == 2

    graph_map = {g.graph_var: g for g in res.graphs}

    # builder compilation
    builder = graph_map["builder"]
    assert builder.is_compiled is True
    assert builder.compile_info is not None
    assert builder.compile_info.compiled_var == "app"
    assert "MemorySaver" in builder.compile_info.checkpointer
    assert builder.compile_info.interrupt_before == ["step"]
    assert builder.compile_info.interrupt_after == ["step"]
    assert builder.compile_info.store == "my_store"

    # wf compilation
    wf = graph_map["wf"]
    assert wf.is_compiled is True
    assert wf.compile_info is not None
    assert wf.compile_info.compiled_var == "<return>"


def test_unresolved_external_node_handler(tmp_path: Path):
    from cz.scanner.engine import scan_repository

    code = """
from langgraph.graph import StateGraph
from external_module import imported_agent_fn

builder = StateGraph(dict)
builder.add_node("external_node", imported_agent_fn)
app = builder.compile()
"""
    file_path = tmp_path / "imported_graph.py"
    file_path.write_text(code)

    res = scan_repository(str(tmp_path))
    manifest = res.to_manifest()

    assert len(manifest.graphs) == 1
    assert len(manifest.nodes) == 1

    node = manifest.nodes[0]
    assert node.id == "external_node"
    assert node.handler == "imported_agent_fn"
    assert node.resolution.status == "unresolved"
    assert node.resolution.reason == "external_import"
