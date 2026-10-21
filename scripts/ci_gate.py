#!/usr/bin/env python3
"""Cohzen Agent CI/CD Gate Script.

Generates architecture manifest, Mermaid diagram, observability audit,
writes GitHub Actions Step Summary, optionally posts sticky PR comments,
and enforces telemetry compliance thresholds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cz.formatters.mermaid import format_mermaid, generate_graph_mermaid
from cz.scanner.engine import scan_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cohzen Agent CI/CD Gate")
    parser.add_argument("--path", default=".", help="Path to repository or project to scan")
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=None,
        help="Minimum required agent/node instrumentation percentage (0-100)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Fail if no telemetry packages or environment configurations are detected",
    )
    parser.add_argument(
        "--manifest-output",
        default="cz-manifest.json",
        help="Path to write CohzenManifest JSON",
    )
    parser.add_argument(
        "--mermaid-output",
        default="cz-architecture.mmd",
        help="Path to write Mermaid diagram",
    )
    parser.add_argument(
        "--audit-output",
        default="cz-audit.json",
        help="Path to write Observability Audit JSON",
    )
    parser.add_argument(
        "--summary-output",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="Path to write GitHub Step Summary markdown",
    )
    parser.add_argument(
        "--comment-pr",
        action="store_true",
        help="Post or update sticky PR comment",
    )
    parser.add_argument(
        "--github-token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub Token for PR comments",
    )
    return parser.parse_args()


def build_markdown_summary(result, manifest_dict: dict, audit_dict: dict, mermaid_code: str) -> str:
    obs = result.observability
    pct = obs.agent_instrumentation_pct if obs else 0.0
    configured = obs.is_observability_configured if obs else False

    status_badge = (
        "🟢 **PASSED**"
        if (configured and pct >= 80.0)
        else ("🟡 **WARNING**" if configured else "🔴 **ACTION REQUIRED**")
    )

    lines = [
        "## 🧠 Cohzen AI Agent Governance Report",
        "",
        f"**CI Status:** {status_badge}  |  **Target:** `{result.target_path}`  |  **Scanned Files:** {result.files_scanned} ({result.python_files_count} Python)",
        "",
        "### 📊 Architecture Overview",
        "",
        "| Metric | Count | Details |",
        "| :--- | :--- | :--- |",
        f"| **Workflows / Graphs** | `{len(result.graphs)}` | `{sum(1 for g in result.graphs if g.is_compiled)} compiled` |",
        f"| **Nodes / Handlers** | `{result.total_nodes}` | `{len(result.agent_definitions)} agent handlers, {len(result.tool_nodes)} ToolNodes` |",
        f"| **Direct & Conditional Edges** | `{sum(len(g.edges) for g in result.graphs)}` | Dynamic routing inspected |",
        f"| **Tools Bound** | `{len(result.tool_definitions)}` | `@tool` definitions detected |",
        f"| **LLM Call Sites** | `{sum(len(a.llm_calls) for a in result.agent_definitions)}` | Providers: OpenAI, Anthropic, Gemini, Groq, LiteLLM |",
        "",
        "### 🛰️ Observability & Telemetry Audit",
        "",
        f"- **Telemetry Configured:** {'✅ Yes' if configured else '❌ No telemetry packages or env configs detected'}",
        f"- **Agent Instrumentation Coverage:** **`{pct}%`** ({obs.instrumented_agents if obs else 0}/{obs.total_agents if obs else 0} nodes instrumented)",
        f"- **Tool Instrumentation Coverage:** **`{(round((obs.instrumented_tools / obs.total_tools) * 100, 1) if (obs and obs.total_tools) else 100.0)}%`** ({obs.instrumented_tools if obs else 0}/{obs.total_tools if obs else 0} tools instrumented)",
    ]

    if obs and obs.tools_detected:
        lines.append(f"- **Active Observability Tools:** {', '.join(f'`{t}`' for t in obs.tools_detected)}")
    if obs and obs.packages:
        pkg_strs = [f"`{p.name}` ({p.source_file})" for p in obs.packages]
        lines.append(f"- **Detected Packages:** {', '.join(pkg_strs)}")
    if obs and obs.env_vars:
        lines.append(f"- **Detected Env Vars:** {', '.join(f'`{v}`' for v in obs.env_vars)}")

    if obs and obs.recommendations:
        lines.extend(
            [
                "",
                "#### ⚠️ Recommendations & Gaps",
                "",
                *(f"- {r}" for r in obs.recommendations),
            ]
        )

    # Mermaid diagrams in collapsible blocks (one ```mermaid block per graph)
    lines.extend(
        [
            "",
            "### 🗺️ Architecture Flowchart",
            "",
        ]
    )

    if not result.graphs:
        lines.extend(
            [
                "<details open>",
                "<summary><b>Interactive LangGraph Architecture Diagram</b> (click to toggle)</summary>",
                "",
                "```mermaid",
                "%% No LangGraph workflows detected.",
                "```",
                "",
                "</details>",
                "",
            ]
        )
    elif len(result.graphs) == 1:
        clean_mermaid = generate_graph_mermaid(result.graphs[0], scan_result=result).strip()
        lines.extend(
            [
                "<details open>",
                "<summary><b>Interactive LangGraph Architecture Diagram</b> (click to toggle)</summary>",
                "",
                "```mermaid",
                clean_mermaid,
                "```",
                "",
                "</details>",
                "",
            ]
        )
    else:
        for idx, graph in enumerate(result.graphs, start=1):
            g_markup = generate_graph_mermaid(graph, scan_result=result).strip()
            title = f"Graph #{idx}: {graph.graph_var} ({graph.graph_class})"
            rel_path = Path(graph.file_path).name
            lines.extend(
                [
                    f"<details{' open' if idx == 1 else ''}>",
                    f"<summary><b>{title}</b> &mdash; <code>{rel_path}:{graph.line_number}</code></summary>",
                    "",
                    "```mermaid",
                    g_markup,
                    "```",
                    "",
                    "</details>",
                    "",
                ]
            )

    lines.extend(
        [
            "---",
            "*Report generated automatically by [Cohzen (`cz`)](https://github.com/cohzenai/cohzen)*",
        ]
    )

    return "\n".join(lines)


def post_or_update_pr_comment(body: str, token: str) -> None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.isfile(event_path):
        print("Not running in a GitHub Actions PR event context. Skipping PR comment.")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    pr_number = event.get("pull_request", {}).get("number")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not pr_number or not repo:
        print("Could not determine PR number or repository. Skipping PR comment.")
        return

    api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Cohzen-CI-Gate",
    }

    marker = "<!-- cohzen-agent-gate -->"
    comment_body = f"{marker}\n{body}"

    # Check for existing comment
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            comments = json.loads(resp.read().decode("utf-8"))

        existing_comment_id = None
        for c in comments:
            if marker in c.get("body", ""):
                existing_comment_id = c.get("id")
                break

        if existing_comment_id:
            update_url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
            update_data = json.dumps({"body": comment_body}).encode("utf-8")
            patch_req = urllib.request.Request(update_url, data=update_data, headers=headers, method="PATCH")
            with urllib.request.urlopen(patch_req) as resp:
                if resp.status == 200:
                    print(f"Updated existing Cohzen PR comment (ID: {existing_comment_id})")
        else:
            create_data = json.dumps({"body": comment_body}).encode("utf-8")
            post_req = urllib.request.Request(api_url, data=create_data, headers=headers, method="POST")
            with urllib.request.urlopen(post_req) as resp:
                if resp.status == 201:
                    print(f"Posted new Cohzen PR comment on PR #{pr_number}")
    except urllib.error.HTTPError as e:
        print(f"Failed to post/update PR comment: HTTP {e.code} - {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Error during PR comment sync: {e}", file=sys.stderr)


def main() -> None:
    args = parse_args()
    print(f"🧠 Scanning agent architecture and observability at: {args.path}")

    result = scan_repository(args.path)
    manifest = result.to_manifest()
    mermaid_code = format_mermaid(result)

    manifest_json = manifest.model_dump_json(indent=2)
    audit_json = result.observability.model_dump_json(indent=2) if result.observability else "{}"

    # 1. Write outputs
    if args.manifest_output:
        Path(args.manifest_output).write_text(manifest_json, encoding="utf-8")
        print(f"✔ Saved manifest to {args.manifest_output}")

    if args.mermaid_output:
        Path(args.mermaid_output).write_text(mermaid_code, encoding="utf-8")
        print(f"✔ Saved Mermaid diagram to {args.mermaid_output}")

    if args.audit_output:
        Path(args.audit_output).write_text(audit_json, encoding="utf-8")
        print(f"✔ Saved audit JSON to {args.audit_output}")

    # 2. Build Markdown Step Summary
    summary_md = build_markdown_summary(result, json.loads(manifest_json), json.loads(audit_json), mermaid_code)

    if args.summary_output:
        summary_path = Path(args.summary_output)
        with open(summary_path, "a" if summary_path.exists() else "w", encoding="utf-8") as f:
            f.write(summary_md + "\n")
        print(f"✔ Appended governance summary to {args.summary_output}")

    # 3. Post to PR if requested
    if args.comment_pr and args.github_token:
        post_or_update_pr_comment(summary_md, args.github_token)

    # 4. Set GitHub Actions outputs if GITHUB_OUTPUT is set
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"total_graphs={len(result.graphs)}\n")
            f.write(f"total_nodes={result.total_nodes}\n")
            f.write(f"total_tools={len(result.tool_definitions)}\n")
            f.write(
                f"instrumentation_pct={result.observability.agent_instrumentation_pct if result.observability else 0.0}\n"
            )
            f.write(f"manifest_path={args.manifest_output}\n")
            f.write(f"mermaid_path={args.mermaid_output}\n")

    # 5. Enforce CI Thresholds
    failed_reasons: list[str] = []
    obs = result.observability

    if args.fail_on_missing:
        if not obs or not obs.is_observability_configured:
            failed_reasons.append("No LLM observability package or environment config was detected.")

    if args.min_coverage is not None:
        pct = obs.agent_instrumentation_pct if obs else 0.0
        if pct < args.min_coverage:
            failed_reasons.append(
                f"Agent instrumentation coverage is {pct}%, below the required threshold of {args.min_coverage}%."
            )

    if failed_reasons:
        print("\n❌ CI Gate Enforcement Failed:", file=sys.stderr)
        for r in failed_reasons:
            print(f"   • {r}", file=sys.stderr)
        sys.exit(1)

    print("\n✅ All Cohzen agent architecture & governance checks passed!")


if __name__ == "__main__":
    main()
