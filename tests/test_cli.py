"""The program's commands with --json, as the skills call them."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from vocabbot import cli, store
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
        "init",
        str(folder),
        "--set",
        "new_words=show",
        "--lang",
        "de:a1-a2",
        "--lang",
        "es:a1-a2:2",
        "--new",
        "6",
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
    preview = program.run("init", str(folder), "--set", "new_words=show", "--lang", "fr:a1-a2")
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
    preview = program.run("init", str(folder), "--set", "new_words=show", "--lang", "de:a1")
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
    out = program.text("init", str(folder), "--set", "new_words=show", "--lang", "de:a1")
    assert "Bez zmian." in out
    assert not (folder / "registers" / "plan.json").exists()
    assert not list((tmp_path / "config" / "pending").glob("*.json"))
    out = program.text("init", str(folder), "--set", "new_words=show", "--lang", "de:a1")
    assert "Zapisano: nowy plan nauki (de)" in out
    decisions = (folder / "log" / "decisions.md").read_text("utf-8")
    assert "zatwierdzone w terminalu" in decisions


def test_plain_output_in_polish(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    token = program.run("init", str(folder), "--set", "new_words=show", "--lang", "fr:a1")["token"]
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
    token = program.run("init", str(folder), "--set", "new_words=show", "--lang", "de:a1")["token"]
    program.run("commit", "--confirm", token)
    out = program.text()
    assert "Dzień nauki" in out and "vocabbot drill" in out


def test_one_card_at_a_time_unless_the_plan_says_otherwise(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "de:a1-a2", "--new", "6"
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    assert program.run("today", *learner)["batch"] == 1
    first = program.run("next", *learner)["items"]
    assert len(first) == 1
    entry = catalog.card(first[0]["card"])
    assert entry is not None
    line = json.dumps({"card": first[0]["card"], "answer": entry["display"]})
    graded = program.run("answer", "--batch", "--stdin", "--next", *learner, stdin=line)
    assert graded["results"][0]["grade"] == "know"
    following = graded["next"]["items"]
    assert len(following) == 1 and following[0]["card"] != first[0]["card"]
    assert program.run("next", *learner)["items"] == following

    change = program.run("plan", "set", "batch=4", *learner)
    program.run("commit", "--confirm", change["token"], *learner)
    assert len(program.run("next", *learner)["items"]) == 4
    assert len(program.run("next", "--count", "2", *learner)["items"]) == 2
    refused = program.run("plan", "set", "batch=0", *learner, code=1)
    assert refused["error"]["code"] == "plan_invalid"


def test_the_counter_adds_up_and_the_day_lists_its_new_words(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "de:a1-a2", "--new", "4"
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    day = program.run("today", *learner)
    assert day["done"] == {"reviews": 0, "new": 0}
    assert day["counter"] == "Postęp: 0/4 · nowe 0/4"
    first = program.run("next", *learner)
    assert first["counter"] == day["counter"]
    card = first["items"][0]["card"]
    known = program.run("grade", "--card", card, "--grade", "known", *learner)
    # a word known before the course brings one more new word, outside the daily limit
    assert known["done"] == {"reviews": 0, "new": 1}
    assert known["counter"] == "Postęp: 1/5 · nowe 1/5"
    second = program.run("next", *learner)["items"][0]["card"]
    line = json.dumps({"card": second, "answer": ""})
    graded = program.run("answer", "--batch", "--stdin", *learner, stdin=line)
    assert graded["done"]["new"] == 2 and graded["left"]["drill"] == 1
    assert graded["counter"] == "Postęp: 2/5 · nowe 2/5 · do utrwalenia 1"
    first_entry, second_entry = catalog.card(card), catalog.card(second)
    assert first_entry is not None and second_entry is not None
    # the word waiting in the drill stays out of the list until it is answered
    waiting = program.run("today", *learner)["learned_today"]
    assert [w["word"] for w in waiting] == [first_entry["display"]]
    assert waiting[0]["known"] is True
    line = json.dumps({"card": second, "answer": second_entry["display"]})
    program.run("answer", "--batch", "--stdin", *learner, stdin=line)
    words = program.run("today", *learner)["learned_today"]
    assert [w["word"] for w in words] == [first_entry["display"], second_entry["display"]]
    assert "known" not in words[1]


def test_a_level_set_too_low_is_named_once(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "de:a1", "--new", "3"
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    hints = []
    for _ in range(11):
        card = program.run("next", *learner)["items"][0]["card"]
        hints.append(
            program.run("grade", "--card", card, "--grade", "known", *learner).get("level_hint")
        )
    assert hints[:9] == [None] * 9 and hints[10] is None
    assert hints[9] == {
        "lang": "de",
        "known": 10,
        "of": 10,
        "levels": "a1",
        "suggested": "a2",
        "setting": "lang.de.levels=a2",
    }


def test_a_change_of_levels_during_the_day_keeps_the_daily_limit(
    program: Program, tmp_path: Path
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "en:a1-a2", "--new", "4"
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    for _ in range(3):
        card = program.run("next", *learner)["items"][0]["card"]
        program.run("grade", "--card", card, "--grade", "known", *learner)
    card = program.run("next", *learner)["items"][0]["card"]
    line = json.dumps({"card": card, "answer": ""})
    program.run("answer", "--batch", "--stdin", *learner, stdin=line)
    before = program.run("today", *learner)
    # three known words added three places; one answered word used one of the four
    assert before["counter"] == "Postęp: 4/7 · nowe 4/7 · do utrwalenia 1"
    change = program.run("plan", "set", "lang.en.levels=a2", *learner)
    program.run("commit", "--confirm", change["token"], *learner)
    after = program.run("today", *learner)
    assert after["counter"] == before["counter"]
    assert after["done"] == {"reviews": 0, "new": 4} and after["left"]["new"] == 3
    # the answered word waits in the drill, so the list holds the three known words
    assert len(after["learned_today"]) == 3


def test_a_report_in_one_language_keeps_the_words_shown_in_another(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init",
        str(folder),
        "--set",
        "new_words=show",
        "--lang",
        "de:a1",
        "--lang",
        "es:a1",
        "--new",
        "4",
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", "2026-11-18")
    shown = []
    for _ in range(3):
        card = program.run("next", *learner)["items"][0]["card"]
        entry = catalog.card(card)
        assert entry is not None
        line = json.dumps({"card": card, "answer": entry["display"]})
        program.run("answer", "--batch", "--stdin", *learner, stdin=line)
        shown.append(card)
    waiting = program.run("next", *learner)["items"][0]["card"]
    program.run("flag", "--card", shown[-1], "--stdin", *learner, stdin="zły przykład")
    # the card on screen stays in the day and can be answered
    entry = catalog.card(waiting)
    assert entry is not None
    line = json.dumps({"card": waiting, "answer": entry["display"]})
    graded = program.run("answer", "--batch", "--stdin", *learner, stdin=line)
    assert graded["results"][0]["grade"] == "know"


def test_a_reported_card_leaves_the_drill_and_the_counter(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "de:a1", "--new", "2"
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    card = program.run("next", *learner)["items"][0]["card"]
    line = json.dumps({"card": card, "answer": ""})
    program.run("answer", "--batch", "--stdin", *learner, stdin=line)
    assert program.run("today", *learner)["left"]["drill"] == 1
    program.run("flag", "--card", card, "--stdin", *learner, stdin="zły przykład")
    day = program.run("today", *learner)
    assert day["left"]["drill"] == 0 and "do utrwalenia" not in day["counter"]


def test_the_next_cards_stay_in_the_chosen_stage(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run(
        "init", str(folder), "--set", "new_words=show", "--lang", "de:a1-a2", "--new", "3"
    )
    program.run("commit", "--confirm", preview["token"])
    monday = ("--learner", str(folder), "--today", DAY)
    for _ in range(3):
        card = program.run("next", *monday)["items"][0]["card"]
        program.run("grade", "--card", card, "--grade", "known", *monday)

    later = ("--learner", str(folder), "--today", "2026-11-30")
    today = program.run("today", *later)
    assert today["left"] == {"reviews": 3, "new": 3, "drill": 0}
    assert today["more"]["new"] > 0
    assert program.run("next", *later)["items"][0]["phase"] == "review"

    first = program.run("next", "--stage", "new", *later)
    assert first["stage"] == "new"
    card = first["items"][0]["card"]
    entry = catalog.card(card)
    assert entry is not None
    answered = program.run(
        "answer", "--card", card, "--stdin", "--next", *later, stdin=entry["display"]
    )
    assert answered["kind"] == "learn" and answered["next"]["stage"] == "new"
    second = answered["next"]["items"][0]
    assert second["phase"] == "new"
    known = program.run("grade", "--card", second["card"], "--grade", "known", "--next", *later)
    assert known["next"]["items"][0]["phase"] == "new"
    # a word marked as known brings one more; the last new words are left unanswered
    last = known
    while last["next"]["stage"] == "new":
        line = json.dumps({"card": last["next"]["items"][0]["card"], "answer": ""})
        last = program.run("answer", "--batch", "--stdin", "--next", *later, stdin=line)
    # the new words are done: the reviews follow, and the drill waits for the end
    assert last["next"]["stage"] == "reviews"
    assert last["left"] == {"reviews": 3, "new": 0, "drill": 2}

    # more new words on top of the day's number, with the first of them in the result
    more = program.run("today", "--extra", "2", "--next", *later)
    assert more["added"] == {"new": 2, "reviews": 0}
    assert more["next"]["stage"] == "new" and more["next"]["items"][0]["phase"] == "new"
    text = program.text("today", "--reviews", "1", *later)
    assert "Dodatkowe nowe słowa na dziś: 2." in text
    refused = program.run("today", "--reviews", "-1", *later, code=1)
    assert refused["error"]["code"] == "bad_extra"


def test_a_plan_asks_new_words_at_once_and_orders_the_reviews(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run("init", str(folder), "--lang", "de:a1", "--new", "2")
    assert any("jak w SuperMemo" in line for line in preview["preview"])
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    assert program.run("today", *learner)["new_words"] == "ask"
    item = program.run("next", *learner)["items"][0]
    assert item["phase"] == "new" and "word" not in item
    assert "nowe słowo" in program.text("next", *learner)
    line = json.dumps({"card": item["card"], "answer": ""})
    missed = program.run("answer", "--batch", "--stdin", "--next", *learner, stdin=line)
    assert missed["results"][0]["grade"] == "dont_know"
    assert missed["results"][0]["word"]["meaning"] and missed["next"]["stage"] == "new"

    change = program.run("plan", "set", "new_words=show", "review_order=interval", *learner)
    program.run("commit", "--confirm", change["token"], *learner)
    shown = program.run("next", *learner)["items"][0]
    assert shown["phase"] == "new" and shown["word"]["meaning"]
    text = program.text("plan", "show", *learner)
    assert "Kolejność powtórek: od najkrótszych odstępów" in text
    refused = program.run("plan", "set", "review_order=newest", *learner, code=1)
    assert refused["error"]["code"] == "plan_invalid"


def test_the_card_as_in_supermemo_through_the_commands(
    program: Program, tmp_path: Path, catalog: Catalog
) -> None:
    folder = tmp_path / "nauka"
    preview = program.run("init", str(folder), "--lang", "de:a1", "--new", "3")
    assert any(
        "Odpowiedź na kartę: wpisanie słowa, ocena silnika" in line for line in preview["preview"]
    )
    program.run("commit", "--confirm", preview["token"])
    learner = ("--learner", str(folder), "--today", DAY)
    settings = ("answer_mode=self", "sentence_translation=hidden", "next_review=hidden")
    change = program.run("plan", "set", *settings, *learner)
    program.run("commit", "--confirm", change["token"], *learner)
    text = program.text("plan", "show", *learner)
    assert "Tłumaczenie zdania: na żądanie, tak jak w SuperMemo" in text
    assert program.run("today", *learner)["view"] == {
        "new_words": "ask",
        "answer_mode": "self",
        "sentence_translation": "hidden",
        "next_review": "hidden",
    }

    item = program.run("next", *learner)["items"][0]
    note = program.run("note", "--card", item["card"], "--stdin", *learner, stdin="mój skrót\n")
    assert note["note"] == "mój skrót"
    shown = program.run("reveal", "--card", item["card"], *learner)
    assert shown["word"]["note"] == "mój skrót" and shown["grades"][1] == "almost"
    assert "Notatka: mój skrót" in program.text("reveal", "--card", item["card"], *learner)
    graded = program.run(
        "grade", "--card", item["card"], "--grade", "dont_know", "--next", *learner
    )
    assert graded["grade"] == "dont_know" and "back" not in graded
    assert graded["word"]["note"] == "mój skrót"

    skipped = program.run("flag", "--card", graded["next"]["items"][0]["card"], "--skip", *learner)
    assert skipped["skipped"] and skipped["counter"] == "Postęp: 1/3 · nowe 1/3 · do utrwalenia 1"
    out = program.text("status", *learner)
    assert "Odłożone słowa:" in out
    program.run("note", "--card", item["card"], "--clear", *learner)
    assert store.Learner(folder).notes() == {}
    refused = program.run("note", "--card", item["card"], "--stdin", *learner, stdin=" ", code=1)
    assert refused["error"]["code"] == "empty_stdin"


def test_conflict_copies_of_the_notes_are_joined(program: Program, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    token = program.run("init", str(folder), "--lang", "de:a1")["token"]
    program.run("commit", "--confirm", token)
    learner = ("--learner", str(folder), "--today", DAY)
    program.run("note", "--card", "de-c90001#p", "--stdin", *learner, stdin="na powitanie")
    copy = folder / "log" / "notes (konflikt).jsonl"
    copy.write_text(
        '{"ts": "2026-11-16T10:00:00.000000Z", "entry": "de-c90002", "note": "rano"}\n',
        encoding="utf-8",
    )
    preview = program.run("doctor", "--merge", *learner)
    program.run("commit", "--confirm", preview["token"], *learner)
    assert not copy.exists()
    assert store.Learner(folder).notes() == {"de-c90001": "na powitanie", "de-c90002": "rano"}
