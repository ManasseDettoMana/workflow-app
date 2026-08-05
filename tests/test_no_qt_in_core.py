"""Invariant 1: nothing under ``workflowapp.core`` may import Qt.

It is what keeps the data layer testable with no platform plugin and the rules
independent of the interface. The check is cheap and the mistake is easy - one
``from PySide6.QtCore import QDate`` in the model for convenience is all it takes
- so it is asserted here and again as its own step in CI.
"""

from __future__ import annotations

import importlib
import pkgutil
import subprocess
import sys

QT_ROOTS = {"PySide6", "shiboken6"}


def test_core_modules_import_without_qt():
    # A fresh interpreter, because by the time this test file runs pytest-qt has
    # already imported PySide6 into this one and sys.modules would prove nothing.
    code = (
        "import importlib, pkgutil, sys; "
        "import workflowapp.core; "
        "[importlib.import_module(m.name) "
        "for m in pkgutil.walk_packages(workflowapp.core.__path__, 'workflowapp.core.')]; "
        "print(','.join(sorted(m for m in sys.modules if m.split('.')[0] "
        "in {'PySide6', 'shiboken6'})))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    leaked = result.stdout.strip()
    assert leaked == "", f"workflowapp.core imported Qt: {leaked}"


def test_every_core_module_is_reachable():
    # Guards the test above: if walk_packages found nothing, it would pass while
    # checking nothing at all.
    import workflowapp.core

    names = [m.name for m in pkgutil.walk_packages(workflowapp.core.__path__, "workflowapp.core.")]
    assert {"workflowapp.core.models", "workflowapp.core.store"} <= set(names)
    for name in names:
        importlib.import_module(name)
