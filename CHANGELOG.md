# Changelog

All notable changes to **Cohzen (`cz`)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2024-09-19

### Added
- **100% Static LangGraph Architecture Reconstruction**: Statically analyzes LangGraph workflows directly from Python AST without executing any runtime code.
- **Immutable System Manifest (`CohzenManifest` v0.1.0)**:
  - Canonical normalized schema representing graphs, nodes, edges, tools, and models.
  - Granular source location tracking (`file`, `line_start`, `line_end`).
  - Graceful degradation resolution states (`resolved`, `partially_resolved`, `unresolved`).
  - Analysis limitations & completeness metadata (`unresolved_symbols`, `dynamic_constructions`, `warnings`).
- **Comprehensive Detector Suite**:
  - LangGraph: `StateGraph`, `MessageGraph`, `Graph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile()`, checkpointer resolution, interrupt points.
  - LLM Providers: OpenAI, Anthropic, Google Gemini, Groq, xAI Grok, LiteLLM, LangChain client calls & `bind_tools`.
  - Tools: `@tool` function inspection, line spans, docstrings, `ToolNode` parameter extraction.
  - Observability Telemetry: Tracing decorator inspection (`@traceable`, `@observe`), manifest detection (`pyproject.toml`, `requirements.txt`), `.env` configuration audits.
- **First-Class Inline Lambda Support**: Automatically parses inline lambda handlers and routers into resolved nodes with body-level LLM inspection.
- **External Dependency Highlighting**: Explicitly identifies node and tool handlers imported from external packages (`external_package`) without conflating them with errors.
- **CLI Commands**:
  - `cz scan [path]`: Interactive terminal dashboard, `--json` manifest, `--mermaid` diagram export.
  - `cz audit [path]`: Observability and telemetry gap audit report with tool attribution.
  - `cz view [path]`: Standalone interactive HTML browser visualizer.
  - `cz version`: Version details.
- **Production Test Suite**: 56 unit, integration, and real-world fixture tests covering diverse patterns (monolithic graphs, split modules, multiple graphs, subgraphs, factory builders, conditional routing, ToolNodes).
