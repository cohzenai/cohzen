from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END

class IngestState(TypedDict):
    raw_files: List[str]
    processed_count: int

def parse_files(state: IngestState):
    return {"processed_count": len(state["raw_files"])}

def embed_chunks(state: IngestState):
    return {"processed_count": state["processed_count"]}

ingest_builder = StateGraph(IngestState)
ingest_builder.add_node("parse", parse_files)
ingest_builder.add_node("embed", embed_chunks)
ingest_builder.add_edge(START, "parse")
ingest_builder.add_edge("parse", "embed")
ingest_builder.add_edge("embed", END)

ingest_app = ingest_builder.compile()
