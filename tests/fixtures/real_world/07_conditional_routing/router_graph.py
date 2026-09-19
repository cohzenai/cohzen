from langgraph.graph import StateGraph, START, END

def router_fn(state: dict) -> str:
    val = state.get("priority", "medium")
    if val == "urgent":
        return "escalate"
    elif val == "low":
        return "archive"
    return "standard"

def standard_handler(state):
    return {"status": "normal"}

def escalate_handler(state):
    return {"status": "escalated"}

def archive_handler(state):
    return {"status": "archived"}

wf = StateGraph(dict)
wf.add_node("standard", standard_handler)
wf.add_node("escalate", escalate_handler)
wf.add_node("archive", archive_handler)

wf.add_conditional_edges(
    START,
    router_fn,
    {
        "standard": "standard",
        "escalate": "escalate",
        "archive": "archive",
    }
)

wf.add_edge("standard", END)
wf.add_edge("escalate", END)
wf.add_edge("archive", END)

app = wf.compile()
