# Guide: Adding a New Detector to Cohzen

Cohzen is designed to be easily extensible. If you use an LLM provider, tool library, or observability platform that Cohzen does not yet recognize, you can add a detector in a few clean steps.

Because Cohzen operates **100% via static AST analysis**, detectors inspect Python code structure without ever importing, running, or executing target code.

---

## The Three Detector Categories

1. **LLM Detectors (`src/cz/detectors/llm/`)**: Identify LLM client call sites (`chat.completions.create`, `messages.create`) and model tool bindings (`model.bind_tools(...)`).
2. **Observability Detectors (`src/cz/audit/`)**: Audit package manifests (`pyproject.toml`, `requirements.txt`), environment variables (`.env`), and tracing decorators (`@traceable`, `@observe`).
3. **Tool Detectors (`src/cz/detectors/tools/`)**: Identify agent tools (such as `@tool` decorated functions) and audit their telemetry coverage.

---

## 1. Adding an LLM Provider Detector

Let's walk through adding support for a new provider (for example, **Mistral AI**).

### Step 1: Create the Detector Module
Create a new directory and detector file: `src/cz/detectors/llm/mistral/detector.py`.

```python
"""Mistral AI LLM and tool binding detector."""

from __future__ import annotations

import ast
from cz.scanner.models import LLMCallSite, ToolsBoundInfo
from cz.scanner.utils import extract_string_literal


class MistralDetector:
    """Detects Mistral client invocations and tool bindings."""

    @property
    def provider_name(self) -> str:
        return "mistral"

    def detect_call(self, call: ast.Call, file_path: str, lineno: int) -> LLMCallSite | None:
        """Match client.chat.complete(...) or client.chat.stream(...)."""
        func = call.func
        if not isinstance(func, ast.Attribute) or func.attr not in ("complete", "stream"):
            return None

        # Check caller is chat attribute (e.g. client.chat.complete)
        value = func.value
        if not isinstance(value, ast.Attribute) or value.attr != "chat":
            return None

        # Extract model argument from keywords: complete(model="mistral-large-latest", ...)
        model_name = "unknown"
        for kw in call.keywords:
            if kw.arg == "model":
                extracted = extract_string_literal(kw.value)
                if extracted:
                    model_name = extracted
                break

        return LLMCallSite(
            provider="mistral",
            model=model_name,
            file_path=file_path,
            lineno=lineno,
            has_tools=any(kw.arg == "tools" for kw in call.keywords),
        )

    def detect_tools_bound(
        self, targets: list[ast.AST], value: ast.AST, file_path: str, lineno: int
    ) -> ToolsBoundInfo | None:
        """Detect tool bindings if the provider has a dedicated binding method."""
        return None
```

Create `src/cz/detectors/llm/mistral/__init__.py`:
```python
from cz.detectors.llm.mistral.detector import MistralDetector

__all__ = ["MistralDetector"]
```

### Step 2: Register the Detector
In `src/cz/detectors/llm/registry.py`:
1. Import `MistralDetector`.
2. Instantiate and add it to `self._detectors` in `LLMDetectorRegistry.__init__`:
   ```python
   from cz.detectors.llm.mistral import MistralDetector


   class LLMDetectorRegistry:
       def __init__(self) -> None:
           self._detectors: list[BaseLLMDetector] = [
               OpenAIDetector(),
               AnthropicDetector(),
               # ...
               MistralDetector(),
           ]
   ```

### Step 3: Write Unit Tests
In `tests/test_llm_providers.py`, add a test verifying detection of your provider's calls:
```python
def test_mistral_detector(tmp_path: Path):
    code = """
from mistralai import Mistral

client = Mistral(api_key="secret")
res = client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": "hello"}])
"""
    f = tmp_path / "app.py"
    f.write_text(code, encoding="utf-8")
    result = scan_python_file(str(f))

    assert len(result.models) == 1
    assert result.models[0].provider == "mistral"
    assert result.models[0].name == "mistral-large-latest"
```

---

## 2. Adding an Observability / Telemetry Detector

Let's walk through adding an audit detector for an observability tool (for example, **Datadog LLM Observability**).

### Step 1: Create the Detector Module
Create `src/cz/audit/datadog/detector.py`:

```python
"""Datadog LLM Observability audit detector."""

from __future__ import annotations

import re
from cz.scanner.models import ObservabilityPackage


class DatadogDetector:
    """Detects Datadog ddtrace package, environment variables, and tracing decorators."""

    @property
    def provider_id(self) -> str:
        return "datadog"

    @property
    def display_name(self) -> str:
        return "Datadog"

    @property
    def category(self) -> str:
        return "APM & LLM Observability"

    def check_manifest(self, manifest_content: str, filename: str) -> ObservabilityPackage | None:
        pattern = r"(?i)(?:^|[\"'\s,])(ddtrace)(?:\[[^\]]*\])?([><=~!].*)?(?:$|[\"'\s,\n])"
        match = re.search(pattern, manifest_content)
        if match:
            return ObservabilityPackage(
                name="ddtrace",
                version_spec=match.group(2).strip() if match.group(2) else None,
                manifest_file=filename,
            )
        return None

    def get_known_env_vars(self) -> list[str]:
        return ["DD_API_KEY", "DD_LLMOBS_ENABLED", "DD_LLMOBS_AGENT_NAME"]

    def get_known_decorators(self) -> list[str]:
        return ["llmobs.llm", "llmobs.workflow", "llmobs.agent", "llmobs.tool"]
```

Create `src/cz/audit/datadog/__init__.py`:
```python
from cz.audit.datadog.detector import DatadogDetector

__all__ = ["DatadogDetector"]
```

### Step 2: Register in the Audit Registry
In `src/cz/audit/registry.py`:
1. Import `DatadogDetector`.
2. Add an instance to `self._detectors`:
   ```python
   from cz.audit.datadog import DatadogDetector


   class ObservabilityRegistry:
       def __init__(self) -> None:
           self._detectors: list[BaseObservabilityDetector] = [
               LangSmithDetector(),
               LangfuseDetector(),
               # ...
               DatadogDetector(),
           ]
   ```

### Step 3: Write Audit Tests
In `tests/test_observability_providers.py`:
```python
def test_datadog_audit_detection(tmp_path: Path):
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("ddtrace>=2.10.0\n", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("DD_LLMOBS_ENABLED=1\nDD_API_KEY=xxx\n", encoding="utf-8")

    result = audit_repository(str(tmp_path))
    datadog = next((t for t in result.tools if t.provider_id == "datadog"), None)

    assert datadog is not None
    assert datadog.package_installed is True
    assert datadog.env_configured is True
```

---

## 3. Adding a Tool Decorator

If your project uses a custom tool decorator (for example, `@action` or `@agent_tool` alongside `@tool`):

1. Inspect `src/cz/detectors/tools/detector.py`.
2. Add your decorator name to `self.tool_decorators` (or pass it during scanner initialization):
   ```python
   class ToolDetector:
       def __init__(self, tool_decorators: set[str] | None = None) -> None:
           self.tool_decorators = tool_decorators or {"tool", "agent_tool"}
   ```
3. Add a test in `tests/test_tools_and_nodes.py` verifying that functions decorated with `@agent_tool` are parsed into `ToolDef` objects with source locations and docstrings.

---

## Testing & Quality Checklist

Before opening a pull request with a new detector:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code is formatted and linted: `ruff check .` and `ruff format .`
- [ ] Commits are signed off: `git commit -s` (DCO)
- [ ] No external runtime dependencies were added (keep static AST analysis lightweight).
