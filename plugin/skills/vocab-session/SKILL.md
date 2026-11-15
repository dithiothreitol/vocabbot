---
name: vocab-session
description: >
  The daily VocabBot vocabulary session in the chat: reviews due today, new
  words and the drill of words that went wrong, one card at a time as in
  SuperMemo (or a few at once, as the learner sets it), in one to three
  languages (English, German, Spanish, French). The engine grades every
  typed answer and sets every due date. Use when the learner says: let's
  learn, daily session, review my words, next words, vocabulary practice;
  po polsku: sesja, codzienna sesja, powtórki, uczymy się, nowe słówka,
  dalej, zaczynamy naukę słówek.
argument-hint: "[cards per message]"
---

# VocabBot: the daily session

The session runs in the engine's order: reviews due today, then new words,
then the drill of cards answered wrong. This skill shows the cards and passes
the learner's answers to the engine, which grades them and schedules the next
review.

Read `shared/rules.md` before the first card. It says how to call the engine
and holds the rules every VocabBot skill keeps; the most important here: the
answer comes after the grade, the engine grades, numbers come from the engine.

```
python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" <command> --json
```

## Step 0: the day

Run `today --json`.

- `error.code` is `no_learner` or `no_plan`: VocabBot is not set up for this
  learner. Offer the setup (`vocab-start`), or pass `--learner <folder>` once
  the learner names the folder.
- `off: true`: a day off; the reviews wait for the next learning day. When
  the learner wants to learn anyway, `today --extra <n> --json` adds new
  words for today, and `next --ahead 10 --json` brings reviews of
  later days (answers to cards with `phase: ahead` go to `answer` with
  `--ahead`). A learner without learned words has no reviews to bring ahead.
- `warnings` with `conflict_copies` or `damaged_rows`: say that `vocab-start`
  checks and repairs the folder; the session can go on.
- `paced`: the engine gives fewer new words today (`today` instead of
  `planned`) so that the day fits the learner's usual minutes; say so in one
  sentence.
- `ahead_hint`: tomorrow is a day off or a day the learner usually skips.
  After today's cards, offer its `count` reviews ahead of their day:
  `next --count <count> --ahead <count> --json`, answered with `--ahead`.

Show the day in two or three lines from `languages` (reviews, new words,
drill per language) and `minutes`.

## Step 1: the cards

`batch` in the result of `today` is the number of cards in one message: 1 by
default, so the session asks one card at a time, as SuperMemo does. A learner
who prefers a list changes it through `vocab-start` (`plan set batch=5`).

Run `next --json`; it returns `batch` items. Keep their order. Each item has
`card`, `lang`, `phase` (`review`, `new`, `drill`, `ahead`) and `question`; a
new word also has `word`. `reference/presentation.md` shows the layout.

- **A question** shows the language tag (EN, DE, ES, FR), the Polish meaning,
  the part of speech, "z rodzajnikiem" when `with_article` is true, the hint
  if any, and the sentence with its gap `___` and `sentence_pl`. Recognition
  cards (`question.ask: meaning`) follow `reference/recognition.md`.
- **A new word** (`phase: new`) is introduced before its question: `word`
  with its gender, forms and IPA, the Polish meaning, and the example with
  its translation. End the message there; its question comes in the next
  message, after the learner says they are ready, so the answer is not on the
  screen. A learner who knew the word before the course says so, and
  `grade --card <card> --grade known --json` records it; that card then needs
  no question.
- **The answers** go to the engine exactly as typed, an unknown one as an
  empty answer, on standard input, with `--next`, so the result also holds
  the next cards (`next`):

  ```
  python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" answer --batch --stdin --next --json <<'EOF'
  {"card": "de-c01997#p", "answer": "der Hund"}
  EOF
  ```

- **A result** is one line per card: "✓ wiem", "≈ prawie" with the error
  classes in Polish (`errors_pl`), or "✗ nie wiem", then `word.word`; add the
  example for "prawie" and "nie wiem". `other_lang` means the learner typed
  the word of another language being learned: name that language. A result
  with `error` was refused; show its message and go on.

**One card at a time (`batch` 1).** Every message holds the result of the
last answer and then the next card from `next.items` of that result: its
question, or the introduction of a new word. After a new word's
introduction the learner's "dalej" brings its question.

**Several cards (`batch` 2 or more).** Introduce the new words of the batch
together and end the message; then ask every remaining card as one numbered
list. The learner answers by number; when the reply does not map clearly onto
the numbers, ask once. Send every answer of the list in one call and show the
results of the list, then the next batch from `next`.

Go on until `left` shows no reviews, no new words and no drill. Cards
answered wrong come back in the "utrwalanie" (the drill) at the end, as many
times as needed; their due date no longer changes that day.

## Step 2: the end

Run `today --json` and sum up the session from it in two lines. Offer the
coach (`vocab-coach`) for the words that went wrong. Announce the next
session or a reminder only as `shared/rules.md` allows.

## During the session

- **Change of a grade.** Only on the learner's explicit request for a named
  card: `regrade --card <card> --grade know|almost|dont_know --json`.
- **More words today.** `today --extra <n> --json`, then Step 1 again.
- **More or fewer cards in a message.** `vocab-start` changes `batch` in the
  plan with a preview and the learner's yes.
- **A mistake in a card.** The learner's note goes to
  `flag --card <card> --stdin --json`; the card leaves the queue until
  `flag --card <card> --clear --json`. Larger corrections belong to
  `vocab-words`.
- **A pause.** Every answer is saved at once. The next `next` call continues
  in the same order, in the chat or in the terminal (`vocabbot drill`).

More: `reference/gotchas.md`.
