"""Concepts: the CEFR-J A1-B2 headwords with ids that never change, and the editors' concepts.

tools/courses/concepts.tsv keeps every id ever given to a CEFR-J headword
(committed to git). A headword that is new to the list gets the next free id;
one that leaves the list keeps its id in the file, so no id is ever reused.

Concepts that CEFR-J does not list (a word of one language, such as Spanish
"estar", or a plural noun such as German "die Eltern") come from the editors'
file tools/courses/editor.jsonl, in rows with a "new" field. Their ids start
at c09001, above every CEFR-J id.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from sources import CEFRJ, TOOLS

IDS = TOOLS / "concepts.tsv"
EDITOR = TOOLS / "editor.jsonl"
FIRST_EDITOR_ID = 9001
# Wiktionary parts of speech an editors' concept may have
EDITOR_POS = frozenset(
    {"noun", "adj", "verb", "adv", "pron", "prep", "conj", "det", "num", "intj", "particle"}
    | {"phrase"}
)
LEVELS = ("a1", "a2", "b1", "b2")
POS_MAP = {
    "noun": "noun",
    "adjective": "adj",
    "verb": "verb",
    "adverb": "adv",
    "pronoun": "pron",
    "preposition": "prep",
    "conjunction": "conj",
    "determiner": "det",
    "number": "num",
    "interjection": "intj",
    "modal auxiliary": "verb",
    "be-verb": "verb",
    "do-verb": "verb",
    "have-verb": "verb",
}


@dataclass(frozen=True)
class Concept:
    id: str
    headword: str
    pos: str  # Wiktionary part of speech
    level: str
    order: int  # position in the CEFR-J list; editors' concepts follow it

    @property
    def from_cefrj(self) -> bool:
        return int(self.id[1:]) < FIRST_EDITOR_ID


def headword_of(raw: str) -> str:
    """'a.m./A.M./am/AM' -> 'a.m.'; spaces trimmed."""
    return raw.split("/")[0].strip()


def read(path: Path = CEFRJ) -> list[Concept]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    known: dict[tuple[str, str], str] = {}
    next_number = 1
    if IDS.is_file():
        for line in IDS.read_text("utf-8").splitlines()[1:]:
            concept, headword, pos = line.split("\t")[:3]
            known[(headword, pos)] = concept
            next_number = max(next_number, int(concept[1:]) + 1)
    concepts: list[Concept] = []
    seen: set[tuple[str, str]] = set()
    for order, row in enumerate(rows):
        pos = POS_MAP.get(row["pos"].strip())
        level = row["CEFR"].strip().lower()
        if pos is None or level not in LEVELS:
            continue
        headword = headword_of(row["headword"])
        key = (headword, pos)
        if key in seen:
            continue
        seen.add(key)
        if key not in known:
            known[key] = f"c{next_number:05d}"
            next_number += 1
        concepts.append(Concept(known[key], headword, pos, level, order))
    if next_number >= FIRST_EDITOR_ID:
        raise SystemExit("CEFR-J ids reached the range of the editors' concepts")
    lines = ["id\theadword\tpos"] + [
        f"{cid}\t{h}\t{p}" for (h, p), cid in sorted(known.items(), key=lambda kv: kv[1])
    ]
    IDS.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return concepts + editor_concepts(len(rows))


def editor_concepts(after: int = 0, path: Path = EDITOR) -> list[Concept]:
    """Concepts the editors added, in the order of their ids."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        new = row.get("new")
        if not new:
            continue
        if int(row["id"][1:]) < FIRST_EDITOR_ID:
            raise SystemExit(f"editor concept {row['id']} must have an id from c{FIRST_EDITOR_ID}")
        if new["pos"] not in EDITOR_POS or new["level"] not in LEVELS:
            raise SystemExit(f"editor concept {row['id']} has an unknown part of speech or level")
        out.append(Concept(row["id"], new["headword"], new["pos"], new["level"], 0))
    out.sort(key=lambda c: c.id)
    return [
        Concept(c.id, c.headword, c.pos, c.level, after + number) for number, c in enumerate(out, 1)
    ]
