"""The course pipeline.

    uv run --group data python tools/courses/pipeline.py STEP

    fetch     download the sources into .cache/sources
    extract   one pass over the Wiktionary extract
    build     write src/vocabbot/data/courses
    sample    samples for the review in .cache/work

The same source files always give the same courses.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from typing import Any

import audio
import build as builder
import concepts
import sources
import wiktionary

SAMPLE_SIZE = 150
BANDS = {"a1-a2": ("a1", "a2"), "b1-b2": ("b1", "b2")}


def sample(seed: int = 20261114) -> list[str]:
    entries: dict[str, dict[str, dict[str, Any]]] = json.loads(
        (sources.WORK / "entries.json").read_text("utf-8")
    )
    headwords = {c.id: c.headword for c in concepts.read()}
    written = []
    for lang, items in entries.items():
        for band, levels in BANDS.items():
            pool = sorted(c for c, e in items.items() if e["level"] in levels)
            picked = sorted(
                random.Random(f"{seed}-{lang}-{band}").sample(pool, min(SAMPLE_SIZE, len(pool)))
            )
            lines = []
            compact = []
            for number, concept in enumerate(picked, 1):
                e = items[concept]
                example = e.get("example") or {}
                forms = ", ".join(f"{k}={v}" for k, v in (e.get("forms") or {}).items())
                accept = "/".join(e.get("accept", []))
                core = (
                    f"{number:3d} {headwords.get(concept, '?')} ({e['pos']}, {e['level']}) | "
                    f"{e['gloss']['pl']} | {e['display']}"
                    + (f" [{e['gender']}]" if e.get("gender") else "")
                    + (f" +{accept}" if accept else "")
                )
                compact.append(core)
                lines.append(
                    f"{core} {concept}"
                    + (f" ({forms})" if forms else "")
                    + (
                        f" | {example.get('text')} [{example.get('gap')}] = {example.get('pl')}"
                        if example
                        else ""
                    )
                )
            path = sources.WORK / f"sample-{lang}-{band}.txt"
            path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
            (sources.WORK / f"compact-{lang}-{band}.txt").write_bytes(
                ("\n".join(compact) + "\n").encode("utf-8")
            )
            written.append(str(path))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("fetch", "extract", "build", "sample", "all"))
    args = parser.parse_args(argv)
    start = time.time()
    if args.step in ("fetch", "all"):
        manifest = sources.fetch()
        print(f"sources: {len(manifest)} files")
        listings = audio.fetch()
        print(f"recordings: {len(listings)} Lingua Libre listings")
    if args.step in ("extract", "all"):
        words = {c.headword for c in concepts.read()}
        counts = wiktionary.extract(words)
        print(f"extracted: {counts}")
    if args.step in ("build", "all"):
        report = builder.build()
        print(json.dumps(report, ensure_ascii=False, indent=1))
    if args.step in ("sample", "all"):
        for path in sample():
            print("sample:", path)
    print(f"done in {time.time() - start:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
