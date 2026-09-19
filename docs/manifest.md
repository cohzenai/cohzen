# CohzenManifest v0.1 Specification

The `CohzenManifest` is the canonical, machine-readable contract defining an agentic system's architecture.

---

## Schema Overview

```json
{
  "version": "0.1.0",
  "frameworks": ["langgraph"],
  "graphs": [...],
  "nodes": [...],
  "tools": [...],
  "models": [...],
  "metadata": {...}
}
```

---

## Top-Level Fields

### 1. `graphs`
An array of discovered graph definitions (`GraphDef`):
- `id`: Stable identifier, e.g. `"graph.workflow"`
- `name`: Variable name in code, e.g. `"workflow"`, `"builder"`
- `framework`: `"langgraph"`
- `graph_class`: `"StateGraph"`, `"MessageGraph"`, or `"Graph"`
- `state_schema`: Name of the state schema class (e.g. `"AgentState"`, `"dict"`)
- `source`: File location (`file`, `line_start`, `line_end`)
- `node_ids`: List of node IDs registered in this graph
- `edges`: Directed edges and conditional branches
- `compilation`: Information on `.compile()`, checkpointer, interrupts, and stores

### 2. `nodes`
An array of registered graph nodes (`NodeDef`):
- `id`: Stable identifier, e.g. `"node.researcher"`
- `name`: Node name in graph
- `kind`: Authoritative fact: `"node"`
- `handler`: Handler function name, lambda snippet, or `ToolNode` call
- `resolution`: Symbol resolution status (`"resolved"`, `"partially_resolved"`, `"unresolved"`, `"external_import"`)
- `classification`: Optional non-authoritative heuristic:
  ```json
  "classification": {
    "role": "agent",
    "confidence": "high",
    "evidence": ["llm_invocation", "tool_binding"]
  }
  ```
- `model_ids`: IDs of models invoked by this node
- `tool_ids`: IDs of tools bound to or executed by this node

### 3. `tools`
An array of tool specifications (`ToolDef`):
- `id`: Stable identifier, e.g. `"tool.search_web"`
- `name`: Function or tool identifier
- `source`: Source location if defined in repository
- `docstring`: First line or full docstring of the tool
- `resolution`: Resolution state (`"resolved"` or `"external_import"`)

### 4. `models`
An array of LLM models and call sites (`ModelDef`):
- `id`: Stable identifier, e.g. `"model.openai.gpt-4o"`
- `provider`: `"openai"`, `"anthropic"`, `"google"`, `"groq"`, `"grok"`, `"langchain"`, `"litellm"`
- `name`: Model name if statically declared, or caller method signature
- `source`: Source location of definition or call

### 5. `metadata`
Scan execution and static analysis completeness metadata:
- `files_scanned`: Total files examined
- `parse_errors`: Files that failed Python syntax parsing
- `unresolved_symbols`: Symbols lacking local definitions
- `dynamic_constructions`: Dynamic closures / unresolvable reflection
- `external_imports`: Components imported from external libraries
- `external_packages`: List of external library package names
- `warnings`: Explicit static analysis caveats
