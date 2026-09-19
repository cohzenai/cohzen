# `cz` (Cohzen CLI)

**`cz`** statically reconstructs existing **LangGraph** applications' architecture and emits an immutable, machine-readable system manifest (**Cohzen Manifest v0.1**).

> **Core Philosophy**: *"Cohzen reconstructs what can be determined statically from the codebase with zero runtime execution."*

Everything in Cohzen flows through a single unified pipeline:

```text
Repository ──► AST ──► Discovery ──► Resolution ──► CohzenManifest (v0.1)
                                                           │
                     ┌───────────────────┬─────────────────┴─────────────────┐
                     ▼                   ▼                                   ▼
              Terminal / Flow      Mermaid Diagram                   Browser Visualizer
              (`cz scan`)         (`cz scan --mermaid`)             (`cz view`)
```

And **`cz audit`** consumes the exact same discovered AST facts to perform in-depth observability and telemetry health audits without redefining architecture.

---

## 🏗️ Production-Grade Modular Architecture

The repository is organized into distinct, enterprise-grade domain packages:

```
cohzen/
├── .github/                       # CI/CD workflows & issue templates
│   ├── workflows/                 # GitHub Actions (tests.yml, release.yml)
│   ├── ISSUE_TEMPLATE/            # Bug report & feature request templates
│   └── pull_request_template.md   # Pull request checklist & guide
│
├── docs/                          # Comprehensive technical documentation
│   ├── architecture.md            # Static AST pipeline & engine architecture
│   ├── manifest.md                # CohzenManifest v0.1 JSON specification
│   ├── supported-frameworks.md    # Framework & LLM detector matrix
│   └── development.md             # Contributor quickstart & testing guidelines
│
├── examples/                      # Runnable standalone LangGraph examples
│   ├── langgraph-basic/           # ProcessState pipeline with MemorySaver
│   ├── langgraph-tools/           # MessagesState agent with ToolNode & lambda routing
│   └── langgraph-routing/         # Supervisor team with conditional routing & interrupts
│
├── src/cz/
│   ├── cli/                       # Modern CLI application (`main.py`, Typer app)
│   ├── scanner/                   # Core AST scanner engine, visitor, and models
│   │   ├── engine.py              # Repository scan orchestrator
│   │   ├── visitor.py             # Unified AST visitor & symbol resolver
│   │   ├── utils.py               # AST string & expression extractors
│   │   └── models.py              # Internal AST scan models & telemetry types
│   │
│   ├── manifest/                  # Immutable Cohzen Manifest v0.1 Contract
│   │   ├── schema.py              # CohzenManifest, GraphDef, NodeDef, ToolDef, ModelDef
│   │   └── builder.py             # Deterministic Manifest compilation
│   │
│   ├── detectors/                 # Static AST pattern detectors
│   │   ├── base.py                # BaseFrameworkScanner & BaseLLMDetector protocols
│   │   ├── langgraph/             # LangGraph framework detector (StateGraph, nodes, edges)
│   │   ├── llm/                   # Frozen v0.1 LLM provider detectors (OpenAI, Anthropic, Google, etc.)
│   │   └── tools/                 # Tool detector (@tool decorators, line spans)
│   │
│   ├── audit/                     # Observability & telemetry governance engine
│   │   ├── engine.py              # Audit orchestrator
│   │   ├── registry.py            # Observability detector registry
│   │   └── [providers]/           # LangSmith, Langfuse, Phoenix, Traceloop, AgentOps, etc.
│   │
│   └── formatters/                # Presentation & serialization
│       ├── console.py             # Rich architecture & audit flow reports
│       ├── mermaid.py             # LangGraph-compatible Mermaid flowchart
│       ├── json_fmt.py            # Cohzen Manifest JSON serializer
│       └── viewer.py              # Interactive dark-mode HTML browser visualizer
│
└── tests/
    ├── fixtures/                  # Real-world & sample test fixtures
    │   ├── real_world/            # 10 production-pattern test projects
    │   └── sample_graphs/         # Specialized graph variations
    └── test_*.py                  # Automated test suites
```

---

## 🔍 CLI Command Hierarchy

| Command | Domain | Description |
|---|---|---|
| **`cz scan [path]`** | **Architecture Discovery** | Reconstructs graphs, nodes, edges, models, tools, and checkpointer persistence. Emits terminal flow or **`CohzenManifest`** JSON. |
| **`cz audit [path]`** | **Observability Audit** | Audits telemetry packages, `.env` configurations, and node-by-node / tool-by-tool instrumentation attribution. |
| **`cz view [path]`** | **Visualization Shortcut** | Convenience alias for `cz scan --view` to launch the interactive browser visualizer. |
| **`cz version`** | **System Info** | Displays the installed `cz` release version. |

### 1. Architecture Discovery (`cz scan`)

```bash
# Clean high-signal terminal report
cz scan .

# Emit the official Cohzen Manifest v0.1 JSON
cz scan . --json

# Export to Mermaid Diagram
cz scan . --mermaid -o architecture.mmd

# Launch dark-mode interactive web visualizer
cz scan . --view
# or shortcut:
cz view .
```

### 2. Observability & Telemetry Audit (`cz audit`)

```bash
# Terminal telemetry audit with active tool attribution
cz audit .

# Export audit findings and coverage as JSON for CI/CD gates
cz audit . --json
```

---

## 📜 The Cohzen System Manifest (v0.1)

The manifest is the **immutable, machine-readable contract** produced by `cz scan --json`. Discovered entities use stable IDs, standardized `SourceLocation`, and explicit resolution tracking:

```json
{
  "version": "0.1.0",
  "metadata": {
    "target": ".",
    "files_scanned": 14,
    "files_skipped": 0,
    "parse_errors": 0,
    "unresolved_symbols": 0,
    "dynamic_constructions": 0,
    "scan_duration_ms": 2.14,
    "created_at": "2026-09-19T12:00:00Z",
    "warnings": []
  },
  "frameworks": ["langgraph"],
  "graphs": [
    {
      "id": "graph.workflow",
      "name": "workflow",
      "framework": "langgraph",
      "graph_class": "StateGraph",
      "state_schema": "AgentState",
      "source": { "file": "app.py", "line_start": 20, "line_end": 20 },
      "node_ids": ["planner", "tools"],
      "edges": [
        { "source": "START", "target": "planner", "edge_type": "direct" },
        { "source": "planner", "target": "tools", "edge_type": "conditional" }
      ],
      "compilation": {
        "compiled_var": "app",
        "checkpointer": "MemorySaver",
        "source": { "file": "app.py", "line_start": 35, "line_end": 35 }
      }
    }
  ],
  "nodes": [
    {
      "id": "planner",
      "name": "planner",
      "kind": "node",
      "handler": "planner_node",
      "source": { "file": "app.py", "line_start": 10, "line_end": 18 },
      "model_ids": ["model.openai.gpt-4o"],
      "tool_ids": ["tool.search_web"],
      "resolution": { "status": "resolved", "reason": null },
      "classification": { "role": "agent", "confidence": "high", "evidence": ["llm_invocation", "tool_binding"] }
    }
  ],
  "tools": [
    {
      "id": "tool.search_web",
      "name": "search_web",
      "source": { "file": "tools.py", "line_start": 5, "line_end": 8 },
      "docstring": "Searches the web",
      "resolution": { "status": "resolved", "reason": null }
    }
  ],
  "models": [
    {
      "id": "model.openai.gpt-4o",
      "provider": "openai",
      "name": "gpt-4o",
      "source": { "file": "app.py", "line_start": 12, "line_end": 12 }
    }
  ]
}
```

---

## 🎯 Features Detected

| Domain | Provider / Tool | Capabilities Detected |
|---|---|---|
| **Frameworks** | **LangGraph** | `StateGraph`, `Graph`, `MessageGraph`, `.compile()` call sites, checkpointers (`MemorySaver`, `SqliteSaver`), human-in-the-loop interrupts (`interrupt_before`, `interrupt_after`), `store`, nodes, direct & conditional edges, `ToolNode` |
| **LLMs & Tool Bindings** | **OpenAI** | `chat.completions.create`, model identification, `tools=[...]`, `functions=[...]` |
| | **Anthropic** | `messages.create`, model identification, `tools=[...]` |
| | **Google** | `generate_content`, `generate_text`, model identification, `tools=[...]` |
| | **Groq** | Groq client chat completions, models, `tools=[...]` |
| | **Grok** | xAI Grok chat completions, models |
| | **LangChain** | `.invoke()`, `.ainvoke()`, `.stream()`, `model.bind_tools(tools)` |
| | **LiteLLM** | `completion()`, `acompletion()`, models, `tools=[...]` |
| **Observability (`cz audit`)** | **LangSmith** | Package manifests, `LANGCHAIN_TRACING_V2`, `@traceable` |
| | **Langfuse** | Package manifests, `LANGFUSE_*`, `@observe` |
| | **OpenTelemetry** | `opentelemetry-*`, `openinference-*`, `OTEL_*` |
| | **Arize Phoenix**| `arize-phoenix`, `phoenix`, `PHOENIX_*` |
| | **Traceloop** | `traceloop-sdk`, `TRACELOOP_*` |
| | **AgentOps** | `agentops`, `AGENTOPS_API_KEY`, `@track_agent` |
| | **W&B Weave** | `wandb`, `weave`, `@weave.op()` |

---

## 🔬 How `cz` Performs the Scan

1. **Zero-Execution Static AST Parsing**: `cz` never executes target code or imports unverified packages. It parses Python source trees into Abstract Syntax Trees using Python's native `ast` standard library.
2. **Registry-Driven Plugin Dispatch**: A unified AST visitor visits syntax nodes and dispatches them in parallel to modular registries:
   - **Framework Scanners**: Trace graph instantiations (`StateGraph`), node registrations (`add_node`), edge links (`add_edge`, `add_conditional_edges`), and compilation points (`compile(checkpointer=...)`).
   - **LLM Detectors**: Inspect function bodies for LLM client invocations, model parameters, and tool binding calls.
   - **Observability Detectors**: Cross-reference decorator names, package manifests (`pyproject.toml`, `requirements.txt`, `Pipfile`), and environment variable configs (`.env`).
3. **Multi-Scope Cross-Referencing**: Connects graph nodes to their corresponding agent implementations and tool executions, resolving same-file definitions before repository-wide fallbacks.
4. **Multi-Format Synthesis**: Formats the unified `ScanResult` into:
   - Rich interactive terminal dashboards with ASCII/Unicode flowcharts
   - Native LangGraph Mermaid diagrams
   - Interactive browser visualizer
   - Automated JSON payloads for CI/CD gates

---

## 🧪 Testing

Run all 56 modular unit, integration, and real-world fixture tests:
```bash
pytest tests/ -v
```

Includes 10 real-world architectural fixture projects under `tests/real_world_fixtures/`:
- `01_single_file.py`: Monolithic graph definition
- `02_graph_split_across_modules/`: Nodes and state split across files
- `03_multiple_graphs/`: Separate supervisor and worker graphs
- `04_imported_nodes/`: Third-party and cross-package node handlers
- `05_imported_tools/`: Tools imported from external helper modules
- `06_factory_created_graph/`: Builder functions returning compiled StateGraphs
- `07_conditional_routing/`: Multi-branch conditional edges
- `08_toolnode_and_bind_tools/`: LangGraph `ToolNode` and LLM `bind_tools`
- `09_subgraphs/`: Parent graphs embedding child workflow nodes
- `10_dynamic_or_partially_unresolvable/`: Dynamic lambdas and unresolvable imports with graceful degradation

Run test coverage report (92%+ coverage):
```bash
pytest --cov=cz --cov-report=term-missing tests/
```

