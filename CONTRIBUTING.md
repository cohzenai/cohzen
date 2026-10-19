# Contributing to Cohzen

Welcome, and thank you for your interest in contributing to **Cohzen (`cz`)**! Cohzen is an open-source, local-first toolkit that reconstructs, audits, and records LangGraph architectures.

This project is maintained part-time by a solo builder. We deeply appreciate community contributions—from bug fixes and documentation polish to new framework and observability detectors.

---

## Code of Conduct

All contributors and participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any concerns to **cohzen.ai@gmail.ai**.

---

## Prerequisites

- **Python 3.10, 3.11, 3.12, or 3.13**
- **Git**
- Recommended: [`uv`](https://docs.astral.sh/uv/) for fast virtualenv and dependency management, or standard `pip` / `venv`.

---

## Getting Started

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/cohzen.git
   cd cohzen
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in editable mode with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   # or with uv:
   # uv pip install -e ".[dev]"
   ```

4. **Verify tests pass locally**:
   ```bash
   pytest
   ```

---

## Finding Something to Work On

- **Good First Issues**: Check out our pre-scoped [Good First Issues](docs/good-first-issues.md) for self-contained tasks like adding new LLM detectors, CLI flags, or runnable examples.
- **Adding Detectors**: For adding support for new LLM clients or observability providers, see the step-by-step [Adding a Detector Guide](docs/adding-a-detector.md).
- **Roadmap**: See [ROADMAP.md](ROADMAP.md) for current priorities and planned framework integrations.

---

## Making a Change

### 1. Branch Naming
Create a feature or bugfix branch off `main`:
```bash
git checkout -b fix/issue-description
# or
git checkout -b feat/new-detector-name
```

### 2. Code Quality & Linting
Cohzen uses **[Ruff](https://docs.astral.sh/ruff/)** for fast linting and formatting. Run checks before committing:
```bash
# Check code for lint issues
ruff check .

# Automatically apply safe fixes
ruff check --fix .

# Verify formatting
ruff format --check .

# Auto-format files
ruff format .
```

### 3. Running the Test Suite
Ensure all tests pass and coverage remains healthy:
```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest --cov=cz --cov-report=term-missing tests/
```

---

## Developer Certificate of Origin (DCO) Sign-off

Cohzen uses the **Developer Certificate of Origin (DCO)** instead of a heavy Contributor License Agreement (CLA). The DCO is a simple statement certifying that you wrote the code or have the legal right to submit it under the project's **Apache 2.0 License**.

### How to Sign Off Your Commits
Simply add the `-s` (or `--signoff`) flag when making git commits:
```bash
git commit -s -m "feat(detector): add Mistral AI LLM detector"
```
This automatically appends a line to your commit message:
```text
Signed-off-by: Your Real Name <your.email@example.com>
```

### Fixing Unsigned Commits
If you forget `-s` on your latest commit, amend it:
```bash
git commit --amend --no-edit -s
```
If you have multiple commits in a PR branch, rebase interactively to sign off all commits:
```bash
git rebase --signoff origin/main
git push --force-with-lease
```

---

## Submitting a Pull Request

1. **Keep PRs Focused**: One PR per bug fix, feature, or detector. Smaller PRs are much easier and faster to review.
2. **Include Tests**: Add unit or integration tests in `tests/` covering new code or reproducing fixed bugs.
3. **Follow the PR Template**: When opening a PR, fill out the provided checklist in `.github/pull_request_template.md`.
4. **Ensure CI Passes**: All automated checks (linting, test suite across Python 3.10–3.13, and DCO sign-off) must pass.

---

## What Reviewers Look For

When reviewing pull requests, we look for:
- [x] Clear description of the problem and approach.
- [x] DCO sign-off on all commits.
- [x] Passing test suite without regressions.
- [x] Ruff linting and formatting compliance.
- [x] Preserved zero-overhead and fail-open guarantees (runtime code must never crash the user's application).
- [x] Accurate documentation or docstrings where applicable.

---

## Maintainer Response Expectations

Cohzen is maintained **part-time by a solo builder**:
- **Initial PR & Issue Triage**: Typically within **48 to 72 hours**.
- **Review Cycles**: You can expect thoughtful, constructive reviews. If a PR has been quiet for a few days, feel free to leave a polite comment to bump it.
- **Patience**: Complex feature requests or architectural proposals may take longer to discuss and test thoroughly.

Thank you for contributing to Cohzen!
