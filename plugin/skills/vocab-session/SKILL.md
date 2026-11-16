---
name: vocab-session
description: >
  The daily VocabBot vocabulary session in the chat: reviews due today, new
  words and the drill of words that went wrong, one card at a time as in
  SuperMemo (or a few at once, as the learner sets it), in one to three
  languages (English, German, Spanish, French, Italian). The engine grades every
  typed answer and sets every due date. Use when the learner says: let's
  learn, daily session, review my words, next words, vocabulary practice;
  po polsku: sesja, codzienna sesja, powtórki, uczymy się, nowe słówka,
  dalej, zaczynamy naukę słówek.
argument-hint: "[cards per message]"
---

# VocabBot: the daily session

The day has three stages, as in SuperMemo: the reviews due today, the new
words, and the drill of cards answered wrong. The session takes them in this
order, and the learner may choose another one at any moment: move to the new
words while reviews wait, go back to the reviews, learn more new words than
the day's number, and start the next round of reviews. This skill shows the
cards and passes the learner's answers to the engine, which grades them and
schedules the next review.

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
  the learner wants to learn anyway, `today --reviews <n> --next --json`
  brings the reviews (the due ones first) and `today --extra <n> --next
  --json` new words.
- `warnings` with `conflict_copies` or `damaged_rows`: say that `vocab-start`
  checks and repairs the folder; the session can go on.
- `paced`: the engine gives fewer new words today (`today` instead of
  `planned`) so that the day fits the learner's usual minutes; say so in one
  sentence.
- `ahead_hint`: tomorrow is a day off or a day the learner usually skips.
  After today's cards, offer its `count` reviews ahead of their day:
  `today --reviews <count> --next --json`.

Show the day in two or three lines from `languages` (reviews, new words,
drill per language) and `minutes`. Then start with the stage the learner
named ("nowe słówka", "tylko powtórki"), or with the reviews, and say once in
one line that the learner chooses: „nowe” moves to the new words, „powtórki”
back to the reviews, „więcej słów” adds new words; with
`view.answer_mode: self` also „pokaż” (the answer for the learner's own
grade), and with `view.sentence_translation: hidden` also „tłumaczenie”.

## Step 1: the cards

`batch` in the result of `today` is the number of cards in one message: 1 by
default, so the session asks one card at a time, as SuperMemo does. A learner
who prefers a list changes it through `vocab-start` (`plan set batch=5`).

Run `next --json`; it returns `batch` items. Keep their order. Each item has
`card`, `lang`, `phase` (`review`, `new`, `drill`, `ahead`) and `question`.
`new_words` in the result of `today` says how new words come: `ask` (the
default) or `show`. `view` in every result of the session holds the plan's settings of how a card is shown: `new_words`, `answer_mode` (`type` or `self`), `sentence_translation` (`shown` or `hidden`) and `next_review` (`shown` or `hidden`). `reference/presentation.md` shows the layout.

- **The counter.** Every result of `next`, `answer`, `grade` and `regrade`
  holds `counter`, the line of the day's progress ("Postęp: 6/25 · nowe 3/15
  · powtórki 3/10"). Start every message of the session with the `counter` of
  the latest result, as it is.

- **A question** shows the language tag (EN, DE, ES, FR, IT), the Polish meaning,
  the part of speech, "z rodzajnikiem" when `with_article` is true, the hint
  if any, and the sentence with its gap `___` and `sentence_pl`. With
  `view.sentence_translation: hidden` every sentence comes without its
  translation, as in SuperMemo; when the learner asks for it ("tłumaczenie"),
  the next message gives it from the same result. With
  `view.answer_mode: self` a question ends with "Wpisz słowo albo napisz
  „pokaż”.". Recognition cards (`question.ask: meaning`) follow `reference/recognition.md`.
- **A new word** (`phase: new`) is asked at once, as any card, under the
  label "Nowe słowo": this is how SuperMemo introduces a word, and the plan's
  default (`new_words: ask`). The learner types the word, or "?" when it is
  not known yet, which goes to the engine as an empty answer. The result is
  the learner's first contact with the word, so show it in full for every
  grade: `word.word` with its gender, forms and IPA, the link to its
  recording when `word.audio` is there (a Markdown link with the text
  "🔊 wymowa" to `word.audio`), the Polish meaning, and the example with its
  translation. A right first answer comes back with the grade `known`: the
  learner knew the word before the course, so write "✓ znane wcześniej", and
  the engine adds one more new word in its place. A missed word comes back
  the same day in the drill.
  A learner who says "znałem" instead of answering gets the same through
  `grade --card <card> --grade known --next --json`.
- **A new word shown first** (`new_words: show`; the item holds `word`): show
  the word in full as above and end the message there; its question comes in
  the next message, after the learner says "dalej", so the answer is not on
  the screen. "znałem" goes to `grade --card <card> --grade known --next
  --json`, and that card needs no question.
- **A level set too low.** A result of `grade` with `level_hint` means that
  most of the learner's last new words (`known` of `of`) were known before the
  course. Say so in one sentence and offer, once, the placement test or the
  levels in `suggested` (`vocab-start`, `plan set <setting>` with its preview
  and the learner's yes). The session goes on with the next card.
- **The answers** go to the engine exactly as typed, an unknown one as an
  empty answer, on standard input, with `--next`, so the result also holds
  the next cards (`next`):

  ```
  python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" answer --batch --stdin --next --json <<'EOF'
  {"card": "de-c01997#p", "answer": "der Hund"}
  EOF
  ```
- **Show the answer** (`view.answer_mode: self`), as SuperMemo's "Check"
  does. When the learner says "pokaż" or "sprawdź" instead of an answer,
  run `reveal --card <card> --json` and show its `word` in full, as a result shows it, with the
  learner's note, then ask for the grade with the names in `grades`: wiem,
  prawie or nie wiem, and in the drill wiem or nie wiem. The learner's reply
  goes to `grade --card <card> --grade <grade> --next --json`, exactly as given: never propose a grade. A first "wiem"
  for a new word comes back as `known`, as a right first answer does. A typed
  word still goes to `answer`, and "?" stays an empty answer.

- **A result** is one line per card: "✓ wiem", "≈ prawie" with the error
  classes in Polish (`errors_pl`), or "✗ nie wiem", then `word.word`; for
  "prawie" and "nie wiem" add the IPA, the recording link and the example.
  In the drill the engine has two grades, as SuperMemo does: "✓ wiem" takes
  the card out, and every other answer is "✗ nie wiem" with its error
  classes and stays.
  End the line with `back` when the result holds it ("wróci za 4 dni"). A
  learner's note (`word.note`) follows the word as "Notatka: …".
  `other_lang` means the learner typed the word of another language being
  learned: name that language. A result with `error` was refused; show its
  message and go on.

**One card at a time (`batch` 1).** Every message holds the result of the
last answer and then the next card from `next.items` of that result: its
question. With `new_words: show` a new word's introduction takes a message
of its own, and the learner's "dalej" brings its question.

**Several cards (`batch` 2 or more).** Ask the cards as one numbered list;
with `new_words: show` introduce the new words of the batch together first
and end the message. The learner answers by number; when the reply does not map clearly onto
the numbers, ask once. Send every answer of the list in one call and show the
results of the list, then the next batch from `next`.

Go on until `left` shows no reviews, no new words and no drill, or until the
learner ends the session. Cards answered wrong come back in the "utrwalanie"
(the drill) at the end, as many times as needed; their due date no longer
changes that day.

## The stages and more cards

The learner decides what to learn and how much, at any moment of the session.

- **The stage.** `stage` in a result of `next`, and in `next` of an answer,
  names the stage of the cards returned: `reviews`, `new` or `drill`.
- **A change of stage.** When the learner asks for the new words, the reviews
  or the drill ("nowe", "pomiń powtórki", "przejdź do nauki", "wróć do
  powtórek", "utrwalanie"), run `next --stage new|reviews|drill --json` and
  go on from its cards. The card that was on screen waits in its own stage,
  unanswered. A message that names a stage is a request, never an answer to
  the card.
- **Staying in the stage.** `--next` returns the next cards of the stage the
  answered card belongs to, so a learner who chose the new words gets the
  next new word while the reviews wait.
- **A stage ends.** When `next.stage` differs from the stage of the answered
  card, or a result holds `stage_empty`, the stage has no cards left. Say in
  one line what is done and what waits, from `left` ("Nowe słowa na dziś
  zrobione. Czekają powtórki: 12."), then show the card returned. Reviews the
  learner leaves undone stay due and come first on the next day.
- **More new words.** The day's number of new words is a start, never a
  limit. When the learner asks for more ("więcej słów", "kolejne słowa",
  "jeszcze 10"), run `today --extra <n> --next --json`: the number the
  learner names, 5 otherwise. `more.new` in the latest result says how many
  the course still has.
- **The next round of reviews.** When the learner asks for more reviews
  ("jeszcze powtórki", "następna tura"), run
  `today --reviews <n> --next --json`: the number the learner names, 10
  otherwise. The engine takes the due reviews outside today's list first
  (`more.reviews_due`: over the review limit, or on a day off), then the
  cards with the nearest later dates (`more.reviews_ahead`), from the state
  after today's answers. These come with `phase: ahead` and are asked as any
  review; the engine counts the shorter gap when it sets the next date.
- The result of `today --extra` or `today --reviews` holds `added` (the cards
  that joined) and `next` with the first of them. `added` with 0 means
  nothing more is there: every word already has today's answer, or the
  levels have no more words.

## Step 2: the end

Run `today --json` and sum up the session from it: the `counter`, then the
new words of the day from `learned_today` (word and meaning, "znane
wcześniej" for `known`). Then offer, in one line, what `more` allows: more
new words, the next round of reviews, or the end; the learner's choice goes
to `today --extra` or `today --reviews` and the session goes on with Step 1.
Offer the coach (`vocab-coach`) for the words that went wrong. Announce the
next session or a reminder only as `shared/rules.md` allows.

## During the session

- **Change of a grade.** Only on the learner's explicit request for a named
  card: `regrade --card <card> --grade know|almost|dont_know --json`.
- **Another stage, more words, more reviews.** The section "The stages and
  more cards".
- **More or fewer cards in a message.** `vocab-start` changes `batch` in the
  plan with a preview and the learner's yes.
- **A mistake in a card.** The learner's note goes to
  `flag --card <card> --stdin --json`; the card leaves the queue until
  `flag --card <card> --clear --json`. Larger corrections belong to
  `vocab-words`.
- **A word the learner does not want.** "nie chcę tego słowa", "pomiń to
  słowo": `flag --card <card> --skip --json`, without showing the word, then
  `next --stage <stage of that card> --json`. The word stays away until the
  learner asks for it back ("przywróć słowo …"): `lookup` finds its card, and
  `flag --card <card> --clear --json` brings it back with its date. The
  result of `flag` holds the day's `counter` after the change.
  `status --json` lists the words put aside (`skipped`).
- **A note.** "zapisz notatkę: …" saves the learner's text as written with
  `note --card <card> --stdin --json` (the text on standard input) for the
  card of the last result, or the card `lookup` finds. The note comes with
  the word's answer and never with its question.
- **A pause.** Every answer is saved at once. The next `next` call continues
  in the same order, in the chat or in the terminal (`vocabbot drill`).

More: `reference/gotchas.md`.
