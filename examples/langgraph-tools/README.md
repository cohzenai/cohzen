# LangGraph Tools & Agent Example

Demonstrates:
- Tool definitions using `@tool` decorator (`search_docs`, `calculate_metrics`)
- Dynamic tool binding: `ChatOpenAI().bind_tools(tools)`
- Tool execution node using LangGraph's `ToolNode(tools)`
- ReAct loop routing (`assistant -> tools -> assistant`)

### Scan with Cohzen:
```bash
cz scan examples/langgraph-tools
```

### Audit Observability Coverage:
```bash
cz audit examples/langgraph-tools
```
