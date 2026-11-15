# The daily session

The session runs in the engine's order: reviews due today, then new words,
then the drill of cards answered wrong. Show the cards and pass the learner's
answers to the engine, which grades them and schedules the next review.

## Step 0: the day

Call `vocab_today`.

- `error.code` is `no_account_plan`: offer the setup (`vocab_guide` with the
  topic `start`).
- `off: true`: a day off; the reviews wait for the next learning day. When
  the learner wants to learn anyway, `vocab_add_today` adds new words for
  today, and `vocab_next` with `count` 10 and `ahead` 10 brings
  reviews of later days (answers to cards with `phase: ahead` go to
  `vocab_answer` with `ahead: true`). A learner without learned words has no
  reviews to bring ahead.
- `paced`: the engine gives fewer new words today (`today` instead of
  `planned`) so that the day fits the learner's usual minutes; say so in one
  sentence.
- `ahead_hint`: tomorrow is a day off or a day the learner usually skips.
  After today's cards, offer its `count` reviews ahead of their day:
  `vocab_next` with `count` and `ahead` set to that number, answered with
  `ahead: true`.

Show the day in two or three lines from `languages` (reviews, new words,
drill per language) and `minutes`.

## Step 1: a batch

Call `vocab_next` with `count` 10 (or the number the learner chose; five suit
a phone). Keep the order of `items`. Each item has `card`, `lang`, `phase`
(`review`, `new`, `drill`, `ahead`) and `question`; a new word also has
`word`.

1. **Introduce the new words.** For each item with `phase: new`, show `word`:
   the word with its gender, forms and IPA, the Polish meaning, and the
   example with its translation. Ask the learner to read them and end the
   message there; the questions come in the next message, after the learner
   says they are ready, so the answers are not on the screen. A learner who
   knew a word before the course says so, and `vocab_grade` with `known`
   records it; that word then leaves the batch.
2. **Ask the questions.** Ask every remaining item of the batch as one
   numbered list. Per item: the language tag (EN, DE, ES, FR), the Polish
   meaning, the part of speech, "z rodzajnikiem" when `with_article` is true,
   the hint if any, and the sentence with its gap `___` and `sentence_pl`.
   Recognition cards (`question.ask: meaning`) follow the section below.
3. **Send the answers.** The learner answers by number. When the reply does
   not map clearly onto the numbers, ask once. Send every answer of the batch
   in one `vocab_answer` call, exactly as typed, an unknown one as an empty
   string.
4. **Show the results.** One line per card: "✓ wiem", "≈ prawie" with the
   error classes in Polish (`errors_pl`), or "✗ nie wiem", then `word.word`;
   add the example for "prawie" and "nie wiem". The cards answered wrong come
   back in the "utrwalanie" (the drill) at the end. `other_lang` means the
   learner typed the word of another language being learned: name that
   language. A result with `error` was refused; show its message and go on.

Repeat Step 1 until `left` in the last result shows no reviews, no new words
and no drill. Cards answered wrong come back in the drill at the end, as many
times as needed; their due date no longer changes that day.

## Step 2: the end

Call `vocab_today` and sum up the session from it in two lines. Offer the
coach (`vocab_guide` with the topic `coach`) for the words that went wrong.

## How a batch looks

The examples use invented cards; the real ones come from `vocab_next`.

```
Nowe słowa (3):

DE  der Hund (r.m., l.mn. die Hunde) /hʊnt/ = pies
    Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
ES  la mesa (r.ż., l.mn. las mesas) /ˈme.sa/ = stół
    La mesa es de madera. · Stół jest z drewna.

Przeczytaj je spokojnie. Jeśli któreś słowo było Ci znane przed kursem, napisz które.
```

```
1. DE · pies (rzeczownik, z rodzajnikiem)
   ___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
2. ES · stół (rzeczownik, z rodzajnikiem)
   ___ es de madera. · Stół jest z drewna.

Odpowiedz numerami, np. „1. …”. Gdy nie pamiętasz, wpisz „?”.
```

```
1. ✓ wiem · der Hund
2. ≈ prawie (rodzajnik) · la mesa
   La mesa es de madera. · Stół jest z drewna.
```

The next due date of each card is in the result (`next_due`); show it only
when the learner asks.

## Recognition cards

A plan with `directions` set to `produce,recognize` also has recognition
cards (`<id>#r`): the foreign word is shown and the learner recalls its
meaning.

1. Show `question.word` and `question.sentence`, and ask what the word means.
2. After the learner's attempt (or "pokaż"), call `vocab_reveal` and show
   `word`: the meaning, the forms and the example.
3. Ask for the learner's own grade: wiem, prawie or nie wiem.
4. Record it with `vocab_grade` (`know`, `almost` or `dont_know`).

In a batch with production and recognition cards, send the production
answers with `vocab_answer` first, then go through the recognition cards.

## During the session

- **Change of a grade.** Only on the learner's explicit request for a named
  card: `vocab_regrade`.
- **More words today.** `vocab_add_today`, then Step 1 again.
- **A mistake in a card.** The learner's note goes to `vocab_flag`; the card
  leaves the queue until `vocab_flag` with `clear: true`.
- **A pause.** Every answer is saved at once. The next `vocab_next` continues
  in the same order, in this conversation or in a new one.

## Gotchas

- `vocab_next` returns the same order again until answers come in; calling it
  twice does not skip cards. Ask the cards the last `vocab_next` returned.
- `not_in_today`: the card is not on today's list. More new words come only
  through `vocab_add_today`.
- `not_due`: a review before its day. Accept it only when the learner chose
  to learn ahead (`ahead: true`).
- `known_only_first`: "znałem" works only the first time a word is shown.
- An empty answer is graded "nie wiem" with the error class "brak
  odpowiedzi". The words "nie wiem" typed as an answer would be graded as a
  wrong word, so send an empty answer.
- With `diacritics: lenient` in the plan, a missing diacritic does not lower
  the grade.
