# Gotchas

- `status` before the first review has `retention_30: null`; say there is
  nothing to measure yet.
- `leeches` lists words from the plan's `leech_lapses` (default 4) lapses
  up; an empty list is good news.
- `recent` leaves out words marked as known and words still waiting in
  today's session; after the session more words appear.
- `lookup` matches the word itself (with or without its article) or a word
  of its Polish meaning, and returns up to ten matches with `more` for the
  rest. A word outside the course gives no match: the learner can add it
  through `vocab-words`.
- A mnemonic or an explanation never becomes part of the course by itself;
  a learner who wants to keep a sentence adds it as an own word through
  `vocab-words`.
- Practice sentences use the forms of the course entry; an inflected form
  in a sentence is fine, but the gap keeps one word.
- The coach does not judge whether a grade was fair. A learner who wants a
  grade changed asks for it in the session (`regrade`).
