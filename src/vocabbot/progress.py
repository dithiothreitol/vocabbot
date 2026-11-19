"""Progress and forecast for each language."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from vocabbot import assets, families, store
from vocabbot import presence as attendance
from vocabbot.book import RATING, Book, CardState, ParameterSet, replay, second_answers, spread_key
from vocabbot.courses import Catalog, card_id, split_card
from vocabbot.fsrs import AGAIN, DEFAULT_PARAMETERS, FIT_MIN_ANSWERS, GOOD, Memory, Scheduler
from vocabbot.queue import DIRECTION_CODES, compute, rotate, split_quota
from vocabbot.session import _seconds, summary

WINDOW_DAYS = 30
FORECAST_MAX = 365
RECENT_DAYS = 7
RECENT_MAX = 40
CONFUSIONS_MAX = 20
ACTIVITY_DAYS = 84  # twelve weeks of answers per day, for the activity of the session page


def status(learner: store.Learner, catalog: Catalog, day: date) -> dict[str, Any]:
    dp = compute(learner, catalog, day)
    plan = dp.plan
    book = dp.book
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
        # mix-ups between languages: the word of another language ("dont_know") and its
        # spelling one letter or one accent away ("almost", `near`); typed answers only,
        # because a self-assessment leaves no text
        typed = [row for row in recent if "given" in row.raw]
        mixed = [row for row in typed if row.raw.get("other_lang")]
        near = [row for row in mixed if row.error != "wrong_language"]
        confusions = []
        for row in reversed(mixed):
            entry = catalog.card(row.card)
            if entry is not None:
                confusions.append(
                    {
                        "card": row.card,
                        "word": entry["display"],
                        "meaning": entry["gloss"]["pl"],
                        "given": row.raw.get("given", ""),
                        "other_lang": row.raw.get("other_lang"),
                        "near": row.error != "wrong_language",
                        "day": row.day.isoformat(),
                        "waiting_today": row.card in remaining,
                    }
                )
        languages[code] = {
            "cards": len(cards),
            "levels": levels,
            "due_week": sum(
                1 for state in cards.values() if state.due(dp.scheduler_for(code)) <= week
            ),
            "lapses": sum(state.lapses for state in cards.values()),
            "retention_30": round(recalled / len(reviews), 3) if reviews else None,
            "reviews_30": len(reviews),
            "changed_grades_30": round(changed / len(graded), 3) if graded else None,
            "errors_30": dict(errors.most_common()),
            "errors_30_pl": {
                assets.text(f"error_classes.{code}"): count for code, count in errors.most_common()
            },
            "leeches": leeches[:20],
            "confusions": confusions[:CONFUSIONS_MAX],
            "mixups_30": {
                "hard": len(mixed) - len(near),
                "near": len(near),
                "typed": len(typed),
            },
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
    per_day = Counter(row.day for row in book.rows)
    first = day - timedelta(days=ACTIVITY_DAYS - 1)
    activity = [
        {
            "day": (first + timedelta(days=n)).isoformat(),
            "answers": per_day.get(first + timedelta(days=n), 0),
        }
        for n in range(ACTIVITY_DAYS)
    ]
    states = learner.flag_states()
    out_of_queue: dict[str, list[dict[str, Any]]] = {"skip": [], "report": []}
    for entry_id, kind in sorted(states.items()):
        entry = catalog.entry(entry_id)
        if entry is not None:
            out_of_queue[kind].append(
                {
                    "card": f"{entry_id}#p",
                    "lang": entry["lang"],
                    "word": entry["display"],
                    "meaning": entry["gloss"]["pl"],
                }
            )
    return {
        "day": day.isoformat(),
        "today": summary(learner, catalog, dp),
        "languages": languages,
        "skipped": out_of_queue["skip"],
        "reported": out_of_queue["report"],
        "streak_days": streak,
        "activity": activity,
        "target_retention": plan["retention"],
        "schedule": schedule(dp),
        "families": family_report(book, catalog, dp.team, since),
    }


def _take_with_families(
    code: str,
    count: int,
    queues: dict[str, list[str]],
    queued: dict[str, set[str]],
    by_concept: dict[str, dict[str, list[str]]],
    met: dict[str, dict[str, date]],
    together: set[str],
    current: date,
) -> list[str]:
    """A day's new words of one language in the forecast, as `queue.select_new` takes them:
    the families met in another language of the set first, the oldest first, then the
    course order."""
    taken: list[str] = []
    if code in together:
        waiting = sorted(
            (min(day for lang, day in langs.items() if lang in together), concept)
            for concept, langs in met.items()
            if code not in langs and set(langs) & (together - {code})
        )
        for _, concept in waiting:
            for card in by_concept[code].get(concept, []):
                if len(taken) >= count:
                    break
                if card in queued.get(code, set()):
                    taken.append(card)
                    queued[code].discard(card)
                    met[concept].setdefault(code, current)
    rest = [card for card in queues[code] if card not in taken]
    if code in queued:
        rest = [card for card in rest if card in queued[code]]
    more, rest = rest[: count - len(taken)], rest[count - len(taken) :]
    for card in more:
        queued.get(code, set()).discard(card)
    queues[code] = rest
    return taken + more


def family_report(book: Book, catalog: Catalog, team: list[str], since: date) -> dict[str, Any]:
    """What learning by families did over 30 days (plan `together`).

    A block is a family's reviews of one day in two or more languages of the
    set; its first card is asked without a neighbour, the following ones after
    it, so the recall of both measures the hint of the neighbour. The mix-ups
    count the typed answers in another language of the plan.
    """
    out: dict[str, Any] = {"together": list(team)}
    if not team:
        return out
    groups: dict[tuple[date, str, str], list[Any]] = defaultdict(list)
    typed = mixed = 0
    for row in book.rows:
        if row.day <= since or row.lang not in team:
            continue
        if "given" in row.raw:
            typed += 1
            mixed += bool(row.raw.get("other_lang"))
        if row.kind != "review":
            continue
        entry = catalog.card(row.card)
        found = families.key_of(row.card, entry)
        if found is not None:
            groups[(row.day, found[0], found[1])].append(row)
    first: list[bool] = []
    following: list[bool] = []
    blocks = 0
    for rows in groups.values():
        if len({row.lang for row in rows}) < 2:
            continue
        blocks += 1
        ordered = sorted(rows, key=lambda row: str(row.raw.get("ts", "")))
        first.append(ordered[0].grade != "dont_know")
        following += [row.grade != "dont_know" for row in ordered[1:]]
    out.update(
        {
            "blocks_30": blocks,
            "first_recall_30": round(sum(first) / len(first), 3) if first else None,
            "following_recall_30": round(sum(following) / len(following), 3) if following else None,
            "mixups_per_100": round(100 * mixed / typed, 1) if typed else None,
        }
    )
    return out


def schedule(dp: Any) -> dict[str, Any]:
    """The parameters in force for each language, the intervals after a first answer,
    and the presence profile."""
    parameters = dp.before.parameters
    own = dict(parameters.languages)
    info = dp.plan.get("parameters_info") or {}
    have = sum(len(points) for points in second_answers(dp.before, set(own)).values())
    languages = {}
    for code in dp.lang_codes():
        scheduler = dp.scheduler_for(code)
        if code in own:
            source = "plan"
        elif parameters.default != DEFAULT_PARAMETERS:
            source = "initial"
        else:
            source = "default"
        languages[code] = {
            "source": source,
            **({"fit": info[code]} if code in own and code in info else {}),
            "first_intervals": {
                grade: scheduler.interval(scheduler.first(RATING[grade]).stability)
                for grade in ("dont_know", "almost", "know", "known")
            },
        }
    default = dp.scheduler
    return {
        "fitted": parameters.fitted,
        "second_answers": have,
        "fit_from": FIT_MIN_ANSWERS,
        "first_intervals": {
            grade: default.interval(default.first(RATING[grade]).stability)
            for grade in ("dont_know", "almost", "know", "known")
        },
        "languages": languages,
        "presence": dp.presence.as_dict() if dp.presence is not None else None,
        "presence_setting": dp.plan.get("presence", "on"),
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


FIRST_ANSWERS_MIN = 20  # first answers in the log before their share replaces the default


def _chance(card: str, day: date) -> float:
    digest = hashlib.sha1(f"{card}|{day.isoformat()}".encode()).hexdigest()
    return int(digest[:8], 16) / 0x100000000


def forecast(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    days: int = 30,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Daily load and the days the planned levels are fully introduced.

    The simulation assumes the plan stays as it is and that each review is
    recalled with the probability the scheduler predicts for it. `plan`
    replaces the folder's plan, as the preview of a change compares both.
    """
    days = max(1, min(days, FORECAST_MAX))
    dp = compute(learner, catalog, day, plan=plan)
    pace = dp.presence if dp.presence is not None and dp.presence.minutes else None
    return simulate(dp, catalog, days, book=dp.book, scheduler_for=dp.scheduler_for, pace=pace)


def simulate(
    dp: Any,
    catalog: Catalog,
    days: int,
    *,
    book: Book,
    scheduler_for: Callable[[str], Scheduler],
    absent: Callable[[date], bool] | None = None,
    pace: attendance.Presence | None = None,
) -> dict[str, Any]:
    """The coming days under one schedule: load, delays and the recall at each review.

    `absent` names the days the learner does not learn (besides the days off);
    `pace` keeps the new words within the usual minutes, as the plan's
    presence setting does.
    """
    day = dp.day
    plan = dp.plan
    seconds = _seconds(dp)
    directions = [DIRECTION_CODES[d] for d in plan["directions"]]
    codes = {item["code"] for item in plan["languages"]}
    memory: dict[str, Memory] = {}
    last: dict[str, date] = {}
    due_of: dict[str, date] = {}
    buckets: dict[date, list[str]] = defaultdict(list)
    for card, state in book.cards.items():
        if state.lang not in codes or split_card(card)[1] not in directions:
            continue
        if catalog.card(card) is None:
            continue
        memory[card] = state.memory
        last[card] = state.last_day
        due = state.due(scheduler_for(state.lang))
        due_of[card] = due
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
    # the first answer to a new word: a plan that asks new words at once gets a right answer
    # only for words known before the course; a plan that shows them first, for most words
    asks = str(plan.get("new_words", "ask")) == "ask"
    right_first = RATING["known" if asks else "know"]
    first_answers = [row.grade for row in book.rows if row.kind == "learn"]
    if len(first_answers) >= FIRST_ANSWERS_MIN:
        right_share = sum(g in ("know", "known") for g in first_answers) / len(first_answers)
    else:
        right_share = 0.2 if asks else 0.8
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
    reviewed = late = 0
    overdue = 0
    recall = 0.0
    # families (plan `together`): new words complete the families of the set first, and a
    # due card brings its family in the other languages of the set, as the day's queue does
    team = families.team(plan)
    together = set(team)
    keys: dict[str, families.Key] = {}
    members: dict[families.Key, list[str]] = defaultdict(list)
    met: dict[str, dict[str, date]] = defaultdict(dict)  # concept: language -> first day
    by_concept: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    queued: dict[str, set[str]] = {}
    joined_total = 0

    def note(card: str, first_day: date) -> None:
        found = families.key_of(card, catalog.card(card))
        if found is None:
            return
        keys[card] = found
        members[found].append(card)
        met[found[0]].setdefault(card[:2], first_day)

    if together:
        for card in memory:
            if card[:2] in together:
                note(card, book.cards[card].first_day if card in book.cards else day)
        for code in together:
            queued[code] = set(queues.get(code, []))
            for card in queues.get(code, []):
                queued_entry = catalog.card(card)
                if queued_entry is not None and queued_entry.get("concept"):
                    by_concept[code][str(queued_entry["concept"])].append(card)
    for offset in range(days):
        current = day + timedelta(days=offset)
        off = store.WEEKDAYS[current.weekday()] in plan["days_off"]
        away = absent is not None and offset > 0 and absent(current)
        due_now = carry + buckets.pop(current, [])
        if together:
            # a card reviewed early with its family left its former day
            due_now = [card for card in due_now if due_of.get(card, current) <= current]
        if off or away:
            carry = due_now
            rows.append(
                {
                    "day": current.isoformat(),
                    "reviews": 0,
                    "new": 0,
                    "minutes": 0,
                    "off": True,
                    **({"absent": True} if away and not off else {}),
                }
            )
            continue
        limit = plan.get("review_limit")
        todays = due_now[:limit] if isinstance(limit, int) else due_now
        carry = due_now[len(todays) :]
        for card in todays:
            scheduler = scheduler_for(card[:2])
            elapsed = (current - last[card]).days
            chance = scheduler.retrievability(memory[card], elapsed)
            recalled = _chance(card, current) < chance
            reviewed += 1
            recall += chance
            delay = (current - due_of.get(card, current)).days
            if delay > 0:
                late += 1
                overdue += delay
            memory[card] = scheduler.review(
                memory[card], GOOD if recalled else AGAIN, max(elapsed, 1)
            )
            last[card] = current
            stamp = spread_key(card, current)
            later = scheduler.due_interval(memory[card].stability, stamp, current)
            due_of[card] = current + timedelta(days=later)
            buckets[due_of[card]].append(card)
        joined: list[str] = []
        if together:
            if offset == 0:
                joined = [card for card in dp.companions if card not in dp.today.seen]
            else:
                dates = {card: (last[card], due_of[card]) for card in keys if card in last}
                anchors = [card for card in todays if card in keys]
                joined = families.joined(anchors, members, keys, dates, current)
            for card in joined:
                scheduler = scheduler_for(card[:2])
                elapsed = (current - last[card]).days
                chance = scheduler.retrievability(memory[card], elapsed)
                recalled = _chance(card, current) < chance
                reviewed += 1
                recall += chance
                memory[card] = scheduler.review(
                    memory[card], GOOD if recalled else AGAIN, max(elapsed, 1)
                )
                last[card] = current
                later = scheduler.due_interval(
                    memory[card].stability, spread_key(card, current), current
                )
                due_of[card] = current + timedelta(days=later)
                buckets[due_of[card]].append(card)
            joined_total += len(joined)
        if offset == 0:
            new_cards = [item.card for item in dp.sequence if item.phase == "new"]
        else:
            planned = int(plan["new_per_day"])
            if pace is not None and pace.minutes:
                planned = attendance.paced(
                    planned, len(todays) + len(joined), pace.minutes, seconds
                )
            quota = split_quota(planned, weights, current.toordinal())
            new_cards = []
            if together:
                for code in rotate(list(quota), current.toordinal()):
                    new_cards += _take_with_families(
                        code, quota[code], queues, queued, by_concept, met, together, current
                    )
            else:
                for code, count in quota.items():
                    take, queues[code] = queues[code][:count], queues[code][count:]
                    new_cards += take
        if together:
            for card in new_cards:
                if card[:2] in together:
                    note(card, current)
        for card in new_cards:
            scheduler = scheduler_for(card[:2])
            first = right_first if _chance(card, current) < right_share else RATING["dont_know"]
            memory[card] = scheduler.first(first)
            last[card] = current
            stamp = spread_key(card, current)
            later = scheduler.due_interval(memory[card].stability, stamp, current)
            due_of[card] = current + timedelta(days=later)
            buckets[due_of[card]].append(card)
            if card in level_of:
                key = level_of[card]
                remaining_by_level[key] -= 1
                if remaining_by_level[key] == 0:
                    complete[key[0]][key[1]] = current.isoformat()
        minutes = (
            (len(todays) + len(joined)) * seconds["review"] + len(new_cards) * seconds["new"]
        ) / 60
        rows.append(
            {
                "day": current.isoformat(),
                "reviews": len(todays) + len(joined),
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
        "reviews_total": reviewed,
        "late_share": round(late / reviewed, 3) if reviewed else 0.0,
        "overdue_days": round(overdue / reviewed, 2) if reviewed else 0.0,
        "recall": round(recall / reviewed, 3) if reviewed else None,
        **(
            {"joined_share": round(joined_total / reviewed, 3) if reviewed else 0.0}
            if together
            else {}
        ),
        "assumes": (
            "reviews recalled with the predicted probability; "
            "four in five new words known at the first test"
        ),
    }


WORKLOAD_DAYS = 28


def _chooser(schedulers: dict[str, Scheduler], fallback: Scheduler) -> Callable[[str], Scheduler]:
    return lambda lang: schedulers.get(lang, fallback)


def workload(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    days: int = WORKLOAD_DAYS,
    fitted: ParameterSet | None = None,
) -> dict[str, Any]:
    """The coming weeks under FSRS-6 and the other schedules, with the learner's usual
    days without learning taken from the presence profile."""
    dp = compute(learner, catalog, day)
    rows, _ = learner.rows()
    profile = dp.presence or attendance.profile(dp.before.rows, day)
    absent: Callable[[date], bool] | None = None
    if profile is not None:
        known = profile

        def away(current: date) -> bool:
            return _chance("absent", current) >= known.chance(current)

        absent = away
    retention = float(dp.plan["retention"])
    options: list[tuple[str, ParameterSet, bool]] = [
        ("fsrs6", ParameterSet(), False),
        ("fsrs6_presence", ParameterSet(), True),
    ]
    if fitted is not None and fitted.fitted:
        options += [("fit", fitted, False), ("fit_presence", fitted, True)]
    out = []
    for name, params, by_presence in options:
        if by_presence and profile is None:
            continue
        book = replay(rows, parameters=params)
        weekdays = profile.weekdays if by_presence and profile is not None else None
        schedulers = {
            code: Scheduler(retention, params.for_lang(code), presence=weekdays)
            for code in dp.lang_codes()
        }
        fallback = Scheduler(retention, params.default, presence=weekdays)
        pace = profile if by_presence and profile is not None and profile.minutes else None
        result = simulate(
            dp,
            catalog,
            days,
            book=book,
            scheduler_for=_chooser(schedulers, fallback),
            absent=absent,
            pace=pace,
        )
        out.append(
            {
                "name": name,
                **{
                    key: result[key]
                    for key in (
                        "average_reviews",
                        "average_minutes",
                        "peak_reviews",
                        "late_share",
                        "overdue_days",
                        "recall",
                    )
                },
            }
        )
    return {
        "days": days,
        "target_retention": retention,
        "presence": profile.as_dict() if profile else None,
        "variants": out,
    }
