# Recognition cards

A plan with `directions` set to `produce,recognize` also has recognition
cards (`<id>#r`): the foreign word is shown and the learner recalls its
meaning. The engine cannot grade a meaning typed in free words, so the
learner grades the recall.

1. Show `question.word` and `question.sentence`, and ask what the word means.
2. After the learner's attempt (or "pokaż"), run
   `reveal --card <card> --json` and show `word`: the meaning, the forms and
   the example.
3. Ask for the learner's own grade: wiem, prawie or nie wiem. You may say
   what the course gives as the meaning; the grade stays the learner's.
4. Record it: `grade --card <card> --grade know|almost|dont_know --json`.

`reveal` refuses production cards (`#p`): their answer appears only in the
result of `answer`.

In a list of several cards with production and recognition cards, send
the production answers with `answer --batch` first, then go through the
recognition cards.
