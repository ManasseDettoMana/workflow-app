"""The data model: a ticket, its activities, and the status it carries.

Everything here is plain Python. The ``to_dict``/``from_dict`` pair on each class
is the whole of the JSON representation; :mod:`workflowapp.core.store` only adds
the envelope and the file handling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from .errors import WorkflowAppError


def new_id() -> str:
    """A fresh identifier.

    A uuid rather than a counter: a max-plus-one counter has to be persisted
    alongside the tickets and hands out a duplicate the first time a ticket is
    deleted and another created.
    """
    return uuid.uuid4().hex


class Status(Enum):
    """The state of a ticket.

    **The value is a stable English token and is what gets stored.** The Italian
    label the user reads lives in ``gui.strings.STATUS_LABELS``. Writing "In
    Lavorazione" into the file would turn a change of wording into a data
    migration, and would make the file depend on the interface's language.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    URGENT = "urgent"

    @classmethod
    def from_token(cls, token: Any) -> Status:
        try:
            return cls(token)
        except ValueError:
            known = ", ".join(s.value for s in cls)
            raise WorkflowAppError(
                f"Stato del ticket non riconosciuto: {token!r}.",
                hint=f"Gli stati validi sono: {known}.",
            ) from None

    @property
    def priority(self) -> int:
        """Sort order for the status column: what needs attention first.

        Declaration order is the ticket's lifecycle, which is not the order
        anybody wants to read a list in. Urgent work comes first and finished
        work last, regardless of how the members happen to be declared.
        """
        return _PRIORITY[self]


_PRIORITY = {
    Status.URGENT: 0,
    Status.IN_PROGRESS: 1,
    Status.OPEN: 2,
    Status.DONE: 3,
}


def _required(raw: dict[str, Any], key: str, what: str) -> Any:
    if key not in raw:
        raise WorkflowAppError(
            f"Dati incompleti: manca il campo '{key}' in {what}.",
            hint="Il file dei ticket potrebbe essere stato modificato a mano.",
        )
    return raw[key]


def _parse_datetime(value: Any, key: str, what: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise WorkflowAppError(
            f"Data non valida nel campo '{key}' di {what}: {value!r}.",
            hint="Le date sono nel formato ISO 8601, ad esempio 2026-08-05T14:30:00.",
        ) from None


def _parse_date(value: Any, key: str, what: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise WorkflowAppError(
            f"Data non valida nel campo '{key}' di {what}: {value!r}.",
            hint="Le date sono nel formato ISO 8601, ad esempio 2026-08-05.",
        ) from None


@dataclass
class Activity:
    """One item on a ticket's todo list."""

    id: str
    description: str
    completed: bool = False

    @classmethod
    def create(cls, description: str) -> Activity:
        return cls(id=new_id(), description=description)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> Activity:
        if not isinstance(raw, dict):
            raise WorkflowAppError(
                "Dati non validi: un'attività non è un oggetto JSON.",
                hint="Il file dei ticket potrebbe essere stato modificato a mano.",
            )
        what = "un'attività"
        return cls(
            id=str(_required(raw, "id", what)),
            description=str(_required(raw, "description", what)),
            completed=bool(raw.get("completed", False)),
        )


@dataclass
class Ticket:
    """A unit of work, with a status and a list of activities.

    ``created_at`` and ``updated_at`` are naive local datetimes. This is a
    single-user application on one machine, so there is nothing for a timezone to
    disambiguate, and a naive value displays as it was recorded.

    ``due_date`` is genuinely optional. A ticket with no deadline is ordinary,
    and forcing one would only get a meaningless date typed into the field.
    """

    id: str
    title: str
    description: str = ""
    status: Status = Status.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_date: date | None = None
    activities: list[Activity] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        status: Status = Status.OPEN,
        due_date: date | None = None,
    ) -> Ticket:
        now = datetime.now()
        return cls(
            id=new_id(),
            title=title,
            description=description,
            status=status,
            created_at=now,
            updated_at=now,
            due_date=due_date,
        )

    @property
    def is_overdue(self) -> bool:
        """Past its due date and not finished.

        A done ticket is never overdue however long ago its deadline was; saying
        otherwise would leave the list permanently red.
        """
        if self.due_date is None or self.status is Status.DONE:
            return False
        return self.due_date < date.today()

    @property
    def completed_count(self) -> int:
        return sum(1 for a in self.activities if a.completed)

    def find_activity(self, activity_id: str) -> Activity | None:
        return next((a for a in self.activities if a.id == activity_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "activities": [a.to_dict() for a in self.activities],
        }

    @classmethod
    def from_dict(cls, raw: Any) -> Ticket:
        if not isinstance(raw, dict):
            raise WorkflowAppError(
                "Dati non validi: un ticket non è un oggetto JSON.",
                hint="Il file dei ticket potrebbe essere stato modificato a mano.",
            )
        what = "un ticket"
        due = raw.get("due_date")
        activities = raw.get("activities", [])
        if not isinstance(activities, list):
            raise WorkflowAppError(
                "Dati non validi: la lista delle attività di un ticket non è una lista.",
                hint="Il file dei ticket potrebbe essere stato modificato a mano.",
            )
        return cls(
            id=str(_required(raw, "id", what)),
            title=str(_required(raw, "title", what)),
            description=str(raw.get("description", "")),
            status=Status.from_token(_required(raw, "status", what)),
            created_at=_parse_datetime(_required(raw, "created_at", what), "created_at", what),
            updated_at=_parse_datetime(_required(raw, "updated_at", what), "updated_at", what),
            due_date=_parse_date(due, "due_date", what) if due is not None else None,
            activities=[Activity.from_dict(a) for a in activities],
        )
