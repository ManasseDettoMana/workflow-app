"""Headless core: models, persistence and business logic.

Nothing in this package may import PySide6. That is what keeps the data layer
testable without a Qt platform plugin and the rules independent of the interface.
``tests/test_no_qt_in_core.py`` asserts it, and CI checks it separately.
"""
