"""Small, dependency-free project marker and runtime configuration helpers."""

import os
from pathlib import Path

DEFAULT_CONFIG = """enabled = true
capture_in_ci = false

[retention]
max_payload_bytes = 65536
max_runs = 1000
max_age_days = 30
"""


def find_project(start: Path | None = None) -> Path | None:
    """Find a project marker, honoring ``COHZEN_PROJECT`` when supplied."""
    override = os.environ.get("COHZEN_PROJECT")
    candidates = [Path(override)] if override else [start or Path.cwd()]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        for directory in [resolved, *resolved.parents]:
            if (directory / ".cohzen").is_dir():
                return directory
    return None


def load_config(project: Path) -> dict[str, object]:
    """Read Cohzen's intentionally small TOML subset without importing TOML packages."""
    config: dict[str, object] = {
        "enabled": True,
        "capture_in_ci": False,
        "max_payload_bytes": 65_536,
        "max_runs": 1_000,
        "max_age_days": 30,
    }
    path = project / ".cohzen" / "config.toml"
    if not path.is_file():
        return config
    section = ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return config
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, raw = (part.strip() for part in line.split("=", 1))
        if section == "retention" and key in {"max_payload_bytes", "max_runs", "max_age_days"}:
            try:
                config[key] = int(raw)
            except ValueError:
                pass
        elif section == "" and key in {"enabled", "capture_in_ci"}:
            config[key] = raw.lower() == "true"
    return config
