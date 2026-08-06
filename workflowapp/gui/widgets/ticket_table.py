"""The ticket table: a model over the manager's list, and the sort/filter proxy.

A model rather than a ``QTableWidget``. It gives sorting and filtering for free
through a proxy, and it keeps invariant 6 honest: the table holds no ticket state
of its own, it reads the snapshot the manager handed it.
"""

from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
)

from workflowapp.core.models import Status, Ticket

from .. import strings, theme
from .status_badge import STATUS_ROLE

#: The value a column should be *ordered* by, which is rarely the text shown.
#: "In Lavorazione" sorts under I alphabetically; by priority it sorts second.
SORT_ROLE = Qt.ItemDataRole.UserRole + 2

#: The ticket's id. Anything acting on a selected row reads this rather than
#: treating the row number as an index into the manager's list - with a sort
#: proxy in between, those are different numbers, and the bug that causes looks
#: like data corruption rather than an off-by-one.
TICKET_ID_ROLE = Qt.ItemDataRole.UserRole + 3


#: Qt passes an invalid index to mean "the root". Built once, because a default
#: argument is evaluated at import time and constructing a QObject there is what
#: ruff's B008 is warning about.
_NO_PARENT = QModelIndex()


class Column(IntEnum):
    TITLE = 0
    STATUS = 1
    DUE_DATE = 2
    ACTIVITIES = 3
    UPDATED = 4


HEADERS = {
    Column.TITLE: strings.COLUMN_TITLE,
    Column.STATUS: strings.COLUMN_STATUS,
    Column.DUE_DATE: strings.COLUMN_DUE_DATE,
    Column.ACTIVITIES: strings.COLUMN_ACTIVITIES,
    Column.UPDATED: strings.COLUMN_UPDATED,
}


class TicketTableModel(QAbstractTableModel):
    """A read-only view of a list of tickets.

    Editing goes through the dialog and the manager, never through the table, so
    ``setData`` is deliberately not implemented.
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._tickets: list[Ticket] = []

    def set_tickets(self, tickets: list[Ticket]) -> None:
        self.beginResetModel()
        self._tickets = list(tickets)
        self.endResetModel()

    def ticket_at(self, row: int) -> Ticket | None:
        if 0 <= row < len(self._tickets):
            return self._tickets[row]
        return None

    # ------------------------------------------------------- Qt model API

    def rowCount(self, parent: QModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(self._tickets)

    def columnCount(self, parent: QModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(Column)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation is Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS.get(Column(section))
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        ticket = self._tickets[index.row()]
        column = Column(index.column())

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(ticket, column)
        if role == SORT_ROLE:
            return self._sort_value(ticket, column)
        if role == STATUS_ROLE:
            return ticket.status
        if role == TICKET_ID_ROLE:
            return ticket.id
        if role == Qt.ItemDataRole.ForegroundRole and column is Column.DUE_DATE:
            if ticket.is_overdue:
                return theme.active_palette().overdue_color()
            if ticket.due_date is None:
                return theme.active_palette().muted_color()
            return None
        if role == Qt.ItemDataRole.ForegroundRole and column is Column.UPDATED:
            return theme.active_palette().muted_color()
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(ticket, column)
        if role == Qt.ItemDataRole.TextAlignmentRole and column is Column.ACTIVITIES:
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    # ---------------------------------------------------------- rendering

    @staticmethod
    def _display(ticket: Ticket, column: Column) -> str:
        if column is Column.TITLE:
            return ticket.title
        if column is Column.STATUS:
            # The delegate paints this column. The text is still supplied so the
            # column is legible if the delegate is ever not installed, and so
            # that keyboard type-ahead finds a row by its status.
            return strings.status_label(ticket.status)
        if column is Column.DUE_DATE:
            if ticket.due_date is None:
                return strings.NO_DUE_DATE
            return ticket.due_date.strftime(strings.DATE_FORMAT_PY)
        if column is Column.ACTIVITIES:
            if not ticket.activities:
                return ""
            return f"{ticket.completed_count}/{len(ticket.activities)}"
        return ticket.updated_at.strftime(strings.DATETIME_FORMAT_PY)

    @staticmethod
    def _sort_value(ticket: Ticket, column: Column):
        if column is Column.TITLE:
            return ticket.title.casefold()
        if column is Column.STATUS:
            return ticket.status.priority
        if column is Column.DUE_DATE:
            # None, handled specially by the proxy so that undated tickets stay
            # at the bottom whichever way the column points.
            return ticket.due_date.toordinal() if ticket.due_date else None
        if column is Column.ACTIVITIES:
            return len(ticket.activities)
        return ticket.updated_at.timestamp()

    @staticmethod
    def _tooltip(ticket: Ticket, column: Column) -> str | None:
        if column is Column.DUE_DATE and ticket.is_overdue:
            return strings.TOOLTIP_OVERDUE
        if column is Column.ACTIVITIES and ticket.activities:
            return strings.ACTIVITY_COUNT.format(
                completate=ticket.completed_count, totali=len(ticket.activities)
            )
        if column is Column.TITLE and ticket.description:
            return ticket.description
        return None


class TicketSortProxy(QSortFilterProxyModel):
    """Sorts by ``SORT_ROLE`` and filters by status and free text."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._status: Status | None = None
        self._text: str = ""
        self._overdue_only: bool = False

    def set_status_filter(self, status: Status | None) -> None:
        self._status = status
        # invalidate(), not invalidateFilter() or invalidateRowsFilter(): PySide6
        # 6.11 marks every invalidate*Filter variant deprecated, and this is the
        # only one that is not.
        self.invalidate()

    def set_text_filter(self, text: str) -> None:
        self._text = text.strip().casefold()
        # invalidate(), not invalidateFilter() or invalidateRowsFilter(): PySide6
        # 6.11 marks every invalidate*Filter variant deprecated, and this is the
        # only one that is not.
        self.invalidate()

    def set_overdue_filter(self, overdue_only: bool) -> None:
        self._overdue_only = overdue_only
        self.invalidate()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        model = self.sourceModel()
        ticket = model.ticket_at(row) if isinstance(model, TicketTableModel) else None
        if ticket is None:
            return False
        if self._overdue_only and not ticket.is_overdue:
            return False
        if self._status is not None and ticket.status is not self._status:
            return False
        if self._text:
            haystack = f"{ticket.title}\n{ticket.description}".casefold()
            if self._text not in haystack:
                return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_value = left.data(SORT_ROLE)
        right_value = right.data(SORT_ROLE)

        # A ticket with no deadline belongs at the bottom in both directions.
        # Qt produces the descending order by reversing what lessThan gives it,
        # so "last" descending means saying it sorts *first* here.
        if left_value is None or right_value is None:
            if left_value is None and right_value is None:
                return False
            ascending = self.sortOrder() is Qt.SortOrder.AscendingOrder
            return (not ascending) if left_value is None else ascending

        return left_value < right_value
