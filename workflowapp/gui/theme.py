"""Light and dark themes: the stylesheets, the status colours, the preference.

Two things are themed, in two different ways.

The **widgets** are styled by a Qt stylesheet, one ``.qss`` file per theme, loaded
from the installed package.

The **status colours** are not, and cannot be. A ``QStyledItemDelegate`` paints
the coloured tag in the table, and a stylesheet cannot reach inside a delegate's
``paint``. They live here as Python, one palette per theme - which they would
need to anyway, because the amber that reads on white is nearly invisible on dark
grey. A single fixed palette is unreadable in one theme or the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from importlib import resources

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from workflowapp.core.models import Status

from . import strings

_SETTINGS_KEY = "theme"


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"

    def other(self) -> Theme:
        return Theme.DARK if self is Theme.LIGHT else Theme.LIGHT


@dataclass(frozen=True)
class Palette:
    """The colours a delegate paints with, for one theme."""

    statuses: dict[Status, str]
    overdue: str
    muted: str
    selected_text: str

    def status_color(self, status: Status) -> QColor:
        return QColor(self.statuses[status])

    def overdue_color(self) -> QColor:
        return QColor(self.overdue)

    def muted_color(self) -> QColor:
        return QColor(self.muted)

    def selected_text_color(self) -> QColor:
        return QColor(self.selected_text)


PALETTES: dict[Theme, Palette] = {
    Theme.LIGHT: Palette(
        statuses={
            Status.OPEN: "#2563eb",
            # Darkened from the obvious amber: #f59e0b on white is around 2:1
            # contrast and unreadable as text.
            Status.IN_PROGRESS: "#b45309",
            Status.DONE: "#15803d",
            Status.URGENT: "#b91c1c",
        },
        overdue="#b91c1c",
        muted="#6b7280",
        selected_text="#ffffff",
    ),
    Theme.DARK: Palette(
        statuses={
            Status.OPEN: "#60a5fa",
            Status.IN_PROGRESS: "#fbbf24",
            Status.DONE: "#4ade80",
            Status.URGENT: "#f87171",
        },
        overdue="#f87171",
        muted="#9aa3b2",
        selected_text="#ffffff",
    ),
}

# The theme currently applied. Module state because the delegates that need it
# are constructed deep inside the view and repainted on every scroll; threading a
# reference down to each one buys nothing when there is exactly one application
# and exactly one active theme.
_active: Theme = Theme.LIGHT


def active() -> Theme:
    return _active


def active_palette() -> Palette:
    return PALETTES[_active]


def stylesheet(theme: Theme) -> str:
    """Read a theme's ``.qss`` from the package.

    ``importlib.resources`` rather than a path relative to ``__file__`` so that
    it keeps working from a zipped or frozen installation.
    """
    return (
        resources.files("workflowapp.gui")
        .joinpath(f"themes/{theme.value}.qss")
        .read_text(encoding="utf-8")
    )


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Style the application and record which theme is now active."""
    global _active
    _active = theme
    app.setStyleSheet(stylesheet(theme))


def settings() -> QSettings:
    """The application's settings.

    On Windows this is the registry, under
    ``HKCU\\Software\\ManasseDettoMana\\Workflow App`` - not a file in the data
    directory, so ``WORKFLOWAPP_DATA_DIR`` does not isolate it. Tests that touch
    the theme must point ``QSettings`` at a temporary ini file instead.
    """
    return QSettings(strings.ORGANISATION, strings.APP_NAME)


def load_preference() -> Theme:
    """The saved theme, defaulting to light if there is nothing usable saved."""
    stored = settings().value(_SETTINGS_KEY, Theme.LIGHT.value)
    try:
        return Theme(stored)
    except ValueError:
        # A settings value written by hand, or by a version that knew a theme
        # this one does not. Not worth an error dialog at startup.
        return Theme.LIGHT


def save_preference(theme: Theme) -> None:
    settings().setValue(_SETTINGS_KEY, theme.value)
