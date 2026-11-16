# Working on VocabBot with Claude Code

## Layout

- `src/vocabbot/` is one package with the engine and the `vocabbot` program.
  - The engine (`fsrs`, `answers`, `courses`, `store`, `book`, `queue`,
    `session`, `quiz`, `gate`, `plans`, `words`, `progress`, `doctor`,
    `cli`, `assets`, `errors`) uses the standard library only and runs on
    Python 3.10 and later, because `vocabbot.pyz` runs on whatever
    interpreter a host's sandbox has.
  - `drill.py` (the terminal session) and `term.py` (colour, symbols and
    widths) use the standard library too; `term.py` follows `NO_COLOR`,
    `FORCE_COLOR`, `TERM=dumb` and falls back to ASCII symbols, so
    `vocabbot.pyz` and the installed program look the same.
  - `server/` is the remote MCP server with accounts (`vocabbot-server`,
    the `server` extra, `docs/server.md`). It is the only part that needs
    packages beyond the standard library (the MCP SDK, uvicorn), it runs the
    program's command handlers through `server/service.py`, and
    `scripts/build.py` leaves it out of `vocabbot.pyz`. Its guides for the
    model (`server/guides/*.md`) follow the skills: a change of a skill's
    steps or of `rules/` changes them too. `server/static/card.html` is the
    card of MCP Apps; `pages.card()` fills in its labels from `pl.json`.
  - `data/courses/<lang>/<level>.jsonl` and `meta.json` are the courses. In
    Stage 1 they hold the starter course that `tools/courses/starter.py`
    generates; Stage 2 replaces them with the A1 to B2 courses.
  - `data/lang/<code>.json` holds the answer rules of a language and
    `data/i18n/pl.json` every text a learner reads.
- `tests/` uses pytest. The tests read the starter course from
  `tests/fixtures/courses` (through `VOCABBOT_COURSES`), so a new packaged
  course does not change them. `tests/fixtures/fsrs_vectors.json` holds
  reference results of py-fsrs 6.3.3 (`make_fsrs_vectors.py` makes them).
- `plugin/` is the plugin: `.claude-plugin/plugin.json` for Claude and the
  portable `plugin.json` for Codex, with the same name, version and
  description; `.claude-plugin/marketplace.json` and
  `.agents/plugins/marketplace.json` at the root list it. The version is the
  semantic form of the version in `pyproject.toml` (`1.0.0rc1` is
  `1.0.0-rc.1`); a bump changes both manifests, `pyproject.toml`,
  `src/vocabbot/__init__.py` and `CHANGELOG.md`.
- `plugin/skills/<skill>/SKILL.md` and `reference/` are written by hand.
  `shared/rules.md`, `shared/labels.md`, `bin/vocabbot.pyz` and
  `plugin/LICENSE`, `plugin/NOTICE` are **generated** by
  `scripts/build.py skills` from `rules/*.md`, `data/i18n/pl.json`, the engine
  and the root files; never edit them by hand.
- `scripts/build.py pyz` builds `build/vocabbot.pyz`; `skills` writes the
  generated files (`--check` reports stale ones); `package` builds `dist/`
  (wheel, sdist, pyz, `vocabbot.plugin`, one zip per skill, `SHA256SUMS`).
- `scripts/validate.py` checks what `claude plugin validate` does not: the
  manifests against each other and `pyproject.toml`, the engine calls the
  skills teach, direct writes, translations, secrets and home paths.
- `sessions/*.json` are session tests run by `scripts/session_test.py`
  through `claude -p` (paid; only with the owner's approval). `--check` seeds
  every learner and resolves every check without a model.
- `tools/courses/` builds the A1 to B2 courses (dependency group `data`):
  `pipeline.py fetch` downloads the sources into `.cache/sources` (about
  3.2 GB, outside git), `extract` makes one pass over the Wiktionary
  extract, `build` writes `src/vocabbot/data/courses`, and `sample` writes
  the review samples into `.cache/work`. `concepts.tsv` keeps the concept
  ids for good, and `review.jsonl` keeps the decisions of the model review
  (`review.py prepare|submit|collect`, Message Batches API, the key in
  `.env`). `editor.jsonl` holds the editors' decisions, which win over the
  review: new concepts (ids from c09001), the A1 starting list (`start`),
  meanings told apart, levels and parts of speech. `examples.jsonl` keeps the
  example review (`examples.py prepare|submit|collect`, which judges the
  candidate sentences a build writes into `.cache/work`), `generated.jsonl`
  keeps the sentences the model wrote for entries without one and their
  review (`generate.py`), and `overrides.json` corrects single entries after
  the merge step. `audio.py` lists the Lingua Libre recordings (Spanish,
  Italian) during `fetch` and picks one recording per entry; the courses keep
  Commons file names, never the files. All of them
  are committed, so a build repeats without the API. A concept enters the
  courses only with a decision of the review or the editors. Raise `VERSION`
  in `build.py` when the sources or the rules change.
- `docs/development-plan.pl.md` is the staged plan. Read the current stage
  before starting work, and update it when a stage closes.

## Checks

```
uv run ruff format
uv run ruff check
uv run mypy
uv run pytest
```

During work run the tests of the modules you change; run the whole suite
before a commit. The suite on Python 3.10 runs in its own environment:

```
UV_PROJECT_ENVIRONMENT=.venv-py310 uv run --python 3.10 pytest
```

After a change of the engine, the rules or the skills:

```
uv run python scripts/build.py skills
uv run python scripts/validate.py
uv run python scripts/session_test.py --check
claude plugin validate ./plugin --profile directory --strict
```

## Rules for changes

- Engine code stays on the standard library and on Python 3.10 syntax and
  modules (no `tomllib`, no `typing.Self`, no `datetime.UTC`).
- The review log `log/reviews.jsonl` only grows. A changed grade is a new
  regrade row; nothing rewrites earlier rows except `doctor` through a
  preview.
- `next` never returns the answer of a card under review or in drill, and
  `answer` grades a typed answer itself; the model never sets a grade.
- A change of the plan or of a course goes through `gate.preview` and
  `vocabbot commit --confirm TOKEN`; in a terminal the program asks instead.
- Text a learner writes (answers, own words, notes) reaches the program on
  standard input, never on the command line.
- Files are written as UTF-8 with LF line endings (`store.write_text`,
  `store.append_jsonl`).
- Texts for the learner live in `data/i18n/pl.json`; errors are
  `VocabError(code, **params)` with the message under `errors.<code>`.
- Test data is synthetic. No learner's folder enters the repository.
- Every course entry names its sources, and `vocabbot course check` passes.
- A skill names only files inside its own folder; `SKILL.md` stays under 500
  lines and detail goes to `reference/`. A rule every skill keeps goes to
  `rules/`, never into one skill only.
- A user-facing document (`README`, `QUICKSTART`, `docs/pilot`, the plugin's
  `README` and `PRIVACY`) changes in English and in its `.pl.md`
  translation together. The plan is written in Polish
  (`development-plan.pl.md`) and translated to `development-plan.md`.
