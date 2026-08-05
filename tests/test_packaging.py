"""The package metadata and the package agree with each other.

CI checks ``workflowapp.__version__`` against the git tag on a tagged build, but
that only runs on a tag. This runs everywhere, and catches the far more common
half of the mistake: bumping the version in one file and not the other.

The resource tests below guard the other half of packaging. Every non-Python
file the application reads at runtime is reached through ``importlib.resources``
and has to be declared in ``[tool.setuptools.package-data]`` to survive an
installed or frozen build. Left out, they load perfectly from a source checkout
and are missing from the build, where the application starts unstyled or
iconless with nothing to say why - so the failure has to be caught here rather
than noticed by whoever runs the executable.
"""

import re
import struct
import tomllib
from importlib import resources
from pathlib import Path

import pytest

import workflowapp

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

#: The first four bytes of an ICO: reserved 0, then type 1.
ICO_MAGIC = b"\x00\x00\x01\x00"


def test_version_matches_pyproject():
    metadata = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert workflowapp.__version__ == metadata["project"]["version"]


def test_version_is_a_release_number():
    assert re.fullmatch(r"\d+\.\d+\.\d+", workflowapp.__version__)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_stylesheet_is_readable_as_a_package_resource(theme):
    text = resources.files("workflowapp.gui").joinpath(f"themes/{theme}.qss").read_text("utf-8")
    assert text.strip()


def test_icon_is_readable_as_a_package_resource():
    from workflowapp.gui import assets

    assert assets.icon_bytes().startswith(ICO_MAGIC)


def test_icon_carries_every_size_windows_asks_for():
    """A single-frame icon looks fine in Explorer and soft in the title bar."""
    from workflowapp.gui import assets

    data = assets.icon_bytes()
    count = struct.unpack("<H", data[4:6])[0]
    # A side of 0 in the directory entry is how the format spells 256.
    sides = {data[6 + entry * 16] or 256 for entry in range(count)}
    assert sides == {16, 32, 48, 64, 128, 256}


def test_package_data_declares_every_runtime_resource():
    """The declaration, not just the files. This is the line that gets dropped."""
    metadata = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared = metadata["tool"]["setuptools"]["package-data"]["workflowapp.gui"]
    assert "themes/*.qss" in declared
    assert "assets/*.ico" in declared
