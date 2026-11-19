"""Stage 5: the full fit, the replay against FSRS-6 and the plan by presence."""

from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import make_learner

from vocabbot import optimize, plans, presence, progress, replay, session, store
from vocabbot.book import RATING, ParameterSet, fitted_replay
from vocabbot.book import replay as replay_log
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError
from vocabbot.fsrs import DEFAULT_PARAMETERS, Scheduler
from vocabbot.queue import compute

START = date(2026, 9, 7)  # a Monday
FORGETFUL = (0.1, 0.6, 1.0, 4.0, *DEFAULT_PARAMETERS[4:])


def weekdays_only(day: date) -> bool:
    return day.weekday() < 5


def write_log(
    root: Path,
    catalog: Catalog,
    days: int,
    present=weekdays_only,  # type: ignore[no-untyped-def]
    truth: Scheduler | None = None,
    per_day: int = 6,
    seed: int = 7,
) -> list[dict]:
    """A synthetic learner: reviews on the days they are present, new words after them."""
    truth = truth or Scheduler(parameters=FORGETFUL)
    rng = random.Random(seed)
    cards = [
        f"{entry['id']}#{direction}"
        for lang in ("de", "fr")
        for entry in catalog.course(lang, ["a1", "a2"])
        for direction in ("p", "r")
    ]
    rng.shuffle(cards)
    pool = iter(cards)
    state: dict[str, tuple] = {}
    rows = []
    second = 0
    for offset in range(days):
        day = START + timedelta(days=offset)
        if not present(day):
            continue

        def add(card: str, grade: str, kind: str, ms: int, day: date = day) -> None:
            nonlocal second
            second += 1
            rows.append(
                {
                    "ts": f"{day.isoformat()}T10:{second // 60 % 60:02d}:{second % 60:02d}.000000Z",
                    "day": day.isoformat(),
                    "card": card,
                    "lang": card[:2],
                    "grade": grade,
                    "kind": kind,
                    "source": "chat",
                    "ms": ms,
                }
            )

        for card in sorted(c for c, (_, _, due) in state.items() if due <= day):
            memory, last, _ = state[card]
            elapsed = (day - last).days
            grade = "know" if rng.random() < truth.retrievability(memory, elapsed) else "dont_know"
            add(card, grade, "review", 9000)
            memory = truth.review(memory, RATING[grade], elapsed)
            state[card] = (memory, day, day + timedelta(days=truth.interval(memory.stability)))
        for _ in range(per_day):
            card = next(pool, None)
            if card is None:
                break
            grade = rng.choice(["know", "know", "almost", "dont_know"])
            add(card, grade, "learn", 20000)
            memory = truth.first(RATING[grade])
            state[card] = (memory, day, day + timedelta(days=truth.interval(memory.stability)))
    log = root / store.REVIEWS
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_bytes("".join(json.dumps(r) + "\n" for r in rows).encode("utf-8"))
    return rows


# ---------------------------------------------------------------- the fit


def histories(truth: Scheduler, cards: int, seed: int) -> list[list[optimize.Answer]]:
    rng = random.Random(seed)
    out = []
    for _ in range(cards):
        rating = rng.choice([1, 2, 3, 3, 3, 4])
        memory = truth.first(rating)
        history = [optimize.Answer(rating, 0, rating != 1)]
        for _ in range(rng.randint(2, 7)):
            days = max(1, round(truth.interval(memory.stability) * rng.uniform(0.6, 1.6)))
            recalled = rng.random() < truth.retrievability(memory, days)
            rating = rng.choice([2, 3, 3, 3, 4]) if recalled else 1
            history.append(optimize.Answer(rating, days, recalled))
            memory = truth.review(memory, rating, days)
        out.append(history)
    return out


def test_the_differentiable_model_matches_the_scheduler() -> None:
    rng = random.Random(1)
    scheduler = Scheduler()
    model = optimize.Model([optimize.Var(p) for p in DEFAULT_PARAMETERS])
    for _ in range(50):
        rating = rng.randint(1, 4)
        memory = scheduler.first(rating)
        s, d = model.first(rating)
        for _ in range(6):
            days, rating = rng.randint(1, 60), rng.randint(1, 4)
            assert model.recall(s, days).value == pytest.approx(
                scheduler.retrievability(memory, days), abs=1e-9
            )
            memory = scheduler.review(memory, rating, days)
            s, d = model.review(s, d, rating, days)
            assert s.value == pytest.approx(memory.stability, rel=1e-9)
            assert d.value == pytest.approx(memory.difficulty, rel=1e-9)


def test_gradients_match_finite_differences() -> None:
    def loss_with(params: list[float]) -> tuple[optimize.Var, list[optimize.Var]]:
        w = [optimize.Var(p) for p in params]
        model = optimize.Model(w)
        s, d = model.first(3)
        terms = []
        for days, rating, recalled in [(3, 3, True), (9, 1, False), (2, 3, True), (40, 2, True)]:
            p = optimize.clamp(model.recall(s, days), 1e-7, 1 - 1e-7)
            terms.append(-optimize.log(p) if recalled else -optimize.log(1.0 - p))
            s, d = model.review(s, d, rating, days)
        return optimize.total(terms), w

    root, w = loss_with(list(DEFAULT_PARAMETERS))
    optimize.backward(root)
    for i in range(21):
        up, down = list(DEFAULT_PARAMETERS), list(DEFAULT_PARAMETERS)
        up[i] += 1e-6
        down[i] -= 1e-6
        numeric = (loss_with(up)[0].value - loss_with(down)[0].value) / 2e-6
        assert w[i].grad == pytest.approx(numeric, abs=1e-6), i


def test_the_fit_needs_512_reviews_and_then_predicts_better() -> None:
    # a learner whose memory grows slower than FSRS-6 expects (w8) and starts weaker
    slower = list(FORGETFUL)
    slower[8] = 1.4
    truth = Scheduler(parameters=tuple(slower))
    assert optimize.fit(histories(truth, 50, 1)) is None
    train, test = histories(truth, 500, 7), histories(truth, 300, 8)
    fitted = optimize.fit(train)
    assert fitted is not None and len(fitted) == 21
    assert all(
        lo <= v <= hi for v, lo, hi in zip(fitted, optimize.LOWER, optimize.UPPER, strict=True)
    )
    assert optimize.loss(test, fitted) < optimize.loss(test, DEFAULT_PARAMETERS)
    assert optimize.fit(train) == fitted  # the same log gives the same parameters


# ---------------------------------------------------------------- the scores


def prediction(p: float, recalled: bool, days: int = 3) -> replay.Prediction:
    return replay.Prediction("de", days, 2, 0, recalled, p)


def test_scores_follow_their_definitions() -> None:
    made = [prediction(0.9, True), prediction(0.8, False), prediction(0.6, True)]
    expected = -(math.log(0.9) + math.log(0.2) + math.log(0.6)) / 3
    assert replay.log_loss(made) == pytest.approx(expected)
    assert replay.auc(made) == pytest.approx(0.5)  # the forgotten one sits between the two
    assert replay.auc([prediction(0.9, True), prediction(0.2, False)]) == 1.0
    assert replay.auc([prediction(0.9, True)]) is None
    # one bin: recall 2/3 against a mean prediction of 0.7667
    assert replay.rmse_bins(made) == pytest.approx(abs(2 / 3 - 2.3 / 3))
    spread = [prediction(0.9, True, days=1), prediction(0.5, False, days=30)]
    assert replay.rmse_bins(spread) == pytest.approx(math.sqrt((0.1**2 + 0.5**2) / 2))


def test_the_replay_of_fsrs6_follows_the_engine(tmp_path: Path, catalog: Catalog) -> None:
    rows = write_log(tmp_path, catalog, 42)
    book = replay_log(rows)
    made = replay.predict(replay.histories(book), lambda lang: DEFAULT_PARAMETERS)
    assert len(made) == sum(1 for row in book.rows if row.kind == "review")
    scheduler = Scheduler()
    _, (_, answers) = next(iter(replay.histories(book).items()))
    memory = scheduler.first(answers[0][1].rating)
    first_review = answers[1][1]
    expected = scheduler.retrievability(memory, first_review.days)
    assert any(x.p == pytest.approx(expected) for x in made)


def test_compare_scores_every_variant_on_the_later_part(tmp_path: Path, catalog: Catalog) -> None:
    rows = write_log(tmp_path, catalog, 56)
    result = replay.compare(rows)
    assert result["test_reviews"] + result["train_reviews"] == result["reviews"]
    assert result["test_reviews"] >= replay.MIN_TEST and result["enough"]
    names = {v["name"]: v for v in result["variants"]}
    assert set(names) == {"fsrs6", "initial", "fit", "fit_lang"}
    assert names["fsrs6"]["available"] and names["fsrs6"]["scores"]["reviews"] > 0
    for variant in names.values():
        if variant["available"]:
            assert variant["scores"]["reviews"] == result["test_reviews"]
            assert set(variant["languages"]) == {"de", "fr"}
            assert "log_loss" in variant["delta"]
    assert names["fsrs6"]["delta"]["log_loss"] == 0
    assert result["best"] in names
    short = replay.compare(write_log(tmp_path / "short", catalog, 21))
    fit = {v["name"]: v for v in short["variants"]}["fit"]
    assert not fit["available"] and fit["reviews"] < optimize.MIN_REVIEWS
    assert "groups" not in names["fsrs6"]  # without the courses' concepts


def test_compare_scores_cards_known_in_another_language_apart(
    tmp_path: Path, catalog: Catalog
) -> None:
    rows = write_log(tmp_path, catalog, 56)

    def concept_of(card: str) -> str | None:
        entry = catalog.card(card)
        return str(entry["concept"]) if entry else None

    result = replay.compare(rows, concept_of=concept_of)
    book = replay_log(rows)
    since = date.fromisoformat(result["since"])
    first: dict[tuple[str, str], date] = {}
    for row in book.rows:
        if row.kind == "learn":
            first.setdefault((concept_of(row.card) or "", row.lang), row.day)
    # the reviews of the later part whose concept had a first answer in the other language
    expected = sum(
        1
        for row in book.rows
        if row.kind == "review"
        and row.day >= since
        and any(
            lang != row.lang and day <= row.day
            for (concept, lang), day in first.items()
            if concept == concept_of(row.card)
        )
    )
    assert 0 < expected < result["test_reviews"]
    for variant in result["variants"]:
        if not variant["available"]:
            continue
        groups = variant["groups"]
        assert groups["sibling"]["reviews"] == expected
        assert groups["sibling"]["reviews"] + groups["alone"]["reviews"] == result["test_reviews"]
    plain = replay.compare(rows)
    # the split changes no score of the whole
    for with_groups, without in zip(result["variants"], plain["variants"], strict=True):
        assert with_groups.get("scores") == without.get("scores")


# ---------------------------------------------------------------- presence


def test_the_profile_comes_from_the_days_of_the_log(tmp_path: Path, catalog: Catalog) -> None:
    rows = write_log(tmp_path, catalog, 56)
    book = replay_log(rows)
    found = presence.profile(book.rows, START + timedelta(days=56))
    assert found is not None
    assert min(found.weekdays[:5]) > 0.9 and max(found.weekdays[5:]) < 0.2
    assert found.minutes is not None and found.minutes > 1
    assert presence.profile(book.rows, START + timedelta(days=10)) is None  # under two weeks


def test_due_dates_avoid_the_days_the_learner_skips() -> None:
    plain = Scheduler()
    weekend_away = Scheduler(presence=(0.95,) * 5 + (0.1, 0.1))
    everyday = Scheduler(presence=(0.9,) * 7)
    friday = date(2026, 11, 13)
    for n in range(300):
        key = f"de-c{n:05d}#p|{friday}"
        days = weekend_away.due_interval(20.0, key, friday)
        assert (friday + timedelta(days=days)).weekday() < 5
        low, high = plain.fuzz_range(plain.interval(20.0))
        assert low <= days <= high
        # equal chances keep the plain spread
        assert everyday.due_interval(20.0, key, friday) == plain.due_interval(20.0, key, friday)


def test_pacing_keeps_the_day_within_the_usual_minutes() -> None:
    per_card = {"review": 10.0, "new": 25.0}
    assert presence.paced(15, 10, 10.0, per_card) == 15  # 10 reviews and 15 words fit in 12.5 min
    assert presence.paced(15, 60, 10.0, per_card) == 6
    assert presence.paced(15, 200, 10.0, per_card) == 0


def test_the_day_plans_by_presence(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2"], new_per_day=6)
    write_log(tmp_path, catalog, 54)
    friday = START + timedelta(days=53)
    assert friday.weekday() == 4
    dp = compute(learner, catalog, friday)
    assert dp.presence is not None
    summary = session.summary(learner, catalog, dp)
    hint = summary.get("ahead_hint")
    if dp.due_tomorrow:
        assert hint == {
            "day": (friday + timedelta(days=1)).isoformat(),
            "count": min(dp.due_tomorrow, presence.AHEAD_MAX),
            "reason": "usually_skipped",
        }
    off = make_learner(tmp_path / "off", ["de:a1-a2", "fr:a1-a2"], new_per_day=6, presence="off")
    write_log(tmp_path / "off", catalog, 54)
    assert compute(off, catalog, friday).presence is None


def test_presence_lowers_the_backlog_after_days_away(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2"], new_per_day=6)
    write_log(tmp_path, catalog, 56)
    result = progress.workload(learner, catalog, START + timedelta(days=56), days=28)
    by_name = {v["name"]: v for v in result["variants"]}
    plain, aware = by_name["fsrs6"], by_name["fsrs6_presence"]
    assert aware["late_share"] < plain["late_share"]
    assert aware["recall"] >= result["target_retention"] - 0.03


# ---------------------------------------------------------------- the plan


def test_plan_parameters_are_checked() -> None:
    assert store.parameter_problems({}) == []
    assert store.parameter_problems({"de": list(DEFAULT_PARAMETERS)}) == []
    assert store.parameter_problems({"de": [1.0] * 20})
    assert store.parameter_problems({"de": [500.0, *DEFAULT_PARAMETERS[1:]]})


def test_plan_parameters_apply_to_their_language(tmp_path: Path, catalog: Catalog) -> None:
    rows = write_log(tmp_path, catalog, 42)
    own = {"de": list(FORGETFUL)}
    book = fitted_replay(rows, own)
    assert book.parameters.for_lang("de") == FORGETFUL
    assert book.parameters.for_lang("fr") != FORGETFUL
    assert ParameterSet.of_plan(own).languages == (("de", FORGETFUL),)


def test_plan_fit_needs_a_better_prediction(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2"], new_per_day=6)
    write_log(tmp_path, catalog, 21)
    with pytest.raises(VocabError) as caught:
        plans.fit_preview(learner, catalog, session.now_utc())
    assert caught.value.code == "no_better_fit"
    plan = learner.plan()
    plan["parameters"] = {"de": list(FORGETFUL)}
    store.write_text(learner.path(store.PLAN), store.dump_json(plan))
    preview = plans.set_preview(learner, catalog, ["parameters=default"], session.now_utc())
    assert any("parameters: de → FSRS-6" in line for line in preview["preview"])
    with pytest.raises(VocabError):
        plans.set_preview(learner, catalog, ["parameters=yes"], session.now_utc())
    preview = plans.set_preview(learner, catalog, ["presence=off"], session.now_utc())
    assert any("presence: on → off" in line for line in preview["preview"])
