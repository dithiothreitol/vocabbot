"""The learner's own words, added as a preview first.

Input comes on standard input, one word per line, either as a JSON object
with the fields of a course entry or as a short line:

    der Hund = pies
    l'ami (m) = przyjaciel | L'ami attend à la gare. | Przyjaciel czeka na dworcu.
    gehen [verb] = iść
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from typing import Any

from vocabbot import assets, gate, store
from vocabbot.answers import normalize, rules, split_article
from vocabbot.courses import POS, Catalog, entry_problems
from vocabbot.errors import VocabError

LINE = re.compile(
    r"^(?P<display>.+?)\s*(?:\((?P<gender>[mfn])\))?\s*(?:\[(?P<pos>[a-z]+)\])?\s*=\s*(?P<rest>.+)$"
)
MAX_WORDS = 200


def _from_line(line: str, lang: str) -> dict[str, Any]:
    match = LINE.match(line)
    if not match:
        raise VocabError("bad_word_line", line=line[:80])
    display = normalize(match["display"])
    parts = [part.strip() for part in match["rest"].split("|")]
    entry: dict[str, Any] = {"display": display, "gloss": {"pl": parts[0]}}
    lang_rules = rules(lang)
    article, core = split_article(display, lang_rules)
    gender = match["gender"] or (lang_rules.gender_of(article) if article else None)
    pos = match["pos"] or ("noun" if article and lang_rules.articles else "other")
    entry["pos"] = pos
    if gender and pos == "noun":
        entry["gender"] = gender
    entry["lemma"] = core if pos == "noun" and article else display
    if len(parts) >= 2 and parts[1]:
        example: dict[str, Any] = {"text": parts[1], "pl": parts[2] if len(parts) >= 3 else ""}
        for gap in (display, entry["lemma"]):
            if re.search(rf"(?<!\w){re.escape(gap)}(?!\w)", parts[1], re.IGNORECASE):
                found = re.search(rf"(?<!\w){re.escape(gap)}(?!\w)", parts[1], re.IGNORECASE)
                assert found is not None
                example["gap"] = found.group(0)
                break
        example["source"] = "own"
        entry["example"] = example
    return entry


def parse(text: str, lang: str) -> list[dict[str, Any]]:
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            try:
                item = json.loads(line)
            except ValueError:
                raise VocabError("bad_word_line", line=line[:80]) from None
            if not isinstance(item, dict):
                raise VocabError("bad_word_line", line=line[:80])
            entries.append(item)
        else:
            entries.append(_from_line(line, lang))
    if not entries:
        raise VocabError("no_words")
    if len(entries) > MAX_WORDS:
        raise VocabError("too_many_words", limit=MAX_WORDS)
    return entries


def _key(text: str) -> str:
    return normalize(text).casefold()


def _course_match(
    raw: dict[str, Any], by_display: dict[str, dict[str, Any]], by_lemma: dict[str, list[Any]]
) -> dict[str, Any] | None:
    """The course entry a learner's word names: the same display, else a single same lemma."""
    found = by_display.get(_key(str(raw.get("display", ""))))
    if found is not None:
        return found
    same = by_lemma.get(_key(str(raw.get("lemma") or raw.get("display", ""))), [])
    return same[0] if len(same) == 1 else None


def add_preview(
    learner: store.Learner, catalog: Catalog, lang: str, text: str, now: datetime
) -> dict[str, Any]:
    """Preview of own words added to courses/<lang>/own.jsonl.

    A word the course already has is not copied: the preview moves that course
    entry forward, so it comes before the course order. A word already in own
    words or already being learned is left out with a note.
    """
    if lang not in assets.known_languages():
        raise VocabError("unknown_language", lang=lang)
    own = catalog.own(lang)
    rank = max((int(e.get("rank", 0)) for e in own), default=0)
    existing = {_key(str(e["display"])): str(e["id"]) for e in own}
    course = catalog.course(lang, list(store.LEVELS))
    by_display = {_key(str(e["display"])): e for e in course}
    by_lemma: dict[str, list[Any]] = {}
    by_meaning: dict[tuple[str, str], list[Any]] = {}
    for e in course:
        by_lemma.setdefault(_key(str(e.get("lemma", ""))), []).append(e)
    for e in [*course, *own]:
        by_meaning.setdefault((_key(str(e["gloss"]["pl"])), str(e.get("pos"))), []).append(e)
    learning = {str(row.get("card", "")).split("#")[0] for row in learner.rows()[0]}
    learning |= catalog.moved_forward(lang)
    new_entries: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    skipped: list[str] = []
    clashes: list[str] = []
    problems: list[str] = []
    for raw in parse(text, lang):
        label = str(raw.get("display", "?"))
        if _key(label) in existing:
            skipped.append(assets.text("words.duplicate", word=label, id=existing[_key(label)]))
            continue
        match = _course_match(raw, by_display, by_lemma)
        if match is not None:
            if str(match["id"]) in learning:
                skipped.append(assets.text("words.learning", word=match["display"]))
            else:
                learning.add(str(match["id"]))
                moved.append(match)
            continue
        token = secrets.token_hex(3)
        rank += 1
        entry: dict[str, Any] = {
            "id": f"{lang}-u{token}",
            "concept": raw.get("concept") or f"u{token}",
            "lang": lang,
            "level": "own",
            "rank": rank,
            "pos": raw.get("pos") if raw.get("pos") in POS else "other",
        }
        for key in (
            "lemma",
            "display",
            "gender",
            "forms",
            "accept",
            "gloss",
            "ipa",
            "hint",
            "example",
        ):
            if raw.get(key) not in (None, "", [], {}):
                entry[key] = raw[key]
        if not entry.get("lemma"):
            article, core = split_article(str(entry.get("display", "")), rules(lang))
            entry["lemma"] = (
                core if article and entry["pos"] == "noun" else entry.get("display", "")
            )
        entry["sources"] = ["own"]
        entry["checked"] = False
        existing[_key(label)] = entry["id"]
        for problem in entry_problems(entry, own=True):
            problems.append(f"{label}: {problem}")
        meaning = (_key(str((entry.get("gloss") or {}).get("pl", ""))), str(entry["pos"]))
        same = by_meaning.setdefault(meaning, [])
        if same and not entry.get("hint"):
            clashes.append(
                assets.text(
                    "words.same_meaning",
                    word=label,
                    meaning=(entry.get("gloss") or {}).get("pl", ""),
                    other=same[0]["display"],
                )
            )
        same.append(entry)
        new_entries.append(entry)
    if problems:
        raise VocabError("words_invalid", problems=problems, detail="; ".join(problems))
    if not new_entries and not moved:
        raise VocabError("nothing_to_add", detail="; ".join(skipped))
    lines = [
        assets.text("words.line", word=e["display"], meaning=e["gloss"]["pl"]) for e in new_entries
    ]
    lines += [
        assets.text(
            "words.moved",
            word=e["display"],
            meaning=e["gloss"]["pl"],
            level=str(e["level"]).upper(),
        )
        for e in moved
    ]
    lines += [assets.text("words.skipped", detail=note) for note in skipped]
    lines += clashes
    if lang not in {item["code"] for item in learner.plan()["languages"]}:
        lines.append(assets.text("words.not_in_plan", lang=lang))
    summary = assets.text("words.summary", count=len(new_entries) + len(moved), lang=lang)
    rows = [*new_entries, *({"ref": e["id"], "lang": lang} for e in moved)]
    content = "".join(store.dump_line(row) + "\n" for row in rows)
    result = gate.preview(
        learner.path(store.PENDING),
        summary,
        lines,
        [gate.Change(learner.own_path(lang), "append", content)],
        now,
        learner.path(store.DECISIONS),
    )
    result["added"] = [e["id"] for e in new_entries]
    result["moved"] = [e["id"] for e in moved]
    result["skipped"] = skipped
    result["same_meaning"] = clashes
    return result
