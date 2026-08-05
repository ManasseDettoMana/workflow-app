# Progress

Where the project stands. Updated in the same commit as the work it describes.

**Current state:** Finished. All six phases are done, 257 tests pass, and the application has been
run end to end against a scratch data file: created a ticket through the dialog, closed it,
reopened it in a fresh process with everything intact and the theme remembered, then corrupted the
file by hand and confirmed it reports and preserves rather than overwrites.

**Next:** nothing planned. Ideas, none of them committed to, are at the bottom of this file.

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

Branch `phase/4-gui-shell`. Tag `v0.4.0-phase4`.

- [x] `gui/strings.py` - every Italian string
- [x] `gui/theme.py` and `gui/themes/*.qss` - light and dark, per-theme status palettes, the
      preference in `QSettings`
- [x] `gui/widgets/status_badge.py` - the runtime-painted coloured tag and its delegate
- [x] `gui/widgets/ticket_table.py` - the table model and the sort proxy
- [x] `gui/main_window.py`, `gui/app.py`, `__main__.py` - the window runs and lists tickets
- [x] Search box, status filter, status bar with the visible/total count and the overdue count
- [x] Delete with confirmation; window geometry remembered

Decided while building it:

- **Anything acting on the selection reads `TICKET_ID_ROLE`, never the row number.** With a sort
  proxy between the view and the model those are different numbers, and confusing them deletes the
  wrong ticket while looking like data corruption. `test_deleting_the_right_ticket_after_sorting`
  is the guard.
- **Status colours are a Python palette per theme, not QSS.** A delegate paints them and a
  stylesheet cannot reach inside one - and the amber that reads on white is nearly invisible on
  dark grey, so one palette would not have worked anyway.
- **The theme toggle has to repaint the dots itself.** The stylesheet reapplies; a delegate and a
  `ForegroundRole` do not.
- **`invalidate()`, not `invalidateFilter()`.** PySide6 6.11 deprecates every `invalidate*Filter`
  variant. `DeprecationWarning` from `workflowapp` is now an error in the test configuration.

## Phase 5 - Ticket dialog and CRUD

Branch `phase/5-ticket-dialog`. Tag `v0.5.0-phase5`.

- [x] `gui/widgets/activity_list.py` - the checkable list with add and remove
- [x] `gui/ticket_dialog.py` - one dialog in new and edit modes, optional due date
- [x] Create, edit, delete and status change wired through the manager
- [x] Confirmation before discarding edits and before deleting
- [x] Double-click opens the detail dialog; an empty title is refused

Decided while building it:

- **The dialog returns a `TicketDraft`, it does not edit the ticket.** Cancel cannot cancel
  anything if the form has been mutating the live object as the user types. The activity list
  copies its `Activity` objects for the same reason.
- **`_dirty` is reset at the end of `__init__`.** Populating the fields fires the same signals
  typing does, so without the reset the dialog opens already believing it was edited and asks
  about discarding changes nobody made.
- **An activity whose text was cleared is dropped on save.** A row the user emptied is not an
  activity, and keeping it would write a nameless entry into the file.
- **Editing is one `update_ticket` call, not one per field**, so a five-field edit is one
  timestamp bump and one write.

Learned while testing it:

- **`QDialog.result()` is `Rejected` from construction**, because `Rejected` is 0. Asserting on it
  to check "did cancelling cancel?" passes before anything happens. The tests assert on
  `isVisible()` instead.
- **`hasFocus()` is unobservable under `QT_QPA_PLATFORM=offscreen`** - there is no active window to
  hold focus - so it is not something the suite can check.

## Phase 6 - Tests and polish

Branch `phase/6-tests-polish`. Tag `v1.0.0-phase6`.

- [x] GUI tests with pytest-qt (from Phase 4 onwards, 257 in total)
- [x] End-to-end: create, close, reopen, everything still there
- [x] Italian and no-emoji sweep, both as automated tests
- [x] Enter opens the selected ticket, as the toolbar tooltip already promised
- [x] Changing the theme no longer drops the selection
- [x] Window geometry remembered (Phase 4)

`tests/test_conventions.py` is the interesting one. Invariants 8 and 9 are exactly the sort of
rule that holds for a month and then quietly stops, so both are now checked rather than trusted:

- **No emoji**, by Unicode range rather than by "is it ASCII". Italian needs the accented letters,
  and `docs/prompt.md` draws a directory tree out of box-drawing characters - both are category
  `So`, so the naive check fails on the brief itself. It also caught the emoji in its own test
  data, which is the sort of thing that makes you believe a test.
- **No Italian outside `gui/strings.py`**, by parsing every GUI module and comparing its string
  literals against an explicit allowlist. Everything on that list is technical - colours, Qt object
  names, `QSettings` keys, format templates. A new entry is a decision somebody has to make on
  purpose, and Italian does not belong in it.

Learned while writing them:

- **A session-scoped scratch directory is the wrong home for a test that writes a broken file.**
  `isolate_data_dir` exists so a forgotten `tmp_path` cannot reach real tickets, and it is shared;
  a `tickets.json.corrupt-*` left in it is still there when the next test looks, and the failure
  then surfaces somewhere unrelated. `scratch_data_dir` is the per-test version.

## Possible future work

None of this is planned, and none of it is needed for the brief.

- Filtering by "overdue" as well as by status.
- Reordering activities within a ticket.
- Exporting a ticket, or the list, as text.
- A packaged executable. The `.qss` files are already declared as package data, which is the part
  that usually gets missed.

## Open questions

- Nothing outstanding.
