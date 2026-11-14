# VocabBot

VocabBot teaches vocabulary in one, two or three foreign languages at once,
at levels A1 to B2, for a learner whose base language is Polish. A learner
meets new words in order of frequency, answers each card by typing the word,
and comes back to it on the day an FSRS-6 scheduler sets for it. One engine
serves two ways in: the `vocabbot` program in a terminal, and a plugin with
Agent Skills for Claude and Codex.

The project is in development (Stage 1 of 3, see
`docs/development-plan.pl.md`). The engine and the program work on a starter
course of 60 concepts in English, German, Spanish and French; the full A1 to
B2 courses and the plugin come in Stages 2 and 3.

## Try it

```
uv tool install .
vocabbot init ~/VocabBot --lang de:a1-a2 --lang es:a1-a2 --new 10
vocabbot drill
vocabbot status
```

The engine also runs from one file without installing anything:

```
python scripts/build.py pyz
python build/vocabbot.pyz today
```

## Licence

The code is licensed under Apache-2.0 (`LICENSE`). The scheduler is a port
of py-fsrs (MIT) and the starter course is licensed under CC BY-SA 4.0;
`NOTICE` has the details.
