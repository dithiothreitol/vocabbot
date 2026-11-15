"""Review of the example sentences by Claude Sonnet 5.5 through the Message Batches API.

    uv run --group data python tools/courses/examples.py prepare            requests and a cost estimate, no API call
    uv run --group data python tools/courses/examples.py submit --max-usd 8
    uv run --group data python tools/courses/examples.py collect --wait     results into tools/courses/examples.jsonl

The build (pipeline.py build) writes up to three candidate sentences for every
entry into .cache/work/example-candidates.jsonl. The model chooses the first
candidate that uses the word in the entry's sense and part of speech, has a
faithful Polish translation and suits adult learners, or none.
tools/courses/examples.jsonl keeps every decision (it is committed), so the
courses build again the same way without the API. The API key comes from
ANTHROPIC_API_KEY or from a .env file in the repository (ignored by git); it is
never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from typing import Any

from review import PRICE_INPUT, PRICE_OUTPUT, client
from sources import TOOLS, WORK

MODEL = "claude-sonnet-5-5"
ITEMS_PER_REQUEST = 40
MAX_TOKENS = 4000
CHARS_PER_TOKEN = 3.0
OUTPUT_TOKENS_PER_ITEM = 24  # one short object per item, no thinking
CANDIDATES = WORK / "example-candidates.jsonl"
REQUESTS = WORK / "examples-requests.jsonl"
BATCH = WORK / "examples-batch.json"
DECISIONS = TOOLS / "examples.jsonl"
LANGUAGES = {"en": "English", "de": "German", "es": "Spanish", "fr": "French", "it": "Italian"}
POS_NAMES = {
    "noun": "noun",
    "verb": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "pron": "pronoun",
    "prep": "preposition",
    "conj": "conjunction",
    "num": "numeral",
    "det": "determiner",
    "interj": "interjection",
    "particle": "particle",
    "phrase": "phrase",
}
ISSUES = ["none", "sense", "part_of_speech", "idiom", "translation", "content", "unnatural"]

SYSTEM = """You check example sentences for a vocabulary course for adult Polish speakers who learn English, German, Spanish, French and Italian at CEFR levels A1 to B2. The course asks for a word by its Polish meaning and shows a sentence in which the word is replaced by a gap, together with the sentence's Polish translation; after the answer the learner sees the whole sentence.

Each item is one course entry: the language, the word, its part of speech, its Polish meaning, the English headword and sense the entry stands for, and up to three candidate sentences, each with its gap (the part the learner types) and its Polish translation.

Choose the first candidate that meets every condition:
1. The gap is the entry's word used in the entry's sense and part of speech. Reject a sentence where the same spelling is another word or another part of speech (a pronoun used as an article, a noun used as a verb), or where the word is part of a fixed phrase with another meaning (German "ab und zu" is not an example of "und").
2. The Polish translation renders the whole sentence faithfully, and the entry's Polish meaning, or a natural form of it, is what the gap means in the sentence.
3. The sentence is natural standard language suitable for adult learners: no vulgar or sexual content, no slurs, no graphic violence, nothing hateful or demeaning.
4. A learner understands the sentence without further context.

Answer pick with the number of that candidate, or 0 when no candidate meets every condition. Answer issue with what is wrong with the first candidate (none when you pick it): sense, part_of_speech, idiom, translation, content or unnatural. Answer with one object per item, in the order of the items."""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "pick": {"type": "integer"},
                    "issue": {"type": "string", "enum": ISSUES},
                },
                "required": ["id", "pick", "issue"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def read_candidates() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CANDIDATES.read_text("utf-8").splitlines() if line.strip()]


def read_decisions() -> dict[str, dict[str, Any]]:
    if not DECISIONS.is_file():
        return {}
    out = {}
    for line in DECISIONS.read_text("utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["entry"]] = row
    return out


def pending(only_missing: bool) -> list[dict[str, Any]]:
    """Entries to review: all, or those whose candidates have no decision yet."""
    rows = read_candidates()
    if not only_missing:
        return rows
    done = read_decisions()
    return [
        row
        for row in rows
        if done.get(row["entry"], {}).get("candidates") != [c["sid"] for c in row["candidates"]]
    ]


def item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["entry"],
        "language": LANGUAGES[row["lang"]],
        "word": row["word"],
        "pos": POS_NAMES.get(row["pos"], row["pos"]),
        "polish": row["meaning"],
        "english": row["headword"],
        "sense": row["sense"],
        "candidates": [
            {"n": number, "text": c["text"], "gap": c["gap"], "polish": c["pl"]}
            for number, c in enumerate(row["candidates"], 1)
        ],
    }


def request_body(chunk: list[dict[str, Any]]) -> dict[str, Any]:
    lines = "\n".join(json.dumps(item(row), ensure_ascii=False) for row in chunk)
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM,
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": f"Items ({len(chunk)}):\n{lines}"}],
    }


def prepare(only_missing: bool = False) -> dict[str, Any]:
    rows = pending(only_missing)
    chunks = [rows[i : i + ITEMS_PER_REQUEST] for i in range(0, len(rows), ITEMS_PER_REQUEST)]
    WORK.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    with REQUESTS.open("wb") as fh:
        for number, chunk in enumerate(chunks, 1):
            body = request_body(chunk)
            total_chars += len(body["system"]) + len(body["messages"][0]["content"])
            row = {"custom_id": f"examples-{number:04d}", "params": body}
            fh.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    input_tokens = total_chars / CHARS_PER_TOKEN
    output_tokens = len(rows) * OUTPUT_TOKENS_PER_ITEM
    cost = input_tokens / 1e6 * PRICE_INPUT + output_tokens / 1e6 * PRICE_OUTPUT
    return {
        "entries": len(rows),
        "candidates": sum(len(r["candidates"]) for r in rows),
        "requests": len(chunks),
        "input_tokens": round(input_tokens),
        "output_tokens": output_tokens,
        "estimated_usd": round(cost, 2),
    }


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
        thinking=sample["thinking"],
        output_config=sample["output_config"],
    )
    sample_chars = len(sample["system"]) + len(sample["messages"][0]["content"])
    measured = counted.input_tokens / sample_chars * estimate["input_tokens"] * CHARS_PER_TOKEN
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
    asked: dict[str, dict[str, Any]] = {}
    for line in REQUESTS.read_text("utf-8").splitlines():
        if line.strip():
            request = json.loads(line)
            content = request["params"]["messages"][0]["content"]
            for raw in content.split("\n")[1:]:
                if raw.strip():
                    entry = json.loads(raw)
                    asked[entry["id"]] = entry
    by_entry = {row["entry"]: row for row in read_candidates()}
    decisions = read_decisions()
    usage = {"input": 0, "output": 0}
    failed: list[str] = []
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
        for decision in answer:
            entry = by_entry.get(decision.get("id", ""))
            if entry is None or entry["entry"] not in asked:
                continue
            sids = [c["sid"] for c in entry["candidates"]]
            pick = decision.get("pick")
            chosen = sids[pick - 1] if isinstance(pick, int) and 1 <= pick <= len(sids) else None
            # the batch id stays in .cache/work/examples-batch.json, not in the repository
            decisions[entry["entry"]] = {
                "entry": entry["entry"],
                "sentence": chosen,
                "candidates": sids,
                "issue": decision.get("issue", "none"),
                "model": MODEL,
            }
    lines = [json.dumps(decisions[k], ensure_ascii=False) for k in sorted(decisions)]
    DECISIONS.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    cost = usage["input"] / 1e6 * PRICE_INPUT + usage["output"] / 1e6 * PRICE_OUTPUT
    chosen_count = sum(1 for d in decisions.values() if d["sentence"] is not None)
    return {
        "status": "ended",
        "decisions": len(decisions),
        "with_sentence": chosen_count,
        "without_sentence": len(decisions) - chosen_count,
        "failed_requests": failed,
        "usage": usage,
        "cost_usd": round(cost, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("prepare", "submit", "collect"))
    parser.add_argument("--max-usd", type=float, default=8.0)
    parser.add_argument(
        "--only-missing", action="store_true", help="only entries whose candidates changed"
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
