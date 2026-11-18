# Changelog

The versions of VocabBot. The plugin uses semantic versions (`1.0.0-rc.1`);
the Python package writes the same version as PEP 440 (`1.0.0rc1`).

## 1.0.0-rc.11 - 2026-11-18

Stages 12 and 13 of the plan: the account as the shared record on every
device, and the session in a phone's browser.

### Added

- `vocabbot login` links a learner's folder to an account on a VocabBot
  server, or downloads the account into a new folder. The program signs in
  through the browser (OAuth with PKCE, the result on 127.0.0.1) or, with
  `--code`, with a short code confirmed on another device. Linking a folder
  is a preview with the numbers of answers on both sides and after joining;
  when the folder and the account have different plans, the learner chooses
  with `--plan folder` or `--plan account`. The tokens live in
  `~/.vocabbot/credentials.json`, readable by the owner only.
- A linked folder synchronises by itself: it fetches before `today`, `next`,
  `drill` and `status`, and sends after every command that writes; the
  terminal session sends in the background. Without a network the rows wait
  in the folder; `today`, `status` and `doctor` show the account, the last
  synchronisation and the rows waiting. `vocabbot sync` synchronises at once
  and `vocabbot logout` ends the connection and unlinks the folder.
- The server's `/sync` joins the logs line by line: sending a line again adds
  nothing, a row of an unknown card or from the future is refused, and the
  account's lock keeps the tools and the synchronisation of one account one
  after another.
- Every approved change of the plan adds a row to `log/plan.jsonl`, and the
  plan is the latest value of every setting, so changes made on two devices
  both hold.
- The plan's `timezone` (an IANA name) sets the learning day on every device
  and on the server. A new account takes the zone of the browser, and linking
  a folder whose plan has none gives it the account's zone.
- `vocabbot export` writes the record as a zip in the form of a learner's
  folder, and `vocabbot import` brings one in as a preview: a new folder, or
  the rows a folder lacks.
- The server's session page (`/app/`) runs the day's cards, progress and the
  plan in a browser, also on a phone and from its home screen, without a chat
  application and without a model. Every step runs a command of the engine,
  so a question comes without its answer and the engine grades. The page
  follows Vercel's Geist: a ring of the day's progress, a switch of the
  stages, grade tiles with their keys, a bar of the result with its return
  date, an activity map of twelve weeks, a chart of the coming days and a
  ring of recall against its target.
- The account page (`/account`) lists the connected applications and
  computers with their last use and disconnects any of them, gives the data
  as a zip, keeps an optional e-mail address for password recovery as a hash
  only, and removes the account after the password.
- Password recovery by e-mail (`/recover`) with SMTP settings
  (`VOCABBOT_SERVER_SMTP_*`): the page answers the same for every login and
  address, and the link works once within 30 minutes.
- `status` holds `activity`, the answers of each of the last 84 days.
- A folder names its account in every synchronisation, and the server and the
  program refuse an exchange with another account (`other_account`), so
  signing in to another account never joins two learners' records.
- Rows the account refuses for a passing reason (a clock ahead of the server,
  a course or a version it does not have yet) go again with every
  synchronisation and count as waiting.
- A change of one language of the plan is kept per language, so changes of two
  languages made on two devices both hold; settings of a newer version stay in
  the history and are left out when the plan is worked out.
- Changing or removing the recovery address on the account page needs the
  password.
- `doctor --merge` also joins conflict copies of the plan's history.
- VocabBot has an avatar in the common form of assistants' avatars, a flat
  tile with a face of two upright eyes. The face is the front card of the
  course with the orange dot of the day's card, and a light blue card stands
  behind it. `scripts/make_icon.py` draws it with the standard library as the
  plugin's icon and as `docs/assets/avatar.png` and `avatar.svg` for
  profiles; the logo and the social preview show it.
- The server shows the avatar on its pages, serves it as their favicon
  (`/static/vocabbot.png`, `/favicon.ico`) and names it in its MCP
  information (`icons`, MCP 2025-11-25), so a chat application can show it
  beside the server's name.

### Changed

- The engine reads a log in its own order (day, time, card) whatever the
  order of its rows in the file, and reads the rows of conflict copies of the
  log, the reports and the notes together with the main files; `doctor
  --merge` still tidies the files.
- Own words and the course words moved forward come in an order that does not
  depend on the order of `own.jsonl`; a moved word keeps a rank of its own.
- The server's pages send their referrer only to the server itself, so a form
  names its origin.
- A row whose day or time does not exist is left out of the replay instead of
  stopping it.
- A plan's `timezone` must be spelled exactly as in the IANA list, and the
  server checks its own zone when it starts.
- A new plan in a folder that already holds logs keeps them.
- The social preview names the five languages and the 28 671 entries of the
  courses.

## 1.0.0-rc.10 - 2026-11-16

### Changed

- Self-assessment and the translation on request are the defaults, as in
  SuperMemo: `answer_mode=self` (typing stays, and the engine grades a typed
  word) and `sentence_translation=hidden`. `answer_mode=type` and
  `sentence_translation=shown` bring back the previous behaviour. A plan
  saved before 1.0.0-rc.9 gets the new defaults; a plan saved by
  1.0.0-rc.9 keeps the values it holds.
- At the start of a session the chat names „pokaż” and „tłumaczenie” beside
  the words that change the stage, when the plan allows them.

## 1.0.0-rc.9 - 2026-11-16

### Added

- Self-assessment beside typing, as SuperMemo's "Check": with the plan's
  `answer_mode=self` (the default stays `type`) `reveal` shows the word of a
  production card waiting today, and `grade` takes the learner's `know`,
  `almost` or `dont_know` for it (in the drill `know` or `dont_know`). The
  row of such a grade has no `auto`. `reveal` names the card's `phase`, the
  `grades` to choose from and the day's counter. In the terminal an empty
  Enter shows the answer for the keys 1, 2, 3.
- `sentence_translation=hidden` keeps the translation of a sentence back
  until the learner asks for it: a button under the sentence in the card,
  "tłumaczenie" in the chat, `/t` (and `t` at an introduction) in the
  terminal. The engine returns `sentence_pl` as before.
- `back` in the result of an answer says when the card comes back ("wróci
  jutro", "wróci za 4 dni", "wróci dziś w utrwalaniu"), the same text in the
  chat, the card and the terminal; `next_review=hidden` leaves it out.
- `view` in every result of a session: the plan's `new_words`,
  `answer_mode`, `sentence_translation` and `next_review`.
- `flag --skip` puts a word aside without reporting a mistake, and
  `flag --clear` brings it back with the date it had; `status` lists
  `skipped` apart from `reported`. The terminal has `/pomin`.
- `note --card ID --stdin` keeps the learner's own note for a word in
  `log/notes.jsonl` (up to 500 characters; `--clear` removes it). The note
  comes as `word.note` in the result of an answer, in `reveal` and in
  `lookup`, never in `next`. The terminal has `/notatka`, and the coach
  offers to keep a mnemonic as a note after the learner's yes.
- The server: `vocab_note` (23 tools), `vocab_flag` with `skip`, and
  `vocab_reveal` shows the card with the grades to choose from.

### Changed

- `doctor --merge` also joins conflict copies of the notes, and puts the
  rows of the flags and the notes in the order of time.
- The result of `flag` holds the day's counter after the change, so a chat
  shows the right counter after a word is put aside or brought back.
- `session-self-assessment` joins the session tests (8 sessions).

## 1.0.0-rc.8 - 2026-11-16

### Added

- A new word is asked at once, as in SuperMemo (`new_words: ask`, the plan's
  default): `next` returns a new card without its word, the result of the
  first answer shows the word in full, and a right first answer is logged as
  `known`, a word known before the course, which adds one more new word and
  counts for the level hint. `new_words=show` keeps the introduction before
  the question. `today` names the setting in `new_words`.
- `review_order` in the plan: `due` (most overdue first, the default),
  `course`, `interval` (shortest intervals first) or `random` (the same
  order for the whole day).
- The stages of a day, as in SuperMemo (repetitions, new material, final
  drill), are the learner's choice: `next --stage reviews|new|drill` brings
  the cards of the chosen stage first, and an answer with `--next` returns
  the next card of the stage the answered card belongs to. A result names
  the stage (`stage`), a chosen stage without cards (`stage_empty`) and the
  cards left in each stage (`left`). Reviews left undone stay due.
- More reviews for a day: `today --reviews N` adds the next round, the due
  cards outside the day's list first (over `review_limit`, or on a day off)
  and then the cards with the nearest later dates as reviews before their
  day. `registers/day.json` keeps the number beside the added new words.
- `more` in the results of `today` and `next`: the new words, due reviews
  and later reviews that can still join the day. `today --extra` and
  `today --reviews` report `added` and, with `--next`, the next cards;
  `grade` takes `--next` as well.
- The terminal session: `/nowe`, `/powtorki`, `/utrwalanie` and `/wiecej`
  at the answer prompt, `p` at a new word, and after the day's list the
  choice of more new words, the next round of reviews or the end.
- The server: `vocab_next` takes `stage`, `vocab_grade` takes `then_next`,
  and `vocab_add_today` takes `count` and `reviews` and shows the card. The
  card shows the three stages with the cards left and marks the one in
  progress. The session guide and the `vocab-session` skill describe the
  stages, the words that change them and the offer after the day's list.

### Changed

- The drill has two grades, as in SuperMemo: an answer other than "know"
  keeps the card in the drill and is logged as `dont_know` (the engine's
  verdict stays in `auto` with its error classes); a drill answer is
  regraded to `know` or `dont_know`.
- A plan saved by an earlier version asks new words at once; `plan set
  new_words=show` brings back the introduction before the question.
- The forecast takes the share of right first answers from the log, and
  20% for a plan that asks new words at once before the log has 20 of them.
- `left.reviews` counts the reviews before their day too, and the server's
  tools no longer take `ahead`: such reviews join the day through
  `vocab_add_today`.

### Fixed

- Asking for more new words several times with two or three languages no
  longer brings more words than asked for: added words join one at a time
  in a fixed order of languages, so a larger number only appends.
- Reviews the learner adds leave the paced number of new words unchanged.

## 1.0.0-rc.7 - 2026-11-16

### Added

- A counter of the day in every result of the session: `done` beside `left`,
  and `counter`, the line "Postęp: 6/25 · nowe 3/15 · powtórki 3/10" that the
  session in a chat shows at the top of every message. `today` lists the
  words first shown that day (`learned_today`) for the summary at the end.
- Recordings: 23,368 entries (81.5%) name a recording on Wikimedia Commons,
  found through Wiktionary and, for Spanish and Italian, through Lingua Libre
  (`tools/courses/audio.py`); English 98–99%, German 92–95%, French 86–94%,
  Spanish 63–91%, Italian 27–79% by level. A reflexive verb or a word
  pronounced two ways gets no recording of another form. The engine gives its MP3 address in
  `word.audio`, and the session shows it as a link beside the IPA, with a new
  word and in the results "prawie" and "nie wiem". The package holds only the
  file names.
- Example sentences for 10,602 entries that had none: Claude Sonnet 5.5 wrote
  one sentence for every entry without a Tatoeba sentence and the example
  review judged it (`tools/courses/generate.py`, `generated.jsonl`; 8.32 USD).
  99.5% of the entries now have an example, at least 99% on every level.
- A hint to raise the level: when 8 of the last 10 new words of a language
  at its present levels were known before the course, the result of `grade`
  or `answer` holds `level_hint` with the plan setting to change, at most once
  a day for the same levels; the session offers it, and the terminal shows it.
- The card of MCP Apps: Claude and ChatGPT show the results of `vocab_today`,
  `vocab_next`, `vocab_answer` and `vocab_grade` as a card with the counter,
  the word, its IPA and a button that plays the recording; the browser's
  speech synthesis reads words and sentences without one.

### Changed

- ChatGPT connects through Settings, Integrations, Plugins and a custom MCP
  server, without developer mode (`docs/server.md`, the server's start page).
- The IPA and the recording come from another part of speech of the same
  word when every record of the word has one pronunciation (German "nein"):
  196 more entries have an IPA. Courses 2026.11.6.

### Fixed

- A change of the levels during the day no longer adds new words on top of
  the daily limit: the words learned that day outside the new plan take the
  places of words not chosen yet, in their own language.
- A card the learner reports leaves the drill as well, so the session ends.
- The server named the course languages without Italian in the description of
  `lang`.

## 1.0.0-rc.6 - 2026-11-15

### Added

- Italian: a course from A1 to B2 (5576 entries, courses 2026.11.5) built
  the same way as the other four, from CEFR-J, Wiktionary, wordfreq and
  Tatoeba. Claude Sonnet 5.5 chose the Italian equivalent of each of 6705
  concepts, keeping the sense and the Polish meaning of the course, and
  judged the example sentences (`tools/courses/review_lang.py`,
  `review-it.jsonl`). The engine grades Italian answers: `lo` beside `il`,
  the elided `l'` and `un'`, the plural `i`, `gli`, `le`, and reflexive verbs
  in `-si` (lavarsi, lavare).
- New or other example sentences for 7 entries of the German, Spanish and
  French courses, through Italian translations in Tatoeba.

### Changed

- The server's pages (the sign-in, the start page, the privacy note) follow
  shadcn/ui with the Geist typeface (SIL Open Font License), in light and
  dark mode and without scripts; the sign-in has tabs for signing in and for
  a new account, hints under the fields and a note on what the invitation
  code is.
- Invitation codes are shown in capitals (`ABCD-EFGH-JKMN`); any case,
  spaces and hyphens are still accepted.
- The session in the chat asks one card at a time, as SuperMemo does: a
  message holds the result of the last answer and the next card, and a new
  word comes alone before its question. The plan's new key `batch` (1 to 20,
  default 1) sets the cards of one message; with more than one the session
  keeps the numbered list.
- `next` without `--count` returns the plan's `batch` of cards, `today`
  reports `batch`, and `answer --next` also returns the next cards, so a card
  needs one call of the engine; the server's `vocab_answer` has `then_next`.

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
