"""The learner's folder: plan, review log, flags, own words and the pointer to it.

    registers/plan.json        languages, levels, weights, limits, retention, days off
    registers/day.json         new words and reviews added to one day
    registers/.pending/        previews waiting for a confirm token
    log/reviews.jsonl          one row per graded answer, never rewritten
    log/decisions.md           one line per approved change of the plan or a course
    log/flags.jsonl            reported mistakes in course entries and words put aside
    log/notes.jsonl            the learner's own notes for words
    courses/<lang>/own.jsonl   the learner's own words

Files are written with LF line endings and UTF-8; the plan is replaced
atomically, the logs only grow.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any

from vocabbot.errors import VocabError

PLAN = "registers/plan.json"
DAY = "registers/day.json"
DAY_SETTINGS = ("extra_new", "extra_reviews")
PENDING = "registers/.pending"
REVIEWS = "log/reviews.jsonl"
DECISIONS = "log/decisions.md"
FLAGS = "log/flags.jsonl"
NOTES = "log/notes.jsonl"
NOTE_MAX = 500
OWN = "courses/{lang}/own.jsonl"
CONFIG = "config.json"

LEVELS = ("a1", "a2", "b1", "b2")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DIRECTIONS = {"produce": "p", "recognize": "r"}
BASE_LANGUAGES = ("pl",)

DEFAULT_PLAN: dict[str, Any] = {
    "schema": 1,
    "base": "pl",
    "languages": [],
    "new_per_day": 15,
    "retention": 0.9,
    "directions": ["produce"],
    "sibling_gap_days": 3,
    "sibling_distance": 5,
    "mix": "interleaved",
    "review_limit": None,
    "days_off": [],
    "day_starts_at": 4,
    "leech_lapses": 4,
    "max_languages": 3,
    "diacritics": "strict",
    "presence": "on",
    # cards in one message of the chat session; 1 asks them one at a time
    "batch": 1,
    # a new word: asked at once as a question, as SuperMemo does, or shown first
    "new_words": "ask",
    # the order of the day's reviews: most overdue first, course order, shortest
    # interval first, or random
    "review_order": "due",
    # a production card: the learner types the word (the engine grades it), or may also
    # show the answer and grade the recall, as SuperMemo's "Check" does
    "answer_mode": "type",
    # the Polish translation of a sentence: shown with it, or on request
    "sentence_translation": "shown",
    # the day a card comes back, with the result of an answer
    "next_review": "shown",
    "parameters": {},
    "parameters_info": {},
}

# key: (type, minimum, maximum) for the numbers of the plan
NUMBERS: dict[str, tuple[type, float, float]] = {
    "new_per_day": (int, 0, 100),
    "retention": (float, 0.7, 0.97),
    "sibling_gap_days": (int, 0, 14),
    "sibling_distance": (int, 0, 20),
    "day_starts_at": (int, 0, 12),
    "leech_lapses": (int, 2, 20),
    "max_languages": (int, 1, 6),
    "batch": (int, 1, 20),
}
CHOICES: dict[str, tuple[str, ...]] = {
    "mix": ("interleaved", "blocks"),
    "diacritics": ("strict", "lenient"),
    "presence": ("on", "off"),
    "new_words": ("ask", "show"),
    "review_order": ("due", "course", "interval", "random"),
    "answer_mode": ("type", "self"),
    "sentence_translation": ("shown", "hidden"),
    "next_review": ("shown", "hidden"),
}
PARAMETER_COUNT = 21


def parameter_problems(parameters: Any) -> list[str]:
    """FSRS-6 parameters of the plan: {language: 21 numbers within the bounds of py-fsrs}."""
    from vocabbot.optimize import LOWER, UPPER

    if parameters is None or parameters == {}:
        return []
    if not isinstance(parameters, dict):
        return ["parameters must map a language to its FSRS-6 parameters"]
    problems = []
    for code, values in parameters.items():
        if (
            not isinstance(values, list)
            or len(values) != PARAMETER_COUNT
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values)
        ):
            problems.append(f"parameters.{code} must be {PARAMETER_COUNT} numbers")
        elif any(not lo <= v <= hi for v, lo, hi in zip(values, LOWER, UPPER, strict=True)):
            problems.append(f"parameters.{code} lie outside the bounds of FSRS-6")
    return problems


def config_dir() -> Path:
    override = os.environ.get("VOCABBOT_CONFIG")
    return Path(override) if override else Path.home() / ".vocabbot"


def locate(learner: str | None = None) -> Path:
    """The learner's folder: --learner, VOCABBOT_HOME, the current folder, the saved pointer.

    The current folder counts when it holds a plan, so a chat that runs in the
    learner's folder (Cowork, a project folder) needs no pointer.
    """
    if learner:
        root = Path(learner).expanduser()
    elif os.environ.get("VOCABBOT_HOME"):
        root = Path(os.environ["VOCABBOT_HOME"]).expanduser()
    elif (Path.cwd() / PLAN).is_file():
        root = Path.cwd()
    else:
        pointer = config_dir() / CONFIG
        try:
            saved = json.loads(pointer.read_text(encoding="utf-8")).get("learner")
        except (OSError, ValueError, AttributeError):
            saved = None
        if not saved:
            raise VocabError("no_learner")
        root = Path(saved)
    if not (root / PLAN).is_file():
        raise VocabError("no_plan", folder=str(root))
    return root.resolve()


def learning_day(now: datetime, day_starts_at: int, tz: tzinfo | None = None) -> date:
    """The learning day of a moment: it starts at `day_starts_at` local time.

    Local time is the computer's, or the time zone `tz` (a server's learners).
    """
    local = now.astimezone(tz)
    if local.hour < day_starts_at:
        return (local - timedelta(days=1)).date()
    return local.date()


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")


# ---------------------------------------------------------------- files


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    """Rows of a JSON-lines file and the numbers of lines that are damaged."""
    rows: list[dict[str, Any]] = []
    damaged: list[int] = []
    if not path.is_file():
        return rows, damaged
    for number, raw in enumerate(path.read_bytes().split(b"\n"), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            damaged.append(number)
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            damaged.append(number)
    return rows, damaged


def dump_line(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(", ", ": "))


def append_jsonl(path: Path, row: dict[str, Any]) -> int:
    """Append one row; a last line cut short by a crash stays on its own line.

    Returns the number of bytes written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = b""
    if path.is_file() and path.stat().st_size:
        with path.open("rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                prefix = b"\n"
    data = prefix + (dump_line(row) + "\n").encode("utf-8")
    with path.open("ab") as fh:
        fh.write(data)
        fh.flush()
        if os.environ.get("VOCABBOT_FSYNC", "1") != "0":  # the tests turn it off for speed
            os.fsync(fh.fileno())
    return len(data)


def write_text(path: Path, text: str) -> None:
    """Replace a file atomically, UTF-8 with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    os.replace(temporary, path)


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def conflict_copies(root: Path) -> list[Path]:
    """Copies a sync service left next to a file it could not merge."""
    found: list[Path] = []
    checks = [(root / "registers", "plan", ".json"), (root / "log", "reviews", ".jsonl")]
    checks.append((root / "log", "flags", ".jsonl"))
    checks.append((root / "log", "notes", ".jsonl"))
    courses = root / "courses"
    if courses.is_dir():
        checks += [
            (folder, "own", ".jsonl") for folder in sorted(courses.iterdir()) if folder.is_dir()
        ]
    for folder, stem, suffix in checks:
        if not folder.is_dir():
            continue
        for item in sorted(folder.iterdir()):
            name = item.name
            if (
                item.is_file()
                and name.startswith(stem)
                and name.endswith(suffix)
                and name != stem + suffix
            ):
                found.append(item)
    return found


# ---------------------------------------------------------------- plan


def parse_levels(text: str) -> list[str]:
    """'a1-b1' -> [a1, a2, b1]; 'a1,b1' -> [a1, b1]; 'a2' -> [a2]."""
    text = text.strip().lower()
    if "-" in text:
        first, _, last = text.partition("-")
        if first not in LEVELS or last not in LEVELS or LEVELS.index(first) > LEVELS.index(last):
            raise VocabError("bad_levels", value=text)
        return list(LEVELS[LEVELS.index(first) : LEVELS.index(last) + 1])
    levels = [part.strip() for part in text.split(",") if part.strip()]
    if not levels or any(level not in LEVELS for level in levels):
        raise VocabError("bad_levels", value=text)
    return sorted(set(levels), key=LEVELS.index)


def parse_language(text: str) -> dict[str, Any]:
    """'de:a1-a2:2' -> {code: de, levels: [a1, a2], weight: 2}."""
    parts = text.strip().split(":")
    if len(parts) not in (2, 3) or not parts[0]:
        raise VocabError("bad_language_spec", value=text)
    weight = 1
    if len(parts) == 3:
        try:
            weight = int(parts[2])
        except ValueError:
            raise VocabError("bad_language_spec", value=text) from None
    return {"code": parts[0].lower(), "levels": parse_levels(parts[1]), "weight": weight}


def plan_problems(plan: dict[str, Any], installed: dict[str, list[str]]) -> list[str]:
    """What is wrong with a plan; `installed` maps a course language to its levels."""
    problems: list[str] = []
    if plan.get("schema") != 1:
        problems.append("schema must be 1")
    if plan.get("base") not in BASE_LANGUAGES:
        problems.append(f"base must be one of {', '.join(BASE_LANGUAGES)}")
    for key, (kind, low, high) in NUMBERS.items():
        value = plan.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"{key} must be a number")
        elif kind is int and not isinstance(value, int):
            problems.append(f"{key} must be a whole number")
        elif not low <= value <= high:
            problems.append(f"{key} must lie between {low:g} and {high:g}")
    for key, options in CHOICES.items():
        if plan.get(key) not in options:
            problems.append(f"{key} must be one of {', '.join(options)}")
    problems += parameter_problems(plan.get("parameters"))
    limit = plan.get("review_limit")
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or not 10 <= limit <= 1000
    ):
        problems.append("review_limit must be empty or a whole number from 10 to 1000")
    directions = plan.get("directions")
    if (
        not isinstance(directions, list)
        or not directions
        or any(d not in DIRECTIONS for d in directions)
    ):
        problems.append("directions must list produce, recognize or both")
    days_off = plan.get("days_off")
    if (
        not isinstance(days_off, list)
        or any(d not in WEEKDAYS for d in days_off)
        or len(set(days_off)) > 6
    ):
        problems.append("days_off must list at most six of " + ", ".join(WEEKDAYS))
    languages = plan.get("languages")
    if not isinstance(languages, list) or not languages:
        problems.append("the plan needs at least one language")
        return problems
    max_languages = plan.get("max_languages", 3)
    if isinstance(max_languages, int) and len(languages) > max_languages:
        problems.append(
            f"the plan has {len(languages)} languages and max_languages is {max_languages}"
        )
    seen: set[str] = set()
    for item in languages:
        code = item.get("code") if isinstance(item, dict) else None
        if not isinstance(code, str):
            problems.append("every language needs a code")
            continue
        if code in seen:
            problems.append(f"{code} appears twice")
        seen.add(code)
        if code == plan.get("base"):
            problems.append(f"{code} is the base language")
        if code not in installed:
            problems.append(
                f"no course for {code} (installed: {', '.join(sorted(installed)) or 'none'})"
            )
            continue
        levels = item.get("levels")
        if (
            not isinstance(levels, list)
            or not levels
            or any(level not in LEVELS for level in levels)
        ):
            problems.append(f"{code}: levels must be a list of {', '.join(LEVELS)}")
        else:
            missing = [level for level in levels if level not in installed[code]]
            if missing:
                problems.append(
                    f"{code}: level {', '.join(missing)} is not installed "
                    f"(installed: {', '.join(installed[code])})"
                )
        weight = item.get("weight", 1)
        if isinstance(weight, bool) or not isinstance(weight, int) or not 1 <= weight <= 5:
            problems.append(f"{code}: weight must be a whole number from 1 to 5")
        if not isinstance(item.get("paused", False), bool):
            problems.append(f"{code}: paused must be true or false")
    return problems


def complete_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """The plan with defaults for keys it does not set."""
    out = dict(DEFAULT_PLAN)
    out.update(plan)
    out["languages"] = [
        {
            "code": item["code"],
            "levels": item["levels"],
            "weight": item.get("weight", 1),
            "paused": item.get("paused", False),
        }
        for item in plan.get("languages", [])
        if isinstance(item, dict) and "code" in item and "levels" in item
    ]
    return out


# ---------------------------------------------------------------- the folder


def _stat_key(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return (st.st_size, st.st_mtime_ns)


@dataclass
class Learner:
    """One learner's folder.

    The review log is read once per process and kept in memory; rows this
    process appends are added to that copy, and any other change of the file
    (size or time) makes the next read start again from the file.
    """

    root: Path
    _plan: dict[str, Any] | None = field(default=None, repr=False)
    _rows: list[dict[str, Any]] | None = field(default=None, repr=False)
    _damaged: list[int] = field(default_factory=list, repr=False)
    _rows_key: tuple[int, int] | None = field(default=None, repr=False)
    cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def path(self, relative: str) -> Path:
        return self.root / relative

    def plan(self) -> dict[str, Any]:
        if self._plan is None:
            try:
                raw = json.loads(self.path(PLAN).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise VocabError("plan_unreadable", detail=str(exc)) from None
            if not isinstance(raw, dict):
                raise VocabError("plan_unreadable", detail="not an object")
            self._plan = complete_plan(raw)
        return self._plan

    def rows(self) -> tuple[list[dict[str, Any]], list[int]]:
        """Rows of the review log (do not change the list) and its damaged line numbers."""
        path = self.path(REVIEWS)
        key = _stat_key(path)
        if self._rows is None or key != self._rows_key:
            self._rows, self._damaged = read_jsonl(path)
            self._rows_key = key
        return self._rows, self._damaged

    def append_review(self, row: dict[str, Any]) -> None:
        path = self.path(REVIEWS)
        current = self._rows is not None and _stat_key(path) == self._rows_key
        size = self._rows_key[0] if self._rows_key else 0
        written = append_jsonl(path, row)
        after = _stat_key(path)
        if (
            current
            and self._rows is not None
            and not self._damaged
            and after is not None
            and after[0] == size + written
        ):
            self._rows.append(row)
            self._rows_key = after
        else:
            self._rows = None

    def flags(self) -> list[dict[str, Any]]:
        return read_jsonl(self.path(FLAGS))[0]

    def flag_states(self) -> dict[str, str]:
        """Entries out of the queue: "report" (a mistake reported) or "skip" (put aside).

        The last row of an entry holds; a row with `clear` brings the entry back.
        """
        state: dict[str, str] = {}
        for row in self.flags():
            entry = row.get("entry")
            if not isinstance(entry, str):
                continue
            if row.get("clear", False):
                state.pop(entry, None)
            else:
                state[entry] = "skip" if row.get("skip") else "report"
        return state

    def suspended(self) -> set[str]:
        """Entries the learner reported as wrong or put aside, and has not brought back."""
        return set(self.flag_states())

    def skipped(self) -> set[str]:
        """Entries the learner put aside without reporting a mistake."""
        return {entry for entry, kind in self.flag_states().items() if kind == "skip"}

    def notes(self) -> dict[str, str]:
        """The learner's notes by entry: the last row of an entry holds, `clear` removes it."""
        notes: dict[str, str] = {}
        for row in read_jsonl(self.path(NOTES))[0]:
            entry = row.get("entry")
            if not isinstance(entry, str):
                continue
            text = row.get("note")
            if row.get("clear") or not isinstance(text, str) or not text.strip():
                notes.pop(entry, None)
            else:
                notes[entry] = text
        return notes

    def _day_setting(self, day: date, key: str) -> int:
        try:
            data = json.loads(self.path(DAY).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        if not isinstance(data, dict) or data.get("day") != day.isoformat():
            return 0
        value = data.get(key, 0)
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0

    def _set_day_setting(self, day: date, key: str, value: int) -> None:
        settings = {name: self._day_setting(day, name) for name in DAY_SETTINGS}
        settings[key] = value
        kept = {name: number for name, number in settings.items() if number > 0}
        write_text(self.path(DAY), dump_json({"day": day.isoformat(), **kept}))

    def extra_new(self, day: date) -> int:
        """New words the learner added to the day, on top of the plan's number."""
        return self._day_setting(day, "extra_new")

    def set_extra_new(self, day: date, extra: int) -> None:
        self._set_day_setting(day, "extra_new", extra)

    def extra_reviews(self, day: date) -> int:
        """Reviews the learner added to the day: due ones over the limit, then later ones."""
        return self._day_setting(day, "extra_reviews")

    def set_extra_reviews(self, day: date, extra: int) -> None:
        self._set_day_setting(day, "extra_reviews", extra)

    def own_path(self, lang: str) -> Path:
        return self.path(OWN.format(lang=lang))
