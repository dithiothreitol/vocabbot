"""Draw the VocabBot icon (512 x 512 PNG) with the standard library only.

Three stacked cards on a blue rounded square; the front card has three lines
of text and an orange dot, the day's card.

    python scripts/make_icon.py    writes plugin/.claude-plugin/icon.png
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE, SS = 512, 3  # supersampling per axis
BLUE = (47, 93, 158)
BACK = (143, 179, 232)
MIDDLE = (201, 218, 245)
WHITE = (255, 255, 255)
ORANGE = (242, 165, 65)
OUT = Path(__file__).resolve().parents[1] / "plugin" / ".claude-plugin" / "icon.png"
Color = tuple[int, int, int]


def in_rounded(x: float, y: float, box: tuple[float, float, float, float], r: float) -> bool:
    left, top, right, bottom = box
    if not (left <= x <= right and top <= y <= bottom):
        return False
    cx = min(max(x, left + r), right - r)
    cy = min(max(y, top + r), bottom - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def color_at(x: float, y: float) -> Color | None:
    if not in_rounded(x, y, (0, 0, SIZE, SIZE), 104):
        return None
    if in_rounded(x, y, (120, 150, 360, 446), 28):
        if (x - 312) ** 2 + (y - 396) ** 2 <= 26**2:
            return ORANGE
        for top, width in ((206, 150), (252, 118), (298, 170)):
            if in_rounded(x, y, (152, top, 152 + width, top + 20), 10):
                return BLUE
        return WHITE
    if in_rounded(x, y, (148, 120, 388, 416), 28):
        return MIDDLE
    if in_rounded(x, y, (176, 90, 416, 386), 28):
        return BACK
    return BLUE


def render() -> bytes:
    rows = []
    for j in range(SIZE):
        row = bytearray([0])
        for i in range(SIZE):
            acc = [0, 0, 0, 0]
            for sj in range(SS):
                for si in range(SS):
                    c = color_at(i + (si + 0.5) / SS, j + (sj + 0.5) / SS)
                    if c:
                        acc[0] += c[0]
                        acc[1] += c[1]
                        acc[2] += c[2]
                        acc[3] += 1
            if acc[3]:
                n = acc[3]
                alpha = round(255 * n / (SS * SS))
                row += bytes([acc[0] // n, acc[1] // n, acc[2] // n, alpha])
            else:
                row += b"\x00\x00\x00\x00"
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + kind + data + crc

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
    return png


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = render()
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data)} bytes)")
