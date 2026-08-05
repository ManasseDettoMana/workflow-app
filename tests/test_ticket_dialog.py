"""The ticket dialog and the activity list."""

from __future__ import annotations

from datetime import date

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QDialog, QMessageBox

from workflowapp.core.models import Activity, Status, Ticket
from workflowapp.gui import strings, theme
from workflowapp.gui.ticket_dialog import TicketDialog
from workflowapp.gui.widgets.activity_list import ActivityList

pytestmark = pytest.mark.gui


@pytest.fixture
def ticket():
    ticket = Ticket.create(
        "Relazione trimestrale",
        description="Raccogliere i dati.",
        status=Status.IN_PROGRESS,
        due_date=date(2026, 9, 15),
    )
    ticket.activities = [
        Activity(id="a1", description="Esportare", completed=True),
        Activity(id="a2", description="Impaginare", completed=False),
    ]
    return ticket


@pytest.fixture
def themed(qapp):
    theme.apply_theme(qapp, theme.Theme.LIGHT)
    return qapp


class TestNewMode:
    def test_the_fields_start_empty(self, qtbot, themed):
        del themed
        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        assert dialog.title_edit.text() == ""
        assert dialog.description_edit.toPlainText() == ""
        assert dialog.status_combo.currentData() is Status.OPEN

    def test_a_new_ticket_has_no_deadline_by_default(self, qtbot, themed):
        del themed
        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        assert dialog.no_due_date.isChecked()
        assert dialog.due_date_edit.isEnabled() is False
        assert dialog.draft().due_date is None

    def test_the_title_says_new(self, qtbot, themed):
        del themed
        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == strings.DIALOG_NEW_TITLE

    def test_no_metadata_line_for_a_ticket_that_does_not_exist_yet(self, qtbot, themed):
        del themed
        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        assert dialog._meta_label.isVisible() is False


class TestEditMode:
    def test_every_field_is_populated(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        assert dialog.title_edit.text() == "Relazione trimestrale"
        assert dialog.description_edit.toPlainText() == "Raccogliere i dati."
        assert dialog.status_combo.currentData() is Status.IN_PROGRESS
        assert dialog.due_date_edit.date() == QDate(2026, 9, 15)
        assert dialog.no_due_date.isChecked() is False

    def test_the_title_says_detail(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == strings.DIALOG_EDIT_TITLE

    def test_the_activities_are_listed_with_their_tick_state(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        activities = dialog.activity_list.activities()
        assert [a.description for a in activities] == ["Esportare", "Impaginare"]
        assert [a.completed for a in activities] == [True, False]

    def test_a_ticket_with_no_deadline_opens_with_the_box_ticked(self, qtbot, themed, ticket):
        del themed
        ticket.due_date = None
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        assert dialog.no_due_date.isChecked()

    def test_the_dialog_does_not_start_dirty(self, qtbot, themed, ticket):
        # Populating the fields fires the same signals typing does. Without the
        # reset at the end of __init__, opening and immediately cancelling would
        # ask whether to discard changes nobody made.
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        assert dialog._dirty is False

    def test_the_metadata_line_shows_both_dates(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        text = dialog._meta_label.text()
        assert "Aperto il" in text and "Aggiornato il" in text


class TestDraft:
    def test_it_reads_back_what_was_typed(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)

        dialog.title_edit.setText("  Titolo modificato  ")
        dialog.description_edit.setPlainText("Nuova descrizione")
        dialog.status_combo.setCurrentIndex(dialog.status_combo.findData(Status.DONE))
        dialog.due_date_edit.setDate(QDate(2027, 1, 31))

        draft = dialog.draft()
        assert draft.title == "Titolo modificato"
        assert draft.description == "Nuova descrizione"
        assert draft.status is Status.DONE
        assert draft.due_date == date(2027, 1, 31)

    def test_ticking_no_deadline_clears_the_date(self, qtbot, themed, ticket):
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        dialog.no_due_date.setChecked(True)
        assert dialog.draft().due_date is None

    def test_the_draft_does_not_touch_the_ticket(self, qtbot, themed, ticket):
        # The dialog is a form, not an editor of live objects. Cancel could not
        # cancel anything if it mutated the ticket as the user typed.
        del themed
        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        dialog.title_edit.setText("Cambiato")
        dialog.activity_list.add_activity()
        assert ticket.title == "Relazione trimestrale"
        assert len(ticket.activities) == 2


class TestValidation:
    def test_an_empty_title_is_refused(self, qtbot, themed, monkeypatch):
        del themed
        shown = []
        monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.text()) or 0)

        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.title_edit.setText("   ")
        dialog.accept()

        assert dialog.isVisible(), "the dialog closed on an empty title"
        assert shown == [strings.ERROR_TITLE_REQUIRED]

    def test_whitespace_only_is_treated_as_empty(self, qtbot, themed, monkeypatch):
        del themed
        shown = []
        monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.text()) or 0)

        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.title_edit.setText("\t   ")
        dialog.accept()

        assert dialog.isVisible()
        assert shown == [strings.ERROR_TITLE_REQUIRED]

    def test_a_real_title_is_accepted(self, qtbot, themed):
        del themed
        dialog = TicketDialog(None)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.title_edit.setText("Un titolo")
        dialog.accept()
        assert not dialog.isVisible()
        assert dialog.result() == QDialog.DialogCode.Accepted


class TestDiscardConfirmation:
    """Whether the dialog actually closed is the thing to assert here.

    Not ``result()``: a QDialog reports ``Rejected`` - which is 0 - from the
    moment it is constructed, so "did rejecting reject it?" is true before
    anything happens and proves nothing either way.
    """

    def test_cancelling_an_untouched_dialog_asks_nothing(self, qtbot, themed, ticket, monkeypatch):
        del themed
        asked = []
        monkeypatch.setattr(QMessageBox, "exec", lambda self: asked.append(1) or 0)

        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.reject()

        assert asked == []
        assert not dialog.isVisible()

    def test_cancelling_after_an_edit_asks(self, qtbot, themed, ticket, monkeypatch):
        del themed
        _answer(monkeypatch, strings.BUTTON_YES_DISCARD)

        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.title_edit.setText("Modificato")
        dialog.reject()

        assert not dialog.isVisible()

    def test_declining_to_discard_keeps_the_dialog_open(self, qtbot, themed, ticket, monkeypatch):
        del themed
        _answer(monkeypatch, strings.BUTTON_NO)

        dialog = TicketDialog(ticket)
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.title_edit.setText("Modificato")
        dialog.reject()

        # Still open, and still holding the user's text.
        assert dialog.isVisible()
        assert dialog.title_edit.text() == "Modificato"


class TestActivityList:
    def test_it_copies_rather_than_referencing(self, qtbot, themed):
        del themed
        original = [Activity(id="a1", description="Prima", completed=False)]
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities(original)

        widget._list.item(0).setCheckState(Qt.CheckState.Checked)

        assert original[0].completed is False
        assert widget.activities()[0].completed is True

    def test_ids_survive_a_round_trip(self, qtbot, themed):
        # Otherwise every save would look like "deleted all, added all", and the
        # tick state would not be attributable to anything.
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities([Activity(id="a1", description="Prima")])
        assert widget.activities()[0].id == "a1"

    def test_adding_appends_a_row(self, qtbot, themed):
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.add_activity()
        assert widget._list.count() == 1

    def test_removing_takes_the_selected_row(self, qtbot, themed):
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities(
            [
                Activity(id="a1", description="Prima"),
                Activity(id="a2", description="Seconda"),
            ]
        )
        widget._list.setCurrentRow(0)
        widget.remove_selected()
        assert [a.description for a in widget.activities()] == ["Seconda"]

    def test_an_emptied_row_is_dropped(self, qtbot, themed):
        # A row the user cleared the text of is not an activity, and saving it
        # would put a nameless entry in the file.
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities([Activity(id="a1", description="Prima")])
        widget._list.item(0).setText("   ")
        assert widget.activities() == []

    def test_the_remove_button_needs_a_selection(self, qtbot, themed):
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities([Activity(id="a1", description="Prima")])
        assert widget._remove_button.isEnabled() is False
        widget._list.setCurrentRow(0)
        assert widget._remove_button.isEnabled() is True

    def test_the_counter_reads_in_italian(self, qtbot, themed):
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        widget.set_activities(
            [
                Activity(id="a1", description="Prima", completed=True),
                Activity(id="a2", description="Seconda"),
            ]
        )
        assert widget._count_label.text() == "1 di 2 completate"

    def test_the_counter_is_blank_with_no_activities(self, qtbot, themed):
        del themed
        widget = ActivityList()
        qtbot.addWidget(widget)
        assert widget._count_label.text() == ""


def _answer(monkeypatch, button_text: str) -> None:
    """Make the next QMessageBox answer with the button carrying this text."""

    def exec_(self):
        for button in self.buttons():
            if button.text().replace("&", "") == button_text:
                self._test_clicked = button
                return 0
        raise AssertionError(f"no button labelled {button_text!r}")

    monkeypatch.setattr(
        QMessageBox, "clickedButton", lambda self: getattr(self, "_test_clicked", None)
    )
    monkeypatch.setattr(QMessageBox, "exec", exec_)
