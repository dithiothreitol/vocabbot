"""The terminal session with a scripted learner."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from conftest import correct, make_learner, moment

from vocabbot import drill
from vocabbot.courses import Catalog
from vocabbot.queue import compute

MONDAY = date(2026, 11, 16)


class Script(drill.Screen):
    """Answers questions right except the listed cards, presses Enter, records output."""

    def __init__(
        self, catalog: Catalog, wrong: set[str], known: set[str], quit_after: int | None = None
    ) -> None:
        self.out: list[str] = []
        super().__init__(write=self.out.append, read_line=self._line, read_one=self._key)
        self.catalog = catalog
        self.wrong = set(wrong)
        self.known = known
        self.quit_after = quit_after
        self.current: str | None = None
        self.answers = 0

    def _line(self, prompt: str) -> str:
        self.answers += 1
        if self.quit_after is not None and self.answers > self.quit_after:
            return drill.QUIT
        assert self.current is not None
        if self.current in self.wrong:
            self.wrong.discard(self.current)  # wrong once, right in the drill
            return "xxx"
        return correct(self.catalog, self.current)

    def _key(self, prompt: str) -> str:
        if "znałem" in prompt and self.current in self.known:
            return "z"
        return ""


def run(learner, catalog: Catalog, day: date, screen: Script) -> dict:  # type: ignore[no-untyped-def]
    clock_values: Iterator[int] = iter(range(10_000))

    original = drill.Drill.ask
    original_intro = drill.Drill.introduce

    def ask(self, item, left=None):  # type: ignore[no-untyped-def]
        screen.current = item.card
        return original(self, item, left)

    def introduce(self, batch, left):  # type: ignore[no-untyped-def]
        out = []
        for item in batch:
            screen.current = item.card
            out += original_intro(self, [item], left)
        return out

    drill.Drill.ask = ask  # type: ignore[method-assign]
    drill.Drill.introduce = introduce  # type: ignore[method-assign]
    try:
        return drill.run(
            learner, catalog, day, screen=screen, clock=lambda: moment(day, next(clock_values))
        )
    finally:
        drill.Drill.ask = original  # type: ignore[method-assign]
        drill.Drill.introduce = original_intro  # type: ignore[method-assign]


def test_a_full_day_in_the_terminal(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2"], new_per_day=6)
    new = compute(learner, catalog, MONDAY).new
    screen = Script(catalog, wrong={new[1]}, known={new[0]})
    result = run(learner, catalog, MONDAY, screen)
    assert result["known"] == 1
    assert result["dont_know"] == 1
    assert not compute(learner, catalog, MONDAY).sequence
    assert any("Na dziś koniec." in line for line in screen.out)
    rows = learner.rows()[0]
    assert rows[0]["grade"] == "known"
    assert all(r["source"] == "cli" for r in rows)

    tuesday = MONDAY + timedelta(days=1)
    result = run(learner, catalog, tuesday, Script(catalog, wrong=set(), known=set()))
    assert result["know"] >= 1


def test_stopping_keeps_the_answers(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["es:a1-a2"], new_per_day=8)
    screen = Script(catalog, wrong=set(), known=set(), quit_after=3)
    result = run(learner, catalog, MONDAY, screen)
    assert result["answered"] == 3
    assert len(learner.rows()[0]) == 3
    assert any("Postęp jest zapisany." in line for line in screen.out)


class Staged(Script):
    """A learner who types commands before the first answer and chooses at the end."""

    def __init__(self, catalog: Catalog, commands: list[str], more: str = "") -> None:
        super().__init__(catalog, wrong=set(), known=set())
        self.commands = commands
        self.more = more
        self.asked: list[str] = []

    def _line(self, prompt: str) -> str:
        if self.commands:
            return self.commands.pop(0)
        assert self.current is not None
        self.asked.append(self.current)
        return super()._line(prompt)

    def _key(self, prompt: str) -> str:
        if "Enter koniec" in prompt:
            key, self.more = self.more, ""
            return key
        return super()._key(prompt)


def test_stages_and_more_cards_in_the_terminal(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    run(learner, catalog, MONDAY, Script(catalog, wrong=set(), known=set()))
    day = MONDAY + timedelta(days=2)
    dp = compute(learner, catalog, day)
    reviews, new = list(dp.reviews), list(dp.new)
    assert len(reviews) == 2 and len(new) == 2

    # /nowe at the first review: the new words come first, the reviews after them;
    # at the end of the list "n" adds new words
    screen = Staged(catalog, commands=["/nowe"], more="n")
    run(learner, catalog, day, screen)
    assert screen.asked[:2] == new and set(screen.asked[2:4]) == set(reviews)
    assert len(screen.asked) == 4 + drill.MORE_NEW
    assert any("Dzisiejsza lista jest zrobiona." in line for line in screen.out)
    assert any(f"Dodane nowe słowa: {drill.MORE_NEW}." in line for line in screen.out)
    assert learner.extra_new(day) == drill.MORE_NEW
    assert any("Na dziś koniec." in line for line in screen.out)

    # every card has today's answer, so only new words are offered now
    again = Staged(catalog, commands=[], more="p")
    run(learner, catalog, day, again)
    assert not again.asked and not learner.extra_reviews(day)

    # the next round of reviews: the cards of later days, before their day
    other = make_learner(tmp_path / "other", ["de:a1-a2"], new_per_day=2)
    run(other, catalog, MONDAY, Script(catalog, wrong=set(), known=set()))
    tuesday = MONDAY + timedelta(days=1)
    learned = set(compute(other, catalog, tuesday).before.cards)
    assert not compute(other, catalog, tuesday).reviews
    screen = Staged(catalog, commands=["/powtorki"], more="p")
    run(other, catalog, tuesday, screen)
    assert any("Powtórki z dzisiejszej listy są zrobione." in line for line in screen.out)
    assert any("Następna tura powtórek: 2." in line for line in screen.out)
    assert set(screen.asked[2:]) == learned
    assert [row.get("ahead") for row in other.rows()[0][-2:]] == [True, True]


def test_new_words_as_questions_in_the_terminal(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2, new_words="ask")
    new = compute(learner, catalog, MONDAY).new
    screen = Script(catalog, wrong=set(new), known=set())
    result = run(learner, catalog, MONDAY, screen)
    # no introduction: each word is asked, missed, and learned in the drill
    assert not any("Sprawdzenie nowych słów" in line for line in screen.out)
    assert result["dont_know"] == 2 and result["know"] == 2
    assert [(r["kind"], r["grade"]) for r in learner.rows()[0]] == [
        ("learn", "dont_know"),
        ("learn", "dont_know"),
        ("drill", "know"),
        ("drill", "know"),
    ]

    # a word answered right at once was known before the course
    other = make_learner(tmp_path / "other", ["de:a1-a2"], new_per_day=2, new_words="ask")
    screen = Script(catalog, wrong=set(), known=set(), quit_after=1)
    result = run(other, catalog, MONDAY, screen)
    assert result["known"] == 1 and other.rows()[0][0]["grade"] == "known"
    assert any("zapisane jako znane" in line for line in screen.out)
    assert len(compute(other, catalog, MONDAY).new) == 3


class Checking(Script):
    """A learner who presses Enter to see the answer and grades it, and types commands."""

    def __init__(self, catalog: Catalog, keys: list[str], commands: list[str]) -> None:
        super().__init__(catalog, wrong=set(), known=set())
        self.keys = keys
        self.commands = commands
        self.prompts: list[str] = []

    def _line(self, prompt: str) -> str:
        if self.commands:
            return self.commands.pop(0)
        return ""

    def _key(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if "Jak dobrze znasz to słowo" in prompt:
            return self.keys.pop(0) if self.keys else "q"
        return super()._key(prompt)


def test_the_answer_shown_at_enter_and_graded_by_the_learner(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(
        tmp_path,
        ["de:a1-a2"],
        new_per_day=2,
        new_words="ask",
        answer_mode="self",
        sentence_translation="hidden",
    )
    first, second = compute(learner, catalog, MONDAY).new
    # /t shows the translation the plan keeps back; Enter shows the answer, graded 3 or 1;
    # a first "wiem" is a word known before, so one more new word joins the day
    screen = Checking(catalog, keys=["3", "1", "3", "1", "1"], commands=["/t"])
    result = run(learner, catalog, MONDAY, screen)
    entry = catalog.card(first)
    assert entry is not None
    assert any(str(entry["example"]["pl"]) in line for line in screen.out)
    assert (result["dont_know"], result["known"], result["know"]) == (2, 1, 2)
    rows = learner.rows()[0]
    extra = rows[2]["card"]
    assert extra not in (first, second)
    assert [(r["card"], r["kind"], r["grade"]) for r in rows] == [
        (first, "learn", "dont_know"),
        (second, "learn", "known"),
        (extra, "learn", "dont_know"),
        (first, "drill", "know"),
        (extra, "drill", "know"),
    ]
    assert all("auto" not in r for r in rows)
    drill_prompts = [p for p in screen.prompts if "Jak dobrze" in p]
    assert "2 prawie" in drill_prompts[0] and "2 prawie" not in drill_prompts[-1]


def test_a_word_put_aside_and_a_note_in_the_terminal(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3, new_words="ask")
    first, second, third = compute(learner, catalog, MONDAY).new
    commands = ["/pomin", correct(catalog, second), "/notatka brzmi znajomo", "/notatka"]
    screen = Checking(catalog, keys=[], commands=commands)
    screen.quit_after = None

    def lines(prompt: str) -> str:
        if screen.commands:
            return screen.commands.pop(0)
        return drill.QUIT

    screen.read_line = lines  # type: ignore[method-assign]
    run(learner, catalog, MONDAY, screen)
    assert learner.skipped() == {first.split("#")[0]}
    assert learner.notes() == {second.split("#")[0]: "brzmi znajomo"}
    assert any("Odłożono słowo" in line for line in screen.out)
    assert any("Zapisano notatkę" in line for line in screen.out)
    assert any("Po /notatka wpisz" in line for line in screen.out)
    assert third in compute(learner, catalog, MONDAY).new
