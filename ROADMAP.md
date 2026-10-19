# Cohzen Project Roadmap

This roadmap outlines active priorities, near-term enhancements, and planned research areas for Cohzen. As a project maintained by a solo builder, priorities focus on correctness, developer ergonomics, and rock-solid stability before feature breadth.

---

## 🎯 Active & In Progress

- **LangGraph Always-On Local Capture (v0.2.x stabilization)**:
  - Validated multi-version LangGraph support matrix (`0.2.76`, `1.0.10`, `1.1.10`, `1.2.16`).
  - Zero-overhead, fail-open startup hooks (`cohzen_startup.pth`) via `cz init`.
  - Comprehensive local secret redaction and configurable retention policies (`.cohzen/config.toml`).
  - Asynchronous, bounded write queue to ensure zero latency impact on user graph execution.

- **Automated CI/CD Agent Quality Gates**:
  - Turnkey GitHub Action with sticky PR summaries and Mermaid diagram rendering.
  - Telemetry coverage scoring and threshold enforcement (`--min-coverage`).

---

## 📋 Near-Term Priorities (Next Releases)

- **Manifest Contract v0.2**:
  - Add optional runtime telemetry facts to the static manifest contract (`manifest.json`) without breaking v0.1 backwards compatibility.
- **Enhanced Node Debugger**:
  - Ergonomic local node state replay from recorded SQLite runs (`cz node run --from-run <id>`).
- **Additional Observability Detectors**:
  - Add detectors for emerging tracing libraries (e.g., OpenInference expansions, Datadog LLM observability).
- **Interactive Visualizer Polish**:
  - Expand `cz view` browser UI with real-time state inspection and search.

---

## 💡 Experimental / Exploratory Ideas

*The following ideas are conceptual proposals under research. Community feedback and detector pull requests are welcome.*

- **Multi-Framework Static Discovery**:
  - *LlamaIndex Workflows*: AST detection for event-driven LlamaIndex step functions.
  - *CrewAI*: Detection of Crews, Agents, and Task delegation pipelines.
  - *AutoGen*: ConversableAgent topologies and group chat managers.
- **OpenTelemetry Standard Export**:
  - Optional OTLP exporter to stream local captured spans directly into any OTLP-compliant collector.

---

## 🤝 Contributing to the Roadmap

Have an idea or need support for a specific LangGraph pattern or detector?
Please open a [Feature Request on GitHub](https://github.com/cohzenai/cohzen/issues/new?template=feature_request.md) or join [GitHub Discussions](https://github.com/cohzenai/cohzen/discussions).
