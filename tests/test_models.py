"""The model round-trips, and rejects data it cannot trust."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.models import Activity, Status, Ticket, new_id


class TestStatus:
    def test_stored_value_is_an_english_token(self):
        # Invariant 4. If this ever reads "In Lavorazione", the file has started
        # depending on the language of the interface.
        assert Status.IN_PROGRESS.value == "in_progress"
        assert {s.value for s in Status} == {"open", "in_progress", "done", "urgent"}

    def test_from_token_round_trips(self):
        for status in Status:
            assert Status.from_token(status.value) is status

    def test_unknown_token_raises_something_the_user_can_read(self):
        with pytest.raises(WorkflowAppError) as excinfo:
            Status.from_token("in-lavorazione")
        assert "in-lavorazione" in str(excinfo.value)
        # The hint should list what would have worked.
        assert "in_progress" in str(excinfo.value)

    def test_priority_puts_urgent_first_and_done_last(self):
        ordered = sorted(Status, key=lambda s: s.priority)
        assert ordered[0] is Status.URGENT
        assert ordered[-1] is Status.DONE


class TestActivity:
    def test_round_trip(self):
        activity = Activity(id="a1", description="Scrivere i test", completed=True)
        assert Activity.from_dict(activity.to_dict()) == activity

    def test_create_assigns_an_id(self):
        activity = Activity.create("Rivedere la bozza")
        assert activity.id
        assert activity.completed is False

    def test_completed_defaults_to_false_when_absent(self):
        activity = Activity.from_dict({"id": "a1", "description": "x"})
        assert activity.completed is False

    def test_missing_description_raises(self):
        with pytest.raises(WorkflowAppError):
            Activity.from_dict({"id": "a1"})

    def test_a_non_object_raises(self):
        with pytest.raises(WorkflowAppError):
            Activity.from_dict("non un oggetto")


class TestTicket:
    def test_round_trip_preserves_every_field(self, sample_ticket):
        assert Ticket.from_dict(sample_ticket.to_dict()) == sample_ticket

    def test_round_trip_without_a_due_date(self, sample_ticket):
        sample_ticket.due_date = None
        restored = Ticket.from_dict(sample_ticket.to_dict())
        assert restored.due_date is None
        assert restored == sample_ticket

    def test_create_sets_both_timestamps_together(self):
        ticket = Ticket.create("Nuovo ticket")
        assert ticket.created_at == ticket.updated_at
        assert ticket.status is Status.OPEN
        assert ticket.activities == []

    def test_dates_serialise_as_iso_8601(self, sample_ticket):
        raw = sample_ticket.to_dict()
        assert raw["due_date"] == "2026-08-20"
        assert raw["created_at"].startswith("2026-08-01T09:30")

    def test_unknown_status_in_the_file_raises(self, sample_ticket):
        raw = sample_ticket.to_dict()
        raw["status"] = "archiviato"
        with pytest.raises(WorkflowAppError):
            Ticket.from_dict(raw)

    def test_unparseable_date_raises(self, sample_ticket):
        raw = sample_ticket.to_dict()
        raw["due_date"] = "20 agosto 2026"
        with pytest.raises(WorkflowAppError) as excinfo:
            Ticket.from_dict(raw)
        assert "due_date" in str(excinfo.value)

    def test_missing_title_raises(self, sample_ticket):
        raw = sample_ticket.to_dict()
        del raw["title"]
        with pytest.raises(WorkflowAppError):
            Ticket.from_dict(raw)

    def test_activities_that_are_not_a_list_raise(self, sample_ticket):
        raw = sample_ticket.to_dict()
        raw["activities"] = {"id": "a1"}
        with pytest.raises(WorkflowAppError):
            Ticket.from_dict(raw)


class TestOverdue:
    def test_a_past_due_date_is_overdue(self):
        ticket = Ticket.create("In ritardo", due_date=date.today() - timedelta(days=1))
        assert ticket.is_overdue

    def test_today_is_not_yet_overdue(self):
        ticket = Ticket.create("Scade oggi", due_date=date.today())
        assert not ticket.is_overdue

    def test_no_due_date_is_never_overdue(self):
        assert not Ticket.create("Senza scadenza").is_overdue

    def test_a_done_ticket_is_never_overdue(self):
        # Otherwise every finished ticket stays red for ever.
        ticket = Ticket.create("Fatto", due_date=date(2020, 1, 1))
        ticket.status = Status.DONE
        assert not ticket.is_overdue


class TestActivityHelpers:
    def test_completed_count(self, sample_ticket):
        assert sample_ticket.completed_count == 1

    def test_find_activity(self, sample_ticket):
        assert sample_ticket.find_activity("act2").description == "Impaginare"
        assert sample_ticket.find_activity("nope") is None


def test_ids_are_unique():
    assert len({new_id() for _ in range(1000)}) == 1000


def test_created_at_defaults_to_now():
    before = datetime.now()
    ticket = Ticket(id="x", title="y")
    assert before <= ticket.created_at <= datetime.now()
