"""Tests for observability package detection, environment scanning, and telemetry gap analysis."""

from pathlib import Path
import pytest

from cz.scanner.models import AgentDef, LLMCallSite, ToolDef
from cz.audit import (
    audit_observability,
    scan_env_files,
    scan_manifest_files,
)


def test_manifest_file_detection(tmp_path: Path):
    pyproject_content = """
[project]
dependencies = [
    "langsmith>=0.1.20",
    "langfuse~=2.0.0",
    "opentelemetry-api",
    "arize-phoenix>=4.0",
]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    packages = scan_manifest_files(tmp_path)
    pkg_names = {p.name for p in packages}
    assert "LangSmith" in pkg_names
    assert "Langfuse" in pkg_names
    assert "OpenTelemetry API" in pkg_names
    assert "Arize Phoenix" in pkg_names

    # Check version spec captured
    langsmith_pkg = next(p for p in packages if p.name == "LangSmith")
    assert ">=0.1.20" in langsmith_pkg.version_spec


def test_env_file_detection(tmp_path: Path):
    env_content = """
# Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=test_key_123
LANGFUSE_PUBLIC_KEY=pk-lf-12345
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
"""
    (tmp_path / ".env").write_text(env_content)

    detected_vars = scan_env_files(tmp_path)
    assert "LANGCHAIN_TRACING_V2" in detected_vars
    assert "LANGCHAIN_API_KEY" in detected_vars
    assert "LANGFUSE_PUBLIC_KEY" in detected_vars
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in detected_vars


def test_observability_audit_gap_recommendations(tmp_path: Path):
    # Scenario: langsmith is installed, but LANGCHAIN_TRACING_V2 is NOT in .env,
    # and an agent makes an LLM call without @traceable
    (tmp_path / "requirements.txt").write_text("langsmith>=0.1.0\n")

    untraced_agent = AgentDef(
        name="billing_agent",
        file_path="billing.py",
        line_start=10,
        line_end=20,
        llm_calls=[
            LLMCallSite(
                caller_var="llm",
                method="invoke",
                file_path="billing.py",
                line_number=15,
            )
        ],
        is_instrumented=False,
    )

    traced_agent = AgentDef(
        name="support_agent",
        file_path="support.py",
        line_start=1,
        line_end=10,
        is_instrumented=True,
        telemetry_decorators=["traceable"],
    )

    untraced_tool = ToolDef(
        name="database_query",
        file_path="db.py",
        line_start=1,
        line_end=5,
        is_instrumented=False,
    )

    audit = audit_observability(
        tmp_path,
        agents=[untraced_agent, traced_agent],
        tools=[untraced_tool],
    )

    assert audit.is_observability_configured is True
    assert audit.total_agents == 2
    assert audit.instrumented_agents == 1
    assert audit.agent_instrumentation_pct == 50.0

    assert audit.total_tools == 1
    assert audit.instrumented_tools == 0

    # Recommendations checks
    rec_text = " ".join(audit.recommendations)
    # Flag: LANGCHAIN_TRACING_V2 not found
    assert "LANGCHAIN_TRACING_V2=true" in rec_text
    # Flag: billing_agent performs LLM calls but lacks tracing
    assert "billing_agent" in rec_text
    # Flag: Tools defined but uninstrumented
    assert "Tools are defined but none have telemetry instrumentation" in rec_text
