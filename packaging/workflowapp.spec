# PyInstaller spec: the Windows build. Run it through tools\build.ps1.
#
# Two artefacts from one Analysis, because analysing PySide6 twice takes twice
# as long and produces the same answer:
#
#   dist\Workflow App\Workflow App.exe   the everyday build. Starts immediately;
#                                        tools\install-shortcut.ps1 points the
#                                        Desktop and Start Menu icons at it.
#   dist\Workflow App portable.exe       one file to copy to another machine.
#                                        Unpacks to %TEMP% on every launch, so
#                                        several seconds to the first window.
#
# Notes for anyone changing this:
#
# * The bundled layout must stay workflowapp/gui/themes/*.qss and
#   workflowapp/gui/assets/*.ico. gui/theme.py and gui/assets.py reach them with
#   importlib.resources.files("workflowapp.gui").joinpath("themes/..."), which
#   works under a frozen build only because the tree matches. Neither directory
#   is a package, and neither should become one.
# * console=False is the same decision pyproject.toml records as gui-scripts:
#   no console window is to appear behind the application.
# * UPX is off. It saves perhaps a third of the size and is a reliable way to
#   have an unsigned executable quarantined by antivirus.

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent

# Both the project (for workflowapp.__version__) and this directory (for
# file_version_info) have to be importable while the spec runs.
for entry in (str(PROJECT_ROOT), SPECPATH):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from file_version_info import version_info  # noqa: E402

PACKAGE = PROJECT_ROOT / "workflowapp"
ICON = PACKAGE / "gui" / "assets" / "app.ico"

FOLDER_NAME = "Workflow App"
PORTABLE_NAME = "Workflow App portable"

datas = [
    (str(PACKAGE / "gui" / "themes"), "workflowapp/gui/themes"),
    (str(PACKAGE / "gui" / "assets"), "workflowapp/gui/assets"),
]

# Only QtCore, QtGui and QtWidgets are imported anywhere in the tree, and the
# PySide6_Addons wheel is the bulk of an unfiltered build. Excluding what is
# never imported is where most of the size goes. QtNetwork stays: Qt reaches for
# it indirectly, and a few megabytes is not worth finding out how.
excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    # Pulled in by nothing here, and each drags a large dependency behind it.
    "tkinter",
    "pytest",
    "numpy",
]

a = Analysis(
    [str(Path(SPECPATH) / "entry.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# The folder build. exclude_binaries=True leaves everything for COLLECT.
folder_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=FOLDER_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
    version=version_info(f"{FOLDER_NAME}.exe"),
)

COLLECT(
    folder_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=FOLDER_NAME,
)

# The portable build: the same analysis, with the binaries inside the executable
# instead of beside it.
EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=PORTABLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
    version=version_info(f"{PORTABLE_NAME}.exe"),
)
