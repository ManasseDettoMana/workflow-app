"""The coloured status tag: a filled circle beside the Italian label.

Painted at runtime rather than shipped as image files. Four statuses times two
themes is eight icons to draw, keep in sync and remember to include in the build;
a ``QPainter`` and a colour is less to go wrong with, and it recolours itself the
moment the theme changes.

The same drawing serves the combo box in the dialog (through :func:`status_icon`)
and the table cells (through :class:`StatusDelegate`), so the two cannot drift
apart.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from workflowapp.core.models import Status

from .. import strings, theme

#: The model supplies the Status itself under this role. The delegate needs the
#: value, not the label, and re-deriving one from the other would mean parsing
#: Italian text back into an enum.
STATUS_ROLE = Qt.ItemDataRole.UserRole + 1

DOT_DIAMETER = 10
DOT_TEXT_GAP = 8
CELL_PADDING = 8


def status_icon(status: Status, size: int = 14) -> QIcon:
    """A filled circle in the status's colour for the current theme."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        _paint_dot(
            painter,
            QRect(0, 0, size, size),
            theme.active_palette().status_color(status),
        )
    finally:
        # Without this the QPixmap is still being painted when it is returned,
        # and Qt warns on every repaint.
        painter.end()

    return QIcon(pixmap)


def _paint_dot(painter: QPainter, rect: QRect, color: QColor, ring: QColor | None = None) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    diameter = min(DOT_DIAMETER, rect.width(), rect.height())
    circle = QRect(0, 0, diameter, diameter)
    circle.moveCenter(rect.center())

    painter.setBrush(color)
    if ring is not None:
        # On a selected row the dot can land on a background close to its own
        # colour - a blue "Aperto" dot on the blue selection disappears. A thin
        # contrasting ring keeps it legible without changing what it means.
        painter.setPen(QPen(ring, 1))
    else:
        painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(circle)
    painter.restore()


class StatusDelegate(QStyledItemDelegate):
    """Draws the status column as a coloured dot followed by its Italian label."""

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        status = index.data(STATUS_ROLE)
        if not isinstance(status, Status):
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # The row background, hover and selection are the style's job. Blanking
        # the text first stops it drawing the label where the dot belongs.
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        palette = theme.active_palette()

        rect = opt.rect.adjusted(CELL_PADDING, 0, -CELL_PADDING, 0)
        dot_rect = QRect(rect.left(), rect.top(), DOT_DIAMETER, rect.height())
        _paint_dot(
            painter,
            dot_rect,
            palette.status_color(status),
            ring=palette.selected_text_color() if selected else None,
        )

        text_rect = rect.adjusted(DOT_DIAMETER + DOT_TEXT_GAP, 0, 0, 0)
        painter.save()
        if selected:
            painter.setPen(palette.selected_text_color())
        else:
            painter.setPen(opt.palette.text().color())
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            strings.status_label(status),
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        size = super().sizeHint(option, index)
        status = index.data(STATUS_ROLE)
        if isinstance(status, Status):
            metrics = option.fontMetrics
            width = metrics.horizontalAdvance(strings.status_label(status))
            size.setWidth(width + DOT_DIAMETER + DOT_TEXT_GAP + CELL_PADDING * 2)
        return size
