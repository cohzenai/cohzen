"""Google Gemini / Vertex AI LLM call and tools detector."""

from __future__ import annotations

import ast
from typing import List, Optional
from cz.scanner.utils import ast_to_str, extract_list_of_strings
from cz.scanner.models import LLMCallSite, ToolsBoundInfo


class GoogleDetector:
    """Detects Google GenAI / Gemini calls and tool bindings."""

    def __init__(self) -> None:
        self.provider_name = "google"

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> Optional[LLMCallSite]:
        func_str = ast_to_str(call.func)
        if "generate_content" in func_str or "generate_text" in func_str or "generate_content_async" in func_str:
            model_name = None
            tools_list: List[str] = []
            arg_summary = ast_to_str(call.args[0]) if call.args else None

            for kw in call.keywords:
                if kw.arg == "model":
                    model_name = ast_to_str(kw.value).strip("'\"")
                elif kw.arg == "tools":
                    tools_list = extract_list_of_strings(kw.value)

            caller = func_str.split(".generate")[0]
            method = "generate_content" if "generate_content" in func_str else "generate_text"
            return LLMCallSite(
                provider="google",
                caller_var=caller,
                method=method,
                model_name=model_name,
                input_arg=arg_summary,
                tools_bound=tools_list,
                file_path=file_path,
                line_number=lineno,
            )
        return None

    def detect_tools_bound(
        self, targets: List[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> Optional[ToolsBoundInfo]:
        return None
