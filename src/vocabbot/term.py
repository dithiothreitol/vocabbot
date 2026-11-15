"""What the terminal can show, and text styled for it, on the standard library only.

Colour follows the common conventions: NO_COLOR turns it off, FORCE_COLOR turns
it on, TERM=dumb and output that is not a terminal get plain text, and on
Windows the console must accept escape sequences. Symbols such as ✓ and █ have
ASCII stand-ins for consoles whose fonts lack them (VOCABBOT_ASCII=1 forces
them). Widths count East Asian wide characters as two columns and combining
marks as none, so columns line up with accented words.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TextIO

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MAX_WIDTH = 78  # prose reads well up to this width, even in a wide window
SGR = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "reverse": "7",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
}
# symbol: (Unicode, ASCII)
GLYPHS: dict[str, tuple[str, str]] = {
    "bullet": ("●", "*"),
    "know": ("✓", "+"),
    "almost": ("≈", "~"),
    "dont_know": ("✗", "x"),
    "known": ("✓", "+"),
    "new": ("+", "+"),
    "prompt": ("❯", ">"),
    "result": ("└", "`-"),
    "arrow": ("→", "->"),
    "sep": ("·", "|"),
    "rule": ("─", "-"),
    "full": ("█", "#"),
    "empty": ("░", "."),
    "quote_open": ("„", '"'),
    "quote_close": ("”", '"'),
}
SPARKS = ("▁▂▃▄▅▆▇█", " .:-=+*#")


@dataclass(frozen=True)
class Caps:
    """What one output stream can do."""

    color: bool = False
    unicode: bool = True
    width: int = 80
    redraw: bool = False  # lines already written may be erased (an interactive terminal)
    dim: str = "2"  # faint text; consoles without it get grey


def enable_vt() -> bool:
    """Turn on escape sequences in the Windows console; True where they work."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError, ValueError):
        return False


def detect(
    stream: TextIO | None = None,
    *,
    plain: bool = False,
    environ: Mapping[str, str] | None = None,
) -> Caps:
    """The capabilities of `stream` (standard output by default)."""
    stream = stream or sys.stdout
    env = os.environ if environ is None else environ
    tty = bool(getattr(stream, "isatty", lambda: False)())
    width = min(shutil.get_terminal_size((80, 24)).columns, 120) if tty else 80
    modern = sys.platform != "win32" or any(
        env.get(name) for name in ("WT_SESSION", "TERM_PROGRAM", "ConEmuANSI", "TERM")
    )
    encoding = str(getattr(stream, "encoding", "") or "").lower().replace("-", "")
    unicode = not env.get("VOCABBOT_ASCII") and modern and (encoding.startswith("utf") or not tty)
    if plain or env.get("NO_COLOR") or env.get("TERM") == "dumb":
        color = False
    elif env.get("FORCE_COLOR"):
        color = True
    else:
        color = tty and enable_vt()
    redraw = color and tty and not plain and bool(getattr(sys.stdin, "isatty", lambda: False)())
    return Caps(
        color=color,
        unicode=unicode,
        width=max(40, width),
        redraw=redraw,
        dim="2" if modern else "90",
    )


class Style:
    """Text in the colours and symbols the terminal can show."""

    def __init__(self, caps: Caps) -> None:
        self.caps = caps

    def __call__(self, text: str, *styles: str) -> str:
        if not self.caps.color or not styles or not text:
            return text
        codes = [self.caps.dim if s == "dim" else SGR[s] for s in styles if s in SGR]
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m" if codes else text

    def glyph(self, name: str) -> str:
        unicode, ascii_ = GLYPHS[name]
        return unicode if self.caps.unicode else ascii_

    @property
    def sep(self) -> str:
        return f" {self.glyph('sep')} "

    def width(self) -> int:
        return min(self.caps.width, MAX_WIDTH)

    def bar(self, done: int, total: int, size: int = 12) -> str:
        """A progress bar: █████░░░ in colour terminals, #####... elsewhere."""
        filled = round(size * done / total) if total else size
        filled = min(size, max(0, filled))
        full = self(self.glyph("full") * filled, "cyan")
        empty = self(self.glyph("empty") * (size - filled), "dim")
        return full + empty

    def spark(self, values: Sequence[float]) -> str:
        """One character per value, from the lowest bar for zero to the highest for the peak."""
        levels = SPARKS[0] if self.caps.unicode else SPARKS[1]
        peak = max(values, default=0)
        out = []
        for value in values:
            if value <= 0:
                out.append(self(levels[0], "dim") if self.caps.unicode else " ")
            else:
                index = 1 + round((len(levels) - 2) * value / peak) if peak else 1
                out.append(self(levels[min(index, len(levels) - 1)], "cyan"))
        return "".join(out)

    def rule(self, width: int | None = None) -> str:
        return self(self.glyph("rule") * (width or self.width()), "dim")


def plain_text(text: str) -> str:
    return ANSI.sub("", text)


def width_of(text: str) -> int:
    """Columns the text takes on screen."""
    total = 0
    for char in plain_text(text):
        if unicodedata.combining(char):
            continue
        total += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return total


def rows_of(lines: Sequence[str], width: int) -> int:
    """Screen rows a list of lines takes in a window `width` columns wide."""
    rows = 0
    for line in lines:
        columns = width_of(line)
        rows += max(1, -(-columns // width))
    return rows


def wrap(text: str, width: int, indent: str = "") -> list[str]:
    """Plain text wrapped to `width` columns; styles go on afterwards."""
    return textwrap.wrap(
        text,
        width=max(20, width),
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [indent]


def pad(text: str, width: int) -> str:
    """`text` followed by spaces up to `width` columns."""
    return text + " " * max(0, width - width_of(text))


def spread(left: str, right: str, width: int) -> str:
    """`left` and `right` at the two ends of one line, or one after the other if too long."""
    gap = width - width_of(left) - width_of(right)
    return f"{left}{' ' * gap}{right}" if gap >= 2 else f"{left}  {right}"


def difference(given: str, expected: str, style: Style) -> tuple[str, str, str]:
    """The typed answer and the expected one with the differing letters marked.

    Returns the two words for one line and, in ASCII mode, a third line of ^
    under the letters of the expected word that the answer missed or changed.
    """
    import difflib

    matcher = difflib.SequenceMatcher(a=given, b=expected, autojunk=False)
    wrong, right, marks = [], [], []
    for op, a1, a2, b1, b2 in matcher.get_opcodes():
        if op == "equal":
            wrong.append(given[a1:a2])
            right.append(expected[b1:b2])
            marks.append(" " * width_of(expected[b1:b2]))
            continue
        if a2 > a1:
            wrong.append(style(given[a1:a2], "red", "underline"))
        if b2 > b1:
            right.append(style(expected[b1:b2], "green", "bold", "underline"))
            marks.append("^" * width_of(expected[b1:b2]))
    caret = "".join(marks).rstrip() if not style.caps.color else ""
    return "".join(wrong), "".join(right), caret


def erase(rows: int) -> str:
    """Escape sequence that moves up `rows` lines and clears everything below."""
    return f"\x1b[{rows}F\x1b[J" if rows > 0 else ""
