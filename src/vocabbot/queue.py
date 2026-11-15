"""The day's queue for one to three languages.

The list of a day is a function of the log before that day, the plan, the
courses and the day itself, so an interrupted session resumes in the same
order in the terminal and in the chat:

1. reviews: cards due by today, most overdue first, up to the review limit;
2. new words: the daily limit split between languages by weight, own words
   first, then the course in order; a concept introduced in another language
   less than `sibling_gap_days` ago waits;
3. drill: cards answered "almost" or "dont_know" today, until "know".

Languages are interleaved (or kept in blocks), and cards of one concept stay
at least `sibling_distance` positions apart.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from fractions import Fraction
from typing import Any

from vocabbot import presence as attendance
from vocabbot import store
from vocabbot.book import Book, Today, activity, extend, fitted_replay
from vocabbot.courses import Catalog, card_id, split_card
from vocabbot.fsrs import Scheduler

DIRECTION_CODES = store.DIRECTIONS


@dataclass
class Item:
    card: str
    lang: str
    phase: str  # review, new, drill or ahead
    entry: dict[str, Any] = field(repr=False)
    due: date | None = None

    @property
    def direction(self) -> str:
        return self.card[-1]

    @property
    def concept(self) -> str:
        return str(self.entry.get("concept"))


@dataclass
class DayPlan:
    day: date
    plan: dict[str, Any]
    off: bool
    scheduler: Scheduler
    before: Book
    book: Book
    today: Today
    due: list[str]
    reviews: list[str]
    overflow: int
    new: list[str]
    drill: list[str]
    sequence: list[Item]
    extra: int
    orphans: int
    quota: dict[str, int]
    schedulers: dict[str, Scheduler] = field(default_factory=dict)
    presence: attendance.Presence | None = None
    planned_new: int = 0  # the plan's new words for the day, before pacing
    paced_new: int | None = None  # fewer new words to stay within the usual minutes
    due_tomorrow: int = 0

    def lang_codes(self) -> list[str]:
        return [item["code"] for item in self.plan["languages"]]

    def scheduler_for(self, lang: str) -> Scheduler:
        return self.schedulers.get(lang, self.scheduler)


def split_quota(total: int, weights: dict[str, int], ordinal: int) -> dict[str, int]:
    """Largest remainders; ties go to languages in an order that rotates by day."""
    if not weights or total <= 0:
        return dict.fromkeys(weights, 0)
    weight_sum = sum(weights.values())
    quota = {code: total * weight // weight_sum for code, weight in weights.items()}
    left = total - sum(quota.values())
    codes = list(weights)
    shift = ordinal % len(codes)
    rotated = codes[shift:] + codes[:shift]
    ranked = sorted(rotated, key=lambda code: -((total * weights[code]) % weight_sum))
    for code in ranked[:left]:
        quota[code] += 1
    return quota


def rotate(codes: list[str], ordinal: int) -> list[str]:
    if not codes:
        return codes
    shift = ordinal % len(codes)
    return codes[shift:] + codes[:shift]


def interleave(cards: list[str], lang_of: dict[str, str], order: list[str]) -> list[str]:
    """Spread each language evenly over the list, keeping each language's own order."""
    by_lang: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        by_lang[lang_of[card]].append(card)
    keyed: list[tuple[Fraction, int, str]] = []
    rank = {code: index for index, code in enumerate(order)}
    for code, items in by_lang.items():
        for index, card in enumerate(items):
            keyed.append((Fraction(2 * index + 1, 2 * len(items)), rank.get(code, len(rank)), card))
    keyed.sort()
    return [card for _, _, card in keyed]


def blocks(cards: list[str], lang_of: dict[str, str], order: list[str]) -> list[str]:
    rank = {code: index for index, code in enumerate(order)}
    return sorted(cards, key=lambda card: rank.get(lang_of[card], len(rank)))


def spread(
    cards: list[str], family: dict[str, str], distance: int, context: list[str]
) -> list[str]:
    """Keep cards of one family `distance` positions apart where the list allows it."""
    if distance <= 0:
        return list(cards)
    placed = list(context[-distance:])
    out: list[str] = []
    pending = list(cards)
    while pending:
        recent = {family[c] for c in placed[-distance:]}
        index = next((i for i, card in enumerate(pending) if family[card] not in recent), 0)
        card = pending.pop(index)
        out.append(card)
        placed.append(card)
    return out


def _candidates(
    catalog: Catalog, lang: str, levels: list[str], directions: list[str]
) -> Iterator[tuple[str, dict[str, Any]]]:
    for entry in [*catalog.first(lang), *catalog.course(lang, levels)]:
        for direction in directions:
            yield card_id(str(entry["id"]), direction), entry


def select_new(
    plan: dict[str, Any],
    catalog: Catalog,
    before: Book,
    today: Today,
    day: date,
    total: int,
    suspended: set[str],
    base: int | None = None,
) -> tuple[list[str], dict[str, int]]:
    """Today's new cards, chosen from the state before the day.

    Answers given during the day do not change the choice. The words of the
    plan (`base`, the daily limit) are chosen first and never change during the
    day; words the learner adds (more words for today, and one more for each
    word marked as known, which does not use the limit) join after them, so a
    card already shown never leaves the list.
    """
    active = [item for item in plan["languages"] if not item.get("paused")]
    weights = {item["code"]: int(item.get("weight", 1)) for item in active}
    known = sum(1 for card in today.learned if today.first_grade.get(card) == "known")
    zero = dict.fromkeys(weights, 0)
    full = total + known if total > 0 else 0
    quota = split_quota(full, weights, day.toordinal()) if full > 0 else zero
    planned_base = min(total if base is None else base, total)
    first = split_quota(planned_base, weights, day.toordinal()) if planned_base > 0 else zero
    second = {code: max(0, quota[code] - first[code]) for code in weights}
    directions = [DIRECTION_CODES[d] for d in plan["directions"]]
    introduced: dict[str, list[tuple[str, str, date]]] = defaultdict(list)
    for card, state in before.cards.items():
        entry = catalog.card(card)
        if entry is not None:
            introduced[str(entry["concept"])].append((state.lang, card, state.first_day))
    taken = set(before.cards)
    gap_days = int(plan["sibling_gap_days"])

    def blocked(card: str, entry: dict[str, Any]) -> bool:
        entry_id = split_card(card)[0]
        for lang, other, first_day in introduced[str(entry["concept"])]:
            if split_card(other)[0] == entry_id:
                gap = 1
            elif lang == entry["lang"]:
                continue
            else:
                gap = gap_days
            if (day - first_day).days < gap:
                return True
        return False

    streams = {
        item["code"]: _candidates(catalog, item["code"], item["levels"], directions)
        for item in active
    }
    picks: dict[str, list[str]] = defaultdict(list)
    exhausted: set[str] = set()

    def take(code: str) -> bool:
        for card, entry in streams[code]:
            if card in taken or split_card(card)[0] in suspended or blocked(card, entry):
                continue
            taken.add(card)
            picks[code].append(card)
            introduced[str(entry["concept"])].append((code, card, day))
            return True
        exhausted.add(code)
        return False

    order = rotate(list(weights), day.toordinal())

    def fill(remaining: dict[str, int]) -> None:
        """Take each language's share; a language without words left passes it on."""
        for code in order:
            while remaining[code] > 0 and take(code):
                remaining[code] -= 1
        leftover = sum(remaining[code] for code in exhausted)
        while leftover > 0:
            progressed = False
            for code in order:
                if leftover > 0 and code not in exhausted and take(code):
                    leftover -= 1
                    progressed = True
            if not progressed:
                break

    fill(first)
    fill(second)
    planned = [card for code in order for card in picks[code]]
    chosen = set(planned)
    # words learned today outside today's choice (the plan changed during the day)
    planned += [card for card in today.learned if card not in chosen]
    return planned, quota


def books(
    learner: store.Learner, day: date, plan: dict[str, Any] | None = None
) -> tuple[Book, Book]:
    """The state before `day` and the state after every row.

    The first is kept for the rest of the process: rows of the day itself do
    not change it, and a change of any earlier row (a merge, a repair) does.
    """
    rows, _ = learner.rows()
    limit = day.isoformat()
    earlier: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []
    for row in rows:
        (earlier if isinstance(row.get("day"), str) and row["day"] < limit else later).append(row)
    parameters = (plan if plan is not None else learner.plan()).get("parameters") or {}
    key = (
        limit,
        len(earlier),
        max((str(r.get("ts")) for r in earlier), default=""),
        repr(sorted(parameters.items())),
    )
    cached = learner.cache.get("before")
    if cached is not None and cached[0] == key:
        before: Book = cached[1]
    else:
        before = fitted_replay(earlier, parameters)
        learner.cache["before"] = (key, before)
    return before, extend(before, later)


def compute(learner: store.Learner, catalog: Catalog, day: date, *, ahead: int = 0) -> DayPlan:
    plan = learner.plan()
    before, book = books(learner, day, plan)
    today = activity(book, day)
    profile = attendance.profile(before.rows, day) if plan.get("presence") == "on" else None
    weekdays = profile.weekdays if profile else None
    retention = float(plan["retention"])
    scheduler = Scheduler(retention, before.parameters.default, presence=weekdays)
    codes = [item["code"] for item in plan["languages"]]
    schedulers = {
        code: Scheduler(retention, before.parameters.for_lang(code), presence=weekdays)
        for code in codes
    }
    directions = {DIRECTION_CODES[d] for d in plan["directions"]}
    suspended = learner.suspended()
    off = store.WEEKDAYS[day.weekday()] in plan["days_off"]
    extra = learner.extra_new(day)

    due_list: list[tuple[date, str]] = []
    later: list[tuple[date, str]] = []
    orphans = 0
    for card, state in before.cards.items():
        if state.lang not in codes:
            continue
        entry_id, direction = split_card(card)
        if catalog.entry(entry_id) is None:
            orphans += 1
            continue
        if entry_id in suspended or direction not in directions:
            continue
        due = state.due(schedulers.get(state.lang, scheduler))
        (due_list if due <= day else later).append((due, card))
    due_list.sort()
    later.sort()
    due_cards = [card for _, card in due_list]
    limit = plan.get("review_limit")
    if off:
        reviews: list[str] = []
    elif isinstance(limit, int):
        reviews = due_cards[:limit]
    else:
        reviews = due_cards
    overflow = 0 if off else len(due_cards) - len(reviews)

    planned = 0 if off else int(plan["new_per_day"])
    base = planned
    paced_new = None
    if profile is not None and profile.minutes and planned:
        per_card = attendance.seconds(before.rows)
        base = attendance.paced(planned, len(reviews), profile.minutes, per_card)
        paced_new = base if base < planned else None
    total = base + extra
    new, quota = select_new(plan, catalog, before, today, day, total, suspended, base=base)

    done = set(today.seen)
    drill = sorted(
        (card for card in today.seen if today.last_grade[card] in ("almost", "dont_know")),
        key=lambda card: today.last_ts[card],
    )
    ahead_cards = [card for _, card in later if card not in done][: max(0, ahead)]
    entries = {card: catalog.card(card) for card in {*reviews, *new, *drill, *ahead_cards}}
    lang_of = {card: card[:2] for card in entries}
    family = {card: str((entry or {}).get("concept", card)) for card, entry in entries.items()}
    arrange = interleave if plan["mix"] == "interleaved" else blocks
    distance = int(plan["sibling_distance"])
    due_of = {card: due for due, card in due_list}

    # The whole day's reviews and new words are put in order first and the
    # cards already answered are left out afterwards, so the order of what
    # remains never changes during the day.
    full_reviews = spread(
        arrange([c for c in reviews if entries.get(c)], lang_of, codes), family, distance, []
    )
    full_new = spread(
        arrange([c for c in new if entries.get(c)], lang_of, codes), family, distance, full_reviews
    )
    left_reviews = [c for c in full_reviews if c not in done]
    left_new = [c for c in full_new if c not in done]
    ahead_order = spread(
        [c for c in ahead_cards if entries.get(c)], family, distance, left_reviews + left_new
    )
    drill_order = spread(
        [c for c in drill if entries.get(c)],
        family,
        distance,
        left_reviews + left_new + ahead_order,
    )

    sequence: list[Item] = []
    for phase, ordered in (
        ("review", left_reviews),
        ("new", left_new),
        ("ahead", ahead_order),
        ("drill", drill_order),
    ):
        for card in ordered:
            entry = entries[card]
            assert entry is not None
            sequence.append(Item(card, lang_of[card], phase, entry, due_of.get(card)))

    return DayPlan(
        day=day,
        plan=plan,
        off=off,
        scheduler=scheduler,
        before=before,
        book=book,
        today=today,
        due=due_cards,
        reviews=reviews,
        overflow=overflow,
        new=new,
        drill=drill,
        sequence=sequence,
        extra=extra,
        orphans=orphans,
        quota=quota,
        schedulers=schedulers,
        presence=profile,
        planned_new=planned,
        paced_new=paced_new,
        due_tomorrow=sum(1 for due, card in later if due == day + timedelta(days=1)),
    )
