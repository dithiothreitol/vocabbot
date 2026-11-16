"""Creating and changing a learner's plan, always as a preview first."""

from __future__ import annotations

import copy
from datetime import datetime
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
    own = sorted((plan.get("parameters") or {}).keys())
    lines.append(
        assets.text(
            "plan.parameters",
            value=", ".join(assets.language_name(code) for code in own)
            or assets.text("plan.parameters_default"),
        )
    )
    return lines


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
        gate.Change(folder / store.REVIEWS, "write", ""),
        gate.Change(
            folder / store.DECISIONS, "write", assets.text("gate.decisions_header") + "\n\n"
        ),
    ]
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

    if any(p.name.startswith("plan") for p in store.conflict_copies(learner.root)):
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
        [gate.Change(learner.path(store.PLAN), "write", store.dump_json(new))],
        now,
        learner.path(store.DECISIONS),
    )


def set_preview(
    learner: store.Learner, catalog: Catalog, assignments: list[str], now: datetime
) -> dict[str, Any]:
    """Preview of a change of the plan."""
    if any(p.name.startswith("plan") for p in store.conflict_copies(learner.root)):
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
        [gate.Change(learner.path(store.PLAN), "write", store.dump_json(new))],
        now,
        learner.path(store.DECISIONS),
    )
