"""Create and edit, from the window through the manager to the file.

These are the tests that would catch the dialog being wired to the wrong ticket,
or an edit that never reaches disk. They drive the real ``MainWindow`` and the
real ``TicketManager``; only the dialog's ``exec`` is replaced, because a modal
dialog cannot be answered from the same thread that opened it.
"""

from __future__ import annotations

from datetime import date

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QDialog

from workflowapp.core.manager import TicketManager
from workflowapp.core.models import Status
from workflowapp.gui import theme
from workflowapp.gui.main_window import MainWindow
from workflowapp.gui.ticket_dialog import TicketDialog
from workflowapp.gui.widgets.ticket_table import Column

pytestmark = pytest.mark.gui


@pytest.fixture
def manager(ticket_file):
    return TicketManager(ticket_file)


@pytest.fixture
def window(qtbot, qapp, manager, isolated_settings):
    del isolated_settings
    theme.apply_theme(qapp, theme.Theme.LIGHT)
    window = MainWindow(manager)
    qtbot.addWidget(window)
    return window


def fill_dialog(monkeypatch, fill, accept=True):
    """Answer the next TicketDialog by running ``fill`` on it, then accepting."""

    def exec_(self):
        fill(self)
        return QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected

    monkeypatch.setattr(TicketDialog, "exec", exec_)


class TestCreate:
    def test_a_new_ticket_reaches_the_file(self, window, manager, monkeypatch):
        def fill(dialog):
            dialog.title_edit.setText("Chiamare il fornitore")
            dialog.description_edit.setPlainText("Chiarire la fattura.")
            dialog.status_combo.setCurrentIndex(dialog.status_combo.findData(Status.URGENT))
            dialog.no_due_date.setChecked(False)
            dialog.due_date_edit.setDate(QDate(2026, 12, 24))

        fill_dialog(monkeypatch, fill)
        window.create_ticket()

        stored = TicketManager(manager.path).tickets()
        assert len(stored) == 1
        assert stored[0].title == "Chiamare il fornitore"
        assert stored[0].status is Status.URGENT
        assert stored[0].due_date == date(2026, 12, 24)

    def test_activities_added_in_the_dialog_are_saved(self, window, manager, monkeypatch):
        def fill(dialog):
            dialog.title_edit.setText("Con attività")
            dialog.activity_list.add_activity()
            dialog.activity_list._list.item(0).setText("Esportare i dati")
            dialog.activity_list.add_activity()
            dialog.activity_list._list.item(1).setText("Impaginare")
            dialog.activity_list._list.item(1).setCheckState(Qt.CheckState.Checked)

        fill_dialog(monkeypatch, fill)
        window.create_ticket()

        stored = TicketManager(manager.path).tickets()[0]
        assert [a.description for a in stored.activities] == ["Esportare i dati", "Impaginare"]
        assert stored.completed_count == 1

    def test_cancelling_creates_nothing(self, window, manager, monkeypatch):
        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Mai salvato"), accept=False)
        window.create_ticket()
        assert manager.tickets() == []

    def test_the_new_ticket_is_selected_afterwards(self, window, monkeypatch):
        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Appena creato"))
        window.create_ticket()
        assert window.selected_ticket().title == "Appena creato"

    def test_the_table_shows_it_immediately(self, window, monkeypatch):
        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Visibile subito"))
        window.create_ticket()
        assert window._proxy.rowCount() == 1


class TestEdit:
    @pytest.fixture
    def populated(self, window, manager):
        manager.add_ticket("Primo", status=Status.OPEN)
        manager.add_ticket("Secondo", status=Status.DONE)
        window.refresh()
        return window

    def test_editing_persists(self, populated, manager, monkeypatch):
        populated._table.selectRow(0)
        target = populated.selected_ticket_id()

        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Titolo modificato"))
        populated.edit_selected()

        stored = TicketManager(manager.path).get(target)
        assert stored.title == "Titolo modificato"

    def test_cancelling_changes_nothing(self, populated, manager, monkeypatch):
        populated._table.selectRow(0)
        target = populated.selected_ticket_id()
        before = manager.get(target).title

        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Non salvare"), accept=False)
        populated.edit_selected()

        assert manager.get(target).title == before

    def test_it_edits_the_selected_ticket_after_sorting(self, populated, manager, monkeypatch):
        # The wrong-row bug again, this time through the edit path: with the
        # table sorted, row 0 is not the manager's first ticket.
        populated._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.DescendingOrder)
        populated._table.selectRow(0)
        target = populated.selected_ticket_id()
        assert manager.get(target).title == "Secondo"

        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Secondo modificato"))
        populated.edit_selected()

        assert manager.get(target).title == "Secondo modificato"
        # And the other one is untouched.
        others = [t for t in manager.tickets() if t.id != target]
        assert others[0].title == "Primo"

    def test_the_dialog_opens_on_the_right_ticket(self, populated, monkeypatch):
        populated._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.DescendingOrder)
        populated._table.selectRow(0)

        seen = {}
        fill_dialog(monkeypatch, lambda d: seen.update(title=d.title_edit.text()))
        populated.edit_selected()

        assert seen["title"] == "Secondo"

    def test_clearing_the_deadline_persists(self, populated, manager, monkeypatch):
        populated._table.selectRow(0)
        target = populated.selected_ticket_id()
        manager.update_ticket(target, due_date=date(2026, 5, 1))
        populated.refresh()
        populated.select_ticket(target)

        fill_dialog(monkeypatch, lambda d: d.no_due_date.setChecked(True))
        populated.edit_selected()

        assert TicketManager(manager.path).get(target).due_date is None

    def test_editing_bumps_the_update_time(self, populated, manager, monkeypatch):
        populated._table.selectRow(0)
        target = populated.selected_ticket_id()
        before = manager.get(target).updated_at

        fill_dialog(monkeypatch, lambda d: d.title_edit.setText("Toccato"))
        populated.edit_selected()

        assert manager.get(target).updated_at > before

    def test_editing_with_no_selection_does_nothing(self, populated, manager, monkeypatch):
        called = []
        fill_dialog(monkeypatch, lambda d: called.append(1))
        populated.edit_selected()
        assert called == []

    def test_a_double_click_opens_the_dialog(self, populated, manager, monkeypatch):
        populated._table.selectRow(0)
        # Not "Primo": the table defaults to most-recently-updated first, so row
        # 0 is whichever ticket was touched last.
        selected = manager.get(populated.selected_ticket_id())

        opened = []
        fill_dialog(monkeypatch, lambda d: opened.append(d.title_edit.text()))
        populated._on_double_click(populated._table.currentIndex())

        assert opened == [selected.title]


class TestFullRestart:
    def test_create_edit_and_reopen(self, window, manager, monkeypatch):
        """The check the whole application exists for: it is all still there."""

        def create(dialog):
            dialog.title_edit.setText("Relazione trimestrale")
            dialog.description_edit.setPlainText("Con accenti: perché, attività.")
            dialog.status_combo.setCurrentIndex(
                dialog.status_combo.findData(Status.IN_PROGRESS)
            )
            dialog.no_due_date.setChecked(False)
            dialog.due_date_edit.setDate(QDate(2026, 11, 30))
            dialog.activity_list.add_activity()
            dialog.activity_list._list.item(0).setText("Esportare i dati")
            dialog.activity_list._list.item(0).setCheckState(Qt.CheckState.Checked)
            dialog.activity_list.add_activity()
            dialog.activity_list._list.item(1).setText("Impaginare")

        fill_dialog(monkeypatch, create)
        window.create_ticket()

        # A brand new manager reading the same file, as a restart would.
        reopened = TicketManager(manager.path)
        assert len(reopened.tickets()) == 1
        ticket = reopened.tickets()[0]
        assert ticket.title == "Relazione trimestrale"
        assert ticket.description == "Con accenti: perché, attività."
        assert ticket.status is Status.IN_PROGRESS
        assert ticket.due_date == date(2026, 11, 30)
        assert [a.description for a in ticket.activities] == ["Esportare i dati", "Impaginare"]
        assert [a.completed for a in ticket.activities] == [True, False]
