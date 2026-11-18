"""The web pages of the server: the sign-ins, the account, recovery, the start page and privacy.

The look follows shadcn/ui (its neutral colour tokens, cards, tabs, inputs and
buttons) with the Geist typeface, written as plain CSS. The pages run one
script only, which reads the browser's time zone into the sign-up forms; the
Content-Security-Policy allows exactly that script by its hash, and the tabs
switch through radio buttons. The session page (/app/) is static/app.html with
static/app.js.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from functools import cache
from html import escape
from importlib import resources
from typing import Any

from vocabbot import __version__, assets

FONT = "/static/geist.woff2"
ICON = "/static/vocabbot.png"
SVG_ICON = "/static/vocabbot.svg"

STYLE = """
@font-face { font-family: "Geist"; src: url("/static/geist.woff2") format("woff2");
  font-weight: 100 900; font-style: normal; font-display: swap; }
:root {
  color-scheme: light dark;
  --background: oklch(1 0 0); --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0); --muted: oklch(0.97 0 0); --muted-foreground: oklch(0.556 0 0);
  --border: oklch(0.922 0 0); --input: oklch(0.922 0 0); --ring: oklch(0.708 0 0);
  --primary: oklch(0.205 0 0); --primary-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.577 0.245 27.325); --grid: oklch(0.145 0 0 / 5%);
  --shadow: 0 1px 2px oklch(0 0 0 / 5%), 0 8px 24px -12px oklch(0 0 0 / 12%);
  --radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --background: oklch(0.145 0 0); --foreground: oklch(0.985 0 0);
    --card: oklch(0.18 0 0); --muted: oklch(0.269 0 0); --muted-foreground: oklch(0.708 0 0);
    --border: oklch(1 0 0 / 10%); --input: oklch(1 0 0 / 15%); --ring: oklch(0.556 0 0);
    --primary: oklch(0.922 0 0); --primary-foreground: oklch(0.205 0 0);
    --destructive: oklch(0.704 0.191 22.216); --grid: oklch(1 0 0 / 6%);
    --shadow: 0 1px 2px oklch(0 0 0 / 40%), 0 12px 32px -16px oklch(0 0 0 / 60%);
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  background: var(--background); color: var(--foreground);
  font: 400 14px/1.5 "Geist", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}
.grid { position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background-image: linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 44px 44px; background-position: center top;
  -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 100%);
  mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 100%); }
.shell { width: 100%; max-width: 400px; margin: 0 auto; padding: 56px 16px 40px; }
.brand { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: 12px; margin-bottom: 24px; }
.pair { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.mark { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
  font-weight: 600; font-size: 18px; letter-spacing: -0.02em; }
.mark.app { background: var(--card); border: 1px solid var(--border); box-shadow: var(--shadow); }
.mark.vb { overflow: hidden; box-shadow: var(--shadow); }
.mark.vb svg { display: block; width: 100%; height: 100%; }
.wire { width: 36px; height: 1px; border-top: 1px dashed var(--muted-foreground); opacity: .6; }
h1 { margin: 0; font-size: 22px; line-height: 1.25; font-weight: 600; letter-spacing: -0.025em;
  text-wrap: balance; }
.lead { margin: 0; color: var(--muted-foreground); text-wrap: pretty; }
.host { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12.5px;
  padding: 1px 6px; border: 1px solid var(--border); border-radius: 6px; background: var(--muted); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 20px; }
.tab-input { position: absolute; opacity: 0; pointer-events: none; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 3px; margin-bottom: 20px;
  background: var(--muted); border-radius: 8px; }
.tab { text-align: center; padding: 6px 8px; border-radius: 6px; font-weight: 500;
  color: var(--muted-foreground); cursor: pointer; user-select: none;
  transition: background .15s, color .15s, box-shadow .15s; }
.tab:hover { color: var(--foreground); }
#tab-login:checked ~ .tabs [for="tab-login"], #tab-signup:checked ~ .tabs [for="tab-signup"] {
  background: var(--background); color: var(--foreground);
  box-shadow: 0 1px 2px oklch(0 0 0 / 10%), 0 0 0 1px var(--border); }
#tab-login:focus-visible ~ .tabs [for="tab-login"],
#tab-signup:focus-visible ~ .tabs [for="tab-signup"] {
  outline: 2px solid var(--ring); outline-offset: 2px; }
.panel { display: none; }
#tab-login:checked ~ .panel-login, #tab-signup:checked ~ .panel-signup { display: block; }
.field { display: grid; gap: 6px; margin-bottom: 16px; }
label.label { font-weight: 500; font-size: 13.5px; }
.input { width: 100%; height: 38px; padding: 0 12px; font: inherit; color: inherit;
  background: transparent; border: 1px solid var(--input); border-radius: 8px;
  box-shadow: 0 1px 2px oklch(0 0 0 / 5%); outline: none;
  transition: border-color .15s, box-shadow .15s; }
.input::placeholder { color: var(--muted-foreground); opacity: .7; }
.input:focus-visible { border-color: var(--ring);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--ring) 35%, transparent); }
.input.code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  text-transform: uppercase; letter-spacing: .08em; }
.hint { margin: 0; color: var(--muted-foreground); font-size: 12.5px; line-height: 1.45; }
.btn { display: inline-flex; align-items: center; justify-content: center; width: 100%;
  height: 40px; margin-top: 4px; border: 0; border-radius: 8px; cursor: pointer;
  font: inherit; font-weight: 500; background: var(--primary); color: var(--primary-foreground);
  transition: opacity .15s, box-shadow .15s; }
.btn:hover { opacity: .9; }
.btn:focus-visible { outline: none;
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--ring) 45%, transparent); }
.alert { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 16px; padding: 12px 14px;
  border: 1px solid color-mix(in oklch, var(--destructive) 45%, transparent);
  border-radius: var(--radius); color: var(--destructive); background: var(--card); }
.alert svg { flex: none; margin-top: 2px; }
.foot { margin-top: 20px; text-align: center; color: var(--muted-foreground); font-size: 12.5px; }
.foot a, .prose a { color: inherit; text-decoration: underline; text-underline-offset: 3px; }
.foot a:hover { color: var(--foreground); }
.address { display: block; margin-top: 8px; padding: 10px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--muted); user-select: all;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 13px;
  overflow-wrap: anywhere; }
.prose p { margin: 0 0 12px; color: var(--muted-foreground); }
.prose p:last-child { margin-bottom: 0; }
.steps { margin: 16px 0 0; padding: 0; list-style: none; display: grid; gap: 8px;
  color: var(--muted-foreground); }
.steps b { color: var(--foreground); font-weight: 500; }
.shell.wide { max-width: 560px; }
.stack { display: grid; gap: 16px; }
.card h2 { margin: 0 0 6px; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
.card p.note { margin: 0 0 12px; color: var(--muted-foreground); }
.btn.secondary { background: transparent; color: var(--foreground);
  border: 1px solid var(--border); }
.btn.danger { background: var(--destructive); color: oklch(0.985 0 0); }
.btn.inline { width: auto; height: 32px; padding: 0 12px; margin: 0; font-size: 13px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.row form { margin: 0; }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.list li { display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; }
.list .what { display: grid; min-width: 0; }
.list .what b { font-weight: 500; overflow-wrap: anywhere; }
.list .what span { color: var(--muted-foreground); font-size: 12.5px; }
.ok { margin-bottom: 16px; padding: 12px 14px; border: 1px solid var(--border);
  border-radius: var(--radius); background: var(--card); }
.nav { display: flex; justify-content: center; gap: 16px; margin: -8px 0 20px;
  font-size: 13px; }
.nav a, .nav button { color: var(--muted-foreground); background: none; border: 0; padding: 0;
  font: inherit; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.nav a:hover, .nav button:hover { color: var(--foreground); }
.nav form { margin: 0; }
.code-big { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 20px; letter-spacing: .12em; text-align: center; text-transform: uppercase; }
"""

# the one script of the pages: the browser's time zone into the sign-up forms
ZONE_SCRIPT = (
    "document.querySelectorAll('input[name=\"tz\"]').forEach(function(i){try{"
    'i.value=Intl.DateTimeFormat().resolvedOptions().timeZone||""}catch(e){}});'
)
ZONE_HASH = base64.b64encode(hashlib.sha256(ZONE_SCRIPT.encode()).digest()).decode()

HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        f"default-src 'none'; script-src 'sha256-{ZONE_HASH}'; style-src 'unsafe-inline';"
        " font-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
    ),
    # same-origin keeps the address from other sites and lets a form name its origin
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
# the session page: its own script and style, recordings from Wikimedia Commons
APP_HEADERS = {
    **HEADERS,
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        " font-src 'self'; img-src 'self' data:; media-src https://upload.wikimedia.org;"
        " connect-src 'self'; manifest-src 'self'; worker-src 'self'; form-action 'self';"
        " frame-ancestors 'none'; base-uri 'none'"
    ),
}

ALERT = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>'
)


def font() -> bytes:
    """The Geist typeface (SIL Open Font License 1.1, see static/geist-OFL.txt)."""
    return (resources.files("vocabbot.server") / "static" / "geist.woff2").read_bytes()


def icon() -> bytes:
    """VocabBot's avatar as a rounded tile: the favicon and the icon MCP clients show."""
    return (resources.files("vocabbot.server") / "static" / "vocabbot.png").read_bytes()


@cache
def mark() -> str:
    """The avatar as inline SVG for the pages (scripts/make_icon.py draws it)."""
    return (resources.files("vocabbot.server") / "static" / "vocabbot.svg").read_text("utf-8")


def card_title() -> str:
    """The card's name, as the chat application lists it."""
    texts = assets.read_json(assets.data_root() / "i18n" / "pl.json")
    return str(texts["server"]["card"]["title"])


def card() -> str:
    """The card a chat application shows beside the session's results (MCP Apps).

    The template (static/card.html) gets the labels from data/i18n/pl.json, so
    every text a learner reads stays there.
    """
    texts = assets.read_json(assets.data_root() / "i18n" / "pl.json")
    labels = {
        "card": texts["server"]["card"],
        "genders": texts["genders"],
        "forms": texts["forms"],
        "phases": texts["phases"],
        "pos": texts["pos"],
        "grades": texts["grades"],
    }
    blob = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    template = (resources.files("vocabbot.server") / "static" / "card.html").read_text("utf-8")
    return template.replace("/*VOCABBOT_LABELS*/{}", blob).replace(
        "/*VOCABBOT_VERSION*/", __version__
    )


def _page(title: str, body: str, *, index: bool = False, wide: bool = False) -> str:
    robots = "" if index else '<meta name="robots" content="noindex, nofollow">'
    shell = "shell wide" if wide else "shell"
    script = f"<script>{ZONE_SCRIPT}</script>" if 'name="tz"' in body else ""
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        f'{robots}<link rel="icon" href="{ICON}" type="image/png">'
        f'<link rel="preload" href="{FONT}" as="font" type="font/woff2" crossorigin>'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head>"
        f'<body><div class="grid" aria-hidden="true"></div><main class="{shell}">{body}</main>'
        f"{script}</body></html>"
    )


def _t(name: str, **values: str) -> str:
    return escape(assets.text(f"server.{name}", **values))


def _brand(title: str, lead: str, app: str | None = None) -> str:
    marks = f'<span class="mark vb" aria-hidden="true">{mark().strip()}</span>'
    if app is not None:
        initial = escape((app.strip()[:1] or "?").upper())
        marks = (
            f'<span class="mark app" aria-hidden="true">{initial}</span>'
            f'<span class="wire" aria-hidden="true"></span>{marks}'
        )
    return (
        f'<header class="brand"><div class="pair">{marks}</div>'
        f'<h1>{title}</h1><p class="lead">{lead}</p></header>'
    )


def _field(
    name: str,
    label: str,
    *,
    id_: str,
    kind: str = "text",
    value: str = "",
    hint: str = "",
    extra: str = "",
) -> str:
    hint_html = f'<p class="hint" id="{id_}-hint">{hint}</p>' if hint else ""
    described = f' aria-describedby="{id_}-hint"' if hint else ""
    classes = "input code" if name == "invite" else "input"
    return (
        f'<div class="field"><label class="label" for="{id_}">{label}</label>'
        f'<input class="{classes}" id="{id_}" name="{name}" type="{kind}"'
        f' value="{escape(value)}"{described} {extra} required>{hint_html}</div>'
    )


def sign_in(
    request_id: str,
    app: str,
    host: str,
    open_signup: bool,
    error: str | None = None,
    login: str = "",
    tab: str = "login",
) -> str:
    hidden = (
        f'<input type="hidden" name="request" value="{escape(request_id)}">'
        '<input type="hidden" name="tz" value="">'
    )
    problem = (
        f'<div class="alert" role="alert">{ALERT}<span>{_t(f"errors.{error}")}</span></div>'
        if error
        else ""
    )
    lead = _t("connect_hint", app=app)
    if host:
        lead += f' {_t("return_to")} <span class="host">{escape(host)}</span>'
    login_form = (
        f'<form class="panel panel-login" method="post" action="/login">{hidden}'
        '<input type="hidden" name="action" value="login">'
        + _field(
            "login",
            _t("login"),
            id_="login",
            value=login if tab == "login" else "",
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
            + (" autofocus" if tab == "login" else ""),
        )
        + _field(
            "password",
            _t("password"),
            id_="password",
            kind="password",
            extra='autocomplete="current-password"',
        )
        + f'<button class="btn" type="submit">{_t("login_button")}</button></form>'
    )
    invite = (
        ""
        if open_signup
        else _field(
            "invite",
            _t("invite"),
            id_="invite",
            hint=_t("invite_hint"),
            extra='autocomplete="off" autocapitalize="characters" spellcheck="false"'
            ' placeholder="ABCD-EFGH-JKMN" maxlength="20"',
        )
    )
    signup_form = (
        f'<form class="panel panel-signup" method="post" action="/login">{hidden}'
        '<input type="hidden" name="action" value="signup">'
        + _field(
            "login",
            _t("login"),
            id_="new-login",
            value=login if tab == "signup" else "",
            hint=_t("login_hint"),
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
            ' minlength="3" maxlength="40"' + (" autofocus" if tab == "signup" else ""),
        )
        + _field(
            "password",
            _t("password"),
            id_="new-password",
            kind="password",
            hint=_t("password_hint"),
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + _field(
            "password2",
            _t("password_again"),
            id_="new-password2",
            kind="password",
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + invite
        + f'<button class="btn" type="submit">{_t("signup_button")}</button></form>'
    )
    checked_login = " checked" if tab != "signup" else ""
    checked_signup = " checked" if tab == "signup" else ""
    body = (
        _brand(_t("connect", app=app), lead, app=app) + problem + '<section class="card">'
        f'<input class="tab-input" type="radio" name="tab" id="tab-login"{checked_login}>'
        f'<input class="tab-input" type="radio" name="tab" id="tab-signup"{checked_signup}>'
        f'<div class="tabs"><label class="tab" for="tab-login">{_t("tab_login")}</label>'
        f'<label class="tab" for="tab-signup">{_t("tab_signup")}</label></div>'
        f"{login_form}{signup_form}</section>"
        f'<p class="foot">{_t("disconnect", app=app)}<br>'
        f'<a href="/privacy">{_t("privacy_link")}</a> · VocabBot {escape(__version__)}</p>'
    )
    return _page(assets.text("server.title"), body)


def _alert(error: str | None) -> str:
    if not error:
        return ""
    return f'<div class="alert" role="alert">{ALERT}<span>{_t(f"errors.{error}")}</span></div>'


def _ok(message: str | None) -> str:
    return f'<div class="ok" role="status">{escape(message)}</div>' if message else ""


def _hidden(name: str, value: str) -> str:
    return f'<input type="hidden" name="{name}" value="{escape(value)}">'


def when(moment: float) -> str:
    """A moment as the pages show it: day.month.year hour:minute (UTC)."""
    stamp = datetime.fromtimestamp(moment, timezone.utc)
    return stamp.strftime("%d.%m.%Y %H:%M UTC")


def web_sign_in(
    target: str,
    open_signup: bool,
    mail_ready: bool,
    error: str | None = None,
    login: str = "",
    tab: str = "login",
) -> str:
    """The sign-in of the session page and the account page: a browser session of 30 days."""
    hidden = _hidden("next", target) + '<input type="hidden" name="tz" value="">'
    login_form = (
        f'<form class="panel panel-login" method="post" action="/app/login">{hidden}'
        + _hidden("action", "login")
        + _field(
            "login",
            _t("login"),
            id_="login",
            value=login if tab == "login" else "",
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
            + (" autofocus" if tab == "login" else ""),
        )
        + _field(
            "password",
            _t("password"),
            id_="password",
            kind="password",
            extra='autocomplete="current-password"',
        )
        + f'<button class="btn" type="submit">{_t("web.login_button")}</button></form>'
    )
    invite = (
        ""
        if open_signup
        else _field(
            "invite",
            _t("invite"),
            id_="invite",
            hint=_t("invite_hint"),
            extra='autocomplete="off" autocapitalize="characters" spellcheck="false"'
            ' placeholder="ABCD-EFGH-JKMN" maxlength="20"',
        )
    )
    email = (
        _field(
            "email",
            _t("web.email"),
            id_="email",
            kind="email",
            hint=_t("web.email_hint"),
            extra='autocomplete="email" maxlength="254"',
        ).replace(" required>", ">")
        if mail_ready
        else ""
    )
    signup_form = (
        f'<form class="panel panel-signup" method="post" action="/app/login">{hidden}'
        + _hidden("action", "signup")
        + _field(
            "login",
            _t("login"),
            id_="new-login",
            value=login if tab == "signup" else "",
            hint=_t("login_hint"),
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
            ' minlength="3" maxlength="40"' + (" autofocus" if tab == "signup" else ""),
        )
        + _field(
            "password",
            _t("password"),
            id_="new-password",
            kind="password",
            hint=_t("password_hint"),
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + _field(
            "password2",
            _t("password_again"),
            id_="new-password2",
            kind="password",
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + email
        + invite
        + f'<button class="btn" type="submit">{_t("web.signup_button")}</button></form>'
    )
    checked_login = " checked" if tab != "signup" else ""
    checked_signup = " checked" if tab == "signup" else ""
    forgot = f'<a href="/recover">{_t("web.forgot")}</a> · ' if mail_ready else ""
    body = (
        _brand(_t("web.sign_in_title"), _t("web.sign_in_lead"))
        + _alert(error)
        + '<section class="card">'
        f'<input class="tab-input" type="radio" name="tab" id="tab-login"{checked_login}>'
        f'<input class="tab-input" type="radio" name="tab" id="tab-signup"{checked_signup}>'
        f'<div class="tabs"><label class="tab" for="tab-login">{_t("tab_login")}</label>'
        f'<label class="tab" for="tab-signup">{_t("tab_signup")}</label></div>'
        f"{login_form}{signup_form}</section>"
        f'<p class="foot">{forgot}<a href="/privacy">{_t("privacy_link")}</a> · VocabBot'
        f" {escape(__version__)}</p>"
    )
    return _page(assets.text("server.web.sign_in_title"), body)


def _nav(csrf: str, here: str) -> str:
    links = []
    if here != "app":
        links.append(f'<a href="/app/">{_t("web.nav_app")}</a>')
    if here != "account":
        links.append(f'<a href="/account">{_t("web.nav_account")}</a>')
    links.append(
        f'<form method="post" action="/app/logout">{_hidden("csrf", csrf)}'
        f'<button type="submit">{_t("web.logout")}</button></form>'
    )
    return f'<nav class="nav">{"".join(links)}</nav>'


def account(
    login: str,
    created: float,
    csrf: str,
    *,
    has_email: bool,
    mail_ready: bool,
    grants: list[Any],
    can_export: bool,
    message: str | None = None,
    error: str | None = None,
) -> str:
    """The account page: the e-mail for recovery, the connections, the data, the removal."""
    token = _hidden("csrf", csrf)
    if mail_ready:
        state = _t("web.email_set") if has_email else _t("web.email_none")
        # the address decides where a new password goes, so a change needs the password
        remove = (
            f'<button class="btn secondary inline" type="submit" name="action"'
            f' value="email_remove" formnovalidate>{_t("web.email_remove")}</button>'
            if has_email
            else ""
        )
        email = (
            f'<section class="card"><h2>{_t("web.email_title")}</h2><p class="note">{state}</p>'
            f'<form method="post" action="/account">{token}'
            + _field(
                "email",
                _t("web.email"),
                id_="email",
                kind="email",
                hint=_t("web.email_hint"),
                extra='autocomplete="email" maxlength="254"',
            ).replace(" required>", ">")
            + _field(
                "password",
                _t("web.email_password"),
                id_="email-password",
                kind="password",
                extra='autocomplete="current-password"',
            )
            + '<div class="row"><button class="btn inline" type="submit" name="action"'
            f' value="email">{_t("web.email_save")}</button>{remove}</div></form></section>'
        )
    else:
        email = (
            f'<section class="card"><h2>{_t("web.email_title")}</h2>'
            f'<p class="note">{_t("web.email_unavailable")}</p></section>'
        )
    if grants:
        items = "".join(
            f'<li><span class="what"><b>{escape(grant.name)}</b>'
            f"<span>{_t('web.device_since', when=when(grant.created))} · "
            f"{_t('web.device_used', when=when(grant.used))}</span></span>"
            f'<form method="post" action="/account">{token}{_hidden("action", "unlink")}'
            f'{_hidden("grant", grant.id)}<button class="btn secondary inline" type="submit">'
            f"{_t('web.unlink')}</button></form></li>"
            for grant in grants
        )
        devices = f'<ul class="list">{items}</ul>'
    else:
        devices = f'<p class="note">{_t("web.devices_none")}</p>'
    data = (
        f'<p class="note">{_t("web.data_lead")}</p>'
        f'<a class="btn secondary" href="/account/export">{_t("web.export")}</a>'
        if can_export
        else f'<p class="note">{_t("web.export_none")}</p>'
    )
    delete = (
        f'<section class="card"><h2>{_t("web.delete_title")}</h2>'
        f'<p class="note">{_t("web.delete_lead")}</p>'
        f'<form method="post" action="/account">{token}{_hidden("action", "delete")}'
        + _field(
            "password",
            _t("web.delete_password"),
            id_="delete-password",
            kind="password",
            extra='autocomplete="current-password"',
        )
        + f'<button class="btn danger" type="submit">{_t("web.delete_button")}</button>'
        "</form></section>"
    )
    body = (
        _brand(_t("web.account_title"), _t("web.account_lead", login=login, created=when(created)))
        + _nav(csrf, "account")
        + _ok(message)
        + _alert(error)
        + '<div class="stack">'
        + f'<section class="card"><h2>{_t("web.devices_title")}</h2>{devices}</section>'
        + email
        + f'<section class="card"><h2>{_t("web.data_title")}</h2>{data}</section>'
        + delete
        + "</div>"
        + f'<p class="foot"><a href="/privacy">{_t("privacy_link")}</a> · VocabBot'
        f" {escape(__version__)}</p>"
    )
    return _page(assets.text("server.web.account_title"), body, wide=True)


def message_page(title: str, lead: str, link: tuple[str, str] | None = None) -> str:
    """A page with one message and one way on."""
    more = (
        f'<section class="card"><a class="btn" href="{escape(link[0])}">{escape(link[1])}</a>'
        "</section>"
        if link
        else ""
    )
    body = (
        _brand(escape(title), escape(lead))
        + more
        + f'<p class="foot"><a href="/">VocabBot</a> · <a href="/privacy">{_t("privacy_link")}'
        "</a></p>"
    )
    return _page(title, body)


def recover(error: str | None = None) -> str:
    body = (
        _brand(_t("web.recover_title"), _t("web.recover_lead"))
        + _alert(error)
        + '<section class="card"><form method="post" action="/recover">'
        + _field(
            "login",
            _t("login"),
            id_="login",
            extra='autocomplete="username" autocapitalize="none" spellcheck="false" autofocus',
        )
        + _field(
            "email", _t("web.email_plain"), id_="email", kind="email", extra='autocomplete="email"'
        )
        + f'<button class="btn" type="submit">{_t("web.recover_button")}</button></form>'
        "</section>" + f'<p class="foot"><a href="/app/login">{_t("web.back_to_login")}</a></p>'
    )
    return _page(assets.text("server.web.recover_title"), body)


def reset(token: str, login: str, error: str | None = None) -> str:
    body = (
        _brand(_t("web.reset_title"), _t("web.reset_lead", login=login))
        + _alert(error)
        + f'<section class="card"><form method="post" action="/recover/{escape(token)}">'
        + _field(
            "password",
            _t("password"),
            id_="password",
            kind="password",
            hint=_t("password_hint"),
            extra='autocomplete="new-password" minlength="12" maxlength="200" autofocus',
        )
        + _field(
            "password2",
            _t("password_again"),
            id_="password2",
            kind="password",
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + f'<button class="btn" type="submit">{_t("web.reset_button")}</button></form></section>'
    )
    return _page(assets.text("server.web.reset_title"), body)


def device(code: str, login: str | None, csrf: str, error: str | None = None) -> str:
    """The page that confirms the code of the program on a computer without a browser."""
    fields = _field(
        "code",
        _t("web.device_code"),
        id_="code",
        value=code,
        extra='autocomplete="off" autocapitalize="characters" spellcheck="false"'
        ' placeholder="ABCD-EFGH" maxlength="12"' + ("" if code else " autofocus"),
    ).replace('class="input"', 'class="input code"')
    if login is None:
        fields += _field(
            "login",
            _t("login"),
            id_="login",
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"',
        ) + _field(
            "password",
            _t("password"),
            id_="password",
            kind="password",
            extra='autocomplete="current-password"',
        )
        lead = _t("web.device_lead")
    else:
        lead = _t("web.device_lead") + " " + _t("web.device_as", login=login)
    body = (
        _brand(_t("web.device_title"), lead)
        + _alert(error)
        + '<section class="card"><form method="post" action="/device">'
        + _hidden("csrf", csrf)
        + fields
        + f'<button class="btn" type="submit">{_t("web.device_button")}</button></form>'
        "</section>" + f'<p class="foot"><a href="/privacy">{_t("privacy_link")}</a> · VocabBot'
        f" {escape(__version__)}</p>"
    )
    return _page(assets.text("server.web.device_title"), body)


@cache
def _app_template() -> str:
    return (resources.files("vocabbot.server") / "static" / "app.html").read_text("utf-8")


@cache
def app_labels() -> str:
    texts = assets.read_json(assets.data_root() / "i18n" / "pl.json")
    labels = {
        "app": texts["server"]["app"],
        "card": texts["server"]["card"],
        "genders": texts["genders"],
        "forms": texts["forms"],
        "phases": texts["phases"],
        "pos": texts["pos"],
        "grades": texts["grades"],
        "error_classes": texts["error_classes"],
        "weekdays": texts["weekdays"],
        "weekdays_short": texts["weekdays_short"],
        "languages": {code: assets.language_name(code) for code in assets.known_languages()},
    }
    return json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")


def app(login: str, csrf: str) -> str:
    """The session page: the labels, the account and the form token go into the template."""
    return (
        _app_template()
        .replace('"/*VOCABBOT_LABELS*/"', app_labels())
        .replace("/*VOCABBOT_LOGIN*/", escape(login, quote=True))
        .replace("/*VOCABBOT_CSRF*/", escape(csrf, quote=True))
        .replace("/*VOCABBOT_VERSION*/", __version__)
    )


def manifest() -> str:
    return json.dumps(
        {
            "name": "VocabBot",
            "short_name": "VocabBot",
            "description": assets.text("server.app.manifest_description"),
            "lang": "pl",
            "start_url": "/app/",
            "scope": "/app/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#171717",
            "icons": [
                {"src": ICON, "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": SVG_ICON, "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
            ],
        },
        ensure_ascii=False,
    )


def static_text(name: str) -> str:
    return (resources.files("vocabbot.server") / "static" / name).read_text("utf-8")


def expired() -> str:
    body = _brand(_t("expired_title"), _t("expired")) + (
        '<p class="foot"><a href="/">VocabBot</a> · '
        f'<a href="/privacy">{_t("privacy_link")}</a></p>'
    )
    return _page(assets.text("server.expired_title"), body)


def home(resource: str) -> str:
    body = (
        _brand(_t("title"), _t("home")) + '<section class="card prose">'
        f'<p>{_t("home_address")}</p><code class="address">{escape(resource)}</code>'
        f'<ul class="steps"><li><b>Claude</b> · {_t("home_claude")}</li>'
        f"<li><b>ChatGPT</b> · {_t('home_chatgpt')}</li></ul></section>"
        f'<section class="card prose" style="margin-top:16px"><p>{_t("home_browser")}</p>'
        f'<a class="btn" href="/app/">{_t("home_open")}</a></section>'
        f'<p class="foot"><a href="/privacy">{_t("privacy_link")}</a> · VocabBot'
        f" {escape(__version__)}</p>"
    )
    return _page(assets.text("server.title"), body, index=True)


def privacy() -> str:
    paragraphs = "".join(f"<p>{escape(text)}</p>" for text in assets.paragraphs("server.privacy"))
    body = (
        _brand(_t("privacy_title"), _t("privacy_lead"))
        + f'<section class="card prose">{paragraphs}</section>'
        + f'<p class="foot"><a href="/">VocabBot</a> · {escape(__version__)}</p>'
    )
    return _page(assets.text("server.privacy_title"), body, index=True)
