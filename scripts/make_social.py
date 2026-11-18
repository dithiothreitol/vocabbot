"""Render the pictures a shared link to the start page shows (Open Graph, X, Slack).

    python scripts/make_social.py    writes the files below

- src/vocabbot/server/static/social-pl.png   1200 by 630, the Polish page
- src/vocabbot/server/static/social-en.png   1200 by 630, the English page

The picture is a small HTML page in the start page's look (the Geist typeface,
the avatar and its colours, the headline and a card of a session), styled by
scripts/social.css, that a headless Chrome or Edge renders. Set CHROME to the
browser's program when it is not in a usual place. The texts come from
data/i18n/pl.json and en.json, so a new headline needs only a new run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "vocabbot" / "server" / "static"
I18N = ROOT / "src" / "vocabbot" / "data" / "i18n"
WIDTH, HEIGHT = 1200, 630
BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
)
STYLE = (Path(__file__).with_name("social.css")).read_text("utf-8")


def texts(lang: str) -> dict[str, object]:
    server: dict[str, object] = json.loads((I18N / f"{lang}.json").read_text("utf-8"))["server"]
    return server


def page(lang: str) -> str:
    own, polish = texts(lang), json.loads((I18N / "pl.json").read_text("utf-8"))
    mock = polish["server"]["mock"]
    mark = (STATIC / "vocabbot.svg").read_text("utf-8").strip()
    check = '<svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>'
    back = polish["back"]["days"].format(days=4)
    langs = "".join(
        f'<span class="lc"><i style="background:{colour}"></i>{code}</span>'
        for code, colour in (
            ("EN", "#006bff"),
            ("DE", "#f5a524"),
            ("ES", "#e5484d"),
            ("FR", "#8e4ec6"),
            ("IT", "#45a557"),
        )
    )
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><style>{STYLE}</style>'
        '</head><body><div class="grid"></div>'
        f'<div class="copy"><div class="brand">{mark}VocabBot</div>'
        f"<h1>{escape(str(own['hero_title']))}<span>{escape(str(own['hero_accent']))}</span></h1>"
        f"<p>{escape(str(own['footer_tagline']))}</p>"
        f'<div class="langs">{langs}<span class="lv">A1 · A2 · B1 · B2</span></div></div>'
        '<div class="host">vocabbot.run</div>'
        '<div class="stage"><div class="card">'
        f'<div class="head">{mark}VocabBot<b>{escape(mock["counter"])}</b></div>'
        '<div class="bar"><i></i></div>'
        f'<span class="chip"><i></i>{escape(mock["lang"])}</span>'
        f'<div class="word">{escape(mock["prompt"])}</div>'
        f'<div class="meta">{escape(mock["meta"])}</div></div>'
        f'<div class="answer" lang="de">{escape(mock["answer"])}</div>'
        f'<div class="grade"><span class="ok">{check}{escape(polish["grades"]["know"])}</span>'
        f'<span class="back">{escape(back)}</span></div></div>'
        '<div class="edge"><i></i></div></body></html>'
    )


def browser() -> str:
    named = os.environ.get("CHROME")
    if named:
        return named
    for candidate in BROWSERS:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    sys.exit("make_social: no Chrome or Edge found; set CHROME to the browser's program")


def render(program: str, lang: str) -> None:
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        shutil.copy(STATIC / "geist.woff2", work / "geist.woff2")
        source = work / "social.html"
        source.write_text(page(lang), "utf-8")
        target = STATIC / f"social-{lang}.png"
        subprocess.run(
            [
                program,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--allow-file-access-from-files",
                f"--user-data-dir={work / 'profile'}",
                f"--window-size={WIDTH},{HEIGHT}",
                "--virtual-time-budget=2000",
                f"--screenshot={target}",
                source.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
        print(f"wrote {target.relative_to(ROOT)}")


def main() -> None:
    program = browser()
    for lang in ("pl", "en"):
        render(program, lang)


if __name__ == "__main__":
    main()
