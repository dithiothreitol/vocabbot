# Setup and the plan

## Step 0: is there a plan?

Call `vocab_plan`.

- It shows a plan: the learner wants a change (B), a comparison of the
  schedule (C), or asks about time and progress (`vocab_forecast`, and the
  topic `coach`).
- `no_account_plan`: set it up (A).

## A. Setup

1. **Courses.** `vocab_courses` gives the languages and the number of words
   per level. Quote these numbers when the learner asks about a course.
2. **Questions, in one message.** Which languages (one to three of
   angielski, niemiecki, hiszpański, francuski, włoski); the level of each
   (A1–A2 for beginners, B1–B2 for the intermediate, or "nie wiem", which
   calls for the test); new words a day for all languages together (the
   default is 15); days off, if any; whether one language should get more
   new words than the others (weight 2 against 1).
3. **Placement test.** Offer it for every language with an unsure level, and
   run it as the section below says. The learner may skip it.
4. **Preview and yes.** `vocab_setup` with `languages` in the form
   `code:levels[:weight]` (`de:a1-a2`, `es:b1-b2:2`), `new_per_day`, and
   `settings` with any plan key below (`days_off=sun`). Show the `preview`
   lines as they are and ask whether to save. After an explicit yes in the
   learner's next message: `vocab_commit` with the token.
5. **Forecast.** `vocab_forecast` with `days` 30: quote `average_minutes`,
   `peak_reviews` and the days in `levels_complete` when each level has been
   introduced in full.
6. **Next.** Offer the first session (the topic `session`).

## B. Changing the plan

`vocab_plan` shows the plan in `lines`. A change is `vocab_plan_change` with
one or more `KEY=VALUE` settings, a preview, the learner's yes and
`vocab_commit`. After a change of the new words a day, the levels or the
languages, call `vocab_forecast` again and quote it.

## C. A schedule fitted to the learner

`vocab_replay` replays the log and compares FSRS-6 with its defaults against
the variants fitted to the earlier part of the log (`variants`, with `scores`
and `delta` against FSRS-6) and simulates the coming weeks (`workload`).
`vocab_plan_fit` is a preview: it gives a language parameters of its own only
where they predict the later reviews better than FSRS-6; after the learner's
yes, `vocab_commit` saves them. `vocab_plan_change` with `parameters=default`
goes back to FSRS-6.

## The placement test

A short test from the course words, level by level, that writes nothing.

1. `vocab_quiz` with `lang`, `levels` `a1-b2` and `count` 6 gives six
   questions for each level, words spread from the most to the least frequent
   of the level. The questions hold no answers.
2. Start with A1, or with the level below the one the learner named. Ask the
   questions of one level as a numbered list: the Polish meaning, the part of
   speech, "z rodzajnikiem" when `with_article` is true, and the sentence
   with its gap and `sentence_pl`. No hints.
3. Grade the level: send every answer given so far in this test, of this
   level and of the earlier ones, to `vocab_quiz_check`, an unknown one as an
   empty answer.
4. Show the results of the level: one line per word with the grade
   (`grade_pl`, with `errors_pl` for "prawie") and the right word, then
   `levels.<level>` (know, almost, asked, share).
5. Go on to the next level while `levels.<level>.known` is true. Stop at the
   first level that is not known.
6. `suggested_levels` is the engine's proposal, for example `a2-b2`. The
   learner decides; the chosen levels go into `vocab_setup`.

A level counts as known from 80% of right answers; "prawie" counts as half.

## Plan keys

`vocab_plan_change` and the `settings` of `vocab_setup` take `KEY=VALUE`.
Several settings in one call give one preview.

| Key | Values | Example |
|---|---|---|
| `new_per_day` | 0 to 100, new words a day for all languages together | `new_per_day=10` |
| `lang.<code>` | `<levels>[:<weight>]` adds a language or changes it | `lang.fr=a1-a2`, `lang.en=b1-b2:2` |
| `lang.<code>` | `paused` stops new words and keeps the reviews; `active` resumes | `lang.es=paused` |
| `lang.<code>` | `off` removes the language from the plan; its log stays | `lang.fr=off` |
| `lang.<code>.weight` | 1 or more; the share of new words against the other languages | `lang.de.weight=2` |
| `lang.<code>.levels` | `a1-a2`, `b1-b2`, `a2-b2`, `a1,b1` | `lang.de.levels=a2-b2` |
| `days_off` | weekdays `mon` to `sun`, comma-separated, or `none` | `days_off=sat,sun` |
| `retention` | 0.7 to 0.97, or a percentage; the recall the scheduler aims at (default 0.9) | `retention=0.85` |
| `review_limit` | the most reviews a day, or `none`; the rest moves to the next day | `review_limit=100` |
| `directions` | `produce` (type the word), `recognize` (recall the meaning), or both | `directions=produce,recognize` |
| `mix` | `interleaved` (languages mixed) or `blocks` (one language after another) | `mix=blocks` |
| `diacritics` | `strict` (a missing diacritic gives "prawie") or `lenient` | `diacritics=lenient` |
| `day_starts_at` | 0 to 12, the hour a learning day starts (default 4) | `day_starts_at=5` |
| `sibling_gap_days` | 0 to 14, days between learning one concept in two languages (default 3) | `sibling_gap_days=5` |
| `max_languages` | 1 to 6; a fourth language needs this raised first | `max_languages=4` |
| `batch` | 1 to 20, the cards in one message of the session; 1 (default) asks one card at a time, as SuperMemo does | `batch=5` |
| `presence` | `on` (default): due dates avoid the weekdays the learner usually skips, new words stay within the usual minutes, and a day before a skipped day offers reviews ahead; `off`: none of this | `presence=off` |
| `parameters` | `default` removes the FSRS-6 parameters fitted by `vocab_plan_fit` | `parameters=default` |

A lower `retention` means fewer reviews and more forgetting; a higher one,
the opposite. `vocab_forecast` shows the effect of the current plan only, so
after a change call it again.

## Gotchas

- `account_has_plan`: the account has a plan already; changes go through
  `vocab_plan_change`.
- `plan_invalid`: the message lists what is wrong (a fourth language without
  `max_languages`, an unknown level, a weight below 1). Fix the settings and
  preview again.
- `unknown_token` or `token_expired`: the preview was saved already or is
  older than 30 minutes. Preview again.
- `changed_since_preview`: the data changed after the preview (a session in
  another conversation). Preview again.
- The levels of a language are a range: `a2-b2` starts with the most frequent
  A2 words and goes on into B1 and B2.
- `new_per_day` is shared by the languages by weight; with three languages
  and 15 words, each gets about five a day.
- `lang.<code>=off` removes a language from the plan but keeps its log: a
  later `lang.<code>=<levels>` brings its cards back with their history.
- `vocab_quiz` and `vocab_forecast` write nothing, so they need no preview.
