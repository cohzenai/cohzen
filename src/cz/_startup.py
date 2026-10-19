"""Minimal always-on bootstrap loaded from Cohzen's active-environment .pth file."""

from __future__ import annotations

import builtins
import os
import sys
from pathlib import Path
from typing import Any

from cz.project import find_project, load_config

_ORIGINAL_IMPORT = builtins.__import__
_INSTALLED = False
_ACTIVATED = False
_NOTICE_EMITTED = False


def _in_ci() -> bool:
    return any(os.environ.get(name) for name in ("CI", "GITHUB_ACTIONS", "BUILD_NUMBER", "BUILD_ID"))


def _notice(message: str) -> None:
    global _NOTICE_EMITTED
    if not _NOTICE_EMITTED:
        _NOTICE_EMITTED = True
        try:
            print(f"cohzen: {message}", file=sys.stderr)
        except Exception:
            pass


def _eligible_project() -> Path | None:
    if os.environ.get("COHZEN_DISABLE") == "1" or os.environ.get("COHZEN_ENV") == "production":
        return None
    script = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path.cwd()
    # A console entry point inside a virtualenv is not an application script.
    script_project = None
    if not {"bin", "Scripts", "site-packages"}.intersection(script.parts):
        script_project = find_project(script.parent)
    project = script_project or find_project(Path.cwd())
    if not project:
        return None
    config = load_config(project)
    if not config["enabled"] or (_in_ci() and not config["capture_in_ci"]):
        return None
    return project


def _activate() -> None:
    global _ACTIVATED
    if _ACTIVATED:
        return
    _ACTIVATED = True
    try:
        builtins.__import__ = _ORIGINAL_IMPORT
    except Exception:
        pass
    try:
        from importlib.metadata import version

        major, minor, *_ = (int(part) for part in version("langgraph").split(".")[:2])
        if not ((major == 1 and 0 <= minor <= 2) or (major == 0 and minor == 2)):
            _notice("LangGraph version is outside the tested 0.2/1.0–1.2 range; capture is off")
            return
        from cz.execution.instrumentation import install

        install(project=_eligible_project())
    except Exception:
        # Startup instrumentation must never alter the target process's behavior.
        return


def _cohzen_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    module = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    if name == "langgraph" or name.startswith("langgraph."):
        try:
            _activate()
        except Exception:
            pass
    return module


def start() -> None:
    """Install a lazy import check only after cheap marker/config checks pass."""
    global _INSTALLED
    try:
        if _INSTALLED or not _eligible_project():
            return
        if "langgraph" in sys.modules:
            _activate()
            return
        builtins.__import__ = _cohzen_import
        _INSTALLED = True
    except Exception:
        return
