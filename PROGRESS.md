# Progress

Where the project stands. Updated in the same commit as the work it describes.

**Current state:** Phase 3 complete. The whole headless half of the application works and is
tested. Nothing on screen yet.

**Next:** Phase 4 - the GUI shell: the window, the ticket table and the themes.

## Phase 1 - Setup

Branch `phase/1-setup`. Tag `v0.1.0-phase1`.

- [x] Private GitHub repository `ManasseDettoMana/workflow-app`
- [x] `.gitignore`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- [x] `README.md` (Italian, for the user), `CLAUDE.md` and `CONTRIBUTING.md` (English, for whoever
      works on it), `PROGRESS.md`
- [x] `docs/prompt.md` - the original brief, moved here and kept for provenance
- [x] GitHub Actions CI: ruff, the no-Qt-in-core check and pytest, on Windows against 3.11 and 3.13
- [x] `tools/hooks/pre-push` and `tools/install-hooks.ps1`
- [x] `.venv` with the dev toolchain

## Phase 2 - Data model and persistence

Branch `phase/2-model-persistence`. Tag `v0.2.0-phase2`.

- [x] `core/errors.py` - `WorkflowAppError` with a user-safe message and an optional hint
- [x] `core/models.py` - `Status`, `Activity`, `Ticket`, each with `to_dict`/`from_dict`
- [x] `core/paths.py` - `%APPDATA%\WorkflowApp`, the `WORKFLOWAPP_DATA_DIR` override, the
      non-Windows fallback
- [x] `core/store.py` - `load_tickets`/`save_tickets`, atomic write, schema version, corrupt-file
      quarantine
- [x] Tests: round-trip, atomic write, missing file, corrupt file, unknown status token
- [x] `tests/conftest.py` isolates the data directory for the whole session, so a test that
      forgets its `tmp_path` cannot reach the real ticket file

Decided while building it:

- **`WorkflowAppError` messages are written in Italian, inside `core`.** Invariant 9 was amended
  to say so explicitly rather than left to be discovered. An error only makes sense next to the
  thing that failed, and a code table buys a second language this application does not have.
- **A file from a newer schema is refused but not quarantined.** It is not corrupt - it is good
  data this version cannot read - and moving it aside would be the destructive act the invariant
  exists to prevent. Only unparseable content is moved.
- **`Ticket.is_overdue` is false for a done ticket**, whatever its due date was, or every finished
  ticket stays marked late for ever.
- **`Status.priority` orders the list Urgente, In Lavorazione, Aperto, Fatto**, which is not the
  lifecycle order the enum is declared in.

## Phase 3 - Business logic

Branch `phase/3-manager`. Tag `v0.3.0-phase3`.

- [x] `core/manager.py` - `TicketManager`: the in-memory list, ticket CRUD, activity CRUD,
      `set_status`, filtering and sorting
- [x] `_touch` as the single place `updated_at` is bumped, followed by a save
- [x] Tests, including `tests/test_no_qt_in_core.py` (added in Phase 2)

Decided while building it:

- **`update_ticket` uses a sentinel default, not `None`.** Clearing a deadline is a real edit, so
  "leave this alone" and "set this to nothing" have to be different things to say.
- **Tickets with no due date sort last in both directions.** Folding the absent date into the sort
  key reads correctly ascending and then puts every undated ticket at the top the moment the user
  reverses the column.
- **`TicketManager.tickets()` returns a new list each call.** The `Ticket` objects inside it are
  shared and mutable - that is what makes editing work - but appending to the returned list must
  not add a ticket nothing will ever save.
- **Loading happens in the constructor and can raise.** An unreadable file is precisely what the
  user must be told about at startup, so the GUI constructs the manager inside a try block.

## Phase 4 - GUI shell

Branch `phase/4-gui-shell`.

- [ ] `gui/strings.py` - every Italian string
- [ ] `gui/theme.py` and `gui/themes/*.qss` - light and dark, per-theme status palettes, the
      preference in `QSettings`
- [ ] `gui/widgets/status_badge.py` - the runtime-painted coloured tag and its delegate
- [ ] `gui/widgets/ticket_table.py` - the table model and the sort proxy
- [ ] `gui/main_window.py`, `gui/app.py`, `__main__.py` - the window runs and lists tickets

## Phase 5 - Ticket dialog and CRUD

Branch `phase/5-ticket-dialog`.

- [ ] `gui/widgets/activity_list.py` - the checkable list with add and remove
- [ ] `gui/ticket_dialog.py` - one dialog in new and edit modes, optional due date
- [ ] Create, edit, delete and status change wired through the manager
- [ ] Confirmation before discarding edits and before deleting

## Phase 6 - Tests and polish

Branch `phase/6-tests-polish`.

- [ ] GUI tests with pytest-qt
- [ ] End-to-end: create, close, reopen, everything still there
- [ ] Italian and no-emoji sweep over the whole UI
- [ ] Spacing, tab order, window geometry remembered

## Open questions

- Nothing outstanding.
