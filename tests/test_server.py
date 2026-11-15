"""The remote server: accounts, OAuth, the tools over HTTP, and the engine for many accounts."""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("mcp")

import anyio
import httpx2
import uvicorn
from conftest import COURSES, correct
from mcp import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)
from pydantic import AnyUrl

from vocabbot import plans, store
from vocabbot.courses import Catalog
from vocabbot.server import guides
from vocabbot.server.accounts import Registry, SignupError, check_password
from vocabbot.server.app import Tools, build, register
from vocabbot.server.config import Settings
from vocabbot.server.oauth import Throttle
from vocabbot.server.service import Service

PASSWORD = "correct horse battery"
REDIRECT = "http://localhost:3030/callback"


# ---------------------------------------------------------------- accounts


def test_signup_takes_one_use_of_an_invitation(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "accounts.db")
    code = registry.create_invite(uses=1, days=1, note="Ola")
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", code)
    account = registry.signup("Ola.K", PASSWORD, code.lower().replace("-", " "), False)
    assert account.login == "ola.k"
    with pytest.raises(SignupError) as used:
        registry.signup("ola2", PASSWORD, code, False)
    assert used.value.code == "bad_invite"
    with pytest.raises(SignupError) as missing:
        registry.signup("ola3", PASSWORD, None, False)
    assert missing.value.code == "bad_invite"
    assert registry.signup("ola4", PASSWORD, None, True).login == "ola4"
    with pytest.raises(SignupError) as taken:
        registry.signup("OLA.K", PASSWORD, None, True)
    assert taken.value.code == "login_taken"
    for login, password, reason in (
        ("ab", PASSWORD, "bad_login"),
        ("ola5", "short", "bad_password"),
    ):
        with pytest.raises(SignupError) as refused:
            registry.signup(login, password, None, True)
        assert refused.value.code == reason
    assert registry.verify("ola.k", PASSWORD) == account
    assert registry.verify("ola.k", PASSWORD + "!") is None
    assert registry.verify("nobody", PASSWORD) is None
    assert [invite.uses for invite in registry.invites()] == [0]


def test_secrets_are_kept_only_as_hashes(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "accounts.db")
    code = registry.create_invite()
    registry.signup("ola", PASSWORD, code, False)
    request_id = registry.save_request("client", "{}", 60)
    raw = (tmp_path / "accounts.db").read_bytes()
    for secret in (PASSWORD, code.replace("-", ""), request_id):
        assert secret.encode() not in raw
    stored = raw.decode("latin-1")
    assert "scrypt$16384$8$1$" in stored
    assert not check_password(PASSWORD, "scrypt$broken")


def test_a_new_password_ends_the_connections(tmp_path: Path) -> None:
    from vocabbot.server.accounts import TokenRow

    registry = Registry(tmp_path / "accounts.db")
    account = registry.signup("ola", PASSWORD, None, True)
    row = TokenRow("access", "client", account.id, ["vocab"], None, "g1", time.time() + 60)
    registry.save_token("token-1", row)
    assert registry.token("token-1", "access") == row
    registry.set_password(account.id, PASSWORD + "2")
    assert registry.token("token-1", "access") is None
    assert registry.verify("ola", PASSWORD + "2") is not None
    registry.delete_account(account.id)
    assert registry.find("ola") is None


def test_throttle_blocks_after_repeated_failures() -> None:
    throttle = Throttle()
    for _ in range(Throttle.PER_LOGIN):
        throttle.fail("10.0.0.1", "Ola", now=1000.0)
    assert throttle.blocked("10.0.0.2", "ola", now=1001.0)
    assert not throttle.blocked("10.0.0.2", "kasia", now=1001.0)
    assert not throttle.blocked("10.0.0.2", "ola", now=1000.0 + Throttle.WINDOW + 1)


# ---------------------------------------------------------------- settings


def test_redirects_go_only_to_chat_applications_and_loopback(tmp_path: Path) -> None:
    settings = Settings(url="https://vocab.example.org/", data=tmp_path)
    assert settings.url == "https://vocab.example.org"
    assert settings.resource == "https://vocab.example.org/mcp"
    allowed = (
        "https://claude.ai/api/mcp/auth_callback",
        "https://claude.com/api/mcp/auth_callback",
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "http://localhost:3030/callback",
        "http://127.0.0.1:8123/cb",
    )
    refused = (
        "https://evil.example.com/cb",
        "https://claude.ai.evil.example.com/cb",
        "https://" + "user" + "@claude.ai/cb",
        "https://claude.ai@example.com/cb",
        "http://claude.ai/cb",
        "https://claude.ai:8443/cb",
        "javascript:alert(1)",
    )
    assert all(settings.redirect_allowed(uri) for uri in allowed)
    assert not any(settings.redirect_allowed(uri) for uri in refused)
    for url in ("http://vocab.example.org", "https://vocab.example.org/mcp", "ftp://x"):
        with pytest.raises(ValueError, match="server address"):
            Settings(url=url, data=tmp_path)


# ---------------------------------------------------------------- the engine changes


def test_a_catalog_on_a_base_shares_the_courses_and_adds_own_words(tmp_path: Path) -> None:
    own = tmp_path / "courses" / "de" / "own.jsonl"
    store.append_jsonl(
        own,
        {
            "id": "de-u00a1b2",
            "concept": "c90001",
            "lang": "de",
            "level": "own",
            "display": "der Testhund",
            "lemma": "Testhund",
            "pos": "noun",
            "gender": "m",
            "gloss": {"pl": "pies testowy"},
        },
    )
    base = Catalog(COURSES)
    family_before = list(base.family("c90001"))
    derived = Catalog(learner=tmp_path, base=base)
    plain = Catalog(COURSES, learner=tmp_path)
    assert derived.installed() == plain.installed()
    assert [e["id"] for e in derived.first("de")] == [e["id"] for e in plain.first("de")]
    assert [e["id"] for e in derived.family("c90001")] == [e["id"] for e in plain.family("c90001")]
    assert derived.entry("de-u00a1b2") is not None
    assert base.entry("de-u00a1b2") is None
    assert base.family("c90001") == family_before
    assert derived.course("de", ["a1"]) == base.course("de", ["a1"])


def test_init_preview_can_wait_in_the_folder_without_a_pointer(tmp_path: Path) -> None:
    folder = tmp_path / "learner"
    now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    preview = plans.init_preview(
        folder, ["de:a1"], 10, Catalog(), now, pending=folder / store.PENDING, pointer=False
    )
    assert (folder / store.PENDING / f"{preview['token']}.json").is_file()
    assert all("config.json" not in path for path in preview["files"])
    assert not (store.config_dir() / "pending").exists()


def test_the_learning_day_follows_the_time_zone() -> None:
    late = datetime(2026, 3, 10, 23, 30, tzinfo=timezone.utc)
    assert store.learning_day(late, 0, timezone.utc).isoformat() == "2026-03-10"
    assert store.learning_day(late, 0, ZoneInfo("Europe/Warsaw")).isoformat() == "2026-03-11"


# ---------------------------------------------------------------- the engine for many accounts


def _service(tmp_path: Path) -> Service:
    return Service(Settings(url="http://127.0.0.1:9", data=tmp_path / "server", timezone="UTC"))


def test_accounts_learn_apart_and_paths_stay_on_the_server(tmp_path: Path) -> None:
    service = _service(tmp_path)
    one, two = "a" * 32, "b" * 32
    assert service.call(one, ["today"])["error"]["code"] == "no_account_plan"
    preview = service.setup(one, ["de:a1", "es:a1"], 6, ["days_off=none"])
    assert preview["ok"], preview
    dumped = json.dumps(preview)
    for leak in (str(tmp_path), tmp_path.as_posix(), "learners"):
        assert leak not in dumped
    assert service.call(two, ["commit", "--confirm", preview["token"]])["error"]["code"] == (
        "unknown_token"
    )
    assert service.call(one, ["commit", "--confirm", preview["token"]])["ok"]
    assert service.setup(one, ["de:a1"], 6, [])["error"]["code"] == "account_has_plan"
    day = service.call(one, ["today"])
    assert day["ok"] and set(day["languages"]) == {"de", "es"}
    batch = service.call(one, ["next", "--count", "4"])
    cards = [item["card"] for item in batch["items"]]
    assert len(cards) == 4
    catalog = Catalog(COURSES)
    lines = "\n".join(
        json.dumps({"card": card, "answer": correct(catalog, card)}) for card in cards
    )
    graded = service.call(one, ["answer", "--batch", "--stdin"], lines)
    assert graded["ok"], graded
    assert [result["grade"] for result in graded["results"]] == ["know"] * 4
    assert service.call(two, ["status"])["error"]["code"] == "no_account_plan"
    status = service.call(one, ["status"])
    assert status["ok"] and str(tmp_path) not in json.dumps(status)


def test_options_cannot_be_smuggled_in_values(tmp_path: Path) -> None:
    service = _service(tmp_path)
    one = "c" * 32
    assert service.setup(one, ["de:a1"], 5, [])["ok"]
    result = service.call(one, ["grade", "--card", "--today=2030-01-01", "--grade", "know"])
    assert result["error"]["code"] == "bad_arguments"
    assert service.setup(one, ["de:a1"], 5, ["--learner=/tmp"])["error"]["code"] == (
        "bad_assignment"
    )
    with pytest.raises(ValueError, match="not an account"):
        service.folder("../other")


# ---------------------------------------------------------------- the guides


def test_the_guides_name_only_tools_that_exist(tmp_path: Path) -> None:
    server: MCPServer = MCPServer(name="vocabbot-test")
    registry = Registry(tmp_path / "accounts.db")
    register(server, Tools(_service(tmp_path), registry))
    names = {tool.name for tool in anyio.run(server.list_tools)}
    assert len(names) == 22
    mentioned: set[str] = set(re.findall(r"vocab_[a-z_]+", guides.INSTRUCTIONS))
    for topic in guides.TOPICS:
        text = guides.guide(topic)
        assert "# VocabBot rules" in text and "# Labels in Polish" in text
        mentioned |= set(re.findall(r"\bvocab_[a-z_]+[a-z]", text))
    assert mentioned <= names, mentioned - names
    assert names - mentioned == set(), names - mentioned
    with pytest.raises(ValueError, match="unknown topic"):
        guides.guide("../rules")


# ---------------------------------------------------------------- over HTTP


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def live(tmp_path: Path) -> Any:
    port = _free_port()
    settings = Settings(url=f"http://127.0.0.1:{port}", data=tmp_path / "server", timezone="UTC")
    server = uvicorn.Server(
        uvicorn.Config(build(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started:
        assert time.time() < deadline, "the server did not start"
        time.sleep(0.05)
    yield settings
    server.should_exit = True
    thread.join(10)


class Memory:
    """The token storage of a test client."""

    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.client: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client = client_info


def _provider(url: str, form: dict[str, str], memory: Memory) -> OAuthClientProvider:
    """A client that registers itself and signs in through the page, as a chat application does."""
    seen: dict[str, str] = {}

    async def redirect_handler(authorization_url: str) -> None:
        async with httpx2.AsyncClient(follow_redirects=False) as browser:
            first = await browser.get(authorization_url)
            assert first.status_code == 302, first.text
            login_url = first.headers["location"]
            assert login_url.startswith(f"{url}/login?request=")
            page = await browser.get(login_url)
            assert page.status_code == 200
            assert "Połącz VocabBota z aplikacją Test client" in page.text
            assert page.headers["x-frame-options"] == "DENY"
            request_id = parse_qs(urlsplit(login_url).query)["request"][0]
            done = await browser.post(f"{url}/login", data={"request": request_id, **form})
            assert done.status_code == 303, done.text
            target = urlsplit(done.headers["location"])
            assert f"{target.scheme}://{target.netloc}{target.path}" == REDIRECT
            seen.update({key: values[0] for key, values in parse_qs(target.query).items()})

    async def callback_handler() -> AuthorizationCodeResult:
        return AuthorizationCodeResult(
            code=seen["code"], state=seen.get("state"), iss=seen.get("iss")
        )

    return OAuthClientProvider(
        server_url=f"{url}/mcp",
        client_metadata=OAuthClientMetadata(
            client_name="Test client",
            redirect_uris=[AnyUrl(REDIRECT)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        ),
        storage=memory,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )


async def _call(client: Client, name: str, **arguments: Any) -> Any:
    result = await client.call_tool(name, arguments)
    text = result.content[0].text  # type: ignore[union-attr]
    return text if name == "vocab_guide" else json.loads(text)


def test_a_chat_application_connects_signs_up_and_learns(live: Settings) -> None:
    registry = Registry(live.database)
    invites = [registry.create_invite(note="test") for _ in range(2)]
    catalog = Catalog(COURSES)

    async def session() -> dict[str, Any]:
        memory = Memory()
        signup = {
            "action": "signup",
            "login": "ola",
            "password": PASSWORD,
            "password2": PASSWORD,
            "invite": invites[0],
        }
        auth = _provider(live.url, signup, memory)
        async with (
            httpx2.AsyncClient(auth=auth, timeout=30) as http,
            Client(streamable_http_client(live.resource, http_client=http)) as client,
        ):
            tools = {tool.name for tool in (await client.list_tools()).tools}
            assert "vocab_next" in tools and len(tools) == 22
            assert "vocab_guide" in (client.instructions or "")
            assert "# The daily session" in await _call(client, "vocab_guide", topic="session")
            assert (await _call(client, "vocab_today"))["error"]["code"] == "no_account_plan"
            preview = await _call(
                client, "vocab_setup", languages=["de:a1", "fr:a1"], new_per_day=6
            )
            assert preview["ok"] and preview["token"]
            assert live.data.as_posix() not in json.dumps(preview)
            assert (await _call(client, "vocab_commit", token=preview["token"]))["ok"]
            batch = await _call(client, "vocab_next", count=3)
            answers = [
                {"card": item["card"], "answer": correct(catalog, item["card"])}
                for item in batch["items"]
            ]
            answers[-1]["answer"] = ""
            graded = await _call(client, "vocab_answer", answers=answers)
            assert [r["grade"] for r in graded["results"]] == ["know", "know", "dont_know"]
            refused = await client.call_tool("vocab_plan_change", {"settings": ["--x=1"]})
            assert refused.is_error
            status = await _call(client, "vocab_status")
            assert status["ok"] and set(status["languages"]) == {"de", "fr"}
        assert memory.tokens is not None and memory.client is not None
        return {"tokens": memory.tokens, "client": memory.client}

    first = anyio.run(session)

    async def second_account() -> None:
        memory = Memory()
        signup = {
            "action": "signup",
            "login": "kasia",
            "password": PASSWORD,
            "password2": PASSWORD,
            "invite": invites[1],
        }
        auth = _provider(live.url, signup, memory)
        async with (
            httpx2.AsyncClient(auth=auth, timeout=30) as http,
            Client(streamable_http_client(live.resource, http_client=http)) as client,
        ):
            assert (await _call(client, "vocab_status"))["error"]["code"] == "no_account_plan"

    anyio.run(second_account)

    async def sign_in_again() -> None:
        memory = Memory()
        auth = _provider(
            live.url, {"action": "login", "login": "OLA", "password": PASSWORD}, memory
        )
        async with (
            httpx2.AsyncClient(auth=auth, timeout=30) as http,
            Client(streamable_http_client(live.resource, http_client=http)) as client,
        ):
            day = await _call(client, "vocab_today")
            assert day["ok"] and set(day["languages"]) == {"de", "fr"}

    anyio.run(sign_in_again)

    # a refresh gives a new pair; the old refresh token and the old access token end
    tokens, client_info = first["tokens"], first["client"]
    with httpx2.Client(base_url=live.url) as web:
        refreshed = web.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_info.client_id,
                "client_secret": client_info.client_secret or "",
            },
        )
        assert refreshed.status_code == 200, refreshed.text
        again = web.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_info.client_id,
                "client_secret": client_info.client_secret or "",
            },
        )
        assert again.status_code == 400 and again.json()["error"] == "invalid_grant"
        call = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        headers = {"accept": "application/json, text/event-stream"}
        old = web.post(
            "/mcp", json=call, headers={**headers, "authorization": f"Bearer {tokens.access_token}"}
        )
        assert old.status_code == 401


def test_the_endpoints_describe_the_server_and_refuse_strangers(live: Settings) -> None:
    with httpx2.Client(base_url=live.url) as web:
        anonymous = web.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"accept": "application/json, text/event-stream"},
        )
        assert anonymous.status_code == 401
        assert "/.well-known/oauth-protected-resource/mcp" in anonymous.headers["www-authenticate"]
        for path in (
            "/.well-known/oauth-protected-resource/mcp",
            "/.well-known/oauth-protected-resource",
        ):
            resource = web.get(path).json()
            assert resource["resource"] == live.resource
            assert resource["authorization_servers"] == [live.url]
        metadata = web.get("/.well-known/oauth-authorization-server").json()
        assert metadata["issuer"] == live.url
        assert metadata["authorization_response_iss_parameter_supported"] is True
        assert metadata["code_challenge_methods_supported"] == ["S256"]
        assert metadata["registration_endpoint"] == f"{live.url}/register"
        stranger = web.post(
            "/register",
            json={
                "client_name": "Stranger",
                "redirect_uris": ["https://evil.example.com/callback"],
            },
        )
        assert stranger.status_code == 400
        assert stranger.json()["error"] == "invalid_redirect_uri"
        expired = web.get("/login", params={"request": "nothing"})
        assert expired.status_code == 400 and "Link wygasł" in expired.text
        assert web.get("/health").json()["ok"] is True
        assert live.resource in web.get("/").text
        assert "Prywatność" in web.get("/privacy").text
        typeface = web.get("/static/geist.woff2")
        assert typeface.content[:4] == b"wOF2"
        assert typeface.headers["content-type"] == "font/woff2"


def test_a_wrong_password_keeps_the_sign_in_open(live: Settings) -> None:
    registry = Registry(live.database)
    registry.signup("ola", PASSWORD, None, True)
    with httpx2.Client(base_url=live.url, follow_redirects=False) as web:
        client = web.post(
            "/register",
            json={"client_name": "Test client", "redirect_uris": [REDIRECT]},
        ).json()
        authorize = web.get(
            "/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": REDIRECT,
                "response_type": "code",
                "code_challenge": "x" * 43,
                "code_challenge_method": "S256",
                "state": "s1",
                "resource": live.resource,
            },
        )
        request_id = parse_qs(urlsplit(authorize.headers["location"]).query)["request"][0]
        wrong = web.post(
            "/login",
            data={"request": request_id, "action": "login", "login": "ola", "password": "x" * 12},
        )
        assert wrong.status_code == 400 and "Nieprawidłowy login lub hasło" in wrong.text
        assert 'id="tab-login" checked' in wrong.text
        page = web.get("/login", params={"request": request_id})
        assert "Kod otrzymujesz od osoby, która prowadzi serwer" in page.text
        assert "font-src 'self'" in page.headers["content-security-policy"]
        no_invite = web.post(
            "/login",
            data={
                "request": request_id,
                "action": "signup",
                "login": "kasia",
                "password": PASSWORD,
                "password2": PASSWORD,
                "invite": "AAAA-BBBB-CCCC",
            },
        )
        assert (
            no_invite.status_code == 400 and "Kod zaproszenia jest nieprawidłowy" in no_invite.text
        )
        assert 'id="tab-signup" checked' in no_invite.text and 'value="kasia"' in no_invite.text
        right = web.post(
            "/login",
            data={"request": request_id, "action": "login", "login": "ola", "password": PASSWORD},
        )
        assert right.status_code == 303
        query = parse_qs(urlsplit(right.headers["location"]).query)
        assert query["state"] == ["s1"] and query["iss"] == [live.url]
        reused = web.post(
            "/login",
            data={"request": request_id, "action": "login", "login": "ola", "password": PASSWORD},
        )
        assert reused.status_code == 400 and "Link wygasł" in reused.text
        elsewhere = web.get(
            "/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": REDIRECT,
                "response_type": "code",
                "code_challenge": "x" * 43,
                "state": "s2",
                "resource": "https://other.example.org/mcp",
            },
        )
        assert "error=invalid_target" in elsewhere.headers["location"]
