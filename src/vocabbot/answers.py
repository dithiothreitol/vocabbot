"""Grading a typed answer against a course entry.

The engine, not the model, decides how good an answer was. An exact answer is
"know"; one small difference (a missing accent, one typo in a longer word,
another article of the right gender, the wrong letter case, another form of
the same word) is "almost"; anything else is "dont_know". The gender belongs
to a German, Spanish or French noun, so an article of another gender, or no
article where the article shows the gender or the plural, is "dont_know" too.
The error classes go to the review log, where status and the coach read them.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from functools import cache
from typing import Any

from vocabbot import assets

KNOW, ALMOST, DONT_KNOW = "know", "almost", "dont_know"
GRADE_RANK = {KNOW: 0, ALMOST: 1, DONT_KNOW: 2}
ERROR_CLASSES = (
    "blank",
    "case",
    "diacritic",
    "typo",
    "article",
    "no_article",
    "gender",
    "form",
    "reflexive",
    "wrong_language",
    "wrong",
)
# errors that make an answer "dont_know" on their own
HARD_ERRORS = frozenset({"wrong", "wrong_language", "blank", "gender", "no_article"})
TYPO_MIN_LENGTH = 5

_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "‘": "'", "´": "'", "`": "'"})
_EDGE = ' .,!?;:¡¿"«»„”“'


@dataclass(frozen=True)
class Rules:
    """How answers in one language are compared (data/lang/<code>.json)."""

    code: str
    articles: dict[str, str]
    plural_articles: tuple[str, ...]
    other_articles: tuple[str, ...]
    elided: str | None
    nouns_capitalized: bool
    feminine_el: bool
    substitutions: tuple[tuple[str, str], ...]
    optional_prefixes: dict[str, tuple[str, ...]]
    reflexive_prefixes: tuple[str, ...] = ()
    reflexive_suffix: str | None = None
    indefinite: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # other forms of a definite singular article and their gender: Italian lo (lo studente)
    article_variants: dict[str, str] = field(default_factory=dict)
    # elided articles besides the definite one: Italian un' (un'amica)
    other_elided: tuple[str, ...] = ()
    # what replaces the reflexive suffix in the plain verb: Italian lavarsi, lavare
    reflexive_base: str = ""

    @property
    def elided_forms(self) -> tuple[str, ...]:
        return ((self.elided,) if self.elided else ()) + self.other_elided

    @property
    def article_words(self) -> frozenset[str]:
        words = set(self.articles.values()) | set(self.plural_articles) | set(self.other_articles)
        words |= set(self.article_variants)
        for prefixes in self.optional_prefixes.values():
            words |= set(prefixes)
        return frozenset(words)

    def gender_of(self, article: str) -> str | None:
        """Gender of a definite singular article, or None for any other word."""
        folded = article.casefold()
        for gender, word in self.articles.items():
            if word == folded:
                return gender
        return self.article_variants.get(folded)

    def genders_of(self, article: str) -> frozenset[str]:
        """What an article can go with: 'der' {m}, 'die' {f, pl}, 'ein' {m, n}; {} if unknown."""
        folded = article.casefold()
        found = {gender for gender, word in self.articles.items() if word == folded}
        if folded in self.article_variants:
            found.add(self.article_variants[folded])
        if folded in self.plural_articles:
            found.add("pl")
        found.update(self.indefinite.get(folded, ()))
        return frozenset(found)

    def shows_gender(self, article: str, gender: str | None) -> bool:
        """The citation article tells the gender or the plural: der, la, les; not l' or el agua."""
        if gender is None or article == self.elided:
            return False
        if gender == "pl":
            return article.casefold() in self.plural_articles
        return self.gender_of(article) == gender


@cache
def rules(code: str) -> Rules:
    data = assets.language(code)
    return Rules(
        code=code,
        articles=dict(data.get("articles", {})),
        plural_articles=tuple(data.get("plural_articles", ())),
        other_articles=tuple(data.get("other_articles", ())),
        elided=data.get("elided_article"),
        nouns_capitalized=bool(data.get("nouns_capitalized", False)),
        feminine_el=bool(data.get("feminine_el", False)),
        substitutions=tuple((a, b) for a, b in data.get("substitutions", ())),
        optional_prefixes={k: tuple(v) for k, v in data.get("optional_prefixes", {}).items()},
        reflexive_prefixes=tuple(data.get("reflexive", {}).get("prefixes", ())),
        reflexive_suffix=data.get("reflexive", {}).get("suffix"),
        indefinite={k: tuple(v) for k, v in data.get("indefinite_articles", {}).items()},
        article_variants=dict(data.get("article_variants", {})),
        other_elided=tuple(data.get("other_elided_articles", ())),
        reflexive_base=str(data.get("reflexive", {}).get("base", "")),
    )


def without_reflexive(expected: str, entry: dict[str, Any], lang: Rules) -> str | None:
    """'ändern' for 'sich ändern', 'laver' for 'se laver', 'levantar' for 'levantarse'."""
    if entry.get("pos") != "verb":
        return None
    low = expected.casefold()
    for prefix in lang.reflexive_prefixes:
        joined = prefix.endswith("'")
        if low.startswith(prefix if joined else prefix + " "):
            rest = expected[len(prefix) if joined else len(prefix) + 1 :]
            return rest or None
    suffix = lang.reflexive_suffix
    if suffix and low.endswith(suffix) and len(low) > len(suffix) + 2 and " " not in low:
        return expected[: -len(suffix)] + lang.reflexive_base
    return None


@dataclass(frozen=True)
class Verdict:
    """The engine's grade of one typed answer."""

    grade: str
    errors: tuple[str, ...] = ()
    matched: str | None = None
    other_lang: str | None = None

    def key(self) -> tuple[int, int, tuple[str, ...]]:
        return (GRADE_RANK[self.grade], len(self.errors), self.errors)


def normalize(text: str) -> str:
    """One space between words, straight apostrophes, no punctuation at the ends."""
    cleaned = unicodedata.normalize("NFC", text).translate(_APOSTROPHES)
    cleaned = " ".join(cleaned.split()).strip(_EDGE)
    return re.sub(r"'\s+", "'", cleaned)


def plain(text: str) -> str:
    """The text without accents and other combining marks."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    )


def substitute(text: str, lang: Rules) -> str:
    for letter, replacement in lang.substitutions:
        text = text.replace(letter, replacement)
    return text


def edit_distance(a: str, b: str) -> int:
    """Optimal string alignment distance, capped at 2 (only 0, 1 and more matter)."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 1:
        return 2
    before: list[int] = []
    previous = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        current = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                current[j] = min(current[j], before[j - 2] + 1)
        before, previous = previous, current
    return min(previous[len(b)], 2)


def split_article(text: str, lang: Rules) -> tuple[str | None, str]:
    """('der', 'Hund') for 'der Hund'; (None, text) when no article leads."""
    folded = text.casefold()
    for elided in lang.elided_forms:
        if folded.startswith(elided) and len(text) > len(elided):
            return text[: len(elided)], text[len(elided) :]
    head, sep, rest = text.partition(" ")
    if sep and rest and head.casefold() in lang.article_words:
        return head, rest
    return None, text


def _case_differs(given: str, expected: str, initial: bool) -> bool:
    if given.casefold() != expected.casefold():
        pairs = [(given[:1], expected[:1])]
    else:
        pairs = list(zip(given, expected, strict=False))
    for index, (g, e) in enumerate(pairs):
        if g == e or g.casefold() != e.casefold():
            continue
        if index == 0 and initial and g.isupper() and not e.isupper():
            continue
        return True
    return False


def core_errors(
    given: str, expected: str, lang: Rules, *, initial: bool, typo_length: int | None = None
) -> list[str]:
    """Error classes between two words or phrases.

    `typo_length` is the length of the word itself when `expected` carries an
    article, so that the article does not make a short word count as long.
    """
    if given == expected:
        return []
    g, e = substitute(given, lang), substitute(expected, lang)
    if g == e:
        return []
    errors: list[str] = []
    if g.casefold() != e.casefold():
        g_plain, e_plain = plain(g.casefold()), plain(e.casefold())
        g_raw, e_raw = plain(given.casefold()), plain(expected.casefold())
        length = len(e_plain) if typo_length is None else typo_length
        if g_plain == e_plain or g_raw == e_raw:
            errors.append("diacritic")
        elif (
            length >= TYPO_MIN_LENGTH
            and min(edit_distance(g_plain, e_plain), edit_distance(g_raw, e_raw)) <= 1
        ):
            errors.append("typo")
        else:
            return ["wrong"]
    if _case_differs(g, e, initial):
        errors.append("case")
    return errors


def article_errors(
    given: str | None, expected: str | None, entry: dict[str, Any], lang: Rules
) -> list[str] | None:
    """Errors in the article, or None when the split comparison does not apply."""
    optional = lang.optional_prefixes.get(str(entry.get("pos", "")), ())
    if expected is None:
        if given is None or given.casefold() in optional:
            return []
        if entry.get("bare") and given.casefold() in lang.article_words:
            return ["article"]  # "el enero" for "enero"
        return None
    gender = str(entry["gender"]) if entry.get("gender") else None
    if given is None:
        return ["no_article"] if lang.shows_gender(expected, gender) else ["article"]
    if given.casefold() == expected.casefold():
        return []
    genders = lang.genders_of(given)
    # "un agua" for "el agua" is right: a feminine noun with a stressed a takes el and un
    euphonic = lang.feminine_el and gender == "f" and expected.casefold() == "el"
    if gender is not None and genders and gender not in genders and not euphonic:
        return ["gender"]
    return ["article"]


def grade_from(errors: Iterable[str], *, lenient: bool = False) -> str:
    counted = [e for e in errors if not (lenient and e == "diacritic")]
    if not counted:
        return KNOW
    if HARD_ERRORS.intersection(counted):
        return DONT_KNOW
    substantive = [e for e in counted if e != "case"]
    return ALMOST if len(substantive) <= 1 else DONT_KNOW


def _comparisons(
    given: str, expected: str, entry: dict[str, Any], lang: Rules, lenient: bool
) -> Iterator[Verdict]:
    g_article, g_core = split_article(given, lang)
    e_article, e_core = split_article(expected, lang)
    whole = core_errors(given, expected, lang, initial=True, typo_length=len(plain(e_core)))
    if g_article is None or e_article is None or g_article.casefold() == e_article.casefold():
        # "la livre" for "le livre" is one letter away, but the article is not a typo
        yield Verdict(grade_from(whole, lenient=lenient), tuple(whole), expected)
    if (
        e_article is not None
        and e_article == lang.elided
        and g_article is None
        and given.casefold().startswith(e_article[0])
    ):
        # "leau" for "l'eau": the elided article without its apostrophe
        core = core_errors(given[1:], e_core, lang, initial=False)
        if "wrong" not in core:
            errors = ["article", *core]
            yield Verdict(grade_from(errors, lenient=lenient), tuple(errors), expected)
    if g_article is None and e_article is None:
        return
    articles = article_errors(g_article, e_article, entry, lang)
    if articles is None:
        return
    core = core_errors(g_core, e_core, lang, initial=g_article is None)
    if "wrong" in core:
        yield Verdict(DONT_KNOW, tuple(articles + core), expected)
        return
    errors = articles + core
    yield Verdict(grade_from(errors, lenient=lenient), tuple(errors), expected)


def _best(
    given: str, forms: Iterable[str], entry: dict[str, Any], lang: Rules, lenient: bool
) -> Verdict:
    best = Verdict(DONT_KNOW, ("wrong",))
    for form in forms:
        expected = normalize(form)
        if not expected:
            continue
        for verdict in _comparisons(given, expected, entry, lang, lenient):
            if verdict.key() < best.key():
                best = verdict
    return best


# the classes of "almost" that may come from the spelling of another language; the others
# ("form", "article", "case", "reflexive") mean a right word of the card's own language
SPELLING_SLIPS = frozenset({"typo", "diacritic"})


def _spelled_elsewhere(
    given: str, verdict: Verdict, siblings: list[dict[str, Any]], near: set[str]
) -> Verdict:
    """An "almost" that is exactly the word of another language being learned names it."""
    if verdict.grade != ALMOST or not SPELLING_SLIPS.intersection(verdict.errors):
        return verdict
    for sibling in siblings:
        code = str(sibling["lang"])
        if code not in near:
            continue
        candidates = [*accepted_forms(sibling), str(sibling.get("lemma") or "")]
        if _best(given, candidates, sibling, rules(code), lenient=False).grade == KNOW:
            return replace(verdict, other_lang=code)
    return verdict


def accepted_forms(entry: dict[str, Any]) -> list[str]:
    forms = [str(entry["display"])]
    forms += [str(a) for a in entry.get("accept", ()) if a not in forms]
    return forms


def grade(
    answer: str,
    entry: dict[str, Any],
    *,
    lenient: bool = False,
    siblings: Iterable[dict[str, Any]] = (),
    near: Iterable[str] = (),
) -> Verdict:
    """Grade a typed answer to a production card of `entry`.

    `siblings` are entries of the same concept in other languages; an answer
    that matches one of them is reported as given in that language. `near`
    names the other languages the learner is learning: an answer one letter
    or one accent away ("sempre" for "siempre") keeps its grade "almost", and
    when it is exactly the word of one of these languages the verdict names
    that language too. For a learner of Spanish alone "sempre" stays a typo.
    """
    siblings = list(siblings)
    lang = rules(str(entry["lang"]))
    given = normalize(answer)
    if not given:
        return Verdict(DONT_KNOW, ("blank",))
    best = _best(given, accepted_forms(entry), entry, lang, lenient)
    if best.grade == KNOW:
        return best
    forms = [str(f) for f in (entry.get("forms") or {}).values()]
    other_form = _best(given, forms, entry, lang, lenient=True)
    if other_form.grade == KNOW and (best.grade == DONT_KNOW or "typo" in best.errors):
        # "drank" for "drink" is another form of the word, not a typo
        return Verdict(ALMOST, ("form",), other_form.matched)
    if best.grade != DONT_KNOW:
        return _spelled_elsewhere(given, best, siblings, set(near))
    for form in accepted_forms(entry):
        base = without_reflexive(normalize(form), entry, lang)
        if base and _best(given, [base], entry, lang, lenient=True).grade == KNOW:
            return Verdict(ALMOST, ("reflexive",), form)
    for sibling in siblings:
        sibling_lang = rules(str(sibling["lang"]))
        candidates = [*accepted_forms(sibling), str(sibling.get("lemma") or "")]
        match = _best(given, candidates, sibling, sibling_lang, lenient=True)
        if match.grade != DONT_KNOW and "typo" not in match.errors:
            return Verdict(DONT_KNOW, ("wrong_language",), match.matched, str(sibling["lang"]))
    return best
