"""Thirty days of three languages on the starter course, run twice."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from conftest import correct, make_learner, moment

from vocabbot import progress, session, store
from vocabbot.book import replay
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


# Spanish cards the scripted learner answers in French: one letter away (near) or far (hard)
SLIPS = {"es-c90031#p": "grand", "es-c90059#p": "facile", "es-c90020#p": "la main"}
NEAR = {"es-c90031#p", "es-c90059#p"}


def simulate_slips(root: Path, catalog: Catalog) -> tuple[store.Learner, dict[str, int]]:
    """Thirty days of Spanish and French; some Spanish cards get the French word at times."""
    learner = make_learner(root, ["es:a1-a2", "fr:a1-a2"], new_per_day=8, sibling_gap_days=0)
    placed = {"near": 0, "hard": 0, "typed": 0}
    for offset in range(30):
        day = START + timedelta(days=offset)
        tries: dict[str, int] = defaultdict(int)
        second = 0
        dp = compute(learner, catalog, day)
        while dp.sequence:
            item = dp.sequence[0]
            tries[item.card] += 1
            assert tries[item.card] < 20, item
            roll = chance(item.card, day, tries[item.card])
            if item.card in SLIPS and item.phase != "drill" and roll < 0.6:
                given = SLIPS[item.card]
                placed["near" if item.card in NEAR else "hard"] += 1
            else:
                given = correct(catalog, item.card) if roll < 0.85 else "xyz"
            placed["typed"] += 1
            second += 1
            session.answer(learner, catalog, day, moment(day, second), item.card, given)
            dp = compute(learner, catalog, day)
    return learner, placed


def test_thirty_days_count_every_mix_up_and_move_no_date(tmp_path: Path, catalog: Catalog) -> None:
    learner, placed = simulate_slips(tmp_path, catalog)
    log = learner.path(store.REVIEWS).read_bytes()
    assert placed["near"] >= 3 and placed["hard"] >= 1
    last = START + timedelta(days=29)
    report = progress.status(learner, catalog, last)["languages"]
    counted = {
        key: sum(lang["mixups_30"][key] for lang in report.values())
        for key in ("near", "hard", "typed")
    }
    assert counted == placed
    rows = [json.loads(line) for line in log.decode("utf-8").splitlines()]
    for row in rows:
        if row["card"] in NEAR and row.get("given") == SLIPS[row["card"]]:
            assert (row["grade"], row["error"], row["other_lang"]) == ("almost", "typo", "fr")
    # the language of a slip is a record only: without it every card has the same state
    stripped = [{k: v for k, v in r.items() if k != "other_lang"} for r in rows]
    assert replay(rows).cards == replay(stripped).cards


# ---------------------------------------------------------------- learning by families (Stage 14b)


def simulate_families(
    root: Path,
    catalog: Catalog,
    days: int = 30,
    *,
    together: tuple[str, ...] = ("es", "fr"),
    switch_on: int = 0,
    slips: bool = True,
) -> tuple[store.Learner, dict[str, int], dict[str, dict[str, date]]]:
    """Spanish and French by families, English on its own; some slips into French.

    With `switch_on` the set starts on that day; before it every language is on
    its own. Returns the learner, the placed mix-ups and the first day of every
    concept in every language.
    """
    learner = make_learner(
        root,
        ["es:a1-a2", "fr:a1-a2", "en:a1-a2"],
        new_per_day=6,
        days_off=["sun"],
        together=list(together) if not switch_on else [],
    )
    placed = {"near": 0, "hard": 0, "typed": 0}
    first_day: dict[str, dict[str, date]] = defaultdict(dict)
    for offset in range(days):
        day = START + timedelta(days=offset)
        if switch_on and offset == switch_on:
            plan = learner.plan()
            plan["together"] = list(together)
            store.write_text(learner.path(store.PLAN), store.dump_json(plan))
            learner.forget()
        tries: dict[str, int] = defaultdict(int)
        second = 0
        dp = compute(learner, catalog, day)
        if dp.off:
            assert not dp.sequence
            continue
        planned = list(dp.new)
        while dp.sequence:
            item = dp.sequence[0]
            tries[item.card] += 1
            assert tries[item.card] < 20, item
            roll = chance(item.card, day, tries[item.card])
            if slips and item.card in SLIPS and item.phase != "drill" and roll < 0.6:
                given = SLIPS[item.card]
                placed["near" if item.card in NEAR else "hard"] += 1
            else:
                right = roll < (0.75 if item.phase != "drill" else 0.9)
                given = correct(catalog, item.card) if right else "xyz"
            placed["typed"] += 1
            second += 1
            result = session.answer(learner, catalog, day, moment(day, second), item.card, given)
            if result["kind"] == "learn":
                entry = catalog.card(item.card)
                assert entry is not None
                first_day[entry["concept"]][item.lang] = day
            dp = compute(learner, catalog, day)
            assert dp.new == planned, day  # answers never change the day's list
        assert len(planned) <= 6, (day, planned)
    return learner, placed, first_day


def test_thirty_days_by_families(tmp_path: Path, catalog: Catalog) -> None:
    """S2 and S3: the same log twice, whole families, the gap outside the set, every slip."""
    learner, placed, first_a = simulate_families(tmp_path / "a", catalog)
    again, _, _ = simulate_families(tmp_path / "b", catalog)
    log = learner.path(store.REVIEWS).read_bytes()
    assert log == again.path(store.REVIEWS).read_bytes()
    rows = [json.loads(line) for line in log.decode("utf-8").splitlines()]
    assert len(rows) > 400
    together = 0
    for concept, days in first_a.items():
        if "es" in days and "fr" in days:
            assert days["es"] == days["fr"], (concept, days)  # a family enters together
            together += 1
        for code in ("es", "fr"):
            if "en" in days and code in days:
                assert abs((days["en"] - days[code]).days) >= 3, (concept, days)
    assert together >= 20
    reviews = defaultdict(int)
    for row in rows:
        if row["kind"] == "review":
            reviews[(row["day"], row["card"])] += 1
    assert max(reviews.values()) == 1  # no card twice on one day
    assert sum(1 for row in rows if row.get("ahead")) > 0  # families joined their due cards
    # S3: every slip is counted, and its language moves no date
    last = START + timedelta(days=29)
    report = progress.status(learner, catalog, last)
    counted = {
        key: sum(lang["mixups_30"][key] for lang in report["languages"].values())
        for key in ("near", "hard", "typed")
    }
    assert counted == placed and placed["near"] > 0
    stripped = [{k: v for k, v in r.items() if k != "other_lang"} for r in rows]
    assert replay(rows).cards == replay(stripped).cards
    families_report = report["families"]
    assert families_report["together"] == ["es", "fr"] and families_report["blocks_30"] > 0


def test_switching_to_families_completes_them_first(tmp_path: Path, catalog: Catalog) -> None:
    """S4: fifteen days apart, then fifteen by families; nothing of the log is lost."""
    learner, placed, first = simulate_families(tmp_path, catalog, switch_on=15, slips=False)
    switch = START + timedelta(days=15)
    rows = learner.rows()[0]
    assert len(rows) == placed["typed"]
    learned = [row for row in rows if row["kind"] == "learn"]
    per_day = defaultdict(int)
    for row in learned:
        per_day[row["day"]] += 1
    assert max(per_day.values()) <= 6 + 2  # the limit and the words known before
    # after the switch a language takes the families it has not met before new concepts;
    # only the gap towards English, outside the set, may hold a family back for a while
    held: set[tuple[str, str]] = set()
    total = 0
    for code, other in (("es", "fr"), ("fr", "es")):
        waiting = [
            name
            for name, days in first.items()
            if other in days and days[other] < switch and days.get(code, switch) >= switch
        ]
        assert waiting, code
        total += len(waiting)
        for name in waiting:
            done = first[name].get(code)
            assert done is not None, (code, name)  # every family is completed
            for new_name, days in first.items():
                taken = days.get(code)
                if new_name in waiting or taken is None or not switch <= taken < done:
                    continue
                english = first[name].get("en")
                assert english is not None and (taken - english).days < 3, (code, name, new_name)
                held.add((code, name))
    assert len(held) < total  # some families wait for the gap, the others come first


def test_the_load_by_families_is_forecast_and_run(tmp_path: Path, catalog: Catalog) -> None:
    """S5: the same log forecast and run for 28 days apart and by families."""
    base, _, _ = simulate_families(tmp_path / "base", catalog, days=14, together=(), slips=False)
    day = START + timedelta(days=14)
    apart = progress.forecast(base, catalog, day, 28)
    plan = {**base.plan(), "together": ["es", "fr"]}
    by_families = progress.forecast(base, catalog, day, 28, plan=plan)
    assert "joined_share" not in apart and by_families["joined_share"] > 0
    for result in (apart, by_families):
        assert len(result["days"]) == 28 and result["average_reviews"] > 0
    print(
        "S5 forecast apart:",
        apart["average_reviews"],
        apart["average_minutes"],
        "by families:",
        by_families["average_reviews"],
        by_families["average_minutes"],
        by_families["joined_share"],
    )
