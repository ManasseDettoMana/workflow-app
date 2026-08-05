"""Workflow App - a personal ticket and activity manager.

The package splits in two. ``workflowapp.core`` holds the models, the JSON store
and the business rules, and imports nothing from Qt; ``workflowapp.gui`` is the
PySide6 interface built on top of it. The dependency only ever points one way.
"""

__version__ = "1.0.0"
