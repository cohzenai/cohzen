"""Tests for tool definitions, tool binding, and ToolNode instances."""

from pathlib import Path
import pytest

from cz.scanner import scan_python_file


def test_tool_definitions_and_line_ranges(tmp_path: Path):
    code = """
from langchain_core.tools import tool
from langsmith import traceable

@tool
def get_weather(city: str) -> str:
    \"\"\"Get current weather for a city.\"\"\"
    return "Sunny"

@tool
@traceable
def execute_sql(query: str) -> str:
    \"\"\"Execute SQL query in readonly mode.\"\"\"
    return "Query result"

def helper_fn():
    return 42
"""
    file_path = tmp_path / "tools.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0
    assert len(res.tool_defs) == 2

    tool_map = {t.name: t for t in res.tool_defs}
    assert "get_weather" in tool_map
    assert "execute_sql" in tool_map

    weather = tool_map["get_weather"]
    assert "Get current weather" in weather.docstring
    assert weather.has_tool_decorator is True
    assert weather.is_instrumented is False
    assert weather.line_start < weather.line_end

    sql = tool_map["execute_sql"]
    assert "Execute SQL" in sql.docstring
    assert sql.is_instrumented is True
    assert "traceable" in sql.telemetry_decorators


def test_tool_binding_and_toolnode_resolution(tmp_path: Path):
    code = """
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

# List variable
available_tools = ["calculator", "search"]

# 1. Standalone ToolNode with variable resolution
node1 = ToolNode(available_tools)

# 2. Standalone ToolNode with literal list
node2 = ToolNode(["rag_retriever", "web_fetch"])

# 3. bind_tools
bound_llm = model.bind_tools(available_tools)

# 4. Inline ToolNode in add_node
builder = StateGraph(dict)
builder.add_node("tools_step", ToolNode(available_tools))
"""
    file_path = tmp_path / "tool_nodes.py"
    file_path.write_text(code)

    res = scan_python_file(str(file_path))
    assert len(res.errors) == 0

    tool_node_map = {tn.var_name: tn for tn in res.tool_nodes}
    assert "node1" in tool_node_map
    assert tool_node_map["node1"].tools == ["calculator", "search"]

    assert "node2" in tool_node_map
    assert tool_node_map["node2"].tools == ["rag_retriever", "web_fetch"]

    assert "tools_step" in tool_node_map
    assert tool_node_map["tools_step"].tools == ["calculator", "search"]

    # Check bind_tools
    bound_map = {b.model_var: b for b in res.tools_bound}
    assert "model" in bound_map
    assert bound_map["model"].tools == ["calculator", "search"]
