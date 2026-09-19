"""Framework scanner registry coordinating active framework detectors."""

from __future__ import annotations

from typing import List
from cz.detectors.base import BaseFrameworkScanner
from cz.detectors.langgraph.scanner import LangGraphScanner


class FrameworkRegistry:
    """Registry maintaining active agentic framework scanners."""

    def __init__(self) -> None:
        self._scanners: List[BaseFrameworkScanner] = [
            LangGraphScanner(),
        ]

    def register(self, scanner: BaseFrameworkScanner) -> None:
        self._scanners.append(scanner)

    def get_all(self) -> List[BaseFrameworkScanner]:
        return self._scanners

    def reset_all(self, file_path: str) -> None:
        for scanner in self._scanners:
            scanner.reset(file_path)


__all__ = ["FrameworkRegistry"]
