# Search & Summarize Agent (Cohzen v0.2)

This example demonstrates a Question-Answering agent that:
1. **Takes user input** - a question
2. **Searches on Google** via a LangChain tool (`@tool def google_search`)
3. **Invokes an LLM function** with dummy responses (`dummy_llm_synthesize`)
4. **Summarizes findings** in an executive response node (`summarize`)

> **Zero User Action Required**: The application code contains **no decorators** (`@cz.observe`), **no manual spans**, and **no `import cz`**. Running `cz init` automatically discovers the architecture and dynamically instruments tools, LLM functions, and nodes at runtime.

---

## Architecture

* **Graph Name**: `search_summary_agent`
* **Nodes**:
  * `search_google`: Executes the `google_search` LangChain tool to gather web context.
  * `generate_insights`: Invokes `dummy_llm_synthesize` to generate technical analysis.
  * `summarize`: Formulates the final synthesized response answering the user's question.
* **Topology**:
  `START -> search_google -> generate_insights -> summarize -> END`

---

## Step-by-Step Walkthrough

### 1. Initialize Cohzen in this project

```bash
cd /Users/aarora/Dev/cohzen-ai/cz/examples/search-summary
cz init .
```

### 2. Run the Agent Normally

```bash
python app.py
```

### 3. Inspect Recorded Executions

```bash
cz runs
```

### 4. Inspect Deep Flow Trace & Reasoning

```bash
cz run <execution-id>
```
