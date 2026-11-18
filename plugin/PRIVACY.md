# Privacy

**English** · [Polski](PRIVACY.pl.md)

VocabBot is a set of instructions and one local program with its courses. It
needs no server and no account and has no analytics; the program sends
nothing over the network unless the learner links the folder to an account
on a VocabBot server.

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
- **An account, when the learner links one.** After `vocabbot login`, the
  folder synchronises with the account on the server the learner chose: the
  rows of the log with the typed answers, notes, own words, reports and
  changes of the plan go there, and the account's rows come back. The
  program keeps its tokens in `~/.vocabbot/credentials.json`, readable by the
  owner only; `vocabbot logout` ends the connection. The server keeps the
  data as its privacy page (`/privacy`) says.

## What VocabBot keeps out

VocabBot asks for no name, address or other personal detail; an account on a
server may keep an e-mail address for password recovery, only as a hash and
only when the learner gives one. The log holds the answers to vocabulary
questions with their times.

## Removing data

Delete the learner's folder and the folder `~/.vocabbot/`. Nothing else holds
a copy made by VocabBot, apart from an account the learner linked: the
account page of its server removes the account with all its data.
