# Progress

Where the project stands. Updated in the same commit as the work it describes.

**Current state:** Phase 1 complete. The repository, tooling and CI exist; no application code yet.

**Next:** Phase 2 - the data model and the JSON store.

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

Branch `phase/2-model-persistence`.

- [ ] `core/errors.py` - `WorkflowAppError` with a user-safe message and an optional hint
- [ ] `core/models.py` - `Status`, `Activity`, `Ticket`, each with `to_dict`/`from_dict`
- [ ] `core/paths.py` - `%APPDATA%\WorkflowApp`, the `WORKFLOWAPP_DATA_DIR` override, the
      non-Windows fallback
- [ ] `core/store.py` - `load_tickets`/`save_tickets`, atomic write, schema version, corrupt-file
      quarantine
- [ ] Tests: round-trip, atomic write, missing file, corrupt file, unknown status token

## Phase 3 - Business logic

Branch `phase/3-manager`.

- [ ] `core/manager.py` - `TicketManager`: the in-memory list, ticket CRUD, activity CRUD,
      `set_status`, filtering and sorting
- [ ] `_touch` as the single place `updated_at` is bumped, followed by a save
- [ ] Tests, including `tests/test_no_qt_in_core.py`

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
