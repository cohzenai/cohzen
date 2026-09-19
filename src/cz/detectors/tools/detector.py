"""Tool detector for agentic tools in Python AST."""

from __future__ import annotations

import ast
from typing import List, Optional, Set
from cz.scanner.utils import get_decorator_names
from cz.scanner.models import ToolDef


class ToolDetector:
    """Detects tool definitions, telemetry wrappers, and docstrings."""

    def __init__(self, tool_decorators: Optional[Set[str]] = None) -> None:
        self.tool_decorators = tool_decorators or {"tool"}

    def detect_tool(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        known_telemetry_decorators: Optional[Set[str]] = None,
    ) -> Optional[ToolDef]:
        """Inspect a function definition and return ToolDef if decorated as a tool."""
        decorators = get_decorator_names(node.decorator_list)
        is_tool = any(d in self.tool_decorators for d in decorators)
        if not is_tool:
            return None

        docstring = ast.get_docstring(node)
        line_start = node.lineno
        line_end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else line_start

        known_telemetry = (known_telemetry_decorators or set()) | {"traceable", "observe"}
        telemetry_decorators = [d for d in decorators if d in known_telemetry]
        is_instrumented = len(telemetry_decorators) > 0

        return ToolDef(
            name=node.name,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            docstring=docstring,
            has_tool_decorator=True,
            is_instrumented=is_instrumented,
            telemetry_decorators=telemetry_decorators,
        )
