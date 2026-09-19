# Development Guide

This guide covers local environment setup, testing standards, and architecture guidelines for developers contributing to Cohzen.

---

## Local Setup

1. **Prerequisites**: Python 3.10, 3.11, or 3.12.
2. **Clone & Virtualenv**:
   ```bash
   git clone https://github.com/cohzen-ai/cohzen.git
   cd cohzen
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Editable Package**:
   ```bash
   pip install -e ".[dev]"
   ```

---

## Testing

Cohzen maintains a comprehensive test suite covering detectors, formats, and real-world repository fixtures.

Run all tests:
```bash
pytest tests/ -v
```

Run test coverage report:
```bash
pytest --cov=cz --cov-report=term-missing tests/
```

Run a specific test file:
```bash
pytest tests/test_cli.py -v
```

---

## CLI Testing Against Examples

Test CLI commands against the bundled example repositories:

```bash
cz scan examples/langgraph-basic
cz scan examples/langgraph-tools --json
cz scan examples/langgraph-routing --mermaid
cz audit examples/langgraph-tools
```

---

## Project Structure Guidelines

- `src/cz/cli/`: CLI entrypoints, Typer command definitions, argument parsing.
- `src/cz/scanner/`: AST traversal engine, visitor dispatch, cross-referencing.
- `src/cz/detectors/`: Modular AST detectors separated by concern (`langgraph`, `llm`, `tools`).
- `src/cz/manifest/`: Authoritative Pydantic schemas for the system contract.
- `src/cz/audit/`: Telemetry inspection, package manifest checks, and gap analysis.
- `src/cz/formatters/`: Output generation (Rich console, Mermaid, HTML viewer, JSON).
