"""Tests for CLI options, flags, runner execution, and output formatters."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cz.cli import app
from cz.formatters.console import print_console_report
from cz.formatters.json_fmt import format_json
from cz.formatters.mermaid import format_mermaid
from cz.scanner.engine import scan_repository

runner = CliRunner()
SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_graphs"


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "cz version" in result.stdout


def test_cli_scan_table_default():
    result = runner.invoke(app, ["scan", str(SAMPLE_DIR)])
    assert result.exit_code == 0
    assert "Cohzen Architecture Scanner" in result.stdout
    assert "Registered Nodes" in result.stdout
    assert "Graph Topology" in result.stdout
    assert "cz audit" in result.stdout


def test_cli_scan_json_and_flag():
    # 1. via --format json
    res1 = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--format", "json"])
    assert res1.exit_code == 0
    parsed1 = json.loads(res1.stdout)
    assert parsed1["version"] == "0.1.0"
    assert "graphs" in parsed1
    assert "nodes" in parsed1
    assert "tools" in parsed1
    assert "models" in parsed1
    assert "metadata" in parsed1
    assert parsed1["metadata"]["target"] == str(SAMPLE_DIR)

    # 2. via --json shortcut
    res2 = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--json"])
    assert res2.exit_code == 0
    parsed2 = json.loads(res2.stdout)
    assert len(parsed2["graphs"]) == len(parsed1["graphs"])
    assert len(parsed2["nodes"]) == len(parsed1["nodes"])


def test_cli_scan_mermaid_and_flag():
    # 1. via --format mermaid
    res1 = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--format", "mermaid"])
    assert res1.exit_code == 0
    assert "flowchart TD" in res1.stdout

    # 2. via --mermaid shortcut
    res2 = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--mermaid"])
    assert res2.exit_code == 0
    assert "flowchart TD" in res2.stdout


def test_cli_scan_output_to_file(tmp_path: Path):
    out_file = tmp_path / "report.json"
    result = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--format", "json", "-o", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    content = json.loads(out_file.read_text())
    assert "graphs" in content


def test_format_mermaid_empty_result(tmp_path: Path):
    res = scan_repository(str(tmp_path))
    mermaid_text = format_mermaid(res)
    assert "No LangGraph workflows detected" in mermaid_text


def test_print_console_report_empty(tmp_path: Path):
    from rich.console import Console
    res = scan_repository(str(tmp_path))
    file_console = Console(record=True)
    print_console_report(res, console=file_console)
    output = file_console.export_text()
    assert "No LangGraph definitions" in output


def test_mermaid_langgraph_structure_elements():
    """Validates that Mermaid output mirrors LangGraph structure across all 6 core dimensions:

    Nodes, Edges, Tools, Checkpointers, LLMs, and Observability.
    """
    res = scan_repository(str(SAMPLE_DIR))
    mermaid_str = format_mermaid(res)

    # 1. Sentinels and Nodes
    assert "__start__([● START])" in mermaid_str
    assert "__end__([● END])" in mermaid_str
    assert "researcher" in mermaid_str
    assert "supervisor" in mermaid_str

    # 2. Edges and Routing
    assert "__start__ -->" in mermaid_str
    assert "--> __end__" in mermaid_str
    assert "-.->|route:" in mermaid_str

    # 3. Tools and ToolNodes
    assert "ToolNode" in mermaid_str
    assert "search_web" in mermaid_str
    assert "calculate_math" in mermaid_str

    # 4. Checkpointers and State Persistence
    assert "💾 Checkpointer" in mermaid_str
    assert "MemorySaver" in mermaid_str
    assert "checkpointer -.->|state persistence| __start__" in mermaid_str

    # 5. LLM Call Invocations
    assert "🧠 LLM:" in mermaid_str
    assert "langchain" in mermaid_str

    # 6. Observability and Styling
    assert "🔭 Tracing:" in mermaid_str
    assert "@traceable" in mermaid_str
    assert "classDef sentinelNode" in mermaid_str
    assert "classDef checkpointerNode" in mermaid_str
    assert "classDef toolNode" in mermaid_str
    assert "classDef instrumentedAgent" in mermaid_str
    assert "classDef uninstrumentedAgent" in mermaid_str


def test_html_viewer_generation():
    from cz.formatters.viewer import generate_viewer_html
    res = scan_repository(str(SAMPLE_DIR))
    html = generate_viewer_html(res)
    assert "<!DOCTYPE html>" in html
    assert "cz LangGraph Architecture Visualizer" in html
    assert "mermaid" in html
    assert "researcher" in html


def test_cli_view_invocations(monkeypatch):
    import cz.formatters.viewer
    opened = []
    monkeypatch.setattr(cz.formatters.viewer.webbrowser, "open", lambda url: opened.append(url))

    # Test via `cz scan --view`
    res1 = runner.invoke(app, ["scan", str(SAMPLE_DIR), "--view"])
    assert res1.exit_code == 0
    assert len(opened) == 1
    assert "cz_graph_viewer.html" in opened[0]

    # Test via `cz view`
    res2 = runner.invoke(app, ["view", str(SAMPLE_DIR)])
    assert res2.exit_code == 0
    assert len(opened) == 2


def test_cli_audit():
    res = runner.invoke(app, ["audit", str(SAMPLE_DIR)])
    assert res.exit_code == 0
    assert "Cohzen Observability & Telemetry Audit" in res.stdout
    assert "Observability Tools" in res.stdout
    assert "LangSmith" in res.stdout
    assert "Telemetry Packages" in res.stdout
    assert "Tracing Coverage" in res.stdout
    assert "Node Instrumentation Status" in res.stdout
    assert "Observability Tool" in res.stdout


def test_cli_audit_json():
    res = runner.invoke(app, ["audit", str(SAMPLE_DIR), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert "packages" in data
    assert "tools_detected" in data
    assert "LangSmith" in data["tools_detected"]
    assert "agent_instrumentation_pct" in data


def test_manifest_normalized_model_and_sorting():
    res = scan_repository(str(SAMPLE_DIR))
    manifest = res.to_manifest()
    assert manifest.version == "0.1.0"
    assert manifest.total_graphs > 0
    assert manifest.total_nodes > 0

    # Verify normalized IDs
    for node in manifest.nodes:
        assert node.kind == "node"
        assert node.source is not None
        assert node.resolution is not None
        for mid in node.model_ids:
            assert mid.startswith("model.")
        for tid in node.tool_ids:
            assert tid.startswith("tool.")

    for tool in manifest.tools:
        assert tool.id.startswith("tool.")
        assert tool.name

    for model in manifest.models:
        assert model.id.startswith("model.")
        assert model.provider

    # Verify deterministic sorting
    graph_ids = [g.id for g in manifest.graphs]
    assert graph_ids == sorted(graph_ids)
    node_ids = [n.id for n in manifest.nodes]
    assert node_ids == sorted(node_ids)
    tool_ids = [t.id for t in manifest.tools]
    assert tool_ids == sorted(tool_ids)
    model_ids = [m.id for m in manifest.models]
    assert model_ids == sorted(model_ids)


