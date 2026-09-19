"""cz LLMs package."""

from cz.detectors.llm.base import BaseLLMDetector
from cz.detectors.llm.registry import LLMRegistry

__all__ = ["BaseLLMDetector", "LLMRegistry"]
