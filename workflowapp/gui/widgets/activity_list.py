"""The todo list inside a ticket: checkable items, plus add and remove.

This widget edits a **detached copy** of the ticket's activities. Nothing it does
reaches the manager or the file until the dialog is accepted, which is what makes
"Annulla" able to actually cancel. The dialog reads the result back with
:meth:`ActivityList.activities`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from workflowapp.core.models import Activity

from .. import strings

_ACTIVITY_ROLE = Qt.ItemDataRole.UserRole + 1


class ActivityList(QWidget):
    """A checkable list of activities with + and - buttons."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._list = QListWidget(self)
        self._list.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self._list)

        controls = QHBoxLayout()
        controls.setSpacing(6)

        self._add_button = QPushButton(strings.ACTIVITY_ADD, self)
        self._add_button.setObjectName("activityButton")
        self._add_button.setToolTip(strings.ACTIVITY_ADD_TIP)
        self._add_button.clicked.connect(self.add_activity)
        controls.addWidget(self._add_button)

        self._remove_button = QPushButton(strings.ACTIVITY_REMOVE, self)
        self._remove_button.setObjectName("activityButton")
        self._remove_button.setToolTip(strings.ACTIVITY_REMOVE_TIP)
        self._remove_button.clicked.connect(self.remove_selected)
        controls.addWidget(self._remove_button)

        controls.addStretch(1)

        self._count_label = QLabel("", self)
        self._count_label.setObjectName("metaLabel")
        controls.addWidget(self._count_label)

        layout.addLayout(controls)

        self._update_buttons()
        self._update_count()

    # --------------------------------------------------------------- state

    def set_activities(self, activities: list[Activity]) -> None:
        """Load a copy of the given activities.

        Copied rather than referenced: editing them in place would change the
        ticket even if the user then cancels the dialog.
        """
        self._list.blockSignals(True)
        self._list.clear()
        for activity in activities:
            self._append(Activity(activity.id, activity.description, activity.completed))
        self._list.blockSignals(False)
        self._update_buttons()
        self._update_count()

    def activities(self) -> list[Activity]:
        """The current list, with the text and tick state read back off the items."""
        result = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            activity: Activity = item.data(_ACTIVITY_ROLE)
            result.append(
                Activity(
                    id=activity.id,
                    description=item.text().strip(),
                    completed=item.checkState() is Qt.CheckState.Checked,
                )
            )
        # An activity whose text was cleared is a row the user emptied rather
        # than removed. Keeping it would save a nameless entry.
        return [a for a in result if a.description]

    # -------------------------------------------------------------- editing

    def add_activity(self) -> None:
        activity = Activity.create(strings.ACTIVITY_NEW_TEXT)
        item = self._append(activity)
        self._list.setCurrentItem(item)
        # Straight into edit mode: an item called "Nuova attività" is a
        # placeholder, not something anybody wanted to add.
        self._list.editItem(item)
        self._update_buttons()
        self._update_count()
        self.changed.emit()

    def remove_selected(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self._update_buttons()
        self._update_count()
        self.changed.emit()

    # -------------------------------------------------------------- private

    def _append(self, activity: Activity) -> QListWidgetItem:
        item = QListWidgetItem(activity.description, self._list)
        item.setFlags(
            item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable
        )
        item.setCheckState(
            Qt.CheckState.Checked if activity.completed else Qt.CheckState.Unchecked
        )
        item.setData(_ACTIVITY_ROLE, activity)
        return item

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        del item
        self._update_count()
        self.changed.emit()

    def _update_buttons(self) -> None:
        self._remove_button.setEnabled(bool(self._list.selectedItems()))

    def _update_count(self) -> None:
        total = self._list.count()
        if total == 0:
            self._count_label.setText("")
            return
        done = sum(
            1
            for row in range(total)
            if self._list.item(row).checkState() is Qt.CheckState.Checked
        )
        self._count_label.setText(strings.ACTIVITY_COUNT.format(completate=done, totali=total))
