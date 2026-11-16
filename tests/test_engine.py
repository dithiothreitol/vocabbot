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


def test_the_level_hint_comes_once_a_day_for_the_present_levels(catalog: Catalog) -> None:
    def row(number: int, grade: str, day: str) -> dict[str, str]:
        return {
            "card": card_of("en", number),
            "lang": "en",
            "kind": "learn",
            "grade": grade,
            "day": day,
        }

    plan = {"languages": [{"code": "en", "levels": ["a1", "a2"]}]}
    monday, tuesday = date(2026, 11, 16), date(2026, 11, 17)
    rows: list[dict[str, str]] = []
    hints = []
    # three of four words known, typed answers between them: the share hovers over the mark
    for number in range(1, 21):
        grade = "know" if number % 4 == 0 else "known"
        rows.append(row(number, grade, monday.isoformat()))
        hints.append(session.level_hint(rows, catalog, "en", plan, monday))
    given = [i for i, hint in enumerate(hints) if hint]
    assert given == [9]  # the tenth word, a typed answer, reaches 8 of 10; once that day
    assert hints[9] == {
        "lang": "en",
        "known": 8,
        "of": 10,
        "levels": "a1-a2",
        "suggested": "a2",
        "setting": "lang.en.levels=a2",
    }
    # the next day the first word over the mark brings it again: 7 of 10, then 8 of 10
    rows.append(row(21, "known", tuesday.isoformat()))
    assert session.level_hint(rows, catalog, "en", plan, tuesday) is None
    rows.append(row(22, "known", tuesday.isoformat()))
    assert session.level_hint(rows, catalog, "en", plan, tuesday) is not None
    # after the change to A2 the A1 words do not count: ten A2 words are needed first
    higher = {"languages": [{"code": "en", "levels": ["a2"]}]}
    assert session.level_hint(rows, catalog, "en", higher, tuesday) is None
    a2 = [row(40 + n, "known", tuesday.isoformat()) for n in range(1, 11)]
    assert session.level_hint([*rows, *a2], catalog, "en", higher, tuesday)["suggested"] == "b1"
    top = {"languages": [{"code": "en", "levels": ["b2"]}]}
    assert session.level_hint(rows, catalog, "en", top, tuesday) is None


# ---------------------------------------------------------------- stages and more cards


def test_the_learner_chooses_the_stage(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3)
    learn_day(learner, catalog, MONDAY)
    day = MONDAY + timedelta(days=2)
    due = compute(learner, catalog, day).reviews
    assert len(due) == 3

    usual = session.next_items(learner, catalog, day, count=1)
    assert usual["stage"] == "reviews" and usual["items"][0]["phase"] == "review"
    chosen = session.next_items(learner, catalog, day, count=1, stage="new")
    assert chosen["stage"] == "new" and chosen["items"][0]["phase"] == "new"
    assert "stage_empty" not in chosen
    assert chosen["left"] == {"reviews": 3, "new": 3, "drill": 0}

    # the new words are answered while the reviews wait; a wrong one goes to the drill
    new = [i["card"] for i in session.next_items(learner, catalog, day, stage="new")["items"][:3]]
    for second, card in enumerate(new):
        given = "xxx" if second == 0 else correct(catalog, card)
        result = session.answer(learner, catalog, day, moment(day, second), card, given)
        assert session.KIND_STAGE[result["kind"]] == "new"
    drill = session.next_items(learner, catalog, day, count=1, stage="drill")
    assert drill["stage"] == "drill" and drill["items"][0]["card"] == new[0]

    # a stage without cards names itself and leads to the engine's order
    after = session.next_items(learner, catalog, day, count=1, stage="new")
    assert after["stage_empty"] == "new" and after["stage"] == "reviews"
    assert after["items"][0]["phase"] == "review"

    # reviews left undone stay due on the next day
    assert set(due) <= set(compute(learner, catalog, day + timedelta(days=1)).reviews)
    with pytest.raises(VocabError) as error:
        session.next_items(learner, catalog, day, stage="later")
    assert error.value.code == "bad_stage"


def test_the_next_round_of_reviews_comes_before_its_day(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=4)
    learn_day(learner, catalog, MONDAY)
    # every card already has today's answer: nothing joins and nothing is written
    assert session.add_extra(learner, catalog, MONDAY, reviews=3)["added"]["reviews"] == 0
    assert learner.extra_reviews(MONDAY) == 0

    tuesday = MONDAY + timedelta(days=1)
    before = compute(learner, catalog, tuesday)
    assert not before.reviews and before.later == 4
    outside = sorted(before.before.cards)[0]
    with pytest.raises(VocabError) as error:
        session.answer(learner, catalog, tuesday, moment(tuesday), outside, "x")
    assert error.value.code == "not_due"

    added = session.add_extra(learner, catalog, tuesday, reviews=3)
    assert added["added"] == {"new": 0, "reviews": 3}
    assert added["left"]["reviews"] == 3 and added["more"]["reviews_ahead"] == 1
    cards = session.next_items(learner, catalog, tuesday, count=10, stage="reviews")
    assert [item["phase"] for item in cards["items"][:3]] == ["ahead"] * 3
    assert all("word" not in item for item in cards["items"][:3])
    card = cards["items"][0]["card"]
    result = session.answer(
        learner, catalog, tuesday, moment(tuesday), card, correct(catalog, card)
    )
    assert result["kind"] == "review" and learner.rows()[0][-1]["ahead"] is True
    assert "przed terminem 1/3" in result["counter"]
    assert result["left"]["reviews"] == 2
    # the early answer moves the card's next date, counted from the real gap
    assert (
        result["next_due"]
        > compute(learner, catalog, tuesday).before.cards[card].due(before.scheduler).isoformat()
    )

    # more new words and more reviews live side by side in the day's register
    session.add_extra(learner, catalog, tuesday, count=2)
    assert learner.extra_new(tuesday) == 2 and learner.extra_reviews(tuesday) == 3
    session.add_extra(learner, catalog, tuesday, reviews=5)
    assert learner.extra_reviews(tuesday) == 4  # only one more card was there
    assert learner.extra_reviews(tuesday + timedelta(days=1)) == 0


def test_more_reviews_take_the_due_ones_first(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=15, review_limit=10)
    learn_day(learner, catalog, MONDAY)
    day = MONDAY + timedelta(days=2)
    planned = compute(learner, catalog, day)
    assert len(planned.reviews) == 10 and planned.waiting == 5
    added = session.add_extra(learner, catalog, day, reviews=3)
    assert added["added"]["reviews"] == 3
    dp = compute(learner, catalog, day)
    assert dp.reviews[:10] == planned.reviews and len(dp.reviews) == 13
    assert not dp.ahead and dp.overflow == 2
    # the planned reviews keep their places; the added ones follow
    order = [item.card for item in dp.sequence if item.phase == "review"]
    assert order[:10] == [item.card for item in planned.sequence if item.phase == "review"]


def test_a_day_off_can_still_bring_its_reviews(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3, days_off=["wed"])
    learn_day(learner, catalog, MONDAY)
    wednesday = MONDAY + timedelta(days=2)
    dp = compute(learner, catalog, wednesday)
    assert dp.off and not dp.sequence and dp.waiting == 3
    assert session.more(dp, catalog)["reviews_due"] == 3
    added = session.add_extra(learner, catalog, wednesday, reviews=2)
    assert added["added"]["reviews"] == 2
    items = session.next_items(learner, catalog, wednesday, count=5)["items"]
    assert [item["phase"] for item in items] == ["review", "review"]


def test_more_words_only_append_to_the_day(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2", "es:a1-a2", "fr:a1-a2"], new_per_day=6)
    chosen = compute(learner, catalog, MONDAY).new
    assert len(chosen) == 6
    second = 0
    for step in range(1, 7):
        # the learner answers what the day holds, then asks for more, several times
        for card in compute(learner, catalog, MONDAY).new:
            if card not in compute(learner, catalog, MONDAY).today.seen:
                second += 1
                session.answer(
                    learner, catalog, MONDAY, moment(MONDAY, second), card, correct(catalog, card)
                )
        added = session.add_extra(learner, catalog, MONDAY, 3)
        longer = compute(learner, catalog, MONDAY).new
        assert added["added"]["new"] == 3
        assert set(chosen) < set(longer) and len(longer) == 6 + 3 * step
        # one word for each language
        assert sorted(card[:2] for card in set(longer) - set(chosen)) == ["de", "es", "fr"]
        chosen = longer
    # a word marked as known brings one more, and nothing else moves
    card = next(c for c in chosen if c not in compute(learner, catalog, MONDAY).today.seen)
    session.self_grade(learner, catalog, MONDAY, moment(MONDAY, 900), card, "known")
    longer = compute(learner, catalog, MONDAY).new
    assert set(chosen) < set(longer) and len(longer) == len(chosen) + 1


# ---------------------------------------------------------------- as in SuperMemo


def test_a_new_word_is_asked_at_once(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3, new_words="ask")
    first = session.next_items(learner, catalog, MONDAY, count=10)
    items = first["items"]
    assert len(items) == 3
    assert all(item["phase"] == "new" and "word" not in item for item in items)
    assert session.summary(learner, catalog, compute(learner, catalog, MONDAY))["new_words"] == (
        "ask"
    )
    known, missed, declared = (item["card"] for item in items)

    # a right first answer: the learner knew the word before the course, so one more comes
    result = session.answer(
        learner, catalog, MONDAY, moment(MONDAY, 1), known, correct(catalog, known)
    )
    assert (result["kind"], result["grade"], result["auto"]) == ("learn", "known", "know")
    assert result["word"]["meaning"] and result["left"]["new"] == 3
    row = learner.rows()[0][-1]
    assert (row["grade"], row["auto"]) == ("known", "know")

    # a missed word is learned from the result and comes back in the drill
    result = session.answer(learner, catalog, MONDAY, moment(MONDAY, 2), missed, "")
    assert result["grade"] == "dont_know" and result["drill"] and result["word"]["word"]
    assert result["left"] == {"reviews": 0, "new": 2, "drill": 1}

    # "znałem" without an answer still works at the first showing
    result = session.self_grade(learner, catalog, MONDAY, moment(MONDAY, 3), declared, "known")
    assert result["grade"] == "known"
    listed = session.summary(learner, catalog, compute(learner, catalog, MONDAY))
    assert [word.get("known") for word in listed["learned_today"]] == [True, True]


def test_the_drill_has_two_grades(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=6)
    dp = compute(learner, catalog, MONDAY)
    close = {}
    for card in dp.new:
        entry = catalog.card(card)
        assert entry is not None
        given = str(entry["display"]).lower()  # a noun without its capital letter
        if session.evaluate(dp, catalog, entry, given).grade == "almost":
            close[card] = given
    card, given = next(iter(close.items()))
    first = session.answer(learner, catalog, MONDAY, moment(MONDAY, 1), card, given)
    assert (first["kind"], first["grade"]) == ("learn", "almost")
    again = session.answer(learner, catalog, MONDAY, moment(MONDAY, 2), card, given)
    assert (again["kind"], again["auto"], again["grade"]) == ("drill", "almost", "dont_know")
    assert again["errors"] and again["drill"] and again["left"]["drill"] == 1
    with pytest.raises(VocabError) as error:
        session.regrade(learner, catalog, MONDAY, moment(MONDAY, 3), card, "almost")
    assert error.value.code == "drill_two_grades"
    done = session.answer(learner, catalog, MONDAY, moment(MONDAY, 4), card, correct(catalog, card))
    assert done["grade"] == "know" and done["left"]["drill"] == 0
    # the first answer keeps its grade and the card its date
    assert [row["grade"] for row in learner.rows()[0]] == ["almost", "dont_know", "know"]
    assert done["next_due"] == first["next_due"]


def test_reviews_come_in_the_order_the_plan_names(tmp_path: Path, catalog: Catalog) -> None:
    day = MONDAY + timedelta(days=4)
    orders: dict[str, list[str]] = {}
    for order in ("due", "course", "interval", "random"):
        learner = make_learner(tmp_path / order, ["de:a1-a2"], new_per_day=8, review_order=order)
        new = compute(learner, catalog, MONDAY).new
        learn_day(learner, catalog, MONDAY, wrong={new[5], new[6]})
        learn_day(learner, catalog, MONDAY + timedelta(days=1), wrong={new[5]})
        dp = compute(learner, catalog, day)
        orders[order] = [item.card for item in dp.sequence if item.phase == "review"]
        assert orders[order] == [
            item.card for item in compute(learner, catalog, day).sequence if item.phase == "review"
        ]
        if order == "interval":
            intervals = [
                (dp.before.cards[c].due(dp.scheduler) - dp.before.cards[c].last_day).days
                for c in orders[order]
            ]
            assert intervals == sorted(intervals) and len(set(intervals)) > 1
    assert len(orders["due"]) >= 8
    assert all(sorted(cards) == sorted(orders["due"]) for cards in orders.values())
    place = {str(e["id"]): n for n, e in enumerate(catalog.course("de", ["a1", "a2"]))}
    assert orders["course"] == sorted(orders["course"], key=lambda c: place[c.split("#")[0]])
    assert len({tuple(cards) for cards in orders.values()}) == 4


# ---------------------------------------------------------------- handling a card as in SuperMemo


def test_self_assessment_shows_the_answer_and_keeps_the_learners_grade(
    tmp_path: Path, catalog: Catalog
) -> None:
    typing = make_learner(tmp_path / "type", ["de:a1-a2"], new_per_day=3)
    card = compute(typing, catalog, MONDAY).new[0]
    for call, code in (
        (lambda: session.reveal(catalog, card, typing, MONDAY), "reveal_production"),
        (
            lambda: session.self_grade(typing, catalog, MONDAY, moment(MONDAY), card, "know"),
            "production_needs_answer",
        ),
    ):
        with pytest.raises(VocabError) as error:
            call()
        assert error.value.code == code
    typed = session.answer(typing, catalog, MONDAY, moment(MONDAY), card, correct(catalog, card))

    learner = make_learner(tmp_path / "self", ["de:a1-a2"], new_per_day=3, answer_mode="self")
    first = session.next_items(learner, catalog, MONDAY, count=1)
    assert first["view"]["answer_mode"] == "self" and first["items"][0]["card"] == card
    shown = session.reveal(catalog, card, learner, MONDAY)
    assert shown["word"]["word"] == correct(catalog, card)
    assert (shown["phase"], shown["grades"]) == ("new", ["know", "almost", "dont_know"])
    assert shown["counter"].startswith("Postęp: 0/3") and shown["stage"] == "new"
    result = session.self_grade(learner, catalog, MONDAY, moment(MONDAY), card, "know")
    assert (result["kind"], result["grade"]) == ("learn", "know")
    row = learner.rows()[0][-1]
    assert row["grade"] == "know" and "auto" not in row
    # the learner's grade schedules the card as the engine's grade would
    assert (result["next_due"], result["interval_days"]) == (
        typed["next_due"],
        typed["interval_days"],
    )

    # a missed word: the drill has two grades, and "almost" stays there as "nie wiem"
    missed = compute(learner, catalog, MONDAY).new[1]
    session.self_grade(learner, catalog, MONDAY, moment(MONDAY, 1), missed, "dont_know")
    drill = session.reveal(catalog, missed, learner, MONDAY)
    assert (drill["phase"], drill["grades"]) == ("drill", ["know", "dont_know"])
    again = session.self_grade(learner, catalog, MONDAY, moment(MONDAY, 2), missed, "almost")
    assert (again["kind"], again["grade"]) == ("drill", "dont_know")
    done = session.self_grade(learner, catalog, MONDAY, moment(MONDAY, 3), missed, "know")
    assert done["left"]["drill"] == 0

    # only a card waiting today shows its answer
    later = compute(learner, catalog, MONDAY).before.cards
    assert not later
    outside = card_of("de", 30)
    assert outside not in [i.card for i in compute(learner, catalog, MONDAY).sequence]
    with pytest.raises(VocabError) as error:
        session.reveal(catalog, outside, learner, MONDAY)
    assert error.value.code == "reveal_not_waiting"


def test_the_result_says_when_the_card_comes_back(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3)
    right, wrong, _ = compute(learner, catalog, MONDAY).new
    known = session.answer(learner, catalog, MONDAY, moment(MONDAY), right, correct(catalog, right))
    days = known["interval_days"]
    assert known["back"] == ("wróci jutro" if days == 1 else f"wróci za {days} dni")
    missed = session.answer(learner, catalog, MONDAY, moment(MONDAY, 1), wrong, "xxx")
    assert missed["back"] == "wróci dziś w utrwalaniu"
    drill = session.answer(
        learner, catalog, MONDAY, moment(MONDAY, 2), wrong, correct(catalog, wrong)
    )
    assert drill["kind"] == "drill" and drill["back"].startswith("wróci ")

    hidden = make_learner(tmp_path / "hidden", ["de:a1-a2"], new_per_day=1, next_review="hidden")
    card = compute(hidden, catalog, MONDAY).new[0]
    result = session.answer(hidden, catalog, MONDAY, moment(MONDAY), card, correct(catalog, card))
    assert "back" not in result and result["next_due"]
    assert result["view"]["next_review"] == "hidden"


def test_a_word_put_aside_leaves_the_queue_until_it_comes_back(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3)
    learn_day(learner, catalog, MONDAY)
    day = MONDAY + timedelta(days=2)
    before = compute(learner, catalog, day)
    review, new = before.reviews[0], before.new[0]
    session.flag(learner, catalog, review, moment(day), skip=True)
    session.flag(learner, catalog, new, moment(day), note="zła liczba mnoga")
    after = compute(learner, catalog, day)
    assert review not in after.reviews and new not in after.new
    assert len(after.new) == 3  # another word takes the place of the one reported
    report = progress.status(learner, catalog, day)
    assert [w["card"] for w in report["skipped"]] == [review.split("#")[0] + "#p"]
    assert [w["card"] for w in report["reported"]] == [new.split("#")[0] + "#p"]
    assert learner.skipped() == {review.split("#")[0]}
    with pytest.raises(VocabError) as error:
        session.answer(learner, catalog, day, moment(day), review, correct(catalog, review))
    assert error.value.code == "card_suspended"
    cleared = session.flag(learner, catalog, review, moment(day, 1), clear=True)
    assert cleared == {"entry": review.split("#")[0], "cleared": True, "skipped": False}
    back = compute(learner, catalog, day)
    assert review in back.reviews
    assert back.before.cards[review].due(back.scheduler) == before.before.cards[review].due(
        before.scheduler
    )


def test_a_note_comes_with_the_answer_and_never_with_the_question(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=3, answer_mode="self")
    card = compute(learner, catalog, MONDAY).new[0]
    saved = session.save_note(learner, catalog, card, moment(MONDAY), "  brzmi jak hound  ")
    assert saved == {"entry": card.split("#")[0], "note": "brzmi jak hound", "cleared": False}
    session.save_note(learner, catalog, card, moment(MONDAY, 1), "Hund jak hound")
    assert learner.notes() == {card.split("#")[0]: "Hund jak hound"}
    for code, text in (("empty_note", "   "), ("note_too_long", "x" * 501)):
        with pytest.raises(VocabError) as error:
            session.save_note(learner, catalog, card, moment(MONDAY), text)
        assert error.value.code == code

    shown = session.next_items(learner, catalog, MONDAY, count=10)
    assert "Hund jak hound" not in json.dumps(shown, ensure_ascii=False)
    assert session.reveal(catalog, card, learner, MONDAY)["word"]["note"] == "Hund jak hound"
    entry = catalog.card(card)
    assert entry is not None
    found = session.lookup(learner, catalog, MONDAY, "de", str(entry["display"]))
    assert found["matches"][0]["word"]["note"] == "Hund jak hound"
    result = session.answer(learner, catalog, MONDAY, moment(MONDAY, 2), card, "")
    assert result["word"]["note"] == "Hund jak hound"
    following = session.next_items(learner, catalog, MONDAY, count=10)
    assert "Hund jak hound" not in json.dumps(following, ensure_ascii=False)

    session.save_note(learner, catalog, card, moment(MONDAY, 3), clear=True)
    assert learner.notes() == {}
    assert "note" not in session.reveal(catalog, card, learner, MONDAY)["word"]
