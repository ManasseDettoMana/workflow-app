"""Themes: the stylesheets load, the palettes are complete, the preference sticks."""

from __future__ import annotations

import pytest

from workflowapp.core.models import Status
from workflowapp.gui import strings, theme

pytestmark = pytest.mark.gui


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

    @pytest.mark.parametrize("which", list(theme.Theme))
    def test_each_theme_paints_the_selected_row_itself(self, which):
        # The selection-* pair on QTableView is not enough. Declaring
        # QTableView::item hands item drawing to the stylesheet, which then takes
        # the selected cell's background from the item rule - and without one, a
        # selected row keeps the view's own background. The rendered proof is in
        # tests/test_main_window.py; this is here so the rule cannot be deleted
        # as a duplicate of the two lines above it.
        rule = theme.stylesheet(which).partition("QTableView::item:selected")[2].partition("}")[0]
        assert "background-color:" in rule
        assert "color:" in rule

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
