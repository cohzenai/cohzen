"""Runtime context and span hierarchy management using Python contextvars."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
import functools
import inspect
from pathlib import Path
import time
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, cast

from cz.execution.models import Execution, Span
from cz.execution.sqlite import SQLiteExecutionStore
from cz.execution.store import ExecutionStore

F = TypeVar("F", bound=Callable[..., Any])

_current_execution: ContextVar[Optional[Execution]] = ContextVar("cz_current_execution", default=None)
_current_span: ContextVar[Optional[Span]] = ContextVar("cz_current_span", default=None)
_current_store: ContextVar[Optional[ExecutionStore]] = ContextVar("cz_current_store", default=None)

_global_store: Optional[ExecutionStore] = None


def _find_db_path() -> Path:
    """Find .cohzen/executions.db traversing parent directories up to project root."""
    curr = Path.cwd().resolve()
    for directory in [curr, *curr.parents]:
        candidate = directory / ".cohzen" / "executions.db"
        if candidate.is_file():
            return candidate
        manifest_candidate = directory / ".cohzen" / "manifest.json"
        if manifest_candidate.is_file():
            return directory / ".cohzen" / "executions.db"
    return Path(".cohzen/executions.db")


def get_global_store() -> ExecutionStore:
    """Return the global execution store, initializing a default SQLite store if none set."""
    global _global_store
    if _global_store is None:
        db_path = _find_db_path()
        _global_store = SQLiteExecutionStore(db_path=db_path)
    return _global_store


def set_global_store(store: ExecutionStore) -> None:
    """Explicitly configure the global execution store."""
    global _global_store
    _global_store = store


def get_current_store() -> ExecutionStore:
    """Return the context-active or global store."""
    store = _current_store.get()
    return store if store is not None else get_global_store()


def get_current_execution() -> Optional[Execution]:
    """Return the active execution from contextvars."""
    return _current_execution.get()


def get_current_span() -> Optional[Span]:
    """Return the active span from contextvars."""
    return _current_span.get()


@contextmanager
def execution_scope(
    graph_id: str,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    store: Optional[ExecutionStore] = None,
    manifest_version: str = "0.1.0",
    reason: Optional[str] = None,
) -> Generator[Execution, None, None]:
    """Context manager establishing an Execution boundary."""
    active_store = store or get_current_store()
    execution = Execution(
        graph_id=graph_id,
        trace_id=trace_id,
        manifest_version=manifest_version,
        metadata=metadata or {},
        status="running",
        reason=reason,
    )
    active_store.create_execution(execution)

    exec_token = _current_execution.set(execution)
    store_token = _current_store.set(active_store)
    start_mono = time.monotonic()
    status = "completed"
    error_msg: Optional[str] = None

    try:
        yield execution
    except Exception as exc:
        status = "failed"
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        raise
    finally:
        duration_ms = round((time.monotonic() - start_mono) * 1000.0, 2)
        ended_at = datetime.now(timezone.utc)
        execution.status = status
        execution.ended_at = ended_at
        execution.duration_ms = duration_ms
        execution.error = error_msg
        active_store.finish_execution(
            execution_id=execution.id,
            status=status,
            ended_at=ended_at,
            duration_ms=duration_ms,
            error=error_msg,
            reason=execution.reason,
        )
        _current_execution.reset(exec_token)
        _current_store.reset(store_token)


@contextmanager
def span_scope(
    name: str,
    kind: str = "node",
    entity_id: Optional[str] = None,
    input: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    execution_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Context manager establishing a Span boundary, nesting under any current active span."""
    active_store = get_current_store()
    current_exec = get_current_execution()

    # Determine execution ID
    exec_id = execution_id or (current_exec.id if current_exec else None)

    # If no execution active, create an auto top-level execution for this span
    auto_exec_scope = None
    if not exec_id:
        auto_exec_scope = execution_scope(graph_id=name)
        auto_exec = auto_exec_scope.__enter__()
        exec_id = auto_exec.id

    parent_span = get_current_span()
    parent_id = parent_span.id if parent_span else None

    span = Span(
        execution_id=exec_id,
        parent_id=parent_id,
        entity_id=entity_id,
        kind=kind,
        name=name,
        input=input,
        metadata=metadata or {},
        status="running",
        reason=reason,
    )
    active_store.create_span(span)
    span_token = _current_span.set(span)
    start_mono = time.monotonic()
    status = "completed"
    error_msg: Optional[str] = None

    try:
        yield span
    except Exception as exc:
        status = "failed"
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        span.error = error_msg
        raise
    finally:
        duration_ms = round((time.monotonic() - start_mono) * 1000.0, 2)
        ended_at = datetime.now(timezone.utc)
        span.status = status
        span.ended_at = ended_at
        span.duration_ms = duration_ms
        active_store.finish_span(
            span_id=span.id,
            status=status,
            ended_at=ended_at,
            duration_ms=duration_ms,
            output=span.output,
            error=error_msg,
            metadata=span.metadata,
            reason=span.reason,
        )
        _current_span.reset(span_token)
        if auto_exec_scope:
            auto_exec_scope.__exit__(None, None, None)


def record_reason(text: str) -> None:
    """Record reasoning, rationale, or why a decision was made in the current span."""
    span = get_current_span()
    if span:
        span.reason = text
        active_store = get_current_store()
        from cz.execution.models import Event
        active_store.add_event(
            Event(
                execution_id=span.execution_id,
                span_id=span.id,
                kind="reasoning",
                data={"reason": text},
            )
        )


def observe(
    name: Optional[str] = None,
    kind: str = "node",
    entity_id: Optional[str] = None,
    reason: Optional[str | Callable[..., str]] = None,
) -> Callable[[F], F]:
    """Decorator to explicitly instrument a custom function or node (escape hatch)."""

    def decorator(fn: F) -> F:
        span_name = name or fn.__name__

        def _resolve_reason(args: tuple, kwargs: dict) -> Optional[str]:
            if callable(reason):
                try:
                    return reason(*args, **kwargs)
                except Exception:
                    return None
            return reason

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                input_data = {"args": args, "kwargs": kwargs} if args or kwargs else None
                computed_reason = _resolve_reason(args, kwargs)
                with span_scope(
                    name=span_name, kind=kind, entity_id=entity_id, input=input_data, reason=computed_reason
                ) as s:
                    res = await fn(*args, **kwargs)
                    s.output = res
                    if isinstance(res, dict) and not s.reason:
                        s.reason = res.get("reason") or res.get("rationale") or res.get("thought")
                    return res
            return cast(F, async_wrapper)
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                input_data = {"args": args, "kwargs": kwargs} if args or kwargs else None
                computed_reason = _resolve_reason(args, kwargs)
                with span_scope(
                    name=span_name, kind=kind, entity_id=entity_id, input=input_data, reason=computed_reason
                ) as s:
                    res = fn(*args, **kwargs)
                    s.output = res
                    if isinstance(res, dict) and not s.reason:
                        s.reason = res.get("reason") or res.get("rationale") or res.get("thought")
                    return res
            return cast(F, sync_wrapper)

    return decorator
