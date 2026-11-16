# VocabBot implementation plan

**English** · [Polski](development-plan.pl.md)

This is the English translation of `development-plan.pl.md`, which is the
version kept up to date first.

Status: 2026-11-16, after Stage 7 (version 1.0.0-rc.6, 1.0.0rc6 in the Python
package). You accepted the plan on 14.11.2026 and added Stages 4, 5, 6 and 7 on
15.11.2026. Stage 7 gave the Italian course and the session one card at a
time. I carried out Stages 8 and 9 (pilot feedback: pronunciation,
examples, a counter, ChatGPT and a card in the chat window) on 16.11.2026;
with your approval I released them as `v1.0.0-rc.7` on GitHub and PyPI and
deployed them on the server. You added Stage 10 (the session's stages as in
SuperMemo: the choice of stage, more words, more rounds of reviews, a new
word as a question, two grades in the drill and the order of reviews) on
16.11.2026; with your approval I released it as `v1.0.0-rc.8` on GitHub and
PyPI and deployed it on the server. Stage 11 (handling a card as in the
SuperMemo application: self-assessment, the sentence's translation on
request, the review date with the result, switching a word off and a note
for a word) you accepted, and I carried it out on 16.11.2026; with your
approval I released it as `v1.0.0-rc.9` on GitHub and PyPI and deployed it
on the server. At your suggestion self-assessment and the translation on
request are the defaults since the same day in the local repository; their
release awaits your approval. The engine, the `vocabbot` program with its new terminal session,
the A1–B2 courses for four languages (23 095 entries) and the plugin with four
skills for Claude and Codex work; section 10 describes the results of the
stages. The release `v1.0.0-rc.3` is published on GitHub and on PyPI
(15.11.2026), and the session tests with a model pass 7 of 7. Stage 5 (a
schedule fitted to the learner) ended with the release `v1.0.0-rc.4` on GitHub
and on PyPI (15.11.2026). Stage 6 (the server for chat applications) ended
with the release `v1.0.0-rc.5` on GitHub and on PyPI (15.11.2026), and the
server runs at `https://vocab.archxs.com`. Version 1.0 still needs the pilot
described in `docs/pilot.md`.

---

## 1. Goal and definition of done

VocabBot is an open tool for learning vocabulary in one, two or three foreign
languages at once, at levels A1–A2 and B1–B2, for a Polish speaker. Learning
works as in the SuperMemo vocabulary courses: the learner meets new words in
order of frequency, grades every answer with one of three grades and comes
back to the word on the day the review algorithm sets. The tool offers one
engine in two ways: its own `vocabbot` program in a terminal, and a
conversation with Claude or Codex led by a plugin with skills in the Agent
Skills standard.

Version 1.0 is done when all conditions hold:

1. A learner goes through the whole path without the author's help:
   installation, the choice of languages and levels, a daily session in the
   terminal and in the chat, a look at progress and a change of the plan.
2. The English, German, Spanish and French courses cover levels A1–A2 and
   B1–B2, pass `vocabbot course check` without errors and meet the quality
   thresholds of Stage 2.
3. Every due date comes from the engine, whose results match the FSRS
   reference library.
4. Every grade in the log comes from the learner's answer graded by the
   engine, or from the learner's own grade. The model raises no grade and
   shows no answer before the learner's answer is saved, as tests confirm.
5. A change of the plan or of a course happens only after a preview and a
   confirmation with a token.
6. The package passes `ruff`, `mypy`, `pytest`, the repository validator and
   `claude plugin validate --profile directory --strict`.
7. The pilot, your own learning for at least two weeks in two or three
   languages, ends without blocking defects.

---

## 2. Starting points

### 2.1 Your decisions of 14.11.2026

| Question | Decision |
|---|---|
| Where the daily session happens | the chat and an own CLI |
| Languages of the first courses | English, German, Spanish, French; Polish as the base language |
| Working name | `vocabbot`, a local repository in `Documents\GitHub\vocabbot` |
| Order of work | this plan first, then the code; as few stages as possible; the newest stable versions of tools and libraries |

### 2.2 Functional model: the SuperMemo vocabulary courses

The findings come from supermemo.com pages checked on 14.11.2026 (sources at
the end of the document).

| Feature of the SuperMemo courses | Finding |
|---|---|
| Vocabulary courses | the Extreme series: Basic A1–A2 (2226 pages), Intermediate B1–B2 (9844 pages), one page per word or phrase |
| Order of the material | words ordered by frequency, the most frequent first |
| Content of a page | the word, a definition in the language being learned, an example sentence, an image, a recording, a translation into the learner's language |
| Learning sections | learning new pages, reviews, a drill |
| Grades | "I know", "almost", "I don't know" |
| Effect of the grades | "I know" lengthens the interval; "almost" also lengthens it and sends the page to the drill of that day; "I don't know" shortens the interval and sends the page to the drill |
| Drill | pages graded "almost" or "I don't know" come back after the reviews planned for the day |
| Goal of the algorithm | a review at the moment the probability of recall is about 90% |
| Algorithm | historically SM-2, now SM-20 (owned by SuperMemo, not available for reuse) |
| Plan | cards a day, the expected length of the course, a calendar with days off |
| Several courses at once | reviews mixed with the material of all the learner's courses |
| Prices | an Extreme course for a year 69.90–89.90 PLN; Premium 35.99 PLN a month |

The content of the SuperMemo courses is protected, so VocabBot reproduces the
way of learning and builds the vocabulary from open sources (section 3,
decision D12).

### 2.3 Architectural model: HouseholdBot

| Element of HouseholdBot | In VocabBot | Reason |
|---|---|---|
| A record in the user's folder, plain files | taken over | a learner's folder with the plan, the log of reviews and own words |
| Scripts prove, the model judges | taken over | the engine computes the schedule, the queue and the grade of an answer; the model explains, finds examples and leads the conversation |
| A guarantee in a script instead of an instruction | taken over | `next` returns no answer, `answer` computes the grade, plan changes go through a preview and a token |
| Two-phase write with a token | adapted | covers the plan and the courses; grades go to the log without the gate, because the learner's answer is the act of learning itself |
| Law as data with a named source | adapted | a course as data: every entry with a source, every file with a licence, the `course check` |
| Language separate from country | taken over | the base language separate from the languages being learned; messages in `data/i18n` |
| Every skill self-sufficient | adapted | every skill carries one `vocabbot.pyz` with the whole engine and the courses |
| Scripts on the standard library only | taken over for the engine | since Stage 4 the terminal session uses the standard library only as well (`term.py`) |
| Outside text off the command line | taken over | answers and own words reach the engine on standard input |
| Four levels of verification | taken over | structure, arithmetic, behaviour, use |
| Two manifests and two marketplace catalogs | taken over | Claude and Codex from one plugin folder |
| Router, skill chains, read-only agent, managed agent cookbook | left out | four skills need no router; learning needs no unattended work |
| Confirmation hook | taken over in version 1.0.0-rc.2 | the walk through the path showed that a model can save a change without a confirmation; the hook moves the confirmation into the host's permission prompt in Claude Code and Cowork |
| A path without Python | left out | a manual calculation gives no reliable due dates; without the engine the skill says so and offers practice without saving |

### 2.4 Learning several languages at once

| Research finding | Rule in the engine |
|---|---|
| Interleaving two languages in one session gave better results than learning in blocks (Waisman Center, UW–Madison; German and Polish in English speakers) | one queue a day with interleaved languages as the default; the setting `mix: blocks` for learners who prefer blocks |
| Learning an equivalent in a new language lowers the recall of the word of a language learned earlier right afterwards (MPI Nijmegen, 2024) | a gap `sibling_gap_days` (3 days by default) between the introduction of one concept in two languages, and such cards kept apart in the queue |
| Interference grows for words similar to words of known languages and fades with time (Bartolotti and Marian, Northwestern) | detection of an answer given in another language being learned, and the `confusable` field of an entry |
| Results of research on interleaving differ by material | the setting stays a choice; `status` shows the measured recall separately for every language |

---

## 3. Design decisions

**D1. One Python package, an engine without dependencies.** All code lives
in `src/vocabbot/`. The engine modules import only the standard library, so
the same code runs in the program installed on a computer and in a host's
sandbox that allows no installation.

**D2. Two ways into one engine.** The `vocabbot` program installed with
`uv tool install vocabbot` has had no dependency since Stage 4, and its
terminal session looks the same as in `vocabbot.pyz`. The file `vocabbot.pyz` (a
`zipapp` archive with the engine and the courses) runs with
`python vocabbot.pyz` without any installation and goes into every skill.
Both ways have the same commands and the same `--json` option, which returns
the result for the skills.

**D3. The learning record in the learner's folder.** The learner chooses the
folder at `vocabbot init`. The program saves a pointer to the folder in
`~/.vocabbot/config.json`; the variable `VOCABBOT_HOME` and the option
`--learner` take precedence. One folder belongs to one person.

**D4. The log is the source of truth.** The file `log/reviews.jsonl` takes
one row for every graded answer and is never rewritten. Every command
replays the state of the cards from the log, so the same log and the same
date always give the same queue. Merging the logs of two computers therefore
means joining their rows.

**D5. The FSRS-6 scheduler.** The engine holds its own implementation of
FSRS-6 with the published default parameters (21 numbers). Tests compare it
with the `fsrs` 6.3.3 library on saved vectors and on random sequences of
grades. The FSRS algorithm is published and has a reference library under the
MIT licence. The schedule aims at a given recall, 0.9 by default, the value
used in the SuperMemo courses.

**D6. Three grades and "known".** The grades `know`, `almost`, `dont_know`
correspond to the buttons "wiem", "prawie", "nie wiem" and to the FSRS grades
Good, Hard, Again. The grade `known` ("I knew this word before the course")
is available only at the first showing, corresponds to Easy and does not use
the daily limit of new words.

**D7. The drill does not change the schedule.** The second and later
answers to the same card on the same day go into the log as drill and leave
the due date unchanged. A card leaves the drill after the answer "know".

**D8. One queue for several languages.** The plan covers one to three
languages with weights. The engine splits the daily limit of new words by
weight, holds back a concept learned recently in another language,
interleaves the languages and keeps the cards of one concept apart. A fourth
language needs the setting `max_languages` raised explicitly.

**D9. The engine grades the answer.** A production card (the Polish meaning
and a sentence with a gap, the answer in the language being learned) needs a
typed answer. The engine compares it with the entry by the rules of the
language and proposes a grade: a match gives "know", a small difference (a
diacritic, one typo in a longer word, a missing or wrong article, the case of
a letter) gives "almost", other answers give "don't know". In the terminal
the learner accepts the proposal with Enter or changes it with one key. In
the chat the command `regrade` changes a grade only at the learner's explicit
request and marks such a row in the log.

**D10. A course as data.** A course is a set of files
`data/courses/<language>/<level>.jsonl` with one entry per line and a file
`meta.json` with the sources, dates and licence. A shared concept id links
the entries of different languages. The learner's own words go into their
folder in the same format.

**D11. A gate for changes of the plan and the courses.** The commands
`plan set` and `words add` create a preview with a token valid for 30
minutes. Only the command `commit --confirm <token>` carries out the shown
change. Every approved change gets a line in `log/decisions.md`.

**D12. Course content from open sources.** The pipeline builds the courses
from the CEFR-J list (levels), the English Wiktionary in the kaikki.org
extract (translations, gender, forms, pronunciation), the wordfreq data
(frequency) and Tatoeba sentences (examples). The code is licensed under
Apache-2.0, the courses under CC BY-SA 4.0, with the list of sources in
`NOTICE`.

**D13. Four skills.** The plugin holds `vocab-start` (setting up the
learning and changing the plan), `vocab-session` (the daily session in the
chat), `vocab-coach` (explanations, mnemonics, lists of words confused
between languages, practice of learned words in sentences, the weekly
review) and `vocab-words` (own words from a text or a list).

**D14. Surfaces of version 1.0.** The plugin works in Claude Code (terminal,
IDE, the Code tab of the desktop app), in Cowork and in Codex CLI. The
`vocabbot` program works in every terminal with Python. A session on a phone
and the claude.ai site alone belong to the extensions after version 1.0
(section 14).

**D15. Version 1.0 covers text.** A card holds the word, the meaning, an
example sentence and the IPA transcription. Images, recordings and speech
recognition belong to the extensions after version 1.0.

---

## 4. Tools and libraries

Versions checked on 14.11.2026 in PyPI, the npm registry, GitHub Releases and
endoflife.date. The file `uv.lock` pins the exact versions. Every stage
starts with `uv lock --upgrade` and a new check of this table.

| Tool or library | Version | Release | Role |
|---|---|---|---|
| Python | 3.15.2 | the 3.15 series since 2026-10-09 | development interpreter and CI |
| uv | 0.13.8 | 2026-11-12 | environment, lock file, build, CLI installation, publishing |
| uv-build | 0.13.8 | 2026-11-12 | the package build backend |
| ruff | 0.17.5 | 2026-11-12 | linter and formatter |
| mypy | 2.4.1 | 2026-10-28 | type checking |
| pytest | 9.2.0 | 2026-10-27 | tests |
| fsrs (py-fsrs) | 6.3.3 | 2026-11-13 | the reference scheduler in tests |
| rich | 15.0.0 | 2026-04-12 | the look of the terminal session until Stage 3; `term.py` replaces it from Stage 4 |
| wordfreq | 3.1.1 | 2023-11-21 | word frequency in the course pipeline (the library's last release) |
| actions/checkout | v7.0.1 | 2026-07-20 | CI |
| astral-sh/setup-uv | v10.3.3 | 2026-10-28 | CI |
| actions/setup-node | v7.1.0 | 2026-10-08 | CI, `claude plugin validate` (added in Stage 3) |
| actions/upload-artifact | v7.0.2 | 2026-10-07 | the release workflow (added in Stage 3) |
| actions/download-artifact | v8.0.2 | 2026-10-07 | the release workflow (added in Stage 3) |
| pypa/gh-action-pypi-publish | v1.14.3 | 2026-10-20 | publishing on PyPI |
| Claude Code | 2.1.325 | npm | host, `claude plugin validate` |
| Codex CLI | 0.169.0 | npm | host |

The state of your computer: Python 3.14.3, uv 0.11.18, Claude Code 2.1.323,
Codex CLI 0.153.4. Stage 1 starts with `uv self update` and
`uv python install 3.15`, which installs the new interpreter next to the
current one. Updating Claude Code and Codex CLI stays with you.

Development and CI run on Python 3.15. The engine code stays compatible with
version 3.10, because `vocabbot.pyz` runs on the interpreter of a host's
sandbox. Stage 3 checks the Python versions of the hosts and sets the final
lower bound. CI runs the tests on 3.10 and 3.15.

Libraries considered and not chosen:

| Library | Version | Reason |
|---|---|---|
| Typer | 0.29.1 | the command module must work in a `.pyz` file without dependencies, so `argparse` from the standard library handles the commands |
| Textual | 8.2.8 | a card session runs in sequence, which `term.py` handles entirely; a full-screen interface adds no function here |
| prompt_toolkit | 3.0.53 | reading a single key is covered by `msvcrt` and `termios` from the standard library |
| ty | 0.0.104 | the tool is below version 1.0, so the stable mypy checks the types |

Sources of the course data:

| Source | State | Licence | Use |
|---|---|---|---|
| kaikki.org, extract of the English Wiktionary | dump of 2026-10-01, a 2.9 GB `.gz` file | CC BY-SA 4.0 and GFDL (Wiktionary content) | translations into de, es, fr, pl; gender; pronunciation |
| kaikki.org, extracts of the de, es, fr editions | current | CC BY-SA 4.0 and GFDL | plural, forms, pronunciation |
| CEFR-J Vocabulary Profile | 1.5 | research and commercial use free of charge with a citation | the A1–B2 level of an English entry, carried over to the concept |
| wordfreq | data of release 3.1.1 | CC BY-SA 4.0 | the order of entries and the choice of the most frequent equivalent |
| Tatoeba | weekly export | CC BY 2.0 FR, some sentences CC0 | example sentences with a Polish translation |

---

## 5. Repository layout

```
vocabbot/
  pyproject.toml  uv.lock  .python-version  LICENSE  NOTICE  CLAUDE.md
  src/vocabbot/
    fsrs.py        the FSRS-6 scheduler
    store.py       the learner's folder: plan, log, folder pointer, conflict copies
    book.py        the state of the cards replayed from the log
    queue.py       the day's queue for several languages, forecast
    answers.py     normalising and grading answers
    courses.py     the course catalog and the entry checks
    gate.py        preview and commit of changes of the plan and the courses
    cli.py         the commands and the JSON output
    drill.py       the interactive session
    term.py        colour, symbols and widths in the terminal
    data/courses/<language>/<level>.jsonl  meta.json
    data/lang/<language>.json              rules for grading answers
    data/i18n/pl.json                      messages
  plugin/                                the plugin (Stage 3)
    .claude-plugin/plugin.json  plugin.json
    skills/<skill>/SKILL.md  reference/  shared/rules.md  bin/vocabbot.pyz
  .claude-plugin/marketplace.json  .agents/plugins/marketplace.json
  rules/                                 shared rules (the source of the copies in the skills)
  tools/courses/                         the course pipeline (Stage 2)
  scripts/build.py  validate.py  session_test.py
  sessions/                              session test files
  tests/  tests/fixtures/
  docs/
  .github/workflows/validate.yml  release.yml
```

The script `scripts/build.py` generates the files `shared/rules.md` and
`bin/vocabbot.pyz` in the skills. The validator refuses a copy older than its
source.

---

## 6. Data model

### 6.1 The learner's folder

```
registers/plan.json     languages, levels, weights, new words a day, recall, days off
log/reviews.jsonl       the log: one row per graded answer
log/decisions.md        one line per approved change of the plan or a course
log/flags.jsonl         reports of mistakes in entries
courses/<language>/own.jsonl   own words
registers/.pending/     previews waiting for a confirmation
```

### 6.2 The plan

```json
{
  "schema": 1,
  "base": "pl",
  "languages": [
    {"code": "en", "levels": ["b1", "b2"], "weight": 2},
    {"code": "de", "levels": ["a1", "a2"], "weight": 1},
    {"code": "es", "levels": ["a1", "a2"], "weight": 1, "paused": false}
  ],
  "new_per_day": 15,
  "retention": 0.9,
  "directions": ["produce"],
  "sibling_gap_days": 3,
  "sibling_distance": 5,
  "mix": "interleaved",
  "review_limit": null,
  "days_off": ["sun"],
  "day_starts_at": 4,
  "leech_lapses": 4,
  "max_languages": 3
}
```

### 6.3 A row of the log

```json
{"ts": "2026-11-16T18:22:05.123456Z", "day": "2026-11-16", "card": "de-a1-0042#p",
 "lang": "de", "grade": "almost", "auto": "almost", "kind": "review",
 "error": "gender", "given": "das Hund", "ms": 4200, "source": "cli"}
```

The field `kind` takes the values `learn`, `review`, `drill`. Replaying the
state works out the kind of a row itself from the order of the rows, so a
second answer on the same day never changes the schedule.

### 6.4 A course entry

```json
{"id": "de-a1-0042", "concept": "c00042", "rank": 42, "pos": "noun",
 "lemma": "Hund", "display": "der Hund", "gender": "m",
 "forms": {"plural": "die Hunde"}, "accept": ["der Hund"],
 "gloss": {"pl": "pies"}, "ipa": "/hʊnt/",
 "example": {"text": "Der Hund schläft im Garten.", "gap": "Hund",
             "pl": "Pies śpi w ogrodzie.", "source": "tatoeba:1234567"},
 "confusable": ["en-a1-0057"], "sources": ["cefrj", "enwiktionary", "wordfreq"],
 "checked": true}
```

### 6.5 A card and a family of cards

A card is an entry with a direction: `<id>#p` means production (the Polish
meaning, the answer in the language being learned), `<id>#r` means
recognition. Version 1.0 turns production on by default, which the engine
grades from the typed answer; recognition is an option of the plan with the
learner's own grade. The cards of one concept in different languages and the
two directions of one entry form a family.

---

## 7. How the engine works

### 7.1 Schedule

The state of a card is its stability, difficulty and the day of the last
review. The engine computes the due date from the current stability and the
recall of the plan, so a change of the recall recomputes all due dates at
once. An interval is a whole number of days, at least one. A learning day
starts at the hour `day_starts_at`.

### 7.2 The day's queue

1. Reviews: cards due today or earlier, in the order of their due dates,
   with an optional limit `review_limit`; cards above the limit move to the
   next day and the result gives their number.
2. New words: the limit `new_per_day` split by weight with the largest
   remainder method, rotating the language that gets the remainder.
   Candidates come in course order. The engine skips today an entry whose
   family holds a card introduced within the last `sibling_gap_days` days.
3. Order of the session: reviews, then new words, at the end the drill. The
   languages are interleaved in proportion to their cards. The engine keeps
   at least `sibling_distance` positions between the cards of one family.
4. The list of the day is a function of the log before that day, the plan,
   the course and the day's register, so an interrupted session resumes in
   the same order in the terminal and in the chat.
5. A day off from `days_off` has an empty queue and the reviews due move to
   the next learning day.
6. The learner chooses the stage (reviews, new words, drill) at any moment:
   the session brings the cards of the chosen stage first, and the other
   cards keep the engine's order (Stage 10).
7. The learner adds more new words and more reviews to the day. Added words
   join one at a time in a fixed order of languages by weight. Added reviews
   are the due cards outside the day's list first, then the cards with the
   nearest later dates as reviews before their day. `registers/day.json`
   keeps the numbers of added cards (Stage 10).
8. A new word comes at once as a question (`new_words: ask`) or after an
   introduction (`new_words: show`). The day's reviews follow the order of
   the plan (`review_order`). The drill has two grades (Stage 10).

### 7.3 Safeguards of saving grades

The engine accepts the grade of a new card only when the card belongs to the
list of the day (the option `--extra` lets the learner add words above the
limit). The engine accepts a review before its due date only with the option
`--ahead`. The grade `known` is available only at the first showing. The
engine refuses a row dated earlier than the last row of the log.

### 7.4 Grading answers

The rules of a language in `data/lang/<language>.json` set the articles,
replacement characters (for example `ss` for `ß`, `ae` for `ä`), optional
elements (the English `to` before a verb) and ignored characters. The engine
recognises the error classes `diacritic`, `typo`, `article`, `gender`, `case`
and `wrong_language` (an answer matching the entry of the same concept in
another language being learned). The engine writes the error class into the
log, which the `status` summaries and the `vocab-coach` skill use.

### 7.5 Forecast and progress

`status` gives for every language the number of learned cards, the reviews
for today and for seven days, the number of lapses, hard words (from
`leech_lapses` lapses), the recall measured over the last 30 days and the
share of grades the learner changed. `forecast` simulates the next days with
the current plan and gives the daily load and the date the chosen levels are
complete.

---

## 8. Commands of the program

| Command | What it does |
|---|---|
| `vocabbot init [FOLDER] --base pl --lang en:b1-b2:2 --lang de:a1-a2 --new 15` | creates the learner's folder and the plan |
| `vocabbot today` | the plan of the day: reviews, new words and drill for every language |
| `vocabbot note --card ID --stdin`, `vocabbot flag --card ID --skip` | a note for a word shown with its answer; a word put aside without a report of a mistake, brought back by `flag --clear` (Stage 11) |
| `vocabbot today --extra N`, `vocabbot today --reviews N` | more new words and the next round of reviews for today; with `--next` the result holds the next cards (Stage 10) |
| `vocabbot drill` | the interactive session in a terminal |
| `vocabbot next --count 10 --json` | the next cards without their answers; new words with their full content to show; `--stage reviews\|new\|drill` brings the cards of the chosen stage first (Stage 10) |
| `vocabbot answer --card ID --stdin --json` | grades a typed answer, saves a row, returns the right answer and the example |
| `vocabbot grade --card ID --grade known` | the learner's own grade: "known" and recognition cards |
| `vocabbot regrade --card ID --grade know` | a change of the last grade at the learner's request, marked in the log |
| `vocabbot status` | progress and recall for every language, hard words, error classes |
| `vocabbot forecast --days 30` | the daily load and the date levels are complete |
| `vocabbot plan show`, `vocabbot plan set KEY=VALUE` | the plan; a change as a preview with a token |
| `vocabbot words add --lang de --stdin` | own words as a preview with a token |
| `vocabbot commit --confirm TOKEN` | carries out the shown change |
| `vocabbot course list`, `vocabbot course check` | courses with counts; a check of the structure and consistency of the entries |
| `vocabbot flag --card ID --stdin` | a report of a mistake in an entry |
| `vocabbot doctor` | a check of the folder: damaged rows, conflict copies, merging logs |
| `vocabbot quiz --lang de [--levels a1-b2] [--count 8]`, `vocabbot quiz --check --stdin` | the placement test: questions without answers, then the grades of the answers and the proposed levels; writes nothing (Stage 3) |
| `vocabbot lookup --lang de --stdin` | course entries for a word or a Polish meaning, marking cards that wait in today's session (Stage 3) |
| `vocabbot reveal --card ID#r` | the meaning of a recognition card before the learner's own grade; refuses production cards (Stage 3) |
| `vocabbot use FOLDER` | points the program at an existing learner's folder, for example on a second computer (Stage 3) |

Every command takes `--json`, `--learner` and `--today`.

---

## 9. Skills and rules of the plugin

| Skill | Scope | Engine commands |
|---|---|---|
| `vocab-start` | the choice of languages, levels, weights and the limit; a short placement test from the course entries; plan changes; installing the `vocabbot` program | `init`, `plan`, `commit`, `course list`, `forecast`, `quiz`, `doctor` |
| `vocab-session` | the daily session in the chat in batches of about 10 cards; the drill; a summary of the session | `today`, `next`, `answer`, `grade`, `regrade`, `reveal`, `flag` |
| `vocab-coach` | explaining a word, mnemonics for hard words, lists of words confused between languages, practice of learned words in sentences, the weekly review | `status`, `forecast`, `lookup` |
| `vocab-words` | own words from a text, a list or a photo of a textbook page; reports of mistakes in entries | `words add`, `commit`, `flag`, `course check`, `lookup` |

Shared rules (`rules/`), copied into every skill:

1. The answer after the grade: the model shows the right answer only after
   the result of `answer` or `grade` for that card.
2. The engine computes the grade; the model proposes no change of a grade and
   runs `regrade` only at the learner's explicit request.
3. Due dates, card counts and progress come only from the engine's results.
4. Content written by the model (a sentence, a mnemonic, an explanation) is
   marked "generated" and enters a course only through `words add` and a
   confirmation.
5. The learner's text and text from documents reach the engine on standard
   input.
6. The conversation runs in the base language. Words and sentences of the
   language being learned keep their original spelling.
7. A skill announces a reminder only when the host has actually scheduled
   it.

In Stage 3 the rules took the form of eight files `rules/*.md` in English:
how to run the engine, the answer after the grade, grades from the engine,
numbers from the engine, marking generated content, standard input, a
confirmation of every change, and language and reminders.

---

## 10. Stages

The plan has five stages, each one working session done in one go. You
added Stage 4 on 15.11.2026 after the audit of version 1.0.0-rc.2. The
protocol of closing a stage: the tests pass, the plan has its updated status
and conclusions, the project memory has a new entry, the changes have a local
commit. A push, a tag, a release and a publication need your separate,
explicit consent.

### Stage 1. The engine and the `vocabbot` program

Scope:

1. The package skeleton: `pyproject.toml` with the `uv_build` backend,
   dependency groups `dev` (pytest, ruff, mypy, fsrs) and `data` (wordfreq),
   `.python-version` 3.15, `uv.lock`, ruff and mypy configuration,
   `CLAUDE.md`, `.gitignore`, the `validate.yml` workflow.
2. `fsrs.py`: FSRS-6 with the default parameters, recall, interval, the
   initial state, the update after a review.
3. `store.py` and `book.py`: the learner's folder, the plan with validation,
   appending to and reading the log, replaying the state, the folder pointer,
   detecting damaged rows and conflict copies, writing with LF line endings.
4. `queue.py`: reviews, the choice of new words, interleaving, the drill,
   limits, days off, the forecast.
5. `answers.py` and the rules of four languages: normalisation, error classes,
   detection of an answer in another language.
6. `courses.py`: the catalog, the entry format, `course check`; a starter
   course of 60 concepts in four languages (240 entries) written and checked
   by hand, with articles, plurals and example sentences.
7. `gate.py`: preview, token, expiry, a check of file changes since the
   preview, the decisions log.
8. `cli.py`: all commands of section 8 and the JSON output.
9. `drill.py`: the terminal session with Rich and a plain text version for
   the `.pyz`; a colour and a language tag on every card; every answer saved
   at once; an exit key that keeps the progress.
10. `scripts/build.py`: building `vocabbot.pyz` with the `zipapp` module.

Acceptance criteria:

- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src` and
  `uv run pytest` pass on Python 3.15; `pytest` passes on 3.10 too.
- The schedule matches `fsrs` 6.3.3 on nine saved scenarios for recall 0.9
  and 0.85 and on 200 random sequences of grades (stability and difficulty
  to 1e-6, the interval to the day).
- Tests confirm: the split of the limit by weight, the gap between languages
  for one concept, keeping a family apart in the queue, the unchanged list of
  the day after an interrupted session, the drill without a change of the
  schedule, refusing a grade outside the list of the day, refusing `known` at
  a review, the same replayed state for a log merged from two sources,
  grading every error class in each of the four languages, the change gate
  (token, expiry, a file changed after the preview), `next` without the
  answer in its result.
- `python vocabbot.pyz` carries out a whole learning day in isolated mode
  (`python -I`), without installed libraries.
- A simulation of 30 days of learning three languages on the starter course
  passes without errors and gives the same result in two runs.
- A manual trial: `vocabbot init`, `vocabbot drill` and `vocabbot status` in
  Windows Terminal, typing ä, ß, ñ, é.

#### Result of Stage 1 (14.11.2026, version 1.0.0.dev1)

All acceptance criteria of Stage 1 are met; the table gives the results.
Environment: uv 0.13.8 (updated from 0.11.18), Python 3.15.2 and 3.10.20
installed through uv next to Python 3.14.3, ruff 0.17.5, mypy 2.4.1,
pytest 9.2.0, rich 15.0.0, fsrs 6.3.3.

| Criterion | Result |
|---|---|
| ruff, ruff format, mypy, pytest on 3.15 | no findings; mypy in strict mode with target 3.10; 117 tests |
| pytest on 3.10 | 117 tests in the separate environment `.venv-py310` |
| agreement with `fsrs` 6.3.3 | 9 scenarios for recall 0.9 and 0.85 and 200 random sequences of grades; stability and difficulty agree to 1e-6, intervals to the day |
| behaviour of the engine | tests cover the split of the limit by weight, the 3-day gap between languages, keeping a family apart in the queue, the unchanged order after an interrupted session, the drill without a change of the due date, refusing a grade outside the list of the day, refusing "known" at a review, the same state after merging two logs, grading every error class in four languages, the change gate and `next` without the answer |
| `vocabbot.pyz` | a 74 KiB archive; a whole learning day of two languages with `python -I -S`, that is without any package outside the standard library |
| a 30-day simulation | three languages, 12 new words a day, Sundays off; two runs give an identical log byte for byte, the list of the day does not change after answers; the gap between languages for every concept is at least 3 days |
| a console trial | the ConPTY pseudo-console that Windows Terminal uses: `vocabbot init` answered "t" to the question about saving, a session with words typed letter by letter (der Bär, süß, el señor, mañana, le café, la fête) graded "know", the `vocabbot status` screen |

The stage brought solutions that complete the plan:

1. An entry id has the form `<language>-<concept>` (`de-c90002`), so a card
   keeps its identity when an entry changes its level in Stage 2. The starter
   course uses the concepts c90001–c90060. Own words get random ids
   (`de-u3f9a1c`).
2. The engine shows new words in batches of five (word, meaning, forms,
   pronunciation, example) and checks them with a question right after the
   batch; the first typed answer sets the initial state of the card.
3. Grading has two more classes: `form` (another form of the same word, for
   example the plural, gives "almost") and `blank` (an empty answer). The plan
   setting `diacritics=lenient` lets learners without a keyboard for é or ñ
   pass answers without diacritics; the log still records such an error.
4. The gate also covers `vocabbot init` and the repairs of `vocabbot doctor`.
   The preview of a new folder waits in `~/.vocabbot/pending`. In a terminal
   the program asks the question "Zapisać tę zmianę? [t/N]" itself. In `--json`
   mode it returns the token, which the skill passes to `vocabbot commit`.
5. Extra new words from `vocabbot today --extra N` go to
   `registers/day.json`, so they count in the terminal and in the chat until
   the end of the day.
6. A paused language gets no new words and keeps its reviews; `lang.xx=off`
   removes a language from the plan. An entry reported with `flag` waits
   outside the queue until `flag --clear`.
7. Besides the modules of section 5 the package has the modules `assets`,
   `errors`, `session` (next cards, answers, grades), `plans`, `words`,
   `progress` (progress and forecast) and `doctor`.

The stage brought three conclusions.

1. The simulation found a defect that the tests of single functions did not
   show: the limit of a language with an exhausted course moved to the other
   languages at every recomputation of the queue, so one language got 15 new
   words with a limit of 12. The engine now chooses the whole list of the day
   from the state before that day and sets the order on the full list; later
   answers only remove cards already done from it.
2. Replaying the whole log at every answer stretched the simulation to 283 s.
   The log read once per process and the state before the day computed once
   per day cut it to 28 s; writing with `fsync` costs about 2.6 ms per answer
   on Windows and stays for the safety of the log.
3. Python 3.15 works in UTF-8 mode by default. On Python 3.10 the program
   sets UTF-8 for input and output itself, because without it the letter ñ
   does not pass through a pipe in the cp1250 encoding.

You can make the trial in the Windows Terminal app itself. The command
`uv tool install .` in the repository folder installs the `vocabbot` program,
after which `vocabbot init`, `vocabbot drill` and `vocabbot status` lead
through the whole path.

### Stage 2. A1–B2 courses for four languages

Scope:

1. `fetch`: downloading the sources into `.cache/` outside the repository
   (about 5 GB, processed as streams from `.gz` files), recording the address,
   the date and the SHA-256 sum of every file.
2. `concepts`: the list of concepts from CEFR-J A1–B2 (entry, part of speech,
   level) with permanent ids, ordered by level and frequency.
3. `align`: the choice of a sense in the English Wiktionary (the first sense
   with translations into at least three of the four other languages), the
   de, es, fr and pl equivalents with gender; the main equivalent by
   frequency in the target language, the others in the `accept` field.
4. `enrich`: plurals, basic forms and IPA pronunciation from the de, es, fr
   editions and from the English entries.
5. `examples`: Tatoeba sentences of 4–10 words with a form of the entry and a
   Polish translation, with the sentence id for the list of authors.
6. `emit`: the course files, `meta.json`, `NOTICE` and the list of sentences
   with their authors.
7. Automatic checks: `vocabbot course check` and the pipeline report
   (coverage per level, missing fields, homonyms, the same Polish meaning for
   two different answers in one language, which needs a sentence with a gap
   or a distinguishing hint).
8. A sample review: 150 random entries per language and pair of levels (1200
   entries in all) compared with the sources; error classes go back into the
   pipeline rules and the pipeline runs again.
9. Extending the `data/lang` rules with cases found in the courses.

Acceptance criteria:

- `vocabbot course check` returns 0 errors for all eight course files.
- Every language has at least 1500 A1–A2 entries and at least 3000 B1–B2
  entries with all required fields: the answer, the Polish meaning, the part
  of speech, the gender for nouns of de, es and fr, the sources.
- At least 80% of A1–A2 entries and 60% of B1–B2 entries have an example
  sentence with a Polish translation.
- The share of entries with a wrong meaning, equivalent or gender in the
  sample is at most 3% for A1–A2 and at most 5% for B1–B2.
- The pipeline run twice on the same source files gives identical course
  files.
- The plan holds the real numbers of entries, coverage and sample results.

Decision point of the stage: when the B1–B2 sample exceeds the threshold
after two pipeline runs, I present two ways to choose from. The first is an
extra review session within this conversation without model costs. The
second is a batch run through a model API with a cost estimate presented
before it starts.

#### Result of Stage 2 (14.11.2026, version 1.0.0.dev2)

The A1–B2 courses for four languages pass the course check without errors
and have 1.2% errors in a sample of 1200 entries. English also meets the
criterion of B1–B2 example coverage, which stays unmet for German, Spanish
and French; the table gives the results.

| Criterion | Result |
|---|---|
| `vocabbot course check` | 0 errors and 0 warnings in 16 course files (four languages, four levels each) |
| A1–A2 entries (threshold 1500) | English 2036, German 2036, Spanish 2020, French 2014 |
| B1–B2 entries (threshold 3000) | English 3583, German 3353, Spanish 3442, French 3435 |
| examples with a Polish translation, A1–A2 (threshold 80%) | English 98.3%, German 88.3%, Spanish 87.8%, French 87.5% |
| examples with a Polish translation, B1–B2 (threshold 60%) | English 74.5%; German 53.8%, Spanish 49.9% and French 51.7% below the threshold |
| errors of meaning, equivalent or gender in the sample (thresholds 3% and 5%) | A1–A2: 8 of 600 (1.3%); B1–B2: 6 of 600 (1.0%) |
| repeatability | two pipeline runs give 24 identical course files |
| tests | 131 on Python 3.15; 124 on Python 3.10, where the pipeline tests need the `data` group |

The pipeline in `tools/courses` downloads the sources (3.2 GB outside the
repository), passes once through the Wiktionary extract in about 3 minutes
and builds the courses in about 3 minutes. The first runs with rules alone
had 9–16% errors in the samples, mostly because of ambiguous words (coke as
coal coke, fan as a hand fan, line as a rope), which rules based on frequency
and back-translation cannot settle. At the decision point you chose the batch
review: Claude Sonnet 5.5 reviewed 6600 concepts through the Message Batches
API in 264 requests (2.15 million input tokens, 0.78 million output, a cost
of 6.04 USD) and gave the sense, the Polish meaning and the equivalents with
gender. The decisions of the review are kept in `tools/courses/review.jsonl`,
so later builds need no API. The pipeline still sets the articles, forms and
pronunciation itself by its rules and dictionaries. The sample after the
review led to three new rules (a noun with a plural article or used only in
the plural is dropped, a Polish meaning does not repeat the word) and to nine
manual corrections of review decisions, marked in the file with the field
`corrected`.

The B1–B2 example coverage depends on Tatoeba, which has sentences with most
of these words, often without a Polish translation. The pipeline also looks
for it through translations into other languages, in one or two steps, and
accepts such a sentence only when the Polish translation contains the Polish
meaning of the entry. The condition came after the sample review, which
found pairs of sentences with different content (for example "Disco"
translated as "puszka"), and lowered the B1–B2 coverage by about 8
percentage points. Closing the gap needs sentences from another source or
sentences prepared by a model with a separate estimate; this decision does
not block Stage 3.

The stage brought solutions that complete the plan:

1. One pass through the raw Wiktionary extract (3.08 GB) gives the English
   entries with translations and the German, Spanish, French and Polish
   entries, so separate files of the de, es and fr editions turned out to be
   unnecessary.
2. Entries with the same Polish meaning merge into one entry with more
   answers only when another language confirms the synonymy. Polish homonyms
   get a hint with the English word, for example "rakieta (ang. racket)" and
   "rakieta (ang. rocket)"; the English course keeps the more frequent one.
3. Grading recognises a reflexive verb typed without its pronoun ("ändern"
   for "sich ändern", "levantar" for "levantarse") as "almost" with the error
   class "reflexive pronoun".
4. The course check requires the fields of the plan (answer, Polish meaning,
   part of speech, gender of a noun, sources) and reports the coverage of
   pronunciation and examples.
5. Every course has a file `sentences.tsv` with the authors of the Tatoeba
   sentences used and a file `meta.json` with the version of the courses
   (`2026.11.2`) and the sources with their licences.
6. The starter course stayed as test data in `tests/fixtures/courses`.

The stage brought three conclusions.

1. Rules based on word frequency and back-translation lowered the errors from
   16% to 9–14%. Only the review of the senses by a model, which cost 6.04
   USD, brought the errors in the sample down to 1.2%.
2. Merging entries with the same Polish meaning needs a confirmation in
   another language, because Polish homonyms (rakieta, spadek, zmiana) glued
   different words together.
3. The sample after the review found errors of the pipeline itself (a plural
   article added by the pipeline, nouns used only in the plural); the rules
   that remove them now work for the whole course.

### Stage 3. The plugin, verification and the release candidate

Scope:

1. Four skills with `reference/` files and the shared rules.
2. Manifests for Claude and Codex, two marketplace catalogs, a version
   consistent with `pyproject.toml`.
3. `scripts/validate.py`: consistent manifests, self-sufficient skills,
   current copies of `rules.md` and `vocabbot.pyz`, no calls that change the
   plan without a preview, no personal data in the repository files.
4. A check of the Python versions of the hosts (Claude Code, Cowork, Codex)
   and the lower bound.
5. Session test files with deterministic checks (the state of the log and the
   plan after a session) and a check of the session files without a model.
6. Documents in English and Polish: README, QUICKSTART, PRIVACY,
   `docs/architecture.md`, CHANGELOG, an English version of the plan.
7. The `release.yml` workflow: a tag runs the tests, builds the package, the
   `.pyz` file and the plugin package, and creates the release.
8. A local installation of the plugin in Claude Code and in Codex CLI and a
   walk through the whole path on a trial folder.
9. The pilot protocol.

Acceptance criteria:

- `claude plugin validate ./plugin --profile directory --strict` and
  `scripts/validate.py` pass without errors and warnings.
- Every skill runs the engine from its own folder in Claude Code and in Codex
  CLI.
- All checks of Stages 1 and 2 still pass.
- The release packages build locally: the wheel and the source archive of the
  package, `vocabbot.pyz`, the plugin package, the archives of single skills.

Steps after your consent, each separately: creating the repository
`dithiothreitol/vocabbot` and a push, the tag `v1.0.0-rc.1` with a release,
publishing the package on PyPI, paid session tests.

#### Result of Stage 3 (14.11.2026, version 1.0.0-rc.1)

The acceptance criteria of Stage 3 are met in the part that needs neither a
model nor your consent. The walk through the whole path with a model in
Claude Code and in Codex CLI and the session tests with a model wait for your
consent with an estimate; the mechanical part of the path (installing the
plugin and the engine run from the folder of every skill) I checked without a
model. The table gives the results.

| Criterion | Result |
|---|---|
| `claude plugin validate ./plugin --profile directory --strict` | no findings; the marketplace catalog (`claude plugin validate . --strict`) too |
| `scripts/validate.py` | 0 errors and 0 warnings: manifests and versions, 43 engine calls in 17 commands compared with the program's parser, current copies, translations of the documents, no secrets and no home paths |
| the engine from a skill's folder | Claude Code 2.1.323 and Codex CLI 0.153.4 install the plugin from the local marketplace in isolated configuration folders; each of the four skills runs `bin/vocabbot.pyz` from its folder in the host's cache (`init`, `commit`, `today`, `status`, `words add`) |
| checks of Stages 1 and 2 | ruff and mypy without findings; 150 tests on Python 3.15 and 143 on 3.10 (after the fixes from the walk through the path), where the pipeline tests need the `data` group; `course check` without errors |
| release packages | `scripts/build.py package` builds the wheel and the source archive 1.0.0rc1, `vocabbot.pyz` (2.3 MB), `vocabbot.plugin` (9.3 MB), four skill archives and `SHA256SUMS` |
| session tests | 7 sessions in five groups (setup, the answer after the grade, grades, consent to a write, numbers) with 13 turns; `session_test.py --check` prepares all of them without a model; unit tests confirm that the checks catch a leaked answer and a plan written without a yes |
| Python versions of the hosts | Claude Code and Codex CLI use the computer's Python (3.14 here); Cowork has Python 3.10.12 on Ubuntu 22.04 according to community reports; claude.ai and the code execution tool have Python 3.11.12 according to the documentation; the lower bound stays at 3.10 |

The stage brought solutions that complete the plan:

1. The placement test `vocabbot quiz` picks words evenly from the whole
   length of a level, that is from the most to the least frequent, and
   prefers entries with an example. A level counts as known from 80% of right
   answers, with "almost" counting as half. The test in a terminal stops at
   the first level that is not known.
2. The command `words add` moves a word the course already has to the front
   of the queue instead of copying it (a row `{"ref": ...}` in `own.jsonl`),
   leaves out words already being learned and warns about the same Polish
   meaning and about a language outside the plan.
3. The result of `status` lists the words learned in the last seven days
   (`recent`) and answers given in another language (`confusions`), and the
   command `lookup` finds entries for a word or a Polish meaning. Cards that
   wait in today's session carry `waiting_today`, so the coach keeps their
   answers back.
4. The command `reveal` shows the meaning of a recognition card and refuses
   production cards, so the rule of the answer after the grade rests on the
   engine for recognition cards too.
5. The engine finds the learner's folder in the current folder when it holds
   a plan, which serves Cowork and a project folder. The command
   `vocabbot use` points at an existing folder on a second computer, and
   `init --set` takes any plan setting in the first preview.
6. Besides `shared/rules.md`, every skill has a file `shared/labels.md` with
   the Polish names of grades, error classes and parts of speech, generated
   from the texts of the engine.
7. The file `vocabbot.pyz` is built from sorted entries with a fixed time.
   The four copies in the skills are identical, so git stores the file once,
   and the freshness check compares the contents of the archive regardless of
   the zlib version.

The stage brought three conclusions.

1. The course starts with short function words (an, sie, ich, la), which
   appear in ordinary text too often for their presence in a model's reply to
   prove a leak. The leak check of the session tests therefore uses a learner
   at levels B1–B2 and words of four letters or more.
2. The example of a function word is sometimes a sentence with another part
   of speech of the same form; for example the Spanish "la" as a pronoun has
   an example in which "la" is the article. This limitation of the Stage 2
   pipeline concerns homographs; the pilot will show its scale, and the fix
   belongs to the course pipeline.
3. On this computer `py -3` points to a removed interpreter while `python3`
   and `python` work, so the engine rule gives the order `python3`, `python`,
   `py -3`.

The steps in the table lead to version 1.0; each waits for your separate
consent.

| Step | Cost | Notes |
|---|---|---|
| session tests with a model: `session_test.py --model sonnet` (7 sessions, 13 turns) | an estimated 3–6 USD with Claude Sonnet 5.5 | the script stops once `--max-cost-usd` is reached |
| a walk through the path with a model in Claude Code and in Codex CLI on a trial folder | an ordinary working session on your accounts | installation and the engine checked without a model |
| the repository `dithiothreitol/vocabbot` and a push | none | |
| the tag `v1.0.0-rc.1` and the release through `release.yml` | none | the release holds the packages from the table of results |
| publishing on PyPI | none | trusted publishing, the repository variable `PUBLISH_PYPI` |
| the pilot according to `docs/pilot.md` | none | after the release |

#### The walk through the path with a model (15.11.2026)

With your consent of 15.11.2026 I walked through the whole path in Claude
Code (the plugin from the repository folder, the Sonnet 5.5 model, 17 turns,
5.24 USD according to `claude -p`) and in Codex CLI (the plugin from a local
marketplace, the gpt-6-astra model, 6 turns on your account), on trial
folders in a temporary directory. The walk covered the setup with a placement
test, a session with the drill and a grade changed on request, own words
with a hint, the coach and a plan change. Every grade in the logs comes from
the engine. The table pairs the observations with the fixes that went into
version 1.0.0-rc.1.

| Observation | Fix |
|---|---|
| On a day off the model offered reviews ahead, which give a new learner no words | the session instructions point to `today --extra` for new words on a day off |
| The model gave the codes of error classes ("wrong", "article") and field names | the engine returns Polish names (`grade_pl`, `errors_pl`, `errors_30_pl`), and a rule keeps commands, fields and ids out of the conversation |
| The warning about the same meaning read like the promise of a hint, so the model promised a hint the preview did not hold | a new wording of the warning; the `vocab-words` instructions lead to a new preview with the hint and treat "yes, but…" as a request for a new preview |
| The Codex sandbox blocks writes outside the working folder, so `init` ended with a traceback while creating `~/.vocabbot/pending` | the preview of a new folder falls back to the folder itself, the pointer in `~/.vocabbot` is optional (the `skipped` field), `commit` also looks for the preview in the current folder and in the folder of `--learner`, and a refused write gives an `io_error` in JSON |
| Codex worked around that block by patching the home folder in a Python wrapper, and saved the plan in the same turn as the preview, without a confirmation | the rules forbid working around the engine, tell the model to end the turn at the question about saving and explain that a request listing every setting is not a confirmation; in a second trial Codex stopped at the preview and saved the plan only after "tak" |
| Codex showed the new words and their questions in one message | the session instructions separate the introduction of the words from the questions |
| An own word given as a JSON object got a lemma with its article | the engine sets the lemma of a noun without the article |

The walk brought three conclusions.

1. The confirmation rule depends on the model, because the engine cannot
   tell who said "yes". One of the two models broke it at the first attempt.
   A confirmation hook in Claude Code (the HouseholdBot pattern) would move
   the confirmation into the host's window; section 2.3 left it out, so adding
   it stays your decision.
2. The courses start with function words whose examples often show another
   part of speech of the same form (French "la" and "le" as pronouns with
   examples using the article, German "das", Spanish "lo más"), so a learner
   meets them in the first session. A fix in the pipeline, for example a
   question without a sentence for such entries, needs a new build of the
   courses and is a decision before the pilot.
3. The npm wrapper `codex.CMD` cuts an argument at its first newline, so the
   walk script passes the text of a turn on standard input (`codex exec -`).

#### Repository and release (15.11.2026)

| Step | Result |
|---|---|
| repository | public `github.com/dithiothreitol/vocabbot` with a description and topics, the `pypi` environment for trusted publishing |
| CI | green on Python 3.10 and 3.15 and in the plugin job after two fixes: `astral-sh/setup-uv` has no moving `v10` tag, so the workflows pin `v10.3.3`; ruff classifies the course pipeline modules explicitly, because a local `build/` folder changed the order of imports |
| tag and release | `v1.0.0-rc.1`, a pre-release with the wheel, the source archive, `vocabbot.pyz`, `vocabbot.plugin`, four skill archives and `SHA256SUMS`; the sums of the downloaded files match |
| installing from GitHub | `claude plugin install vocabbot --marketplace dithiothreitol/vocabbot` in an isolated configuration and `uvx --from git+https://github.com/dithiothreitol/vocabbot@v1.0.0-rc.1 vocabbot` work |
| PyPI | `vocabbot 1.0.0rc1` published on 15.11.2026 with a token from your account: the wheel and the source archive downloaded from the GitHub release and checked against their sums; `uv tool install vocabbot` and `pip` install this version. Later releases can use a trusted publisher (project `vocabbot`, owner `dithiothreitol`, repository `vocabbot`, workflow `release.yml`, environment `pypi`) |

#### Version 1.0.0-rc.2 (15.11.2026)

You approved both decisions from the walk through the path on 15.11.2026, and
version 1.0.0-rc.2 carries them out.

| Change | Result |
|---|---|
| confirmation hook (`plugin/hooks/`) | in Claude Code and Cowork every engine `commit` and every direct write into a learner's folder goes to the host's permission prompt with the content of the preview; `VOCABBOT_HOOK=off` turns the prompt off in tests without a person; 4 tests, a check in `validate.py`, `claude plugin validate --profile directory --strict` without findings |
| examples of function words (courses 2026.11.3) | a word spelt like an article but of another part of speech (French and Spanish "la", "le", "les", "los", "un", "unos") is asked without a sentence; German "das" keeps an example only where no noun follows it; 7 entries changed and a few neighbouring entries got other examples; `course check` without errors, two builds identical |
| graphics (`docs/assets/`) | the logo at the top of both READMEs, also shown on the PyPI page, and a 1280×640 social preview image for the repository; the HTML sources and the render command sit next to the PNG files |
| tests | 154 on Python 3.15 and 147 on 3.10; CI green |
| release | the tag `v1.0.0-rc.2`, a GitHub pre-release with all packages, `vocabbot 1.0.0rc2` on PyPI (the release files checked against their sums), the plugin in your Codex refreshed to rc.2 |

The social preview image needs a one-time upload in the repository settings
(Settings, Social preview), because GitHub offers no programming interface for
it. You uploaded it on 15.11.2026.

---

### Stage 4. Course content, mechanics and the terminal session

The audit of 15.11.2026, made before the session tests, compared the engine,
the courses and the terminal program with the SuperMemo courses. The engine
follows the SuperMemo way of learning: the sections of reviews, new words and
the drill, three grades, a drill that leaves the schedule as it was, and a
target recall of 90%. The courses lack part of the basic vocabulary, about 6%
of the examples use the word in another sense or as another part of speech,
and the terminal session prints plain text. You approved Stage 4 on
15.11.2026 together with four decisions: the order of the work (content,
mechanics, terminal, session tests), basic words added without model costs,
a model review of the examples, and the grade "nie wiem" for a wrong article.

| Area | Finding of the audit |
|---|---|
| basic words | the courses lack, among others, English yes, no, with, house, hello, thanks and the names of the months, German ja, nein, kein, du, danke, Eltern, Leute, kennen, heißen, Spanish sí, gracias, estar, haber, tú, conocer and French oui, non, merci, tu, chez, il y a, gens, combien |
| causes in the pipeline | 1018 concepts without a Polish translation in the table of the same part of speech, 133 concepts without an English entry of that part of speech (Wiktionary files the months as proper names), CEFR-J determiners outside the map of parts of speech, about 1000 merges per language, 64 English entries dropped as homonyms (with and house among them), nouns used only in the plural left out |
| the start of A1 | function words make up 87–97% of the first 30 entries, and some of them have an ambiguous or narrowed meaning (German "mit" as "razem") |
| examples | 11 of 180 sentences in a random sample use the word in another sense or as another part of speech; a few dozen Tatoeba sentences are vulgar |
| schedule | due dates have no spread, so the words learned on one day come back together; "prawie" for a wrong article lengthens the interval; the FSRS parameters are the defaults for every learner |
| terminal | plain text, colour only with the Rich package, two confirmations for every card, the forecast as a list of 30 lines |

Scope:

1. The course pipeline recovers concepts: CEFR-J determiners get their part
   of speech, a concept without a translation table uses the table of
   another part of speech of the same headword (an interjection, a proper
   name), and a noun used only in the plural enters the course with its
   plural article (die Eltern, les gens). A recovered concept enters the
   course only with a decision of the model review or of the editors.
2. The editors' file `tools/courses/editor.jsonl` holds the decisions for
   recovered A1–A2 concepts, concepts that belong to one language (estar,
   haber, kein, chez, kennen, conocer, connaître and the like), the
   separation of common synonyms and homonyms by a note in the Polish
   meaning (house and home, with and of) and corrected meanings of function
   words. The editing uses no paid model.
3. Level A1 starts with the editors' starting list: greetings, "yes" and
   "no", personal pronouns and basic verbs and nouns. The further entries of
   every level follow frequency, and every ten entries hold at most three
   function words.
4. Claude Sonnet 5.5, through the Message Batches API, judges up to three
   candidate sentences for each entry (sense, part of speech, a faithful
   Polish translation, suitable content) and chooses the first good one or
   none. The decisions live in `tools/courses/examples.jsonl`, so later
   builds need no API, and a filter of vulgar words in the pipeline guards
   the entries without a decision. The cost limit is 8 USD.
5. The engine spreads due dates from 3 days up, following the FSRS ranges.
   The spread follows from the card id and the day of the answer, so both
   computers see the same due dates. In German, Spanish and French an
   article of another gender, or no article for a noun whose article shows
   its gender, gives the grade "nie wiem". The answer rules and the course
   check handle nouns in the plural.
6. The engine fits the initial intervals, the first four FSRS-6
   parameters, to the learner's log once the log has enough second answers.
   `status` compares the measured recall with the target.
7. A new module `term.py` on the standard library detects what the terminal
   can do (`NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, VT mode on Windows),
   replaces Unicode characters with ASCII where the terminal cannot show
   them, and wraps text by the width of its characters. The Rich package is
   no longer needed.
8. `vocabbot drill` gets a new session layout, and `vocabbot` without a
   command shows a start screen with the plan of the day. The session shows
   a compact card, saves a correct answer without an extra key, shows a
   character-level difference, folds a card into one line after the answer
   and takes the commands `/cofnij`, `/znam`, `/koniec` and `/pomoc`. A
   progress line shows the place in the session, and the summary gives the
   result, the words to work on, tomorrow's load and the activity of the
   last weeks.
9. `today`, `status` and `forecast` get progress bars of the levels, a load
   chart and a compact layout of the numbers.
10. Version 1.0.0-rc.3: manifests, `pyproject.toml`, CHANGELOG, the
    documents in both languages and the plan.

Acceptance criteria:

- `vocabbot course check` passes without errors, and every word on the
  audit's check list is in the course or has the reason of its absence in
  the plan.
- Every entry with an example has a decision of the example review, or
  comes from the build after the review and passed the filter of vulgar
  words.
- The first 30 A1 entries of every language hold at most 9 function words.
- Tests cover the spread of due dates, the grading of articles, nouns in the
  plural, the fit of the parameters and the terminal module without colour
  and with ASCII characters.
- The checks of Stages 1–3 pass, and two builds of the courses give
  identical files.

Steps after your consent, each separately: the session tests on version
rc.3, the push, the tag and the release of rc.3. You approved all of them on
15.11.2026.

#### Result of Stage 4 (15.11.2026, version 1.0.0-rc.3)

Stage 4 completed the course content, the mechanics and the terminal
session. The courses 2026.11.4 hold 23 095 entries instead of 21 919, every
word on the audit's check list is in the courses, and every example sentence
passed a model review.

| Criterion | Result |
|---|---|
| `vocabbot course check` | 0 errors and 0 warnings in 16 course files |
| entries | English 6286, German 5649, Spanish 5581, French 5579 |
| the audit's check list | every word is in the courses, among them yes, no, with, house, hello, thank you, the names of the months, ja, nein, kein, du, danke, die Eltern, die Leute, kennen, heißen, sí, gracias, estar, hay, tú, conocer, oui, non, merci, tu, chez, il y a, les gens, combien; the English articles the, a and an are no cards, because Polish has no equivalent |
| editors' decisions | 229 rows in `tools/courses/editor.jsonl`: 10 new concepts (among them ty, Pan, nazywać się, estar, es gibt, znać, ile, chez, rodzice, chętnie), 43 places of the A1 starting list, decisions for 24 of the 46 CEFR-J determiners (23 in the courses), 12 names of the months, about 90 recovered A1–A2 concepts, 42 concepts with a meaning told apart by a note, 5 concepts left out |
| the start of A1 | the first 30 entries hold 6–7 function words (limit 9); the level opens with "cześć", "dzień dobry", "tak", "nie", "dziękuję", "proszę" |
| example review | Claude Sonnet 5.5 judged 42 156 candidate sentences for 16 406 entries in 411 requests: 14 911 sentences stay, 1495 entries have no good sentence; the first candidate failed in 3406 cases (mostly the translation, the sense and the part of speech); the cost was 6.36 USD plus 0.03 USD for a test request |
| examples with a Polish translation, A1–A2 (threshold 80%) | English 90.0%, German 84.4%, Spanish 82.8%, French 81.9% |
| examples with a Polish translation, B1–B2 (threshold 60%) | English 66.2%; German 48.5%, Spanish 44.3% and French 47.1% below the threshold, because the review rejected sentences with another sense |
| engine | due dates spread by the FSRS ranges with the card and the day as the key; "nie wiem" for an article of another gender and for a missing article that shows the gender; nouns used only in the plural and months without an article; initial stabilities fitted from 40 second answers; `status` shows the intervals after a first answer and the recall against the target |
| terminal | `term.py` on the standard library, the new session `vocabbot drill`, the start screen `vocabbot`, a new look of `today`, `status` and `forecast`; the package no longer depends on Rich |
| reproducibility | two builds of the courses give identical files |
| tests | 190 on Python 3.15; 173 on Python 3.10 (1 skipped without the `data` group) |
| plugin checks | `validate.py` 0 errors and 0 warnings, `session_test.py --check` 7 of 7, `claude plugin validate --profile directory --strict` without remarks |
| release | the tag `v1.0.0-rc.3`, a GitHub pre-release with every package; `vocabbot 1.0.0rc3` on PyPI through trusted publishing (`release.yml` started for the tag, no token), file checksums equal to the GitHub release; the package has no dependencies; the plugin in your Codex refreshed to rc.3 |
| session tests with a model (Claude Sonnet 5.5, consent of 15.11.2026) | the first run passed 6 of 7 for 1.78 USD; the check of the placement test took a word of a sentence the engine gave, the answer of another question, for a leak; after the fix of the engine (such a question loses its sentence) and of the check (the engine's sentences are no leak) the test passes for 0.31 USD; 7 of 7 in all for 2.09 USD |

A trial of the terminal session found a defect that the starting list made
common: marking a word as known recomputed the whole list of the day, and the
gap between languages for one concept then blocked a card already shown in
the other language. The words of the plan are now chosen first and stay the
same during the day, and words added later join after them; a test checks
that a card once shown stays on the list.

Conclusions:

1. Courses built only from the CEFR-J list and the rules of the pipeline
   lose basic words where parts of speech meet (the months as proper names,
   determiners outside the map, English verbs spelt like nouns). An editors'
   file with human decisions fills these gaps cheaply and repeatably.
2. The model review of the examples rejected one in five first candidates.
   The rules that find a word in a sentence do not see its sense, so every
   new sentence needs such a review.
3. The coverage of B1–B2 examples for German, Spanish and French depends on
   the number of Tatoeba sentences with a Polish translation. Raising it
   needs sentences from another source or translations prepared by a model,
   priced separately.

---

### Stage 5. A schedule fitted to the learner

You added Stage 5 on 15.11.2026, during Stage 4. It covers three topics: a
full fit of the FSRS parameters to the learner, a day plan aware of the
learner's presence, and a tool that replays the log and compares every
variant with FSRS-6. The tool comes first, because it decides whether the
other two variants improve the predictions and the load compared with FSRS-6.
Stage 4 brings the first step of the fit: initial stabilities computed from
the learner's second answers.

| Topic | State on 15.11.2026 | Source |
|---|---|---|
| FSRS optimizer | py-fsrs fits parameters in the extra `fsrs[optimizer]` with heavy dependencies; FSRS-Optimizer uses PyTorch; fsrs-rs 1.2.1 keeps the default parameters below 64 training items | open-spaced-repetition repositories |
| Measures of comparison | the benchmark of spaced-repetition algorithms compares log loss, RMSE(bins) and AUC on answers predicted before their outcome | srs-benchmark, Expertium's description |
| A plan by presence | Anki has had "Easy Days" since 24.11 (fewer reviews on chosen weekdays, set by hand) and load balancing within the fuzz | FSRS Helper and Anki documentation |

Scope:

1. `vocabbot replay` replays the log in order of time and, for every review,
   records the recall each variant predicts before the answer is known. The
   report gives log loss, RMSE(bins) and AUC for every variant and the
   difference from FSRS-6 with the default parameters, overall and for each
   language. A fit uses the earlier part of the log and the evaluation the
   later part, so no variant sees the answers it predicts.
2. The same command simulates the load: reviews a day, minutes and the
   predicted recall of every scheduling variant for the coming weeks. The
   simulation uses the rules of `forecast`.
3. A full fit of the 21 FSRS-6 parameters on the standard library (gradient
   descent regularised towards the defaults), for each language separately
   once the language's log has enough reviews. The engine takes fitted
   parameters only when `replay` shows a lower log loss than FSRS-6 with the
   defaults on the later part of the log.
4. A day plan aware of presence. From the ordinary statistics of the log,
   without a network, the engine computes the chance of a session on each
   weekday and the usual number of minutes. Within the fuzz it chooses for a
   review the day with the better chance of presence and the lighter load,
   the number of new words keeps the forecast minutes within the learner's
   usual time, and before an expected break the session offers reviews ahead
   of their day. The result stays a function of the log and the plan, so both
   computers compute the same plan.
5. `status` and the coach show which parameters apply, how many answers they
   come from and how they score in `replay`.

Acceptance criteria:

- `replay` on the synthetic logs of the tests recovers the parameters of
  the generator, and for FSRS-6 with the defaults gives results that match
  the `fsrs` module.
- Fitted parameters apply only with a better score in `replay`; otherwise
  the engine stays with FSRS-6.
- In the simulation, the plan by presence lowers the backlog after days
  without learning without the predicted recall falling below the target.
- The day's queue stays identical on two computers with the same log.

Data: the fit and the plan by presence need a few weeks of the log, so the
`replay` tool is ready before the end of the pilot, and the fit and the plan
use the pilot's log. The stage needs no model costs.

#### Result of Stage 5 (15.11.2026, version 1.0.0-rc.4)

Stage 5 gave the engine a comparison with FSRS-6, the full fit of the
parameters and the plan by presence. All three parts run on the standard
library and follow from the log, so both computers compute the same plan.

| Criterion | Result |
|---|---|
| `vocabbot replay` | predicts every review before its outcome; for FSRS-6 with the defaults it gives the same values as the `fsrs` module; reports log loss, RMSE(bins) with the bins of fsrs-optimizer and AUC of every variant and the difference from FSRS-6, overall and for each language; simulates four weeks of every schedule with the days without learning from the presence profile |
| full fit (`optimize.py`) | the forward pass matches the `fsrs` module to 1e-12, the derivatives match finite differences; 2272 reviews in 0.6–2 s; on six synthetic learners the test loss fell on average from 0.3582 (FSRS-6) to 0.3548, against 0.3529 for the generator's parameters |
| recovering the generator's parameters | the quality of the predictions comes close to the generator, while single parameters, for example the stability after "znałem", cannot be read from a few thousand reviews; for a learner who differs from FSRS-6 only in the initial stabilities the fit predicted the test part worse than the defaults |
| the gate of `plan fit` | a language gets parameters of its own only when they predict the later part of the log better than FSRS-6; otherwise the preview ends with a message and the plan stays as it is |
| the plan by presence | for a synthetic learner who skips weekends (56 days, 901 reviews), the simulated share of late reviews fell from 34% to 19%, the mean delay from 0.43 to 0.24 days, and the predicted recall stayed at 0.89 against a target of 0.90 |
| the pace of new words and reviews ahead | `today` and the chat session give fewer new words when the day would exceed the usual minutes by more than a quarter, and offer reviews ahead before a day off or a day usually skipped |
| tests | 14 new tests in `tests/test_schedule.py`; 204 in all on Python 3.15 and 187 on 3.10 (1 skipped without the `data` group); the plugin checks without remarks |
| release | with your consent of 15.11.2026: the tag `v1.0.0-rc.4`, a GitHub pre-release with every package, `vocabbot 1.0.0rc4` on PyPI through trusted publishing with checksums equal to GitHub's, CI green, the plugin in your Codex refreshed to rc.4 |

Conclusions:

1. On the log of one learner after a few weeks, the full fit need not
   predict better than FSRS-6, so the comparison on the later part of the
   log is the condition of its use, not an extra.
2. The plan by presence lowers the backlog without a cost to the recall,
   because it moves due dates only within the FSRS fuzz.
3. The pilot's log will decide whether the full fit enters the plan of any of
   your languages; `vocabbot replay` shows it after two weeks.

### Stage 6. The server for chat applications

You added Stage 6 on 15.11.2026, after the analysis of a service with a chat
window and a subscription. Instead of a chat window of its own, VocabBot runs
as a remote MCP server with accounts: Claude on the web, on the desktop and
on the phone, ChatGPT, Claude Code and Codex connect to it as to any
connector, and the chat application's model runs the conversation on the
learner's subscription. The server measures interest without model costs on
your side and runs on your VPS at Hetzner.

| Topic | State on 15.11.2026 | Source |
|---|---|---|
| The MCP SDK for Python | version 2.3.0 (02.10.2026): `MCPServer`, the Streamable HTTP transport, an authorization server with dynamic client registration, PKCE and refresh tokens | PyPI, the package's code |
| Connectors in Claude | custom connectors to remote MCP servers work on every plan (the free plan: one connector); the redirect address `https://claude.ai/api/mcp/auth_callback`, later also `claude.com` | Anthropic's help center |
| Apps in ChatGPT | an MCP server over Streamable HTTP with OAuth 2.1, resource metadata and the `resource` indicator; a stable redirect address with RFC 9207; tools that write data in developer mode on the Business, Enterprise and Edu plans according to the help center | the Apps SDK documentation, OpenAI's help center |

Scope:

1. The package `vocabbot.server` with the program `vocabbot-server` in the
   extra `vocabbot[server]`; the engine and `vocabbot.pyz` stay on the
   standard library.
2. Accounts with invitation codes, passwords in scrypt, the OAuth records in
   SQLite as SHA-256 hashes, a sign-in and sign-up page in Polish.
3. An OAuth 2.1 authorization server from the MCP SDK: dynamic client
   registration with a list of allowed redirect addresses, PKCE, an access
   token for an hour, a refresh token that changes at every use, the resource
   indicator and the issuer in the sign-in response.
4. MCP tools that run the program's commands on the account's folder and
   return the same JSON as the plugin, and guides for the model that follow
   the plugin's skills.
5. The engine for many accounts in one process: a shared catalog of courses,
   the preview of a new plan in the account's folder without a pointer, the
   learning day in the server's time zone.
6. Docker behind Caddy with a TLS certificate, and the document
   `docs/server.md`.

Acceptance criteria:

- The MCP SDK's OAuth client, acting as a chat application, registers, signs
  in through the server's page and uses the tools; two accounts work apart
  and no result reveals the server's paths.
- The engine's guarantees hold through the server: a question without its
  answer, the engine's grade, a change only through a preview and its token,
  the learner's text outside the command's options.
- The Docker image passes the whole path on the real courses, also behind
  Caddy with TLS.
- The tests of every module pass on Python 3.10 and 3.15.

#### Result of Stage 6 (15.11.2026, version 1.0.0-rc.5)

Stage 6 gave VocabBot a server with accounts for chat applications. The
server uses the same engine commands as the program and the plugin, so a
session in Claude on a phone follows the same rules as a session in Claude
Code.

| Criterion | Result |
|---|---|
| OAuth 2.1 | the MCP SDK's reference client passes the resource discovery, the registration, the sign-in on the server's page, the code exchange with PKCE and the issuer check (RFC 9207); a refresh token works once, and after a refresh the previous access token ends |
| sign-in safeguards | redirects only to Claude, ChatGPT and the learner's computer; a limit of failed attempts per login and per address; a single-use authorization code; a new password ends the account's connections |
| tools | 22 tools with read and write annotations; values passed as a command's options end with the error `bad_arguments`, and plan settings must have the form KEY=VALUE |
| accounts apart | a second account sees no plan of the first one and cannot commit its preview; results give paths relative to the account's folder |
| the engine for many accounts | the catalog of courses loads once (0.33 s and 70 MB), and every account gets a copy of it with its own words without a new load |
| the Docker image | on the real courses all 22 tools work with response times from 11 to 87 ms; the same path passes behind Caddy with TLS, with correct addresses in the metadata and in the `WWW-Authenticate` header |
| clients | Claude Code connects to the server with a token and recognises the OAuth sign-in without one; connecting claude.ai and ChatGPT needs a public address, that is the deployment on the VPS |
| tests | 14 new tests in `tests/test_server.py` and a test of the session batch; 219 in all on Python 3.15 and 202 on 3.10 (1 skipped without the `data` group); the repository checks without remarks |
| deployment | with your consent of 15.11.2026 the server runs at `https://vocab.archxs.com` on your VPS at Hetzner as one more site of the shared Caddy, with a Let's Encrypt certificate, a limit of 384 MB (it uses 132 MB) and a daily backup at 4:00; the server's other sites run without a break; `scripts/deploy_vps.sh` repeats the deployment |
| test in production | all 22 tools through the MCP SDK's OAuth client on the real courses; the metadata, the `WWW-Authenticate` header and the refusal of a foreign redirect match the local tests |
| test with a model | Claude Code with Claude Sonnet 5.5, connected only to the server, went through 8 turns for 1.54 USD: the setup with a preview and the saving only after "tak", the session with the introduction of new words, questions without answers, the grading of answers passed unchanged (an empty one for "?"), the drill and the summary; the account's log on the server matches the conversation |
| release | with your consent of 15.11.2026: the tag `v1.0.0-rc.5`, a GitHub pre-release with every package, `vocabbot 1.0.0rc5` on PyPI through trusted publishing with checksums equal to GitHub's (with the `server` extra), CI green, the plugin in your Codex refreshed to rc.5 |
| engine fix | the test with a model showed a sentence with the answer of another card of the same batch ("„___, danke.”" next to the question about "danke"); the session batch now hides such sentences as the placement test does |

Conclusions:

1. An MCP server with accounts gives a chat window in Claude and ChatGPT,
   also on a phone, without model costs on the server's side, so it fits a
   test of interest before a decision about a service of your own.
2. In ChatGPT, tools that write data depend on the account's plan; a trial
   on the Plus or Pro plan shows whether the answers of a session reach the
   log.
3. Connecting claude.ai and ChatGPT from your account closes the check of
   the server; after that the server can take the first learners with
   invitations.

### Stage 7. Italian and the session one card at a time

You added Stage 7 on 15.11.2026 with two requests: Italian as the fifth
course language, and a chat session that shows one card at a time, as
SuperMemo does, with the number of cards in a message set in the plan. You
approved the model review with a limit of 7 USD.

Scope:

1. The plan key `batch` (1 to 20, default 1): with 1, a message holds the
   result of the last answer and the next card, and a new word comes alone
   before its question; `answer --next` returns the next cards at once.
2. Italian sources: the entries and translations of Wiktionary and the
   Tatoeba sentences with the links that start from Italian, so the
   translation paths of the other courses stay as they were.
3. Answer rules: `lo` beside `il`, the elided `l'` and `un'`, the plural `i`,
   `gli`, `le`, reflexive verbs in `-si`.
4. Course rules: the article by the first sound, the plural, months without
   an article, the spelling of forms without Wiktionary's stress marks.
5. The review of an added language (`review_lang.py`): the model chooses the
   Italian equivalent of the sense the course already has, seeing the Polish
   meaning and the words of the German, Spanish and French courses.

#### Result of Stage 7 (15.11.2026)

| Criterion | Result |
|---|---|
| the session one card at a time | `next` without `--count` returns `batch` cards, `today` reports `batch`, `answer --next` and the server's `then_next` save one call per card; the skill, the server's guide and the plan key describe both modes; deployed on the server on 15.11.2026 |
| the Italian course | 5576 entries (A1 1003, A2 1134, B1 1681, B2 1758), courses version 2026.11.5, the course check without remarks |
| the meaning review | 6705 decisions for 2.28 USD (Claude Sonnet 5.5, Message Batches); 27 concepts without a single Italian word |
| the example review | 3264 entries for 1.26 USD; 89% of the A1 entries have a sentence, 68% of A2, 50% of B1 and 29% of B2 |
| quality sample | 40 random entries: meanings, equivalents, articles and genders right; the sample showed Wiktionary's stress mark in 887 participles (organizzàto), which the build now removes; two of the 40 lists of other answers are too broad (il calore beside il bagliore) |
| the other courses | English unchanged; in German, Spanish and French 7 entries have a new or another example sentence through Italian translations in Tatoeba |
| cost | 3.54 USD of the 7 USD limit |
| release | with your consent of 15.11.2026: the tag `v1.0.0-rc.6`, a GitHub pre-release with every package, `vocabbot 1.0.0rc6` on PyPI through trusted publishing with checksums equal to GitHub's, CI green, the plugin in your Codex refreshed to rc.6 |

Conclusions:

1. Another course language needs above all a review decision for every
   concept; the rules of articles and spelling are short, and the review of
   one language costs about 3.5 USD.
2. The coverage of examples at B1–B2 is lower for Italian than for the other
   languages, because Tatoeba has few direct Italian–Polish translations.

### Stage 8. Pilot feedback: pronunciation, examples, a counter and ChatGPT

You added Stage 8 on 16.11.2026 after the feedback of the first pilot
learner, who learns English in ChatGPT. Status: carried out on 16.11.2026,
the result below.

#### Check of the feedback (16.11.2026)

| Feedback | Facts | Change |
|---|---|---|
| connecting ChatGPT looks different from the instructions | OpenAI's help center describes adding a server under Plugins (the plus button, a custom MCP server) without developer mode; the account's log on the server confirms that ChatGPT saved the plan and 18 answers | item 1 |
| the word cannot be heard | the courses hold no recordings; a chat application shows text and links | item 3 |
| the word cannot be read | 74% to 98% of the entries have IPA, depending on the language and level; `vocab_next` returns it with a new word and the guide asks to show it, while the result of an answer does not repeat it; the feedback may mean the written pronunciation or reading aloud, which a question to the pilot learner settles | item 3 |
| not every new word has an example | 10,738 of 28,671 entries have no sentence: 7% to 11% of the A1 entries and 45% to 71% of the B2 entries; 6 of the pilot learner's 18 cards had none (for, all, one, over, take, IT); the sentences come only from Tatoeba, and the rules forbid the chat model to add course data | item 4 |
| a counter of the words done | `vocab_today` reports the reviews and new words done for each language; `vocab_answer` and `vocab_next` report only the cards left, and the guide does not ask for a counter; the terminal session has a counter with a progress bar | item 2 |

The log also shows 14 answers "znałem" among the first 15 new A2 words, after
which the pilot learner changed the levels to B1–B2 (item 5).

Scope:

1. **ChatGPT.** The path Settings, Integrations, Plugins, the plus button and
   a custom MCP server with OAuth in `docs/server.md`, `docs/server.pl.md`,
   on the server's home page (`server.home_chatgpt`) and in the pilot
   invitation. The risk row on read-only access in ChatGPT reports the
   result of 16.11.2026.
2. **A counter.** The results of `answer`, `grade`, `regrade` and `next`
   report `done` beside `left`: the reviews, new words and drill done that
   day. The server's guide and the `vocab-session` skill start every message
   of a session with a counter line, for example "7 z 25 · nowe 3/15 ·
   powtórki 4/10". `today` lists the day's new words, so the summary at the
   end of a session gives their number and list.
3. **Pronunciation.** The pipeline writes the file name of a Wikimedia
   Commons recording into the entry. English, German and French recordings
   come from Wiktionary (for English the British one first, as the course's
   IPA). Spanish and Italian recordings come from Lingua Libre, because the
   Wiktionary extract leaves out the recordings in the pronunciation
   templates of these languages. `presentation` returns the address of the
   MP3 file, computed from the name by the Commons scheme, so the package
   holds only file names. The guide and the skill show the IPA and a link
   "🔊 wymowa" with a new word and in the result "prawie" and "nie wiem".
   `NOTICE` and the README name the source and the licences of the
   recordings. Coverage measured on 16.11.2026: English 98–100%, German
   95–98%, French 87–95%, Spanish 63–91%, Italian 27–81%.
4. **Examples.** A pipeline step `tools/courses/generate.py
   prepare|submit|collect` (Message Batches API, Claude Sonnet 5.5) writes,
   for every entry without a Tatoeba sentence, one short sentence at the
   entry's level, in the course meaning, with a Polish translation. The
   example review (`examples.py`) judges them as it judges Tatoeba
   sentences. The decisions go to `generated.jsonl` in the repository, so a
   build repeats without the API. The sentence names the source `generated`
   in the entry. First a sample of 200 entries and a check of 40 random
   ones, then the full run after your approval with the cost measured on the
   sample. The goal: a sentence in at least 95% of the entries of every
   level.
5. **A level set too low.** When at least 8 of the last 10 new words of a
   language get "znałem", the result of `grade` holds `level_hint`. The
   guide then offers the placement test or a higher level through a preview
   of the plan change.
6. **Checks and release.** Engine tests for `done`, `level_hint` and the
   recording's address, a pipeline test for the recording names,
   `session_test.py --check`, the server tests, a manual check of the
   recording link in Claude and ChatGPT in a browser and on a phone.
   Release `v1.0.0-rc.7` and deployment on the server, each with a separate
   approval.

#### Result of Stage 8 (16.11.2026)

You accepted Stages 8 and 9 on 16.11.2026 with one request that also asked
for a confirmation that they work, simulations and a code review. You
approved the full run of the model's sentences with a limit of 12 USD after
the estimate from the sample.

| Criterion | Result |
|---|---|
| ChatGPT | the path Settings, Integrations, Plugins and a custom MCP server in `docs/server.md`, `docs/server.pl.md`, on the server's start page and in the pilot invitation |
| the counter | `done` and `counter` in the results of `next`, `answer`, `grade`, `regrade` and `today`, the list `learned_today` in `today`; the server's guide and the `vocab-session` skill start every message with the counter and end the session with the day's new words |
| pronunciation | 23,368 entries (81.5%) with a recording on Wikimedia Commons: English 98–99%, German 92–95%, French 86–94%, Spanish 63–91%, Italian 27–79% by level; a reflexive verb and a word pronounced two ways get no recording of another form; recordings from Wiktionary, for Spanish and Italian from the Lingua Libre listings (`audio.py`); the IPA and the recording from another part of speech of the same word with one pronunciation gave an IPA to 196 more entries (91.4% of the entries in all) |
| examples | 10,738 entries without a Tatoeba sentence; the model wrote a sentence for each, the example review accepted 10,380 in the first run and 222 of 358 after one retry; 10,602 sentences in all (`generated.jsonl`) and an example in 99.5% of the entries, at least 99% on every level |
| quality sample | of 40 random sentences of the sample 38 right, two with a wrong tense in the translation (regañar) and a meaning inside a compound (sex education); the review rejected 356 sentences of the first run, mostly as unnatural (137), for the translation (76), the sense (46) or the part of speech (43) |
| a level set too low | `level_hint` in the result of `grade` or `answer` when 8 of the last 10 new words at the present levels were known, with the plan setting to change, at most once a day for the same levels; one line of hint in the terminal |
| an engine fix | a change of the levels during the day no longer adds new words on top of the daily limit; the simulation with the model found it (a counter of 10/35 instead of 10/25 after ten "znałem" and a change of the levels) |
| courses | version 2026.11.6; against version 2026.11.5 only added fields: a recording in 23,368 entries, an example in 10,602, an IPA in 196; no existing sentence or IPA changed; the course check without remarks |
| simulation without a model | two learners over 10 days (English from A2 with 12 words "znałem" on the first day and a change to B1–B2; Italian, Spanish and German from A1): 2496 checks of the counter, 804 answers, 550 new words (548 with a sentence, 537 with a recording, 531 with an IPA), one level hint, every day ended without cards left, no violation; the recordings of all five languages answer from Commons as `audio/mpeg` |
| simulation with a model | 9 turns of Claude Code (the Sonnet model) through a local server with a synthetic account, 1.84 USD: the counter in every message, a new word with its IPA and recording link, the level hint once, the change of the levels through a preview and "tak", the summary with the day's words; in the result "nie wiem" the model left out the recording link, so the result examples of the guide and the skill now show it; a second session after the fixes of the code review (6 turns, 1.02 USD) confirmed the counter of 10/25 after the change of the levels, one level hint without a break in the session and the recording link in the result "nie wiem" |
| code review | 15 confirmed faults, all fixed: a second choice of new words on spent generators that also moved shares between languages (replaced by places counted beforehand for the words outside the plan, in their language), the day's list with the answers of cards waiting in the drill, a level hint repeated or missing after a typed answer (now at most once a day for the present levels), a counter without reviews ahead, a reported card in the drill, the card's speech of the previous word, a voice of another variety, a batch collected twice and sentences kept for a changed entry, a Lingua Libre listing cut by an API error, a reflexive verb's recording without its pronoun, the copy of the rules in the server's guide, needless recounts of the day in the terminal; after the fixes 139 entries lost a wrong recording |
| tests | 248 on Python 3.15 and 220 on Python 3.10 (1 skipped without wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 of 7), `claude plugin validate --strict` and the course check without remarks |
| release | with your approval of 16.11.2026: the tag `v1.0.0-rc.7`, a pre-release on GitHub with every package, `vocabbot 1.0.0rc7` on PyPI through trusted publishing with sums matching GitHub, CI green, the plugin in your Codex refreshed to rc.7 |
| cost | 8.32 USD for the sentences (sample 0.09, writing 4.82, review 3.14, retry 0.27) of the 12 USD limit, and 2.86 USD for two simulations with the model |

Conclusions:

1. Sentences from the model with a review fill the course cheaply: the gap of
   37% of the entries cost 8.32 USD, and the review accepted 98.7% of the
   sentences.
2. Wiktionary gives recordings for English, German and French; Lingua Libre
   helps for Spanish and Italian, and the speech synthesis of the card from
   Stage 9 covers the words without a recording.
3. The simulation with a real model found an engine fault that the unit tests
   did not show, so it is worth repeating before a release.

### Stage 9 (conditional). A card in the chat window

MCP Apps let a tool show an interactive card in the conversation, in a frame
of its own. According to the announcement of 26.01.2026, Claude in the
browser and in the desktop application and ChatGPT support them; the
announcement does not mention the phone applications or audio playback. The
VocabBot card would show the counter, the word, the IPA and a button that
plays the recording. The browser's speech synthesis would read the words and
sentences without a recording. The stage starts with a trial: support for the
extension in the MCP Python SDK, the CSP rules for files from
`upload.wikimedia.org`, and playback in Claude and ChatGPT on a computer and
on a phone. I carried out the stage on 16.11.2026 together with Stage 8 at
your request, the result below.

#### Result of Stage 9 (16.11.2026)

| Criterion | Result |
|---|---|
| SDK | MCP Python SDK 2.3.0 has the `Apps` extension; the server announces `io.modelcontextprotocol/ui`, the tools `vocab_today`, `vocab_next`, `vocab_answer` and `vocab_grade` name the card in `_meta.ui.resourceUri` and in `openai/outputTemplate`, and the resource `ui://vocabbot/card.html` has the type `text/html;profile=mcp-app` |
| the card | `server/static/card.html` without outside dependencies: `ui/initialize`, `tool-result`, the size reports, the host's theme and variables; the labels from `pl.json`; the host draws the border (`prefersBorder`); a question neither shows nor plays its word |
| sound | the button plays the MP3 from `upload.wikimedia.org`, the only domain in the card's CSP; the browser's speech synthesis reads the words and sentences without a recording, marked by a dashed outline of the button |
| trial | a test host in Edge with real tool results: the card completes the handshake and shows a new word, a result with the drill and the day's summary in the light and dark theme, without JavaScript errors; the server test checks the tools' metadata, the resource and the CSP |
| deployment | server 1.0.0rc7 at `https://vocab.archxs.com` since 16.11.2026; a smoke test with a short-lived token of the test account, revoked after the test: 22 tools, the card on four tools, the card resource with its CSP and labels, the counter in `vocab_today`, a recording and an example in `vocab_lookup` |
| to check | the card in Claude and ChatGPT on a computer and on a phone from your account |

### Stage 10. The session's stages as in SuperMemo: the choice of stage, more words and more rounds of reviews

You added Stage 10 on 16.11.2026 after comparing VocabBot's session with the
SuperMemo application (two screenshots of a German course). Status: carried
out, released as `v1.0.0-rc.8` and deployed on 16.11.2026, result below.

#### How SuperMemo works (as of 16.11.2026)

| Mechanism | SuperMemo | Source |
|---|---|---|
| three stages of a day | the application's bar has three counters: repetitions, new material and drills; a course opens on the repetitions, then on the new material, then on the drills | FAQ "Repetitions and drills", the post "How to start learning with a course" |
| moving between the stages | the learner changes the mode at any moment (the Tab key in the browser) | FAQ on keyboard shortcuts |
| new material | the number of cards a day in the course plan (5, 10, 20, 30 or one's own) is a start, and after it the course goes on with further pages | the post "Customize your learning with SuperMemo", observation of the application |
| repetitions | repetitions left undone move to the following days, the new interval follows the real time since the previous repetition, the calendar has a daily limit of repetitions and excluded days | FAQ "Repetition limit", the post "Sort your repetitions" |
| a repetition before its day | SuperMemo for Windows makes a mid-interval repetition with a correction in the algorithm; the help of the course application describes no such function | SuperMemo help, "Mid-interval repetition" |
| the drill | a card graded "I don't know" or "Almost" comes back the same day until it succeeds, in a fixed order; grades of the final drill in SuperMemo for Windows leave the intervals unchanged | FAQ "Repetitions and drills", SuperMemo help, "Final drill" |
| grades | "I know" lengthens the interval, "Almost" lengthens it and sends the card to the drill, "I don't know" shortens it | the post "Repeat section and 3 buttons assessment" |
| the first contact | the first contact with a word counts as learning and the next ones as repetitions | the post "How to learn with SuperMemo" |

#### Scope and result of Stage 10 (16.11.2026)

| Your remark | How |
|---|---|
| 1. a choice between new words and reviews | `next --stage reviews\|new\|drill` (on the server `vocab_next` with `stage`) brings the cards of the chosen stage first; the result names the stage (`stage`), a stage without cards (`stage_empty`) and the cards left in the three stages (`left`); without a choice the engine's order holds: reviews, new words, drill |
| 2. the day's number of new words as a start | `today --extra N --next` (`vocab_add_today` with `count`) adds words on top of the plan's number any number of times, up to 100 a day; `more.new` gives the words available at the plan's levels, and the session offers more words after the day's list |
| 3. skipping the reviews | moving to the stage `new` leaves the reviews untouched: the card on screen waits in its stage, and reviews left undone keep their date and open the next day |
| 4. moving to the new words during the reviews | an answer with `--next` (`then_next`) returns the next card of the stage the answered card belongs to, so the chosen stage lasts without further parameters; after the last card of a stage the session moves to the next one in the engine's order |
| 4. a new cycle of reviews after all of them | `today --reviews N --next` (`vocab_add_today` with `reviews`) adds the next round: the due reviews outside the day's list first (over `review_limit`, or of a day off), then the cards with the nearest later dates as reviews before their day; the engine counts the next date from the real gap (FSRS), the log row carries `ahead`, and a card answered today joins no further round |
| the drill | unchanged in principle: a card graded "prawie" or "nie wiem" comes back until "wiem" and its date no longer changes that day; the stage `drill` may be chosen earlier |
| the day's register | `registers/day.json` keeps the new words and the reviews added to one day, so the day's list stays a function of the log before the day, the plan, the course and this file, and an interrupted session resumes at the same place in the terminal and in the chat |
| the terminal | `vocabbot drill` takes `/nowe`, `/powtorki`, `/utrwalanie` and `/wiecej` at the answer prompt and the key `p` at a new word, and after the day's list offers `n` (5 new words), `p` (the next round of 10 reviews) and Enter (the end) |
| the chat | the guide `session` and the skill `vocab-session` have the section "The stages and more cards": a start from the reviews with one line about the choice, the words "nowe", "powtórki", "utrwalanie", "więcej słów" and "jeszcze powtórki", one line at the end of a stage and the offer after the day's list |
| the server and the card | `vocab_next` takes `stage`, `vocab_grade` takes `then_next`, `vocab_add_today` takes `count` and `reviews` and returns `added` and `next`; the parameter `ahead` left the tools, since reviews before their day join the day through `vocab_add_today`; the card shows the three stages with the cards left and marks the stage in progress |
| a fault found by the simulation | a second request for more new words with three languages gave 28 words instead of 25: the largest remainder split moved a place between languages and a word already shown fell outside the choice; added words now join one at a time in a fixed order of languages by weight, so a larger number only appends (this also covers the word added after "znałem") |
| the day's pace | reviews the learner adds leave the number of new words set from the presence profile unchanged |
| tests | 255 on Python 3.15 and 227 on Python 3.10 (1 skipped without wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 of 7) and `claude plugin validate --strict` without remarks; new tests: the choice of a stage and a stage without cards, a round of reviews before their day, due reviews over the limit first, a day off with reviews on request, the next card in the chosen stage through the commands, stages and additions in the terminal, more new words with three languages, the server's tools with `stage`, `then_next` and `reviews` |
| simulation | the full courses (de A1–A2, es A1, it A1, 15 new words a day) through the program's commands: 1206 checks without a fault; the counter adds up after every answer, the next card stays in the chosen stage, two additions give 25 new words, four rounds give 35 reviews before their day without a repeat, and a round is empty when every card has today's answer; the table below describes the simulation with a model |

#### The three differences aligned with SuperMemo (16.11.2026, with your approval)

| Difference | How |
|---|---|
| a new word | the plan setting `new_words` with the default `ask`: `next` gives a new card as a question without its word, the result of the first answer shows the word in full (forms, IPA, recording, meaning, example), and a word answered "nie wiem" comes back the same day in the drill; a right first answer gets the grade `known` (a word known before the course), adds one more new word to the day and counts for the level hint; `new_words=show` keeps the introduction before the question; plans saved earlier get `ask` |
| two grades in the drill | a drill answer other than "wiem" keeps the card in the drill and enters the log as `dont_know`; the engine's verdict with its error classes stays in `auto`; the terminal offers the keys 1 and 3 in the drill, and a regrade there takes `know` or `dont_know` |
| the order of reviews | the plan setting `review_order`: `due` (most overdue first, the default), `course` (the order of the course), `interval` (shortest intervals first), `random` (the same for the whole day); reviews added during the day follow the planned ones |
| the forecast | `forecast` takes the share of right first answers from the log, and before 20 such answers it assumes 20% for a plan that asks at once and 80% for a plan that shows the word first |
| the chat, the terminal and the card | the guide, the skill `vocab-session` and the rule about the answer after the grade describe a new word as a question, the result "✓ znane wcześniej" and the two grades of the drill; the terminal asks a new word without an introduction and shows its forms and example after a right answer; the card shows a new word in full with the result of its first answer |
| tests | 260 on Python 3.15 and 232 on Python 3.10 (1 skipped without wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 of 7) and `claude plugin validate --strict` without remarks; new tests: a new word as a question and the grade `known`, the two grades of the drill with the refusal of "prawie", the four orders of reviews, the plan settings through the commands, the terminal session asking at once |
| simulation of the program | the full courses through the commands with the default plan: 1407 checks without a fault in 131 answers (55 new words not known, 16 known before, 41 drill answers graded only `know` or `dont_know`); no card gave its word before the grade, and the four orders of reviews hold the same cards |
| simulation with a model | a local server and Claude Code with the Sonnet model, 10 turns for 1.79 USD: a start from the reviews with the line about the choice, "nowe" (`vocab_next` with `stage: new`), a new word as a question, the full introduction after "?", "✓ znane wcześniej" after a right answer, "daj jeszcze 3 słowa" (`vocab_add_today` with `count: 3`), back to the reviews, the next round (`vocab_add_today` with `reviews: 5`, the 4 available cards joined) and a move to the drill; every turn followed the guide |
| release and deployment | with your approval of 16.11.2026: the tag `v1.0.0-rc.8`, a pre-release on GitHub with all 9 packages, `vocabbot 1.0.0rc8` on PyPI through trusted publishing with sums matching GitHub, CI green, the plugin in your Codex refreshed to rc.8; server 1.0.0rc8 at `https://vocab.archxs.com`, a smoke test with a short-lived token of the test account, revoked after the test: 22 tools, the card on five tools (with `vocab_add_today`), the card resource with its CSP and labels, the counter in `vocab_today`, a recording and an example in `vocab_lookup` |
| to check | a session from your account in Claude and ChatGPT: a new word as a question, the words "nowe", "powtórki", "więcej słów" and "jeszcze powtórki", the card with three stages; the plans of the accounts on the server, the pilot's account too, now have `new_words=ask` |

### Stage 11. Handling a card as in the SuperMemo application

I proposed Stage 11 on 16.11.2026 after your question about the differences
in handling (apart from the algorithms) between VocabBot and the SuperMemo
application. Status: accepted with the defaults `answer_mode=type` and
`sentence_translation=shown`, carried out, released as `v1.0.0-rc.9` and
deployed on 16.11.2026, result below. The scope holds only confirmed differences: the state of
VocabBot checked in the repository, the state of SuperMemo seen on your
screenshots or described literally in the SuperMemo FAQ. The stage fits one
working session, needs your approval before it starts and ends with version
`1.0.0-rc.9`.

#### Basis of the scope

| Difference | SuperMemo | VocabBot in rc.8 | Certainty |
|---|---|---|---|
| self-assessment | the "Check" button shows the answer, then the learner picks one of three grades; the input field for answers is an element switched on in the course settings | a production card needs a typed word and the engine grades it; only recognition cards take the learner's own grade | screenshots, the FAQ on the configuration of the Extreme courses, the code |
| the sentence's translation | an icon under the example sentence opens its translation | a question shows the translation at once | screenshots, the session guide |
| the next review date | the switch "Show the number of days until the next repetition" | the terminal shows the date with every answer, the chat gives it on request | FAQ, the code |
| switching a word off | "Disable repetitions" and "Enable repetitions" for a card | a word leaves the queue only through a report of a mistake in the entry | FAQ, the code |
| a note for a word | an edit icon on the card (I have not checked what it does) | the coach's mnemonics live only in the conversation; the learner's folder has no notes | the code; on SuperMemo's side only the presence of the icon |

#### Scope

1. **Self-assessment beside typing.** The plan setting `answer_mode` takes
   `type` (the default, today's behaviour) or `self`.
   - The engine: in the mode `self` the command `reveal` accepts a production
     card of today's list, and `grade` accepts `know`, `almost` and
     `dont_know` for it. In the mode `type` both commands refuse as before,
     with a message that names the setting. A typed answer keeps the
     engine's grade in both modes. A log row with the learner's own grade
     has no `auto` field, like the rows of recognition cards.
   - The common rules of rc.8 hold unchanged: a first grade "wiem" of a new
     word gives `known`, the drill has two grades.
   - The chat: "pokaż" or "sprawdź" calls `vocab_reveal`, the message shows
     the word in full and asks for the grade, and the learner's reply goes to
     `vocab_grade` with `then_next`. The model passes the grade exactly as
     the learner gave it and proposes none itself (the rule
     `03-engine-grades`).
   - The terminal: in the mode `self` an empty Enter shows the answer and
     asks for the grade with the keys 1, 2, 3; a typed word is graded by the
     engine. In the mode `type` an empty Enter means "nie wiem" as before.
   - The card in the chat window: the result of `vocab_reveal` shows the
     word with its recording and a line with the three grades to type.
2. **The sentence's translation on request.** The plan setting
   `sentence_translation` takes `shown` (the default) or `hidden`.
   - The engine returns `sentence_pl` as before, and `today` names the
     setting.
   - The card: with `hidden` a button under the sentence opens the
     translation, without the model and the server.
   - The chat: with `hidden` a question leaves the translation out, and
     "tłumaczenie" adds it from the data the model already holds.
   - The terminal: with `hidden` the command `/t` shows the translation.
   - The default stays `shown`, since in the chat a request for the
     translation costs one more turn of the model. A change of the default
     to `hidden` is your decision when you accept the stage.
3. **The next review date with the result.** The plan setting `next_review`
   takes `shown` (the default) or `hidden`.
   - The engine adds the field `back` to the result of an answer, with a
     ready text ("wróci jutro", "wróci za 4 dni", "wróci dziś
     w utrwalaniu"). The texts move from the terminal's section to a common
     section of `pl.json`, so the chat, the card and the terminal show the
     same.
   - The chat and the card end the result line with `back`.
4. **Switching a word off.** The command `flag --card ID --skip` puts a word
   aside without reporting a mistake, and `flag --card ID --clear` brings it
   back.
   - The engine: the row in `log/flags.jsonl` gets the mark `skip`; the word
     leaves the queue, the drill and the choice of new words as a reported
     word does. `status` gives the list `skipped` apart from the reports.
   - The server: `vocab_flag` gets the parameter `skip`.
   - The chat: "nie chcę tego słowa" and "pomiń to słowo" put the word
     aside, "przywróć słowo …" brings it back (`vocab_lookup` finds the
     card).
   - The terminal: the command `/pomin` at the answer prompt.
5. **A note for a word.** The command `note --card ID --stdin` saves the
   learner's own note (up to 500 characters), and `note --card ID --clear`
   removes it.
   - The engine: the file `log/notes.jsonl` only grows and the last row of
     an entry holds. The note comes back as `word.note` in the result of an
     answer, in `reveal` and in `lookup`. A question never holds it, since a
     note may give the answer away.
   - The server: a new tool `vocab_note` (23 tools instead of 22).
   - The chat: "zapisz notatkę: …" saves the learner's text. After a
     mnemonic the coach offers to save it and saves it only after "tak".
   - The terminal: the command `/notatka text` saves a note for the previous
     card.
   - `doctor --merge` joins conflict copies of the notes file as it does
     for the log, and `PRIVACY` names the notes among the data in the
     learner's folder.

#### Files

| Layer | Files |
|---|---|
| engine | `store.py` (plan settings, the notes file, the mark `skip`), `session.py` (`reveal`, `self_grade`, the field `back`, the note in results), `plans.py`, `progress.py` (`skipped` in `status`), `doctor.py`, `cli.py` (`note`, `flag --skip`), `data/i18n/pl.json` |
| terminal | `drill.py` (an empty Enter in the mode `self`, `/t`, `/pomin`, `/notatka`) |
| server | `server/app.py` (`vocab_note`, `vocab_flag` with `skip`, the card with `vocab_reveal`), `server/static/card.html`, `server/guides/session.md`, `coach.md`, `start.md`, `rules.md` |
| plugin | `rules/02-answer-after-grade.md`, `rules/03-engine-grades.md`, `vocab-session` (`SKILL.md`, `reference/`), `vocab-coach`, `vocab-start/reference/plan-keys.md`, the files generated by `scripts/build.py skills` |
| documents | `README`, `QUICKSTART`, `docs/server`, `docs/pilot`, `plugin/PRIVACY`, `CHANGELOG`, this plan; every document in English and in Polish |
| tests | `tests/test_engine.py`, `test_cli.py`, `test_drill.py`, `test_server.py`, the session `sessions/session-self-assessment.json` for `session_test.py --check` |

#### Order of work in the session

1. The engine and the commands for the five points, with tests of each.
2. The terminal.
3. The server, the card, the guides, the rules and the skills;
   `build.py skills` and the validations.
4. A simulation through the commands on the full courses, and a preview of
   the card in the test host in the light and the dark theme.
5. The documents, the plan, the project memory and a local commit.
6. With your separate approval: a simulation with a model, the release
   `v1.0.0-rc.9` and the deployment.

#### Completion criteria

| Criterion | Check |
|---|---|
| the mode `type` keeps today's guarantees | tests of the refusals `reveal_production` and `production_needs_answer`; the session test of the answer leak unchanged |
| the mode `self` saves the learner's grade | a test: `reveal`, then `grade`, a row without `auto`, the date as for the same grade of the engine |
| an answer appears only after a grade or after `reveal` | the simulation: no `next` holds a word or a note |
| a word put aside and brought back | a test: the card leaves the queue and the drill, `status` lists it, `--clear` brings it back with its date |
| a note | a test: saving, changing, removing, present in the result and in `lookup`, absent from the question, a conflict copy joined |
| the field `back` | a test: the same texts in the command's result, in the terminal and in the card |
| checks of the repository | `ruff`, `mypy`, `pytest` on Python 3.15 and 3.10, `validate.py`, `session_test.py --check`, `claude plugin validate --strict` |

#### Costs and decisions

| Item | Cost | Approval |
|---|---|---|
| implementation, tests, the simulation through the commands | no model costs | acceptance of the stage |
| a simulation of the session with a model through a local server | an estimate of 1–2 USD (Sonnet in Claude Code, a limit of 2 USD) | separate |
| push, tag, release on GitHub, PyPI, deployment | none | separate for every step |

Decisions at acceptance: the default of `sentence_translation` (`shown` as
proposed) and the default of `answer_mode` (`type` as proposed).

#### Result of Stage 11 (16.11.2026)

| Criterion | Result |
|---|---|
| self-assessment | `answer_mode=self`: `reveal` shows the word of a production card waiting today with its phase, the grades to choose from (two in the drill) and the day's counter, `grade` saves the learner's grade without `auto`; the date is the same as after the same grade of the engine; with `answer_mode=type` both refusals work as before, and their messages name the setting |
| the sentence's translation | `sentence_translation=hidden`: the card shows a "Tłumaczenie" button under every sentence, the chat gives the translation on "tłumaczenie", the terminal on `/t` at a question and the key `t` at an introduction |
| the review date | the field `back` in the result of an answer with a text from the common section `back` of `pl.json`; the terminal, the card and the chat show the same text; `next_review=hidden` leaves the field out |
| settings in the results | `view` in the results of `next`, `answer`, `grade`, `reveal` and `today` (`new_words`, `answer_mode`, `sentence_translation`, `next_review`) |
| a word put aside | `flag --skip` and `vocab_flag` with `skip`; the word leaves the queue, the drill and the choice of new words, `status` gives `skipped` apart from `reported`, `--clear` brings the word back with its date; the terminal has `/pomin` |
| a note | `note --card ID --stdin` and `vocab_note` (23 tools); `log/notes.jsonl` only grows and the last row of an entry holds; the note comes back in the result of an answer, in `reveal` and in `lookup`, never in `next`; the terminal has `/notatka`, the coach offers to save a mnemonic and saves it after "tak"; the rule about approval covers notes |
| a fault found by the tests | `doctor --merge` did not join conflict copies of the notes; it now joins them with the log and the reports, and puts the rows of the reports and the notes in the order of time, since the last row of an entry holds |
| guides and rules | the guide `session`, the skill `vocab-session` with an example of "pokaż", `coach`, `words`, `start` and `plan-keys`; the rules about the answer after the grade, the engine's grade and approval, with their copy in the server's `rules` guide |
| tests | 268 on Python 3.15 and 240 on Python 3.10 (1 skipped without wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (8 of 8, the new session `session-self-assessment`) and `claude plugin validate --strict` without remarks; new tests of the engine, the commands, the terminal and the server for each of the five points |
| simulation through the commands | the full courses (de A1–A2, es A1, it A1, 15 new words a day), three days of learning with self-assessment, the translation on request and notes, then a day with the date kept back: 6140 checks without a fault in 199 answers (66 grades of the learner in every variant, 29 notes, 11 words put aside); no `next` held a word or a note, and an answer outside today's session was refused |
| preview of the card | the test host in Edge in the light and the dark theme: a question with the translation kept back, the answer after "pokaż" with a note and three grades, in the drill with two, a result with its return date |
| simulation with a model | a local server and Claude Code with the Sonnet model, a plan with `answer_mode=self` and `sentence_translation=hidden`, 8 turns for 1.32 USD (a limit of 2 USD): a question without its translation and with the hint "pokaż", "tłumaczenie" given from the same result without a tool call, "pokaż" (`vocab_reveal`) with the full answer and the question about the grade, "prawie" passed as given to `vocab_grade` (a row without `auto`) with "wróci dziś w utrwalaniu", a note through `vocab_note`, a typed answer through `vocab_answer` with "wróci za 2 dni", "nie chcę tego słowa" (`vocab_flag` with `skip`) without showing the answer, and the word brought back named by its Polish meaning; the one fault: after bringing the word back the model showed the counter from before the change, since the result of `vocab_flag` had no counter; the result of `flag` now holds the day's counter after the change |
| release and deployment | with your approval of 16.11.2026: the tag `v1.0.0-rc.9`, a pre-release on GitHub with all 9 packages, `vocabbot 1.0.0rc9` on PyPI through trusted publishing with sums matching GitHub, CI green, the plugin in your Codex refreshed to rc.9; server 1.0.0rc9 at `https://vocab.archxs.com`, a read-only smoke test with a short-lived token of the test account, revoked after the test: 23 tools with `vocab_note`, the card on six tools (with `vocab_reveal`), `view` in `vocab_today`, the refusal `reveal_production` with `answer_mode=type`, a recording and an example in `vocab_lookup` |
| to check | a session from your account in Claude and ChatGPT after changing the plan to `answer_mode=self` and `sentence_translation=hidden`: "pokaż", the "Tłumaczenie" button in the card, "nie chcę tego słowa", "zapisz notatkę: …" |

#### A change of the defaults (16.11.2026, at your suggestion)

After the release of rc.9 you suggested turning the new possibilities on by
default. The defaults are now `answer_mode=self` and
`sentence_translation=hidden`, as in the SuperMemo course of your screenshot,
which has the "Check" button and three grades without an input field. Typing
stays, and the engine still grades a typed word. "pokaż" takes two messages
a card in a text chat instead of one, and a request for the translation one
message more; the card in the chat window shows the translation with a button
without the model. At the start of a session the model names "pokaż" and
"tłumaczenie", since nothing else tells about them in a text chat. A plan
saved before rc.9 gets the new defaults; on the server this covers both
accounts, since no plan saved these settings under rc.9. The tests that
assume typing now set it explicitly, and the tests of the default plan check
the new behaviour.

#### Out of scope until trials

| Topic | Confirmation missing |
|---|---|
| an interactive card (an answer field and buttons that call the server without the model) | your check that today's card shows in Claude and ChatGPT on a computer and on a phone; a trial whether these applications let a card call the server's tools |
| a second sentence, collocations, recordings of sentences | a count of the coverage in the sources (Wiktionary, Tatoeba) and of the recordings' licences; an estimate of a model run before it starts |
| images with the entries | a trial of how well images match on a sample of entries |
| a week's summary and a calendar of reviews as screens | I know these screens of the SuperMemo application only from descriptions |
| an own session page at `vocab.archxs.com` | the result of the card trials; a separate, larger stage |

---

## 11. Completeness check

### 11.1 Features of the SuperMemo courses

| Feature | Version 1.0 | How |
|---|---|---|
| A vocabulary course by frequency with CEFR levels | yes | A1–A2 and B1–B2 courses, ordered by frequency |
| A word page: meaning, example, pronunciation | yes | the Polish meaning, a sentence with a gap, IPA |
| Three grades | yes | `know`, `almost`, `dont_know`; two grades in the drill (Stage 10) |
| Learning, reviews, drill | yes | three stages of the day in this order, with the learner's choice of stage, more new words and more rounds of reviews (Stage 10) |
| A review at a recall of about 90% | yes | FSRS-6, the recall in the plan, the spread of due dates, initial intervals fitted to the log, the full fit of a language after a win in `replay`, due dates by presence |
| Skipping known words | yes | the grade "known" and the placement test |
| Cards a day, the length of the course | yes | `plan`, `forecast` |
| A calendar with days off | yes | `days_off` |
| Reviews mixed from several courses | yes | the default setting with the rules for card families |
| Learning statistics | yes | `status` |
| A conversation with an assistant on the learned vocabulary | yes | `vocab-coach` |
| Synchronisation between computers | yes | the learner's folder on a synced drive, merging logs in `doctor` |
| Images, recordings, speech recognition | after 1.0 | section 14 |
| A phone app | after 1.0 | section 14 |

Features beyond the SuperMemo courses: language weights, the gap between
languages for one concept, detection of an answer in another language, lists
of words confused between languages, own words from any text.

### 11.2 Levels of verification

| Level | Scope | Tool |
|---|---|---|
| 1. Structure | package, manifests, skills, courses | `ruff`, `mypy`, `scripts/validate.py`, `vocabbot course check`, `claude plugin validate` |
| 2. Arithmetic | schedule, queue, grading, gate, replay | `pytest`, the `fsrs` library as the reference |
| 3. Behaviour | the skills in multi-turn sessions on a trial folder | `scripts/session_test.py` with `claude -p`, after your consent |
| 4. Use | daily learning | the pilot |

---

## 12. Costs and consents

| Item | Model cost | Consent |
|---|---|---|
| Stage 1 | none | acceptance of the plan |
| Stage 2, the pipeline and the sample review | none | acceptance of the plan |
| Stage 2, the batch run through the API | an estimate before the run | separate, only at the decision point |
| Stage 3, session tests with `claude -p` | an estimated 3–6 USD with Claude Sonnet 5.5 (7 sessions, 13 turns) | separate |
| Stage 4, editing of the basic words | none | approved on 15.11.2026 |
| Stage 4, review of the examples through the Message Batches API | up to 8 USD with Claude Sonnet 5.5 | approved on 15.11.2026 |
| Stage 4, session tests on version rc.3 | an estimated 3–6 USD with Claude Sonnet 5.5 | separate |
| Stage 5, a schedule fitted to the learner | none | acceptance of the stage |
| Stage 6, the server for chat applications | none | acceptance of the stage on 15.11.2026 |
| Stage 6, a session test with a model through the connector | 1.54 USD with Claude Sonnet 5.5 (estimate 1–3 USD) | approved on 15.11.2026 |
| Stage 6, the deployment on the VPS | no model costs | approved on 15.11.2026 |
| Stage 7, the review of the Italian meanings and examples | 3.54 USD with Claude Sonnet 5.5 (limit 7 USD) | approved on 15.11.2026 |
| Stage 8, example sentences from the model for 10,738 entries | 8.32 USD with Claude Sonnet 5.5 (sample 0.09 USD, limit 12 USD) | approved on 16.11.2026 after the sample |
| Stage 8, simulated sessions with the model through a local server | 2.86 USD (9 and 6 turns, the Sonnet model in Claude Code) | within the request of 16.11.2026 |
| Stage 10, a simulation of the session with a model through a local server | 1.79 USD (10 turns, the Sonnet model in Claude Code; estimate 1–2 USD) | approved 16.11.2026 |
| Stage 11, a simulation of the session with a model through a local server | 1.32 USD (8 turns, the Sonnet model in Claude Code; a limit of 2 USD) | approved 16.11.2026 |
| GitHub repository, tag, release, PyPI | none | separate for every step |

The name `vocabbot` was free on PyPI and on the `dithiothreitol` GitHub
account on 14.11.2026.

---

## 13. Risks and responses

| Risk | Response |
|---|---|
| The automatic choice of a sense in Wiktionary gives wrong equivalents | an error threshold in the sample, pipeline rules corrected by error class, the `checked` field, `flag` reports, the decision point of Stage 2 |
| The CEFR-J terms do not describe redistribution directly | reading the licence file at the start of Stage 2; a course gives the level as a feature of the concept with a citation of the source; a fallback sets the levels from wordfreq frequency bands |
| Entries with all fields below the thresholds | a coverage report after the first run; additions from the de, es, fr and pl editions of Wiktionary; an update of the thresholds in the plan with your knowledge |
| An older Python in a host's sandbox | code compatible with 3.10, a test in CI, a check of the hosts in Stage 3 |
| Typing diacritics in a terminal | replacement characters in the language rules, "almost" for a missing diacritic, a manual trial in Stage 1 |
| The wordfreq data comes from the period until 2021 | A1–B2 vocabulary changes slowly; frequency serves only the order |
| The model in the chat gives the answer away | `next` without the answer, rule 1, a session test of this rule |
| A public server attracts unwanted accounts and sign-in attempts | accounts only with an invitation code, a limit of failed attempts, passwords in scrypt, tokens as hashes, redirects from a list of allowed addresses |
| ChatGPT on the Plus and Pro plans gives custom connectors read access only | Claude as the first application of the pilot; on 16.11.2026 the pilot learner's account in ChatGPT saved the plan and 18 answers through the server added under Plugins |
| A sentence written by the model has a mistake or another meaning of the word | the example review as for Tatoeba sentences, a sample of 40 entries before the full run, the source `generated` in the entry, `flag` reports |
| A recording on Commons is renamed or removed | the names are refreshed at every course build; an entry without a recording shows the IPA alone |

---

## 14. Extensions after version 1.0

- Pronunciation in the terminal session (playing recordings and the speech
  synthesis of the operating system); Stage 8 covers recordings in the chat,
  Stage 9 a card that plays them.
- A session on a phone outside chat applications: a page in the home network
  or on the server of Stage 6, using the same learner's folder.
- More languages to learn and English as a second base language.
- Recognition cards and sentence cards as the default for B1–B2.
- Images for entries from open collections.

---

## Sources

- SuperMemo, course catalog: https://www.supermemo.com/pl/catalog
- SuperMemo, Extreme English Basic: https://supermemo.com/en/courses/extreme-english-1
- SuperMemo, the method: https://www.supermemo.com/en/supermemo-method
- SuperMemo, the review section and three grades: https://supermemo.com/blog/repeat-section-and-3-buttons-assessment
- SuperMemo, mixed repetitions: https://www.supermemo.com/en/faq/mixed-repetitions
- SuperMemo, learning plan: https://www.supermemo.com/en/faq/learning-plan
- SuperMemo, repetitions and drills: https://www.supermemo.com/en/faq/repetitions-and-drills
- SuperMemo, first steps with a course: https://www.supermemo.com/en/blog/how-to-start-learning-with-a-course-5-easy-steps
- SuperMemo, keyboard shortcuts: https://www.supermemo.com/en/faq/which-keyboard-shortcuts-can-i-use-in-supermemo
- SuperMemo, cards a day: https://www.supermemo.com/en/blog/customize-your-learning-with-supermemo
- SuperMemo, repetition limit: https://www.supermemo.com/en/faq/repetition-limit
- SuperMemo, order of repetitions: https://www.supermemo.com/en/blog/new-at-supermemo-sort-your-repetitions
- SuperMemo, how to learn: https://www.supermemo.com/en/blog/how-to-learn-with-supermemo
- SuperMemo for Windows, glossary (Final drill, Mid-interval repetition): https://www.super-memory.com/help/g.htm
- FSRS, description of the algorithm: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
- py-fsrs: https://github.com/open-spaced-repetition/py-fsrs
- kaikki.org, Wiktionary data: https://kaikki.org/dictionary/rawdata.html
- CEFR-J Vocabulary Profile: https://github.com/openlanguageprofiles/olp-en-cefrj
- Tatoeba, downloads: https://tatoeba.org/downloads
- MCP, authorization: https://modelcontextprotocol.io/specification/draft/basic/authorization
- The MCP SDK for Python: https://github.com/modelcontextprotocol/python-sdk
- Anthropic, custom connectors using remote MCP: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Anthropic, building custom connectors: https://support.anthropic.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers
- OpenAI, authentication in the Apps SDK: https://developers.openai.com/apps-sdk/build/auth
- OpenAI, developer mode and MCP apps: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- fsrs-rs: https://docs.rs/fsrs/
- Benchmark of spaced-repetition algorithms: https://github.com/open-spaced-repetition/srs-benchmark and https://expertium.github.io/Benchmark.html
- FSRS Helper (Easy Days, load balancing): https://github.com/open-spaced-repetition/fsrs4anki-helper
- Waisman Center, interleaving languages: https://www.waisman.wisc.edu/?p=36980
- MPI Nijmegen, "New in, old out": https://forms.mpi.nl/node/55663
- Bartolotti and Marian, learning a third language: https://bilingualism.northwestern.edu/wp-content/uploads/2018/05/BartolottiMarian2018.pdf
- Anthropic, code execution tool (Python 3.11.12): https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
- Simon Willison, the Cowork environment (Python 3.10.12, Ubuntu 22.04): https://gist.github.com/simonw/35732f187edbe4fbd0bf976d013f22c8
