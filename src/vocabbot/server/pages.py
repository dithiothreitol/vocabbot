"""The web pages of the server in Polish and English.

The start page, privacy, the sign-ins, the account, recovery and the device
code follow Vercel's Geist: the neutral colour tokens of the session page,
hairline borders, one dark primary and colour only where it means something.
The start page borrows from the AI assistants' own pages: a large headline and
a conversation with the assistant that runs a session, which plays as a loop.
Its pictures move with plain CSS. The pages run two scripts, allowed by their
hashes in the Content-Security-Policy: one reads the browser's time zone into
the sign-up forms and gives the copy buttons their action, the other shows the
start page's sections as they scroll into view and counts its numbers up. A
page without the second script shows everything at once.

The pages search engines index (the start page and privacy) carry a canonical
address, the links between their languages, Open Graph and schema.org data;
`robots()`, `sitemap()` and `llms()` write /robots.txt, /sitemap.xml and
/llms.txt.

The language of a page comes from `?lang=`, then from the cookie the language
switch sets, then from the browser's Accept-Language; Polish is the default.
The English texts live in data/i18n/en.json, and a text it lacks falls back to
Polish. The session page (/app/) is static/app.html with static/app.js and
stays Polish like the course.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import cache
from html import escape
from importlib import resources
from typing import Any
from urllib.parse import urlencode, urlsplit

from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse

from vocabbot import __version__, assets, store

FONT = "/static/geist.woff2"
ICON = "/static/vocabbot.png"
SVG_ICON = "/static/vocabbot.svg"
STYLE = "/static/site.css"
SOCIAL = "/static/social-{lang}.png"  # the picture of a shared link, 1200 by 630
SOCIAL_SIZE = (1200, 630)
LANGS = ("pl", "en")
LANG_COOKIE = "vocabbot_lang"
REPO = "https://github.com/dithiothreitol/vocabbot"
PACKAGE = "https://pypi.org/project/vocabbot/"
CODE_LICENSE = "https://www.apache.org/licenses/LICENSE-2.0"
COURSE_LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
COURSES = ("en", "de", "es", "fr", "it")  # the order of the courses on the start page
INDEXED = ("/", "/privacy")  # the pages of the sitemap
# what the crawlers of search engines and of AI assistants leave alone: forms and the API
PRIVATE = (
    "/app/",
    "/account",
    "/api/",
    "/login",
    "/authorize",
    "/token",
    "/register",
    "/revoke",
    "/device",
    "/recover",
    "/mcp",
    "/sync",
)
# crawlers named beside `*`, so their own group in a robots.txt never drops these rules
CRAWLERS = (
    "Googlebot",
    "Bingbot",
    "DuckDuckBot",
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Applebot",
    "Applebot-Extended",
    "CCBot",
)
MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@cache
def stylesheet() -> str:
    """The style of the pages (static/site.css), cached by browsers under its digest."""
    return (resources.files("vocabbot.server") / "static" / "site.css").read_text("utf-8")


@cache
def style_address() -> str:
    """The stylesheet's address with its digest, so a new style reaches every browser at once."""
    digest = hashlib.sha256(stylesheet().encode()).hexdigest()[:12]
    return f"{STYLE}?v={digest}"


# the one script of the pages: the browser's time zone into the sign-up forms and the copy buttons
SCRIPT = (
    "document.querySelectorAll('input[name=\"tz\"]').forEach(function(i){try{"
    'i.value=Intl.DateTimeFormat().resolvedOptions().timeZone||""}catch(e){}});'
    "document.querySelectorAll('[data-copy]').forEach(function(b){"
    "if(!navigator.clipboard)return;var l=b.getAttribute('aria-label');b.hidden=false;"
    "b.addEventListener('click',function(){var s=document.getElementById(b.dataset.copy);"
    "if(!s)return;navigator.clipboard.writeText(s.textContent.trim()).then(function(){"
    "b.classList.add('done');b.setAttribute('aria-label',b.dataset.done||l);"
    "clearTimeout(b.t);b.t=setTimeout(function(){b.classList.remove('done');"
    "b.setAttribute('aria-label',l)},1600)},function(){})})});"
)
SCRIPT_HASH = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
# the start page's script: sections appear as they scroll into view and numbers count up;
# without it, or with reduced motion, the page shows everything at once
MOTION = (
    "(function(){var d=document.documentElement;"
    "if(!('IntersectionObserver' in window)||(window.matchMedia&&"
    "matchMedia('(prefers-reduced-motion: reduce)').matches))return;"
    "d.classList.add('anim');"
    "function count(n){var to=+n.dataset.count,text=n.textContent,t0=0,"
    "f=new Intl.NumberFormat(d.lang);if(!(to>9))return;"
    "function step(t){if(!t0)t0=t;var p=Math.min(1,(t-t0)/1400),e=1-Math.pow(1-p,3);"
    "n.textContent=p<1?f.format(Math.round(to*e)):text;if(p<1)requestAnimationFrame(step)}"
    "requestAnimationFrame(step)}"
    "var io=new IntersectionObserver(function(es){es.forEach(function(e){"
    "if(!e.isIntersecting)return;io.unobserve(e.target);e.target.classList.add('in');"
    "e.target.querySelectorAll('[data-count]').forEach(count)})},"
    "{rootMargin:'0px 0px -8% 0px',threshold:.1});"
    "document.querySelectorAll('.reveal').forEach(function(n){io.observe(n)})})();"
)
MOTION_HASH = base64.b64encode(hashlib.sha256(MOTION.encode()).digest()).decode()

HEADERS = {
    "Cache-Control": "no-store",
    # no form-action: Chrome applies it to the redirect after the sign-in, to the chat's address
    "Content-Security-Policy": (
        f"default-src 'none'; script-src 'sha256-{SCRIPT_HASH}' 'sha256-{MOTION_HASH}';"
        " style-src 'self'; font-src 'self'; img-src 'self' data:; frame-ancestors 'none';"
        " base-uri 'none'"
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

# Lucide's outlines (ISC), as the session page draws them
PATHS: dict[str, tuple[str, ...]] = {
    "check": ("M20 6 9 17l-5-5",),
    "alert": ("M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "M12 8v4", "M12 16h.01"),
    "info": ("M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "M12 16v-4", "M12 8h.01"),
    "circle_check": ("M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "m9 12 2 2 4-4"),
    "arrow": ("M5 12h14", "m12 5 7 7-7 7"),
    "arrow_up": ("m5 12 7-7 7 7", "M12 19V5"),
    "chevron": ("m9 18 6-6-6-6",),
    "plus": ("M5 12h14", "M12 5v14"),
    "repeat": (
        "m17 2 4 4-4 4",
        "M3 11v-1a4 4 0 0 1 4-4h14",
        "m7 22-4-4 4-4",
        "M21 13v1a4 4 0 0 1-4 4H3",
    ),
    "languages": ("m5 8 6 6", "m4 14 6-6 2-3", "M2 5h12", "M7 2h1", "m22 22-5-10-5 10", "M14 18h6"),
    "devices": (
        "M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8",
        "M10 19v-3.96 3.15",
        "M7 19h5",
        "M18 12h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z",
    ),
    "shield": (
        "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0"
        " 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
        "m9 12 2 2 4-4",
    ),
    "chat": ("M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",),
    "terminal": ("m4 17 6-6-6-6", "M12 19h8"),
    "phone": (
        "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z",
        "M12 18h.01",
    ),
    "laptop": (
        "M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0 1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1"
        " 1 0 0 1-.9-1.45L4 16",
    ),
    "globe": (
        "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
        "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20",
        "M2 12h20",
    ),
    "copy": (
        "M10 8h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2z",
        "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2",
    ),
    "link": (
        "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71",
        "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
    ),
    "lock": (
        "M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z",
        "M7 11V7a5 5 0 0 1 10 0v4",
    ),
    "key": (
        "m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4",
        "m21 2-9.6 9.6",
        "M13 15.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
    ),
    "mail": (
        "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
        "m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7",
    ),
    "download": ("M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "m7 10 5 5 5-5", "M12 15V3"),
    "trash": (
        "M3 6h18",
        "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6",
        "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2",
        "M10 11v6",
        "M14 11v6",
    ),
    "logout": ("M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "m16 17 5-5-5-5", "M21 12H9"),
    "login": ("M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4", "m10 17 5-5-5-5", "M15 12H3"),
    "user": ("M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2", "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0"),
    "user_plus": (
        "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2",
        "M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
        "M19 8v6",
        "M22 11h-6",
    ),
    "book": (
        "M12 7v14",
        "M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0"
        " 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z",
    ),
    "wrench": (
        "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91"
        " 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
    ),
}
STATUS = {
    "ok": ("green", "check"),
    "error": ("red", "alert"),
    "info": ("blue", "info"),
    "mail": ("blue", "mail"),
    "key": ("neutral", "key"),
    "lock": ("neutral", "lock"),
    "terminal": ("neutral", "terminal"),
}
WORKS = (
    ("chat", "Claude"),
    ("chat", "ChatGPT"),
    ("terminal", "Claude Code"),
    ("terminal", "Codex"),
)
TICKS = re.compile(r"`([^`]+)`")
# the sections of the start page, as the navigation names them (texts `nav_<name>`)
SECTIONS = ("features", "day", "languages", "connect", "faq")
# words of the courses that drift beside the headline and run in the courses' ribbon
FLOATS = (
    ("de", "die Sprache"),
    ("es", "la palabra"),
    ("en", "word"),
    ("fr", "le mot"),
    ("it", "la parola"),
    ("en", "language"),
)
RIBBON = (
    (
        ("en", "dog"),
        ("de", "der Hund"),
        ("es", "el perro"),
        ("fr", "le chien"),
        ("it", "il cane"),
        ("en", "house"),
        ("de", "das Haus"),
        ("es", "la casa"),
        ("fr", "la maison"),
        ("it", "la casa"),
    ),
    (
        ("it", "il libro"),
        ("fr", "le livre"),
        ("es", "el libro"),
        ("de", "das Buch"),
        ("en", "book"),
        ("it", "l'acqua"),
        ("fr", "l'eau"),
        ("es", "el agua"),
        ("de", "das Wasser"),
        ("en", "water"),
    ),
)


# ------------------------------------------------------------ files of the pages


def font() -> bytes:
    """The Geist typeface (SIL Open Font License 1.1, see static/geist-OFL.txt)."""
    return (resources.files("vocabbot.server") / "static" / "geist.woff2").read_bytes()


def icon() -> bytes:
    """VocabBot's avatar as a rounded tile: the favicon and the icon MCP clients show."""
    return (resources.files("vocabbot.server") / "static" / "vocabbot.png").read_bytes()


def social(lang: str) -> bytes:
    """The picture a shared link shows (scripts/make_social.py renders it), 1200 by 630."""
    name = f"social-{lang if lang in LANGS else LANGS[0]}.png"
    return (resources.files("vocabbot.server") / "static" / name).read_bytes()


@cache
def mark() -> str:
    """The avatar as inline SVG for the pages (scripts/make_icon.py draws it)."""
    return (resources.files("vocabbot.server") / "static" / "vocabbot.svg").read_text("utf-8")


def static_text(name: str) -> str:
    return (resources.files("vocabbot.server") / "static" / name).read_text("utf-8")


# ------------------------------------------------------------ the language of a page


@cache
def _bundle(lang: str) -> dict[str, Any]:
    data: dict[str, Any] = assets.read_json(assets.data_root() / "i18n" / f"{lang}.json")
    return data


def _node(lang: str, name: str) -> Any:
    node: Any = _bundle(lang)
    for part in f"server.{name}".split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def say(lang: str, name: str, /, **values: Any) -> str:
    """A text of the pages (under `server.`) in a language; Polish fills a gap in English."""
    node = _node(lang, name)
    if not isinstance(node, str):
        node = _node("pl", name)
    if not isinstance(node, str):
        return name
    return node.format(**values) if values else node


def items(lang: str, name: str) -> list[Any]:
    """A list of the pages' texts (paragraphs, cards) in a language, Polish if English lacks it."""
    node = _node(lang, name)
    if not isinstance(node, list):
        node = _node("pl", name)
    return list(node) if isinstance(node, list) else []


def accepted(header: str) -> str:
    """The pages' language a browser prefers (Accept-Language); Polish when it names neither."""
    best, best_q = "pl", 0.0
    for part in header.split(",")[:32]:
        tag, _, params = part.strip().partition(";")
        code = tag.strip().lower().split("-")[0]
        if code not in LANGS:
            continue
        q = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.strip() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        if q > best_q:
            best, best_q = code, q
    return best


@dataclass(frozen=True)
class Locale:
    """The language of a page and what its language switch needs."""

    lang: str = "pl"
    here: str = "/"  # the page's path and query without `lang`, where the switch leads
    chosen: bool = False  # asked for with ?lang=, so the answer keeps it in a cookie
    secure: bool = False
    site: str = ""  # the server's address, for the links search engines read

    def at(self, here: str) -> Locale:
        """The same language with the switch leading to another address of the page."""
        return replace(self, here=here)

    def say(self, name: str, /, **values: Any) -> str:
        return say(self.lang, name, **values)

    def t(self, name: str, /, **values: Any) -> str:
        """A text, escaped for HTML."""
        return escape(say(self.lang, name, **values))

    def link(self, lang: str) -> str:
        joiner = "&" if "?" in self.here else "?"
        return f"{self.here}{joiner}lang={lang}"

    def address(self, lang: str | None = None) -> str:
        """The page's one address in a language, as search engines keep it."""
        return address(self.site, urlsplit(self.here).path, lang or self.lang)


def address(site: str, path: str, lang: str) -> str:
    """Polish is the page's plain address; the other language adds `?lang=`."""
    return f"{site}{path}" + ("" if lang == LANGS[0] else f"?lang={lang}")


def locale(request: Request, *, secure: bool = False, site: str = "") -> Locale:
    """The language of the page a request asks for: ?lang=, the cookie, Accept-Language, Polish."""
    asked = request.query_params.get("lang", "")
    chosen = asked in LANGS
    if chosen:
        lang = asked
    else:
        kept = request.cookies.get(LANG_COOKIE, "")
        lang = kept if kept in LANGS else accepted(request.headers.get("accept-language", ""))
    query = [(key, value) for key, value in request.query_params.multi_items() if key != "lang"]
    here = request.url.path + (f"?{urlencode(query)}" if query else "")
    return Locale(lang, here, chosen, secure, site)


def respond(
    loc: Locale, page: str, status: int = 200, background: BackgroundTask | None = None
) -> HTMLResponse:
    """A page with the pages' headers; a language chosen with the switch stays in a cookie."""
    headers = {**HEADERS, "Content-Language": loc.lang, "Vary": "Accept-Language, Cookie"}
    response = HTMLResponse(page, status_code=status, headers=headers, background=background)
    if loc.chosen:
        response.set_cookie(
            LANG_COOKIE,
            loc.lang,
            max_age=365 * 86400,
            path="/",
            httponly=True,
            secure=loc.secure,
            samesite="lax",
        )
    return response


def when(moment: float, lang: str = "pl") -> str:
    """A moment as the pages show it, in UTC."""
    stamp = datetime.fromtimestamp(moment, timezone.utc)
    if lang == "en":
        return f"{stamp.day} {MONTHS_EN[stamp.month - 1]} {stamp.year}, {stamp:%H:%M} UTC"
    return stamp.strftime("%d.%m.%Y, %H:%M UTC")


# ------------------------------------------------------------ building blocks


def _icon(name: str, extra: str = "") -> str:
    paths = "".join(f'<path d="{d}"/>' for d in PATHS[name])
    classes = f"icon {extra}" if extra else "icon"
    return f'<svg class="{classes}" viewBox="0 0 24 24" aria-hidden="true">{paths}</svg>'


def _mark(size: str = "") -> str:
    classes = f"mark vb {size}" if size else "mark vb"
    return f'<span class="{classes}" aria-hidden="true">{mark().strip()}</span>'


def _rich(text: str) -> str:
    """Escaped text with `code` in backticks."""
    return TICKS.sub(lambda found: f"<code>{found[1]}</code>", escape(text))


def _hidden(name: str, value: str) -> str:
    return f'<input type="hidden" name="{name}" value="{escape(value)}">'


def _logo() -> str:
    return f'<a class="logo" href="/">{_mark()}<span>VocabBot</span></a>'


def _switch(loc: Locale) -> str:
    links = "".join(
        f'<a href="{escape(loc.link(code))}" hreflang="{code}" lang="{code}"'
        f' title="{escape(say(code, "lang_name"))}"'
        + (' aria-current="true"' if code == loc.lang else "")
        + f">{code.upper()}</a>"
        for code in LANGS
    )
    label = loc.t("lang_label")
    return f'<div class="lang" role="group" aria-label="{label}">{_icon("globe")}{links}</div>'


def _copy(loc: Locale, target: str) -> str:
    """A copy button; the script shows it where the browser can copy."""
    return (
        f'<button class="icon-btn" type="button" data-copy="{target}" data-done="{loc.t("copied")}"'
        f' aria-label="{loc.t("copy")}" title="{loc.t("copy")}" hidden>'
        f"{_icon('copy', 'i-copy')}{_icon('check', 'i-done')}</button>"
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
    required: bool = True,
    classes: str = "input",
) -> str:
    hint_html = f'<p class="hint" id="{id_}-hint">{hint}</p>' if hint else ""
    described = f' aria-describedby="{id_}-hint"' if hint else ""
    needed = " required" if required else ""
    return (
        f'<div class="field"><label for="{id_}">{label}</label>'
        f'<input class="{classes}" id="{id_}" name="{name}" type="{kind}"'
        f' value="{escape(value)}"{described} {extra}{needed}>{hint_html}</div>'
    )


def _alert(loc: Locale, error: str | None) -> str:
    if not error:
        return ""
    return (
        f'<div class="alert tone-red" role="alert">{_icon("alert")}'
        f"<span>{loc.t(f'errors.{error}')}</span></div>"
    )


def _flash(message: str | None) -> str:
    if not message:
        return ""
    return (
        f'<div class="alert tone-green" role="status">{_icon("circle_check")}'
        f"<span>{escape(message)}</span></div>"
    )


def _search_head(loc: Locale, title: str, description: str) -> str:
    """What search engines and link previews read: the address, the languages, the picture."""
    path = urlsplit(loc.here).path
    here = escape(loc.address())
    width, height = SOCIAL_SIZE
    picture = escape(loc.site + SOCIAL.format(lang=loc.lang))
    locales = {"pl": "pl_PL", "en": "en_US"}
    head = f'<link rel="canonical" href="{here}">'
    for code in (*LANGS, "x-default"):
        target = escape(address(loc.site, path, LANGS[0] if code == "x-default" else code))
        head += f'<link rel="alternate" hreflang="{code}" href="{target}">'
    head += (
        '<meta property="og:type" content="website">'
        '<meta property="og:site_name" content="VocabBot">'
        f'<meta property="og:title" content="{escape(title)}">'
        f'<meta property="og:url" content="{here}">'
        f'<meta property="og:image" content="{picture}">'
        '<meta property="og:image:type" content="image/png">'
        f'<meta property="og:image:width" content="{width}">'
        f'<meta property="og:image:height" content="{height}">'
        f'<meta property="og:image:alt" content="{loc.t("social_alt")}">'
        f'<meta property="og:locale" content="{locales[loc.lang]}">'
    )
    head += "".join(
        f'<meta property="og:locale:alternate" content="{locales[code]}">'
        for code in LANGS
        if code != loc.lang
    )
    head += (
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{escape(title)}">'
        f'<meta name="twitter:image" content="{picture}">'
        f'<meta name="twitter:image:alt" content="{loc.t("social_alt")}">'
    )
    if description:
        head += (
            f'<meta property="og:description" content="{escape(description)}">'
            f'<meta name="twitter:description" content="{escape(description)}">'
        )
    return head


def _linked_data(nodes: list[dict[str, Any]]) -> str:
    """schema.org data of a page as JSON-LD; a browser reads it as data, never as a script."""
    graph = json.dumps(
        {"@context": "https://schema.org", "@graph": nodes},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # no text of the data may close the element or open a comment
    safe = graph.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/ld+json">{safe}</script>'


def _page(
    loc: Locale,
    title: str,
    body: str,
    *,
    index: bool = False,
    soft: bool = False,
    description: str = "",
    data: list[dict[str, Any]] | None = None,
    motion: bool = False,
) -> str:
    head = (
        '<meta name="robots" content="index, follow, max-image-preview:large,'
        ' max-snippet:-1, max-video-preview:-1">'
        if index
        else '<meta name="robots" content="noindex, nofollow">'
    )
    if description:
        head += f'<meta name="description" content="{escape(description)}">'
    if index and loc.site:
        head += _search_head(loc, title, description)
        if data:
            head += _linked_data(data)
    script = f"<script>{SCRIPT}</script>" if ('name="tz"' in body or "data-copy=" in body) else ""
    if motion:
        script += f"<script>{MOTION}</script>"
    tint = "#fafafa" if soft else "#ffffff"
    tag = '<body class="soft">' if soft else "<body>"
    return (
        f'<!doctype html><html lang="{loc.lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<meta name="color-scheme" content="light dark">'
        f'<meta name="theme-color" content="{tint}" media="(prefers-color-scheme: light)">'
        '<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">'
        f'{head}<link rel="icon" href="{ICON}" type="image/png">'
        f'<link rel="apple-touch-icon" href="{ICON}">'
        f'<link rel="preload" href="{FONT}" as="font" type="font/woff2" crossorigin>'
        f'<link rel="stylesheet" href="{style_address()}">'
        f"<title>{escape(title)}</title></head>"
        f"{tag}{body}{script}</body></html>"
    )


# ------------------------------------------------------------ the frame of the site


def _site_top(loc: Locale, *, home: bool) -> str:
    base = "" if home else "/"
    links = "".join(f'<a href="{base}#{part}">{loc.t(f"nav_{part}")}</a>' for part in SECTIONS)
    return (
        f'<a class="skip" href="#main">{loc.t("skip")}</a>'
        '<header class="top site"><div class="wrap bar">'
        f"{_logo()}"
        f'<nav class="links" aria-label="VocabBot">{links}</nav>'
        f'<div class="end">{_switch(loc)}'
        f'<a class="btn ghost sm wide-only" href="/app/login">{loc.t("nav_sign_in")}</a>'
        f'<a class="btn primary sm" href="/app/">{loc.t("nav_open")}</a></div>'
        "</div></header>"
    )


def _site_foot(loc: Locale, *, home: bool) -> str:
    base = "" if home else "/"

    def column(title: str, links: list[tuple[str, str]]) -> str:
        rows = "".join(
            f'<li><a href="{escape(target)}"'
            + (' rel="noopener"' if target.startswith("https://") else "")
            + f">{escape(label)}</a></li>"
            for target, label in links
        )
        return f'<nav aria-label="{escape(title)}"><h2>{escape(title)}</h2><ul>{rows}</ul></nav>'

    columns = (
        column(
            loc.say("foot_product"),
            [(f"{base}#{part}", loc.say(f"nav_{part}")) for part in SECTIONS],
        )
        + column(
            loc.say("foot_account"),
            [
                ("/app/", loc.say("web.nav_app")),
                ("/account", loc.say("web.nav_account")),
                ("/app/login", loc.say("nav_sign_in")),
                ("/privacy", loc.say("privacy_link")),
            ],
        )
        + column(
            loc.say("foot_resources"),
            [
                (REPO, loc.say("foot_source")),
                (PACKAGE, loc.say("foot_package")),
                ("/llms.txt", loc.say("foot_llms")),
            ],
        )
    )
    return (
        '<footer class="site-foot"><div class="wrap"><div class="foot-grid">'
        f'<div class="foot-brand">{_logo()}<p>{loc.t("footer_tagline")}</p>'
        f'<p class="fine">{loc.t("foot_license")}</p></div>'
        f'<div class="foot-cols">{columns}</div></div>'
        f'<div class="foot-bottom"><span>VocabBot {escape(__version__)}</span>{_switch(loc)}</div>'
        "</div></footer>"
    )


def _auth(loc: Locale, title: str, head: str, content: str, foot: str = "") -> str:
    """The frame of a sign-in or a message: the logo, the switch and one narrow column."""
    body = (
        '<div class="auth-bg" aria-hidden="true"></div>'
        f'<header class="auth-top">{_logo()}{_switch(loc)}</header>'
        f'<main class="auth">{head}{content}'
        + (f'<p class="auth-foot">{foot}</p>' if foot else "")
        + "</main>"
    )
    return _page(loc, title, body, soft=True)


def _head(title: str, lead: str = "", *, app: str | None = None, status: str | None = None) -> str:
    """The top of a narrow page: the avatar, a status or the pair of applications, a title."""
    if status is not None:
        tone, name = STATUS[status]
        top = f'<span class="status tone-{tone}">{_icon(name)}</span>'
    elif app is not None:
        initial = escape((app.strip()[:1] or "?").upper())
        top = (
            f'<div class="pair"><span class="tile-app" aria-hidden="true">{initial}</span>'
            f'<span class="link-line" aria-hidden="true"><span class="link-dot">{_icon("lock")}'
            f"</span></span>{_mark('lg')}</div>"
        )
    else:
        top = _mark("lg")
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    return f'<div class="auth-head">{top}<h1>{title}</h1>{lead_html}</div>'


def _tabs(loc: Locale, login_form: str, signup_form: str, tab: str) -> str:
    checked_login = " checked" if tab != "signup" else ""
    checked_signup = " checked" if tab == "signup" else ""
    return (
        '<section class="box">'
        f'<input class="tab-input" type="radio" name="tab" id="tab-login"{checked_login}>'
        f'<input class="tab-input" type="radio" name="tab" id="tab-signup"{checked_signup}>'
        f'<div class="tabs"><label class="tab" for="tab-login">{_icon("login")}'
        f'{loc.t("tab_login")}</label><label class="tab" for="tab-signup">{_icon("user_plus")}'
        f"{loc.t('tab_signup')}</label></div>{login_form}{signup_form}</section>"
    )


def _login_fields(loc: Locale, login: str, focus: bool) -> str:
    return _field(
        "login",
        loc.t("login"),
        id_="login",
        value=login,
        extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
        + (" autofocus" if focus else ""),
    ) + _field(
        "password",
        loc.t("password"),
        id_="password",
        kind="password",
        extra='autocomplete="current-password"',
    )


def _signup_fields(loc: Locale, login: str, focus: bool, *, email: bool, invite: bool) -> str:
    fields = (
        _field(
            "login",
            loc.t("login"),
            id_="new-login",
            value=login,
            hint=loc.t("login_hint"),
            extra='autocomplete="username" autocapitalize="none" spellcheck="false"'
            ' minlength="3" maxlength="40"' + (" autofocus" if focus else ""),
        )
        + _field(
            "password",
            loc.t("password"),
            id_="new-password",
            kind="password",
            hint=loc.t("password_hint"),
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + _field(
            "password2",
            loc.t("password_again"),
            id_="new-password2",
            kind="password",
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
    )
    if email:
        fields += _field(
            "email",
            loc.t("web.email"),
            id_="email",
            kind="email",
            hint=loc.t("web.email_hint"),
            extra='autocomplete="email" maxlength="254"',
            required=False,
        )
    if invite:
        fields += _field(
            "invite",
            loc.t("invite"),
            id_="invite",
            hint=loc.t("invite_hint"),
            classes="input code",
            extra='autocomplete="off" autocapitalize="characters" spellcheck="false"'
            ' placeholder="ABCD-EFGH-JKMN" maxlength="20"',
        )
    return fields


def _version_foot(loc: Locale, before: str = "") -> str:
    return (
        f'{before}<a href="/privacy">{loc.t("privacy_link")}</a> · VocabBot {escape(__version__)}'
    )


# ------------------------------------------------------------ sign-ins


def sign_in(
    loc: Locale,
    request_id: str,
    app: str,
    host: str,
    open_signup: bool,
    error: str | None = None,
    login: str = "",
    tab: str = "login",
) -> str:
    """The sign-in that connects a chat application (OAuth)."""
    hidden = _hidden("request", request_id) + '<input type="hidden" name="tz" value="">'
    lead = loc.t("connect_hint", app=app)
    if host:
        lead += f' {loc.t("return_to")} <span class="host">{escape(host)}</span>'
    login_form = (
        f'<form class="pane pane-login" method="post" action="/login">{hidden}'
        + _hidden("action", "login")
        + _login_fields(loc, login if tab == "login" else "", tab == "login")
        + f'<button class="btn primary block" type="submit">{loc.t("login_button")}</button></form>'
    )
    signup_form = (
        f'<form class="pane pane-signup" method="post" action="/login">{hidden}'
        + _hidden("action", "signup")
        + _signup_fields(
            loc,
            login if tab == "signup" else "",
            tab == "signup",
            email=False,
            invite=not open_signup,
        )
        + f'<button class="btn primary block" type="submit">{loc.t("signup_button")}</button>'
        "</form>"
    )
    return _auth(
        loc,
        loc.say("connect", app=app),
        _head(loc.t("connect", app=app), lead, app=app),
        _alert(loc, error) + _tabs(loc, login_form, signup_form, tab),
        _version_foot(loc, f"{loc.t('disconnect', app=app)}<br>"),
    )


def web_sign_in(
    loc: Locale,
    target: str,
    open_signup: bool,
    mail_ready: bool,
    error: str | None = None,
    login: str = "",
    tab: str = "login",
) -> str:
    """The sign-in of the session page and the account page: a browser session of 30 days."""
    hidden = _hidden("next", target) + '<input type="hidden" name="tz" value="">'
    forgot = (
        f'<div class="forgot"><a class="link" href="/recover">{loc.t("web.forgot")}</a></div>'
        if mail_ready
        else ""
    )
    login_form = (
        f'<form class="pane pane-login" method="post" action="/app/login">{hidden}'
        + _hidden("action", "login")
        + _login_fields(loc, login if tab == "login" else "", tab == "login")
        + forgot
        + f'<button class="btn primary block" type="submit">{loc.t("web.login_button")}</button>'
        "</form>"
    )
    signup_form = (
        f'<form class="pane pane-signup" method="post" action="/app/login">{hidden}'
        + _hidden("action", "signup")
        + _signup_fields(
            loc,
            login if tab == "signup" else "",
            tab == "signup",
            email=mail_ready,
            invite=not open_signup,
        )
        + f'<button class="btn primary block" type="submit">{loc.t("web.signup_button")}</button>'
        "</form>"
    )
    return _auth(
        loc,
        loc.say("web.sign_in_title"),
        _head(loc.t("web.sign_in_title"), loc.t("web.sign_in_lead")),
        _alert(loc, error) + _tabs(loc, login_form, signup_form, tab),
        _version_foot(loc),
    )


def message_page(
    loc: Locale,
    title: str,
    lead: str,
    link: tuple[str, str] | None = None,
    tone: str = "info",
) -> str:
    """A page with one message, its status and one way on."""
    action = (
        f'<div class="actions-col"><a class="btn primary block" href="{escape(link[0])}">'
        f"{escape(link[1])}</a></div>"
        if link
        else ""
    )
    return _auth(
        loc,
        f"{title} · VocabBot",
        _head(escape(title), escape(lead), status=tone),
        action,
        f'<a href="/">VocabBot</a> · <a href="/privacy">{loc.t("privacy_link")}</a>',
    )


def expired(loc: Locale) -> str:
    return message_page(loc, loc.say("expired_title"), loc.say("expired"), tone="error")


def recover(loc: Locale, error: str | None = None) -> str:
    form = (
        '<section class="box"><form method="post" action="/recover">'
        + _field(
            "login",
            loc.t("login"),
            id_="login",
            extra='autocomplete="username" autocapitalize="none" spellcheck="false" autofocus',
        )
        + _field(
            "email",
            loc.t("web.email_plain"),
            id_="email",
            kind="email",
            extra='autocomplete="email"',
        )
        + f'<button class="btn primary block" type="submit">{loc.t("web.recover_button")}</button>'
        "</form></section>"
    )
    return _auth(
        loc,
        loc.say("web.recover_title"),
        _head(loc.t("web.recover_title"), loc.t("web.recover_lead"), status="key"),
        _alert(loc, error) + form,
        f'<a href="/app/login">{loc.t("web.back_to_login")}</a>',
    )


def reset(loc: Locale, token: str, login: str, error: str | None = None) -> str:
    form = (
        f'<section class="box"><form method="post" action="/recover/{escape(token)}">'
        + _field(
            "password",
            loc.t("password"),
            id_="password",
            kind="password",
            hint=loc.t("password_hint"),
            extra='autocomplete="new-password" minlength="12" maxlength="200" autofocus',
        )
        + _field(
            "password2",
            loc.t("password_again"),
            id_="password2",
            kind="password",
            extra='autocomplete="new-password" minlength="12" maxlength="200"',
        )
        + f'<button class="btn primary block" type="submit">{loc.t("web.reset_button")}</button>'
        "</form></section>"
    )
    return _auth(
        loc,
        loc.say("web.reset_title"),
        _head(loc.t("web.reset_title"), loc.t("web.reset_lead", login=login), status="lock"),
        _alert(loc, error) + form,
    )


def device(loc: Locale, code: str, login: str | None, csrf: str, error: str | None = None) -> str:
    """The page that confirms the code of the program on a computer without a browser."""
    fields = _field(
        "code",
        loc.t("web.device_code"),
        id_="code",
        value=code,
        classes="input code big",
        extra='autocomplete="off" autocapitalize="characters" spellcheck="false"'
        ' placeholder="ABCD-EFGH" maxlength="12"' + ("" if code else " autofocus"),
    )
    if login is None:
        fields += _login_fields(loc, "", False)
        lead = loc.t("web.device_lead")
    else:
        lead = loc.t("web.device_lead") + " " + loc.t("web.device_as", login=login)
    form = (
        '<section class="box"><form method="post" action="/device">'
        + _hidden("csrf", csrf)
        + fields
        + f'<button class="btn primary block" type="submit">{loc.t("web.device_button")}</button>'
        "</form></section>"
    )
    return _auth(
        loc,
        loc.say("web.device_title"),
        _head(loc.t("web.device_title"), lead, status="terminal"),
        _alert(loc, error) + form,
        _version_foot(loc),
    )


# ------------------------------------------------------------ the account


def _set(
    title: str,
    desc: str,
    body: str = "",
    *,
    foot: str = "",
    actions: str = "",
    form: str | None = None,
    danger: bool = False,
) -> str:
    """A settings card: the title and the description, its content and a footer with actions."""
    classes = "set danger" if danger else "set"
    opening = (
        f'<form class="{classes}" method="post" action="/account">{form}'
        if form is not None
        else f'<section class="{classes}">'
    )
    closing = "</form>" if form is not None else "</section>"
    footer = (
        f'<div class="set-foot"><span>{foot}</span><div class="actions">{actions}</div></div>'
        if foot or actions
        else ""
    )
    return (
        f'{opening}<div class="set-body"><h2>{title}</h2><p class="desc">{desc}</p>{body}</div>'
        f"{footer}{closing}"
    )


def _account_top(loc: Locale, login: str, csrf: str) -> str:
    return (
        '<header class="top app"><div class="wrap narrow"><div class="bar">'
        f'{_logo()}<span class="slash" aria-hidden="true">/</span>'
        f'<span class="who">{escape(login)}</span>'
        f'<div class="end">{_switch(loc)}'
        f'<form method="post" action="/app/logout">{_hidden("csrf", csrf)}'
        f'<button class="btn ghost sm" type="submit" aria-label="{loc.t("web.logout")}">'
        f'{_icon("logout")}<span class="wide-only">{loc.t("web.logout")}</span></button></form>'
        "</div></div>"
        f'<nav class="tabs-nav" aria-label="VocabBot"><a href="/app/">{_icon("book")}'
        f'{loc.t("web.nav_app")}</a><a href="/account" aria-current="page">{_icon("user")}'
        f"{loc.t('web.nav_account')}</a></nav></div></header>"
    )


def account(
    loc: Locale,
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
    """The account page: the connections, the e-mail for recovery, the data, the removal."""
    token = _hidden("csrf", csrf)
    if grants:
        rows = "".join(
            f'<li><span class="dev-icon">'
            f"{_icon('terminal' if 'vocabbot' in grant.name.lower() else 'chat')}</span>"
            f'<span class="what"><b>{escape(grant.name)}</b>'
            f"<span>{loc.t('web.device_since', when=when(grant.created, loc.lang))} · "
            f"{loc.t('web.device_used', when=when(grant.used, loc.lang))}</span></span>"
            f'<form method="post" action="/account">{token}{_hidden("action", "unlink")}'
            f'{_hidden("grant", grant.id)}<button class="btn secondary sm" type="submit">'
            f"{loc.t('web.unlink')}</button></form></li>"
            for grant in grants
        )
        devices = f'<ul class="devices">{rows}</ul>'
    else:
        devices = (
            f'<div class="empty-row">{_icon("link")}<span>{loc.t("web.devices_none")}</span></div>'
        )
    cards = _set(
        loc.t("web.devices_title"),
        loc.t("web.devices_lead"),
        devices,
        foot=loc.t("web.devices_foot") if grants else "",
    )
    if mail_ready:
        # the address decides where a new password goes, so a change needs the password
        remove = (
            '<button class="btn secondary sm" type="submit" name="action" value="email_remove"'
            f" formnovalidate>{loc.t('web.email_remove')}</button>"
            if has_email
            else ""
        )
        fields = (
            '<div class="fields">'
            + _field(
                "email",
                loc.t("web.email"),
                id_="email",
                kind="email",
                hint=loc.t("web.email_hint"),
                extra='autocomplete="email" maxlength="254"',
                required=False,
            )
            + _field(
                "password",
                loc.t("web.email_password"),
                id_="email-password",
                kind="password",
                extra='autocomplete="current-password"',
            )
            + "</div>"
        )
        cards += _set(
            loc.t("web.email_title"),
            loc.t("web.email_set") if has_email else loc.t("web.email_none"),
            fields,
            foot=loc.t("web.email_foot"),
            actions=remove
            + '<button class="btn primary sm" type="submit" name="action" value="email">'
            f"{loc.t('web.email_save')}</button>",
            form=token,
        )
    else:
        cards += _set(loc.t("web.email_title"), loc.t("web.email_unavailable"))
    if can_export:
        cards += _set(
            loc.t("web.data_title"),
            _rich(loc.say("web.data_lead")),
            actions=f'<a class="btn secondary sm" href="/account/export">{_icon("download")}'
            f"{loc.t('web.export')}</a>",
        )
    else:
        cards += _set(loc.t("web.data_title"), loc.t("web.export_none"))
    cards += _set(
        loc.t("web.delete_title"),
        loc.t("web.delete_lead"),
        '<div class="fields">'
        + _field(
            "password",
            loc.t("web.delete_password"),
            id_="delete-password",
            kind="password",
            extra='autocomplete="current-password"',
        )
        + "</div>",
        actions=f'<button class="btn danger sm" type="submit">{_icon("trash")}'
        f"{loc.t('web.delete_button')}</button>",
        form=token + _hidden("action", "delete"),
        danger=True,
    )
    lead = loc.t("web.account_lead", login=login, created=when(created, loc.lang))
    body = (
        _account_top(loc, login, csrf) + '<main class="wrap narrow settings">'
        f'<div class="page-head"><h1>{loc.t("web.account_title")}</h1><p>{lead}</p></div>'
        + _flash(message)
        + _alert(loc, error)
        + cards
        + "</main>"
        + f'<footer class="mini-foot">{_version_foot(loc)}</footer>'
    )
    return _page(loc, f"{loc.say('web.account_title')} · VocabBot", body, soft=True)


# ------------------------------------------------------------ the start page


@cache
def course_sizes() -> dict[str, dict[str, int]]:
    """The entries of every installed course by level, as the courses' meta.json counts them."""
    sizes: dict[str, dict[str, int]] = {}
    root = assets.course_root()
    for lang in COURSES:
        try:
            meta = assets.read_json(root / lang / "meta.json")
        except (OSError, ValueError):
            continue
        levels = meta.get("levels") if isinstance(meta, dict) else None
        if not isinstance(levels, dict):
            continue
        counted = {
            str(level): count
            for level, count in levels.items()
            if isinstance(count, int) and count > 0
        }
        if counted:
            sizes[lang] = counted
    return sizes


def number(value: int, lang: str) -> str:
    """A number as the page's language writes it: 28 671 in Polish, 28,671 in English."""
    if lang == "en":
        return f"{value:,}"
    return f"{value:,}".replace(",", " ") if value >= 10000 else str(value)


def _display(loc: Locale) -> str:
    """The headline: one sentence, its closing words in the colour of the avatar."""
    return (
        f'<span class="line"><span>{loc.t("hero_title")}</span></span> '
        f'<span class="line accent"><span>{loc.t("hero_accent")}</span></span>'
    )


def _eyebrow(text: str) -> str:
    return f'<span class="eyebrow"><i class="pip" aria-hidden="true"></i>{text}</span>'


def _section_head(loc: Locale, name: str) -> str:
    return (
        f'<div class="section-head reveal">{_eyebrow(loc.t(f"{name}_eyebrow"))}'
        f'<h2>{loc.t(f"{name}_title")}</h2><p class="sub">{loc.t(f"{name}_lead")}</p></div>'
    )


def _word(lang: str, word: str, extra: str = "") -> str:
    """A word of a course with the dot of its language."""
    classes = f"wchip {extra}" if extra else "wchip"
    return f'<span class="{classes}" lang="{lang}"><i class="dot {lang}"></i>{escape(word)}</span>'


def _letters(text: str) -> str:
    """A text letter by letter, for the pictures that type it."""
    return "".join(f"<i>{'&nbsp;' if sign == ' ' else escape(sign)}</i>" for sign in text)


def _mock(name: str) -> str:
    return escape(assets.text(f"server.mock.{name}"))


def _showcase(loc: Locale) -> str:
    """A conversation in a chat application with VocabBot's card: a question and its answer.

    The classes q1 to q7 bring the parts in one after another, and `play` marks the parts
    only the moving picture shows (the sent answer and its grade).
    """

    def card(name: str) -> str:
        return escape(assets.text(f"server.card.{name}"))

    initial = _mock("assistant_name")[:1]
    wrench, check = _icon("wrench"), _icon("check")
    back = escape(assets.text("back.days", days=4))
    window = (
        '<div class="window" aria-hidden="true">'
        '<div class="window-bar"><span class="dots"><i></i><i></i><i></i></span>'
        f'<span class="window-title">{_mock("chat_title")}</span>'
        f'<span class="connector">{_mark()}VocabBot<span class="on"></span></span></div>'
        '<div class="chat">'
        f'<div class="msg user q1">{_mock("user")}</div>'
        f'<div class="msg bot"><span class="bot-avatar q2">{initial}</span>'
        f'<div class="bot-body"><p class="q2">{_mock("assistant")}</p>'
        f'<span class="toolcall q3">{wrench}<code>vocab_next</code>'
        f'<span class="ok">{check}</span></span>'
        '<div class="vcard q4">'
        f'<div class="vcard-head">{_mark()}<b>VocabBot</b>'
        f'<span class="count"><span class="was">{_mock("counter")}</span>'
        f'<span class="now">{_mock("progress_after")}</span></span></div>'
        '<div class="vcard-bar"><i></i></div>'
        f'<div class="stages"><span class="stage on">{card("stage_reviews")} <b>4</b></span>'
        f'<span class="stage">{card("stage_new")} <b>3</b></span>'
        f'<span class="stage">{card("stage_drill")} <b>0</b></span></div>'
        '<div class="vcard-body"><div class="badges">'
        f'<span class="badge outline"><i class="dot de"></i>{_mock("lang")}</span>'
        f'<span class="badge tone-purple">{_icon("repeat")}{escape(assets.text("phases.review"))}'
        "</span></div>"
        f'<div class="prompt">{_mock("prompt")}</div>'
        f'<div class="meta">{_mock("meta")} · {card("with_article")}</div></div></div>'
        f'<p class="q5">{_mock("question")}</p></div></div>'
        f'<div class="msg user q6 play" lang="de">{_mock("answer")}</div>'
        f'<div class="msg bot q7 play"><span class="bot-avatar">{initial}</span>'
        f'<div class="bot-body"><span class="toolcall">{wrench}<code>vocab_answer</code>'
        f'<span class="ok">{check}</span></span>'
        f'<div class="verdict"><span class="badge tone-green">{check}'
        f"{escape(assets.text('grades.know'))}</span>"
        f'<span class="back">{back}</span></div></div></div></div>'
        '<div class="composer"><div class="composer-box">'
        f'<span class="plus">{_icon("plus")}</span>'
        f'<span class="typed"><span class="ph">{_mock("composer")}</span>'
        f'<span class="letters" lang="de">{_letters(assets.text("server.mock.answer"))}</span>'
        '<i class="caret"></i></span>'
        f'<span class="send">{_icon("arrow_up")}</span></div></div></div>'
    )
    caption = loc.t("mock_caption")
    return (
        f'<figure class="showcase"><div class="stage-panel">{window}</div>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def _visual(name: str) -> str:
    """The small picture above a feature."""
    if name == "repeat":
        curve = (
            "M20 18 C36 52 52 70 70 76 L70 18 C96 46 118 62 140 70 L140 18 C180 42 220 56 250 62"
            " L250 18 C270 28 288 35 304 39"
        )
        points = "".join(
            f'<circle class="pt p{number}" cx="{x}" cy="18" r="4"/>'
            for number, x in enumerate((20, 70, 140, 250), start=1)
        )
        return (
            '<svg class="curve" viewBox="0 0 320 112" aria-hidden="true"><defs>'
            '<linearGradient id="vb-fade" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="currentColor" stop-opacity=".22"/>'
            '<stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs>'
            '<path class="gl" d="M12 18H308M12 60H308M12 102H308"/>'
            f'<path class="area" d="{curve} L304 102 L20 102 Z" fill="url(#vb-fade)"/>'
            f'<path class="line" pathLength="1" d="{curve}"/>{points}</svg>'
        )
    if name == "languages":
        chips = "".join(
            f'<span class="lchip{" on" if code in ("en", "de", "es") else ""}">'
            f'<i class="dot {code}"></i>{code.upper()}</span>'
            for code in COURSES
        )
        levels = (
            '<span class="on">A1</span><span class="on">A2</span><span class="half">B1</span>'
            "<span>B2</span>"
        )
        return (
            f'<div class="langs"><div class="lang-chips">{chips}</div>'
            f'<div class="levels">{levels}</div></div>'
        )
    if name == "devices":
        wires = "".join(
            f'<path d="M160 74 L{x} {y}"/>' for x, y in ((56, 38), (56, 110), (264, 38), (264, 110))
        )
        return (
            '<div class="grid-bg"></div><div class="hub">'
            f'<svg class="wires" viewBox="0 0 320 148" preserveAspectRatio="none">{wires}</svg>'
            + "".join(
                f'<span class="node n{number}">{_icon(name)}</span>'
                for number, name in enumerate(("chat", "terminal", "phone", "laptop"), start=1)
            )
            + f'<span class="core">{_mark()}</span></div>'
        )
    return (
        '<div class="tool"><div class="tool-head">'
        f'<span class="tool-ico">{_icon("wrench")}</span><code>vocab_answer</code>'
        '<span class="tool-tag">MCP</span></div><div class="tool-io">'
        '<div class="io"><span class="k">answer</span><span class="v">"der Hund"</span></div>'
        f'<div class="io"><span class="k">grade</span><span class="v good">{_icon("check")}"know"'
        "</span></div></div></div>"
    )


def _stage_picture(name: str) -> str:
    """The picture of a stage of the day: cards that are due, a new word, the drill's grades."""
    if name == "reviews":
        words = [str(word) for word in items("pl", "mock.deck")]
        dues = (_mock("due_overdue"), _mock("due_today"), _mock("due_today"))
        rows = "".join(
            f'<div class="mini m{place}"><i class="dot {lang}"></i><b>{escape(word)}</b>'
            f"<span>{due}</span></div>"
            for place, (lang, word, due) in enumerate(
                zip(("de", "es", "en"), words, dues, strict=False), start=1
            )
        )
        return f'<div class="deck">{rows}</div>'
    if name == "new":
        return (
            '<div class="gapcard"><div class="badges">'
            f'<span class="badge outline"><i class="dot de"></i>{_mock("lang")}</span>'
            f'<span class="badge tone-blue">{_icon("plus")}{escape(assets.text("phases.new"))}'
            "</span></div>"
            f'<p class="gap-line" lang="de">{_mock("gap_before")} <span class="gap">'
            f'<span class="letters">{_letters(assets.text("server.mock.gap_word"))}</span></span>'
            f" {_mock('gap_after')}</p>"
            f'<p class="gap-meaning">{_mock("gap_meaning")}</p></div>'
        )
    grades = "".join(
        f'<span class="gtile tone-{tone} g{place}">{_icon(sign)}'
        f"{escape(assets.text(f'grades.{grade}'))}</span>"
        for place, (grade, tone, sign) in enumerate(
            (
                ("dont_know", "red", "repeat"),
                ("almost", "amber", "repeat"),
                ("know", "green", "check"),
            ),
            start=1,
        )
    )
    return f'<div class="grades">{grades}</div>'


def _stats(loc: Locale) -> str:
    sizes = course_sizes()
    values = {
        "languages": len(sizes),
        "levels": len({level for levels in sizes.values() for level in levels}),
        "words": sum(sum(levels.values()) for levels in sizes.values()),
        "parallel": int(store.DEFAULT_PLAN["max_languages"]),
    }
    cells = "".join(
        f'<div class="stat"><dt>{escape(str(item["label"]))}</dt>'
        f'<dd><b data-count="{values[str(item["name"])]}">'
        f"{number(values[str(item['name'])], loc.lang)}</b>"
        f"<span>{escape(str(item['note']))}</span></dd></div>"
        for item in items(loc.lang, "stats")
        if str(item["name"]) in values
    )
    return (
        f'<section class="stats" aria-label="{loc.t("stats_label")}"><div class="wrap">'
        f'<dl class="stat-grid reveal">{cells}</dl></div></section>'
    )


def _courses(loc: Locale) -> str:
    """The courses: a ribbon of their words and one table of entries per language."""
    sizes = course_sizes()
    top = max((count for levels in sizes.values() for count in levels.values()), default=1)

    def course(lang: str, levels: dict[str, int]) -> str:
        name = loc.say(f"lang_names.{lang}")
        name = name[:1].upper() + name[1:]
        rows = "".join(
            f'<tr><th scope="row">{escape(level.upper())}</th><td class="bar-cell">'
            '<svg class="lvl-bar" viewBox="0 0 100 6" preserveAspectRatio="none"'
            ' aria-hidden="true">'
            f'<rect width="{100 * count / top:.1f}" height="6"/></svg></td>'
            f'<td class="num">{number(count, loc.lang)}</td></tr>'
            for level, count in levels.items()
        )
        return (
            f'<article class="course reveal"><h3><i class="dot {lang}"></i>{escape(name)}'
            f'<span class="code">{lang.upper()}</span></h3>'
            f'<table><caption class="sr">{loc.t("langs_caption", lang=name)}</caption>'
            f"<tbody>{rows}</tbody><tfoot><tr><th scope='row'>{loc.t('langs_total')}</th>"
            f'<td></td><td class="num">{number(sum(levels.values()), loc.lang)}</td></tr>'
            "</tfoot></table></article>"
        )

    def row(words: tuple[tuple[str, str], ...], extra: str) -> str:
        chips = "".join(_word(lang, word) for lang, word in words)
        # the words twice, so the ribbon runs without a seam
        return f'<div class="ribbon-row {extra}"><div class="track">{chips}{chips}</div></div>'

    ribbon = (
        '<div class="ribbon" aria-hidden="true">'
        + "".join(row(words, "back" if place % 2 else "") for place, words in enumerate(RIBBON))
        + "</div>"
    )
    cards = "".join(course(lang, levels) for lang, levels in sizes.items())
    return (
        '<section class="section" id="languages"><div class="wrap">'
        f"{_section_head(loc, 'langs')}</div>{ribbon}"
        f'<div class="wrap"><div class="course-grid">{cards}</div>'
        f'<p class="note reveal">{loc.t("langs_note")}</p></div></section>'
    )


def _home_data(loc: Locale, title: str, description: str) -> list[dict[str, Any]]:
    """schema.org data of the start page: the publisher, the site, the program and the FAQ."""
    site, here = loc.site, loc.address()
    publisher, website, program = f"{site}/#organization", f"{site}/#website", f"{site}/#app"
    width, height = SOCIAL_SIZE
    picture = {
        "@type": "ImageObject",
        "url": site + SOCIAL.format(lang=loc.lang),
        "width": width,
        "height": height,
    }
    taught = [say("en", f"lang_names.{lang}") for lang in course_sizes()]
    return [
        {
            "@type": "Organization",
            "@id": publisher,
            "name": "VocabBot",
            "url": f"{site}/",
            "logo": {"@type": "ImageObject", "url": site + ICON, "width": 512, "height": 512},
            "sameAs": [REPO, PACKAGE],
        },
        {
            "@type": "WebSite",
            "@id": website,
            "url": f"{site}/",
            "name": "VocabBot",
            "description": description,
            "inLanguage": list(LANGS),
            "publisher": {"@id": publisher},
        },
        {
            "@type": "WebPage",
            "@id": f"{here}#webpage",
            "url": here,
            "name": title,
            "description": description,
            "inLanguage": loc.lang,
            "isPartOf": {"@id": website},
            "about": {"@id": program},
            "primaryImageOfPage": picture,
        },
        {
            "@type": "SoftwareApplication",
            "@id": program,
            "name": "VocabBot",
            "url": f"{site}/",
            "description": loc.say("hero_lead"),
            "applicationCategory": "EducationalApplication",
            "applicationSubCategory": "Language learning",
            "operatingSystem": "Web browser; Windows, macOS and Linux with Python 3.10 or later",
            "softwareVersion": __version__,
            "image": picture,
            "inLanguage": list(LANGS),
            "featureList": [str(item["title"]) for item in items(loc.lang, "features")],
            "teaches": [f"{name} vocabulary, CEFR levels A1 to B2" for name in taught],
            "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
            "license": CODE_LICENSE,
            "sameAs": [REPO, PACKAGE],
            "publisher": {"@id": publisher},
        },
        {
            "@type": "FAQPage",
            "@id": f"{here}#faq",
            "inLanguage": loc.lang,
            "isPartOf": {"@id": f"{here}#webpage"},
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": str(item["q"]),
                    "acceptedAnswer": {"@type": "Answer", "text": str(item["a"])},
                }
                for item in items(loc.lang, "faq")
            ],
        },
    ]


def home(loc: Locale, resource: str) -> str:
    """The start page: what VocabBot is, a day of learning, the courses, the setup and the FAQ."""
    works = "".join(f"<span>{_icon(name)}{escape(label)}</span>" for name, label in WORKS)
    start = (
        f'<a class="btn primary lg" href="/app/">{loc.t("hero_primary")}'
        f"{_icon('arrow', 'arrow')}</a>"
    )
    floats = "".join(
        _word(lang, word, f"float f{place}") for place, (lang, word) in enumerate(FLOATS, start=1)
    )
    hero = (
        '<section class="hero"><div class="grid-bg" aria-hidden="true"></div>'
        f'<div class="floats" aria-hidden="true">{floats}</div><div class="wrap">'
        '<div class="hero-copy">'
        f'<a class="announce" href="/app/"><span class="tag">{loc.t("hero_badge_tag")}</span>'
        f'<span class="txt">{loc.t("hero_badge")}</span>{_icon("chevron")}</a>'
        f'<h1 class="display">{_display(loc)}</h1>'
        f'<p class="lead">{loc.t("hero_lead")}</p>'
        f'<div class="ctas">{start}'
        f'<a class="btn secondary lg" href="#connect">{loc.t("hero_secondary")}</a></div>'
        f'<div class="works"><span class="label">{loc.t("works_with")}</span>{works}</div></div>'
        f"{_showcase(loc)}</div></section>"
    )
    cells = "".join(
        f'<article class="cell reveal d{place % 2}"><div class="visual" aria-hidden="true">'
        f"{_visual(str(item['icon']))}"
        f"</div><h3>{_icon(str(item['icon']))}{escape(str(item['title']))}</h3>"
        f"<p>{escape(str(item['text']))}</p></article>"
        for place, item in enumerate(items(loc.lang, "features"))
    )
    features = (
        '<section class="section" id="features"><div class="wrap">'
        f'{_section_head(loc, "features")}<div class="bento">{cells}</div></div></section>'
    )
    steps = "".join(
        f'<li class="day-step reveal d{place}"><div class="visual" aria-hidden="true">'
        f"{_stage_picture(str(item['name']))}</div>"
        f'<div class="rail"><span class="step-no">{place + 1:02d}</span><i></i></div>'
        f"<h3>{escape(str(item['title']))}</h3><p>{escape(str(item['text']))}</p></li>"
        for place, item in enumerate(items(loc.lang, "day_steps"))
    )
    day = (
        '<section class="section alt" id="day"><div class="wrap">'
        f'{_section_head(loc, "day")}<ol class="day-grid">{steps}</ol></div></section>'
    )
    commands = (
        ("cmd-claude", f"claude mcp add --transport http vocabbot {resource}"),
        ("cmd-codex", f"codex mcp add vocabbot --url {resource}"),
    )

    def way(place: int, item: dict[str, Any]) -> str:
        more = ""
        if item["icon"] == "terminal":
            more = (
                '<div class="term">'
                + "".join(
                    f'<div class="term-line"><span class="ps" aria-hidden="true">$</span>'
                    f'<code id="{key}">{escape(line)}</code>{_copy(loc, key)}</div>'
                    for key, line in commands
                )
                + "</div>"
            )
        elif item["icon"] == "phone":
            more = (
                f'<a class="btn secondary sm" href="/app/">{loc.t("nav_open")}'
                f"{_icon('arrow', 'arrow')}</a>"
            )
        wide = " wide" if item["icon"] == "terminal" else ""
        return (
            f'<article class="connect-card reveal d{place % 3}{wide}"><div class="cc-head">'
            f'<span class="tile">{_icon(str(item["icon"]))}</span><div>'
            f"<h3>{escape(str(item['name']))}</h3>"
            f'<p class="where">{escape(str(item["where"]))}</p></div></div>'
            f'<p class="steps">{_rich(str(item["steps"]))}</p>{more}</article>'
        )

    connect = (
        '<section class="section alt" id="connect"><div class="wrap">'
        f"{_section_head(loc, 'connect')}"
        f'<div class="address reveal"><span class="address-label">{_icon("link")}'
        f'{loc.t("connect_address")}</span><div class="copybox"><code id="mcp-url">'
        f"{escape(resource)}</code>{_copy(loc, 'mcp-url')}</div></div>"
        '<div class="connect-grid">'
        + "".join(way(place, item) for place, item in enumerate(items(loc.lang, "connect_items")))
        + "</div></div></section>"
    )
    questions = "".join(
        f'<details class="qa" name="faq"{" open" if place == 0 else ""}><summary>'
        f"<h3>{escape(str(item['q']))}</h3>{_icon('plus')}</summary>"
        f'<div class="qa-body"><p>{escape(str(item["a"]))}</p></div></details>'
        for place, item in enumerate(items(loc.lang, "faq"))
    )
    faq = (
        '<section class="section" id="faq"><div class="wrap narrow">'
        f'{_section_head(loc, "faq")}<div class="faq reveal">{questions}</div></div></section>'
    )
    cta = (
        '<section class="section"><div class="wrap"><div class="cta-box reveal">'
        f'<div class="grid-bg" aria-hidden="true"></div>{_mark("lg")}'
        f'<h2>{loc.t("cta_title")}</h2><p class="sub">{loc.t("cta_lead")}</p>'
        f'<div class="ctas">{start}'
        f'<a class="btn secondary lg" href="/app/login">{loc.t("nav_sign_in")}</a></div>'
        "</div></div></section>"
    )
    body = (
        _site_top(loc, home=True)
        + f'<main id="main">{hero}{_stats(loc)}{features}{day}{_courses(loc)}{connect}{faq}{cta}'
        + "</main>"
        + _site_foot(loc, home=True)
    )
    title, description = loc.say("seo_title"), loc.say("seo_description")
    return _page(
        loc,
        title,
        body,
        index=True,
        description=description,
        data=_home_data(loc, title, description),
        motion=True,
    )


def privacy(loc: Locale) -> str:
    headings = items(loc.lang, "privacy_headings")
    texts = items(loc.lang, "privacy")
    sections = "".join(
        f'<section class="doc-sec"><span class="num">{number:02d}</span><div>'
        f"<h2>{escape(str(heading))}</h2><p>{escape(str(text))}</p></div></section>"
        for number, (heading, text) in enumerate(zip(headings, texts, strict=True), start=1)
    )
    head = (
        f'<div class="doc-head"><span class="eyebrow">{_icon("shield")}VocabBot</span>'
        f'<h1>{loc.t("privacy_title")}</h1><p class="lead">{loc.t("privacy_lead")}</p></div>'
    )
    body = (
        _site_top(loc, home=False)
        + f'<main class="wrap narrow doc" id="main">{head}{sections}</main>'
        + _site_foot(loc, home=False)
    )
    title = f"{loc.say('privacy_title')} · VocabBot"
    here = loc.address()
    data: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{here}#webpage",
            "url": here,
            "name": title,
            "description": loc.say("privacy_lead"),
            "inLanguage": loc.lang,
            "isPartOf": {"@id": f"{loc.site}/#website"},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "VocabBot",
                    "item": address(loc.site, "/", loc.lang),
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": loc.say("privacy_title"),
                    "item": here,
                },
            ],
        },
    ]
    return _page(loc, title, body, index=True, description=loc.say("privacy_lead"), data=data)


# ------------------------------------------------------------ files for crawlers


def robots(site: str) -> str:
    """/robots.txt: the public pages are open to every crawler; forms and the API are not."""
    agents = "".join(f"User-agent: {name}\n" for name in ("*", *CRAWLERS))
    rules = "Allow: /\n" + "".join(f"Disallow: {path}\n" for path in PRIVATE)
    return f"{agents}{rules}\nSitemap: {site}/sitemap.xml\n"


def sitemap(site: str) -> str:
    """/sitemap.xml: every indexed page in both languages, each naming its other language."""
    rows = ""
    for path in INDEXED:
        links = "".join(
            f'<xhtml:link rel="alternate" hreflang="{code}" href="'
            f'{escape(address(site, path, LANGS[0] if code == "x-default" else code))}"/>'
            for code in (*LANGS, "x-default")
        )
        for lang in LANGS:
            rows += f"<url><loc>{escape(address(site, path, lang))}</loc>{links}</url>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        f' xmlns:xhtml="http://www.w3.org/1999/xhtml">{rows}</urlset>\n'
    )


def llms(site: str, resource: str) -> str:
    """/llms.txt: what VocabBot is, as Markdown for the models that answer questions about it."""
    sizes = course_sizes()

    def en(name: str) -> str:
        return say("en", name)

    names = [en(f"lang_names.{lang}") for lang in sizes]
    levels = sorted({level.upper() for counted in sizes.values() for level in counted})
    lines = [
        "# VocabBot",
        "",
        f"> {en('seo_description')}",
        "",
        en("hero_lead"),
        "",
        f"- Website: {site}/",
        f"- MCP server address: {resource}",
        f"- Languages taught: {', '.join(names)}",
        f"- Levels: {', '.join(levels)} (CEFR)",
        "- Base language of the courses: Polish",
        "- Scheduling: FSRS-6 spaced repetition, 90% retention by default",
        "- Works with: Claude, ChatGPT, Claude Code, Codex, a web browser and a terminal",
        "- Licences: code under Apache-2.0, courses under CC BY-SA 4.0",
        f"- Version: {__version__}",
        "",
        f"## {en('features_eyebrow')}",
        "",
        en("features_lead"),
        "",
    ]
    lines += [f"- **{item['title']}**: {item['text']}" for item in items("en", "features")]
    lines += ["", f"## {en('day_title')}", "", en("day_lead"), ""]
    lines += [
        f"{place}. **{item['title']}**: {item['text']}"
        for place, item in enumerate(items("en", "day_steps"), start=1)
    ]
    lines += ["", f"## {en('langs_title')}", "", en("langs_lead"), ""]
    if sizes:
        heads = sorted({level for counted in sizes.values() for level in counted})
        lines.append(f"| Language | {' | '.join(h.upper() for h in heads)} | {en('langs_total')} |")
        lines.append("|---|" + "---:|" * (len(heads) + 1))
        for lang, counted in sizes.items():
            cells = " | ".join(str(counted.get(level, 0)) for level in heads)
            lines.append(f"| {en(f'lang_names.{lang}')} | {cells} | {sum(counted.values())} |")
        lines.append("")
    lines += [en("langs_note"), "", f"## {en('connect_title')}", "", en("connect_lead"), ""]
    lines += [
        f"- **{item['name']}** ({item['where']}): {item['steps']}"
        for item in items("en", "connect_items")
    ]
    lines += [
        "",
        "```",
        f"claude mcp add --transport http vocabbot {resource}",
        f"codex mcp add vocabbot --url {resource}",
        "```",
        "",
        f"## {en('faq_title')}",
        "",
    ]
    for item in items("en", "faq"):
        lines += [f"### {item['q']}", "", str(item["a"]), ""]
    lines += [
        "## Links",
        "",
        f"- [Start page in Polish]({address(site, '/', 'pl')})",
        f"- [Start page in English]({address(site, '/', 'en')})",
        f"- [Learning session in the browser]({site}/app/)",
        f"- [Privacy]({address(site, '/privacy', 'en')})",
        f"- [Source code]({REPO})",
        f"- [Python package]({PACKAGE})",
        "",
        "## Po polsku",
        "",
        say("pl", "seo_description"),
        "",
        say("pl", "hero_lead"),
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------ the card and the session page


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
        # the language a learner's answer came from (`other_lang` of a result)
        "languages": {code: assets.language_name(code) for code in assets.known_languages()},
    }
    blob = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    template = (resources.files("vocabbot.server") / "static" / "card.html").read_text("utf-8")
    return template.replace("/*VOCABBOT_LABELS*/{}", blob).replace(
        "/*VOCABBOT_VERSION*/", __version__
    )


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
