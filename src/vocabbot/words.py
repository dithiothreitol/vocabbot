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


def add_preview(
    learner: store.Learner, catalog: Catalog, lang: str, text: str, now: datetime
) -> dict[str, Any]:
    """Preview of own words added to courses/<lang>/own.jsonl."""
    if lang not in assets.known_languages():
        raise VocabError("unknown_language", lang=lang)
    own = catalog.own(lang)
    rank = max((int(e.get("rank", 0)) for e in own), default=0)
    existing = {
        normalize(str(e["display"])).casefold(): str(e["id"])
        for e in [*own, *catalog.course(lang, list(store.LEVELS))]
    }
    new_entries: list[dict[str, Any]] = []
    problems: list[str] = []
    for raw in parse(text, lang):
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
        entry.setdefault("lemma", entry.get("display", ""))
        entry["sources"] = ["own"]
        entry["checked"] = False
        label = str(entry.get("display", "?"))
        key = normalize(label).casefold()
        if key in existing:
            problems.append(assets.text("words.duplicate", word=label, id=existing[key]))
            continue
        existing[key] = entry["id"]
        for problem in entry_problems(entry, own=True):
            problems.append(f"{label}: {problem}")
        new_entries.append(entry)
    if problems:
        raise VocabError("words_invalid", problems=problems, detail="; ".join(problems))
    lines = [
        assets.text("words.line", word=e["display"], meaning=e["gloss"]["pl"]) for e in new_entries
    ]
    summary = assets.text("words.summary", count=len(new_entries), lang=lang)
    content = "".join(store.dump_line(e) + "\n" for e in new_entries)
    return gate.preview(
        learner.path(store.PENDING),
        summary,
        lines,
        [gate.Change(learner.own_path(lang), "append", content)],
        now,
        learner.path(store.DECISIONS),
    )
