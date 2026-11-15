"""Session tests: conversations with the plugin, checked by the state of the learner's folder.

Each file in sessions/<name>.json describes a synthetic learner (or none, for
a setup), the turns a learner says, and checks after every turn: rows added
to the log and their grades, the plan and own words changed or unchanged,
lines added to the decisions, text in the reply, and above all no answer of a
card that waits in today's session or in a placement test. The learner's
history is made with the engine itself, from today backwards, so the files
never age.

The host is `claude -p --plugin-dir plugin`, continued with `--resume`, in the
learner's folder; every run costs model time. `--check` costs nothing: it
validates the files, seeds every learner, works out the values each check
needs and prints the first turn. `--lint` only validates the files.

    python scripts/session_test.py --check
    python scripts/session_test.py --session "session-*" --model sonnet --max-cost-usd 5
    python scripts/session_test.py --list

Reports go to build/sessions/<time>/ (outside git).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SESSIONS = REPO / "sessions"
RESULTS = REPO / "build" / "sessions"
sys.path.insert(0, str(REPO / "src"))
sys.dont_write_bytecode = True

from vocabbot import answers, quiz, session, store  # noqa: E402
from vocabbot.courses import Catalog, question  # noqa: E402
from vocabbot.progress import status  # noqa: E402
from vocabbot.queue import compute  # noqa: E402

GROUPS = ("setup", "answer-gate", "grades", "write-gate", "numbers")
SKILLS = ("vocab-start", "vocab-session", "vocab-coach", "vocab-words")
CHECKS = {
    "reply_matches",
    "reply_not_matches",
    "no_answer_leak",
    "no_quiz_leak",
    "log_rows_added",
    "rows_where",
    "graded_by_engine",
    "plan_unchanged",
    "plan_matches",
    "own_rows_added",
    "decisions_added",
    "files_exist",
    "files_absent",
}
LEARNER_KEYS = {"languages", "new_per_day", "history_days", "wrong_every", "settings", "prepare"}
MIN_LEAK_LENGTH = 4  # shorter words appear inside ordinary text too often to count as a leak


class SessionError(Exception):
    """A session file that cannot run as written."""


# ---------------------------------------------------------------- files


def lint(data: dict[str, Any], name: str) -> list[str]:
    problems = []
    if data.get("group") not in GROUPS:
        problems.append(f"group must be one of {GROUPS}")
    if data.get("skill") not in SKILLS:
        problems.append(f"skill must be one of {SKILLS}")
    learner = data.get("learner")
    if learner is not None:
        if not isinstance(learner, dict) or not learner.get("languages"):
            problems.append("learner needs languages")
        else:
            unknown = set(learner) - LEARNER_KEYS
            if unknown:
                problems.append(f"learner: unknown keys {sorted(unknown)}")
    turns = data.get("turns")
    if not isinstance(turns, list) or not turns:
        problems.append("no turns")
        turns = []
    for number, turn in enumerate(turns, 1):
        if not str(turn.get("say", "")).strip():
            problems.append(f"turn {number} says nothing")
        expect = turn.get("expect") or {}
        if not expect:
            problems.append(f"turn {number} checks nothing")
        unknown = set(expect) - CHECKS
        if unknown:
            problems.append(f"turn {number}: unknown checks {sorted(unknown)}")
        for pattern in [*expect.get("reply_matches", []), *expect.get("reply_not_matches", [])]:
            try:
                re.compile(pattern)
            except re.error as exc:
                problems.append(f"turn {number}: bad pattern {pattern!r}: {exc}")
    return [f"{name}: {p}" for p in problems]


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = lint(data, path.name)
    if problems:
        raise SessionError("; ".join(problems))
    data.setdefault("name", path.stem)
    return data


# ---------------------------------------------------------------- the learner


def learning_day() -> date:
    return store.learning_day(datetime.now(timezone.utc), 4)


def moment(day: date, second: int) -> datetime:
    return datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc) + timedelta(
        seconds=second
    )


def seed(spec: dict[str, Any], folder: Path, today: date) -> store.Learner:
    """A plan and a history of answers made by the engine, ending the day before today."""
    plan = store.complete_plan(
        {
            "languages": [store.parse_language(s) for s in spec["languages"]],
            "new_per_day": spec.get("new_per_day", 6),
            **(spec.get("settings") or {}),
        }
    )
    store.write_text(folder / store.PLAN, store.dump_json(plan))
    store.write_text(folder / store.REVIEWS, "")
    store.write_text(folder / store.DECISIONS, "# decisions\n\n")
    learner = store.Learner(folder)
    catalog = Catalog(learner=folder)
    wrong_every = int(spec.get("wrong_every", 4))
    count = 0
    for back in range(int(spec.get("history_days", 0)), 0, -1):
        day = today - timedelta(days=back)
        second = 0
        while True:
            items = compute(learner, catalog, day).sequence
            if not items:
                break
            item = items[0]
            count += 1
            second += 1
            right = item.phase == "drill" or count % wrong_every
            given = str(item.entry["display"]) if right else "xxx"
            session.answer(learner, catalog, day, moment(day, second), item.card, given)
    for step in spec.get("prepare") or []:
        prepare(step, learner, catalog, today)
    return learner


def prepare(step: str, learner: store.Learner, catalog: Catalog, today: date) -> None:
    """Answers given today before the conversation starts."""
    if step != "typo_first_review":
        raise SessionError(f"unknown prepare step {step!r}")
    for item in compute(learner, catalog, today).sequence:
        display = str(item.entry["display"])
        if item.phase != "review":
            continue
        for slip in (display[:-1] + ("q" if display[-1] != "q" else "z"), display.upper()):
            verdict = answers.grade(slip, item.entry, lenient=False)
            if verdict.grade == "almost" and slip != display:
                session.answer(learner, catalog, today, datetime.now(timezone.utc), item.card, slip)
                return
    raise SessionError("no review card takes a slip graded 'almost'; raise history_days")


def values_for(learner: store.Learner | None, today: date) -> dict[str, str]:
    """Placeholders for the turns: <<folder>> and, with a history, facts of today."""
    out: dict[str, str] = {}
    if learner is None:
        return out
    rows, _ = learner.rows()
    catalog = Catalog(learner=learner.root)
    if rows and rows[-1].get("day") == today.isoformat():
        entry = catalog.card(str(rows[-1]["card"]))
        if entry is not None:
            out["today_word"] = str(entry["display"])
            out["today_meaning"] = str(entry["gloss"]["pl"])
    report = status(learner, catalog, today)
    out["streak_days"] = str(report["streak_days"])
    return out


def fill(text: str, values: dict[str, str], pattern: bool = False) -> str:
    """Placeholders <<name>> replaced; in a pattern the value is escaped."""

    def sub(match: re.Match[str]) -> str:
        if match.group(1) not in values:
            raise SessionError(f"unknown placeholder <<{match.group(1)}>>")
        value = values[match.group(1)]
        return re.escape(value) if pattern else value

    return re.sub(r"<<([a-z_]+)>>", sub, text)


def fill_expect(expect: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    out = dict(expect)
    for key in ("reply_matches", "reply_not_matches"):
        if key in out:
            out[key] = [fill(p, values, pattern=True) for p in out[key]]
    return out


# ---------------------------------------------------------------- checks


@dataclass
class Snapshot:
    rows: list[dict[str, Any]] = field(default_factory=list)
    plan: bytes = b""
    own: dict[str, int] = field(default_factory=dict)
    decisions: int = 0
    waiting: dict[str, list[str]] = field(default_factory=dict)
    # sentences the engine itself puts into the questions of the waiting cards
    sentences: set[str] = field(default_factory=set)


def answers_of(entry: dict[str, Any]) -> list[str]:
    forms = [*answers.accepted_forms(entry), str(entry.get("lemma") or "")]
    return [f for f in dict.fromkeys(forms) if len(f) >= MIN_LEAK_LENGTH]


def snapshot(folder: Path, today: date) -> Snapshot:
    snap = Snapshot()
    if not (folder / store.PLAN).is_file():
        return snap
    learner = store.Learner(folder)
    snap.rows, _ = store.read_jsonl(folder / store.REVIEWS)
    snap.plan = (folder / store.PLAN).read_bytes()
    for own in (folder / "courses").glob("*/own.jsonl"):
        snap.own[own.parent.name] = len(store.read_jsonl(own)[0])
    decisions = folder / store.DECISIONS
    if decisions.is_file():
        snap.decisions = sum(
            1 for line in decisions.read_text(encoding="utf-8").splitlines() if line[:2] == "- "
        )
    catalog = Catalog(learner=folder)
    for item in compute(learner, catalog, today).sequence:
        if item.phase != "new":
            snap.waiting[item.card] = answers_of(item.entry)
            snap.sentences |= sentences_of(question(item.entry, item.direction))
    return snap


def sentences_of(asked: dict[str, Any]) -> set[str]:
    return {str(asked[key]) for key in ("sentence", "sentence_pl") if asked.get(key)}


def leaks(
    reply: str, candidates: dict[str, list[str]], sentences: set[str] | None = None
) -> list[str]:
    """Answers the reply shows, outside the sentences the engine gave for the questions.

    A sentence of one question may hold the answer of another; the model that
    copies the engine's sentence shows nothing the engine did not give it.
    """
    text = re.sub(r"_{2,}", "___", reply)
    for sentence in sorted(sentences or (), key=len, reverse=True):
        text = text.replace(sentence, " ")
    found = []
    for card, words in candidates.items():
        for word in words:
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.IGNORECASE):
                found.append(f"{card}: {word}")
                break
    return found


def quiz_candidates(lang: str) -> tuple[dict[str, list[str]], set[str]]:
    """Answers of every placement question the engine may ask, and the sentences it gives."""
    catalog = Catalog()
    out: dict[str, list[str]] = {}
    sentences: set[str] = set()
    for count in (4, 5, 6, 8, 10):
        for item in quiz.questions(catalog, lang, list(store.LEVELS), count)["items"]:
            entry = catalog.card(item["card"])
            if entry is not None:
                out[item["card"]] = answers_of(entry)
            sentences |= sentences_of(item["question"])
    return out, sentences


def within(value: int, spec: Any) -> bool:
    if isinstance(spec, int):
        return value == spec
    return int(spec.get("min", 0)) <= value <= int(spec.get("max", 10**6))


def check_turn(
    expect: dict[str, Any], reply: str, before: Snapshot, after: Snapshot, folder: Path
) -> list[str]:
    fails = []
    for pattern in expect.get("reply_matches", []):
        if not re.search(pattern, reply, re.IGNORECASE | re.DOTALL):
            fails.append(f"reply lacks /{pattern}/")
    for pattern in expect.get("reply_not_matches", []):
        found = re.search(pattern, reply, re.IGNORECASE | re.DOTALL)
        if found:
            fails.append(f"reply holds /{pattern}/: {found.group(0)[:60]!r}")
    added = after.rows[len(before.rows) :]
    answered = {str(row.get("card")) for row in added}
    if expect.get("no_answer_leak"):
        still = {c: w for c, w in before.waiting.items() if c not in answered}
        fails += [
            f"answer shown before its grade: {leak}"
            for leak in leaks(reply, still, before.sentences)
        ]
    if expect.get("no_quiz_leak"):
        candidates, given = quiz_candidates(str(expect["no_quiz_leak"]))
        fails += [f"placement answer shown: {leak}" for leak in leaks(reply, candidates, given)]
    if "log_rows_added" in expect and not within(len(added), expect["log_rows_added"]):
        fails.append(f"log rows added: {len(added)}, expected {expect['log_rows_added']}")
    for spec in expect.get("rows_where", []):
        hits = [r for r in added if all(r.get(k) == v for k, v in spec["where"].items())]
        if not within(len(hits), spec["count"]):
            fails.append(f"rows with {spec['where']}: {len(hits)}, expected {spec['count']}")
    if expect.get("graded_by_engine"):
        for row in added:
            card = str(row.get("card", ""))
            if row.get("kind") == "regrade" or row.get("grade") == "known":
                continue
            if card.endswith("#p") and row.get("auto") != row.get("grade"):
                fails.append(f"{card}: grade {row.get('grade')} is not the engine's")
    if expect.get("plan_unchanged") and before.plan != after.plan:
        fails.append("the plan changed")
    for key, want in (expect.get("plan_matches") or {}).items():
        plan = json.loads(after.plan or b"{}")
        have = (
            [item["code"] for item in plan.get("languages", [])]
            if key == "languages"
            else plan.get(key)
        )
        if have != want:
            fails.append(f"plan {key}: {have!r}, expected {want!r}")
    if "own_rows_added" in expect:
        grown = sum(after.own.values()) - sum(before.own.values())
        if not within(grown, expect["own_rows_added"]):
            fails.append(f"own rows added: {grown}, expected {expect['own_rows_added']}")
    if "decisions_added" in expect:
        grown = after.decisions - before.decisions
        if not within(grown, expect["decisions_added"]):
            fails.append(f"decisions added: {grown}, expected {expect['decisions_added']}")
    for relative in expect.get("files_exist", []):
        if not (folder / relative).exists():
            fails.append(f"{relative} is missing")
    for relative in expect.get("files_absent", []):
        if (folder / relative).exists():
            fails.append(f"{relative} exists")
    return fails


# ---------------------------------------------------------------- hosts


class ClaudeHost:
    """claude -p with the plugin of this repository; turns continue with --resume."""

    name = "claude"
    tools = ("Bash", "Read", "Glob", "Grep", "Skill")

    def __init__(self, model: str) -> None:
        exe = shutil.which("claude")
        if exe is None:
            raise SessionError("claude is not on PATH")
        self.exe = exe
        self.model = model

    def send(self, text: str, cwd: Path, env: dict[str, str], resume: str | None) -> Reply:
        cmd = [self.exe, "-p", text, "--plugin-dir", str(PLUGIN), "--model", self.model]
        cmd += ["--allowedTools", *self.tools, "--output-format", "json"]
        if resume:
            cmd += ["--resume", resume]
        done = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, **env},
            timeout=1200,
        )
        try:
            out = json.loads(done.stdout)
        except ValueError:
            raise SessionError(f"claude gave no JSON: {done.stderr.strip()[:300]}") from None
        return Reply(
            str(out.get("result") or ""),
            out.get("session_id"),
            float(out.get("total_cost_usd") or 0.0),
        )


@dataclass
class Reply:
    text: str
    session_id: str | None
    cost_usd: float


class ScriptedHost:
    """For the runner's own tests: replies made by functions of the folder."""

    name = "scripted"

    def __init__(self, replies: list[Callable[[Path], str]]) -> None:
        self.replies = list(replies)

    def send(self, text: str, cwd: Path, env: dict[str, str], resume: str | None) -> Reply:
        return Reply(self.replies.pop(0)(cwd), "scripted", 0.0)


# ---------------------------------------------------------------- running


def run_session(data: dict[str, Any], host: Any, keep: Path | None = None) -> dict[str, Any]:
    today = learning_day()
    base = Path(tempfile.mkdtemp(prefix="vocabbot-session-"))
    folder = base / "learner"
    folder.mkdir()
    # no person answers the host's permission prompt in a test run; the engine still needs a token
    env = {
        "VOCABBOT_CONFIG": str(base / "config"),
        "PYTHONIOENCODING": "utf-8",
        "VOCABBOT_HOOK": "off",
    }
    result: dict[str, Any] = {"name": data["name"], "group": data["group"], "turns": []}
    cost = 0.0
    previous = os.environ.get("VOCABBOT_CONFIG")
    os.environ["VOCABBOT_CONFIG"] = env["VOCABBOT_CONFIG"]
    try:
        learner = seed(data["learner"], folder, today) if data.get("learner") else None
        values = {"folder": str(folder), **values_for(learner, today)}
        resume = None
        for number, turn in enumerate(data["turns"], 1):
            before = snapshot(folder, today)
            said = fill(turn["say"], values)
            started = time.time()
            reply = host.send(said, folder, env, resume)
            resume, cost = reply.session_id, cost + reply.cost_usd
            after = snapshot(folder, today)
            expect = fill_expect(turn["expect"], values)
            fails = check_turn(expect, reply.text, before, after, folder)
            result["turns"].append(
                {
                    "turn": number,
                    "say": said,
                    "reply": reply.text,
                    "fails": fails,
                    "seconds": round(time.time() - started, 1),
                }
            )
        result["passed"] = all(not t["fails"] for t in result["turns"])
    except SessionError as exc:
        result.update(passed=False, error=str(exc))
    finally:
        if previous is None:
            os.environ.pop("VOCABBOT_CONFIG", None)
        else:
            os.environ["VOCABBOT_CONFIG"] = previous
        if keep is not None:
            shutil.copytree(base, keep / data["name"], dirs_exist_ok=True)
        shutil.rmtree(base, ignore_errors=True)
    result["cost_usd"] = round(cost, 4)
    return result


def check_only(sessions: list[dict[str, Any]]) -> int:
    """No model: every learner seeds, every placeholder resolves, every leak list is ready."""
    bad = 0
    today = learning_day()
    for data in sessions:
        base = Path(tempfile.mkdtemp(prefix="vocabbot-session-check-"))
        previous = os.environ.get("VOCABBOT_CONFIG")
        os.environ["VOCABBOT_CONFIG"] = str(base / "config")
        try:
            folder = base / "learner"
            folder.mkdir()
            learner = seed(data["learner"], folder, today) if data.get("learner") else None
            values = {"folder": str(folder), **values_for(learner, today)}
            first = fill(data["turns"][0]["say"], values)
            for turn in data["turns"]:
                fill(turn["say"], values)
                fill_expect(turn["expect"], values)
                if turn["expect"].get("no_quiz_leak"):
                    quiz_candidates(str(turn["expect"]["no_quiz_leak"]))
            waiting = len(snapshot(folder, today).waiting)
            print(
                f"ok    {data['group']:<12} {data['name']:<32} {len(data['turns'])} turns, "
                f"{waiting} cards waiting; first: {first[:70]}"
            )
        except (SessionError, KeyError, ValueError) as exc:
            bad += 1
            print(f"FAIL  {data.get('name')}: {exc}")
        finally:
            if previous is None:
                os.environ.pop("VOCABBOT_CONFIG", None)
            else:
                os.environ["VOCABBOT_CONFIG"] = previous
            shutil.rmtree(base, ignore_errors=True)
    print(f"{len(sessions) - bad} of {len(sessions)} sessions ready")
    return 1 if bad else 0


def write_report(results: list[dict[str, Any]], host: str, model: str) -> Path:
    out = RESULTS / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    report = {"host": host, "model": model, "results": results}
    (out / "results.json").write_bytes(json.dumps(report, ensure_ascii=False, indent=1).encode())
    lines = [f"# Session tests, {host}, {model}", ""]
    for result in results:
        mark = "PASS" if result["passed"] else "FAIL"
        lines.append(f"## {mark} {result['name']} (USD {result['cost_usd']:.2f})")
        if result.get("error"):
            lines.append(f"- error: {result['error']}")
        for turn in result["turns"]:
            lines += [f"- turn {turn['turn']}: {fail}" for fail in turn["fails"]]
        lines.append("")
    (out / "report.md").write_bytes("\n".join(lines).encode("utf-8"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--session", default="*", help="a name pattern, e.g. session-*")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--check", action="store_true", help="seed and prepare; no model")
    parser.add_argument("--lint", action="store_true", help="validate the files only")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the folders in the report")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = sorted(p for p in SESSIONS.glob("*.json") if fnmatch.fnmatch(p.stem, args.session))
    if args.lint:
        problems = []
        for path in paths:
            try:
                problems += lint(json.loads(path.read_text(encoding="utf-8")), path.name)
            except ValueError as exc:
                problems.append(f"{path.name}: {exc}")
        print("\n".join(problems) or f"{len(paths)} session files")
        return 1 if problems or not paths else 0
    sessions = [load(p) for p in paths]
    if args.list:
        for data in sessions:
            print(f"{data['group']:<12} {data['name']:<32} {data.get('about', '')}")
        return 0
    if args.check:
        return check_only(sessions)
    host = ClaudeHost(args.model)
    results: list[dict[str, Any]] = []
    spent = 0.0
    keep = RESULTS / "folders" / datetime.now().strftime("%Y%m%d-%H%M%S") if args.keep else None
    for run in range(args.runs):
        for data in sessions:
            if spent >= args.max_cost_usd:
                print(f"stopped: USD {spent:.2f} reached the ceiling of {args.max_cost_usd}")
                break
            result = run_session(data, host, keep)
            result["run"] = run + 1
            spent += result["cost_usd"]
            results.append(result)
            mark = "PASS" if result["passed"] else "FAIL"
            print(f"{mark}  {data['name']} (run {run + 1}, USD {result['cost_usd']:.2f})")
    out = write_report(results, host.name, args.model)
    passed = sum(1 for r in results if r["passed"])
    print(f"{passed} of {len(results)} passed; USD {spent:.2f}; report {out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
