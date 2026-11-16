from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from vocabbot import store
from vocabbot.courses import Catalog

FIXTURES = Path(__file__).parent / "fixtures"
COURSES = FIXTURES / "courses"


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test reads the starter course from the fixtures and keeps its pointer in tmp."""
    monkeypatch.setenv("VOCABBOT_COURSES", str(COURSES))
    monkeypatch.setenv("VOCABBOT_CONFIG", str(tmp_path / "config"))
    monkeypatch.setenv("VOCABBOT_FSYNC", "0")
    monkeypatch.delenv("VOCABBOT_HOME", raising=False)


@pytest.fixture
def catalog() -> Catalog:
    return Catalog(COURSES)


def entry_of(catalog: Catalog, lang: str, number: int) -> dict[str, Any]:
    entry = catalog.entry(f"{lang}-c{90000 + number:05d}")
    assert entry is not None
    return entry


def card_of(lang: str, number: int, direction: str = "p") -> str:
    return f"{lang}-c{90000 + number:05d}#{direction}"


def make_learner(root: Path, languages: list[str], **settings: Any) -> store.Learner:
    """A learner folder written directly, without the preview of init.

    New words are shown before their question unless a test asks otherwise, so
    a scripted learner who answers them right learns them (`new_words: ask`,
    the default of a plan, takes such an answer as a word known before).
    """
    settings.setdefault("new_words", "show")
    plan = store.complete_plan(
        {"languages": [store.parse_language(s) for s in languages], **settings}
    )
    store.write_text(root / store.PLAN, store.dump_json(plan))
    return store.Learner(root)


def moment(day: date, second: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=second
    )


def correct(catalog: Catalog, card: str) -> str:
    entry = catalog.card(card)
    assert entry is not None
    return str(entry["display"])
