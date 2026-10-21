"""Narrow, opt-in wrappers around public LangGraph compiled-graph execution APIs."""

from __future__ import annotations

import atexit
import functools
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cz.execution.callbacks import CohzenCallbackHandler
from cz.execution.context import execution_scope, get_current_execution, set_global_store
from cz.execution.manifest_matcher import ManifestMatcher
from cz.execution.sqlite import RetentionPolicy, SQLiteExecutionStore
from cz.execution.store import ExecutionStore
from cz.execution.writer import AsyncExecutionStore
from cz.project import load_config

_PATCHED: dict[tuple[type[Any], str], Callable[..., Any]] = {}
_ADDED_ATTRIBUTES: set[tuple[type[Any], str]] = set()
_NOTICE_EMITTED = False


def _notice() -> None:
    global _NOTICE_EMITTED
    if not _NOTICE_EMITTED:
        _NOTICE_EMITTED = True
        print("cohzen: capturing LangGraph runs", file=sys.stderr)


def _call(fn: Callable[..., Any], instance: Any, *args: Any, **kwargs: Any) -> Any:
    return fn(instance, *args, **kwargs)


async def _acall(fn: Callable[..., Any], instance: Any, *args: Any, **kwargs: Any) -> Any:
    return await fn(instance, *args, **kwargs)


def _has_handler(callbacks: Any) -> bool:
    handlers = callbacks if isinstance(callbacks, list) else getattr(callbacks, "handlers", ())
    return any(isinstance(handler, CohzenCallbackHandler) for handler in handlers or ())


def _add_callback(
    args: tuple[Any, ...], kwargs: dict[str, Any], handler: CohzenCallbackHandler
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Copy config/callbacks; never mutate user-owned callback configuration."""
    config_from_args = len(args) >= 2
    config = args[1] if config_from_args else kwargs.get("config")
    cfg = dict(config or {})
    callbacks = cfg.get("callbacks")
    if _has_handler(callbacks):
        return args, kwargs
    if callbacks is None:
        cfg["callbacks"] = [handler]
    elif isinstance(callbacks, list):
        cfg["callbacks"] = [*callbacks, handler]
    elif hasattr(callbacks, "copy") and hasattr(callbacks, "add_handler"):
        copied = callbacks.copy()
        copied.add_handler(handler, inherit=True)
        cfg["callbacks"] = copied
    else:
        # LangChain accepts a handler list; preserve unknown callback containers as members.
        cfg["callbacks"] = [callbacks, handler]
    new_kwargs = dict(kwargs)
    if config_from_args:
        new_args = (*args[:1], cfg, *args[2:])
    else:
        new_args = args
        new_kwargs["config"] = cfg
    return new_args, new_kwargs


def _graph_context(instance: Any, entrypoint: str) -> tuple[ManifestMatcher, str, CohzenCallbackHandler]:
    matcher = ManifestMatcher()
    graph_name = getattr(instance, "name", None) or "graph"
    graph_id = matcher.resolve_graph_id(graph_name)
    return matcher, graph_id, CohzenCallbackHandler(matcher=matcher, graph_id=graph_id)


def _wrap_invoke(original: Callable[..., Any], entrypoint: str) -> Callable[..., Any]:
    @functools.wraps(original)
    def wrapped(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _, graph_id, handler = _graph_context(instance, entrypoint)
        call_args, call_kwargs = _add_callback(args, kwargs, handler)
        _notice()
        if get_current_execution():
            return _call(original, instance, *call_args, **call_kwargs)
        with execution_scope(graph_id=graph_id, metadata={"entrypoint": entrypoint}):
            return _call(original, instance, *call_args, **call_kwargs)

    return wrapped


def _wrap_ainvoke(original: Callable[..., Any], entrypoint: str) -> Callable[..., Any]:
    @functools.wraps(original)
    async def wrapped(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _, graph_id, handler = _graph_context(instance, entrypoint)
        call_args, call_kwargs = _add_callback(args, kwargs, handler)
        _notice()
        if get_current_execution():
            return await _acall(original, instance, *call_args, **call_kwargs)
        with execution_scope(graph_id=graph_id, metadata={"entrypoint": entrypoint}):
            return await _acall(original, instance, *call_args, **call_kwargs)

    return wrapped


def _wrap_stream(original: Callable[..., Any], entrypoint: str) -> Callable[..., Any]:
    @functools.wraps(original)
    def wrapped(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _, graph_id, handler = _graph_context(instance, entrypoint)
        call_args, call_kwargs = _add_callback(args, kwargs, handler)
        _notice()
        if get_current_execution():
            yield from _call(original, instance, *call_args, **call_kwargs)
            return
        with execution_scope(graph_id=graph_id, metadata={"entrypoint": entrypoint}):
            yield from _call(original, instance, *call_args, **call_kwargs)

    return wrapped


def _wrap_astream(original: Callable[..., Any], entrypoint: str) -> Callable[..., Any]:
    @functools.wraps(original)
    async def wrapped(instance: Any, *args: Any, **kwargs: Any) -> Any:
        _, graph_id, handler = _graph_context(instance, entrypoint)
        call_args, call_kwargs = _add_callback(args, kwargs, handler)
        _notice()
        if get_current_execution():
            async for item in _call(original, instance, *call_args, **call_kwargs):
                yield item
            return
        with execution_scope(graph_id=graph_id, metadata={"entrypoint": entrypoint}):
            async for item in _call(original, instance, *call_args, **call_kwargs):
                yield item

    return wrapped


def _patch_class(cls: type[Any]) -> None:
    for method, factory in {
        "invoke": _wrap_invoke,
        "ainvoke": _wrap_ainvoke,
        "stream": _wrap_stream,
        "astream": _wrap_astream,
    }.items():
        key = (cls, method)
        if key in _PATCHED:
            continue
        # Avoid patching inherited methods if an ancestor is already patched
        if any((base, method) in _PATCHED for base in cls.__mro__[1:]):
            continue
        if not hasattr(cls, method):
            continue
        original = getattr(cls, method)
        _PATCHED[key] = original
        if method not in cls.__dict__:
            _ADDED_ATTRIBUTES.add(key)
        setattr(cls, method, factory(original, f"{cls.__name__}.{method}"))


def _patch_compiled_graphs() -> None:
    """Patch only LangGraph compiled graph classes, never builders or Runnable."""
    candidates: list[type[Any]] = []
    for module_name, class_name in (
        ("langgraph.pregel.main", "Pregel"),
        ("langgraph.pregel.base", "Pregel"),
        ("langgraph.pregel", "Pregel"),
        ("langgraph.graph.state", "CompiledStateGraph"),
        ("langgraph.graph.graph", "CompiledGraph"),
    ):
        module = sys.modules.get(module_name)
        if not module and "langgraph" in sys.modules:
            try:
                import importlib

                module = importlib.import_module(module_name)
            except Exception:
                pass
        cls = getattr(module, class_name, None) if module else None
        if isinstance(cls, type) and cls not in candidates:
            candidates.append(cls)

    # Also resolve Pregel from base classes of any compiled graph candidate
    for c in list(candidates):
        for base in c.__mro__:
            if getattr(base, "__name__", "") == "Pregel" and isinstance(base, type) and base not in candidates:
                candidates.append(base)

    # Patch base classes first (e.g. Pregel before CompiledStateGraph)
    candidates.sort(key=lambda c: len(c.__mro__))
    for cls in candidates:
        _patch_class(cls)


def install(store: ExecutionStore | None = None, project: Path | None = None) -> None:
    """Enable explicit runtime capture after LangGraph has been imported."""
    try:
        if store is None and project is not None:
            config = load_config(project)
            retention = RetentionPolicy(
                max_payload_bytes=int(config["max_payload_bytes"]),
                max_runs=int(config["max_runs"]),
                max_age_days=int(config["max_age_days"]),
            )
            store = AsyncExecutionStore(
                SQLiteExecutionStore(project / ".cohzen" / "executions.db", retention=retention),
                max_payload_bytes=retention.max_payload_bytes,
            )
        if store is not None:
            set_global_store(store)
        _patch_compiled_graphs()
        if store is not None and hasattr(store, "flush"):
            atexit.register(store.flush, 1.0)
    except Exception:
        return


def uninstall() -> None:
    """Restore patched compiled-graph methods; intended for tests and explicit teardown."""
    for (cls, method), original in list(_PATCHED.items()):
        key = (cls, method)
        if key in _ADDED_ATTRIBUTES:
            try:
                delattr(cls, method)
            except AttributeError:
                setattr(cls, method, original)
        else:
            setattr(cls, method, original)
    _PATCHED.clear()
    _ADDED_ATTRIBUTES.clear()


def track(store: ExecutionStore | None = None) -> None:
    """Compatibility alias for explicit runtime installation."""
    install(store=store)
