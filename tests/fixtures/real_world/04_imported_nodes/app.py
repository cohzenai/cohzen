# Node functions imported from third-party or unparsed package
from external_agent_pkg import autonomous_solver, safety_guardrail
from langgraph.graph import END, START, StateGraph

builder = StateGraph(dict)
builder.add_node("solver", autonomous_solver)
builder.add_node("guardrail", safety_guardrail)

builder.add_edge(START, "solver")
builder.add_edge("solver", "guardrail")
builder.add_edge("guardrail", END)

app = builder.compile()
