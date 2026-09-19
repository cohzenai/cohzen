"""LLM detector registry coordinating provider detectors."""

from __future__ import annotations

import ast
from typing import List, Optional

from cz.scanner.models import LLMCallSite, ToolsBoundInfo
from cz.detectors.llm.anthropic import AnthropicDetector
from cz.detectors.llm.base import BaseLLMDetector
from cz.detectors.llm.google import GoogleDetector
from cz.detectors.llm.grok import GrokDetector
from cz.detectors.llm.groq import GroqDetector
from cz.detectors.llm.langchain import LangChainLLMDetector
from cz.detectors.llm.litellm import LiteLLMDetector
from cz.detectors.llm.openai import OpenAIDetector


class LLMRegistry:
    """Registry maintaining active LLM call and tool binding detectors."""

    def __init__(self) -> None:
        self._detectors: List[BaseLLMDetector] = [
            OpenAIDetector(),
            AnthropicDetector(),
            GoogleDetector(),
            GroqDetector(),
            GrokDetector(),
            LangChainLLMDetector(),
            LiteLLMDetector(),
        ]

    def register(self, detector: BaseLLMDetector) -> None:
        self._detectors.append(detector)

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> Optional[LLMCallSite]:
        for detector in self._detectors:
            site = detector.detect_call(call, file_path, lineno)
            if site:
                return site
        return None

    def detect_tools_bound(
        self, targets: List[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> Optional[ToolsBoundInfo]:
        for detector in self._detectors:
            bound = detector.detect_tools_bound(targets, value, file_path, lineno)
            if bound:
                return bound
        return None
