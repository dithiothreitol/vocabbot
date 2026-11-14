"""The one error type the engine raises for a learner to read."""

from __future__ import annotations

from typing import Any

from vocabbot import assets


class VocabError(Exception):
    """A refusal or a problem the learner can act on.

    `code` is stable for programs (the skills read it); the message comes from
    the interface texts in the base language.
    """

    def __init__(self, code: str, **params: Any) -> None:
        self.code = code
        self.params = params
        super().__init__(assets.text(f"errors.{code}", **params))

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": str(self)}
        if self.params:
            out["details"] = {k: v for k, v in self.params.items() if _plain(v)}
        return out


def _plain(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, list, dict)) or value is None
