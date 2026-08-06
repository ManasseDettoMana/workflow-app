"""The table model and its sort/filter proxy."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from PySide6.QtCore import Qt

from workflowapp.core.models import Activity, Status, Ticket
from workflowapp.gui import strings, theme
from workflowapp.gui.widgets.status_badge import STATUS_ROLE
from workflowapp.gui.widgets.ticket_table import (
    SORT_ROLE,
    TICKET_ID_ROLE,
    Column,
    TicketSortProxy,
    TicketTableModel,
)

pytestmark = pytest.mark.gui


@pytest.fixture
def tickets():
    return [
        Ticket.create("Zeta", status=Status.DONE, due_date=date(2026, 1, 10)),
        Ticket.create("alfa", status=Status.URGENT, due_date=date(2026, 3, 5)),
        Ticket.create("Mezzo", status=Status.OPEN),
    ]


@pytest.fixture
def model(qapp, tickets):
    del qapp
    model = TicketTableModel()
    model.set_tickets(tickets)
    return model


@pytest.fixture
def proxy(model):
    proxy = TicketSortProxy()
    proxy.setSourceModel(model)
    return proxy


def titles(proxy) -> list[str]:
    return [
        proxy.index(row, int(Column.TITLE)).data(Qt.ItemDataRole.DisplayRole)
        for row in range(proxy.rowCount())
    ]


class TestModel:
    def test_shape(self, model, tickets):
        assert model.rowCount() == len(tickets)
        assert model.columnCount() == len(Column)

    def test_headers_are_italian(self, model):
        headers = [
            model.headerData(c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            for c in range(model.columnCount())
        ]
        assert headers == ["Titolo", "Stato", "Scadenza", "Attività", "Aggiornato"]

    def test_status_is_shown_as_its_italian_label(self, model):
        labels = {
            model.index(r, int(Column.STATUS)).data() for r in range(model.rowCount())
        }
        assert labels == {"Fatto", "Urgente", "Aperto"}

    def test_the_status_role_carries_the_enum_not_the_label(self, model):
        # The delegate needs the value; parsing Italian back into an enum would
        # be absurd and would break the moment a label changed.
        value = model.index(0, int(Column.STATUS)).data(STATUS_ROLE)
        assert value is Status.DONE

    def test_dates_are_shown_in_italian_order(self, model):
        assert model.index(0, int(Column.DUE_DATE)).data() == "10/01/2026"

    def test_a_missing_due_date_shows_a_dash(self, model):
        assert model.index(2, int(Column.DUE_DATE)).data() == strings.NO_DUE_DATE

    def test_activities_show_completed_over_total(self, qapp):
        del qapp
        ticket = Ticket.create("Con attività")
        ticket.activities = [
            Activity(id="a1", description="Prima", completed=True),
            Activity(id="a2", description="Seconda", completed=False),
        ]
        model = TicketTableModel()
        model.set_tickets([ticket])
        assert model.index(0, int(Column.ACTIVITIES)).data() == "1/2"

    def test_a_ticket_with_no_activities_shows_nothing(self, model):
        assert model.index(0, int(Column.ACTIVITIES)).data() == ""

    def test_the_ticket_id_is_available_on_every_column(self, model, tickets):
        for column in Column:
            assert model.index(0, int(column)).data(TICKET_ID_ROLE) == tickets[0].id

    def test_an_overdue_date_is_painted_in_the_overdue_colour(self, qapp):
        del qapp
        overdue = Ticket.create("In ritardo", due_date=date.today() - timedelta(days=2))
        model = TicketTableModel()
        model.set_tickets([overdue])
        colour = model.index(0, int(Column.DUE_DATE)).data(Qt.ItemDataRole.ForegroundRole)
        assert colour == theme.active_palette().overdue_color()

    def test_a_done_ticket_is_not_painted_overdue(self, qapp):
        del qapp
        ticket = Ticket.create("Finito", due_date=date.today() - timedelta(days=2))
        ticket.status = Status.DONE
        model = TicketTableModel()
        model.set_tickets([ticket])
        assert model.index(0, int(Column.DUE_DATE)).data(Qt.ItemDataRole.ForegroundRole) is None

    def test_the_title_tooltip_is_the_description(self, qapp):
        del qapp
        ticket = Ticket.create("Titolo", description="La descrizione lunga")
        model = TicketTableModel()
        model.set_tickets([ticket])
        tip = model.index(0, int(Column.TITLE)).data(Qt.ItemDataRole.ToolTipRole)
        assert tip == "La descrizione lunga"

    def test_set_tickets_replaces_everything(self, model):
        model.set_tickets([])
        assert model.rowCount() == 0


class TestSorting:
    def test_by_title_is_case_insensitive(self, proxy):
        proxy.sort(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        assert titles(proxy) == ["alfa", "Mezzo", "Zeta"]

    def test_by_status_uses_priority_not_the_alphabet(self, proxy):
        proxy.sort(int(Column.STATUS), Qt.SortOrder.AscendingOrder)
        # Alphabetically "Aperto" would come first; by priority "Urgente" does.
        assert titles(proxy)[0] == "alfa"

    def test_undated_tickets_stay_last_ascending(self, proxy):
        proxy.sort(int(Column.DUE_DATE), Qt.SortOrder.AscendingOrder)
        assert titles(proxy) == ["Zeta", "alfa", "Mezzo"]

    def test_undated_tickets_stay_last_descending(self, proxy):
        # The whole reason lessThan is overridden. Sorting on the raw value puts
        # every undated ticket at the top the moment the column is reversed.
        proxy.sort(int(Column.DUE_DATE), Qt.SortOrder.DescendingOrder)
        assert titles(proxy) == ["alfa", "Zeta", "Mezzo"]

    def test_the_sort_role_is_not_the_display_text(self, model):
        index = model.index(0, int(Column.STATUS))
        assert index.data(SORT_ROLE) == Status.DONE.priority
        assert index.data(Qt.ItemDataRole.DisplayRole) == "Fatto"


class TestFiltering:
    def test_by_status(self, proxy):
        proxy.set_status_filter(Status.OPEN)
        assert titles(proxy) == ["Mezzo"]

    def test_clearing_the_status_filter(self, proxy):
        proxy.set_status_filter(Status.OPEN)
        proxy.set_status_filter(None)
        assert proxy.rowCount() == 3

    def test_by_text_is_case_insensitive(self, proxy):
        proxy.set_text_filter("ALFA")
        assert titles(proxy) == ["alfa"]

    def test_by_text_searches_the_description_too(self, qapp):
        del qapp
        model = TicketTableModel()
        model.set_tickets(
            [
                Ticket.create("Primo", description="parla di relazione"),
                Ticket.create("Secondo", description="niente"),
            ]
        )
        proxy = TicketSortProxy()
        proxy.setSourceModel(model)
        proxy.set_text_filter("relazione")
        assert titles(proxy) == ["Primo"]

    def test_whitespace_only_text_is_not_a_filter(self, proxy):
        proxy.set_text_filter("   ")
        assert proxy.rowCount() == 3

    def test_filters_combine(self, proxy):
        proxy.set_status_filter(Status.DONE)
        proxy.set_text_filter("alfa")
        assert proxy.rowCount() == 0

    def test_by_overdue(self, qapp):
        del qapp
        overdue_ticket = Ticket.create(
            "Overdue", status=Status.OPEN, due_date=date.today() - timedelta(days=2)
        )
        normal_ticket = Ticket.create(
            "Normal", status=Status.OPEN, due_date=date.today() + timedelta(days=2)
        )
        done_ticket = Ticket.create(
            "Done", status=Status.DONE, due_date=date.today() - timedelta(days=2)
        )

        model = TicketTableModel()
        model.set_tickets([overdue_ticket, normal_ticket, done_ticket])
        proxy = TicketSortProxy()
        proxy.setSourceModel(model)

        proxy.set_overdue_filter(True)
        assert titles(proxy) == ["Overdue"]

        proxy.set_overdue_filter(False)
        assert proxy.rowCount() == 3
