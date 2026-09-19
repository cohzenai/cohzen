"""Base protocol for observability and telemetry tool plugins."""

from __future__ import annotations

from typing import List, Optional, Protocol
from cz.scanner.models import ObservabilityPackage


class BaseObservabilityDetector(Protocol):
    """Protocol for an observability tool detector."""

    @property
    def provider_id(self) -> str:
        """Internal provider identifier (e.g. 'langsmith', 'langfuse')."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable display name (e.g. 'LangSmith', 'Langfuse')."""
        ...

    @property
    def category(self) -> str:
        """Category (e.g. 'LLM Tracing & Evaluation', 'Distributed Tracing')."""
        ...

    def check_manifest(self, manifest_content: str, filename: str) -> Optional[ObservabilityPackage]:
        """Check if this tool's package is listed in a dependency manifest."""
        ...

    def get_known_env_vars(self) -> List[str]:
        """List of environment variable keys associated with this tool."""
        ...

    def get_known_decorators(self) -> List[str]:
        """List of AST decorator names indicating tracing (e.g. 'traceable', 'observe')."""
        ...
