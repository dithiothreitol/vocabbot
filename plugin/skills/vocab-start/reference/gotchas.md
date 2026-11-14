# Gotchas

- `plan_exists`: the folder already has a plan. Use `plan set` for changes,
  or another folder for another person; one folder belongs to one learner.
- `plan_invalid`: the message lists what is wrong (a fourth language without
  `max_languages`, an unknown level, a weight below 1). Fix the arguments and
  preview again.
- `unknown_token` or `token_expired`: the preview was committed already or
  is older than 30 minutes. Preview again.
- `changed_since_preview`: a file changed after the preview (a session in
  the terminal, another computer). Preview again.
- `init` writes the pointer to the folder in `~/.vocabbot/config.json`, so
  later calls need no `--learner`. In Cowork the current folder counts when
  it holds `registers/plan.json`.
- The levels of a language are a range: `a2-b2` starts with the most frequent
  A2 words and goes on into B1 and B2.
- `new_per_day` is shared by the languages by weight; with three languages
  and 15 words, each gets about five a day.
- A language added later starts with its first words; the words of other
  languages keep their schedule.
- `lang.<code>=off` removes a language from the plan but keeps its log: a
  later `lang.<code>=<levels>` brings its cards back with their history.
- `quiz` and `forecast` write nothing, so they need no preview.
