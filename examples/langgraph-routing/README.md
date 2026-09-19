# LangGraph Routing Example

Demonstrates:
- Supervisor pattern coordinating multiple specialized sub-agents
- Conditional branching with named routing function (`route_decision`)
- Interrupt points on critical steps (`interrupt_before=["reviewer"]`)
- Multi-cycle feedback loop back to supervisor

### Scan with Cohzen:
```bash
cz scan examples/langgraph-routing
```

### Export Mermaid Diagram:
```bash
cz scan examples/langgraph-routing --mermaid
```
