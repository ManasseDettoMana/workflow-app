"""The application icon, read from the package.

One asset and one function, kept out of ``app.py`` for the same reason the
stylesheets are kept out of it: loading a resource and starting an application
are different jobs, and ``theme.py`` already set the pattern.

``importlib.resources`` rather than a path relative to ``__file__``, exactly as
in :func:`workflowapp.gui.theme.stylesheet`, so that this keeps working from a
frozen build where there is no ``workflowapp/gui/assets`` directory on disk to
point at.

The ``.ico`` holds six frames and all six are handed to the ``QIcon``, rather
than one that Qt then rescales. Qt's ICO reader returns the 16px frame first, so
taking whatever it hands back would put a 16px image in the Alt-Tab switcher,
blown up and soft.
"""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtGui import QIcon, QImageReader, QPixmap

ICON_RESOURCE = "assets/app.ico"


def icon_bytes() -> bytes:
    """The raw ``.ico``, as shipped in the package."""
    return resources.files("workflowapp.gui").joinpath(ICON_RESOURCE).read_bytes()


def app_icon() -> QIcon:
    """The application icon, with every resolution the file carries."""
    payload = QByteArray(icon_bytes())
    buffer = QBuffer(payload)
    buffer.open(QBuffer.OpenModeFlag.ReadOnly)

    icon = QIcon()
    try:
        reader = QImageReader(buffer, b"ico")
        for index in range(reader.imageCount()):
            reader.jumpToImage(index)
            image = reader.read()
            # A frame Qt cannot decode is skipped rather than fatal: a missing
            # size costs a slightly soft icon, and no icon at all is worse.
            if not image.isNull():
                icon.addPixmap(QPixmap.fromImage(image))
    finally:
        buffer.close()

    return icon
