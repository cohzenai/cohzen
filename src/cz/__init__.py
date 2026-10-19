"""cz - Cohzen CLI & Runtime Observability Engine."""

from typing import Any

__version__ = "0.3.0"


def __getattr__(name: str) -> Any:
    """Keep package import cheap for the always-on ``.pth`` startup hook."""
    if name in {"execution_scope", "observe", "record_reason", "span_scope", "track"}:
        from cz import execution

        return getattr(execution, name)
    if name == "reason":
        from cz.execution import record_reason

        return record_reason
    raise AttributeError(name)


__all__ = [
    "__version__",
    "execution_scope",
    "observe",
    "reason",
    "record_reason",
    "span_scope",
    "track",
]
