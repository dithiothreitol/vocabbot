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


def test_plural_and_bare_nouns(catalog: Catalog) -> None:
    good = entry_of(catalog, "de", 2)
    plural = {**copy.deepcopy(good), "display": "die Eltern", "lemma": "Eltern", "gender": "pl"}
    plural.pop("example", None)
    assert courses.entry_problems(plural) == []
    assert courses.entry_problems({**plural, "display": "der Eltern"})
    month = {**plural, "lang": "es", "id": "es-" + plural["concept"], "display": "enero"}
    month.update({"lemma": "enero", "gender": "m", "bare": True})
    assert courses.entry_problems(month) == []
    assert not courses.needs_article(month)
    assert courses.entry_problems({**month, "display": "el enero"})


def test_a_recording_is_a_commons_file_played_as_mp3(catalog: Catalog) -> None:
    entry = copy.deepcopy(entry_of(catalog, "de", 1))
    assert "audio" not in courses.presentation(entry)
    entry["audio"] = "De-Hund.ogg"
    assert courses.entry_problems(entry) == []
    assert courses.presentation(entry)["audio"] == (
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/aa/De-Hund.ogg/De-Hund.ogg.mp3"
    )
    spanish = "LL-Q1321 (spa)-Noaius Paticus-(American Spanish) Ciudad de Cebú.wav"
    assert courses.audio_url(spanish) == (
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/c/c3/"
        "LL-Q1321_%28spa%29-Noaius_Paticus-%28American_Spanish%29_Ciudad_de_Ceb%C3%BA.wav/"
        "LL-Q1321_%28spa%29-Noaius_Paticus-%28American_Spanish%29_Ciudad_de_Ceb%C3%BA.wav.mp3"
    )
    assert courses.audio_url("en-us-word.mp3").endswith("/En-us-word.mp3")
    for wrong in ("../etc/passwd.ogg", "De-Hund.exe", "https://example.com/a.ogg", 7):
        entry["audio"] = wrong
        assert courses.entry_problems(entry) == [
            "audio must be the file name of a recording on Wikimedia Commons"
        ]
        assert "audio" not in courses.presentation(entry)
