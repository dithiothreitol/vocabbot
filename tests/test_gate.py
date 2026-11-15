"""Preview and commit, the learner's folder, own words and the doctor."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import make_learner, moment

from vocabbot import courses, doctor, gate, plans, store, words
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError
from vocabbot.queue import compute

MONDAY = date(2026, 11, 16)


def pending(learner: store.Learner) -> list[Path]:
    return [learner.path(store.PENDING), store.config_dir() / "pending"]


def test_plan_change_is_written_only_by_commit(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"])
    before = learner.path(store.PLAN).read_bytes()
    preview = plans.set_preview(
        learner, catalog, ["new_per_day=20", "lang.es=a1-a2:2"], moment(MONDAY)
    )
    assert "new_per_day: 15 → 20" in preview["preview"]
    assert learner.path(store.PLAN).read_bytes() == before
    result = gate.commit(preview["token"], pending(learner), moment(MONDAY, 60), via="token")
    assert "new_per_day" in result["applied"]
    plan = store.Learner(learner.root).plan()
    assert plan["new_per_day"] == 20
    assert [i["code"] for i in plan["languages"]] == ["de", "es"]
    assert "zatwierdzone tokenem" in learner.path(store.DECISIONS).read_text("utf-8")
    with pytest.raises(VocabError) as error:
        gate.commit(preview["token"], pending(learner), moment(MONDAY, 61), via="token")
    assert error.value.code == "unknown_token"


def test_expired_and_stale_previews_are_refused(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"])
    preview = plans.set_preview(learner, catalog, ["new_per_day=20"], moment(MONDAY))
    with pytest.raises(VocabError) as error:
        gate.commit(
            preview["token"], pending(learner), moment(MONDAY) + timedelta(minutes=31), via="token"
        )
    assert error.value.code == "token_expired"
    preview = plans.set_preview(learner, catalog, ["new_per_day=20"], moment(MONDAY))
    plan = json.loads(learner.path(store.PLAN).read_text("utf-8"))
    plan["new_per_day"] = 5
    store.write_text(learner.path(store.PLAN), store.dump_json(plan))
    with pytest.raises(VocabError) as error:
        gate.commit(preview["token"], pending(learner), moment(MONDAY, 5), via="token")
    assert error.value.code == "changed_since_preview"
    for token, code in (("nope", "bad_token"), ("0123456789abcdef", "unknown_token")):
        with pytest.raises(VocabError) as error:
            gate.commit(token, pending(learner), moment(MONDAY), via="token")
        assert error.value.code == code


def test_plan_checks(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"])
    for assignment, code in [
        (["lang.en=b1-b2"], "plan_invalid"),
        (["lang.en=a1", "lang.es=a1", "lang.fr=a1"], "plan_invalid"),
        (["retention=0.99"], "plan_invalid"),
        (["new_per_day=15"], "no_change"),
        (["colour=blue"], "unknown_key"),
        (["new_per_day"], "bad_assignment"),
    ]:
        with pytest.raises(VocabError) as error:
            plans.set_preview(learner, catalog, assignment, moment(MONDAY))
        assert error.value.code == code, assignment
    preview = plans.set_preview(
        learner,
        catalog,
        ["max_languages=4", "lang.en=a1", "lang.es=a1", "lang.fr=a1"],
        moment(MONDAY),
    )
    assert preview["token"]


def test_init_writes_the_folder_and_the_pointer(tmp_path: Path, catalog: Catalog) -> None:
    folder = tmp_path / "nauka"
    preview = plans.init_preview(folder, ["de:a1-a2", "es:a1:2"], 10, catalog, moment(MONDAY))
    assert not folder.exists() or not (folder / store.PLAN).exists()
    gate.commit(preview["token"], [store.config_dir() / "pending"], moment(MONDAY, 1), via="token")
    assert store.locate() == folder.resolve()
    plan = store.Learner(folder).plan()
    assert plan["new_per_day"] == 10
    assert plan["languages"][1]["weight"] == 2
    with pytest.raises(VocabError) as error:
        plans.init_preview(folder, ["de:a1"], 10, catalog, moment(MONDAY))
    assert error.value.code == "plan_exists"


def test_own_words(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    text = "\n".join(
        [
            "der Schrank = szafa | Der Schrank ist groß. | Szafa jest duża.",
            "gehen = iść",
            json.dumps(
                {"display": "die Tasse", "gender": "f", "pos": "noun", "gloss": {"pl": "filiżanka"}}
            ),
        ]
    )
    # gehen is in the course (de-c90023): the preview moves it forward instead of copying it
    preview = words.add_preview(learner, Catalog(learner=learner.root), "de", text, moment(MONDAY))
    assert len(preview["preview"]) == 3
    assert preview["moved"] == ["de-c90023"]
    assert len(preview["added"]) == 2
    gate.commit(preview["token"], pending(learner), moment(MONDAY, 1), via="token")
    fresh = Catalog(learner=learner.root)
    own = fresh.own("de")
    assert [e["display"] for e in own] == ["der Schrank", "die Tasse"]
    assert own[0]["gender"] == "m"
    assert own[1]["lemma"] == "Tasse"
    assert own[0]["example"]["gap"] == "Der Schrank"
    assert [e["id"] for e in fresh.first("de")] == [own[0]["id"], own[1]["id"], "de-c90023"]
    assert fresh.moved_forward("de") == {"de-c90023"}
    assert courses.check(fresh)["ok"]
    learner_three = make_learner(tmp_path / "three", ["de:a1"], new_per_day=3)
    store.write_text(
        learner_three.own_path("de"), learner.own_path("de").read_text(encoding="utf-8")
    )
    new = compute(learner_three, Catalog(learner=learner_three.root), MONDAY).new
    assert new == [f"{own[0]['id']}#p", f"{own[1]['id']}#p", "de-c90023#p"]
    # the same words again: own words and moved words are left out, so nothing remains
    with pytest.raises(VocabError) as error:
        words.add_preview(learner, fresh, "de", text, moment(MONDAY, 2))
    assert error.value.code == "nothing_to_add"
    mixed = words.add_preview(
        learner, fresh, "de", "der Schrank = szafa\nlaufen [verb] = biegać", moment(MONDAY, 3)
    )
    assert len(mixed["added"]) == 1
    assert len(mixed["skipped"]) == 1
    outside = words.add_preview(learner, fresh, "es", "la mesa = stół", moment(MONDAY, 4))
    assert any("nie należy do planu" in line for line in outside["preview"])


def test_init_takes_further_settings(tmp_path: Path, catalog: Catalog) -> None:
    preview = plans.init_preview(
        tmp_path / "nauka",
        ["de:a1-a2"],
        10,
        catalog,
        moment(MONDAY),
        assignments=["days_off=sun", "diacritics=lenient"],
    )
    assert any("niedziela" in line for line in preview["preview"])
    gate.commit(preview["token"], [store.config_dir() / "pending"], moment(MONDAY, 1), via="token")
    plan = store.Learner(tmp_path / "nauka").plan()
    assert plan["days_off"] == ["sun"]
    assert plan["diacritics"] == "lenient"
    with pytest.raises(VocabError) as error:
        plans.init_preview(
            tmp_path / "other", ["de:a1"], 10, catalog, moment(MONDAY), assignments=["mix=wild"]
        )
    assert error.value.code == "plan_invalid"


def test_the_current_folder_counts_when_it_holds_a_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    learner = make_learner(tmp_path / "nauka", ["de:a1"])
    with pytest.raises(VocabError) as error:
        store.locate()
    assert error.value.code == "no_learner"
    monkeypatch.chdir(learner.root)
    assert store.locate() == learner.root.resolve()


def test_damaged_rows_and_conflict_copies(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path, ["de:a1-a2"], new_per_day=2)
    log = learner.path(store.REVIEWS)
    row = {
        "ts": "2026-11-16T12:00:00.000000Z",
        "day": "2026-11-16",
        "card": "de-c90001#p",
        "lang": "de",
        "grade": "know",
        "kind": "learn",
        "source": "cli",
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_bytes((store.dump_line(row) + "\n" + '{"ts": "2026-11-16T12:00:01').encode("utf-8"))
    learner.append_review({**row, "ts": "2026-11-16T12:00:02.000000Z", "card": "de-c90002#p"})
    rows, damaged = learner.rows()
    assert len(rows) == 2
    assert damaged == [2]
    assert b"\r\n" not in log.read_bytes()
    copy = learner.path("log/reviews (1).jsonl")
    copy.write_bytes(
        (
            store.dump_line({**row, "ts": "2026-11-16T12:00:03.000000Z", "card": "de-c90003#p"})
            + "\n"
        ).encode("utf-8")
    )
    report = doctor.check(learner, catalog, moment(MONDAY))
    assert {p["code"] for p in report["problems"]} >= {"damaged_rows", "conflict_copies"}
    repair = doctor.repair_preview(learner, moment(MONDAY))
    gate.commit(repair["token"], pending(learner), moment(MONDAY, 1), via="token")
    assert learner.rows()[1] == []
    assert len(learner.rows()[0]) == 2
    aside = list(learner.path("log").glob("damaged-*.txt"))
    assert len(aside) == 1
    assert aside[0].read_text("utf-8").startswith('{"ts": "2026-11-16T12:00:01')
    merge = doctor.merge_preview(learner, moment(MONDAY))
    gate.commit(merge["token"], pending(learner), moment(MONDAY, 2), via="token")
    assert not copy.exists()
    assert len(learner.rows()[0]) == 3
    assert doctor.check(learner, catalog, moment(MONDAY))["ok"]


def test_learning_day_starts_at_four() -> None:
    from datetime import datetime

    late = datetime(2026, 11, 17, 2, 30).astimezone()
    assert store.learning_day(late, 4) == date(2026, 11, 16)
    assert store.learning_day(late, 0) == date(2026, 11, 17)


def test_levels_and_language_specs() -> None:
    assert store.parse_levels("a1-b1") == ["a1", "a2", "b1"]
    assert store.parse_levels("b2,a1") == ["a1", "b2"]
    assert store.parse_language("en:b1-b2:2") == {"code": "en", "levels": ["b1", "b2"], "weight": 2}
    for bad in ("c1", "b2-a1", ""):
        with pytest.raises(VocabError):
            store.parse_levels(bad)
