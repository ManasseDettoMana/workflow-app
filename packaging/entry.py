"""The script PyInstaller freezes.

``workflowapp/__main__.py`` cannot serve as the entry script: PyInstaller runs it
as ``__main__`` with no package context, and its ``from .gui.app import main``
is a relative import that then has nothing to be relative to. Two lines of
absolute import here is the whole difference.
"""

from workflowapp.gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
