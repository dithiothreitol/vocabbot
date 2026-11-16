# Gotchas

- `next` returns the same order again until answers come in; calling it
  twice does not skip cards. Ask the cards the last `next` returned.
- `not_in_today`: the card is not on today's list (a new word beyond the
  day's number). More new words come only through `today --extra <n>`.
- `not_due`: a review before its day. It joins the day only through
  `today --reviews <n>`.
- After `grade` use `--next` as well; a separate `next` without `--stage`
  returns to the engine's order.
- In the terminal session the same choices are `/nowe`, `/powtorki`,
  `/utrwalanie` and `/wiecej`, and the keys offered at the end of the list;
  `/t` shows a sentence's translation, `/pomin` puts a word aside and
  `/notatka` saves a note for the previous word.
- `known_only_first`: "znałem" works only the first time a word is shown.
- `drill_two_grades`: a drill answer is regraded to `know` or `dont_know`.
- `reveal_production`: the plan's `answer_mode` is `type`, so a production
  card is answered by typing; `reveal_not_waiting`: the card is not in
  today's session.
- A learner's note (`word.note`) comes in results, `reveal` and `lookup`,
  never in `next`; keep it with the answer.
- The order of the reviews is the plan's `review_order`: `due` (most overdue
  first, the default), `course`, `interval` or `random`; `vocab-start`
  changes it.
- `nothing_to_regrade` or `same_grade`: there is no grade from today to
  change, or the grade is already the requested one.
- A drill answer (the second and later answers on one day) leaves the due
  date unchanged; a card leaves the drill after "wiem".
- An empty answer is graded "nie wiem" with the error class "brak
  odpowiedzi". The word "nie wiem" typed as an answer would be graded as a
  wrong word, so send it as an empty answer.
- With `diacritics: lenient` in the plan, a missing diacritic does not lower
  the grade; the log still records it.
- Answers in another language being learned get `other_lang`; this happens
  most with words that look alike, so name the language in the result.
- The plan's `batch` sets the cards of one message: 1 by default, one card
  at a time. `next --count <n>` overrides it for one call.
- The terminal session (`vocabbot drill`) and the chat share the folder and
  the order, so a session can start in one and end in the other.
