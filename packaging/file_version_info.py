"""The version resource Windows shows in the executable's Properties dialog.

Built from ``workflowapp.__version__`` rather than typed out, because
``tests/test_packaging.py`` exists to stop the version being maintained in two
places and a third copy here would walk straight past it.
"""

from __future__ import annotations

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

import workflowapp

COMPANY = "ManasseDettoMana"
PRODUCT = "Workflow App"
DESCRIPTION = "Gestore personale di ticket e attivita"

#: Italian (0x0410), Unicode (1200). The description above is the one string in
#: here a user ever reads, and it is in Italian like the rest of the interface.
LANGUAGE = 0x0410
CHARSET = 1200


def _version_tuple() -> tuple[int, int, int, int]:
    """``1.1.0`` as the four-part number the Windows resource format wants."""
    major, minor, patch = (int(part) for part in workflowapp.__version__.split("."))
    return (major, minor, patch, 0)


def version_info(executable_name: str) -> VSVersionInfo:
    """The resource for one executable.

    Both builds share everything except their filename, which Windows shows as
    "Original filename" and which differs between the folder build and the
    portable one.
    """
    numbers = _version_tuple()
    text = workflowapp.__version__

    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=numbers,
            prodvers=numbers,
            # No pre-release, patched or private-build flags to declare.
            mask=0x3F,
            flags=0x0,
            # VOS_NT_WINDOWS32, VFT_APP: an ordinary Windows application.
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        f"{LANGUAGE:04x}{CHARSET:04x}",
                        [
                            StringStruct("CompanyName", COMPANY),
                            StringStruct("FileDescription", DESCRIPTION),
                            StringStruct("FileVersion", text),
                            StringStruct("InternalName", PRODUCT),
                            StringStruct("OriginalFilename", executable_name),
                            StringStruct("ProductName", PRODUCT),
                            StringStruct("ProductVersion", text),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [LANGUAGE, CHARSET])]),
        ],
    )
