"""Tests for repository traversal engine, ignore patterns, syntax error handling, and cross-referencing."""

from pathlib import Path
import pytest

from cz.scanner.engine import scan_repository


def test_engine_directory_ignore_rules(tmp_path: Path):
    # Create standard source file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "graph.py").write_text("""
from langgraph.graph import StateGraph
builder = StateGraph(dict)
""")

    # Create ignored directories with python files that shouldn't be scanned
    for ignored_name in [".git", "node_modules", ".venv", "__pycache__", "build", "dist"]:
        ign_dir = tmp_path / ignored_name
        ign_dir.mkdir()
        (ign_dir / "ignored.py").write_text("""
from langgraph.graph import StateGraph
bad_builder = StateGraph(dict)
""")

    result = scan_repository(str(tmp_path))
    assert result.files_scanned == 1
    assert result.python_files_count == 1
    assert result.total_graphs == 1
    assert result.graphs[0].graph_var == "builder"


def test_engine_single_file_scan(tmp_path: Path):
    file_path = tmp_path / "single_file.py"
    file_path.write_text("""
from langgraph.graph import StateGraph
flow = StateGraph(dict)
flow.add_node("agent", lambda s: s)
""")

    result = scan_repository(str(file_path))
    assert result.files_scanned == 1
    assert result.python_files_count == 1
    assert result.total_graphs == 1
    assert result.graphs[0].graph_var == "flow"


def test_engine_nonexistent_path(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    result = scan_repository(str(non_existent))

    assert len(result.errors) == 1
    assert result.errors[0].error_type == "NotFound"
    assert result.total_graphs == 0


def test_engine_syntax_error_handling(tmp_path: Path):
    bad_file = tmp_path / "broken_syntax.py"
    bad_file.write_text("""
def incomplete_function(
    # Missing closing parenthesis and colon
""")

    result = scan_repository(str(tmp_path))
    assert len(result.errors) == 1
    assert result.errors[0].error_type == "SyntaxError"


def test_node_to_agent_cross_referencing(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

def my_agent_handler(state):
    \"\"\"Docstring for agent handler.\"\"\"
    return state

tools = ["search"]

wf = StateGraph(dict)
wf.add_node("agent_step", my_agent_handler)
wf.add_node("tool_step", ToolNode(tools))
"""
    file_path = tmp_path / "cross_ref.py"
    file_path.write_text(code)

    result = scan_repository(str(file_path))
    assert result.total_graphs == 1

    graph = result.graphs[0]
    node_map = {n.name: n for n in graph.nodes}

    # Verify agent_step was linked to my_agent_handler AgentDef
    agent_node = node_map["agent_step"]
    assert agent_node.agent_def is not None
    assert agent_node.agent_def.name == "my_agent_handler"
    assert "Docstring for agent handler." in agent_node.agent_def.docstring

    # Verify tool_step was linked to ToolNodeDef
    tool_node = node_map["tool_step"]
    assert tool_node.tool_node_def is not None
    assert tool_node.tool_node_def.tools == ["search"]
