"""Tests for ManifestMatcher linking spans to AST entities."""

from pathlib import Path
from cz.execution.manifest_matcher import ManifestMatcher
from cz.manifest.schema import CohzenManifest, GraphDef, ManifestMetadata, ModelDef, NodeDef, ToolDef


def test_manifest_matcher_with_sample_manifest(tmp_path: Path):
    manifest = CohzenManifest(
        version="0.1.0",
        metadata=ManifestMetadata(target=str(tmp_path)),
        graphs=[
            GraphDef(id="graph.customer_flow", name="customer_flow"),
        ],
        nodes=[
            NodeDef(id="planner", name="planner", handler="plan_fn"),
            NodeDef(id="writer", name="writer", handler="write_fn"),
        ],
        tools=[
            ToolDef(id="tool.search", name="search"),
        ],
        models=[
            ModelDef(id="model.openai.gpt-4o", provider="openai", name="gpt-4o"),
        ],
    )
    cohzen_dir = tmp_path / ".cohzen"
    cohzen_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = cohzen_dir / "manifest.json"
    manifest_file.write_text(manifest.model_dump_json(), encoding="utf-8")

    matcher = ManifestMatcher(manifest_path=manifest_file)

    assert matcher.resolve_graph_id("customer_flow") == "graph.customer_flow"
    assert matcher.resolve_node_entity_id("planner") == "node.planner"
    assert matcher.resolve_node_entity_id("writer") == "node.writer"
    assert matcher.resolve_tool_entity_id("search") == "tool.search"
    assert matcher.resolve_model_entity_id("gpt-4o", "openai") == "model.openai.gpt-4o"

    # Fallback unmapped entities
    assert matcher.resolve_node_entity_id("unknown_node") == "node.unknown_node"
    assert matcher.resolve_tool_entity_id("unknown_tool") == "tool.unknown_tool"
    assert matcher.resolve_model_entity_id("claude-3-5-sonnet", "anthropic") == "model.anthropic.claude-3-5-sonnet"


def test_manifest_matcher_without_manifest():
    matcher = ManifestMatcher(manifest_path=None)
    assert matcher.resolve_graph_id("my_flow") == "my_flow"
    assert matcher.resolve_node_entity_id("worker") == "node.worker"
    assert matcher.resolve_tool_entity_id("calculator") == "tool.calculator"
    assert matcher.resolve_model_entity_id("gpt-4o", "openai") == "model.openai.gpt-4o"
