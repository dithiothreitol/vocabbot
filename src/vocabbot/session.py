"""What a learner does in a session: see the next cards, answer, grade, regrade.

These functions hold the guarantees of the engine:

- `next_items` never returns the answer of a card under review or in drill, and
  with the plan's `new_words: ask` (the default, as in SuperMemo) of no card at
  all: a new word is asked at once and its first right answer means the learner
  knew it before the course ("known"); `new_words: show` introduces it first;
- the drill has two grades: an answer that is not "know" stays in the drill and
  is logged as "dont_know";
- `answer` grades a typed answer itself and logs the engine's grade; with the
  plan's `answer_mode: self` a production card may also be revealed (`reveal`)
  and graded by the learner (`self_grade`), as SuperMemo's "Check" does;
- a learner's note for a word comes with its answer, never with its question;
- a new card is accepted only when it is on today's list;
- a card that is not due is accepted only as a review ahead of time: one of the
  reviews the learner added to the day, or an answer marked `ahead`;
- the learner chooses the stage (reviews, new words, drill) and may add new
  words and reviews to the day; the engine's order holds when nothing is chosen;
- "known" (I knew this word before the course) only at a card's first showing;
- a regrade changes only the last grade of a card on the same day and is marked.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from vocabbot import answers, assets, families, store
from vocabbot import presence as attendance
from vocabbot.book import RATING, CardState, spread_key
from vocabbot.courses import Catalog, hide_other_answers, presentation, question, split_card
from vocabbot.errors import VocabError
from vocabbot.queue import STAGE_OF, STAGES, DayPlan, compute, staged

SELF_GRADES = ("known", "know", "almost", "dont_know")
# the grades the learner chooses from after `reveal`; the drill has two
REVEAL_GRADES = ("know", "almost", "dont_know")
DRILL_GRADES = ("know", "dont_know")
# the plan's settings of how a session shows a card, given with every result of a session
VIEW_KEYS = ("new_words", "answer_mode", "sentence_translation", "next_review")
MAX_GIVEN = 200
SECONDS = {"review": 10, "new": 25, "drill": 8, "ahead": 10}
# a level set too low: most of the last new words of a language were known before the course
HINT_WINDOW = 10
HINT_KNOWN = 8
# the stage an answer belongs to, so the next cards stay in the stage the learner chose
KIND_STAGE = {"learn": "new", "review": "reviews", "drill": "drill"}
MAX_EXTRA_NEW = 100
MAX_EXTRA_REVIEWS = 500


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
        if due <= dp.day or ahead or card in dp.ahead or card in dp.companions:
            return entry, "review", state
        raise VocabError("not_due", card=card, due=due.isoformat())
    if card in dp.new:
        return entry, "learn", None
    raise VocabError("not_in_today", card=card)


def view(plan: dict[str, Any]) -> dict[str, str]:
    """How the session shows a card: the plan's settings a chat, a card and a terminal follow."""
    return {key: str(plan.get(key, store.DEFAULT_PLAN[key])) for key in VIEW_KEYS}


def self_assessed(plan: dict[str, Any]) -> bool:
    """A production card may be revealed and graded by the learner (`answer_mode: self`)."""
    return str(plan.get("answer_mode", "type")) == "self"


def back_text(day: date, due: date | None, drill: bool) -> str | None:
    """When a card comes back, as the learner says it: today in the drill, tomorrow, in N days."""
    if drill:
        return assets.text("back.today")
    if due is None or due <= day:
        return None
    days = (due - day).days
    if days == 1:
        return assets.text("back.tomorrow")
    return assets.text("back.days", days=days)


def asks_new_words(plan: dict[str, Any]) -> bool:
    """New words come as questions at once (SuperMemo); otherwise they are shown first."""
    return str(plan.get("new_words", "ask")) == "ask"


def logged_grade(
    dp: DayPlan,
    kind: str,
    grade: str,
    entry: dict[str, Any] | None = None,
    catalog: Catalog | None = None,
) -> str:
    """The grade a row gets for a graded answer.

    A new word asked at once and answered right was known before the course,
    unless the learner saw its family in another language of the set today
    (plan `together`): a word worked out from its neighbour is learned, not
    known. The drill has two grades, as in SuperMemo: "almost" keeps the card
    there.
    """
    if kind == "learn" and grade == "know" and asks_new_words(dp.plan):
        neighbour = (
            entry is not None
            and catalog is not None
            and families.met_today(dp.plan, dp.today.seen, entry, catalog)
        )
        return "know" if neighbour else "known"
    if kind == "drill" and grade == "almost":
        return "dont_know"
    return grade


def _phases(dp: DayPlan) -> dict[str, int]:
    counts = {"review": 0, "new": 0, "drill": 0, "ahead": 0}
    for item in dp.sequence:
        counts[item.phase] += 1
    return counts


def progress(dp: DayPlan) -> dict[str, Any]:
    """The day's cards done and left, and the counter line a session shows with every card.

    A card counts once: a review when it is first answered today, a new word
    when it is first shown. Drill repeats are counted apart, as the cards left
    to consolidate. The totals are the sums of done and left, so the counter
    adds up even when a card leaves the day (a report of a mistake). Reviews
    ahead of their day count only on a day with such reviews (`ahead`).
    """
    seen, learned = set(dp.today.seen), set(dp.today.learned)
    phases = _phases(dp)
    # the cards left in each of the three stages; reviews before their day belong to reviews
    left = {
        "reviews": phases["review"] + phases["ahead"],
        "new": phases["new"],
        "drill": phases["drill"],
    }
    done = {
        "reviews": sum(1 for card in dp.reviews if card in seen),
        "new": sum(1 for card in dp.new if card in learned),
    }
    due = set(dp.reviews)
    ahead_done = sum(1 for card in dp.today.seen if card in dp.before.cards and card not in due)
    ahead_left = phases["ahead"]
    reviews, new = done["reviews"] + phases["review"], done["new"] + left["new"]
    finished = done["reviews"] + done["new"] + ahead_done
    parts = [
        assets.text(
            "progress.counter", done=finished, total=reviews + new + ahead_done + ahead_left
        )
    ]
    if new:
        parts.append(assets.text("progress.new", done=done["new"], total=new))
    if reviews:
        parts.append(assets.text("progress.reviews", done=done["reviews"], total=reviews))
    if ahead_done or ahead_left:
        parts.append(assets.text("progress.ahead", done=ahead_done, total=ahead_done + ahead_left))
    if left["drill"]:
        parts.append(assets.text("progress.drill", count=left["drill"]))
    out: dict[str, Any] = {"left": left, "done": done, "counter": " · ".join(parts)}
    if ahead_done or ahead_left:
        out["ahead"] = {"done": ahead_done, "left": ahead_left}
    return out


def day_progress(learner: store.Learner, catalog: Catalog, day: date) -> dict[str, Any]:
    """`progress` after the latest answers, for results that changed the day, with `view`."""
    dp = compute(learner, catalog, day)
    return {**progress(dp), "view": view(dp.plan)}


def _higher(levels: list[str]) -> list[str]:
    """The levels without the lowest one; one level up when the plan has a single level."""
    if len(levels) > 1:
        return levels[1:]
    index = store.LEVELS.index(levels[0])
    return [store.LEVELS[index + 1]] if index + 1 < len(store.LEVELS) else []


def _levels_text(levels: list[str]) -> str:
    indexes = [store.LEVELS.index(level) for level in levels]
    if len(levels) > 1 and indexes == list(range(indexes[0], indexes[-1] + 1)):
        return f"{levels[0]}-{levels[-1]}"
    return ",".join(levels)


def level_hint(
    rows: list[dict[str, Any]], catalog: Catalog, lang: str, plan: dict[str, Any], day: date
) -> dict[str, Any] | None:
    """A hint to raise the level when most of the last new words were known before the course.

    It looks at the last HINT_WINDOW new words of the language at the plan's
    current levels, whether marked "znałem" or answered, and comes when
    HINT_KNOWN of them were known. It comes once a day for the same levels: at
    the first new word of the day that reaches the mark. Words of levels the
    learner has just left do not count, so following the hint starts afresh.
    """
    item = next((i for i in plan["languages"] if i["code"] == lang), None)
    if item is None:
        return None
    levels = [str(level) for level in item["levels"]]
    higher = _higher(levels)
    if not higher:
        return None
    current = set(levels)
    learn: list[dict[str, Any]] = []
    for row in rows:
        if row.get("lang") != lang or row.get("kind") != "learn":
            continue
        entry = catalog.card(str(row.get("card")))
        if entry is not None and entry.get("level") in current:
            learn.append(row)

    def known_in(end: int) -> int | None:
        window = learn[max(0, end - HINT_WINDOW) : end]
        if len(window) < HINT_WINDOW:
            return None
        return sum(1 for r in window if r.get("grade") == "known")

    known = known_in(len(learn))
    if known is None or known < HINT_KNOWN:
        return None
    first_today = next(
        (i for i, r in enumerate(learn) if r.get("day") == day.isoformat()), len(learn)
    )
    for end in range(first_today + 1, len(learn)):
        earlier = known_in(end)
        if earlier is not None and earlier >= HINT_KNOWN:
            return None
    return {
        "lang": lang,
        "known": known,
        "of": HINT_WINDOW,
        "levels": _levels_text(levels),
        "suggested": _levels_text(higher),
        "setting": f"lang.{lang}.levels={_levels_text(higher)}",
    }


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
    """The engine's grade; a slip into the spelling of another language of the plan
    (paused ones too) names that language, which `status` counts as a mix-up."""
    family = [
        e
        for e in catalog.family(str(entry["concept"]))
        if e["lang"] != entry["lang"] and e["id"] != entry["id"]
    ]
    lenient = dp.plan.get("diacritics") == "lenient"
    near = [code for code in dp.lang_codes() if code != entry["lang"]]
    return answers.grade(given, entry, lenient=lenient, siblings=family, near=near)


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
    catalog: Catalog | None = None,
) -> dict[str, Any]:
    """Append one graded answer to the log and describe what it changed.

    With `catalog`, the result of a card learned by families (plan `together`)
    holds the family table.
    """
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
    if kind == "review" and early and (ahead or card in dp.ahead or card in dp.companions):
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
    note = learner.notes().get(str(entry["id"]))
    if note:
        result["word"]["note"] = note
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
    if str(dp.plan.get("next_review", "shown")) == "shown":
        back = back_text(dp.day, due, result["drill"])
        if back:
            result["back"] = back
    if catalog is not None:
        family = family_table(dp, catalog, card, entry)
        if family is not None:
            result["family"] = family
    return result


def family_table(
    dp: DayPlan, catalog: Catalog, card: str, entry: dict[str, Any]
) -> dict[str, Any] | None:
    """The family of an answered card in the other languages of the set (plan `together`).

    A card that still waits today, in any stage, shows no word, and neither does
    a word that answers a waiting card, so the table never answers a question of
    the day.
    """
    if not dp.team:
        return None
    waiting = {item.card for item in dp.sequence if item.card != card}
    return families.table(
        dp.plan,
        card,
        entry,
        catalog,
        lambda other: other in dp.book.cards,
        waiting,
        families.hidden_forms(waiting, catalog),
    )


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
    with_progress: bool = True,
) -> dict[str, Any]:
    """Grade a typed answer to a production card and log it."""
    dp = compute(learner, catalog, day)
    entry, kind, state = classify(dp, catalog, learner, card, ahead=ahead)
    if split_card(card)[1] != "p":
        raise VocabError("answer_needs_production", card=card)
    verdict = evaluate(dp, catalog, entry, given)
    result = record(
        learner,
        dp,
        card,
        entry,
        kind,
        state,
        logged_grade(dp, kind, verdict.grade, entry, catalog),
        now,
        verdict=verdict,
        given=given,
        ms=ms,
        source=source,
        ahead=ahead,
        catalog=catalog,
    )
    if kind == "learn":
        hint = level_hint(learner.rows()[0], catalog, str(entry["lang"]), dp.plan, day)
        if hint is not None:
            result["level_hint"] = hint
    if with_progress:
        result.update(day_progress(learner, catalog, day))
    return result


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
    with_progress: bool = True,
) -> dict[str, Any]:
    """The learner's own grade: "known" at a first showing, any grade for recognition cards."""
    if grade not in SELF_GRADES:
        raise VocabError("bad_grade", grade=grade)
    dp = compute(learner, catalog, day)
    entry, kind, state = classify(dp, catalog, learner, card, ahead=ahead)
    if grade == "known" and kind != "learn":
        raise VocabError("known_only_first", card=card)
    if grade != "known" and split_card(card)[1] == "p" and not self_assessed(dp.plan):
        raise VocabError("production_needs_answer", card=card)
    grade = logged_grade(dp, kind, grade, entry, catalog)
    result = record(
        learner,
        dp,
        card,
        entry,
        kind,
        state,
        grade,
        now,
        source=source,
        ahead=ahead,
        catalog=catalog,
    )
    if kind == "learn":
        hint = level_hint(learner.rows()[0], catalog, str(entry["lang"]), dp.plan, day)
        if hint is not None:
            result["level_hint"] = hint
    if with_progress:
        result.update(day_progress(learner, catalog, day))
    return result


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
    notes: dict[str, str] = {}
    if learner is not None and day is not None:
        dp = compute(learner, catalog, day)
        waiting = {item.card.split("#")[0] for item in dp.sequence}
        learning = {card.split("#")[0] for card in dp.book.cards}
        notes = learner.notes()
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
    for match in found:
        note = notes.get(match["card"].split("#")[0])
        if note:
            match["word"]["note"] = note
    return {"lang": lang, "matches": found[:LOOKUP_MAX], "more": max(0, len(found) - LOOKUP_MAX)}


def reveal(
    catalog: Catalog,
    card: str,
    learner: store.Learner | None = None,
    day: date | None = None,
) -> dict[str, Any]:
    """The answer of a card, shown so the learner can grade the recall.

    A recognition card shows its meaning. A production card shows its word only
    when the plan lets the learner grade the recall (`answer_mode: self`) and
    the card waits in today's session; otherwise its answer appears only in the
    result of `answer`. With the learner's folder the result also holds the
    card's phase, the grades to choose from (two in the drill) and the note.
    """
    try:
        entry_id, direction = split_card(card)
    except ValueError:
        raise VocabError("bad_card", card=card) from None
    if learner is None or day is None:
        if direction != "r":
            raise VocabError("reveal_production", card=card)
        entry = catalog.entry(entry_id)
        if entry is None:
            raise VocabError("unknown_card", card=card)
        return {"card": card, "word": presentation(entry)}
    entry = catalog.entry(entry_id)
    if entry is None:
        raise VocabError("unknown_card", card=card)
    dp = compute(learner, catalog, day)
    phase = next((item.phase for item in dp.sequence if item.card == card), None)
    if direction != "r":
        if not self_assessed(dp.plan):
            raise VocabError("reveal_production", card=card)
        if phase is None:
            raise VocabError("reveal_not_waiting", card=card)
    out: dict[str, Any] = {"card": card, "lang": entry["lang"], "word": presentation(entry)}
    if phase is not None:
        out["phase"] = phase
        out["stage"] = STAGE_OF[phase]
        out["grades"] = list(DRILL_GRADES if phase == "drill" else REVEAL_GRADES)
    note = learner.notes().get(entry_id)
    if note:
        out["word"]["note"] = note
    out.update(progress(dp))
    out["view"] = view(dp.plan)
    return out


def _entry_of(catalog: Catalog, card: str) -> str:
    try:
        entry_id = split_card(card)[0]
    except ValueError:
        raise VocabError("bad_card", card=card) from None
    if catalog.entry(entry_id) is None:
        raise VocabError("unknown_card", card=card)
    return entry_id


def flag(
    learner: store.Learner,
    catalog: Catalog,
    card: str,
    now: datetime,
    *,
    note: str = "",
    skip: bool = False,
    clear: bool = False,
) -> dict[str, Any]:
    """A report of a mistake in an entry, a word put aside (`skip`), or either withdrawn.

    Both take the entry out of the queue, the drill and the choice of new words;
    `clear` brings it back with the date it had.
    """
    entry_id = _entry_of(catalog, card)
    row: dict[str, Any] = {"ts": store.iso(now), "entry": entry_id, "card": card}
    if clear:
        row["clear"] = True
    elif skip:
        row["skip"] = True
    else:
        row["note"] = note.strip()[: store.NOTE_MAX]
    store.append_jsonl(learner.path(store.FLAGS), row)
    return {"entry": entry_id, "cleared": clear, "skipped": skip and not clear}


def save_note(
    learner: store.Learner,
    catalog: Catalog,
    card: str,
    now: datetime,
    text: str = "",
    *,
    clear: bool = False,
) -> dict[str, Any]:
    """The learner's own note for a word, shown with its answer; `clear` removes it."""
    entry_id = _entry_of(catalog, card)
    row: dict[str, Any] = {"ts": store.iso(now), "entry": entry_id}
    if clear:
        row["clear"] = True
    else:
        text = text.strip()
        if not text:
            raise VocabError("empty_note")
        if len(text) > store.NOTE_MAX:
            raise VocabError("note_too_long", max=store.NOTE_MAX, length=len(text))
        row["note"] = text
    store.append_jsonl(learner.path(store.NOTES), row)
    if clear:
        return {"entry": entry_id, "cleared": True}
    return {"entry": entry_id, "note": row["note"], "cleared": False}


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
    if target.kind == "drill" and grade == "almost":
        raise VocabError("drill_two_grades", card=card)
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
    out.update(progress(after))
    return out


def more(dp: DayPlan, catalog: Catalog) -> dict[str, int]:
    """What the learner can still add to the day: new words of the plan's levels, due
    reviews outside today's list, and reviews before their day."""
    directions = [store.DIRECTIONS[d] for d in dp.plan["directions"]]
    taken = set(dp.before.cards) | set(dp.new)
    entries: set[str] = set()
    for item in dp.plan["languages"]:
        if item.get("paused"):
            continue
        code = item["code"]
        for entry in [*catalog.first(code), *catalog.course(code, item["levels"])]:
            entries.add(str(entry["id"]))
    new = sum(
        1
        for entry_id in entries - dp.suspended
        for direction in directions
        if f"{entry_id}#{direction}" not in taken
    )
    return {
        "new": max(0, min(new, MAX_EXTRA_NEW - dp.extra)),
        "reviews_due": dp.waiting,
        "reviews_ahead": dp.later,
    }


def next_items(
    learner: store.Learner,
    catalog: Catalog,
    day: date,
    *,
    count: int = 10,
    ahead: int = 0,
    stage: str | None = None,
) -> dict[str, Any]:
    """The next cards of the day, without their answers.

    Only a plan with `new_words: show` gets the word of a new card, to
    introduce it before its question. With `stage` the cards of that stage
    come first (reviews, new or drill);
    `stage` in the result names the stage of the first card returned, and
    `stage_empty` the chosen stage when it has no cards left.
    """
    if stage is not None and stage not in STAGES:
        raise VocabError("bad_stage", stage=stage)
    dp = compute(learner, catalog, day, ahead=ahead)
    sequence = staged(dp.sequence, stage)
    introduce = not asks_new_words(dp.plan)
    items = []
    for item in sequence[: max(0, count)]:
        shown: dict[str, Any] = {
            "card": item.card,
            "lang": item.lang,
            "phase": item.phase,
            "question": question(item.entry, item.direction),
        }
        if item.phase == "new" and introduce:
            shown["word"] = presentation(item.entry)
        items.append(shown)
    hide_other_answers(catalog, items)
    out: dict[str, Any] = {
        "day": day.isoformat(),
        "items": items,
        **progress(dp),
        "off": dp.off,
        "view": view(dp.plan),
    }
    if sequence:
        out["stage"] = STAGE_OF[sequence[0].phase]
    if stage is not None and out.get("stage") != stage:
        out["stage_empty"] = stage
    out["more"] = more(dp, catalog)
    return out


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
    counts = progress(dp)
    left = counts["left"]
    seconds = _seconds(dp)
    phases = _phases(dp)
    minutes = sum(phases[phase] * seconds[phase] for phase in phases) / 60
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
        "extra_reviews": dp.extra_reviews,
        "more": more(dp, catalog),
        "languages": languages,
        "left": left,
        "done": counts["done"],
        "counter": counts["counter"],
        "learned_today": learned_today(catalog, dp),
        "minutes": round(minutes),
        "batch": int(dp.plan.get("batch", 1)),
        "new_words": str(dp.plan.get("new_words", "ask")),
        "view": view(dp.plan),
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
    if dp.team:
        # learning by families: the cards of one family come as a block, and the reviews
        # that joined a due card of their family count among the reviews before their day
        out["together"] = {"languages": dp.team, "joined": len(dp.companions)}
    return out


def learned_today(catalog: Catalog, dp: DayPlan) -> list[dict[str, Any]]:
    """The words first shown today, in their order, for the summary at the end of a session.

    A word whose card still waits in today's queue (the drill) stays out of
    the list until it is answered, so the list never shows an answer early.
    """
    out: list[dict[str, Any]] = []
    waiting = {item.card.split("#")[0] for item in dp.sequence}
    entries: set[str] = set(waiting)
    for card in dp.today.learned:
        entry_id = card.split("#")[0]
        entry = catalog.entry(entry_id)
        if entry is None or entry_id in entries:
            continue
        entries.add(entry_id)
        item = {"lang": entry["lang"], "word": entry["display"], "meaning": entry["gloss"]["pl"]}
        if dp.today.first_grade.get(card) == "known":
            item["known"] = True
        recording = presentation(entry).get("audio")
        if recording:
            item["audio"] = recording
        out.append(item)
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


def add_extra(
    learner: store.Learner, catalog: Catalog, day: date, count: int = 0, reviews: int = 0
) -> dict[str, Any]:
    """More new words and more reviews for today, written to registers/day.json.

    More reviews are the due cards outside today's list (over the review
    limit, or all of them on a day off), most overdue first, and then the
    cards with the nearest later dates as reviews before their day: the next
    round of reviews after the due ones. `added` says how many cards joined.
    """
    if count < 0 or reviews < 0 or count + reviews < 1:
        raise VocabError("bad_extra", count=count)
    before = compute(learner, catalog, day)
    if reviews:
        possible = before.waiting + before.later
        extra = min(MAX_EXTRA_REVIEWS, before.extra_reviews + min(reviews, possible))
        learner.set_extra_reviews(day, extra)
    if count:
        learner.set_extra_new(day, min(MAX_EXTRA_NEW, before.extra + count))
    after = compute(learner, catalog, day)
    out = summary(learner, catalog, after)
    was, now = _phases(before), _phases(after)
    out["added"] = {
        "new": now["new"] - was["new"],
        "reviews": now["review"] + now["ahead"] - was["review"] - was["ahead"],
    }
    return out
