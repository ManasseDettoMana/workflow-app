"""Starting up, and failing to.

The unreadable-file path is the one worth testing here. PySide6 ends the process
on an unhandled exception, so "the tickets could not be read" has to arrive as a
message box and an exit code, not as a traceback and a dead window.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from workflowapp.core import store
from workflowapp.gui import app as gui_app
from workflowapp.gui import strings, theme

pytestmark = pytest.mark.gui


class TestBuildApplication:
    def test_it_reuses_the_existing_instance(self, qapp):
        # pytest-qt has already built one, and constructing a second aborts the
        # process rather than raising.
        assert gui_app.build_application([]) is qapp
        assert QApplication.instance() is qapp


class TestStartupFailure:
    def test_an_unreadable_file_reports_and_exits(self, qapp, monkeypatch, scratch_data_dir):
        del qapp
        bad = scratch_data_dir / "tickets.json"
        bad.write_text("{non e json", encoding="utf-8")

        shown = []
        monkeypatch.setattr(
            QMessageBox,
            "critical",
            staticmethod(lambda parent, title, text: shown.append((title, text)) or 0),
        )

        code = gui_app.main([])

        assert code == 1, "a failed startup must not report success"
        assert len(shown) == 1
        title, text = shown[0]
        assert title == strings.ERROR_STARTUP_TITLE
        # The message has to say where the file went, or it is unrecoverable.
        assert "corrupt-" in text

    def test_the_unreadable_file_is_preserved(self, qapp, monkeypatch, scratch_data_dir):
        del qapp
        bad = scratch_data_dir / "tickets.json"
        bad.write_text("{non e json", encoding="utf-8")
        monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: 0))

        gui_app.main([])

        preserved = list(scratch_data_dir.glob("tickets.json.corrupt-*"))
        assert len(preserved) == 1
        assert preserved[0].read_text(encoding="utf-8") == "{non e json"

    def test_a_file_from_a_newer_version_is_left_alone(
        self, qapp, monkeypatch, scratch_data_dir
    ):
        del qapp
        newer = scratch_data_dir / "tickets.json"
        payload = json.dumps({"schema": store.SCHEMA_VERSION + 1, "tickets": []})
        newer.write_text(payload, encoding="utf-8")
        monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: 0))

        assert gui_app.main([]) == 1
        # Good data this version cannot read. Quarantining it would be the
        # destructive act the whole rule exists to prevent.
        assert newer.read_text(encoding="utf-8") == payload
        assert list(scratch_data_dir.glob("tickets.json.corrupt-*")) == []


class TestTheming:
    def test_the_saved_theme_is_applied_before_any_window_exists(
        self, qapp, monkeypatch, isolated_settings
    ):
        del isolated_settings
        theme.save_preference(theme.Theme.DARK)

        applied = []
        monkeypatch.setattr(
            gui_app.theme, "apply_theme", lambda a, t: applied.append(t)
        )
        # Stop before a window is built; the theme call is what is under test.
        monkeypatch.setattr(
            gui_app, "TicketManager", lambda: (_ for _ in ()).throw(RuntimeError("stop"))
        )
        monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: 0))

        with pytest.raises(RuntimeError):
            gui_app.main([])

        assert applied == [theme.Theme.DARK]
        del qapp
