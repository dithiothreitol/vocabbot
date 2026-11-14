"""Grading of typed answers: every error class in every language of the starter course."""

from __future__ import annotations

import pytest
from conftest import entry_of

from vocabbot import answers
from vocabbot.courses import Catalog

CASES = [
    # language, concept number, answer, grade, first error
    ("de", 2, "der Hund", "know", None),
    ("de", 2, "Der Hund", "know", None),
    ("de", 2, "  der   Hund. ", "know", None),
    ("de", 2, "die Hund", "almost", "gender"),
    ("de", 2, "Hund", "almost", "article"),
    ("de", 2, "ein Hund", "almost", "article"),
    ("de", 2, "der hund", "almost", "case"),
    ("de", 2, "die Hunde", "almost", "form"),
    ("de", 2, "der Hnud", "dont_know", "wrong"),
    ("de", 12, "die Strasse", "know", None),
    ("de", 12, "die Strase", "almost", "typo"),
    ("de", 12, "die strasse", "almost", "case"),
    ("de", 57, "gluecklich", "know", None),
    ("de", 57, "glucklich", "almost", "diacritic"),
    ("de", 13, "der Wagen", "know", None),
    ("es", 4, "el agua", "know", None),
    ("es", 4, "la agua", "almost", "article"),
    ("es", 4, "agua", "almost", "article"),
    ("es", 2, "la perro", "almost", "gender"),
    ("es", 32, "pequeno", "almost", "diacritic"),
    ("es", 40, "si", "almost", "diacritic"),
    ("es", 16, "el ano", "almost", "diacritic"),
    ("es", 60, "a menudo", "know", None),
    ("es", 60, "con frecuencia", "know", None),
    ("es", 13, "el carro", "know", None),
    ("es", 32, "pequeña", "almost", "form"),
    ("es", 7, "la Manzana", "almost", "case"),
    ("es", 7, "la manzaan", "almost", "typo"),
    ("es", 7, "una manzana", "almost", "article"),
    ("fr", 4, "l'eau", "know", None),
    ("fr", 4, "l’eau", "know", None),
    ("fr", 4, "l' eau", "know", None),
    ("fr", 4, "leau", "almost", "article"),
    ("fr", 4, "le eau", "almost", "gender"),
    ("fr", 2, "la chien", "almost", "gender"),
    ("fr", 2, "chien", "almost", "article"),
    ("fr", 9, "l'ecole", "almost", "diacritic"),
    ("fr", 46, "la fenetre", "almost", "diacritic"),
    ("fr", 38, "aujourd'hui", "know", None),
    ("fr", 38, "aujourdhui", "almost", "typo"),
    ("fr", 45, "la clef", "know", None),
    ("fr", 57, "heureuse", "almost", "form"),
    ("fr", 1, "la Maison", "almost", "case"),
    ("fr", 1, "la maisno", "almost", "typo"),
    ("fr", 1, "une maison", "almost", "article"),
    ("fr", 3, "le chta", "dont_know", "wrong"),
    ("en", 2, "dog", "know", None),
    ("en", 2, "a dog", "know", None),
    ("en", 2, "the dog", "know", None),
    ("en", 2, "Dog", "know", None),
    ("en", 2, "dogs", "almost", "form"),
    ("en", 2, "dgo", "dont_know", "wrong"),
    ("en", 21, "to drink", "know", None),
    ("en", 21, "drank", "almost", "form"),
    ("en", 7, "aple", "almost", "typo"),
    ("en", 38, "Today", "know", None),
    ("en", 38, "TODAY", "almost", "case"),
    ("en", 39, "thanks", "know", None),
    ("en", 55, "to look for", "know", None),
    ("en", 31, "large", "know", None),
    ("en", 2, "", "dont_know", "blank"),
]


@pytest.mark.parametrize(("lang", "number", "given", "grade", "error"), CASES)
def test_grades(
    catalog: Catalog, lang: str, number: int, given: str, grade: str, error: str | None
) -> None:
    entry = entry_of(catalog, lang, number)
    verdict = answers.grade(given, entry)
    assert verdict.grade == grade, verdict
    assert (verdict.errors[0] if verdict.errors else None) == error, verdict


@pytest.mark.parametrize(
    ("lang", "number", "given", "other"),
    [
        ("de", 2, "el perro", "es"),
        ("de", 2, "perro", "es"),
        ("en", 2, "der Hund", "de"),
        ("es", 2, "le chien", "fr"),
        ("fr", 3, "the cat", "en"),
    ],
)
def test_answer_in_another_language(
    catalog: Catalog, lang: str, number: int, given: str, other: str
) -> None:
    entry = entry_of(catalog, lang, number)
    family = [e for e in catalog.family(entry["concept"]) if e["lang"] != lang]
    verdict = answers.grade(given, entry, siblings=family)
    assert verdict.grade == "dont_know"
    assert verdict.errors == ("wrong_language",)
    assert verdict.other_lang == other


def test_same_word_in_two_languages_is_right(catalog: Catalog) -> None:
    entry = entry_of(catalog, "es", 27)  # dormir in Spanish and French
    family = [e for e in catalog.family(entry["concept"]) if e["lang"] != "es"]
    assert answers.grade("dormir", entry, siblings=family).grade == "know"


def test_lenient_diacritics(catalog: Catalog) -> None:
    entry = entry_of(catalog, "es", 32)
    verdict = answers.grade("pequeno", entry, lenient=True)
    assert verdict.grade == "know"
    assert verdict.errors == ("diacritic",)


def test_two_substantive_errors_are_wrong(catalog: Catalog) -> None:
    entry = entry_of(catalog, "de", 12)
    assert answers.grade("der Strase", entry).grade == "dont_know"


def test_edit_distance() -> None:
    assert answers.edit_distance("abcde", "abced") == 1
    assert answers.edit_distance("abc", "abc") == 0
    assert answers.edit_distance("abc", "xyz") == 2
