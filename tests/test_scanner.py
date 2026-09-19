"""Unit tests for the cz LangGraph architecture and observability scanner."""

from pathlib import Path
import pytest

from cz.scanner.engine import scan_repository
from cz.scanner import scan_python_file
from cz.formatters.json_fmt import format_json
from cz.formatters.mermaid import format_mermaid

SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_graphs"


def test_scan_simple_graph():
    file_path = str(SAMPLE_DIR / "simple_graph.py")
    res = scan_python_file(file_path)

    assert len(res.errors) == 0
    assert len(res.graphs) == 1

    graph = res.graphs[0]
    assert graph.graph_var == "workflow"
    assert graph.graph_class == "StateGraph"
    assert graph.state_schema == "AgentState"
    assert graph.is_compiled is True

    # Check compile info
    assert graph.compile_info is not None
    assert graph.compile_info.compiled_var == "app"
    assert graph.compile_info.checkpointer == "checkpointer"

    # Check nodes
    node_names = [n.name for n in graph.nodes]
    assert "agent" in node_names
    assert "tools" in node_names
    assert len(graph.nodes) == 2

    # Check edges
    edge_pairs = [(e.source, e.target) for e in graph.edges]
    assert ("START", "agent") in edge_pairs
    assert ("tools", "agent") in edge_pairs
    assert ("agent", "END") in edge_pairs


def test_scan_multi_agent_router():
    file_path = str(SAMPLE_DIR / "multi_agent_router.py")
    res = scan_python_file(file_path)

    assert len(res.errors) == 0
    assert len(res.graphs) == 1

    graph = res.graphs[0]
    assert graph.graph_var == "builder"
    assert graph.state_schema == "RouterState"
    assert graph.is_compiled is True

    # Check compile info
    assert graph.compile_info is not None
    assert graph.compile_info.compiled_var == "compiled_system"
    assert graph.compile_info.interrupt_before == ["reviewer"]

    # Check agents
    agent_names = graph.agent_names
    assert set(agent_names) == {"supervisor", "researcher", "coder", "reviewer"}

    # Check conditional edge
    conditional_edges = [e for e in graph.edges if e.edge_type == "conditional"]
    assert len(conditional_edges) == 1
    c_edge = conditional_edges[0]
    assert c_edge.source == "supervisor"
    assert c_edge.condition_fn == "route_decision"
    assert c_edge.conditional_mapping == {
        "research": "researcher",
        "code": "coder",
        "finish": "END",
    }


def test_scan_agent_with_tools_and_tracing():
    file_path = str(SAMPLE_DIR / "agent_with_tools_and_tracing.py")
    res = scan_python_file(file_path)

    assert len(res.errors) == 0
    assert len(res.graphs) == 1

    # Check tool definitions (@tool)
    assert len(res.tool_defs) == 2
    tool_names = {t.name: t for t in res.tool_defs}
    assert "search_web" in tool_names
    assert "calculate_math" in tool_names

    # Check tool line ranges and docstrings
    search_tool = tool_names["search_web"]
    assert search_tool.line_start < search_tool.line_end
    assert "Search Google" in search_tool.docstring
    assert not search_tool.is_instrumented

    calc_tool = tool_names["calculate_math"]
    assert calc_tool.is_instrumented is True
    assert "traceable" in calc_tool.telemetry_decorators

    # Check ToolNodes
    assert len(res.tool_nodes) >= 1
    tool_node = res.tool_nodes[0]
    assert set(tool_node.tools) == {"search_web", "calculate_math"}

    # Check Prompt definitions
    assert len(res.prompts) >= 1
    prompt = res.prompts[0]
    assert prompt.var_name == "system_prompt"
    assert prompt.template_type == "ChatPromptTemplate"

    # Check Agent definitions
    agent_names = {a.name: a for a in res.agent_defs}
    assert "researcher_agent" in agent_names
    researcher = agent_names["researcher_agent"]

    # Line range
    assert researcher.line_start < researcher.line_end
    assert "Primary researcher agent" in researcher.docstring

    # Tracing
    assert researcher.is_instrumented is True
    assert "traceable" in researcher.telemetry_decorators

    # LLM calls inside agent
    assert len(researcher.llm_calls) == 1
    llm_call = researcher.llm_calls[0]
    assert llm_call.caller_var == "model_with_tools"
    assert llm_call.method == "invoke"


def test_scan_repository_observability_audit():
    result = scan_repository(str(SAMPLE_DIR))

    assert result.total_graphs == 3
    assert result.total_compiled == 3
    assert len(result.tool_definitions) == 2
    assert len(result.tool_nodes) >= 1

    # Check Observability Audit
    assert result.observability is not None
    obs = result.observability

    # Packages detected from sample requirements.txt
    pkg_names = [p.name for p in obs.packages]
    assert "LangSmith" in pkg_names
    assert "OpenTelemetry API" in pkg_names

    # Env vars detected from sample .env
    assert "LANGCHAIN_TRACING_V2" in obs.env_vars
    assert "LANGCHAIN_API_KEY" in obs.env_vars

    # Tracing coverage
    assert obs.instrumented_agents >= 1
    assert obs.instrumented_tools >= 1


def test_json_formatter():
    result = scan_repository(str(SAMPLE_DIR))
    # Test standardized Cohzen Manifest v0.1 format
    manifest_json = format_json(result)
    assert '"graphs"' in manifest_json
    assert '"nodes"' in manifest_json
    assert '"tools"' in manifest_json
    assert '"models"' in manifest_json
    assert '"compiled_var": "app"' in manifest_json
    assert '"target":' in manifest_json

    # Test raw ScanResult format
    raw_json = format_json(result, raw=True)
    assert '"target_path"' in raw_json
    assert '"observability"' in raw_json


def test_mermaid_formatter():
    result = scan_repository(str(SAMPLE_DIR))
    mermaid_str = format_mermaid(result)
    assert "flowchart TD" in mermaid_str
    assert "__start__([● START])" in mermaid_str
    assert "__end__([● END])" in mermaid_str
    assert "supervisor" in mermaid_str
    assert "researcher" in mermaid_str
    assert "Checkpointer" in mermaid_str
    assert "ToolNode" in mermaid_str
    assert "Tracing" in mermaid_str
