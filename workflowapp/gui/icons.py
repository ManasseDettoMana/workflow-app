"""The toolbar's icons, drawn at runtime in the active theme's ink.

The same reasoning as :mod:`workflowapp.gui.widgets.status_badge`: four icons
shipped as image files would be four more runtime resources, each needing a line
in ``[tool.setuptools.package-data]``, a line in ``datas`` in
``packaging/workflowapp.spec`` and an assertion in ``tests/test_packaging.py``,
or they load from a source checkout and are silently missing from the frozen
build. A ``QPainterPath`` and a colour is less to forget.

A loaded ``QIcon`` also cannot follow the theme. That is not hypothetical here:
it is exactly why ``TicketDialog._theme_calendar`` has to throw away the month
arrows Qt bakes from the style, which stay dark on the dark navigation bar.

``QStyle.StandardPixmap`` was the other candidate. It is free, but its members
are drawn in whichever visual language the platform style speaks, there is no
member meaning "edit" or "theme", and they follow the system palette rather than
this application's.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap

from . import theme

#: The toolbar's icon size. Text sits beside the icon, so it is sized to the
#: label rather than to a button of its own.
ICON_SIZE = 16

#: A sixteenth of a degree, which is the unit QPainter::drawPie takes.
_DEGREE = 16


def _icon(draw: Callable[[QPainter, float], None], size: int) -> QIcon:
    """Run ``draw`` on a transparent square of ``size`` in the theme's ink."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(theme.active_palette().icon_color(), size / 9)
        # Round throughout: at this size a mitred join on the pencil's nib or
        # the bin's taper turns into a stray pixel spur.
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        draw(painter, float(size))
    finally:
        # The pixmap is still being painted until this runs, and an icon built
        # from one that is comes out blank on some repaints.
        painter.end()

    return QIcon(pixmap)


def _plus(painter: QPainter, side: float) -> None:
    inset = side * 0.22
    middle = side / 2
    painter.drawLine(QPointF(inset, middle), QPointF(side - inset, middle))
    painter.drawLine(QPointF(middle, inset), QPointF(middle, side - inset))


def _pencil(painter: QPainter, side: float) -> None:
    # The shaft on its diagonal, nib downwards, over the line it writes on.
    # The point is what separates it from a rubber at this size.
    shaft = QPainterPath(QPointF(side * 0.22, side * 0.80))
    shaft.lineTo(QPointF(side * 0.28, side * 0.62))
    shaft.lineTo(QPointF(side * 0.64, side * 0.26))
    shaft.lineTo(QPointF(side * 0.76, side * 0.38))
    shaft.lineTo(QPointF(side * 0.40, side * 0.74))
    shaft.closeSubpath()
    painter.drawPath(shaft)
    painter.drawLine(QPointF(side * 0.20, side * 0.88), QPointF(side * 0.80, side * 0.88))


def _bin(painter: QPainter, side: float) -> None:
    lid = side * 0.30
    painter.drawLine(QPointF(side * 0.16, lid), QPointF(side * 0.84, lid))

    handle = QPainterPath(QPointF(side * 0.38, lid))
    handle.lineTo(QPointF(side * 0.38, side * 0.16))
    handle.lineTo(QPointF(side * 0.62, side * 0.16))
    handle.lineTo(QPointF(side * 0.62, lid))
    painter.drawPath(handle)

    body = QPainterPath(QPointF(side * 0.26, lid))
    body.lineTo(QPointF(side * 0.34, side * 0.84))
    body.lineTo(QPointF(side * 0.66, side * 0.84))
    body.lineTo(QPointF(side * 0.74, lid))
    painter.drawPath(body)


def _half_disc(painter: QPainter, side: float) -> None:
    # Half light, half dark, which is what a theme toggle looks like everywhere.
    inset = side * 0.16
    circle = QRectF(inset, inset, side - 2 * inset, side - 2 * inset)
    painter.drawEllipse(circle)

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.active_palette().icon_color())
    painter.drawPie(circle, 90 * _DEGREE, 180 * _DEGREE)
    painter.restore()


def new_icon(size: int = ICON_SIZE) -> QIcon:
    return _icon(_plus, size)


def edit_icon(size: int = ICON_SIZE) -> QIcon:
    return _icon(_pencil, size)


def delete_icon(size: int = ICON_SIZE) -> QIcon:
    return _icon(_bin, size)


def theme_icon(size: int = ICON_SIZE) -> QIcon:
    return _icon(_half_disc, size)
