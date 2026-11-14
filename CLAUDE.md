# Working on VocabBot with Claude Code

## Layout

- `src/vocabbot/` is one package with the engine and the `vocabbot` program.
  - The engine (`fsrs`, `answers`, `courses`, `store`, `book`, `queue`,
    `session`, `gate`, `plans`, `words`, `progress`, `doctor`, `cli`,
    `assets`, `errors`) uses the standard library only and runs on
    Python 3.10 and later, because `vocabbot.pyz` runs on whatever
    interpreter a host's sandbox has.
  - `drill.py` imports Rich inside `RichScreen` only; without Rich the
    session runs in plain text.
  - `data/courses/<lang>/<level>.jsonl` and `meta.json` are the courses. In
    Stage 1 they hold the starter course that `tools/courses/starter.py`
    generates; Stage 2 replaces them with the A1 to B2 courses.
  - `data/lang/<code>.json` holds the answer rules of a language and
    `data/i18n/pl.json` every text a learner reads.
- `tests/` uses pytest. The tests read the starter course from
  `tests/fixtures/courses` (through `VOCABBOT_COURSES`), so a new packaged
  course does not change them. `tests/fixtures/fsrs_vectors.json` holds
  reference results of py-fsrs 6.3.3 (`make_fsrs_vectors.py` makes them).
- `scripts/build.py pyz` builds `build/vocabbot.pyz`.
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
