# Release Checklist

This document is the release checklist for maintainers releasing a new version of `cohzen` to PyPI and GitHub.

---

## 1. Pre-Release Verification

Run the full local test suite and code quality linters:

```bash
# 1. Format and lint checks
uv run ruff check .
uv run ruff format --check .

# 2. Run test suite and coverage check
uv run pytest --cov=cz --cov-report=term-missing tests/

# 3. Verify CLI on bundled examples
uv run cz scan examples/langgraph-basic
uv run cz scan examples/langgraph-tools --json
uv run cz audit examples/langgraph-tools
```

All 114 tests must pass without regressions.

---

## 2. Version Bump & Changelog

1. **`pyproject.toml`**: Bump `version = "X.Y.Z"`.
2. **`src/cz/__init__.py`**: Update `__version__ = "X.Y.Z"`.
3. **`CHANGELOG.md`**:
   - Change `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`.
   - Add a fresh `## [Unreleased]` block at the top for future work.
4. **`README.md`**: Check that the support matrix and quickstarts reflect the new release.

---

## 3. Branch, Pull Request, & Merge

1. Create a release branch:
   ```bash
   git checkout -b release/vX.Y.Z
   git commit -sm "chore: prepare release vX.Y.Z"
   git push -u origin release/vX.Y.Z
   ```
2. Open a Pull Request into `main`.
3. Verify CI passes (tests across Python 3.10–3.13, DCO sign-off check, linting).
4. Merge the Pull Request into `main`.

---

## 4. Tagging & Publishing

Once `main` is updated:

```bash
git checkout main
git pull origin main

# Create annotated git tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# Push tag to GitHub
git push origin vX.Y.Z
```

Pushing the `v*` tag triggers the automated `.github/workflows/release.yml` workflow:
- Builds source distribution (`sdist`) and wheel (`bdist_wheel`) via `uv build`.
- Publishes packages to PyPI via Trusted Publishing (OIDC).
- Creates a GitHub Release with draft notes.

---

## 5. Post-Release Verification

1. **Verify on PyPI**: Inspect [https://pypi.org/project/cohzen/](https://pypi.org/project/cohzen/) to confirm the new version is live.
2. **Verify Installation**:
   ```bash
   pip install --upgrade cohzen
   cz version
   ```
3. **Verify GitHub Release**: Review and publish release notes on [GitHub Releases](https://github.com/cohzenai/cohzen/releases).
