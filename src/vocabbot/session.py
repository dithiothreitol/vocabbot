"""What a learner does in a session: see the next cards, answer, grade, regrade.

These functions hold the guarantees of the engine:

- `next_items` never returns the answer of a card under review or in drill;
- `answer` grades a typed answer itself and logs the engine's grade;
- a new card is accepted only when it is on today's list;
- a card that is not due is accepted only as a review ahead of time;
- "known" (I knew this word before the course) only at a card's first showing;
- a regrade changes only the last grade of a card on the same day and is marked.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from vocabbot import answers, assets, store
from vocabbot import presence as attendance
from vocabbot.book import RATING, CardState, spread_key
from vocabbot.courses import Catalog, hide_other_answers, presentation, question, split_card
from vocabbot.errors import VocabError
from vocabbot.queue import DayPlan, compute

SELF_GRADES = ("known", "know", "almost", "dont_know")
MAX_GIVEN = 200
SECONDS = {"review": 10, "new": 25, "drill": 8, "ahead": 10}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _next_ts(rows: list[dict[str, Any]], now: datetime, day: date) -> str:
    last_day = max((str(r.get("day")) for r in rows if isinstance(r.get("day"), str)), default="")
    if last_day > day.isoformat():
        raise VocabError("day_before_last", day=day.isoformat(), last=last_day)
    stamp = store.iso(now)
    last_ts = max((str(r.get("ts")) for r in rows if isinstance(r.get("ts"), str)), default="")
    if stamp <= last_ts:
        moment = store.parse_iso(last_ts) + timedelta(microseconds=1)
        stamp = moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return stamp


def classify(
    dp: DayPlan, catalog: Catalog, learner: store.Learner, card: str, *, ahead: bool = False
) -> tuple[dict[str, Any], str, CardState | None]:
    """The entry, the kind of row an answer to `card` would be, and its state; or a refusal."""
    try:
        entry_id, _ = split_card(card)
    except ValueError:
        raise VocabError("bad_card", card=card) from None
    entry = catalog.entry(entry_id)
    if entry is None:
        raise VocabError("unknown_card", card=card)
    if entry["lang"] not in dp.lang_codes():
        raise VocabError("lang_not_in_plan", card=card, lang=entry["lang"])
    if entry_id in learner.suspended():
        raise VocabError("card_suspended", card=card)
    if card in dp.today.seen:
        return entry, "drill", dp.book.cards.get(card)
    state = dp.before.cards.get(card)
    if state is not None:
        due = state.due(dp.scheduler_for(state.lang))
        if due <= dp.day or ahead:
            return entry, "review", state
        raise VocabError("not_due", card=card, due=due.isoformat())
    if card in dp.new:
        return entry, "learn", None
    raise VocabError("not_in_today", card=card)


def _left(dp: DayPlan) -> dict[str, int]:
    counts = {"review": 0, "new": 0, "drill": 0, "ahead": 0}
    for item in dp.sequence:
        counts[item.phase] += 1
    return {"reviews": counts["review"], "new": counts["new"], "drill": counts["drill"]}


def _schedule_after(
    dp: DayPlan, card: str, kind: str, state: CardState | None, grade: str
) -> tuple[date | None, int | None]:
    scheduler = dp.scheduler_for(card[:2])
    key = spread_key(card, dp.day)
    if kind == "learn":
        memory = scheduler.first(RATING[grade])
        interval = scheduler.due_interval(memory.stability, key, dp.day)
        return dp.day + timedelta(days=interval), interval
    if kind == "review" and state is not None:
        memory = scheduler.review(state.memory, RATING[grade], (dp.day - state.last_day).days)
        interval = scheduler.due_interval(memory.stability, key, dp.day)
        return dp.day + timedelta(days=interval), interval
    if state is not None:
        return state.due(scheduler), None
    return None, None


def evaluate(dp: DayPlan, catalog: Catalog, entry: dict[str, Any], given: str) -> answers.Verdict:
    family = [
        e
        for e in catalog.family(str(entry["concept"]))
        if e["lang"] != entry["lang"] and e["id"] != entry["id"]
    ]
    lenient = dp.plan.get("diacritics") == "lenient"
    return answers.grade(given, entry, lenient=lenient, siblings=family)


def record(
    learner: store.Learner,
    dp: DayPlan,
    card: str,
    entry: dict[str, Any],
    kind: str,
    state: CardState | None,
    grade: str,
    now: datetime,
    *,
    verdict: answers.Verdict | None = None,
    given: str | None = None,
    ms: int | None = None,
    source: str = "cli",
    ahead: bool = False,
) -> dict[str, Any]:
    """Append one graded answer to the log and describe what it changed."""
    rows, _ = learner.rows()
    row: dict[str, Any] = {
        "ts": _next_ts(rows, now, dp.day),
        "day": dp.day.isoformat(),
        "card": card,
        "lang": entry["lang"],
        "grade": grade,
        "kind": kind,
        "source": source,
    }
    if verdict is not None:
        row["auto"] = verdict.grade
        if verdict.errors:
            row["error"] = verdict.errors[0]
        if verdict.other_lang:
            row["other_lang"] = verdict.other_lang
    if given is not None:
        row["given"] = given[:MAX_GIVEN]
    if ms is not None and ms > 0:
        row["ms"] = int(ms)
    early = state is not None and state.due(dp.scheduler_for(state.lang)) > dp.day
    if ahead and kind == "review" and early:
        row["ahead"] = True
    learner.append_review(row)
    due, interval = _schedule_after(dp, card, kind, state, grade)
    result: dict[str, Any] = {
        "card": card,
        "lang": entry["lang"],
        "kind": kind,
        "grade": grade,
        "grade_pl": assets.text(f"grades.{grade}"),
        "word": presentation(entry),
        "drill": grade in ("almost", "dont_know"),
    }
    if verdict is not None:
        result["auto"] = verdict.grade
        result["errors"] = list(verdict.errors)
        result["errors_pl"] = [assets.text(f"error_classes.{e}") for e in verdict.errors]
        if verdict.other_lang:
            result["other_lang"] = verdict.other_lang
        if verdict.matched and verdict.matched != entry["display"]:
            result["matched"] = verdict.matched
    if given is not None:
        result["given"] = given[:MAX_GIVEN]
    if due is not None:
        result["next_due"] = due.isoformat()
    if interval is not None:
        result["interval_days"] = interval
    return result


def answer(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    now: datetime,
    card: str,
    given: str,
    *,
    ahead: bool = False,
    source: str = "chat",
    ms: int | None = None,
) -> dict[str, Any]:
    """Grade a typed answer to a production card and log it."""
    dp = compute(learner, catalog, day)
    entry, kind, state = classify(dp, catalog, learner, card, ahead=ahead)
    if split_card(card)[1] != "p":
        raise VocabError("answer_needs_production", card=card)
    verdict = evaluate(dp, catalog, entry, given)
    return record(
        learner,
        dp,
        card,
        entry,
        kind,
        state,
        verdict.grade,
        now,
        verdict=verdict,
        given=given,
        ms=ms,
        source=source,
        ahead=ahead,
    )


def self_grade(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    now: datetime,
    card: str,
    grade: str,
    *,
    ahead: bool = False,
    source: str = "chat",
) -> dict[str, Any]:
    """The learner's own grade: "known" at a first showing, any grade for recognition cards."""
    if grade not in SELF_GRADES:
        raise VocabError("bad_grade", grade=grade)
    dp = compute(learner, catalog, day)
    entry, kind, state = classify(dp, catalog, learner, card, ahead=ahead)
    if grade == "known" and kind != "learn":
        raise VocabError("known_only_first", card=card)
    if grade != "known" and split_card(card)[1] == "p":
        raise VocabError("production_needs_answer", card=card)
    return record(learner, dp, card, entry, kind, state, grade, now, source=source, ahead=ahead)


LOOKUP_MAX = 10


def lookup(
    learner: store.Learner | None, catalog: Catalog, day: date | None, lang: str, text: str
) -> dict[str, Any]:
    """Course entries for a word in the language, or for a Polish meaning.

    Each match says whether its card waits in today's session, so a skill can
    keep the answer back until the session has asked it.
    """
    query = answers.normalize(text).casefold()
    if not query:
        raise VocabError("empty_stdin")
    waiting: set[str] = set()
    learning: set[str] = set()
    if learner is not None and day is not None:
        dp = compute(learner, catalog, day)
        waiting = {item.card.split("#")[0] for item in dp.sequence}
        learning = {card.split("#")[0] for card in dp.book.cards}
    pattern = re.compile(rf"(?<!\w){re.escape(query)}(?!\w)")
    exact: list[dict[str, Any]] = []
    by_meaning: list[dict[str, Any]] = []
    for entry in [*catalog.own(lang), *catalog.course(lang, list(store.LEVELS))]:
        names = {
            answers.normalize(str(entry.get(key, ""))).casefold() for key in ("display", "lemma")
        }
        named = query in names
        if not named and not pattern.search(str(entry["gloss"]["pl"]).casefold()):
            continue
        (exact if named else by_meaning).append(
            {
                "card": f"{entry['id']}#p",
                "level": entry.get("level"),
                "word": presentation(entry),
                "learning": entry["id"] in learning,
                "waiting_today": entry["id"] in waiting,
            }
        )
    found = exact + by_meaning
    return {"lang": lang, "matches": found[:LOOKUP_MAX], "more": max(0, len(found) - LOOKUP_MAX)}


def reveal(catalog: Catalog, card: str) -> dict[str, Any]:
    """The meaning of a recognition card, shown so the learner can grade the recall.

    A production card is graded from the typed answer, so its answer appears
    only in the result of `answer`.
    """
    try:
        entry_id, direction = split_card(card)
    except ValueError:
        raise VocabError("bad_card", card=card) from None
    if direction != "r":
        raise VocabError("reveal_production", card=card)
    entry = catalog.entry(entry_id)
    if entry is None:
        raise VocabError("unknown_card", card=card)
    return {"card": card, "word": presentation(entry)}


def regrade(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    now: datetime,
    card: str,
    grade: str,
    *,
    source: str = "chat",
) -> dict[str, Any]:
    """Change the last grade of a card given today, on the learner's request."""
    if grade not in ("know", "almost", "dont_know"):
        raise VocabError("bad_regrade", grade=grade)
    dp = compute(learner, catalog, day)
    target = dp.today.last_row.get(card)
    if target is None:
        raise VocabError("nothing_to_regrade", card=card)
    if target.grade == "known":
        raise VocabError("known_not_regraded", card=card)
    if target.grade == grade:
        raise VocabError("same_grade", card=card, grade=grade)
    rows, _ = learner.rows()
    learner.append_review(
        {
            "ts": _next_ts(rows, now, day),
            "day": day.isoformat(),
            "card": card,
            "lang": card[:2],
            "kind": "regrade",
            "grade": grade,
            "replaces": target.ts,
            "source": source,
        }
    )
    after = compute(learner, catalog, day)
    state = after.book.cards.get(card)
    out: dict[str, Any] = {"card": card, "grade": grade, "was": target.grade, "kind": target.kind}
    if state is not None:
        out["next_due"] = state.due(after.scheduler_for(state.lang)).isoformat()
    out["left"] = _left(after)
    return out


def next_items(
    learner: store.Learner, catalog: Catalog, day: date, *, count: int = 10, ahead: int = 0
) -> dict[str, Any]:
    """The next cards of the day. Answers appear only for new words, which are introduced."""
    dp = compute(learner, catalog, day, ahead=ahead)
    items = []
    for item in dp.sequence[: max(0, count)]:
        out: dict[str, Any] = {
            "card": item.card,
            "lang": item.lang,
            "phase": item.phase,
            "question": question(item.entry, item.direction),
        }
        if item.phase == "new":
            out["word"] = presentation(item.entry)
        items.append(out)
    hide_other_answers(catalog, items)
    return {"day": day.isoformat(), "items": items, "left": _left(dp), "off": dp.off}


def summary(learner: store.Learner, catalog: Catalog, dp: DayPlan) -> dict[str, Any]:
    """Counts of the day for each language, and the time the rest should take."""
    seen = set(dp.today.seen)
    learned = set(dp.today.learned)
    languages: dict[str, dict[str, Any]] = {}
    for item in dp.plan["languages"]:
        code = item["code"]
        reviews = [c for c in dp.reviews if c[:2] == code]
        new = [c for c in dp.new if c[:2] == code]
        languages[code] = {
            "reviews": len(reviews),
            "reviews_done": sum(1 for c in reviews if c in seen),
            "new": len(new),
            "new_done": sum(1 for c in new if c in learned),
            "drill": sum(1 for c in dp.drill if c[:2] == code),
            "paused": bool(item.get("paused")),
        }
    left = _left(dp)
    seconds = _seconds(dp)
    minutes = (
        left["reviews"] * seconds["review"]
        + left["new"] * seconds["new"]
        + left["drill"] * seconds["drill"]
    ) / 60
    warnings: list[dict[str, Any]] = []
    copies = store.conflict_copies(learner.root)
    if copies:
        warnings.append({"code": "conflict_copies", "files": [str(p) for p in copies]})
    _, damaged = learner.rows()
    if damaged:
        warnings.append({"code": "damaged_rows", "lines": damaged})
    if dp.orphans:
        warnings.append({"code": "orphans", "count": dp.orphans})
    if dp.overflow:
        warnings.append({"code": "review_limit", "count": dp.overflow})
    out: dict[str, Any] = {
        "day": dp.day.isoformat(),
        "off": dp.off,
        "extra_new": dp.extra,
        "languages": languages,
        "left": left,
        "minutes": round(minutes),
        "batch": int(dp.plan.get("batch", 1)),
        "warnings": warnings,
    }
    # pacing matters only while the courses still have the words it holds back
    if dp.paced_new is not None and dp.presence is not None and len(dp.new) >= dp.paced_new:
        out["paced"] = {
            "planned": dp.planned_new,
            "today": dp.paced_new,
            "usual_minutes": dp.presence.minutes,
        }
    hint = ahead_hint(dp)
    if hint:
        out["ahead_hint"] = hint
    return out


def ahead_hint(dp: DayPlan) -> dict[str, Any] | None:
    """Reviews of tomorrow worth doing today: tomorrow is a day off or one usually skipped."""
    tomorrow = dp.day + timedelta(days=1)
    off = store.WEEKDAYS[tomorrow.weekday()] in dp.plan["days_off"]
    skipped = dp.presence is not None and dp.presence.chance(tomorrow) < attendance.LOW
    if dp.off or not (off or skipped) or not dp.due_tomorrow:
        return None
    return {
        "day": tomorrow.isoformat(),
        "count": min(dp.due_tomorrow, attendance.AHEAD_MAX),
        "reason": "day_off" if off else "usually_skipped",
    }


def _seconds(dp: DayPlan) -> dict[str, float]:
    return attendance.seconds(dp.book.rows)


def add_extra(learner: store.Learner, catalog: Catalog, day: date, count: int) -> dict[str, Any]:
    """More new words for today (written to registers/day.json, the day's only setting)."""
    if count < 1:
        raise VocabError("bad_extra", count=count)
    extra = min(100, learner.extra_new(day) + count)
    learner.set_extra_new(day, extra)
    return summary(learner, catalog, compute(learner, catalog, day))
