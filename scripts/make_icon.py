"""Draw the VocabBot avatar with the standard library only.

The avatar follows the common form of assistants' avatars: a flat tile and a
face with two upright eyes. The face is the front card of the course, white
with the orange dot of the day's card, and a light blue card stands behind
it, on the blue of the brand. The shapes are written once and give both the
vector and the bitmap files.

    python scripts/make_icon.py    writes the files below

- plugin/.claude-plugin/icon.png          the plugin's icon (rounded tile)
- src/vocabbot/server/static/vocabbot.png the server's favicon and MCP icon
- src/vocabbot/server/static/vocabbot.svg the mark on the server's pages
- docs/assets/avatar.png                  the avatar for profiles (square)
- docs/assets/avatar.svg                  the same avatar as a vector

The square files fill the whole frame, because GitHub, Slack or a chat
application round the corners themselves; the face stays inside the circle of
a round frame.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE = 512  # pixels per side
SS = 4  # samples per axis in a pixel on an edge
TILE_RADIUS = 104  # the corner of the rounded tile
BLUE = "#2F5D9E"
BACK = "#8FB3E8"
WHITE = "#FFFFFF"
NAVY = "#1F3F70"
ORANGE = "#F2A541"
# the face is drawn on a 512 grid and placed with this scale and offset
SCALE, SHIFT_X, SHIFT_Y = 0.9, 10.0, 30.0
# later shapes cover earlier ones
#   rect: x, y, width, height, corner radius, turn in degrees about its centre
#   circle: centre x, centre y, radius
SHAPES: list[tuple[str, str, tuple[float, ...]]] = [
    ("rect", BACK, (178, 70, 256, 306, 48, 10)),
    ("rect", WHITE, (98, 122, 296, 334, 54, 0)),
    ("rect", NAVY, (166, 224, 58, 118, 29, 0)),
    ("rect", NAVY, (268, 224, 58, 118, 29, 0)),
    ("circle", ORANGE, (344, 410, 21)),
]
Color = tuple[int, int, int]


def rgb(colour: str) -> Color:
    return (int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16))


def in_rounded(x: float, y: float, box: tuple[float, float, float, float], r: float) -> bool:
    left, top, right, bottom = box
    if not (left <= x <= right and top <= y <= bottom):
        return False
    cx = min(max(x, left + r), right - r)
    cy = min(max(y, top + r), bottom - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def inside(kind: str, geometry: tuple[float, ...], x: float, y: float) -> bool:
    if kind == "circle":
        cx, cy, r = geometry
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    left, top, width, height, r, turn = geometry
    if turn:
        # turn the point back, so the test runs on the upright rectangle
        cx, cy = left + width / 2, top + height / 2
        a = math.radians(-turn)
        dx, dy = x - cx, y - cy
        x = cx + dx * math.cos(a) - dy * math.sin(a)
        y = cy + dx * math.sin(a) + dy * math.cos(a)
    return in_rounded(x, y, (left, top, left + width, top + height), r)


def colour_at(x: float, y: float, tile: bool) -> str | None:
    if tile:
        if not in_rounded(x, y, (0, 0, SIZE, SIZE), TILE_RADIUS):
            return None
    elif not (0 <= x <= SIZE and 0 <= y <= SIZE):
        return None
    fx, fy = (x - SHIFT_X) / SCALE, (y - SHIFT_Y) / SCALE
    for kind, colour, geometry in reversed(SHAPES):
        if inside(kind, geometry, fx, fy):
            return colour
    return BLUE


def pixel(samples: list[str | None]) -> bytes:
    hits = [rgb(s) for s in samples if s is not None]
    if not hits:
        return b"\x00\x00\x00\x00"
    n = len(hits)
    red = round(sum(h[0] for h in hits) / n)
    green = round(sum(h[1] for h in hits) / n)
    blue = round(sum(h[2] for h in hits) / n)
    return bytes([red, green, blue, round(255 * n / len(samples))])


def render(tile: bool) -> bytes:
    """The PNG; a pixel whose four corners agree takes their colour, an edge is sampled."""
    corners = [[colour_at(i, j, tile) for i in range(SIZE + 1)] for j in range(SIZE + 1)]
    rows = []
    for j in range(SIZE):
        row = bytearray([0])
        for i in range(SIZE):
            first = corners[j][i]
            if first == corners[j][i + 1] == corners[j + 1][i] == corners[j + 1][i + 1]:
                row += pixel([first])
                continue
            samples = [
                colour_at(i + (si + 0.5) / SS, j + (sj + 0.5) / SS, tile)
                for sj in range(SS)
                for si in range(SS)
            ]
            row += pixel(samples)
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + kind + data + crc

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
    return png


def svg() -> str:
    """The square avatar as SVG, the same shapes as the bitmap."""
    parts = []
    for kind, colour, g in SHAPES:
        if kind == "circle":
            parts.append(f'<circle cx="{g[0]:g}" cy="{g[1]:g}" r="{g[2]:g}" fill="{colour}"/>')
            continue
        x, y, w, h, r, turn = g
        about = f' transform="rotate({turn:g} {x + w / 2:g} {y + h / 2:g})"' if turn else ""
        parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}"'
            f' fill="{colour}"{about}/>'
        )
    face = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}"'
        f' width="{SIZE}" height="{SIZE}">'
        f'<rect width="{SIZE}" height="{SIZE}" fill="{BLUE}"/>'
        f'<g transform="matrix({SCALE:g} 0 0 {SCALE:g} {SHIFT_X:g} {SHIFT_Y:g})">{face}</g>'
        "</svg>\n"
    )


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"wrote {path.relative_to(ROOT).as_posix()} ({len(data)} bytes)")


if __name__ == "__main__":
    tile, square, vector = render(tile=True), render(tile=False), svg().encode()
    write(ROOT / "plugin" / ".claude-plugin" / "icon.png", tile)
    write(ROOT / "src" / "vocabbot" / "server" / "static" / "vocabbot.png", tile)
    write(ROOT / "src" / "vocabbot" / "server" / "static" / "vocabbot.svg", vector)
    write(ROOT / "docs" / "assets" / "avatar.png", square)
    write(ROOT / "docs" / "assets" / "avatar.svg", vector)
