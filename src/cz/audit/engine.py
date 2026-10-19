"""Audit engine evaluating repository observability and governance posture."""

from __future__ import annotations

from pathlib import Path

from cz.audit.registry import ObservabilityRegistry
from cz.scanner.models import (
    AgentDef,
    ObservabilityAudit,
    ObservabilityPackage,
    ToolDef,
)


class AuditEngine:
    """Engine executing observability audits against repositories and discovered components."""

    def __init__(self, registry: ObservabilityRegistry | None = None) -> None:
        self.registry = registry or ObservabilityRegistry()

    def scan_manifests(self, repo_path: Path) -> list[ObservabilityPackage]:
        """Scan dependency manifests for known observability tools."""
        return self.registry.scan_manifests(repo_path)

    def scan_env_files(self, repo_path: Path) -> list[str]:
        """Scan environment files for known telemetry variables."""
        return self.registry.scan_env_files(repo_path)

    def audit(self, repo_path: Path, agents: list[AgentDef], tools: list[ToolDef]) -> ObservabilityAudit:
        """Perform comprehensive observability audit across manifests, env, and code."""
        return self.registry.audit(repo_path, agents, tools)


_default_audit_engine = AuditEngine()


def audit_repository(repo_path: Path, agents: list[AgentDef], tools: list[ToolDef]) -> ObservabilityAudit:
    """Convenience function auditing a repository against detected agents and tools."""
    return _default_audit_engine.audit(repo_path, agents, tools)


def scan_manifest_files(repo_path: Path) -> list[ObservabilityPackage]:
    """Convenience helper scanning manifests for observability dependencies."""
    return _default_audit_engine.scan_manifests(repo_path)


def scan_env_files(repo_path: Path) -> list[str]:
    """Convenience helper scanning env files for observability variables."""
    return _default_audit_engine.scan_env_files(repo_path)


audit_observability = audit_repository

__all__ = [
    "AuditEngine",
    "audit_observability",
    "audit_repository",
    "scan_env_files",
    "scan_manifest_files",
]
