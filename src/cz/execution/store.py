"""Storage abstraction for Cohzen execution telemetry."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from cz.execution.models import Event, Execution, Span


class ExecutionStore(Protocol):
    """Protocol defining persistence operations for executions, spans, and events."""

    def create_execution(self, execution: Execution) -> None:
        """Record the start of a new execution."""
        ...

    def finish_execution(
        self,
        execution_id: str,
        status: str,
        ended_at: datetime,
        duration_ms: float,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> None:
        """Mark an execution as finished (completed or failed)."""
        ...

    def create_span(self, span: Span) -> None:
        """Record the start of a new span."""
        ...

    def finish_span(
        self,
        span_id: str,
        status: str,
        ended_at: datetime,
        duration_ms: float,
        output: Any | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> None:
        """Mark a span as finished."""
        ...

    def add_event(self, event: Event) -> None:
        """Record an event occurring within an execution or span."""
        ...

    def get_execution(self, execution_id: str) -> Execution | None:
        """Retrieve an execution by ID or short prefix match."""
        ...

    def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        """List executions ordered by started_at descending."""
        ...

    def get_spans(self, execution_id: str) -> list[Span]:
        """Retrieve all spans belonging to an execution."""
        ...

    def get_events(self, execution_id: str, span_id: str | None = None) -> list[Event]:
        """Retrieve events belonging to an execution (and optionally a specific span)."""
        ...
