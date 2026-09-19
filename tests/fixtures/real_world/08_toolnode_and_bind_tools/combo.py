from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

@tool
def execute_sql(query: str) -> str:
    """Execute read-only SQL query."""
    return "Query executed"

tools = [execute_sql]
tool_node = ToolNode(tools)

model = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)

def assistant_agent(state):
    res = model.invoke(state["messages"])
    return {"messages": [res]}

builder = StateGraph(dict)
builder.add_node("assistant", assistant_agent)
builder.add_node("tools", tool_node)

builder.add_edge(START, "assistant")
builder.add_edge("assistant", "tools")
builder.add_edge("tools", "assistant")

app = builder.compile()
