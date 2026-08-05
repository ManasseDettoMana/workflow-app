"""``python -m workflowapp``.

The GUI is imported inside ``main`` rather than at module scope so that importing
this module costs nothing and pulls in no Qt.
"""

from __future__ import annotations


def main() -> int:
    from .gui.app import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
