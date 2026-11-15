"""The program's commands with --json, as the skills call them."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from vocabbot import cli
from vocabbot.courses import Catalog

DAY = "2026-11-16"


class Program:
    def __init__(self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
        self.capsys = capsys
        self.monkeypatch = monkeypatch

    def run(self, *argv: str, stdin: str = "", code: int = 0) -> dict[str, Any]:
        self.monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
        self.capsys.readouterr()
        assert cli.main([*argv, "--json"]) == code, self.capsys.readouterr()
        data: dict[str, Any] = json.loads(self.capsys.readouterr().out)
        return data

    def text(self, *argv: str, stdin: str = "") -> str:
        self.monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
        self.capsys.readouterr()
        cli.main(list(argv))
        out: str = self.capsys.readouterr().out
        return out


@pytest.fixture
def program(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> Program:
    return Program(capsys, monkeypatch)


def test_a_day_through_the_commands(program: Program, tmp_path: Path, catalog: Catalog) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--lang", "de:a1-a2", "--lang", "es:a1-a2:2", "--new", "6"
    )
    assert preview["token"]
    assert not (folder / "registers" / "plan.json").exists()
    applied = program.run("commit", "--confirm", preview["token"])
    assert "de, es" in applied["applied"]

    today = program.run("today", "--today", DAY)
    assert today["left"] == {"reviews": 0, "new": 6, "drill": 0}
    items = program.run("next", "--count", "20", "--today", DAY)["items"]
    assert len(items) == 6
    assert all(item["phase"] == "new" for item in items)

    lines = []
    for index, item in enumerate(items):
        entry = catalog.card(item["card"])
        assert entry is not None
        answer = entry["display"] if index else "xxx"
        lines.append(json.dumps({"card": item["card"], "answer": answer}, ensure_ascii=False))
    lines.append(json.dumps({"card": "de-c90060#p", "answer": "oft"}))
    lines.append("not json")
    result = program.run("answer", "--batch", "--today", DAY, stdin="\n".join(lines), code=1)
    assert result["refused"] == 2
    grades = [r.get("grade") for r in result["results"]]
    assert grades[:6] == ["dont_know", "know", "know", "know", "know", "know"]
    assert result["results"][6]["error"]["code"] == "not_in_today"
    assert result["left"] == {"reviews": 0, "new": 0, "drill": 1}

    drill = program.run("next", "--today", DAY)["items"][0]
    assert drill["phase"] == "drill"
    assert "word" not in drill
    regraded = program.run("regrade", "--card", drill["card"], "--grade", "almost", "--today", DAY)
    assert regraded["was"] == "dont_know"
    again = program.run(
        "answer",
        "--card",
        drill["card"],
        "--stdin",
        "--today",
        DAY,
        stdin=catalog.card(drill["card"])["display"] + "\n",
    )
    assert again["kind"] == "drill"
    assert again["grade"] == "know"

    status = program.run("status", "--today", DAY)
    assert status["languages"]["de"]["cards"] + status["languages"]["es"]["cards"] == 6
    forecast = program.run("forecast", "--days", "14", "--today", DAY)
    assert len(forecast["days"]) == 14
    assert forecast["days"][2]["reviews"] > 0

    plan = program.run("plan", "show")
    assert plan["plan"]["new_per_day"] == 6
    change = program.run("plan", "set", "new_per_day=8", "days_off=sun")
    program.run("commit", "--confirm", change["token"])
    assert program.run("plan", "show")["plan"]["days_off"] == ["sun"]

    added = program.run("words", "add", "--lang", "de", "--stdin", stdin="der Schrank = szafa\n")
    program.run("commit", "--confirm", added["token"])

    flagged = program.run("flag", "--card", "de-c90010#p", "--stdin", stdin="zły rodzaj\n")
    assert flagged["entry"] == "de-c90010"
    assert program.run("doctor")["ok"]
    assert program.run("course", "check")["ok"]
    courses = program.run("course", "list")["languages"]
    assert courses["fr"]["levels"] == {"a1": 40, "a2": 20}


def test_setup_where_only_the_working_folder_can_be_written(
    program: Program, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sandbox (Codex) forbids ~/.vocabbot: the preview waits in the new folder."""
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("a file where the config folder would be", encoding="utf-8")
    monkeypatch.setenv("VOCABBOT_CONFIG", str(blocked / "config"))
    folder = tmp_path / "nauka"
    monkeypatch.chdir(tmp_path)
    preview = program.run("init", str(folder), "--lang", "fr:a1-a2")
    assert (folder / "registers" / ".pending" / f"{preview['token']}.json").is_file()
    assert not (folder / "registers" / "plan.json").exists()
    done = program.run("commit", "--confirm", preview["token"], "--learner", str(folder))
    assert done["skipped"] == [str(blocked / "config" / "config.json")]
    assert (folder / "registers" / "plan.json").is_file()
    monkeypatch.chdir(folder)
    assert program.run("today")["languages"]["fr"]["new"] > 0
    error = program.run("plan", "set", "new_per_day=5", "--learner", str(blocked), code=1)
    assert error["error"]["code"] == "no_plan"


def test_a_refused_write_is_a_json_error(
    program: Program, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise PermissionError(13, "Access is denied", "C:/somewhere/plan.json")

    monkeypatch.setattr("vocabbot.store.write_text", refuse)
    monkeypatch.setattr("vocabbot.gate.store.write_text", refuse)
    error = program.run("init", str(tmp_path / "x"), "--lang", "de:a1", code=1)
    assert error["error"]["code"] == "io_error"


def test_use_points_at_an_existing_folder(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    preview = program.run("init", str(folder), "--lang", "de:a1")
    program.run("commit", "--confirm", preview["token"])
    (tmp_path / "config" / "config.json").unlink()
    assert program.run("today", code=1)["error"]["code"] == "no_learner"
    assert program.run("use", str(folder))["learner"] == str(folder.resolve())
    assert program.run("today")["languages"]["de"]["new"] > 0
    assert program.run("use", str(tmp_path / "empty"), code=1)["error"]["code"] == "no_plan"


def test_placement_test_through_the_program(program: Program) -> None:
    data = program.run("quiz", "--lang", "de", "--levels", "a1", "--count", "2")
    assert len(data["items"]) == 2
    lines = "\n".join(json.dumps({"card": i["card"], "answer": "xxx"}) for i in data["items"])
    result = program.run("quiz", "--check", "--stdin", stdin=lines)
    assert result["suggested_levels"] == "a1-b2"
    assert program.run("quiz", "--lang", "xx", code=1)["error"]["code"] == "no_course"
    bad = program.run("quiz", "--check", "--stdin", stdin="not json", code=1)
    assert bad["error"]["code"] == "bad_batch_line"


def test_errors_are_json_with_a_code(program: Program, tmp_path: Path) -> None:
    error = program.run("today", code=1)
    assert error == {
        "ok": False,
        "error": {"code": "no_learner", "message": error["error"]["message"]},
    }
    error = program.run("init", str(tmp_path / "x"), "--lang", "en:c1", code=1)
    assert error["error"]["code"] == "bad_levels"
    error = program.run("commit", "--confirm", "0123456789abcdef", code=1)
    assert error["error"]["code"] == "unknown_token"


def test_terminal_asks_before_writing(
    program: Program, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.Context, "interactive", lambda self: True)
    replies = iter(["n", "t"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    folder = tmp_path / "nauka"
    out = program.text("init", str(folder), "--lang", "de:a1")
    assert "Bez zmian." in out
    assert not (folder / "registers" / "plan.json").exists()
    assert not list((tmp_path / "config" / "pending").glob("*.json"))
    out = program.text("init", str(folder), "--lang", "de:a1")
    assert "Zapisano: nowy plan nauki (de)" in out
    decisions = (folder / "log" / "decisions.md").read_text("utf-8")
    assert "zatwierdzone w terminalu" in decisions


def test_plain_output_in_polish(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    token = program.run("init", str(folder), "--lang", "fr:a1")["token"]
    program.run("commit", "--confirm", token)
    out = program.text("today", "--today", DAY)
    assert "Dzień nauki 2026-11-16 (poniedziałek)" in out
    assert "francuski (fr)" in out
    out = program.text("next", "--today", DAY, "--count", "2")
    assert "[FR] nowe słowo: la maison" in out
    out = program.text("status", "--today", DAY)
    assert "(cel 90%)" in out and "Odstępy po pierwszej odpowiedzi" in out
    out = program.text("forecast", "--today", DAY)
    assert "Prognoza na 30 dni" in out


def test_start_screen(program: Program, tmp_path: Path) -> None:
    out = program.text()
    assert "Folder nauki jeszcze nie istnieje" in out
    folder = tmp_path / "nauka"
    token = program.run("init", str(folder), "--lang", "de:a1")["token"]
    program.run("commit", "--confirm", token)
    out = program.text()
    assert "Dzień nauki" in out and "vocabbot drill" in out
