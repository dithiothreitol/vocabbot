"""The repository checks: versions, engine calls taught by skills, direct writes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "vocabbot_validate_script", REPO / "scripts" / "validate.py"
)
assert _spec is not None and _spec.loader is not None
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)


def test_package_versions_map_to_semver() -> None:
    assert validate.semver_of("1.0.0rc1") == "1.0.0-rc.1"
    assert validate.semver_of("1.0.0") == "1.0.0"
    assert validate.semver_of("1.2.3.dev2") == "1.2.3-dev.2"
    assert validate.semver_of("1.0.0b3") == "1.0.0-beta.3"


def test_taught_calls_are_checked_against_the_program() -> None:
    known = validate.commands()
    validate.errors.clear()
    text = "\n".join(
        [
            "Run `today --json` first.",
            "```",
            'python3 "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" answer --batch --stdin --json'
            " <<'EOF'",
            "```",
            "Then `plan set new_per_day=10 --json` and `next --count 10 --ahead 3 --json`.",
        ]
    )
    calls = validate.taught_calls(text)
    assert calls[0] == "today --json"
    for call in calls:
        validate.check_call(call, known, "x.md")
    assert validate.errors == []
    for bad in ("tomorrow --json", "next --bogus --json", "plan erase --json"):
        validate.check_call(bad, known, "x.md")
    assert len(validate.errors) == 3
    validate.errors.clear()


def test_direct_writes_to_the_learners_files_are_found() -> None:
    assert validate.DIRECT_WRITE.search('echo "{}" >> log/reviews.jsonl')
    assert validate.DIRECT_WRITE.search("Use Edit on registers/plan.json")
    assert not validate.DIRECT_WRITE.search("`plan set new_per_day=10 --json`")
