"""Themes: the stylesheets load, the palettes are complete, the preference sticks."""

from __future__ import annotations

import re

import pytest

from workflowapp.core.models import Status
from workflowapp.gui import strings, theme

pytestmark = pytest.mark.gui


def _selectors(qss: str) -> set[str]:
    """Every selector list in a stylesheet, comments stripped, spacing normalised.

    Enough of a parser to compare two files that are meant to differ only in
    their values. It does not understand nesting, which Qt stylesheets do not
    have.
    """
    without_comments = re.sub(r"/\*.*?\*/", "", qss, flags=re.DOTALL)
    return {" ".join(block.split()) for block in re.findall(r"([^{}]+)\{", without_comments)}


class TestStylesheets:
    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_each_theme_has_a_stylesheet_with_content_in_it(self, which):
        # Reads through importlib.resources, which is what will fail first if
        # the .qss files ever drop out of package-data.
        qss = theme.stylesheet(which)
        assert "QTableView" in qss
        assert "QToolBar" in qss

    def test_the_two_themes_are_not_the_same_file(self):
        assert theme.stylesheet(theme.Theme.LIGHT) != theme.stylesheet(theme.Theme.DARK)

    def test_the_two_themes_declare_the_same_selectors(self):
        # The two files are meant to be one design in two colourways: same rules
        # throughout, different values. Nothing enforced that, and a widget styled
        # in one theme and forgotten in the other is invisible until somebody
        # switches - which is how the native checkbox indicator and the unthemed
        # calendar popup both survived this long.
        light = _selectors(theme.stylesheet(theme.Theme.LIGHT))
        dark = _selectors(theme.stylesheet(theme.Theme.DARK))
        assert light == dark

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_each_theme_paints_the_selected_row_itself(self, which):
        # The selection-* pair on QTableView is not enough. Declaring
        # QTableView::item hands item drawing to the stylesheet, which then takes
        # the selected cell's background from the item rule - and without one, a
        # selected row keeps the view's own background. The rendered proof is in
        # tests/test_main_window.py; this is here so the rule cannot be deleted
        # as a duplicate of the two lines above it.
        rule = (
            theme.stylesheet(which)
            .partition("#ticketTable::item:selected {")[2]
            .partition("}")[0]
        )
        assert "background-color:" in rule
        assert "color:" in rule

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_the_table_rules_never_escape_the_ticket_table(self, which):
        # A QCalendarWidget keeps its day grid in a QTableView, so a bare
        # QTableView rule reaches into the ticket dialog's date popup. An ::item
        # rule reaching it is the damaging one: it takes the day cell away from
        # QCalendarWidget::paintCell and paints over it.
        escaped = [
            selector
            for selector in _selectors(theme.stylesheet(which))
            if "QTableView" in selector and "#ticketTable" not in selector
        ]
        assert escaped == []

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_each_theme_styles_the_calendar_popup(self, which):
        # Unstyled, the ticket dialog's date popup is a native white calendar
        # dropping out of a dark dialog.
        qss = theme.stylesheet(which)
        assert "qt_calendar_navigationbar" in qss
        assert "qt_calendar_calendarview" in qss
        assert "qt_datetimedit_calendar" in qss

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_neither_stylesheet_declares_an_item_rule_for_the_calendar(self, which):
        # QCalendarWidget::paintCell draws the day cells itself, out of the
        # view's palette - which is why the selection-* properties on that view
        # reach it at all. Declaring ::item hands the cell to QStyleSheetStyle
        # instead, and it paints over paintCell.
        offenders = [
            selector
            for selector in _selectors(theme.stylesheet(which))
            if "qt_calendar_calendarview" in selector and "::item" in selector
        ]
        assert offenders == []

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_each_theme_styles_a_checkbox_indicator(self, which):
        # Left to the native indicator, the box is drawn from the system palette
        # and stays light on a dark dialog. Both halves of the selector were
        # measured rather than assumed: a QListWidget's checkable item goes
        # through PE_IndicatorItemViewItemCheck, and it does pick this up.
        qss = theme.stylesheet(which)
        assert "QCheckBox::indicator" in qss
        assert "QListWidget::indicator" in qss
        assert "QCheckBox::indicator:checked" in qss

    def test_neither_stylesheet_styles_the_status_column(self):
        # The delegate owns that column. A rule here would be a second opinion
        # about it, and the two would drift.
        for which in theme.Theme:
            assert "StatusDelegate" not in theme.stylesheet(which)


class TestPalettes:
    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_every_status_has_a_colour(self, which):
        assert set(theme.PALETTES[which].statuses) == set(Status)

    def test_the_two_palettes_differ(self):
        light = theme.PALETTES[theme.Theme.LIGHT].statuses
        dark = theme.PALETTES[theme.Theme.DARK].statuses
        # Not a style preference: a single palette is unreadable in one theme or
        # the other, so if these ever converge somebody has undone the point.
        assert all(light[s] != dark[s] for s in Status)

    def test_applying_a_theme_switches_the_active_palette(self, qapp):
        theme.apply_theme(qapp, theme.Theme.DARK)
        assert theme.active() is theme.Theme.DARK
        assert theme.active_palette() is theme.PALETTES[theme.Theme.DARK]

        theme.apply_theme(qapp, theme.Theme.LIGHT)
        assert theme.active_palette().status_color(Status.URGENT).name() == "#b91c1c"

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_every_theme_has_a_quieter_ink_for_an_unfocused_selection(self, which):
        # The stylesheet paints an unfocused selection much paler than a focused
        # one, and the status delegate picks its pen from these two. If they ever
        # converge, one of the two backgrounds is being written on in the other's
        # ink.
        palette = theme.PALETTES[which]
        assert palette.selected_text_inactive != palette.selected_text
        assert palette.selected_text_inactive_color().isValid()
        assert palette.icon_color().isValid()

    def test_other_toggles(self):
        assert theme.Theme.LIGHT.other() is theme.Theme.DARK
        assert theme.Theme.DARK.other() is theme.Theme.LIGHT


class TestPreference:
    def test_it_round_trips(self, isolated_settings):
        del isolated_settings
        theme.save_preference(theme.Theme.DARK)
        assert theme.load_preference() is theme.Theme.DARK

    def test_an_unreadable_value_falls_back_to_light(self, isolated_settings):
        del isolated_settings
        theme.settings().setValue("theme", "arcobaleno")
        # Not worth an error dialog at startup over a settings value.
        assert theme.load_preference() is theme.Theme.LIGHT

    def test_the_default_is_light(self, isolated_settings):
        del isolated_settings
        assert theme.load_preference() is theme.Theme.LIGHT


def test_every_status_has_an_italian_label():
    assert set(strings.STATUS_LABELS) == set(Status)
    assert strings.status_label(Status.IN_PROGRESS) == "In Lavorazione"
