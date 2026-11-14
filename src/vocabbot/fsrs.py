"""FSRS-6 spaced-repetition scheduler, standard library only.

A port of the scheduler in py-fsrs 6.3.3 (MIT, see NOTICE) for whole-day
intervals, without learning steps and without fuzz. The memory of a card is
its stability (days until recall falls to 90%) and its difficulty (1 to 10).
tests/test_fsrs.py compares this module with py-fsrs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
RATINGS = (AGAIN, HARD, GOOD, EASY)


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

    def retrievability(self, memory: Memory, elapsed_days: float) -> float:
        """Probability of recall after the given number of days."""
        elapsed = max(0.0, elapsed_days)
        return float((1 + self.factor * elapsed / memory.stability) ** self.decay)

    def interval(self, stability: float) -> int:
        """Whole days until recall falls to the desired retention."""
        days = float((stability / self.factor) * ((self.retention ** (1 / self.decay)) - 1))
        return min(max(round(days), 1), self.maximum_interval)

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
