# The daily session

The day has three stages, as in SuperMemo: the reviews due today, the new
words, and the drill of cards answered wrong. The session takes them in this
order, and the learner may choose another one at any moment: move to the new
words while reviews wait, go back to the reviews, learn more new words than
the day's number, and start the next round of reviews. Show the cards and
pass the learner's answers to the engine, which grades them and schedules the
next review.

## Step 0: the day

Call `vocab_today`.

- `error.code` is `no_account_plan`: offer the setup (`vocab_guide` with the
  topic `start`).
- `off: true`: a day off; the reviews wait for the next learning day. When
  the learner wants to learn anyway, `vocab_add_today` brings the cards:
  `reviews` for the reviews (the due ones first), `count` for new words.
- `paced`: the engine gives fewer new words today (`today` instead of
  `planned`) so that the day fits the learner's usual minutes; say so in one
  sentence.
- `ahead_hint`: tomorrow is a day off or a day the learner usually skips.
  After today's cards, offer its `count` reviews ahead of their day:
  `vocab_add_today` with `reviews` set to that number.

Show the day in two or three lines from `languages` (reviews, new words,
drill per language) and `minutes`. Then start with the stage the learner
named ("nowe słówka", "tylko powtórki"), or with the reviews, and say once in
one line that the learner chooses: „nowe” moves to the new words, „powtórki”
back to the reviews, „więcej słów” adds new words; with
`view.answer_mode: self` also „pokaż” (the answer for the learner's own
grade), and with `view.sentence_translation: hidden` also „tłumaczenie”.

## Step 1: the cards

`batch` in the result of `vocab_today` is the number of cards in one message:
1 by default, so the session asks one card at a time, as SuperMemo does. A
learner who prefers a list changes it in the plan (`vocab_plan_change` with
`batch=5`, the topic `start`).

Call `vocab_next` without `count`; it returns `batch` items. Keep their order.
Each item has `card`, `lang`, `phase` (`review`, `new`, `drill`, `ahead`) and
`question`. `new_words` in the result of `vocab_today` says how new words
come: `ask` (the default) or `show`.
`view` in every result of the session holds the plan's settings of how a card
is shown: `new_words`, `answer_mode` (`type` or `self`), `sentence_translation`
(`shown` or `hidden`) and `next_review` (`shown` or `hidden`).

- **The counter.** Every result of `vocab_next`, `vocab_answer`, `vocab_grade`
  and `vocab_regrade` holds `counter`, the line of the day's progress
  ("Postęp: 6/25 · nowe 3/15 · powtórki 3/10"). Start every message of the
  session with the `counter` of the latest result, as it is.

- **A question** shows the language tag (EN, DE, ES, FR, IT), the Polish meaning,
  the part of speech, "z rodzajnikiem" when `with_article` is true, the hint
  if any, and the sentence with its gap `___` and `sentence_pl`. With
  `view.sentence_translation: hidden` every sentence comes without its
  translation, as in SuperMemo; when the learner asks for it ("tłumaczenie"),
  the next message gives it from the same result. With
  `view.answer_mode: self` a question ends with "Wpisz słowo albo napisz
  „pokaż”.". Recognition cards (`question.ask: meaning`) follow the section below.
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
  `vocab_grade` with `known` and `then_next: true`.
- **A new word shown first** (`new_words: show`; the item holds `word`): show
  the word in full as above and end the message there; its question comes in
  the next message, after the learner says "dalej", so the answer is not on
  the screen. "znałem" goes to `vocab_grade` with `known`, and that card
  needs no question.
- **A level set too low.** A result of `vocab_grade` with `level_hint` means
  that most of the learner's last new words (`known` of `of`) were known
  before the course. Say so in one sentence and offer, once, the placement
  test or the levels in `suggested` (`vocab_guide` with the topic `start`;
  `vocab_plan_change` with `setting` shows a preview for the learner's yes).
  The session goes on with the next card.
- **The answers** go to `vocab_answer` exactly as typed, an unknown one as an
  empty string, with `then_next: true`, so the result also holds the next
  cards (`next`).
- **Show the answer** (`view.answer_mode: self`), as SuperMemo's "Check"
  does. When the learner says "pokaż" or "sprawdź" instead of an answer,
  call `vocab_reveal` with the card and show its `word` in full, as a result shows it, with the
  learner's note, then ask for the grade with the names in `grades`: wiem,
  prawie or nie wiem, and in the drill wiem or nie wiem. The learner's reply
  goes to `vocab_grade` with that grade and `then_next: true`, exactly as given: never propose a grade. A first "wiem"
  for a new word comes back as `known`, as a right first answer does. A typed
  word still goes to `vocab_answer`, and "?" stays an empty answer.
- **A result** is one line per card: "✓ wiem", "≈ prawie" with the error
  classes in Polish (`errors_pl`), or "✗ nie wiem", then `word.word`; for
  "prawie" and "nie wiem" add the IPA, the recording link and the example.
  In the drill the engine has two grades, as SuperMemo does: "✓ wiem" takes
  the card out, and every other answer is "✗ nie wiem" with its error
  classes and stays.
  End the line with `back` when the result holds it ("wróci za 4 dni"). A
  learner's note (`word.note`) follows the word as "Notatka: …".
  `other_lang` means the learner typed the word of another language being
  learned: name that language. With the grade "prawie" it is the spelling of
  that language one letter or one accent away ("sempre" for "siempre"): say
  so and show the difference. A result with `error` was refused; show its
  message and go on.
  A result of a card learned by families (`together` in the plan) may hold
  `family`: show its rows under the result as "<language>: <word>", with the
  parts marked false in `parts` emphasised, a row with `waiting` as "czeka
  dziś w kolejce", a row with `hidden` (its word answers another card waiting
  today) as "ukryte do dzisiejszego pytania" and `rule` as the endings that
  correspond. Show only these words; never add an equivalent of your own,
  because a card of the family may still wait today.

**One card at a time (`batch` 1).** Every message holds the result of the
last answer and then the next card from `next.items` of that result: its
question. With `new_words: show` a new word's introduction takes a message
of its own, and the learner's "dalej" brings its question.

**Several cards (`batch` 2 or more).** Ask the cards as one numbered list;
with `new_words: show` introduce the new words of the batch together first
and end the message. The learner answers by number; when the reply does not map clearly onto
the numbers, ask once. Send every answer of the list in one `vocab_answer`
call and show the results of the list, then the next batch from `next`.

Go on until `left` shows no reviews, no new words and no drill, or until the
learner ends the session. Cards answered wrong come back in the "utrwalanie"
(the drill) at the end, as many times as needed; their due date no longer
changes that day.

## The stages and more cards

The learner decides what to learn and how much, at any moment of the session.

- **The stage.** `stage` in a result of `vocab_next`, and in `next` of an
  answer, names the stage of the cards returned: `reviews`, `new` or `drill`.
- **A change of stage.** When the learner asks for the new words, the reviews
  or the drill ("nowe", "pomiń powtórki", "przejdź do nauki", "wróć do
  powtórek", "utrwalanie"), call `vocab_next` with `stage` and go on from its
  cards. The card that was on screen waits in its own stage, unanswered. A
  message that names a stage is a request, never an answer to the card.
- **Staying in the stage.** `then_next` returns the next cards of the stage
  the answered card belongs to, so a learner who chose the new words gets the
  next new word while the reviews wait.
- **A stage ends.** When `next.stage` differs from the stage of the answered
  card, or a result holds `stage_empty`, the stage has no cards left. Say in
  one line what is done and what waits, from `left` ("Nowe słowa na dziś
  zrobione. Czekają powtórki: 12."), then show the card returned. Reviews the
  learner leaves undone stay due and come first on the next day.
- **More new words.** The day's number of new words is a start, never a
  limit. When the learner asks for more ("więcej słów", "kolejne słowa",
  "jeszcze 10"), call `vocab_add_today` with `count`: the number the learner
  names, 5 otherwise. `more.new` in the latest result says how many the
  course still has.
- **The next round of reviews.** When the learner asks for more reviews
  ("jeszcze powtórki", "następna tura"), call `vocab_add_today` with
  `reviews`: the number the learner names, 10 otherwise. The engine takes the
  due reviews outside today's list first (`more.reviews_due`: over the review
  limit, or on a day off), then the cards with the nearest later dates
  (`more.reviews_ahead`), from the state after today's answers. These come
  with `phase: ahead` and are asked as any review; the engine counts the
  shorter gap when it sets the next date.
- The result of `vocab_add_today` holds `added` (the cards that joined) and
  `next` with the first of them. `added` with 0 means nothing more is there:
  every word already has today's answer, or the levels have no more words.

## Step 2: the end

Call `vocab_today` and sum up the session from it: the `counter`, then the
new words of the day from `learned_today` (word and meaning, "znane
wcześniej" for `known`). Then offer, in one line, what `more` allows: more
new words, the next round of reviews, or the end; the learner's choice goes
to `vocab_add_today` and the session goes on with Step 1. Offer the coach
(`vocab_guide` with the topic `coach`) for the words that went wrong.

Chat applications that show MCP Apps display a card with the results of
`vocab_next`, `vocab_answer`, `vocab_grade`, `vocab_reveal`,
`vocab_add_today` and `vocab_today`: the counter,
the word with a button that plays its recording, and the question. The
messages stay the same, since the card only adds sound and a view of the
same results.

## How the cards look

The examples use invented cards; the real ones come from `vocab_next`.

One card at a time: a new word, asked at once under the counter.

```
Postęp: 6/25 · nowe 3/15 · powtórki 3/10

Nowe słowo · DE · pies (rzeczownik, z rodzajnikiem)
___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.

Wpisz słowo albo „?”, jeśli jeszcze go nie znasz.
```

Its result, the first contact with the word, and the next card:

```
✗ nie wiem · der Hund (r.m., l.mn. die Hunde) /hʊnt/ [🔊 wymowa](https://upload.wikimedia.org/…) = pies
Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
Słowo wróci dziś w utrwalaniu.

ES · stół (rzeczownik, z rodzajnikiem)
___ es de madera. · Stół jest z drewna.
```

A new word the learner knew before the course:

```
✓ znane wcześniej · la mesa (r.ż., l.mn. las mesas) /ˈme.sa/ [🔊 wymowa](https://upload.wikimedia.org/…) = stół
La mesa es de madera. · Stół jest z drewna.
```

With `new_words: show`: a new word, alone in its message.

```
Postęp: 6/25 · nowe 3/15 · powtórki 3/10

Nowe słowo · DE
der Hund (r.m., l.mn. die Hunde) /hʊnt/ [🔊 wymowa](https://upload.wikimedia.org/…) = pies
Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.

Napisz „dalej”, gdy będziesz gotowy, albo „znałem”, jeśli znałeś to słowo przed kursem.
```

Its question, after "dalej":

```
DE · pies (rzeczownik, z rodzajnikiem)
___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
```

The result and the next card in one message:

```
≈ prawie (rodzajnik) · der Hund /hʊnt/ [🔊 wymowa](https://upload.wikimedia.org/…)
Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.

ES · stół (rzeczownik, z rodzajnikiem)
___ es de madera. · Stół jest z drewna.
```

A stage ends, and the next one follows in the same message:

```
Postęp: 15/27 · nowe 15/15 · powtórki 0/12

✓ wiem · la mesa
Nowe słowa na dziś zrobione. Czekają powtórki: 12. Więcej nowych słów dodam na hasło „więcej słów”.

DE · pies (rzeczownik, z rodzajnikiem)
___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
```

The end of the day's list, after the summary:

```
Dzisiejsza lista jest zrobiona. Możesz wziąć kolejne nowe słowa („więcej słów”), następną turę powtórek („jeszcze powtórki”) albo zakończyć.
```

With `view.answer_mode: self`, "pokaż" instead of an answer:

```
Postęp: 7/25 · nowe 4/15 · powtórki 3/10

der Hund (r.m., l.mn. die Hunde) /hʊnt/ [🔊 wymowa](https://upload.wikimedia.org/…) = pies
Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
Notatka: Hund brzmi jak angielskie hound.

Jak Ci poszło: wiem, prawie czy nie wiem?
```

Several cards as a numbered list:

```
1. DE · pies (rzeczownik, z rodzajnikiem)
   ___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
2. ES · stół (rzeczownik, z rodzajnikiem)
   ___ es de madera. · Stół jest z drewna.

Odpowiedz numerami, np. „1. …”. Gdy nie pamiętasz, wpisz „?”.
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

In a list of several cards with production and recognition cards, send the
production answers with `vocab_answer` first, then go through the
recognition cards.

## During the session

- **Change of a grade.** Only on the learner's explicit request for a named
  card: `vocab_regrade`.
- **Another stage, more words, more reviews.** The section "The stages and
  more cards".
- **A mistake in a card.** The learner's note goes to `vocab_flag`; the card
  leaves the queue until `vocab_flag` with `clear: true`.
- **A word the learner does not want.** "nie chcę tego słowa", "pomiń to
  słowo": `vocab_flag` with the card and `skip: true`, without showing the
  word, then `vocab_next` with the stage of that card. The word stays away
  until the learner asks for it back ("przywróć słowo …"): `vocab_lookup`
  finds its card, and `vocab_flag` with `clear: true` brings it back with its
  date. The result of `vocab_flag` holds the day's `counter` after the
  change. `vocab_status` lists the words put aside (`skipped`).
- **A note.** "zapisz notatkę: …" saves the learner's text as written with
  `vocab_note` for the card of the last result (or the card `vocab_lookup`
  finds). The note comes with the word's answer and never with its question.
- **A pause.** Every answer is saved at once. The next `vocab_next` continues
  in the same order, in this conversation or in a new one.

## Gotchas

- `vocab_next` returns the same order again until answers come in; calling it
  twice does not skip cards. Ask the cards the last `vocab_next` returned.
- `not_in_today`: the card is not on today's list. More new words come only
  through `vocab_add_today` with `count`.
- `not_due`: a review before its day. It joins the day only through
  `vocab_add_today` with `reviews`.
- After `vocab_grade` use `then_next: true` as well; a separate `vocab_next`
  without `stage` returns to the engine's order.
- `known_only_first`: "znałem" works only the first time a word is shown.
- `drill_two_grades`: a drill answer is regraded to `know` or `dont_know`.
- `reveal_production`: the plan's `answer_mode` is `type`, so a production
  card is answered by typing; `reveal_not_waiting`: the card is not in
  today's session.
- The order of the reviews is the plan's `review_order`: `due` (most overdue
  first, the default), `course`, `interval` or `random`; a change goes
  through `vocab_plan_change` (the topic `start`).
- An empty answer is graded "nie wiem" with the error class "brak
  odpowiedzi". The words "nie wiem" typed as an answer would be graded as a
  wrong word, so send an empty answer.
- With `diacritics: lenient` in the plan, a missing diacritic does not lower
  the grade.
