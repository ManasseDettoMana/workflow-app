"""The main window: what it lists, what it enables, and what it deletes."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from workflowapp.core.manager import TicketManager
from workflowapp.core.models import Status
from workflowapp.gui import strings, theme
from workflowapp.gui.main_window import MainWindow
from workflowapp.gui.widgets.ticket_table import Column

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
    def test_it_counts_visible_and_total(self, window):
        window._search.setText("fornitore")
        message = window.statusBar().currentMessage()
        assert "1" in message and "3" in message

    def test_overdue_tickets_are_mentioned(self, qtbot, qapp, ticket_file):
        del qapp
        manager = TicketManager(ticket_file)
        manager.add_ticket("In ritardo", due_date=date.today() - timedelta(days=3))
        window = MainWindow(manager)
        qtbot.addWidget(window)
        assert "ritardo" in window.statusBar().currentMessage()


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
    def _title_pixels(window, *, selected: bool) -> dict[tuple[int, int], int]:
        table = window._table
        table.selectRow(0) if selected else table.clearSelection()
        QApplication.processEvents()
        rect = table.visualRect(window._proxy.index(0, int(Column.TITLE)))
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

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_the_title_survives_being_selected(self, windows11_style, window, qtbot, qapp, which):
        del windows11_style
        theme.apply_theme(qapp, which)
        window.show()
        qtbot.waitExposed(window)

        plain = self._title_pixels(window, selected=False)
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
            pytest.skip("the title rendered no text to measure")

        selected = self._title_pixels(window, selected=True)
        background = self._background(selected)
        assert background != plain_background, (
            f"the selected row is painted {background.name()}, the same as an "
            f"unselected one, in the {which.value} theme"
        )

        surviving = sum(
            1 for at in ink if _contrast(QColor.fromRgb(selected[at]), background) >= MIN_CONTRAST
        )
        assert surviving >= len(ink) * MIN_INK_SURVIVING, (
            f"only {surviving} of {len(ink)} pixels of the title still reach "
            f"{MIN_CONTRAST}:1 against {background.name()} once the row is "
            f"selected, in the {which.value} theme"
        )

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
