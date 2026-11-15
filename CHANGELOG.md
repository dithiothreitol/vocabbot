# Changelog

The versions of VocabBot. The plugin uses semantic versions (`1.0.0-rc.1`);
the Python package writes the same version as PEP 440 (`1.0.0rc1`).

## 1.0.0-rc.5 - 2026-11-15

### Added

- `vocabbot-server`, VocabBot as a remote MCP server with accounts
  (`pip install "vocabbot[server]"`). Chat applications that connect to
  remote MCP servers (Claude on the web, the desktop and the phone, ChatGPT,
  Claude Code, Codex) sign in with OAuth 2.1: dynamic client registration,
  PKCE, refresh tokens that change at every use, the resource indicator and
  the issuer in the sign-in response. A learner opens an account on the
  server's page with an invitation code; passwords are kept as scrypt
  hashes, codes and tokens as SHA-256 hashes.
- 22 tools run the program's commands on the account's own folder and return
  the same JSON as the plugin's skills read; `vocab_guide` gives the model
  the rules and steps of the skills with the tools in place of the commands.
- `deploy/` runs the server with Docker behind Caddy, which obtains the TLS
  certificate; `docs/server.md` describes the setup, the accounts and the
  connection of each chat application.

### Fixed

- A batch of the session no longer shows a sentence that holds the answer of
  another card of the same batch; the sentence and its translation stay out,
  as in the placement test. The session test through the server found it
  ("„___, danke.”" next to the question about "danke").
- `scripts/deploy_vps.sh` deploys the server to a machine whose Caddy already
  serves other sites.

### Changed

- The engine serves many learners in one process: a catalog can share the
  courses of another one already in memory, `init_preview` can keep its
  preview in the new folder without a pointer, the learning day can follow a
  given time zone, and the program's commands read the learner's text
  through their context.
- `vocabbot.pyz` leaves the server out, so the skills keep running on the
  standard library alone.

## 1.0.0-rc.4 - 2026-11-15

### Added

- `vocabbot replay` replays the log and predicts every review before its
  outcome. It scores FSRS-6 with its defaults and the variants fitted to the
  earlier 70% of the reviews (initial intervals, the whole log, each
  language) on the later part, with log loss, RMSE(bins) and AUC, and
  simulates the coming four weeks of each schedule with the learner's usual
  days without learning.
- The full fit of the 21 FSRS-6 parameters on the standard library
  (`optimize.py`): reverse-mode derivatives and Adam as in the optimizer of
  py-fsrs, from 512 reviews. `vocabbot plan fit` is a preview that gives a
  language parameters of its own only where they predict the later reviews
  better than FSRS-6; `plan set parameters=default` goes back.
- A plan by presence (`presence=on`, the default): from two weeks of the log,
  due dates avoid the weekdays the learner usually skips, new words stay
  within the usual minutes, and the day before a day off or a skipped day
  offers its reviews ahead. Everything follows from the log, without a
  network.
- `status` shows the parameters in force for each language and the presence
  profile; the coach reads them in the weekly review.

## 1.0.0-rc.3 - 2026-11-15

### Added

- A new terminal session (`vocabbot drill`) on the standard library: a
  compact card with a progress bar, a correct answer saved without an extra
  key, the typed answer and the expected one with the differing letters
  marked, a card folded into one line after the answer in an interactive
  terminal, the commands `/cofnij`, `/znam`, `/pomoc` and `/koniec`, and a
  summary with the words to work on, tomorrow's load and the activity of the
  last four weeks. Colour follows `NO_COLOR`, `FORCE_COLOR` and `TERM=dumb`;
  consoles without Unicode fonts get ASCII symbols (`VOCABBOT_ASCII=1` forces
  them). The program no longer depends on Rich.
- `vocabbot` without a command shows the plan of the day and starts the
  session with Enter.
- `today`, `status` and `forecast` show progress bars, a load chart and the
  intervals after a first answer.
- Due dates spread within the FSRS fuzz ranges from 3 days up. The spread
  follows from the card and the day of the answer, so both computers see the
  same dates.
- The initial intervals (the first four FSRS-6 parameters) fit the learner's
  second answers once the log holds 40 of them; `status` says which intervals
  apply.
- Courses 2026.11.4: 228 decisions of the editors (`tools/courses/editor.jsonl`)
  add basic words such as yes and no, thank you, goodbye, the months, the
  possessive determiners, there is (es gibt, hay, il y a), estar, kennen,
  conocer, connaître, du, tú, tu, Sie, usted, how much (wie viel, cuánto,
  combien), chez, gern and die Eltern, and tell common meanings apart (house
  and home, tell and say, tall and high). English keeps verbs and nouns of
  one spelling (work, stop, walk). Level A1 opens with a starting list of
  greetings, pronouns and basic verbs and nouns, and any ten entries hold at
  most three function words. Nouns used only in the plural (die Eltern, les
  gens) and months without an article (enero, janvier) enter the courses.
  Claude Sonnet 5.5 reviewed every example sentence (sense, part of speech,
  Polish translation, suitable content): 14 911 sentences stay, 1 495
  entries are asked without one, and a filter of vulgar words guards the
  rest. The courses hold 23 095 entries (21 919 before).

### Changed

- In German, Spanish and French an article of another gender, or no article
  where the article shows the gender or the plural, makes the answer
  "nie wiem" (error classes `gender` and the new `no_article`).
- Words added during the day (more words, a word marked as known) join the
  day's list after the planned words, so a card already shown never leaves
  the list.
- The placement test asks a question without its sentence when the sentence
  holds the answer of another question of the same test.
- The session tests count the sentences the engine gives in its questions as
  no leak; a model that fills in the answer still fails.

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
