"""Auto-instrumentation and runtime patching for LangGraph and LangChain."""

from __future__ import annotations

import builtins
import functools
import inspect
import sys
from typing import Any, Callable, Dict, Optional, Set

from cz.execution.callbacks import CohzenCallbackHandler
from cz.execution.context import execution_scope, get_current_execution, get_current_store, set_global_store
from cz.execution.manifest_matcher import ManifestMatcher
from cz.execution.store import ExecutionStore

_PATCHED: Set[str] = set()
_ORIGINAL_FUNCS: Dict[str, Callable[..., Any]] = {}
_IMPORT_HOOK_INSTALLED = False
_ORIGINAL_IMPORT = builtins.__import__


def _call_original(fn: Any, self: Any, *args: Any, **kwargs: Any) -> Any:
    if hasattr(fn, "__self__") and fn.__self__ is not None:
        return fn(*args, **kwargs)
    return fn(self, *args, **kwargs)


async def _acall_original(fn: Any, self: Any, *args: Any, **kwargs: Any) -> Any:
    if hasattr(fn, "__self__") and fn.__self__ is not None:
        return await fn(*args, **kwargs)
    return await fn(self, *args, **kwargs)


def _wrap_compiled_graph_invoke(original_invoke: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original_invoke)
    def wrapper(self: Any, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        cfg = dict(config) if config else {}
        callbacks = cfg.get("callbacks")
        if callbacks and any(isinstance(cb, CohzenCallbackHandler) for cb in callbacks):
            return _call_original(original_invoke, self, input, config=cfg, **kwargs)

        matcher = ManifestMatcher()
        graph_name = getattr(self, "name", None) or "graph"
        graph_id = matcher.resolve_graph_id(graph_name)

        handler = CohzenCallbackHandler(matcher=matcher, graph_id=graph_id)
        if callbacks is None:
            cfg["callbacks"] = [handler]
        elif isinstance(callbacks, list):
            cfg["callbacks"] = callbacks + [handler]

        current_exec = get_current_execution()
        if not current_exec:
            with execution_scope(graph_id=graph_id, metadata={"entrypoint": "CompiledGraph.invoke"}):
                return _call_original(original_invoke, self, input, config=cfg, **kwargs)
        else:
            return _call_original(original_invoke, self, input, config=cfg, **kwargs)

    return wrapper


def _wrap_compiled_graph_ainvoke(original_ainvoke: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original_ainvoke)
    async def wrapper(self: Any, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        cfg = dict(config) if config else {}
        callbacks = cfg.get("callbacks")
        if callbacks and any(isinstance(cb, CohzenCallbackHandler) for cb in callbacks):
            return await _acall_original(original_ainvoke, self, input, config=cfg, **kwargs)

        matcher = ManifestMatcher()
        graph_name = getattr(self, "name", None) or "graph"
        graph_id = matcher.resolve_graph_id(graph_name)

        handler = CohzenCallbackHandler(matcher=matcher, graph_id=graph_id)
        if callbacks is None:
            cfg["callbacks"] = [handler]
        elif isinstance(callbacks, list):
            cfg["callbacks"] = callbacks + [handler]

        current_exec = get_current_execution()
        if not current_exec:
            with execution_scope(graph_id=graph_id, metadata={"entrypoint": "CompiledGraph.ainvoke"}):
                return await _acall_original(original_ainvoke, self, input, config=cfg, **kwargs)
        else:
            return await _acall_original(original_ainvoke, self, input, config=cfg, **kwargs)

    return wrapper


def _patch_target_class(mod_name: str, class_name: str) -> None:
    mod = sys.modules.get(mod_name)
    if not mod:
        return
    cls = getattr(mod, class_name, None)
    if not cls or not isinstance(cls, type):
        return
    key = f"{mod_name}.{class_name}"
    if key in _PATCHED:
        return

    if "invoke" in cls.__dict__:
        orig_invoke = cls.invoke
        _ORIGINAL_FUNCS[f"{key}.invoke"] = orig_invoke
        cls.invoke = _wrap_compiled_graph_invoke(orig_invoke)

    if "ainvoke" in cls.__dict__:
        orig_ainvoke = cls.ainvoke
        _ORIGINAL_FUNCS[f"{key}.ainvoke"] = orig_ainvoke
        cls.ainvoke = _wrap_compiled_graph_ainvoke(orig_ainvoke)

    _PATCHED.add(key)


def _patch_compile_method(mod_name: str, class_name: str) -> None:
    mod = sys.modules.get(mod_name)
    if not mod:
        return
    cls = getattr(mod, class_name, None)
    if not cls or not isinstance(cls, type):
        return
    key = f"{mod_name}.{class_name}.compile"
    if key in _PATCHED:
        return

    if hasattr(cls, "compile"):
        orig_compile = cls.compile
        _ORIGINAL_FUNCS[key] = orig_compile

        @functools.wraps(orig_compile)
        def compile_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            compiled = orig_compile(self, *args, **kwargs)
            builder_name = getattr(self, "name", None)
            if builder_name and not getattr(compiled, "name", None):
                compiled.name = builder_name

            orig_inv = compiled.invoke
            wrapped_inv = _wrap_compiled_graph_invoke(orig_inv)
            wrapped_inv._cohzen_wrapped = True
            compiled.invoke = wrapped_inv.__get__(compiled, type(compiled))

            if hasattr(compiled, "ainvoke"):
                orig_ainv = compiled.ainvoke
                wrapped_ainv = _wrap_compiled_graph_ainvoke(orig_ainv)
                wrapped_ainv._cohzen_wrapped = True
                compiled.ainvoke = wrapped_ainv.__get__(compiled, type(compiled))

            return compiled

        cls.compile = compile_wrapper
        _PATCHED.add(key)


def _patch_langgraph() -> None:
    # Patch compilation factories
    compile_targets = [
        ("langgraph.graph.state", "StateGraph"),
        ("langgraph.graph.graph", "Graph"),
        ("langgraph.graph.message", "MessageGraph"),
    ]
    for mod_name, class_name in compile_targets:
        _patch_compile_method(mod_name, class_name)

    # Patch core runtime classes
    runtime_targets = [
        ("langgraph.pregel.main", "Pregel"),
        ("langgraph.pregel", "Pregel"),
        ("langgraph.graph.graph", "CompiledGraph"),
        ("langgraph.graph.state", "CompiledStateGraph"),
    ]
    for mod_name, class_name in runtime_targets:
        _patch_target_class(mod_name, class_name)


def _apply_patches_if_needed(mod_name: str) -> None:
    if "langgraph" in mod_name:
        _patch_langgraph()


def _cohzen_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    mod = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    _apply_patches_if_needed(name)
    return mod


def install(store: Optional[ExecutionStore] = None) -> None:
    """Install auto-instrumentation hooks for LangGraph and LangChain.

    Called automatically via sitecustomize.py (from `cz init`) or programmatically via `cz.track()`.
    """
    global _IMPORT_HOOK_INSTALLED

    if store is not None:
        set_global_store(store)

    # Patch existing modules if already loaded
    _patch_langgraph()

    # Install import hook for lazily loaded packages
    if not _IMPORT_HOOK_INSTALLED:
        builtins.__import__ = _cohzen_import
        _IMPORT_HOOK_INSTALLED = True


def uninstall() -> None:
    """Revert installed patches and restore original functions."""
    global _IMPORT_HOOK_INSTALLED

    if _IMPORT_HOOK_INSTALLED:
        builtins.__import__ = _ORIGINAL_IMPORT
        _IMPORT_HOOK_INSTALLED = False

    for func_key, orig in _ORIGINAL_FUNCS.items():
        parts = func_key.split(".")
        method_name = parts[-1]
        cls_name = parts[-2]
        mod_name = ".".join(parts[:-2])
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, cls_name):
            cls = getattr(mod, cls_name)
            setattr(cls, method_name, orig)

    _ORIGINAL_FUNCS.clear()
    _PATCHED.clear()


def track(store: Optional[ExecutionStore] = None) -> None:
    """Convenience function to enable Cohzen execution tracking."""
    install(store=store)
