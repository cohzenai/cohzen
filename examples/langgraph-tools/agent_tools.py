from typing import List
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

@tool
def search_docs(query: str) -> str:
    """Search internal documentation for relevant context."""
    return f"Results for: {query}"

@tool
def calculate_metrics(metric_id: str) -> float:
    """Compute aggregate statistical score."""
    return 42.0

tools = [search_docs, calculate_metrics]
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def assistant(state: MessagesState) -> dict:
    """LLM agent node deciding whether to invoke tools."""
    response = model.invoke(state["messages"])
    return {"messages": [response]}

tool_node = ToolNode(tools)

builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)

builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    lambda state: "tools" if state["messages"][-1].tool_calls else "finish",
    {"tools": "tools", "finish": END}
)
builder.add_edge("tools", "assistant")

app = builder.compile()
