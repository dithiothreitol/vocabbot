"""Rules of the course pipeline (tools/courses) that are easy to break."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("wordfreq")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "courses"))

import build
import wiktionary


def test_spanish_feminine_nouns_with_stressed_a_take_el() -> None:
    assert build.article_for("es", "f", "agua", {"ipa": "/ˈaɡwa/"}) == "el"
    assert build.article_for("es", "f", "hambre", {"ipa": "/ˈambɾe/"}) == "el"
    assert build.article_for("es", "f", "abeja", {"ipa": "/aˈbexa/"}) == "la"
    assert build.article_for("es", "m", "año", {"ipa": "/ˈaɲo/"}) == "el"


def test_french_elision_and_aspirated_h() -> None:
    assert build.article_for("fr", "f", "école", None) == "l'"
    assert build.article_for("fr", "m", "homme", {}) == "l'"
    assert build.article_for("fr", "m", "haricot", {"h_aspire": True}) == "le"
    assert build.with_article("l'", "école") == "l'école"
    assert build.with_article("die", "Katze") == "die Katze"


def test_gap_prefers_the_citation_form() -> None:
    word = build.Word("de", "Hund", "der Hund", "m")
    assert build.find_gap("Der Hund schläft.", word, "noun") == ("Der Hund", True)
    assert build.find_gap("Ich sehe den Hund.", word, "noun") == ("den Hund", False)
    assert build.find_gap("Der Hund sieht den Hund.", word, "noun") is None
    french = build.Word("fr", "eau", "l'eau", "f")
    assert build.find_gap("Je bois de l'eau.", french, "noun") == ("l'eau", True)


def test_reviewed_words_follow_the_article_rules() -> None:
    lexicon = build.Lexicon()
    lexicon.by_word["agua"].append(
        {"word": "agua", "pos": "noun", "ipa": "/ˈaɡwa/", "plural": ["aguas"]}
    )
    water = build.reviewed_word(
        "es", "noun", {"word": "la agua", "gender": "f", "also": []}, lexicon
    )
    assert (
        water is not None and water.display == "el agua" and water.forms == {"plural": "las aguas"}
    )
    school = build.reviewed_word(
        "fr", "noun", {"word": "école", "gender": "f", "also": ["l'établissement"]}, build.Lexicon()
    )
    assert (
        school is not None and school.display == "l'école" and school.accept == ["l'établissement"]
    )
    assert (
        build.reviewed_word("de", "noun", {"word": "der hund", "gender": "m", "also": []}, lexicon)
        is None
    )
    assert (
        build.reviewed_word("de", "verb", {"word": "", "gender": "none", "also": []}, lexicon)
        is None
    )
    assert build.reviewed_gloss(" kola,  napój gazowany , extra") == "kola, napój gazowany"


def test_clean_drops_notes_and_long_phrases() -> None:
    assert build.clean("Hund (animal)") == "Hund"
    assert build.clean("a b c d") is None
    assert build.clean("2nd") is None


def test_head_genders() -> None:
    assert wiktionary.head_genders("Hund m (strong, genitive Hundes, plural Hunde)", "Hund") == [
        "m"
    ]
    assert wiktionary.head_genders("Single m or f (plural Singles)", "Single") == ["m", "f"]
    assert wiktionary.head_genders("agua f (plural aguas)", "agua") == ["f"]


def entry(concept: str, lang: str, display: str, gloss: str, level: str = "a1") -> dict:
    return {
        "concept": concept,
        "lang": lang,
        "level": level,
        "display": display,
        "gloss": {"pl": gloss},
        "pos": "noun",
        "_frequency": 5.0,
    }


def test_synonyms_merge_and_homonyms_get_hints() -> None:
    families = {
        "c1": {"en": "big", "de": "groß", "es": "grande"},
        "c2": {"en": "large", "de": "groß", "es": "amplio"},
        "c3": {"en": "racket", "de": "der Schläger", "es": "la raqueta"},
        "c4": {"en": "rocket", "de": "die Rakete", "es": "el cohete"},
    }
    spanish = {
        "c1": entry("c1", "es", "grande", "duży"),
        "c2": entry("c2", "es", "amplio", "duży", "b1"),
        "c3": entry("c3", "es", "la raqueta", "rakieta"),
        "c4": entry("c4", "es", "el cohete", "rakieta", "a2"),
    }
    assert build.merge_duplicates(spanish, families) == 1
    assert spanish["c1"]["accept"] == ["amplio"]
    assert spanish["c3"]["hint"] == "ang. racket" and spanish["c4"]["hint"] == "ang. rocket"
    english = {
        "c3": entry("c3", "en", "racket", "rakieta"),
        "c4": entry("c4", "en", "rocket", "rakieta", "a2"),
    }
    assert build.merge_duplicates(english, families) == 1
    assert list(english) == ["c3"] and "hint" not in english["c3"]
