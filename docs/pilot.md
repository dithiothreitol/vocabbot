# Pilot protocol

**English** · [Polski](pilot.pl.md)

The pilot is the last condition of version 1.0 (section 1 of the plan,
condition 7): two weeks of daily learning in two or three languages, in the
chat and in the terminal, end without an open blocking defect. The pilot runs
on version 1.0.0-rc.2.

## Before the first session

- **VocabBot 1.0.0-rc.2** installed as a plugin in Claude Code (and in Codex
  CLI, if the pilot covers Codex) and as the `vocabbot` program
  (`uv tool install vocabbot`, from PyPI). `vocabbot --version` shows it.
- **A learning folder outside the repository**, best in a synced folder such
  as `OneDrive/VocabBot`. A learner's folder never enters the repository.
- **Python 3.10 or later** on the PATH; `python --version` answers.
- **This file and a notes file** side by side, following the template below.

## Scenarios

| # | Scenario | Request or command | What to check |
|---|---|---|---|
| 1 | Setup with a test | "skonfiguruj VocabBota", a test for one language | the test shows questions without answers; one yes creates the plan; the forecast comes from the engine |
| 2 | Session in the chat | "sesja" on three days | batches of about 10 cards; no answer before its grade; the drill at the end |
| 3 | Session in the terminal | `vocabbot drill` on three days | typing ä, ß, ñ, é, ç; the grade keys; stopping with q |
| 4 | Switching during a day | start in the chat, finish in the terminal | the same order, no card twice |
| 5 | A word known before the course | "to słowo znałem" | "znałem" only at the first showing; the daily limit unchanged |
| 6 | A changed grade | "to była literówka, zalicz" | only that card changes; the row is marked in the log |
| 7 | Own words | a text or a photo of a page | a preview split into own, moved and left-out words; written after the yes |
| 8 | A mistake in an entry | "to tłumaczenie jest złe" | the card leaves the queue until the report is withdrawn |
| 9 | A plan change | "mniej nowych słów", "dodaj trzeci język" | a preview, the yes, a new forecast |
| 10 | The coach | "przegląd tygodnia", "ciągle mylę …" | numbers match `vocabbot status`; the model's content is marked as generated |
| 11 | A day off and a backlog | a day without learning, then a session | the reviews come on the next day; the forecast follows |
| 12 | Two computers | the same folder on a second computer (`vocabbot use`) | one shared state; `vocabbot doctor` finds conflict copies and joins them after a yes |

## Measures

| Measure | Target | How |
|---|---|---|
| Answers shown before their grade | 0 | watching every batch in the chat |
| Grades not from the engine | 0 | `vocabbot status` (share of changed grades) and own changes |
| Changes without a yes | 0 | every line of `log/decisions.md` matches a yes |
| Wrong entries | recorded | `flag` reports with a note; the Stage 2 targets are at most 3% for A1–A2 and 5% for B1–B2 |
| Minutes a day | recorded | compared with `vocabbot forecast` |
| Recall over 30 days | close to 90% | `vocabbot status` after two weeks |

## Defects

**Blocking:** an answer shown before its grade, a grade or a due date not from
the engine, a write without a yes, a lost or damaged log, a crash that stops
a session. Each is reproduced on synthetic data and gets a test and a fix
before version 1.0.

**Not blocking:** wording, the order of information, a wrong entry for a
single word, slowness. Each is recorded and fixed when the fix is cheap;
wrong entries go back to the course pipeline.

## Notes template

Notes describe what happened in your own words and hold no personal data.

```
Scenario: 2 · session in the chat
Date: <day> · Host: Claude Code <version> · Model: <model>
What I asked for:
What happened:
What I expected:
Blocking: yes / no
Card or entry (the id from the result):
```

## End of the pilot

The pilot ends after two weeks of learning, when every scenario has been run
(a scenario that does not fit gets a note), no blocking defect is open and
the measures are recorded. The notes start the work on version 1.0.
