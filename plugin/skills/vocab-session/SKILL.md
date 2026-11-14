---
name: vocab-session
description: >
  The daily VocabBot vocabulary session in the chat: reviews due today, new
  words in small batches and the drill of words that went wrong, in one to
  three languages (English, German, Spanish, French). The engine grades every
  typed answer and sets every due date. Use when the learner says: let's
  learn, daily session, review my words, next words, vocabulary practice;
  po polsku: sesja, codzienna sesja, powtórki, uczymy się, nowe słówka,
  dalej, zaczynamy naukę słówek.
argument-hint: "[cards per batch]"
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
- `off: true`: a day off; the reviews wait for the next learning day. Learn
  ahead only when the learner asks for it: `next --count 10 --ahead 10`, and
  answers to cards with `phase: ahead` go to `answer` with `--ahead`.
- `warnings` with `conflict_copies` or `damaged_rows`: say that `vocab-start`
  checks and repairs the folder; the session can go on.

Show the day in two or three lines from `languages` (reviews, new words,
drill per language) and `minutes`.

## Step 1: a batch

Run `next --count 10 --json` (or the number the learner chose). Keep the
order of `items`. Each item has `card`, `lang`, `phase` (`review`, `new`,
`drill`, `ahead`) and `question`; a new word also has `word`.

1. **Introduce the new words.** For each item with `phase: new`, show `word`:
   the word with its gender, forms and IPA, the Polish meaning, and the
   example with its translation. Ask the learner to read them. A learner who
   knew a word before the course says so, and
   `grade --card <card> --grade known --json` records it; that word then
   leaves the batch.
2. **Ask the questions.** Ask every remaining item of the batch as one
   numbered list. Per item: the language tag (EN, DE, ES, FR), the Polish
   meaning, the part of speech, "z rodzajnikiem" when `with_article` is true,
   the hint if any, and the sentence with its gap `___` and `sentence_pl`.
   Recognition cards (`question.ask: meaning`) follow
   `reference/recognition.md`. `reference/presentation.md` shows the layout.
3. **Send the answers.** The learner answers by number. When the reply does
   not map clearly onto the numbers, ask once. Send every answer of the batch
   in one call, exactly as typed, on standard input:

   ```
   python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" answer --batch --stdin --json <<'EOF'
   {"card": "de-c01997#p", "answer": "der Hund"}
   {"card": "es-c02790#p", "answer": ""}
   EOF
   ```

4. **Show the results.** One line per card: "✓ wiem", "≈ prawie" with the
   error classes, or "✗ nie wiem", then `word.word`; add the example for
   "prawie" and "nie wiem". `other_lang` means the learner typed the word of
   another language being learned: name that language. A result with `error`
   was refused; show its message and go on.

Repeat Step 1 until `left` in the last result shows no reviews, no new words
and no drill. Cards answered wrong come back in the drill at the end, as many
times as needed; their due date no longer changes that day.

## Step 2: the end

Run `today --json` and sum up the session from it in two lines. Offer the
coach (`vocab-coach`) for the words that went wrong. Announce the next
session or a reminder only as `shared/rules.md` allows.

## During the session

- **Change of a grade.** Only on the learner's explicit request for a named
  card: `regrade --card <card> --grade know|almost|dont_know --json`.
- **More words today.** `today --extra <n> --json`, then Step 1 again.
- **A mistake in a card.** The learner's note goes to
  `flag --card <card> --stdin --json`; the card leaves the queue until
  `flag --card <card> --clear --json`. Larger corrections belong to
  `vocab-words`.
- **A pause.** Every answer is saved at once. The next `next` call continues
  in the same order, in the chat or in the terminal (`vocabbot drill`).

More: `reference/gotchas.md`.
