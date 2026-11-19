# Plan keys

`plan set` and `init --set` take `KEY=VALUE`. Several pairs go in one call
and give one preview.

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
| `together` | languages learned by families, at least two of the plan, `all` or `none` (default): a concept enters them together, its cards stand side by side as a block, a due card brings its family in the other languages of the set as reviews before their day, and the gap of `sibling_gap_days` holds only towards the other languages; the preview shows the load of 28 days before and after the change | `together=es,it,fr` |
| `max_languages` | 1 to 6; a fourth language needs this raised first | `max_languages=4` |
| `batch` | 1 to 20, the cards in one message of the chat session; 1 (default) asks one card at a time, as SuperMemo does | `batch=5` |
| `new_words` | `ask` (default): a new word comes at once as a question, as in SuperMemo, and a right first answer marks it as known before the course; `show`: the word is shown first and asked afterwards | `new_words=show` |
| `review_order` | the order of the day's reviews: `due` (most overdue first, default), `course` (the order of the course), `interval` (shortest intervals first) or `random` | `review_order=course` |
| `answer_mode` | `self` (default): the learner types the word of a production card, which the engine grades, or says "pokaż", sees the answer and grades the recall, as SuperMemo's "Check" does; `type`: typing only | `answer_mode=type` |
| `sentence_translation` | `hidden` (default): a sentence's Polish translation comes on request, as in SuperMemo; `shown`: with the sentence | `sentence_translation=shown` |
| `next_review` | `shown` (default): the result of an answer says when the card comes back ("wróci za 4 dni"); `hidden`: it does not | `next_review=hidden` |
| `presence` | `on` (default): due dates avoid the weekdays the learner usually skips, new words stay within the usual minutes, and a day before a skipped day offers reviews ahead; `off`: none of this | `presence=off` |
| `parameters` | `default` removes the FSRS-6 parameters fitted by `plan fit` | `parameters=default` |

A lower `retention` means fewer reviews and more forgetting; a higher one,
the opposite. `forecast` shows the effect of the current plan only, so
after a change run it again.
