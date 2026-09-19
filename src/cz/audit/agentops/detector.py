"""AgentOps observability provider detector."""

from __future__ import annotations

import re
from typing import List, Optional
from cz.scanner.models import ObservabilityPackage


class AgentOpsDetector:
    def __init__(self) -> None:
        self.provider_id = "agentops"
        self.display_name = "AgentOps"
        self.category = "Agent Monitoring & Replay"

    def check_manifest(self, manifest_content: str, filename: str) -> Optional[ObservabilityPackage]:
        pattern = r"(?i)(?:^|[\"'\s,])(agentops)(?:\[[^\]]*\])?([><=~!].*)?(?:$|[\"'\s,\n])"
        match = re.search(pattern, manifest_content, re.MULTILINE)
        if match:
            version_spec = match.group(2).strip() if match.group(2) else None
            return ObservabilityPackage(
                name=self.display_name,
                provider_id=self.provider_id,
                category=self.category,
                source_file=filename,
                version_spec=version_spec,
            )
        return None

    def get_known_env_vars(self) -> List[str]:
        return ["AGENTOPS_API_KEY"]

    def get_known_decorators(self) -> List[str]:
        return ["record_action", "track_agent"]
