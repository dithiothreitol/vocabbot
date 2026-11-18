"""The program's connection to a VocabBot server: signing in, tokens and the synchronisation.

`vocabbot login` signs the program in to an account with OAuth 2.1, as a chat
application does: the program registers itself, opens the server's sign-in
page in the browser and receives the result on 127.0.0.1 (PKCE). Without a
browser it shows an address and a short code to confirm on another device
(the device flow of RFC 8628 on the server's own addresses). The learner types
the password only on the server's page.

The tokens live in ~/.vocabbot/credentials.json, readable by the owner only,
never in the learner's folder and never in a command's result. An access
token lasts an hour; the refresh token changes at every use, and a process
that finds its refresh token used by another process takes the new one from
the file.

Everything here uses the standard library (urllib, http.server, webbrowser),
so vocabbot.pyz synchronises in any host that lets it reach the network.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import html
import http.server
import json
import os
import platform
import secrets
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from vocabbot import __version__, assets, store, sync
from vocabbot.errors import VocabError

DEFAULT_SERVER = "https://vocabbot.run"
CREDENTIALS = "credentials.json"
SCOPE = "vocab"
USER_AGENT = f"vocabbot/{__version__}"
TIMEOUT = 30.0  # seconds of a request the learner asked for
AUTO_TIMEOUT = 6.0  # seconds of a synchronisation around a command
PAUSE = timedelta(seconds=60)  # after a failed synchronisation the next commands do not wait
LOGIN_TIMEOUT = 300.0
DEVICE_TIMEOUT = 900.0
MAX_RESPONSE = 64 * 1024 * 1024
LOOPBACK = ("localhost", "127.0.0.1", "::1")
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def server_url(given: str | None = None) -> str:
    """The server's address: scheme and host, https except on this computer."""
    raw = (given or os.environ.get("VOCABBOT_SERVER") or DEFAULT_SERVER).strip()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        parts.port  # noqa: B018 - a port that is not a number raises here
    except ValueError:
        raise VocabError("bad_server", server=raw[:100]) from None
    if parts.scheme not in ("https", "http") or not host or parts.username or parts.password:
        raise VocabError("bad_server", server=raw[:100])
    if parts.scheme == "http" and host not in LOOPBACK:
        raise VocabError("bad_server", server=raw[:100])
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise VocabError("bad_server", server=raw[:100])
    return f"{parts.scheme}://{parts.netloc.lower()}"


def host_of(url: str) -> str:
    return urlsplit(url).netloc


def same_server(address: Any, server: str) -> bool:
    """True when an address names the same server, whatever the case of its host."""
    if not isinstance(address, str):
        return False
    try:
        return server_url(address) == server
    except VocabError:
        return False


# ---------------------------------------------------------------- HTTP


class Http:
    """JSON and form requests with urllib; a network failure is a VocabError."""

    def request(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
        form: dict[str, str] | None = None,
        token: str | None = None,
        timeout: float = TIMEOUT,
    ) -> tuple[int, Any]:
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        data: bytes | None = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urlencode(form).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status, raw = int(response.status), response.read(MAX_RESPONSE)
        except urllib.error.HTTPError as exc:
            status, raw = int(exc.code), exc.read(MAX_RESPONSE)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise VocabError(
                "server_unreachable", server=host_of(url), detail=str(reason)[:200]
            ) from None
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, ValueError):
            body = {}
        return status, body


# ---------------------------------------------------------------- credentials


def _credentials_path() -> Path:
    return store.config_dir() / CREDENTIALS


def _read_all() -> dict[str, Any]:
    try:
        data = json.loads(_credentials_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"servers": {}}
    if not isinstance(data, dict) or not isinstance(data.get("servers"), dict):
        return {"servers": {}}
    return data


def credentials(server: str) -> dict[str, Any] | None:
    found = _read_all()["servers"].get(server)
    return found if isinstance(found, dict) and found.get("refresh_token") else None


def save_credentials(server: str, data: dict[str, Any] | None) -> None:
    """Keep (or with None forget) the tokens of a server, readable by the owner only."""
    everything = _read_all()
    if data is None:
        everything["servers"].pop(server, None)
    else:
        everything["servers"][server] = data
    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # created readable by the owner only, then put in place in one step
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "wb") as out:
        out.write(store.dump_json(everything).encode("utf-8"))
    with contextlib.suppress(OSError):
        os.chmod(temporary, 0o600)
    os.replace(temporary, path)


# ---------------------------------------------------------------- OAuth


def discover(http: Http, server: str) -> dict[str, Any]:
    """The authorization server's metadata; its issuer must be the server itself."""
    status, meta = http.request("GET", f"{server}/.well-known/oauth-authorization-server")
    if status != 200 or not isinstance(meta, dict) or not same_server(meta.get("issuer"), server):
        raise VocabError("not_a_server", server=host_of(server))
    for key in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
        address = meta.get(key)
        if not isinstance(address, str) or not same_server(address.rsplit("/", 1)[0], server):
            raise VocabError("not_a_server", server=host_of(server))
    return meta


def register(http: Http, meta: dict[str, Any], redirect: str) -> str:
    """A public client of its own for this sign-in (a loopback address with its port)."""
    name = assets.text("remote.client_name", host=(platform.node() or "?")[:40])
    status, body = http.request(
        "POST",
        str(meta["registration_endpoint"]),
        json_body={
            "client_name": name,
            "redirect_uris": [redirect],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": SCOPE,
        },
    )
    if status not in (200, 201) or not isinstance(body, dict) or not body.get("client_id"):
        raise VocabError("login_refused", detail=str(body.get("error_description") or status))
    return str(body["client_id"])


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.decode("ascii").rstrip("=")


def _tokens(
    server: str, meta: dict[str, Any], client_id: str, body: Any, now: float
) -> dict[str, Any]:
    if not isinstance(body, dict) or not body.get("access_token") or not body.get("refresh_token"):
        raise VocabError("login_refused", detail="no tokens")
    return {
        "client_id": client_id,
        "access_token": str(body["access_token"]),
        "refresh_token": str(body["refresh_token"]),
        "expires_at": now + float(body.get("expires_in") or 3600),
        "token_endpoint": str(meta["token_endpoint"]),
        "revocation_endpoint": str(meta.get("revocation_endpoint") or f"{server}/revoke"),
    }


class _Callback(http.server.BaseHTTPRequestHandler):
    """The page the browser comes back to after the sign-in, on 127.0.0.1."""

    server: _CallbackServer

    def do_GET(self) -> None:
        parts = urlsplit(self.path)
        if parts.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        self.server.result = {key: values[0] for key, values in parse_qs(parts.query).items()}
        failed = "error" in self.server.result or "code" not in self.server.result
        text = assets.text("remote.browser_failed" if failed else "remote.browser_done")
        page = (
            '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
            f"<title>VocabBot</title></head><body><p>{html.escape(text)}</p>"
            "</body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, format: str, *args: Any) -> None:
        return


class _CallbackServer(http.server.HTTPServer):
    result: dict[str, str] | None = None


def login_browser(
    server: str,
    http: Http,
    announce: Callable[[str], None],
    *,
    opener: Callable[[str], bool] = webbrowser.open,
    timeout: float = LOGIN_TIMEOUT,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Sign in through the browser; the result comes back to a port of 127.0.0.1."""
    meta = discover(http, server)
    callback = _CallbackServer(("127.0.0.1", 0), _Callback)
    try:
        port = int(callback.server_address[1])
        redirect = f"http://127.0.0.1:{port}/callback"
        client_id = register(http, meta, redirect)
        verifier, challenge = pkce()
        state = secrets.token_urlsafe(16)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
                "scope": SCOPE,
                "resource": f"{server}/mcp",
            }
        )
        address = f"{meta['authorization_endpoint']}?{query}"
        announce(assets.text("remote.open_browser", url=address))
        with contextlib.suppress(webbrowser.Error):
            opener(address)
        callback.timeout = 0.5
        deadline = clock() + timeout
        while callback.result is None:
            if clock() > deadline:
                raise VocabError("login_timeout")
            callback.handle_request()
        result = callback.result
    finally:
        callback.server_close()
    if result.get("state") != state:
        raise VocabError("login_refused", detail="state")
    if result.get("error"):
        raise VocabError("login_refused", detail=str(result["error"])[:100])
    if result.get("iss") is not None and not same_server(result.get("iss"), server):
        raise VocabError("login_refused", detail="iss")
    status, body = http.request(
        "POST",
        str(meta["token_endpoint"]),
        form={
            "grant_type": "authorization_code",
            "code": result.get("code", ""),
            "redirect_uri": redirect,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": f"{server}/mcp",
        },
    )
    if status != 200:
        raise VocabError("login_refused", detail=str(body.get("error") or status))
    return _tokens(server, meta, client_id, body, time.time())


def login_device(
    server: str,
    http: Http,
    announce: Callable[[str], None],
    *,
    sleep: Callable[[float], None] = time.sleep,
    timeout: float = DEVICE_TIMEOUT,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Sign in with a short code confirmed on another device (a phone, a laptop)."""
    meta = discover(http, server)
    client_id = register(http, meta, "http://127.0.0.1/device")
    status, body = http.request(
        "POST", f"{server}/device/authorize", form={"client_id": client_id, "scope": SCOPE}
    )
    if status != 200 or not isinstance(body, dict) or not body.get("device_code"):
        raise VocabError("login_refused", detail=str(body.get("error") or status))
    announce(
        assets.text(
            "remote.device_code",
            url=str(body.get("verification_uri") or f"{server}/device"),
            code=str(body.get("user_code")),
        )
    )
    interval = float(body.get("interval") or 5)
    deadline = clock() + min(timeout, float(body.get("expires_in") or timeout))
    while clock() < deadline:
        sleep(interval)
        status, answer = http.request(
            "POST",
            f"{server}/device/token",
            form={
                "grant_type": DEVICE_GRANT,
                "device_code": str(body["device_code"]),
                "client_id": client_id,
            },
        )
        if status == 200:
            return _tokens(server, meta, client_id, answer, time.time())
        error = answer.get("error") if isinstance(answer, dict) else None
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise VocabError("login_refused", detail=str(error or status))
    raise VocabError("login_timeout")


def access_token(http: Http, server: str, *, force: bool = False, timeout: float = TIMEOUT) -> str:
    """A valid access token for the server, refreshed when it ends within a minute."""
    found = credentials(server)
    if found is None:
        raise VocabError("signed_out", server=host_of(server))
    if not force and float(found.get("expires_at", 0)) - 60 > time.time():
        return str(found["access_token"])
    status, body = http.request(
        "POST",
        str(found.get("token_endpoint") or f"{server}/token"),
        form={
            "grant_type": "refresh_token",
            "refresh_token": str(found["refresh_token"]),
            "client_id": str(found["client_id"]),
            "resource": f"{server}/mcp",
        },
        timeout=timeout,
    )
    if status == 200 and isinstance(body, dict) and body.get("access_token"):
        found.update(
            access_token=str(body["access_token"]),
            refresh_token=str(body.get("refresh_token") or found["refresh_token"]),
            expires_at=time.time() + float(body.get("expires_in") or 3600),
        )
        save_credentials(server, found)
        return str(found["access_token"])
    # another process may have used the refresh token a moment ago and kept the new pair
    again = credentials(server)
    if (
        again is not None
        and again.get("refresh_token") != found.get("refresh_token")
        and float(again.get("expires_at", 0)) - 60 > time.time()
    ):
        return str(again["access_token"])
    if status in (400, 401):
        save_credentials(server, None)
        raise VocabError("signed_out", server=host_of(server))
    raise VocabError("sync_failed", status=status, detail=str(body.get("error") or ""))


def revoke(http: Http, server: str) -> bool:
    """End the program's connection on the server; True when the server confirmed it."""
    found = credentials(server)
    if found is None:
        return False
    try:
        status, _ = http.request(
            "POST",
            str(found.get("revocation_endpoint") or f"{server}/revoke"),
            form={
                "token": str(found["refresh_token"]),
                "token_type_hint": "refresh_token",
                "client_id": str(found["client_id"]),
                # a public client has no secret, but the SDK's revocation form names the field
                "client_secret": "",
            },
        )
    except VocabError:
        return False
    return status == 200


class HttpTransport:
    """The synchronisation's way to the account: POST /sync with the account's token."""

    def __init__(self, server: str, http: Http | None = None, timeout: float = TIMEOUT) -> None:
        self.server = server
        self.http = http or Http()
        self.timeout = timeout

    def exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        status: int = 0
        body: Any = {}
        for attempt in (0, 1):
            token = access_token(self.http, self.server, force=attempt == 1, timeout=self.timeout)
            status, body = self.http.request(
                "POST",
                f"{self.server}/sync",
                json_body=payload,
                token=token,
                timeout=self.timeout,
            )
            if status != 401:
                break
        if status == 200 and isinstance(body, dict):
            return body
        if status == 401:
            raise VocabError("signed_out", server=host_of(self.server))
        if status == 429:
            raise VocabError("sync_busy")
        error = body.get("error") if isinstance(body, dict) else None
        details = error.get("details") if isinstance(error, dict) else None
        if (
            isinstance(error, dict)
            and error.get("code") == "other_account"
            and isinstance(details, dict)
        ):
            raise VocabError(
                "other_account",
                login=str(details.get("login", "?")),
                linked=str(details.get("linked", "?")),
            )
        message = error.get("message") if isinstance(error, dict) else error
        raise VocabError("sync_failed", status=status, detail=str(message or "")[:200])


# ---------------------------------------------------------------- around the commands


def _recent(stamp: Any, now: datetime) -> bool:
    try:
        moment = store.parse_iso(str(stamp))
    except ValueError:
        return False
    return now.replace(tzinfo=None) - moment < PAUSE


def auto(
    root: Path,
    now: datetime,
    installed: Callable[[], dict[str, list[str]]],
    *,
    push_only: bool = False,
    timeout: float = AUTO_TIMEOUT,
    transport: sync.Transport | None = None,
) -> dict[str, Any] | None:
    """The synchronisation around a command of a linked folder; None for a folder without a link.

    It never stops the learning: a failure is kept in the link and reported, the
    rows wait in the folder, and for a minute after a failure the commands do
    not wait for the network.
    """
    with _lock_of(root):
        return _auto(root, now, installed, push_only, timeout, transport)


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_of(root: Path) -> threading.Lock:
    """One synchronisation of a folder at a time in this process (a session's background
    sending and its closing synchronisation)."""
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(str(root.resolve()), threading.Lock())


def _auto(
    root: Path,
    now: datetime,
    installed: Callable[[], dict[str, list[str]]],
    push_only: bool,
    timeout: float,
    transport: sync.Transport | None,
) -> dict[str, Any] | None:
    state = sync.link_state(root)
    if state is None:
        return None
    failed = state.get("failed")
    if transport is None and isinstance(failed, dict) and _recent(failed.get("at"), now):
        return {"ok": False, "skipped": True, "pending": sync.pending(root, state)}
    try:
        way = transport or HttpTransport(str(state["server"]), Http(), timeout)
        return sync.run(root, way, now, installed, push_only=push_only)
    except Exception as exc:  # a synchronisation never stops a command or a session
        error = (
            exc if isinstance(exc, VocabError) else VocabError("sync_error", detail=str(exc)[:200])
        )
        latest = sync.link_state(root) or state
        latest["failed"] = {"at": store.iso(now), "code": error.code}
        with contextlib.suppress(OSError):
            sync.save_state(root, latest)
        return {"ok": False, "error": error.as_dict(), "pending": sync.pending(root, latest)}


class Pusher:
    """Sends the terminal session's answers in the background, a moment after each one.

    It watches the folder's logs and sends (only sends) when they changed, so
    nothing is appended to the folder while the session writes to it.
    """

    def __init__(self, root: Path, push: Callable[[], Any], interval: float = 2.0) -> None:
        self.root = root
        self.push = push
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="vocabbot-sync", daemon=True)

    def _key(self) -> tuple[Any, ...]:
        out = []
        for name in sync.stream_names(self.root):
            try:
                st = (self.root / name).stat()
                out.append((name, st.st_size, st.st_mtime_ns))
            except OSError:
                continue
        return tuple(out)

    def _loop(self) -> None:
        seen = self._key()
        while not self._stop.wait(self.interval):
            current = self._key()
            if current != seen:
                seen = current
                try:
                    self.push()
                except Exception:  # the session goes on; the closing synchronisation reports
                    continue

    def __enter__(self) -> Pusher:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(AUTO_TIMEOUT * 2)


def describe(root: Path) -> dict[str, Any] | None:
    """The link of the folder for `status`, `today` and `doctor`; None without a link."""
    state = sync.link_state(root)
    if state is None:
        return None
    server = str(state["server"])
    out: dict[str, Any] = {
        "server": host_of(server),
        "login": state.get("login") or "",
        "last": state.get("last"),
        "pending": sync.pending(root, state),
        "signed_in": credentials(server) is not None,
        "version": __version__,
    }
    if isinstance(state.get("failed"), dict):
        out["failed"] = state["failed"]
    if isinstance(state.get("server_version"), str):
        out["server_version"] = state["server_version"]
    return out
