"""The state of every card, rebuilt from the review log.

The log is the source of truth. Rows are ordered by learning day, then by
time. The first row of a card is its first answer ("learn"); the first row on
a later day is a review that moves the schedule; every further row on the
same day is drill, which leaves the schedule as it was. A regrade row changes
the grade of an earlier row of the same day.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any

from vocabbot.courses import CARD_ID
from vocabbot.fsrs import (
    AGAIN,
    DEFAULT_PARAMETERS,
    EASY,
    GOOD,
    HARD,
    Memory,
    Scheduler,
    fit_initial,
)

GRADES = ("known", "know", "almost", "dont_know")
RATING = {"known": EASY, "know": GOOD, "almost": HARD, "dont_know": AGAIN}
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


@dataclass
class CardState:
    card: str
    lang: str
    memory: Memory
    first_day: date
    last_day: date
    reps: int = 1
    lapses: int = 0
    last_grade: str = ""
    known: bool = False

    def due(self, scheduler: Scheduler) -> date:
        days = scheduler.due_interval(self.memory.stability, spread_key(self.card, self.last_day))
        return self.last_day + timedelta(days=days)


def spread_key(card: str, day: date) -> str:
    """What the spread of a due date depends on: the card and the day of its answer."""
    return f"{card}|{day.isoformat()}"


@dataclass
class Row:
    """One graded answer with its grade after regrades and its kind."""

    ts: str
    day: date
    card: str
    lang: str
    grade: str
    auto: str | None
    kind: str = ""
    error: str | None = None
    regraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Book:
    cards: dict[str, CardState]
    rows: list[Row]
    invalid: int = 0
    parameters: tuple[float, ...] = DEFAULT_PARAMETERS

    @property
    def fitted(self) -> bool:
        return self.parameters != DEFAULT_PARAMETERS

    def rows_on(self, day: date) -> list[Row]:
        return [row for row in self.rows if row.day == day]


def valid_row(raw: dict[str, Any]) -> bool:
    if not isinstance(raw.get("ts"), str) or not TS.match(raw["ts"]):
        return False
    if not isinstance(raw.get("day"), str) or not DAY.match(raw["day"]):
        return False
    if not isinstance(raw.get("card"), str) or not CARD_ID.match(raw["card"]):
        return False
    if raw.get("kind") == "regrade":
        return raw.get("grade") in GRADES[1:] and isinstance(raw.get("replaces"), str)
    return raw.get("grade") in GRADES


def order_key(raw: dict[str, Any]) -> tuple[str, str, str]:
    return (raw["day"], raw["ts"], raw["card"])


def replay(
    raw_rows: list[dict[str, Any]],
    *,
    before: date | None = None,
    parameters: tuple[float, ...] = DEFAULT_PARAMETERS,
) -> Book:
    """Card states from the log; with `before`, only rows of earlier days count."""
    good = [r for r in raw_rows if valid_row(r)]
    invalid = len(raw_rows) - len(good)
    if before is not None:
        limit = before.isoformat()
        good = [r for r in good if r["day"] < limit]
    cards: dict[str, CardState] = {}
    rows = _apply(cards, good, Scheduler(parameters=parameters))
    return Book(cards=cards, rows=rows, invalid=invalid, parameters=parameters)


def fitted_replay(raw_rows: list[dict[str, Any]]) -> Book:
    """The replay with initial stabilities fitted to the learner's second answers."""
    book = replay(raw_rows)
    parameters = fit_initial(second_answers(book))
    if parameters == book.parameters:
        return book
    return replay(raw_rows, parameters=parameters)


def second_answers(book: Book) -> dict[int, list[tuple[int, bool]]]:
    """For each first rating: days to the second answer and whether it was recalled."""
    first: dict[str, Row] = {}
    points: dict[int, list[tuple[int, bool]]] = {rating: [] for rating in RATING.values()}
    for row in book.rows:
        if row.kind == "learn":
            first[row.card] = row
        elif row.kind == "review" and row.card in first:
            learned = first.pop(row.card)
            points[RATING[learned.grade]].append(
                ((row.day - learned.day).days, row.grade != "dont_know")
            )
    return points


def extend(book: Book, raw_rows: list[dict[str, Any]]) -> Book:
    """`book` followed by rows of the same or later days; `book` itself stays as it was."""
    good = [r for r in raw_rows if valid_row(r)]
    cards = dict(book.cards)
    rows = _apply(cards, good, Scheduler(parameters=book.parameters))
    return Book(
        cards=cards,
        rows=[*book.rows, *rows],
        invalid=book.invalid + len(raw_rows) - len(good),
        parameters=book.parameters,
    )


def _apply(
    cards: dict[str, CardState], good: list[dict[str, Any]], scheduler: Scheduler
) -> list[Row]:
    """Apply valid rows in order. States are replaced, never changed in place."""
    good = sorted(good, key=order_key)
    regrades: dict[tuple[str, str], str] = {}
    for raw in good:
        if raw.get("kind") == "regrade":
            regrades[(raw["card"], raw["replaces"])] = raw["grade"]
    rows: list[Row] = []
    for raw in good:
        if raw.get("kind") == "regrade":
            continue
        card = raw["card"]
        day = date.fromisoformat(raw["day"])
        grade = regrades.get((card, raw["ts"]), raw["grade"])
        row = Row(
            ts=raw["ts"],
            day=day,
            card=card,
            lang=str(raw.get("lang") or card[:2]),
            grade=grade,
            auto=raw.get("auto"),
            error=raw.get("error"),
            regraded=(card, raw["ts"]) in regrades,
            raw=raw,
        )
        state = cards.get(card)
        if state is None:
            row.kind = "learn"
            cards[card] = CardState(
                card=card,
                lang=row.lang,
                memory=scheduler.first(RATING[grade]),
                first_day=day,
                last_day=day,
                last_grade=grade,
                known=grade == "known",
            )
        elif day <= state.last_day:
            row.kind = "drill"
        else:
            row.kind = "review"
            elapsed = (day - state.last_day).days
            cards[card] = replace(
                state,
                memory=scheduler.review(state.memory, RATING[grade], elapsed),
                last_day=day,
                reps=state.reps + 1,
                last_grade=grade,
                lapses=state.lapses + (1 if grade == "dont_know" else 0),
            )
        rows.append(row)
    return rows


@dataclass
class Today:
    """What the learner did on one day."""

    seen: list[str]  # cards in the order of their first row that day
    learned: list[str]  # cards whose first row ever was that day
    first_grade: dict[str, str]
    last_grade: dict[str, str]
    last_ts: dict[str, str]
    last_row: dict[str, Row]


def activity(book: Book, day: date) -> Today:
    seen: list[str] = []
    learned: list[str] = []
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    last_ts: dict[str, str] = {}
    last_row: dict[str, Row] = {}
    for row in book.rows_on(day):
        if row.card not in first:
            seen.append(row.card)
            first[row.card] = row.grade
            if row.kind == "learn":
                learned.append(row.card)
        last[row.card] = row.grade
        last_ts[row.card] = row.ts
        last_row[row.card] = row
    return Today(seen, learned, first, last, last_ts, last_row)


__all__ = [
    "AGAIN",
    "EASY",
    "GOOD",
    "GRADES",
    "HARD",
    "RATING",
    "Book",
    "CardState",
    "Row",
    "Today",
    "fitted_replay",
    "second_answers",
    "spread_key",
]
