"""Serialization utilities for telemetry, execution state, messages, and payloads."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from typing import Any, Dict, List, Optional


def serialize_for_storage(val: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
    """Recursively serialize arbitrary runtime objects into JSON-compatible primitives."""
    if current_depth > max_depth:
        return str(val)

    if val is None or isinstance(val, (int, float, bool, str)):
        return val

    if isinstance(val, (datetime, date)):
        return val.isoformat()

    # Handle LangChain BaseMessage instances (HumanMessage, AIMessage, SystemMessage, ToolMessage)
    if hasattr(val, "content") and (hasattr(val, "type") or hasattr(val, "additional_kwargs")):
        msg_type = getattr(val, "type", "message")
        msg_dict: Dict[str, Any] = {
            "role": _normalize_role(msg_type),
            "type": msg_type,
            "content": serialize_for_storage(getattr(val, "content", ""), max_depth, current_depth + 1),
        }
        name = getattr(val, "name", None)
        if name:
            msg_dict["name"] = name
        tool_calls = getattr(val, "tool_calls", None)
        if tool_calls:
            msg_dict["tool_calls"] = serialize_for_storage(tool_calls, max_depth, current_depth + 1)
        tool_call_id = getattr(val, "tool_call_id", None)
        if tool_call_id:
            msg_dict["tool_call_id"] = tool_call_id
        add_kwargs = getattr(val, "additional_kwargs", None)
        if add_kwargs and isinstance(add_kwargs, dict):
            # Clean additional_kwargs
            cleaned_kwargs = {k: serialize_for_storage(v, max_depth, current_depth + 1) for k, v in add_kwargs.items() if k != "refusal" or v is not None}
            if cleaned_kwargs:
                msg_dict["additional_kwargs"] = cleaned_kwargs
        resp_meta = getattr(val, "response_metadata", None)
        if resp_meta and isinstance(resp_meta, dict):
            msg_dict["response_metadata"] = serialize_for_storage(resp_meta, max_depth, current_depth + 1)
        return msg_dict

    # Handle Pydantic models (v1 and v2)
    if hasattr(val, "model_dump") and callable(val.model_dump):
        try:
            return serialize_for_storage(val.model_dump(mode="json"), max_depth, current_depth + 1)
        except Exception:
            pass
    if hasattr(val, "dict") and callable(val.dict):
        try:
            return serialize_for_storage(val.dict(), max_depth, current_depth + 1)
        except Exception:
            pass

    # Handle dictionaries
    if isinstance(val, dict):
        return {
            str(k): serialize_for_storage(v, max_depth, current_depth + 1)
            for k, v in val.items()
        }

    # Handle lists, tuples, sets
    if isinstance(val, (list, tuple, set)):
        return [serialize_for_storage(item, max_depth, current_depth + 1) for item in val]

    # Handle exceptions
    if isinstance(val, BaseException):
        return f"{type(val).__name__}: {str(val)}"

    # Handle arbitrary objects with __dict__
    if hasattr(val, "__dict__"):
        try:
            return {
                str(k): serialize_for_storage(v, max_depth, current_depth + 1)
                for k, v in val.__dict__.items()
                if not k.startswith("_")
            }
        except Exception:
            pass

    # Fallback to string representation
    return str(val)


def _normalize_role(msg_type: str) -> str:
    """Map LangChain message types to standard roles."""
    mapping = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
        "tool": "tool",
        "function": "function",
        "chat": "user",
    }
    return mapping.get(msg_type.lower(), msg_type)


def extract_llm_generation(response: Any) -> Dict[str, Any]:
    """Extract clean, structured output, tool calls, and token metrics from LLMResult / ChatResult."""
    result: Dict[str, Any] = {
        "generations": [],
        "text": "",
        "tool_calls": [],
        "token_usage": None,
    }

    if not response:
        return result

    # Extract token usage if available in llm_output
    if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
        token_usage = response.llm_output.get("token_usage")
        if token_usage:
            result["token_usage"] = serialize_for_storage(token_usage)

    # Extract generations
    if hasattr(response, "generations") and isinstance(response.generations, list):
        extracted_gens = []
        all_texts = []
        for group in response.generations:
            if not isinstance(group, (list, tuple)):
                group = [group]
            for gen in group:
                gen_dict: Dict[str, Any] = {}
                text = getattr(gen, "text", "")
                if hasattr(gen, "message"):
                    msg_obj = gen.message
                    serialized_msg = serialize_for_storage(msg_obj)
                    gen_dict["message"] = serialized_msg
                    if not text and isinstance(serialized_msg, dict):
                        text = serialized_msg.get("content", "")
                    # Extract tool calls from ChatGeneration
                    tool_calls = getattr(msg_obj, "tool_calls", None)
                    if tool_calls:
                        gen_dict["tool_calls"] = serialize_for_storage(tool_calls)
                        result["tool_calls"].extend(gen_dict["tool_calls"])
                gen_dict["text"] = text
                if text:
                    all_texts.append(text)
                extracted_gens.append(gen_dict)
        result["generations"] = extracted_gens
        result["text"] = "\n".join(all_texts) if all_texts else ""
    elif isinstance(response, str):
        result["text"] = response
        result["generations"] = [{"text": response}]
    else:
        serialized = serialize_for_storage(response)
        result["text"] = str(serialized)
        result["generations"] = [serialized]

    return result
