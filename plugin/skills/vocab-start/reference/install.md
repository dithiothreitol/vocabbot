# The vocabbot program in a terminal

The program has the same commands as the engine in this skill and a
coloured session, `vocabbot drill`, with one key per grade.

With uv (https://docs.astral.sh/uv/):

```
uv tool install vocabbot
vocabbot drill
```

Before the package is on PyPI, install it from the repository:

```
uv tool install git+https://github.com/dithiothreitol/vocabbot
```

With pipx: `pipx install vocabbot`. With pip only:
`python -m pip install --user vocabbot`.

Without installing anything, the engine file of this skill runs the same
session in plain text:

```
python "<this skill's folder>/bin/vocabbot.pyz" drill
```

The program finds the learner's folder from the pointer saved by `init`
(`~/.vocabbot/config.json`). On a second computer with the same synced
folder, `vocabbot use <folder>` saves the pointer once; `--learner <folder>`
or the environment variable `VOCABBOT_HOME` point to a folder for one call
or one shell.

Show the command that fits the learner's computer and run it only after
their yes. On Windows, `python3` can be a Microsoft Store alias that runs
nothing; `python --version` or `py -3 --version` shows a working Python.
