# Supported Frameworks & Detectors

Cohzen v0.1 focuses authoritatively on **LangGraph**.

---

## 1. LangGraph Support (v0.1)

| Feature | Detection Capability | Status |
| :--- | :--- | :--- |
| **Graph Types** | `StateGraph`, `MessageGraph`, `Graph` | ✅ Full Static Support |
| **Nodes** | `add_node(name, fn)`, `add_node(fn)` | ✅ Full Static Support |
| **Inline Lambdas** | `add_node(name, lambda ...)` | ✅ Full Static Support |
| **Direct Edges** | `add_edge(start, end)`, `set_entry_point()`, `set_finish_point()` | ✅ Full Static Support |
| **Conditional Edges** | `add_conditional_edges(src, fn, mapping)` | ✅ Full Static Support |
| **ToolNodes** | `ToolNode(tools)`, inline `ToolNode` nodes | ✅ Full Static Support |
| **Subgraphs** | Parent graphs embedding child workflow nodes | ✅ Full Static Support |
| **Compilation** | `.compile(checkpointer=..., interrupt_before=...)` | ✅ Full Static Support |
| **Checkpointers** | `MemorySaver`, `SqliteSaver`, custom checkpointers | ✅ Full Static Support |

---

## 2. LLM Providers (v0.1 Frozen Scope)

Cohzen detects model declarations, tool bindings (`bind_tools`), and call sites across:
- **OpenAI**: `OpenAI()`, `AsyncOpenAI()`, `chat.completions.create`
- **Anthropic**: `Anthropic()`, `AsyncAnthropic()`, `messages.create`
- **Google**: `genai.Client()`, `GenerativeModel()`
- **Groq**: `Groq()`, `AsyncGroq()`
- **xAI Grok**: `Client(base_url="api.x.ai")`
- **LiteLLM**: `completion()`, `acompletion()`
- **LangChain / LangGraph Models**: `ChatOpenAI`, `ChatAnthropic`, `init_chat_model`, `.bind_tools()`, `.invoke()`

---

## 3. Observability Audit Providers

- **LangSmith**: `@traceable`, `LANGCHAIN_TRACING_V2=true`
- **Langfuse**: `@observe`, `LANGFUSE_PUBLIC_KEY`
- **OpenTelemetry API**: `@tracer.start_as_current_span`
- **Arize Phoenix**: `openinference-instrumentation-*`
- **Traceloop / OpenLLMetry**: `traceloop-sdk`
- **AgentOps**: `agentops.record_function`
- **W&B Weave**: `@weave.op()`

---

## Roadmap

Future releases of Cohzen will extend static architecture reconstruction to:
- LlamaIndex Workflows
- CrewAI
- AutoGen
