"""Unit tests for individual modular LLM provider detectors."""

import ast
import pytest
from cz.detectors.llm.openai import OpenAIDetector
from cz.detectors.llm.anthropic import AnthropicDetector
from cz.detectors.llm.google import GoogleDetector
from cz.detectors.llm.groq import GroqDetector
from cz.detectors.llm.grok import GrokDetector
from cz.detectors.llm.langchain import LangChainLLMDetector
from cz.detectors.llm.litellm import LiteLLMDetector


def _parse_call(code: str) -> ast.Call:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            return node
    raise ValueError("No call found")


def test_openai_detector_call_and_tools():
    detector = OpenAIDetector()
    call = _parse_call('client.chat.completions.create(model="gpt-4o", messages=[], tools=[search_tool])')
    site = detector.detect_call(call, "test.py", 10)

    assert site is not None
    assert site.provider == "openai"
    assert site.model_name == "gpt-4o"
    assert site.method == "create"
    assert site.tools_bound == ["search_tool"]


def test_anthropic_detector_call_and_tools():
    detector = AnthropicDetector()
    call = _parse_call('client.messages.create(model="claude-3-5-sonnet", messages=[], tools=[calc_tool])')
    site = detector.detect_call(call, "test.py", 12)

    assert site is not None
    assert site.provider == "anthropic"
    assert site.model_name == "claude-3-5-sonnet"
    assert site.tools_bound == ["calc_tool"]


def test_google_detector_call_and_tools():
    detector = GoogleDetector()
    call = _parse_call('model.generate_content("hello", tools=[weather_tool])')
    site = detector.detect_call(call, "test.py", 15)

    assert site is not None
    assert site.provider == "google"
    assert site.method == "generate_content"
    assert site.tools_bound == ["weather_tool"]


def test_groq_detector_call_and_tools():
    detector = GroqDetector()
    call = _parse_call('groq_client.chat.completions.create(model="llama3-70b", messages=[], tools=[t1])')
    site = detector.detect_call(call, "test.py", 20)

    assert site is not None
    assert site.provider == "groq"
    assert site.model_name == "llama3-70b"
    assert site.tools_bound == ["t1"]


def test_grok_detector_call_and_tools():
    detector = GrokDetector()
    call = _parse_call('xai_client.chat.completions.create(model="grok-beta", messages=[])')
    site = detector.detect_call(call, "test.py", 25)

    assert site is not None
    assert site.provider == "grok"
    assert site.model_name == "grok-beta"


def test_litellm_detector_call_and_tools():
    detector = LiteLLMDetector()
    call = _parse_call('litellm.completion(model="gpt-4o", messages=[], tools=[search_tool])')
    site = detector.detect_call(call, "test.py", 30)

    assert site is not None
    assert site.provider == "litellm"
    assert site.model_name == "gpt-4o"
    assert site.tools_bound == ["search_tool"]


def test_langchain_detector_call_and_bind_tools():
    detector = LangChainLLMDetector()
    call = _parse_call('model.invoke({"messages": []})')
    site = detector.detect_call(call, "test.py", 35)

    assert site is not None
    assert site.provider == "langchain"
    assert site.method == "invoke"
