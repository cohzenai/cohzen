"""OpenTelemetry / OpenInference observability provider detector."""

from __future__ import annotations

import re
from typing import List, Optional
from cz.scanner.models import ObservabilityPackage

OTEL_PACKAGES = [
    "openinference-instrumentation-langchain",
    "openinference-instrumentation-openai",
    "openinference-semantic-conventions",
    "opentelemetry-api",
    "opentelemetry-sdk",
]


class OpenTelemetryDetector:
    def __init__(self) -> None:
        self.provider_id = "opentelemetry"
        self.display_name = "OpenTelemetry"
        self.category = "Distributed Tracing"

    def check_manifest(self, manifest_content: str, filename: str) -> Optional[ObservabilityPackage]:
        for pkg_name in OTEL_PACKAGES:
            pattern = rf"(?i)(?:^|[\"'\s,])({re.escape(pkg_name)})(?:\[[^\]]*\])?([><=~!].*)?(?:$|[\"'\s,\n])"
            match = re.search(pattern, manifest_content, re.MULTILINE)
            if match:
                version_spec = match.group(2).strip() if match.group(2) else None
                name = "OpenTelemetry API" if "api" in pkg_name else "OpenInference LangChain" if "langchain" in pkg_name else self.display_name
                return ObservabilityPackage(
                    name=name,
                    provider_id=self.provider_id,
                    category=self.category,
                    source_file=filename,
                    version_spec=version_spec,
                )
        return None

    def get_known_env_vars(self) -> List[str]:
        return ["OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_SERVICE_NAME", "OTEL_TRACES_EXPORTER"]

    def get_known_decorators(self) -> List[str]:
        return ["instrument", "trace"]
