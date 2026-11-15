# Gotchas

- `next` returns the same order again until answers come in; calling it
  twice does not skip cards. Ask the cards the last `next` returned.
- `not_in_today`: the card is not on today's list (a new word beyond the
  daily limit). More new words come only through `today --extra <n>`.
- `not_due`: a review before its day. Accept it only when the learner chose
  to learn ahead (`answer --ahead`).
- `known_only_first`: "znałem" works only the first time a word is shown.
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
  at a time. `next --count <n>` overrides it for one call, for example for
  reviews ahead.
- The terminal session (`vocabbot drill`) and the chat share the folder and
  the order, so a session can start in one and end in the other.
