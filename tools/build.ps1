# Build the Windows executables.
#
#     .\tools\build.ps1
#
# Produces both artefacts from one PyInstaller run:
#
#     dist\Workflow App\Workflow App.exe   the everyday build, starts immediately
#     dist\Workflow App portable.exe       one file to copy elsewhere, slower to start
#
# Then run .\tools\install-shortcut.ps1 to put the Desktop and Start Menu icons
# on the folder build.
#
# Needs the build dependency, which is not in requirements-dev.txt:
#
#     python -m pip install -r requirements-build.txt

[CmdletBinding()]
param(
    # Skip the icon regeneration. The .ico is committed, so this is only ever
    # needed after editing tools\make_icon.py.
    [switch]$SkipIcon
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

try {
    # The project virtualenv if there is one, whatever is on PATH otherwise, so
    # this works the same locally and on a CI runner.
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = "python"
    }

    # $LASTEXITCODE rather than $? throughout: PyInstaller logs its progress to
    # stderr, and Windows PowerShell reads a native command's stderr as failure
    # whatever the process actually returned. Only the exit code means anything.
    & $python -c "import PyInstaller"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller is missing. Run: python -m pip install -r requirements-build.txt"
        exit 1
    }

    if (-not $SkipIcon) {
        Write-Host "Drawing the icon..."
        & $python (Join-Path $root "tools\make_icon.py")
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    # build\ is PyInstaller's cache. Stale entries in it are how a rename or a
    # dropped data file survives into a build that no longer declares it.
    foreach ($stale in @("build", "dist")) {
        $path = Join-Path $root $stale
        if (Test-Path $path) {
            Write-Host "Removing $stale\..."
            Remove-Item -Recurse -Force $path
        }
    }

    Write-Host "Running PyInstaller..."
    & $python -m PyInstaller --noconfirm --clean (Join-Path $root "packaging\workflowapp.spec")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "The build failed."
        exit 1
    }

    $folder = Join-Path $root "dist\Workflow App\Workflow App.exe"
    $portable = Join-Path $root "dist\Workflow App portable.exe"

    # The stylesheets are the thing that goes missing without anyone noticing:
    # left out of the bundle the application starts unstyled and says nothing.
    # Checked here rather than discovered by whoever double-clicks the icon.
    $bundled = Join-Path $root "dist\Workflow App\_internal\workflowapp\gui"
    $required = @(
        (Join-Path $bundled "themes\light.qss"),
        (Join-Path $bundled "themes\dark.qss"),
        (Join-Path $bundled "assets\app.ico")
    )
    foreach ($file in $required) {
        if (-not (Test-Path $file)) {
            Write-Error "Missing from the bundle: $file. Check datas in packaging\workflowapp.spec."
            exit 1
        }
    }

    Write-Host ""
    Write-Host "Built:"
    foreach ($artefact in @($folder, $portable)) {
        if (Test-Path $artefact) {
            $size = [math]::Round((Get-Item $artefact).Length / 1MB, 1)
            Write-Host ("  {0}  ({1} MB)" -f $artefact, $size)
        }
        else {
            Write-Error "Expected artefact is missing: $artefact"
            exit 1
        }
    }

    $folderSize = [math]::Round(
        ((Get-ChildItem (Join-Path $root "dist\Workflow App") -Recurse |
            Measure-Object -Property Length -Sum).Sum / 1MB), 1)
    Write-Host ("  the folder build totals {0} MB" -f $folderSize)
    Write-Host ""
    Write-Host "Next: .\tools\install-shortcut.ps1"
}
finally {
    Pop-Location
}
