"""Pronunciation recordings from Wikimedia Commons: one file per course entry.

English, German and French recordings come with the Wiktionary extract (the
`audio` field of a record). Spanish and Italian ones mostly do not, because
Wiktionary keeps them inside the pronunciation templates of these languages,
which the extract does not expand. For them `fetch` lists the Lingua Libre
recordings on Commons (one category per language) into
.cache/sources/lingualibre/<code>.txt and records the listing in the manifest.

The courses keep only the file name; the engine turns it into the address of
the file on Commons (`vocabbot.courses.audio_url`), so the package holds no
recordings.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from sources import SOURCES, described, read_manifest, write_manifest

LINGUALIBRE = {"es": "spa", "it": "ita"}
FOLDER = SOURCES / "lingualibre"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "vocab-course-pipeline/1.0 (python-urllib)"
PAUSE = 1.5  # seconds between the pages of a listing, as Wikimedia's API etiquette asks
TITLE = re.compile(
    r"^LL-Q\d+ \((?P<code>[a-z]{3})\)-(?P<rest>.+)\.(?P<ext>wav|ogg|oga|opus|flac|mp3|webm)$",
    re.IGNORECASE,
)
VARIANT = re.compile(r"^\((?P<variant>[^)]*)\) ?")


def category(code: str) -> str:
    return f"Category:Lingua_Libre_pronunciation-{code}"


def _get(params: dict[str, str]) -> dict[str, object]:
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data: dict[str, object] = json.load(response)
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503):
                raise
            wait = exc.headers.get("Retry-After") or "10"
            time.sleep((int(wait) if wait.isdigit() else 10) + 5 * attempt)
    raise SystemExit(f"Commons kept refusing the listing of {params.get('cmtitle')}")


def list_titles(code: str) -> list[str]:
    """Every file in the Lingua Libre category of a language, without the File: prefix."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category(code),
        "cmtype": "file",
        "cmprop": "title",
        "cmlimit": "500",
        "format": "json",
    }
    titles: list[str] = []
    while True:
        data = _get(params)
        if "error" in data:
            # an error reply has no `continue` either; taking it for the end would cut the list
            raise SystemExit(f"Commons refused the listing of {category(code)}: {data['error']}")
        query = data.get("query")
        members = query.get("categorymembers", []) if isinstance(query, dict) else []
        titles += [str(m["title"]).removeprefix("File:") for m in members]
        more = data.get("continue")
        if not isinstance(more, dict):
            return sorted(set(titles))
        params.update({str(k): str(v) for k, v in more.items()})
        time.sleep(PAUSE)


def fetch(force: bool = False) -> dict[str, dict[str, object]]:
    """List the recordings of every language in LINGUALIBRE that has no listing yet."""
    FOLDER.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    for code in LINGUALIBRE.values():
        path = FOLDER / f"{code}.txt"
        key = f"lingualibre/{code}.txt"
        if force or not path.is_file():
            titles = list_titles(code)
            path.write_bytes(("\n".join(titles) + "\n").encode("utf-8"))
            manifest.pop(key, None)
        if key not in manifest:
            url = f"{API}?action=query&list=categorymembers&cmtitle={category(code)}"
            manifest[key] = described(path, url)
    write_manifest(manifest)
    return {k: v for k, v in manifest.items() if k.startswith("lingualibre/")}


def parse(title: str) -> list[tuple[str, str, str | None]]:
    """The (word, speaker, variant) readings of a Lingua Libre file name.

    The name is `LL-Q<id> (<code>)-<speaker>-<word>.<ext>`, the word sometimes
    after a variant in brackets ("(American Spanish) palabra"). A speaker's name
    may hold a hyphen itself, so every split after a hyphen is a reading; the
    course word picks the one that matches it.
    """
    match = TITLE.match(title)
    if not match:
        return []
    rest = match["rest"]
    readings: list[tuple[str, str, str | None]] = []
    for position in [i for i, char in enumerate(rest) if char == "-"]:
        speaker, word = rest[:position], rest[position + 1 :]
        variant_match = VARIANT.match(word)
        variant = variant_match["variant"] if variant_match else None
        if variant_match:
            word = word[variant_match.end() :]
        word = " ".join(word.replace("_", " ").split())
        if speaker and word:
            readings.append((word, speaker, variant))
    return readings


def index(lang: str, folder: Path = FOLDER) -> dict[str, str]:
    """A recording for every word Lingua Libre has in the language, by the word in lower case.

    Among several recordings of one word the choice is a file without a variant
    in its name, then the speaker with the most recordings (one voice for as
    many words as possible), then the file name, so it repeats between builds.
    """
    code = LINGUALIBRE.get(lang)
    path = folder / f"{code}.txt"
    if code is None or not path.is_file():
        return {}
    titles = [t for t in path.read_text("utf-8").splitlines() if t.strip()]
    parsed = [(title, parse(title)) for title in titles]
    # a name with one hyphen names its speaker for sure; those speakers settle the others,
    # and a name no known speaker settles keeps every reading (a wrong one names no word)
    sure: Counter[str] = Counter(r[0][1] for _, r in parsed if len(r) == 1)
    chosen: list[tuple[str, tuple[str, str, str | None]]] = []
    for title, readings in parsed:
        known = [r for r in readings if sure[r[1]]]
        if known:
            chosen.append((title, max(known, key=lambda r: sure[r[1]])))
        else:
            chosen += [(title, reading) for reading in readings]
    speakers = Counter(reading[1] for _, reading in chosen)
    best: dict[str, tuple[tuple[int, int, str], str]] = {}
    for title, (word, speaker, variant) in chosen:
        key = word.casefold()
        rank = (int(variant is not None), -speakers[speaker], title)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, title)
    return {key: title for key, (_, title) in best.items()}
