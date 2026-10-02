"""Isolated Node Debugger and Runner for LangGraph applications.

Enables executing, testing, and debugging any individual node directly with
custom or recorded inputs, without compiling or executing the entire graph.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from cz.execution.context import (
    execution_scope,
    get_current_execution,
    get_current_store,
    span_scope,
)
from cz.execution.models import Execution, Span
from cz.execution.serializer import serialize_for_storage
from cz.execution.sqlite import SQLiteExecutionStore


class SmartStateDict(dict):
    """Dictionary supporting both dict item access (d['a']) and attribute access (d.a)."""

    def __getattr__(self, name: str) -> Any:
        if name in self:
            val = self[name]
            if isinstance(val, dict) and not isinstance(val, SmartStateDict):
                val = SmartStateDict(val)
                self[name] = val
            return val
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        if name in self:
            del self[name]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def _parse_model_repr_string(s: str) -> Optional[Dict[str, Any]]:
    """Parse string representations of Python objects/Pydantic models into a dictionary."""
    if not isinstance(s, str) or "=" not in s:
        return None

    cleaned = s.strip()
    # Strip class name prefix if present (e.g. "RequiredInformation(a=1, b=2)")
    if cleaned.endswith(")") and "(" in cleaned:
        cleaned = cleaned[cleaned.find("(") + 1 : -1]

    pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)=((?:'[^']*')|(?:\"[^\"]*\")|(?:[^\s,]+))")
    matches = pattern.findall(cleaned)
    if not matches:
        return None

    res: Dict[str, Any] = {}
    for key, raw_val in matches:
        raw_val = raw_val.strip()
        if (raw_val.startswith("'") and raw_val.endswith("'")) or (raw_val.startswith('"') and raw_val.endswith('"')):
            res[key] = raw_val[1:-1]
        elif raw_val.lower() == "none":
            res[key] = None
        elif raw_val.lower() == "true":
            res[key] = True
        elif raw_val.lower() == "false":
            res[key] = False
        elif raw_val.isdigit() or (raw_val.startswith("-") and raw_val[1:].isdigit()):
            res[key] = int(raw_val)
        else:
            try:
                res[key] = float(raw_val)
            except ValueError:
                res[key] = raw_val
    return res


def _parse_message_item(item: Any) -> Any:
    """Parse a message item (string or dict) into a message object with .content, .type, .tool_calls."""
    if isinstance(item, str):
        content_val = None
        if "content=" in item:
            m = re.search(r"content=(?:'([^']*)'|\"([^\"]*)\")", item)
            if m:
                content_val = m.group(1) if m.group(1) is not None else m.group(2)
        if content_val is None:
            content_val = item

        try:
            from langchain_core.messages import AIMessage, HumanMessage
            if "AIMessage" in item or "refusal" in item or "token_usage" in item:
                return AIMessage(content=content_val)
            return HumanMessage(content=content_val)
        except ImportError:
            return SmartStateDict({
                "content": content_val,
                "type": "user",
                "role": "user",
                "tool_calls": [],
                "additional_kwargs": {},
            })
    elif isinstance(item, dict):
        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
            role = item.get("role") or item.get("type") or "user"
            content = item.get("content", "")
            if role in ("ai", "assistant"):
                return AIMessage(content=content, tool_calls=item.get("tool_calls", []))
            elif role == "system":
                return SystemMessage(content=content)
            elif role == "tool":
                return ToolMessage(content=content, tool_call_id=item.get("tool_call_id", ""))
            return HumanMessage(content=content)
        except ImportError:
            return SmartStateDict(item)
    return item


def hydrate_state_for_node(state: Any, node_fn: Any) -> Any:
    """Intelligently hydrate state dict, restoring Pydantic objects, SmartDicts, and message objects."""
    if not isinstance(state, dict):
        return state

    field_annotations: Dict[str, Any] = {}
    try:
        import typing
        hints = typing.get_type_hints(node_fn)
        sig = inspect.signature(node_fn)
        params = list(sig.parameters.values())
        if params:
            first_param = params[0]
            state_cls = hints.get(first_param.name) or first_param.annotation
            if hasattr(state_cls, "__annotations__"):
                field_annotations = dict(state_cls.__annotations__)
    except Exception:
        try:
            sig = inspect.signature(node_fn)
            params = list(sig.parameters.values())
            if params:
                state_param = params[0]
                ann = state_param.annotation
                if ann and ann != inspect.Parameter.empty and hasattr(ann, "__annotations__"):
                    field_annotations = dict(ann.__annotations__)
        except Exception:
            pass

    hydrated = SmartStateDict()
    for k, v in state.items():
        target_cls = field_annotations.get(k)
        if isinstance(target_cls, str):
            mod = inspect.getmodule(node_fn)
            if mod and hasattr(mod, target_cls):
                target_cls = getattr(mod, target_cls)
            elif hasattr(node_fn, "__globals__") and target_cls in node_fn.__globals__:
                target_cls = node_fn.__globals__[target_cls]

        # 1. String representing a model / object
        if isinstance(v, str):
            parsed = _parse_model_repr_string(v)
            if parsed is not None:
                if isinstance(target_cls, type) and issubclass(target_cls, BaseModel):
                    try:
                        hydrated[k] = target_cls(**parsed)
                        continue
                    except Exception:
                        pass
                hydrated[k] = SmartStateDict(parsed)
                continue

        # 2. Dictionary
        if isinstance(v, dict):
            if isinstance(target_cls, type) and issubclass(target_cls, BaseModel):
                try:
                    hydrated[k] = target_cls(**v)
                    continue
                except Exception:
                    pass
            hydrated[k] = SmartStateDict(v)
            continue

        # 3. Messages list
        if k == "messages" and isinstance(v, list):
            hydrated[k] = [_parse_message_item(m) for m in v]
            continue

        hydrated[k] = v

    return hydrated


class NodeDebugResult(BaseModel):
    """Result of an isolated node execution."""
    node_name: str
    handler_name: str
    file_path: Optional[str] = None
    status: str = "completed"  # 'completed' or 'failed'
    input_state: Any = None
    output_state: Any = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    reason: Optional[str] = None
    execution_id: Optional[str] = None
    child_spans: List[Span] = Field(default_factory=list)


def _find_db(path_str: str = ".") -> Path:
    p = Path(path_str).resolve()
    if p.is_file() and p.name == "executions.db":
        return p
    if (p / ".cohzen" / "executions.db").is_file():
        return p / ".cohzen" / "executions.db"
    for parent in [p, *p.parents]:
        cand = parent / ".cohzen" / "executions.db"
        if cand.is_file():
            return cand
    return p / ".cohzen" / "executions.db"


def get_node_input_from_run(
    execution_id: str,
    node_name: str,
    db_path: Optional[Path | str] = None,
) -> Any:
    """Retrieve the exact input payload passed to a node during a previous execution run."""
    resolved_db = Path(db_path) if db_path else _find_db()
    store = SQLiteExecutionStore(db_path=resolved_db) if resolved_db.is_file() else None
    execution = store.get_execution(execution_id) if store else None

    # If not found in primary db, search parent databases
    if not execution:
        start_p = resolved_db.parent if resolved_db else Path.cwd()
        for parent in start_p.resolve().parents:
            cand = parent / ".cohzen" / "executions.db"
            if cand.is_file() and cand != resolved_db:
                cand_store = SQLiteExecutionStore(db_path=cand)
                cand_exec = cand_store.get_execution(execution_id)
                if cand_exec:
                    store = cand_store
                    execution = cand_exec
                    resolved_db = cand
                    break

    if not execution or not store:
        raise ValueError(f"Execution '{execution_id}' not found in store.")

    spans = store.get_spans(execution.id)

    # Search for matching node spans
    matching_spans = [
        s for s in spans
        if s.kind == "node" and (s.name == node_name or (s.entity_id and s.entity_id.endswith(f".{node_name}")))
    ]

    if not matching_spans:
        # Fallback: check any span with this name
        matching_spans = [s for s in spans if s.name == node_name]

    if not matching_spans:
        avail_nodes = [s.name for s in spans if s.kind == "node"]
        raise ValueError(
            f"Node '{node_name}' not found in execution {execution.id}. "
            f"Available nodes in this run: {', '.join(avail_nodes) if avail_nodes else 'none'}"
        )

    # Pick the most complete input from the matching spans (often the last or first with non-empty input)
    for sp in reversed(matching_spans):
        if sp.input is not None:
            return sp.input

    return matching_spans[-1].input


def _import_file_module(file_path: Path):
    """Import a Python file as a standalone module."""
    mod_name = f"_cz_target_{file_path.stem}_{abs(hash(str(file_path)))}"
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {file_path}")

    # Ensure parent directory is in sys.path for relative imports
    file_dir = str(file_path.parent.resolve())
    if file_dir not in sys.path:
        sys.path.insert(0, file_dir)

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def resolve_node_function(
    node_name: str,
    project_dir: Path | str = ".",
    graph_target: Optional[str] = None,
) -> Tuple[Callable[..., Any], str, str]:
    """Resolve and return (callable_function, handler_name, file_path) for the target node."""
    p_dir = Path(project_dir).resolve()

    # 1. If explicit file or target given (e.g. app.py or app.py:app)
    if graph_target:
        target_path = Path(graph_target)
        if not target_path.is_absolute():
            target_path = p_dir / target_path
        if ":" in str(target_path):
            file_part, var_part = str(target_path).split(":", 1)
            target_file = Path(file_part)
            if target_file.is_file():
                mod = _import_file_module(target_file)
                graph_obj = getattr(mod, var_part, None)
                if graph_obj and hasattr(graph_obj, "nodes") and node_name in graph_obj.nodes:
                    node_item = graph_obj.nodes[node_name]
                    runnable = getattr(node_item, "runnable", node_item)
                    return runnable, node_name, str(target_file)
        elif target_path.is_file():
            mod = _import_file_module(target_path)
            # Check compiled graphs in module
            for attr_name, val in mod.__dict__.items():
                if hasattr(val, "nodes") and isinstance(val.nodes, dict) and node_name in val.nodes:
                    node_item = val.nodes[node_name]
                    runnable = getattr(node_item, "runnable", node_item)
                    return runnable, node_name, str(target_path)
            # Check direct function in module
            if hasattr(mod, node_name) and callable(getattr(mod, node_name)):
                return getattr(mod, node_name), node_name, str(target_path)

    # 2. Check manifest.json if present
    manifest_path = p_dir / ".cohzen" / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            graphs = data.get("graphs", [])
            for g in graphs:
                for n in g.get("nodes", []):
                    if n.get("name") == node_name:
                        handler = n.get("handler") or node_name
                        file_path = n.get("file_path")
                        if file_path:
                            target_file = Path(file_path)
                            if not target_file.is_absolute():
                                target_file = p_dir / target_file
                            if target_file.is_file():
                                mod = _import_file_module(target_file)
                                if hasattr(mod, handler):
                                    return getattr(mod, handler), handler, str(target_file)
        except Exception:
            pass

    # 3. Use scanner AST engine to locate node
    from cz.scanner.engine import scan_repository
    scan_res = scan_repository(str(p_dir))
    for g in scan_res.graphs:
        for n in g.nodes:
            if n.name == node_name:
                handler = n.handler or node_name
                target_file = Path(n.file_path)
                if not target_file.is_absolute():
                    target_file = p_dir / target_file
                if target_file.is_file():
                    mod = _import_file_module(target_file)
                    if hasattr(mod, handler):
                        return getattr(mod, handler), handler, str(target_file)

    # 4. Search python files for function with name or matching name
    candidates = list(p_dir.rglob("*.py"))
    for py_file in candidates:
        if any(part.startswith(".") or part in ("venv", ".venv", "tests") for part in py_file.parts):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if f"def {node_name}(" in content or f"add_node('{node_name}'" in content or f'add_node("{node_name}"' in content:
                mod = _import_file_module(py_file)
                if hasattr(mod, node_name) and callable(getattr(mod, node_name)):
                    return getattr(mod, node_name), node_name, str(py_file)
                # Check graph objects
                for val in mod.__dict__.values():
                    if hasattr(val, "nodes") and isinstance(val.nodes, dict) and node_name in val.nodes:
                        node_item = val.nodes[node_name]
                        runnable = getattr(node_item, "runnable", node_item)
                        return runnable, node_name, str(py_file)
        except Exception:
            continue

    raise ValueError(f"Could not locate node handler for '{node_name}' in project {p_dir}")


def run_isolated_node(
    node_name: str,
    input_state: Any,
    project_dir: Path | str = ".",
    graph_target: Optional[str] = None,
    record: bool = True,
    config: Optional[Dict[str, Any]] = None,
) -> NodeDebugResult:
    """Execute a single node directly with the given input state without compiling or running the entire graph."""
    p_dir = Path(project_dir).resolve()
    node_fn, handler_name, file_path = resolve_node_function(node_name, project_dir=p_dir, graph_target=graph_target)

    # Prepare input state
    state = input_state
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except json.JSONDecodeError:
            pass

    # Hydrate state for target node handler
    state = hydrate_state_for_node(state, node_fn)

    store = get_current_store() if record else None
    exec_id: Optional[str] = None
    child_spans: List[Span] = []
    output_state: Any = None
    error_msg: Optional[str] = None
    status = "completed"
    start_time = time.monotonic()
    reason_captured: Optional[str] = None

    try:
        if record:
            with execution_scope(
                graph_id=f"isolated_node:{node_name}",
                metadata={
                    "mode": "isolated_node_debug",
                    "target_node": node_name,
                    "handler": handler_name,
                    "file_path": file_path,
                },
            ) as exec_obj:
                exec_id = exec_obj.id
                with span_scope(
                    name=node_name,
                    kind="node",
                    entity_id=f"node.{node_name}",
                    input=state,
                ) as s:
                    # Invoke node function / runnable
                    output_state = _invoke_callable(node_fn, state, config=config)
                    if s.reason:
                        reason_captured = s.reason
                    elif isinstance(output_state, dict):
                        reason_captured = (
                            output_state.get("reason")
                            or output_state.get("reasoning")
                            or output_state.get("rationale")
                            or output_state.get("why")
                        )
                # Fetch child spans captured during this execution
                if store:
                    all_spans = store.get_spans(exec_id)
                    child_spans = [sp for sp in all_spans if sp.name != node_name and sp.kind != "graph"]
        else:
            output_state = _invoke_callable(node_fn, state, config=config)
    except Exception as exc:
        status = "failed"
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    duration_ms = round((time.monotonic() - start_time) * 1000.0, 2)

    return NodeDebugResult(
        node_name=node_name,
        handler_name=handler_name,
        file_path=file_path,
        status=status,
        input_state=serialize_for_storage(state),
        output_state=serialize_for_storage(output_state) if output_state is not None else None,
        duration_ms=duration_ms,
        error=error_msg,
        reason=reason_captured,
        execution_id=exec_id,
        child_spans=child_spans,
    )


def _invoke_callable(
    fn: Any,
    state: Any,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """Invoke function, method, or Runnable supporting both sync and async."""
    # If it's a LangChain Runnable or has .invoke
    if hasattr(fn, "invoke") and callable(fn.invoke):
        cfg = config or {}
        try:
            return fn.invoke(state, config=cfg)
        except TypeError:
            return fn.invoke(state)

    # If it's a coroutine function
    if inspect.iscoroutinefunction(fn):
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            if len(params) >= 2 and config is not None:
                return asyncio.run(fn(state, config))
            return asyncio.run(fn(state))
        except (ValueError, TypeError):
            return asyncio.run(fn(state))

    # Standard function
    try:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if len(params) >= 2 and config is not None:
            return fn(state, config)
        return fn(state)
    except (ValueError, TypeError):
        return fn(state)
