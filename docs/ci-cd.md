# 🛡️ CI/CD Integration Guide: Cohzen Agent Gate

Cohzen (`cz`) provides first-class CI/CD support to ensure that AI agent architectures, routing topologies, and observability configurations remain governed and healthy across every commit and pull request.

---

## ⚡ Quickstart: Add Cohzen to Your GitHub Actions

To attach Cohzen directly to your repository's CI/CD pipeline, create `.github/workflows/agent-ci.yml`:

```yaml
name: Agent CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write # Required for posting/updating the sticky architecture report

jobs:
  code-quality:
    name: Lint & Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install ruff pytest pytest-cov
          pip install -e ".[dev]"

      - name: Run Ruff Lint & Format
        run: |
          ruff check .
          ruff format --check .

      - name: Run Pytest
        run: pytest

  cohzen-gate:
    name: Cohzen Architecture & Telemetry Audit
    needs: code-quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Cohzen Agent Gate
        uses: cohzenai/cohzen@v0.3.1 # or uses: ./ if vendored
        with:
          path: "."
          min-coverage: "80" # Enforce 80% node/tool telemetry coverage
          fail-on-missing-telemetry: "true" # Fail if no telemetry is configured
          comment-pr: "true" # Post architecture flowchart to PR
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## ⚙️ Action Inputs & Configuration

| Input | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `path` | string | `.` | Directory or repository path to scan and audit. |
| `min-coverage` | number | `""` | Minimum required node/tool instrumentation percentage (0–100). Fails the build if below threshold. |
| `fail-on-missing-telemetry`| boolean | `false` | When `true`, fails if no LLM observability package or environment config is detected. |
| `export-manifest` | boolean | `true` | Uploads `cz-manifest.json` as a GitHub Actions build artifact. |
| `export-mermaid` | boolean | `true` | Uploads `cz-architecture.mmd` as a build artifact. |
| `comment-pr` | boolean | `true` | Posts or updates a sticky comment on pull requests with the architecture report. |
| `github-token` | string | `${{ github.token }}` | GitHub token with `pull-requests: write` permission for PR comments. |
| `python-version` | string | `3.11` | Python runtime version. |

---

## 📤 Action Outputs

| Output | Description |
| :--- | :--- |
| `total-graphs` | Number of agentic workflows/graphs detected. |
| `total-nodes` | Total number of registered agent/node handlers. |
| `total-tools` | Total number of `@tool` definitions detected. |
| `instrumentation-pct` | Actual telemetry instrumentation percentage. |
| `manifest-path` | Path to generated `cz-manifest.json`. |
| `mermaid-path` | Path to generated `cz-architecture.mmd`. |

---

## 🖥️ Running Locally or in Other CI Systems

You can also run the exact same checks locally or in GitLab CI / CircleCI via the `cz` CLI:

```bash
# 1. Audit observability with minimum 80% coverage threshold
cz audit . --min-coverage 80 --fail-on-missing

# 2. Emit JSON audit for downstream machine consumption
cz audit . --json -o audit-report.json

# 3. Export architecture manifest and Mermaid diagram
cz scan . --json -o manifest.json
cz scan . --mermaid -o architecture.mmd
```
