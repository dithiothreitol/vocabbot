# VocabBot

**English** · [Polski](README.pl.md)

VocabBot teaches vocabulary in one, two or three languages at once: English,
German, Spanish and French, from A1 to B2, for learners whose base language
is Polish. New words come in order of frequency, every typed answer is graded
by the engine, and every card comes back on the day the FSRS-6 scheduler sets
for it, when about nine in ten words are still remembered.

## Skills

| Skill | What it does |
|---|---|
| `vocab-start` | Setup: languages, levels, new words a day, a placement test, the learner's folder. Later: plan changes, the forecast, a check of the folder, the terminal program. |
| `vocab-session` | The daily session: reviews, new words and the drill of words that went wrong, one card at a time as in SuperMemo (or a few at once, by the plan's `batch`). |
| `vocab-coach` | Explanations, mnemonics for hard words, words mixed up between languages, practice in sentences, the weekly review. |
| `vocab-words` | Own words from a text, a list or a photo of a page; course words moved forward; reports of mistakes in entries. |

## Install

Claude Code:

```
/plugin install vocabbot --marketplace dithiothreitol/vocabbot
```

or in two steps: `/plugin marketplace add dithiothreitol/vocabbot`, then
`/plugin install vocabbot@vocabbot`. Then say "skonfiguruj VocabBota" or
type `/vocabbot:vocab-start`.

Codex CLI:

```
codex plugin marketplace add dithiothreitol/vocabbot
codex plugin add vocabbot@vocabbot
```

## Requirements

Python 3.10 or later on the computer, or in the host's sandbox. Each skill
carries the engine and all courses in one file, `bin/vocabbot.pyz`, which
needs no other package.

## Confirmations

Every change of the plan or of own words is shown as a preview first and saved
only after the learner's yes. In Claude Code and Cowork the plugin's hook also
asks in the host's own permission prompt before the engine saves a change.

## The learner's data

The plan, the log of answers and the own words stay in a folder the learner
chooses; [PRIVACY.md](PRIVACY.md) describes what is kept where.

## Licence

The code is licensed under Apache-2.0 ([LICENSE](LICENSE)). The courses are
licensed under CC BY-SA 4.0 and are built from CEFR-J, Wiktionary (through
kaikki.org), wordfreq and Tatoeba; [NOTICE](NOTICE) lists the sources and
their terms.
