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
| mix-ups with other languages | `confusions`; `mixups_30` (`hard`, `near` of `typed` answers) |
| learning by families | `families`: `together`, `blocks_30`, `first_recall_30` against `following_recall_30`, `mixups_per_100` |

Then `streak_days`, and from `forecast`: `average_minutes`, `average_reviews`,
`peak_reviews` and `levels_complete`.

From `schedule` in `status`: for each language whether the FSRS-6
parameters are the defaults, the initial intervals fitted to the learner's
second answers, or parameters of its own (`source`, with `fit` for the
reviews they come from and their log loss against FSRS-6), and the presence
profile (`presence.weekdays`, `presence.minutes`).

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
- Many `confusions` (`mixups_30.hard` plus `near` against `typed`): a larger
  `sibling_gap_days`, or `mix=blocks`.
- Several related languages (Spanish, Italian, French) with few `confusions`:
  learning them by families (`together`), which keeps the same words together.
- A family set (`families.together`) with `mixups_per_100` growing over the
  weeks: back to separate languages (`together=none`).
- A level complete soon (`levels_complete`): the next level for that
  language (`lang.<code>.levels`).
- A log with many reviews and FSRS-6 defaults: `vocab-start` can compare the
  fitted schedule (`replay`) and save it when it predicts better (`plan fit`).

Plan changes go through `vocab-start`: a preview and the learner's yes.
