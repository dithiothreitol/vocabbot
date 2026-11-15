"""The vocabbot program: plain output for a person, --json for the skills.

Text written by the learner (answers, own words, notes) comes on standard
input, never on the command line.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from vocabbot import (
    __version__,
    assets,
    courses,
    doctor,
    gate,
    plans,
    progress,
    quiz,
    session,
    store,
    words,
)
from vocabbot.courses import Catalog, split_card
from vocabbot.errors import VocabError
from vocabbot.queue import compute

Renderer = Callable[[dict[str, Any]], list[str]]


@dataclass
class Context:
    args: argparse.Namespace
    now: datetime
    _learner: store.Learner | None = None
    _catalog: Catalog | None = None

    def learner(self) -> store.Learner:
        if self._learner is None:
            self._learner = store.Learner(store.locate(self.args.learner))
        return self._learner

    def catalog(self) -> Catalog:
        if self._catalog is None:
            try:
                root: Path | None = self.learner().root
            except VocabError:
                root = None
            self._catalog = Catalog(learner=root)
        return self._catalog

    def day(self) -> date:
        if self.args.today:
            try:
                return date.fromisoformat(self.args.today)
            except ValueError:
                raise VocabError("bad_day", value=self.args.today) from None
        return store.learning_day(self.now, int(self.learner().plan()["day_starts_at"]))

    def interactive(self) -> bool:
        return not self.args.json and sys.stdin.isatty() and sys.stdout.isatty()

    def pending_folders(self) -> list[Path]:
        """Where previews wait: the learner's folder, ~/.vocabbot, and a new folder's own."""
        folders = []
        with contextlib.suppress(VocabError):
            folders.append(self.learner().path(store.PENDING))
        folders.append(store.config_dir() / "pending")
        if getattr(self.args, "learner", None):
            folders.append(Path(self.args.learner).expanduser() / store.PENDING)
        folders.append(Path.cwd() / store.PENDING)
        return list(dict.fromkeys(folders))


def read_stdin() -> str:
    text = sys.stdin.read()
    if not text.strip():
        raise VocabError("empty_stdin")
    return text


def answer_lines(text: str) -> list[tuple[int, dict[str, Any] | None]]:
    """JSON lines {"card": ..., "answer": ...}; a line that is not one gives None."""
    out: list[tuple[int, dict[str, Any] | None]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item["answer"], str):
                raise TypeError
            out.append((number, {"card": str(item["card"]), "answer": item["answer"]}))
        except (ValueError, KeyError, TypeError):
            out.append((number, None))
    return out


def finish_preview(ctx: Context, preview: dict[str, Any]) -> dict[str, Any]:
    """In a terminal ask the question; otherwise return the preview with its token."""
    if not ctx.interactive():
        return preview
    for line in preview["preview"]:
        print(line)
    reply = input(assets.text("gate.confirm")).strip().lower()
    if reply in ("t", "tak", "y", "yes"):
        result = gate.commit(preview["token"], ctx.pending_folders(), ctx.now, via="terminal")
        return {"applied": result["applied"], "lines": []}
    for folder in ctx.pending_folders():
        (folder / f"{preview['token']}.json").unlink(missing_ok=True)
    return {"cancelled": True}


# ---------------------------------------------------------------- rendering


def _weekday(day: str) -> str:
    return assets.text(f"weekdays.{store.WEEKDAYS[date.fromisoformat(day).weekday()]}")


def _tag(code: str) -> str:
    try:
        return str(assets.language(code)["tag"])
    except KeyError:
        return code.upper()


def describe_question(q: dict[str, Any]) -> str:
    if q["ask"] == "word":
        extras = [assets.text(f"pos.{q['pos']}")] if q.get("pos") else []
        if q.get("with_article"):
            extras.append(assets.text("drill.with_article"))
        text = f"{q['meaning']} ({', '.join(extras)})" if extras else str(q["meaning"])
        if q.get("hint"):
            text += f" [{q['hint']}]"
        if q.get("sentence"):
            text += f" · {q['sentence']}"
        return text
    return f"{q['word']}" + (f" · {q['sentence']}" if q.get("sentence") else "")


def describe_word(w: dict[str, Any]) -> str:
    details = [assets.text(f"pos.{w['pos']}")] if w.get("pos") else []
    if w.get("gender"):
        details.append(assets.text(f"genders.{w['gender']}"))
    for key, value in (w.get("forms") or {}).items():
        details.append(f"{assets.text(f'forms.{key}')} {value}")
    text = f"{w['word']} ({', '.join(details)})" if details else str(w["word"])
    if w.get("ipa"):
        text += f" {w['ipa']}"
    return f"{text} = {w['meaning']}"


def render_summary(data: dict[str, Any]) -> list[str]:
    lines = [assets.text("cli.day", day=data["day"], weekday=_weekday(data["day"]))]
    if data["off"]:
        lines.append(assets.text("cli.day_off"))
    for code, counts in data["languages"].items():
        lines.append(
            assets.text("cli.lang_line", name=assets.language_name(code), code=code, **counts)
        )
    left = data["left"]
    if any(left.values()):
        lines.append(assets.text("cli.left", minutes=data["minutes"], **left))
    else:
        lines.append(assets.text("cli.done"))
    if data.get("extra_new"):
        lines.append(assets.text("cli.extra", count=data["extra_new"]))
    for warning in data["warnings"]:
        if warning["code"] == "conflict_copies":
            lines.append(assets.text("cli.warning_conflict"))
        elif warning["code"] == "damaged_rows":
            lines.append(assets.text("cli.warning_damaged", count=len(warning["lines"])))
        elif warning["code"] == "orphans":
            lines.append(assets.text("cli.warning_orphans", count=warning["count"]))
        elif warning["code"] == "review_limit":
            lines.append(assets.text("cli.warning_limit", count=warning["count"]))
    return lines


def render_next(data: dict[str, Any]) -> list[str]:
    lines = []
    for n, item in enumerate(data["items"], 1):
        meaning = (
            describe_word(item["word"])
            if item["phase"] == "new"
            else describe_question(item["question"])
        )
        lines.append(
            assets.text(
                "cli.item",
                n=n,
                tag=_tag(item["lang"]),
                phase=assets.text(f"phases.{item['phase']}"),
                meaning=meaning,
            )
        )
    if not lines:
        lines.append(assets.text("cli.done"))
    return lines


def render_answer(data: dict[str, Any]) -> list[str]:
    if "results" in data:
        lines: list[str] = []
        for result in data["results"]:
            lines += (
                render_answer(result) if "error" not in result else [result["error"]["message"]]
            )
        return lines
    word = describe_word(data["word"])
    grade = data["grade"]
    if grade in ("know", "known"):
        lines = [assets.text("cli.answer_know", word=word)]
    elif grade == "almost":
        errors = ", ".join(assets.text(f"error_classes.{e}") for e in data.get("errors", []))
        lines = [assets.text("cli.answer_almost", word=word, errors=errors)]
    else:
        lines = [assets.text("cli.answer_dont_know", word=word)]
    if data.get("other_lang"):
        lines.append(assets.text("cli.other_lang", lang=assets.language_name(data["other_lang"])))
    if data["word"].get("example"):
        lines.append(f"  {data['word']['example']}  {data['word'].get('example_pl', '')}".rstrip())
    if data.get("next_due"):
        lines.append(assets.text("cli.next_due", due=data["next_due"]))
    return lines


def render_status(data: dict[str, Any]) -> list[str]:
    lines = render_summary(data["today"])
    for code, info in data["languages"].items():
        retention = (
            f"{round(info['retention_30'] * 100)}%" if info["retention_30"] is not None else "-"
        )
        lines.append(
            assets.text(
                "cli.status_line",
                name=assets.language_name(code),
                code=code,
                cards=info["cards"],
                retention=retention,
                week=info["due_week"],
                lapses=info["lapses"],
            )
        )
        for level, counts in info["levels"].items():
            label = assets.text("cli.own_words") if level == "own" else level.upper()
            lines.append(assets.text("cli.status_level", level=label, **counts))
        for leech in info["leeches"][:5]:
            lines.append(
                assets.text(
                    "cli.status_leech", **{k: leech[k] for k in ("word", "meaning", "lapses")}
                )
            )
    lines.append(assets.text("cli.streak", days=data["streak_days"]))
    return lines


def render_forecast(data: dict[str, Any]) -> list[str]:
    lines = []
    for row in data["days"]:
        if row.get("off"):
            lines.append(assets.text("cli.forecast_off", day=row["day"]))
        else:
            lines.append(
                assets.text(
                    "cli.forecast_line", **{k: row[k] for k in ("day", "reviews", "new", "minutes")}
                )
            )
    lines.append(
        assets.text(
            "cli.forecast_avg",
            reviews=data["average_reviews"],
            minutes=data["average_minutes"],
            peak=data["peak_reviews"],
        )
    )
    for code, levels in data["levels_complete"].items():
        for level, day in levels.items():
            lines.append(
                assets.text(
                    "cli.forecast_complete",
                    name=assets.language_name(code),
                    level=level.upper(),
                    day=day,
                )
            )
    return lines


def render_preview(data: dict[str, Any]) -> list[str]:
    if data.get("cancelled"):
        return [assets.text("gate.cancelled")]
    if "applied" in data:
        return [*data.get("lines", []), assets.text("gate.applied", summary=data["applied"])]
    expires = data["expires"][11:16] + " UTC"
    return [*data["preview"], assets.text("gate.token", token=data["token"], expires=expires)]


def render_lines(data: dict[str, Any]) -> list[str]:
    return [str(line) for line in data.get("lines", [])]


def render_courses(data: dict[str, Any]) -> list[str]:
    lines = []
    for code, info in data["languages"].items():
        levels = ", ".join(f"{level.upper()} {count}" for level, count in info["levels"].items())
        lines.append(assets.text("cli.course_line", name=info["name"], code=code, levels=levels))
    return lines


def render_check(data: dict[str, Any]) -> list[str]:
    if data["ok"]:
        return [assets.text("cli.check_ok"), *data["warnings"]]
    return [
        assets.text("cli.check_errors", count=len(data["errors"])),
        *data["errors"],
        *data["warnings"],
    ]


def render_doctor(data: dict[str, Any]) -> list[str]:
    if "token" in data or "applied" in data:
        return render_preview(data)
    if data["ok"]:
        return [assets.text("doctor.ok")]
    lines = [assets.text("doctor.problems", count=len(data["problems"]))]
    lines += ["  " + json.dumps(problem, ensure_ascii=False) for problem in data["problems"]]
    return lines


def render_simple(key: str) -> Renderer:
    def render(data: dict[str, Any]) -> list[str]:
        return [assets.text(key, **data)]

    return render


# ---------------------------------------------------------------- commands


def cmd_init(ctx: Context) -> dict[str, Any]:
    if not ctx.args.lang:
        raise VocabError("bad_language_spec", value="")
    folder = Path(ctx.args.folder) if ctx.args.folder else Path.home() / "VocabBot"
    preview = plans.init_preview(
        folder,
        ctx.args.lang,
        ctx.args.new,
        Catalog(),
        ctx.now,
        base=ctx.args.base,
        assignments=ctx.args.set,
    )
    return finish_preview(ctx, preview)


def cmd_use(ctx: Context) -> dict[str, Any]:
    """Point the program at an existing learner's folder, e.g. on a second computer."""
    folder = store.locate(ctx.args.folder)
    store.write_text(store.config_dir() / store.CONFIG, store.dump_json({"learner": str(folder)}))
    return {"learner": str(folder)}


def cmd_today(ctx: Context) -> dict[str, Any]:
    learner, catalog, day = ctx.learner(), ctx.catalog(), ctx.day()
    if ctx.args.extra:
        return session.add_extra(learner, catalog, day, ctx.args.extra)
    return session.summary(learner, catalog, compute(learner, catalog, day))


def cmd_next(ctx: Context) -> dict[str, Any]:
    if ctx.args.count < 1:
        raise VocabError("bad_count")
    return session.next_items(
        ctx.learner(), ctx.catalog(), ctx.day(), count=ctx.args.count, ahead=ctx.args.ahead
    )


def cmd_answer(ctx: Context) -> dict[str, Any]:
    learner, catalog, day = ctx.learner(), ctx.catalog(), ctx.day()
    source = "chat" if ctx.args.json else "cli"
    if not ctx.args.batch:
        if not ctx.args.card:
            raise VocabError("bad_card", card="")
        given = read_stdin().rstrip("\r\n")
        return session.answer(
            learner,
            catalog,
            day,
            session.now_utc(),
            ctx.args.card,
            given,
            ahead=ctx.args.ahead,
            source=source,
        )
    results: list[dict[str, Any]] = []
    refused = 0
    for number, item in answer_lines(read_stdin()):
        if item is None:
            results.append(
                {"line": number, "error": VocabError("bad_batch_line", line=number).as_dict()}
            )
            refused += 1
            continue
        card, given = item["card"], item["answer"]
        try:
            results.append(
                session.answer(
                    learner,
                    catalog,
                    day,
                    session.now_utc(),
                    card,
                    given,
                    ahead=ctx.args.ahead,
                    source=source,
                )
            )
        except VocabError as exc:
            results.append({"card": card, "error": exc.as_dict()})
            refused += 1
    left = session.next_items(learner, catalog, day, count=0)["left"]
    return {"ok": refused == 0, "results": results, "refused": refused, "left": left}


def cmd_grade(ctx: Context) -> dict[str, Any]:
    source = "chat" if ctx.args.json else "cli"
    return session.self_grade(
        ctx.learner(),
        ctx.catalog(),
        ctx.day(),
        session.now_utc(),
        ctx.args.card,
        ctx.args.grade,
        ahead=ctx.args.ahead,
        source=source,
    )


def cmd_reveal(ctx: Context) -> dict[str, Any]:
    return session.reveal(ctx.catalog(), ctx.args.card)


def cmd_lookup(ctx: Context) -> dict[str, Any]:
    lang = ctx.args.lang.strip().lower()
    if lang not in ctx.catalog().installed():
        raise VocabError("no_course", lang=lang)
    try:
        learner: store.Learner | None = ctx.learner()
        day: date | None = ctx.day()
    except VocabError:
        learner, day = None, None
    return session.lookup(learner, ctx.catalog(), day, lang, read_stdin())


def render_lookup(data: dict[str, Any]) -> list[str]:
    lines = [
        f"{match['card']} [{str(match['level']).upper()}] {describe_word(match['word'])}"
        for match in data["matches"]
    ]
    return lines or [assets.text("cli.no_match")]


def render_reveal(data: dict[str, Any]) -> list[str]:
    return [describe_word(data["word"])]


def cmd_regrade(ctx: Context) -> dict[str, Any]:
    source = "chat" if ctx.args.json else "cli"
    return session.regrade(
        ctx.learner(),
        ctx.catalog(),
        ctx.day(),
        session.now_utc(),
        ctx.args.card,
        ctx.args.grade,
        source=source,
    )


def cmd_status(ctx: Context) -> dict[str, Any]:
    return progress.status(ctx.learner(), ctx.catalog(), ctx.day())


def cmd_forecast(ctx: Context) -> dict[str, Any]:
    return progress.forecast(ctx.learner(), ctx.catalog(), ctx.day(), ctx.args.days)


def cmd_plan(ctx: Context) -> dict[str, Any]:
    learner = ctx.learner()
    if ctx.args.plan_action == "set":
        preview = plans.set_preview(learner, ctx.catalog(), ctx.args.assignments, ctx.now)
        return finish_preview(ctx, preview)
    plan = learner.plan()
    return {"plan": plan, "lines": plans.describe(plan), "folder": str(learner.root)}


def cmd_words(ctx: Context) -> dict[str, Any]:
    learner = ctx.learner()
    preview = words.add_preview(learner, ctx.catalog(), ctx.args.lang, read_stdin(), ctx.now)
    return finish_preview(ctx, preview)


def cmd_commit(ctx: Context) -> dict[str, Any]:
    return gate.commit(ctx.args.confirm, ctx.pending_folders(), ctx.now, via="token")


def cmd_course(ctx: Context) -> dict[str, Any]:
    catalog = ctx.catalog()
    if ctx.args.course_action == "check":
        return courses.check(catalog)
    languages = {}
    for code, levels in catalog.installed().items():
        languages[code] = {
            "name": assets.language_name(code),
            "levels": {level: len(catalog.course(code, [level])) for level in levels},
            "meta": {
                k: v for k, v in catalog.meta(code).items() if k in ("title", "version", "license")
            },
        }
    return {"languages": languages}


def cmd_quiz(ctx: Context) -> dict[str, Any]:
    catalog = Catalog()
    if ctx.args.check:
        lines = []
        for number, item in answer_lines(read_stdin()):
            if item is None:
                raise VocabError("bad_batch_line", line=number)
            lines.append(item)
        return quiz.check(catalog, lines, lenient=ctx.args.lenient)
    lang = (ctx.args.lang or "").strip().lower()
    installed = catalog.installed()
    if lang not in installed:
        raise VocabError("no_course", lang=lang)
    levels = store.parse_levels(ctx.args.levels) if ctx.args.levels else installed[lang]
    data = quiz.questions(catalog, lang, levels, ctx.args.count)
    return run_quiz(catalog, data, ctx.args.lenient) if ctx.interactive() else data


def run_quiz(catalog: Catalog, data: dict[str, Any], lenient: bool) -> dict[str, Any]:
    """The test in a terminal, level by level; it stops at the first level below the threshold."""
    levels = ", ".join(level.upper() for level in data["levels"])
    print(
        assets.text("quiz.title", name=assets.language_name(data["lang"]), levels=levels),
        flush=True,
    )
    given: list[dict[str, Any]] = []
    for level in data["levels"]:
        items = [item for item in data["items"] if item["level"] == level]
        if not items:
            continue
        print("\n" + assets.text("quiz.level", level=level.upper()))
        for n, item in enumerate(items, 1):
            prompt = assets.text("quiz.question", n=n, meaning=describe_question(item["question"]))
            given.append({"card": item["card"], "answer": input(prompt + "\n> ")})
        result = quiz.check(catalog, given, lenient=lenient)
        if not result["levels"][level]["known"]:
            print(assets.text("quiz.stop", percent=round(quiz.KNOWN_SHARE * 100)))
            break
    return quiz.check(catalog, given, lenient=lenient)


def cmd_flag(ctx: Context) -> dict[str, Any]:
    learner, catalog = ctx.learner(), ctx.catalog()
    try:
        entry_id = split_card(ctx.args.card)[0]
    except ValueError:
        raise VocabError("bad_card", card=ctx.args.card) from None
    if catalog.entry(entry_id) is None:
        raise VocabError("unknown_card", card=ctx.args.card)
    row: dict[str, Any] = {"ts": store.iso(ctx.now), "entry": entry_id, "card": ctx.args.card}
    if ctx.args.clear:
        row["clear"] = True
    else:
        row["note"] = read_stdin().strip()[:500] if ctx.args.stdin else ""
    store.append_jsonl(learner.path(store.FLAGS), row)
    return {"entry": entry_id, "cleared": bool(ctx.args.clear)}


def cmd_doctor(ctx: Context) -> dict[str, Any]:
    learner = ctx.learner()
    if ctx.args.merge:
        return finish_preview(ctx, doctor.merge_preview(learner, ctx.now))
    if ctx.args.repair:
        return finish_preview(ctx, doctor.repair_preview(learner, ctx.now))
    return doctor.check(learner, ctx.catalog(), ctx.now)


def cmd_drill(ctx: Context) -> dict[str, Any]:
    from vocabbot import drill

    return drill.run(
        ctx.learner(), ctx.catalog(), ctx.day(), ahead=ctx.args.ahead, plain=ctx.args.plain
    )


def render_quiz(data: dict[str, Any]) -> list[str]:
    if "results" not in data:
        return [
            assets.text(
                "cli.item",
                n=n,
                tag=item["level"].upper(),
                phase=item["card"],
                meaning=describe_question(item["question"]),
            )
            for n, item in enumerate(data["items"], 1)
        ]
    lines = []
    for n, result in enumerate(data["results"], 1):
        word = result["word"]
        lines.append(
            assets.text(
                "quiz.result",
                n=n,
                meaning=word["meaning"],
                word=word["word"],
                grade=assets.text(f"grades.{result['grade']}"),
            )
        )
    for level, info in data["levels"].items():
        lines.append(
            assets.text(
                "quiz.level_line",
                level=level.upper(),
                percent=round(info["share"] * 100),
                **{k: info[k] for k in ("know", "almost", "asked")},
            )
        )
    if data["suggested_levels"]:
        lines.append(assets.text("quiz.suggest", levels=data["suggested_levels"].upper()))
    else:
        lines.append(assets.text("quiz.none"))
    return lines


def render_flag(data: dict[str, Any]) -> list[str]:
    key = "cli.unflagged" if data["cleared"] else "cli.flagged"
    return [assets.text(key, entry=data["entry"])]


def render_grade(data: dict[str, Any]) -> list[str]:
    if data["grade"] == "known":
        return [assets.text("cli.known", due=data.get("next_due", "-"))]
    return render_answer(data)


def render_regrade(data: dict[str, Any]) -> list[str]:
    return [
        assets.text(
            "cli.regraded",
            card=data["card"],
            was=assets.text(f"grades.{data['was']}"),
            grade=assets.text(f"grades.{data['grade']}"),
        )
    ]


def render_drill(data: dict[str, Any]) -> list[str]:
    return []


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json", action="store_true", help="print one JSON object (for the skills)"
    )
    common.add_argument("--learner", help="the learner's folder (default: the saved pointer)")
    common.add_argument("--today", help="the learning day as YYYY-MM-DD (default: today)")

    parser = argparse.ArgumentParser(
        prog="vocabbot",
        description="Vocabulary in one to three languages at once, with spaced repetition.",
    )
    parser.add_argument("--version", action="version", version=f"vocabbot {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(
        name: str,
        handler: Callable[[Context], dict[str, Any]],
        render: Renderer,
        help: str,
        group: bool = False,
    ) -> argparse.ArgumentParser:
        p = sub.add_parser(name, parents=[] if group else [common], help=help, description=help)
        p.set_defaults(handler=handler, render=render)
        return p

    p = add("init", cmd_init, render_preview, "create a learner folder and a plan")
    p.add_argument("folder", nargs="?", help="the folder (default: ~/VocabBot)")
    p.add_argument(
        "--lang",
        action="append",
        default=[],
        metavar="CODE:LEVELS[:WEIGHT]",
        help="a language, e.g. de:a1-a2 or en:b1-b2:2; repeat for up to three",
    )
    p.add_argument("--new", type=int, default=15, help="new words a day (default 15)")
    p.add_argument("--base", default="pl", help="the base language (pl)")
    p.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="another plan setting, e.g. days_off=sun; repeat as needed",
    )

    p = add(
        "use", cmd_use, render_simple("cli.use"), "use an existing learner's folder from now on"
    )
    p.add_argument("folder", help="the folder that holds registers/plan.json")

    p = add("today", cmd_today, render_summary, "the plan of the day")
    p.add_argument("--extra", type=int, default=0, help="add this many new words to today")

    p = add("drill", cmd_drill, render_drill, "the day's session in the terminal")
    p.add_argument(
        "--ahead", type=int, default=0, help="also review this many cards before their day"
    )
    p.add_argument("--plain", action="store_true", help="plain text without colours")

    p = add("next", cmd_next, render_next, "the next cards, without their answers")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--ahead", type=int, default=0)

    p = add("answer", cmd_answer, render_answer, "grade a typed answer read from standard input")
    p.add_argument("--card", help="the card, e.g. de-c00042#p")
    p.add_argument("--stdin", action="store_true", help="read the answer from standard input")
    p.add_argument(
        "--batch",
        action="store_true",
        help='read JSON lines {"card": ..., "answer": ...} from standard input',
    )
    p.add_argument("--ahead", action="store_true", help="accept a card before its day")

    p = add(
        "grade", cmd_grade, render_grade, "the learner's own grade: known, or a recognition card"
    )
    p.add_argument("--card", required=True)
    p.add_argument("--grade", required=True, choices=session.SELF_GRADES)
    p.add_argument("--ahead", action="store_true")

    p = add(
        "lookup",
        cmd_lookup,
        render_lookup,
        "find course entries for a word or a Polish meaning read from standard input",
    )
    p.add_argument("--lang", required=True)
    p.add_argument("--stdin", action="store_true", help="read the word from standard input")

    p = add(
        "reveal",
        cmd_reveal,
        render_reveal,
        "the meaning of a recognition card, before the learner's own grade",
    )
    p.add_argument("--card", required=True)

    p = add("regrade", cmd_regrade, render_regrade, "change today's last grade of a card")
    p.add_argument("--card", required=True)
    p.add_argument("--grade", required=True, choices=("know", "almost", "dont_know"))

    add("status", cmd_status, render_status, "progress for each language")

    p = add("forecast", cmd_forecast, render_forecast, "daily load and when levels are complete")
    p.add_argument("--days", type=int, default=30)

    p = add("plan", cmd_plan, render_lines, "show or change the plan", group=True)
    plan_sub = p.add_subparsers(dest="plan_action", required=True)
    plan_sub.add_parser("show", parents=[common], help="show the plan").set_defaults(
        render=render_lines
    )
    plan_set = plan_sub.add_parser("set", parents=[common], help="change the plan (preview first)")
    plan_set.add_argument("assignments", nargs="+", metavar="KEY=VALUE")
    plan_set.set_defaults(render=render_preview)

    p = add("words", cmd_words, render_preview, "add own words (preview first)", group=True)
    words_sub = p.add_subparsers(dest="words_action", required=True)
    words_add = words_sub.add_parser(
        "add", parents=[common], help="add own words from standard input"
    )
    words_add.add_argument("--lang", required=True)
    words_add.add_argument("--stdin", action="store_true")
    words_add.set_defaults(render=render_preview)

    p = add("commit", cmd_commit, render_preview, "apply a previewed change")
    p.add_argument("--confirm", required=True, metavar="TOKEN")

    p = add("course", cmd_course, render_courses, "installed courses", group=True)
    course_sub = p.add_subparsers(dest="course_action", required=True)
    course_sub.add_parser("list", parents=[common]).set_defaults(render=render_courses)
    course_sub.add_parser("check", parents=[common]).set_defaults(render=render_check)

    p = add(
        "quiz",
        cmd_quiz,
        render_quiz,
        "a placement test: questions without answers, then --check grades the answers",
    )
    p.add_argument("--lang", help="the course language, e.g. de")
    p.add_argument("--levels", help="levels to test, e.g. a1-b2 (default: every level)")
    p.add_argument("--count", type=int, default=8, help="questions per level (default 8)")
    p.add_argument(
        "--check",
        action="store_true",
        help='grade JSON lines {"card": ..., "answer": ...} from standard input; writes nothing',
    )
    p.add_argument("--stdin", action="store_true", help="read the answers from standard input")
    p.add_argument(
        "--lenient", action="store_true", help="a missing diacritic does not lower a grade"
    )

    p = add(
        "flag", cmd_flag, render_flag, "report a mistake in an entry (the note on standard input)"
    )
    p.add_argument("--card", required=True)
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--clear", action="store_true", help="withdraw the report")

    p = add("doctor", cmd_doctor, render_doctor, "check the learner's folder")
    p.add_argument("--merge", action="store_true", help="join conflict copies (preview first)")
    p.add_argument("--repair", action="store_true", help="move damaged rows aside (preview first)")
    return parser


def _utf8() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8()
    args = build_parser().parse_args(argv)
    ctx = Context(args=args, now=session.now_utc())
    try:
        data = args.handler(ctx)
    except VocabError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": exc.as_dict()}, ensure_ascii=False, indent=1))
        else:
            print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        error = VocabError(
            "io_error", path=str(exc.filename or ""), detail=exc.strerror or str(exc)
        )
        if args.json:
            print(json.dumps({"ok": False, "error": error.as_dict()}, ensure_ascii=False, indent=1))
        else:
            print(str(error), file=sys.stderr)
        return 1
    ok = bool(data.get("ok", True))
    if args.json:
        print(
            json.dumps(
                {"ok": ok, **{k: v for k, v in data.items() if k != "ok"}},
                ensure_ascii=False,
                indent=1,
                default=str,
            )
        )
    else:
        for line in args.render(data):
            print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
