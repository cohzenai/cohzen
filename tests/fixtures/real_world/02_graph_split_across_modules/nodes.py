from langchain_core.tools import tool

@tool
def fetch_docs(topic: str) -> str:
    """Fetch relevant technical documentation."""
    return f"Documentation about {topic}"

def retriever_node(state):
    docs = fetch_docs(state["query"])
    return {"documents": [docs]}

def generator_node(state):
    return {"response": f"Answer based on {state['documents']}"}
