"""Matches runtime nodes, tools, and models to static entities in the Cohzen Manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from cz.manifest.schema import CohzenManifest


class ManifestMatcher:
    """Loads a project's Cohzen Manifest to link runtime spans to static AST entities."""

    def __init__(self, manifest_path: Optional[Path | str] = None):
        self.manifest_path = self._find_manifest(manifest_path)
        self.manifest: Optional[CohzenManifest] = None
        self._node_ids: Dict[str, str] = {}
        self._tool_ids: Dict[str, str] = {}
        self._model_ids: Dict[str, str] = {}
        self._graph_ids: Dict[str, str] = {}
        self._load()

    def _find_manifest(self, explicit_path: Optional[Path | str]) -> Optional[Path]:
        if explicit_path:
            p = Path(explicit_path)
            if p.is_file():
                return p
            elif (p / ".cohzen" / "manifest.json").is_file():
                return p / ".cohzen" / "manifest.json"

        curr = Path.cwd()
        for directory in [curr, *curr.parents]:
            candidate = directory / ".cohzen" / "manifest.json"
            if candidate.is_file():
                return candidate
        return None

    def _load(self) -> None:
        if not self.manifest_path or not self.manifest_path.is_file():
            return
        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            self.manifest = CohzenManifest.model_validate_json(content)
            for g in self.manifest.graphs:
                self._graph_ids[g.id] = g.id
                self._graph_ids[g.name] = g.id

            for n in self.manifest.nodes:
                self._node_ids[n.id] = f"node.{n.id}"
                self._node_ids[n.name] = f"node.{n.id}"

            for t in self.manifest.tools:
                self._tool_ids[t.id] = t.id
                self._tool_ids[t.name] = t.id

            for m in self.manifest.models:
                self._model_ids[m.id] = m.id
                self._model_ids[m.name] = m.id
        except Exception:
            # Manifest loading is best-effort and must not crash execution
            self.manifest = None

    def resolve_graph_id(self, graph_name: str) -> str:
        """Resolve a graph identifier or fallback to standard name."""
        if graph_name in self._graph_ids:
            return self._graph_ids[graph_name]
        return graph_name or "graph.default"

    def resolve_node_entity_id(self, node_name: str) -> str:
        """Resolve a node entity ID (e.g. 'node.planner')."""
        if node_name in self._node_ids:
            return self._node_ids[node_name]
        return f"node.{node_name}"

    def resolve_tool_entity_id(self, tool_name: str) -> str:
        """Resolve a tool entity ID (e.g. 'tool.search')."""
        if tool_name in self._tool_ids:
            return self._tool_ids[tool_name]
        return f"tool.{tool_name}"

    def resolve_model_entity_id(self, model_name: str, provider: Optional[str] = None) -> str:
        """Resolve an LLM entity ID (e.g. 'model.openai.gpt-4o')."""
        if model_name in self._model_ids:
            return self._model_ids[model_name]
        prov = provider or "unknown"
        return f"model.{prov}.{model_name}"
