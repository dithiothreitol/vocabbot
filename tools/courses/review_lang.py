"""Review of a course language added after the first review, by Claude Sonnet 5.5 (Message Batches).

    uv run --group data python tools/courses/review_lang.py prepare --lang it    requests and a cost estimate, no API call
    uv run --group data python tools/courses/review_lang.py submit --lang it --max-usd 6
    uv run --group data python tools/courses/review_lang.py collect --lang it    results into tools/courses/review-it.jsonl

The concepts of the course keep the sense and the Polish meaning the first
review and the editors chose. For every concept the model gives only the
equivalent in the added language, seeing the German, Spanish and French words
the course already uses for that sense and the candidates of Wiktionary's
translation tables. tools/courses/review-<lang>.jsonl keeps every decision (it
is committed), so the course builds again the same way without the API. The
API key comes from ANTHROPIC_API_KEY or from a .env file in the repository
(ignored by git); it is never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from typing import Any

import build as builder
from concepts import read as read_concepts
from review import client
from sources import TOOLS, WORK
from wiktionary import load

MODEL = "claude-sonnet-5-5"
PRICE_INPUT, PRICE_OUTPUT = 1.0, 5.0  # USD per million tokens, Message Batches, Sonnet 5.5
ITEMS_PER_REQUEST = 30
MAX_TOKENS = 6000
CHARS_PER_TOKEN = 3.0
OUTPUT_TOKENS_PER_ITEM = 70  # one short object per item and a little thinking at low effort
MAX_CANDIDATES = 8

LANGUAGES = {
    "it": {
        "name": "Italian",
        "form": (
            "a noun with its definite article in the singular (il; lo before s and a"
            " consonant, z, gn, ps, x or y; la; l' before a vowel or h, joined to the word as"
            " in l'amico), a verb in the infinitive (with -si when the verb is reflexive in this"
            " sense, as in lavarsi), an adjective in the masculine singular. Months go without an"
            " article (gennaio). A noun the sense needs in the plural takes its plural article"
            " (i genitori) and the gender pl."
        ),
        "genders": ["m", "f", "pl", "none"],
    },
}

SYSTEM = """You add {name} to a vocabulary course for adult Polish speakers at CEFR levels A1 to B2.

Each item is a concept the course already teaches: the English headword with its part of speech and level, the sense the course chose, the Polish meaning the learner is asked about, the German, Spanish and French words the course uses for that sense, and candidate {name} translations from English Wiktionary's translation tables, each with the sense of its table and its gender in brackets.

For each item give the most common standard {name} equivalent of exactly that sense, the word a learner at that level should learn for the Polish meaning, in its citation form: {form} Give the gender of a noun as {genders}, and none for other words. Prefer a candidate when one is right for the sense; otherwise give the right word. Add up to two other answers that are equally correct for that sense, in the same citation form, under "also". When {name} has no single common word for the sense, leave word empty.

Answer with one object per item, in the order of the items."""


def schema(lang: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "word": {"type": "string"},
                        "gender": {"type": "string", "enum": LANGUAGES[lang]["genders"]},
                        "also": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "word", "gender", "also"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


def paths(lang: str) -> dict[str, Any]:
    return {
        "review": TOOLS / f"review-{lang}.jsonl",
        "requests": WORK / f"review-{lang}-requests.jsonl",
        "batch": WORK / f"review-{lang}-batch.json",
    }


def candidates(records: list[dict[str, Any]], lang: str) -> list[str]:
    out: list[str] = []
    for record in records:
        for item in record.get("translations", []):
            if item["lang"] != lang:
                continue
            word = builder.clean(item["word"])
            if not word:
                continue
            genders = [
                {"masculine": "m", "feminine": "f", "neuter": "n"}[t]
                for t in item.get("tags") or []
                if t in ("masculine", "feminine", "neuter")
            ]
            label = f"{word} [{'/'.join(genders)}]" if genders else word
            sense = str(item.get("sense") or "")[:60]
            entry = f"{label} ({sense})" if sense else label
            if entry not in out:
                out.append(entry)
    return out[:MAX_CANDIDATES]


def known(decision: dict[str, Any]) -> dict[str, str]:
    return {
        code: str((decision.get(code) or {}).get("word") or "")
        for code in builder.FIRST_TARGETS
        if (decision.get(code) or {}).get("word")
    }


def items(lang: str) -> list[dict[str, Any]]:
    """One item per concept the course keeps, with its sense and Polish meaning."""
    english: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in load("english.jsonl"):
        english.setdefault((record["word"], record["pos"]), []).append(record)
    reviews = builder.load_review()
    editor = builder.load_editor()
    out = []
    for concept in read_concepts():
        review = reviews.get(concept.id)
        edit = editor.get(concept.id)
        decision = builder.decision_of(review, edit)
        if decision is None or not decision.get("keep", True):
            continue
        if builder.reviewed_gloss(str(decision.get("pl") or "")) is None:
            continue
        if lang in (edit or {}):
            continue  # the editors chose this language's word themselves
        en = decision.get("en", True)
        headword = str(en["word"]) if isinstance(en, dict) else concept.headword
        pos = str(decision.get("pos") or concept.pos)
        out.append(
            {
                "id": concept.id,
                "word": headword,
                "pos": pos,
                "level": str(decision.get("level") or concept.level).upper(),
                "sense": str(decision.get("sense") or "")[:100],
                "pl": str(decision.get("pl")),
                "course": known(decision),
                "candidates": candidates(english.get((headword, concept.pos), []), lang),
            }
        )
    return out


def request_body(lang: str, chunk: list[dict[str, Any]]) -> dict[str, Any]:
    spec = LANGUAGES[lang]
    system = SYSTEM.format(
        name=spec["name"], form=spec["form"], genders=", ".join(spec["genders"][:-1])
    )
    lines = "\n".join(json.dumps(item, ensure_ascii=False) for item in chunk)
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "output_config": {
            "effort": "low",
            "format": {"type": "json_schema", "schema": schema(lang)},
        },
        "messages": [{"role": "user", "content": f"Items ({len(chunk)}):\n{lines}"}],
    }


def done_ids(lang: str) -> set[str]:
    path = paths(lang)["review"]
    if not path.is_file():
        return set()
    return {json.loads(line)["id"] for line in path.read_text("utf-8").splitlines() if line.strip()}


def prepare(lang: str, only_missing: bool = False) -> dict[str, Any]:
    pending = items(lang)
    if only_missing:
        done = done_ids(lang)
        pending = [item for item in pending if item["id"] not in done]
    chunks = [pending[i : i + ITEMS_PER_REQUEST] for i in range(0, len(pending), ITEMS_PER_REQUEST)]
    WORK.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    with paths(lang)["requests"].open("wb") as fh:
        for number, chunk in enumerate(chunks, 1):
            body = request_body(lang, chunk)
            total_chars += len(body["system"]) + len(body["messages"][0]["content"])
            row = {"custom_id": f"review-{lang}-{number:04d}", "params": body}
            fh.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    input_tokens = total_chars / CHARS_PER_TOKEN
    output_tokens = len(pending) * OUTPUT_TOKENS_PER_ITEM
    cost = input_tokens / 1e6 * PRICE_INPUT + output_tokens / 1e6 * PRICE_OUTPUT
    return {
        "lang": lang,
        "items": len(pending),
        "without_candidates": sum(1 for item in pending if not item["candidates"]),
        "requests": len(chunks),
        "input_tokens": round(input_tokens),
        "output_tokens": output_tokens,
        "estimated_usd": round(cost, 2),
    }


def submit(lang: str, max_usd: float, only_missing: bool) -> dict[str, Any]:
    estimate = prepare(lang, only_missing)
    if estimate["estimated_usd"] > max_usd:
        raise SystemExit(
            f"estimated {estimate['estimated_usd']} USD is above the limit of {max_usd} USD"
        )
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    files = paths(lang)
    rows = [json.loads(line) for line in files["requests"].read_text("utf-8").splitlines() if line]
    api = client()
    sample = rows[0]["params"]
    counted = api.messages.count_tokens(
        model=MODEL,
        system=sample["system"],
        messages=sample["messages"],
        output_config=sample["output_config"],
    )
    measured = counted.input_tokens * len(rows)
    cost = measured / 1e6 * PRICE_INPUT + estimate["output_tokens"] / 1e6 * PRICE_OUTPUT
    if cost > max_usd:
        raise SystemExit(f"measured estimate {cost:.2f} USD is above the limit of {max_usd} USD")
    batch = api.messages.batches.create(
        requests=[
            Request(
                custom_id=row["custom_id"], params=MessageCreateParamsNonStreaming(**row["params"])
            )
            for row in rows
        ]
    )
    record = {
        "id": batch.id,
        "created": date.today().isoformat(),
        "requests": len(rows),
        "estimated_usd": round(cost, 2),
        "first_request_input_tokens": counted.input_tokens,
    }
    files["batch"].write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return record


def collect(lang: str, wait: bool) -> dict[str, Any]:
    files = paths(lang)
    record = json.loads(files["batch"].read_text("utf-8"))
    api = client()
    while True:
        batch = api.messages.batches.retrieve(record["id"])
        if batch.processing_status == "ended" or not wait:
            break
        time.sleep(60)
    if batch.processing_status != "ended":
        return {"status": batch.processing_status, "counts": batch.request_counts.model_dump()}
    requests = {
        json.loads(line)["custom_id"]: json.loads(line)
        for line in files["requests"].read_text("utf-8").splitlines()
        if line.strip()
    }
    reviewed: dict[str, dict[str, Any]] = {}
    if files["review"].is_file():
        for line in files["review"].read_text("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                reviewed[row["id"]] = row
    usage = {"input": 0, "output": 0}
    failed = []
    for result in api.messages.batches.results(record["id"]):
        if result.result.type != "succeeded":
            failed.append(result.custom_id)
            continue
        message = result.result.message
        usage["input"] += message.usage.input_tokens
        usage["output"] += message.usage.output_tokens
        text = next((b.text for b in message.content if b.type == "text"), "")
        try:
            answer = json.loads(text)["items"]
        except (ValueError, KeyError):
            failed.append(result.custom_id)
            continue
        asked = {item["id"]: item for item in _items_of(requests.get(result.custom_id))}
        for item in answer:
            if item.get("id") in asked:
                choice = {"word": item["word"], "gender": item["gender"], "also": item["also"]}
                reviewed[item["id"]] = {
                    "id": item["id"],
                    lang: choice,
                    "headword": asked[item["id"]]["word"],
                    "model": MODEL,
                }
    lines = [json.dumps(reviewed[k], ensure_ascii=False) for k in sorted(reviewed)]
    files["review"].write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    cost = usage["input"] / 1e6 * PRICE_INPUT + usage["output"] / 1e6 * PRICE_OUTPUT
    return {
        "status": "ended",
        "reviewed": len(reviewed),
        "failed_requests": failed,
        "usage": usage,
        "cost_usd": round(cost, 2),
    }


def _items_of(row: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not row:
        return []
    content = row["params"]["messages"][0]["content"]
    return [json.loads(line) for line in content.split("\n")[1:] if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("prepare", "submit", "collect"))
    parser.add_argument("--lang", required=True, choices=sorted(LANGUAGES))
    parser.add_argument("--max-usd", type=float, default=6.0)
    parser.add_argument(
        "--only-missing", action="store_true", help="only concepts without a decision yet"
    )
    parser.add_argument("--wait", action="store_true", help="wait until the batch has ended")
    args = parser.parse_args(argv)
    if args.step == "prepare":
        result = prepare(args.lang, args.only_missing)
    elif args.step == "submit":
        result = submit(args.lang, args.max_usd, args.only_missing)
    else:
        result = collect(args.lang, args.wait)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
