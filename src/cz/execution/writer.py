"""Bounded asynchronous execution-store writer for always-on capture."""

from __future__ import annotations

import copy
import os
import queue
import threading
import time
from datetime import datetime
from typing import Any, Callable

from cz.execution.models import Event, Execution, Span
from cz.execution.processor import PayloadLimiter
from cz.execution.store import ExecutionStore


class AsyncExecutionStore(ExecutionStore):
    """Queue writes off the application's execution path and recover after fork."""

    def __init__(self, store: ExecutionStore, max_payload_bytes: int | None = 65_536, max_queue_size: int = 10_000):
        self.store = store
        self.limiter = PayloadLimiter(max_payload_bytes)
        self.max_queue_size = max_queue_size
        self._pid = os.getpid()
        self._queue: queue.Queue[tuple[Callable[..., None], tuple[Any, ...], dict[str, Any]] | None] = queue.Queue(
            max_queue_size
        )
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._start()

    def _start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="cohzen-writer", daemon=True)
        self._thread.start()

    def _ensure_process(self) -> None:
        if self._pid != os.getpid():
            self._pid = os.getpid()
            self._queue = queue.Queue(self.max_queue_size)
            self._thread = None
            self._start()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            method, args, kwargs = item
            try:
                method(*args, **kwargs)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def _snapshot(self, value: Any) -> Any:
        try:
            return self.limiter.process(copy.deepcopy(value))
        except Exception:
            return self.limiter.process(str(value))

    def _enqueue(self, method: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        self._ensure_process()
        try:
            self._queue.put_nowait((method, args, kwargs))
        except queue.Full:
            pass

    def create_execution(self, execution: Execution) -> None:
        copied = execution.model_copy(deep=True)
        copied.metadata = self._snapshot(copied.metadata)
        copied.reason = self._snapshot(copied.reason)
        copied.error = self._snapshot(copied.error)
        self._enqueue(self.store.create_execution, copied)

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
        self._enqueue(
            self.store.finish_execution,
            execution_id,
            status,
            ended_at,
            duration_ms,
            self._snapshot(error),
            self._snapshot(metadata),
            self._snapshot(reason),
        )

    def create_span(self, span: Span) -> None:
        copied = span.model_copy(deep=True)
        copied.input = self._snapshot(copied.input)
        copied.output = self._snapshot(copied.output)
        copied.metadata = self._snapshot(copied.metadata)
        copied.reason = self._snapshot(copied.reason)
        copied.error = self._snapshot(copied.error)
        self._enqueue(self.store.create_span, copied)

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
        self._enqueue(
            self.store.finish_span,
            span_id,
            status,
            ended_at,
            duration_ms,
            self._snapshot(output),
            self._snapshot(error),
            self._snapshot(metadata),
            self._snapshot(reason),
        )

    def add_event(self, event: Event) -> None:
        copied = event.model_copy(deep=True)
        copied.data = self._snapshot(copied.data)
        self._enqueue(self.store.add_event, copied)

    def flush(self, timeout: float = 1.0) -> bool:
        self._ensure_process()
        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.005)
        return self._queue.unfinished_tasks == 0

    def get_execution(self, execution_id: str) -> Execution | None:
        self.flush()
        return self.store.get_execution(execution_id)

    def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        self.flush()
        return self.store.list_executions(limit, offset)

    def get_spans(self, execution_id: str) -> list[Span]:
        self.flush()
        return self.store.get_spans(execution_id)

    def get_events(self, execution_id: str, span_id: str | None = None) -> list[Event]:
        self.flush()
        return self.store.get_events(execution_id, span_id)
