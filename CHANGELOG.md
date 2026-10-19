# Changelog

All notable changes to **Cohzen (`cz`)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.3.0] - 2026-10-19

### License
- **License Change**: Changed project open-source license from MIT to **Apache 2.0** (`Apache-2.0`) with an explicit `NOTICE` attribution file. *(Note: previously published release v0.2.0 on PyPI was released under MIT).*

### Added
- **Fail-Open Always-On Local Capture**:
  - Environment-level `.pth` startup hook (`cohzen_startup.pth`) installed via `cz init` to capture LangGraph graph executions with zero user code modifications.
  - Fail-open, zero-overhead safety gating: skips unmarked projects, production environments (`COHZEN_ENV=production`), CI runs without explicit consent (`capture_in_ci = true`), and virtualenv console scripts.
- **Asynchronous Telemetry Persistence (`AsyncExecutionStore`)**:
  - Bounded in-memory write queue with copy-on-write snapshotting to eliminate application latency impact.
  - Fork-safe recovery and automatic reinitialization on PID change.
  - Bounded `atexit` flush handler (1.0s limit) guaranteeing process termination without hanging.
- **Lifecycle Management Commands**:
  - `cz status`: Inspect project capture status, hook health, and retention policies.
  - `cz on` / `cz off`: Toggle always-on capture without modifying code or uninstalling hooks.
  - `cz deinit`: Complete teardown with confirmation, exact file removal plan, and optional data retention (`--keep-data`).
- **Automated Secret Redaction & Retention**:
  - Built-in `RedactionProcessor` redacting API keys (OpenAI, AWS, Google, GitHub), Bearer tokens, private keys, emails, and phone numbers before writing to SQLite.
  - Automatic pruning of excess runs (`max_runs`) and expired runs (`max_age_days`) configured via `.cohzen/config.toml`.
- **Cross-Version LangGraph Contract Verification**:
  - Dedicated multi-version contract test suite covering `CallbackManager` non-mutation, positional configs, stream cancellation (`GeneratorExit` / `CancelledError`), nested graphs, thread-safety, and exception handling.
  - GitHub Actions matrix testing LangGraph `0.2.76`, `1.0.10`, `1.1.10`, and `1.2.16`, plus scheduled daily runs against unpinned latest PyPI releases.
- **Community Governance & Security**:
  - Added Contributor Covenant Code of Conduct (`CODE_OF_CONDUCT.md`).
  - Added Security policy (`SECURITY.md`) detailing private vulnerability reporting and local telemetry safety.
  - Added DCO commit sign-off verification workflow (`.github/workflows/dco.yml`).
  - Added step-by-step contribution guide for AST detectors (`docs/adding-a-detector.md`).
  - Migrated PyPI release automation to Trusted Publishing (OIDC).

### Changed & Deprecated
- **Deprecated `sitecustomize.py` Injection**:
  - `cz init` no longer writes or modifies project-local `sitecustomize.py` files.
  - Added automated migration in `cz init` and `cz deinit` to remove legacy Cohzen blocks from existing `sitecustomize.py` files and replace deprecated `cohzen.pth` hooks.
- **Narrow Compiled-Graph Interception**:
  - Replaced broad runtime import patching with narrow wrappers around public LangGraph compiled graph classes (`Pregel`, `CompiledStateGraph`, `CompiledGraph`). Graph builders, schemas, and `Runnable` base classes remain untouched.

---

## [0.2.0] - 2026-10-02

### Added
- **Runtime Execution Tracking & Observability (`cz init`, `cz runs`, `cz run <id>`)**:
  - Transparent LangChain / LangGraph execution tracing with zero code changes via `CohzenCallbackHandler`.
  - SQLite persistent telemetry store `.cohzen/executions.db` recording run states, tokens, latency, and spans.
  - Interactive terminal run viewers, detailed JSON payloads, and execution waterfall timeline graphs (`cz waterfall`).
- **Isolated Node Debugger (`cz node run`, `cz node list`, `cz debug`)**:
  - Test and run individual LangGraph nodes directly in isolation without compiling or running the entire graph.
  - State replay from previous executions using `--from-run <id>`.
  - Smart state hydration reconstructing Pydantic models, dual-access state dicts, and LangChain message objects.
- **Interactive Browser Telemetry Viewer**:
  - Visual Gantt waterfall and execution trace inspection in browser (`cz run <id> --view`).

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
