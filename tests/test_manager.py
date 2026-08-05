"""TicketManager: the CRUD, the timestamp rule, and saving on every change."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from workflowapp.core import store
from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.manager import SortField, TicketManager
from workflowapp.core.models import Status


@pytest.fixture
def manager(ticket_file):
    return TicketManager(ticket_file)


def reread(manager) -> list:
    """What is actually on disk, not what is in memory."""
    return store.load_tickets(manager.path)


class TestLoading:
    def test_a_new_manager_starts_empty(self, manager):
        assert manager.tickets() == []

    def test_it_loads_what_was_saved(self, ticket_file, sample_ticket):
        store.save_tickets([sample_ticket], ticket_file)
        assert TicketManager(ticket_file).tickets() == [sample_ticket]

    def test_an_unreadable_file_raises_from_the_constructor(self, ticket_file):
        ticket_file.write_text("{rotto", encoding="utf-8")
        with pytest.raises(WorkflowAppError):
            TicketManager(ticket_file)

    def test_reload_discards_in_memory_state(self, manager):
        manager.add_ticket("Primo")
        store.save_tickets([], manager.path)
        manager.reload()
        assert manager.tickets() == []

    def test_tickets_returns_a_copy(self, manager):
        manager.add_ticket("Primo")
        got = manager.tickets()
        got.append("spazzatura")
        assert len(manager.tickets()) == 1


class TestTicketCrud:
    def test_add_persists_immediately(self, manager):
        ticket = manager.add_ticket("Preparare la relazione")
        assert [t.id for t in reread(manager)] == [ticket.id]

    def test_add_strips_whitespace_from_the_title(self, manager):
        assert manager.add_ticket("   Con spazi   ").title == "Con spazi"

    def test_add_defaults_to_open_with_no_deadline(self, manager):
        ticket = manager.add_ticket("Nuovo")
        assert ticket.status is Status.OPEN
        assert ticket.due_date is None
        assert ticket.activities == []

    def test_update_changes_only_what_was_passed(self, manager):
        ticket = manager.add_ticket("Titolo", description="Descrizione originale")
        manager.update_ticket(ticket.id, title="Titolo nuovo")
        assert ticket.title == "Titolo nuovo"
        assert ticket.description == "Descrizione originale"

    def test_update_can_clear_the_due_date(self, manager):
        # The reason update_ticket uses a sentinel default rather than None:
        # clearing a deadline is a real edit and must be expressible.
        ticket = manager.add_ticket("Con scadenza", due_date=date(2026, 9, 1))
        manager.update_ticket(ticket.id, due_date=None)
        assert ticket.due_date is None
        assert reread(manager)[0].due_date is None

    def test_update_leaves_the_due_date_alone_when_not_mentioned(self, manager):
        ticket = manager.add_ticket("Con scadenza", due_date=date(2026, 9, 1))
        manager.update_ticket(ticket.id, title="Altro titolo")
        assert ticket.due_date == date(2026, 9, 1)

    def test_delete_persists(self, manager):
        first = manager.add_ticket("Primo")
        manager.add_ticket("Secondo")
        manager.delete_ticket(first.id)
        assert [t.title for t in reread(manager)] == ["Secondo"]

    def test_operations_on_a_missing_ticket_raise(self, manager):
        for call in (
            lambda: manager.get("inesistente"),
            lambda: manager.delete_ticket("inesistente"),
            lambda: manager.update_ticket("inesistente", title="x"),
            lambda: manager.add_activity("inesistente", "x"),
        ):
            with pytest.raises(WorkflowAppError):
                call()

    def test_set_status(self, manager):
        ticket = manager.add_ticket("Da fare")
        manager.set_status(ticket.id, Status.DONE)
        assert reread(manager)[0].status is Status.DONE


class TestActivities:
    def test_add_and_persist(self, manager):
        ticket = manager.add_ticket("Con attività")
        manager.add_activity(ticket.id, "  Scrivere la bozza  ")
        stored = reread(manager)[0]
        assert [a.description for a in stored.activities] == ["Scrivere la bozza"]
        assert stored.activities[0].completed is False

    def test_tick_and_untick(self, manager):
        ticket = manager.add_ticket("Con attività")
        activity = manager.add_activity(ticket.id, "Fare")
        manager.set_activity_completed(ticket.id, activity.id, True)
        assert reread(manager)[0].activities[0].completed is True
        manager.set_activity_completed(ticket.id, activity.id, False)
        assert reread(manager)[0].activities[0].completed is False

    def test_remove(self, manager):
        ticket = manager.add_ticket("Con attività")
        first = manager.add_activity(ticket.id, "Prima")
        manager.add_activity(ticket.id, "Seconda")
        manager.remove_activity(ticket.id, first.id)
        assert [a.description for a in reread(manager)[0].activities] == ["Seconda"]

    def test_rename(self, manager):
        ticket = manager.add_ticket("Con attività")
        activity = manager.add_activity(ticket.id, "Vecchia")
        manager.set_activity_description(ticket.id, activity.id, "Nuova")
        assert reread(manager)[0].activities[0].description == "Nuova"

    def test_a_missing_activity_raises(self, manager):
        ticket = manager.add_ticket("Con attività")
        with pytest.raises(WorkflowAppError):
            manager.remove_activity(ticket.id, "inesistente")


class TestUpdatedAt:
    """Invariant 5: every mutation bumps updated_at, and nothing else does."""

    def test_every_mutating_method_bumps_it(self, manager):
        ticket = manager.add_ticket("Titolo")
        activity = manager.add_activity(ticket.id, "Attività")

        mutations = [
            lambda: manager.update_ticket(ticket.id, title="Altro"),
            lambda: manager.set_status(ticket.id, Status.DONE),
            lambda: manager.set_activity_completed(ticket.id, activity.id, True),
            lambda: manager.set_activity_description(ticket.id, activity.id, "Rinominata"),
            lambda: manager.add_activity(ticket.id, "Un'altra"),
            lambda: manager.remove_activity(ticket.id, activity.id),
        ]
        for mutate in mutations:
            ticket.updated_at = datetime(2000, 1, 1)
            mutate()
            assert ticket.updated_at.year != 2000, f"{mutate} did not bump updated_at"

    def test_created_at_is_never_touched(self, manager):
        ticket = manager.add_ticket("Titolo")
        created = ticket.created_at
        manager.update_ticket(ticket.id, title="Cambiato")
        manager.set_status(ticket.id, Status.URGENT)
        assert ticket.created_at == created

    def test_reading_does_not_bump_it(self, manager):
        ticket = manager.add_ticket("Titolo")
        before = ticket.updated_at
        manager.tickets()
        manager.sorted_tickets()
        manager.get(ticket.id)
        manager.counts_by_status()
        assert ticket.updated_at == before


class TestSortingAndFiltering:
    @pytest.fixture
    def populated(self, manager):
        manager.add_ticket("Zeta", status=Status.DONE, due_date=date(2026, 1, 10))
        manager.add_ticket("alfa", status=Status.URGENT, due_date=date(2026, 3, 5))
        manager.add_ticket("Mezzo", status=Status.OPEN)
        return manager

    def test_sort_by_title_is_case_insensitive(self, populated):
        titles = [t.title for t in populated.sorted_tickets(SortField.TITLE, descending=False)]
        assert titles == ["alfa", "Mezzo", "Zeta"]

    def test_sort_by_status_puts_urgent_first(self, populated):
        first = populated.sorted_tickets(SortField.STATUS, descending=False)[0]
        assert first.status is Status.URGENT

    def test_tickets_without_a_deadline_sort_last_ascending(self, populated):
        order = populated.sorted_tickets(SortField.DUE_DATE, descending=False)
        assert [t.title for t in order] == ["Zeta", "alfa", "Mezzo"]

    def test_tickets_without_a_deadline_sort_last_descending_too(self, populated):
        # Reversing the column must not promote "no deadline" to the top.
        order = populated.sorted_tickets(SortField.DUE_DATE, descending=True)
        assert [t.title for t in order] == ["alfa", "Zeta", "Mezzo"]

    def test_filter_by_status(self, populated):
        result = populated.sorted_tickets(status=Status.OPEN)
        assert [t.title for t in result] == ["Mezzo"]

    def test_filter_by_text_matches_title_and_description(self, manager):
        manager.add_ticket("Relazione", description="niente")
        manager.add_ticket("Altro", description="parla di relazione")
        manager.add_ticket("Terzo", description="niente")
        assert len(manager.sorted_tickets(text="RELAZIONE")) == 2

    def test_filters_combine(self, populated):
        assert populated.sorted_tickets(status=Status.DONE, text="alfa") == []

    def test_default_sort_is_most_recently_updated_first(self, populated):
        oldest = populated.sorted_tickets(SortField.TITLE, descending=False)[0]
        populated.update_ticket(oldest.id, title="alfa modificato")
        assert populated.sorted_tickets()[0].id == oldest.id

    def test_counts_by_status_covers_every_status(self, populated):
        counts = populated.counts_by_status()
        assert set(counts) == set(Status)
        assert counts[Status.URGENT] == 1
        assert counts[Status.IN_PROGRESS] == 0


class TestPersistenceAcrossRestart:
    def test_everything_survives_a_new_manager(self, ticket_file):
        first = TicketManager(ticket_file)
        ticket = first.add_ticket(
            "Relazione trimestrale",
            description="Con accenti: perché, attività, così.",
            status=Status.IN_PROGRESS,
            due_date=date.today() + timedelta(days=7),
        )
        done = first.add_activity(ticket.id, "Esportare i dati")
        first.add_activity(ticket.id, "Impaginare")
        first.set_activity_completed(ticket.id, done.id, True)

        second = TicketManager(ticket_file)
        restored = second.get(ticket.id)
        assert restored == ticket
        assert restored.description == "Con accenti: perché, attività, così."
        assert restored.completed_count == 1
        assert restored.status is Status.IN_PROGRESS

    def test_the_default_path_is_used_when_none_is_given(self, isolate_data_dir):
        manager = TicketManager()
        assert manager.path.parent == isolate_data_dir
        manager.add_ticket("Sul percorso predefinito")
        assert TicketManager().tickets()[-1].title == "Sul percorso predefinito"
