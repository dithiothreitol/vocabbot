"""Courses: the packaged word lists and the learner's own words.

A course is data: data/courses/<lang>/<level>.jsonl with one entry per line
and meta.json with sources, version and licence. Entries of different
languages share a concept id, which makes them one family. A card is an entry
with a direction: <entry id>#p asks for the word (production), #r for its
meaning (recognition).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from vocabbot import assets, store
from vocabbot.answers import accepted_forms, rules, split_article

LEVELS = store.LEVELS
LEVEL_ORDER = {level: index for index, level in enumerate((*LEVELS, "own"))}
POS = (
    "noun",
    "verb",
    "adj",
    "adv",
    "pron",
    "prep",
    "conj",
    "num",
    "det",
    "interj",
    "particle",
    "phrase",
    "other",
)
FORM_KEYS = (
    "plural",
    "feminine",
    "past",
    "participle",
    "present_1sg",
    "present_3sg",
    "comparative",
)
# "pl" is a noun used only in the plural, shown with the plural article (die Eltern)
GENDERS = {
    "de": ("m", "f", "n", "pl"),
    "es": ("m", "f", "pl"),
    "fr": ("m", "f", "pl"),
    "it": ("m", "f", "pl"),
}
ENTRY_ID = re.compile(r"^(?P<lang>[a-z]{2})-(?P<concept>c\d{5}|u[0-9a-f]{6})$")
CARD_ID = re.compile(r"^(?P<entry>[a-z]{2}-(?:c\d{5}|u[0-9a-f]{6}))#(?P<direction>[pr])$")
IPA = re.compile(r"^(/[^/]+/|\[[^\]]+\])$")
GAP = "___"


def card_id(entry_id: str, direction: str) -> str:
    return f"{entry_id}#{direction}"


def split_card(card: str) -> tuple[str, str]:
    match = CARD_ID.match(card)
    if not match:
        raise ValueError(card)
    return match["entry"], match["direction"]


def _gap_pattern(gap: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(gap)}(?!\w)")


class Catalog:
    """All entries a learner can meet: installed courses and own words."""

    def __init__(
        self,
        root: assets.Resource | None = None,
        learner: Path | None = None,
        base: Catalog | None = None,
    ) -> None:
        """`base` is a catalog of the same courses already in memory: this one shares its
        course entries (they are never changed) and adds only the learner's own words."""
        self.base = base
        self.root: assets.Resource = (
            base.root if base is not None else root if root is not None else assets.course_root()
        )
        self.learner = learner
        self.problems: list[str] = []
        self._loaded = False
        self._entries: dict[str, dict[str, Any]] = {}
        self._course: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self._own: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # own words and course words the learner moved forward, in the order of own.jsonl
        self._first: dict[str, list[str]] = defaultdict(list)
        self._concepts: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._meta: dict[str, dict[str, Any]] = {}

    # ---------------------------------------------------------------- loading

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.base is not None:
            self.base._load()
            self.problems = list(self.base.problems)
            self._entries = dict(self.base._entries)
            self._course = self.base._course
            self._concepts = defaultdict(list, self.base._concepts)
            self._meta = self.base._meta
        elif self.root.is_dir():
            for folder in sorted(self.root.iterdir(), key=lambda item: item.name):
                if not folder.is_dir() or not (folder / "meta.json").is_file():
                    continue
                lang = folder.name
                self._meta[lang] = assets.read_json(folder / "meta.json")
                for level in LEVELS:
                    resource = folder / f"{level}.jsonl"
                    if resource.is_file():
                        self._add_lines(
                            resource.read_text(encoding="utf-8"), f"{lang}/{level}", own=False
                        )
        if self.learner is not None:
            courses = self.learner / "courses"
            if courses.is_dir():
                for folder in sorted(courses.iterdir()):
                    own = folder / "own.jsonl"
                    if own.is_file():
                        rows, damaged = store.read_jsonl(own)
                        for number in damaged:
                            self.problems.append(
                                f"{folder.name}/own.jsonl line {number} is damaged"
                            )
                        for row in rows:
                            if "ref" in row:
                                self._add_ref(row, folder.name)
                            else:
                                self._add(row, own=True)
        if self.base is None:
            for items in self._course.values():
                items.sort(key=lambda e: int(e.get("rank", 0)))

    def _add_ref(self, row: dict[str, Any], lang: str) -> None:
        """A course word the learner moved forward with `words add`."""
        ref = row.get("ref")
        entry = self._entries.get(ref) if isinstance(ref, str) else None
        if entry is None or entry.get("lang") != lang:
            self.problems.append(f"{lang}/own.jsonl names {ref!r}, which is not a {lang} entry")
        elif ref not in self._first[lang]:
            self._first[lang].append(str(ref))

    def _add_lines(self, text: str, label: str, own: bool) -> None:
        for number, line in enumerate(text.split("\n"), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                self.problems.append(f"{label} line {number} is damaged")
                continue
            if isinstance(entry, dict):
                self._add(entry, own=own)

    def _add(self, entry: dict[str, Any], own: bool) -> None:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or entry_id in self._entries:
            self.problems.append(f"entry {entry_id!r} is missing an id or appears twice")
            return
        self._entries[entry_id] = entry
        if own:
            self._own[str(entry.get("lang"))].append(entry)
            self._first[str(entry.get("lang"))].append(entry_id)
        else:
            self._course[(str(entry.get("lang")), str(entry.get("level")))].append(entry)
        if isinstance(entry.get("concept"), str):
            # a new list, so a catalog that shares the lists of its base never changes them
            concept = entry["concept"]
            self._concepts[concept] = [*self._concepts.get(concept, []), entry]

    # ---------------------------------------------------------------- reading

    def installed(self) -> dict[str, list[str]]:
        """Course languages and their levels."""
        self._load()
        out: dict[str, list[str]] = {}
        for lang in self._meta:
            out[lang] = [level for level in LEVELS if self._course.get((lang, level))]
        return out

    def meta(self, lang: str) -> dict[str, Any]:
        self._load()
        return self._meta.get(lang, {})

    def course(self, lang: str, levels: list[str]) -> list[dict[str, Any]]:
        self._load()
        out: list[dict[str, Any]] = []
        for level in LEVELS:
            if level in levels:
                out += self._course.get((lang, level), [])
        return out

    def own(self, lang: str) -> list[dict[str, Any]]:
        self._load()
        return list(self._own.get(lang, []))

    def first(self, lang: str) -> list[dict[str, Any]]:
        """Entries that come before the course: own words and course words moved forward."""
        self._load()
        return [self._entries[entry_id] for entry_id in self._first.get(lang, [])]

    def moved_forward(self, lang: str) -> set[str]:
        """Ids of course entries the learner moved forward."""
        self._load()
        own = {str(e["id"]) for e in self._own.get(lang, [])}
        return {entry_id for entry_id in self._first.get(lang, []) if entry_id not in own}

    def entry(self, entry_id: str) -> dict[str, Any] | None:
        self._load()
        return self._entries.get(entry_id)

    def card(self, card: str) -> dict[str, Any] | None:
        match = CARD_ID.match(card)
        return self.entry(match["entry"]) if match else None

    def family(self, concept: str) -> list[dict[str, Any]]:
        self._load()
        return list(self._concepts.get(concept, []))

    def entries(self) -> list[dict[str, Any]]:
        self._load()
        return list(self._entries.values())


# ---------------------------------------------------------------- prompts


def gap_sentence(entry: dict[str, Any]) -> str | None:
    example = entry.get("example") or {}
    text, gap = example.get("text"), example.get("gap")
    if not text or not gap:
        return None
    return _gap_pattern(str(gap)).sub(GAP, str(text), count=1)


def needs_article(entry: dict[str, Any]) -> bool:
    if entry.get("pos") != "noun" or entry.get("bare"):
        return False  # "enero", "janvier": a month goes without an article
    return bool(rules(str(entry["lang"])).articles)


def question(entry: dict[str, Any], direction: str) -> dict[str, Any]:
    """What the learner sees before answering. It never holds the answer."""
    example = entry.get("example") or {}
    if direction == "p":
        out: dict[str, Any] = {
            "ask": "word",
            "meaning": entry["gloss"]["pl"],
            "pos": entry.get("pos"),
            "with_article": needs_article(entry),
        }
        if entry.get("hint"):
            out["hint"] = entry["hint"]
        if gap_sentence(entry):
            out["sentence"] = gap_sentence(entry)
            out["sentence_pl"] = example.get("pl")
        return out
    out = {"ask": "meaning", "word": entry["display"], "pos": entry.get("pos")}
    if example.get("text"):
        out["sentence"] = example["text"]
    return out


def hide_other_answers(catalog: Catalog, items: list[dict[str, Any]]) -> None:
    """A question whose sentence holds the answer of another card asked with it loses the sentence.

    Only cards that ask for the word (`#p`) have an answer to keep back; the
    sentence goes together with its translation.
    """
    answers_by_card: dict[str, list[str]] = {}
    for item in items:
        entry = catalog.card(item["card"])
        if entry is not None and str(item["card"]).endswith("#p"):
            forms = [*accepted_forms(entry), str(entry.get("lemma") or "")]
            answers_by_card[item["card"]] = [f for f in forms if len(f) >= 2]
    for item in items:
        sentence = item["question"].get("sentence")
        if not sentence:
            continue
        for card, forms in answers_by_card.items():
            if card == item["card"]:
                continue
            if any(
                re.search(rf"(?<!\w){re.escape(f)}(?!\w)", sentence, re.IGNORECASE) for f in forms
            ):
                item["question"].pop("sentence", None)
                item["question"].pop("sentence_pl", None)
                break


def presentation(entry: dict[str, Any]) -> dict[str, Any]:
    """Everything about a word: shown when a new word is introduced and after an answer."""
    out: dict[str, Any] = {
        "word": entry["display"],
        "meaning": entry["gloss"]["pl"],
        "pos": entry.get("pos"),
    }
    for key in ("gender", "ipa", "hint"):
        if entry.get(key):
            out[key] = entry[key]
    if entry.get("forms"):
        out["forms"] = entry["forms"]
    if entry.get("accept"):
        out["also"] = entry["accept"]
    example = entry.get("example") or {}
    if example.get("text"):
        out["example"] = example["text"]
        if example.get("pl"):
            out["example_pl"] = example["pl"]
    return out


# ---------------------------------------------------------------- checks


def entry_problems(entry: dict[str, Any], *, own: bool = False) -> list[str]:
    """What is wrong with one entry; own words need fewer fields."""
    problems: list[str] = []
    entry_id = str(entry.get("id"))
    match = ENTRY_ID.match(entry_id)
    lang = entry.get("lang")
    if not match:
        problems.append("id must look like de-c00042 or de-u3f9a1c")
    elif match["lang"] != lang:
        problems.append("the id does not start with the entry's language")
    elif not own and entry.get("concept") != match["concept"]:
        problems.append("the id does not end with the entry's concept")
    if lang not in assets.known_languages():
        return [*problems, f"no answer rules for language {lang!r}"]
    if not isinstance(entry.get("concept"), str) or not entry["concept"]:
        problems.append("concept is missing")
    level = entry.get("level")
    if level not in ((*LEVELS, "own") if own else LEVELS):
        problems.append(f"level {level!r} is not one of {', '.join(LEVELS)}")
    rank = entry.get("rank")
    if not own and (isinstance(rank, bool) or not isinstance(rank, int) or rank < 1):
        problems.append("rank must be a whole number from 1")
    pos = entry.get("pos")
    if pos not in POS:
        problems.append(f"pos {pos!r} is not one of {', '.join(POS)}")
    display = entry.get("display")
    if not isinstance(display, str) or not display.strip():
        return [*problems, "display is missing"]
    if not isinstance(entry.get("lemma"), str) or not entry["lemma"].strip():
        problems.append("lemma is missing")
    gloss = entry.get("gloss")
    if (
        not isinstance(gloss, dict)
        or not isinstance(gloss.get("pl"), str)
        or not gloss["pl"].strip()
    ):
        problems.append("gloss.pl is missing")
    if pos == "noun" and lang in GENDERS:
        problems += _noun_problems(entry, str(lang), display)
    accept = entry.get("accept", [])
    if not isinstance(accept, list) or any(not isinstance(a, str) or not a.strip() for a in accept):
        problems.append("accept must be a list of answers")
    forms = entry.get("forms", {})
    if not isinstance(forms, dict) or any(
        k not in FORM_KEYS or not isinstance(v, str) or not v.strip() for k, v in forms.items()
    ):
        problems.append(f"forms may only hold {', '.join(FORM_KEYS)} as text")
    # pronunciation and an example are wanted, not required: course check counts them
    ipa = entry.get("ipa")
    if ipa is not None and (not isinstance(ipa, str) or not IPA.match(ipa)):
        problems.append("ipa must be written between slashes or square brackets")
    example = entry.get("example")
    if example is not None:
        problems += _example_problems(example)
    sources = entry.get("sources")
    if not own and (not isinstance(sources, list) or not sources):
        problems.append("sources are missing")
    if not isinstance(entry.get("checked", False), bool):
        problems.append("checked must be true or false")
    return problems


def _noun_problems(entry: dict[str, Any], lang: str, display: str) -> list[str]:
    lang_rules = rules(lang)
    gender = entry.get("gender")
    if gender not in GENDERS[lang]:
        return [f"gender must be one of {', '.join(GENDERS[lang])}"]
    if entry.get("bare"):
        if split_article(display, lang_rules)[0] is not None or gender == "pl":
            return ["a noun marked bare is shown without an article"]
        return []
    article, core = split_article(display, lang_rules)
    if article is None:
        return ["a noun is shown with its definite article"]
    problems: list[str] = []
    if gender == "pl":
        if article.casefold() not in lang_rules.plural_articles:
            problems.append(f"a plural noun takes {' or '.join(lang_rules.plural_articles)}")
    elif article == lang_rules.elided:
        if core[:1].lower() not in "aeiouyhâàäéèêëîïôöûüœ":
            problems.append("the elided article stands only before a vowel or h")
    elif (
        article != lang_rules.articles.get(str(gender))
        and lang_rules.article_variants.get(article.casefold()) != gender
    ):
        stressed_a = core.lower().startswith(("a", "á", "ha", "há"))
        if not (lang_rules.feminine_el and gender == "f" and article == "el" and stressed_a):
            problems.append(f"the article {article!r} does not match gender {gender!r}")
    if lang_rules.nouns_capitalized and not core[:1].isupper():
        problems.append("the noun must start with a capital letter")
    return problems


def _example_problems(example: Any) -> list[str]:
    if not isinstance(example, dict):
        return ["example must be an object"]
    problems: list[str] = []
    text, gap = example.get("text"), example.get("gap")
    if not isinstance(text, str) or not text.strip():
        problems.append("example.text is missing")
    elif not isinstance(gap, str) or not gap.strip():
        problems.append("example.gap is missing")
    elif len(_gap_pattern(gap).findall(text)) != 1:
        problems.append(f"example.gap {gap!r} must appear once as a whole word in the text")
    if not isinstance(example.get("pl"), str) or not example["pl"].strip():
        problems.append("example.pl is missing")
    return problems


def check(catalog: Catalog) -> dict[str, Any]:
    """Structure and consistency of every installed course and of the own words."""
    errors: list[str] = list(catalog.problems)
    warnings: list[str] = []
    counts: dict[str, dict[str, int]] = defaultdict(dict)
    coverage: dict[str, Counter[str]] = defaultdict(Counter)
    seen_rank: set[tuple[str, str, int]] = set()
    meanings: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    entries = catalog.entries()
    ids = {str(e.get("id")) for e in entries}
    for entry in entries:
        own = entry.get("level") == "own" or str(entry.get("id", "")).split("-")[-1].startswith("u")
        label = str(entry.get("id"))
        for problem in entry_problems(entry, own=own):
            errors.append(f"{label}: {problem}")
        lang, level = str(entry.get("lang")), str(entry.get("level"))
        counts[lang][level] = counts[lang].get(level, 0) + 1
        coverage[lang]["entries"] += 1
        coverage[lang]["example"] += "example" in entry
        coverage[lang]["ipa"] += "ipa" in entry
        if not own and isinstance(entry.get("rank"), int):
            key = (lang, level, int(entry["rank"]))
            if key in seen_rank:
                errors.append(f"{label}: rank {entry['rank']} appears twice in {lang}/{level}")
            seen_rank.add(key)
        gloss = entry.get("gloss")
        if isinstance(gloss, dict) and isinstance(gloss.get("pl"), str):
            # the question shows the part of speech, so only the same meaning and part clash
            meanings[(lang, gloss["pl"].strip().casefold(), str(entry.get("pos")))].append(entry)
        for other in entry.get("confusable", []) or []:
            if other not in ids:
                errors.append(f"{label}: confusable {other!r} is not an entry")
    for (lang, meaning, _), same in meanings.items():
        if len(same) > 1 and not all(e.get("hint") for e in same):
            names = ", ".join(str(e.get("id")) for e in same)
            message = f"{lang}: {names} share the meaning {meaning!r} and need a hint each"
            # a clash with an own word is the learner's to settle; the courses stay valid
            own_word = any(e.get("level") == "own" for e in same)
            (warnings if own_word else errors).append(message)
    for lang, levels in catalog.installed().items():
        meta = catalog.meta(lang)
        if not meta.get("license") or not meta.get("sources"):
            errors.append(f"{lang}/meta.json needs license and sources")
        for level, number in (meta.get("levels") or {}).items():
            if counts.get(lang, {}).get(level, 0) != number:
                warnings.append(f"{lang}/meta.json counts {number} entries in {level}")
        if not levels:
            warnings.append(f"{lang} has no level installed")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            lang: dict(sorted(c.items(), key=lambda i: LEVEL_ORDER.get(i[0], 9)))
            for lang, c in sorted(counts.items())
        },
        "coverage": {lang: dict(c) for lang, c in sorted(coverage.items())},
    }
