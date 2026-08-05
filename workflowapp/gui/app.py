"""Building the application, and starting it."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.manager import TicketManager

from . import assets, strings, theme
from .main_window import MainWindow

#: What Windows groups taskbar buttons by. Set explicitly because the default is
#: derived from the running executable, which is ``pythonw.exe`` from a source
#: checkout - so without this the taskbar shows Python's icon next to a window
#: wearing ours, and pins the wrong thing.
APP_USER_MODEL_ID = "ManasseDettoMana.WorkflowApp"


def _claim_taskbar_identity() -> None:
    """Tell Windows this process is its own application, not Python.

    A no-op anywhere else, and deliberately quiet if it fails: an icon grouped
    under the wrong name is a blemish, not a reason to refuse to start.
    """
    if sys.platform != "win32":
        return

    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass


def build_application(argv: list[str] | None = None) -> QApplication:
    """Return the ``QApplication``, reusing one if it already exists.

    pytest-qt builds its own before any test runs, and constructing a second
    aborts the process, so this must never assume it is the first caller.
    """
    existing = QApplication.instance()
    if existing is not None:
        return existing

    _claim_taskbar_identity()

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(strings.APP_NAME)
    app.setOrganizationName(strings.ORGANISATION)
    # Inherited by every window, so no widget has to remember to set it.
    app.setWindowIcon(assets.app_icon())
    return app


def main(argv: list[str] | None = None) -> int:
    app = build_application(argv)
    # Applied before any window exists, so nothing is ever shown unstyled.
    theme.apply_theme(app, theme.load_preference())

    try:
        manager = TicketManager()
    except WorkflowAppError as exc:
        # There is no window to parent this to yet, and no useful application to
        # show without the tickets, so this reports and stops.
        QMessageBox.critical(None, strings.ERROR_STARTUP_TITLE, str(exc))
        return 1

    window = MainWindow(manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
