"""Data processor and sensitive data redaction interface for Cohzen."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol


class DataProcessor(Protocol):
    """Protocol for transforming/sanitizing runtime inputs and outputs."""

    def process(self, value: Any) -> Any:
        """Process and optionally sanitize/redact a value before storage."""
        ...


class NoopProcessor:
    """Pass-through processor that leaves values unmodified."""

    def process(self, value: Any) -> Any:
        return value


class PayloadLimiter:
    """Snapshot and bound payloads before they enter an asynchronous writer queue."""

    def __init__(self, max_payload_bytes: int | None = 65_536):
        self.max_payload_bytes = max_payload_bytes

    def process(self, value: Any) -> Any:
        if self.max_payload_bytes is None:
            return value
        encoded = json.dumps(value, default=str, ensure_ascii=False).encode("utf-8")
        if len(encoded) <= self.max_payload_bytes:
            return value
        if isinstance(value, str):
            preview = value.encode("utf-8")[: max(0, self.max_payload_bytes - 48)].decode("utf-8", "ignore")
            return f"{preview}[TRUNCATED: {len(encoded)} bytes]"
        return {"_cohzen_truncated": True, "original_bytes": len(encoded), "max_payload_bytes": self.max_payload_bytes}


class RedactionProcessor:
    """Redact sensitive values and bound a persisted payload's size.

    Redaction happens before size limiting, so a truncated value cannot leak a
    credential in its preview. ``max_payload_bytes`` applies independently to
    every value passed to :meth:`process`.
    """

    DEFAULT_SENSITIVE_KEYS: set[str] = {
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
        re.compile(r"sk-(?:[a-z0-9]+-)?[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{30,}", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        re.compile(r"(?:xox[baprs]-)[a-zA-Z0-9-]{10,}", re.IGNORECASE),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)"),
    ]

    def __init__(
        self,
        sensitive_keys: set[str] | None = None,
        mask: str = "[REDACTED]",
        max_payload_bytes: int | None = 65_536,
    ):
        self.sensitive_keys = {k.lower() for k in (sensitive_keys or self.DEFAULT_SENSITIVE_KEYS)}
        self.mask = mask
        self.max_payload_bytes = max_payload_bytes

    def process(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            processed = self._process_dict(value)
        elif isinstance(value, (list, tuple)):
            processed = [self.process(item) for item in value]
        elif isinstance(value, str):
            processed = self._process_str(value)
        else:
            processed = value
        return self._limit(processed)

    def _process_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key, val in data.items():
            key_str = str(key).lower()
            if self._is_sensitive_key(key_str):
                result[key] = self.mask
            else:
                result[key] = self.process(val)
        return result

    def _is_sensitive_key(self, key: str) -> bool:
        """Avoid treating safe operational fields such as ``token_usage`` as secrets."""
        return key in self.sensitive_keys or key.endswith(
            ("_api_key", "_secret", "_password", "_token", "_private_key")
        )

    def _process_str(self, text: str) -> str:
        res = text
        for pattern in self.KEY_PATTERNS:
            res = pattern.sub(self.mask, res)
        return res

    def _limit(self, value: Any) -> Any:
        """Return a deterministic marker when a JSON-serializable payload is too large."""
        if self.max_payload_bytes is None:
            return value
        encoded = json.dumps(value, default=str, ensure_ascii=False).encode("utf-8")
        if len(encoded) <= self.max_payload_bytes:
            return value
        if isinstance(value, str):
            preview_bytes = max(0, self.max_payload_bytes - 48)
            preview = value.encode("utf-8")[:preview_bytes].decode("utf-8", errors="ignore")
            return f"{preview}[TRUNCATED: {len(encoded)} bytes]"
        return {
            "_cohzen_truncated": True,
            "original_bytes": len(encoded),
            "max_payload_bytes": self.max_payload_bytes,
        }
