# Progress

Where the project stands. Updated in the same commit as the work it describes.

**Current state:** Finished and packaged. All eight phases are done, 271 tests pass, and the
application has been run end to end against a scratch data file: created a ticket through the
dialog, closed it, reopened it in a fresh process with everything intact and the theme remembered,
then corrupted the file by hand and confirmed it reports and preserves rather than overwrites. It
now also builds into a Windows executable that starts from a Desktop icon.

**Next:** nothing planned. Ideas, none of them committed to, are at the bottom of this file.
Phase 8 was not planned either - it is what using the application turned up.

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

## Phase 7 - Packaging

Branch `phase/7-packaging`. Tag `v1.1.0-phase7`. Version 1.1.0.

The application could only be started with `python -m workflowapp` from an activated virtualenv,
which is not a thing the one person it was built for should have to do.

- [x] `tools/make_icon.py` and `workflowapp/gui/assets/app.ico` - the application finally has an
      icon. There was none, and no `setWindowIcon` call either
- [x] `workflowapp/gui/assets.py` - `app_icon()`, loaded from the package like the stylesheets
- [x] `setWindowIcon` on the application, plus the Windows AppUserModelID
- [x] `packaging/workflowapp.spec` - one `Analysis`, two `EXE` targets
- [x] `tools/build.ps1` and `tools/install-shortcut.ps1`
- [x] `requirements-build.txt` - PyInstaller, kept out of the dev set so CI does not install it
- [x] Tests: the resources resolve through `importlib.resources`, the `.ico` has all six sizes,
      and the `package-data` declaration names both
- [x] A `package` job in CI, on tags and `workflow_dispatch`
- [x] Both artefacts built and run end to end against a scratch data file

Two artefacts, roughly 110 MB as a folder and 44 MB as one file:

| | Starts in | For |
| --- | --- | --- |
| `dist\Workflow App\Workflow App.exe` | under a second | every day, through the Desktop shortcut |
| `dist\Workflow App portable.exe` | a few seconds | copying to another machine |

Decided while building it:

- **The icon is drawn by a script, not committed as a binary from nowhere.** `make_icon.py` is its
  source; the `.ico` is committed as its output so a build never depends on regenerating it. The
  same reasoning as the status dots in `status_badge.py`, which are painted rather than shipped.
- **A checkmark rather than a letter.** Two strokes stay legible at 16px, and drawing paths instead
  of text means no font dependency and the same result on every machine. The blue is `Status.OPEN`
  from the light palette, so the icon and the application agree rather than merely resembling
  each other.
- **The `.ico` container is assembled in Python.** Qt's ICO writer does one frame per file and
  Windows wants six in one container. The format is a six-byte header plus sixteen bytes per
  frame, and PNG frames are valid from Vista onwards - which is less code than a dependency.
- **`packaging/entry.py` rather than freezing `__main__.py`.** PyInstaller runs the entry script as
  `__main__` with no package context, and `from .gui.app import main` then has nothing to be
  relative to.
- **The version resource reads `workflowapp.__version__`.** `tests/test_packaging.py` exists to
  stop the version living in two places; a third hand-typed copy in the spec would walk past it.
- **UPX is off.** It saves perhaps a third of the size and is a reliable way to have an unsigned
  executable quarantined by antivirus.
- **The shortcut points into `dist\` rather than copying the build.** One place to rebuild over and
  no second copy of unknown age. The cost is that moving `dist\` breaks the shortcut, which
  `install-shortcut.ps1` says and the README repeats.
- **The `package` CI job does not run on pull requests.** It adds minutes to a run that finishes
  fast, and the thing it guards - a resource missing from the bundle - is already asserted by
  `test_packaging.py` on every run and by `build.ps1` on every build.

Learned while building it:

- **The window appearing at all is the proof the resources loaded.** `apply_theme` and `app_icon`
  both run before `MainWindow` exists, and both raise if their file is missing from the bundle, so
  a frozen build that shows a window has already demonstrated the part that usually breaks.
- **A onefile build runs as two processes**, and the window belongs to the child. Waiting on the
  process that was started looks exactly like an application that never opened.
- **Windows PowerShell reads a native command's stderr as failure.** PyInstaller logs its progress
  there, so `$?` is `$false` after a build that succeeded. `build.ps1` checks `$LASTEXITCODE`.
- **`Set-Content -Encoding utf8` writes a BOM** in Windows PowerShell, and `json.loads` refuses the
  result. A hand-written ticket file made this way is quarantined as corrupt - which is invariant 3
  working correctly, and confusing for exactly as long as it takes to notice the BOM.

## Phase 8 - The overdue filter, and a selected row you can read

Branch `phase/8-overdue-filter-and-contrast`.

Two unrelated things, found by using the application rather than by planning it.

- [x] `TicketSortProxy.set_overdue_filter` and a "Solo in scadenza" checkbox beside the status
      combo box. The first item off the list below, and the only one of them the brief implies
- [x] `QTableView::item:selected` in both stylesheets - the selected row was unreadable
- [x] Tests: the rule is present in both themes, and the title is measured on screen as still
      legible once its row is selected

**The selected row bug, because the cause is not where it looks.** The report was "I cannot see
the ticket's name when it is selected", in the light theme. It was not a colour that needed
darkening. Declaring `QTableView::item` at all - which both stylesheets do, for padding - hands
item drawing to `QStyleSheetStyle`, and under Qt's `windows11` style, the default on Windows 11,
that path takes the selected cell's *background* from the `::item` rule rather than from
`QTableView`'s `selection-background-color`. With no background declared there, a selected cell
kept the view's own white, while its text still took `selection-color`. White on white. The dark
theme had the identical defect and merely looked survivable: the row simply did not change colour.

Worth knowing about it:

- **Only the `windows11` style does this.** `windowsvista`, `Windows` and `Fusion` all paint the
  selection correctly with or without the rule - and `Fusion` is what the offscreen platform picks,
  so the test in CI would have measured a passing case forever. `tests/test_main_window.py` forces
  the style, or it would be asserting nothing.
- **The test measures pixels, not the stylesheet.** It finds the title's glyphs in an unselected
  row, where they are easy to see, then looks at those same pixels once the row is selected. That
  is a check on what the user sees; a check on the text of the `.qss` would have passed throughout
  the bug, since `selection-color: #ffffff` was there all along and did nothing.
- **A delegate for this was written and then deleted.** The worry was that the model's
  `ForegroundRole` - the muted grey of "Aggiornato", the red of an overdue date - would be painted
  on the blue selection. Measured with the delegate in and out, the rendered pixels were identical:
  the `::item:selected` rule already outranks a `ForegroundRole`. It would have been code that
  looked load-bearing and was not.

## Possible future work

None of this is planned, and none of it is needed for the brief.

- Reordering activities within a ticket.
- Exporting a ticket, or the list, as text.
- Signing the executable, so Windows stops warning on first run. Needs a certificate.
- An installer rather than a folder plus a shortcut script.

## Open questions

- Nothing outstanding.
