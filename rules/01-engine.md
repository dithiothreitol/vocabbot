## The engine

Every card, grade, due date and count comes from `bin/vocabbot.pyz`, the
VocabBot engine with its courses, in this skill's folder:

```
python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" <command> --json
```

- Where `${CLAUDE_SKILL_DIR}` was not substituted (Codex, an uploaded skill),
  use the folder this skill's `SKILL.md` was read from.
- Where `python3` is missing or opens the Microsoft Store, use `python`, then
  `py -3`. The engine needs Python 3.10 or later and nothing else.
- Every call prints one JSON object. `"ok": false` comes with
  `error.code` and `error.message`; the message is written for the learner in
  their base language, so show it as it is and do not retry the same call.
- The engine finds the learner's folder itself: the current folder when it
  holds `registers/plan.json`, otherwise the folder saved by `init`. When a
  call fails with `no_learner` or `no_plan`, ask whether VocabBot is set up;
  the `vocab-start` skill sets it up. When the learner names a folder, pass
  `--learner <folder>` to every call.
- Never set the learning day yourself; the engine knows when a day starts.
- Never read or unpack `vocabbot.pyz`, and never open the files of the
  learner's folder to read or change them. The engine's commands are the only
  way to its data.
- Run the engine as shown and nothing else: no wrapper program, no patched
  home folder, no changed environment. When the host refuses a write
  (`io_error`), show the message and ask the learner how to go on.
- Without a Python that runs the engine, say that grades and due dates cannot
  be saved here, and offer practice that saves nothing, or the session in a
  terminal (`vocabbot drill`).
