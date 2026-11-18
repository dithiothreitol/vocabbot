"""Stages 12 and 13 over HTTP: the program's sign-in, /sync, the account page, recovery and /app."""

from __future__ import annotations

import html
import io
import json
import re
import socket
import threading
import time
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

pytest.importorskip("mcp")

import httpx2
import uvicorn
from conftest import COURSES, correct, make_learner

from vocabbot import cli, gate, remote, session, store, sync
from vocabbot.book import replay
from vocabbot.courses import Catalog
from vocabbot.queue import compute
from vocabbot.server.accounts import Registry
from vocabbot.server.app import build
from vocabbot.server.config import Mail, Settings

PASSWORD = "correct horse battery"
CODE = re.compile(r"[A-Z2-9]{4}-[A-Z2-9]{4}")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Served:
    """A running server, its settings, its browser routes and the messages it sent."""

    def __init__(self, settings: Settings, app: Any, server: uvicorn.Server) -> None:
        self.settings = settings
        self.web = app.state.web
        self.server = server
        self.sent: list[tuple[str, str, str]] = []
        self.web.send_mail = lambda to, subject, body: self.sent.append((to, subject, body))
        self.registry = Registry(settings.database)

    @property
    def url(self) -> str:
        return self.settings.url


@pytest.fixture
def serve(tmp_path: Path) -> Iterator[Callable[..., Served]]:
    running: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start(name: str = "server", mail: Mail | None = None) -> Served:
        port = _free_port()
        settings = Settings(
            url=f"http://127.0.0.1:{port}",
            data=tmp_path / name,
            timezone="UTC",
            mail=mail or Mail(host="smtp.test", sender="vocabbot@test"),
        )
        app = build(settings)
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.time() + 20
        while not server.started:
            assert time.time() < deadline, "the server did not start"
            time.sleep(0.05)
        running.append((server, thread))
        return Served(settings, app, server)

    yield start
    for server, thread in running:
        server.should_exit = True
        thread.join(10)


def account(served: Served, login: str) -> str:
    """An account opened with an invitation, in the registry."""
    code = served.registry.create_invite()
    return served.registry.signup(login, PASSWORD, code, False).id


def browser(served: Served, login: str, *, email: str = "", signup: bool = True) -> httpx2.Client:
    """A browser signed in on /app/login (opening the account with an invitation)."""
    web = httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30)
    form = {"login": login, "password": PASSWORD, "tz": "Europe/Warsaw", "next": "/app/"}
    if signup:
        form.update(
            action="signup",
            password2=PASSWORD,
            invite=served.registry.create_invite(),
            email=email,
        )
    else:
        form["action"] = "login"
    done = web.post("/app/login", data=form)
    assert done.status_code == 303, done.text
    assert done.headers["location"] == "/app/"
    return web


def csrf(web: httpx2.Client) -> str:
    page = web.get("/app/")
    assert page.status_code == 200, page.text
    found = re.search(r'name="vocabbot-csrf" content="([0-9a-f]{32})"', page.text)
    assert found
    return found[1]


def api(web: httpx2.Client, token: str, name: str, body: dict[str, Any] | None = None) -> Any:
    if body is None:
        return web.get(f"/api/{name}").json()
    return web.post(f"/api/{name}", json=body, headers={"X-CSRF-Token": token}).json()


def program_login(served: Served, login: str) -> None:
    """The program signs in with a code, which the learner confirms on a phone (/device)."""
    shown: list[str] = []
    confirmed: list[bool] = []

    def sleep(_: float) -> None:
        if confirmed:
            return
        code = CODE.search(shown[-1])
        assert code, shown
        with httpx2.Client(base_url=served.url, timeout=30) as phone:
            page = phone.post(
                "/device", data={"code": code[0], "login": login, "password": PASSWORD}
            )
            assert page.status_code == 200 and "Program został połączony" in page.text, page.text
        confirmed.append(True)

    found = remote.login_device(served.url, remote.Http(), shown.append, sleep=sleep)
    remote.save_credentials(served.url, found)


def rows_of(root: Path) -> set[str]:
    return sync.keys_of(store.REVIEWS, sync.read_lines(root / store.REVIEWS))


def answer_some(learner: store.Learner, count: int) -> None:
    catalog = Catalog(COURSES, learner=learner.root)
    day = store.learning_day(session.now_utc(), 4, learner.zone())
    for _ in range(count):
        dp = compute(learner, catalog, day)
        if not dp.sequence:
            return
        card = dp.sequence[0].card
        session.answer(learner, catalog, day, session.now_utc(), card, correct(catalog, card))


# ---------------------------------------------------------------- the program's sign-in


def test_the_program_signs_in_in_the_browser_and_links_its_folder(
    serve: Callable[..., Served], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    served = serve()
    owner = account(served, "ola")
    learner = make_learner(tmp_path / "one", ["de:a1"], new_per_day=4)
    answer_some(learner, 3)

    def opener(address: str) -> bool:
        def walk() -> None:
            with httpx2.Client(follow_redirects=False, timeout=30) as page:
                first = page.get(address)
                assert first.status_code == 302, first.text
                target = first.headers["location"]
                request_id = parse_qs(urlsplit(target).query)["request"][0]
                done = page.post(
                    f"{served.url}/login",
                    data={
                        "request": request_id,
                        "action": "login",
                        "login": "ola",
                        "password": PASSWORD,
                        "tz": "Europe/Warsaw",
                    },
                )
                assert done.status_code == 303, done.text
                assert done.headers["location"].startswith("http://127.0.0.1:")
                back = page.get(done.headers["location"])
                assert "Zalogowano" in back.text

        threading.Thread(target=walk, daemon=True).start()
        return True

    shown: list[str] = []
    found = remote.login_browser(served.url, remote.Http(), shown.append, opener=opener)
    assert "/authorize?" in shown[0]
    remote.save_credentials(served.url, found)
    stored = (store.config_dir() / remote.CREDENTIALS).read_text("utf-8")
    assert found["refresh_token"] in stored
    assert served.registry.timezone(owner) == "Europe/Warsaw"
    # the folder links to the account after a preview and a yes
    code = cli.main(["login", served.url, "--learner", str(learner.root), "--json"])
    preview = json.loads(capsys.readouterr().out)
    assert code == 0 and preview["token"], preview
    assert any("na koncie 0" in line for line in preview["preview"])
    assert found["refresh_token"] not in json.dumps(preview)
    code = cli.main(["commit", "--confirm", preview["token"], "--learner", str(learner.root)])
    capsys.readouterr()
    assert code == 0
    folder = served.settings.learners / owner
    assert rows_of(folder) == rows_of(learner.root) and len(rows_of(folder)) == 3
    # the plan keeps the account's time zone from the browser
    assert store.Learner(learner.root).plan()["timezone"] == "Europe/Warsaw"
    names = [grant.name for grant in served.registry.grants(owner)]
    assert len(names) == 1 and names[0].startswith("Program VocabBot")
    # the same day in the browser: the counters agree with the folder's
    web = browser(served, "ola", signup=False)
    token = csrf(web)
    in_browser = api(web, token, "today")
    assert cli.main(["today", "--learner", str(learner.root), "--json"]) == 0
    in_folder = json.loads(capsys.readouterr().out)
    assert in_browser["counter"] == in_folder["counter"]
    assert in_folder["sync"]["login"] == "ola" and in_folder["sync"]["pending"] == 0
    # an answer in the browser reaches the folder before its next command
    item = api(web, token, "next")["items"][0]
    graded = api(web, token, "answer", {"card": item["card"], "answer": "nie wiem"})
    assert graded["results"][0]["grade"] == "dont_know"
    assert cli.main(["next", "--learner", str(learner.root), "--json"]) == 0
    capsys.readouterr()
    assert rows_of(learner.root) == rows_of(folder) and len(rows_of(folder)) == 4


def test_a_code_signs_the_program_in_and_a_new_computer_downloads_the_account(
    serve: Callable[..., Served], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    served = serve()
    owner = account(served, "kasia")
    web = browser(served, "kasia", signup=False)
    token = csrf(web)
    preview = api(web, token, "setup", {"languages": ["de:a1"], "new_per_day": 4})
    assert preview["ok"] and api(web, token, "commit", {"token": preview["token"]})["ok"]
    for _ in range(2):
        item = api(web, token, "next")["items"][0]
        api(web, token, "answer", {"card": item["card"], "answer": "x"})
    # a wrong code and a stranger are refused
    with httpx2.Client(base_url=served.url, timeout=30) as phone:
        wrong = phone.post(
            "/device", data={"code": "ABCD-EFGH", "login": "kasia", "password": PASSWORD}
        )
        assert wrong.status_code == 400 and "nieprawidłowy" in wrong.text
        refused = phone.post("/device/token", data={"grant_type": "x", "device_code": "y"})
        assert refused.json()["error"] == "unsupported_grant_type"
    program_login(served, "kasia")
    folder = tmp_path / "new"
    code = cli.main(["login", served.url, "--learner", str(folder), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["downloaded"], out
    assert rows_of(folder) == rows_of(served.settings.learners / owner)
    assert store.Learner(folder).plan()["languages"][0]["code"] == "de"
    # the pointer leads the next commands to the new folder
    assert cli.main(["status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["sync"]["login"] == "kasia"


def test_sync_refuses_strangers_and_keeps_accounts_apart(
    serve: Callable[..., Served], tmp_path: Path
) -> None:
    served = serve()
    account(served, "ola")
    with httpx2.Client(base_url=served.url, timeout=30) as web:
        anonymous = web.post("/sync", json={})
        assert anonymous.status_code == 401
        assert "resource_metadata" in anonymous.headers["www-authenticate"]
        forged = web.post("/sync", json={}, headers={"authorization": "Bearer nothing"})
        assert forged.status_code == 401
    program_login(served, "ola")
    learner = make_learner(tmp_path / "one", ["de:a1"])
    answer_some(learner, 2)
    sync.save_state(
        learner.root, {"server": served.url, "login": "ola", "first": {"plan_from": "folder"}}
    )
    transport = remote.HttpTransport(served.url)
    result = sync.run(learner.root, transport, session.now_utc(), Catalog(COURSES).installed)
    assert result["ok"] and result["sent"] >= 2
    with httpx2.Client(base_url=served.url, timeout=30) as web:
        access = remote.credentials(served.url)
        assert access is not None
        bearer = {"authorization": f"Bearer {access['access_token']}"}
        assert web.post("/sync", content=b"not json", headers=bearer).status_code == 400
    # another account sees nothing of the first one
    remote.save_credentials(served.url, None)
    account(served, "kasia")
    program_login(served, "kasia")
    found = sync.probe(remote.HttpTransport(served.url))
    assert found["plan"] is None and not found["streams"].get(store.REVIEWS)
    assert found["account"]["login"] == "kasia"


# ---------------------------------------------------------------- the account page


def test_the_account_page_lists_unlinks_exports_and_deletes(
    serve: Callable[..., Served], tmp_path: Path
) -> None:
    served = serve()
    web = browser(served, "ola", email="ola@example.org")
    token = csrf(web)
    owner = served.registry.find("ola")
    assert owner is not None and served.registry.has_email(owner.id)
    assert b"ola@example.org" not in served.settings.database.read_bytes()
    preview = api(web, token, "setup", {"languages": ["de:a1"], "new_per_day": 3})
    api(web, token, "commit", {"token": preview["token"]})
    item = api(web, token, "next")["items"][0]
    api(web, token, "answer", {"card": item["card"], "answer": "x"})
    program_login(served, "ola")
    page = web.get("/account")
    assert page.status_code == 200 and "Program VocabBot" in page.text
    assert "Content-Security-Policy" in page.headers
    grant = re.search(r'name="grant" value="([0-9a-f]+)"', page.text)
    assert grant
    # a form without its token changes nothing
    refused = web.post("/account", data={"action": "unlink", "grant": grant[1]})
    assert refused.status_code == 400 and "Program VocabBot" in web.get("/account").text
    foreign = web.post(
        "/account",
        data={"action": "unlink", "grant": grant[1], "csrf": token},
        headers={"origin": "https://evil.example.com"},
    )
    assert foreign.status_code == 400
    done = web.post("/account", data={"action": "unlink", "grant": grant[1], "csrf": token})
    assert done.status_code == 200 and "Program VocabBot" not in done.text
    folder = make_learner(tmp_path / "linked", ["de:a1"])
    sync.save_state(folder.root, {"server": served.url, "login": "ola"})
    failed = remote.auto(folder.root, session.now_utc(), Catalog(COURSES).installed)
    assert failed is not None and failed["error"]["code"] == "signed_out"
    # the data as a zip in the form of a learner's folder
    archive = web.get("/account/export")
    assert archive.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(archive.content)).namelist()
    assert store.PLAN in names and store.REVIEWS in names
    copy = tmp_path / "copy"
    now = session.now_utc()
    found = sync.import_preview(copy, archive.content, Catalog(COURSES).installed(), now)
    gate.commit(found["token"], [store.config_dir() / "pending"], now, via="token")
    assert rows_of(copy) == rows_of(served.settings.learners / owner.id)
    book = replay(store.Learner(copy).rows()[0])
    assert len(book.cards) == 1
    # the removal needs the password
    wrong = web.post("/account", data={"action": "delete", "password": "nope", "csrf": token})
    assert wrong.status_code == 400 and "Nieprawidłowe hasło" in wrong.text
    gone = web.post("/account", data={"action": "delete", "password": PASSWORD, "csrf": token})
    assert gone.status_code == 200 and "usunięte" in gone.text
    assert served.registry.find("ola") is None
    assert not (served.settings.learners / owner.id).exists()
    assert web.get("/api/today").status_code == 401


def test_password_recovery_by_an_optional_email(serve: Callable[..., Served]) -> None:
    served = serve()
    web = browser(served, "ola", email="Ola@example.org")
    program_login(served, "ola")
    owner = served.registry.find("ola")
    assert owner is not None and served.registry.grants(owner.id)
    anonymous = httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30)
    pages = []
    for login, address in (
        ("ola", "wrong@example.org"),
        ("nobody", "ola@example.org"),
        ("ola", "ola@example.org"),
    ):
        answer = anonymous.post("/recover", data={"login": login, "email": address})
        assert answer.status_code == 200
        pages.append(answer.text)
    # the page answers the same for every login and address
    assert pages[0] == pages[1] == pages[2]
    deadline = time.time() + 5
    while not served.sent and time.time() < deadline:
        time.sleep(0.05)
    assert len(served.sent) == 1
    to, subject, body = served.sent[0]
    assert to == "ola@example.org" and "VocabBot" in subject
    link = re.search(r"http://127\.0\.0\.1:\d+/recover/[\w-]+", body)
    assert link
    path = urlsplit(link[0]).path
    assert "Nowe hasło" in anonymous.get(path).text
    mismatch = anonymous.post(path, data={"password": "x" * 12, "password2": "y" * 12})
    assert mismatch.status_code == 400
    new = "a much better password"
    done = anonymous.post(path, data={"password": new, "password2": new})
    assert done.status_code == 200 and "Hasło zostało zmienione" in done.text
    assert anonymous.post(path, data={"password": new, "password2": new}).status_code == 400
    assert served.registry.verify("ola", new) is not None
    # the new password ended every connection and the browser's session
    assert served.registry.grants(owner.id) == []
    assert web.get("/api/today").status_code == 401
    assert b"ola@example.org" not in served.settings.database.read_bytes()


def test_a_server_without_mail_offers_no_recovery(serve: Callable[..., Served]) -> None:
    served = serve("plain", mail=Mail())
    with httpx2.Client(base_url=served.url, timeout=30) as web:
        page = web.get("/app/login")
        assert "Nie pamiętam hasła" not in page.text and 'name="email"' not in page.text
        assert "nie wysyła wiadomości" in web.get("/recover").text


# ---------------------------------------------------------------- the session page


def test_the_session_page_keeps_answers_back_and_logs_what_the_program_logs(
    serve: Callable[..., Served], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    served = serve()
    with httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30) as stranger:
        assert stranger.get("/app/").headers["location"].startswith("/app/login")
        assert stranger.get("/api/today").status_code == 401
        assert stranger.get("/app").status_code == 308
        manifest = stranger.get("/app/manifest.webmanifest").json()
        assert manifest["start_url"] == "/app/" and manifest["display"] == "standalone"
        worker = stranger.get("/app/sw.js")
        assert "/api/" in worker.text and worker.headers["service-worker-allowed"] == "/app/"
        assert "function" in stranger.get("/static/app.js").text
        assert stranger.get("/static/vocabbot.svg").headers["content-type"].startswith("image/svg")
        login_page = stranger.get("/app/login")
        assert "script-src 'sha256-" in login_page.headers["content-security-policy"]
    web = browser(served, "ola")
    page = web.get("/app/")
    policy = page.headers["content-security-policy"]
    assert "script-src 'self'" in policy and "media-src https://upload.wikimedia.org" in policy
    assert "VOCABBOT_LABELS" not in page.text and '"tab_session"' in page.text
    token = csrf(web)
    assert api(web, token, "me")["login"] == "ola"
    assert api(web, token, "today")["error"]["code"] == "no_account_plan"
    settings = ["new_words=ask", "answer_mode=type", "days_off=none"]
    preview = api(
        web, token, "setup", {"languages": ["de:a1"], "new_per_day": 4, "settings": settings}
    )
    assert preview["ok"] and api(web, token, "commit", {"token": preview["token"]})["ok"]
    # the same plan in a folder of the program
    folder = tmp_path / "folder"
    argv = ["init", str(folder), "--lang", "de:a1", "--new", "4", "--json"]
    for setting in settings:
        argv += ["--set", setting]
    assert cli.main(argv) == 0
    made = json.loads(capsys.readouterr().out)
    assert cli.main(["commit", "--confirm", made["token"], "--json"]) == 0
    capsys.readouterr()
    learner = store.Learner(folder)
    catalog = Catalog(COURSES, learner=folder)
    day = store.learning_day(session.now_utc(), 4, None)
    plain = Catalog(COURSES)
    given: list[str] = []
    for n in range(12):
        shown = api(web, token, "next")
        if not shown["items"]:
            break
        item = shown["items"][0]
        entry = plain.card(item["card"])
        assert entry is not None
        # a question never holds its word or a note
        assert "word" not in item and entry["display"] not in json.dumps(item["question"])
        answer = correct(plain, item["card"]) if n % 3 else "zzz"
        graded = api(web, token, "answer", {"card": item["card"], "answer": answer})
        assert graded["results"][0]["card"] == item["card"]
        session.answer(learner, catalog, day, session.now_utc(), item["card"], answer)
        given.append(item["card"])
    assert len(given) >= 6
    owner = served.registry.find("ola")
    assert owner is not None
    on_server = store.Learner(served.settings.learners / owner.id).rows()[0]
    in_folder = store.Learner(folder).rows()[0]

    def kept(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [(r["card"], r["grade"], r.get("kind"), r.get("error"), r["day"]) for r in rows]

    assert kept(on_server) == kept(in_folder)
    # writes need the session's token and the server's own origin
    refused = web.post("/api/answer", json={"card": given[0], "answer": "x"})
    assert refused.status_code == 403
    foreign = web.post(
        "/api/answer",
        json={"card": given[0], "answer": "x"},
        headers={"X-CSRF-Token": token, "origin": "https://evil.example.com"},
    )
    assert foreign.status_code == 403
    bad = web.post(
        "/api/answer", json={"card": "../x", "answer": ""}, headers={"X-CSRF-Token": token}
    )
    assert bad.status_code == 400
    # another account's browser sees nothing of the first one
    other = browser(served, "kasia")
    assert api(other, csrf(other), "today")["error"]["code"] == "no_account_plan"
    # the progress and the plan
    status = api(web, token, "status")
    assert status["ok"] and len(status["activity"]) == 84
    assert status["activity"][-1]["answers"] >= len(given)
    assert len(api(web, token, "forecast")["days"]) == 14
    change = api(web, token, "plan", {"settings": ["new_per_day=5"]})
    assert change["token"] and api(web, token, "commit", {"token": change["token"]})["ok"]
    assert api(web, token, "plan")["plan"]["new_per_day"] == 5
    # signing out ends the session
    out = web.post("/app/logout", data={"csrf": token})
    assert out.status_code == 303
    assert web.get("/api/today").status_code == 401


def test_a_folder_of_one_account_never_joins_another(
    serve: Callable[..., Served], tmp_path: Path
) -> None:
    served = serve()
    account(served, "ola")
    second = account(served, "kasia")
    program_login(served, "ola")
    learner = make_learner(tmp_path / "one", ["de:a1"])
    answer_some(learner, 2)
    sync.save_state(
        learner.root, {"server": served.url, "login": "ola", "first": {"plan_from": "folder"}}
    )
    result = sync.run(
        learner.root,
        remote.HttpTransport(served.url),
        session.now_utc(),
        Catalog(COURSES).installed,
    )
    assert result["ok"]
    # the computer signs in to another account; the folder stays the first one's
    remote.save_credentials(served.url, None)
    program_login(served, "kasia")
    before = (learner.root / store.REVIEWS).read_bytes()
    failed = remote.auto(learner.root, session.now_utc(), Catalog(COURSES).installed)
    assert failed is not None and failed["error"]["code"] == "other_account"
    assert not (served.settings.learners / second / store.REVIEWS).exists()
    assert (learner.root / store.REVIEWS).read_bytes() == before


def test_the_recovery_address_changes_only_with_the_password(
    serve: Callable[..., Served],
) -> None:
    served = serve()
    web = browser(served, "ola")
    token = csrf(web)
    owner = served.registry.find("ola")
    assert owner is not None and not served.registry.has_email(owner.id)
    page = web.get("/account").text
    assert 'id="email-password"' in page
    refused = web.post(
        "/account", data={"action": "email", "email": "x@example.org", "csrf": token}
    )
    assert refused.status_code == 400 and not served.registry.has_email(owner.id)
    saved = web.post(
        "/account",
        data={"action": "email", "email": "x@example.org", "password": PASSWORD, "csrf": token},
    )
    assert saved.status_code == 200 and served.registry.has_email(owner.id)
    removed = web.post(
        "/account", data={"action": "email_remove", "password": PASSWORD, "csrf": token}
    )
    assert removed.status_code == 200 and not served.registry.has_email(owner.id)


def test_the_server_refuses_a_time_zone_spelled_otherwise(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone"):
        Settings(url="http://127.0.0.1:9", data=tmp_path, timezone="europe/warsaw")
    assert Settings(url="http://127.0.0.1:9", data=tmp_path, timezone="UTC").timezone == "UTC"


# ---------------------------------------------------------------- the pages in two languages


def test_the_pages_language_follows_the_switch_the_cookie_and_the_browser() -> None:
    from vocabbot.server import pages

    assert pages.accepted("") == "pl"
    assert pages.accepted("en-US,en;q=0.9,pl;q=0.8") == "en"
    assert pages.accepted("pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7") == "pl"
    assert pages.accepted("de-DE,de;q=0.9,en;q=0.5") == "en"
    assert pages.accepted("de, fr;q=0.8") == "pl"
    assert pages.accepted("en;q=0, pl;q=0.1") == "pl"
    assert pages.accepted("en;q=nonsense") == "pl"
    # the switch keeps the page's own query
    loc = pages.Locale("pl", "/app/login?next=%2Faccount")
    assert loc.link("en") == "/app/login?next=%2Faccount&lang=en"
    assert pages.Locale("en", "/").link("pl") == "/?lang=pl"


def test_every_text_of_the_pages_has_its_english_version() -> None:
    from vocabbot import assets

    polish = assets.read_json(assets.data_root() / "i18n" / "pl.json")["server"]
    english = assets.read_json(assets.data_root() / "i18n" / "en.json")["server"]
    # the card, the session page and the errors of /api speak Polish like the course;
    # the conversation in the start page's picture is the Polish one in both languages
    skipped = {"card", "app", "api_errors", "mock"}
    missing: list[str] = []

    def walk(one: Any, other: Any, path: str) -> None:
        if isinstance(one, dict):
            for key, value in one.items():
                if not path and key in skipped:
                    continue
                if not isinstance(other, dict) or key not in other:
                    missing.append(path + key)
                else:
                    walk(value, other[key], f"{path}{key}.")
        elif isinstance(one, list):
            if not isinstance(other, list) or len(other) != len(one):
                missing.append(path.rstrip("."))
            else:
                for index, (a, b) in enumerate(zip(one, other, strict=True)):
                    walk(a, b, f"{path}{index}.")
        elif isinstance(one, str):
            fields = set(re.findall(r"\{(\w+)\}", one))
            if not isinstance(other, str) or set(re.findall(r"\{(\w+)\}", other)) != fields:
                missing.append(path.rstrip("."))

    walk(polish, english, "")
    assert missing == []
    assert set(english) - set(polish) == set()
    for texts in (polish, english):
        assert len(texts["privacy"]) == len(texts["privacy_headings"])


def test_the_pages_speak_polish_or_english(serve: Callable[..., Served]) -> None:
    served = serve()
    with httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30) as web:
        home = web.get("/")
        assert home.headers["content-language"] == "pl" and '<html lang="pl">' in home.text
        assert "Poszerzaj słownictwo" in home.text
        assert "vocabbot_lang" not in home.headers.get("set-cookie", "")
        english = web.get("/", params={"lang": "en"})
        assert english.headers["content-language"] == "en" and '<html lang="en">' in english.text
        assert "Grow your vocabulary" in english.text and served.settings.resource in english.text
        assert "vocabbot_lang=en" in english.headers["set-cookie"]
        assert 'hreflang="pl"' in english.text and 'aria-current="true">EN<' in english.text
        # the cookie keeps the choice on the next pages
        assert "Sign in to VocabBot" in web.get("/app/login").text
        assert "Data the server stores" in web.get("/privacy").text
        back = web.get("/app/login", params={"next": "/account", "lang": "pl"})
        assert "Zaloguj się do VocabBota" in back.text
        assert 'href="/app/login?next=%2Faccount&amp;lang=en"' in back.text
    with httpx2.Client(
        base_url=served.url, timeout=30, headers={"Accept-Language": "en-GB,en;q=0.9"}
    ) as browser_en:
        page = browser_en.get("/recover")
        assert "Reset your password" in page.text and page.headers["content-language"] == "en"
        # the sheet of styles is cached under its digest; the pages run no inline style
        style = re.search(r'href="(/static/site\.css\?v=[0-9a-f]{12})"', page.text)
        assert style
        sheet = browser_en.get(style[1])
        assert sheet.headers["content-type"].startswith("text/css")
        assert "immutable" in sheet.headers["cache-control"] and ".btn.primary" in sheet.text
        policy = page.headers["content-security-policy"]
        assert "style-src 'self'" in policy and "unsafe-inline" not in policy


def test_the_start_page_tells_search_engines_and_models_what_vocabbot_is(
    serve: Callable[..., Served],
) -> None:
    import base64
    import hashlib

    served = serve()
    site = served.url
    with httpx2.Client(base_url=site, follow_redirects=False, timeout=30) as web:
        polish, english = web.get("/"), web.get("/", params={"lang": "en"})
        for page, here, lang in ((polish, f"{site}/", "pl"), (english, f"{site}/?lang=en", "en")):
            text = page.text
            assert f'<link rel="canonical" href="{here}">' in text
            assert f'<link rel="alternate" hreflang="x-default" href="{site}/">' in text
            assert f'hreflang="en" href="{site}/?lang=en"' in text
            assert '<meta name="robots" content="index, follow' in text
            assert f'<meta property="og:image" content="{site}/static/social-{lang}.png">' in text
            assert '<meta name="twitter:card" content="summary_large_image">' in text
            # every inline script runs under its hash in the Content-Security-Policy
            policy = page.headers["content-security-policy"]
            scripts = re.findall(r"<script>(.*?)</script>", text, re.S)
            assert len(scripts) == 2
            for script in scripts:
                digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                assert f"'sha256-{digest}'" in policy
            # schema.org data: the program and the questions shown on the page
            found = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            assert found and "<" not in found[1]
            graph = {node["@type"]: node for node in json.loads(found[1])["@graph"]}
            assert {"Organization", "WebSite", "WebPage", "SoftwareApplication", "FAQPage"} <= set(
                graph
            )
            assert graph["SoftwareApplication"]["applicationCategory"] == "EducationalApplication"
            assert graph["WebPage"]["inLanguage"] == lang
            questions = graph["FAQPage"]["mainEntity"]
            assert len(questions) >= 8
            for question in questions:
                assert html.escape(question["name"], quote=False) in text
            # the courses' numbers come from the installed courses
            from vocabbot.server import pages

            assert f'data-count="{len(pages.course_sizes())}"' in text
            assert 'id="faq"' in text and 'id="languages"' in text
        assert "Najczęstsze pytania" in polish.text and "Frequently asked questions" in english.text
        # a page behind a sign-in stays out of the index
        assert '<meta name="robots" content="noindex' in web.get("/app/login").text
        privacy = web.get("/privacy", params={"lang": "en"}).text
        assert f'<link rel="canonical" href="{site}/privacy?lang=en">' in privacy
        assert '"BreadcrumbList"' in privacy

        robots = web.get("/robots.txt")
        assert robots.headers["content-type"].startswith("text/plain")
        for line in ("User-agent: *", "User-agent: GPTBot", "User-agent: ClaudeBot", "Allow: /"):
            assert line in robots.text
        for path in ("/app/", "/account", "/api/", "/mcp", "/login"):
            assert f"Disallow: {path}\n" in robots.text
        assert f"Sitemap: {site}/sitemap.xml" in robots.text

        sitemap = web.get("/sitemap.xml")
        assert sitemap.headers["content-type"].startswith("application/xml")
        from xml.etree import ElementTree

        tree = ElementTree.fromstring(sitemap.content)
        spaces = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        listed = [node.text for node in tree.findall("s:url/s:loc", spaces)]
        assert listed == [
            f"{site}/",
            f"{site}/?lang=en",
            f"{site}/privacy",
            f"{site}/privacy?lang=en",
        ]

        summary = web.get("/llms.txt")
        assert summary.headers["content-type"].startswith("text/markdown")
        assert summary.text.startswith("# VocabBot\n\n> ")
        assert (
            served.settings.resource in summary.text
            and "## Frequently asked questions" in summary.text
        )
        assert "| Language |" in summary.text

        for lang in ("pl", "en"):
            picture = web.get(f"/static/social-{lang}.png")
            assert picture.headers["content-type"] == "image/png"
            assert picture.content[:8] == b"\x89PNG\r\n\x1a\n"
            # the width and the height in the PNG header: 1200 by 630
            assert picture.content[16:24] == (1200).to_bytes(4, "big") + (630).to_bytes(4, "big")


def test_the_recovery_message_speaks_the_language_of_the_page(
    serve: Callable[..., Served],
) -> None:
    served = serve()
    browser(served, "ola", email="ola@example.org")
    with httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30) as web:
        sent = web.post(
            "/recover",
            params={"lang": "en"},
            data={"login": "ola", "email": "ola@example.org"},
        )
        assert sent.status_code == 200 and "the link has been sent" in sent.text
        deadline = time.time() + 5
        while not served.sent and time.time() < deadline:
            time.sleep(0.05)
        to, subject, body = served.sent[0]
        assert to == "ola@example.org" and subject == "VocabBot: set a new password"
        assert "received a request to set a new password" in body
        link = re.search(r"http://127\.0\.0\.1:\d+/recover/[\w-]+\?lang=en", body)
        assert link
        page = web.get(urlsplit(link[0]).path + "?lang=en")
        assert "Set a new password for the account ola" in page.text


def test_the_sign_in_of_a_chat_application_speaks_english(serve: Callable[..., Served]) -> None:
    served = serve()
    redirect = "http://localhost:3030/callback"
    with httpx2.Client(base_url=served.url, follow_redirects=False, timeout=30) as web:
        client = web.post(
            "/register", json={"client_name": "Test client", "redirect_uris": [redirect]}
        ).json()
        authorize = web.get(
            "/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": redirect,
                "response_type": "code",
                "code_challenge": "x" * 43,
                "code_challenge_method": "S256",
                "state": "s1",
                "resource": served.settings.resource,
            },
        )
        request_id = parse_qs(urlsplit(authorize.headers["location"]).query)["request"][0]
        page = web.get("/login", params={"request": request_id, "lang": "en"})
        assert page.status_code == 200 and "Connect VocabBot to Test client" in page.text
        # a refused password keeps the language and the switch keeps the request
        wrong = web.post(
            "/login",
            data={"request": request_id, "action": "login", "login": "ola", "password": "x" * 12},
        )
        assert wrong.status_code == 400 and "Incorrect username or password" in wrong.text
        assert f'href="/login?request={request_id}&amp;lang=pl"' in wrong.text
        assert "Link has expired" not in web.get("/login", params={"request": "nothing"}).text
        assert "The link has expired" in web.get("/login", params={"request": "nothing"}).text
