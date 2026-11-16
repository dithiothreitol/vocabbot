## The answer comes after the grade

- A card under review, in drill or in the placement test shows only its
  `question`. The answer appears after the engine graded the learner's
  answer: in the result of `answer`, `grade` or `quiz --check` for that card.
- Before that, give no part of the answer: not the word, its first letter,
  its length, its article, a synonym or a cognate in the language of the
  card, and not the same word in another language being learned.
- A new word (`phase: new`) is asked at once, as in SuperMemo, and the result
  of its first answer introduces it in full. Only a plan with
  `new_words: show` puts `word` in the item of a new card: that word is
  meant to be shown first, and its question follows after the introduction.
- A recognition card (`question.ask: meaning`) shows the foreign word; its
  meaning comes from `reveal` after the learner has tried to recall it.
- Results of `lookup` and `status` mark cards still waiting in today's
  session with `waiting_today: true`. Keep their answers back until the
  session has asked them.
