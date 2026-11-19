"""End to end: a server process, the program as processes on two computers, and a phone.

The server and the program run as separate processes on the packaged courses,
as a learner meets them: the phone opens an account and learns on the session
page, the first computer signs in with a code confirmed on the phone and
downloads the account, the second computer links a folder with its own
answers and takes the account's plan, and every side ends with the same log.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")

import httpx2

import vocabbot as vocabbot_package
from vocabbot import families, store, sync
from vocabbot.courses import Catalog

PASSWORD = "correct horse battery"
CODE = re.compile(r"[A-Z2-9]{4}-[A-Z2-9]{4}")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _env(config: Path) -> dict[str, str]:
    """A computer of its own: its config folder, the packaged courses, no shared pointer."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("VOCABBOT_")}
    env.update(VOCABBOT_CONFIG=str(config), VOCABBOT_FSYNC="0", PYTHONUTF8="1")
    return env


@pytest.fixture
def server(tmp_path: Path) -> Iterator[dict[str, Any]]:
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    data = tmp_path / "server"
    env = _env(tmp_path / "server-config")
    command = [sys.executable, "-m", "vocabbot.server.cli", "--data", str(data)]
    process = subprocess.Popen(
        [*command, "serve", "--url", url, "--port", str(port), "--timezone", "Europe/Warsaw"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 60
        while True:
            try:
                if httpx2.get(f"{url}/health", timeout=2).status_code == 200:
                    break
            except httpx2.HTTPError:
                pass
            assert time.time() < deadline, "the server did not start"
            time.sleep(0.2)
        invite = subprocess.run(
            [*command, "invite", "--note", "e2e"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        yield {"url": url, "data": data, "invite": invite}
    finally:
        process.terminate()
        process.wait(20)


def vocabbot(config: Path, *args: str, stdin: str = "") -> dict[str, Any]:
    """The program on one computer, with --json; its output as a dict."""
    done = subprocess.run(
        [sys.executable, "-m", "vocabbot", *args, "--json"],
        env=_env(config),
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    try:
        out: dict[str, Any] = json.loads(done.stdout)
    except ValueError:
        raise AssertionError(f"{args}: {done.stdout}\n{done.stderr}") from None
    return out


def login_with_code(config: Path, phone: httpx2.Client, *args: str) -> dict[str, Any]:
    """`vocabbot login --code`: the program shows a code, the phone confirms it on /device."""
    process = subprocess.Popen(
        [sys.executable, "-m", "vocabbot", "login", *args, "--code", "--json"],
        env=_env(config),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stderr is not None and process.stdout is not None
    shown: list[str] = []
    found: list[str] = []

    def read() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            shown.append(line)
            match = CODE.search(line)
            if match and not found:
                found.append(match[0])

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.time() + 60
    while not found:
        assert time.time() < deadline and process.poll() is None, "".join(shown)
        time.sleep(0.1)
    page = phone.get("/device", params={"code": found[0]})
    token = re.search(r'name="csrf" value="([0-9a-f]+)"', page.text)
    assert page.status_code == 200 and token, page.text
    confirmed = phone.post("/device", data={"code": found[0], "csrf": token[1]})
    assert confirmed.status_code == 200 and "Program został połączony" in confirmed.text, (
        confirmed.text
    )
    out, _ = process.communicate(timeout=120)
    assert process.returncode == 0, out + "".join(shown)
    result: dict[str, Any] = json.loads(out)
    return result


def api(phone: httpx2.Client, csrf: str, name: str, body: dict[str, Any] | None = None) -> Any:
    if body is None:
        return phone.get(f"/api/{name}").json()
    return phone.post(f"/api/{name}", json=body, headers={"X-CSRF-Token": csrf}).json()


def learn_in_browser(phone: httpx2.Client, csrf: str, count: int) -> None:
    """Answers on the phone: "pokaż", then the learner's own grade."""
    for n in range(count):
        item = api(phone, csrf, "next")["items"][0]
        shown = api(phone, csrf, "reveal", {"card": item["card"]})
        assert shown["word"]["word"]
        grade = "dont_know" if n % 2 else "know"
        assert api(phone, csrf, "grade", {"card": item["card"], "grade": grade})["ok"]


def learn_in_terminal(config: Path, folder: Path, count: int) -> list[str]:
    cards = []
    for _ in range(count):
        item = vocabbot(config, "next", "--learner", str(folder))["items"][0]
        card = item["card"]
        assert "word" not in item
        assert vocabbot(config, "reveal", "--card", card, "--learner", str(folder))["ok"]
        graded = vocabbot(
            config, "grade", "--card", card, "--grade", "almost", "--learner", str(folder)
        )
        assert graded["ok"], graded
        cards.append(card)
    return cards


def rows_of(root: Path) -> set[str]:
    return sync.keys_of(store.REVIEWS, sync.read_lines(root / store.REVIEWS))


def test_a_learner_moves_between_a_phone_and_two_computers(
    server: dict[str, Any], tmp_path: Path
) -> None:
    url = server["url"]
    # the phone: an account with an invitation, a plan, three answers on the session page
    phone = httpx2.Client(base_url=url, follow_redirects=False, timeout=60)
    opened = phone.post(
        "/app/login",
        data={
            "action": "signup",
            "login": "ola",
            "password": PASSWORD,
            "password2": PASSWORD,
            "invite": server["invite"],
            "tz": "Europe/Warsaw",
            "next": "/app/",
        },
    )
    assert opened.status_code == 303, opened.text
    csrf = re.search(r'name="vocabbot-csrf" content="([0-9a-f]+)"', phone.get("/app/").text)
    assert csrf
    token = csrf[1]
    preview = api(phone, token, "setup", {"languages": ["de:a1-a2", "es:a1"], "new_per_day": 6})
    assert preview["ok"], preview
    assert any("Europe/Warsaw" in line for line in preview["preview"])
    assert api(phone, token, "commit", {"token": preview["token"]})["ok"]
    learn_in_browser(phone, token, 3)
    on_phone = api(phone, token, "today")
    account_folder = next((server["data"] / "learners").iterdir())

    # the first computer: a code confirmed on the phone, the account downloaded
    one = tmp_path / "computer-one"
    folder_one = tmp_path / "VocabBot-one"
    linked = login_with_code(one, phone, url, "--learner", str(folder_one))
    assert linked["downloaded"] and linked["login"] == "ola"
    today_one = vocabbot(one, "today")  # the pointer leads to the new folder
    assert today_one["counter"] == on_phone["counter"]
    assert today_one["sync"]["pending"] == 0
    # the session goes on in the terminal at the card the phone would show next
    next_on_phone = api(phone, token, "next")["items"][0]["card"]
    cards = learn_in_terminal(one, folder_one, 2)
    assert cards[0] == next_on_phone
    assert api(phone, token, "today")["counter"] == vocabbot(one, "today")["counter"]

    # the second computer: its own folder and answers, linked with the account's plan
    two = tmp_path / "computer-two"
    folder_two = tmp_path / "VocabBot-two"
    made = vocabbot(two, "init", str(folder_two), "--lang", "it:a1", "--new", "4")
    assert vocabbot(two, "commit", "--confirm", made["token"])["ok"]
    learn_in_terminal(two, folder_two, 2)
    preview = login_with_code(two, phone, url, "--learner", str(folder_two), "--plan", "account")
    assert preview["token"] and any("plan konta" in line for line in preview["preview"])
    committed = vocabbot(two, "commit", "--confirm", preview["token"], "--learner", str(folder_two))
    assert committed["ok"] and committed["sync"]["ok"], committed
    plan_two = vocabbot(two, "plan", "show", "--learner", str(folder_two))["plan"]
    assert [item["code"] for item in plan_two["languages"]] == ["de", "es"]
    assert plan_two["timezone"] == "Europe/Warsaw"

    # the first computer takes the second one's rows; every side has the same log
    assert vocabbot(one, "sync", "--learner", str(folder_one))["received"] >= 2
    assert rows_of(folder_one) == rows_of(folder_two) == rows_of(account_folder)
    assert len(rows_of(account_folder)) == 3 + 2 + 2
    counters = {
        vocabbot(one, "today")["counter"],
        vocabbot(two, "today", "--learner", str(folder_two))["counter"],
        api(phone, token, "today")["counter"],
    }
    assert len(counters) == 1, counters

    # the account page: the data as a zip, opened as a third folder
    archive = phone.get("/account/export")
    assert archive.status_code == 200
    zipped = tmp_path / "record.zip"
    zipped.write_bytes(archive.content)
    three = tmp_path / "computer-three"
    folder_three = tmp_path / "VocabBot-three"
    imported = vocabbot(three, "import", str(zipped), "--learner", str(folder_three))
    assert vocabbot(three, "commit", "--confirm", imported["token"])["ok"]
    assert rows_of(folder_three) == rows_of(account_folder)

    # signing out ends the first computer's connection; the account page lists one program
    page = phone.get("/account").text
    assert page.count("Program VocabBot") == 2
    out = vocabbot(one, "logout", "--learner", str(folder_one))
    assert out["revoked"] and out["unlinked"]
    assert phone.get("/account").text.count("Program VocabBot") == 1
    assert "sync" not in vocabbot(one, "today", "--learner", str(folder_one))


PACKAGED = Path(vocabbot_package.__file__).parent / "data" / "courses"


def test_a_family_moves_between_the_phone_and_two_computers(
    server: dict[str, Any], tmp_path: Path
) -> None:
    """S6 of Stage 14: Spanish and Italian by families on a phone and two computers."""
    url = server["url"]
    courses = Catalog(PACKAGED)
    phone = httpx2.Client(base_url=url, follow_redirects=False, timeout=60)
    opened = phone.post(
        "/app/login",
        data={
            "action": "signup",
            "login": "ola",
            "password": PASSWORD,
            "password2": PASSWORD,
            "invite": server["invite"],
            "tz": "Europe/Warsaw",
            "next": "/app/",
        },
    )
    assert opened.status_code == 303, opened.text
    csrf = re.search(r'name="vocabbot-csrf" content="([0-9a-f]+)"', phone.get("/app/").text)
    assert csrf
    token = csrf[1]
    settings = ["together=es,it", "new_words=show", "answer_mode=type"]
    preview = api(
        phone,
        token,
        "setup",
        {"languages": ["es:a1", "it:a1"], "new_per_day": 6, "settings": settings},
    )
    assert preview["ok"], preview
    assert api(phone, token, "commit", {"token": preview["token"]})["ok"]
    assert api(phone, token, "today")["together"]["languages"] == ["es", "it"]

    # the phone starts a block: the first card of a family
    first = api(phone, token, "next")["items"][0]["card"]
    word = courses.card(first)
    assert word is not None
    graded = api(phone, token, "answer", {"card": first, "answer": word["display"]})
    assert graded["results"][0]["grade"] == "know"
    account_folder = next((server["data"] / "learners").iterdir())

    # the first computer downloads the account and finishes the same block in the terminal
    one = tmp_path / "computer-one"
    folder_one = tmp_path / "VocabBot-one"
    assert login_with_code(one, phone, url, "--learner", str(folder_one))["downloaded"]
    second = vocabbot(one, "next", "--learner", str(folder_one))["items"][0]["card"]
    assert second[:2] != first[:2] and second[2:] == first[2:]  # the same family
    other = courses.card(second)
    assert other is not None
    done = vocabbot(
        one, "answer", "--card", second, "--learner", str(folder_one), stdin=other["display"]
    )
    assert done["grade"] == "know"
    family = done["family"]["rows"]
    assert family == [
        {
            "lang": first[:2],
            "card": first,
            "word": word["display"],
            "parts": family[0]["parts"],
        }
    ]

    # the second computer types the word of the other language of the next family
    two = tmp_path / "computer-two"
    folder_two = tmp_path / "VocabBot-two"
    assert login_with_code(two, phone, url, "--learner", str(folder_two))["downloaded"]
    shown = vocabbot(two, "next", "--learner", str(folder_two))["items"]
    card = shown[0]["card"]
    entry = courses.card(card)
    assert entry is not None
    sibling = next(
        e
        for e in courses.family(entry["concept"])
        if e["lang"] not in (card[:2],) and e["lang"] in ("es", "it")
    )
    slip = vocabbot(
        two, "answer", "--card", card, "--learner", str(folder_two), stdin=sibling["display"]
    )
    identical = families.shape(entry["display"], sibling["display"]) == "identical"
    if identical:
        assert slip["grade"] == "know", slip
    else:
        assert slip["other_lang"] == sibling["lang"], slip

    # every side ends with the same log and the same day; the phone sees the mix-up
    assert vocabbot(one, "sync", "--learner", str(folder_one))["ok"]
    assert vocabbot(two, "sync", "--learner", str(folder_two))["ok"]
    assert vocabbot(one, "sync", "--learner", str(folder_one))["ok"]
    assert rows_of(folder_one) == rows_of(folder_two) == rows_of(account_folder)
    assert len(rows_of(account_folder)) == 3
    counters = {
        vocabbot(one, "today", "--learner", str(folder_one))["counter"],
        vocabbot(two, "today", "--learner", str(folder_two))["counter"],
        api(phone, token, "today")["counter"],
    }
    assert len(counters) == 1, counters
    status = api(phone, token, "status")
    assert status["families"]["together"] == ["es", "it"]
    if not identical:
        mixed = sum(
            lang["mixups_30"]["hard"] + lang["mixups_30"]["near"]
            for lang in status["languages"].values()
        )
        assert mixed == 1
        assert status["languages"][card[:2]]["confusions"][0]["card"] == card
