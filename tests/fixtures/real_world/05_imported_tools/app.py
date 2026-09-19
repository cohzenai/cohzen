from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool

# External tool objects
tavily_tool = TavilySearchResults(max_results=3)
sql_tool = QuerySQLDataBaseTool()

tools = [tavily_tool, sql_tool]
tool_node = ToolNode(tools)

def agent(state):
    return {"messages": ["call tools"]}

builder = StateGraph(dict)
builder.add_node("agent", agent)
builder.add_node("tools", tool_node)

builder.add_edge(START, "agent")
builder.add_edge("agent", "tools")
builder.add_edge("tools", END)

app = builder.compile()
