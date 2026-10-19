# `cz` (Cohzen CLI)

**`cz`** statically reconstructs existing **LangGraph** applications' architecture and emits an immutable, machine-readable system manifest (**Cohzen Manifest v0.1**). Package v0.2.0 still emits the v0.1 manifest contract; Manifest v0.2 is planned as an additive runtime contract.

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

## 🚀 Installation

```bash
pip install cohzen
# or with uv:
uv add cohzen
```

*Note: Once installed, both `cz` and `cohzen` commands are available.*

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
│   ├── ci-cd.md                   # CI/CD integration and GitHub Action guide
│   ├── gtm.md                     # Go-To-Market strategy and commercial roadmap
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
│   │   └── (built in scanner/models.py) # Deterministic Manifest compilation
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
│   ├── execution/                 # Opt-in local runtime spans, SQLite storage, and redaction
│   │   ├── callbacks.py            # LangChain/LangGraph callback recorder
│   │   ├── context.py              # Execution and span context managers
│   │   ├── instrumentation.py      # Legacy runtime patching hooks
│   │   ├── processor.py            # Default redaction and payload limits
│   │   └── sqlite.py               # Local run/span/event store and retention
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
| **`cz init [path]`** | **Always-On Setup** | Enables always-on local capture: creates configuration, telemetry DB, manifest, gitignore entry, and installs an isolated startup hook. |
| **`cz status [path]`** | **Capture Status** | Inspects effective capture settings, project marker, startup hook status, and retention limits. |
| **`cz on [path]` / `cz off [path]`** | **Capture Toggle** | Enables or disables always-on capture in `.cohzen/config.toml` without uninstalling hooks. |
| **`cz deinit [path]`** | **Project Teardown** | Reverts initialization: removes startup hooks, configuration, gitignore entries, and optionally retains `executions.db` (`--keep-data`). |
| **`cz capture -- <command>`** | **One-Off Capture** | Runs the supplied command with Cohzen capture enabled only for that single execution. |
| **`cz runs [path]` / `cz run <id>`** | **Runtime Records** | Lists local execution records or displays one record's hierarchical spans and timings. |
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

# CI / CD gate enforcement (fails with code 1 if under 80% coverage or unconfigured)
cz audit . --min-coverage 80 --fail-on-missing
```

### 3. Local Always-On Runtime Capture

Cohzen provides **fail-open, zero-overhead, always-on capture** for local LangGraph application development. Once initialized, LangGraph graph invocations (`invoke`, `ainvoke`, `stream`, `astream`) in your project are automatically recorded to a local SQLite database without requiring code modifications.

#### Initialization & Lifecycle

```bash
# Initialize always-on capture for the current project (shows exact planned actions and confirms)
cz init .

# Apply non-interactively in automated setups
cz init . --yes

# Specify target Python environment for virtual environments
cz init . --python /path/to/venv/bin/python

# Check current capture status and retention settings
cz status .

# Temporarily disable or re-enable capture for the project
cz off .
cz on .

# Deinitialize: remove configuration and startup hooks while retaining historical telemetry data
cz deinit . --yes --keep-data

# Full deinitialize: remove all artifacts and database
cz deinit . --yes
```

#### Exact File Plan & Legacy Migration
Running `cz init` plans and applies:
1. `.cohzen/config.toml`: Project configuration and retention policies.
2. `.cohzen/manifest.json`: Scanned architectural manifest.
3. `.cohzen/executions.db`: Local SQLite telemetry store with WAL mode and busy timeouts.
4. `.gitignore`: Automatically adds `.cohzen/` to prevent committing local databases.
5. `cohzen_startup.pth`: Lightweight startup hook in target site-packages (`import cz._startup; cz._startup.start()`).
6. **Automatic Legacy Migration**: Cleans legacy `sitecustomize.py` Cohzen blocks and replaces deprecated `cohzen.pth` files.

#### Configuration (`.cohzen/config.toml`)

```toml
enabled = true
capture_in_ci = false

[retention]
max_payload_bytes = 65536
max_runs = 1000
max_age_days = 30
```

#### Production Safety & Fail-Open Guarantees
* **Unmarked Project Safety**: Skips execution unless a valid `.cohzen` directory is found (or `COHZEN_PROJECT` is set).
* **Production & Disable Gates**: Capture is completely inert if `COHZEN_ENV=production` or `COHZEN_DISABLE=1`.
* **CI Isolation**: Disabled in CI environments by default; requires `capture_in_ci = true`.
* **Tool Isolation**: Avoids treating virtualenv console scripts (`bin/pytest`, `bin/ruff`, etc.) as application runs.
* **Narrow Compiled-Graph Interception**: Wraps only public compiled graph APIs (`Pregel`, `CompiledStateGraph`, `CompiledGraph`). Builders, schemas, and `Runnable` base classes remain untouched.
* **Non-Mutating Configs**: User-provided callback configurations and `CallbackManager` instances are never mutated in place.
* **Asynchronous Persistence**: Telemetry writes are queued asynchronously via `AsyncExecutionStore` off the execution hot path, with bounded queues, payload snapshotting, fork-safe PID recovery, and bounded `atexit` flushing (1.0s limit).
* **Default Redaction**: Sensitive keys (passwords, tokens, secrets, API keys) and value patterns (emails, phone numbers, bearer headers, private keys, AWS/OpenAI/GitHub keys) are redacted before persisting to disk.

### 4. One-Off Runtime Capture (`cz capture`)

For environments without startup hooks or for single-command runs:

```bash
cz capture -- python app.py
cz capture -- python -m pytest
cz runs .
cz run <run-id>
```

### Runtime Support Matrix

| Dependency | Supported range | Verified in this repository | Notes |
|---|---:|---:|---|
| Python | `>=3.10` | 3.10, 3.11, 3.12, 3.13 | Full automated test matrix across all 4 versions. |
| LangGraph | `>=0.2,<1.3` | 0.2.76, 1.0.10, 1.1.10, 1.2.16 | Tested via dedicated multi-version contract matrix and daily scheduled CI. |
| LangChain Core | `>=0.2,<1.7` | 1.6.6 | Safe copy-on-write callback propagation. |
| OpenTelemetry API | `>=1.20,<2` | 1.45.0 | Telemetry auditing and attribute detection. |

---

## 🛡️ GitHub Actions & CI/CD Governance

Attach Cohzen directly to your GitHub Actions pipeline using the official composite action:

```yaml
- name: Cohzen Agent Architecture & Telemetry Gate
  uses: cohzenai/cohzen@v0.2.0
  with:
    path: "."
    min-coverage: "80"
    fail-on-missing-telemetry: "true"
    comment-pr: "true"
```

The action automatically:
* 📊 Audits telemetry compliance and enforces `--min-coverage` thresholds.
* 🗺️ Renders an interactive Mermaid architecture diagram in the GitHub Step Summary.
* 💬 Posts/updates a sticky comment on pull requests with the architecture scorecard.
* 📦 Exports `manifest.json`, `architecture.mmd`, and `audit.json` build artifacts.

See the complete [CI/CD Integration Guide](docs/ci-cd.md) for full configuration options.

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

Run all 88 modular unit, integration, runtime, and real-world fixture tests:
```bash
pytest tests/ -v
```

Includes 10 real-world architectural fixture projects under `tests/fixtures/real_world/`:
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

Run the measured test coverage report (last local measurement: 72% total coverage on Python 3.13.11):
```bash
pytest --cov=cz --cov-report=term-missing tests/
```

