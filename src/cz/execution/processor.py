"""Data processor and sensitive data redaction interface for Cohzen."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Protocol, Set


class DataProcessor(Protocol):
    """Protocol for transforming/sanitizing runtime inputs and outputs."""

    def process(self, value: Any) -> Any:
        """Process and optionally sanitize/redact a value before storage."""
        ...


class NoopProcessor:
    """Pass-through processor that leaves values unmodified."""

    def process(self, value: Any) -> Any:
        return value


class RedactionProcessor:
    """Processor that redacts known sensitive keys and credential patterns."""

    DEFAULT_SENSITIVE_KEYS: Set[str] = {
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "auth",
        "private_key",
        "client_secret",
        "credit_card",
        "ssn",
    }

    # Common API key and secret regex patterns
    KEY_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{30,}", re.IGNORECASE),
    ]

    def __init__(self, sensitive_keys: Optional[Set[str]] = None, mask: str = "[REDACTED]"):
        self.sensitive_keys = {k.lower() for k in (sensitive_keys or self.DEFAULT_SENSITIVE_KEYS)}
        self.mask = mask

    def process(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return self._process_dict(value)
        if isinstance(value, (list, tuple)):
            return [self.process(item) for item in value]
        if isinstance(value, str):
            return self._process_str(value)
        return value

    def _process_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, val in data.items():
            key_str = str(key).lower()
            if any(s in key_str for s in self.sensitive_keys):
                result[key] = self.mask
            else:
                result[key] = self.process(val)
        return result

    def _process_str(self, text: str) -> str:
        res = text
        for pattern in self.KEY_PATTERNS:
            res = pattern.sub(self.mask, res)
        return res
