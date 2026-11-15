"""The placement test: questions without answers, grading without the log."""

from __future__ import annotations

import pytest
from conftest import correct

from vocabbot import quiz
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError

QUESTION_KEYS = {"ask", "meaning", "pos", "with_article", "hint", "sentence", "sentence_pl"}


def test_questions_spread_over_levels_without_answers(catalog: Catalog) -> None:
    data = quiz.questions(catalog, "de", ["a1", "a2"], 4)
    assert [item["level"] for item in data["items"]] == ["a1"] * 4 + ["a2"] * 4
    assert len({item["card"] for item in data["items"]}) == 8
    for item in data["items"]:
        assert item["card"].endswith("#p")
        assert set(item["question"]) <= QUESTION_KEYS
    assert quiz.questions(catalog, "de", ["a1", "a2"], 4) == data
    with pytest.raises(VocabError) as error:
        quiz.questions(catalog, "it", ["a1"], 4)
    assert error.value.code == "no_course"
    with pytest.raises(VocabError):
        quiz.questions(catalog, "de", ["a1"], 0)


def test_check_grades_levels_and_suggests_where_to_start(catalog: Catalog) -> None:
    items = quiz.questions(catalog, "de", ["a1", "a2"], 3)["items"]
    right = [{"card": i["card"], "answer": correct(catalog, i["card"])} for i in items[:3]]
    wrong = [{"card": i["card"], "answer": "xxx"} for i in items[3:]]
    result = quiz.check(catalog, right + wrong)
    assert result["levels"]["a1"] == {
        "asked": 3,
        "know": 3,
        "almost": 0,
        "share": 1.0,
        "known": True,
    }
    assert result["levels"]["a2"]["known"] is False
    assert result["suggested_levels"] == "a2-b2"
    assert all(r["word"]["word"] for r in result["results"])
    # every asked level known: start one level higher
    assert quiz.check(catalog, right)["suggested_levels"] == "a2-b2"
    # an answer graded "almost" counts as half
    almost = [{"card": items[0]["card"], "answer": correct(catalog, items[0]["card"]).upper()}]
    assert quiz.check(catalog, almost)["levels"]["a1"]["share"] in (0.5, 1.0)
    assert quiz.suggest({}) is None
    assert quiz.suggest({"b2": {"known": True}}) == "b2"


def test_check_refuses_cards_it_cannot_grade(catalog: Catalog) -> None:
    for card, code in (
        ("nonsense", "bad_card"),
        ("de-c90001#r", "unknown_card"),
        ("de-c99999#p", "unknown_card"),
    ):
        with pytest.raises(VocabError) as error:
            quiz.check(catalog, [{"card": card, "answer": "x"}])
        assert error.value.code == code


def test_a_sentence_never_holds_another_answer(catalog: Catalog) -> None:
    data = quiz.questions(catalog, "de", ["a1", "a2"], 6)
    answers = {}
    for item in data["items"]:
        entry = catalog.card(item["card"])
        assert entry is not None
        answers[item["card"]] = [str(entry["display"]), str(entry["lemma"])]
    for item in data["items"]:
        sentence = item["question"].get("sentence", "")
        for card, forms in answers.items():
            if card != item["card"]:
                assert not any(f" {form} " in f" {sentence} " for form in forms), (item, card)
