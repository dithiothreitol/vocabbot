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
