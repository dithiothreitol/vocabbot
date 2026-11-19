"""Word families: one concept learned in several languages together.

The plan's setting `together` names languages whose words a learner meets and
reviews by families (Stage 14b of the plan). A concept enters every language of
the set, and its cards stand side by side in the day's queue as one block
(queue.py). A card of the set due today brings the cards of its family in the
other languages of the set, once half of their interval has passed: they join
its block as reviews before their day. Without the setting, or with fewer than
two languages of the set active, nothing here changes the day.

This module holds what the queue, the session and the forecast share: the set
of a plan, the key of a family, the reviews that join a due card, the order of
a block, the shape of two forms, the parts of a form that differ, the
correspondences of endings and the family table of a result. It uses the
standard library only, like the rest of the engine.
"""

from __future__ import annotations

import difflib
import hashlib
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from functools import cache
from typing import Any

from vocabbot import assets
from vocabbot.answers import accepted_forms, normalize, plain
from vocabbot.courses import Catalog, card_id, split_card

Key = tuple[str, str]  # (concept, direction)

# two forms count as nearly the same (the measurement of Stage 14): the same letters,
# at most two edits in words of four letters and more, or a shared start of four letters
# that covers 70% of the longer word
NEAR_EDITS = 2
NEAR_LENGTH = 4
NEAR_PREFIX = 4
NEAR_SHARE = 0.7


def team(plan: Mapping[str, Any]) -> list[str]:
    """The languages learned by families: those of `together` that are active, in the
    plan's order, when there are at least two of them; otherwise none."""
    chosen = set(plan.get("together") or [])
    active = [
        str(item["code"])
        for item in plan.get("languages", [])
        if not item.get("paused") and item.get("code") in chosen
    ]
    return active if len(active) >= 2 else []


def key_of(card: str, entry: Mapping[str, Any] | None) -> Key | None:
    """The family of a card: its concept and its direction."""
    if not entry or not entry.get("concept"):
        return None
    return (str(entry["concept"]), split_card(card)[1])


def joined(
    anchors: Sequence[str],
    members: Mapping[Key, Sequence[str]],
    keys: Mapping[str, Key | None],
    dates: Mapping[str, tuple[date, date]],
    day: date,
    skip: Iterable[str] = (),
) -> list[str]:
    """The cards that join the review of a due card of their family.

    `anchors` are the day's due cards of the set's languages, `members` the
    introduced cards of every family, and `dates` the last answer and the due
    day of each card. A card joins when it is not due today, at least one day
    and at least half of its interval have passed since its last answer, and it
    is neither an anchor nor in `skip`. The order follows the anchors, so the
    list is the same on every computer.
    """
    taken = set(anchors) | set(skip)
    out: list[str] = []
    for anchor in anchors:
        family = keys.get(anchor)
        if family is None:
            continue
        for card in members.get(family, ()):
            if card in taken or card not in dates:
                continue
            last, due = dates[card]
            elapsed = (day - last).days
            if due > day and elapsed >= 1 and 2 * elapsed >= (due - last).days:
                out.append(card)
                taken.add(card)
    return out


def block_order(cards: Sequence[str], codes: Sequence[str], family: Key, day: date) -> list[str]:
    """The cards of one block, in the set's languages rotated by the family and the day,
    so every language comes first at times and both computers build the same block."""
    if len(cards) < 2:
        return list(cards)
    digest = hashlib.sha256(f"{family[0]}|{family[1]}|{day.isoformat()}".encode()).digest()
    shift = digest[0] % len(codes)
    rank = {code: (index - shift) % len(codes) for index, code in enumerate(codes)}
    return sorted(cards, key=lambda card: (rank.get(card[:2], len(codes)), card))


def units(
    cards: Sequence[str],
    keys: Mapping[str, Key | None],
    codes: Sequence[str],
    day: date,
    extra: dict[Key, list[str]] | None = None,
) -> list[list[str]]:
    """The cards as units of the queue.

    The cards of one family in the set's languages make one block at the place of
    its first card, together with the cards of `extra` that join that family
    (taken out of `extra`, so a family joins one block only). Every other card is
    a unit of its own. Without a set every card is its own unit and the list keeps
    its order.
    """
    members = set(codes)
    blocks: dict[Key, list[str]] = {}
    out: list[list[str]] = []
    for card in cards:
        family = keys.get(card) if card[:2] in members else None
        if family is None:
            out.append([card])
        elif family in blocks:
            blocks[family].append(card)
        else:
            blocks[family] = [card]
            out.append(blocks[family])
    for family, block in blocks.items():
        if extra and family in extra:
            block += extra.pop(family)
        block[:] = block_order(block, codes, family, day)
    return out


# ---------------------------------------------------------------- forms


def _folded(text: str) -> str:
    return plain(text.lower())


def distance(a: str, b: str) -> int:
    """Levenshtein distance (insertions, deletions and substitutions)."""
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def shape(a: str, b: str) -> str:
    """ "identical", "near" or "distinct": how alike two forms are, without accents."""
    x, y = _folded(a), _folded(b)
    if x == y:
        return "identical"
    if min(len(x), len(y)) >= NEAR_LENGTH and distance(x, y) <= NEAR_EDITS:
        return "near"
    shared = 0
    for p, q in zip(x, y, strict=False):
        if p != q:
            break
        shared += 1
    if shared >= NEAR_PREFIX and shared >= NEAR_SHARE * max(len(x), len(y)):
        return "near"
    return "distinct"


def split(word: str, other: str) -> list[list[Any]]:
    """The parts of `word` that `other` shares and the parts it does not, to mark.

    [["gran", True], ["d", False]]: each part with True where the letters match
    an alignment with `other` (accents and case aside).
    """
    a, b = _folded(word), _folded(other)
    if len(a) != len(word):
        a, b = word.lower(), other.lower()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    parts: list[list[Any]] = []
    at = 0
    for block in matcher.get_matching_blocks():
        if block.a > at:
            parts.append([word[at : block.a], False])
        if block.size:
            parts.append([word[block.a : block.a + block.size], True])
        at = block.a + block.size
    if at < len(word):
        parts.append([word[at:], False])
    return parts


def parts(word: str, other: str) -> list[list[Any]]:
    """`split` for forms alike; a distinct word is one part that differs as a whole."""
    if shape(word, other) == "distinct":
        return [[word, False]]
    return split(word, other)


@cache
def correspondences() -> tuple[dict[str, str], ...]:
    """Regular correspondences of endings between the languages of the courses."""
    data = assets.read_json(assets.data_root() / "correspondences.json")
    return tuple(dict(item["endings"]) for item in data["patterns"])


def near_stems(a: str, b: str) -> bool:
    """Stems close enough for a rule of endings: at most one edit in four letters."""
    x, y = _folded(a), _folded(b)
    return distance(x, y) <= max(1, min(len(x), len(y)) // 4)


def rule(lemmas: Mapping[str, str]) -> dict[str, str] | None:
    """The correspondence of endings that fits every word, when their stems are near.

    `lemmas` maps a language to its word. A rule needs at least two words, an
    ending for every language and stems at most one edit apart in four letters,
    so "hablar" and "parlare" get none.
    """
    if len(lemmas) < 2:
        return None
    for endings in correspondences():
        if not all(lang in endings for lang in lemmas):
            continue
        stems = {}
        for lang, word in lemmas.items():
            folded = word.lower()
            ending = endings[lang]
            if not folded.endswith(ending) or len(folded) <= len(ending):
                break
            stems[lang] = folded[: -len(ending)]
        else:
            values = list(stems.values())
            if all(near_stems(values[0], other) for other in values[1:]):
                return {lang: endings[lang] for lang in lemmas}
    return None


# ---------------------------------------------------------------- the session


def met_today(
    plan: Mapping[str, Any], seen: Iterable[str], entry: Mapping[str, Any], catalog: Catalog
) -> bool:
    """Whether a card of the entry's family in another language of the set was seen today."""
    codes = team(plan)
    lang = str(entry.get("lang"))
    if lang not in codes or not entry.get("concept"):
        return False
    concept = str(entry["concept"])
    for card in seen:
        if card[:2] == lang or card[:2] not in codes:
            continue
        other = catalog.card(card)
        if other is not None and str(other.get("concept")) == concept:
            return True
    return False


def hidden_forms(cards: Iterable[str], catalog: Catalog) -> set[str]:
    """The answers of the production cards still waiting today, as a table may not show them."""
    out: set[str] = set()
    for card in cards:
        if not card.endswith("#p"):
            continue
        entry = catalog.card(card)
        if entry is None:
            continue
        for form in [*accepted_forms(entry), str(entry.get("lemma") or "")]:
            if form:
                out.add(normalize(form).casefold())
    return out


def table(
    plan: Mapping[str, Any],
    card: str,
    entry: Mapping[str, Any],
    catalog: Catalog,
    introduced: Callable[[str], bool],
    waiting: set[str],
    hidden: set[str],
) -> dict[str, Any] | None:
    """The family of an answered card in the other languages of the set.

    A row for every card of the family already introduced (`introduced`): its
    language, its word and the parts of the word that differ from the answered
    one. A card still waiting today (`waiting`), or a word that is the answer of
    a waiting card (`hidden`), gives a row with `waiting` and no word, so a
    table never answers a question of the day. `rule` names the correspondence
    of endings that fits every word shown with the answered one.
    """
    codes = team(plan)
    lang = str(entry.get("lang"))
    if lang not in codes or not entry.get("concept"):
        return None
    direction = split_card(card)[1]
    word = str(entry["display"])
    rows: list[dict[str, Any]] = []
    lemmas = {lang: str(entry.get("lemma") or word)}
    first: str | None = None
    for code in codes:
        if code == lang:
            continue
        for other in catalog.family(str(entry["concept"])):
            if other.get("lang") != code:
                continue
            other_card = card_id(str(other["id"]), direction)
            if not introduced(other_card):
                continue
            shown = str(other["display"])
            if other_card in waiting or normalize(shown).casefold() in hidden:
                rows.append({"lang": code, "card": other_card, "waiting": True})
                continue
            rows.append(
                {"lang": code, "card": other_card, "word": shown, "parts": parts(shown, word)}
            )
            lemmas.setdefault(code, str(other.get("lemma") or shown))
            first = first or shown
    if not rows:
        return None
    out: dict[str, Any] = {"rows": rows}
    if first is not None:
        out["word_parts"] = parts(word, first)
        found = rule(lemmas)
        if found:
            out["rule"] = found
    return out
