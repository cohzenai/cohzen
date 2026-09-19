from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

class AgentState(TypedDict):
    messages: list[str]

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Results for {query}"

model = ChatOpenAI(model="gpt-4o").bind_tools([search_web])

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
