"""FSRS-6 spaced-repetition scheduler, standard library only.

A port of the scheduler in py-fsrs 6.3.3 (MIT, see NOTICE) for whole-day
intervals, without learning steps. The memory of a card is its stability (days
until recall falls to 90%) and its difficulty (1 to 10). tests/test_fsrs.py
compares this module with py-fsrs.

The fuzz uses the ranges of py-fsrs, but the day inside a range comes from a
hash of the card and the day of its answer instead of a random number, so the
same log gives the same due dates on every computer. With a presence profile
(the chance of a session on each weekday, presence.py) the day inside the
range is the one nearest to that hash among the days with a good chance.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

DEFAULT_PARAMETERS: tuple[float, ...] = (
    0.212,
    1.2931,
    2.3065,
    8.2956,
    6.4133,
    0.8334,
    3.0194,
    0.001,
    1.8722,
    0.1666,
    0.796,
    1.4835,
    0.0614,
    0.2629,
    1.6483,
    0.6014,
    1.8729,
    0.5425,
    0.0912,
    0.0658,
    0.1542,
)
STABILITY_MIN = 0.001
DIFFICULTY_MIN = 1.0
DIFFICULTY_MAX = 10.0
MAXIMUM_INTERVAL = 36500

# (from, to, share): an interval of `days` may move by 1 day plus the share of
# the days it has in each range, as in py-fsrs; intervals under 2.5 days stay
FUZZ_RANGES = ((2.5, 7.0, 0.15), (7.0, 20.0, 0.1), (20.0, math.inf, 0.05))
# weekdays this close to the best chance of a session in a range count as equally good
PRESENCE_TOLERANCE = 0.2

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
RATINGS = (AGAIN, HARD, GOOD, EASY)

# The initial stabilities (the first four parameters) are fitted to the
# learner's second answers once there are enough of them, as in the
# pretraining step of FSRS; the other parameters keep their defaults.
FIT_MIN_ANSWERS = 40  # second answers in all before any fit
FIT_MIN_PER_RATING = 15  # second answers after one first rating
FIT_RANGE = (0.1, 100.0)  # days of initial stability the search may choose
FIT_PULL = 1 / 16  # loss per day of distance from the default stability


@dataclass(frozen=True)
class Memory:
    """What the scheduler knows about one card."""

    stability: float
    difficulty: float


class Scheduler:
    """FSRS-6 with a desired retention between 0 and 1."""

    def __init__(
        self,
        retention: float = 0.9,
        parameters: tuple[float, ...] = DEFAULT_PARAMETERS,
        maximum_interval: int = MAXIMUM_INTERVAL,
        presence: Sequence[float] | None = None,
    ) -> None:
        if len(parameters) != 21:
            raise ValueError("FSRS-6 takes 21 parameters")
        if not 0 < retention < 1:
            raise ValueError("retention must lie between 0 and 1")
        self.w = parameters
        self.retention = retention
        self.maximum_interval = maximum_interval
        self.decay = -parameters[20]
        self.factor = 0.9 ** (1 / self.decay) - 1
        self.presence = tuple(presence) if presence else None

    def retrievability(self, memory: Memory, elapsed_days: float) -> float:
        """Probability of recall after the given number of days."""
        elapsed = max(0.0, elapsed_days)
        return float((1 + self.factor * elapsed / memory.stability) ** self.decay)

    def interval(self, stability: float) -> int:
        """Whole days until recall falls to the desired retention."""
        days = float((stability / self.factor) * ((self.retention ** (1 / self.decay)) - 1))
        return min(max(round(days), 1), self.maximum_interval)

    def fuzz_range(self, interval: int) -> tuple[int, int]:
        """The shortest and the longest interval a review may get around `interval`."""
        if interval < 2.5:
            return interval, interval
        delta = 1.0
        for start, end, share in FUZZ_RANGES:
            delta += share * max(min(interval, end) - start, 0.0)
        low = max(2, round(interval - delta))
        high = min(round(interval + delta), self.maximum_interval)
        return min(low, high), high

    def due_interval(self, stability: float, key: str, start: date | None = None) -> int:
        """The interval with its spread: the same key always gives the same number of days.

        With a presence profile and the day of the answer (`start`), the days of
        the range with a much lower chance of a session than the best one drop out.
        """
        low, high = self.fuzz_range(self.interval(stability))
        if low == high:
            return low
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        pick = low + int.from_bytes(digest[:8], "big") % (high - low + 1)
        if self.presence is None or start is None:
            return pick
        options = range(low, high + 1)
        chance = {days: self.presence[(start + timedelta(days=days)).weekday()] for days in options}
        best = max(chance.values())
        good = [days for days in options if chance[days] >= best - PRESENCE_TOLERANCE]
        return min(good, key=lambda days: (abs(days - pick), days))

    def first(self, rating: int) -> Memory:
        """Memory after the first answer to a new card."""
        self._check(rating)
        return Memory(
            stability=max(self.w[rating - 1], STABILITY_MIN),
            difficulty=_clamp(self._initial_difficulty(rating)),
        )

    def review(self, memory: Memory, rating: int, elapsed_days: int) -> Memory:
        """Memory after an answer given the number of days after the last one."""
        self._check(rating)
        if elapsed_days < 1:
            stability = self._short_term_stability(memory.stability, rating)
        else:
            r = self.retrievability(memory, elapsed_days)
            if rating == AGAIN:
                stability = self._forget_stability(memory, r)
            else:
                stability = self._recall_stability(memory, r, rating)
        return Memory(
            stability=max(stability, STABILITY_MIN),
            difficulty=self._next_difficulty(memory.difficulty, rating),
        )

    def _check(self, rating: int) -> None:
        if rating not in RATINGS:
            raise ValueError(f"unknown rating {rating}")

    def _initial_difficulty(self, rating: int) -> float:
        return float(self.w[4] - (math.e ** (self.w[5] * (rating - 1))) + 1)

    def _next_difficulty(self, difficulty: float, rating: int) -> float:
        delta = -(self.w[6] * (rating - 3))
        damped = difficulty + (10.0 - difficulty) * delta / 9.0
        reverted = self.w[7] * self._initial_difficulty(EASY) + (1 - self.w[7]) * damped
        return _clamp(reverted)

    def _short_term_stability(self, stability: float, rating: int) -> float:
        increase = float(
            (math.e ** (self.w[17] * (rating - 3 + self.w[18]))) * (stability ** -self.w[19])
        )
        if rating in (HARD, GOOD, EASY):
            increase = max(increase, 1.0)
        return stability * increase

    def _forget_stability(self, memory: Memory, r: float) -> float:
        long_term = (
            self.w[11]
            * (memory.difficulty ** -self.w[12])
            * (((memory.stability + 1) ** (self.w[13])) - 1)
            * (math.e ** ((1 - r) * self.w[14]))
        )
        short_term = memory.stability / (math.e ** (self.w[17] * self.w[18]))
        return float(min(long_term, short_term))

    def _recall_stability(self, memory: Memory, r: float, rating: int) -> float:
        hard_penalty = self.w[15] if rating == HARD else 1
        easy_bonus = self.w[16] if rating == EASY else 1
        return float(
            memory.stability
            * (
                1
                + (math.e ** (self.w[8]))
                * (11 - memory.difficulty)
                * (memory.stability ** -self.w[9])
                * ((math.e ** ((1 - r) * self.w[10])) - 1)
                * hard_penalty
                * easy_bonus
            )
        )


def _clamp(difficulty: float) -> float:
    return min(max(difficulty, DIFFICULTY_MIN), DIFFICULTY_MAX)


def fit_initial(
    points: dict[int, list[tuple[int, bool]]],
    parameters: tuple[float, ...] = DEFAULT_PARAMETERS,
) -> tuple[float, ...]:
    """Parameters whose initial stabilities fit the learner's second answers.

    `points[rating]` lists, for the cards first answered with that rating,
    the days until the second answer and whether it was recalled. A rating
    with too few answers keeps its default, and a better first rating never
    gets a shorter stability than a worse one.
    """
    if sum(len(data) for data in points.values()) < FIT_MIN_ANSWERS:
        return parameters
    decay = -parameters[20]
    factor = 0.9 ** (1 / decay) - 1
    w = list(parameters)
    for rating in RATINGS:
        data = points.get(rating, [])
        if len(data) < FIT_MIN_PER_RATING:
            continue
        groups: dict[int, list[bool]] = defaultdict(list)
        for days, recalled in data:
            groups[max(1, days)].append(recalled)
        default = parameters[rating - 1]

        def loss(
            stability: float, groups: dict[int, list[bool]] = groups, default: float = default
        ) -> float:
            total = abs(stability - default) * FIT_PULL
            for days, outcomes in groups.items():
                predicted = (1 + factor * days / stability) ** decay
                predicted = min(max(predicted, 1e-6), 1 - 1e-6)
                share = sum(outcomes) / len(outcomes)
                total -= math.sqrt(len(outcomes)) * (
                    share * math.log(predicted) + (1 - share) * math.log(1 - predicted)
                )
            return total

        w[rating - 1] = _minimum(loss, *FIT_RANGE)
    for index in range(1, 4):
        w[index] = max(w[index], w[index - 1])
    return tuple(w)


def _minimum(function: Callable[[float], float], low: float, high: float) -> float:
    """Golden-section search for the minimum, on a logarithmic scale of days."""
    ratio = (math.sqrt(5) - 1) / 2
    a, b = math.log(low), math.log(high)
    c, d = b - ratio * (b - a), a + ratio * (b - a)
    fc, fd = function(math.exp(c)), function(math.exp(d))
    for _ in range(80):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - ratio * (b - a)
            fc = function(math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + ratio * (b - a)
            fd = function(math.exp(d))
    return round(math.exp((a + b) / 2), 4)
