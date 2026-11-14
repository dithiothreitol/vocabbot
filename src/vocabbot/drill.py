"""The day's session in a terminal.

Every answer is written to the log the moment it is graded, so the learner may
stop at any card (`:q`, Ctrl+C or the end of input) and lose nothing. With Rich
installed each card carries its language in colour; without it (vocabbot.pyz)
the session runs in plain text.
"""

from __future__ import annotations

import os
import sys
import time
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from vocabbot import assets, session, store
from vocabbot.courses import Catalog, presentation, question
from vocabbot.errors import VocabError
from vocabbot.queue import Item, compute

QUIT = ":q"
BATCH = 5
KEY_GRADES = {"1": "know", "2": "almost", "3": "dont_know"}


class Quit(Exception):
    """The learner ends the session."""


def read_key(prompt: str) -> str:
    """One key press; a whole line when the input is not a terminal."""
    print(prompt, end="", flush=True)
    if not sys.stdin.isatty():
        line = sys.stdin.readline()
        print()
        if line == "":
            raise EOFError
        return line.strip()[:1].lower()
    if sys.platform == "win32":
        import msvcrt

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            msvcrt.getwch()
            key = ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print()
    if key == "\x03":
        raise KeyboardInterrupt
    if key in ("\x04", "\x1a"):
        raise EOFError
    return "" if key in ("\r", "\n") else key.lower()


class Screen:
    """Plain text; RichScreen adds colours."""

    def __init__(
        self,
        write: Callable[[str], None] = print,
        read_line: Callable[[str], str] = input,
        read_one: Callable[[str], str] = read_key,
    ) -> None:
        self.write = write
        self.read_line = read_line
        self.read_one = read_one

    def show(self, text: str, style: str = "") -> None:
        self.write(text)

    def tag(self, lang: str) -> str:
        try:
            return str(assets.language(lang)["tag"])
        except KeyError:
            return lang.upper()

    def header(self, lang: str, label: str) -> None:
        self.show("")
        self.show(f"[{self.tag(lang)}] {label}", style=f"bold {self.color(lang)}")

    def color(self, lang: str) -> str:
        try:
            return str(assets.language(lang)["color"])
        except KeyError:
            return "white"

    def ask(self, prompt: str) -> str:
        return self.read_line(prompt)

    def key(self, prompt: str) -> str:
        return self.read_one(prompt)


class RichScreen(Screen):
    def __init__(self) -> None:
        from rich.console import Console

        self.console = Console(highlight=False)
        super().__init__(read_line=self._input)

    def _input(self, prompt: str) -> str:
        return self.console.input(prompt, markup=False)

    def show(self, text: str, style: str = "") -> None:
        self.console.print(text, style=style or None, markup=False)


def make_screen(plain: bool) -> Screen:
    if plain or os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return Screen()
    try:
        return RichScreen()
    except ImportError:
        return Screen()


def _word_lines(word: dict[str, Any]) -> list[str]:
    details = [assets.text(f"pos.{word['pos']}")] if word.get("pos") else []
    if word.get("gender"):
        details.append(assets.text(f"genders.{word['gender']}"))
    for key, value in (word.get("forms") or {}).items():
        details.append(f"{assets.text(f'forms.{key}')} {value}")
    first = word["word"] + (f"  ({', '.join(details)})" if details else "")
    if word.get("ipa"):
        first += f"  {word['ipa']}"
    lines = [first, f"= {word['meaning']}"]
    if word.get("also"):
        lines.append("  + " + ", ".join(word["also"]))
    if word.get("example"):
        lines.append(f"  {word['example']}")
        if word.get("example_pl"):
            lines.append(f"  {word['example_pl']}")
    return lines


def _question_lines(q: dict[str, Any]) -> list[str]:
    if q["ask"] == "word":
        extras = [assets.text(f"pos.{q['pos']}")] if q.get("pos") else []
        if q.get("with_article"):
            extras.append(assets.text("drill.with_article"))
        lines = [str(q["meaning"]) + (f"  ({', '.join(extras)})" if extras else "")]
        if q.get("hint"):
            lines.append(f"  {q['hint']}")
        if q.get("sentence"):
            lines.append(f"  {q['sentence']}")
            if q.get("sentence_pl"):
                lines.append(f"  {q['sentence_pl']}")
        return lines
    lines = [str(q["word"])]
    if q.get("sentence"):
        lines.append(f"  {q['sentence']}")
    return lines


class Drill:
    def __init__(
        self,
        learner: store.Learner,
        catalog: Catalog,
        day: date,
        screen: Screen,
        clock: Callable[[], datetime],
        ahead: int,
    ) -> None:
        self.learner = learner
        self.catalog = catalog
        self.day = day
        self.screen = screen
        self.clock = clock
        self.ahead = ahead
        self.counts: Counter[str] = Counter()
        self.failed: set[str] = set()

    def compute(self) -> Any:
        return compute(self.learner, self.catalog, self.day, ahead=self.ahead)

    def run(self) -> dict[str, Any]:
        dp = self.compute()
        summary = session.summary(self.learner, self.catalog, dp)
        self.screen.show(assets.text("drill.title", day=self.day.isoformat()), style="bold")
        self.screen.show(
            assets.text("drill.summary", minutes=summary["minutes"], **summary["left"])
        )
        self.screen.show(assets.text("drill.help"), style="dim")
        try:
            while True:
                dp = self.compute()
                pending = [item for item in dp.sequence if item.card not in self.failed]
                if not pending:
                    self.screen.show("")
                    self.screen.show(assets.text("drill.finished"), style="bold green")
                    break
                if pending[0].phase == "new":
                    batch = [item for item in pending if item.phase == "new"][:BATCH]
                    for item in self.introduce(batch, len(pending)):
                        self.ask(item)
                else:
                    self.ask(pending[0], left=len(pending))
        except (Quit, EOFError, KeyboardInterrupt):
            self.screen.show("")
            self.screen.show(assets.text("drill.saved_progress"), style="dim")
        answered = sum(self.counts.values())
        self.screen.show(
            assets.text(
                "drill.answered",
                count=answered,
                know=self.counts["know"],
                almost=self.counts["almost"],
                dont_know=self.counts["dont_know"],
            )
        )
        return {"answered": answered, **dict(self.counts)}

    def introduce(self, batch: list[Item], left: int) -> list[Item]:
        to_test = []
        for index, item in enumerate(batch, 1):
            label = f"{assets.text('drill.new_word')} {index}/{len(batch)}"
            self.screen.header(item.lang, label)
            for line in _word_lines(presentation(item.entry)):
                self.screen.show(line)
            key = self.screen.key(assets.text("drill.intro_keys") + " ")
            if key == "q":
                raise Quit
            if key == "z":
                try:
                    session.self_grade(
                        self.learner,
                        self.catalog,
                        self.day,
                        self.clock(),
                        item.card,
                        "known",
                        source="cli",
                    )
                    self.counts["known"] += 1
                except VocabError as exc:
                    self.screen.show(str(exc), style="red")
                    self.failed.add(item.card)
                continue
            to_test.append(item)
        if to_test:
            self.screen.show("")
            self.screen.show(assets.text("drill.test_title"), style="bold")
        return to_test

    def ask(self, item: Item, left: int | None = None) -> None:
        phase = assets.text(f"phases.{item.phase}")
        label = f"{phase} · {left}" if left else phase
        self.screen.header(item.lang, label)
        for line in _question_lines(question(item.entry, item.direction)):
            self.screen.show(line)
        start = time.monotonic()
        ahead = item.phase == "ahead"
        if item.direction == "p":
            given = self.screen.ask("> ")
            if given.strip() == QUIT:
                raise Quit
            ms = int((time.monotonic() - start) * 1000)
            dp = self.compute()
            try:
                entry, kind, state = session.classify(
                    dp, self.catalog, self.learner, item.card, ahead=ahead
                )
            except VocabError as exc:
                self.screen.show(str(exc), style="red")
                self.failed.add(item.card)
                return
            verdict = session.evaluate(dp, self.catalog, entry, given)
            self.show_verdict(verdict, entry)
            key = self.screen.key(
                assets.text("drill.grade_keys", grade=assets.text(f"grades.{verdict.grade}")) + " "
            )
            grade = KEY_GRADES.get(key, verdict.grade)
            result = session.record(
                self.learner,
                dp,
                item.card,
                entry,
                kind,
                state,
                grade,
                self.clock(),
                verdict=verdict,
                given=given,
                ms=ms,
                source="cli",
                ahead=ahead,
            )
            self.counts[grade] += 1
            if result.get("next_due"):
                self.screen.show(assets.text("cli.next_due", due=result["next_due"]), style="dim")
            if key == "q":
                raise Quit
            return
        self.screen.key(assets.text("drill.show_meaning") + " ")
        for line in _word_lines(presentation(item.entry)):
            self.screen.show(line)
        key = ""
        while key not in KEY_GRADES:
            key = self.screen.key(assets.text("drill.recognize_keys") + " ")
            if key == "q":
                raise Quit
        try:
            result = session.self_grade(
                self.learner,
                self.catalog,
                self.day,
                self.clock(),
                item.card,
                KEY_GRADES[key],
                ahead=ahead,
                source="cli",
            )
        except VocabError as exc:
            self.screen.show(str(exc), style="red")
            self.failed.add(item.card)
            return
        self.counts[KEY_GRADES[key]] += 1
        if result.get("next_due"):
            self.screen.show(assets.text("cli.next_due", due=result["next_due"]), style="dim")

    def show_verdict(self, verdict: Any, entry: dict[str, Any]) -> None:
        word = presentation(entry)
        lines = _word_lines(word)
        if verdict.grade == "know":
            self.screen.show("✓ " + lines[0], style="bold green")
        elif verdict.grade == "almost":
            errors = ", ".join(assets.text(f"error_classes.{e}") for e in verdict.errors)
            self.screen.show(f"≈ {lines[0]}  ({errors})", style="bold yellow")
        else:
            self.screen.show("✗ " + lines[0], style="bold red")
            if verdict.other_lang:
                self.screen.show(
                    assets.text("cli.other_lang", lang=assets.language_name(verdict.other_lang)),
                    style="red",
                )
        for line in lines[1:]:
            self.screen.show(line)


def run(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    *,
    ahead: int = 0,
    plain: bool = False,
    screen: Screen | None = None,
    clock: Callable[[], datetime] = session.now_utc,
) -> dict[str, Any]:
    drill = Drill(learner, catalog, day, screen or make_screen(plain), clock, ahead)
    return drill.run()
