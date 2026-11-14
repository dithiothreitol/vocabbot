"""Review of the concepts by Claude Sonnet 5.5 through the Message Batches API.

    uv run --group data python tools/courses/review.py prepare            requests and a cost estimate, no API call
    uv run --group data python tools/courses/review.py submit --max-usd 15
    uv run --group data python tools/courses/review.py collect            results into tools/courses/review.jsonl

The model chooses, for every CEFR-J concept, the sense a learner meets first,
the Polish meaning and the German, Spanish and French equivalents with their
gender. tools/courses/review.jsonl keeps every decision (it is committed), so
the course builds again the same way without the API. The API key comes from
ANTHROPIC_API_KEY or from a .env file in the repository (ignored by git); it
is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from typing import Any

from concepts import read as read_concepts
from sources import REPO, TOOLS, WORK
from wiktionary import load

import build as builder

MODEL = "claude-sonnet-5-5"
PRICE_INPUT, PRICE_OUTPUT = (
    1.0,
    5.0,
)  # USD per million tokens, Message Batches price of Claude Sonnet 5.5
ITEMS_PER_REQUEST = 25
MAX_TOKENS = 8000
CHARS_PER_TOKEN = 3.0
OUTPUT_TOKENS_PER_ITEM = 160  # the answer and some thinking at low effort
REVIEW = TOOLS / "review.jsonl"
REQUESTS = WORK / "review-requests.jsonl"
BATCH = WORK / "review-batch.json"
MAX_GROUPS = 3
MAX_CANDIDATES = 6

SYSTEM = """You curate a vocabulary course for adult Polish speakers who learn English, German, Spanish and French at CEFR levels A1 to B2.

Each item is an English headword from the CEFR-J word list with its part of speech and level, the meanings English Wiktionary gives for it, and candidate translations from Wiktionary's translation tables, grouped by sense (gender in brackets).

For each item:
1. Choose the sense a learner at that level meets first in everyday language. For example "coke" at A1 is the drink, "fan" at A1 is a supporter, "cab" is a taxi, "line" is a line, not a rope.
2. Write the Polish meaning the learner will be asked about: one or two common Polish words separated by a comma, in the base form (infinitive, nominative singular, masculine singular adjective), with no explanation. It must name the chosen sense, so that the German, Spanish and French words translate it.
3. For German, Spanish and French give the most common standard equivalent of that sense in its citation form: a noun with the definite article in the singular (der, die, das; el or la, with el before a feminine noun with a stressed initial a; le or la, and l' before a vowel or a mute h), a verb in the infinitive (with sich, -se or se/s' when the verb is reflexive), an adjective in the masculine singular. German nouns start with a capital letter. Give the gender of a noun as m, f or n, and none for other words. Prefer a candidate from the lists, and use another word only when no candidate is right. Add up to two other answers that are equally correct for that sense, in the same citation form, under "also".
4. When a language has no single common word for the sense, leave its word empty.
5. Set keep to false only when no sense of the headword belongs in a vocabulary course at that level.

Answer with one object per item, in the order of the items."""

LANGUAGE = {
    "type": "object",
    "properties": {
        "word": {"type": "string"},
        "gender": {"type": "string", "enum": ["m", "f", "n", "none"]},
        "also": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["word", "gender", "also"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "keep": {"type": "boolean"},
                    "sense": {"type": "string"},
                    "pl": {"type": "string"},
                    "de": LANGUAGE,
                    "es": LANGUAGE,
                    "fr": LANGUAGE,
                },
                "required": ["id", "keep", "sense", "pl", "de", "es", "fr"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def candidates(items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in items:
        word = builder.clean(item["word"])
        if not word:
            continue
        genders = [
            {"masculine": "m", "feminine": "f", "neuter": "n"}[t]
            for t in item.get("tags") or []
            if t in ("masculine", "feminine", "neuter")
        ]
        label = f"{word} [{'/'.join(genders)}]" if genders else word
        if label not in out:
            out.append(label)
    return out[:MAX_CANDIDATES]


def items() -> list[dict[str, Any]]:
    """One review item per concept that has an English entry with a Polish translation."""
    english: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in load("english.jsonl"):
        english.setdefault((record["word"], record["pos"]), []).append(record)
    lexicons = builder.load_lexicons()
    out = []
    for concept in read_concepts():
        records = english.get((concept.headword, concept.pos), [])
        groups = builder.translation_groups(records)
        if not any(g.get("pl") for g in groups):
            continue
        ctx = builder.Context(concept.headword, concept.pos, lexicons)
        scored = sorted(
            ((builder.group_score(g, i, ctx), i, g) for i, g in enumerate(groups) if g.get("pl")),
            key=lambda t: (-t[0], t[1]),
        )[:MAX_GROUPS]
        senses = []
        for _, _, group in sorted(scored, key=lambda t: t[1]):
            sense = next((x.get("sense", "") for v in group.values() for x in v), "")
            senses.append(
                {
                    "sense": sense[:100],
                    **{lang: candidates(group.get(lang, [])) for lang in ("pl", "de", "es", "fr")},
                }
            )
        meanings = [g[:100] for r in records for g in r.get("gloss", [])][:4]
        out.append(
            {
                "id": concept.id,
                "word": concept.headword,
                "pos": concept.pos,
                "level": concept.level.upper(),
                "meanings": meanings,
                "senses": senses,
            }
        )
    return out


def request_body(chunk: list[dict[str, Any]]) -> dict[str, Any]:
    lines = "\n".join(json.dumps(item, ensure_ascii=False) for item in chunk)
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM,
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": f"Items ({len(chunk)}):\n{lines}"}],
    }


def prepare(only_missing: bool = False) -> dict[str, Any]:
    pending = items()
    if only_missing and REVIEW.is_file():
        done = {
            json.loads(line)["id"]
            for line in REVIEW.read_text("utf-8").splitlines()
            if line.strip()
        }
        pending = [item for item in pending if item["id"] not in done]
    chunks = [pending[i : i + ITEMS_PER_REQUEST] for i in range(0, len(pending), ITEMS_PER_REQUEST)]
    WORK.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    with REQUESTS.open("wb") as fh:
        for number, chunk in enumerate(chunks, 1):
            body = request_body(chunk)
            total_chars += len(body["system"]) + len(body["messages"][0]["content"])
            row = {"custom_id": f"review-{number:04d}", "params": body}
            fh.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    input_tokens = total_chars / CHARS_PER_TOKEN
    output_tokens = len(pending) * OUTPUT_TOKENS_PER_ITEM
    cost = input_tokens / 1e6 * PRICE_INPUT + output_tokens / 1e6 * PRICE_OUTPUT
    return {
        "items": len(pending),
        "requests": len(chunks),
        "input_tokens": round(input_tokens),
        "output_tokens": output_tokens,
        "estimated_usd": round(cost, 2),
    }


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    env = REPO / ".env"
    if not key and env.is_file():
        for line in env.read_text("utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set (environment or .env in the repository)")
    return key


def client() -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=api_key())


def submit(max_usd: float, only_missing: bool) -> dict[str, Any]:
    estimate = prepare(only_missing)
    if estimate["estimated_usd"] > max_usd:
        raise SystemExit(
            f"estimated {estimate['estimated_usd']} USD is above the limit of {max_usd} USD"
        )
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    rows = [json.loads(line) for line in REQUESTS.read_text("utf-8").splitlines() if line.strip()]
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
    BATCH.write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return record


def collect(wait: bool) -> dict[str, Any]:
    record = json.loads(BATCH.read_text("utf-8"))
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
        for line in REQUESTS.read_text("utf-8").splitlines()
        if line.strip()
    }
    reviewed: dict[str, dict[str, Any]] = {}
    if REVIEW.is_file():
        for line in REVIEW.read_text("utf-8").splitlines():
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
                # the batch id stays in .cache/work/review-batch.json, not in the repository
                reviewed[item["id"]] = {
                    **item,
                    "headword": asked[item["id"]]["word"],
                    "model": MODEL,
                }
    lines = [json.dumps(reviewed[k], ensure_ascii=False) for k in sorted(reviewed)]
    REVIEW.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
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
    parser.add_argument("--max-usd", type=float, default=15.0)
    parser.add_argument(
        "--only-missing", action="store_true", help="only concepts without a review yet"
    )
    parser.add_argument("--wait", action="store_true", help="wait until the batch has ended")
    args = parser.parse_args(argv)
    if args.step == "prepare":
        result = prepare(args.only_missing)
    elif args.step == "submit":
        result = submit(args.max_usd, args.only_missing)
    else:
        result = collect(args.wait)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
