"""The main window: what it lists, what it enables, and what it deletes."""

from __future__ import annotations

import ast
import re
from collections import Counter
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QMessageBox,
    QStyle,
    QStyleFactory,
    QStyleOptionViewItem,
    QToolBar,
)

from workflowapp.core.manager import TicketManager
from workflowapp.core.models import Status
from workflowapp.gui import icons, strings, theme
from workflowapp.gui import main_window as main_window_module
from workflowapp.gui.main_window import MainWindow
from workflowapp.gui.ticket_dialog import TicketDialog
from workflowapp.gui.widgets.status_badge import StatusDelegate
from workflowapp.gui.widgets.table_view import NO_ROW
from workflowapp.gui.widgets.ticket_table import TICKET_ID_ROLE, Column

pytestmark = pytest.mark.gui


@pytest.fixture
def manager(ticket_file):
    manager = TicketManager(ticket_file)
    manager.add_ticket("Relazione trimestrale", status=Status.IN_PROGRESS)
    manager.add_ticket("Chiamare il fornitore", status=Status.URGENT)
    manager.add_ticket("Archiviare i documenti", status=Status.DONE)
    return manager


@pytest.fixture
def window(qtbot, qapp, manager, isolated_settings):
    del isolated_settings
    theme.apply_theme(qapp, theme.Theme.LIGHT)
    window = MainWindow(manager)
    qtbot.addWidget(window)
    return window


class TestListing:
    def test_it_shows_every_ticket(self, window):
        assert window._proxy.rowCount() == 3

    def test_the_window_title_is_italian(self, window):
        assert window.windowTitle() == strings.WINDOW_TITLE

    def test_refresh_picks_up_a_new_ticket(self, window, manager):
        manager.add_ticket("Aggiunto dopo")
        window.refresh()
        assert window._proxy.rowCount() == 4

    def test_the_empty_message_appears_with_no_tickets(self, qtbot, qapp, ticket_file):
        del qapp
        window = MainWindow(TicketManager(ticket_file))
        qtbot.addWidget(window)
        window.show()
        assert window._empty_label.isVisible()
        assert window._empty_label.text() == strings.EMPTY_LIST
        assert not window._table.isVisible()

    def test_a_filter_matching_nothing_says_so_differently(self, window):
        window.show()
        window._search.setText("qualcosa che non esiste")
        assert window._empty_label.text() == strings.EMPTY_FILTER


class TestSelection:
    def test_nothing_is_selected_to_begin_with(self, window):
        assert window.selected_ticket_id() is None
        assert window.action_delete.isEnabled() is False
        assert window.action_edit.isEnabled() is False

    def test_selecting_a_row_enables_the_actions(self, window):
        window._table.selectRow(0)
        assert window.selected_ticket_id() is not None
        assert window.action_delete.isEnabled() is True

    def test_the_selected_id_survives_sorting(self, window, manager):
        # The bug this guards against: taking the view's row number and using it
        # as an index into the manager's list. With a sort proxy in between those
        # are different rows, and the symptom is deleting the wrong ticket.
        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        window._table.selectRow(0)
        first_by_title = sorted(manager.tickets(), key=lambda t: t.title.casefold())[0]
        assert window.selected_ticket_id() == first_by_title.id

        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.DescendingOrder)
        window._table.selectRow(0)
        last_by_title = sorted(manager.tickets(), key=lambda t: t.title.casefold())[-1]
        assert window.selected_ticket_id() == last_by_title.id

    def test_the_selection_is_kept_across_a_refresh(self, window, manager):
        window._table.selectRow(1)
        chosen = window.selected_ticket_id()
        manager.add_ticket("Un altro")
        window.refresh()
        assert window.selected_ticket_id() == chosen


class TestDeletion:
    def test_confirming_deletes(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        _answer(monkeypatch, strings.BUTTON_YES_DELETE)

        window.delete_selected()

        assert all(t.id != target for t in manager.tickets())
        assert window._proxy.rowCount() == 2

    def test_declining_keeps_the_ticket(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        _answer(monkeypatch, strings.BUTTON_NO)

        window.delete_selected()

        assert len(manager.tickets()) == 3

    def test_deleting_the_right_ticket_after_sorting(self, window, manager, monkeypatch):
        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        expected = sorted(manager.tickets(), key=lambda t: t.title.casefold())[0].id
        assert target == expected

        _answer(monkeypatch, strings.BUTTON_YES_DELETE)
        window.delete_selected()
        assert all(t.id != expected for t in manager.tickets())

    def test_deleting_persists(self, window, manager, monkeypatch):
        window._table.selectRow(0)
        target = window.selected_ticket_id()
        _answer(monkeypatch, strings.BUTTON_YES_DELETE)
        window.delete_selected()

        reopened = TicketManager(manager.path)
        assert all(t.id != target for t in reopened.tickets())

    def test_deleting_with_no_selection_does_nothing(self, window, manager):
        window.delete_selected()
        assert len(manager.tickets()) == 3


class TestFiltering:
    def test_the_search_box_filters(self, window):
        window._search.setText("fornitore")
        assert window._proxy.rowCount() == 1

    def test_the_status_combo_filters(self, window):
        index = window._status_filter.findData(Status.DONE)
        window._status_filter.setCurrentIndex(index)
        assert window._proxy.rowCount() == 1

    def test_the_first_combo_entry_means_no_filter(self, window):
        assert window._status_filter.itemData(0) is None
        assert window._status_filter.itemText(0) == strings.FILTER_ALL_STATUSES

    def test_every_status_is_offered_with_an_icon(self, window):
        offered = {
            window._status_filter.itemData(i) for i in range(1, window._status_filter.count())
        }
        assert offered == set(Status)
        assert not window._status_filter.itemIcon(1).isNull()

    def test_the_overdue_checkbox_filters(self, window, manager):
        overdue = manager.add_ticket("Scaduto", due_date=date.today() - timedelta(days=3))
        window.refresh()
        assert window._proxy.rowCount() == 4
        window._overdue_check.setChecked(True)
        assert window._proxy.rowCount() == 1
        window.select_ticket(overdue.id)
        assert window.selected_ticket().title == "Scaduto"


class TestStatusBar:
    """Two labels, not a temporary message.

    ``showMessage`` hides everything added with ``addWidget`` for as long as the
    message is up, so the count and the badge have to be widgets or a single
    stray call blanks them.
    """

    def test_it_counts_visible_and_total(self, window):
        window._search.setText("fornitore")
        assert "1" in window._status_label.text()
        assert "3" in window._status_label.text()

    def test_overdue_tickets_get_their_own_badge(self, qtbot, qapp, ticket_file):
        del qapp
        manager = TicketManager(ticket_file)
        manager.add_ticket("In ritardo", due_date=date.today() - timedelta(days=3))
        window = MainWindow(manager)
        qtbot.addWidget(window)
        window.show()
        assert window._overdue_label.isVisible()
        assert "ritardo" in window._overdue_label.text()

    def test_the_badge_is_hidden_when_nothing_is_late(self, window):
        window.show()
        # "0 in ritardo" is a number to read and dismiss on every glance.
        assert not window._overdue_label.isVisible()

    def test_nothing_ever_calls_show_message(self):
        # The count is a widget now, and a widget added with addWidget is hidden
        # for as long as a temporary message is up. One stray showMessage blanks
        # the bar, and nothing about the blank bar says why - which is why this
        # is asserted about the module rather than left to a review comment.
        tree = ast.parse(Path(main_window_module.__file__).read_text(encoding="utf-8"))
        called = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        assert "showMessage" not in called


class TestTheme:
    def test_toggling_switches_and_saves(self, window, qapp):
        assert theme.active() is theme.Theme.LIGHT
        window.toggle_theme()
        assert theme.active() is theme.Theme.DARK
        assert theme.load_preference() is theme.Theme.DARK
        assert qapp.styleSheet() == theme.stylesheet(theme.Theme.DARK)

    def test_toggling_twice_returns(self, window):
        window.toggle_theme()
        window.toggle_theme()
        assert theme.active() is theme.Theme.LIGHT

    def test_the_status_icons_are_repainted(self, window):
        # They are drawn from the Python palette, so unlike the stylesheet they
        # do not refresh themselves when the theme changes.
        before = window._status_filter.itemIcon(1).pixmap(14, 14).toImage()
        window.toggle_theme()
        after = window._status_filter.itemIcon(1).pixmap(14, 14).toImage()
        assert before != after


#: WCAG AA for body text.
MIN_CONTRAST = 4.5

#: How much of the title's ink has to survive being selected. Antialiased edge
#: pixels always lose contrast when the background darkens - white on blue has
#: less headroom than black on white - so the whole glyph never survives. The
#: failure this guards against leaves nothing at all: about a third gets through
#: when it works, and none of it when it does not.
MIN_INK_SURVIVING = 0.25


def _luminance(color: QColor) -> float:
    """WCAG relative luminance."""

    def channel(value: int) -> float:
        v = value / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(color.red())
        + 0.7152 * channel(color.green())
        + 0.0722 * channel(color.blue())
    )


def _contrast(one: QColor, other: QColor) -> float:
    high, low = sorted((_luminance(one), _luminance(other)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.fixture
def windows11_style(qapp):
    """Force the Qt style the bug below belongs to, and put back the old one.

    Left to the runner's default this test proves nothing: under Fusion - what
    the offscreen platform picks, and so what CI would otherwise measure - the
    selected row renders correctly with or without the fix.
    """
    style = QStyleFactory.create("windows11")
    if style is None:
        pytest.skip("the windows11 style is not available on this platform")
    previous = qapp.style().objectName()
    qapp.setStyle(style)
    yield
    qapp.setStyle(QStyleFactory.create(previous) or QStyleFactory.create("Fusion"))


class TestSelectedRowIsReadable:
    """The title has to still be legible once its row is selected.

    Rendered rather than read off the stylesheet, because what goes wrong is a
    style's doing and not a colour's. Under Qt's "windows11" style - the default
    on Windows 11 - declaring ``QTableView::item`` at all hands item drawing to
    the stylesheet, which then paints the selected cell with ``selection-color``
    for the text and the view's own ``background-color`` behind it: white on
    white, and the ticket's title disappears. Every other style paints it from
    the palette and is unaffected, which is why this forces the style.
    """

    @staticmethod
    def _cell_pixels(window, column, *, selected: bool) -> dict[tuple[int, int], int]:
        table = window._table
        table.selectRow(0) if selected else table.clearSelection()
        QApplication.processEvents()
        rect = table.visualRect(window._proxy.index(0, int(column)))
        image = table.viewport().grab(rect).toImage()
        return {
            (x, y): image.pixel(x, y)
            for y in range(image.height())
            for x in range(image.width())
        }

    @staticmethod
    def _background(pixels: dict[tuple[int, int], int]) -> QColor:
        # The commonest colour in a cell of text is the cell's background.
        return QColor.fromRgb(Counter(pixels.values()).most_common(1)[0][0])

    # TITLE is drawn by the stylesheet, STATUS by a delegate that paints its own
    # text. The delegate is the half no stylesheet rule can fix, so it is the
    # half worth rendering rather than reading off the .qss.
    @pytest.mark.parametrize("column", [Column.TITLE, Column.STATUS])
    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_the_row_survives_being_selected(
        self, windows11_style, window, qtbot, qapp, which, column
    ):
        del windows11_style
        theme.apply_theme(qapp, which)
        window.show()
        qtbot.waitExposed(window)

        plain = self._cell_pixels(window, column, selected=False)
        plain_background = self._background(plain)
        # The glyphs, located while they are still easy to see. The same pixels
        # are then looked at again once the row is selected, which is what makes
        # this a measurement of the text rather than of whatever else the style
        # drew in the cell.
        ink = [
            at
            for at, pixel in plain.items()
            if _contrast(QColor.fromRgb(pixel), plain_background) >= MIN_CONTRAST
        ]
        if len(ink) < 50:
            # No fonts on the runner, nothing rasterised. Better skipped than
            # failed for a reason that has nothing to do with the colours.
            pytest.skip(f"the {column.name} column rendered no text to measure")

        selected = self._cell_pixels(window, column, selected=True)
        background = self._background(selected)
        assert background != plain_background, (
            f"the selected row is painted {background.name()}, the same as an "
            f"unselected one, in the {which.value} theme"
        )

        surviving = sum(
            1 for at in ink if _contrast(QColor.fromRgb(selected[at]), background) >= MIN_CONTRAST
        )
        assert surviving >= len(ink) * MIN_INK_SURVIVING, (
            f"only {surviving} of {len(ink)} pixels of the {column.name} column "
            f"still reach {MIN_CONTRAST}:1 against {background.name()} once the "
            f"row is selected, in the {which.value} theme"
        )


class TestTheUnfocusedSelectionStaysReadable:
    """The status label has to survive the window losing focus, too.

    Deliberately not a rendered test. ``State_Active`` follows
    ``isActiveWindow()``, which is false under ``QT_QPA_PLATFORM=offscreen``, so
    a rendering would measure whichever branch the platform happened to land on
    and would pass just as happily with the branch removed. The decision is
    named instead, and the contrast it depends on is checked against the
    stylesheet that actually paints the background.
    """

    @staticmethod
    def _option(*, selected: bool, active: bool) -> QStyleOptionViewItem:
        opt = QStyleOptionViewItem()
        if selected:
            opt.state |= QStyle.StateFlag.State_Selected
        if active:
            opt.state |= QStyle.StateFlag.State_Active
        return opt

    @staticmethod
    def _inactive_background(which) -> QColor:
        rule = (
            theme.stylesheet(which)
            .partition("#ticketTable::item:selected:!active {")[2]
            .partition("}")[0]
        )
        found = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", rule)
        assert found, f"the {which.value} theme has no unfocused-selection rule"
        return QColor(found.group(1))

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_an_active_selection_takes_the_light_ink(self, which):
        palette = theme.PALETTES[which]
        pen = StatusDelegate._text_pen(palette, self._option(selected=True, active=True))
        assert pen == palette.selected_text_color()

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_an_unfocused_selection_takes_the_quieter_ink(self, which):
        palette = theme.PALETTES[which]
        pen = StatusDelegate._text_pen(palette, self._option(selected=True, active=False))
        assert pen == palette.selected_text_inactive_color()

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_an_unselected_row_takes_the_palettes_own_text(self, which):
        opt = self._option(selected=False, active=True)
        pen = StatusDelegate._text_pen(theme.PALETTES[which], opt)
        assert pen == opt.palette.text().color()

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_the_quieter_ink_is_readable_on_the_quieter_background(self, which):
        # The pairing the delegate and the stylesheet have to agree on. Retuning
        # one of the two colours without the other is what this catches, and
        # white on the light theme's pale selection is 1.2:1.
        ink = theme.PALETTES[which].selected_text_inactive_color()
        assert _contrast(ink, self._inactive_background(which)) >= MIN_CONTRAST


class TestRowHover:
    """Qt hovers one cell; this table hovers the row.

    ``QAbstractItemView`` gives ``State_MouseOver`` to the index under the
    pointer alone. With SelectRows in force, one tinted cell reads as a rendering
    fault, so the view tracks the row and the delegates widen the state to it.
    """

    @staticmethod
    def _state_for(window, row: int, column) -> QStyleOptionViewItem:
        index = window._proxy.index(row, int(column))
        delegate = window._table.itemDelegateForIndex(index)
        opt = QStyleOptionViewItem()
        delegate.initStyleOption(opt, index)
        return opt

    @pytest.mark.parametrize("column", list(Column))
    def test_the_hover_reaches_every_column_in_the_row(self, window, column):
        window._table._set_hovered_row(0)
        opt = self._state_for(window, 0, column)
        assert opt.state & QStyle.StateFlag.State_MouseOver

    @pytest.mark.parametrize("column", list(Column))
    def test_a_row_that_is_not_hovered_keeps_its_state_clear(self, window, column):
        window._table._set_hovered_row(0)
        opt = self._state_for(window, 1, column)
        assert not (opt.state & QStyle.StateFlag.State_MouseOver)

    def test_leaving_the_table_drops_the_hover(self, window):
        window._table._set_hovered_row(0)
        window._table.leaveEvent(QEvent(QEvent.Type.Leave))
        assert window._table.hovered_row() == NO_ROW


@pytest.fixture
def shown(window, qtbot):
    """The window on screen, which window-level shortcuts need to fire at all."""
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    return window


class TestKeyboardShortcuts:
    def test_ctrl_f_selects_what_is_already_in_the_search_box(self, shown, qtbot):
        shown._search.setText("fornitore")
        qtbot.keyClick(shown, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        # Asserted on the selection rather than on hasFocus(), which is
        # unobservable under the offscreen platform. It is also the half that
        # matters: Ctrl+F on a box that already holds a search means a new
        # search, so the next keystroke has to replace it, not extend it.
        assert shown._search.selectedText() == "fornitore"

    def test_esc_clears_every_filter_at_once(self, shown, qtbot):
        shown._search.setText("fornitore")
        shown._status_filter.setCurrentIndex(shown._status_filter.findData(Status.URGENT))
        shown._overdue_check.setChecked(True)

        qtbot.keyClick(shown, Qt.Key.Key_Escape)

        assert shown._search.text() == ""
        assert shown._status_filter.currentData() is None
        assert shown._overdue_check.isChecked() is False
        # The proxy has to have heard about it, not just the widgets: the three
        # are silenced while they are cleared, so a forgotten _on_filter_changed
        # leaves an empty filter row over a still-filtered table.
        assert shown._proxy.rowCount() == 3

    def test_esc_with_nothing_set_changes_nothing(self, shown, qtbot):
        qtbot.keyClick(shown, Qt.Key.Key_Escape)
        assert shown._proxy.rowCount() == 3
        assert shown._search.text() == ""

    def test_f2_opens_the_selected_ticket(self, shown, qtbot, monkeypatch):
        shown._table.selectRow(0)
        opened: list[str] = []

        def exec_(self):
            opened.append(self._ticket.id)
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(TicketDialog, "exec", exec_)
        qtbot.keyClick(shown, Qt.Key.Key_F2)

        assert opened == [shown.selected_ticket_id()]

    def test_the_edit_tooltip_names_both_ways_in(self, window):
        assert "Invio" in window.action_edit.toolTip()
        assert "F2" in window.action_edit.toolTip()

    def test_the_search_box_names_both_its_keys(self, window):
        tip = window._search.toolTip()
        assert strings.TOOLTIP_SEARCH in tip
        assert strings.TOOLTIP_CLEAR_FILTERS in tip


class TestContextMenu:
    @staticmethod
    def _at_row(window, row: int) -> QPoint:
        return window._table.visualRect(window._proxy.index(row, int(Column.TITLE))).center()

    @staticmethod
    def _id_of_row(window, row: int) -> str:
        return window._proxy.index(row, int(Column.TITLE)).data(TICKET_ID_ROLE)

    def test_it_offers_opening_and_deleting(self, shown):
        menu = shown._context_menu_at(self._at_row(shown, 0))
        assert [action.text() for action in menu.actions()] == [
            strings.ACTION_EDIT,
            strings.ACTION_DELETE,
        ]

    def test_right_clicking_a_row_selects_it_first(self, shown):
        shown._table.selectRow(2)
        shown._context_menu_at(self._at_row(shown, 0))
        # Without this the menu acts on whatever was selected before the click,
        # which is a ticket the user is not pointing at.
        assert shown.selected_ticket_id() == self._id_of_row(shown, 0)

    def test_the_actions_are_enabled_by_the_time_the_menu_is_built(self, shown):
        shown._table.clearSelection()
        menu = shown._context_menu_at(self._at_row(shown, 0))
        assert all(action.isEnabled() for action in menu.actions())

    def test_empty_space_offers_no_menu(self, shown):
        # A menu holding nothing but greyed-out entries is worse than no menu.
        assert shown._context_menu_at(QPoint(5, shown._table.viewport().height() - 1)) is None

    def test_it_acts_on_the_row_under_the_pointer_after_sorting(self, shown, manager):
        # The proxy invariant, same one as test_deleting_the_right_ticket_after
        # _sorting: a view row is not a list index, and a menu that confused the
        # two would delete a different ticket than the one right-clicked.
        shown._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        QApplication.processEvents()
        shown._context_menu_at(self._at_row(shown, 0))
        first_by_title = sorted(manager.tickets(), key=lambda t: t.title.casefold())[0]
        assert shown.selected_ticket_id() == first_by_title.id


class TestTheHeaderLayoutIsRemembered:
    """The sort and the column widths survive a restart.

    One QSettings key: QHeaderView.saveState already carries the widths, the
    sort indicator's section and its order.
    """

    @staticmethod
    def _reopen(qtbot, manager) -> MainWindow:
        window = MainWindow(manager)
        qtbot.addWidget(window)
        window.show()
        QApplication.processEvents()
        return window

    def test_the_sort_column_comes_back(self, window, qtbot, manager):
        window.show()
        window._table.sortByColumn(int(Column.TITLE), Qt.SortOrder.AscendingOrder)
        window.close()

        again = self._reopen(qtbot, manager)
        header = again._table.horizontalHeader()
        assert header.sortIndicatorSection() == int(Column.TITLE)
        assert header.sortIndicatorOrder() is Qt.SortOrder.AscendingOrder

    def test_a_column_width_comes_back(self, window, qtbot, manager):
        window.show()
        QApplication.processEvents()
        window._table.setColumnWidth(int(Column.DUE_DATE), 173)
        window.close()

        again = self._reopen(qtbot, manager)
        assert again._table.columnWidth(int(Column.DUE_DATE)) == 173

    def test_the_columns_a_user_can_drag_are_the_ones_that_are_remembered(self, window):
        # Neither Stretch nor ResizeToContents can be dragged, so under those
        # there is no width to remember and the key would store something
        # nothing could ever change.
        header = window._table.horizontalHeader()
        assert header.sectionResizeMode(int(Column.TITLE)) is QHeaderView.ResizeMode.Stretch
        for column in (Column.STATUS, Column.DUE_DATE, Column.ACTIVITIES, Column.UPDATED):
            assert (
                header.sectionResizeMode(int(column)) is QHeaderView.ResizeMode.Interactive
            )


class TestToolbarIcons:
    @staticmethod
    def _actions(window) -> list:
        return [
            window.action_new,
            window.action_edit,
            window.action_delete,
            window.action_theme,
        ]

    @staticmethod
    def _drawn(action) -> object:
        return action.icon().pixmap(icons.ICON_SIZE, icons.ICON_SIZE).toImage()

    def test_every_toolbar_action_carries_one(self, window):
        assert all(not action.icon().isNull() for action in self._actions(window))

    def test_no_two_of_them_are_the_same_drawing(self, window):
        # A copy-paste in _apply_action_icons is invisible otherwise: four
        # buttons all showing the plus still passes "every action has an icon".
        drawings = [self._drawn(action) for action in self._actions(window)]
        assert all(one != other for one, other in combinations(drawings, 2))

    def test_the_label_stays_beside_the_icon(self, window):
        # Icon-only would be four glyphs nobody has seen before, in an
        # application whose whole interface is words.
        toolbar = window.findChild(QToolBar)
        assert toolbar.toolButtonStyle() is Qt.ToolButtonStyle.ToolButtonTextBesideIcon

    def test_they_are_repainted_on_a_theme_change(self, window):
        # The mirror of test_the_status_icons_are_repainted, and what catches
        # _apply_action_icons being left out of _retint. A QIcon is not
        # stylesheet-driven, so without it the dark toolbar keeps dark icons.
        before = [self._drawn(action) for action in self._actions(window)]
        window.toggle_theme()
        after = [self._drawn(action) for action in self._actions(window)]
        assert all(one != other for one, other in zip(before, after, strict=True))


def _answer(monkeypatch, button_text: str) -> None:
    """Make the next QMessageBox answer with the button carrying this text."""

    def exec_(self):
        for button in self.buttons():
            if button.text().replace("&", "") == button_text:
                self.setClickedButtonForTest(button)
                return 0
        raise AssertionError(f"no button labelled {button_text!r}")

    # QMessageBox has no public way to say which button was clicked, so the
    # window is asked instead through a small shim installed on the class.
    def set_clicked(self, button):
        self._test_clicked = button

    def clicked_button(self):
        return getattr(self, "_test_clicked", None)

    monkeypatch.setattr(QMessageBox, "setClickedButtonForTest", set_clicked, raising=False)
    monkeypatch.setattr(QMessageBox, "clickedButton", clicked_button, raising=False)
    monkeypatch.setattr(QMessageBox, "exec", exec_, raising=False)
