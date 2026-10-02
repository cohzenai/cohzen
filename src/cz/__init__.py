"""cz - Cohzen CLI & Runtime Observability Engine."""

from cz.execution import execution_scope, observe, record_reason, span_scope, track
from cz.execution.debugger import run_isolated_node

__version__ = "0.2.0"

# Auto-activate tracking when cz is imported
try:
    track()
except Exception:
    pass

# Aliases
reason = record_reason
debug_node = run_isolated_node

__all__ = [
    "__version__",
    "observe",
    "track",
    "execution_scope",
    "span_scope",
    "record_reason",
    "reason",
    "debug_node",
    "run_isolated_node",
]
