"""Real-world repository diversity test suite.

Tests cz against 10 distinct architectural patterns and challenging repository layouts:
01_single_file
02_graph_split_across_modules
03_multiple_graphs
04_imported_nodes
05_imported_tools
06_factory_created_graph
07_conditional_routing
08_toolnode_and_bind_tools
09_subgraphs
10_dynamic_or_partially_unresolvable
"""

from pathlib import Path
import pytest
from cz.scanner.engine import scan_repository

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real_world"


def test_01_single_file():
    target = FIXTURES_DIR / "01_single_file.py"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert g.name == "workflow"
    assert g.is_compiled is True
    assert g.compilation.checkpointer == "checkpointer"
    assert "agent" in g.node_ids
    assert manifest.total_tools == 1
    assert manifest.tools[0].name == "search_web"
    assert manifest.metadata.unresolved_symbols == 0


def test_02_graph_split_across_modules():
    target = FIXTURES_DIR / "02_graph_split_across_modules"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert g.name == "builder"
    assert g.state_schema == "MultiModuleState"
    assert set(g.node_ids) == {"retriever", "generator"}
    assert manifest.total_tools == 1
    assert manifest.tools[0].name == "fetch_docs"


def test_03_multiple_graphs():
    target = FIXTURES_DIR / "03_multiple_graphs"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 2
    graph_names = {g.name for g in manifest.graphs}
    assert graph_names == {"ingest_builder", "query_builder"}

    node_ids = {n.id for n in manifest.nodes}
    assert {"parse", "embed", "search", "synthesize"}.issubset(node_ids)


def test_04_imported_nodes_graceful_degradation():
    target = FIXTURES_DIR / "04_imported_nodes"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert set(g.node_ids) == {"solver", "guardrail"}

    # Both imported nodes must degrade gracefully to unresolved
    solver_node = next(n for n in manifest.nodes if n.id == "solver")
    guardrail_node = next(n for n in manifest.nodes if n.id == "guardrail")

    assert solver_node.resolution.status == "unresolved"
    assert solver_node.resolution.reason == "external_import"
    assert guardrail_node.resolution.status == "unresolved"
    assert guardrail_node.resolution.reason == "external_import"

    assert manifest.metadata.unresolved_symbols >= 2
    assert len(manifest.metadata.warnings) >= 1


def test_05_imported_tools_graceful_degradation():
    target = FIXTURES_DIR / "05_imported_tools"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert "tools" in g.node_ids

    tool_node = next(n for n in manifest.nodes if n.id == "tools")
    assert tool_node.classification.role == "tool_node"

    # External tools must be recorded with unresolved status
    tool_names = {t.name for t in manifest.tools}
    assert "tavily_tool" in tool_names
    assert "sql_tool" in tool_names

    tavily_tool = next(t for t in manifest.tools if t.name == "tavily_tool")
    assert tavily_tool.resolution.status == "unresolved"
    assert tavily_tool.resolution.reason == "missing_symbol"


def test_06_factory_created_graph():
    target = FIXTURES_DIR / "06_factory_created_graph"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert g.name == "builder"
    assert set(g.node_ids) == {"triage", "billing"}
    assert g.is_compiled is True
    assert "memory" in (g.compilation.checkpointer or "")
    assert "billing" in g.compilation.interrupt_before


def test_07_conditional_routing():
    target = FIXTURES_DIR / "07_conditional_routing"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert set(g.node_ids) == {"standard", "escalate", "archive"}

    cond_edge = next((e for e in g.edges if e.edge_type == "conditional"), None)
    assert cond_edge is not None
    assert cond_edge.condition_fn == "router_fn"
    assert cond_edge.conditional_mapping == {
        "standard": "standard",
        "escalate": "escalate",
        "archive": "archive",
    }


def test_08_toolnode_and_bind_tools():
    target = FIXTURES_DIR / "08_toolnode_and_bind_tools"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert set(g.node_ids) == {"assistant", "tools"}

    assistant = next(n for n in manifest.nodes if n.id == "assistant")
    assert "tool.execute_sql" in assistant.tool_ids

    tools_node = next(n for n in manifest.nodes if n.id == "tools")
    assert "tool.execute_sql" in tools_node.tool_ids


def test_09_subgraphs():
    target = FIXTURES_DIR / "09_subgraphs"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    # Both child and parent graphs should be detected
    assert manifest.total_graphs == 2
    graph_names = {g.name for g in manifest.graphs}
    assert graph_names == {"child_builder", "parent_builder"}

    parent_g = next(g for g in manifest.graphs if g.name == "parent_builder")
    assert "subgraph_task" in parent_g.node_ids


def test_10_dynamic_or_partially_unresolvable():
    target = FIXTURES_DIR / "10_dynamic_or_partially_unresolvable"
    res = scan_repository(str(target))
    manifest = res.to_manifest()

    assert manifest.total_graphs == 1
    g = manifest.graphs[0]
    assert set(g.node_ids) == {"transform", "agent"}

    # Inline lambda handler is fully supported as a resolved logic node
    transform_node = next(n for n in manifest.nodes if n.id == "transform")
    assert transform_node.resolution.status == "resolved"
    assert transform_node.classification.role == "logic"
    assert "inline_lambda" in transform_node.classification.evidence

    agent_node = next(n for n in manifest.nodes if n.id == "agent")
    assert agent_node.resolution.status == "resolved"
    assert agent_node.classification.role == "agent"

