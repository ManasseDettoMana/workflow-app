"""Reading and writing the ticket file.

The file is a JSON object with a schema version and a list of tickets::

    {"schema": 1, "tickets": [ ... ]}

The version is there so that a future change of shape has something to branch on.
A bare top-level list would leave no room for one.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import WorkflowAppError
from .models import Ticket
from .paths import tickets_path

SCHEMA_VERSION = 1


def load_tickets(path: Path | None = None) -> list[Ticket]:
    """Read the ticket file.

    A missing file is the first run and gives an empty list. Anything else that
    goes wrong raises, and **never degrades into an empty list**: the caller
    would then save that empty list back over data that was merely unreadable.

    Before raising over content this cannot parse, the file is moved aside as
    ``tickets.json.corrupt-<timestamp>``. That is deliberate belt and braces - it
    means even a caller that swallows the exception cannot destroy the original.
    """
    path = path or tickets_path()

    if not path.exists():
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowAppError(
            f"Impossibile leggere il file dei ticket:\n{path}",
            hint=f"Dettaglio: {exc.strerror or exc}.",
        ) from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        quarantined = _quarantine(path)
        raise WorkflowAppError(
            f"Il file dei ticket non è leggibile (riga {exc.lineno}, colonna {exc.colno}).",
            hint=f"Il file è stato conservato qui:\n{quarantined}",
        ) from exc

    return _tickets_from_payload(raw, path)


def _tickets_from_payload(raw: Any, path: Path) -> list[Ticket]:
    if not isinstance(raw, dict):
        raise WorkflowAppError(
            "Il file dei ticket non ha la struttura attesa.",
            hint=f"Il file è stato conservato qui:\n{_quarantine(path)}",
        )

    schema = raw.get("schema")
    if schema != SCHEMA_VERSION:
        # A newer schema is not corruption - the file is perfectly good, it was
        # just written by a version this one does not understand. Quarantining it
        # would be destructive, so this branch leaves the file exactly where it
        # is and only refuses to guess at its contents.
        if isinstance(schema, int) and schema > SCHEMA_VERSION:
            raise WorkflowAppError(
                f"Il file dei ticket è stato scritto da una versione più recente "
                f"dell'applicazione (schema {schema}).",
                hint="Aggiornare l'applicazione per aprirlo. Il file non è stato modificato.",
            )
        raise WorkflowAppError(
            f"Il file dei ticket dichiara uno schema non valido: {schema!r}.",
            hint=f"Il file è stato conservato qui:\n{_quarantine(path)}",
        )

    tickets = raw.get("tickets")
    if not isinstance(tickets, list):
        raise WorkflowAppError(
            "Il file dei ticket non contiene una lista di ticket.",
            hint=f"Il file è stato conservato qui:\n{_quarantine(path)}",
        )

    try:
        return [Ticket.from_dict(item) for item in tickets]
    except WorkflowAppError as exc:
        # models.py knows which field was wrong but nothing about the file, so
        # the path and the quarantine are added here, where they are known.
        raise WorkflowAppError(
            f"{exc.args[0]}",
            hint=f"Il file è stato conservato qui:\n{_quarantine(path)}",
        ) from exc


def save_tickets(tickets: list[Ticket], path: Path | None = None) -> None:
    """Write the ticket file, atomically.

    The whole file is rewritten on every change, so this must never be a
    truncate-then-write: interrupted between the two, that loses every ticket
    rather than one. Instead it writes a temporary file in the same directory -
    same directory so that it is on the same volume, which is what makes the
    rename atomic - flushes it to disk, and renames it over the target.

    ``os.replace`` overwrites an existing destination on Windows as well as on
    POSIX; ``os.rename`` does not, and would fail here every time after the first.
    """
    path = path or tickets_path()

    payload = {
        "schema": SCHEMA_VERSION,
        "tickets": [t.to_dict() for t in tickets],
    }
    # Serialised before anything is opened, so that a failure to serialise leaves
    # no temporary file behind and cannot touch the existing one.
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkflowAppError(
            f"Impossibile creare la cartella dei dati:\n{path.parent}",
            hint=f"Dettaglio: {exc.strerror or exc}.",
        ) from exc

    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
        # newline="\n" so the file does not pick up CRLF on Windows and change
        # byte for byte between machines.
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            # Without this the rename can land before the contents do, and a
            # power loss leaves a file that exists and is empty.
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    except OSError as exc:
        raise WorkflowAppError(
            f"Impossibile salvare i ticket:\n{path}",
            hint=f"Dettaglio: {exc.strerror or exc}.",
        ) from exc
    finally:
        if tmp_path is not None:
            # The rename did not happen, so this is ours to clean up. A failure
            # here is not worth reporting over the failure that caused it.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _quarantine(path: Path) -> Path:
    """Move an unreadable file aside and return where it went.

    Returns the original path unchanged if the move itself fails; the caller is
    already reporting a problem, and a second failure buried inside the first
    helps nobody.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    counter = 1
    while target.exists():
        target = path.with_name(f"{path.name}.corrupt-{stamp}-{counter}")
        counter += 1
    try:
        os.replace(path, target)
    except OSError:
        return path
    return target
