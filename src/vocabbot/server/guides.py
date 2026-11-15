"""What the model in a chat application needs to run VocabBot: the rules, a guide per topic, labels.

The guides follow the plugin's skills, with the tools in place of the
commands, so a learner meets the same session in Claude Code, in Codex and in
a chat application connected to the server.
"""

from __future__ import annotations

from importlib import resources

from vocabbot import assets

TOPICS = ("session", "start", "coach", "words")
LABELS = (
    ("grades", "Grades (`grade`)"),
    ("error_classes", "Error classes (`errors`)"),
    ("pos", "Parts of speech (`pos`)"),
    ("genders", "Genders (`gender`)"),
    ("forms", "Forms (`forms`)"),
    ("phases", "Phases (`phase`)"),
)

INSTRUCTIONS = """\
VocabBot runs the learner's vocabulary course in one to three languages at once \
(English, German, Spanish, French; levels A1 to B2) for a Polish speaker, with spaced \
repetition. The engine behind these tools grades every answer and sets every due date; \
its results are the only source of cards, grades and numbers.

Before the first VocabBot step of a conversation, call vocab_guide with the topic that \
fits and follow it: session (the daily session: reviews, new words, the drill), start \
(setup, the placement test, changes of the plan), coach (explanations, mnemonics, \
mix-ups, the weekly review) or words (own words and reports of mistakes). Talk to the \
learner in Polish."""


def _read(name: str) -> str:
    return (resources.files("vocabbot.server") / "guides" / name).read_text(encoding="utf-8")


def labels() -> str:
    texts = assets.read_json(assets.data_root() / "i18n" / "pl.json")
    lines = ["# Labels in Polish", "", "The engine's codes and the words the learner reads."]
    for key, title in LABELS:
        lines += ["", f"## {title}", "", "| Code | Polish |", "|---|---|"]
        lines += [f"| `{code}` | {label} |" for code, label in texts[key].items()]
    return "\n".join(lines)


def guide(topic: str) -> str:
    if topic not in TOPICS:
        raise ValueError(f"unknown topic {topic!r}; the topics are {', '.join(TOPICS)}")
    parts = [_read("rules.md").strip(), _read(f"{topic}.md").strip(), labels()]
    return "\n\n".join(parts) + "\n"
