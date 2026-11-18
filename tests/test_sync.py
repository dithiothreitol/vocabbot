"""Stage 12: a folder linked to an account, its synchronisation, and moving a record.

The account's side (`sync.serve`) runs in the process behind a transport that
passes every request through JSON, as HTTP does, so these tests need no
server packages and run on Python 3.10 as well.
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from conftest import COURSES, card_of, correct, make_learner, moment

from vocabbot import cli, gate, plans, remote, session, store, sync, words
from vocabbot.book import replay
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError
from vocabbot.queue import compute

MONDAY = date(2026, 11, 16)
LATER = datetime(2030, 1, 1, tzinfo=timezone.utc)


class Account:
    """The account's folder and its side of the synchronisation, as a transport."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.offline = False
        self.requests: list[dict[str, Any]] = []
        self.now = LATER

    def exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.offline:
            raise VocabError("server_unreachable", server="test", detail="offline")
        sent = json.loads(json.dumps(payload))
        self.requests.append(sent)
        out = sync.serve(
            self.root,
            sent,
            lambda: Catalog(COURSES, learner=self.root),
            Catalog(COURSES).installed(),
            self.now,
            zone="Europe/Warsaw",
        )
        out["account"] = {"login": "ola", "timezone": "Europe/Warsaw"}
        return json.loads(json.dumps(out))


def installed() -> dict[str, list[str]]:
    return Catalog(COURSES).installed()


def link(root: Path, plan_from: str | None = "folder", zone: str | None = None) -> None:
    """The link `login` writes: with `plan_from` for a folder that has a plan, without it
    for a new folder that takes the account as it is."""
    state: dict[str, Any] = {"server": "https://test", "login": "ola"}
    if plan_from is not None:
        state["first"] = {"plan_from": plan_from}
        if zone:
            state["first"]["timezone"] = zone
    sync.save_state(root, state)


def run(root: Path, account: Account, now: datetime | None = None) -> dict[str, Any]:
    return sync.run(root, account, now or moment(MONDAY), installed)


def pending(learner: store.Learner) -> list[Path]:
    return [learner.path(store.PENDING), store.config_dir() / "pending"]


def rows_of(root: Path, name: str = store.REVIEWS) -> set[str]:
    return sync.keys_of(name, sync.read_lines(root / name))


def answer_some(learner: store.Learner, day: date, count: int, start: int = 0) -> list[str]:
    catalog = Catalog(COURSES, learner=learner.root)
    done = []
    for n in range(count):
        dp = compute(learner, catalog, day)
        if not dp.sequence:
            break
        card = dp.sequence[0].card
        session.answer(learner, catalog, day, moment(day, start + n), card, correct(catalog, card))
        done.append(card)
    return done


def state_of(root: Path, day: date) -> tuple[Any, ...]:
    """What must agree between devices: rows, card states, the day's queue and the plan."""
    learner = store.Learner(root)
    catalog = Catalog(COURSES, learner=root)
    book = replay(learner.rows()[0])
    cards = {
        card: (state.last_day, round(state.memory.stability, 6), state.reps, state.lapses)
        for card, state in book.cards.items()
    }
    dp = compute(learner, catalog, day)
    plan = {k: v for k, v in learner.plan().items() if k != "parameters_info"}
    streams = {
        name: sync.keys_of(name, sync.read_lines(root / name))
        for name in sync.stream_names(root)
        if name != store.DECISIONS
    }
    return (
        cards,
        [item.card for item in dp.sequence],
        json.dumps(plan, sort_keys=True),
        streams,
        sorted(learner.notes().items()),
        sorted(learner.flag_states().items()),
    )


# ---------------------------------------------------------------- reading a log in its order


def test_rows_from_another_device_join_in_the_order_of_the_log(tmp_path: Path) -> None:
    learner = make_learner(tmp_path / "a", ["de:a1"])
    answer_some(learner, MONDAY, 3)
    rows, _ = learner.rows()
    late = {**rows[0], "ts": "2026-11-16T11:00:00.000000Z", "card": card_of("de", 30)}
    store.append_jsonl(learner.path(store.REVIEWS), late)
    fresh = store.Learner(learner.root)
    ordered, _ = fresh.rows()
    assert ordered[0]["card"] == card_of("de", 30)
    assert [r["ts"] for r in ordered] == sorted(r["ts"] for r in ordered)
    # an answer after that is still the latest row, kept in order in memory
    answer_some(fresh, MONDAY, 1, start=100)
    assert fresh.rows()[0] == sorted(fresh.rows()[0], key=store.log_order)


def test_conflict_copies_of_notes_and_reports_count_without_a_merge(tmp_path: Path) -> None:
    learner = make_learner(tmp_path / "a", ["de:a1"])
    catalog = Catalog(COURSES, learner=learner.root)
    session.save_note(learner, catalog, card_of("de", 1), moment(MONDAY, 1), "pierwsza")
    copy = learner.path("log/notes-DESKTOP.jsonl")
    entry = card_of("de", 1).split("#")[0]
    store.append_jsonl(copy, {"ts": store.iso(moment(MONDAY, 5)), "entry": entry, "note": "nowsza"})
    flags = learner.path("log/flags (2).jsonl")
    store.append_jsonl(flags, {"ts": store.iso(moment(MONDAY, 6)), "entry": entry, "skip": True})
    assert learner.notes()[entry] == "nowsza"
    assert learner.flag_states() == {entry: "skip"}


# ---------------------------------------------------------------- the time zone of the plan


def test_the_plan_names_the_time_zone_of_the_learning_day(tmp_path: Path) -> None:
    assert store.zone_problem("") is None
    assert store.zone_problem("Europe/Warsaw") is None
    assert store.zone_problem("UTC") is None
    assert store.zone_problem("../etc/passwd") is not None
    assert store.zone_problem("Mars/Olympus") is not None
    learner = make_learner(tmp_path / "a", ["de:a1"], timezone="America/New_York")
    late = datetime(2026, 11, 17, 3, 0, tzinfo=timezone.utc)  # 22:00 in New York, Nov 16
    assert store.learning_day(late, 0, learner.zone()) == date(2026, 11, 16)
    preview = plans.set_preview(learner, Catalog(COURSES), ["timezone=Europe/Warsaw"], LATER)
    assert "timezone: America/New_York → Europe/Warsaw" in preview["preview"]
    with pytest.raises(VocabError) as bad:
        plans.set_preview(learner, Catalog(COURSES), ["timezone=Nowhere/Land"], LATER)
    assert bad.value.code == "plan_invalid"


# ---------------------------------------------------------------- the plan's history


def test_every_change_of_the_plan_has_a_row_and_the_rows_give_the_plan(tmp_path: Path) -> None:
    learner = make_learner(tmp_path / "a", ["de:a1"], new_per_day=6)
    assert plans.history_rows(learner.root) == []
    preview = plans.set_preview(learner, Catalog(COURSES), ["new_per_day=8"], moment(MONDAY))
    gate.commit(preview["token"], pending(learner), moment(MONDAY, 1), via="token")
    rows = plans.history_rows(learner.root)
    # the first row keeps the plan saved before the history began, the second the change
    assert rows[0].get("base") and rows[0]["set"]["new_per_day"] == 6
    assert rows[1]["set"] == {"new_per_day": 8}
    folded = store.complete_plan(plans.fold(rows) or {})
    assert folded == store.Learner(learner.root).plan()
    # a later change of another setting on another device joins; the last value of each holds
    later = {"ts": store.iso(moment(MONDAY, 50)), "set": {"days_off": ["sun"]}}
    earlier = {"ts": store.iso(moment(MONDAY, -50)), "set": {"new_per_day": 3}}
    store.append_jsonl(learner.path(store.PLAN_LOG), later)
    store.append_jsonl(learner.path(store.PLAN_LOG), earlier)
    assert plans.apply_history(learner.root, installed()) == {"changed": True}
    plan = store.Learner(learner.root).plan()
    assert plan["days_off"] == ["sun"] and plan["new_per_day"] == 8
    # a history that gives a plan failing its check leaves the plan in force
    bad = {"ts": store.iso(moment(MONDAY, 99)), "set": {"new_per_day": 1000}}
    store.append_jsonl(learner.path(store.PLAN_LOG), bad)
    applied = plans.apply_history(learner.root, installed())
    assert not applied["changed"] and applied["problems"]
    assert store.Learner(learner.root).plan()["new_per_day"] == 8


# ---------------------------------------------------------------- linking and joining


def test_a_folder_joins_an_empty_account_and_a_second_computer_downloads_it(
    tmp_path: Path,
) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1", "es:a1"], new_per_day=6)
    answer_some(one, MONDAY, 4)
    link(one.root, "folder", "Europe/Warsaw")
    result = run(one.root, account)
    assert result["ok"] and result["pending"] == 0 and result["sent"] >= 4
    assert rows_of(account.root) == rows_of(one.root)
    # the plan of the folder holds on the account, with the account's time zone
    assert store.Learner(account.root).plan()["timezone"] == "Europe/Warsaw"
    assert store.Learner(one.root).plan()["timezone"] == "Europe/Warsaw"
    two = tmp_path / "two"
    two.mkdir()
    link(two, None)
    run(two, account)
    assert state_of(two, MONDAY) == state_of(one.root, MONDAY)
    # a session begun on one computer goes on on the other, at the same card
    next_one = compute(store.Learner(one.root), Catalog(COURSES, learner=one.root), MONDAY)
    next_two = compute(store.Learner(two), Catalog(COURSES, learner=two), MONDAY)
    assert next_one.sequence[0].card == next_two.sequence[0].card
    answer_some(store.Learner(two), MONDAY, 2, start=200)
    run(two, account)
    run(one.root, account)
    assert state_of(one.root, MONDAY) == state_of(two, MONDAY)


def test_the_account_plan_holds_when_the_learner_chooses_it(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"], new_per_day=6)
    link(one.root)
    run(one.root, account)
    other = make_learner(tmp_path / "other", ["es:a1"], new_per_day=9)
    answer_some(other, MONDAY, 2)
    found = sync.probe(account)
    assert sync.plans_differ(other, found)
    preview = sync.link_preview(other, "https://test", found, "account", moment(MONDAY))
    text = "\n".join(preview["preview"])
    assert "Odpowiedzi: w folderze 2, na koncie 0, po połączeniu 2." in text
    assert "plan konta" in text
    gate.commit(preview["token"], pending(other), moment(MONDAY, 1), via="token")
    run(other.root, account)
    plan = store.Learner(other.root).plan()
    assert [item["code"] for item in plan["languages"]] == ["de"] and plan["new_per_day"] == 6
    # the folder's two answers joined the account
    assert len(rows_of(account.root)) == 2


def test_sending_again_doubles_nothing_and_a_fresh_start_gives_the_same_state(
    tmp_path: Path,
) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    answer_some(one, MONDAY, 3)
    link(one.root)
    run(one.root, account)
    before = (account.root / store.REVIEWS).read_bytes()
    account.exchange(account.requests[0])  # the same request again
    assert (account.root / store.REVIEWS).read_bytes() == before
    state = sync.link_state(one.root)
    assert state is not None
    state.pop("files")
    state.pop("epoch")
    sync.save_state(one.root, state)
    log_before = (one.root / store.REVIEWS).read_bytes()
    run(one.root, account)
    assert (one.root / store.REVIEWS).read_bytes() == log_before
    assert (account.root / store.REVIEWS).read_bytes() == before


def test_without_a_network_the_rows_wait_and_go_later(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    run(one.root, account)
    answer_some(one, MONDAY, 3)
    account.offline = True
    failed = remote.auto(one.root, moment(MONDAY, 10), installed, transport=account)
    assert failed is not None and not failed["ok"] and failed["pending"] == 3
    assert failed["error"]["code"] == "server_unreachable"
    described = remote.describe(one.root)
    assert described is not None and described["pending"] == 3
    assert described["failed"]["code"] == "server_unreachable"
    account.offline = False
    done = remote.auto(one.root, moment(MONDAY, 20), installed, transport=account)
    assert done is not None and done["ok"] and done["pending"] == 0
    assert rows_of(account.root) == rows_of(one.root)
    assert "failed" not in (sync.link_state(one.root) or {})


def test_the_same_card_on_two_devices_moves_its_date_once(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"], new_per_day=2)
    answer_some(one, MONDAY, 2)
    link(one.root)
    run(one.root, account)
    two = tmp_path / "two"
    two.mkdir()
    link(two, None)
    run(two, account)
    tuesday = MONDAY + timedelta(days=2)
    catalog = Catalog(COURSES)
    card = compute(one, Catalog(COURSES, learner=one.root), tuesday).reviews[0]
    # both devices answer the same review without a network: two first, then one
    session.answer(
        store.Learner(two), Catalog(COURSES, learner=two), tuesday, moment(tuesday, 1), card, "xx"
    )
    session.answer(
        store.Learner(one.root),
        Catalog(COURSES, learner=one.root),
        tuesday,
        moment(tuesday, 2),
        card,
        correct(catalog, card),
    )
    for root in (one.root, two, one.root):
        run(root, account)
    book = replay(store.Learner(one.root).rows()[0])
    kinds = [row.kind for row in book.rows if row.card == card and row.day == tuesday]
    assert kinds == ["review", "drill"]
    assert state_of(one.root, tuesday) == state_of(two, tuesday)


def test_the_account_refuses_rows_it_cannot_trust(tmp_path: Path) -> None:
    root = tmp_path / "account"
    good = {
        "ts": "2026-11-16T12:00:00.000000Z",
        "day": "2026-11-16",
        "card": card_of("de", 1),
        "lang": "de",
        "grade": "know",
        "kind": "learn",
    }
    unknown = {**good, "card": "de-c99999#p"}
    future = {**good, "ts": "2031-01-01T00:00:00.000000Z", "day": "2031-01-01"}
    stranger = {"id": "de-c00001", "lang": "de", "level": "own"}
    lines = [store.dump_line(r) for r in (good, unknown, future)] + ["not json", "a\nb"]
    request = {
        "files": {
            store.REVIEWS: {"rows": lines},
            "courses/de/own.jsonl": {"rows": [store.dump_line(stranger)]},
            "../escape.jsonl": {"rows": [store.dump_line(good)]},
        }
    }
    out = sync.serve(
        root,
        request,
        lambda: Catalog(COURSES, learner=root),
        installed(),
        LATER - timedelta(days=365),
        zone="UTC",
    )
    reasons = sorted(r["reason"] for r in out["refused"])
    assert reasons == ["future", "invalid_row", "not_a_line", "not_a_row", "unknown_card"]
    assert out["received"] == {store.REVIEWS: 1}
    assert not (tmp_path / "escape.jsonl").exists()
    with pytest.raises(VocabError) as large:
        sync.serve(
            root,
            {"files": {store.REVIEWS: {"rows": ["x"] * (sync.PUSH_LIMIT + 1)}}},
            lambda: Catalog(COURSES, learner=root),
            installed(),
            LATER,
        )
    assert large.value.code == "sync_too_large"


def test_three_devices_converge_whatever_the_order(tmp_path: Path) -> None:
    """Answers, notes, words put aside, own words and plan changes on three devices, with
    synchronisations at random moments: after the last one every side has the same record."""
    for seed in range(3):
        base = tmp_path / f"seed{seed}"
        rng = random.Random(seed)
        account = Account(base / "account")
        first = make_learner(base / "d0", ["de:a1", "es:a1"], new_per_day=4)
        # the plan was saved before the days of the test, as it would be in use
        early = moment(MONDAY - timedelta(days=7)).timestamp()
        os.utime(first.path(store.PLAN), (early, early))
        link(first.root)
        run(first.root, account)
        devices = [first.root]
        for n in (1, 2):
            folder = base / f"d{n}"
            folder.mkdir(parents=True)
            link(folder, None)
            run(folder, account)
            devices.append(folder)
        second = 0
        for offset in range(3):
            day = MONDAY + timedelta(days=offset)
            for _ in range(12):
                root = rng.choice(devices)
                learner = store.Learner(root)
                catalog = Catalog(COURSES, learner=root)
                second += 1
                now = moment(day, second)
                roll = rng.random()
                dp = compute(learner, catalog, day)
                if roll < 0.55 and dp.sequence:
                    card = dp.sequence[0].card
                    given = correct(catalog, card) if rng.random() < 0.7 else "zzz"
                    session.answer(learner, catalog, day, now, card, given)
                elif roll < 0.65 and dp.book.cards:
                    card = rng.choice(sorted(dp.book.cards))
                    session.save_note(learner, catalog, card, now, f"notatka {second}")
                elif roll < 0.72 and dp.book.cards:
                    card = rng.choice(sorted(dp.book.cards))
                    session.flag(learner, catalog, card, now, skip=True, clear=rng.random() < 0.5)
                elif roll < 0.78:
                    text = f"das Testwort{second} = słowo testowe {second}"
                    preview = words.add_preview(learner, catalog, "de", text, now)
                    gate.commit(preview["token"], pending(learner), now, via="token")
                elif roll < 0.84:
                    setting = rng.choice(
                        [
                            f"new_per_day={rng.choice([3, 4, 5, 6])}",
                            f"lang.de.weight={rng.choice([1, 2])}",
                            f"lang.es.weight={rng.choice([1, 2])}",
                        ]
                    )
                    try:
                        preview = plans.set_preview(learner, Catalog(COURSES), [setting], now)
                    except VocabError:
                        continue
                    gate.commit(preview["token"], pending(learner), now, via="token")
                else:
                    run(root, account, now)
        for root in devices + devices:
            run(root, account, moment(MONDAY + timedelta(days=3), 0))
        last = MONDAY + timedelta(days=3)
        states = [state_of(root, last) for root in devices]
        assert states[0] == states[1] == states[2], f"seed {seed}"
        assert rows_of(account.root) == rows_of(devices[0])
        assert store.Learner(account.root).plan() == store.Learner(devices[0]).plan()
        for root in devices:
            assert sync.pending(root) == 0


def test_a_log_only_grows_on_both_sides(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    answer_some(one, MONDAY, 2)
    run(one.root, account)
    two = tmp_path / "two"
    two.mkdir()
    link(two, None)
    run(two, account)
    sides = (one.root, two, account.root)
    before = {root: (root / store.REVIEWS).read_bytes() for root in sides}
    answer_some(store.Learner(two), MONDAY, 2, start=50)
    for root in (two, one.root):
        run(root, account)
    for root in sides:
        assert (root / store.REVIEWS).read_bytes().startswith(before[root])


# ---------------------------------------------------------------- the commands


def test_login_needs_a_choice_when_the_plans_differ_and_logout_unlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    run(one.root, account)
    other = make_learner(tmp_path / "other", ["es:a1"])
    remote.save_credentials(
        "https://test",
        {"client_id": "c", "access_token": "a", "refresh_token": "r", "expires_at": 9e12},
    )
    monkeypatch.setattr(remote, "HttpTransport", lambda server, http=None, timeout=30: account)
    monkeypatch.setattr(remote, "revoke", lambda http, server: True)
    code = cli.main(["login", "https://test", "--learner", str(other.root), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["error"]["code"] == "choose_plan"
    assert out["error"]["details"]["account_plan"]
    code = cli.main(
        ["login", "https://test", "--learner", str(other.root), "--plan", "folder", "--json"]
    )
    preview = json.loads(capsys.readouterr().out)
    assert code == 0 and preview["token"]
    assert sync.link_state(other.root) is None  # nothing changes before the yes
    code = cli.main(["commit", "--confirm", preview["token"], "--learner", str(other.root)])
    capsys.readouterr()
    assert code == 0
    assert sync.link_state(other.root) is not None
    assert rows_of(account.root) == rows_of(other.root)
    assert store.Learner(account.root).plan()["languages"][0]["code"] == "es"
    status = cli.main(["status", "--learner", str(other.root), "--json"])
    shown = json.loads(capsys.readouterr().out)
    assert status == 0 and shown["sync"]["login"] == "ola" and shown["sync"]["pending"] == 0
    code = cli.main(["logout", "--learner", str(other.root), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["unlinked"] and out["revoked"]
    assert sync.link_state(other.root) is None
    assert remote.credentials("https://test") is None


def test_export_and_import_move_the_whole_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    one = make_learner(tmp_path / "one", ["de:a1"])
    answer_some(one, MONDAY, 4)
    catalog = Catalog(COURSES, learner=one.root)
    session.save_note(one, catalog, card_of("de", 1), moment(MONDAY, 99), "moja")
    archive = tmp_path / "record.zip"
    assert cli.main(["export", str(archive), "--learner", str(one.root), "--json"]) == 0
    capsys.readouterr()
    assert cli.main(["export", str(archive), "--learner", str(one.root), "--json"]) == 1
    capsys.readouterr()
    target = tmp_path / "copy"
    assert cli.main(["import", str(archive), "--learner", str(target), "--json"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert not (target / store.PLAN).exists()
    assert cli.main(["commit", "--confirm", preview["token"], "--learner", str(target)]) == 0
    capsys.readouterr()
    assert state_of(target, MONDAY) == state_of(one.root, MONDAY)
    # into a folder that has a plan, an import adds only the rows it lacks and keeps the plan
    other = make_learner(tmp_path / "other", ["de:a1"], new_per_day=3)
    data = archive.read_bytes()
    found = sync.import_preview(other.root, data, installed(), moment(MONDAY, 200))
    gate.commit(found["token"], pending(other), moment(MONDAY, 201), via="token")
    assert rows_of(other.root) == rows_of(one.root)
    assert store.Learner(other.root).plan()["new_per_day"] == 3
    with pytest.raises(VocabError) as again:
        sync.import_preview(other.root, data, installed(), moment(MONDAY, 202))
    assert again.value.code == "nothing_to_import"
    with pytest.raises(VocabError) as bad:
        sync.import_preview(other.root, b"not a zip", installed(), moment(MONDAY, 203))
    assert bad.value.code == "bad_archive"


class Busy:
    """A transport during whose exchange the session writes the next answer."""

    def __init__(self, account: Account, learner: store.Learner) -> None:
        self.account = account
        self.learner = learner
        self.calls = 0

    def exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            answer_some(self.learner, MONDAY, 1, start=500)
        return self.account.exchange(payload)


def test_an_answer_written_while_a_synchronisation_runs_is_sent_later(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    run(one.root, account)
    answer_some(one, MONDAY, 2)
    busy = Busy(account, store.Learner(one.root))
    sync.run(one.root, busy, moment(MONDAY, 600), installed, push_only=True)
    # the answer written during the exchange did not go, and it is not taken for sent
    assert sync.pending(one.root) == 1
    run(one.root, account)
    assert rows_of(account.root) == rows_of(one.root) and len(rows_of(one.root)) == 3


def test_lines_refused_for_a_passing_reason_go_again(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    account.now = moment(MONDAY) - timedelta(days=2)  # the account's clock is behind
    answer_some(one, MONDAY, 2)
    result = run(one.root, account)
    # the answers and the plan's rows are all ahead of the account's clock
    assert result["refused"] >= 2 and result["pending"] >= 2
    assert not rows_of(account.root)
    account.now = LATER
    result = run(one.root, account)
    assert result["pending"] == 0 and rows_of(account.root) == rows_of(one.root)


def test_a_day_that_does_not_exist_is_left_out(tmp_path: Path) -> None:
    from vocabbot.book import valid_row

    row = {
        "ts": "2026-11-16T12:00:00.000000Z",
        "day": "2026-11-16",
        "card": card_of("de", 1),
        "grade": "know",
    }
    assert valid_row(row)
    assert not valid_row({**row, "day": "2026-02-30"})
    assert not valid_row({**row, "day": "2026-11-16\n"})
    assert not valid_row({**row, "ts": "2026-11-16T25:00:00.000000Z"})
    learner = make_learner(tmp_path / "one", ["de:a1"])
    store.append_jsonl(learner.path(store.REVIEWS), {**row, "day": "2026-02-30"})
    answer_some(learner, MONDAY, 1)
    assert len(replay(store.Learner(learner.root).rows()[0]).cards) == 1


def test_changes_of_two_languages_on_two_devices_both_hold(tmp_path: Path) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1", "es:a1"])
    link(one.root)
    run(one.root, account)
    two = tmp_path / "two"
    two.mkdir()
    link(two, None)
    run(two, account)
    first = plans.set_preview(one, Catalog(COURSES), ["lang.es=paused"], moment(MONDAY, 10))
    gate.commit(first["token"], pending(one), moment(MONDAY, 11), via="token")
    other = store.Learner(two)
    second = plans.set_preview(other, Catalog(COURSES), ["lang.de.weight=3"], moment(MONDAY, 20))
    gate.commit(second["token"], pending(other), moment(MONDAY, 21), via="token")
    for root in (one.root, two, one.root):
        run(root, account, moment(MONDAY, 30))
    for root in (one.root, two, account.root):
        languages = {item["code"]: item for item in store.Learner(root).plan()["languages"]}
        assert languages["es"]["paused"] is True and languages["de"]["weight"] == 3


def test_rows_of_a_newer_version_keep_their_place(tmp_path: Path) -> None:
    row = {"ts": "2026-11-16T12:00:00.000000Z", "set": {"new_per_day": 7, "future_key": "x"}}
    assert plans.valid_history_row(row)
    assert plans.fold([row]) == {"new_per_day": 7}
    assert not plans.valid_history_row({**row, "set": {"languages": None}})
    assert not plans.valid_history_row({**row, "langs": {"de": {"code": "es", "levels": []}}})


def test_the_link_row_is_written_once_and_waits_for_a_full_synchronisation(
    tmp_path: Path,
) -> None:
    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root, "folder")
    account.offline = True
    for second in (1, 2):
        remote.auto(one.root, moment(MONDAY, second), installed, transport=account)
    links = [r for r in plans.history_rows(one.root) if r.get("from") == "link"]
    assert len(links) == 1
    account.offline = False
    skipped = sync.run(one.root, account, moment(MONDAY, 3), installed, push_only=True)
    assert skipped["skipped"] and (sync.link_state(one.root) or {}).get("first")
    run(one.root, account, moment(MONDAY, 4))
    assert "first" not in (sync.link_state(one.root) or {})
    assert len([r for r in plans.history_rows(account.root) if r.get("from") == "link"]) == 1


def test_conflict_copies_of_the_plan_and_many_copy_rows(tmp_path: Path) -> None:
    from vocabbot import doctor

    account = Account(tmp_path / "account")
    one = make_learner(tmp_path / "one", ["de:a1"])
    link(one.root)
    run(one.root, account)
    # a copy of the plan's history counts and does not hold back a change
    copy = one.path("log/plan (1).jsonl")
    store.append_jsonl(copy, {"ts": store.iso(moment(MONDAY, 1)), "set": {"days_off": ["sun"]}})
    assert any(r["set"].get("days_off") == ["sun"] for r in plans.history_rows(one.root))
    preview = plans.set_preview(one, Catalog(COURSES), ["new_per_day=7"], moment(MONDAY, 2))
    assert preview["token"]
    merged = doctor.merge_preview(one, moment(MONDAY, 3))
    assert any("plan" in line for line in merged["preview"])
    # a reviews copy longer than one request goes in full
    base = {"day": "2026-11-16", "card": card_of("de", 1), "lang": "de", "grade": "know"}
    reviews_copy = one.path("log/reviews (1).jsonl")
    for second in range(2500):
        stamp = store.iso(moment(MONDAY, 100) + timedelta(microseconds=second))
        store.append_jsonl(reviews_copy, {**base, "ts": stamp})
    run(one.root, account, moment(MONDAY, 4))
    assert len(rows_of(account.root)) == 2500
    # an export keeps the rows of copies
    from io import BytesIO
    from zipfile import ZipFile

    data = sync.archive(one.root, moment(MONDAY, 5))
    exported = ZipFile(BytesIO(data)).read(store.REVIEWS).decode("utf-8")
    assert len([line for line in exported.split("\n") if line]) == 2500


def test_a_new_plan_keeps_the_logs_a_folder_holds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "logs-only"
    row = {
        "ts": "2026-11-16T12:00:00.000000Z",
        "day": "2026-11-16",
        "card": card_of("de", 1),
        "lang": "de",
        "grade": "know",
    }
    store.append_jsonl(folder / store.REVIEWS, row)
    made = plans.init_preview(folder, ["de:a1"], 5, Catalog(COURSES), moment(MONDAY))
    gate.commit(made["token"], [store.config_dir() / "pending"], moment(MONDAY, 1), via="token")
    assert len(rows_of(folder)) == 1
    archive_from = make_learner(tmp_path / "source", ["de:a1"])
    data = sync.archive(archive_from.root, moment(MONDAY))
    empty_plan = tmp_path / "half"
    store.append_jsonl(empty_plan / store.REVIEWS, row)
    with pytest.raises(VocabError) as taken:
        sync.import_preview(empty_plan, data, installed(), moment(MONDAY))
    assert taken.value.code == "folder_not_empty"
    del capsys


def test_the_server_names_its_time_zone_exactly(tmp_path: Path) -> None:
    assert store.zone_problem("europe/warsaw") is not None
    assert store.zone_problem("Europe/Warsaw") is None


def test_a_folder_without_a_link_never_reaches_a_network(tmp_path: Path) -> None:
    one = make_learner(tmp_path / "one", ["de:a1"])
    assert remote.auto(one.root, moment(MONDAY), installed) is None
    assert remote.describe(one.root) is None
    assert sync.pending(one.root) == 0
    with pytest.raises(VocabError) as no_link:
        sync.run(one.root, Account(tmp_path / "account"), moment(MONDAY), installed)
    assert no_link.value.code == "not_linked"


def test_the_server_address_must_be_https_except_on_this_computer() -> None:
    assert remote.server_url("vocab.example.org") == "https://vocab.example.org"
    assert remote.server_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    for wrong in ("http://vocab.example.org", "https://x/path", "ftp://x", "https://u:p@x"):
        with pytest.raises(VocabError):
            remote.server_url(wrong)
