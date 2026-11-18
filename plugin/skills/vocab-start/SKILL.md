---
name: vocab-start
description: >
  Set up VocabBot, vocabulary learning in one to three languages at once
  (English, German, Spanish, French, Italian; levels A1 to B2) for a Polish speaker:
  choose languages, levels, weights and new words a day, run a short
  placement test, create the learner's folder, change the plan later, show
  the courses and the forecast, check the folder, install the vocabbot
  terminal program. Use when the learner says: set up vocabbot, I want to
  learn German, placement test, change my plan, fewer new words, add Spanish,
  pause French, how long will it take; po polsku: skonfiguruj VocabBota, chcę
  się uczyć niemieckiego, test poziomujący, zmień plan, mniej nowych słów,
  dodaj hiszpański, chcę się uczyć włoskiego, wstrzymaj francuski, ile to potrwa.
argument-hint: "[languages and levels]"
---

# VocabBot: setup and the plan

Read `shared/rules.md` first: it says how to call the engine and holds the
rules every VocabBot skill keeps.

```
python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" <command> --json
```

## Step 0: is VocabBot set up?

Run `plan show --json`.

- It shows a plan: the learner wants a change (B), the terminal program (C)
  or a check of the folder (D). Questions about time and progress go to
  `forecast` (A6) and to `vocab-coach`.
- `no_learner` or `no_plan`: set it up (A). If the learner says a folder
  already exists, pass `--learner <folder>` and run `plan show` again.

## A. Setup

1. **Courses.** `course list --json` gives the languages and the number of
   words per level. Quote these numbers when the learner asks about a course.
2. **Questions, in one message.** Which languages (one to three of
   angielski, niemiecki, hiszpański, francuski, włoski); the level of each
   (A1–A2 for beginners, B1–B2 for the intermediate, or "nie wiem", which
   calls for the test); new words a day for all languages together (the
   default is 15); days off, if any; whether one language should get more
   new words than the others (weight 2 against 1).
3. **Placement test.** Offer it for every language with an unsure level, and
   run it as `reference/placement-test.md` says. The learner may skip it.
4. **Folder.** In Claude Code or a terminal the default is `~/VocabBot`; a
   folder the learner names works too (an account on a server, E, adds the
   phone and other computers), and a synced folder (OneDrive,
   Dropbox) shares the learning between computers. In Cowork, use the folder
   the learner opened for this work. The learner's folder is theirs: never
   put it inside the plugin or a project repository.
5. **Preview and yes.**

   ```
   python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" init <folder> --lang de:a1-a2 --lang es:b1-b2:2 --new 15 --set days_off=sun --json
   ```

   `--lang` is `code:levels[:weight]`; `--set` takes any plan key from
   `reference/plan-keys.md` and repeats. Show the `preview` lines as they
   are and ask whether to save. After an explicit yes:
   `commit --confirm <token> --learner <folder> --json`. `skipped` in its
   result means the host's sandbox kept the engine from saving the pointer
   in the home folder; later calls then work from the learner's folder as
   the current folder, or with `--learner <folder>`.
6. **Forecast.** `forecast --days 30 --json`: quote `average_minutes`,
   `peak_reviews` and the days in `levels_complete` when each level has been
   introduced in full.
7. **Next.** Offer the first session (`vocab-session`) and the terminal
   program (C).

## B. Changing the plan

`plan show --json` shows the plan in `lines`. A change is
`plan set KEY=VALUE [KEY=VALUE ...] --json`, a preview, the learner's yes and
`commit --confirm <token> --json`. Keys and examples:
`reference/plan-keys.md`. After a change of the new words a day, the levels
or the languages, run `forecast --days 30 --json` again and quote it.

The schedule can follow the learner's own log. `replay --json` replays the
log and compares FSRS-6 with its defaults against the variants fitted to the
earlier part of the log (`variants`, with `scores` and `delta` against
FSRS-6) and simulates the coming weeks (`workload`). `plan fit --json` is a
preview: it gives a language parameters of its own only where they predict
the later reviews better than FSRS-6; after the learner's yes, `commit`
saves them. `plan set parameters=default --json` goes back to FSRS-6.

## C. The terminal program

The same engine runs as the `vocabbot` program with a coloured session
(`vocabbot drill`). `reference/install.md` gives the commands. Installing
software is the learner's decision: show the command and run it only after
their yes.

## D. Checking the folder

`doctor --json` lists problems: damaged rows, conflict copies from a synced
folder, expired previews. Rows of conflict copies already count in every
result; `doctor --merge --json` joins the copies into the main files and
`doctor --repair --json` moves damaged rows aside. Both are previews and
need the learner's yes before `commit`.

## E. Other devices and the account

The recommended way to learn on several devices is an account on a VocabBot
server: the folder becomes a copy of the account that works without a
network and synchronises by itself, and the phone learns in the chat
application connected to the server or on the server's session page
(`https://<server>/app/`). `reference/devices.md` gives the details.

1. **Signing in is the learner's step.** `vocabbot login [server]` opens the
   server's sign-in page in the browser and waits for it; `vocabbot login
   --code` shows a code to confirm on a phone instead. Show the command and
   ask the learner to run it in their own terminal; never ask for or type a
   password.
2. **The link is a preview.** When the folder and the account both have a
   plan and the plans differ, `login` stops with `choose_plan` and lists both
   plans (`error.details`): ask which one stays, then
   `login --plan folder` or `login --plan account`. Show the preview lines
   (answers in the folder, on the account, after joining) and, after the
   learner's yes, `commit --confirm <token> --json`; its `sync` holds the
   first synchronisation.
3. **After the link.** `today` and `status` carry `sync` (the account, the
   last synchronisation, the rows waiting); quote it as it is. `sync --json`
   synchronises at once, `logout --json` ends the connection and unlinks the
   folder, which stays as it is.
4. **Moving a record.** `export <file.zip> --json` writes the record as a
   zip; `import <file.zip> --json` is a preview of a new folder, or of the
   rows a folder lacks, saved after the learner's yes.

More: `reference/gotchas.md`.
