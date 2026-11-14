"""Preview and commit: a change of the plan or a course is written only after a yes.

A writing command stores the exact change under a confirm token and shows it.
`vocabbot commit --confirm TOKEN` applies that change and nothing else; a
token older than 30 minutes, or one whose files changed since the preview, is
refused. In a terminal the program asks the question itself and applies the
change on the learner's yes.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from vocabbot import assets, store
from vocabbot.errors import VocabError

TTL = timedelta(minutes=30)
TOKEN = re.compile(r"^[0-9a-f]{16}$")


@dataclass(frozen=True)
class Change:
    path: Path
    action: str  # write, append or delete
    content: str = ""


def _sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _created(record: dict[str, Any]) -> datetime:
    return store.parse_iso(str(record["created"])).replace(tzinfo=timezone.utc)


def _sweep(folder: Path, now: datetime) -> None:
    if not folder.is_dir():
        return
    for item in folder.glob("*.json"):
        try:
            record = json.loads(item.read_text(encoding="utf-8"))
            if now - _created(record) > TTL:
                item.unlink()
        except (OSError, ValueError, KeyError):
            continue


def preview(
    pending: Path,
    summary: str,
    lines: list[str],
    changes: list[Change],
    now: datetime,
    decisions: Path | None,
) -> dict[str, Any]:
    """Store a change under a new token and describe it."""
    _sweep(pending, now)
    token = secrets.token_hex(8)
    record = {
        "token": token,
        "created": store.iso(now),
        "summary": summary,
        "lines": lines,
        "decisions": str(decisions) if decisions else None,
        "changes": [
            {
                "path": str(change.path),
                "action": change.action,
                "content": change.content,
                "base": _sha(change.path),
            }
            for change in changes
        ],
    }
    store.write_text(pending / f"{token}.json", store.dump_json(record))
    return {
        "preview": lines,
        "summary": summary,
        "token": token,
        "expires": store.iso(now + TTL),
        "files": [str(change.path) for change in changes],
    }


def commit(token: str, folders: list[Path], now: datetime, via: str) -> dict[str, Any]:
    """Apply the change stored under `token`, exactly as it was previewed."""
    if not TOKEN.match(token):
        raise VocabError("bad_token", token=token)
    found = next(
        (folder / f"{token}.json" for folder in folders if (folder / f"{token}.json").is_file()),
        None,
    )
    if found is None:
        raise VocabError("unknown_token", token=token)
    record = json.loads(found.read_text(encoding="utf-8"))
    if now - _created(record) > TTL:
        found.unlink()
        raise VocabError("token_expired", token=token)
    for change in record["changes"]:
        if _sha(Path(change["path"])) != change["base"]:
            raise VocabError("changed_since_preview", file=change["path"])
    for change in record["changes"]:
        path = Path(change["path"])
        if change["action"] == "write":
            store.write_text(path, change["content"])
        elif change["action"] == "append":
            for line in change["content"].splitlines():
                if line.strip():
                    store.append_jsonl(path, json.loads(line))
        elif change["action"] == "delete":
            if path.is_file():
                path.unlink()
        else:
            raise VocabError("bad_pending", token=token)
    if record.get("decisions"):
        moment = now.strftime("%Y-%m-%d %H:%M UTC")
        line = f"- {moment} · {record['summary']} · {assets.text(f'gate.via_{via}')} · {token}\n"
        decisions = Path(record["decisions"])
        decisions.parent.mkdir(parents=True, exist_ok=True)
        with decisions.open("ab") as fh:
            fh.write(line.encode("utf-8"))
    found.unlink()
    return {"applied": record["summary"], "lines": record["lines"], "token": token}
