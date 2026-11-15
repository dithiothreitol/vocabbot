#!/usr/bin/env python3
"""VocabBot confirmation gate for Claude Code and Cowork: a PreToolUse hook.

It sends two kinds of tool call to the host's own permission prompt, so that the
learner answers and not the model:

- `commit --confirm TOKEN` of the engine (`vocabbot.pyz` or the `vocabbot`
  program). The prompt shows what the stored preview changes.
- A host write tool (Write, Edit, MultiEdit, NotebookEdit) aimed at a file in a
  learner's folder, which would go around the engine.

Every other call passes without output. Standard library only; the hook input
arrives as JSON on standard input. VOCABBOT_HOOK=off in the host's environment
turns the prompt off for test runs with no person to answer (`claude -p`); the
engine still writes nothing without a previewed token.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

COMMIT_RE = re.compile(r"vocabbot(?:\.pyz)?['\"]?\s+commit\b")
TOKEN_RE = re.compile(r"--confirm(?:=|\s+)['\"]?([0-9a-f]{16})\b")
LEARNER_RE = re.compile(r"--learner(?:=|\s+)(?:\"([^\"]+)\"|'([^']+)'|(\S+))")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PLAN = Path("registers") / "plan.json"
PENDING = Path("registers") / ".pending"
TEXT = {
    "commit": "VocabBot prosi o potwierdzenie zmiany",
    "files": "pliki",
    "unknown": (
        "VocabBot: ten zapis nie wskazuje podglądu, który bramka może pokazać; potwierdź tylko "
        "wtedy, gdy zmiana była pokazana w rozmowie"
    ),
    "direct": ("VocabBot: {path} należy do folderu nauki, a ten zapis omija silnik i jego podgląd"),
}


def config_dir() -> Path:
    override = os.environ.get("VOCABBOT_CONFIG")
    return Path(override) if override else Path.home() / ".vocabbot"


def learner_root(start: Path) -> Path | None:
    for folder in [start, *start.parents]:
        if (folder / PLAN).is_file():
            return folder
    return None


def learner_from_command(command: str, cwd: Path) -> Path | None:
    """The folder after --learner; a regular expression keeps Windows backslashes."""
    found = LEARNER_RE.search(command)
    if not found:
        return None
    folder = Path(next(group for group in found.groups() if group)).expanduser()
    return folder if folder.is_absolute() else cwd / folder


def pointer() -> Path | None:
    try:
        saved = json.loads((config_dir() / "config.json").read_text(encoding="utf-8"))
        return Path(saved["learner"]) if saved.get("learner") else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def load_pending(folders: list[Path], token: str) -> dict | None:
    for folder in folders:
        path = folder / f"{token}.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            return data if isinstance(data, dict) else None
    return None


def commit_reason(record: dict | None) -> str:
    if not record:
        return TEXT["unknown"]
    lines = [str(line) for line in record.get("lines") or []]
    shown = "; ".join(lines[:4]) + (f" (+{len(lines) - 4})" if len(lines) > 4 else "")
    files = [Path(str(c.get("path", ""))).name for c in record.get("changes") or []]
    summary = str(record.get("summary") or "")
    return f"{TEXT['commit']}: {summary}. {shown} [{TEXT['files']}: {', '.join(files)}]"


def decide(data: dict) -> str | None:
    """The reason to ask, or None to let the call through."""
    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    cwd = Path(data.get("cwd") or os.getcwd())
    if tool == "Bash":
        command = str(tool_input.get("command") or "")
        if not COMMIT_RE.search(command):
            return None
        token = TOKEN_RE.search(command)
        folders = [config_dir() / "pending", cwd / PENDING]
        for root in (learner_from_command(command, cwd), learner_root(cwd), pointer()):
            if root is not None:
                folders.append(root / PENDING)
        record = load_pending(folders, token.group(1)) if token else None
        return commit_reason(record)
    if tool in WRITE_TOOLS:
        raw = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not raw:
            return None
        path = Path(str(raw)).expanduser()
        path = path if path.is_absolute() else cwd / path
        root = learner_root(path.resolve().parent)
        if root is None:
            return None
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            relative = path.name
        return TEXT["direct"].format(path=relative)
    return None


def ask(reason: str) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason[:1000],
        }
    }
    print(json.dumps(output, ensure_ascii=False))


def main() -> int:
    if os.environ.get("VOCABBOT_HOOK", "").strip().lower() == "off":
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        stream = getattr(sys.stdin, "buffer", None)
        raw = stream.read().decode("utf-8-sig") if stream is not None else sys.stdin.read()
        data = json.loads(raw or "{}")
    except (OSError, ValueError):
        return 0
    reason = decide(data if isinstance(data, dict) else {})
    if reason:
        ask(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
