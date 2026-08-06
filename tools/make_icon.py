"""Draw the application icon and write it as a multi-resolution ``.ico``.

Run this to regenerate ``workflowapp/gui/assets/app.ico``:

    python tools\\make_icon.py

The output is committed, so a build never depends on running this first. The
script exists so the icon has a source: a checked-in binary nobody can
regenerate is a file that can never be changed again.

**The mark** is a white checkmark on a rounded square in ``#2563eb`` - the light
theme's colour for ``Status.OPEN``, taken from ``gui/theme.py`` so the icon and
the application agree rather than merely resembling each other. A checkmark
rather than a letter: two strokes stay legible at 16px where a glyph turns to
mush, and drawing paths instead of text means no font dependency and the same
result on every machine. It is the same reasoning as
``gui/widgets/status_badge.py``, which paints its coloured dots rather than
shipping eight image files that drift apart.

**The container** is assembled here rather than by Qt. Qt's ICO writer produces
one frame per file and Windows wants six in one container, so the six-byte
header and the sixteen-byte directory entries are written by hand. The frames
themselves are PNG, which every Windows since Vista reads at any size.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

# Set before PySide6 is imported: this draws into a QImage and never shows a
# window, and without it the script needs a display to run.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)

#: Status.OPEN in the light palette. See gui/theme.py.
BACKGROUND = "#2563eb"
FOREGROUND = "#ffffff"

#: What Windows asks for. 256 is the one Explorer shows in large-icon views;
#: 16 is the title bar and the taskbar at standard scaling.
SIZES = (16, 32, 48, 64, 128, 256)

#: Everything below is a fraction of the icon's side, so one drawing serves
#: every size. The corner radius is Windows-ish rather than a full squircle.
CORNER_RADIUS = 0.22
STROKE_WIDTH = 0.10
#: The three points of the checkmark: down to the elbow, then up the long arm.
CHECK_POINTS = ((0.27, 0.52), (0.43, 0.68), (0.73, 0.34))

OUTPUT = Path(__file__).resolve().parent.parent / "workflowapp" / "gui" / "assets" / "app.ico"


def render(size: int) -> QImage:
    """The mark, drawn at one size."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        radius = size * CORNER_RADIUS
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BACKGROUND))
        painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

        path = QPainterPath(QPointF(CHECK_POINTS[0][0] * size, CHECK_POINTS[0][1] * size))
        for x, y in CHECK_POINTS[1:]:
            path.lineTo(QPointF(x * size, y * size))

        pen = QPen(QColor(FOREGROUND), size * STROKE_WIDTH)
        # Round caps and joins: a mitred elbow on a checkmark produces a spike
        # that reads as a smudge once the icon is 16 pixels across.
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    finally:
        # The QImage must not be used while a painter is still on it.
        painter.end()

    return image


def to_png(image: QImage) -> bytes:
    """One frame, PNG-encoded, ready to embed."""
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    try:
        if not image.save(buffer, "PNG"):
            raise RuntimeError(f"Qt could not encode the {image.width()}px frame as PNG.")
    finally:
        buffer.close()
    return bytes(data)


def build_ico(frames: dict[int, bytes]) -> bytes:
    """Pack PNG frames into an ICO container.

    ICONDIR is six bytes, then one sixteen-byte ICONDIRENTRY per frame, then the
    frames themselves. A side of 256 is written as 0, which is what the single
    byte the format allows for it means.
    """
    count = len(frames)
    header = struct.pack("<HHH", 0, 1, count)
    offset = len(header) + count * 16

    directory = bytearray()
    for size, png in frames.items():
        side = 0 if size >= 256 else size
        directory += struct.pack(
            "<BBBBHHII",
            side,  # width
            side,  # height
            0,  # colours in the palette; 0 for truecolour
            0,  # reserved
            1,  # colour planes
            32,  # bits per pixel
            len(png),
            offset,
        )
        offset += len(png)

    return bytes(header + directory) + b"".join(frames.values())


def main() -> int:
    # Constructed even though nothing is shown: QPainter needs the GUI
    # application's font and paint engine to exist.
    QGuiApplication([])

    frames = {size: to_png(render(size)) for size in SIZES}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(build_ico(frames))

    total = OUTPUT.stat().st_size
    print(f"Wrote {OUTPUT} ({total} bytes, {len(frames)} frames: {', '.join(map(str, SIZES))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
