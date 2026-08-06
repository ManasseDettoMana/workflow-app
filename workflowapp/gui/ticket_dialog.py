"""The ticket dialog: one class, two modes.

"New ticket" and "ticket detail" are the same form. The only differences are the
window title and whether the fields start empty, so they are one class with a
mode rather than two that would slowly drift apart.

The dialog edits nothing in place. It reads values out of a ticket, lets the user
change them, and hands back a :class:`TicketDraft` on accept. The caller applies
that through the manager. That is what makes "Annulla" genuinely cancel, and it
keeps invariant 6 - the interface holds no ticket state - true of the dialog as
well as of the table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtGui import QFont, QIcon, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from workflowapp.core.models import Activity, Status, Ticket

from . import strings, theme
from .widgets.activity_list import ActivityList
from .widgets.status_badge import status_icon


@dataclass
class TicketDraft:
    """What the dialog collected. Not a Ticket - it has no id and no timestamps."""

    title: str
    description: str
    status: Status
    due_date: date | None
    activities: list[Activity] = field(default_factory=list)


class TicketDialog(QDialog):
    def __init__(self, ticket: Ticket | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._ticket = ticket
        self._dirty = False

        self.setWindowTitle(
            strings.DIALOG_EDIT_TITLE if ticket else strings.DIALOG_NEW_TITLE
        )
        self.setMinimumWidth(520)

        self._build()
        self._populate()
        # Set after populating: filling the fields fires the same signals a user
        # typing does, and the dialog would open already believing it was edited.
        self._dirty = False

    # ------------------------------------------------------------ building

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.title_edit = QLineEdit(self)
        self.title_edit.setMaxLength(200)
        self.title_edit.textChanged.connect(self._mark_dirty)
        form.addRow(strings.FIELD_TITLE, self.title_edit)

        self.description_edit = QPlainTextEdit(self)
        self.description_edit.setMinimumHeight(90)
        self.description_edit.textChanged.connect(self._mark_dirty)
        form.addRow(strings.FIELD_DESCRIPTION, self.description_edit)

        self.status_combo = QComboBox(self)
        for status in Status:
            self.status_combo.addItem(status_icon(status), strings.status_label(status), status)
        self.status_combo.currentIndexChanged.connect(self._mark_dirty)
        form.addRow(strings.FIELD_STATUS, self.status_combo)

        form.addRow(strings.FIELD_DUE_DATE, self._build_due_date_row())

        activities_label = QLabel(strings.FIELD_ACTIVITIES, self)
        activities_label.setObjectName("sectionLabel")
        self.activity_list = ActivityList(self)
        self.activity_list.changed.connect(self._mark_dirty)
        form.addRow(activities_label, self.activity_list)

        layout.addLayout(form)

        self._meta_label = QLabel("", self)
        self._meta_label.setObjectName("metaLabel")
        layout.addWidget(self._meta_label)

        self._buttons = QDialogButtonBox(self)
        self._save_button = self._buttons.addButton(
            strings.BUTTON_SAVE, QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._save_button.setDefault(True)
        self._buttons.addButton(strings.BUTTON_CANCEL, QDialogButtonBox.ButtonRole.RejectRole)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _build_due_date_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.due_date_edit = QDateEdit(row)
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat(strings.DATE_FORMAT)
        self.due_date_edit.setDate(QDate.currentDate())
        self.due_date_edit.dateChanged.connect(self._mark_dirty)
        self._theme_calendar()
        layout.addWidget(self.due_date_edit)

        # A ticket with no deadline is ordinary, and a QDateEdit has no way to
        # be empty. The checkbox is what makes "none" expressible at all.
        self.no_due_date = QCheckBox(strings.FIELD_NO_DUE_DATE, row)
        self.no_due_date.toggled.connect(self._on_no_due_date_toggled)
        layout.addWidget(self.no_due_date)
        layout.addStretch(1)

        return row

    def _theme_calendar(self) -> None:
        """Set the parts of the calendar popup a stylesheet cannot reach.

        Everything else about the popup is in the themes' Calendar section. These
        four are not reachable from there:

        Qt gives Saturday and Sunday a hard-coded red foreground as a
        ``QTextCharFormat``, and QSS has no way into one. That red belongs to
        neither palette, and in the dark theme it is close enough to the overdue
        colour that a weekend reads as a deadline.

        The month names come from the system locale, which is Italian on this
        machine and would not be on another. Invariant 9 says the interface is
        Italian, not "Italian if Windows happens to be".

        The prev and next buttons carry a ``QIcon`` baked from the style at
        construction, and a stylesheet cannot recolour a ``QIcon`` - it stays
        dark on the dark theme's navigation bar. Cleared, the button falls back
        to drawing an arrow primitive, which the stylesheet does reach.

        The dialog is modal and built fresh each time, so this reads whichever
        palette is active now and never needs to be redone on a theme change.
        """
        calendar = self.due_date_edit.calendarWidget()
        calendar.setLocale(QLocale(QLocale.Language.Italian))
        # Nobody schedules a personal ticket by ISO week number, and the column
        # is a second QHeaderView for the stylesheet to have an opinion about.
        calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )

        muted = theme.active_palette().muted_color()

        # The weekday row's default format is NoBrush on both sides, so it
        # already follows the view palette the stylesheet sets. Only the weight
        # is added: Qt paints that row on a slightly shaded band, and spending
        # the muted colour on it as well drops the day names to 3.9:1 there.
        header = QTextCharFormat()
        header.setFontWeight(QFont.Weight.DemiBold)
        calendar.setHeaderTextFormat(header)

        weekend = QTextCharFormat()
        weekend.setForeground(muted)
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            calendar.setWeekdayTextFormat(day, weekend)

        for name, arrow in (
            ("qt_calendar_prevmonth", Qt.ArrowType.LeftArrow),
            ("qt_calendar_nextmonth", Qt.ArrowType.RightArrow),
        ):
            # Qt-internal names. A future Qt that renamed them must cost a
            # missing arrow, not an AttributeError inside a dialog constructor.
            button = calendar.findChild(QToolButton, name)
            if button is not None:
                button.setIcon(QIcon())
                button.setArrowType(arrow)

    # ---------------------------------------------------------- populating

    def _populate(self) -> None:
        if self._ticket is None:
            self.no_due_date.setChecked(True)
            self._meta_label.setVisible(False)
            return

        ticket = self._ticket
        self.title_edit.setText(ticket.title)
        self.description_edit.setPlainText(ticket.description)
        self.status_combo.setCurrentIndex(self.status_combo.findData(ticket.status))
        self.activity_list.set_activities(ticket.activities)

        if ticket.due_date is None:
            self.no_due_date.setChecked(True)
        else:
            self.no_due_date.setChecked(False)
            self.due_date_edit.setDate(QDate(ticket.due_date))

        self._meta_label.setText(
            "{} - {}".format(
                strings.META_CREATED.format(
                    data=ticket.created_at.strftime(strings.DATETIME_FORMAT_PY)
                ),
                strings.META_UPDATED.format(
                    data=ticket.updated_at.strftime(strings.DATETIME_FORMAT_PY)
                ),
            )
        )

    # --------------------------------------------------------------- result

    def draft(self) -> TicketDraft:
        return TicketDraft(
            title=self.title_edit.text().strip(),
            description=self.description_edit.toPlainText().strip(),
            status=self.status_combo.currentData(),
            due_date=None if self.no_due_date.isChecked() else self.due_date_edit.date().toPython(),
            activities=self.activity_list.activities(),
        )

    # --------------------------------------------------------------- events

    def accept(self) -> None:
        if not self.title_edit.text().strip():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(strings.ERROR_TITLE)
            box.setText(strings.ERROR_TITLE_REQUIRED)
            box.setInformativeText(strings.ERROR_TITLE_REQUIRED_HINT)
            box.exec()
            self.title_edit.setFocus()
            return
        super().accept()

    def reject(self) -> None:
        """Invariant 7: cancelling with unsaved edits asks first."""
        if self._dirty and not self._confirm_discard():
            return
        super().reject()

    def _confirm_discard(self) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(strings.CONFIRM_DISCARD_TITLE)
        box.setText(strings.CONFIRM_DISCARD_TEXT)
        discard = box.addButton(strings.BUTTON_YES_DISCARD, QMessageBox.ButtonRole.DestructiveRole)
        keep = box.addButton(strings.BUTTON_NO, QMessageBox.ButtonRole.RejectRole)
        # Dismissing the question must not throw the work away.
        box.setDefaultButton(keep)
        box.exec()
        return box.clickedButton() is discard

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _on_no_due_date_toggled(self, checked: bool) -> None:
        self.due_date_edit.setEnabled(not checked)
        self._mark_dirty()
