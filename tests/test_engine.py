"""The day's queue, the session's guarantees and the replay of the log."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import card_of, correct, make_learner, moment

from vocabbot import progress, session, store
from vocabbot.book import replay
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError
from vocabbot.queue import compute, interleave, split_quota, spread

MONDAY = date(2026, 11, 16)


def learn_day(
    learner: store.Learner, catalog: Catalog, day: date, wrong: set[str] = frozenset()
) -> list[str]:
    """Answer every card of the day: right unless listed in `wrong`, drills right."""
    answered = []
    second = 0
    while True:
        dp = compute(learner, catalog, day)
        if not dp.sequence:
            return answered
        item = dp.sequence[0]
        given = (
            "xxx" if item.card in wrong and item.phase != "drill" else correct(catalog, item.card)
        )
        second += 1
        session.answer(learner, catalog, day, moment(day, second), item.card, given)
        answered.append(item.card)


# ---------------------------------------------------------------- quotas and order


def test_split_quota_follows_weights_and_rotates_ties() -> None:
    weights = {"en": 2, "de": 1, "es": 1}
    totals = [split_quota(15, weights, ordinal) for ordinal in range(4)]
    for quota in totals:
        assert sum(quota.values()) == 15
        assert quota["en"] in (7, 8)
    extras = {code: sum(q[code] for q in totals) for code in weights}
    assert extras["de"] == extras["es"]


def test_interleave_spreads_languages() -> None:
    cards = ["en1", "en2", "en3", "en4", "de1", "de2"]
    lang_of = {c: c[:2] for c in cards}
    assert interleave(cards, lang_of, ["en", "de"]) == ["en1", "de1", "en2", "en3", "de2", "en4"]


def test_spread_keeps_one_family_apart() -> None:
    cards = ["a1", "a2", "b1", "c1", "d1", "e1", "f1"]
    family = {"a1": "a", "a2": "a", "b1": "b", "c1": "c", "d1": "d", "e1": "e", "f1": "f"}
    out = spread(cards, family, 3, [])
    assert out.index("a2") - out.index("a1") >= 3


def test_new_words_respect_quota_and_the_gap_between_languages(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2"], new_per_day=4, sibling_gap_days=3)
    first_day: dict[str, dict[str, date]] = {}
    for offset in range(6):
        day = MONDAY + timedelta(days=offset)
        dp = compute(learner, catalog, day)
        new = list(dp.new)
        assert sum(1 for c in new if c.startswith("de")) == 2
        assert sum(1 for c in new if c.startswith("es")) == 2
        learn_day(learner, catalog, day)
        for card in new:
            entry = catalog.card(card)
            assert entry is not None
            first_day.setdefault(entry["concept"], {})[card[:2]] = day
    for concept, days in first_day.items():
        if len(days) == 2:
            assert abs((days["de"] - days["es"]).days) >= 3, concept


def test_interrupted_day_resumes_in_the_same_order(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2", "fr:a1-a2"], new_per_day=9)
    for offset in range(3):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset))
    day = MONDAY + timedelta(days=3)
    before = [item.card for item in compute(learner, catalog, day).sequence]
    for index, card in enumerate(before[:4]):
        session.answer(learner, catalog, day, moment(day, index), card, correct(catalog, card))
    after = [item.card for item in compute(learner, catalog, day).sequence]
    assert after == before[4:]


def test_known_does_not_use_the_daily_limit(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3)
    first = compute(learner, catalog, MONDAY).new
    session.self_grade(learner, catalog, MONDAY, moment(MONDAY), first[0], "known")
    new = compute(learner, catalog, MONDAY).new
    assert len(new) == 4
    assert new[0] == first[0]
    assert new[1:3] == first[1:]


def test_days_off_move_reviews_to_the_next_day(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3, days_off=["wed"])
    learn_day(learner, catalog, MONDAY)  # due on Wednesday after "know"
    wednesday = compute(learner, catalog, MONDAY + timedelta(days=2))
    assert wednesday.off
    assert not wednesday.sequence
    assert len(wednesday.due) == 3
    thursday = compute(learner, catalog, MONDAY + timedelta(days=3))
    assert len([i for i in thursday.sequence if i.phase == "review"]) == 3


def test_review_limit_moves_the_rest(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=15, review_limit=10)
    learn_day(learner, catalog, MONDAY)
    dp = compute(learner, catalog, MONDAY + timedelta(days=2))
    assert len(dp.reviews) == 10
    assert dp.overflow == 5


def test_extra_words_are_accepted(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    planned = compute(learner, catalog, MONDAY).new
    outside = card_of("de", 10)
    assert outside not in planned
    with pytest.raises(VocabError) as error:
        session.answer(learner, catalog, MONDAY, moment(MONDAY), outside, "der Freund")
    assert error.value.code == "not_in_today"
    session.add_extra(learner, catalog, MONDAY, 8)
    assert outside in compute(learner, catalog, MONDAY).new
    result = session.answer(learner, catalog, MONDAY, moment(MONDAY), outside, "der Freund")
    assert result["grade"] == "know"
    assert result["kind"] == "learn"


# ---------------------------------------------------------------- guarantees of a session


def test_next_never_shows_the_answer_of_a_review(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2"], new_per_day=6)
    learn_day(learner, catalog, MONDAY, wrong={card_of("de", 1)})
    day = MONDAY + timedelta(days=2)
    data = session.next_items(learner, catalog, day, count=50)
    reviews = [item for item in data["items"] if item["phase"] in ("review", "drill")]
    assert reviews
    for item in reviews:
        entry = catalog.card(item["card"])
        assert entry is not None
        text = json.dumps(item, ensure_ascii=False)
        assert entry["display"] not in text
        assert "word" not in item
    new = [item for item in data["items"] if item["phase"] == "new"]
    assert all(item["word"]["word"] for item in new)


def test_drill_leaves_the_schedule_alone(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=1)
    card = compute(learner, catalog, MONDAY).new[0]
    first = session.answer(learner, catalog, MONDAY, moment(MONDAY, 1), card, "xxx")
    assert first["grade"] == "dont_know"
    assert first["drill"]
    for second in range(2, 5):
        again = session.answer(
            learner, catalog, MONDAY, moment(MONDAY, second), card, correct(catalog, card)
        )
        assert again["kind"] == "drill"
        assert again["next_due"] == first["next_due"]
    assert not compute(learner, catalog, MONDAY).drill


def test_refusals(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    card = compute(learner, catalog, MONDAY).new[0]
    session.answer(learner, catalog, MONDAY, moment(MONDAY), card, correct(catalog, card))
    tomorrow = MONDAY + timedelta(days=1)
    cases = [
        (
            lambda: session.answer(learner, catalog, tomorrow, moment(tomorrow), card, "x"),
            "not_due",
        ),
        (
            lambda: session.self_grade(
                learner, catalog, MONDAY + timedelta(days=2), moment(MONDAY), card, "known"
            ),
            "known_only_first",
        ),
        (
            lambda: session.self_grade(learner, catalog, MONDAY, moment(MONDAY), card, "know"),
            "production_needs_answer",
        ),
        (
            lambda: session.answer(
                learner, catalog, MONDAY, moment(MONDAY), "en-c90001#p", "house"
            ),
            "lang_not_in_plan",
        ),
        (
            lambda: session.answer(learner, catalog, MONDAY, moment(MONDAY), "de-c99999#p", "x"),
            "unknown_card",
        ),
        (
            lambda: session.answer(
                learner,
                catalog,
                MONDAY - timedelta(days=1),
                moment(MONDAY),
                card_of("de", 2),
                "der Hund",
            ),
            "day_before_last",
        ),
    ]
    for call, code in cases:
        with pytest.raises(VocabError) as error:
            call()
        assert error.value.code == code


def test_review_ahead_is_marked(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=1)
    card = compute(learner, catalog, MONDAY).new[0]
    session.answer(learner, catalog, MONDAY, moment(MONDAY), card, correct(catalog, card))
    tomorrow = MONDAY + timedelta(days=1)
    result = session.answer(
        learner, catalog, tomorrow, moment(tomorrow), card, correct(catalog, card), ahead=True
    )
    assert result["kind"] == "review"
    assert learner.rows()[0][-1]["ahead"] is True


def test_regrade_changes_the_last_grade_and_is_marked(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=1)
    card = compute(learner, catalog, MONDAY).new[0]
    session.answer(learner, catalog, MONDAY, moment(MONDAY, 1), card, "xxx")
    assert compute(learner, catalog, MONDAY).drill == [card]
    result = session.regrade(learner, catalog, MONDAY, moment(MONDAY, 2), card, "know")
    assert result["was"] == "dont_know"
    dp = compute(learner, catalog, MONDAY)
    assert dp.drill == []
    row = dp.book.rows[-1]
    assert row.grade == "know"
    assert row.regraded
    assert row.auto == "dont_know"
    with pytest.raises(VocabError):
        session.regrade(
            learner, catalog, MONDAY + timedelta(days=1), moment(MONDAY), card, "almost"
        )


def test_wrong_language_is_reported(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2"], new_per_day=2, sibling_gap_days=0)
    dp = compute(learner, catalog, MONDAY)
    card = next(c for c in dp.new if c.startswith("de"))
    entry = catalog.card(card)
    assert entry is not None
    spanish = next(e for e in catalog.family(entry["concept"]) if e["lang"] == "es")
    result = session.answer(learner, catalog, MONDAY, moment(MONDAY), card, spanish["display"])
    assert result["grade"] == "dont_know"
    assert result["other_lang"] == "es"


def test_status_lists_confused_and_recent_words(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2"], new_per_day=4, sibling_gap_days=0)
    card = next(c for c in compute(learner, catalog, MONDAY).new if c.startswith("de"))
    entry = catalog.card(card)
    assert entry is not None
    spanish = next(e for e in catalog.family(entry["concept"]) if e["lang"] == "es")
    result = session.answer(learner, catalog, MONDAY, moment(MONDAY), card, spanish["display"])
    assert result["errors_pl"] == ["słowo z innego języka"]
    assert result["grade_pl"] == "nie wiem"
    report = progress.status(learner, catalog, MONDAY)["languages"]["de"]
    assert report["errors_30_pl"] == {"słowo z innego języka": 1}
    assert report["confusions"][0]["card"] == card
    assert report["confusions"][0]["other_lang"] == "es"
    assert report["confusions"][0]["given"] == spanish["display"]
    # the card waits in today's drill, so the list of recent words leaves it out
    assert card not in {word["card"] for word in report["recent"]}
    learn_day(learner, catalog, MONDAY)
    report = progress.status(learner, catalog, MONDAY)["languages"]["de"]
    assert card in {word["card"] for word in report["recent"]}
    assert all("word" in word and "meaning" in word for word in report["recent"])


def test_lookup_finds_words_and_meanings(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    house = card_of("de", 1)
    assert house in compute(learner, catalog, MONDAY).new
    by_word = session.lookup(learner, catalog, MONDAY, "de", "haus")
    assert by_word["matches"][0]["card"] == house
    assert by_word["matches"][0]["waiting_today"] is True
    by_meaning = session.lookup(None, catalog, None, "de", "dom")
    match = next(m for m in by_meaning["matches"] if m["card"] == house)
    assert match["waiting_today"] is False
    assert match["word"]["word"] == "das Haus"
    assert session.lookup(None, catalog, None, "de", "qqq")["matches"] == []


def test_reveal_serves_recognition_cards_only(catalog: Catalog) -> None:
    with pytest.raises(VocabError) as error:
        session.reveal(catalog, card_of("de", 1))
    assert error.value.code == "reveal_production"
    assert session.reveal(catalog, card_of("de", 1, "r"))["word"]["word"] == "das Haus"


def test_merged_logs_give_the_same_state(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2"], new_per_day=6)
    rng = random.Random(7)
    for offset in range(8):
        day = MONDAY + timedelta(days=offset)
        wrong = {
            item.card for item in compute(learner, catalog, day).sequence if rng.random() < 0.2
        }
        learn_day(learner, catalog, day, wrong=wrong)
    rows = learner.rows()[0]
    halves: list[list[dict]] = [[], []]
    for row in rows:
        halves[rng.randrange(2)].append(row)
    merged = halves[1] + halves[0]
    original, joined = replay(rows), replay(merged)
    assert {k: (v.memory, v.last_day, v.lapses) for k, v in original.cards.items()} == {
        k: (v.memory, v.last_day, v.lapses) for k, v in joined.cards.items()
    }


def test_a_shown_card_never_leaves_the_list(tmp_path: Path, catalog: Catalog) -> None:
    """Marking words as known adds words; every card of the day's list stays on it."""
    learner = make_learner(tmp_path, ["de:a1-a2", "fr:a1-a2", "es:a1-a2"], new_per_day=6)
    first = compute(learner, catalog, MONDAY).new
    for number, card in enumerate(first[:4]):
        session.self_grade(
            learner, catalog, MONDAY, moment(MONDAY, number), card, "known", source="chat"
        )
        now = compute(learner, catalog, MONDAY).new
        assert set(first) <= set(now)
        assert len(now) == len(first) + number + 1


def test_initial_stabilities_follow_the_second_answers() -> None:
    from vocabbot.fsrs import DEFAULT_PARAMETERS, GOOD, fit_initial

    # second answers after "know" recalled even after 12 days: longer initial stability
    points = {GOOD: [(12, True)] * 45 + [(12, False)] * 5}
    fitted = fit_initial(points)
    assert fitted[GOOD - 1] > DEFAULT_PARAMETERS[GOOD - 1] * 2
    assert fitted[:2] == DEFAULT_PARAMETERS[:2]  # too few answers for the other ratings
    assert fitted[3] >= fitted[2]  # a better first rating never gets a shorter stability
    assert fitted[4:] == DEFAULT_PARAMETERS[4:]
    # forgotten after two days: shorter
    assert fit_initial({GOOD: [(2, False)] * 30 + [(2, True)] * 20})[GOOD - 1] < 2.3065
    # too few second answers in all: the defaults stay
    assert fit_initial({GOOD: [(5, True)] * 20}) == DEFAULT_PARAMETERS
