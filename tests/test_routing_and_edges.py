"""Tests for graph topology: direct edges, conditional branches, entry/finish points, and chained calls."""

from pathlib import Path
import pytest

from cz.scanner import scan_python_file


def test_edges_and_entry_finish_points(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(dict)
workflow.add_node("agent_a", lambda s: s)
workflow.add_node("agent_b", lambda s: s)

# Direct edge with START sentinel
workflow.add_edge(START, "agent_a")

# Direct edge between nodes
workflow.add_edge("agent_a", "agent_b")

# Direct edge with END sentinel
workflow.add_edge("agent_b", END)

# Alternative entry & finish points
alt_flow = StateGraph(dict)
alt_flow.add_node("worker", lambda s: s)
alt_flow.set_entry_point("worker")
alt_flow.set_finish_point("worker")
"""
    file_path = tmp_path / "edges.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0
    assert len(res.graphs) == 2

    graph_map = {g.graph_var: g for g in res.graphs}

    # workflow edges
    wf = graph_map["workflow"]
    edge_pairs = [(e.source, e.target, e.edge_type) for e in wf.edges]
    assert ("START", "agent_a", "direct") in edge_pairs
    assert ("agent_a", "agent_b", "direct") in edge_pairs
    assert ("agent_b", "END", "direct") in edge_pairs

    # alt_flow entry and finish
    alt = graph_map["alt_flow"]
    alt_pairs = [(e.source, e.target, e.edge_type) for e in alt.edges]
    assert ("START", "worker", "entry_point") in alt_pairs
    assert ("worker", "END", "finish_point") in alt_pairs


def test_conditional_edges_dict_and_list_mapping(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph, END

builder = StateGraph(dict)
builder.add_node("router_node", lambda s: s)
builder.add_node("branch_1", lambda s: s)
builder.add_node("branch_2", lambda s: s)

def route_decision(state): return "next"

# 1. Dict mapping
builder.add_conditional_edges(
    "router_node",
    route_decision,
    {
        "opt1": "branch_1",
        "opt2": "branch_2",
        "stop": END,
    }
)

# 2. List mapping
builder.add_conditional_edges(
    "branch_1",
    route_decision,
    ["branch_2", END]
)
"""
    file_path = tmp_path / "conditional_edges.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0

    builder = res.graphs[0]
    cond_edges = [e for e in builder.edges if e.edge_type == "conditional"]
    assert len(cond_edges) == 2

    # First conditional edge (dict)
    edge1 = cond_edges[0]
    assert edge1.source == "router_node"
    assert edge1.condition_fn == "route_decision"
    assert edge1.conditional_mapping == {
        "opt1": "branch_1",
        "opt2": "branch_2",
        "stop": "END",
    }

    # Second conditional edge (list)
    edge2 = cond_edges[1]
    assert edge2.source == "branch_1"
    assert edge2.conditional_mapping == {
        "branch_2": "branch_2",
        "END": "END",
    }
