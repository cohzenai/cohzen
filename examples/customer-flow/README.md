# Customer Flow Example (Cohzen v0.2)

This example demonstrates zero-friction LangGraph execution tracking with Cohzen.

## Architecture

* **Graph**: `customer_flow`
* **Nodes**:
  * `planner`: Decomposes incoming customer inquiry.
  * `search`: Queries customer knowledge base tool (`tool.search`).
  * `writer`: Invokes LLM (`model.openai.gpt-4o`) to draft final response.
* **Edges**: `START -> planner -> search -> writer -> END`

## Step-by-Step Walkthrough

### 1. Initialize Cohzen in this project

```bash
cz init .
```

This will:
* Statically scan the repository and output `.cohzen/manifest.json`.
* Initialize the local execution store at `.cohzen/executions.db`.
* Create `sitecustomize.py` to transparently hook into LangGraph executions without modifying application code.
* Add `.cohzen/` to `.gitignore`.

### 2. Run the application normally

```bash
python app.py
```

Cohzen automatically records the execution, graph boundaries, node transitions, tool calls, and LLM queries.

### 3. Inspect Recorded Executions

```bash
cz runs
```

Output:
```
Cohzen Executions

ID          Graph          Status    Duration    Started
a82f91      customer_flow  ✓         412ms       22:30:12
91be22      customer_flow  ✓         408ms       22:30:13
```

### 4. Inspect Deep Flow Graph & Spans

```bash
cz run <execution-id>
```

Output:
```
Execution a82f91
────────────────────────────
Graph       customer_flow
Status      ✓ completed
Duration    412ms

START
  │
  ▼
planner                         122ms
  │
  ▼
search                          85ms
  │
  ▼
writer                          195ms
  │
  ▼
llm:gpt-4o                      182ms
  │
  ▼
END

LLM calls     1
Tool calls    1
Nodes         3
```

For detailed span inputs, outputs, and entity mapping:
```bash
cz run <execution-id> --verbose
```
