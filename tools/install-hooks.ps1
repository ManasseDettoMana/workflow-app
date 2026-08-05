# Point this clone's hooks at tools/hooks.
#
# core.hooksPath rather than copying files into .git/hooks: a copy goes stale the
# moment somebody edits the hook, and nothing tells you that it has. This way the
# hook under version control is the hook that runs.
#
# Run once per clone:
#
#     .\tools\install-hooks.ps1

$ErrorActionPreference = "Stop"

$root = git rev-parse --show-toplevel
if (-not $?) {
    Write-Error "Not inside a git repository."
    exit 1
}

$hooks = Join-Path $root "tools/hooks"
if (-not (Test-Path $hooks)) {
    Write-Error "No hooks directory at $hooks."
    exit 1
}

git config core.hooksPath "tools/hooks"
Write-Host "core.hooksPath -> tools/hooks"

# Git for Windows runs hooks under its bundled sh, which honours the executable
# bit git records rather than any NTFS permission. Set it if it is missing, or
# the hook is ignored silently on a fresh clone.
$mode = git ls-files --stage tools/hooks/pre-push
if ($mode -and -not $mode.StartsWith("100755")) {
    git update-index --chmod=+x tools/hooks/pre-push
    Write-Host "marked tools/hooks/pre-push executable (commit this)"
}

Write-Host ""
Write-Host "Installed. Pushes to main are refused; every other push runs ruff and"
Write-Host "the tests first. Use --no-verify only when you mean to."
