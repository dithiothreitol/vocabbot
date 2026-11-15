"""The scheduler against py-fsrs 6.3.3: saved vectors and random rating sequences."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vocabbot.fsrs import AGAIN, EASY, GOOD, HARD, Memory, Scheduler

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "fsrs_vectors.json").read_text("utf-8"))


def replay(scheduler: Scheduler, rows: list[dict]) -> list[tuple[float, float, int]]:
    memory: Memory | None = None
    out = []
    for row in rows:
        if memory is None:
            memory = scheduler.first(row["grade"])
        else:
            memory = scheduler.review(memory, row["grade"], row["elapsed"])
        out.append((memory.stability, memory.difficulty, scheduler.interval(memory.stability)))
    return out


@pytest.mark.parametrize("retention", sorted(VECTORS))
def test_saved_vectors(retention: str) -> None:
    scheduler = Scheduler(retention=float(retention))
    for name, rows in VECTORS[retention].items():
        got = replay(scheduler, rows)
        for row, (s, d, interval) in zip(rows, got, strict=True):
            assert s == pytest.approx(row["s"], abs=1e-6), name
            assert d == pytest.approx(row["d"], abs=1e-6), name
            assert interval == row["interval"], name


def test_random_sequences_match_py_fsrs() -> None:
    fsrs = pytest.importorskip("fsrs")
    rng = random.Random(20261114)
    for _ in range(200):
        retention = rng.choice([0.8, 0.85, 0.9, 0.93, 0.95])
        ref = fsrs.Scheduler(
            desired_retention=retention,
            learning_steps=(),
            relearning_steps=(),
            enable_fuzzing=False,
        )
        ours = Scheduler(retention=retention)
        card = fsrs.Card()
        now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        memory: Memory | None = None
        for step in range(rng.randint(1, 12)):
            grade = rng.choice([AGAIN, HARD, GOOD, GOOD, GOOD, EASY])
            if step:
                gap = rng.choice(["due", "due", "early", "late", "same"])
                interval = (card.due - card.last_review).days
                if gap == "due":
                    elapsed = interval
                elif gap == "early":
                    elapsed = rng.randint(1, max(1, interval))
                elif gap == "late":
                    elapsed = interval + rng.randint(1, 3 * interval + 5)
                else:
                    elapsed = 0
                now = card.last_review + timedelta(days=elapsed)
            card, _ = ref.review_card(card, fsrs.Rating(grade), review_datetime=now)
            memory = ours.first(grade) if memory is None else ours.review(memory, grade, elapsed)
            assert memory.stability == pytest.approx(card.stability, abs=1e-6)
            assert memory.difficulty == pytest.approx(card.difficulty, abs=1e-6)
            assert ours.interval(memory.stability) == (card.due - now).days


def test_retrievability_is_ninety_percent_after_stability_days() -> None:
    scheduler = Scheduler()
    memory = Memory(stability=12.5, difficulty=5.0)
    assert scheduler.retrievability(memory, 12.5) == pytest.approx(0.9)


def test_lower_retention_gives_longer_intervals() -> None:
    assert Scheduler(retention=0.85).interval(10) > Scheduler(retention=0.9).interval(10)
    assert Scheduler(retention=0.95).interval(10) < Scheduler(retention=0.9).interval(10)


def test_bad_input_is_refused() -> None:
    with pytest.raises(ValueError, match="retention"):
        Scheduler(retention=1.0)
    with pytest.raises(ValueError, match="rating"):
        Scheduler().first(5)
    assert HARD == 2


def test_fuzz_ranges_follow_py_fsrs() -> None:
    scheduler = Scheduler()
    assert scheduler.fuzz_range(1) == (1, 1)
    assert scheduler.fuzz_range(2) == (2, 2)
    assert scheduler.fuzz_range(3) == (2, 4)
    assert scheduler.fuzz_range(10) == (8, 12)  # 1 + 0.15 * 4.5 + 0.1 * 3 = 1.975 days
    assert scheduler.fuzz_range(100) == (93, 107)


def test_spread_is_the_same_for_the_same_card_and_day() -> None:
    scheduler = Scheduler()
    stability = 40.0
    low, high = scheduler.fuzz_range(scheduler.interval(stability))
    days = {scheduler.due_interval(stability, f"de-c{n:05d}#p|2026-11-15") for n in range(200)}
    assert days <= set(range(low, high + 1)) and len(days) > 3
    assert scheduler.due_interval(stability, "de-c00001#p|2026-11-15") == scheduler.due_interval(
        stability, "de-c00001#p|2026-11-15"
    )
    assert scheduler.due_interval(0.5, "any") == scheduler.interval(0.5)
