"""Base detector protocols and classes."""

from __future__ import annotations

import ast
from typing import List, Optional, Protocol, Set
from cz.scanner.models import GraphInfo, LLMCallSite, ToolDef, ToolsBoundInfo


class BaseDetector(Protocol):
    """General base protocol for all AST detectors."""
    pass


class BaseFrameworkScanner(Protocol):
    """Protocol for scanning and detecting a specific agentic framework."""

    @property
    def framework_name(self) -> str:
        """Name of the framework (e.g. 'langgraph', 'crewai', 'openai_agents')."""
        ...

    def reset(self, file_path: str) -> None:
        """Reset internal visitor state for a new file."""
        ...

    def visit_assign(self, targets: List[ast.AST], value: ast.AST, lineno: int) -> None:
        """Called for Assign and AnnAssign AST nodes."""
        ...

    def visit_call(self, call: ast.Call, lineno: int) -> None:
        """Called for Expr(Call) AST nodes."""
        ...

    def visit_return(self, node: ast.Return) -> None:
        """Called for Return AST nodes."""
        ...

    def get_graphs(self) -> List[GraphInfo]:
        """Return all graphs detected in the current file."""
        ...


class BaseLLMDetector(Protocol):
    """Protocol for detecting LLM calls and tool bindings for an LLM provider."""

    @property
    def provider_name(self) -> str:
        """Identifier for the provider (e.g. 'openai', 'anthropic', 'google')."""
        ...

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> Optional[LLMCallSite]:
        """Inspect an AST Call node and return an LLMCallSite if this provider was invoked."""
        ...

    def detect_tools_bound(
        self, targets: List[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> Optional[ToolsBoundInfo]:
        """Inspect an assignment to detect if tools were bound to a model."""
        ...


class BaseToolDetector(Protocol):
    """Protocol for detecting tool definitions and tool nodes."""

    def detect_tool(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, known_decorators: Set[str]
    ) -> Optional[ToolDef]:
        """Inspect a function node to detect whether it is an agent tool."""
        ...
