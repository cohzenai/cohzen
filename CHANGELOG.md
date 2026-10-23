# Changelog

All notable changes to **Cohzen (`cz`)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.3.3] - 2026-10-23

### Fixed

- **`agent_instrumentation_pct` Returns `null` for Empty Repos**: `ObservabilityAudit.agent_instrumentation_pct`
  now returns `None` (serialised as JSON `null`) when `total_agents == 0`, so callers can distinguish
  "not applicable" from "0% coverage on a live codebase." All output surfaces updated:
  - **Terminal**: continues to display `n/a, no nodes found` (no visible change).
  - **JSON (`cz audit --json`)**: field is now `null` instead of `0.0`.
  - **PR comment / GitHub Action output (`instrumentation-pct`)**: shows `n/a` instead of `0.0`.
- **`--min-coverage` Gate Skipped on Empty Repos (Exit 0)**: When no agent nodes are found,
  `--min-coverage` is now silently skipped with a single `INFO` line and exits `0` by default.
  Use the new `--fail-on-empty` flag to treat empty repos as a CI failure instead.
- **New `--fail-on-empty` Gate Flag**: `cz audit --fail-on-empty` exits `1` when no agent nodes are
  detected in the scanned path. Useful for enforcing that a repository must contain LangGraph agents
  before any governance checks run.
- **Version Fallback is `"unknown"`**: The `except`-branch fallback in `__init__.py` is now the literal
  string `"unknown"` rather than a hardcoded version number, preventing stale strings from drifting
  across releases.

### Added

- **Exit Code Documentation**: `cz audit` docstring now documents all exit codes:
  `0` (all checks passed or skipped on empty repo), `1` (gate check failed), `2` (usage error).

### Docs

- Exit codes for `cz audit` documented in command help text.
- `--min-coverage` help text explains the new skip-on-empty behaviour and `--fail-on-empty` as the
  alternative.

## [0.3.2] - 2026-10-23

### Fixed
- **Syntax Error Reporting in Static Scan**: Surfaced file parsing and syntax errors prominently in terminal scan reports rather than silently reporting "No graphs found."
- **Empty Repo Observability Coverage**: Formatted coverage as `n/a, no nodes found` on codebases with 0 nodes instead of displaying a misleading `Nodes: 0/0 (100.0%)`.
- **Single Source of Truth for Version**: Updated `cz version` to read version dynamically from package metadata via `importlib.metadata` with graceful fallback, eliminating hardcoded drift.
- **Clean Error Handling in `cz capture`**: Caught missing command/executable errors cleanly (`FileNotFoundError`) to display a concise one-line error instead of a 40-line Python traceback.
- **Non-Zero Exit on Missing Execution**: Ensured `cz run <bad_id>` exits with code `1` when an execution ID is not found in the SQLite store.

## [0.3.1] - 2026-10-21

### Fixed
- **Multi-Version LangGraph Pregel Patching**: Resolved `Pregel` runtime engine via `cls.__mro__` and module candidate checks to intercept compiled graphs cleanly across LangGraph 0.2.x and 1.x without dropping runs.
- **Silent Uninstallation Safety**: Guarded `.pth` startup hook with a silent `try-except` block to eliminate Python startup errors if `cohzen` is uninstalled without running `cz deinit`.
- **Multi-Graph Mermaid PR Comments**: Output dedicated, collapsible ````mermaid ```` blocks per detected graph in GitHub Action CI comments, resolving Mermaid parser errors when repositories define multiple workflows.
- **CI Dependencies in Test Matrix**: Installed `.[dev,runtime]` in CI test matrix jobs and added `pytest.importorskip` guards for `langgraph` and `langchain-core` to allow running tests in minimal environments.
- **Privacy & Zero-Egress Tests**: Extended privacy verification test suite to assert zero network egress across both static scanning (`cz scan`) and runtime capture (`AsyncExecutionStore`, SQLite, `cz runs`).
- **Security Contact & Governance**: Updated security contact email in `SECURITY.md` to `security@cohzen.ai` and clarified best-effort heuristic redaction boundaries.

## [0.3.0] - 2026-10-19

### License & Project Identity
- **License Change**: Changed project open-source license from MIT to **Apache 2.0** (`Apache-2.0`) with an explicit `NOTICE` attribution file. *(Note: previously published release v0.2.0 on PyPI was released under the MIT license).*
- **Package Name**: Standardized project name as `cohzen` with CLI entry points `cz` and `cohzen`.

### Added
- **Fail-Open Always-On Local Capture**:
  - Environment-level `.pth` startup hook (`cohzen_startup.pth`) installed via `cz init` to capture LangGraph graph executions without modifying application code.
  - Fail-open, zero-overhead safety gating: skips unmarked projects, production environments (`COHZEN_ENV=production`), CI runs without explicit consent (`capture_in_ci = true`), and virtualenv console scripts.
  - Guarded `.pth` bootstrap wrapped in error-handling to ensure completely silent Python startup if the package is uninstalled without running `cz deinit`.
- **Asynchronous Telemetry Persistence (`AsyncExecutionStore`)**:
  - Bounded in-memory write queue with copy-on-write snapshotting to minimize latency impact on the host application.
  - Fork-safe recovery and automatic reinitialization on PID change.
  - Bounded `atexit` flush handler (1.0s limit) guaranteeing process termination without hanging.
- **Lifecycle Management Commands**:
  - `cz status`: Inspect project capture status, hook health, and retention policies.
  - `cz on` / `cz off`: Toggle always-on capture without modifying code or uninstalling hooks.
  - `cz deinit`: Complete teardown with confirmation, exact file removal plan, and optional data retention (`--keep-data`).
  - `cz capture -- <command>`: One-off execution capture for a single command.
  - `cz runs` and `cz run <id>`: Inspect local execution records, timings, and hierarchical spans in the terminal.
- **Pattern-Based Secret Redaction & Retention**:
  - Configurable `RedactionProcessor` redacting common API key formats (OpenAI, AWS, Google, GitHub), Bearer tokens, private keys, emails, and phone numbers before writing to SQLite. Heuristic regex matching is best-effort.
  - Automatic pruning of excess runs (`max_runs`) and expired runs (`max_age_days`) configured via `.cohzen/config.toml`.
- **Cross-Version LangGraph Contract Verification**:
  - Multi-version contract test suite covering `CallbackManager` non-mutation, positional configs, stream cancellation (`GeneratorExit` / `CancelledError`), nested graphs, thread-safety, and exception handling.
  - Verified across LangGraph `0.2.76`, `1.0.10`, `1.1.10`, and `1.2.16` (retaining 0.2.76 backward compatibility for legacy production deployments).
- **Automated CI/CD Governance Action**:
  - Composite GitHub Action (`cohzenai/cohzen`) to audit agent architecture and telemetry coverage on pull requests.
  - Multi-graph Mermaid flowchart visualization and markdown governance scorecards.
- **Community Governance & Security**:
  - Added Contributor Covenant Code of Conduct (`CODE_OF_CONDUCT.md`).
  - Added Security policy (`SECURITY.md`) detailing vulnerability reporting and local telemetry safety.
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
- **Observability Gap Auditing (`cz audit [path]`)**:
  - Automated inspection of telemetry package presence (`pyproject.toml`, `requirements.txt`), active environment variables, and node-by-node tracing decorators (`@traceable`, `@observe`).
- **Interactive HTML Graph Visualizer (`cz view [path]`)**:
  - Standalone dark-themed browser visualizer embedding Mermaid.js for inspecting reconstructed graph topologies.
- **Packaging & CI Improvements**:
  - Published to PyPI under MIT license with enhanced issue templates and initial CI workflow.

---

## [0.1.0] - 2024-09-19

### Added
- **100% Static LangGraph Architecture Reconstruction**: Statically analyzes LangGraph workflows directly from Python AST without executing runtime code.
- **Immutable System Manifest (`CohzenManifest` v0.1.0)**:
  - Canonical normalized schema representing graphs, nodes, edges, tools, and models.
  - Granular source location tracking (`file`, `line_start`, `line_end`).
  - Graceful degradation resolution states (`resolved`, `partially_resolved`, `unresolved`).
- **Detector Suite**:
  - LangGraph: `StateGraph`, `MessageGraph`, `Graph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile()`, checkpointer resolution, interrupt points.
  - LLM Providers: OpenAI, Anthropic, Google Gemini, Groq, xAI Grok, LiteLLM, LangChain client calls & `bind_tools`.
  - Tools: `@tool` function inspection, line spans, docstrings, `ToolNode` parameter extraction.
- **CLI Commands**:
  - `cz scan [path]`: Terminal dashboard, `--json` manifest, `--mermaid` diagram export.
  - `cz version`: Version details.
- **Test Suite**: 56 unit and integration fixture tests covering monolithic graphs, split modules, multiple graphs, subgraphs, and ToolNodes.
