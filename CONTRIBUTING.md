# Contributing to Cohzen

Thank you for your interest in contributing to **Cohzen**! We welcome contributions from the community to make static agentic architecture discovery fast, accurate, and developer-friendly.

---

## Code of Conduct

Please be respectful, collaborative, and constructive when interacting with maintainers and other contributors.

---

## Development Setup

Cohzen requires **Python 3.10+**.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/cohzen-ai/cohzen.git
   cd cohzen
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in editable mode with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify the installation**:
   ```bash
   cz version
   pytest tests/ -v
   ```

---

## Repository Structure

```text
cohzen/
├── .github/                       # CI/CD workflows & community templates
│   ├── workflows/
│   │   ├── tests.yml              # Multi-Python (3.10, 3.11, 3.12) test matrix
│   │   └── release.yml            # Automated PyPI release workflow
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md          # Bug report template
│   │   └── feature_request.md     # Feature/detector request template
│   └── pull_request_template.md   # PR checklist and guidelines
│
├── docs/                          # Comprehensive technical documentation
│   ├── architecture.md            # Static AST engine & pipeline architecture
│   ├── manifest.md                # CohzenManifest v0.1 JSON specification
│   ├── supported-frameworks.md    # Framework & LLM detector matrix
│   └── development.md             # Contributor development workflow
│
├── examples/                      # Runnable standalone LangGraph examples
│   ├── langgraph-basic/           # ProcessState pipeline with MemorySaver
│   ├── langgraph-tools/           # MessagesState agent with ToolNode & lambda routing
│   └── langgraph-routing/         # Supervisor team with conditional routing & interrupts
│
├── src/cz/                        # Core codebase
│   ├── cli/                       # Typer-based CLI application (`main.py`)
│   │   ├── __init__.py
│   │   └── main.py                # Commands: cz scan, cz audit, cz view, cz version
│   │
│   ├── scanner/                   # AST analysis engine, visitor, and data models
│   │   ├── __init__.py
│   │   ├── engine.py              # Repository scan orchestrator (scan_repository, scan_file)
│   │   ├── visitor.py             # AST visitor & symbol resolver (scan_python_file)
│   │   ├── utils.py               # AST string & expression extractors
│   │   └── models.py              # ScanResult, GraphInfo, NodeInfo, ToolDef, etc.
│   │
│   ├── manifest/                  # Immutable Cohzen Manifest v0.1 Contract
│   │   ├── __init__.py
│   │   ├── schema.py              # CohzenManifest, GraphDef, NodeDef, ToolDef, ModelDef
│   │   └── builder.py             # Deterministic Manifest compilation
│   │
│   ├── detectors/                 # Static pattern detectors
│   │   ├── __init__.py
│   │   ├── base.py                # BaseFrameworkScanner, BaseLLMDetector, BaseToolDetector
│   │   ├── registry.py            # FrameworkRegistry
│   │   ├── langgraph/             # LangGraph framework detector (StateGraph, nodes, edges)
│   │   ├── llm/                   # Frozen v0.1 LLM provider detectors
│   │   │   ├── base.py
│   │   │   ├── registry.py        # LLMRegistry
│   │   │   ├── openai/
│   │   │   ├── anthropic/
│   │   │   ├── google/
│   │   │   ├── groq/
│   │   │   ├── grok/
│   │   │   ├── langchain/
│   │   │   └── litellm/
│   │   └── tools/                 # Tool detector (@tool decorators, line spans)
│   │       ├── __init__.py
│   │       └── detector.py
│   │
│   ├── audit/                     # Observability & telemetry governance engine
│   │   ├── __init__.py
│   │   ├── engine.py              # Audit orchestrator (audit_repository, scan_manifest_files)
│   │   ├── registry.py            # Observability detector registry
│   │   ├── base.py                # BaseObservabilityDetector protocol
│   │   ├── langsmith/
│   │   ├── langfuse/
│   │   ├── opentelemetry/
│   │   ├── arize_phoenix/
│   │   ├── traceloop/
│   │   ├── agentops/
│   │   └── wandb/
│   │
│   └── formatters/                # Output presentation & visualization
│       ├── __init__.py
│       ├── console.py             # Rich terminal architecture & audit flow reports
│       ├── mermaid.py             # LangGraph-compatible Mermaid flowchart
│       ├── json_fmt.py            # Cohzen Manifest JSON serializer
│       └── viewer.py              # Interactive dark-mode HTML browser visualizer
│
├── tests/                         # Test suites & fixtures
│   ├── fixtures/                  # Real-world & sample test fixtures
│   │   ├── real_world/            # 10 production-pattern test projects (01 to 10)
│   │   └── sample_graphs/         # Specialized graph variations
│   ├── test_scanner.py
│   ├── test_cli_and_formatters.py
│   ├── test_real_world_fixtures.py
│   ├── test_graphs_and_compilation.py
│   ├── test_routing_and_edges.py
│   ├── test_tools_and_nodes.py
│   ├── test_agents_and_llms.py
│   ├── test_llm_providers.py
│   ├── test_observability_audit.py
│   ├── test_observability_providers.py
│   ├── test_framework_registry.py
│   └── test_engine_and_ignores.py
│
├── .gitignore                     # Git ignore rules
├── pyproject.toml                 # Build configuration & entrypoint (cz = "cz.cli.main:app")
├── LICENSE                        # MIT License
├── README.md                      # Project documentation & overview
├── CHANGELOG.md                   # Version release notes
└── CONTRIBUTING.md                # Contributor guide
```

---

## Core Guiding Principles

When making changes to Cohzen:
1. **Zero Runtime Execution**: Cohzen is strictly a **static AST analysis tool**. Never import or execute scanned target user code (`importlib`, `exec()`, `eval()`).
2. **Immutable Contract**: The `CohzenManifest` (`v0.1.0`) is the single source of truth. Formats (`console`, `mermaid`, `json`, `view`) must consume discovered facts from this manifest.
3. **Graceful Degradation**: Real-world Python can be dynamic or external. Degrade gracefully (`resolved` -> `partially_resolved` -> `unresolved`) with honest static limitations rather than crashing or guessing.

---

## Running Tests

Run the complete test suite:
```bash
pytest tests/ -v
```

Generate a test coverage report:
```bash
pytest --cov=cz --cov-report=term-missing tests/
```

---

## Pull Request Guidelines

1. **Branch naming**: `feature/your-feature-name` or `fix/your-bug-fix`.
2. **Include tests**: Add unit tests or real-world fixtures under `tests/` demonstrating your fix or new detection pattern.
3. **Documentation**: Update relevant guides in `docs/` or `README.md` if CLI flags or manifest schemas change.
4. **Clean Git history**: Ensure commits are logical and well-described.
