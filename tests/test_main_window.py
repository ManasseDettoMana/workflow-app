"""The main window: what it lists, what it enables, and what it deletes."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from workflowapp.core.manager import TicketManager
from workflowapp.core.models import Status
from workflowapp.gui import strings, theme
from workflowapp.gui.main_window import MainWindow
from workflowapp.gui.widgets.ticket_table import Column

pytestmark = pytest.mark.gui


@pytest.fixture
def manager(ticket_file):
    manager = TicketManager(ticket_file)
    manager.add_ticket("Relazione trimestrale", status=Status.IN_PROGRESS)
    manager.add_ticket("Chiamare il fornitore", status=Status.URGENT)
    manager.add_ticket("Archiviare i documenti", status=Status.DONE)
    return manager


@pytest.fixture
def window(qtbot, qapp, manager, isolated_settings):
    del isolated_settings
    theme.apply_theme(qapp, theme.Theme.LIGHT)
    window = MainWindow(manager)
    qtbot.addWidget(window)
    return window


class TestListing:
    def test_it_shows_every_ticket(self, window):
        assert window._proxy.rowCount() == 3

    def test_the_window_title_is_italian(self, window):
        assert window.windowTitle() == strings.WINDOW_TITLE

    def test_refresh_picks_up_a_new_ticket(self, window, manager):
        manager.add_ticket("Aggiunto dopo")
        window.refresh()
        assert window._proxy.rowCount() == 4

    def test_the_empty_message_appears_with_no_tickets(self, qtbot, qapp, ticket_file):
        del qapp
        window = MainWindow(TicketManager(ticket_file))
        qtbot.addWidget(window)
        window.show()
        assert window._empty_label.isVisible()
        assert window._empty_label.text() == strings.EMPTY_LIST
        assert not window._table.isVisible()

    def test_a_filter_matching_nothing_says_so_differently(self, window):
        window.show()
        window._search.setText("qualcosa che non esiste")
        assert window._empty_label.text() == strings.EMPTY_FILTER


class TestSelection:
    def test_nothing_is_selected_to_begin_with(self, window):
        assert window.selected_ticket_id() is None
        assert window.action_delete.isEnabled() is False
        assert window.action_edit.isEnabled() is False

    def test_selecting_a_row_enables_the_actions(self, window):
        window._table.selectRow(0)
        assert window.selected_ticket_id() is not None
        assert window.action_delete.isEnabled() is True

    def test_the_selected_id_survives_sorting(self, window, manager):
        # The bug this guards against: taking the view's row number and using it
        # as an index into the manager's list. With a sort proxy in between those
        # are different rows, and the symptom is deleting the wrong ticket.
        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        window._table.selectRow(0)
        first_by_title = sorted(manager.tickets(), key=lambda t: t.title.casefold())[0]
        assert window.selected_ticket_id() == first_by_title.id

        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.DescendingOrder)
        window._table.selectRow(0)
        last_by_title = sorted(manager.tickets(), key=lambda t: t.title.casefold())[-1]
        assert window.selected_ticket_id() == last_by_title.id

    def test_the_selection_is_kept_across_a_refresh(self, window, manager):
        window._table.selectRow(1)
        chosen = window.selected_ticket_id()
        manager.add_ticket("Un altro")
        window.refresh()
        assert window.selected_ticket_id() == chosen


class TestDeletion:
    def test_confirming_deletes(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        _answer(monkeypatch, strings.BUTTON_YES_DELETE)

        window.delete_selected()

        assert all(t.id != target for t in manager.tickets())
        assert window._proxy.rowCount() == 2

    def test_declining_keeps_the_ticket(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        _answer(monkeypatch, strings.BUTTON_NO)

        window.delete_selected()

        assert len(manager.tickets()) == 3

    def test_deleting_the_right_ticket_after_sorting(self, window, manager, monkeypatch):
        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        expected = sorted(manager.tickets(), key=lambda t: t.title.casefold())[0].id
        assert target == expected

        _answer(monkeypatch, strings.BUTTON_YES_DELETE)
        window.delete_selected()
        assert all(t.id != expected for t in manager.tickets())

    def test_deleting_persists(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        _answer(monkeypatch, strings.BUTTON_YES_DELETE)
        window.delete_selected()

        reopened = TicketManager(manager.path)
        assert all(t.id != target for t in reopened.tickets())

    def test_deleting_with_no_selection_does_nothing(self, window, manager):
        window.delete_selected()
        assert len(manager.tickets()) == 3


class TestFiltering:
    def test_the_search_box_filters(self, window):
        window._search.setText("fornitore")
        assert window._proxy.rowCount() == 1

    def test_the_status_combo_filters(self, window):
        index = window._status_filter.findData(Status.DONE)
        window._status_filter.setCurrentIndex(index)
        assert window._proxy.rowCount() == 1

    def test_the_first_combo_entry_means_no_filter(self, window):
        assert window._status_filter.itemData(0) is None
        assert window._status_filter.itemText(0) == strings.FILTER_ALL_STATUSES

    def test_every_status_is_offered_with_an_icon(self, window):
        offered = {
            window._status_filter.itemData(i) for i in range(1, window._status_filter.count())
        }
        assert offered == set(Status)
        assert not window._status_filter.itemIcon(1).isNull()

    def test_the_overdue_checkbox_filters(self, window, manager):
        overdue = manager.add_ticket("Scaduto", due_date=date.today() - timedelta(days=3))
        window.refresh()
        assert window._proxy.rowCount() == 4
        window._overdue_check.setChecked(True)
        assert window._proxy.rowCount() == 1
        window.select_ticket(overdue.id)
        assert window.selected_ticket().title == "Scaduto"


class TestStatusBar:
    def test_it_counts_visible_and_total(self, window):
        window._search.setText("fornitore")
        message = window.statusBar().currentMessage()
        assert "1" in message and "3" in message

    def test_overdue_tickets_are_mentioned(self, qtbot, qapp, ticket_file):
        del qapp
        manager = TicketManager(ticket_file)
        manager.add_ticket("In ritardo", due_date=date.today() - timedelta(days=3))
        window = MainWindow(manager)
        qtbot.addWidget(window)
        assert "ritardo" in window.statusBar().currentMessage()


class TestTheme:
    def test_toggling_switches_and_saves(self, window, qapp):
        assert theme.active() is theme.Theme.LIGHT
        window.toggle_theme()
        assert theme.active() is theme.Theme.DARK
        assert theme.load_preference() is theme.Theme.DARK
        assert qapp.styleSheet() == theme.stylesheet(theme.Theme.DARK)

    def test_toggling_twice_returns(self, window):
        window.toggle_theme()
        window.toggle_theme()
        assert theme.active() is theme.Theme.LIGHT

    def test_the_status_icons_are_repainted(self, window):
        # They are drawn from the Python palette, so unlike the stylesheet they
        # do not refresh themselves when the theme changes.
        before = window._status_filter.itemIcon(1).pixmap(14, 14).toImage()
        window.toggle_theme()
        after = window._status_filter.itemIcon(1).pixmap(14, 14).toImage()
        assert before != after


def _answer(monkeypatch, button_text: str) -> None:
    """Make the next QMessageBox answer with the button carrying this text."""

    def exec_(self):
        for button in self.buttons():
            if button.text().replace("&", "") == button_text:
                self.setClickedButtonForTest(button)
                return 0
        raise AssertionError(f"no button labelled {button_text!r}")

    # QMessageBox has no public way to say which button was clicked, so the
    # window is asked instead through a small shim installed on the class.
    def set_clicked(self, button):
        self._test_clicked = button

    def clicked_button(self):
        return getattr(self, "_test_clicked", None)

    monkeypatch.setattr(QMessageBox, "setClickedButtonForTest", set_clicked, raising=False)
    monkeypatch.setattr(QMessageBox, "clickedButton", clicked_button, raising=False)
    monkeypatch.setattr(QMessageBox, "exec", exec_, raising=False)
