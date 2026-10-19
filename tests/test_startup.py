"""Tests for the dependency-free always-on startup decision path."""

from __future__ import annotations

import importlib
from pathlib import Path


def _reload_startup():
    module = importlib.import_module("cz._startup")
    return importlib.reload(module)


def test_startup_is_inert_without_marker(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COHZEN_PROJECT", raising=False)
    startup = _reload_startup()
    assert startup._eligible_project() is None


def test_startup_respects_disabled_config_and_project_override(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    marker = project / ".cohzen"
    marker.mkdir(parents=True)
    (marker / "config.toml").write_text("enabled = false\ncapture_in_ci = true\n", encoding="utf-8")
    monkeypatch.setenv("COHZEN_PROJECT", str(project))
    startup = _reload_startup()
    assert startup._eligible_project() is None


def test_startup_respects_disable_and_production(tmp_path: Path, monkeypatch):
    marker = tmp_path / ".cohzen"
    marker.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COHZEN_DISABLE", "1")
    startup = _reload_startup()
    assert startup._eligible_project() is None
    monkeypatch.delenv("COHZEN_DISABLE")
    monkeypatch.setenv("COHZEN_ENV", "production")
    assert startup._eligible_project() is None


def test_startup_fail_open_when_activation_is_broken(tmp_path: Path, monkeypatch):
    marker = tmp_path / ".cohzen"
    marker.mkdir()
    monkeypatch.chdir(tmp_path)
    startup = _reload_startup()
    monkeypatch.setattr(startup, "_activate", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
    # The import hook itself must not surface a Cohzen failure into the program.
    startup.start()
    try:
        __import__("langgraph")
    except RuntimeError as exc:  # pragma: no cover - assertion is clearer than swallowing
        raise AssertionError("Cohzen startup leaked an error") from exc
