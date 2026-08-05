"""The business logic between the interface and the file.

``TicketManager`` owns the in-memory list of tickets and is the only thing that
writes it. The interface asks it questions and tells it to change things; it
never reaches into the store, and it never keeps its own copy of a ticket.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from . import store
from .errors import WorkflowAppError
from .models import Activity, Status, Ticket

#: Distinguishes "leave this field alone" from "set this field to None", which
#: ``due_date`` genuinely needs - clearing a deadline is a real edit.
_UNSET: Any = object()


class SortField(Enum):
    """What a list of tickets can be ordered by."""

    TITLE = "title"
    STATUS = "status"
    DUE_DATE = "due_date"
    CREATED = "created_at"
    UPDATED = "updated_at"


class TicketManager:
    """The ticket list, and every operation that changes it.

    Loading happens in the constructor and can raise :class:`WorkflowAppError` -
    an unreadable file is exactly the thing the user has to be told about at
    startup, so the caller is expected to construct this inside a try block.
    """

    def __init__(self, path: Path | None = None):
        self._path = path
        self._tickets: list[Ticket] = []
        self.reload()

    # ---------------------------------------------------------------- reading

    def reload(self) -> None:
        """Re-read the file, discarding anything held in memory."""
        self._tickets = store.load_tickets(self._path)

    @property
    def path(self) -> Path:
        return self._path or store.tickets_path()

    def tickets(self) -> list[Ticket]:
        """The tickets, in the order they are held.

        A new list each time, so that a caller appending to what it got back
        cannot quietly add a ticket that was never saved. The ``Ticket`` objects
        themselves are shared and mutable - that is deliberate, and is why
        nothing outside this class should be assigning to their fields.
        """
        return list(self._tickets)

    def get(self, ticket_id: str) -> Ticket:
        ticket = next((t for t in self._tickets if t.id == ticket_id), None)
        if ticket is None:
            raise WorkflowAppError(
                "Il ticket richiesto non esiste più.",
                hint="Potrebbe essere stato eliminato. Aggiornare l'elenco.",
            )
        return ticket

    def sorted_tickets(
        self,
        field: SortField = SortField.UPDATED,
        descending: bool = True,
        status: Status | None = None,
        text: str | None = None,
    ) -> list[Ticket]:
        """Filtered and ordered, for display.

        ``text`` matches the title or the description, case-insensitively.
        """
        result = self._tickets
        if status is not None:
            result = [t for t in result if t.status is status]
        if text:
            needle = text.casefold()
            result = [
                t
                for t in result
                if needle in t.title.casefold() or needle in t.description.casefold()
            ]

        if field is SortField.DUE_DATE:
            # Tickets with no deadline go last in *both* directions. Folding the
            # absent date into the sort key instead - (t.due_date is None, ...) -
            # reads correctly ascending and then puts them all at the top the
            # moment the user reverses the column, which is not what "no
            # deadline" means.
            dated = [t for t in result if t.due_date is not None]
            undated = [t for t in result if t.due_date is None]
            dated.sort(key=lambda t: t.due_date, reverse=descending)
            return dated + undated

        return sorted(result, key=_sort_key(field), reverse=descending)

    def counts_by_status(self) -> dict[Status, int]:
        return {status: sum(1 for t in self._tickets if t.status is status) for status in Status}

    # --------------------------------------------------------------- tickets

    def add_ticket(
        self,
        title: str,
        description: str = "",
        status: Status = Status.OPEN,
        due_date: date | None = None,
        activities: list[Activity] | None = None,
    ) -> Ticket:
        ticket = Ticket.create(
            title=title.strip(),
            description=description,
            status=status,
            due_date=due_date,
        )
        if activities:
            ticket.activities = list(activities)
        self._tickets.append(ticket)
        self._save()
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        title: str = _UNSET,
        description: str = _UNSET,
        status: Status = _UNSET,
        due_date: date | None = _UNSET,
        activities: list[Activity] = _UNSET,
    ) -> Ticket:
        """Change any subset of a ticket's fields.

        A field left out is left alone. ``due_date=None`` clears the deadline,
        which is why the default is a sentinel and not ``None``.
        """
        ticket = self.get(ticket_id)
        if title is not _UNSET:
            ticket.title = title.strip()
        if description is not _UNSET:
            ticket.description = description
        if status is not _UNSET:
            ticket.status = status
        if due_date is not _UNSET:
            ticket.due_date = due_date
        if activities is not _UNSET:
            ticket.activities = list(activities)
        self._touch(ticket)
        return ticket

    def delete_ticket(self, ticket_id: str) -> None:
        ticket = self.get(ticket_id)
        self._tickets.remove(ticket)
        self._save()

    def set_status(self, ticket_id: str, status: Status) -> Ticket:
        return self.update_ticket(ticket_id, status=status)

    # ------------------------------------------------------------ activities

    def add_activity(self, ticket_id: str, description: str) -> Activity:
        ticket = self.get(ticket_id)
        activity = Activity.create(description.strip())
        ticket.activities.append(activity)
        self._touch(ticket)
        return activity

    def remove_activity(self, ticket_id: str, activity_id: str) -> None:
        ticket = self.get(ticket_id)
        activity = self._activity(ticket, activity_id)
        ticket.activities.remove(activity)
        self._touch(ticket)

    def set_activity_completed(self, ticket_id: str, activity_id: str, completed: bool) -> Activity:
        ticket = self.get(ticket_id)
        activity = self._activity(ticket, activity_id)
        activity.completed = completed
        self._touch(ticket)
        return activity

    def set_activity_description(
        self, ticket_id: str, activity_id: str, description: str
    ) -> Activity:
        ticket = self.get(ticket_id)
        activity = self._activity(ticket, activity_id)
        activity.description = description.strip()
        self._touch(ticket)
        return activity

    # --------------------------------------------------------------- private

    @staticmethod
    def _activity(ticket: Ticket, activity_id: str) -> Activity:
        activity = ticket.find_activity(activity_id)
        if activity is None:
            raise WorkflowAppError(
                "L'attività richiesta non esiste più.",
                hint="Potrebbe essere stata eliminata. Riaprire il ticket.",
            )
        return activity

    def _touch(self, ticket: Ticket) -> None:
        """Record that a ticket changed, then persist.

        Invariant 5: this is the **only** place ``updated_at`` is assigned.
        Every mutating method above ends here, so no path can change a ticket
        and leave its timestamp - or the file - behind.
        """
        ticket.updated_at = datetime.now()
        self._save()

    def _save(self) -> None:
        store.save_tickets(self._tickets, self._path)


def _sort_key(field: SortField):
    if field is SortField.TITLE:
        return lambda t: t.title.casefold()
    if field is SortField.STATUS:
        return lambda t: t.status.priority
    if field is SortField.CREATED:
        return lambda t: t.created_at
    return lambda t: t.updated_at
