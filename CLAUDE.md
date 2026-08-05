# CLAUDE.md

Guidance for Claude Code when working in this repository. Read `PROGRESS.md` next.

## What this project is

**Workflow App** - a lightweight offline desktop application for managing one person's work
workflow, like a simplified ticketing system. A ticket has a title, a description, an opening date,
an update date, an optional due date, a colour-tagged status, and a list of activities to tick off.

It is deliberately small. One user, one machine, no server, no database, no accounts, no
synchronisation, no attachments, no notifications. Data is a single JSON file under `%APPDATA%`.

The original brief is `docs/prompt.md`. Where this file and that one disagree, this file won.
The disagreements were settled with the user and are recorded under "Decisions" below.

The sibling repositories `../dynamic-reader` (xfafiller) and `../pdf-xfa-tools` are the reference
for house style: package layout, ruff configuration, the CI workflow, the pre-push hook and the
commit conventions here all come from them.

## Commands

```powershell
.venv\Scripts\Activate.ps1                      # the project virtualenv
python -m pip install -r requirements-dev.txt   # full dev environment
python -m workflowapp                           # the application
python -m pytest -q                             # test suite
python -m pytest -q -m "not gui"                # headless core only, no Qt platform needed
python -m pytest -q tests/test_store.py         # one file
python -m pytest -q -k atomic                   # one test by name
python -m ruff check .                          # lint
python -m ruff check . --fix                    # and fix what is mechanical
.\tools\install-hooks.ps1                       # once per clone: the pre-push guardrail
```

The GUI tests need a Qt platform plugin. CI sets `QT_QPA_PLATFORM=offscreen`; do the same when
running them over SSH or in a container, or use `-m "not gui"` to skip them.

Set `WORKFLOWAPP_DATA_DIR` to work against a scratch ticket file instead of the real one:

```powershell
$env:WORKFLOWAPP_DATA_DIR = "$env:TEMP\workflowapp-scratch"; python -m workflowapp
```

## Layout

```
workflowapp/core/     headless: models, persistence, business logic. No PySide6, ever.
  errors.py           WorkflowAppError - user-safe message plus optional hint
  models.py           Status, Activity, Ticket; to_dict/from_dict for each
  paths.py            data_dir, tickets_path; the WORKFLOWAPP_DATA_DIR override
  store.py            load_tickets/save_tickets; atomic write, corrupt-file quarantine
  manager.py          TicketManager - the in-memory list, CRUD, saves on every change
workflowapp/gui/      depends on core, never the reverse
  app.py              build_application, main
  main_window.py      toolbar, table, and the wiring to the manager
  ticket_dialog.py    one dialog, two modes: new and edit
  strings.py          every Italian string in the application
  theme.py            QSS loading, the per-theme status palettes, QSettings persistence
  widgets/
    ticket_table.py   TicketTableModel + the sort proxy
    status_badge.py   status_icon and StatusDelegate - the coloured tag
    activity_list.py  the checkable activity list with add and remove
  themes/
    light.qss, dark.qss
tests/                mirrors the module names; conftest.py isolates the data directory
docs/prompt.md        the original brief, kept for provenance
```

## Architecture in one line

**A headless core the GUI sits on top of.** `core/` knows about tickets, files and rules; `gui/`
knows about Qt and Italian. The dependency only ever points one way, which is what lets the whole
data layer be tested without a display.

## Invariants

These are not style preferences. Breaking them loses a user's tickets or misleads them.

1. **`core/` must never import PySide6.** It is what keeps the data layer testable headlessly and
   the rules independent of the interface. `tests/test_no_qt_in_core.py` asserts it and CI checks
   it separately.
2. **The ticket file is written atomically.** `store.save_tickets` serialises to a temporary file
   in the same directory and then `os.replace()`s it onto the target. The whole file is rewritten
   on every single change, so a truncating write interrupted at the wrong moment would lose every
   ticket rather than one.
3. **A file that cannot be read is never overwritten.** Unparseable JSON, a bad schema version or
   an unknown status token all raise `WorkflowAppError` - they never degrade to "start with an
   empty list", because the next change would then save that empty list over the user's data.
   `store.py` moves the unreadable file aside as `tickets.json.corrupt-<timestamp>` first, so even
   a caller that ignores the error cannot destroy it.
4. **Status is stored as a stable English token, never as its Italian label.** The JSON holds
   `open`, `in_progress`, `done`, `urgent`; `strings.STATUS_LABELS` maps those to what the user
   reads. Storing `"In Lavorazione"` would turn every wording change into a data migration.
5. **`updated_at` is bumped in exactly one place** - `TicketManager._touch`, called by every
   mutating method, which then saves. Bumping it at call sites is how one path ends up forgetting.
6. **The interface never owns ticket state.** `TicketManager` holds the list; the table model and
   the dialog read from it and write through it. A widget keeping its own copy is how the table
   and the file come to disagree.
7. **Nothing that discards a user's edits happens silently.** Cancelling a dialog with unsaved
   changes asks first, and so does deleting a ticket.
8. **No emojis** anywhere - UI, code, comments, docs or commit messages.
9. **Code, comments, docstrings and documentation in English. Every string the user reads in
   Italian.** Interface text - labels, buttons, column headings, confirmations - is defined in
   `gui/strings.py`, and a literal Italian string among the widgets is a bug: one file is what
   makes "is all of the UI actually Italian?" a question with an answer.

   The messages carried by `WorkflowAppError` are the **one deliberate exception**: they are
   written in Italian at the point they are raised, inside `core/`. An error message only makes
   sense next to the thing that failed, and routing them through a code table - which is what
   `../dynamic-reader` does - buys a second language this application does not have. If a second
   language is ever wanted, that indirection is the change to make, and it is confined to `core`.

## Decisions, and what they overrode

`docs/prompt.md` asked for some things this repository deliberately does differently. Do not
"fix" these back.

- **Italian only in the UI, not in the code.** The brief asked for Italian identifiers, comments
  and docs. House style across the three sibling repositories is English code with translated
  user-facing strings, and that won. Hence `Ticket.title`, not `Ticket.titolo`, and hence
  `gui/strings.py`.
- **A package with `pyproject.toml`, not `src/` plus `main.py`.** The brief sketched a loose `src/`
  tree. `xfafiller` is the model instead: an importable, installable package run as
  `python -m workflowapp`.
- **`CLAUDE.md` and `PROGRESS.md`, not `docs/context.txt` and `docs/todo.md`.** Same purpose -
  letting a future session resume - in the form the other repositories already use. Two sets of
  files describing one project drift apart.
- **`uuid4().hex` ids, not a counter.** A max-plus-one counter has to be persisted and breaks the
  moment a ticket is deleted.
- **The due date is optional.** The brief implies every ticket has one. A ticket with no deadline
  is ordinary, and a required date would be answered with a meaningless one.

## Environment facts that are easy to get wrong

- **A `QSortFilterProxyModel` between the view and the model means view indexes are not model
  indexes.** Anything taking a selection from the view must call `proxy.mapToSource()` before it
  indexes the ticket list. Sorting the table and then deleting the wrong ticket is the failure
  this causes, and it looks like a data bug rather than an index bug.
- **Status colours live in Python, per theme, not in the QSS.** A `QStyledItemDelegate` paints
  them, and a stylesheet cannot reach into a delegate. They are also genuinely different per
  theme: the amber that reads on white is nearly invisible on dark grey.
- **The `.qss` files must stay declared in `[tool.setuptools.package-data]`.** Left out, they load
  fine from a source checkout and are missing from an installed build, where the application
  starts unstyled with nothing to say why.
- **`QSettings` on Windows writes to the registry**, under `HKCU\Software\ManasseDettoMana\
  Workflow App`. It is not a file in the data directory, so `WORKFLOWAPP_DATA_DIR` does not
  isolate it. `tests/conftest.py` switches the default format to `IniFormat` under a scratch
  directory for the whole session, which is what stops a test rewriting your own saved theme and
  window position.
- **`isolate_data_dir` is session-scoped and shared; `scratch_data_dir` is per test.** Use the
  latter for anything that deliberately writes a broken ticket file. A `tickets.json.corrupt-*`
  left in the shared directory is still there when the next test looks, and the failure surfaces
  somewhere unrelated to the test that caused it.
- **PySide6 6.11 marks every `invalidate*Filter` variant deprecated** - `invalidateFilter`,
  `invalidateRowsFilter`, `invalidateColumnsFilter`. Plain `invalidate()` is the one that is not.
  `pyproject.toml` turns a `DeprecationWarning` raised from `workflowapp` into an error, so the
  next one of these fails the suite rather than scrolling past in the warnings summary.
- **A `QPainter` must be `end()`ed before the `QPixmap` it drew into is used.** Returning the
  pixmap while the painter is still alive produces a warning on every repaint, and the icon is
  intermittently blank.
- **The floor is Python 3.11, not 3.10**, for `tomllib` in the standard library and a
  `date.fromisoformat` that is not strict about the exact `YYYY-MM-DD` spelling. Dates are still
  written with `isoformat()` so the stored form is canonical whatever reads it.
- **PySide6 ends the process on an unhandled exception inside a slot.** Every slot that can reach
  the store catches `WorkflowAppError` and shows it in a `QMessageBox`; anything uncaught is a
  crash, not a message.
- **Do not pipe `pip install` into `tail` or anything else** - a pipeline reports the exit code of
  its last stage, so a failed install looks like a successful one.

## Conventions

- Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`), imperative
  mood, in English. The body explains *why* when the diff does not.
- One branch per phase, merged into `main` through a PR with green CI. `main` is never committed
  to directly. See `CONTRIBUTING.md`.
- `PROGRESS.md` is updated in the same commit as the work it describes, never in a trailing
  "update docs" commit.
- Errors raised by `core` subclass `WorkflowAppError` and carry a message the user can read, plus
  an optional `hint`. The GUI prints `str(exc)`, so no tracebacks leak.
- **`main` is not protected on GitHub and cannot be.** Branch protection and rulesets both answer
  `403 Upgrade to GitHub Pro or make this repository public` on a private repo on a free account.
  `tools/hooks/pre-push` enforces it locally instead: run `.\tools\install-hooks.ps1` once per
  clone. It is a guardrail, not a gate - `--no-verify` walks past it - and CI on the PR is the
  check that always runs.
- `gh` is installed and authenticated as `ManasseDettoMana` with `repo` and `workflow` scopes.
  Pull requests are opened and merged with it.
