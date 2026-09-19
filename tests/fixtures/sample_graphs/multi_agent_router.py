"""Sample LangGraph: Multi-agent system with conditional routing and human-in-the-loop interrupt."""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class RouterState(TypedDict):
    task: str
    decision: str

def supervisor_agent(state: RouterState):
    return {"decision": "code"}

def researcher_agent(state: RouterState):
    return {"task": "researched info"}

def coder_agent(state: RouterState):
    return {"task": "implemented code"}

def reviewer_agent(state: RouterState):
    return {"task": "approved"}

def route_decision(state: RouterState):
    return state.get("decision", "finish")

builder = StateGraph(RouterState)
builder.add_node("supervisor", supervisor_agent)
builder.add_node("researcher", researcher_agent)
builder.add_node("coder", coder_agent)
builder.add_node("reviewer", reviewer_agent)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_decision,
    {
        "research": "researcher",
        "code": "coder",
        "finish": END,
    }
)
builder.add_edge("researcher", "supervisor")
builder.add_edge("coder", "reviewer")
builder.add_edge("reviewer", END)

compiled_system = builder.compile(interrupt_before=["reviewer"])
