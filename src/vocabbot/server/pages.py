"""The few web pages of the server: the sign-in, the start page and the privacy note.

The look follows shadcn/ui (its neutral colour tokens, cards, tabs, inputs and
buttons) with the Geist typeface, written as plain CSS: the pages run no
script, so a strict Content-Security-Policy holds, and the tabs switch through
radio buttons.
"""

from __future__ import annotations

import json
from html import escape
from importlib import resources

from vocabbot import __version__, assets

FONT = "/static/geist.woff2"

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
.mark.vb { background: var(--primary); color: var(--primary-foreground);
  box-shadow: var(--shadow); }
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
"""

HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; font-src 'self'; img-src 'self' data:;"
        " frame-ancestors 'none'; base-uri 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

LOGO = "V"
ALERT = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>'
)


def font() -> bytes:
    """The Geist typeface (SIL Open Font License 1.1, see static/geist-OFL.txt)."""
    return (resources.files("vocabbot.server") / "static" / "geist.woff2").read_bytes()


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


def _page(title: str, body: str, *, index: bool = False) -> str:
    robots = "" if index else '<meta name="robots" content="noindex, nofollow">'
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        f'{robots}<link rel="preload" href="{FONT}" as="font" type="font/woff2" crossorigin>'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head>"
        f'<body><div class="grid" aria-hidden="true"></div><main class="shell">{body}</main>'
        "</body></html>"
    )


def _t(name: str, **values: str) -> str:
    return escape(assets.text(f"server.{name}", **values))


def _brand(title: str, lead: str, app: str | None = None) -> str:
    marks = f'<span class="mark vb">{LOGO}</span>'
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
    hidden = f'<input type="hidden" name="request" value="{escape(request_id)}">'
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
