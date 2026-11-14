"""Progress and forecast for each language."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from vocabbot import store
from vocabbot.book import RATING, CardState, replay
from vocabbot.courses import Catalog, card_id, split_card
from vocabbot.fsrs import AGAIN, GOOD, Memory, Scheduler
from vocabbot.queue import DIRECTION_CODES, compute, split_quota
from vocabbot.session import _seconds, summary

WINDOW_DAYS = 30
FORECAST_MAX = 365
RECENT_DAYS = 7
RECENT_MAX = 40
CONFUSIONS_MAX = 20


def status(learner: store.Learner, catalog: Catalog, day: date) -> dict[str, Any]:
    dp = compute(learner, catalog, day)
    plan = dp.plan
    book = dp.book
    scheduler = dp.scheduler
    directions = [DIRECTION_CODES[d] for d in plan["directions"]]
    since = day - timedelta(days=WINDOW_DAYS)
    week = day + timedelta(days=7)
    remaining = {item.card for item in dp.sequence}
    languages: dict[str, Any] = {}
    for item in plan["languages"]:
        code = item["code"]
        cards = {card: state for card, state in book.cards.items() if state.lang == code}
        levels: dict[str, Any] = {}
        for level in item["levels"]:
            course = catalog.course(code, [level])
            total = len(course) * len(directions)
            learned = sum(
                1 for e in course for d in directions if card_id(str(e["id"]), d) in cards
            )
            levels[level] = {"learned": learned, "total": total}
        own = catalog.own(code)
        if own:
            levels["own"] = {
                "learned": sum(
                    1 for e in own for d in directions if card_id(str(e["id"]), d) in cards
                ),
                "total": len(own) * len(directions),
            }
        recent = [row for row in book.rows if row.lang == code and row.day > since]
        reviews = [row for row in recent if row.kind == "review"]
        recalled = sum(1 for row in reviews if row.grade in ("know", "almost"))
        graded = [row for row in recent if row.auto]
        changed = sum(1 for row in graded if row.regraded or row.grade != row.auto)
        leeches = []
        for card, state in sorted(cards.items(), key=lambda kv: -kv[1].lapses):
            if state.lapses < int(plan["leech_lapses"]):
                break
            entry = catalog.card(card)
            leeches.append(
                {
                    "card": card,
                    "word": entry["display"] if entry else card,
                    "meaning": entry["gloss"]["pl"] if entry else "",
                    "lapses": state.lapses,
                    "waiting_today": card in remaining,
                }
            )
        errors = Counter(row.error for row in recent if row.error)
        confusions = []
        for row in reversed(recent):
            entry = catalog.card(row.card)
            if row.error == "wrong_language" and entry is not None:
                confusions.append(
                    {
                        "card": row.card,
                        "word": entry["display"],
                        "meaning": entry["gloss"]["pl"],
                        "given": row.raw.get("given", ""),
                        "other_lang": row.raw.get("other_lang"),
                        "day": row.day.isoformat(),
                        "waiting_today": row.card in remaining,
                    }
                )
        languages[code] = {
            "cards": len(cards),
            "levels": levels,
            "due_week": sum(1 for state in cards.values() if state.due(scheduler) <= week),
            "lapses": sum(state.lapses for state in cards.values()),
            "retention_30": round(recalled / len(reviews), 3) if reviews else None,
            "reviews_30": len(reviews),
            "changed_grades_30": round(changed / len(graded), 3) if graded else None,
            "errors_30": dict(errors.most_common()),
            "leeches": leeches[:20],
            "confusions": confusions[:CONFUSIONS_MAX],
            "recent": recent_words(catalog, cards, remaining, day),
            "paused": bool(item.get("paused")),
        }
    days = sorted({row.day for row in book.rows})
    streak = 0
    cursor = day if day in days else day - timedelta(days=1)
    learned_days = set(days)
    while cursor in learned_days:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "day": day.isoformat(),
        "today": summary(learner, catalog, dp),
        "languages": languages,
        "streak_days": streak,
        "target_retention": plan["retention"],
    }


def recent_words(
    catalog: Catalog, cards: dict[str, CardState], remaining: set[str], day: date
) -> list[dict[str, Any]]:
    """Words introduced in the last days, for practice outside the session.

    Cards still waiting in today's session and words marked as known are left
    out, so the list never shows the answer to a question the learner is
    about to get.
    """
    since = day - timedelta(days=RECENT_DAYS)
    picked = sorted(
        (
            (state.first_day, card)
            for card, state in cards.items()
            if state.first_day > since and not state.known and card not in remaining
        ),
        reverse=True,
    )
    out = []
    for first_day, card in picked[:RECENT_MAX]:
        entry = catalog.card(card)
        if entry is not None:
            out.append(
                {
                    "card": card,
                    "word": entry["display"],
                    "meaning": entry["gloss"]["pl"],
                    "first_day": first_day.isoformat(),
                }
            )
    return out


def _chance(card: str, day: date) -> float:
    digest = hashlib.sha1(f"{card}|{day.isoformat()}".encode()).hexdigest()
    return int(digest[:8], 16) / 0x100000000


def forecast(learner: store.Learner, catalog: Catalog, day: date, days: int = 30) -> dict[str, Any]:
    """Daily load and the days the planned levels are fully introduced.

    The simulation assumes the plan stays as it is and that each review is
    recalled with the probability the scheduler predicts for it.
    """
    days = max(1, min(days, FORECAST_MAX))
    dp = compute(learner, catalog, day)
    plan = dp.plan
    scheduler = Scheduler(retention=float(plan["retention"]))
    seconds = _seconds(dp)
    directions = [DIRECTION_CODES[d] for d in plan["directions"]]
    codes = {item["code"] for item in plan["languages"]}
    book = replay(learner.rows()[0])
    memory: dict[str, Memory] = {}
    last: dict[str, date] = {}
    buckets: dict[date, list[str]] = defaultdict(list)
    for card, state in book.cards.items():
        if state.lang not in codes or split_card(card)[1] not in directions:
            continue
        if catalog.card(card) is None:
            continue
        memory[card] = state.memory
        last[card] = state.last_day
        due = state.due(scheduler)
        buckets[
            max(due, day + timedelta(days=1)) if card in dp.today.seen else max(due, day)
        ].append(card)
    queues: dict[str, list[str]] = {}
    for item in plan["languages"]:
        code = item["code"]
        if item.get("paused"):
            continue
        cards = dict.fromkeys(
            card_id(str(e["id"]), d)
            for e in [*catalog.first(code), *catalog.course(code, item["levels"])]
            for d in directions
        )
        queues[code] = [c for c in cards if c not in memory and c not in dp.new]
    level_of = {}
    for item in plan["languages"]:
        for level in item["levels"]:
            for entry in catalog.course(item["code"], [level]):
                for d in directions:
                    level_of[card_id(str(entry["id"]), d)] = (item["code"], level)
    remaining_by_level: Counter[tuple[str, str]] = Counter(
        level_of[c] for q in queues.values() for c in q if c in level_of
    )
    weights = {
        item["code"]: int(item.get("weight", 1))
        for item in plan["languages"]
        if not item.get("paused")
    }
    complete: dict[str, dict[str, str]] = defaultdict(dict)
    rows: list[dict[str, Any]] = []
    carry: list[str] = []
    for offset in range(days):
        current = day + timedelta(days=offset)
        off = store.WEEKDAYS[current.weekday()] in plan["days_off"]
        due_now = carry + buckets.pop(current, [])
        if off:
            carry = due_now
            rows.append(
                {"day": current.isoformat(), "reviews": 0, "new": 0, "minutes": 0, "off": True}
            )
            continue
        limit = plan.get("review_limit")
        todays = due_now[:limit] if isinstance(limit, int) else due_now
        carry = due_now[len(todays) :]
        for card in todays:
            elapsed = (current - last[card]).days
            recalled = _chance(card, current) < scheduler.retrievability(memory[card], elapsed)
            memory[card] = scheduler.review(
                memory[card], GOOD if recalled else AGAIN, max(elapsed, 1)
            )
            last[card] = current
            buckets[current + timedelta(days=scheduler.interval(memory[card].stability))].append(
                card
            )
        if offset == 0:
            new_cards = [item.card for item in dp.sequence if item.phase == "new"]
        else:
            quota = split_quota(int(plan["new_per_day"]), weights, current.toordinal())
            new_cards = []
            for code, count in quota.items():
                take, queues[code] = queues[code][:count], queues[code][count:]
                new_cards += take
        for card in new_cards:
            first = RATING["know"] if _chance(card, current) < 0.8 else RATING["dont_know"]
            memory[card] = scheduler.first(first)
            last[card] = current
            buckets[current + timedelta(days=scheduler.interval(memory[card].stability))].append(
                card
            )
            if card in level_of:
                key = level_of[card]
                remaining_by_level[key] -= 1
                if remaining_by_level[key] == 0:
                    complete[key[0]][key[1]] = current.isoformat()
        minutes = (len(todays) * seconds["review"] + len(new_cards) * seconds["new"]) / 60
        rows.append(
            {
                "day": current.isoformat(),
                "reviews": len(todays),
                "new": len(new_cards),
                "minutes": round(minutes),
            }
        )
    for (code, level), left in remaining_by_level.items():
        if left > 0 and level not in complete[code]:
            per_week = split_quota(int(plan["new_per_day"]), weights, 0).get(code, 0) * (
                7 - len(plan["days_off"])
            )
            if per_week:
                weeks_needed = left / per_week
                complete[code][level] = (
                    day + timedelta(days=days + round(weeks_needed * 7))
                ).isoformat()
    working = [r for r in rows if not r.get("off")]
    return {
        "day": day.isoformat(),
        "days": rows,
        "average_reviews": round(sum(r["reviews"] for r in working) / len(working), 1)
        if working
        else 0,
        "average_minutes": round(sum(r["minutes"] for r in working) / len(working), 1)
        if working
        else 0,
        "peak_reviews": max((r["reviews"] for r in rows), default=0),
        "levels_complete": {
            code: dict(sorted(levels.items())) for code, levels in complete.items()
        },
        "assumes": (
            "reviews recalled with the predicted probability; "
            "four in five new words known at the first test"
        ),
    }
