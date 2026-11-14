"""Concepts: the CEFR-J A1-B2 headwords with ids that never change.

tools/courses/concepts.tsv keeps every id ever given (committed to git). A
headword that is new to the list gets the next free id; one that leaves the
list keeps its id in the file, so no id is ever reused.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sources import CEFRJ, TOOLS

IDS = TOOLS / "concepts.tsv"
LEVELS = ("a1", "a2", "b1", "b2")
POS_MAP = {
    "noun": "noun",
    "adjective": "adj",
    "verb": "verb",
    "adverb": "adv",
    "pronoun": "pron",
    "preposition": "prep",
    "conjunction": "conj",
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
    order: int  # position in the CEFR-J list


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
    lines = ["id\theadword\tpos"] + [
        f"{cid}\t{h}\t{p}" for (h, p), cid in sorted(known.items(), key=lambda kv: kv[1])
    ]
    IDS.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return concepts
