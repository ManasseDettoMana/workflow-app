"""The two conventions that are cheap to state and expensive to police by eye.

Invariant 8: no emojis, anywhere.
Invariant 9: the interface is Italian, and that Italian lives in ``gui/strings.py``.

Both are the kind of rule that holds for a month and then quietly stops. A test
is what makes "is the whole UI actually Italian?" answerable.
"""

from __future__ import annotations

import ast
import unicodedata
from pathlib import Path

import pytest

from workflowapp.core.models import Status
from workflowapp.gui import strings

ROOT = Path(__file__).resolve().parent.parent
GUI = ROOT / "workflowapp" / "gui"

SOURCE_FILES = sorted(
    path
    for pattern in ("workflowapp/**/*.py", "tests/**/*.py", "*.md", "docs/*.md")
    for path in ROOT.glob(pattern)
)

QSS_FILES = sorted(GUI.glob("themes/*.qss"))


#: Where emoji actually live. "Not ASCII" is far too blunt - Italian needs
#: à, è, é, ì, ò, ù - and so is Unicode category So on its own, which also covers
#: the box-drawing characters that draw the directory tree in docs/prompt.md and
#: the © and ° that are ordinary typography.
_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),  # the emoji planes proper
    (0x2600, 0x27BF),  # miscellaneous symbols and dingbats
    (0x2B00, 0x2BFF),  # arrows and stars used as emoji
    (0xFE0F, 0xFE0F),  # the variation selector that makes one render as emoji
)


def _is_emoji(char: str) -> bool:
    if char.isascii():
        return False
    if unicodedata.category(char) != "So" and ord(char) != 0xFE0F:
        return False
    return any(low <= ord(char) <= high for low, high in _EMOJI_RANGES)


class TestNoEmoji:
    @pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
    def test_source_and_documentation(self, path):
        offenders = {c for c in path.read_text(encoding="utf-8") if _is_emoji(c)}
        assert not offenders, f"{path.relative_to(ROOT)} contains {offenders}"

    @pytest.mark.parametrize("path", QSS_FILES, ids=lambda p: p.name)
    def test_stylesheets(self, path):
        offenders = {c for c in path.read_text(encoding="utf-8") if _is_emoji(c)}
        assert not offenders, f"{path.relative_to(ROOT)} contains {offenders}"

    # Built from code points rather than written out, because this file is one
    # of the files the sweep above reads - a literal emoji here would make the
    # suite fail on its own test data. It did.
    @pytest.mark.parametrize(
        "codepoint", [0x1F600, 0x1F680, 0x2705, 0x2B50, 0x26A0], ids=hex
    )
    def test_the_detector_catches_real_emoji(self, codepoint):
        # Otherwise every test above passes by never finding anything.
        assert _is_emoji(chr(codepoint))

    @pytest.mark.parametrize(
        "codepoint",
        [ord("a"), ord("à"), ord("è"), 0x2014, 0x00A9, 0x00B0, 0x2500, 0x251C],
        ids=hex,
    )
    def test_the_detector_leaves_text_alone(self, codepoint):
        # Italian letters, typography, and the box drawing in docs/prompt.md.
        assert not _is_emoji(chr(codepoint))


#: Every string literal that may appear in ``gui`` outside ``strings.py``.
#: All of them are technical: colours, Qt object names, settings keys, format
#: templates, resource paths. A new entry here is a decision, and an Italian one
#: does not belong in it.
ALLOWED_GUI_LITERALS = {
    # Separators and format templates.
    "\n",
    " - ",
    "/",
    "{} - {}",
    # Theme palette colours.
    "#15803d",
    "#2563eb",
    "#4ade80",
    "#60a5fa",
    "#6b7280",
    "#9aa3b2",
    "#b45309",
    "#b91c1c",
    "#f87171",
    "#fbbf24",
    "#ffffff",
    # Qt object names, used by the stylesheets to target widgets.
    "activityButton",
    "emptyLabel",
    "metaLabel",
    "sectionLabel",
    # Theme tokens and resource loading.
    "dark",
    "light",
    "themes/",
    ".qss",
    "utf-8",
    "workflowapp.gui",
    "assets/app.ico",
    # QSettings keys.
    "theme",
    "window/geometry",
    "window/state",
    # Python, and the platform check guarding the Windows-only taskbar call.
    "__main__",
    "win32",
    # The AppUserModelID. Not read by anyone: it is the key Windows groups
    # taskbar buttons under, and it has to be a stable identifier rather than a
    # translated name.
    "ManasseDettoMana.WorkflowApp",
}


def _literals(path: Path) -> dict[str, int]:
    """String literals in a module, excluding docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    return {
        node.value: node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value
        and node.value not in docstrings
    }


GUI_MODULES = sorted(p for p in GUI.rglob("*.py") if p.name != "strings.py")


class TestItalianLivesInOnePlace:
    @pytest.mark.parametrize("path", GUI_MODULES, ids=lambda p: p.name)
    def test_no_unexpected_literal_in_a_gui_module(self, path):
        unexpected = {
            text: line
            for text, line in _literals(path).items()
            if text not in ALLOWED_GUI_LITERALS
        }
        assert not unexpected, (
            f"{path.relative_to(ROOT)} has string literals that are not in "
            f"ALLOWED_GUI_LITERALS: {unexpected}. If one of these is text the "
            f"user reads, it belongs in gui/strings.py."
        )

    def test_strings_covers_every_status(self):
        assert set(strings.STATUS_LABELS) == set(Status)

    def test_the_status_labels_are_the_italian_the_brief_asked_for(self):
        assert [strings.status_label(s) for s in Status] == [
            "Aperto",
            "In Lavorazione",
            "Fatto",
            "Urgente",
        ]

    def test_no_status_label_is_stored_anywhere(self):
        # Invariant 4 from the other direction: the tokens go in the file, the
        # labels go on the screen, and the two must not be confused.
        tokens = {s.value for s in Status}
        labels = set(strings.STATUS_LABELS.values())
        assert tokens.isdisjoint(labels)


class TestCoreErrorMessagesAreItalian:
    """The one deliberate exception to "Italian lives in strings.py"."""

    def test_they_are_written_at_the_raise_site(self):
        core = ROOT / "workflowapp" / "core"
        messages = []
        for path in sorted(core.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name != "WorkflowAppError":
                    continue
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        messages.append(arg.value)
                    elif isinstance(arg, ast.JoinedStr):
                        messages.append("".join(
                            v.value for v in arg.values if isinstance(v, ast.Constant)
                        ))
        assert messages, "no WorkflowAppError messages found - has core moved?"
        # A sanity check rather than a translation audit: Italian error text
        # reaches for these words and English does not.
        italian = [m for m in messages if any(w in m.lower() for w in ("il ", "la ", "non "))]
        assert len(italian) >= len(messages) // 2
