"""Observability registry coordinating tool plugins, manifest audits, and env checks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set

from cz.scanner.models import AgentDef, ObservabilityAudit, ObservabilityPackage, ToolDef
from cz.audit.agentops import AgentOpsDetector
from cz.audit.arize_phoenix import ArizePhoenixDetector
from cz.audit.base import BaseObservabilityDetector
from cz.audit.langfuse import LangfuseDetector
from cz.audit.langsmith import LangSmithDetector
from cz.audit.opentelemetry import OpenTelemetryDetector
from cz.audit.traceloop import TraceloopDetector
from cz.audit.wandb import WandBDetector


class ObservabilityRegistry:
    """Registry maintaining active observability and telemetry detectors."""

    def __init__(self) -> None:
        self._detectors: List[BaseObservabilityDetector] = [
            LangSmithDetector(),
            LangfuseDetector(),
            OpenTelemetryDetector(),
            ArizePhoenixDetector(),
            TraceloopDetector(),
            AgentOpsDetector(),
            WandBDetector(),
        ]

    def register(self, detector: BaseObservabilityDetector) -> None:
        self._detectors.append(detector)

    def get_all_known_decorators(self) -> Set[str]:
        decorators = set()
        for d in self._detectors:
            decorators.update(d.get_known_decorators())
        return decorators

    def scan_manifests(self, repo_path: Path) -> List[ObservabilityPackage]:
        packages: List[ObservabilityPackage] = []
        manifest_files = [
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "Pipfile",
        ]

        seen_providers: Set[str] = set()

        for filename in manifest_files:
            file_path = repo_path / filename
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for detector in self._detectors:
                if detector.provider_id in seen_providers:
                    continue
                pkg = detector.check_manifest(content, filename)
                if pkg:
                    packages.append(pkg)
                    seen_providers.add(detector.provider_id)

        return packages

    def scan_env_files(self, repo_path: Path) -> List[str]:
        known_env_vars: Set[str] = set()
        for d in self._detectors:
            known_env_vars.update(d.get_known_env_vars())

        detected_vars: Set[str] = set()
        env_files = [".env", ".env.example", ".env.local", ".env.sample"]

        for env_name in env_files:
            env_file = repo_path / env_name
            if not env_file.is_file():
                continue

            try:
                lines = env_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key = line.split("=", 1)[0].strip()
                if key in known_env_vars:
                    detected_vars.add(key)

        for var in known_env_vars:
            if os.environ.get(var):
                detected_vars.add(var)

        return sorted(list(detected_vars))

    def resolve_tool_for_decorator(self, decorator: str) -> Optional[str]:
        """Returns the display name of the observability tool associated with a decorator."""
        dec_clean = decorator.lstrip("@").strip()
        for detector in self._detectors:
            for known in detector.get_known_decorators():
                if dec_clean == known or dec_clean.startswith(f"{known}.") or dec_clean.endswith(f".{known}"):
                    return detector.display_name
        return None

    def get_tool_for_decorators(self, decorators: List[str]) -> Optional[str]:
        """Returns the first matching observability tool name for a list of decorators."""
        for dec in decorators:
            tool = self.resolve_tool_for_decorator(dec)
            if tool:
                return tool
        return None

    def audit(
        self,
        repo_path: Path,
        agents: List[AgentDef],
        tools: List[ToolDef],
    ) -> ObservabilityAudit:
        packages = self.scan_manifests(repo_path)
        env_vars = self.scan_env_files(repo_path)

        total_agents = len(agents)
        instrumented_agents = sum(1 for a in agents if a.is_instrumented)

        total_tools = len(tools)
        instrumented_tools = sum(1 for t in tools if t.is_instrumented)

        # Collect all active observability tools detected across packages, env vars, and code decorators
        tools_detected: Set[str] = set()
        for p in packages:
            tools_detected.add(p.name)
        for detector in self._detectors:
            if any(e in env_vars for e in detector.get_known_env_vars()):
                tools_detected.add(detector.display_name)
        for a in agents:
            for dec in a.telemetry_decorators:
                t_name = self.resolve_tool_for_decorator(dec)
                if t_name:
                    tools_detected.add(t_name)
        for t in tools:
            for dec in t.telemetry_decorators:
                t_name = self.resolve_tool_for_decorator(dec)
                if t_name:
                    tools_detected.add(t_name)

        sorted_tools_detected = sorted(list(tools_detected))

        recommendations: List[str] = []
        has_langsmith = any(p.provider_id == "langsmith" for p in packages) or "LangSmith" in tools_detected
        has_langsmith_env = "LANGCHAIN_TRACING_V2" in env_vars

        if not packages and not env_vars and not tools_detected:
            recommendations.append("No LLM observability package, environment configuration, or tracing decorators detected in repository.")

        if "LangSmith" in tools_detected and not has_langsmith_env:
            recommendations.append("LangSmith tracing detected, but 'LANGCHAIN_TRACING_V2=true' was not found in .env files.")

        uninstrumented_agents_with_llm = [
            a.name for a in agents if a.llm_calls and not a.is_instrumented
        ]
        if uninstrumented_agents_with_llm:
            names = ", ".join(f"'{n}'" for n in uninstrumented_agents_with_llm[:3])
            if len(uninstrumented_agents_with_llm) > 3:
                names += f" and {len(uninstrumented_agents_with_llm) - 3} more"
            recommendations.append(
                f"Agent(s) {names} perform LLM calls but lack function-level tracing decorators (e.g. @traceable or @observe)."
            )

        if total_tools > 0 and instrumented_tools == 0 and tools_detected:
            recommendations.append("Tools are defined but none have telemetry instrumentation enabled.")

        return ObservabilityAudit(
            packages=packages,
            env_vars=env_vars,
            tools_detected=sorted_tools_detected,
            total_agents=total_agents,
            instrumented_agents=instrumented_agents,
            total_tools=total_tools,
            instrumented_tools=instrumented_tools,
            recommendations=recommendations,
        )
