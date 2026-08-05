"""The package metadata and the package agree with each other.

CI checks ``workflowapp.__version__`` against the git tag on a tagged build, but
that only runs on a tag. This runs everywhere, and catches the far more common
half of the mistake: bumping the version in one file and not the other.
"""

import re
import tomllib
from pathlib import Path

import workflowapp

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_matches_pyproject():
    metadata = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert workflowapp.__version__ == metadata["project"]["version"]


def test_version_is_a_release_number():
    assert re.fullmatch(r"\d+\.\d+\.\d+", workflowapp.__version__)
