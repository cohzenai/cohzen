# Versioning & Deprecation Policy

Cohzen follows [Semantic Versioning 2.0.0](https://semver.org/) (`MAJOR.MINOR.PATCH`).

---

## Semantic Versioning Rules

### 1. PATCH Releases (`0.3.x`)
PATCH releases contain backward-compatible bug fixes and non-breaking improvements:
- AST parsing precision enhancements and scanner bug fixes.
- Internal telemetry writer optimizations.
- Dependency updates and security patches.
- Documentation additions and clarifications.

### 2. MINOR Releases (`0.x.0` / `x.Y.0`)
MINOR releases introduce new features in a backward-compatible manner:
- New CLI commands (e.g. `cz status`, `cz on`, `cz off`).
- Additive manifest fields or new detector plugins (e.g. new LLM provider, new observability vendor).
- Deprecation notices for existing behaviors or flags.
- Support for new Python versions or major LangGraph versions.

### 3. MAJOR Releases (`X.0.0`)
MAJOR releases contain breaking changes to user-facing or integration contracts:
- Breaking changes to the CLI argument signatures or exit codes.
- Breaking modifications to the serialized `CohzenManifest` schema (`version: "0.2.0"` or higher).
- Breaking changes to runtime capture database schemas requiring manual migrations.
- Dropping support for deprecated Python runtimes.

---

## Deprecation Policy

We respect our users' time and production stability:

1. **Advance Notice**: Any feature, command, or hook mechanism slated for deprecation will be marked as deprecated in at least **one MINOR release** before removal.
2. **Runtime & Log Warnings**: Deprecated features will output actionable console or log warnings indicating what replacement to use.
3. **Automated Migration**: Where feasible, Cohzen provides automated cleanup and migration paths (for example, `cz init` automatically cleans up legacy `sitecustomize.py` blocks and replaces deprecated `.pth` files).
4. **Removal**: Deprecated functionality will only be completely removed in the subsequent major or minor milestone after adequate warning.

---

## Contract Stability

| Contract | Current Version | Stability Guarantee |
|---|---|---|
| **CLI Exit Codes** | `0` (clean), `1` (gate/audit failure), `2` (CLI error) | Stable across all minor releases. |
| **CohzenManifest Schema** | `0.1.0` | Schema is immutable. Future fields are strictly additive or require a bumped manifest schema version. |
| **Telemetry Database** | SQLite WAL | Tables (`runs`, `spans`, `events`) are versioned; additive columns are handled via automatic migrations. |
