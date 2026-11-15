"""A short placement test from the course: questions without answers, graded without the log.

`questions` picks words spread evenly over each level, which the courses keep
in order of frequency, and prefers words with an example sentence. `check`
grades typed answers with the rules of a session and suggests the levels to
start from. Nothing is written anywhere.
"""

from __future__ import annotations

import re
from typing import Any

from vocabbot import answers, assets, store
from vocabbot.courses import Catalog, card_id, presentation, question, split_card
from vocabbot.errors import VocabError

KNOWN_SHARE = 0.8  # a level counts as known from this share of right answers
ALMOST_WEIGHT = 0.5  # an answer graded "almost" counts as half a right answer
MAX_PER_LEVEL = 20


def questions(catalog: Catalog, lang: str, levels: list[str], count: int) -> dict[str, Any]:
    installed = catalog.installed()
    if lang not in installed:
        raise VocabError("no_course", lang=lang)
    if count < 1 or count > MAX_PER_LEVEL:
        raise VocabError("bad_count")
    items = []
    for level in levels:
        course = catalog.course(lang, [level])
        if not course:
            continue
        step = len(course) / count
        for index in range(min(count, len(course))):
            window = course[int(index * step) : max(int((index + 1) * step), int(index * step) + 1)]
            middle = len(window) // 2
            ordered = window[middle:] + window[:middle]
            entry = next((e for e in ordered if e.get("example")), ordered[0])
            items.append(
                {
                    "card": card_id(str(entry["id"]), "p"),
                    "lang": lang,
                    "level": level,
                    "question": question(entry, "p"),
                }
            )
    _hide_other_answers(catalog, items)
    return {
        "lang": lang,
        "levels": [lvl for lvl in levels if lvl in installed[lang]],
        "items": items,
    }


def _hide_other_answers(catalog: Catalog, items: list[dict[str, Any]]) -> None:
    """A sentence that holds the answer of another question of the test loses its sentence."""
    answers_by_card = {}
    for item in items:
        entry = catalog.card(item["card"])
        if entry is not None:
            forms = [*answers.accepted_forms(entry), str(entry.get("lemma") or "")]
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


def check(
    catalog: Catalog, lines: list[dict[str, Any]], *, lenient: bool = False
) -> dict[str, Any]:
    results = []
    by_level: dict[str, list[str]] = {}
    for line in lines:
        card = str(line.get("card", ""))
        try:
            entry_id, direction = split_card(card)
        except ValueError:
            raise VocabError("bad_card", card=card) from None
        entry = catalog.entry(entry_id)
        if entry is None or direction != "p" or entry.get("level") not in store.LEVELS:
            raise VocabError("unknown_card", card=card)
        verdict = answers.grade(str(line.get("answer", "")), entry, lenient=lenient)
        results.append(
            {
                "card": card,
                "level": entry["level"],
                "grade": verdict.grade,
                "grade_pl": assets.text(f"grades.{verdict.grade}"),
                "errors": list(verdict.errors),
                "errors_pl": [assets.text(f"error_classes.{e}") for e in verdict.errors],
                "word": presentation(entry),
            }
        )
        by_level.setdefault(str(entry["level"]), []).append(verdict.grade)
    levels: dict[str, dict[str, Any]] = {}
    for level in store.LEVELS:
        grades = by_level.get(level)
        if grades:
            know = grades.count(answers.KNOW)
            almost = grades.count(answers.ALMOST)
            share = (know + ALMOST_WEIGHT * almost) / len(grades)
            levels[level] = {
                "asked": len(grades),
                "know": know,
                "almost": almost,
                "share": round(share, 2),
                "known": share >= KNOWN_SHARE,
            }
    return {"results": results, "levels": levels, "suggested_levels": suggest(levels)}


def suggest(levels: dict[str, dict[str, Any]]) -> str | None:
    """The levels to learn: from the first level below the threshold to B2."""
    if not levels:
        return None
    start = next((lvl for lvl in store.LEVELS if lvl in levels and not levels[lvl]["known"]), None)
    if start is None:
        highest = max(store.LEVELS.index(lvl) for lvl in levels)
        start = store.LEVELS[min(highest + 1, len(store.LEVELS) - 1)]
    return start if start == store.LEVELS[-1] else f"{start}-{store.LEVELS[-1]}"
