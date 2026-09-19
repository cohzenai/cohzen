"""Sample LangGraph: Simple agent with tools and memory saver checkpointer."""

from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class AgentState(TypedDict):
    messages: List[str]

def call_model(state: AgentState):
    return {"messages": ["model response"]}

def tool_node(state: AgentState):
    return {"messages": ["tool response"]}

# Graph construction
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_edge("tools", "agent")
workflow.add_edge("agent", END)

# Compilation
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
