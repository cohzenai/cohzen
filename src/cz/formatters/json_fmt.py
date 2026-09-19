"""JSON serialization formatter for cz scan results and manifests."""

from __future__ import annotations

from cz.scanner.models import ScanResult


def format_json(result: ScanResult, indent: int = 2, raw: bool = False) -> str:
    """Serializes scan results into pretty-printed JSON.

    By default (raw=False), serializes the standardized Cohzen Manifest v0.1.
    If raw=True, serializes the internal ScanResult object.
    """
    if raw:
        return result.model_dump_json(indent=indent)
    return result.to_manifest().model_dump_json(indent=indent)
