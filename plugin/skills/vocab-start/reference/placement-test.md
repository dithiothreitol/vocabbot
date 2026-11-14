# The placement test

A short test from the course words, level by level, that writes nothing.

1. `quiz --lang <code> --levels a1-b2 --count 6 --json` gives six questions
   for each level, words spread from the most to the least frequent of the
   level. The questions hold no answers.
2. Start with A1, or with the level below the one the learner named. Ask the
   questions of one level as a numbered list: the Polish meaning, the part
   of speech, "z rodzajnikiem" when `with_article` is true, and the sentence
   with its gap and `sentence_pl`. No hints.
3. Grade the level: send every answer given so far in this test, of this
   level and of the earlier ones, on standard input, an unknown one as an
   empty answer:

   ```
   python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" quiz --check --stdin --json <<'EOF'
   {"card": "de-c07513#p", "answer": "das Wasser"}
   {"card": "de-c07160#p", "answer": ""}
   EOF
   ```

4. Show the results of the level: one line per word with the grade and the
   right word, then `levels.<level>` (know, almost, asked, share).
5. Go on to the next level while `levels.<level>.known` is true. Stop at the
   first level that is not known.
6. `suggested_levels` is the engine's proposal, for example `a2-b2`. The
   learner decides; the chosen levels go into `init --lang <code>:<levels>`.

A level counts as known from 80% of right answers; "prawie" counts as half.
The test can run again: the same `--count` gives the same words, another
count gives other words.
