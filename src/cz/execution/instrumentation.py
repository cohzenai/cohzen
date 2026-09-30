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


def _wrap_compiled_graph_stream(original_stream: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original_stream)
    def wrapper(self: Any, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        cfg = dict(config) if config else {}
        callbacks = cfg.get("callbacks")
        if callbacks and any(isinstance(cb, CohzenCallbackHandler) for cb in callbacks):
            yield from _call_original(original_stream, self, input, config=cfg, **kwargs)
            return

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
            with execution_scope(graph_id=graph_id, metadata={"entrypoint": "CompiledGraph.stream"}):
                yield from _call_original(original_stream, self, input, config=cfg, **kwargs)
        else:
            yield from _call_original(original_stream, self, input, config=cfg, **kwargs)

    return wrapper


def _wrap_compiled_graph_astream(original_astream: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(original_astream)
    async def wrapper(self: Any, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        cfg = dict(config) if config else {}
        callbacks = cfg.get("callbacks")
        if callbacks and any(isinstance(cb, CohzenCallbackHandler) for cb in callbacks):
            gen = _call_original(original_astream, self, input, config=cfg, **kwargs)
            async for chunk in gen:
                yield chunk
            return

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
            with execution_scope(graph_id=graph_id, metadata={"entrypoint": "CompiledGraph.astream"}):
                gen = _call_original(original_astream, self, input, config=cfg, **kwargs)
                async for chunk in gen:
                    yield chunk
        else:
            gen = _call_original(original_astream, self, input, config=cfg, **kwargs)
            async for chunk in gen:
                yield chunk

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

    if "stream" in cls.__dict__:
        orig_stream = cls.stream
        _ORIGINAL_FUNCS[f"{key}.stream"] = orig_stream
        cls.stream = _wrap_compiled_graph_stream(orig_stream)

    if "astream" in cls.__dict__:
        orig_astream = cls.astream
        _ORIGINAL_FUNCS[f"{key}.astream"] = orig_astream
        cls.astream = _wrap_compiled_graph_astream(orig_astream)

    _PATCHED.add(key)


def _auto_instrument_dict(target_dict: Dict[str, Any], matcher: ManifestMatcher) -> None:
    """Inspect a module's namespace and dynamically wrap tools and LLM callables with @cz.observe."""
    from cz.execution.context import observe

    for name, obj in list(target_dict.items()):
        if name.startswith("__") or isinstance(obj, type):
            continue

        # Handle LangChain BaseTool (@tool)
        if hasattr(obj, "func") and callable(obj.func) and not getattr(obj.func, "_cohzen_wrapped", False):
            doc = (getattr(obj, "description", "") or getattr(obj.func, "__doc__", "") or "").strip()
            entity_id = matcher.resolve_tool_entity_id(name)
            reason_text = doc or f"Executing tool: {name}"
            wrapped_func = observe(name=name, kind="tool", entity_id=entity_id, reason=reason_text)(obj.func)
            wrapped_func._cohzen_wrapped = True
            obj.func = wrapped_func
            continue

        if not callable(obj):
            continue
        if getattr(obj, "_cohzen_wrapped", False):
            continue

        doc = (getattr(obj, "__doc__", "") or "").strip()

        # Check if function matches a tool in the manifest or naming conventions
        is_tool = (
            name in matcher._tool_ids
            or f"tool.{name}" in matcher._tool_ids
            or name.startswith("tool_")
            or name.startswith("tool")
            or "search" in name.lower()
        )

        # Check if function matches an LLM / model in the manifest or naming conventions
        is_llm = (
            name in matcher._model_ids
            or f"model.{name}" in matcher._model_ids
            or name.startswith("dummy_llm_")
            or name.startswith("llm_")
            or name.startswith("call_llm")
            or name.startswith("model_")
            or "llm" in name.lower()
        )

        if is_tool:
            entity_id = matcher.resolve_tool_entity_id(name)
            reason_text = doc or f"Executing tool: {name}"
            wrapped = observe(name=name, kind="tool", entity_id=entity_id, reason=reason_text)(obj)
            wrapped._cohzen_wrapped = True
            target_dict[name] = wrapped
        elif is_llm:
            entity_id = matcher.resolve_model_entity_id(name)
            reason_text = doc or f"Invoking model: {name}"
            wrapped = observe(name=name, kind="llm", entity_id=entity_id, reason=reason_text)(obj)
            wrapped._cohzen_wrapped = True
            target_dict[name] = wrapped


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
            # Auto-instrument caller's module functions before compiling
            try:
                matcher = ManifestMatcher()
                frame = inspect.currentframe()
                caller = frame.f_back if frame else None
                while caller:
                    fname = caller.f_code.co_filename
                    if "langgraph" not in fname and "cz/execution" not in fname and "contextlib" not in fname:
                        break
                    caller = caller.f_back
                if caller and caller.f_globals:
                    _auto_instrument_dict(caller.f_globals, matcher)
            except Exception:
                pass

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

            if hasattr(compiled, "stream"):
                orig_stream = compiled.stream
                wrapped_stream = _wrap_compiled_graph_stream(orig_stream)
                wrapped_stream._cohzen_wrapped = True
                compiled.stream = wrapped_stream.__get__(compiled, type(compiled))

            if hasattr(compiled, "astream"):
                orig_astream = compiled.astream
                wrapped_astream = _wrap_compiled_graph_astream(orig_astream)
                wrapped_astream._cohzen_wrapped = True
                compiled.astream = wrapped_astream.__get__(compiled, type(compiled))

            return compiled

        cls.compile = compile_wrapper
        _PATCHED.add(key)


def _patch_add_node_method(mod_name: str, class_name: str) -> None:
    mod = sys.modules.get(mod_name)
    if not mod:
        return
    cls = getattr(mod, class_name, None)
    if not cls or not isinstance(cls, type):
        return
    key = f"{mod_name}.{class_name}.add_node"
    if key in _PATCHED:
        return

    if hasattr(cls, "add_node"):
        orig_add_node = cls.add_node
        _ORIGINAL_FUNCS[key] = orig_add_node

        @functools.wraps(orig_add_node)
        def add_node_wrapper(self: Any, node: Any, action: Any = None, **kwargs: Any) -> Any:
            if action is not None and callable(action) and not getattr(action, "_cohzen_wrapped", False):
                node_name = node if isinstance(node, str) else getattr(node, "name", str(node))
                doc = (getattr(action, "__doc__", "") or "").strip()
                default_reason = doc or f"Executing node: {node_name}"

                from cz.execution.context import get_current_span

                if inspect.iscoroutinefunction(action):
                    @functools.wraps(action)
                    async def wrapped_node_action(*n_args: Any, **n_kwargs: Any) -> Any:
                        span = get_current_span()
                        if span and not span.reason:
                            span.reason = default_reason
                        res = await action(*n_args, **n_kwargs)
                        if isinstance(res, dict) and span and not span.reason:
                            span.reason = res.get("reason") or res.get("reasoning") or res.get("why")
                        return res
                    wrapped_action = wrapped_node_action
                else:
                    @functools.wraps(action)
                    def wrapped_node_action(*n_args: Any, **n_kwargs: Any) -> Any:
                        span = get_current_span()
                        if span and not span.reason:
                            span.reason = default_reason
                        res = action(*n_args, **n_kwargs)
                        if isinstance(res, dict) and span and not span.reason:
                            span.reason = res.get("reason") or res.get("reasoning") or res.get("why")
                        return res
                    wrapped_action = wrapped_node_action

                wrapped_action._cohzen_wrapped = True
                return orig_add_node(self, node, wrapped_action, **kwargs)

            return orig_add_node(self, node, action, **kwargs)

        cls.add_node = add_node_wrapper
        _PATCHED.add(key)


def _patch_langgraph() -> None:
    # Patch compilation factories and node registration
    compile_targets = [
        ("langgraph.graph.state", "StateGraph"),
        ("langgraph.graph.graph", "Graph"),
        ("langgraph.graph.message", "MessageGraph"),
    ]
    for mod_name, class_name in compile_targets:
        _patch_compile_method(mod_name, class_name)
        _patch_add_node_method(mod_name, class_name)

    # Patch core runtime classes
    runtime_targets = [
        ("langgraph.pregel.main", "Pregel"),
        ("langgraph.pregel", "Pregel"),
        ("langgraph.graph.graph", "CompiledGraph"),
        ("langgraph.graph.state", "CompiledStateGraph"),
    ]
    for mod_name, class_name in runtime_targets:
        _patch_target_class(mod_name, class_name)


def _apply_patches_if_needed(mod_name: str, mod: Any = None) -> None:
    if "langgraph" in mod_name:
        _patch_langgraph()

    # If an application module is loaded, check if it should be auto-instrumented
    if mod and hasattr(mod, "__file__") and mod.__file__:
        try:
            matcher = ManifestMatcher()
            if matcher.manifest_path:
                proj_dir = str(matcher.manifest_path.parent.parent)
                if mod.__file__.startswith(proj_dir) and "site-packages" not in mod.__file__:
                    _auto_instrument_dict(mod.__dict__, matcher)
        except Exception:
            pass


def _cohzen_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    mod = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    _apply_patches_if_needed(name, mod)
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
