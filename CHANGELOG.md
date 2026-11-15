# Changelog

The versions of VocabBot. The plugin uses semantic versions (`1.0.0-rc.1`);
the Python package writes the same version as PEP 440 (`1.0.0rc1`).

## 1.0.0-rc.2 - 2026-11-15

### Added

- A confirmation hook for Claude Code and Cowork: every `commit` of the
  engine and every direct write into a learner's folder goes to the host's
  own permission prompt, which shows what the preview changes. The engine
  still writes nothing without a previewed token; `VOCABBOT_HOOK=off` turns
  the prompt off for test runs.
- A logo at the top of the READMEs (also on PyPI) and a social preview image
  for the repository (`docs/assets/`).

### Changed

- Courses 2026.11.3: a pronoun, numeral or other word spelt like an article
  (French and Spanish "la", "le", "les", "los", "un", "unos") is asked without
  an example sentence, because the sentences used it as the article; German
  "das" keeps an example only where no capitalised noun follows it. Seven
  entries changed and a few neighbouring entries got other examples.

## 1.0.0-rc.1 - 2026-11-14

The first release candidate: the plugin, its checks and the documents.

### Added

- The plugin with four skills: `vocab-start` (setup, placement test, plan,
  forecast, folder check, the terminal program), `vocab-session` (the daily
  session in the chat), `vocab-coach` (explanations, mnemonics, mix-ups
  between languages, practice in sentences, the weekly review) and
  `vocab-words` (own words, course words moved forward, reports of mistakes).
  Each skill carries the engine with the courses in `bin/vocabbot.pyz` and the
  shared rules in `shared/`.
- Manifests for Claude (`plugin/.claude-plugin/plugin.json`) and for Codex
  (`plugin/plugin.json`), and a marketplace catalog for each.
- New engine commands: `quiz` (a placement test that writes nothing),
  `lookup` (course entries for a word or a Polish meaning), `reveal` (the
  meaning of a recognition card before the learner's own grade) and `use`
  (point the program at an existing folder).
- `words add` moves a course word forward instead of copying it, leaves out
  words already learned, and warns when an own word shares its Polish
  meaning with another word.
- `init --set KEY=VALUE` takes any plan setting in the first preview.
- `status` lists words introduced in the last seven days and answers given in
  another language, and marks cards still waiting in today's session.
- The current folder counts as the learner's folder when it holds a plan.
- `scripts/validate.py`, `scripts/session_test.py` with seven sessions,
  `scripts/build.py skills` and `package`, the release workflow, the
  documents in English and Polish, and the pilot protocol.
- Results of `answer`, `grade` and `quiz --check` carry the Polish names of
  the grade and the error classes (`grade_pl`, `errors_pl`); `status`
  carries `errors_30_pl`.
- Where a sandbox allows writes only in the working folder (Codex), the
  preview of a new folder waits in the folder itself, the pointer in
  `~/.vocabbot` is skipped, and `commit` finds the preview in the current
  folder or the folder of `--learner`. A refused write is an `io_error` in
  JSON instead of a traceback.

### Changed

- The shared rules end a turn at the question about saving, keep commands,
  field names and ids out of the conversation, and forbid running the engine
  through a wrapper or a changed environment; found in the walk through the
  path with Claude Code and Codex.
- `course check` reports a clash between an own word and a course word with
  the same meaning as a warning; the courses stay valid.
- `vocabbot.pyz` is built with sorted entries and a fixed time, so the same
  sources give the same archive.

## 1.0.0.dev2 - 2026-11-14

- The A1 to B2 courses for English, German, Spanish and French: 21 919
  entries from CEFR-J, Wiktionary (kaikki.org), wordfreq and Tatoeba, with the
  meanings reviewed by Claude Sonnet 5.5.
- Answers to reflexive verbs without the pronoun are graded "prawie".

## 1.0.0.dev1 - 2026-11-14

- The engine: FSRS-6 matching py-fsrs 6.3.3, the day's queue for one to three
  languages, the answer grader for four languages, the preview and token
  gate, the `vocabbot` program with `--json`, the terminal session and
  `vocabbot.pyz`.
