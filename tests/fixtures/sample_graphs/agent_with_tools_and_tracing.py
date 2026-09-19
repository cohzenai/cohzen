"""Sample LangGraph: Agent with tool binding, ToolNode, prompt, and LangSmith tracing."""

from typing import TypedDict, List
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langsmith import traceable


class MessagesState(TypedDict):
    messages: List[str]


@tool
def search_web(query: str) -> str:
    """Search Google for up-to-date web results."""
    return f"Search results for: {query}"


@tool
@traceable(name="calculate_math")
def calculate_math(expression: str) -> str:
    """Safely calculate mathematical equations."""
    return "42"


# Tools list
tools = [search_web, calculate_math]

# Prompts
system_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research assistant with access to tools."),
    ("placeholder", "{messages}"),
])


@traceable(name="research_agent")
def researcher_agent(state: MessagesState):
    """Primary researcher agent that calls LLM with bound tools."""
    messages = state["messages"]
    # Simulated model with bound tools
    model = None
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def router(state: MessagesState):
    return "tools"


# Graph builder
graph_builder = StateGraph(MessagesState)

graph_builder.add_node("researcher", researcher_agent)
graph_builder.add_node("tools", ToolNode(tools))

graph_builder.add_edge(START, "researcher")
graph_builder.add_conditional_edges(
    "researcher",
    router,
    {"tools": "tools", "finish": END},
)
graph_builder.add_edge("tools", "researcher")

app = graph_builder.compile()
