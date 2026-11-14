"""Thirty days of three languages on the starter course, run twice."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from conftest import correct, make_learner, moment

from vocabbot import session, store
from vocabbot.courses import Catalog
from vocabbot.queue import compute

START = date(2026, 11, 16)


def chance(card: str, day: date, tries: int) -> float:
    digest = hashlib.sha256(f"{card}|{day}|{tries}".encode()).hexdigest()
    return int(digest[:8], 16) / 0x100000000


def simulate(root: Path, catalog: Catalog) -> tuple[bytes, dict[str, dict[str, date]]]:
    learner = make_learner(
        root, ["en:a1-a2:2", "de:a1-a2", "es:a1-a2"], new_per_day=12, days_off=["sun"]
    )
    first_day: dict[str, dict[str, date]] = defaultdict(dict)
    for offset in range(30):
        day = START + timedelta(days=offset)
        tries: dict[str, int] = defaultdict(int)
        second = 0
        dp = compute(learner, catalog, day)
        if dp.off:
            assert not dp.sequence
            continue
        planned = list(dp.new)
        new_today: dict[str, int] = defaultdict(int)
        while dp.sequence:
            item = dp.sequence[0]
            tries[item.card] += 1
            assert tries[item.card] < 20, item
            right = chance(item.card, day, tries[item.card]) < (
                0.75 if item.phase != "drill" else 0.9
            )
            second += 1
            result = session.answer(
                learner,
                catalog,
                day,
                moment(day, second),
                item.card,
                correct(catalog, item.card) if right else "xyz",
            )
            if result["kind"] == "learn":
                new_today[item.lang] += 1
                entry = catalog.card(item.card)
                assert entry is not None
                first_day[entry["concept"]][item.lang] = day
            dp = compute(learner, catalog, day)
            assert dp.new == planned, day  # answers never change the day's list
        assert sum(new_today.values()) <= 12, (day, dict(new_today))
    return learner.path(store.REVIEWS).read_bytes(), first_day


def test_thirty_days_three_languages(tmp_path: Path, catalog: Catalog) -> None:
    log_a, first_a = simulate(tmp_path / "a", catalog)
    log_b, _ = simulate(tmp_path / "b", catalog)
    assert log_a == log_b
    rows = [line for line in log_a.decode("utf-8").splitlines() if line]
    assert len(rows) > 500
    for concept, days in first_a.items():
        langs = sorted(days)
        for i, a in enumerate(langs):
            for b in langs[i + 1 :]:
                assert abs((days[a] - days[b]).days) >= 3, (concept, days)
    learner = store.Learner(tmp_path / "a")
    final = compute(learner, catalog, START + timedelta(days=30))
    assert len(final.before.cards) == 180
