# Quick start

**English** · [Polski](QUICKSTART.pl.md)

## 1. Install

**Claude Code** (terminal, IDE, the Code tab of the desktop app):

```
/plugin install vocabbot --marketplace dithiothreitol/vocabbot
```

**Codex CLI**:

```
codex plugin marketplace add dithiothreitol/vocabbot
codex plugin add vocabbot@vocabbot
```

**Cowork** in the Claude desktop app: add the marketplace
`dithiothreitol/vocabbot`, or upload `vocabbot.plugin` from the release
(Add > Upload plugin), and open the folder you want to keep your learning in.

**Terminal only**: `uv tool install vocabbot` (or `pipx install vocabbot`).

Every way needs Python 3.10 or later. On Windows, check with
`python --version`: `python3` can be a Microsoft Store alias that runs
nothing.

## 2. Set up

Say "skonfiguruj VocabBota" (or type `/vocabbot:vocab-start`). VocabBot asks
for:

- the languages, one to three of English, German, Spanish and French;
- the level of each: A1–A2 for beginners, B1–B2 for the intermediate, or a
  short placement test when you are not sure;
- the number of new words a day for all languages together (15 by default)
  and days off, if you want any;
- the folder for your learning (`~/VocabBot` by default; a synced folder such
  as OneDrive lets two computers share it).

It shows the plan as a preview and saves it after your yes, then quotes the
forecast: minutes a day and when each level will have been introduced.

In a terminal the same setup is one command:

```
vocabbot quiz --lang de
vocabbot init --lang de:a1-a2 --lang es:b1-b2:2 --new 15 --set days_off=sun
```

## 3. The daily session

Say "sesja" or "uczymy się" in the chat, or run `vocabbot drill` in a
terminal. Both use the same folder and the same order, so a session can start
in one and end in the other.

- New words are introduced first; say which ones you knew before ("znałem"),
  and they will not take your daily limit.
- Questions show the Polish meaning and a sentence with a gap. Type the word
  with its article for nouns of German, Spanish and French. "?" or an empty
  answer means you do not know.
- Every answer is graded at once: wiem, prawie (with what was off) or nie
  wiem. Words that went wrong come back at the end of the session.
- In the terminal a right answer is saved at once and folds into one line.
  After a mistake you see your answer next to the right one with the
  differing letters marked; Enter saves the proposed grade and 1, 2 and 3
  choose another. While introducing new words, z marks one as known. At the
  answer prompt `/znam` marks a new word as known, `/cofnij` changes the grade
  of the previous answer, `/pomoc` lists the commands and `/koniec` (or q at a
  key prompt) ends the session with everything saved.
- `vocabbot` without a command shows the plan of the day; Enter starts the
  session.
- A grade changes only when you ask for it ("to była literówka, zalicz").

## 4. Own words

"Dodaj do niemieckiego: der Feierabend = koniec dnia pracy", a pasted text or
a photo of a textbook page. VocabBot shows what it will add: your own words,
course words moved to the front of the queue, and words left out because you
already learn them. Nothing is saved before your yes.

## 5. Progress and the plan

- "Jak mi idzie?", "przegląd tygodnia", or `vocabbot status` and
  `vocabbot forecast`.
- "Mniej nowych słów", "dodaj francuski", "wstrzymaj hiszpański", "niedziele
  wolne", or `vocabbot plan set new_per_day=10`. Every change is a preview
  first.
- "Wyjaśnij mi słowo …", "ciągle mylę …": the coach explains, finds
  mnemonics and compares words between your languages.
- After two weeks the plan follows your presence: due dates avoid the
  weekdays you usually skip, new words stay within your usual minutes, and
  the day before a skipped day offers reviews ahead. `presence=off` in the
  plan turns this off.
- `vocabbot replay` compares the schedule fitted to your own log with FSRS-6
  on the later part of the log; `vocabbot plan fit` saves the fitted
  parameters for a language only where they predict better, after your yes.

## 6. Two computers

Keep the learning folder in a synced folder. On the other computer,
`vocabbot use <folder>` points the program at it once; `--learner <folder>`
or the variable `VOCABBOT_HOME` do the same for one call or one shell. When
the sync makes conflict copies of the log,
`vocabbot doctor` finds them and `vocabbot doctor --merge` joins them after
your yes; the merged log gives the same schedule.

## 7. Removing it

Delete the learning folder and `~/.vocabbot/`. Uninstall the plugin with
`/plugin uninstall vocabbot` (Claude Code) or `codex plugin remove vocabbot`,
and the program with `uv tool uninstall vocabbot`.
