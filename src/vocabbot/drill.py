"""The day's session in a terminal.

Every answer is written to the log the moment it is graded, so the learner may
stop at any card (/koniec, Ctrl+C or the end of input) and lose nothing. The
day runs in the engine's order (reviews, new words, drill); the learner moves
to another stage at any card (/nowe, /powtorki, /utrwalanie), asks for more
new words (/wiecej), and at the end of the day's list chooses between more
new words, the next round of reviews and the end. The session draws with
term.py: colours and symbols where the terminal shows them,
plain text elsewhere. In an interactive terminal a finished card folds into
one line, so the screen keeps a short history of the session.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from vocabbot import assets, session, store, term
from vocabbot.courses import Catalog, presentation, question
from vocabbot.errors import VocabError
from vocabbot.queue import STAGES, Item, compute, staged

QUIT = ":q"
COMMANDS = {
    ":q": "quit",
    "/q": "quit",
    "/koniec": "quit",
    "/cofnij": "undo",
    "/znam": "known",
    "/pomoc": "help",
    "/?": "help",
    "/nowe": "new",
    "/powtorki": "reviews",
    "/powtórki": "reviews",
    "/utrwalanie": "drill",
    "/wiecej": "more",
    "/więcej": "more",
}
BATCH = 5
MORE_NEW = 5  # new words added by /wiecej and by "n" at the end of the day's list
MORE_REVIEWS = 10  # reviews of the next round, added by "p" at the end of the day's list
KEY_GRADES = {"1": "know", "2": "almost", "3": "dont_know"}
GRADE_COLOURS = {
    "know": "green",
    "known": "green",
    "almost": "yellow",
    "dont_know": "red",
    "new": "cyan",
}
NO_DIFF = {"wrong", "blank", "wrong_language"}
ACTIVITY_DAYS = 28


class Quit(Exception):
    """The learner ends the session."""


class Switch(Exception):
    """The learner moves to another stage; the card on screen stays in the queue."""


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
            msvcrt.getwch()  # an arrow or a function key
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
    if key == "\x1b":
        return "esc"
    return "" if key in ("\r", "\n") else key.lower()


def read_line(prompt: str) -> str:
    """A typed answer; with input from a pipe the answer is echoed, as a terminal would."""
    answer = input(prompt)
    if not sys.stdin.isatty():
        print(answer)
    return answer


def _raw(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


class Screen:
    """Where the session writes and reads; tests give their own functions."""

    def __init__(
        self,
        write: Callable[[str], None] = print,
        read_line: Callable[[str], str] = read_line,
        read_one: Callable[[str], str] = read_key,
        caps: term.Caps | None = None,
        raw: Callable[[str], None] = _raw,
    ) -> None:
        self.write = write
        self.read_line = read_line
        self.read_one = read_one
        self.caps = caps or term.Caps()
        self.style = term.Style(self.caps)
        self.raw = raw
        self.block: list[str] = []

    def show(self, text: str = "", *styles: str) -> None:
        line = self.style(text, *styles)
        self.write(line)
        self.block.append(line)

    def ask(self, prompt: str) -> str:
        answer = self.read_line(prompt)
        self.block.append(prompt + answer)
        return answer

    def key(self, prompt: str) -> str:
        pressed = self.read_one(prompt)
        self.block.append(prompt)
        return pressed

    def begin(self) -> None:
        """A new card starts; what is on screen stays."""
        self.block = []

    def fold(self, line: str | None, *, plain_too: bool = False) -> None:
        """Replace the card on screen by one line where the terminal can redraw.

        A terminal that cannot redraw keeps the card; the line follows only
        when `plain_too` asks for it (the result of an answer saved at once).
        """
        if self.caps.redraw and self.block:
            self.raw(term.erase(term.rows_of(self.block, self.caps.width)))
            if line is not None:
                self.write(line)
        elif line is not None and plain_too:
            self.write(line)
        self.block = []


def make_screen(plain: bool) -> Screen:
    return Screen(caps=term.detect(plain=plain))


# ---------------------------------------------------------------- pieces of a card


def lang_tag(lang: str) -> str:
    try:
        return str(assets.language(lang)["tag"])
    except KeyError:
        return lang.upper()


def lang_colour(lang: str) -> str:
    try:
        return str(assets.language(lang)["color"])
    except KeyError:
        return "white"


def word_details(word: dict[str, Any]) -> str:
    """Part of speech, gender, forms and pronunciation in one line."""
    details = [assets.text(f"pos.{word['pos']}")] if word.get("pos") else []
    if word.get("gender"):
        details.append(assets.text(f"genders.{word['gender']}"))
    for key, value in (word.get("forms") or {}).items():
        details.append(f"{assets.text(f'forms.{key}')} {value}")
    if word.get("ipa"):
        details.append(str(word["ipa"]))
    return ", ".join(details)


def when_back(result: dict[str, Any]) -> str:
    """When the card comes back, as the learner says it."""
    if result.get("drill"):
        return assets.text("drill.back_today")
    days = result.get("interval_days")
    if days == 1:
        return assets.text("drill.back_tomorrow")
    if days:
        return assets.text("drill.back_days", days=days)
    if result.get("next_due"):
        return assets.text("drill.back_on", day=result["next_due"])
    return ""


def polish_date(day: date) -> str:
    weekday = assets.text(f"weekdays.{store.WEEKDAYS[day.weekday()]}")
    month = assets.text(f"months_genitive.{day.month}")
    return f"{weekday}, {day.day} {month}"


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
        self.style = screen.style
        self.clock = clock
        self.ahead = ahead
        self.stage: str | None = None  # the stage the learner chose; None is the engine's order
        self.counts: Counter[str] = Counter()
        self.failed: set[str] = set()
        self.done = 0
        self.total = 0
        self.last: dict[str, Any] | None = None  # the last saved answer, for /cofnij
        self.to_work_on: list[str] = []
        self.started = time.monotonic()

    def compute(self) -> Any:
        return compute(self.learner, self.catalog, self.day, ahead=self.ahead)

    # ------------------------------------------------------------ the session

    def run(self) -> dict[str, Any]:
        dp = self.compute()
        summary = session.summary(self.learner, self.catalog, dp)
        self.header(summary)
        finished = False
        try:
            while True:
                dp = self.compute()
                pending = staged(
                    [item for item in dp.sequence if item.card not in self.failed], self.stage
                )
                self.total = self.done + len(pending)
                if not pending:
                    finished = True
                    if not self.offer_more(dp):
                        break
                    finished = False
                    continue
                try:
                    if pending[0].phase == "new":
                        batch = [item for item in pending if item.phase == "new"][:BATCH]
                        for item in self.introduce(batch, len(pending)):
                            self.ask(item)
                    else:
                        self.ask(pending[0], left=len(pending))
                except Switch:
                    continue
        except (Quit, EOFError, KeyboardInterrupt):
            pass
        self.closing(finished)
        answered = sum(self.counts.values())
        return {"answered": answered, **dict(self.counts)}

    def header(self, summary: dict[str, Any]) -> None:
        style = self.style
        left = summary["left"]
        self.screen.write(style(f"VocabBot{style.sep}{polish_date(self.day)}", "bold"))
        if any(left.values()):
            self.screen.write(
                style(assets.text("drill.summary", minutes=summary["minutes"], **left), "dim")
            )
        self.screen.write(style(assets.text("drill.help"), "dim"))

    # ------------------------------------------------------------ stages and more cards

    def switch(self, stage: str) -> None:
        """Move to a stage that has cards; the card on screen waits in its own stage."""
        waiting = {item.phase for item in self.compute().sequence if item.card not in self.failed}
        if not waiting & set(STAGES[stage]):
            self.screen.show(f"  {assets.text(f'drill.stage_empty_{stage}')}", "yellow")
            return
        self.stage = stage
        self.screen.fold(None)
        self.screen.write(self.style(assets.text(f"drill.stage_{stage}"), "bold"))
        raise Switch

    def add_more(self, new: int = 0, reviews: int = 0) -> bool:
        """More new words or the next round of reviews for today; False when none joined."""
        result = session.add_extra(self.learner, self.catalog, self.day, new, reviews)
        added = result["added"]["reviews" if reviews else "new"]
        key = "drill.added_reviews" if reviews else "drill.added_new"
        if not added:
            key = "drill.no_more_reviews" if reviews else "drill.no_more_new"
        self.screen.write(self.style(assets.text(key, count=added), "bold" if added else "yellow"))
        if added:
            self.stage = "reviews" if reviews else "new"
        return bool(added)

    def offer_more(self, dp: Any) -> bool:
        """At the end of the day's list: more new words, the next round of reviews, or the end."""
        available = session.more(dp, self.catalog)
        reviews = available["reviews_due"] + available["reviews_ahead"]
        options = []
        if available["new"]:
            options.append(assets.text("drill.more_new", count=min(MORE_NEW, available["new"])))
        if reviews:
            options.append(assets.text("drill.more_reviews", count=min(MORE_REVIEWS, reviews)))
        if not options:
            return False
        self.screen.write(self.style(assets.text("drill.list_done"), "bold"))
        prompt = self.style.sep.join([*options, assets.text("drill.more_end")])
        key = self.screen.key(self.style(prompt, "dim") + " ")
        if key == "n" and available["new"]:
            return self.add_more(new=MORE_NEW)
        if key == "p" and reviews:
            return self.add_more(reviews=MORE_REVIEWS)
        return False

    def card_head(self, item: Item, label: str) -> str:
        style = self.style
        colour = lang_colour(item.lang)
        left = (
            f"{style(style.glyph('bullet'), colour)} {style(lang_tag(item.lang), 'bold', colour)}"
        )
        left += f"  {style(label, 'dim')}"
        done = min(self.done, self.total)
        right = f"{style.bar(done, self.total, 10)} {style(f'{done}/{self.total}', 'dim')}"
        return term.spread(left, right, style.width())

    def sentence_lines(self, text: str | None, polish: str | None) -> None:
        width = self.style.width() - 2
        if text:
            for line in term.wrap(text, width, "  "):
                self.screen.show(line)
        if polish:
            for line in term.wrap(polish, width, "  "):
                self.screen.show(line, "dim")

    # ------------------------------------------------------------ new words

    def introduce(self, batch: list[Item], left: int) -> list[Item]:
        to_test = []
        style = self.style
        for index, item in enumerate(batch, 1):
            self.screen.begin()
            word = presentation(item.entry)
            label = f"{assets.text('drill.new_word')} {index}/{len(batch)}"
            self.screen.show(self.card_head(item, label))
            self.screen.show(f"  {style(word['word'], 'bold')}{style.sep}{word['meaning']}")
            details = word_details(word)
            if details:
                self.screen.show(f"  {details}", "dim")
            if word.get("also"):
                self.screen.show(f"  {assets.text('drill.also')} {', '.join(word['also'])}", "dim")
            self.sentence_lines(word.get("example"), word.get("example_pl"))
            key = self.screen.key(style(assets.text("drill.intro_keys"), "dim") + " ")
            while key == "p":
                self.switch("reviews")  # leaves the word when reviews wait, else says so
                key = self.screen.key(style(assets.text("drill.intro_keys"), "dim") + " ")
            if key in ("q", "esc"):
                raise Quit
            if key == "z":
                self.save_known(item, word)
                continue
            self.screen.fold(self.line_for(item, "new", f"{word['word']} = {word['meaning']}"))
            to_test.append(item)
        if to_test:
            self.screen.write(style(assets.text("drill.test_title"), "bold"))
        return to_test

    def save_known(self, item: Item, word: dict[str, Any]) -> None:
        try:
            result = session.self_grade(
                self.learner,
                self.catalog,
                self.day,
                self.clock(),
                item.card,
                "known",
                source="cli",
                with_progress=False,
            )
        except VocabError as exc:
            self.screen.show(f"  {exc}", "red")
            self.failed.add(item.card)
            return
        self.counts["known"] += 1
        self.done += 1
        self.last = None
        summary = f"{word['word']} = {word['meaning']}"
        self.screen.fold(
            self.line_for(item, "known", summary, assets.text("drill.known_saved")), plain_too=True
        )
        hint = result.get("level_hint")
        if hint:
            self.screen.show("  " + assets.text("progress.level_hint", **hint), "dim")

    # ------------------------------------------------------------ questions

    def ask(self, item: Item, left: int | None = None) -> None:
        style = self.style
        self.screen.begin()
        phase = assets.text(f"phases.{item.phase}")
        q = question(item.entry, item.direction)
        self.screen.show(self.card_head(item, phase))
        if item.direction != "p":
            self.recognition(item, q)
            return
        extras = [assets.text(f"pos.{q['pos']}")] if q.get("pos") else []
        if q.get("with_article"):
            extras.append(assets.text("drill.with_article"))
        line = f"  {style(str(q['meaning']), 'bold')}"
        if extras:
            line += style(style.sep + ", ".join(extras), "dim")
        self.screen.show(line)
        if q.get("hint"):
            self.screen.show(f"  {q['hint']}", "dim")
        self.sentence_lines(q.get("sentence"), q.get("sentence_pl"))
        start = time.monotonic()
        while True:
            given = self.screen.ask(style(style.glyph("prompt"), "cyan", "bold") + " ")
            command = COMMANDS.get(given.strip().lower())
            if command is None:
                break
            if command == "quit":
                raise Quit
            if command == "help":
                self.help()
            elif command == "undo":
                self.undo()
            elif command in STAGES:
                self.switch(command)
            elif command == "more":
                if self.add_more(new=MORE_NEW):
                    self.screen.fold(None)
                    raise Switch
            elif command == "known":
                if item.phase == "new":
                    self.save_known(item, presentation(item.entry))
                    return
                self.screen.show(f"  {assets.text('drill.known_only_new')}", "yellow")
        ms = int((time.monotonic() - start) * 1000)
        dp = self.compute()
        ahead = item.phase == "ahead"
        try:
            entry, kind, state = session.classify(
                dp, self.catalog, self.learner, item.card, ahead=ahead
            )
        except VocabError as exc:
            self.screen.show(f"  {exc}", "red")
            self.failed.add(item.card)
            return
        verdict = session.evaluate(dp, self.catalog, entry, given)
        word = presentation(entry)
        if verdict.grade == "know":
            result = self.save(dp, item, entry, kind, state, "know", verdict, given, ms, ahead)
            summary = f"{q['meaning']} {style.glyph('arrow')} {word['word']}"
            self.screen.fold(
                self.line_for(item, "know", summary, when_back(result)), plain_too=True
            )
            return
        self.show_verdict(verdict, word, given)
        grade_name = assets.text(f"grades.{verdict.grade}")
        key = self.screen.key(style(assets.text("drill.grade_keys", grade=grade_name), "dim") + " ")
        grade = KEY_GRADES.get(key, verdict.grade)
        result = self.save(dp, item, entry, kind, state, grade, verdict, given, ms, ahead)
        summary = f"{q['meaning']} {style.glyph('arrow')} {word['word']}"
        if verdict.errors and grade != "know":
            errors = ", ".join(assets.text(f"error_classes.{e}") for e in verdict.errors)
            summary += f"  ({errors})"
            self.to_work_on.append(f"{word['word']} ({errors})")
        self.screen.fold(self.line_for(item, grade, summary, when_back(result)))
        if key in ("q", "esc"):
            raise Quit

    def save(
        self,
        dp: Any,
        item: Item,
        entry: dict[str, Any],
        kind: str,
        state: Any,
        grade: str,
        verdict: Any,
        given: str,
        ms: int,
        ahead: bool,
    ) -> dict[str, Any]:
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
        self.done += 1
        self.last = {"card": item.card, "grade": grade, "word": result["word"]["word"]}
        return result

    def show_verdict(self, verdict: Any, word: dict[str, Any], given: str) -> None:
        style = self.style
        grade = verdict.grade
        colour = GRADE_COLOURS[grade]
        head = f"{style.glyph(grade)} {assets.text(f'grades.{grade}')}"
        if verdict.errors:
            errors = ", ".join(assets.text(f"error_classes.{e}") for e in verdict.errors)
            head += f"{style.sep}{errors}"
        self.screen.show(f"  {style(style.glyph('result'), 'dim')} {style(head, colour, 'bold')}")
        if verdict.other_lang:
            other = assets.language_name(verdict.other_lang)
            self.screen.show(f"    {assets.text('cli.other_lang', lang=other)}", "red")
        target = verdict.matched or word["word"]
        if given.strip() and not set(verdict.errors) & NO_DIFF:
            wrong, right, caret = term.difference(given.strip(), str(target), style)
            arrow = style.glyph("arrow")
            self.screen.show(f"    {wrong} {arrow} {right}")
            if caret:
                self.screen.show(
                    f"    {' ' * (term.width_of(given.strip()) + len(arrow) + 2)}{caret}"
                )
            if target != word["word"]:
                self.screen.show(f"    {style(word['word'], 'bold')}")
        else:
            self.screen.show(f"    {style(word['word'], 'bold')}")
        details = word_details(word)
        if details:
            self.screen.show(f"    {details}", "dim")
        if word.get("example"):
            width = style.width() - 4
            for line in term.wrap(str(word["example"]), width, "    "):
                self.screen.show(line)

    def recognition(self, item: Item, q: dict[str, Any]) -> None:
        style = self.style
        self.screen.show(f"  {style(str(q['word']), 'bold')}")
        self.sentence_lines(q.get("sentence"), None)
        key = self.screen.key(style(assets.text("drill.show_meaning"), "dim") + " ")
        if key in ("q", "esc"):
            raise Quit
        word = presentation(item.entry)
        self.screen.show(f"  {style.glyph('result')} {style(word['meaning'], 'bold')}")
        details = word_details(word)
        if details:
            self.screen.show(f"    {details}", "dim")
        key = ""
        while key not in KEY_GRADES:
            key = self.screen.key(style(assets.text("drill.recognize_keys"), "dim") + " ")
            if key in ("q", "esc"):
                raise Quit
        grade = KEY_GRADES[key]
        try:
            result = session.self_grade(
                self.learner,
                self.catalog,
                self.day,
                self.clock(),
                item.card,
                grade,
                ahead=item.phase == "ahead",
                source="cli",
                with_progress=False,
            )
        except VocabError as exc:
            self.screen.show(f"  {exc}", "red")
            self.failed.add(item.card)
            return
        self.counts[grade] += 1
        self.done += 1
        self.last = {"card": item.card, "grade": grade, "word": word["word"]}
        summary = f"{word['word']} {style.glyph('arrow')} {word['meaning']}"
        self.screen.fold(self.line_for(item, grade, summary, when_back(result)))

    # ------------------------------------------------------------ commands

    def help(self) -> None:
        for key in (
            "help_answer",
            "help_known",
            "help_undo",
            "help_stages",
            "help_more",
            "help_quit",
        ):
            self.screen.show(f"  {assets.text(f'drill.{key}', count=MORE_NEW)}", "dim")

    def undo(self) -> None:
        """/cofnij: another grade for the last answer, on the learner's request."""
        style = self.style
        if self.last is None:
            self.screen.show(f"  {assets.text('drill.nothing_to_undo')}", "yellow")
            return
        was = assets.text(f"grades.{self.last['grade']}")
        prompt = assets.text("drill.undo_keys", word=self.last["word"], grade=was)
        key = self.screen.key(style(prompt, "dim") + " ")
        grade = KEY_GRADES.get(key)
        if grade is None or grade == self.last["grade"]:
            return
        try:
            session.regrade(
                self.learner,
                self.catalog,
                self.day,
                self.clock(),
                self.last["card"],
                grade,
                source="cli",
            )
        except VocabError as exc:
            self.screen.show(f"  {exc}", "red")
            return
        self.counts[self.last["grade"]] -= 1
        self.counts[grade] += 1
        if grade == "know":
            prefix = f"{self.last['word']} ("
            self.to_work_on = [w for w in self.to_work_on if not w.startswith(prefix)]
        self.screen.show(
            "  "
            + assets.text(
                "drill.undone", word=self.last["word"], grade=assets.text(f"grades.{grade}")
            ),
            "green",
        )
        self.last["grade"] = grade

    # ------------------------------------------------------------ lines and the end

    def line_for(self, item: Item, grade: str, summary: str, right: str = "") -> str:
        style = self.style
        glyph = style(style.glyph(grade), GRADE_COLOURS.get(grade, "white"), "bold")
        tag = style(lang_tag(item.lang), lang_colour(item.lang))
        left = f"{glyph} {tag}  {summary}"
        return term.spread(left, style(right, "dim"), style.width()) if right else left

    def closing(self, finished: bool) -> None:
        style = self.style
        answered = sum(self.counts.values())
        minutes = max(1, round((time.monotonic() - self.started) / 60)) if answered else 0
        self.screen.write(style.rule())
        title = assets.text("drill.finished" if finished else "drill.saved_progress")
        line = title
        if answered:
            line += style.sep + assets.text("drill.answered_short", count=answered, minutes=minutes)
        self.screen.write(style(line, "bold"))
        if answered:
            parts = []
            for grade in ("know", "almost", "dont_know", "known"):
                if self.counts[grade]:
                    glyph = style(style.glyph(grade), GRADE_COLOURS[grade], "bold")
                    parts.append(f"{glyph} {self.counts[grade]} {assets.text(f'grades.{grade}')}")
            self.screen.write("  " + "   ".join(parts))
        if self.to_work_on:
            text = assets.text("drill.work_on", words=", ".join(self.to_work_on[:6]))
            for wrapped in term.wrap(text, style.width() - 2, "  "):
                self.screen.write(wrapped)
        tomorrow = session.summary(
            self.learner, self.catalog, compute(self.learner, self.catalog, self.day + timedelta(1))
        )
        left = tomorrow["left"]
        if any(left.values()):
            self.screen.write(
                "  " + assets.text("drill.tomorrow", minutes=tomorrow["minutes"], **left)
            )
        activity = self.activity()
        if any(activity):
            streak = self.streak()
            self.screen.write(
                "  "
                + assets.text("drill.activity", days=ACTIVITY_DAYS)
                + "  "
                + style.spark(activity)
                + style(style.sep + assets.text("drill.streak", days=streak), "dim")
            )

    def activity(self) -> list[int]:
        rows = compute(self.learner, self.catalog, self.day).book.rows
        per_day = Counter(row.day for row in rows)
        first = self.day - timedelta(days=ACTIVITY_DAYS - 1)
        return [per_day.get(first + timedelta(days=n), 0) for n in range(ACTIVITY_DAYS)]

    def streak(self) -> int:
        days = {row.day for row in compute(self.learner, self.catalog, self.day).book.rows}
        cursor = self.day if self.day in days else self.day - timedelta(days=1)
        count = 0
        while cursor in days:
            count += 1
            cursor -= timedelta(days=1)
        return count


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
