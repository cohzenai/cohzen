"""LangChain and LangGraph callback integration for Cohzen execution tracking."""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from cz.execution.context import _current_span, get_current_execution, get_current_span, get_current_store
from cz.execution.manifest_matcher import ManifestMatcher
from cz.execution.models import Event, Execution, Span
from cz.execution.serializer import extract_llm_generation, serialize_for_storage
from cz.execution.store import ExecutionStore

# BaseCallbackHandler may or may not be available depending on user environment
try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback callback handler base class when langchain_core is not installed."""
        pass


class CohzenCallbackHandler(BaseCallbackHandler):
    """LangChain / LangGraph callback handler that creates hierarchically nested Spans."""

    def __init__(
        self,
        store: Optional[ExecutionStore] = None,
        matcher: Optional[ManifestMatcher] = None,
        graph_id: Optional[str] = None,
    ):
        super().__init__()
        self.store = store or get_current_store()
        self.matcher = matcher or ManifestMatcher()
        self.graph_id = graph_id
        # Map run_id (str) -> Span
        self._run_spans: Dict[str, Span] = {}
        # Map run_id -> contextvar Token
        self._span_tokens: Dict[str, Any] = {}
        # Map run_id -> monotonic start time
        self._start_times: Dict[str, float] = {}
        # Active stack of node span IDs for proper parent-child hierarchy
        self._active_node_ids: List[str] = []
        # Root run ID representing the graph invocation
        self._root_run_id: Optional[str] = None
        # Track whether this handler created the top-level execution
        self._created_execution: Optional[Execution] = None

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        if run_id_str in self._run_spans:
            return

        parent_id_str = str(parent_run_id) if parent_run_id else None
        meta = metadata or {}
        tags_list = tags or []

        # Check if this is the root invocation of the graph
        if parent_id_str is None and self._root_run_id is None:
            self._root_run_id = run_id_str
            graph_name = self.graph_id or meta.get("langgraph_graph") or (serialized.get("name") if serialized else None) or "graph"
            resolved_graph_id = self.matcher.resolve_graph_id(graph_name)

            # Ensure an Execution exists
            current_exec = get_current_execution()
            if not current_exec:
                exec_obj = Execution(
                    graph_id=resolved_graph_id,
                    metadata={"framework": "langgraph", "root_run_id": run_id_str},
                )
                self.store.create_execution(exec_obj)
                self._created_execution = exec_obj
                exec_id = exec_obj.id
            else:
                exec_id = current_exec.id

            # Create root graph span
            span = Span(
                id=run_id_str,
                execution_id=exec_id,
                parent_id=None,
                entity_id=resolved_graph_id,
                kind="graph",
                name=graph_name,
                input=serialize_for_storage(inputs),
                metadata=serialize_for_storage(meta),
            )
            self.store.create_span(span)
            self._run_spans[run_id_str] = span
            self._start_times[run_id_str] = time.monotonic()
            return

        # Check if this chain invocation represents a LangGraph node
        node_name = meta.get("langgraph_node")
        if not node_name and serialized and serialized.get("name"):
            # Check if name looks like a node
            name = serialized.get("name")
            if name not in ("RunnableSequence", "RunnableParallel", "StateGraph", "CompiledStateGraph"):
                node_name = name

        if node_name:
            exec_id = self._get_execution_id()
            entity_id = self.matcher.resolve_node_entity_id(node_name)
            parent_span_id = self._find_parent_span_id(parent_id_str)

            span = Span(
                id=run_id_str,
                execution_id=exec_id,
                parent_id=parent_span_id,
                entity_id=entity_id,
                kind="node",
                name=node_name,
                input=serialize_for_storage(inputs),
                metadata={**serialize_for_storage(meta), "tags": tags_list},
            )
            self.store.create_span(span)
            self._run_spans[run_id_str] = span
            self._active_node_ids.append(run_id_str)
            self._start_times[run_id_str] = time.monotonic()
            self._span_tokens[run_id_str] = _current_span.set(span)

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        if run_id_str in self._active_node_ids:
            self._active_node_ids.remove(run_id_str)

        span = self._run_spans.get(run_id_str)
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            if isinstance(outputs, dict) and not span.reason:
                span.reason = (
                    outputs.get("reason")
                    or outputs.get("reasoning")
                    or outputs.get("rationale")
                    or outputs.get("why")
                    or outputs.get("thought")
                )
            self.store.finish_span(
                span_id=span.id,
                status="completed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                output=serialize_for_storage(outputs),
                reason=span.reason,
            )

        tok = self._span_tokens.pop(run_id_str, None)
        if tok:
            try:
                _current_span.reset(tok)
            except Exception:
                pass

        # If root run completed and we created the execution, finish the execution
        if run_id_str == self._root_run_id and self._created_execution:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_execution(
                execution_id=self._created_execution.id,
                status="completed",
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        if run_id_str in self._active_node_ids:
            self._active_node_ids.remove(run_id_str)

        span = self._run_spans.get(run_id_str)
        err_msg = f"{type(error).__name__}: {str(error)}"
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_span(
                span_id=span.id,
                status="failed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                error=err_msg,
            )

        tok = self._span_tokens.pop(run_id_str, None)
        if tok:
            try:
                _current_span.reset(tok)
            except Exception:
                pass

        if run_id_str == self._root_run_id and self._created_execution:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_execution(
                execution_id=self._created_execution.id,
                status="failed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                error=err_msg,
            )

    def on_chat_model_start(
        self,
        serialized: Optional[Dict[str, Any]],
        messages: List[List[Any]],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        invocation_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._record_llm_start(
            serialized=serialized,
            inputs={"messages": messages},
            run_id=run_id,
            parent_run_id=parent_run_id,
            metadata=metadata,
            invocation_params=invocation_params,
        )

    def on_llm_start(
        self,
        serialized: Optional[Dict[str, Any]],
        prompts: List[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        invocation_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._record_llm_start(
            serialized=serialized,
            inputs={"prompts": prompts},
            run_id=run_id,
            parent_run_id=parent_run_id,
            metadata=metadata,
            invocation_params=invocation_params,
        )

    def _record_llm_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Any,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID],
        metadata: Optional[Dict[str, Any]],
        invocation_params: Optional[Dict[str, Any]],
    ) -> None:
        run_id_str = str(run_id)
        parent_id_str = str(parent_run_id) if parent_run_id else None
        meta = metadata or {}
        inv_params = invocation_params or {}

        # Extract model and provider
        model_name = (
            inv_params.get("model")
            or inv_params.get("model_name")
            or meta.get("ls_model_name")
            or (serialized.get("name") if serialized else None)
            or "llm"
        )
        provider = meta.get("ls_provider")
        if not provider and serialized and "id" in serialized:
            id_parts = serialized["id"]
            if isinstance(id_parts, list) and len(id_parts) > 2:
                provider = id_parts[2]

        entity_id = self.matcher.resolve_model_entity_id(model_name, provider)
        exec_id = self._get_execution_id()
        parent_span_id = self._find_parent_span_id(parent_id_str)

        span = Span(
            id=run_id_str,
            execution_id=exec_id,
            parent_id=parent_span_id,
            entity_id=entity_id,
            kind="llm",
            name=f"llm:{model_name}",
            input=serialize_for_storage(inputs),
            metadata={
                "model": model_name,
                "provider": provider,
                "invocation_params": serialize_for_storage(inv_params),
            },
        )
        self.store.create_span(span)
        self._run_spans[run_id_str] = span
        self._start_times[run_id_str] = time.monotonic()

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        span = self._run_spans.get(run_id_str)
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)

            # Extract structured generations, tool calls, and token usage
            llm_data = extract_llm_generation(response)
            if llm_data.get("token_usage"):
                span.metadata["token_usage"] = llm_data["token_usage"]
            if llm_data.get("tool_calls"):
                span.metadata["tool_calls"] = llm_data["tool_calls"]
            if llm_data.get("text"):
                span.metadata["text"] = llm_data["text"]

            output_data = llm_data["generations"] if llm_data["generations"] else llm_data["text"]

            self.store.finish_span(
                span_id=span.id,
                status="completed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                output=output_data,
                metadata=span.metadata,
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        span = self._run_spans.get(run_id_str)
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_span(
                span_id=span.id,
                status="failed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                error=f"{type(error).__name__}: {str(error)}",
            )

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        parent_id_str = str(parent_run_id) if parent_run_id else None
        tool_name = (serialized.get("name") if serialized else None) or "tool"
        entity_id = self.matcher.resolve_tool_entity_id(tool_name)
        exec_id = self._get_execution_id()
        parent_span_id = self._find_parent_span_id(parent_id_str)

        span = Span(
            id=run_id_str,
            execution_id=exec_id,
            parent_id=parent_span_id,
            entity_id=entity_id,
            kind="tool",
            name=tool_name,
            input=serialize_for_storage(input_str),
            metadata=serialize_for_storage(metadata or {}),
        )
        self.store.create_span(span)
        self._run_spans[run_id_str] = span
        self._start_times[run_id_str] = time.monotonic()

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        span = self._run_spans.get(run_id_str)
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_span(
                span_id=span.id,
                status="completed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                output=serialize_for_storage(output),
            )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        span = self._run_spans.get(run_id_str)
        if span:
            duration_ms = self._calc_duration(run_id_str)
            ended_at = datetime.now(timezone.utc)
            self.store.finish_span(
                span_id=span.id,
                status="failed",
                ended_at=ended_at,
                duration_ms=duration_ms,
                error=f"{type(error).__name__}: {str(error)}",
            )

    def _calc_duration(self, run_id_str: str) -> float:
        start = self._start_times.get(run_id_str)
        if start is not None:
            return round((time.monotonic() - start) * 1000.0, 2)
        return 0.0

    def _get_execution_id(self) -> str:
        if self._created_execution:
            return self._created_execution.id
        current = get_current_execution()
        if current:
            return current.id
        return "exec_unknown"

    def _find_parent_span_id(self, parent_run_id_str: Optional[str]) -> Optional[str]:
        if parent_run_id_str and parent_run_id_str in self._run_spans:
            return parent_run_id_str
        if self._active_node_ids:
            return self._active_node_ids[-1]
        current_span = get_current_span()
        return current_span.id if current_span else self._root_run_id
