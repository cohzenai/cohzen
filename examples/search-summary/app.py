"""Search & Summarize Agent using LangGraph and LangChain.

Demonstrates a clean, multi-step Question-Answering agent:
1. Takes user input - a question
2. Searches Google using a LangChain tool (@tool)
3. Invokes an LLM function with dummy responses
4. Summarizes findings into an executive response

Pure application code with zero manual decorators or manual instrumentation!
"""

from __future__ import annotations

import time
from typing import TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph


# ============================================================================
# State Definition
# ============================================================================

class QuestionAnsweringState(TypedDict):
    question: str
    search_results: str
    insights: str
    summary: str


# ============================================================================
# LangChain Tool: Google Search
# ============================================================================

@tool
def google_search(query: str) -> str:
    """Search Google for up-to-date documentation, technical articles, and benchmark data."""
    time.sleep(0.09)  # Simulate search latency
    return (
        f"Google Search Results for '{query}':\n"
        f"1. AI Reasoning Frontiers (2025): Test-time compute scaling laws and chain-of-thought verification.\n"
        f"2. DeepSeek-R1 & OpenAI o-series: Reinforcement learning without supervised warm-up triggers emergent reasoning.\n"
        f"3. Architecture shifts: Moving from raw parameter scale to inference-time search and Monte Carlo tree evaluation."
    )


# ============================================================================
# Dummy LLM Function
# ============================================================================

def dummy_llm_synthesize(prompt: str) -> str:
    """Analyze search findings and synthesize technical arguments via LLM."""
    time.sleep(0.12)  # Simulate model inference latency
    return (
        "Key Insight: Modern AI reasoning models achieve state-of-the-art benchmark accuracy "
        "not solely through parameter scaling, but by dynamically allocating compute during inference "
        "via step-by-step reflection, backtracking, and self-correction verification."
    )


# ============================================================================
# Graph Nodes
# ============================================================================

def search_node(state: QuestionAnsweringState) -> dict:
    """Search Google using the LangChain tool to gather relevant real-time context."""
    question = state.get("question", "")
    print(f"  [search_node] Querying Google for: '{question}'")

    results = google_search.invoke({"query": question})
    return {"search_results": str(results)}


def generate_insights_node(state: QuestionAnsweringState) -> dict:
    """Analyze search findings and draft key arguments via the LLM function."""
    print("  [generate_insights] Invoking LLM to analyze search context...")
    prompt = f"Question: {state['question']}\nContext: {state['search_results']}"

    insights = dummy_llm_synthesize(prompt)
    return {"insights": insights}


def summarize_node(state: QuestionAnsweringState) -> dict:
    """Synthesize gathered research and insights into a concise final summary."""
    print("  [summarize] Compiling executive response...")
    question = state.get("question", "")
    insights = state.get("insights", "")
    search_results = state.get("search_results", "")

    summary = (
        f"### Answer to: '{question}'\n\n"
        f"**Synthesis:**\n{insights}\n\n"
        f"**Source Data:**\n{search_results}"
    )
    return {"summary": summary}


# ============================================================================
# LangGraph Workflow Construction
# ============================================================================

builder = StateGraph(QuestionAnsweringState)

# Add Nodes
builder.add_node("search_google", search_node)
builder.add_node("generate_insights", generate_insights_node)
builder.add_node("summarize", summarize_node)

# Add Edges
builder.add_edge(START, "search_google")
builder.add_edge("search_google", "generate_insights")
builder.add_edge("generate_insights", "summarize")
builder.add_edge("summarize", END)

# Compile Application
app = builder.compile()
app.name = "search_summary_agent"


# ============================================================================
# Demo Runner
# ============================================================================

def run_demo() -> None:
    print("━" * 60)
    print("Running Search & Summarize Agent (LangGraph + LangChain)")
    print("━" * 60)

    sample_questions = [
        "What are the latest developments in AI reasoning models?",
        "How does test-time compute scaling improve mathematical reasoning?",
    ]

    for question in sample_questions:
        print(f"\nProcessing Question: '{question}'")
        print("─" * 60)
        result = app.invoke({"question": question})
        print("\n✔ Completed! Executive Summary:")
        print(result["summary"])
        print()

    print("━" * 60)
    print("Execution complete! View recorded executions with:")
    print("  cz runs")
    print("  cz run <execution-id>")
    print("━" * 60)


if __name__ == "__main__":
    run_demo()
