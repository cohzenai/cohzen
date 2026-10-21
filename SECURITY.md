# Security Policy

Cohzen takes the security and privacy of developer systems, source code, and telemetry data seriously.

---

## Supported Versions

Security fixes and patches are applied to the latest release line and the main branch:

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| < 0.2.0 | :x:                |

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please use one of the following private channels:

1. **GitHub Private Vulnerability Reporting (Preferred)**:
   Navigate to the repository's **Security** tab, click **Advisories**, and select **Report a vulnerability**. This creates a private draft advisory where we can discuss the issue confidentially.
2. **Email**:
   Send an encrypted or direct email to **security@cohzen.ai** with the subject `[SECURITY] Cohzen Vulnerability Report`.

Please include:
- A description of the vulnerability and its potential impact.
- Steps to reproduce or a minimal proof-of-concept.
- The version of Cohzen, Python, and operating system used.

### Response Expectations
Cohzen is maintained part-time by a solo builder. You can expect an initial acknowledgement within **48 to 72 hours**. If confirmed, a fix will be developed, tested, and released as a patch release alongside a coordinated disclosure advisory.

---

## Local Telemetry & Data Handling

Cohzen is designed to be **privacy-first and local-first**.

### What Cohzen Stores Locally
When always-on capture or `cz capture` is active, Cohzen records:
- **Graph Metadata**: Graph IDs, execution timestamps, duration in milliseconds, and status (`completed`, `failed`, `cancelled`).
- **Span Hierarchy**: Node names, LLM model calls, tool executions, and step durations.
- **Payloads**: State inputs and outputs passed through graph nodes.

### Where Data is Stored
All execution telemetry is persisted strictly in a **local SQLite database** within your project directory:
```text
your-project/
└── .cohzen/
    ├── config.toml       # Local retention and capture configuration
    ├── manifest.json     # Architecture manifest
    └── executions.db     # Local SQLite database
```

### Zero Telemetry Egress
**Cohzen's CLI does not phone home.** The CLI does not transmit source code, prompts, state values, or run data to external servers or cloud backends. External communication (such as GitHub Actions PR comments or future telemetry export) is strictly opt-in and under user control.

### Automatic Secret Redaction
Before any data is written to the local SQLite database, it passes through Cohzen's built-in redaction processor:
1. **Key Masking**: Any dict key matching sensitive terms (including `password`, `token`, `secret`, `api_key`, `authorization`, `private_key`) has its value replaced with `"[REDACTED]"`.
2. **Pattern Redaction**: Regex scanners detect and redact common secret formats from strings, including:
   - Bearer authentication headers (`Bearer ...`)
   - OpenAI API keys (`sk-proj-...`)
   - GitHub Personal Access Tokens (`ghp_...`)
   - AWS Access Key IDs (`AKIA...`)
   - Google API Keys (`AIza...`)
   - Private key blocks (`-----BEGIN PRIVATE KEY-----`)
   - Email addresses and phone numbers

### Retention & Size Limits
To prevent unbounded disk usage, Cohzen enforces configurable limits via `.cohzen/config.toml`:
- `max_payload_bytes`: Caps individual persisted payload fields (default: `65536` bytes / 64 KiB). Payloads exceeding this are truncated with `_cohzen_truncated: true`.
- `max_runs`: Retains a rolling window of executions (default: `1000` runs).
- `max_age_days`: Automatically purges runs older than the threshold (default: `30` days).

### Limitations
- **Heuristic Pattern Matching**: While Cohzen redacts common credential patterns, heuristic regex scanners cannot guarantee 100% detection of arbitrary proprietary tokens, internal passwords, or confidential business data embedded inside unstructured LLM prompt text.
- **Development vs. Production**: Always-on capture is intended for **local development and testing**. It automatically disables itself when `COHZEN_ENV=production` or `COHZEN_DISABLE=1` is set.
