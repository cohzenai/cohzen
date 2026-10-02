"""Deep Research Agent Workflow using LangGraph.

A clean, multi-stage researcher agent workflow:
- Clarification / Intent checking
- Research brief planning and subtopic decomposition
- Simulated web search and strategic reflection (think tool)
- Final report synthesis
- Zero-cost dummy LLM calls and tool functions (pure application code, no decorators)
"""

from __future__ import annotations

import time
from typing import List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


# ============================================================================
# State Definition
# ============================================================================

class ResearcherState(TypedDict):
    topic: str
    need_clarification: bool
    clarification_question: str
    clarified_context: str
    research_brief: str
    subtopics: List[str]
    notes: List[str]
    final_report: str


# ============================================================================
# Dummy LLM Functions (Plain Python functions)
# ============================================================================

def dummy_llm_clarify_analysis(topic: str) -> dict:
    """Analyze whether the research query requires user clarification."""
    time.sleep(0.08)
    words = topic.strip().split()
    if len(words) <= 2:
        return {
            "need_clarification": True,
            "question": f"Your query '{topic}' is broad. Would you like to focus on technical architecture, commercial adoption, or algorithmic benchmarks?",
        }
    return {
        "need_clarification": False,
        "question": "",
    }


def dummy_llm_generate_brief(topic: str, context: str = "") -> dict:
    """Generate structured research brief and subtopics."""
    time.sleep(0.12)
    augmented_topic = f"{topic} (Focus: {context})" if context else topic
    subtopics = [
        f"{augmented_topic}: Current State of the Art & Breakthroughs",
        f"{augmented_topic}: Architectural Bottlenecks & Scaling Constraints",
        f"{augmented_topic}: Industry Roadmap & 2025-2027 Projections",
    ]
    brief = (
        f"Research Objective: Comprehensive assessment of '{augmented_topic}'.\n"
        f"Key Inquiries: SOTA benchmarks, engineering challenges, and future milestones."
    )
    return {"brief": brief, "subtopics": subtopics}


def dummy_llm_summarize_research(subtopic: str, search_data: str, reflection: str) -> str:
    """Summarize search results and reflection into structured notes."""
    time.sleep(0.10)
    return (
        f"### Subtopic: {subtopic}\n"
        f"- Evidence: {search_data}\n"
        f"- Analysis: {reflection}\n"
        f"- Key Takeaway: Validated strong momentum with critical dependency on error mitigation.\n"
    )


def dummy_llm_generate_report(topic: str, brief: str, notes: List[str]) -> str:
    """Generate final comprehensive markdown report."""
    time.sleep(0.15)
    aggregated_notes = "\n".join(notes)
    return (
        f"# Deep Research Report: {topic.title()}\n\n"
        f"## Executive Summary\n"
        f"This report provides an in-depth investigation into {topic}. "
        f"Based on aggregated empirical findings, the ecosystem is rapidly maturing.\n\n"
        f"## Research Brief & Scope\n"
        f"{brief}\n\n"
        f"## Key Research Findings\n\n"
        f"{aggregated_notes}\n"
        f"## Strategic Outlook & Conclusion\n"
        f"The sector demonstrates a high compounding trajectory. Continued focus on system reliability "
        f"and standard interfaces remains the critical differentiator over the next 24 months.\n"
    )


# ============================================================================
# Dummy Tools (Plain Python functions)
# ============================================================================

def tool_web_search(query: str) -> str:
    """Simulate native web search tool."""
    time.sleep(0.09)
    return f"Indexed 4 sources for '{query}': Found high-impact peer-reviewed data and benchmarks."


def tool_think(reflection: str) -> str:
    """Simulate strategic reflection tool for research planning."""
    time.sleep(0.05)
    return f"Reflection logged: Evaluated data sufficiency ({reflection[:40]}...)"


# ============================================================================
# Graph Nodes
# ============================================================================

def clarify_query(state: ResearcherState) -> dict:
    """Analyze input prompt to determine if user clarification is required."""
    topic = state.get("topic", "")
    print(f"  [clarify_query] Assessing scope for topic: '{topic}'")

    analysis = dummy_llm_clarify_analysis(topic)
    need_clarify = analysis["need_clarification"]

    return {
        "need_clarification": need_clarify,
        "clarification_question": analysis.get("question", ""),
    }


def human_clarification(state: ResearcherState) -> dict:
    """Simulate human-in-the-loop response for ambiguous prompts."""
    question = state.get("clarification_question", "")
    print(f"  [human_clarification] Clarification requested: '{question}'")

    # Simulate resolved context from user
    clarified = "Focus on technical architecture and 2025 performance milestones."
    print(f"  [human_clarification] User provided guidance: '{clarified}'")

    return {
        "clarified_context": clarified,
        "need_clarification": False,
    }


def route_clarification(state: ResearcherState) -> Literal["human_clarification", "write_research_brief"]:
    """Conditional router based on clarification evaluation."""
    if state.get("need_clarification"):
        return "human_clarification"
    return "write_research_brief"


def write_research_brief(state: ResearcherState) -> dict:
    """Formulate the structured research brief and identify parallel subtopics."""
    topic = state.get("topic", "")
    context = state.get("clarified_context", "")
    print(f"  [write_research_brief] Decomposing topic: '{topic}'")

    plan = dummy_llm_generate_brief(topic, context)

    return {
        "research_brief": plan["brief"],
        "subtopics": plan["subtopics"],
        "notes": [],
    }


def conduct_research(state: ResearcherState) -> dict:
    """Execute research supervisor and sub-researchers (search, think, summarize)."""
    subtopics = state.get("subtopics", [])
    print(f"  [conduct_research] Executing research units across {len(subtopics)} subtopics...")

    notes: List[str] = []
    for idx, subtopic in enumerate(subtopics, 1):
        print(f"    -> Sub-researcher {idx}: '{subtopic[:45]}...'")

        # 1. Search web
        search_data = tool_web_search(subtopic)

        # 2. Reflect on findings
        reflection_thought = f"Sufficient empirical coverage obtained for {subtopic[:30]}"
        reflection_ack = tool_think(reflection_thought)

        # 3. Summarize findings into notes
        note = dummy_llm_summarize_research(subtopic, search_data, reflection_ack)
        notes.append(note)

    return {"notes": notes}


def generate_report(state: ResearcherState) -> dict:
    """Compile final synthesis report from research notes."""
    topic = state.get("topic", "")
    brief = state.get("research_brief", "")
    notes = state.get("notes", [])
    print("  [generate_report] Compiling comprehensive research report...")

    report = dummy_llm_generate_report(topic, brief, notes)

    return {"final_report": report}


# ============================================================================
# Graph Construction & Compilation
# ============================================================================

builder = StateGraph(ResearcherState)

builder.add_node("clarify_query", clarify_query)
builder.add_node("human_clarification", human_clarification)
builder.add_node("write_research_brief", write_research_brief)
builder.add_node("conduct_research", conduct_research)
builder.add_node("generate_report", generate_report)

# Edges
builder.add_edge(START, "clarify_query")
builder.add_conditional_edges(
    "clarify_query",
    route_clarification,
    {
        "human_clarification": "human_clarification",
        "write_research_brief": "write_research_brief",
    },
)
builder.add_edge("human_clarification", "write_research_brief")
builder.add_edge("write_research_brief", "conduct_research")
builder.add_edge("conduct_research", "generate_report")
builder.add_edge("generate_report", END)

app = builder.compile()
app.name = "researcher_flow"


# ============================================================================
# Interactive Demo Runner
# ============================================================================

def run_demo() -> None:
    print("━" * 60)
    print("Running Deep Researcher Agent Workflow (LangGraph)")
    print("━" * 60)

    test_cases = [
        {
            "description": "Case 1: Specific Topic (Direct Research Flow)",
            "input": {"topic": "Quantum Error Correction and fault tolerance architectures"},
        },
        {
            "description": "Case 2: Broad Topic (Triggers Clarification Flow)",
            "input": {"topic": "Quantum"},
        },
    ]

    for case in test_cases:
        print(f"\n{case['description']}")
        print("─" * 60)
        result = app.invoke(case["input"])
        print("\n✔ Research Run Completed!")
        print("Final Report Snapshot:")
        report_lines = result["final_report"].split("\n")
        print("\n".join(report_lines[:7]) + "\n...")

    print("\n" + "━" * 60)
    print("Execution complete! View recorded executions with:")
    print("  cz runs")
    print("  cz run <execution-id>")
    print("  cz run <execution-id> --verbose")
    print("━" * 60)


if __name__ == "__main__":
    run_demo()
