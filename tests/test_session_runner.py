"""The session test runner catches a leaked answer, a grade not from the engine and a write
without a yes, with scripted replies instead of a model."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from vocabbot import plans, session, store
from vocabbot.courses import Catalog
from vocabbot.queue import compute

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "vocabbot_session_test", REPO / "scripts" / "session_test.py"
)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
# dataclasses on Python 3.10 look their module up in sys.modules
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)


@pytest.fixture(autouse=True)
def packaged_courses(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sessions run on the packaged courses, as the plugin does."""
    monkeypatch.delenv("VOCABBOT_COURSES", raising=False)


def load(name: str) -> dict[str, Any]:
    return runner.load(REPO / "sessions" / f"{name}.json")


def waiting_items(folder: Path) -> list[Any]:
    learner = store.Learner(folder)
    dp = compute(learner, Catalog(learner=folder), runner.learning_day())
    return [item for item in dp.sequence if item.phase != "new"][:5]


def ask(folder: Path) -> str:
    """A good first turn: meanings only."""
    return "\n".join(
        f"{n}. {item.entry['gloss']['pl']}" for n, item in enumerate(waiting_items(folder), 1)
    )


def leak(folder: Path) -> str:
    """A bad first turn: one answer shown with its question."""
    item = next(i for i in waiting_items(folder) if len(str(i.entry["display"])) >= 4)
    return f"1. {item.entry['gloss']['pl']} (podpowiedź: {item.entry['display']})"


def skip_all(folder: Path) -> str:
    learner = store.Learner(folder)
    catalog = Catalog(learner=folder)
    day = runner.learning_day()
    for item in waiting_items(folder):
        session.answer(learner, catalog, day, datetime.now(timezone.utc), item.card, "")
    return "Zapisane, wszystkie jako „nie wiem”."


def test_a_session_that_keeps_the_rules_passes() -> None:
    result = runner.run_session(
        load("session-no-answer-leak"), runner.ScriptedHost([ask, skip_all])
    )
    assert result["passed"], result


def test_a_leaked_answer_fails() -> None:
    result = runner.run_session(
        load("session-no-answer-leak"), runner.ScriptedHost([leak, skip_all])
    )
    assert not result["passed"]
    assert any("answer shown before its grade" in f for f in result["turns"][0]["fails"])


def test_a_plan_written_without_a_yes_fails() -> None:
    def commit_at_once(folder: Path) -> str:
        learner = store.Learner(folder)
        now = datetime.now(timezone.utc)
        preview = plans.set_preview(learner, Catalog(learner=folder), ["new_per_day=20"], now)
        from vocabbot import gate

        gate.commit(preview["token"], [learner.path(store.PENDING)], now, via="token")
        return "Zmieniono plan na 20 nowych słów."

    result = runner.run_session(
        load("plan-change-needs-yes"),
        runner.ScriptedHost([commit_at_once, lambda folder: "Dobrze."]),
    )
    assert not result["passed"]
    fails = result["turns"][0]["fails"]
    assert "the plan changed" in fails
    assert any(f.startswith("decisions added") for f in fails)


def test_every_session_file_is_valid() -> None:
    for path in sorted((REPO / "sessions").glob("*.json")):
        assert runner.lint(json.loads(path.read_text(encoding="utf-8")), path.name) == []
