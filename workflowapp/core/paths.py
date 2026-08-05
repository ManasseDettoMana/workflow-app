"""Where the ticket file lives."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "WorkflowApp"
TICKETS_FILENAME = "tickets.json"

#: Overrides the data directory entirely. Tests set it so that a forgotten
#: ``tmp_path`` cannot reach the real ticket file, and it is how you run the
#: application against a scratch file without touching your own tickets.
DATA_DIR_ENV = "WORKFLOWAPP_DATA_DIR"


def data_dir() -> Path:
    """The directory holding the ticket file.

    ``%APPDATA%\\WorkflowApp`` on Windows, which is the target platform. The
    ``~/.workflowapp`` fallback is not cross-platform support - it is what keeps
    this function total on a machine where ``APPDATA`` is unset, so that
    importing the module never depends on the environment.

    The directory is not created here. Creating it is the writer's job, and a
    read of a file that has never been written should not leave a folder behind.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME
    return Path.home() / ".workflowapp"


def tickets_path() -> Path:
    return data_dir() / TICKETS_FILENAME
