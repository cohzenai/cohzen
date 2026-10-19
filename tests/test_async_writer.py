"""Tests for asynchronous, fork-safe local runtime persistence."""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from cz.execution.models import Execution
from cz.execution.sqlite import SQLiteExecutionStore
from cz.execution.writer import AsyncExecutionStore


def _write_process(db_path: str, execution_id: str) -> None:
    store = AsyncExecutionStore(SQLiteExecutionStore(db_path))
    store.create_execution(Execution(id=execution_id, graph_id="flow", metadata={"token": "secret"}))
    assert store.flush(2)


def test_async_writer_flushes_redacted_snapshots(tmp_path: Path):
    db_path = tmp_path / "async.db"
    store = AsyncExecutionStore(SQLiteExecutionStore(db_path), max_payload_bytes=100)
    store.create_execution(Execution(id="async", graph_id="flow", metadata={"email": "person@example.com"}))
    assert store.flush(1)
    assert store.get_execution("async").metadata["email"] == "[REDACTED]"


def test_async_writer_is_safe_for_two_processes(tmp_path: Path):
    db_path = str(tmp_path / "multi.db")
    processes = [multiprocessing.Process(target=_write_process, args=(db_path, f"run-{index}")) for index in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(5)
        assert process.exitcode == 0
    assert len(SQLiteExecutionStore(db_path).list_executions()) == 2


def test_async_writer_flush_bounded_timeout(tmp_path: Path):
    import time
    from unittest.mock import MagicMock

    mock_underlying = MagicMock()

    def slow_create(*args, **kwargs):
        time.sleep(0.5)

    mock_underlying.create_execution.side_effect = slow_create

    store = AsyncExecutionStore(mock_underlying)
    store.create_execution(Execution(id="slow_run", graph_id="slow_flow"))

    t0 = time.monotonic()
    # Flushes with a strict 0.05s timeout
    flushed = store.flush(timeout=0.05)
    duration = time.monotonic() - t0

    assert flushed is False
    # Verified to return promptly within a bounded duration, never hanging indefinitely
    assert duration < 0.25


def test_atexit_flushing_in_subprocess(tmp_path: Path):
    import subprocess
    import sys

    db_path = tmp_path / "atexit_subp.db"
    script = tmp_path / "run_and_exit.py"
    script.write_text(
        f"""
from pathlib import Path
from cz.execution.models import Execution
from cz.execution.sqlite import SQLiteExecutionStore
from cz.execution.instrumentation import install

store = SQLiteExecutionStore(Path(r"{db_path}"))
install(store=store)

# Enqueue an execution via context or store; atexit handler flushes it on process exit
from cz.execution.context import get_current_store
s = get_current_store()
s.create_execution(Execution(id="subp_run", graph_id="subp_flow", metadata={{"key": "val"}}))
# Exits immediately without manual flush
""",
        encoding="utf-8",
    )

    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0

    # Verify atexit flush wrote the record to the SQLite database
    persisted_store = SQLiteExecutionStore(db_path)
    runs = persisted_store.list_executions()
    assert len(runs) == 1
    assert runs[0].id == "subp_run"
