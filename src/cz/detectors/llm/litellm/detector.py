"""LiteLLM completion and tools detector."""

from __future__ import annotations

import ast

from cz.scanner.models import LLMCallSite, ToolsBoundInfo
from cz.scanner.utils import ast_to_str, extract_list_of_strings


class LiteLLMDetector:
    """Detects LiteLLM completion and acompletion calls."""

    def __init__(self) -> None:
        self.provider_name = "litellm"

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> LLMCallSite | None:
        func_str = ast_to_str(call.func)
        if func_str in (
            "litellm.completion",
            "litellm.acompletion",
            "completion",
            "acompletion",
        ):
            model_name = None
            tools_list: list[str] = []
            arg_summary = ast_to_str(call.args[0]) if call.args else None

            for kw in call.keywords:
                if kw.arg == "model":
                    model_name = ast_to_str(kw.value).strip("'\"")
                elif kw.arg == "tools":
                    tools_list = extract_list_of_strings(kw.value)

            method = "acompletion" if "acompletion" in func_str else "completion"
            return LLMCallSite(
                provider="litellm",
                caller_var="litellm",
                method=method,
                model_name=model_name,
                input_arg=arg_summary,
                tools_bound=tools_list,
                file_path=file_path,
                line_number=lineno,
            )
        return None

    def detect_tools_bound(
        self, targets: list[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> ToolsBoundInfo | None:
        return None
