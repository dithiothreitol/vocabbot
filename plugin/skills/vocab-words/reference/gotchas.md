# Gotchas

- `words_invalid`: the message names the word and the missing or wrong
  field (no Polish meaning, a noun without gender). Fix the line and preview
  again.
- `nothing_to_add`: every word is already an own word or already being
  learned; the message lists them.
- `bad_word_line`: a line has no `=` and is not JSON.
- One call takes up to 200 words. Larger lists go in parts, each with its own
  preview.
- A word typed without its article can still match a course noun by its
  lemma; the preview then shows the course entry with the article, which is
  the form the questions expect.
- Two own words with the same Polish meaning need a `hint` each, so that the
  question tells them apart; `course check` reports the clash.
- Own words live in `courses/<code>/own.jsonl` of the learner's folder and
  are written only through the preview and `commit`.
- A photo of a textbook page often holds the publisher's text: take single
  words and short phrases for the learner's own use, not whole exercises.
