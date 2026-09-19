from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class QueryState(TypedDict):
    question: str
    answer: str

def search_index(state: QueryState):
    return {"answer": "Found context"}

def synthesize(state: QueryState):
    return {"answer": f"Final: {state['answer']}"}

query_builder = StateGraph(QueryState)
query_builder.add_node("search", search_index)
query_builder.add_node("synthesize", synthesize)
query_builder.add_edge(START, "search")
query_builder.add_edge("search", "synthesize")
query_builder.add_edge("synthesize", END)

query_app = query_builder.compile()
