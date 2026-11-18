"""The server in a browser: the session page, the account page, recovery and device codes.

A browser signs in on /app/login and gets a session cookie for 30 days
(HttpOnly, SameSite=Strict, and Secure on https). Every write needs the form
token of the session (a hidden field, or the X-CSRF-Token header of the
session page) and a request from the server's own origin.

The session page (/app/) calls /api/<name>, and every address runs a command
of the engine through `Service.call`, as an MCP tool does: a question comes
without its answer, the engine grades, a change of the plan waits for a
preview and its token. Nothing here uses a model.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from collections import deque
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import anyio.to_thread
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from vocabbot import __version__, assets, store
from vocabbot.courses import CARD_ID
from vocabbot.server import mail, pages
from vocabbot.server.accounts import Account, Registry, SignupError, valid_email
from vocabbot.server.config import Settings
from vocabbot.server.oauth import Throttle, browser_zone
from vocabbot.server.service import ASSIGNMENT, Service

COOKIE = "vocabbot_session"
NEXT = re.compile(r"^/(?:app/|account|device)[A-Za-z0-9/?=&._%-]*$")
LANG = re.compile(r"^[a-z]{2}$")
LEVELS = re.compile(r"^[abcABC][12]([-,][abcABC][12])*$")
TOKEN = re.compile(r"^[0-9a-f]{16}$")
GRADES = ("known", "know", "almost", "dont_know")
STAGES = ("reviews", "new", "drill")
MAX_BODY = 256 * 1024
SYNC_BODY = 16 * 1024 * 1024


class Rate:
    """At most `limit` requests of one key within a minute."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._seen: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        recent = self._seen.setdefault(key, deque())
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= self.limit:
            return False
        recent.append(now)
        return True


class BadInput(Exception):
    """A request of the session page the server refuses before the engine sees it."""


def _card(body: dict[str, Any]) -> str:
    card = body.get("card")
    if not isinstance(card, str) or not CARD_ID.match(card):
        raise BadInput("card")
    return card


def _text(body: dict[str, Any], key: str, limit: int) -> str:
    value = body.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise BadInput(key)
    return value


def _number(body: dict[str, Any], key: str, low: int, high: int, default: int) -> int:
    value = body.get(key, default)
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise BadInput(key) from None
    if not low <= number <= high:
        raise BadInput(key)
    return number


def _answer_line(card: str, answer: str) -> str:
    return json.dumps({"card": card, "answer": answer}, ensure_ascii=False)


class Web:
    """The routes of the browser: pages, the session page and its /api."""

    def __init__(
        self,
        registry: Registry,
        settings: Settings,
        service: Service,
        devices: Any,
        throttle: Throttle | None = None,
    ) -> None:
        self.registry = registry
        self.settings = settings
        self.service = service
        self.devices = devices
        # one count of failed passwords with the sign-in of chat applications
        self.throttle = throttle or Throttle()
        self.recovery = Throttle()
        self.api_rate = Rate(600)
        self.send_mail: Callable[[str, str, str], None] = self._send

    # ------------------------------------------------------------ sessions and forms

    def _send(self, to: str, subject: str, body: str) -> None:
        mail.send(self.settings.mail, to, subject, body)

    def session_token(self, request: Request) -> str:
        return request.cookies.get(COOKIE, "")

    def account_of(self, request: Request) -> Account | None:
        token = self.session_token(request)
        return self.registry.session(token) if token else None

    @staticmethod
    def csrf_of(token: str) -> str:
        """The form token of a session, derived from it, so nothing more is kept."""
        return hmac.new(token.encode(), b"vocabbot-csrf", hashlib.sha256).hexdigest()[:32]

    def csrf_ok(self, request: Request, given: str) -> bool:
        token = self.session_token(request)
        return bool(token) and hmac.compare_digest(self.csrf_of(token), given or "")

    def origin_ok(self, request: Request) -> bool:
        """A write comes from the server's own pages: its Origin, or a same-origin fetch."""
        origin = request.headers.get("origin")
        site = request.headers.get("sec-fetch-site")
        if origin is not None and origin != "null":
            return origin == self.settings.url
        if origin == "null":
            return site == "same-origin"
        return site in (None, "same-origin", "none")

    def _cookie(self, response: Response, token: str) -> Response:
        response.set_cookie(
            COOKIE,
            token,
            max_age=30 * 86400,
            path="/",
            httponly=True,
            secure=self.settings.secure,
            samesite="strict",
        )
        return response

    def _loc(self, request: Request) -> pages.Locale:
        """The language of the page: ?lang=, the switch's cookie, the browser, Polish."""
        return pages.locale(request, secure=self.settings.secure, site=self.settings.url)

    @staticmethod
    def _address(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _next(value: Any) -> str:
        target = str(value or "")
        return target if NEXT.match(target) else "/app/"

    def _to_login(self, target: str) -> RedirectResponse:
        return RedirectResponse(f"/app/login?next={quote(target)}", status_code=303)

    # ------------------------------------------------------------ sign-in

    async def sign_in(self, request: Request) -> Response:
        mail_ready = self.settings.mail.ready
        open_signup = self.settings.open_signup
        loc = self._loc(request)
        if request.method == "GET":
            target = self._next(request.query_params.get("next"))
            if self.account_of(request) is not None:
                return RedirectResponse(target, status_code=303)
            return pages.respond(loc, pages.web_sign_in(loc, target, open_signup, mail_ready))
        if not self.origin_ok(request):
            page = pages.web_sign_in(loc, "/app/", open_signup, mail_ready, "origin")
            return pages.respond(loc, page, 403)
        form = await request.form()
        target = self._next(form.get("next"))
        login = str(form.get("login") or "")[:100]
        password = str(form.get("password") or "")
        tab = "signup" if form.get("action") == "signup" else "login"
        address = self._address(request)
        loc = loc.at(f"/app/login?next={quote(target)}")

        def refuse(error: str, status: int = 400) -> Response:
            page = pages.web_sign_in(loc, target, open_signup, mail_ready, error, login, tab)
            return pages.respond(loc, page, 429 if error == "throttled" else status)

        if self.throttle.blocked(address, login):
            return refuse("throttled")
        zone = browser_zone(form.get("tz"))
        account: Account | None
        if tab == "signup":
            if password != str(form.get("password2") or ""):
                return refuse("password_mismatch")
            email = str(form.get("email") or "").strip()
            if email and not (mail_ready and valid_email(email)):
                return refuse("bad_email")
            try:
                account = await anyio.to_thread.run_sync(
                    self.registry.signup,
                    login,
                    password,
                    str(form.get("invite") or ""),
                    open_signup,
                )
            except SignupError as exc:
                if exc.code == "bad_invite":
                    self.throttle.fail(address, login)
                return refuse(exc.code)
            self.registry.set_timezone(account.id, zone)
            if email:
                await anyio.to_thread.run_sync(self.registry.set_email, account.id, email)
        else:
            account = await anyio.to_thread.run_sync(self.registry.verify, login, password)
            if account is None:
                self.throttle.fail(address, login)
                return refuse("wrong_credentials")
            self.registry.set_timezone(account.id, zone, only_empty=True)
        token = self.registry.open_session(account.id)
        return self._cookie(RedirectResponse(target, status_code=303), token)

    async def sign_out(self, request: Request) -> Response:
        form = await request.form()
        if self.origin_ok(request) and self.csrf_ok(request, str(form.get("csrf") or "")):
            self.registry.close_session(self.session_token(request))
        response = RedirectResponse("/app/login", status_code=303)
        response.delete_cookie(COOKIE, path="/")
        return response

    # ------------------------------------------------------------ the account page

    def _account_page(
        self,
        request: Request,
        account: Account,
        message: str | None = None,
        error: str | None = None,
    ) -> Response:
        """The account page, with a message (the name of its text) or an error."""
        loc = self._loc(request).at("/account")
        page = pages.account(
            loc,
            account.login,
            account.created,
            self.csrf_of(self.session_token(request)),
            has_email=self.registry.has_email(account.id),
            mail_ready=self.settings.mail.ready,
            grants=self.registry.grants(account.id),
            can_export=(self.service.folder(account.id) / store.PLAN).is_file(),
            message=loc.say(message) if message else None,
            error=error,
        )
        return pages.respond(loc, page, 400 if error else 200)

    async def account(self, request: Request) -> Response:
        account = self.account_of(request)
        if account is None:
            return self._to_login("/account")
        if request.method == "GET":
            return self._account_page(request, account)
        form = await request.form()
        if not self.origin_ok(request) or not self.csrf_ok(request, str(form.get("csrf") or "")):
            return self._account_page(request, account, error="origin")
        action = form.get("action")
        # the address decides where a new password goes, so it changes with the password
        password = str(form.get("password") or "")
        if action in ("email", "email_remove") and not await self._password_ok(
            request, account, password
        ):
            return self._account_page(request, account, error="wrong_password")
        if action == "email" and self.settings.mail.ready:
            try:
                email = str(form.get("email") or "")
                await anyio.to_thread.run_sync(self.registry.set_email, account.id, email)
            except SignupError:
                return self._account_page(request, account, error="bad_email")
            return self._account_page(request, account, "web.saved_email")
        if action == "email_remove":
            self.registry.set_email(account.id, None)
            return self._account_page(request, account, "web.removed_email")
        if action == "unlink":
            self.registry.drop_account_grant(account.id, str(form.get("grant") or ""))
            return self._account_page(request, account, "web.unlinked")
        if action == "delete":
            if not await self._password_ok(request, account, str(form.get("password") or "")):
                return self._account_page(request, account, error="wrong_password")
            self.registry.delete_account(account.id)
            await anyio.to_thread.run_sync(self.service.remove, account.id)
            loc = self._loc(request).at("/")
            page = pages.message_page(
                loc, loc.say("web.delete_title"), loc.say("web.deleted"), tone="ok"
            )
            response = pages.respond(loc, page)
            response.delete_cookie(COOKIE, path="/")
            return response
        return self._account_page(request, account)

    async def _password_ok(self, request: Request, account: Account, password: str) -> bool:
        address = self._address(request)
        if self.throttle.blocked(address, account.login):
            return False
        checked = await anyio.to_thread.run_sync(self.registry.verify, account.login, password)
        if checked is None or checked.id != account.id:
            self.throttle.fail(address, account.login)
            return False
        return True

    async def export(self, request: Request) -> Response:
        account = self.account_of(request)
        if account is None:
            return self._to_login("/account")
        data = await anyio.to_thread.run_sync(self.service.export, account.id)
        if data is None:
            return self._account_page(request, account)
        name = f"vocabbot-{account.login}-{time.strftime('%Y-%m-%d')}.zip"
        return Response(
            data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    # ------------------------------------------------------------ password recovery

    async def recover(self, request: Request) -> Response:
        loc = self._loc(request).at("/recover")
        if not self.settings.mail.ready:
            page = pages.message_page(
                loc, loc.say("web.recover_title"), loc.say("web.email_unavailable"), tone="info"
            )
            return pages.respond(loc, page)
        if request.method == "GET":
            return pages.respond(loc, pages.recover(loc))
        if not self.origin_ok(request):
            return pages.respond(loc, pages.recover(loc, "origin"), 403)
        form = await request.form()
        login = str(form.get("login") or "")[:100]
        email = str(form.get("email") or "")[:254]
        address = self._address(request)
        sent = pages.message_page(
            loc, loc.say("web.recover_title"), loc.say("web.recover_sent"), tone="mail"
        )
        # counted per address and login, so nobody can block another learner's recovery
        source = f"{address}|{login.strip().lower()}"
        if self.recovery.blocked(address, source):
            return pages.respond(loc, pages.recover(loc, "throttled"), 429)
        self.recovery.fail(address, source)  # every request counts, so the page cannot be tried out
        account = await anyio.to_thread.run_sync(self.registry.match_email, login, email)
        if account is None:
            return pages.respond(loc, sent)
        token = self.registry.start_reset(account.id)
        # the message and the page of the new password speak the language of this page
        link = f"{self.settings.url}/recover/{token}?lang={loc.lang}"
        subject = loc.say("web.recover_mail_subject")
        body = loc.say(
            "web.recover_mail_body",
            login=account.login,
            server=self.settings.host,
            link=link,
        )
        # the message leaves after the answer, so a known address does not answer later
        return pages.respond(
            loc, sent, background=BackgroundTask(self._deliver, email.strip(), subject, body)
        )

    def _deliver(self, to: str, subject: str, body: str) -> None:
        try:
            self.send_mail(to, subject, body)
        except Exception as exc:  # the learner sees the same page; the log keeps the reason
            print(f"vocabbot-server: the recovery message was not sent: {exc}", flush=True)

    async def reset(self, request: Request) -> Response:
        token = str(request.path_params.get("token") or "")
        loc = self._loc(request).at(request.url.path)
        account = self.registry.reset_account(token)
        expired = pages.message_page(
            loc,
            loc.say("web.reset_title"),
            loc.say("web.reset_expired"),
            ("/recover", loc.say("web.recover_title")),
            tone="error",
        )
        if account is None:
            return pages.respond(loc, expired, 400)
        if request.method == "GET":
            return pages.respond(loc, pages.reset(loc, token, account.login))
        if not self.origin_ok(request):
            return pages.respond(loc, pages.reset(loc, token, account.login, "origin"), 403)
        form = await request.form()
        password = str(form.get("password") or "")
        if password != str(form.get("password2") or ""):
            page = pages.reset(loc, token, account.login, "password_mismatch")
            return pages.respond(loc, page, 400)
        if not 12 <= len(password) <= 200:
            return pages.respond(loc, pages.reset(loc, token, account.login, "bad_password"), 400)
        used = self.registry.take_reset(token)
        if used is None:
            return pages.respond(loc, expired, 400)
        await anyio.to_thread.run_sync(self.registry.set_password, used.id, password)
        page = pages.message_page(
            loc,
            loc.say("web.reset_title"),
            loc.say("web.reset_done"),
            ("/app/login", loc.say("web.login_button")),
            tone="ok",
        )
        return pages.respond(loc, page)

    # ------------------------------------------------------------ the device code

    async def device(self, request: Request) -> Response:
        account = self.account_of(request)
        csrf = self.csrf_of(self.session_token(request)) if account else ""
        login = account.login if account else None
        loc = self._loc(request)
        if request.method == "GET":
            code = str(request.query_params.get("code") or "")[:12]
            return pages.respond(loc, pages.device(loc, code, login, csrf))
        if not self.origin_ok(request):
            return pages.respond(loc, pages.device(loc, "", login, csrf, "origin"), 403)
        form = await request.form()
        code = str(form.get("code") or "")[:20]
        address = self._address(request)
        loc = loc.at(f"/device?code={quote(code)}" if code else "/device")

        def refuse(error: str, status: int, who: str | None, token: str) -> Response:
            return pages.respond(loc, pages.device(loc, code, who, token, error), status)

        if account is None:
            name = str(form.get("login") or "")[:100]
            if self.throttle.blocked(address, name):
                return refuse("throttled", 429, None, "")
            account = await anyio.to_thread.run_sync(
                self.registry.verify, name, str(form.get("password") or "")
            )
            if account is None:
                self.throttle.fail(address, name)
                return refuse("wrong_credentials", 400, None, "")
        elif not self.csrf_ok(request, str(form.get("csrf") or "")):
            return refuse("origin", 403, login, csrf)
        if self.throttle.blocked(address, f"device:{address}"):
            return refuse("throttled", 429, login, csrf)
        if not self.registry.approve_device(code, account.id):
            self.throttle.fail(address, f"device:{address}")
            return refuse("bad_code", 400, login, csrf)
        page = pages.message_page(
            loc,
            loc.say("web.device_title"),
            loc.say("web.device_done", login=account.login),
            tone="ok",
        )
        return pages.respond(loc, page)

    # ------------------------------------------------------------ the session page

    async def app_page(self, request: Request) -> Response:
        account = self.account_of(request)
        if account is None:
            return self._to_login("/app/")
        page = pages.app(account.login, self.csrf_of(self.session_token(request)))
        return HTMLResponse(page, headers=pages.APP_HEADERS)

    async def app_redirect(self, request: Request) -> Response:
        return RedirectResponse("/app/", status_code=308)

    async def manifest(self, request: Request) -> Response:
        return Response(
            pages.manifest(),
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    async def worker(self, request: Request) -> Response:
        return Response(
            pages.static_text("sw.js").replace("/*VOCABBOT_VERSION*/", __version__),
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/app/"},
        )

    async def script(self, request: Request) -> Response:
        return Response(
            pages.static_text("app.js"),
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    async def style(self, request: Request) -> Response:
        # the pages ask for it under its digest, so a browser may keep it
        return Response(
            pages.stylesheet(),
            media_type="text/css",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Content-Type-Options": "nosniff",
            },
        )

    async def svg(self, request: Request) -> Response:
        return Response(
            pages.mark(),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # ------------------------------------------------------------ /api

    async def api(self, request: Request) -> Response:
        account = self.account_of(request)
        if account is None:
            return JSONResponse({"ok": False, "error": api_error("signed_out")}, status_code=401)
        if not self.api_rate.allow(account.id):
            return JSONResponse({"ok": False, "error": api_error("busy")}, status_code=429)
        body: dict[str, Any] = dict(request.query_params)
        if request.method == "POST":
            if not self.origin_ok(request) or not self.csrf_ok(
                request, request.headers.get("x-csrf-token", "")
            ):
                return JSONResponse({"ok": False, "error": api_error("origin")}, status_code=403)
            raw = await read_body(request, MAX_BODY)
            if raw is None:
                return JSONResponse({"ok": False, "error": api_error("too_large")}, status_code=413)
            try:
                parsed = json.loads(raw or b"{}")
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                return JSONResponse({"ok": False, "error": api_error("bad_input")}, status_code=400)
            body = parsed
        name = str(request.path_params.get("name") or "")
        try:
            data = await self._api_call(account, request.method, name, body)
        except BadInput as exc:
            error = {**api_error("bad_input"), "field": str(exc)}
            return JSONResponse({"ok": False, "error": error}, status_code=400)
        if data is None:
            return JSONResponse({"ok": False, "error": api_error("not_found")}, status_code=404)
        self.registry.touch(account.id, time.time())
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    async def _api_call(
        self, account: Account, method: str, name: str, body: dict[str, Any]
    ) -> dict[str, Any] | None:
        argv: list[str] | None = None
        text = ""
        if method == "GET" and name == "me":
            return {"ok": True, "login": account.login, "version": __version__}
        if method == "GET" and name == "today":
            argv = ["today"]
        elif method == "GET" and name == "next":
            stage = body.get("stage")
            argv = ["next", "--count", "1"]
            if stage:
                if stage not in STAGES:
                    raise BadInput("stage")
                argv += ["--stage", str(stage)]
        elif method == "GET" and name == "status":
            argv = ["status"]
        elif method == "GET" and name == "forecast":
            argv = ["forecast", "--days", str(_number(body, "days", 1, 90, 14))]
        elif method == "GET" and name == "plan":
            argv = ["plan", "show"]
        elif method == "GET" and name == "courses":
            argv = ["course", "list"]
        elif method == "GET" and name == "quiz":
            lang = str(body.get("lang") or "")
            levels = str(body.get("levels") or "a1-b2")
            if not LANG.match(lang):
                raise BadInput("lang")
            if not LEVELS.match(levels):
                raise BadInput("levels")
            count = _number(body, "count", 1, 20, 6)
            argv = ["quiz", "--lang", lang, "--levels", levels.lower(), "--count", str(count)]
        elif method == "POST" and name == "answer":
            card = _card(body)
            argv = ["answer", "--batch", "--stdin", "--next"]
            text = _answer_line(card, _text(body, "answer", 500))
        elif method == "POST" and name == "reveal":
            argv = ["reveal", "--card", _card(body)]
        elif method == "POST" and name == "grade":
            grade = body.get("grade")
            if grade not in GRADES:
                raise BadInput("grade")
            argv = ["grade", "--card", _card(body), "--grade", str(grade), "--next"]
        elif method == "POST" and name == "regrade":
            grade = body.get("grade")
            if grade not in GRADES[1:]:
                raise BadInput("grade")
            argv = ["regrade", "--card", _card(body), "--grade", str(grade)]
        elif method == "POST" and name == "flag":
            card = _card(body)
            argv = ["flag", "--card", card, "--clear" if body.get("clear") else "--skip"]
        elif method == "POST" and name == "note":
            card = _card(body)
            if body.get("clear"):
                argv = ["note", "--card", card, "--clear"]
            else:
                text = _text(body, "note", store.NOTE_MAX)
                if not text.strip():
                    raise BadInput("note")
                argv = ["note", "--card", card, "--stdin"]
        elif method == "POST" and name == "more":
            count = _number(body, "count", 0, 100, 0)
            reviews = _number(body, "reviews", 0, 200, 0)
            if count + reviews < 1:
                raise BadInput("count")
            argv = ["today", "--extra", str(count), "--reviews", str(reviews), "--next"]
        elif method == "POST" and name == "plan":
            settings = body.get("settings")
            if (
                not isinstance(settings, list)
                or not 1 <= len(settings) <= 20
                or not all(
                    isinstance(s, str) and len(s) <= 200 and ASSIGNMENT.match(s) for s in settings
                )
            ):
                raise BadInput("settings")
            argv = ["plan", "set", *settings]
        elif method == "POST" and name == "commit":
            token = body.get("token")
            if not isinstance(token, str) or not TOKEN.match(token):
                raise BadInput("token")
            argv = ["commit", "--confirm", token]
        elif method == "POST" and name == "setup":
            languages = body.get("languages")
            settings = body.get("settings") or []
            if (
                not isinstance(languages, list)
                or not 1 <= len(languages) <= 6
                or not all(isinstance(item, str) and len(item) <= 20 for item in languages)
            ):
                raise BadInput("languages")
            if not isinstance(settings, list) or len(settings) > 20:
                raise BadInput("settings")
            if not all(isinstance(s, str) and len(s) <= 200 for s in settings):
                raise BadInput("settings")
            new = _number(body, "new_per_day", 0, 100, 15)
            zone = self.registry.timezone(account.id)
            return await anyio.to_thread.run_sync(
                self.service.setup, account.id, languages, new, settings, zone
            )
        elif method == "POST" and name == "quiz":
            answers = body.get("answers")
            if not isinstance(answers, list) or not 1 <= len(answers) <= 200:
                raise BadInput("answers")
            lines = []
            for item in answers:
                if not isinstance(item, dict):
                    raise BadInput("answers")
                lines.append(_answer_line(_card(item), _text(item, "answer", 500)))
            argv = ["quiz", "--check", "--stdin"]
            text = "\n".join(lines)
        if argv is None:
            return None
        result: dict[str, Any] = await anyio.to_thread.run_sync(
            self.service.call, account.id, argv, text
        )
        return result

    # ------------------------------------------------------------ the routes

    def routes(self) -> list[Route]:
        return [
            Route("/app", self.app_redirect, methods=["GET"]),
            Route("/app/", self.app_page, methods=["GET"]),
            Route("/app/login", self.sign_in, methods=["GET", "POST"]),
            Route("/app/logout", self.sign_out, methods=["POST"]),
            Route("/app/manifest.webmanifest", self.manifest, methods=["GET"]),
            Route("/app/sw.js", self.worker, methods=["GET"]),
            Route("/static/app.js", self.script, methods=["GET"]),
            Route(pages.STYLE, self.style, methods=["GET"]),
            Route(pages.SVG_ICON, self.svg, methods=["GET"]),
            Route("/account", self.account, methods=["GET", "POST"]),
            Route("/account/export", self.export, methods=["GET"]),
            Route("/recover", self.recover, methods=["GET", "POST"]),
            Route("/recover/{token}", self.reset, methods=["GET", "POST"]),
            Route("/device", self.device, methods=["GET", "POST"]),
            Route("/device/authorize", self.devices.authorize, methods=["POST"]),
            Route("/device/token", self.devices.token, methods=["POST"]),
            Route("/api/{name}", self.api, methods=["GET", "POST"]),
        ]


def api_error(code: str) -> dict[str, str]:
    """An error of the session page's addresses with its message for the learner."""
    return {"code": code, "message": assets.text(f"server.api_errors.{code}")}


async def read_body(request: Request, limit: int) -> bytes | None:
    """The body of a request, or None when it is longer than `limit` (read no further)."""
    size = request.headers.get("content-length")
    if size is not None and (not size.isdigit() or int(size) > limit):
        return None
    parts: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            return None
        parts.append(chunk)
    return b"".join(parts)


def bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


def sync_route(registry: Registry, settings: Settings, service: Service, provider: Any) -> Route:
    """POST /sync: a linked folder's synchronisation, with the account's access token."""
    rate = Rate(120)
    challenge = {
        "WWW-Authenticate": (
            f'Bearer resource_metadata="{settings.url}/.well-known/oauth-protected-resource/mcp"'
        )
    }

    async def handle(request: Request) -> Response:
        token = await provider.load_access_token(bearer(request)) if bearer(request) else None
        if token is None or not token.subject or token.resource != settings.resource:
            return JSONResponse(
                {"ok": False, "error": {"code": "signed_out"}}, status_code=401, headers=challenge
            )
        account = str(token.subject)
        if not rate.allow(account):
            return JSONResponse({"ok": False, "error": {"code": "sync_busy"}}, status_code=429)
        raw = await read_body(request, SYNC_BODY)
        if raw is None:
            return JSONResponse({"ok": False, "error": api_error("too_large")}, status_code=413)
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            return JSONResponse({"ok": False, "error": {"code": "bad_input"}}, status_code=400)
        found = registry.account(account)
        if found is None:
            return JSONResponse({"ok": False, "error": {"code": "signed_out"}}, status_code=401)
        registry.touch(account, time.time())
        data = await anyio.to_thread.run_sync(
            service.sync, account, payload, found.login, registry.timezone(account)
        )
        status = 200 if data.get("ok") else 400
        return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})

    return Route("/sync", handle, methods=["POST"])
