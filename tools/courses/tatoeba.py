"""Example sentences from Tatoeba with a Polish translation.

A sentence in the course language is usable when it has a Polish
translation, linked directly or through one sentence in another language
that is linked to both (target -> pivot -> Polish). English comes first
among the pivots, then the other course languages, then the languages with
the most links to Polish.
"""

from __future__ import annotations

import bz2
import re
from collections import defaultdict
from dataclasses import dataclass

from sources import EXTRA_PIVOTS, TATOEBA, TATOEBA_LANG

TOKEN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
MIN_TOKENS, MAX_TOKENS = 3, 20
PIVOTS = ("en", "de", "fr", "es", *EXTRA_PIVOTS)


def course_links() -> dict[tuple[str, str], dict[int, list[int]]]:
    """Links from a course language to another pivot, for translations in two steps."""
    out = {}
    for a in PIVOTS:
        for b in PIVOTS:
            path = TATOEBA / f"{TATOEBA_LANG[a]}-{TATOEBA_LANG[b]}_links.tsv.bz2"
            if a != b and path.is_file():
                out[(a, b)] = read_links(a, b)
    return out


@dataclass(frozen=True)
class Sentence:
    id: int
    text: str
    user: str


def read_sentences(code: str) -> dict[int, Sentence]:
    out: dict[int, Sentence] = {}
    path = TATOEBA / f"{TATOEBA_LANG[code]}_sentences_detailed.tsv.bz2"
    with bz2.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            out[int(parts[0])] = Sentence(int(parts[0]), parts[2], parts[3])
    return out


def read_links(a: str, b: str) -> dict[int, list[int]]:
    out: dict[int, list[int]] = defaultdict(list)
    path = TATOEBA / f"{TATOEBA_LANG[a]}-{TATOEBA_LANG[b]}_links.tsv.bz2"
    with bz2.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split("\t")
            if len(parts) >= 2:
                out[int(parts[0])].append(int(parts[1]))
    return out


def polish_links() -> dict[str, dict[int, list[int]]]:
    return {code: read_links(code, "pl") for code in PIVOTS}


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text)


class Corpus:
    """Sentences of one language that have a Polish translation, indexed by word."""

    def __init__(
        self,
        code: str,
        polish: dict[int, Sentence],
        to_polish: dict[str, dict[int, list[int]]],
        between: dict[tuple[str, str], dict[int, list[int]]] | None = None,
    ) -> None:
        self.code = code
        self.between = between or {}
        sentences = read_sentences(code)
        pivots = {
            other: read_links(code, other)
            for other in PIVOTS
            if other != code
            and (TATOEBA / f"{TATOEBA_LANG[code]}-{TATOEBA_LANG[other]}_links.tsv.bz2").is_file()
        }
        direct = to_polish.get(code, {})
        self.sentences: dict[int, Sentence] = {}
        self.polish: dict[int, tuple[Sentence, str]] = {}
        for sid, sentence in sentences.items():
            if not MIN_TOKENS <= len(tokens(sentence.text)) <= MAX_TOKENS:
                continue
            found = self._polish_of(sid, direct, pivots, polish, to_polish)
            if found is None:
                found = self._two_steps(sid, polish, to_polish)
            if found is None:
                continue
            self.sentences[sid] = sentence
            self.polish[sid] = found
        self.index: dict[str, list[int]] = defaultdict(list)
        for sid, sentence in self.sentences.items():
            for token in {t.casefold() for t in tokens(sentence.text)}:
                self.index[token].append(sid)

    @staticmethod
    def _polish_of(
        sid: int,
        direct: dict[int, list[int]],
        pivots: dict[str, dict[int, list[int]]],
        polish: dict[int, Sentence],
        to_polish: dict[str, dict[int, list[int]]],
    ) -> tuple[Sentence, str] | None:
        for pid in sorted(direct.get(sid, [])):
            if pid in polish:
                return polish[pid], "direct"
        for pivot in PIVOTS:
            if pivot not in pivots:
                continue
            for other in sorted(pivots[pivot].get(sid, [])):
                for pid in sorted(to_polish.get(pivot, {}).get(other, [])):
                    if pid in polish:
                        return polish[pid], pivot
        return None

    def _two_steps(
        self, sid: int, polish: dict[int, Sentence], to_polish: dict[str, dict[int, list[int]]]
    ) -> tuple[Sentence, str] | None:
        """target -> one pivot -> another pivot -> Polish."""
        for first in PIVOTS:
            if first == self.code:
                continue
            for one in sorted(self.between.get((self.code, first), {}).get(sid, [])):
                for second in PIVOTS:
                    if second in (self.code, first):
                        continue
                    for two in sorted(self.between.get((first, second), {}).get(one, [])):
                        for pid in sorted(to_polish.get(second, {}).get(two, [])):
                            if pid in polish:
                                return polish[pid], f"{first}+{second}"
        return None

    def candidates(self, phrase: str) -> list[int]:
        words = [t.casefold() for t in tokens(phrase)]
        if not words:
            return []
        pools = [set(self.index.get(w, ())) for w in words]
        found = set.intersection(*pools) if pools else set()
        return sorted(found)
