"""Unit tests for individual modular observability provider detectors."""

import pytest
from cz.audit.agentops import AgentOpsDetector
from cz.audit.arize_phoenix import ArizePhoenixDetector
from cz.audit.langfuse import LangfuseDetector
from cz.audit.langsmith import LangSmithDetector
from cz.audit.opentelemetry import OpenTelemetryDetector
from cz.audit.traceloop import TraceloopDetector
from cz.audit.wandb import WandBDetector


def test_individual_observability_detectors():
    detectors = [
        LangSmithDetector(),
        LangfuseDetector(),
        OpenTelemetryDetector(),
        ArizePhoenixDetector(),
        TraceloopDetector(),
        AgentOpsDetector(),
        WandBDetector(),
    ]

    for d in detectors:
        assert d.provider_id
        assert d.display_name
        assert d.category
        assert len(d.get_known_env_vars()) > 0
        assert len(d.get_known_decorators()) > 0


def test_manifest_matching_across_providers():
    langsmith_det = LangSmithDetector()
    pkg = langsmith_det.check_manifest("langsmith>=0.1.0\n", "requirements.txt")
    assert pkg is not None
    assert pkg.name == "LangSmith"

    langfuse_det = LangfuseDetector()
    pkg2 = langfuse_det.check_manifest('"langfuse": "^2.0.0"', "package.json")
    assert pkg2 is not None
    assert pkg2.name == "Langfuse"

    agentops_det = AgentOpsDetector()
    pkg3 = agentops_det.check_manifest("agentops==0.3.0", "requirements.txt")
    assert pkg3 is not None
    assert pkg3.name == "AgentOps"
