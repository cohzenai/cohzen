from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class AgentTeamState(TypedDict):
    task: str
    next_agent: Literal["researcher", "coder", "reviewer", "finish"]
    output: str

def supervisor(state: AgentTeamState) -> dict:
    """Multi-agent supervisor delegating tasks to specialists."""
    return {"next_agent": "researcher"}

def researcher(state: AgentTeamState) -> dict:
    """Specialist gathering facts."""
    return {"output": "research findings"}

def coder(state: AgentTeamState) -> dict:
    """Specialist writing implementation."""
    return {"output": "def solve(): pass"}

def reviewer(state: AgentTeamState) -> dict:
    """Specialist auditing quality before final completion."""
    return {"output": "approved"}

def route_decision(state: AgentTeamState) -> str:
    return state.get("next_agent", "finish")

builder = StateGraph(AgentTeamState)
builder.add_node("supervisor", supervisor)
builder.add_node("researcher", researcher)
builder.add_node("coder", coder)
builder.add_node("reviewer", reviewer)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_decision,
    {
        "researcher": "researcher",
        "code": "coder",
        "finish": "reviewer"
    }
)
builder.add_edge("researcher", "supervisor")
builder.add_edge("coder", "reviewer")
builder.add_edge("reviewer", END)

workflow = builder.compile(interrupt_before=["reviewer"])
