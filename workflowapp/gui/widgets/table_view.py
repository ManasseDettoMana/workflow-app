"""A table view that hovers a whole row, and the delegate that lets it.

``QAbstractItemView`` tracks one hovered ``QModelIndex`` and gives
``State_MouseOver`` to that index alone. ``QTreeView`` extends it to the row;
``QTableView`` does not. With ``SelectRows`` in force, a single tinted cell under
the pointer reads as a rendering fault rather than as feedback, so the hovered
row is tracked here and the delegates ask for it.

This lives in its own module rather than in ``ticket_table``: ``ticket_table``
imports ``STATUS_ROLE`` from ``status_badge``, and ``status_badge`` imports the
delegate below, so putting it there would close the loop.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableView, QWidget

#: What ``hovered_row`` reports when the pointer is not over a row.
NO_ROW = -1


class TicketTableView(QTableView):
    """A table whose hover covers the row, not just the cell under the pointer."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # Without this the view only hears about the mouse while a button is
        # down, and the hover would only appear mid-drag.
        self.setMouseTracking(True)
        self._hovered_row = NO_ROW

    def hovered_row(self) -> int:
        return self._hovered_row

    def mouseMoveEvent(self, event) -> None:
        self._set_hovered_row(self.indexAt(event.position().toPoint()).row())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered_row(NO_ROW)
        super().leaveEvent(event)

    def _set_hovered_row(self, row: int) -> None:
        if row == self._hovered_row:
            return
        self._hovered_row = row
        # The whole viewport rather than the two rows that changed. At a few tens
        # of rows the repaint is not worth measuring, and it is a great deal less
        # code than working out two row rectangles.
        self.viewport().update()


class RowHoverDelegate(QStyledItemDelegate):
    """Extends the hover from the cell under the pointer to its whole row.

    Subclass this instead of ``QStyledItemDelegate`` for any column of a
    :class:`TicketTableView`, or that column will be the one cell that does not
    light up with the rest of the row.
    """

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        view = self.parent()
        if not isinstance(view, TicketTableView):
            return
        # |= and &= ~, not state.setFlag(): the mutating form is the one that
        # reliably writes back through PySide6.
        if index.row() == view.hovered_row():
            option.state |= QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver
