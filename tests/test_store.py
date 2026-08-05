"""Persistence: the round trip, the atomic write, and refusing to destroy data."""

from __future__ import annotations

import json
import os

import pytest

from workflowapp.core import store
from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.models import Status, Ticket


class TestRoundTrip:
    def test_save_then_load(self, ticket_file, sample_ticket):
        store.save_tickets([sample_ticket], ticket_file)
        assert store.load_tickets(ticket_file) == [sample_ticket]

    def test_a_missing_file_is_the_first_run(self, ticket_file):
        assert not ticket_file.exists()
        assert store.load_tickets(ticket_file) == []
        # Reading must not create anything.
        assert not ticket_file.exists()

    def test_an_empty_list_round_trips(self, ticket_file):
        store.save_tickets([], ticket_file)
        assert store.load_tickets(ticket_file) == []

    def test_the_file_carries_a_schema_version(self, ticket_file, sample_ticket):
        store.save_tickets([sample_ticket], ticket_file)
        raw = json.loads(ticket_file.read_text(encoding="utf-8"))
        assert raw["schema"] == store.SCHEMA_VERSION
        assert isinstance(raw["tickets"], list)

    def test_accented_text_stays_readable_in_the_file(self, ticket_file):
        ticket = Ticket.create("Attività di verifica", description="Perché serve")
        store.save_tickets([ticket], ticket_file)
        text = ticket_file.read_text(encoding="utf-8")
        # ensure_ascii=False: the file is meant to be legible if opened by hand.
        assert "Attività" in text
        assert "\\u00e0" not in text

    def test_the_parent_directory_is_created_on_save(self, tmp_path, sample_ticket):
        nested = tmp_path / "does" / "not" / "exist" / "tickets.json"
        store.save_tickets([sample_ticket], nested)
        assert store.load_tickets(nested) == [sample_ticket]


class TestAtomicWrite:
    def test_no_temporary_file_is_left_behind(self, ticket_file, sample_ticket):
        store.save_tickets([sample_ticket], ticket_file)
        leftovers = [p.name for p in ticket_file.parent.iterdir() if p.name != ticket_file.name]
        assert leftovers == []

    def test_a_failed_rename_leaves_the_previous_file_intact(
        self, ticket_file, sample_ticket, monkeypatch
    ):
        # The point of the temporary file: if the write cannot be completed, the
        # data that was already there survives untouched.
        store.save_tickets([sample_ticket], ticket_file)
        original = ticket_file.read_text(encoding="utf-8")

        def boom(src, dst):
            raise OSError(13, "Permission denied")

        monkeypatch.setattr(store.os, "replace", boom)
        with pytest.raises(WorkflowAppError):
            store.save_tickets([Ticket.create("Non deve arrivare")], ticket_file)

        assert ticket_file.read_text(encoding="utf-8") == original
        leftovers = [p.name for p in ticket_file.parent.iterdir() if p.name != ticket_file.name]
        assert leftovers == [], "the temporary file was not cleaned up"

    def test_replace_is_used_rather_than_rename(self, ticket_file, sample_ticket):
        # os.rename refuses an existing destination on Windows, so saving twice
        # is the check that this is os.replace.
        store.save_tickets([sample_ticket], ticket_file)
        store.save_tickets([sample_ticket, Ticket.create("Secondo")], ticket_file)
        assert len(store.load_tickets(ticket_file)) == 2

    def test_the_temporary_file_is_written_beside_the_target(
        self, ticket_file, sample_ticket, monkeypatch
    ):
        # Same directory means same volume, and only a same-volume rename is
        # atomic. A temp file in %TEMP% would make the whole exercise pointless.
        seen = {}
        real_mkstemp = store.tempfile.mkstemp

        def spy(*args, **kwargs):
            seen["dir"] = kwargs.get("dir")
            return real_mkstemp(*args, **kwargs)

        monkeypatch.setattr(store.tempfile, "mkstemp", spy)
        store.save_tickets([sample_ticket], ticket_file)
        assert os.path.samefile(seen["dir"], ticket_file.parent)


class TestUnreadableFiles:
    def test_broken_json_raises_and_never_returns_empty(self, ticket_file):
        ticket_file.write_text("{questo non e json", encoding="utf-8")
        with pytest.raises(WorkflowAppError):
            store.load_tickets(ticket_file)

    def test_broken_json_is_moved_aside_rather_than_lost(self, ticket_file):
        ticket_file.write_text("{rotto", encoding="utf-8")
        with pytest.raises(WorkflowAppError) as excinfo:
            store.load_tickets(ticket_file)

        quarantined = list(ticket_file.parent.glob("tickets.json.corrupt-*"))
        assert len(quarantined) == 1
        assert quarantined[0].read_text(encoding="utf-8") == "{rotto"
        # The message must say where it went, or the user cannot get it back.
        assert quarantined[0].name in str(excinfo.value)

    def test_a_top_level_list_is_rejected(self, ticket_file):
        ticket_file.write_text("[]", encoding="utf-8")
        with pytest.raises(WorkflowAppError):
            store.load_tickets(ticket_file)

    def test_a_ticket_with_a_bad_field_is_reported_with_the_file(self, ticket_file, sample_ticket):
        raw = {"schema": 1, "tickets": [sample_ticket.to_dict()]}
        raw["tickets"][0]["status"] = "sconosciuto"
        ticket_file.write_text(json.dumps(raw), encoding="utf-8")

        with pytest.raises(WorkflowAppError) as excinfo:
            store.load_tickets(ticket_file)
        message = str(excinfo.value)
        assert "sconosciuto" in message
        assert "corrupt-" in message

    def test_quarantine_does_not_overwrite_an_earlier_one(self, ticket_file):
        for _ in range(3):
            ticket_file.write_text("{rotto", encoding="utf-8")
            with pytest.raises(WorkflowAppError):
                store.load_tickets(ticket_file)
        # Three failures, three preserved files - not one file overwritten twice.
        assert len(list(ticket_file.parent.glob("tickets.json.corrupt-*"))) == 3


class TestSchemaVersion:
    def test_a_newer_schema_is_refused_but_left_alone(self, ticket_file, sample_ticket):
        raw = {"schema": store.SCHEMA_VERSION + 1, "tickets": [sample_ticket.to_dict()]}
        text = json.dumps(raw)
        ticket_file.write_text(text, encoding="utf-8")

        with pytest.raises(WorkflowAppError) as excinfo:
            store.load_tickets(ticket_file)

        # This file is not corrupt, it is from the future. Moving it aside would
        # be destroying perfectly good data.
        assert ticket_file.read_text(encoding="utf-8") == text
        assert list(ticket_file.parent.glob("tickets.json.corrupt-*")) == []
        assert "recente" in str(excinfo.value)

    def test_a_nonsense_schema_is_treated_as_corruption(self, ticket_file):
        ticket_file.write_text(json.dumps({"schema": "uno", "tickets": []}), encoding="utf-8")
        with pytest.raises(WorkflowAppError):
            store.load_tickets(ticket_file)
        assert len(list(ticket_file.parent.glob("tickets.json.corrupt-*"))) == 1


class TestDefaultPath:
    def test_the_default_path_is_the_isolated_one(self, isolate_data_dir):
        # Proof that conftest's guard actually works: without it this would be
        # the developer's real %APPDATA% file.
        assert store.tickets_path().parent == isolate_data_dir

    def test_save_and_load_with_no_path_argument(self):
        ticket = Ticket.create("Percorso predefinito", status=Status.URGENT)
        store.save_tickets([ticket])
        assert store.load_tickets() == [ticket]
