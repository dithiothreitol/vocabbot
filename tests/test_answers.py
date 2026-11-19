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
    ("de", 2, "die Hund", "dont_know", "gender"),
    ("de", 2, "Hund", "dont_know", "no_article"),
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
    ("es", 2, "la perro", "dont_know", "gender"),
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
    ("fr", 4, "le eau", "dont_know", "gender"),
    ("fr", 2, "la chien", "dont_know", "gender"),
    ("fr", 2, "chien", "dont_know", "no_article"),
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


@pytest.mark.parametrize(
    ("lang", "number", "given", "near", "errors", "other"),
    [
        # one letter from the card's word and exactly the word of another language of the plan
        ("es", 31, "grand", ("fr",), ("typo",), "fr"),
        ("es", 59, "facile", ("fr", "en"), ("typo",), "fr"),
        # the same slip without French in the plan is a typo
        ("es", 31, "grand", (), ("typo",), None),
        ("es", 31, "grand", ("de",), ("typo",), None),
        # "grande" is the feminine form of French "grand", a word of the card's own language
        ("fr", 31, "grande", ("es",), ("form",), None),
        # a missing accent that is no word of another language stays a diacritic
        ("es", 59, "facil", ("fr",), ("diacritic",), None),
    ],
)
@pytest.mark.parametrize("lenient", [False, True])
def test_a_slip_into_another_language_keeps_its_grade(
    catalog: Catalog,
    lang: str,
    number: int,
    given: str,
    near: tuple[str, ...],
    errors: tuple[str, ...],
    other: str | None,
    lenient: bool,
) -> None:
    entry = entry_of(catalog, lang, number)
    family = [e for e in catalog.family(entry["concept"]) if e["lang"] != lang]
    verdict = answers.grade(given, entry, lenient=lenient, siblings=family, near=near)
    before = answers.grade(given, entry, lenient=lenient, siblings=family)
    # the grade and the error classes are those of the grading before Stage 14
    assert (verdict.grade, verdict.errors) == (before.grade, before.errors)
    assert verdict.errors == errors
    assert verdict.other_lang == other
    if not (lenient and errors == ("diacritic",)):
        assert verdict.grade == "almost"


def test_a_word_of_another_language_still_needs_no_plan(catalog: Catalog) -> None:
    entry = entry_of(catalog, "es", 20)  # la mano; French la main
    family = [e for e in catalog.family(entry["concept"]) if e["lang"] != "es"]
    for near in ((), ("fr",)):
        verdict = answers.grade("la main", entry, siblings=family, near=near)
        assert (verdict.grade, verdict.errors, verdict.other_lang) == (
            "dont_know",
            ("wrong_language",),
            "fr",
        )


def test_same_word_in_two_languages_is_right(catalog: Catalog) -> None:
    entry = entry_of(catalog, "es", 27)  # dormir in Spanish and French
    family = [e for e in catalog.family(entry["concept"]) if e["lang"] != "es"]
    assert answers.grade("dormir", entry, siblings=family).grade == "know"


@pytest.mark.parametrize(
    ("lang", "display", "given", "grade"),
    [
        ("de", "sich ändern", "ändern", "almost"),
        ("de", "sich ändern", "sich ändern", "know"),
        ("fr", "se laver", "laver", "almost"),
        ("fr", "s'habiller", "habiller", "almost"),
        ("es", "levantarse", "levantar", "almost"),
        ("es", "levantarse", "levantarse", "know"),
    ],
)
def test_reflexive_verbs(lang: str, display: str, given: str, grade: str) -> None:
    entry = {"lang": lang, "pos": "verb", "display": display, "lemma": display}
    verdict = answers.grade(given, entry)
    assert verdict.grade == grade
    if grade == "almost":
        assert verdict.errors == ("reflexive",)


def test_spanish_noun_ending_in_se_is_not_reflexive() -> None:
    entry = {"lang": "es", "pos": "noun", "display": "la clase", "lemma": "clase", "gender": "f"}
    assert answers.grade("la cla", entry).grade == "dont_know"


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


def noun(lang: str, display: str, gender: str, **extra: object) -> dict:
    lemma = display.split(" ", 1)[-1].removeprefix("l'")
    return {
        "lang": lang,
        "pos": "noun",
        "display": display,
        "lemma": lemma,
        "gender": gender,
        **extra,
    }


@pytest.mark.parametrize(
    ("entry", "given", "grade", "errors"),
    [
        # an article one letter away is still another gender, not a typo
        (noun("fr", "le livre", "m"), "la livre", "dont_know", ("gender",)),
        (noun("de", "der Hund", "m"), "eine Hund", "dont_know", ("gender",)),
        (noun("de", "das Kind", "n"), "ein Kind", "almost", ("article",)),
        # a feminine noun with a stressed a takes el and un
        (noun("es", "el agua", "f"), "un agua", "almost", ("article",)),
        (noun("es", "el agua", "f"), "agua", "almost", ("article",)),
        # the elided article does not show the gender, so leaving it out is a small error
        (noun("fr", "l'eau", "f"), "eau", "almost", ("article",)),
        # nouns used only in the plural
        (noun("de", "die Eltern", "pl"), "die Eltern", "know", ()),
        (noun("de", "die Eltern", "pl"), "der Eltern", "dont_know", ("gender",)),
        (noun("de", "die Eltern", "pl"), "Eltern", "dont_know", ("no_article",)),
        (noun("fr", "les gens", "pl"), "le gens", "dont_know", ("gender",)),
        # months without an article
        (noun("es", "enero", "m", bare=True), "enero", "know", ()),
        (noun("es", "enero", "m", bare=True), "el enero", "almost", ("article",)),
    ],
)
def test_articles_and_genders(entry: dict, given: str, grade: str, errors: tuple) -> None:
    verdict = answers.grade(given, entry)
    assert (verdict.grade, verdict.errors) == (grade, errors), verdict


def test_genders_an_article_can_show() -> None:
    german = answers.rules("de")
    assert german.genders_of("die") == {"f", "pl"}
    assert german.genders_of("ein") == {"m", "n"}
    assert german.genders_of("den") == frozenset()
    assert german.shows_gender("der", "m") and german.shows_gender("die", "pl")
    assert not answers.rules("fr").shows_gender("l'", "f")
    assert not answers.rules("es").shows_gender("el", "f")  # el agua


ITALIAN = {
    "studente": {
        "lang": "it",
        "display": "lo studente",
        "lemma": "studente",
        "pos": "noun",
        "gender": "m",
    },
    "amica": {"lang": "it", "display": "l'amica", "lemma": "amica", "pos": "noun", "gender": "f"},
    "cane": {"lang": "it", "display": "il cane", "lemma": "cane", "pos": "noun", "gender": "m"},
    "lavarsi": {"lang": "it", "display": "lavarsi", "lemma": "lavarsi", "pos": "verb"},
}


@pytest.mark.parametrize(
    ("word", "given", "grade", "errors"),
    [
        ("studente", "lo studente", "know", ()),
        ("studente", "il studente", "almost", ("article",)),
        ("studente", "la studente", "dont_know", ("gender",)),
        ("studente", "studente", "dont_know", ("no_article",)),
        ("amica", "l'amica", "know", ()),
        ("amica", "un'amica", "almost", ("article",)),
        ("cane", "il cane", "know", ()),
        ("cane", "la cane", "dont_know", ("gender",)),
        ("lavarsi", "lavare", "almost", ("reflexive",)),
    ],
)
def test_italian_articles_and_reflexive_verbs(
    word: str, given: str, grade: str, errors: tuple[str, ...]
) -> None:
    verdict = answers.grade(given, ITALIAN[word])
    assert (verdict.grade, verdict.errors) == (grade, errors)


def test_italian_lo_shows_the_gender() -> None:
    rules = answers.rules("it")
    assert rules.gender_of("lo") == "m" and rules.shows_gender("lo", "m")
    assert rules.genders_of("gli") == frozenset({"pl"})
    assert not rules.shows_gender("l'", "f")
