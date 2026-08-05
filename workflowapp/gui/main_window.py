"""The main window: the toolbar, the filter row and the ticket table.

Every action goes through the ``TicketManager``, which saves as it goes. The
window holds no ticket state of its own: it asks the manager for the list, hands
it to the table model, and asks again after anything changes.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from workflowapp.core.errors import WorkflowAppError
from workflowapp.core.manager import TicketManager
from workflowapp.core.models import Status, Ticket

from . import strings, theme
from .ticket_dialog import TicketDialog
from .widgets.status_badge import StatusDelegate, status_icon
from .widgets.ticket_table import (
    TICKET_ID_ROLE,
    Column,
    TicketSortProxy,
    TicketTableModel,
)

WINDOW_GEOMETRY_KEY = "window/geometry"
WINDOW_STATE_KEY = "window/state"


class MainWindow(QMainWindow):
    def __init__(self, manager: TicketManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._manager = manager

        self.setWindowTitle(strings.WINDOW_TITLE)
        self.resize(940, 600)

        self._model = TicketTableModel(self)
        self._proxy = TicketSortProxy(self)
        self._proxy.setSourceModel(self._model)

        self._build_toolbar()
        self._build_body()
        self.setStatusBar(QStatusBar(self))

        self._restore_geometry()
        self.refresh()

    # ------------------------------------------------------------ building

    def _build_toolbar(self) -> None:
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        self.action_new = QAction(strings.ACTION_NEW, self)
        self.action_new.setToolTip(strings.ACTION_NEW_TIP)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.create_ticket)
        toolbar.addAction(self.action_new)

        self.action_edit = QAction(strings.ACTION_EDIT, self)
        self.action_edit.setToolTip(strings.ACTION_EDIT_TIP)
        self.action_edit.triggered.connect(self.edit_selected)
        toolbar.addAction(self.action_edit)

        self.action_delete = QAction(strings.ACTION_DELETE, self)
        self.action_delete.setToolTip(strings.ACTION_DELETE_TIP)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_delete.triggered.connect(self.delete_selected)
        toolbar.addAction(self.action_delete)

        toolbar.addSeparator()

        self.action_theme = QAction(strings.ACTION_THEME, self)
        self.action_theme.setToolTip(strings.ACTION_THEME_TIP)
        self.action_theme.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.action_theme)

    def _build_body(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addLayout(self._build_filter_row())

        self._table = QTableView(central)
        self._table.setModel(self._proxy)
        self._table.setItemDelegateForColumn(int(Column.STATUS), StatusDelegate(self._table))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(34)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.selectionModel().selectionChanged.connect(self._update_actions)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(int(Column.TITLE), QHeaderView.ResizeMode.Stretch)
        for column in (Column.STATUS, Column.DUE_DATE, Column.ACTIVITIES, Column.UPDATED):
            header.setSectionResizeMode(int(column), QHeaderView.ResizeMode.ResizeToContents)
        header.setHighlightSections(False)

        # Most recently updated first, which is what "what was I doing?" means.
        self._table.sortByColumn(int(Column.UPDATED), Qt.SortOrder.DescendingOrder)

        layout.addWidget(self._table)

        self._empty_label = QLabel(strings.EMPTY_LIST, central)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)

        self.setCentralWidget(central)

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel(strings.FILTER_LABEL, self)
        label.setObjectName("sectionLabel")
        row.addWidget(label)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText(strings.FILTER_PLACEHOLDER)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter_changed)
        row.addWidget(self._search, 1)

        self._status_filter = QComboBox(self)
        self._status_filter.addItem(strings.FILTER_ALL_STATUSES, None)
        for status in Status:
            self._status_filter.addItem(
                status_icon(status), strings.status_label(status), status
            )
        self._status_filter.currentIndexChanged.connect(self._on_filter_changed)
        row.addWidget(self._status_filter)

        return row

    # ------------------------------------------------------------- reading

    def refresh(self) -> None:
        """Pull the current list from the manager and redraw.

        The table never holds ticket state of its own (invariant 6), so every
        change goes: manager mutates, then this.
        """
        selected = self.selected_ticket_id()
        self._model.set_tickets(self._manager.tickets())
        if selected is not None:
            self.select_ticket(selected)
        self._update_status_bar()
        self._update_actions()

    def selected_ticket_id(self) -> str | None:
        """The id of the selected ticket, or None.

        Reads the id from the model rather than using the row number. With a sort
        proxy in the way, a view row and a manager list index are different
        numbers, and confusing them deletes the wrong ticket.
        """
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].data(TICKET_ID_ROLE)

    def selected_ticket(self) -> Ticket | None:
        ticket_id = self.selected_ticket_id()
        if ticket_id is None:
            return None
        try:
            return self._manager.get(ticket_id)
        except WorkflowAppError:
            return None

    def select_ticket(self, ticket_id: str) -> None:
        for row in range(self._proxy.rowCount()):
            index = self._proxy.index(row, int(Column.TITLE))
            if index.data(TICKET_ID_ROLE) == ticket_id:
                self._table.selectRow(row)
                self._table.scrollTo(index)
                return

    # ------------------------------------------------------------- actions

    def create_ticket(self) -> None:
        dialog = TicketDialog(None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        draft = dialog.draft()
        with self._reporting_errors():
            ticket = self._manager.add_ticket(
                title=draft.title,
                description=draft.description,
                status=draft.status,
                due_date=draft.due_date,
                activities=draft.activities,
            )
            self.refresh()
            self.select_ticket(ticket.id)

    def edit_selected(self) -> None:
        ticket = self.selected_ticket()
        if ticket is None:
            return

        dialog = TicketDialog(ticket, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        draft = dialog.draft()
        with self._reporting_errors():
            # One update rather than a call per field: update_ticket touches the
            # timestamp and saves once, so a five-field edit is one write.
            self._manager.update_ticket(
                ticket.id,
                title=draft.title,
                description=draft.description,
                status=draft.status,
                due_date=draft.due_date,
                activities=draft.activities,
            )
            self.refresh()

    def delete_selected(self) -> None:
        ticket = self.selected_ticket()
        if ticket is None:
            return

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle(strings.CONFIRM_DELETE_TITLE)
        confirm.setText(strings.CONFIRM_DELETE_TEXT.format(titolo=ticket.title))
        confirm.setInformativeText(strings.CONFIRM_DELETE_HINT)
        delete_button = confirm.addButton(
            strings.BUTTON_YES_DELETE, QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = confirm.addButton(strings.BUTTON_NO, QMessageBox.ButtonRole.RejectRole)
        # The safe answer is the one that happens if the dialog is dismissed.
        confirm.setDefaultButton(cancel_button)
        confirm.exec()

        if confirm.clickedButton() is not delete_button:
            return

        with self._reporting_errors():
            self._manager.delete_ticket(ticket.id)
            self.refresh()

    def toggle_theme(self) -> None:
        new_theme = theme.active().other()
        theme.apply_theme(QApplication.instance(), new_theme)
        theme.save_preference(new_theme)
        self._retint()

    def _retint(self) -> None:
        """Repaint everything whose colour came from the theme's Python palette.

        The stylesheet reapplies itself; the status dots and the overdue dates do
        not, because a delegate and a ForegroundRole are not stylesheet-driven.
        """
        for index in range(self._status_filter.count()):
            status = self._status_filter.itemData(index)
            if status is not None:
                self._status_filter.setItemIcon(index, status_icon(status))
        self._model.set_tickets(self._manager.tickets())
        self._table.viewport().update()

    # ------------------------------------------------------------- private

    def _on_double_click(self, index: QModelIndex) -> None:
        del index
        self.edit_selected()

    def _on_filter_changed(self) -> None:
        self._proxy.set_text_filter(self._search.text())
        self._proxy.set_status_filter(self._status_filter.currentData())
        self._update_status_bar()
        self._update_actions()

    def _update_actions(self) -> None:
        has_selection = self.selected_ticket_id() is not None
        self.action_edit.setEnabled(has_selection)
        self.action_delete.setEnabled(has_selection)

    def _update_status_bar(self) -> None:
        total = len(self._manager.tickets())
        visible = self._proxy.rowCount()
        message = strings.STATUS_BAR_COUNT.format(visibili=visible, totali=total)

        overdue = sum(1 for t in self._manager.tickets() if t.is_overdue)
        if overdue:
            message = f"{message} - {strings.STATUS_BAR_OVERDUE.format(scaduti=overdue)}"
        self.statusBar().showMessage(message)

        empty = visible == 0
        self._empty_label.setVisible(empty)
        self._empty_label.setText(strings.EMPTY_LIST if total == 0 else strings.EMPTY_FILTER)
        self._table.setVisible(not empty)

    def _reporting_errors(self):
        return _ErrorReporter(self)

    # ---------------------------------------------------------- persistence

    def _restore_geometry(self) -> None:
        settings = theme.settings()
        geometry = settings.value(WINDOW_GEOMETRY_KEY)
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value(WINDOW_STATE_KEY)
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:
        settings = theme.settings()
        settings.setValue(WINDOW_GEOMETRY_KEY, self.saveGeometry())
        settings.setValue(WINDOW_STATE_KEY, self.saveState())
        super().closeEvent(event)


class _ErrorReporter:
    """Turns a ``WorkflowAppError`` into a message box instead of a crash.

    PySide6 ends the process on an unhandled exception inside a slot, so every
    slot that can reach the store goes through this.
    """

    def __init__(self, window: QMainWindow):
        self._window = window

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is not None and issubclass(exc_type, WorkflowAppError):
            QMessageBox.critical(self._window, strings.ERROR_TITLE, str(exc))
            return True
        return False
