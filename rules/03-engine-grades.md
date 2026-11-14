## The engine grades

- Pass the learner's answer exactly as typed: no corrected letters, no added
  article, no changed case. An answer the learner marks as unknown (`?`,
  `-`, "nie wiem", "pas") goes to the engine as an empty answer.
- The grade is the engine's. Report it as it is, with its error classes, and
  never suggest a different one.
- `regrade` changes today's last grade of one card, and only when the learner
  explicitly asks for that card ("to była literówka, zalicz"). The log marks
  such a row.
- `grade --grade known` records that the learner knew a word before the
  course; it is accepted only at a word's first showing. A recognition card
  gets the learner's own grade (`know`, `almost`, `dont_know`), never one you
  chose.
