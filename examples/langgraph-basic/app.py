from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class ProcessState(TypedDict):
    input_text: str
    processed_text: str
    step_count: int

def validate_input(state: ProcessState) -> dict:
    """Validate incoming query."""
    return {"step_count": state.get("step_count", 0) + 1}

def transform_data(state: ProcessState) -> dict:
    """Format and normalize text."""
    text = state.get("input_text", "").strip()
    return {"processed_text": text.upper()}

# Build workflow
builder = StateGraph(ProcessState)
builder.add_node("validate", validate_input)
builder.add_node("transform", transform_data)

builder.add_edge(START, "validate")
builder.add_edge("validate", "transform")
builder.add_edge("transform", END)

checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)
