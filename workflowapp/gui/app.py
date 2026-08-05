"""Building the application, and starting it."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.manager import TicketManager

from . import strings, theme
from .main_window import MainWindow


def build_application(argv: list[str] | None = None) -> QApplication:
    """Return the ``QApplication``, reusing one if it already exists.

    pytest-qt builds its own before any test runs, and constructing a second
    aborts the process, so this must never assume it is the first caller.
    """
    existing = QApplication.instance()
    if existing is not None:
        return existing

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(strings.APP_NAME)
    app.setOrganizationName(strings.ORGANISATION)
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
