"""Generate OpenBoson OB monogram app icons (run from repo as needed)."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen

OUT = Path(__file__).resolve().parents[1] / "src" / "openboson" / "gui" / "resources"

SVG = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="4" y="4" width="56" height="56" rx="14" fill="#ffffff"
        stroke="#0f766e" stroke-width="3"/>
  <text x="32" y="42" text-anchor="middle"
        font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="700"
        fill="#0f766e">OB</text>
</svg>
"""


def paint_icon(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    margin = size * 0.06
    radius = size * 0.22
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    p.setBrush(QColor("#ffffff"))
    pen = QPen(QColor("#0f766e"))
    pen.setWidthF(max(2.0, size * 0.045))
    p.setPen(pen)
    p.drawRoundedRect(rect, radius, radius)
    font = QFont("Segoe UI")
    font.setBold(True)
    font.setPixelSize(int(size * 0.38))
    p.setFont(font)
    p.setPen(QColor("#0f766e"))
    p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "OB")
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def write_ico(path: Path, sizes: list[int]) -> None:
    png_blobs = [png_bytes(paint_icon(s)) for s in sizes]
    num = len(sizes)
    header = struct.pack("<HHH", 0, 1, num)
    entries: list[bytes] = []
    offset = 6 + 16 * num
    payload = b""
    for s, blob in zip(sizes, png_blobs, strict=True):
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        entries.append(struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(blob), offset))
        payload += blob
        offset += len(blob)
    path.write_bytes(header + b"".join(entries) + payload)


def main() -> None:
    app = QGuiApplication([])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "app_icon.svg").write_text(SVG, encoding="utf-8")
    assert paint_icon(256).save(str(OUT / "app_icon.png"), "PNG")
    write_ico(OUT / "app_icon.ico", [16, 24, 32, 48, 64, 128, 256])
    print("wrote", sorted(p.name for p in OUT.iterdir()))
    del app


if __name__ == "__main__":
    main()
