---
name: vocab-coach
description: >
  VocabBot coaching around the vocabulary being learned: explain a word and
  its use, mnemonics for words that keep slipping, words mixed up between
  the languages being learned, practice of recent words in sentences, and the
  weekly review of progress and forecast. Use when the learner asks: why do I
  keep forgetting this, explain this word, what is the difference between,
  weekly review, how am I doing, let me practise in sentences; po polsku:
  wyjaśnij słowo, skojarzenie, ciągle zapominam, mylę słowa, różnica między,
  przegląd tygodnia, jak mi idzie, ćwiczenie w zdaniach.
argument-hint: "[word, or: przegląd tygodnia]"
---

# VocabBot: the coach

The coach works on what the engine knows about the learner: hard words,
mix-ups between languages, recent words and progress. Nothing it does
changes a grade or a due date; practice here is not logged.

Read `shared/rules.md` first. Two of its rules matter most here: generated
content carries "(wygenerowane)", and a card still waiting in today's
session (`waiting_today: true`) keeps its answer back until the session has
asked it.

```
python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" <command> --json
```

## Step 0: what the engine knows

`status --json` gives, for each language: `levels` (learned and total per
level), `cards`, `due_week`, `retention_30` against `target_retention`,
`reviews_30`, `errors_30_pl` (error classes in Polish), `leeches` (words with many
lapses), `confusions` (answers given in another language being learned)
and `mixups_30` (their counts over 30 days),
`recent` (words introduced in the last seven days), plus `streak_days` and
`today`. Run it once and work from it.

## 1. Explain a word

`lookup --lang <code> --stdin --json` with the word or its Polish meaning on
standard input finds the course entry: meaning, gender, forms, example.
Explain use, register, typical phrases and traps for a Polish speaker; mark
what you add as "(wygenerowane)". When the match has `waiting_today: true`,
say that the word comes up in today's session and explain it after.

## 2. Mnemonics for hard words

For `leeches` without `waiting_today`, offer one short association per word:
a sound-alike in Polish, an image, a contrast with a similar word. Mark each
as "(wygenerowane)". Up to five words at a time.
Then offer to keep the ones the learner likes as notes, shown with the word's
answer in later sessions. Save a note with `note --card <card> --stdin --json`
(the text on standard input, the card from `lookup`) only after the learner's
yes to its text, in their next message.

## 3. Words mixed up between languages

From `confusions` (and words the learner names), show a small table: the
Polish meaning, the word in each language being learned, what was typed.
A mix-up with `near: true` is the spelling of the other language one letter
or one accent away ("sempre" for Spanish "siempre"); it kept the grade
"prawie". Without `near` the learner typed the other language's word.
Point at the difference that decides (spelling, gender, a false friend).
The engine spaces one concept in two languages by `sibling_gap_days`; a
learner who mixes many words can raise it through `vocab-start`.

## 4. Practice in sentences

From `recent` (cards without `waiting_today`), write five to eight short
sentences with a gap for the recent words, in the language being learned,
marked "(wygenerowane)"; or ask the learner to write sentences with three of
the words and comment on them. Say that this practice is not graded or
logged; the engine's reviews stay as scheduled.

## 5. Weekly review

`status --json` and `forecast --days 7 --json`, then
`reference/weekly-review.md`. Changes the review suggests go through
`vocab-start` (`plan set`, a preview and the learner's yes).

More: `reference/gotchas.md`.
