# Contributing

Read `CLAUDE.md` for what the project is and what its invariants are, and `PROGRESS.md` for where
it currently stands. This file is only about how work gets from a working copy into `main`.

## Set up

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
.\tools\install-hooks.ps1          # once per clone
```

## The rule

**`main` always runs and is never committed to directly.** Every change reaches it through a
branch and a pull request whose CI run is green.

```
main
  phase/2-model-persistence     one branch per phase
  fix/sort-proxy-index          or per piece of work, named for what it does
```

```powershell
git switch -c phase/2-model-persistence
# ... work, with PROGRESS.md updated in the same commit as the work it describes
git push -u origin phase/2-model-persistence
gh pr create --base main
gh pr merge --merge            # once CI is green
git tag -a v0.2.0-phase2 -m "Phase 2: data model and persistence"
```

## How that rule is enforced, and how far

By a local `pre-push` hook, which refuses a push to `main` and runs `ruff` and the tests before
any other push. **Not by GitHub.** Branch protection and rulesets both answer

```
403 Upgrade to GitHub Pro or make this repository public
```

on this repository, which is private on a free account. This is not a permissions problem - the
token has admin on the repo - and it is recorded here so nobody spends an afternoon rediscovering
it. The options, none of which is free: upgrade the account, make the repository public, or accept
a local guardrail.

A local hook is a guardrail. `git push --no-verify` walks past it, and it only exists on machines
where `install-hooks.ps1` has been run. It catches the mistake people actually make; it does not
stop a determined push. CI on the pull request is the check that always runs.

## Commits

Conventional commits, imperative mood, in English, no emojis anywhere:

```
feat:  a capability the application did not have
fix:   a defect, with the failure it caused in the body
docs:  documentation only
test:  tests only
chore: version bumps, dependencies, tooling
refactor: no behaviour change
```

The body explains **why** when the diff does not. "Fixed the bug" says nothing a reader cannot
already see; "the table was sorted, so the selected row index addressed a different ticket in the
manager's list than the one on screen" says what to be careful of next time.

`PROGRESS.md` is updated in the same commit as the work it describes, never in a trailing "update
docs" commit. That is what makes a resumed session trustworthy.

## Before you push

```powershell
python -m ruff check .
python -m pytest -q
```

CI runs both on Windows against Python 3.11 and 3.13, with `QT_QPA_PLATFORM=offscreen`.

## What a review looks for

The invariants in `CLAUDE.md`, in this order:

1. Does anything under `core/` import PySide6?
2. Can the ticket file be written non-atomically, or overwritten after a failed read?
3. Is a status stored as an Italian label rather than its token?
4. Is `updated_at` bumped anywhere but `TicketManager._touch`?
5. Is there a user-visible Italian string outside `gui/strings.py`?
6. Does a slot that can reach the store fail to catch `WorkflowAppError`? PySide6 ends the process
   on an unhandled exception in a slot, so that is a crash rather than a message.

## Tags

An annotated tag per phase merge (`v0.2.0-phase2`), and `v1.0.0` at release, so any state is
recoverable by name rather than by hunting through the log. The version in `pyproject.toml` and
`workflowapp/__init__.py` is bumped with the phase, and CI checks that a tagged build's version
matches its tag.
