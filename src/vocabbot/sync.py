"""Joining a learner's folder with an account on a VocabBot server, and moving a record.

A folder linked to an account (`vocabbot login`) is a copy of the account's
record that works without a network. Every synchronisation sends the lines the
folder has and the account lacks, and fetches the lines the account has and
the folder lacks. The logs only grow on both sides, and the engine reads every
log in its own order (day, time, card), so the union of the rows gives one
schedule on every device.

The files that join line by line (streams):

    log/reviews.jsonl, log/flags.jsonl, log/notes.jsonl    the union of rows
    log/plan.jsonl                                         the plan's history
    log/decisions.md                                       the union of lines
    courses/<lang>/own.jsonl                               own words

registers/plan.json follows from log/plan.jsonl (`plans.apply_history`), and
registers/day.json keeps the larger number of the same day. Previews waiting
for a token (registers/.pending) stay on their device.

Both sides use this module: the server runs `serve` for an account's folder
under the account's lock, and the program runs `run` for the learner's folder
with a transport that reaches the server. A line is told apart by its content
(the canonical JSON of a row), so sending a line again adds nothing.

`archive` and `import_preview` move a whole record as a zip in the format of a
learner's folder: the export of the account page and of `vocabbot export`.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import secrets
import zipfile
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from vocabbot import __version__, assets, gate, plans, store
from vocabbot.book import TS, valid_row
from vocabbot.courses import ENTRY_ID, Catalog, entry_problems
from vocabbot.errors import VocabError

LOGS = (store.REVIEWS, store.FLAGS, store.NOTES, store.PLAN_LOG)
TEXTS = (store.DECISIONS,)
OWN_STREAM = re.compile(r"^courses/([a-z]{2})/own\.jsonl$")
ACCOUNT_STATE = "registers/sync-account.json"
PUSH_LIMIT = 5000  # lines of one stream a request sends
PULL_LIMIT = 5000  # lines of one stream a response brings
MAX_LINE = 8000  # characters of one line
FUTURE = timedelta(minutes=10)  # how far a device's clock may run ahead of the server
MAX_ROUNDS = 500
ARCHIVE_MANIFEST = "vocabbot-export.json"
# lines of a file split at LF only: splitlines would also split rows at U+2028 and its kin
NL = "\n"
ARCHIVE_MAX = 200 * 1024 * 1024  # bytes of an unpacked archive


class Transport(Protocol):
    """What reaches the account: one exchange of a request and its response."""

    def exchange(self, payload: dict[str, Any]) -> dict[str, Any]: ...


# ---------------------------------------------------------------- streams


def is_stream(name: Any) -> bool:
    if not isinstance(name, str):
        return False
    if name in LOGS or name in TEXTS:
        return True
    match = OWN_STREAM.match(name)
    return match is not None and match[1] in assets.known_languages()


def later_than(stamps: list[Any], now: datetime) -> str:
    """A time after every one of `stamps` and not before `now`: a link's row of the plan
    holds even when another device's clock runs ahead. Stamps further ahead than the
    account accepts (`FUTURE`) do not count."""
    limit = store.iso(now + FUTURE)
    latest = max(
        (s for s in stamps if isinstance(s, str) and TS.fullmatch(s) and s <= limit),
        default="",
    )
    moment = store.iso(now)
    if latest and latest >= moment:
        return store.iso(store.parse_iso(latest) + timedelta(microseconds=1))
    return moment


def plan_stamps(lines: list[str]) -> list[Any]:
    """The times of the rows of a plan's history."""
    return [row.get("ts") for row in (_parse(line) for line in lines) if row is not None]


def _order(name: str) -> tuple[int, str]:
    """Own words first (reviews of own words need them), then the plan, then the rest."""
    if OWN_STREAM.match(name):
        return (0, name)
    if name == store.PLAN_LOG:
        return (1, name)
    return (2, name)


def stream_names(root: Path) -> list[str]:
    """The streams the folder holds, in the order a synchronisation handles them.

    A log whose main file is missing counts when a conflict copy of it is there.
    """
    names = [
        name
        for name in (*LOGS, *TEXTS)
        if (root / name).is_file() or (name in LOGS and store.copies_of(root, name))
    ]
    courses = root / "courses"
    if courses.is_dir():
        for folder in sorted(courses.iterdir()):
            name = f"courses/{folder.name}/own.jsonl"
            if is_stream(name) and (root / name).is_file():
                names.append(name)
    return sorted(names, key=_order)


def read_lines(path: Path) -> list[str]:
    """The lines of a stream with text, as written (without LF or CR)."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return []
    out = []
    for chunk in raw.split(b"\n"):
        line = chunk.rstrip(b"\r")
        if not line.strip():
            continue
        try:
            out.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    return out


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _parse(line: str) -> dict[str, Any] | None:
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


def read_plan(path: Path) -> dict[str, Any] | None:
    """registers/plan.json as a dict, or None for a missing or damaged plan."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def line_key(name: str, line: str) -> str | None:
    """What tells a line apart: the canonical JSON of a row; None for a damaged row."""
    if name.endswith(".jsonl"):
        row = _parse(line)
        return store.canonical(row) if row is not None else None
    return line.rstrip()


def keys_of(name: str, lines: list[str]) -> set[str]:
    return {key for key in (line_key(name, line) for line in lines) if key is not None}


def digest(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def append_stream(root: Path, name: str, lines: list[str]) -> int:
    """Append lines to a stream; a row is written in the folder's own form."""
    if not lines:
        return 0
    if name.endswith(".jsonl"):
        rows = [row for row in (_parse(line) for line in lines) if row is not None]
        store.append_lines(root / name, [store.dump_line(row) for row in rows])
        return len(rows)
    store.append_lines(root / name, lines)
    return len(lines)


def merge_day(root: Path, given: Any) -> dict[str, Any] | None:
    """registers/day.json joined with another device's: the later day, or the larger numbers."""
    current = store.Learner(root).day_register()
    other = _day(given)
    mine = _day(current)
    if other is None:
        return mine
    if mine is None or other["day"] > mine["day"]:
        result = other
    elif other["day"] < mine["day"]:
        result = mine
    else:
        result = {"day": mine["day"]}
        for key in store.DAY_SETTINGS:
            value = max(mine.get(key, 0), other.get(key, 0))
            if value:
                result[key] = value
    if result != mine:
        store.write_text(root / store.DAY, store.dump_json(result))
    return result


def _day(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not isinstance(value.get("day"), str):
        return None
    try:
        date.fromisoformat(value["day"])
    except ValueError:
        return None
    out: dict[str, Any] = {"day": value["day"]}
    for key in store.DAY_SETTINGS:
        number = value.get(key, 0)
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            out[key] = min(number, 1000)
    return out


# ---------------------------------------------------------------- the account's side


def _moment(text: Any) -> datetime | None:
    if not isinstance(text, str) or not TS.match(text):
        return None
    try:
        return store.parse_iso(text).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def check_line(
    name: str, line: Any, catalog: Catalog, now: datetime
) -> tuple[str | None, str | None]:
    """The key of a line the account accepts, or the reason it is refused."""
    if not isinstance(line, str) or "\n" in line or not line.strip():
        return None, "not_a_line"
    if len(line) > MAX_LINE:
        return None, "too_long"
    if not name.endswith(".jsonl"):
        return line_key(name, line), None
    row = _parse(line)
    if row is None:
        return None, "not_a_row"
    late = now + FUTURE
    if name == store.REVIEWS:
        if not valid_row(row):
            return None, "invalid_row"
        if catalog.card(row["card"]) is None:
            return None, "unknown_card"
        moment = _moment(row["ts"])
        if (
            moment is None
            or moment > late
            or row["day"] > (late + timedelta(days=1)).date().isoformat()
        ):
            return None, "future"
    elif name in (store.FLAGS, store.NOTES):
        entry = row.get("entry")
        moment = _moment(row.get("ts"))
        if not isinstance(entry, str) or not ENTRY_ID.match(entry) or moment is None:
            return None, "invalid_row"
        if moment > late:
            return None, "future"
        note = row.get("note", "")
        if not isinstance(note, str) or len(note) > store.NOTE_MAX:
            return None, "invalid_row"
    elif name == store.PLAN_LOG:
        if not plans.valid_history_row(row):
            return None, "invalid_row"
        moment = _moment(row["ts"])
        if moment is None or moment > late:
            return None, "future"
    else:
        match = OWN_STREAM.match(name)
        lang = match[1] if match else ""
        if "ref" in row:
            ref = row.get("ref")
            if not isinstance(ref, str) or not ENTRY_ID.match(ref) or row.get("lang") != lang:
                return None, "invalid_row"
        else:
            if row.get("lang") != lang or not str(row.get("id", "")).startswith(f"{lang}-u"):
                return None, "invalid_row"
            if entry_problems(row, own=True):
                return None, "invalid_row"
            known = catalog.entry(str(row["id"]))
            if known is not None and store.canonical(known) != store.canonical(row):
                return None, "id_taken"
    return store.canonical(row), None


def account_state(root: Path, *, create: bool) -> dict[str, Any]:
    """The account's side of the links: the epoch that a fresh start of the folder changes."""
    path = root / ACCOUNT_STATE
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(state, dict) and isinstance(state.get("epoch"), str):
            return state
    except (OSError, ValueError):
        pass
    state = {"epoch": secrets.token_hex(8)}
    if create:
        store.write_text(path, store.dump_json(state))
    return state


def serve(
    root: Path,
    request: dict[str, Any],
    catalog: Callable[[], Catalog],
    installed: dict[str, list[str]],
    now: datetime,
    *,
    zone: str = "",
) -> dict[str, Any]:
    """The account's side of one synchronisation.

    The device sends, for every stream, how many lines of the account it has
    taken (`pulled`) and the lines it may lack (`rows`). The account keeps the
    lines it accepts and returns the lines from `pulled` on, as they were before
    this request's lines joined them; `cursor` is where the device stands after
    taking them. `zone` is the account's time zone, which the plan gets at the
    first link when it has none.
    """
    dry = bool(request.get("dry"))
    push_only = bool(request.get("push_only"))
    state = account_state(root, create=not dry)
    epoch = str(state["epoch"])
    # a probe reads from the cursors it sends; a device reads from them only within one epoch
    same = dry or request.get("epoch") == epoch
    files = _dict(request.get("files"))
    plan_changed = False
    if not dry:
        root.mkdir(parents=True, exist_ok=True)
        plans.ensure_history(root, now)
        account_plan = read_plan(root / store.PLAN)
        if request.get("plan_from") == "account" and account_plan is not None:
            plan = store.complete_plan(account_plan)
            if not plan.get("timezone") and zone:
                plan["timezone"] = zone
            sent_rows = _list(_dict(files.get(store.PLAN_LOG)).get("rows"))
            stamps = plan_stamps(read_lines(root / store.PLAN_LOG))
            stamps += plan_stamps([line for line in sent_rows if isinstance(line, str)])
            row = {"ts": later_than(stamps, now), "set": plan, "from": "link"}
            store.append_jsonl(root / store.PLAN_LOG, row)
            plan_changed = True
    names = sorted(
        set(stream_names(root)) | {name for name in files if is_stream(name)}, key=_order
    )
    snapshot = {name: read_lines(root / name) for name in names}
    received: dict[str, int] = {}
    refused: list[dict[str, Any]] = []
    if not dry:
        current = catalog()
        for name in names:
            pushed = _list(_dict(files.get(name)).get("rows"))
            if not pushed:
                continue
            if len(pushed) > PUSH_LIMIT:
                raise VocabError("sync_too_large", limit=PUSH_LIMIT)
            if name == store.REVIEWS or name in (store.FLAGS, store.NOTES):
                current = catalog()  # own words this request brought are entries now
            keys = keys_of(name, snapshot[name])
            accepted: list[str] = []
            for index, line in enumerate(pushed):
                key, reason = check_line(name, line, current, now)
                if reason is not None or key is None:
                    refused.append({"file": name, "index": index, "reason": reason})
                    continue
                if key in keys:
                    continue
                keys.add(key)
                accepted.append(line)
            added = append_stream(root, name, accepted)
            if added:
                received[name] = added
            if name == store.PLAN_LOG and added:
                plan_changed = True
    out_files: dict[str, Any] = {}
    for name in names:
        lines = snapshot[name]
        start = _dict(files.get(name)).get("pulled", 0) if same else 0
        start = start if isinstance(start, int) and 0 <= start <= len(lines) else 0
        if push_only:
            out_files[name] = {"rows": [], "cursor": start, "more": False}
            continue
        chunk = lines[start : start + PULL_LIMIT]
        more = start + len(chunk) < len(lines)
        cursor = start + len(chunk) if more else len(lines) + received.get(name, 0)
        out_files[name] = {"rows": chunk, "cursor": cursor, "more": more}
    out: dict[str, Any] = {
        "epoch": epoch,
        "files": out_files,
        "received": received,
        "refused": refused,
        "version": __version__,
    }
    if not dry:
        out["day"] = merge_day(root, request.get("day"))
        if plan_changed or plans.history_rows(root):
            applied = plans.apply_history(root, installed)
            if applied.get("problems"):
                out["plan_problems"] = applied["problems"]
    else:
        out["day"] = store.Learner(root).day_register() or None
    if dry:
        found = read_plan(root / store.PLAN)
        out["plan"] = store.complete_plan(found) if found is not None else None
    return out


# ---------------------------------------------------------------- the folder's side


def link_state(root: Path) -> dict[str, Any] | None:
    """The folder's link to an account (registers/sync.json), or None."""
    try:
        state = json.loads((root / store.SYNC).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict) or not isinstance(state.get("server"), str):
        return None
    return state


def save_state(root: Path, state: dict[str, Any]) -> None:
    store.write_text(root / store.SYNC, store.dump_json(state))


def _known(entry: dict[str, Any], lines: list[str]) -> int:
    """How many first lines of a stream the account has, as far as the folder knows."""
    known = entry.get("known", 0)
    if not isinstance(known, int) or known < 0 or known > len(lines):
        return 0
    if known and digest(lines[:known]) != entry.get("digest"):
        return 0  # the file changed below what was sent (a repair, a merge): send it all again
    return known


def _copy_lines(root: Path, name: str, lines: list[str]) -> list[str]:
    """Lines of conflict copies of a log that its main file lacks."""
    if name not in LOGS:
        return []
    keys = keys_of(name, lines)
    extra: list[str] = []
    for copy in store.copies_of(root, name):
        for line in read_lines(copy):
            key = line_key(name, line)
            if key is not None and key not in keys:
                keys.add(key)
                extra.append(line)
    return extra


def pending(root: Path, state: dict[str, Any] | None = None) -> int:
    """Lines of the folder the account has not taken yet, with the lines to send again."""
    state = state if state is not None else link_state(root)
    if state is None:
        return 0
    files = _dict(state.get("files"))
    waiting = 0
    for name in stream_names(root):
        lines = read_lines(root / name)
        entry = _dict(files.get(name))
        waiting += len(lines) - _known(entry, lines)
    for entry in files.values():
        waiting += len(_list(_dict(entry).get("retry")))
    return waiting


# reasons of a refusal that may pass: a clock running ahead, a course or a version of the
# program the account does not have yet; such lines go again with every synchronisation
RETRY_REASONS = frozenset({"future", "unknown_card", "invalid_row"})
RETRY_MAX = 2000


class _Keys:
    """The keys of a stream's lines, read once per synchronisation and extended as it grows."""

    def __init__(self) -> None:
        self._known: dict[str, tuple[int, set[str]]] = {}

    def of(self, name: str, lines: list[str]) -> set[str]:
        count, keys = self._known.get(name, (0, set()))
        if count > len(lines):
            count, keys = 0, set()
        keys |= keys_of(name, lines[count:])
        self._known[name] = (len(lines), keys)
        return keys


def run(
    root: Path,
    transport: Transport,
    now: datetime,
    installed: Callable[[], dict[str, list[str]]],
    *,
    push_only: bool = False,
) -> dict[str, Any]:
    """The folder's side: send what the account lacks, take what the folder lacks.

    `push_only` only sends (the terminal session sends in the background while
    it writes to the log, so nothing is appended to the folder meanwhile). The
    first synchronisation of a link chooses the plan, so it waits for a full one.
    """
    state = link_state(root)
    if state is None:
        raise VocabError("not_linked")
    first = _dict(state.get("first")) or None
    if push_only and first is not None:
        return {"ok": True, "skipped": True, "pending": pending(root, state)}
    files_state: dict[str, Any] = state.setdefault("files", {})
    plan_changed = False
    if (root / store.PLAN).is_file() and not push_only:
        plans.ensure_history(root, now)
        current = read_plan(root / store.PLAN)
        if (
            first is not None
            and first.get("plan_from") == "folder"
            and not first.get("written")
            and current is not None
        ):
            plan = store.complete_plan(current)
            zone = first.get("timezone")
            if not plan.get("timezone") and isinstance(zone, str) and zone:
                plan["timezone"] = zone
            stamps = [*plan_stamps(read_lines(root / store.PLAN_LOG)), first.get("after")]
            row = {"ts": later_than(stamps, now), "set": plan, "from": "link"}
            store.append_jsonl(root / store.PLAN_LOG, row)
            # written once: a failed exchange sends the same row again, never a new one
            first["written"] = row["ts"]
            state["first"] = first
            save_state(root, state)
            plan_changed = True
    sent = received = 0
    refused: list[dict[str, Any]] = []
    retry: dict[str, list[str]] = {}
    response: dict[str, Any] = {}
    plan_problems: list[str] = []
    keys = _Keys()
    # lines that go once per synchronisation besides the new ones: the rows of conflict
    # copies the main file lacks, and the lines the account refused for a passing reason
    extras: dict[str, list[str]] = {}
    for name in sorted(set(stream_names(root)) | set(files_state), key=_order):
        if is_stream(name):
            again = [
                line
                for line in _list(_dict(files_state.get(name)).get("retry"))
                if isinstance(line, str)
            ]
            extras[name] = [*_copy_lines(root, name, read_lines(root / name)), *again]
    for round_number in range(MAX_ROUNDS):
        payload_files: dict[str, Any] = {}
        sending: dict[str, dict[str, Any]] = {}
        for name in sorted(set(stream_names(root)) | set(files_state) | set(extras), key=_order):
            if not is_stream(name):
                continue
            lines = read_lines(root / name)
            entry = _dict(files_state.get(name))
            known = _known(entry, lines)
            chunk = lines[known : known + PUSH_LIMIT]
            waiting = extras.get(name, [])
            extra = waiting[: PUSH_LIMIT - len(chunk)]
            extras[name] = waiting[len(extra) :]
            rows = [*chunk, *extra]
            sending[name] = {"known": known, "count": len(chunk), "before": lines, "rows": rows}
            item: dict[str, Any] = {"pulled": entry.get("pulled", 0)}
            if rows:
                item["rows"] = rows
            payload_files[name] = item
        payload: dict[str, Any] = {
            "version": __version__,
            "epoch": state.get("epoch"),
            "account": state.get("login") or None,
            "files": payload_files,
            "day": store.Learner(root).day_register() or None,
        }
        if push_only:
            payload["push_only"] = True
        if first is not None and round_number == 0 and first.get("plan_from") == "account":
            payload["plan_from"] = "account"
        response = transport.exchange(payload)
        if not isinstance(response, dict) or not isinstance(response.get("files"), dict):
            raise VocabError("sync_failed", status="?", detail="the answer is not a sync answer")
        answered = _dict(response.get("account")).get("login")
        if state.get("login") and answered and answered != state["login"]:
            raise VocabError("other_account", login=str(answered), linked=str(state["login"]))
        if response.get("epoch") != state.get("epoch"):
            state["epoch"] = response.get("epoch")
        refused_now = [r for r in _list(response.get("refused")) if isinstance(r, dict)]
        refused += refused_now
        more = False
        for name, info in response["files"].items():
            if not is_stream(name) or not isinstance(info, dict):
                continue
            outgoing = sending.get(name)
            before = outgoing["before"] if outgoing is not None else read_lines(root / name)
            mine = keys.of(name, before)
            new: list[str] = []
            for line in _list(info.get("rows")):
                if not isinstance(line, str):
                    continue
                key = line_key(name, line)
                if key is not None and key not in mine:
                    mine.add(key)
                    new.append(line)
            got = append_stream(root, name, new)
            received += got
            if name == store.PLAN_LOG and got:
                plan_changed = True
            entry = files_state.setdefault(name, {})
            cursor = info.get("cursor", 0)
            entry["pulled"] = cursor if isinstance(cursor, int) and cursor >= 0 else 0
            more = more or bool(info.get("more"))
            known = outgoing["known"] if outgoing is not None else 0
            count = outgoing["count"] if outgoing is not None else 0
            sent += count
            if known + count >= len(before):
                # all the folder's lines went: the account has them and the lines just fetched,
                # unless another writer appended a row meanwhile, which then stays to be sent
                after = read_lines(root / name)
                exact = len(after) == len(before) + got and after[: len(before)] == before
                done = after if exact else before
                entry["known"], entry["digest"] = len(done), digest(done)
            else:
                entry["known"] = known + count
                entry["digest"] = digest(before[: known + count])
            if outgoing is not None:
                for refusal in refused_now:
                    index = refusal.get("index")
                    if (
                        refusal.get("file") == name
                        and refusal.get("reason") in RETRY_REASONS
                        and isinstance(index, int)
                        and 0 <= index < len(outgoing["rows"])
                    ):
                        retry.setdefault(name, []).append(outgoing["rows"][index])
        left = any(s["known"] + s["count"] < len(s["before"]) for s in sending.values())
        left = left or any(extras.values())
        if not push_only:
            merge_day(root, response.get("day"))
        if not more and not left:
            break
    for name, entry in files_state.items():
        if not isinstance(entry, dict):
            continue
        again = list(dict.fromkeys(retry.get(name, [])))[:RETRY_MAX]
        if again:
            entry["retry"] = again
        else:
            entry.pop("retry", None)
    # the plan always follows its history, also when a change of this device lost to a later one
    if not push_only and (plan_changed or plans.history_rows(root)):
        applied = plans.apply_history(root, installed)
        plan_problems = applied.get("problems", [])
    if isinstance(response.get("plan_problems"), list):
        plan_problems += [str(p) for p in response["plan_problems"]]
    if not push_only:
        state.pop("first", None)
    state.pop("failed", None)
    state["last"] = store.iso(now)
    if isinstance(response.get("version"), str):
        state["server_version"] = response["version"]
    save_state(root, state)
    out: dict[str, Any] = {
        "ok": True,
        "sent": sent,
        "received": received,
        "refused": len(refused),
        "pending": pending(root, state),
        "last": state["last"],
    }
    if refused:
        out["refused_rows"] = refused[:20]
    if plan_problems:
        out["plan_problems"] = plan_problems
    return out


def probe(transport: Transport) -> dict[str, Any]:
    """The account as it is, without changing it: its plan and every line of its streams."""
    streams: dict[str, list[str]] = {}
    cursors: dict[str, int] = {}
    plan: dict[str, Any] | None = None
    for _ in range(MAX_ROUNDS):
        response = transport.exchange(
            {
                "version": __version__,
                "dry": True,
                "epoch": None,
                "files": {name: {"pulled": cursor} for name, cursor in cursors.items()},
            }
        )
        if not isinstance(response.get("files"), dict):
            raise VocabError("sync_failed", status="?", detail="the answer is not a sync answer")
        plan = response.get("plan") if isinstance(response.get("plan"), dict) else None
        more = False
        for name, info in response["files"].items():
            if not is_stream(name) or not isinstance(info, dict):
                continue
            rows = [line for line in info.get("rows", []) if isinstance(line, str)]
            streams.setdefault(name, []).extend(rows)
            cursors[name] = int(info.get("cursor", 0))
            more = more or bool(info.get("more"))
        if not more:
            break
    return {"plan": plan, "streams": streams, "account": response.get("account") or {}}


def link_preview(
    learner: store.Learner,
    server: str,
    found: dict[str, Any],
    plan_from: str,
    now: datetime,
) -> dict[str, Any]:
    """The preview of linking the folder to the account: what joins, and whose plan holds."""
    account = found.get("account") or {}
    login = str(account.get("login") or "")
    zone = str(account.get("timezone") or "")
    root = learner.root
    lines = [assets.text("sync.link_title", folder=str(root), login=login, server=server)]
    remote: dict[str, list[str]] = found.get("streams") or {}
    for name, label in (
        (store.REVIEWS, "sync.link_reviews"),
        (store.NOTES, "sync.link_notes"),
        (store.FLAGS, "sync.link_flags"),
    ):
        here = keys_of(name, read_lines(root / name))
        there = keys_of(name, remote.get(name, []))
        lines.append(
            assets.text(label, local=len(here), remote=len(there), total=len(here | there))
        )
    own_here = sum(
        len(keys_of(name, read_lines(root / name)))
        for name in stream_names(root)
        if OWN_STREAM.match(name)
    )
    own_there = sum(
        len(keys_of(name, rows)) for name, rows in remote.items() if OWN_STREAM.match(name)
    )
    if own_here or own_there:
        lines.append(assets.text("sync.link_own", local=own_here, remote=own_there))
    account_plan = found.get("plan")
    chosen = learner.plan() if plan_from == "folder" or not account_plan else account_plan
    lines.append(
        assets.text(
            "sync.link_plan_folder" if chosen is not account_plan else "sync.link_plan_account"
        )
    )
    lines += ["  " + line for line in plans.describe(store.complete_plan(chosen))]
    if not chosen.get("timezone") and zone:
        lines.append(assets.text("sync.link_timezone", zone=zone))
    lines.append(assets.text("sync.link_after"))
    first: dict[str, Any] = {"plan_from": "folder" if chosen is not account_plan else "account"}
    if zone:
        first["timezone"] = zone
    stamps = [s for s in plan_stamps(remote.get(store.PLAN_LOG, [])) if isinstance(s, str)]
    if stamps:
        first["after"] = max(stamps)
    state = {"server": server, "login": login, "first": first}
    summary = assets.text("sync.link_summary", login=login, server=server)
    return gate.preview(
        learner.path(store.PENDING),
        summary,
        lines,
        [gate.Change(root / store.SYNC, "write", store.dump_json(state))],
        now,
        learner.path(store.DECISIONS),
    )


def plans_differ(learner: store.Learner, found: dict[str, Any]) -> bool:
    """True when the folder and the account both have a plan and the plans are not the same."""
    account_plan = found.get("plan")
    if not isinstance(account_plan, dict):
        return False
    mine = {k: v for k, v in learner.plan().items() if k not in ("parameters_info",)}
    theirs = {
        k: v for k, v in store.complete_plan(account_plan).items() if k not in ("parameters_info",)
    }
    return mine != theirs


# ---------------------------------------------------------------- moving a record


def archive(root: Path, now: datetime) -> bytes:
    """The record as a zip in the format of a learner's folder.

    A log goes with the rows of its conflict copies that the main file lacks, so
    nothing the engine counts is left out.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        manifest = {"format": 1, "version": __version__, "created": store.iso(now)}
        zipped.writestr(ARCHIVE_MANIFEST, store.dump_json(manifest))
        for name in (store.PLAN, store.DAY):
            if (root / name).is_file():
                zipped.writestr(name, (root / name).read_bytes())
        for name in stream_names(root):
            lines = read_lines(root / name)
            lines += _copy_lines(root, name, lines)
            zipped.writestr(name, "".join(line + "\n" for line in lines))
    return buffer.getvalue()


def read_archive(data: bytes) -> dict[str, str]:
    """The files of an archive, by their place in a learner's folder; anything else is refused."""
    try:
        zipped = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError):
        raise VocabError("bad_archive", detail="not a zip file") from None
    files: dict[str, str] = {}
    left = ARCHIVE_MAX
    with zipped:
        names = zipped.namelist()
        if ARCHIVE_MANIFEST not in names:
            raise VocabError("bad_archive", detail=f"no {ARCHIVE_MANIFEST}")
        if len(names) != len(set(names)):
            raise VocabError("bad_archive", detail="a file appears twice")
        for info in zipped.infolist():
            name = info.filename
            if info.is_dir() or name == ARCHIVE_MANIFEST:
                continue
            if name not in (store.PLAN, store.DAY) and not is_stream(name):
                raise VocabError("bad_archive", detail=f"unexpected file {name[:80]}")
            try:
                # read what the file really holds, at most what is left of the limit
                with zipped.open(info) as handle:
                    raw = handle.read(left + 1)
                text = raw.decode("utf-8").replace("\r\n", "\n")
            except (UnicodeDecodeError, zipfile.BadZipFile, OSError, RuntimeError):
                raise VocabError("bad_archive", detail=f"{name[:80]} cannot be read") from None
            left -= len(raw)
            if left < 0:
                raise VocabError("bad_archive", detail="too large")
            files[name] = text
    return files


def import_preview(
    root: Path,
    data: bytes,
    installed: dict[str, list[str]],
    now: datetime,
    *,
    pointer: bool = True,
) -> dict[str, Any]:
    """The preview of importing an archive: a new folder, or the lines a folder lacks."""
    files = read_archive(data)
    root = root.expanduser().resolve()
    lines = [assets.text("sync.import_title", folder=str(root))]
    changes: list[gate.Change] = []
    if not (root / store.PLAN).is_file():
        if store.PLAN not in files:
            raise VocabError("bad_archive", detail="no plan")
        # a folder without a plan that holds logs is not a new folder: nothing is written over
        taken = [name for name in stream_names(root) if read_lines(root / name)]
        if taken:
            raise VocabError("folder_not_empty", folder=str(root))
        try:
            plan = store.complete_plan(json.loads(files[store.PLAN]))
        except (ValueError, AttributeError, TypeError):
            raise VocabError("bad_archive", detail="the plan cannot be read") from None
        problems = store.plan_problems(plan, installed)
        if problems:
            raise VocabError("plan_invalid", problems=problems, detail="; ".join(problems))
        for name, text in sorted(files.items()):
            changes.append(gate.Change(root / name, "write", text))
        lines.append(
            assets.text(
                "sync.import_new",
                reviews=len(keys_of(store.REVIEWS, files.get(store.REVIEWS, "").split(NL))),
            )
        )
        lines += ["  " + line for line in plans.describe(plan)]
        if pointer:
            changes.append(
                gate.Change(
                    store.config_dir() / store.CONFIG,
                    "write",
                    store.dump_json({"learner": str(root)}),
                    optional=True,
                )
            )
        pending_folder = store.config_dir() / "pending"
    else:
        added = 0
        for name, text in sorted(files.items(), key=lambda item: _order(item[0])):
            if not is_stream(name) or name == store.PLAN_LOG:
                continue
            mine = keys_of(name, read_lines(root / name))
            new: list[str] = []
            for line in text.split(NL):
                key = line_key(name, line) if line.strip() else None
                if key is not None and key not in mine:
                    mine.add(key)
                    new.append(line)
            if not new:
                continue
            added += len(new)
            action = "append" if name.endswith(".jsonl") else "append_text"
            changes.append(gate.Change(root / name, action, "\n".join(new) + "\n"))
            lines.append(assets.text("sync.import_lines", file=name, count=len(new)))
        if not added:
            raise VocabError("nothing_to_import")
        lines.append(assets.text("sync.import_plan_kept"))
        pending_folder = root / store.PENDING
    # the decision's line joins the account with the log, so it names no local path
    summary = assets.text("sync.import_summary", folder=root.name)
    try:
        return gate.preview(pending_folder, summary, lines, changes, now, root / store.DECISIONS)
    except OSError:
        return gate.preview(
            root / store.PENDING, summary, lines, changes, now, root / store.DECISIONS
        )
