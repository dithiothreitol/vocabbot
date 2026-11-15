# Architecture

VocabBot is one engine with two ways in. The engine is a Python package that
uses the standard library only; the `vocabbot` program runs it in a terminal,
and four Agent Skills run the same engine from a chat in Claude or Codex,
each from its own copy of `vocabbot.pyz`. The model in the chat shows cards,
reads answers and explains words; the engine decides every card, grade, due
date and count.

```
learner ── terminal ── vocabbot (drill, status, …) ─┐
                                                   ├── engine ── learner's folder
learner ── chat ── skill ── bin/vocabbot.pyz --json ┘     │       (plan, log, own words)
                                                          └── courses (inside the package)
```

## The engine

| Module | Role |
|---|---|
| `fsrs.py` | FSRS-6 with the published default parameters; the target recall sets the interval; the fuzz of py-fsrs with a day taken from a hash of the card and the day of the answer; the fit of the initial stabilities to the learner's second answers |
| `store.py` | the learner's folder, the plan and its checks, JSON-lines files written with LF |
| `book.py` | the state of every card replayed from the log, with the initial stabilities fitted once the log holds 40 second answers |
| `queue.py` | the day: reviews, new words split by weight, interleaving, the drill |
| `answers.py` | normalising and grading a typed answer by the rules of its language |
| `courses.py` | the catalog of courses and own words, questions and presentations, `course check` |
| `session.py` | the next cards, answers, own grades, regrades, `lookup`, `reveal` |
| `quiz.py` | the placement test, graded without the log |
| `gate.py` | previews with a token, `commit`, the decisions log |
| `plans.py`, `words.py`, `doctor.py` | changes of the plan, own words, repairs of the folder; all as previews |
| `progress.py` | `status` and `forecast` |
| `cli.py`, `drill.py`, `term.py` | the program, its terminal session and the terminal layer (colour by `NO_COLOR`, `FORCE_COLOR` and `TERM=dumb`, ASCII symbols for consoles without Unicode fonts, widths of wide and combining characters) |

Texts the learner reads live in `data/i18n/pl.json`; the answer rules of a
language in `data/lang/<code>.json`; the courses in
`data/courses/<code>/<level>.jsonl` with `meta.json` and `sentences.tsv`.

## The learner's folder

```
registers/plan.json        languages, levels, weights, new words a day, settings
registers/day.json         extra new words of the day
registers/.pending/        previews waiting for a yes (30 minutes)
log/reviews.jsonl          one row per graded answer; never rewritten
log/decisions.md           one line per approved change
log/flags.jsonl            reports of mistakes in entries
courses/<code>/own.jsonl   own words, and references to course words moved forward
```

The log is the source of truth. Every command replays it, so the same log and
the same day give the same queue in the terminal and in the chat, and a log
merged from two computers gives the same schedule. A changed grade is a new
row that names the row it replaces.

## Guarantees and where they are kept

| Guarantee | Kept by |
|---|---|
| A card under review shows no answer before the grade | `next` leaves the answer out; `reveal` refuses production cards; rule 2 of the skills; the session tests check every reply against the answers of waiting cards |
| The engine grades | `answer` grades the typed text; the model has no command that sets the grade of a production card; `regrade` marks its row; rule 3; the session tests compare each row with the engine's grade |
| Numbers come from the engine | every count, date and forecast is a field of a result; rule 4 |
| No change without a yes | `init`, `plan set`, `words add` and `doctor` repairs return a preview; only `commit --confirm <token>` writes, within 30 minutes and only if the files did not change; in Claude Code and Cowork the plugin's hook (`plugin/hooks/`) sends every `commit` and every direct write into a learner's folder to the host's permission prompt; rule 7; `validate.py` refuses a skill that writes the learner's files directly or commits without a yes |
| The learner's text cannot steer the shell | answers, words and notes come on standard input; rule 6 |
| A new word in two languages does not interfere | `sibling_gap_days` between the introductions of one concept, `sibling_distance` between its cards in a session |

The rules live in `rules/*.md`; `scripts/build.py skills` copies them into
`shared/rules.md` of every skill together with `shared/labels.md` and the
engine file, and `scripts/validate.py` refuses stale copies.

## Why one engine file per skill

A skill can be installed alone (claude.ai takes single skills) and a host's
sandbox may not install packages, so every skill carries the engine and the
courses in `bin/vocabbot.pyz`, which runs with the interpreter alone
(`python -I -S`). The four copies are the same bytes, so git stores the file
once. The plugin is about 9 MB.

Python on the hosts, checked on 2026-11-14:

| Host | Python | Source |
|---|---|---|
| Claude Code, Codex CLI | the computer's own | the shell of the computer; this repository's development machine has 3.14 |
| Cowork (Claude desktop) | 3.10.12 on Ubuntu 22.04 | community reports of the Cowork VM; no official list |
| claude.ai and the API code execution tool | 3.11.12 | Anthropic's documentation of the code execution tool |
| GitHub Actions `ubuntu-latest` | 3.10 to 3.15 through `setup-uv` | CI of this repository |

The lower bound stays at Python 3.10: the engine uses no module or syntax
newer than 3.10, and CI runs the tests on 3.10 and 3.15.

## Courses

`tools/courses/pipeline.py` builds the courses in four steps: `fetch`
downloads the sources into `.cache/` (3.2 GB, outside git), `extract` reads
the Wiktionary extract once, `build` writes the courses, and `sample` draws
the review samples. A concept enters the courses only with a decision: the
model review of the senses and equivalents (`review.jsonl`, Claude Sonnet 5.5
through the Message Batches API) or the editors (`editor.jsonl`, which wins
and also holds the A1 starting list and the concepts CEFR-J lacks, with ids
from c09001). Every example sentence comes from up to three Tatoeba
candidates judged by the example review (`examples.jsonl`); a filter of
vulgar words guards the entries without a decision. Within a level, any ten
entries in a row hold at most three function words. These files and
`overrides.json` are committed, so a build repeats without the API and gives
the same files.

## Checks

| Level | What | How |
|---|---|---|
| structure | package, manifests, skills, courses | `ruff`, `mypy --strict`, `scripts/validate.py`, `vocabbot course check`, `claude plugin validate --profile directory --strict` |
| arithmetic | scheduler, queue, grading, gate, replay | `pytest` on Python 3.10 and 3.15; py-fsrs as the reference |
| behaviour | the skills in conversations | `scripts/session_test.py` with `claude -p` (paid, on approval); `--check` without a model |
| use | daily learning | the pilot, `docs/pilot.md` |
