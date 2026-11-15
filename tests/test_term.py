"""The terminal module: capabilities, styles, widths and the folding of a card."""

from __future__ import annotations

import io

from vocabbot import drill, term


class Tty(io.StringIO):
    encoding = "utf-8"

    def isatty(self) -> bool:
        return True


def test_colour_follows_the_conventions() -> None:
    piped = io.StringIO()
    assert not term.detect(piped, environ={}).color
    assert term.detect(piped, environ={"FORCE_COLOR": "1"}).color
    assert not term.detect(Tty(), environ={"NO_COLOR": "1", "FORCE_COLOR": "1"}).color
    assert not term.detect(Tty(), environ={"TERM": "dumb"}).color
    assert not term.detect(Tty(), plain=True, environ={"FORCE_COLOR": "1"}).color
    assert not term.detect(piped, environ={"VOCABBOT_ASCII": "1", "TERM": "xterm"}).unicode


def test_plain_style_leaves_text_alone() -> None:
    plain = term.Style(term.Caps(color=False, unicode=False))
    assert plain("tak", "bold", "green") == "tak"
    assert plain.glyph("know") == "+" and plain.glyph("arrow") == "->"
    assert plain.bar(3, 6, 6) == "###..."
    assert plain.spark([0, 1, 4]) == " -#"
    coloured = term.Style(term.Caps(color=True))
    assert coloured("tak", "bold", "green") == "\x1b[1;32mtak\x1b[0m"
    assert term.width_of(coloured("tak", "red")) == 3


def test_widths_count_columns() -> None:
    assert term.width_of("żółć") == 4
    assert term.width_of("日本") == 4
    assert term.width_of("é") == 1  # e with a combining accent
    assert term.rows_of(["a" * 100, "", "b"], 40) == 5
    assert term.pad("ab", 4) == "ab  "
    assert term.spread("a", "b", 6) == "a    b"
    assert term.wrap("jeden dwa trzy cztery", 20, "  ")[0].startswith("  jeden")


def test_difference_marks_the_changed_letters() -> None:
    ascii_style = term.Style(term.Caps(color=False, unicode=False))
    wrong, right, caret = term.difference("nien", "nein", ascii_style)
    assert (wrong, right) == ("nien", "nein") and caret.strip("^ ") == ""
    assert "^" in caret
    coloured = term.Style(term.Caps(color=True))
    wrong, right, caret = term.difference("Hunt", "Hund", coloured)
    assert term.plain_text(right) == "Hund" and "\x1b[" in right and caret == ""


def test_a_card_folds_into_one_line_where_the_terminal_redraws() -> None:
    written: list[str] = []
    raw: list[str] = []
    screen = drill.Screen(
        write=written.append,
        read_line=lambda prompt: "der Hund",
        read_one=lambda prompt: "",
        caps=term.Caps(color=True, redraw=True, width=40),
        raw=raw.append,
    )
    screen.begin()
    screen.show("● DE  powtórka")
    screen.show("  pies")
    screen.ask("> ")
    screen.fold("✓ DE  pies → der Hund")
    assert raw == [term.erase(3)]
    assert written[-1] == "✓ DE  pies → der Hund"
    plain = drill.Screen(write=written.append, raw=raw.append)
    plain.begin()
    plain.show("karta")
    plain.fold("wiersz")
    assert written[-1] == "karta" and raw == [term.erase(3)]
    plain.fold("wiersz", plain_too=True)
    assert written[-1] == "wiersz"
