"""Learning by families (Stage 14b): the plan's `together` on the starter course.

The starter course has the same 60 concepts in German, English, Spanish and
French, so every family of Spanish and French is complete. Its Spanish and
French pairs cover the shapes of two forms: "grande" and "grand" (near),
"dormir" (identical) and "el perro" and "le chien" (distinct).
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import card_of, correct, make_learner, moment

import vocabbot
from vocabbot import families, gate, plans, progress, session, store
from vocabbot.courses import Catalog, split_card
from vocabbot.errors import VocabError
from vocabbot.queue import compute

MONDAY = date(2026, 11, 16)
SET = ["es:a1-a2", "fr:a1-a2"]


def concept(catalog: Catalog, card: str) -> str:
    entry = catalog.card(card)
    assert entry is not None
    return str(entry["concept"])


def learn_day(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    *,
    wrong_every: int = 0,
    stop_after: int | None = None,
) -> list[dict[str, Any]]:
    """Answer the day's cards in order: right, or wrong every `wrong_every` answers."""
    results = []
    second = 0
    dp = compute(learner, catalog, day)
    while dp.sequence and (stop_after is None or second < stop_after):
        item = dp.sequence[0]
        second += 1
        wrong = wrong_every and second % wrong_every == 0 and item.phase != "drill"
        given = "xyz" if wrong else correct(catalog, item.card)
        results.append(session.answer(learner, catalog, day, moment(day, second), item.card, given))
        dp = compute(learner, catalog, day)
    return results


def change(learner: store.Learner, catalog: Catalog, day: date, *settings: str) -> dict[str, Any]:
    now = moment(day, 0)
    preview = plans.set_preview(learner, catalog, list(settings), now)
    gate.commit(preview["token"], [learner.path(store.PENDING)], now, via="token")
    learner.forget()
    return preview


# ---------------------------------------------------------------- the module


def test_the_shape_and_the_parts_of_two_forms() -> None:
    assert families.shape("grande", "grand") == "near"
    assert families.shape("fácil", "facil") == "identical"
    assert families.shape("dormir", "dormir") == "identical"
    assert families.shape("la mano", "la main") == "near"
    assert families.shape("el perro", "le chien") == "distinct"
    assert families.shape("universidad", "université") == "near"  # a shared start
    assert families.split("grande", "grand") == [["grand", True], ["e", False]]
    assert families.split("grand", "grande") == [["grand", True]]
    assert families.split("fácil", "facile") == [["fácil", True]]
    # distinct words differ as a whole, without letters matched by chance
    assert families.parts("la maison", "la casa") == [["la maison", False]]


def test_every_rule_of_endings_fits_ten_concepts_of_the_courses() -> None:
    root = Path(vocabbot.__file__).parent / "data" / "courses"
    lemmas: dict[str, dict[str, str]] = defaultdict(dict)
    for lang in ("es", "it", "fr"):
        for level in store.LEVELS:
            for line in (root / lang / f"{level}.jsonl").read_text("utf-8").splitlines():
                entry = json.loads(line)
                lemmas[entry["concept"]].setdefault(lang, entry["lemma"])
    found: Counter[str] = Counter()
    for words in lemmas.values():
        if len(words) == 3:
            fitting = families.rule(words)
            if fitting:
                found[json.dumps(fitting, sort_keys=True)] += 1
    patterns = families.correspondences()
    assert len(patterns) >= 10
    for endings in patterns:
        assert found[json.dumps(endings, sort_keys=True)] >= 10, endings
    # a rule needs near stems
    assert families.rule({"es": "hablar", "it": "parlare", "fr": "parler"}) is None
    assert families.rule({"es": "información", "fr": "information"}) == {
        "es": "ción",
        "fr": "tion",
    }
    assert families.rule({"es": "información"}) is None


def test_the_set_of_a_plan() -> None:
    def plan(together: list[str], paused: str = "") -> dict[str, Any]:
        languages = [
            {"code": code, "levels": ["a1"], "paused": code == paused}
            for code in ("es", "fr", "it")
        ]
        return {"languages": languages, "together": together}

    assert families.team(plan(["fr", "es"])) == ["es", "fr"]  # in the plan's order
    assert families.team(plan(["es", "fr"], paused="fr")) == []  # one language is no set
    assert families.team(plan(["es", "fr", "it"], paused="it")) == ["es", "fr"]
    assert families.team(plan(["es", "de"])) == []
    assert families.team(plan([])) == []


# ---------------------------------------------------------------- the setting


def test_the_setting_goes_through_a_preview(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, [*SET, "en:a1-a2"], new_per_day=6)
    preview = change(learner, catalog, MONDAY, "together=fr,es")
    assert preview["summary"].endswith("together: none → es,fr")
    assert any(line.startswith("Prognoza na 28 dni") for line in preview["preview"])
    assert learner.plan()["together"] == ["es", "fr"]
    assert "Nauka rodzinami: hiszpański, francuski" in plans.describe(learner.plan())
    change(learner, catalog, MONDAY, "together=all")
    assert learner.plan()["together"] == ["es", "fr", "en"]
    # a language that leaves the plan leaves its families
    change(learner, catalog, MONDAY, "lang.en=off")
    assert learner.plan()["together"] == ["es", "fr"]
    change(learner, catalog, MONDAY, "lang.fr=off")
    assert learner.plan()["together"] == []
    for wrong, code in (
        ("together=es", "together_too_few"),
        ("together=es,de", "lang_not_in_plan"),
    ):
        with pytest.raises(VocabError) as refused:
            plans.set_preview(learner, catalog, [wrong], moment(MONDAY))
        assert refused.value.code == code
    rows = plans.history_rows(learner.root)
    assert any(row["set"].get("together") == ["es", "fr"] for row in rows)


def test_two_devices_join_their_changes_of_the_set() -> None:
    first = {
        "ts": "2026-11-16T10:00:00.000000Z",
        "set": {"languages": [{"code": c, "levels": ["a1"]} for c in ("es", "fr", "en")]},
    }
    laptop = {"ts": "2026-11-16T11:00:00.000000Z", "set": {"together": ["es", "fr"]}}
    phone = {"ts": "2026-11-16T11:05:00.000000Z", "set": {"new_per_day": 8}}
    assert all(plans.valid_history_row(row) for row in (first, laptop, phone))
    folded = plans.fold([phone, first, laptop])
    assert folded is not None
    assert folded["together"] == ["es", "fr"] and folded["new_per_day"] == 8
    assert not plans.valid_history_row({**laptop, "set": {"together": "es,fr"}})


# ---------------------------------------------------------------- new words


def test_new_words_come_as_whole_families(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=["es", "fr"])
    for offset in range(5):
        day = MONDAY + timedelta(days=offset)
        dp = compute(learner, catalog, day)
        by_lang: dict[str, set[str]] = defaultdict(set)
        for card in dp.new:
            by_lang[card[:2]].add(concept(catalog, card))
        assert len(by_lang["es"]) == len(by_lang["fr"]) == 3
        assert by_lang["es"] == by_lang["fr"], day
        learn_day(learner, catalog, day)


def test_a_language_first_completes_the_families_it_has_not_met(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6)
    for offset in range(4):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset))
    day = MONDAY + timedelta(days=4)
    change(learner, catalog, day, "together=es,fr")
    dp = compute(learner, catalog, day)
    first: dict[str, dict[str, date]] = defaultdict(dict)
    for card, state in dp.before.cards.items():
        first[concept(catalog, card)][card[:2]] = state.first_day
    for code, other in (("es", "fr"), ("fr", "es")):
        waiting = sorted(
            (days[other], name)
            for name, days in first.items()
            if other in days and code not in days
        )
        picked = [concept(catalog, card) for card in dp.new if card[:2] == code]
        # the oldest families of the other language come first, in the order they were met
        assert picked == [name for _, name in waiting][: len(picked)], code
        assert picked


def test_weights_levels_and_words_put_aside_lose_no_place(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["es:a1-a2:2", "fr:a1"], new_per_day=9, together=["es", "fr"])
    # a French word put aside: its family waits for it no longer
    session.flag(learner, catalog, card_of("fr", 2), moment(MONDAY), skip=True)
    for offset in range(6):
        day = MONDAY + timedelta(days=offset)
        dp = compute(learner, catalog, day)
        counts = Counter(card[:2] for card in dp.new)
        assert counts == {"es": 6, "fr": 3}, (day, counts)
        for card in dp.new:
            if card[:2] == "fr":
                entry = catalog.card(card)
                assert entry is not None and entry["level"] == "a1"
        learn_day(learner, catalog, day)
    # French completes Spanish families of its own level only, the oldest first
    book = compute(learner, catalog, MONDAY + timedelta(days=6)).before
    french = {concept(catalog, card) for card in book.cards if card[:2] == "fr"}
    spanish = {concept(catalog, card) for card in book.cards if card[:2] == "es"}
    assert french <= spanish
    assert card_of("fr", 2) not in book.cards


def test_a_paused_language_ends_the_set_of_two(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=["es", "fr"])
    learn_day(learner, catalog, MONDAY)
    change(learner, catalog, MONDAY, "lang.fr=paused")
    dp = compute(learner, catalog, MONDAY + timedelta(days=1))
    assert dp.team == [] and dp.companions == []
    assert all(card[:2] == "es" for card in dp.new) and len(dp.new) == 6


def test_more_words_and_known_words_only_append(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(
        tmp_path, [*SET, "en:a1-a2"], new_per_day=6, together=["es", "fr"], new_words="ask"
    )
    before = compute(learner, catalog, MONDAY).new
    session.add_extra(learner, catalog, MONDAY, count=5)
    after = compute(learner, catalog, MONDAY).new
    # a card once on the list never leaves it
    assert set(before) <= set(after) and len(after) == len(before) + 5
    # a word known before the course brings one more word
    learn_day(learner, catalog, MONDAY, stop_after=1)
    final = compute(learner, catalog, MONDAY).new
    assert set(after) <= set(final) and len(final) == len(after) + 1


# ---------------------------------------------------------------- the order of the day


def blocks_of(dp: Any, catalog: Catalog) -> list[list[str]]:
    """The runs of cards of one family in the set's languages, in the day's order."""
    out: list[list[str]] = []
    for item in dp.sequence:
        if item.lang not in dp.team or item.phase == "drill":
            continue
        key = families.key_of(item.card, item.entry)
        if out and families.key_of(out[-1][-1], catalog.card(out[-1][-1])) == key:
            out[-1].append(item.card)
        else:
            out.append([item.card])
    return out


def test_a_family_stands_as_one_block_and_its_first_language_turns(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, [*SET, "en:a1-a2"], new_per_day=9, together=["es", "fr"])
    leaders: Counter[str] = Counter()
    for offset in range(10):
        day = MONDAY + timedelta(days=offset)
        dp = compute(learner, catalog, day)
        runs = blocks_of(dp, catalog)
        keys = [families.key_of(run[0], catalog.card(run[0])) for run in runs]
        # every family of the set appears once, as one block
        assert len(keys) == len(set(keys)), day
        for run in runs:
            if len(run) > 1:
                leaders[run[0][:2]] += 1
        learn_day(learner, catalog, day, wrong_every=6)
    assert leaders["es"] > 0 and leaders["fr"] > 0


def test_a_language_outside_the_set_keeps_its_gap(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, [*SET, "en:a1-a2"], new_per_day=9, together=["es", "fr"])
    for offset in range(12):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset))
    book = compute(learner, catalog, MONDAY + timedelta(days=12)).before
    first: dict[str, dict[str, date]] = defaultdict(dict)
    for card, state in book.cards.items():
        first[concept(catalog, card)][card[:2]] = state.first_day
    checked = 0
    for days in first.values():
        if "en" in days:
            for code in ("es", "fr"):
                if code in days:
                    assert abs((days["en"] - days[code]).days) >= 3, days
                    checked += 1
        if "es" in days and "fr" in days:
            assert days["es"] == days["fr"]
    assert checked > 0


# ---------------------------------------------------------------- reviews by families


def test_a_due_card_brings_its_family_from_half_its_interval(
    tmp_path: Path, catalog: Catalog
) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=["es", "fr"])
    joined = 0
    for offset in range(24):
        day = MONDAY + timedelta(days=offset)
        dp = compute(learner, catalog, day)
        anchors = {families.key_of(c, catalog.card(c)) for c in dp.reviews}
        for card, state in dp.before.cards.items():
            due = state.due(dp.scheduler_for(state.lang))
            elapsed = (day - state.last_day).days
            key = families.key_of(card, catalog.card(card))
            eligible = (
                key in anchors
                and card not in dp.reviews
                and due > day
                and elapsed >= 1
                and 2 * elapsed >= (due - state.last_day).days
            )
            assert (card in dp.companions) == eligible, (day, card)
        joined += len(dp.companions)
        ahead = {item.card for item in dp.sequence if item.phase == "ahead"}
        assert set(dp.companions) <= ahead
        learn_day(learner, catalog, day, wrong_every=5)
    assert joined > 0
    rows = learner.rows()[0]
    companions = [row for row in rows if row.get("ahead")]
    assert companions and all(row["kind"] == "review" for row in companions)
    # no card is reviewed twice on one day
    reviews = Counter((row["day"], row["card"]) for row in rows if row["kind"] == "review")
    assert max(reviews.values()) == 1


def test_the_limit_a_day_off_and_a_break_keep_the_order(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=8, together=["es", "fr"], days_off=["sun"])
    for offset in range(9):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset))
    sunday = MONDAY + timedelta(days=13)
    assert compute(learner, catalog, sunday).companions == []
    day = MONDAY + timedelta(days=9)
    dp = compute(learner, catalog, day)
    planned = [item.card for item in dp.sequence]
    learn_day(learner, catalog, day, stop_after=3)
    rest = [item.card for item in compute(learner, catalog, day).sequence if item.phase != "drill"]
    assert rest == [card for card in planned[3:] if card in rest]
    change(learner, catalog, day, "review_limit=10")
    limited = compute(learner, catalog, day + timedelta(days=1))
    assert len(limited.reviews) <= 10  # the companions come on top of the limit


# ---------------------------------------------------------------- the first answer


def test_the_second_card_of_a_family_is_learned_not_known(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=["es", "fr"], new_words="ask")
    dp = compute(learner, catalog, MONDAY)
    first, second = dp.sequence[0], dp.sequence[1]
    assert families.key_of(first.card, first.entry) == families.key_of(second.card, second.entry)
    one = session.answer(
        learner, catalog, MONDAY, moment(MONDAY, 1), first.card, correct(catalog, first.card)
    )
    assert one["grade"] == "known"
    two = session.answer(
        learner, catalog, MONDAY, moment(MONDAY, 2), second.card, correct(catalog, second.card)
    )
    assert two["grade"] == "know"
    # "known" adds a word to the day; the neighbour's word adds none
    assert len(compute(learner, catalog, MONDAY).new) == len(dp.new) + 1


# ---------------------------------------------------------------- answers stay back


def test_no_question_and_no_table_answers_a_waiting_card(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(
        tmp_path, SET, new_per_day=10, together=["es", "fr"], new_words="ask", batch=3
    )
    tables = 0
    for offset in range(6):
        day = MONDAY + timedelta(days=offset)
        second = 0
        while True:
            shown = session.next_items(learner, catalog, day, count=3)
            if not shown["items"]:
                break
            for item in shown["items"]:
                assert "word" not in item
            item = shown["items"][0]
            second += 1
            given = correct(catalog, item["card"]) if second % 4 else "xyz"
            result = session.answer(learner, catalog, day, moment(day, second), item["card"], given)
            # the answered card's own word is in the result anyway, also when it waits in
            # the drill; the table may not show the answer of any other waiting card
            left = {i.card for i in compute(learner, catalog, day).sequence} - {item["card"]}
            hidden = families.hidden_forms(left, catalog)
            for row in (result.get("family") or {}).get("rows", []):
                tables += 1
                if "word" in row:
                    assert row["card"] not in left
                    assert row["word"].casefold() not in hidden, (row, item)
                else:
                    assert row["waiting"] is True
    assert tables > 20


def test_the_table_names_the_rule_of_endings(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=0, together=["es", "fr"])
    entry = catalog.card(card_of("es", 31))  # grande; French grand
    assert entry is not None
    table = families.table(
        learner.plan(),
        card_of("es", 31),
        entry,
        catalog,
        lambda card: card == card_of("fr", 31),
        set(),
        set(),
    )
    assert table is not None
    assert table["rows"] == [
        {"lang": "fr", "card": card_of("fr", 31), "word": "grand", "parts": [["grand", True]]}
    ]
    assert table["word_parts"] == [["grand", True], ["e", False]]
    waiting = families.table(
        learner.plan(),
        card_of("es", 31),
        entry,
        catalog,
        lambda card: True,
        {card_of("fr", 31)},
        set(),
    )
    assert waiting == {"rows": [{"lang": "fr", "card": card_of("fr", 31), "waiting": True}]}


# ---------------------------------------------------------------- measurement and forecast


def test_status_measures_learning_by_families(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=["es", "fr"])
    for offset in range(14):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset), wrong_every=4)
    day = MONDAY + timedelta(days=13)
    report = progress.status(learner, catalog, day)["families"]
    rows = learner.rows()[0]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["kind"] == "review":
            groups[(row["day"], concept(catalog, row["card"]) + split_card(row["card"])[1])].append(
                row
            )
    blocks = [sorted(g, key=lambda r: r["ts"]) for g in groups.values() if len(g) >= 2]
    first = [b[0]["grade"] != "dont_know" for b in blocks]
    following = [r["grade"] != "dont_know" for b in blocks for r in b[1:]]
    assert report["together"] == ["es", "fr"]
    assert report["blocks_30"] == len(blocks) > 0
    assert report["first_recall_30"] == round(sum(first) / len(first), 3)
    assert report["following_recall_30"] == round(sum(following) / len(following), 3)
    assert report["mixups_per_100"] == 0.0


@pytest.mark.parametrize("together", [[], ["es", "fr"]])
def test_the_forecast_of_the_first_day_is_the_day(
    tmp_path: Path, catalog: Catalog, together: list[str]
) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6, together=together)
    for offset in range(10):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset), wrong_every=5)
    day = MONDAY + timedelta(days=10)
    dp = compute(learner, catalog, day)
    phases = Counter(item.phase for item in dp.sequence)
    first = progress.forecast(learner, catalog, day, 7)["days"][0]
    assert first["reviews"] == phases["review"] + phases["ahead"]
    assert first["new"] == phases["new"]
    if together:
        assert phases["ahead"] == len(dp.companions)


def test_the_preview_shows_the_load_before_and_after(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, SET, new_per_day=6)
    for offset in range(8):
        learn_day(learner, catalog, MONDAY + timedelta(days=offset))
    day = MONDAY + timedelta(days=8)
    preview = plans.set_preview(learner, catalog, ["together=es,fr"], moment(day))
    old = learner.plan()
    new = {**old, "together": ["es", "fr"]}
    before = progress.forecast(learner, catalog, day, 28, plan=old)
    after = progress.forecast(learner, catalog, day, 28, plan=new)
    line = next(line for line in preview["preview"] if line.startswith("Prognoza"))
    assert f"obecnie {before['average_reviews']} powtórek" in line
    assert f"po zmianie {after['average_reviews']} powtórek" in line
    assert after["joined_share"] > 0
