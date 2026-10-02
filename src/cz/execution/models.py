"""Cohzen Execution Data Models for v0.2.

Generic runtime model for executions, spans, and events.
Spans support kind: 'graph', 'node', 'llm', 'tool', linked to static manifest entity IDs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field


def generate_short_id() -> str:
    """Generate a readable short hex ID (e.g. 'a82f91' or '91be22')."""
    return uuid.uuid4().hex[:8]


class Execution(BaseModel):
    """Execution represents a single run of an agentic graph."""
    id: str = Field(default_factory=generate_short_id, description="Unique execution ID (e.g. 'a82f91')")
    trace_id: Optional[str] = Field(default=None, description="External or distributed trace ID if available")
    manifest_version: str = Field(default="0.1.0", description="Cohzen Manifest version schema")
    graph_id: str = Field(description="Target graph ID or name (e.g. 'customer_flow', 'workflow')")
    status: str = Field(default="running", description="Status: 'running', 'completed', or 'failed'")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when execution started")
    ended_at: Optional[datetime] = Field(default=None, description="Timestamp when execution completed or failed")
    duration_ms: Optional[float] = Field(default=None, description="Total execution duration in milliseconds")
    reason: Optional[str] = Field(default=None, description="High-level goal or reason for the execution run")
    error: Optional[str] = Field(default=None, description="Error message or exception details if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata or runtime context")


class Span(BaseModel):
    """Span represents a discrete unit of work within an execution (graph, node, llm, tool)."""
    id: str = Field(default_factory=generate_short_id, description="Unique span ID")
    execution_id: str = Field(description="Associated Execution ID")
    parent_id: Optional[str] = Field(default=None, description="Parent Span ID (e.g. node_span -> llm_span)")
    entity_id: Optional[str] = Field(
        default=None,
        description="Linked entity ID from the v0.1 manifest (e.g. 'node.planner', 'tool.search', 'model.openai.gpt-4o')",
    )
    kind: str = Field(default="node", description="Span kind: 'graph', 'node', 'llm', 'tool'")
    name: str = Field(description="Readable name of the operation or entity")
    status: str = Field(default="running", description="Status: 'running', 'completed', or 'failed'")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Span start time")
    ended_at: Optional[datetime] = Field(default=None, description="Span end time")
    duration_ms: Optional[float] = Field(default=None, description="Span duration in milliseconds")
    reason: Optional[str] = Field(default=None, description="Reasoning, rationale, or explanation of why this step or decision occurred")
    input: Optional[Any] = Field(default=None, description="Input parameters, payload, or messages")
    output: Optional[Any] = Field(default=None, description="Output result, state update, or LLM response")
    error: Optional[str] = Field(default=None, description="Error message if span failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata such as token usage, model params, etc.")


class Event(BaseModel):
    """Event represents a point-in-time occurrence within an execution or span."""
    id: str = Field(default_factory=generate_short_id, description="Unique event ID")
    execution_id: str = Field(description="Associated Execution ID")
    span_id: Optional[str] = Field(default=None, description="Associated Span ID if occurred during a span")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the event")
    kind: str = Field(
        description="Event kind: 'tool_call', 'tool_result', 'stream_chunk', 'interrupt', 'checkpoint', 'error', 'retry'",
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary event data payload")
