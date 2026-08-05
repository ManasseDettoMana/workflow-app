"""Where the data directory resolves to, and how it is overridden."""

from __future__ import annotations

from pathlib import Path

from workflowapp.core import paths


def test_the_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path))
    monkeypatch.setenv("APPDATA", r"C:\Users\qualcuno\AppData\Roaming")
    assert paths.data_dir() == tmp_path


def test_appdata_is_used_when_there_is_no_override(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.DATA_DIR_ENV, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.data_dir() == tmp_path / "WorkflowApp"


def test_there_is_a_fallback_when_appdata_is_unset(monkeypatch):
    # Keeps the function total: importing this module must not depend on the
    # environment being Windows-shaped.
    monkeypatch.delenv(paths.DATA_DIR_ENV, raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    assert paths.data_dir() == Path.home() / ".workflowapp"


def test_an_empty_override_is_ignored(monkeypatch, tmp_path):
    # An empty environment variable is how a shell says "unset", not "use the
    # current directory".
    monkeypatch.setenv(paths.DATA_DIR_ENV, "")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.data_dir() == tmp_path / "WorkflowApp"


def test_reading_the_path_creates_nothing(monkeypatch, tmp_path):
    target = tmp_path / "mai-creata"
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(target))
    assert paths.tickets_path() == target / "tickets.json"
    assert not target.exists()
