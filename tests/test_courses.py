"""The starter course and the checks of course entries."""

from __future__ import annotations

import copy

from conftest import entry_of

from vocabbot import courses
from vocabbot.courses import Catalog


def test_fixture_course_passes(catalog: Catalog) -> None:
    result = courses.check(catalog)
    assert result["errors"] == []
    assert result["warnings"] == []
    for lang in ("en", "de", "es", "fr"):
        assert result["counts"][lang] == {"a1": 40, "a2": 20}


def test_packaged_course_passes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("VOCABBOT_COURSES")
    result = courses.check(Catalog())
    assert result["ok"], result["errors"][:5]


def test_families_join_four_languages(catalog: Catalog) -> None:
    family = catalog.family("c90002")
    assert sorted(e["lang"] for e in family) == ["de", "en", "es", "fr"]


def test_question_never_holds_the_answer(catalog: Catalog) -> None:
    for entry in catalog.entries():
        q = courses.question(entry, "p")
        text = " ".join(str(v) for v in q.values())
        assert entry["display"] not in text, entry["id"]


def test_entry_problems_are_found(catalog: Catalog) -> None:
    good = entry_of(catalog, "de", 2)
    assert courses.entry_problems(good) == []
    cases = {
        "gender": ("gender", "x"),
        "article": ("display", "die Hund"),
        "capital": ("display", "der hund"),
        "gap": ("example", {"text": "Ein Hund.", "gap": "Katze", "pl": "Pies."}),
        "ipa": ("ipa", "hʊnt"),
        "pos": ("pos", "noun-ish"),
    }
    for name, (key, value) in cases.items():
        bad = copy.deepcopy(good)
        bad[key] = value
        assert courses.entry_problems(bad), name


def test_spanish_feminine_el(catalog: Catalog) -> None:
    assert courses.entry_problems(entry_of(catalog, "es", 4)) == []


def test_duplicate_meaning_needs_hints(catalog: Catalog) -> None:
    extra = copy.deepcopy(entry_of(catalog, "de", 2))
    extra.update(
        {
            "id": "de-c91000",
            "concept": "c91000",
            "rank": 99,
            "display": "der Köter",
            "lemma": "Köter",
        }
    )
    extra["example"] = {"text": "Der Köter bellt.", "gap": "Der Köter", "pl": "Kundel szczeka."}
    catalog._load()
    catalog._add(extra, own=False)
    result = courses.check(catalog)
    assert any("share the meaning" in e for e in result["errors"])
