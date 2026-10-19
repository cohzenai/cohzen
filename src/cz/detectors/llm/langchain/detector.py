"""LangChain model call and bind_tools detector."""

from __future__ import annotations

import ast

from cz.scanner.models import LLMCallSite, ToolsBoundInfo
from cz.scanner.utils import ast_to_str, extract_list_of_strings

KNOWN_LANGCHAIN_METHODS = {
    "invoke",
    "ainvoke",
    "stream",
    "astream",
    "batch",
    "abatch",
    "generate",
}


class LangChainLLMDetector:
    """Detects LangChain model invocations and bind_tools calls."""

    def __init__(self) -> None:
        self.provider_name = "langchain"

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> LLMCallSite | None:
        if isinstance(call.func, ast.Attribute) and call.func.attr in KNOWN_LANGCHAIN_METHODS:
            caller = ast_to_str(call.func.value)
            caller_lower = caller.lower()
            if caller_lower in (
                "runner",
                "clirunner",
                "cli_runner",
                "app",
                "context",
                "ctx",
            ) or caller_lower.endswith("runner"):
                return None
            arg_summary = ast_to_str(call.args[0]) if call.args else None
            return LLMCallSite(
                provider="langchain",
                caller_var=caller,
                method=call.func.attr,
                input_arg=arg_summary,
                file_path=file_path,
                line_number=lineno,
            )
        return None

    def detect_tools_bound(
        self, targets: list[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> ToolsBoundInfo | None:
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            if value.func.attr == "bind_tools":
                callee_var = ast_to_str(value.func.value)
                assigned_var = ast_to_str(targets[0]) if targets else None
                model_var = callee_var if isinstance(value.func.value, ast.Name) else (assigned_var or callee_var)
                raw_tools = []
                if value.args:
                    raw_tools = extract_list_of_strings(value.args[0])
                for kw in value.keywords:
                    if kw.arg == "tools":
                        raw_tools = extract_list_of_strings(kw.value)

                return ToolsBoundInfo(
                    model_var=model_var,
                    tools=raw_tools,
                    provider="langchain",
                    file_path=file_path,
                    line_number=lineno,
                )
        return None
