"""SQLite implementation of the ExecutionStore."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cz.execution.models import Event, Execution, Span
from cz.execution.processor import DataProcessor, RedactionProcessor
from cz.execution.store import ExecutionStore


def _json_dumps(val: Any) -> str:
    """Safe JSON dump supporting arbitrary types and datetimes."""
    return json.dumps(val, default=str)


def _parse_iso(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        return None


class RetentionPolicy:
    """Limits for locally persisted executions. ``None`` disables one limit."""

    def __init__(
        self,
        max_payload_bytes: int | None = 65_536,
        max_runs: int | None = 1_000,
        max_age_days: int | None = 30,
    ) -> None:
        for name, value in {
            "max_payload_bytes": max_payload_bytes,
            "max_runs": max_runs,
            "max_age_days": max_age_days,
        }.items():
            if value is not None and value < 1:
                raise ValueError(f"{name} must be positive or None")
        self.max_payload_bytes = max_payload_bytes
        self.max_runs = max_runs
        self.max_age_days = max_age_days

    @classmethod
    def from_environment(cls) -> "RetentionPolicy":
        """Read optional ``COHZEN_MAX_*`` overrides for the default store."""

        def read(name: str, default: int) -> int | None:
            raw = os.environ.get(name)
            if raw is None:
                return default
            if raw.lower() in {"none", "off", "disabled"}:
                return None
            return int(raw)

        return cls(
            max_payload_bytes=read("COHZEN_MAX_PAYLOAD_BYTES", 65_536),
            max_runs=read("COHZEN_MAX_RUNS", 1_000),
            max_age_days=read("COHZEN_MAX_AGE_DAYS", 30),
        )
class SQLiteExecutionStore(ExecutionStore):
    """Local SQLite-backed persistent execution and span store."""

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS executions (
        id TEXT PRIMARY KEY,
        trace_id TEXT,
        manifest_version TEXT NOT NULL,
        graph_id TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_ms REAL,
        reason TEXT,
        error TEXT,
        metadata TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS spans (
        id TEXT PRIMARY KEY,
        execution_id TEXT NOT NULL,
        parent_id TEXT,
        entity_id TEXT,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_ms REAL,
        reason TEXT,
        input TEXT,
        output TEXT,
        error TEXT,
        metadata TEXT NOT NULL,
        FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        execution_id TEXT NOT NULL,
        span_id TEXT,
        timestamp TEXT NOT NULL,
        kind TEXT NOT NULL,
        data TEXT NOT NULL,
        FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_executions_started ON executions (started_at DESC);
    CREATE INDEX IF NOT EXISTS idx_spans_execution ON spans (execution_id);
    CREATE INDEX IF NOT EXISTS idx_spans_parent ON spans (parent_id);
    CREATE INDEX IF NOT EXISTS idx_events_execution ON events (execution_id);
    """

    def __init__(
        self,
        db_path: Path | str = ".cohzen/executions.db",
        processor: DataProcessor | None = None,
        retention: RetentionPolicy | None = None,
    ):
        self.db_path = Path(db_path)
        self.retention = retention or RetentionPolicy.from_environment()
        self.processor: DataProcessor = processor or RedactionProcessor(
            max_payload_bytes=self.retention.max_payload_bytes
        )
        self._lock = threading.RLock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create parent directory and initialize tables and pragmas."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(self.SCHEMA_SQL)
            # Automatic schema migration for existing databases
            try:
                conn.execute("ALTER TABLE executions ADD COLUMN reason TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE spans ADD COLUMN reason TEXT;")
            except sqlite3.OperationalError:
                pass

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_execution(self, execution: Execution) -> None:
        metadata = self.processor.process(execution.metadata)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO executions (
                    id, trace_id, manifest_version, graph_id, status,
                    started_at, ended_at, duration_ms, reason, error, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.id,
                    execution.trace_id,
                    execution.manifest_version,
                    execution.graph_id,
                    execution.status,
                    execution.started_at.isoformat(),
                    execution.ended_at.isoformat() if execution.ended_at else None,
                    execution.duration_ms,
                    self.processor.process(execution.reason),
                    self.processor.process(execution.error),
                    _json_dumps(metadata),
                ),
            )
            self._apply_retention(conn)

    def _apply_retention(self, conn: sqlite3.Connection) -> None:
        """Remove expired executions and their dependent spans/events."""
        if self.retention.max_age_days is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - self.retention.max_age_days * 86_400
            cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
            conn.execute("DELETE FROM executions WHERE started_at < ?", (cutoff_iso,))
        if self.retention.max_runs is not None:
            conn.execute(
                """
                DELETE FROM executions WHERE id IN (
                    SELECT id FROM executions ORDER BY started_at DESC, id DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (self.retention.max_runs,),
            )

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
        with self._lock, self._connect() as conn:
            if metadata is not None and reason is not None:
                processed_meta = self.processor.process(metadata)
                conn.execute(
                    """
                    UPDATE executions
                    SET status = ?, ended_at = ?, duration_ms = ?, error = ?, metadata = ?, reason = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        self.processor.process(error),
                        _json_dumps(processed_meta),
                        self.processor.process(reason),
                        execution_id,
                    ),
                )
            elif metadata is not None:
                processed_meta = self.processor.process(metadata)
                conn.execute(
                    """
                    UPDATE executions
                    SET status = ?, ended_at = ?, duration_ms = ?, error = ?, metadata = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        self.processor.process(error),
                        _json_dumps(processed_meta),
                        execution_id,
                    ),
                )
            elif reason is not None:
                conn.execute(
                    """
                    UPDATE executions
                    SET status = ?, ended_at = ?, duration_ms = ?, error = ?, reason = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        self.processor.process(error),
                        self.processor.process(reason),
                        execution_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE executions
                    SET status = ?, ended_at = ?, duration_ms = ?, error = ?
                    WHERE id = ?
                    """,
                    (status, ended_at.isoformat(), duration_ms, self.processor.process(error), execution_id),
                )

    def create_span(self, span: Span) -> None:
        processed_input = self.processor.process(span.input)
        processed_metadata = self.processor.process(span.metadata)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO spans (
                    id, execution_id, parent_id, entity_id, kind, name, status,
                    started_at, ended_at, duration_ms, reason, input, output, error, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.id,
                    span.execution_id,
                    span.parent_id,
                    span.entity_id,
                    span.kind,
                    span.name,
                    span.status,
                    span.started_at.isoformat(),
                    span.ended_at.isoformat() if span.ended_at else None,
                    span.duration_ms,
                    self.processor.process(span.reason),
                    _json_dumps(processed_input) if processed_input is not None else None,
                    None,
                    self.processor.process(span.error),
                    _json_dumps(processed_metadata),
                ),
            )

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
        processed_output = self.processor.process(output)
        with self._lock, self._connect() as conn:
            if metadata is not None and reason is not None:
                processed_meta = self.processor.process(metadata)
                conn.execute(
                    """
                    UPDATE spans
                    SET status = ?, ended_at = ?, duration_ms = ?, output = ?, error = ?, metadata = ?, reason = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        _json_dumps(processed_output) if processed_output is not None else None,
                        self.processor.process(error),
                        _json_dumps(processed_meta),
                        self.processor.process(reason),
                        span_id,
                    ),
                )
            elif metadata is not None:
                processed_meta = self.processor.process(metadata)
                conn.execute(
                    """
                    UPDATE spans
                    SET status = ?, ended_at = ?, duration_ms = ?, output = ?, error = ?, metadata = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        _json_dumps(processed_output) if processed_output is not None else None,
                        self.processor.process(error),
                        _json_dumps(processed_meta),
                        span_id,
                    ),
                )
            elif reason is not None:
                conn.execute(
                    """
                    UPDATE spans
                    SET status = ?, ended_at = ?, duration_ms = ?, output = ?, error = ?, reason = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        _json_dumps(processed_output) if processed_output is not None else None,
                        self.processor.process(error),
                        self.processor.process(reason),
                        span_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE spans
                    SET status = ?, ended_at = ?, duration_ms = ?, output = ?, error = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        ended_at.isoformat(),
                        duration_ms,
                        _json_dumps(processed_output) if processed_output is not None else None,
                        self.processor.process(error),
                        span_id,
                    ),
                )

    def add_event(self, event: Event) -> None:
        processed_data = self.processor.process(event.data)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (id, execution_id, span_id, timestamp, kind, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.execution_id,
                    event.span_id,
                    event.timestamp.isoformat(),
                    event.kind,
                    _json_dumps(processed_data),
                ),
            )

    def get_execution(self, execution_id: str) -> Execution | None:
        with self._lock, self._connect() as conn:
            # First try exact match
            cur = conn.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cur.fetchone()
            if not row:
                # Fallback to prefix match
                cur = conn.execute(
                    "SELECT * FROM executions WHERE id LIKE ? || '%' ORDER BY started_at DESC LIMIT 1",
                    (execution_id,),
                )
                row = cur.fetchone()

            if not row:
                return None

            return self._row_to_execution(row)

    def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM executions ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cur.fetchall()
            return [self._row_to_execution(r) for r in rows]

    def get_spans(self, execution_id: str) -> list[Span]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM spans WHERE execution_id = ? ORDER BY started_at ASC",
                (execution_id,),
            )
            rows = cur.fetchall()
            return [self._row_to_span(r) for r in rows]

    def get_events(self, execution_id: str, span_id: str | None = None) -> list[Event]:
        with self._lock, self._connect() as conn:
            if span_id:
                cur = conn.execute(
                    "SELECT * FROM events WHERE execution_id = ? AND span_id = ? ORDER BY timestamp ASC",
                    (execution_id, span_id),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM events WHERE execution_id = ? ORDER BY timestamp ASC",
                    (execution_id,),
                )
            rows = cur.fetchall()
            return [self._row_to_event(r) for r in rows]

    def _row_to_execution(self, row: sqlite3.Row) -> Execution:
        return Execution(
            id=row["id"],
            trace_id=row["trace_id"],
            manifest_version=row["manifest_version"],
            graph_id=row["graph_id"],
            status=row["status"],
            started_at=_parse_iso(row["started_at"]) or datetime.now(timezone.utc),
            ended_at=_parse_iso(row["ended_at"]),
            duration_ms=row["duration_ms"],
            reason=row["reason"] if "reason" in row.keys() else None,
            error=row["error"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_span(self, row: sqlite3.Row) -> Span:
        return Span(
            id=row["id"],
            execution_id=row["execution_id"],
            parent_id=row["parent_id"],
            entity_id=row["entity_id"],
            kind=row["kind"],
            name=row["name"],
            status=row["status"],
            started_at=_parse_iso(row["started_at"]) or datetime.now(timezone.utc),
            ended_at=_parse_iso(row["ended_at"]),
            duration_ms=row["duration_ms"],
            reason=row["reason"] if "reason" in row.keys() else None,
            input=json.loads(row["input"]) if row["input"] else None,
            output=json.loads(row["output"]) if row["output"] else None,
            error=row["error"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            execution_id=row["execution_id"],
            span_id=row["span_id"],
            timestamp=_parse_iso(row["timestamp"]) or datetime.now(timezone.utc),
            kind=row["kind"],
            data=json.loads(row["data"]) if row["data"] else {},
        )
