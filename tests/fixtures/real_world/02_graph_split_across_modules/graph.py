from langgraph.graph import StateGraph, START, END
from .state import MultiModuleState
from .nodes import retriever_node, generator_node

builder = StateGraph(MultiModuleState)
builder.add_node("retriever", retriever_node)
builder.add_node("generator", generator_node)

builder.add_edge(START, "retriever")
builder.add_edge("retriever", "generator")
builder.add_edge("generator", END)

rag_app = builder.compile()
