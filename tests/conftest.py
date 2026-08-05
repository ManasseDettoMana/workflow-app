"""Shared fixtures, and the guard that keeps tests away from real data.

``isolate_data_dir`` is autouse and session-scoped. Without it, any test that
calls ``store.load_tickets()`` or ``TicketManager()`` with no argument would
reach ``%APPDATA%\\WorkflowApp\\tickets.json`` - the developer's actual tickets -
and the write path would happily replace them. It is easy to forget a ``tmp_path``
in one test out of forty, so this makes forgetting harmless rather than relying
on nobody ever doing it.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from workflowapp.core.models import Activity, Status, Ticket
from workflowapp.core.paths import DATA_DIR_ENV


@pytest.fixture(autouse=True, scope="session")
def isolate_data_dir(tmp_path_factory):
    import os

    scratch = tmp_path_factory.mktemp("data-dir")
    previous = os.environ.get(DATA_DIR_ENV)
    os.environ[DATA_DIR_ENV] = str(scratch)
    yield scratch
    if previous is None:
        del os.environ[DATA_DIR_ENV]
    else:
        os.environ[DATA_DIR_ENV] = previous


@pytest.fixture
def ticket_file(tmp_path):
    """A path in a fresh directory. The file itself does not exist yet."""
    return tmp_path / "tickets.json"


@pytest.fixture
def sample_ticket():
    """A ticket exercising every field, including the ones with defaults."""
    return Ticket(
        id="abc123",
        title="Preparare la relazione trimestrale",
        description="Raccogliere i dati e impaginare il documento.",
        status=Status.IN_PROGRESS,
        created_at=datetime(2026, 8, 1, 9, 30, 0),
        updated_at=datetime(2026, 8, 3, 16, 45, 12),
        due_date=date(2026, 8, 20),
        activities=[
            Activity(id="act1", description="Esportare i dati", completed=True),
            Activity(id="act2", description="Impaginare", completed=False),
        ],
    )
