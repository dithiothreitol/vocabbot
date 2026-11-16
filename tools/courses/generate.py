"""Example sentences written by Claude Sonnet 5.5 for the entries without one, through the Message Batches API.

    uv run --group data python tools/courses/generate.py prepare [--sample N]        requests and a cost estimate, no API call
    uv run --group data python tools/courses/generate.py submit --max-usd 10 [--sample N]
    uv run --group data python tools/courses/generate.py collect --wait              sentences into tools/courses/generated.jsonl
    uv run --group data python tools/courses/generate.py review-submit --max-usd 4   the example review of the new sentences
    uv run --group data python tools/courses/generate.py review-collect --wait       its verdicts into generated.jsonl

An entry gets a sentence of Tatoeba when the example review accepts one of its
candidates; the others (the build's .cache/work/entries.json) get one sentence
from the model: at the entry's level, in the course's sense and part of
speech, with the gap the learner types and a faithful Polish translation. The
example review (examples.py, the same instructions as for Tatoeba sentences)
then judges every new sentence, and the build uses only the accepted ones.
`--retry` writes a new sentence for an entry whose sentence the review
rejected or the checks refused, once.

tools/courses/generated.jsonl keeps every sentence and verdict (it is
committed), so the courses build again the same way without the API. The API
key comes from ANTHROPIC_API_KEY or from a .env file in the repository
(ignored by git); it is never printed.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from vocabbot.courses import _example_problems

import examples
from review import PRICE_INPUT, PRICE_OUTPUT, client
from sources import TOOLS, WORK

MODEL = "claude-sonnet-5-5"
ITEMS_PER_REQUEST = 40
MAX_TOKENS = 12000
CHARS_PER_TOKEN = 3.0
OUTPUT_TOKENS_PER_ITEM = 90  # the sentence, its gap and its translation, no thinking
REVIEW_OUTPUT_TOKENS_PER_ITEM = examples.OUTPUT_TOKENS_PER_ITEM
ENTRIES = WORK / "entries.json"
GENERATED = TOOLS / "generated.jsonl"
MAX_WORDS = {"a1": 8, "a2": 10, "b1": 12, "b2": 15}
MAX_ATTEMPTS = 2

SYSTEM = """You write example sentences for a vocabulary course for adult Polish speakers who learn English, German, Spanish, French and Italian at CEFR levels A1 to B2. The course asks for a word by its Polish meaning and shows a sentence in which the word is replaced by a gap, together with the sentence's Polish translation; after the answer the learner sees the whole sentence.

Each item is one course entry: the language, the CEFR level, the word as the course shows it (a noun with its definite article), its part of speech, its Polish meaning, and the English headword and sense the entry stands for.

Write one sentence for every item:
1. The sentence uses the entry's word in the entry's sense and part of speech, in natural standard language, and a learner understands it without further context.
2. It is short and simple for the level: at most 8 words at A1, 10 at A2, 12 at B1 and 15 at B2, and the other words are easier than the entry's word.
3. The word appears in the form the course shows when the sentence allows it: the infinitive of a verb, a noun with the article shown. Another form is fine where the language needs it.
4. gap is the exact part of the sentence the learner types for the word: the word as it appears in the sentence, together with its article when the article shown stands right before it. gap appears exactly once in the sentence as whole words, with the same letters and capitals.
5. polish is a faithful, natural Polish translation of the whole sentence, in which the entry's Polish meaning, or a natural form of it, renders the gap.
6. The content is neutral and everyday: no vulgar or sexual content, no violence, no politics or religion, no real people or brands. Common first names such as Tom, Anna or Marco are fine.

Answer with one object per item, in the order of the items."""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "gap": {"type": "string"},
                    "polish": {"type": "string"},
                },
                "required": ["id", "text", "gap", "polish"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def files(review: bool) -> tuple[Path, Path]:
    name = "generated-review" if review else "generated"
    return WORK / f"{name}-requests.jsonl", WORK / f"{name}-batch.json"


def read_entries() -> dict[str, dict[str, Any]]:
    """Every built entry by id, with the sense the build kept (`_headword`, `_sense`)."""
    built = json.loads(ENTRIES.read_text("utf-8"))
    return {entry["id"]: entry for by_concept in built.values() for entry in by_concept.values()}


def read_generated() -> dict[str, dict[str, Any]]:
    if not GENERATED.is_file():
        return {}
    out = {}
    for line in lines(GENERATED):
        row = json.loads(line)
        out[row["entry"]] = row
    return out


def lines(path: Path) -> list[str]:
    """The lines of a JSON Lines file, split on newlines only: a sentence may hold a line
    separator (U+2028) that str.splitlines() would cut."""
    return [line for line in path.read_text("utf-8").split("\n") if line.strip()]


def written_for(row: dict[str, Any], entry: dict[str, Any]) -> bool:
    """The row was written for the entry's present word and meaning."""
    return bool(row.get("word") == entry["display"] and row.get("meaning") == entry["gloss"]["pl"])


def write_generated(rows: dict[str, dict[str, Any]]) -> None:
    lines = [json.dumps(rows[key], ensure_ascii=False) for key in sorted(rows)]
    GENERATED.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def without_example(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        e for e in entries.values() if not e.get("example") or e["example"]["source"] == "generated"
    ]


def needs_sentence(row: dict[str, Any] | None, entry: dict[str, Any], retry: bool) -> bool:
    if row is None or not written_for(row, entry):
        return True
    return retry and row.get("ok") is False and row.get("attempts", 1) < MAX_ATTEMPTS


def pending(sample: int | None, retry: bool) -> list[dict[str, Any]]:
    """Entries that need a sentence: none yet or one written for another word or meaning,
    or (with `retry`) a refused one."""
    done = read_generated()
    rows = []
    for entry in without_example(read_entries()):
        if needs_sentence(done.get(entry["id"]), entry, retry):
            rows.append(entry)
    rows.sort(key=lambda e: e["id"])
    if sample is not None:
        rows = sorted(
            random.Random(20261116).sample(rows, min(sample, len(rows))), key=lambda e: e["id"]
        )
    return rows


def item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "language": examples.LANGUAGES[entry["lang"]],
        "level": entry["level"].upper(),
        "word": entry["display"],
        "pos": examples.POS_NAMES.get(entry["pos"], entry["pos"]),
        "polish": entry["gloss"]["pl"],
        "english": entry.get("_headword", ""),
        "sense": entry.get("_sense", ""),
    }


def request_body(chunk: list[dict[str, Any]]) -> dict[str, Any]:
    lines = "\n".join(json.dumps(item(entry), ensure_ascii=False) for entry in chunk)
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM,
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": f"Items ({len(chunk)}):\n{lines}"}],
    }


def write_requests(
    rows: list[dict[str, Any]], body: Any, prefix: str, path: Path, per_item_output: int
) -> dict[str, Any]:
    chunks = [rows[i : i + ITEMS_PER_REQUEST] for i in range(0, len(rows), ITEMS_PER_REQUEST)]
    WORK.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    with path.open("wb") as fh:
        for number, chunk in enumerate(chunks, 1):
            params = body(chunk)
            total_chars += len(params["system"]) + len(params["messages"][0]["content"])
            row = {"custom_id": f"{prefix}-{number:04d}", "params": params}
            fh.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    input_tokens = total_chars / CHARS_PER_TOKEN
    output_tokens = len(rows) * per_item_output
    cost = input_tokens / 1e6 * PRICE_INPUT + output_tokens / 1e6 * PRICE_OUTPUT
    return {
        "entries": len(rows),
        "requests": len(chunks),
        "input_tokens": round(input_tokens),
        "output_tokens": output_tokens,
        "estimated_usd": round(cost, 2),
    }


def prepare(sample: int | None = None, retry: bool = False) -> dict[str, Any]:
    requests, _ = files(review=False)
    return write_requests(
        pending(sample, retry), request_body, "generate", requests, OUTPUT_TOKENS_PER_ITEM
    )


def review_rows() -> list[dict[str, Any]]:
    """The new sentences without a verdict, as rows of the example review."""
    entries = read_entries()
    rows = []
    for key, row in sorted(read_generated().items()):
        entry = entries.get(key)
        if entry is None or row.get("ok") is not None or not row.get("text"):
            continue
        rows.append(
            {
                "entry": key,
                "lang": entry["lang"],
                "word": entry["display"],
                "pos": entry["pos"],
                "meaning": entry["gloss"]["pl"],
                "headword": entry.get("_headword", ""),
                "sense": entry.get("_sense", ""),
                "candidates": [{"text": row["text"], "gap": row["gap"], "pl": row["pl"]}],
            }
        )
    return rows


def review_prepare() -> dict[str, Any]:
    requests, _ = files(review=True)
    return write_requests(
        review_rows(), examples.request_body, "review", requests, REVIEW_OUTPUT_TOKENS_PER_ITEM
    )


def submit(estimate: dict[str, Any], max_usd: float, review: bool) -> dict[str, Any]:
    if estimate["entries"] == 0:
        raise SystemExit("nothing to send")
    if estimate["estimated_usd"] > max_usd:
        raise SystemExit(
            f"estimated {estimate['estimated_usd']} USD is above the limit of {max_usd} USD"
        )
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    requests, batch_file = files(review)
    rows = [json.loads(line) for line in lines(requests)]
    api = client()
    sample = rows[0]["params"]
    counted = api.messages.count_tokens(
        model=sample["model"],
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
        "entries": estimate["entries"],
        "estimated_usd": round(cost, 2),
    }
    batch_file.write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return record


def asked(review: bool) -> set[str]:
    """The entries the batch asked about, read from its requests."""
    requests, _ = files(review)
    ids: set[str] = set()
    for line in lines(requests):
        content = json.loads(line)["params"]["messages"][0]["content"]
        for raw in content.split("\n")[1:]:
            if raw.strip():
                ids.add(json.loads(raw)["id"])
    return ids


def results(review: bool, wait: bool) -> tuple[str, Any, dict[str, dict[str, Any]], list[str]]:
    """The batch's answers by entry id, with the usage and the failed requests.

    A batch is collected once: its record then says so, and a second collect
    would only overwrite the verdicts that came after it.
    """
    _, batch_file = files(review)
    record = json.loads(batch_file.read_text("utf-8"))
    if record.get("collected"):
        raise SystemExit(f"the batch {record['id']} was collected on {record['collected']}")
    api = client()
    while True:
        batch = api.messages.batches.retrieve(record["id"])
        if batch.processing_status == "ended" or not wait:
            break
        time.sleep(60)
    if batch.processing_status != "ended":
        return batch.processing_status, batch.request_counts.model_dump(), {}, []
    answers: dict[str, dict[str, Any]] = {}
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
            items = json.loads(text)["items"]
        except (ValueError, KeyError):
            failed.append(result.custom_id)
            continue
        for answer in items:
            if isinstance(answer, dict) and isinstance(answer.get("id"), str):
                answers[answer["id"]] = answer
    wanted = asked(review)
    answers = {key: value for key, value in answers.items() if key in wanted}
    record["collected"] = date.today().isoformat()
    batch_file.write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    return "ended", usage, answers, failed


def problems(entry: dict[str, Any], text: str, gap: str, polish: str) -> list[str]:
    """What keeps a sentence out of the course before the review sees it: the course check
    of an example (the gap once as whole words, a translation), one line, and the length."""
    out = []
    found = _example_problems({"text": text, "gap": gap, "pl": polish})
    if any(p.startswith("example.text") for p in found) or "\n" in text or len(text) > 200:
        out.append("text")
    elif any(p.startswith("example.gap") for p in found):
        out.append("gap")
    if len(text.split()) > MAX_WORDS.get(entry["level"], 15) + 3:
        out.append("length")
    if any(p.startswith("example.pl") for p in found) or "\n" in polish:
        out.append("polish")
    return out


def collect(wait: bool) -> dict[str, Any]:
    status, usage, answers, failed = results(review=False, wait=wait)
    if status != "ended":
        return {"status": status, "counts": usage}
    entries = read_entries()
    rows = read_generated()
    written = refused = 0
    for key, answer in answers.items():
        entry = entries.get(key)
        if entry is None:
            continue
        text, gap, polish = (str(answer.get(k, "")).strip() for k in ("text", "gap", "polish"))
        found = problems(entry, text, gap, polish)
        attempts = rows.get(key, {}).get("attempts", 0) + 1
        rows[key] = {
            "entry": key,
            "word": entry["display"],
            "meaning": entry["gloss"]["pl"],
            "text": text,
            "gap": gap,
            "pl": polish,
            "model": MODEL,
            "attempts": attempts,
            "ok": False if found else None,
            "issue": ",".join(found) if found else None,
        }
        written += 1
        refused += bool(found)
    write_generated(rows)
    cost = usage["input"] / 1e6 * PRICE_INPUT + usage["output"] / 1e6 * PRICE_OUTPUT
    return {
        "status": "ended",
        "written": written,
        "refused_by_checks": refused,
        "failed_requests": failed,
        "usage": usage,
        "cost_usd": round(cost, 2),
    }


def review_collect(wait: bool) -> dict[str, Any]:
    status, usage, answers, failed = results(review=True, wait=wait)
    if status != "ended":
        return {"status": status, "counts": usage}
    rows = read_generated()
    accepted = rejected = 0
    for key, verdict in answers.items():
        row = rows.get(key)
        if row is None or row.get("ok") is not None:
            continue
        row["ok"] = verdict.get("pick") == 1
        row["issue"] = None if row["ok"] else str(verdict.get("issue") or "none")
        accepted += row["ok"]
        rejected += not row["ok"]
    write_generated(rows)
    cost = usage["input"] / 1e6 * PRICE_INPUT + usage["output"] / 1e6 * PRICE_OUTPUT
    return {
        "status": "ended",
        "accepted": accepted,
        "rejected": rejected,
        "failed_requests": failed,
        "usage": usage,
        "cost_usd": round(cost, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "step",
        choices=(
            "prepare",
            "submit",
            "collect",
            "review-prepare",
            "review-submit",
            "review-collect",
        ),
    )
    parser.add_argument("--max-usd", type=float, default=10.0)
    parser.add_argument("--sample", type=int, help="only this many entries, chosen at random")
    parser.add_argument(
        "--retry", action="store_true", help="also entries whose sentence was refused"
    )
    parser.add_argument("--wait", action="store_true", help="wait until the batch has ended")
    args = parser.parse_args(argv)
    if args.step == "prepare":
        result = prepare(args.sample, args.retry)
    elif args.step == "submit":
        result = submit(prepare(args.sample, args.retry), args.max_usd, review=False)
    elif args.step == "collect":
        result = collect(args.wait)
    elif args.step == "review-prepare":
        result = review_prepare()
    elif args.step == "review-submit":
        result = submit(review_prepare(), args.max_usd, review=True)
    else:
        result = review_collect(args.wait)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
