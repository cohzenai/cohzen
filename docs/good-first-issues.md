# Good First Issues for External Contributors

These 5 issue drafts are pre-written for project maintainers to publish as GitHub Issues with the `good first issue` and `help wanted` labels upon open-source launch.

---

### Issue 1: Add Static AST Detector for Cohere (`cohere` Client)

- **Labels**: `good first issue`, `enhancement`, `detectors`
- **Difficulty**: Beginner
- **Title**: `feat(detectors): Add static LLM detector for Cohere Command models`
- **Description**:
  ```markdown
  ### Description
  Cohzen currently detects LLM invocations for OpenAI, Anthropic, Google, Groq, xAI Grok, and LiteLLM. We would like to add a static detector for the official Cohere Python SDK (`cohere.Client` / `cohere.ClientV2`).

  ### Scope & Implementation Details
  1. Follow the guide in [docs/adding-a-detector.md](adding-a-detector.md).
  2. Create `src/cz/detectors/llm/cohere/detector.py`:
     - Detect `cohere.Client` or `cohere.ClientV2` instantiation or call sites.
     - Match call sites like `client.chat(...)`, `client.chat_stream(...)`.
     - Extract model name (e.g., `"command-r-plus"`, `"command-r"`) and tools argument if passed.
  3. Register the detector in `src/cz/detectors/llm/registry.py`.
  4. Add unit test in `tests/test_detectors_llm.py` testing both constant model names and variable arguments.

  ### Acceptance Criteria
  - [ ] Passes `uv run pytest` and `uv run ruff check .`
  - [ ] DCO signed-off commit (`git commit -s`)
  ```

---

### Issue 2: Add Static AST Detector for Mistral AI (`mistralai` Client)

- **Labels**: `good first issue`, `enhancement`, `detectors`
- **Difficulty**: Beginner
- **Title**: `feat(detectors): Add static LLM detector for Mistral AI SDK`
- **Description**:
  ```markdown
  ### Description
  Add static AST detection for the Mistral AI Python SDK (`from mistralai import Mistral`).

  ### Scope & Implementation Details
  1. Follow [docs/adding-a-detector.md](adding-a-detector.md).
  2. Create `src/cz/detectors/llm/mistral/detector.py`:
     - Detect calls to `client.chat.complete(...)` and `client.chat.stream(...)`.
     - Extract `model` strings (e.g. `"mistral-large-latest"`, `"codestral-latest"`) and `tools=[...]`.
  3. Register in `src/cz/detectors/llm/registry.py`.
  4. Add unit tests in `tests/test_detectors_llm.py`.

  ### Acceptance Criteria
  - [ ] Detects Mistral model calls without executing user code
  - [ ] All tests pass cleanly (`pytest`)
  - [ ] Signed-off commit (`git commit -s`)
  ```

---

### Issue 3: Add Output File Option (`--output` / `-o`) to `cz audit`

- **Labels**: `good first issue`, `cli`, `dx`
- **Difficulty**: Beginner
- **Title**: `feat(cli): Add -o / --output flag to cz audit command`
- **Description**:
  ```markdown
  ### Description
  `cz scan` supports writing output directly to a file via `-o` / `--output` (e.g. `cz scan . --json -o manifest.json`). Currently, `cz audit . --json` prints to stdout and requires shell redirection (`> audit.json`).

  ### Scope & Implementation Details
  1. In `src/cz/cli/main.py`, update the `audit` command definition to accept an optional `--output` / `-o` option:
     ```python
     output: Annotated[Optional[Path], typer.Option("-o", "--output", help="Write audit report to file")] = None
     ```
  2. If specified, write the JSON or Markdown report to the target file path.
  3. Add test coverage in `tests/test_cli.py` verifying that `--output report.json` writes valid JSON to disk.

  ### Acceptance Criteria
  - [ ] `cz audit . --json -o audit.json` writes valid JSON to the specified path
  - [ ] Unit test added in `tests/test_cli.py`
  - [ ] Code formatted and linted with Ruff
  ```

---

### Issue 4: Add Static Observability Detector for OpenInference LangGraph

- **Labels**: `good first issue`, `audit`, `observability`
- **Difficulty**: Beginner
- **Title**: `feat(audit): Detect openinference-instrumentation-langchain package in cz audit`
- **Description**:
  ```markdown
  ### Description
  `cz audit` checks repository dependencies and environment variables for telemetry frameworks. Many teams using OpenTelemetry instrument LangGraph/LangChain via `openinference-instrumentation-langchain`.

  ### Scope & Implementation Details
  1. In `src/cz/audit/opentelemetry/detector.py`:
     - Check package manifests (`pyproject.toml`, `requirements.txt`, etc.) for `openinference-instrumentation-langchain` or `openinference-instrumentation-dspy`.
     - Detect calls to `LangChainInstrumentor().instrument()`.
  2. Mark nodes and tools as instrumented when OpenInference is present and configured.
  3. Add a test in `tests/test_audit.py`.

  ### Acceptance Criteria
  - [ ] `cz audit` reports OpenInference under detected OpenTelemetry integrations
  - [ ] All test suites pass
  ```

---

### Issue 5: Add Runnable Example for LangGraph Human-in-the-Loop (`interrupt`)

- **Labels**: `good first issue`, `documentation`, `examples`
- **Difficulty**: Beginner
- **Title**: `docs(examples): Add runnable Human-in-the-loop example in examples/`
- **Description**:
  ```markdown
  ### Description
  Cohzen's scanner detects human-in-the-loop interrupt points (`interrupt_before`, `interrupt_after`, and `langgraph.types.interrupt`). We would like a clean, runnable example demonstrating this pattern in `examples/`.

  ### Scope & Implementation Details
  1. Create `examples/langgraph-human-in-the-loop/`:
     - `app.py`: Simple 2-node graph using `interrupt_before=["approval_node"]` with `MemorySaver`.
     - `README.md`: Explaining the flow and how to run `cz scan .` and `cz audit .` on it.
  2. Verify with `cz scan examples/langgraph-human-in-the-loop/` and ensure the interrupt points appear in the terminal output and manifest.
  3. Add a test assertion in `tests/test_examples.py` (or `test_scanner.py`) asserting that the example graph is discovered with interrupts detected.

  ### Acceptance Criteria
  - [ ] Self-contained, runnable example without external credentials
  - [ ] Verified by `cz scan`
  ```
