"""When the learner usually learns, from the ordinary statistics of the log, without a network.

The profile holds the chance of a session on each weekday over the last eight
weeks and the usual minutes of a learning day. With the plan's setting
`presence` on, the scheduler chooses, within the spread of a due date, a day
with a good chance of a session; the day's plan keeps the new words within the
usual minutes; and before a day the learner usually skips, the day offers
reviews ahead of their date. Everything follows from the log before the day
and from the plan, so both computers compute the same plan.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

WEEKS = 8  # the weeks the profile looks back on
MIN_DAYS = 14  # days since the first answer before a profile exists
PRIOR = 2.0  # days of the overall rate added to every weekday's count
MIN_TIMED_DAYS = 5  # learning days with timed answers before the usual minutes exist
LOW = 0.35  # a weekday below this chance is one the learner usually skips
ROOM = 1.25  # the day's plan may go this far beyond the usual minutes
AHEAD_MAX = 30  # reviews offered ahead of an expected day without learning
# seconds per card until the log has 20 timed answers of a kind
SECONDS = {"review": 10.0, "new": 25.0, "drill": 8.0, "ahead": 10.0}


@dataclass(frozen=True)
class Presence:
    """The chance of a session on each weekday (Monday first) and the usual minutes."""

    weekdays: tuple[float, ...]
    minutes: float | None
    days: int  # the days the profile rests on

    def chance(self, day: date) -> float:
        return self.weekdays[day.weekday()]

    def as_dict(self) -> dict[str, Any]:
        return {"weekdays": list(self.weekdays), "minutes": self.minutes, "days": self.days}


def profile(rows: Sequence[Any], day: date) -> Presence | None:
    """The profile from the rows of the log before `day`; None while the log is too short."""
    spent: dict[date, int] = {}
    timed: set[date] = set()
    for row in rows:
        if row.day >= day:
            continue
        spent.setdefault(row.day, 0)
        ms = row.raw.get("ms")
        if isinstance(ms, int) and 0 < ms < 600_000:
            spent[row.day] += ms
            timed.add(row.day)
    if not spent:
        return None
    first = min(spent)
    if (day - first).days < MIN_DAYS:
        return None
    start = max(first, day - timedelta(weeks=WEEKS))
    counts = [0] * 7
    hits = [0] * 7
    cursor = start
    while cursor < day:
        counts[cursor.weekday()] += 1
        hits[cursor.weekday()] += cursor in spent
        cursor += timedelta(days=1)
    overall = sum(hits) / max(1, sum(counts))
    weekdays = tuple(round((hits[i] + PRIOR * overall) / (counts[i] + PRIOR), 3) for i in range(7))
    minutes_of = sorted(spent[d] / 60000 for d in timed if d >= start)
    minutes = round(statistics.median(minutes_of), 1) if len(minutes_of) >= MIN_TIMED_DAYS else None
    return Presence(weekdays, minutes, (day - start).days)


def seconds(rows: Sequence[Any]) -> dict[str, float]:
    """Seconds per card of each kind from the last timed answers, the defaults without them."""
    times: dict[str, list[int]] = {"learn": [], "review": [], "drill": []}
    for row in rows[-500:]:
        ms = row.raw.get("ms")
        if isinstance(ms, int) and 0 < ms < 600_000 and row.kind in times:
            times[row.kind].append(ms)
    out = dict(SECONDS)
    if len(times["review"]) >= 20:
        out["review"] = statistics.median(times["review"]) / 1000
    if len(times["learn"]) >= 20:
        out["new"] = statistics.median(times["learn"]) / 1000 * 2
    if len(times["drill"]) >= 20:
        out["drill"] = statistics.median(times["drill"]) / 1000
    return out


def paced(planned: int, reviews: int, usual_minutes: float, per_card: dict[str, float]) -> int:
    """New words that keep the day within the usual minutes (and a quarter more)."""
    room = usual_minutes * ROOM * 60 - reviews * per_card["review"]
    allowed = math.floor(room / per_card["new"]) if room > 0 else 0
    return max(0, min(planned, allowed))
