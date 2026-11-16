# Privacy

**English** · [Polski](PRIVACY.pl.md)

VocabBot is a set of instructions and one local program with its courses. It
has no server, no account and no analytics, and the program sends nothing
over the network.

## Where the learner's data is kept

- **The learner's folder.** The plan, the log of answers (with the answers as
  typed), own words, notes for words, reports of mistakes and words put
  aside, and the list of approved changes
  live in a folder the learner chooses. VocabBot reads and writes there,
  apart from two places in `~/.vocabbot/`: `config.json` with the path of the
  folder, and `pending/`, where the preview of a new folder waits for the
  learner's yes for at most 30 minutes. Previews of later changes wait in
  the folder itself (`registers/.pending/`), also for at most 30 minutes.
- **The chat.** In Claude or Codex, the cards, the learner's answers and the
  engine's results pass through the host's model under the learner's own
  account and its terms.
- **The terminal.** The `vocabbot` program works without a network.

## What VocabBot keeps out

VocabBot asks for no name, address, e-mail or other personal detail. The log
holds the answers to vocabulary questions with their times.

## Removing data

Delete the learner's folder and the folder `~/.vocabbot/`. Nothing else holds
a copy made by VocabBot.
