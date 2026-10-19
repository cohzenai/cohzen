from langgraph.graph import END, START, StateGraph

from .nodes import generator_node, retriever_node
from .state import MultiModuleState

builder = StateGraph(MultiModuleState)
builder.add_node("retriever", retriever_node)
builder.add_node("generator", generator_node)

builder.add_edge(START, "retriever")
builder.add_edge("retriever", "generator")
builder.add_edge("generator", END)

rag_app = builder.compile()
