"""Customer Support Agent Workflow using LangGraph and Cohzen.

Demonstrates multi-node LangGraph execution with Tool and LLM tracking,
including capturing the "why" / reasoning behind every step and decision.
"""

from __future__ import annotations

import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
import cz


class CustomerState(TypedDict):
    customer_id: str
    inquiry: str
    plan: str
    search_results: str
    response: str


def planner(state: CustomerState) -> dict:
    """Analyze the customer inquiry and devise an action plan."""
    inquiry = state.get("inquiry", "")
    print(f"  [planner] Analyzing inquiry: '{inquiry}'")
    time.sleep(0.12)  # Simulate planning latency

    # Record the reasoning for this node
    cz.reason(f"Classified inquiry '{inquiry[:30]}...'; determined knowledge base retrieval is needed.")
    return {"plan": f"Search knowledge base for: {inquiry}"}


@cz.observe(
    name="search",
    kind="tool",
    entity_id="tool.search",
    reason=lambda query: f"Querying internal support knowledge base for: {query[:45]}",
)
def search_knowledge_base(query: str) -> str:
    """Simulate tool lookup against support database."""
    time.sleep(0.08)  # Simulate tool call latency
    return f"KnowledgeBase: Standard policy found for query '{query}'"


def search(state: CustomerState) -> dict:
    """Node executing knowledge base lookup tool."""
    plan = state.get("plan", "")
    print(f"  [search] Querying knowledge base based on plan: {plan}")

    # Record the why reason for executing this node
    cz.reason("Executing policy search tool to resolve customer request with official procedures.")
    results = search_knowledge_base(plan)
    return {"search_results": results}


@cz.observe(
    name="llm:gpt-4o",
    kind="llm",
    entity_id="model.openai.gpt-4o",
    reason="Formulating polite, professional customer response using retrieved knowledge base context.",
)
def call_llm(prompt: str) -> str:
    """Simulate LLM generation call."""
    time.sleep(0.18)  # Simulate model inference latency
    return "Thank you for reaching out! We reviewed your inquiry and applied our standard resolution policy."


def writer(state: CustomerState) -> dict:
    """Draft final polished response to the customer."""
    print("  [writer] Generating response via LLM...")

    # Record the why reason for drafting the response
    cz.reason("Synthesizing final verified customer communication with resolution details.")
    prompt = f"Plan: {state['plan']}\nResults: {state['search_results']}"
    llm_output = call_llm(prompt)
    return {"response": llm_output}


# Build LangGraph StateGraph
builder = StateGraph(CustomerState)
builder.add_node("planner", planner)
builder.add_node("search", search)
builder.add_node("writer", writer)

builder.add_edge(START, "planner")
builder.add_edge("planner", "search")
builder.add_edge("search", "writer")
builder.add_edge("writer", END)

# Compile application
app = builder.compile()
app.name = "customer_flow"


def run_demo() -> None:
    print("━" * 50)
    print("Running Customer Support Workflow (LangGraph)...")
    print("━" * 50)

    sample_inquiries = [
        {"customer_id": "cust_4821", "inquiry": "How do I upgrade to enterprise tier?"},
        {"customer_id": "cust_9103", "inquiry": "Where can I download my invoice for September?"},
    ]

    for item in sample_inquiries:
        print(f"\nProcessing request for {item['customer_id']}...")
        result = app.invoke(item)
        print(f"✔ Completed. Response: {result['response']}")

    print("\n" + "━" * 50)
    print("Execution complete! View recorded executions with:")
    print("  cz runs")
    print("  cz run <execution-id>")
    print("━" * 50)


if __name__ == "__main__":
    run_demo()
