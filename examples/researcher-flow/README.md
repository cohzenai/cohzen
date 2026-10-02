# Deep Researcher Agent Workflow Example (Cohzen v0.2)

This example demonstrates a complete **Deep Researcher Agentic Workflow** built with LangGraph, executed with zero-cost **dummy LLM calls** and simulated research tools.

> **Zero User Action Required**: The application code in [`app.py`](file:///Users/aarora/Dev/cohzen-ai/cz/examples/researcher-flow/app.py) contains **no decorators** (`@cz.observe`), **no manual spans**, and **no `import cz`**. Running `cz init` automatically detects the architecture and enables dynamic runtime auto-instrumentation!

---

## Architecture

* **Graph Name**: `researcher_flow`
* **Nodes**:
  * `clarify_query`: Evaluates if the research query is sufficiently scoped or requires clarification.
  * `human_clarification`: Simulates human-in-the-loop (HITL) clarification response for underspecified requests.
  * `write_research_brief`: Deconstructs the research topic into targeted sub-investigation vectors.
  * `conduct_research`: Coordinates sub-researchers that execute web search, reflection (`tool_think`), and note summarization.
  * `generate_report`: Compiles findings into an executive-ready structured markdown report.
* **Routing**:
  * `START -> clarify_query`
  * `clarify_query -> [if ambiguous] -> human_clarification -> write_research_brief`
  * `clarify_query -> [if specific] -> write_research_brief`
  * `write_research_brief -> conduct_research -> generate_report -> END`
* **Zero-Friction Observability**:
  * Reasoning (`why:`) is automatically extracted from function docstrings without any manual annotations.
  * Internal LLM and tool calls are automatically detected and wrapped as child spans at runtime.

---

## Step-by-Step Walkthrough

### 1. Initialize Cohzen in this project

From the `examples/researcher-flow` directory:
```bash
cz init .
```
This generates `.cohzen/manifest.json`, sets up `.cohzen/executions.db`, and enables auto-recording via `sitecustomize.py`.

### 2. Run the Application Normally

Run directly with Python (no OpenAI API key or network required!):
```bash
python app.py
```

### 3. Statically Scan the Graph Architecture

```bash
cz scan .
```

### 4. Inspect Recorded Executions

```bash
cz runs
```

### 5. Inspect Deep Flow Trace and Reasoning

```bash
cz run <execution-id>
```

Example trace captured completely dynamically without any user code decorators:
```
Execution 227a56f1
────────────────────────────
Graph       researcher_flow
Status      ✓ completed
Duration    1.17s

START
  │
  ▼
clarify_query                   87ms
      why: Analyze input prompt to determine if user clarification is required.
  │
  ▼
dummy_llm_clarify_analysis      85ms
      why: Analyze whether the research query requires user clarification.
  │
  ▼
clarify_query                   0ms
  │
  ▼
human_clarification             0ms
      why: Simulate human-in-the-loop response for ambiguous prompts.
  │
  ▼
write_research_brief            127ms
      why: Formulate the structured research brief and identify parallel subtopics.
  │
  ▼
dummy_llm_generate_brief        125ms
      why: Generate structured research brief and subtopics.
  │
  ▼
conduct_research                785ms
      why: Execute research supervisor and sub-researchers (search, think, summarize).
  │
  ▼
tool_web_search                 90ms
      why: Simulate native web search tool.
  │
  ▼
tool_think                      55ms
      why: Simulate strategic reflection tool for research planning.
  │
  ▼
dummy_llm_summarize_research    104ms
      why: Summarize search results and reflection into structured notes.
  │
  ▼
generate_report                 153ms
      why: Compile final synthesis report from research notes.
  │
  ▼
dummy_llm_generate_report       151ms
      why: Generate final comprehensive markdown report.
  │
  ▼
END

LLM calls     6
Tool calls    6
Nodes         6
```
