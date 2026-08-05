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


@pytest.fixture(autouse=True, scope="session")
def isolate_settings(tmp_path_factory):
    """Keep QSettings out of the real registry.

    On Windows ``QSettings`` writes to ``HKCU\\Software\\...``, which is not in
    the data directory and so is not covered by ``isolate_data_dir``. Switching
    the default format to an ini file under a scratch directory means no test can
    change the developer's saved theme or window geometry.
    """
    from PySide6.QtCore import QSettings

    scratch = tmp_path_factory.mktemp("settings")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(scratch))
    return scratch


@pytest.fixture
def isolated_settings(isolate_settings):
    """As above, and empty at the start and end of the test."""
    from workflowapp.gui import theme

    theme.settings().clear()
    yield isolate_settings
    theme.settings().clear()


@pytest.fixture(autouse=True)
def reset_active_theme():
    """The active theme is module state, so it leaks between tests unless reset."""
    yield
    from workflowapp.gui import theme

    theme._active = theme.Theme.LIGHT


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
