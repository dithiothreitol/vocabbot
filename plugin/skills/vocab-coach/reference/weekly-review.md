# The weekly review

Every number comes from `status` and `forecast` of this conversation.

## Per language

| What | From |
|---|---|
| words learned per level | `levels.<level>.learned` of `levels.<level>.total` |
| recall over 30 days | `retention_30` against `target_retention` (null until there are reviews) |
| reviews over 30 days | `reviews_30` |
| reviews due within 7 days | `due_week` |
| most frequent error classes | `errors_30` |
| hard words | `leeches` (count, and up to five by name) |
| mix-ups with other languages | `confusions` |

Then `streak_days`, and from `forecast`: `average_minutes`, `average_reviews`,
`peak_reviews` and `levels_complete`.

## Suggestions

At most three, each tied to a number above, each phrased as an option:

- `retention_30` well below `target_retention` with many reviews: fewer new
  words (`new_per_day`) for a while.
- Many reviews a day (`peak_reviews`) and little time: a `review_limit`, or
  fewer new words.
- `diacritic` among the top error classes: the keyboard layout of the
  language, or `diacritics=lenient` in the plan.
- `article` or `gender` among the top error classes: the coach's practice
  of genders for the recent nouns.
- Many `confusions`: a larger `sibling_gap_days`, or `mix=blocks`.
- A level complete soon (`levels_complete`): the next level for that
  language (`lang.<code>.levels`).

Plan changes go through `vocab-start`: a preview and the learner's yes.
