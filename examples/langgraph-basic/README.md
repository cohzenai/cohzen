# LangGraph Basic Example

A minimal linear workflow demonstrating:
- StateGraph with TypedDict schema (`ProcessState`)
- Input validation and transform logic nodes
- Sequential direct edges (`START -> validate -> transform -> END`)
- MemorySaver checkpointer compilation

### Scan with Cohzen:
```bash
cz scan examples/langgraph-basic
```
