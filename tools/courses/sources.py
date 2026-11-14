"""Where the course sources come from and where the pipeline keeps them.

Everything downloaded or derived stays in .cache/ (outside git). The fetch
step records the address, date, size and SHA-256 of every file it downloads
in .cache/sources/manifest.json.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / ".cache"
SOURCES = CACHE / "sources"
WORK = CACHE / "work"
TOOLS = Path(__file__).resolve().parent
COURSES = REPO / "src" / "vocabbot" / "data" / "courses"

WIKTIONARY = SOURCES / "raw-wiktextract-data.jsonl.gz"
CEFRJ = SOURCES / "olp-cefrj-vocabulary-profile-1.5.csv"
TATOEBA = SOURCES / "tatoeba"

TATOEBA_BASE = "https://downloads.tatoeba.org/exports/per_language"
DOWNLOADS = {
    WIKTIONARY: "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz",
    CEFRJ: "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/"
    "cefrj-vocabulary-profile-1.5.csv",
    SOURCES
    / "olp-README.md": "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/"
    "master/README.md",
}
TATOEBA_LANG = {"en": "eng", "de": "deu", "es": "spa", "fr": "fra", "pl": "pol"}
# languages whose Tatoeba sentences carry a Polish translation to many of our sentences
EXTRA_PIVOTS = {
    "ja": "jpn",
    "uk": "ukr",
    "he": "heb",
    "eo": "epo",
    "ru": "rus",
    "hu": "hun",
    "nl": "nld",
    "it": "ita",
}
TATOEBA_LANG.update(EXTRA_PIVOTS)
for code in ("eng", "deu", "spa", "fra", "pol"):
    DOWNLOADS[TATOEBA / f"{code}_sentences_detailed.tsv.bz2"] = (
        f"{TATOEBA_BASE}/{code}/{code}_sentences_detailed.tsv.bz2"
    )
for code in ("deu", "spa", "fra", "eng", *EXTRA_PIVOTS.values()):
    DOWNLOADS[TATOEBA / f"{code}-pol_links.tsv.bz2"] = (
        f"{TATOEBA_BASE}/{code}/{code}-pol_links.tsv.bz2"
    )
for target in ("deu", "spa", "fra"):
    for pivot in EXTRA_PIVOTS.values():
        DOWNLOADS[TATOEBA / f"{target}-{pivot}_links.tsv.bz2"] = (
            f"{TATOEBA_BASE}/{target}/{target}-{pivot}_links.tsv.bz2"
        )
for pair in (
    "deu-eng",
    "spa-eng",
    "fra-eng",
    "eng-deu",
    "eng-spa",
    "eng-fra",
    "deu-fra",
    "deu-spa",
    "fra-deu",
    "fra-spa",
    "spa-deu",
    "spa-fra",
):
    first = pair.split("-")[0]
    DOWNLOADS[TATOEBA / f"{pair}_links.tsv.bz2"] = f"{TATOEBA_BASE}/{first}/{pair}_links.tsv.bz2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(force: bool = False) -> dict[str, dict[str, object]]:
    """Download every source that is missing and write the manifest."""
    SOURCES.mkdir(parents=True, exist_ok=True)
    TATOEBA.mkdir(parents=True, exist_ok=True)
    manifest_path = SOURCES / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.is_file() else {}
    for path, url in DOWNLOADS.items():
        key = str(path.relative_to(SOURCES)).replace("\\", "/")
        if force or not path.is_file():
            subprocess.run(["curl", "-sfL", "--retry", "5", "-o", str(path), url], check=True)
            manifest.pop(key, None)
        if key not in manifest:
            manifest[key] = {
                "url": url,
                "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    return manifest
