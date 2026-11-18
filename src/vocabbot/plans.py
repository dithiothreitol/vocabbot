"""Creating and changing a learner's plan, always as a preview first."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from vocabbot import assets, gate, store
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError

INT_KEYS = (
    "new_per_day",
    "sibling_gap_days",
    "sibling_distance",
    "day_starts_at",
    "leech_lapses",
    "max_languages",
    "batch",
)


def describe(plan: dict[str, Any]) -> list[str]:
    """The plan in a few lines of the base language."""
    lines = []
    for item in plan["languages"]:
        name = assets.language_name(item["code"])
        levels = ", ".join(level.upper() for level in item["levels"])
        state = assets.text("plan.paused") if item.get("paused") else ""
        lines.append(
            assets.text(
                "plan.language_line",
                name=name,
                code=item["code"],
                levels=levels,
                weight=item.get("weight", 1),
                state=state,
            ).rstrip()
        )
    days_off = ", ".join(assets.text(f"weekdays.{d}") for d in plan["days_off"]) or assets.text(
        "plan.none"
    )
    limit = plan["review_limit"] if plan["review_limit"] is not None else assets.text("plan.none")
    lines += [
        assets.text("plan.new_per_day", value=plan["new_per_day"]),
        assets.text("plan.retention", value=round(float(plan["retention"]) * 100)),
        assets.text(
            "plan.directions",
            value=", ".join(assets.text(f"directions.{d}") for d in plan["directions"]),
        ),
        assets.text("plan.mix", value=assets.text(f"mix.{plan['mix']}")),
        assets.text("plan.sibling_gap", value=plan["sibling_gap_days"]),
        assets.text("plan.review_limit", value=limit),
        assets.text("plan.days_off", value=days_off),
        assets.text("plan.day_starts_at", value=plan["day_starts_at"]),
        assets.text("plan.diacritics", value=assets.text(f"diacritics.{plan['diacritics']}")),
        assets.text("plan.presence", value=assets.text(f"presence.{plan.get('presence', 'on')}")),
        assets.text("plan.batch", value=plan.get("batch", 1)),
        assets.text(
            "plan.new_words", value=assets.text(f"new_words.{plan.get('new_words', 'ask')}")
        ),
        assets.text(
            "plan.review_order",
            value=assets.text(f"review_order.{plan.get('review_order', 'due')}"),
        ),
        *(
            assets.text(f"plan.{key}", value=assets.text(f"{key}.{plan.get(key, default)}"))
            for key, default in (
                ("answer_mode", "type"),
                ("sentence_translation", "shown"),
                ("next_review", "shown"),
            )
        ),
    ]
    zone = plan.get("timezone") or ""
    lines.append(
        assets.text("plan.timezone", value=zone) if zone else assets.text("plan.timezone_local")
    )
    own = sorted((plan.get("parameters") or {}).keys())
    lines.append(
        assets.text(
            "plan.parameters",
            value=", ".join(assets.language_name(code) for code in own)
            or assets.text("plan.parameters_default"),
        )
    )
    return lines


def plan_copies(root: Path) -> list[Path]:
    """Conflict copies of registers/plan.json (copies of the plan's history count as rows)."""
    return [p for p in store.conflict_copies(root) if p.parent.name == "registers"]


def _check(plan: dict[str, Any], catalog: Catalog) -> None:
    problems = store.plan_problems(plan, catalog.installed())
    if problems:
        raise VocabError("plan_invalid", problems=problems, detail="; ".join(problems))


def init_preview(
    folder: Path,
    languages: list[str],
    new_per_day: int,
    catalog: Catalog,
    now: datetime,
    base: str = "pl",
    assignments: list[str] | None = None,
    *,
    pending: Path | None = None,
    pointer: bool = True,
) -> dict[str, Any]:
    """Preview of a new learner folder with its plan and the pointer to it.

    `assignments` are further settings in the form of `plan set` (days_off=sun).
    `pending` names the folder where the preview waits (by default ~/.vocabbot/pending),
    and `pointer=False` leaves out the pointer, as a server with many learners does.
    """
    folder = folder.expanduser().resolve()
    if (folder / store.PLAN).exists():
        raise VocabError("plan_exists", folder=str(folder))
    plan = store.complete_plan(
        {
            "base": base,
            "new_per_day": new_per_day,
            "languages": [store.parse_language(s) for s in languages],
        }
    )
    for assignment in assignments or []:
        _apply(plan, assignment)
    _check(plan, catalog)
    changes = [
        gate.Change(folder / store.PLAN, "write", store.dump_json(plan)),
        history_change(folder, None, plan, now),
    ]
    # logs the folder already holds (an account's rows a plan could not be made for) stay
    if not (folder / store.REVIEWS).exists():
        changes.append(gate.Change(folder / store.REVIEWS, "write", ""))
    if not (folder / store.DECISIONS).exists():
        changes.append(
            gate.Change(
                folder / store.DECISIONS, "write", assets.text("gate.decisions_header") + "\n\n"
            )
        )
    if pointer:
        # the pointer is a convenience: a sandbox may forbid writing outside the folder
        changes.append(
            gate.Change(
                store.config_dir() / store.CONFIG,
                "write",
                store.dump_json({"learner": str(folder)}),
                optional=True,
            )
        )
    lines = [assets.text("plan.init_folder", folder=str(folder)), *describe(plan)]
    summary = assets.text(
        "plan.init_summary", languages=", ".join(i["code"] for i in plan["languages"])
    )
    if pending is not None:
        return gate.preview(pending, summary, lines, changes, now, folder / store.DECISIONS)
    try:
        return gate.preview(
            store.config_dir() / "pending", summary, lines, changes, now, folder / store.DECISIONS
        )
    except OSError:
        # a sandbox that allows writing only in the working folder: wait in the new folder
        return gate.preview(
            folder / store.PENDING, summary, lines, changes, now, folder / store.DECISIONS
        )


def _value(key: str, raw: str) -> Any:
    raw = raw.strip()
    if key in INT_KEYS:
        try:
            return int(raw)
        except ValueError:
            raise VocabError("bad_value", key=key, value=raw) from None
    if key == "retention":
        try:
            value = float(raw.rstrip("%")) / (100 if raw.endswith("%") else 1)
        except ValueError:
            raise VocabError("bad_value", key=key, value=raw) from None
        return value
    if key == "review_limit":
        if raw.lower() in ("none", "brak", ""):
            return None
        try:
            return int(raw)
        except ValueError:
            raise VocabError("bad_value", key=key, value=raw) from None
    if key in ("days_off", "directions"):
        if raw.lower() in ("none", "brak", ""):
            return []
        return [part.strip().lower() for part in raw.split(",") if part.strip()]
    if key in store.CHOICES:
        return raw.lower()
    if key == "timezone":
        if raw.lower() in ("none", "brak", "local", ""):
            return ""
        return "UTC" if raw.upper() == "UTC" else raw
    if key == "parameters":
        if raw.lower() not in ("default", "fsrs6", "none"):
            raise VocabError("bad_value", key=key, value=raw)
        return {}
    raise VocabError("unknown_key", key=key)


def _apply(plan: dict[str, Any], assignment: str) -> None:
    key, sep, raw = assignment.partition("=")
    key = key.strip()
    if not sep or not key:
        raise VocabError("bad_assignment", value=assignment)
    if not key.startswith("lang."):
        plan[key] = _value(key, raw)
        if key == "parameters":
            plan["parameters_info"] = {}
        return
    parts = key.split(".")
    code = parts[1].lower() if len(parts) > 1 else ""
    languages: list[dict[str, Any]] = plan["languages"]
    item = next((lang for lang in languages if lang["code"] == code), None)
    value = raw.strip().lower()
    if len(parts) == 2:
        if value == "off":
            if item is None:
                raise VocabError("lang_not_in_plan", card="", lang=code)
            languages.remove(item)
        elif value in ("paused", "active"):
            if item is None:
                raise VocabError("lang_not_in_plan", card="", lang=code)
            item["paused"] = value == "paused"
        else:
            spec = store.parse_language(f"{code}:{value}")
            if item is None:
                languages.append({**spec, "paused": False})
            else:
                item.update(spec)
        return
    if item is None:
        raise VocabError("lang_not_in_plan", card="", lang=code)
    field = parts[2] if len(parts) == 3 else ""
    if field == "weight":
        try:
            item["weight"] = int(value)
        except ValueError:
            raise VocabError("bad_value", key=key, value=raw) from None
    elif field == "levels":
        item["levels"] = store.parse_levels(value)
    elif field == "paused":
        if value not in ("true", "false", "tak", "nie"):
            raise VocabError("bad_value", key=key, value=raw)
        item["paused"] = value in ("true", "tak")
    else:
        raise VocabError("unknown_key", key=key)


def _diff(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    lines = []
    for key in store.DEFAULT_PLAN:
        if key in ("languages", "parameters_info") or old.get(key) == new.get(key):
            continue
        if key == "parameters":
            was = ", ".join(sorted(old.get(key) or {})) or "FSRS-6"
            now = ", ".join(sorted(new.get(key) or {})) or "FSRS-6"
            lines.append(f"{key}: {was} → {now}")
            continue
        lines.append(f"{key}: {_show(old.get(key))} → {_show(new.get(key))}")
    old_langs = {item["code"]: item for item in old["languages"]}
    new_langs = {item["code"]: item for item in new["languages"]}
    for code in [*old_langs, *(c for c in new_langs if c not in old_langs)]:
        before, after = old_langs.get(code), new_langs.get(code)
        if before == after:
            continue
        lines.append(f"lang.{code}: {_show_lang(before)} → {_show_lang(after)}")
    return lines


def _show(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, list):
        return ",".join(str(v) for v in value) or "none"
    return str(value)


def _show_lang(item: dict[str, Any] | None) -> str:
    if item is None:
        return "off"
    state = " (paused)" if item.get("paused") else ""
    return f"{'-'.join([item['levels'][0], item['levels'][-1]])}:{item.get('weight', 1)}{state}"


def fit_preview(learner: store.Learner, catalog: Catalog, now: datetime) -> dict[str, Any]:
    """Preview of FSRS-6 parameters fitted to the log, for the languages where they win.

    A language gets parameters of its own only when, on the later part of the
    log, they predict the reviews better than FSRS-6 with its defaults
    (replay.compare); the other languages keep FSRS-6.
    """
    from vocabbot import replay

    if plan_copies(learner.root):
        raise VocabError("conflict_copies")
    old = learner.plan()
    rows, _ = learner.rows()
    codes = [item["code"] for item in old["languages"]]
    found = replay.fit_languages(rows, codes)
    new = copy.deepcopy(old)
    new["parameters"] = {code: info["parameters"] for code, info in found.items()}
    new["parameters_info"] = {
        code: {k: v for k, v in info.items() if k != "parameters"} for code, info in found.items()
    }
    _check(new, catalog)
    if new["parameters"] == (old.get("parameters") or {}):
        raise VocabError("no_better_fit")
    lines = []
    for code in codes:
        name = assets.language_name(code)
        if code in found:
            info = found[code]
            lines.append(
                assets.text(
                    "plan.fit_line",
                    name=name,
                    reviews=info["reviews"],
                    loss=f"{info['log_loss']:.3f}",
                    base=f"{info['log_loss_fsrs6']:.3f}",
                )
            )
        else:
            lines.append(assets.text("plan.fit_default", name=name))
    summary = assets.text(
        "plan.fit_summary",
        languages=", ".join(assets.language_name(code) for code in found) or "-",
    )
    return gate.preview(
        learner.path(store.PENDING),
        summary,
        lines,
        [
            gate.Change(learner.path(store.PLAN), "write", store.dump_json(new)),
            history_change(learner.root, old, new, now),
        ],
        now,
        learner.path(store.DECISIONS),
    )


# ---------------------------------------------------------------- the plan's history
#
# Every approved change of the plan adds a row to log/plan.jsonl: its time and the
# settings it set. Devices joined to one account join these rows like any log, and
# the plan is the last value of every setting (`fold`), so a change made on one
# device and another change made on a second device both hold.


def history_rows(root: Path) -> list[dict[str, Any]]:
    """The valid rows of the plan's history (with its conflict copies), in the order of time."""
    rows, _ = store.read_joined(root / store.PLAN_LOG, store.copies_of(root, store.PLAN_LOG))
    good = [row for row in rows if valid_history_row(row)]
    return sorted(good, key=lambda row: str(row["ts"]))


def _language_ok(item: Any) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and isinstance(item.get("levels"), list)
        and all(isinstance(level, str) for level in item["levels"])
    )


def _setting_ok(key: str, value: Any) -> bool:
    """A value of a known setting has the type the plan needs (its range is checked later)."""
    if key == "languages":
        return isinstance(value, list) and all(_language_ok(item) for item in value)
    if key in ("days_off", "directions"):
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if key == "review_limit":
        return value is None or (isinstance(value, int) and not isinstance(value, bool))
    if key in ("parameters", "parameters_info"):
        return isinstance(value, dict)
    if key in store.NUMBERS or key == "schema":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def valid_history_row(row: Any) -> bool:
    """A row of the history this version can apply.

    Settings this version does not know are kept for newer versions and left out
    of the plan here, so devices on different versions keep each other's rows.
    """
    if not isinstance(row, dict) or not isinstance(row.get("ts"), str):
        return False
    try:
        store.parse_iso(row["ts"])
    except ValueError:
        return False
    settings = row.get("set")
    unset = row.get("unset", [])
    langs = row.get("langs", {})
    return (
        isinstance(settings, dict)
        and all(
            _setting_ok(key, value) for key, value in settings.items() if key in store.DEFAULT_PLAN
        )
        and isinstance(unset, list)
        and all(isinstance(key, str) for key in unset)
        and isinstance(langs, dict)
        and all(
            item is None or (_language_ok(item) and item["code"] == code)
            for code, item in langs.items()
        )
    )


def fold(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The plan the history gives: the last value of every setting; None without rows.

    A change of one language (`langs`) changes only that language, so changes of
    two languages made on two devices both hold.
    """
    plan: dict[str, Any] = {}
    for row in sorted(rows, key=lambda r: str(r["ts"])):
        for key, value in row["set"].items():
            if key in store.DEFAULT_PLAN:
                plan[key] = copy.deepcopy(value)
        for key in row.get("unset", []):
            plan.pop(key, None)
        for code, item in row.get("langs", {}).items():
            languages = [dict(entry) for entry in plan.get("languages", []) if _language_ok(entry)]
            at = next((i for i, entry in enumerate(languages) if entry["code"] == code), None)
            if item is None:
                if at is not None:
                    languages.pop(at)
            elif at is not None:
                languages[at] = copy.deepcopy(item)
            else:
                languages.append(copy.deepcopy(item))
            plan["languages"] = languages
    return plan or None


def change_row(
    old: dict[str, Any] | None, new: dict[str, Any], now: datetime
) -> dict[str, Any] | None:
    """The row of one change: the settings whose value changed (all of them for a new plan).

    A change of the languages is kept per language (`langs`: the language as it
    is now, or None for a language taken out).
    """
    settings = {
        key: copy.deepcopy(value)
        for key, value in new.items()
        if (old is None or key not in old or old[key] != value)
        and (old is None or key != "languages")
    }
    unset = sorted(key for key in (old or {}) if key not in new)
    langs: dict[str, Any] = {}
    if old is not None:
        before = {i["code"]: i for i in old.get("languages", []) if _language_ok(i)}
        after = {i["code"]: i for i in new.get("languages", []) if _language_ok(i)}
        for code, item in after.items():
            if before.get(code) != item:
                langs[code] = copy.deepcopy(item)
        for code in before:
            if code not in after:
                langs[code] = None
    if not settings and not unset and not langs:
        return None
    row: dict[str, Any] = {"ts": store.iso(now), "set": settings}
    if unset:
        row["unset"] = unset
    if langs:
        row["langs"] = langs
    return row


def base_row(root: Path, before: datetime | None = None) -> dict[str, Any] | None:
    """A first row for a plan saved before its history began: the whole plan at its time.

    With `before`, the row comes before that moment (the change that follows it).
    """
    path = root / store.PLAN
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        moment = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except (OSError, ValueError):
        return None
    if before is not None:
        moment = min(moment, before - timedelta(microseconds=1))
    if not isinstance(raw, dict):
        return None
    settings = {key: value for key, value in raw.items() if key in store.DEFAULT_PLAN}
    return {"ts": store.iso(moment), "set": settings, "base": True}


def history_change(
    root: Path, old: dict[str, Any] | None, new: dict[str, Any], now: datetime
) -> gate.Change:
    """The rows a change of the plan adds to its history, with the first row when it is missing."""
    rows: list[dict[str, Any]] = []
    if old is not None and not history_rows(root):
        start = base_row(root, now)
        if start is not None:
            rows.append(start)
    row = change_row(old, new, now)
    if row is not None:
        rows.append(row)
    content = "".join(store.dump_line(row) + "\n" for row in rows)
    return gate.Change(root / store.PLAN_LOG, "append", content)


def ensure_history(root: Path, now: datetime | None = None) -> bool:
    """Give a plan without a history its first row; True when a row was written.

    With `now`, the row is not later than that moment, so a change made at `now`
    (a link's choice of plan) comes after it.
    """
    if not (root / store.PLAN).is_file() or history_rows(root):
        return False
    start = base_row(root, now + timedelta(microseconds=1) if now is not None else None)
    if start is None:
        return False
    store.append_jsonl(root / store.PLAN_LOG, start)
    return True


def apply_history(
    root: Path,
    installed: dict[str, list[str]] | Callable[[], dict[str, list[str]]],
) -> dict[str, Any]:
    """Write registers/plan.json from the history when it gives another valid plan.

    Returns {"changed": bool} and, for a plan that fails its check, the problems:
    the plan in force then stays as it was. `installed` may be a function, called
    only when the plan changes (reading every course takes a moment). A time zone
    this system does not know is left out rather than holding back every later
    change, since the zone data of systems differ.
    """
    folded = fold(history_rows(root))
    if folded is None:
        return {"changed": False}
    try:
        plan = store.complete_plan(folded)
    except (TypeError, KeyError, AttributeError, ValueError):
        return {"changed": False, "problems": ["the plan's history cannot be read"]}
    notes: list[str] = []
    zone_issue = store.zone_problem(plan.get("timezone", ""))
    if zone_issue:
        plan["timezone"] = ""
        notes.append(zone_issue)
    path = root / store.PLAN
    try:
        current = store.complete_plan(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, AttributeError, TypeError):
        current = None
    if current == plan:
        return {"changed": False, **({"notes": notes} if notes else {})}
    courses = installed() if callable(installed) else installed
    problems = store.plan_problems(plan, courses)
    if problems:
        return {"changed": False, "problems": problems}
    store.write_text(path, store.dump_json(plan))
    return {"changed": True, **({"notes": notes} if notes else {})}


def set_preview(
    learner: store.Learner, catalog: Catalog, assignments: list[str], now: datetime
) -> dict[str, Any]:
    """Preview of a change of the plan."""
    if plan_copies(learner.root):
        raise VocabError("conflict_copies")
    old = learner.plan()
    new = copy.deepcopy(old)
    for assignment in assignments:
        _apply(new, assignment)
    _check(new, catalog)
    changes = _diff(old, new)
    if not changes:
        raise VocabError("no_change")
    summary = assets.text("plan.set_summary", changes="; ".join(changes))
    return gate.preview(
        learner.path(store.PENDING),
        summary,
        changes,
        [
            gate.Change(learner.path(store.PLAN), "write", store.dump_json(new)),
            history_change(learner.root, old, new, now),
        ],
        now,
        learner.path(store.DECISIONS),
    )
