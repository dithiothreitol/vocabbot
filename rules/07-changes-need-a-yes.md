## A change needs the learner's yes

`init`, `plan set`, `words add` and `doctor --merge` or `--repair` return a
preview with a token and change nothing. Show the preview lines as they are,
ask whether to save them, and end your turn there. Only after the learner's
explicit yes to that preview, in their next message, run
`commit --confirm <token> --json`. A request that already lists every
setting is not a yes: the learner has not seen the preview yet. A token is
valid for 30 minutes and for the files as they were at the preview; after
that, or after any other change, make a new preview. Never run `commit` in
the same turn as its preview, and never on a yes given to something else.
