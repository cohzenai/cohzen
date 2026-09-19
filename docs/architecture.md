# Cohzen Architecture

Cohzen is a **100% static architecture scanner and observability auditor** for agentic workflows, focused on LangGraph in v0.1.

---

## The Core Pipeline

Everything in Cohzen flows through a single deterministic pipeline:

```text
Repository
   ↓
AST Parsing (Zero Runtime Execution)
   ↓
Discovery (Detectors: Frameworks, LLMs, Tools)
   ↓
Resolution (Resolved / Partially Resolved / Unresolved)
   ↓
CohzenManifest v0.1.0 (The Immutable Contract)
   ↓
 ┌───────────┬───────────┬───────────┬───────────┐
Console    Mermaid      JSON        View      Audit
```

---

## Architectural Principles

### 1. Zero Runtime Execution
Cohzen reconstructs what can be determined statically from the codebase. It:
- **Never executes** Python code (`exec()`, `eval()`, `importlib.import_module()`).
- **Never requires** active environment variables (`OPENAI_API_KEY`, etc.).
- **Never triggers** database connections, network requests, or side-effects.

### 2. The Manifest as Immutable Single Source of Truth
The architecture model (`CohzenManifest`) is decoupled from rendering formats and telemetry:
- `cz scan .` renders terminal dashboards from the manifest.
- `cz scan . --json` dumps the raw canonical manifest.
- `cz scan . --mermaid` translates the manifest topology to Mermaid markup.
- `cz view .` generates a local browser visualization.
- `cz audit .` evaluates telemetry instrumentation against the exact same architectural facts.

### 3. Graceful Degradation
Real-world code contains dynamic constructs and third-party library dependencies. Cohzen handles these gracefully:
- **Resolved**: Handlers and tools defined within the scanned codebase.
- **External Import**: Components imported from third-party packages; tracked and highlighted with `package="pkg_name"`.
- **Partially Resolved**: Dynamic runtime reflections or closures; recorded with `dynamic_expression`.
- **Unresolved**: Missing references without imports; surfaced in explicit analysis limitations.

---

## Subsystem Overview

| Component | Responsibility |
| :--- | :--- |
| `cz.scanner` | Filesystem traversal, AST visitor coordination, and cross-referencing. |
| `cz.detectors.langgraph` | LangGraph class instantiation, node registration, routing edges, and compilation. |
| `cz.detectors.llm` | Client invocations, prompt template binding, and `bind_tools` calls. |
| `cz.detectors.tools` | `@tool` functions, parameter schemas, docstrings, and `ToolNode` definitions. |
| `cz.manifest` | Authoritative schema definition (`v0.1.0`), deterministic sorting, serialization. |
| `cz.audit` | Observability package discovery, environment tracing checks, and telemetry coverage. |
| `cz.formatters` | Console Rich dashboards, Mermaid flowcharts, and standalone HTML visualizers. |
