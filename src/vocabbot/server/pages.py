"""The few web pages of the server: the sign-in, the start page and the privacy note."""

from __future__ import annotations

from html import escape

from vocabbot import __version__, assets

STYLE = """
:root { color-scheme: light dark; --ink: #1d2433; --muted: #5b6475; --line: #d8dde6;
  --card: #ffffff; --page: #f3f5f9; --accent: #2f5bd3; --bad: #b42318; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e7eaf0; --muted: #a3abba; --line: #343b4a; --card: #1b2030;
    --page: #11151f; --accent: #8aa8ff; --bad: #ff8a80; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 34rem; margin: 0 auto; padding: 2rem 1rem 3rem; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
h2 { font-size: 1.1rem; margin: 0 0 .75rem; }
p { margin: .5rem 0; }
.muted { color: var(--muted); font-size: .9rem; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 1.25rem; margin-top: 1rem; }
label { display: block; margin: .75rem 0 .25rem; font-weight: 600; font-size: .9rem; }
input { width: 100%; padding: .6rem .7rem; font: inherit; color: inherit;
  background: transparent; border: 1px solid var(--line); border-radius: 8px; }
button { margin-top: 1rem; width: 100%; padding: .7rem; font: inherit; font-weight: 600;
  color: #fff; background: var(--accent); border: 0; border-radius: 8px; cursor: pointer; }
.error { color: var(--bad); font-weight: 600; }
code { overflow-wrap: anywhere; }
"""

HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


def _t(name: str, **values: str) -> str:
    return escape(assets.text(f"server.{name}", **values))


def sign_in(
    request_id: str,
    app: str,
    host: str,
    open_signup: bool,
    error: str | None = None,
    login: str = "",
) -> str:
    hidden = f'<input type="hidden" name="request" value="{escape(request_id)}">'
    problem = f'<p class="error" role="alert">{_t(f"errors.{error}")}</p>' if error else ""
    invite = (
        ""
        if open_signup
        else f'<label for="invite">{_t("invite")}</label>'
        '<input id="invite" name="invite" autocomplete="off" required>'
    )
    body = (
        f"<h1>{_t('connect', app=app)}</h1>"
        f'<p class="muted">{_t("connect_hint", app=app, host=host)}</p>{problem}'
        f'<form class="card" method="post" action="/login">{hidden}'
        f'<input type="hidden" name="action" value="login"><h2>{_t("login_title")}</h2>'
        f'<label for="login">{_t("login")}</label>'
        f'<input id="login" name="login" value="{escape(login)}" autocomplete="username"'
        ' autocapitalize="none" required>'
        f'<label for="password">{_t("password")}</label>'
        '<input id="password" name="password" type="password" autocomplete="current-password"'
        " required>"
        f'<button type="submit">{_t("login_button")}</button></form>'
        f'<form class="card" method="post" action="/login">{hidden}'
        f'<input type="hidden" name="action" value="signup"><h2>{_t("signup_title")}</h2>'
        f'<p class="muted">{_t("signup_rules")}</p>'
        f'<label for="new-login">{_t("login")}</label>'
        '<input id="new-login" name="login" autocomplete="username" autocapitalize="none"'
        " required>"
        f'<label for="new-password">{_t("password")}</label>'
        '<input id="new-password" name="password" type="password" autocomplete="new-password"'
        ' minlength="12" required>'
        f'<label for="new-password2">{_t("password_again")}</label>'
        '<input id="new-password2" name="password2" type="password" autocomplete="new-password"'
        ' minlength="12" required>'
        f"{invite}"
        f'<button type="submit">{_t("signup_button")}</button></form>'
        f'<p class="muted"><a href="/privacy">{_t("privacy_link")}</a></p>'
    )
    return _page(assets.text("server.title"), body)


def expired() -> str:
    body = f"<h1>{_t('expired_title')}</h1><p>{_t('expired')}</p>"
    return _page(assets.text("server.expired_title"), body)


def home(resource: str) -> str:
    body = (
        f"<h1>{_t('title')}</h1><p>{_t('home')}</p>"
        f"<p>{_t('home_address')}<br><code>{escape(resource)}</code></p>"
        f'<p class="muted"><a href="/privacy">{_t("privacy_link")}</a> · {__version__}</p>'
    )
    return _page(assets.text("server.title"), body)


def privacy() -> str:
    paragraphs = "".join(f"<p>{escape(text)}</p>" for text in assets.paragraphs("server.privacy"))
    body = f"<h1>{_t('privacy_title')}</h1>{paragraphs}"
    return _page(assets.text("server.privacy_title"), body)
