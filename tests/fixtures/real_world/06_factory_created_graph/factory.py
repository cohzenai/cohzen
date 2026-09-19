from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

def create_customer_support_graph(db_path: str = ":memory:"):
    """Factory function constructing support workflow."""
    builder = StateGraph(dict)

    def triage_step(state):
        return {"category": "billing"}

    def handle_billing(state):
        return {"status": "resolved"}

    builder.add_node("triage", triage_step)
    builder.add_node("billing", handle_billing)

    builder.add_edge(START, "triage")
    builder.add_edge("triage", "billing")
    builder.add_edge("billing", END)

    memory = SqliteSaver.from_conn_string(db_path)
    return builder.compile(checkpointer=memory, interrupt_before=["billing"])
