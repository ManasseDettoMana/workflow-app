# Put the application's icon on the Desktop and in the Start Menu.
#
#     .\tools\build.ps1
#     .\tools\install-shortcut.ps1
#
# The shortcuts point at dist\Workflow App\Workflow App.exe where it already is,
# rather than copying the build somewhere. One place to rebuild over, and no
# second copy to wonder about the age of. The consequence is that moving or
# deleting dist\ breaks the shortcuts - rerun this after moving the build.
#
#     .\tools\install-shortcut.ps1 -Remove      take them off again

[CmdletBinding()]
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "dist\Workflow App\Workflow App.exe"

$desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "Workflow App.lnk"
$startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "Workflow App.lnk"
$shortcuts = @($desktop, $startMenu)

if ($Remove) {
    foreach ($path in $shortcuts) {
        if (Test-Path $path) {
            Remove-Item $path -Force
            Write-Host "Removed $path"
        }
    }
    exit 0
}

if (-not (Test-Path $target)) {
    Write-Error "No build at $target. Run .\tools\build.ps1 first."
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
try {
    foreach ($path in $shortcuts) {
        $link = $shell.CreateShortcut($path)
        $link.TargetPath = $target
        # The application reads nothing from its own directory, but a shortcut
        # with no working directory starts the process in system32, which is a
        # confusing place for anything to go wrong in.
        $link.WorkingDirectory = Split-Path -Parent $target
        $link.IconLocation = "$target,0"
        $link.Description = "Gestore personale di ticket e attivita"
        $link.Save()
        Write-Host "Created $path"
    }
}
finally {
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell)
}

Write-Host ""
Write-Host "Done. Windows will warn once that the executable is unsigned:"
Write-Host "choose More info, then Run anyway."
