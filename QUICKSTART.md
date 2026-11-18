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

- the languages, one to three of English, German, Spanish, French and Italian;
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

- A new word comes at once as a question, as in SuperMemo. Type it when you
  know it: a right first answer marks the word as known before the course,
  and it will not take your daily limit. Type "?" when you do not know it
  yet: the result shows the word with its forms, pronunciation and example,
  and the word comes back the same day in the drill. `new_words=show` in the
  plan shows every new word before its question.
- Questions show the Polish meaning and a sentence with a gap. Type the word
  with its article for nouns of German, Spanish, French and Italian, or say
  "pokaż" to see the answer and grade yourself: wiem, prawie or nie wiem.
  "?" means you do not know. In the terminal an empty Enter shows the
  answer for your own grade.
- Every answer is graded at once: wiem, prawie (with what was off) or nie
  wiem. Words that went wrong come back at the end of the session.
- In the terminal a right answer is saved at once and folds into one line.
  After a mistake you see your answer next to the right one with the
  differing letters marked; Enter saves the proposed grade and 1, 2 and 3
  choose another (the drill has two grades, 1 and 3). At the
  answer prompt `/znam` marks a new word as known, `/cofnij` changes the grade
  of the previous answer, `/pomoc` lists the commands and `/koniec` (or q at a
  key prompt) ends the session with everything saved.
- You choose what to learn. In the chat say "nowe" to move to the new words
  while reviews wait, "powtórki" to go back, "więcej słów" for more new
  words than the day's number, and "jeszcze powtórki" for the next round of
  reviews. In the terminal the same choices are `/nowe`, `/powtorki`,
  `/utrwalanie` and `/wiecej`, and after the day's list the session offers n
  (5 more new words), p (the next round of 10 reviews) and Enter (the end).
  Reviews you leave for later stay due and come first on the next day.
- More controls of a card, as in SuperMemo. A sentence's translation comes
  when you ask for "tłumaczenie" (in the terminal `/t`, in the card a
  button). `answer_mode=type` in the plan leaves typing only, and
  `sentence_translation=shown` shows every translation at once. "Nie chcę
  tego słowa" (in the terminal `/pomin`) puts a word aside; "przywróć słowo
  …" brings it back.
  "Zapisz notatkę: …" (in the terminal `/notatka …` after the answer) keeps
  your note, shown with the word's answer from then on.
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

## 6. Several devices

The recommended way is an account on a VocabBot server, which keeps your
record for every device:

- **A computer.** `vocabbot login` signs the program in through the browser
  and links your learning folder to the account. When the folder and the
  account have different plans, choose with `--plan folder` or
  `--plan account`; the link is a preview with the numbers of answers on both
  sides, saved after your yes. On a computer without a folder, `vocabbot
  login` downloads the account into `~/VocabBot`. Without a browser on that
  computer, `vocabbot login --code` shows a code to confirm on your phone.
- **Every day.** The folder synchronises by itself: it fetches before
  `today`, `next`, `drill` and `status`, and sends after every answer.
  Without a network the answers wait in the folder; `vocabbot status` shows
  the last synchronisation and what waits, and `vocabbot sync` synchronises
  at once.
- **A phone.** The chat application connected to the server, or the
  server's session page (`https://<server>/app/`) in the browser, which you
  can add to the home screen. A session begun on one device goes on on
  another at the same card.
- **The account page** (`/account`) lists the connected applications and
  computers and disconnects them, gives your data as a zip
  (`vocabbot import <file.zip>` opens it as a folder), keeps an optional
  e-mail address for password recovery and removes the account.
  `vocabbot logout` ends a computer's connection.

Without an account, keep the learning folder in a synced folder. On the
other computer, `vocabbot use <folder>` points the program at it once;
`--learner <folder>` or the variable `VOCABBOT_HOME` do the same for one
call or one shell. Rows of the conflict copies the sync makes count at once;
`vocabbot doctor --merge` tidies the files after your yes.

## 7. Removing it

Delete the learning folder and `~/.vocabbot/`. Uninstall the plugin with
`/plugin uninstall vocabbot` (Claude Code) or `codex plugin remove vocabbot`,
and the program with `uv tool uninstall vocabbot`.
