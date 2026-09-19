"""Base protocol for LLM call and tool binding detectors."""

from __future__ import annotations

import ast
from typing import List, Optional, Protocol
from cz.scanner.models import LLMCallSite, ToolsBoundInfo


class BaseLLMDetector(Protocol):
    """Protocol for detecting LLM calls and tool bindings for a specific LLM provider."""

    @property
    def provider_name(self) -> str:
        """Identifier for the provider (e.g. 'openai', 'anthropic', 'google', 'groq', 'grok', 'langchain', 'litellm')."""
        ...

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> Optional[LLMCallSite]:
        """Inspect an AST Call node and return an LLMCallSite if this provider was invoked."""
        ...

    def detect_tools_bound(
        self, targets: List[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> Optional[ToolsBoundInfo]:
        """Inspect an assignment to detect if tools were bound to a model."""
        ...
