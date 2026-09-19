# `cz` Architecture & Design Decisions

This document details the modular, extensible architecture of the `cz` CLI package.

---

## 1. Architectural Philosophy

`cz` is designed as an extensible, multi-framework static scanner for AI agentic applications. To ensure maintainability, testability, and zero cross-contamination, the codebase is partitioned into isolated domain plugins:

```
┌────────────────────────────────────────────────────────┐
│                        cz CLI                          │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Master Engine                       │
│  - Directory walker (respects .git, venv, node_modules)│
│  - Orchestrates Registries                             │
└─────────────┬─────────────┬─────────────┬──────────────┘
              │             │             │
              ▼             ▼             ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│FrameworkRegistry │ │ LLMRegistry  │ │ObservabilityReg. │
│- langgraph/      │ │- openai/     │ │- langsmith/      │
│- (future crewai) │ │- anthropic/  │ │- langfuse/       │
│- (future adk)    │ │- google/     │ │- opentelemetry/  │
│                  │ │- groq/       │ │- arize_phoenix/  │
│                  │ │- grok/       │ │- traceloop/      │
│                  │ │- langchain/  │ │- agentops/       │
│                  │ │- litellm/    │ │- wandb/          │
└──────────────────┘ └──────────────┘ └──────────────────┘
```

---

## 2. Domain Registries

### A. Frameworks (`src/cz/frameworks/`)
- Protocol: `BaseFrameworkScanner` (defines `visit_assign`, `visit_call`, `visit_return`, `get_graphs`).
- Primary Implementation: `src/cz/frameworks/langgraph/`
  - `scanner.py`: Extracts `StateGraph`, `Graph`, `MessageGraph`, nodes, direct edges, conditional edges, `ToolNode`, and `.compile()`.
  - `models.py`: LangGraph-specific models and aliases.
- Extensibility: Adding a new framework (e.g. CrewAI or Google ADK) requires only creating a folder in `src/cz/frameworks/` and implementing `BaseFrameworkScanner`.

### B. LLM Provider Detectors (`src/cz/llms/`)
- Protocol: `BaseLLMDetector` (defines `detect_call` and `detect_tools_bound`).
- Each provider lives in its own folder:
  - `openai/`: Detects `client.chat.completions.create`, models, and `tools=[...]`.
  - `anthropic/`: Detects `client.messages.create`, models, and `tools=[...]`.
  - `google/`: Detects `generate_content`, `generate_text`, models, and `tools=[...]`.
  - `groq/`: Detects Groq client completions, models, and `tools=[...]`.
  - `grok/`: Detects xAI Grok completions.
  - `langchain/`: Detects `.invoke()`, `.ainvoke()`, `.stream()`, and `model.bind_tools(tools)`.
  - `litellm/`: Detects `completion()`, `acompletion()`, models, and `tools=[...]`.

### C. Observability Providers (`src/cz/observability/`)
- Protocol: `BaseObservabilityDetector` (defines `check_manifest`, `get_known_env_vars`, `get_known_decorators`).
- Each tool lives in its own folder:
  - `langsmith/`
  - `langfuse/`
  - `opentelemetry/`
  - `arize_phoenix/`
  - `traceloop/`
  - `agentops/`
  - `wandb/`
- The `ObservabilityRegistry` computes coverage metrics and generates gap analysis.

---

## 3. How to Extend

### Adding a New LLM Provider
1. Create `src/cz/llms/<provider_name>/detector.py`.
2. Implement `detect_call(call, file_path, lineno)` returning `Optional[LLMCallSite]`.
3. Register the detector in `src/cz/llms/registry.py`.

### Adding a New Observability Tool
1. Create `src/cz/observability/<tool_name>/detector.py`.
2. Define `provider_id`, `display_name`, `check_manifest`, `get_known_env_vars`, and `get_known_decorators`.
3. Register the detector in `src/cz/observability/registry.py`.

### Adding a New Agentic Framework
1. Create `src/cz/frameworks/<framework_name>/scanner.py`.
2. Implement `BaseFrameworkScanner`.
3. Register in `src/cz/frameworks/registry.py`.
