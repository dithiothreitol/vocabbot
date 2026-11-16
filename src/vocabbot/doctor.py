"""Checks of a learner's folder, and the repairs it offers as previews."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from vocabbot import assets, gate, store
from vocabbot.book import order_key, replay, valid_row
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError


def check(learner: store.Learner, catalog: Catalog, now: datetime) -> dict[str, Any]:
    problems: list[dict[str, Any]] = []
    try:
        plan = learner.plan()
        for problem in store.plan_problems(plan, catalog.installed()):
            problems.append({"code": "plan", "detail": problem})
    except VocabError as exc:
        problems.append({"code": "plan", "detail": str(exc)})
    copies = store.conflict_copies(learner.root)
    if copies:
        problems.append({"code": "conflict_copies", "files": [str(p) for p in copies]})
    rows, damaged = learner.rows()
    if damaged:
        problems.append({"code": "damaged_rows", "file": store.REVIEWS, "lines": damaged})
    invalid = [i for i, row in enumerate(rows, 1) if not valid_row(row)]
    if invalid:
        problems.append({"code": "invalid_rows", "file": store.REVIEWS, "count": len(invalid)})
    book = replay(rows)
    orphans = sorted({row.card for row in book.rows if catalog.card(row.card) is None})
    if orphans:
        problems.append({"code": "orphans", "cards": orphans[:50], "count": len(orphans)})
    for problem in catalog.problems:
        problems.append({"code": "own_words", "detail": problem})
    pending = learner.path(store.PENDING)
    expired = []
    if pending.is_dir():
        for item in pending.glob("*.json"):
            try:
                created = store.parse_iso(json.loads(item.read_text("utf-8"))["created"])
            except (OSError, ValueError, KeyError):
                expired.append(item.name)
                continue
            if now.replace(tzinfo=None) - created > gate.TTL:
                expired.append(item.name)
    if expired:
        problems.append({"code": "expired_previews", "files": expired})
    return {"ok": not problems, "problems": problems, "rows": len(rows), "cards": len(book.cards)}


def merge_preview(learner: store.Learner, now: datetime) -> dict[str, Any]:
    """Join conflict copies of the review log, the flags and the notes into the main files."""
    changes: list[gate.Change] = []
    lines: list[str] = []
    damaged: list[bytes] = []
    for name in (store.REVIEWS, store.FLAGS, store.NOTES):
        main = learner.path(name)
        stem = main.name.rsplit(".", 1)[0]
        copies = [
            p
            for p in store.conflict_copies(learner.root)
            if p.parent == main.parent and p.name.startswith(stem)
        ]
        if not copies:
            continue
        rows, _ = store.read_jsonl(main)
        damaged += _damaged_lines(main)
        seen = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows}
        added = 0
        for copy in copies:
            damaged += _damaged_lines(copy)
            for row in store.read_jsonl(copy)[0]:
                key = json.dumps(row, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
                    added += 1
            changes.append(gate.Change(copy, "delete"))
        if name == store.REVIEWS:
            rows.sort(key=lambda r: order_key(r) if valid_row(r) else ("", "", ""))
        else:
            # the last row of an entry holds, so the rows of every copy go in the order of time
            rows.sort(key=lambda r: str(r.get("ts", "")))
        text = "".join(store.dump_line(r) + "\n" for r in rows)
        changes.insert(0, gate.Change(main, "write", text))
        lines.append(assets.text("doctor.merge_line", file=name, copies=len(copies), added=added))
    if not changes:
        raise VocabError("nothing_to_merge")
    if damaged:
        aside = learner.path(f"log/damaged-{now.strftime('%Y%m%d-%H%M%S')}.txt")
        text = b"".join(m + b"\n" for m in damaged).decode("utf-8", "replace")
        changes.append(gate.Change(aside, "write", text))
        lines.append(assets.text("doctor.repair_line", count=len(damaged), file=aside.name))
    return gate.preview(
        learner.path(store.PENDING),
        assets.text("doctor.merge_summary"),
        lines,
        changes,
        now,
        learner.path(store.DECISIONS),
    )


def _damaged_lines(path: Path) -> list[bytes]:
    _, numbers = store.read_jsonl(path)
    if not numbers:
        return []
    raw = path.read_bytes().split(b"\n")
    return [raw[number - 1] for number in numbers]


def repair_preview(learner: store.Learner, now: datetime) -> dict[str, Any]:
    """Move damaged lines of the review log aside and drop expired previews."""
    changes: list[gate.Change] = []
    lines: list[str] = []
    main = learner.path(store.REVIEWS)
    _, damaged = store.read_jsonl(main)
    if damaged:
        raw_lines = main.read_bytes().split(b"\n")
        keep = [
            raw for number, raw in enumerate(raw_lines, 1) if number not in damaged and raw.strip()
        ]
        moved = [raw for number, raw in enumerate(raw_lines, 1) if number in damaged]
        changes.append(
            gate.Change(main, "write", b"".join(k + b"\n" for k in keep).decode("utf-8"))
        )
        aside = learner.path(f"log/damaged-{now.strftime('%Y%m%d-%H%M%S')}.txt")
        changes.append(
            gate.Change(
                aside, "write", b"".join(m + b"\n" for m in moved).decode("utf-8", "replace")
            )
        )
        lines.append(assets.text("doctor.repair_line", count=len(damaged), file=str(aside.name)))
    pending = learner.path(store.PENDING)
    if pending.is_dir():
        for item in pending.glob("*.json"):
            try:
                created = store.parse_iso(json.loads(item.read_text("utf-8"))["created"])
                stale = now.replace(tzinfo=None) - created > gate.TTL + timedelta(seconds=1)
            except (OSError, ValueError, KeyError):
                stale = True
            if stale:
                changes.append(gate.Change(item, "delete"))
                lines.append(assets.text("doctor.expired_line", file=item.name))
    if not changes:
        raise VocabError("nothing_to_repair")
    return gate.preview(
        pending,
        assets.text("doctor.repair_summary"),
        lines,
        changes,
        now,
        learner.path(store.DECISIONS),
    )
