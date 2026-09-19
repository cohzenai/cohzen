from langgraph.graph import StateGraph, START, END

# 1. Child subgraph
child_builder = StateGraph(dict)

def worker_step(state):
    return {"sub_result": "done"}

child_builder.add_node("worker", worker_step)
child_builder.add_edge(START, "worker")
child_builder.add_edge("worker", END)
child_subgraph = child_builder.compile()

# 2. Parent main workflow
parent_builder = StateGraph(dict)

def prepare_step(state):
    return {"init": True}

parent_builder.add_node("prepare", prepare_step)
parent_builder.add_node("subgraph_task", child_subgraph)

parent_builder.add_edge(START, "prepare")
parent_builder.add_edge("prepare", "subgraph_task")
parent_builder.add_edge("subgraph_task", END)

main_app = parent_builder.compile()
