"""The confirmation gate: a commit and a direct write go to the host's permission prompt."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from conftest import make_learner, moment

from vocabbot import plans
from vocabbot.courses import Catalog

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / "plugin" / "hooks"
_spec = importlib.util.spec_from_file_location("vocabbot_gate_hook", HOOKS / "gate.py")
assert _spec is not None and _spec.loader is not None
gate_hook = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gate_hook
sys.dont_write_bytecode = True  # no __pycache__ inside the plugin
_spec.loader.exec_module(gate_hook)
sys.dont_write_bytecode = False

MONDAY = date(2026, 11, 16)


def bash(command: str, cwd: Path) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def test_a_commit_asks_and_shows_the_preview(tmp_path: Path, catalog: Catalog) -> None:
    learner = make_learner(tmp_path / "nauka", ["de:a1-a2"])
    preview = plans.set_preview(learner, catalog, ["new_per_day=20"], moment(MONDAY))
    command = f'python3 "/x/bin/vocabbot.pyz" commit --confirm {preview["token"]} --json'
    reason = gate_hook.decide(bash(command, learner.root))
    assert reason is not None
    assert "new_per_day: 15 → 20" in reason
    assert "plan.json" in reason
    elsewhere = gate_hook.decide(bash(command + f' --learner "{learner.root}"', tmp_path))
    assert elsewhere is not None and "new_per_day" in elsewhere
    unknown = gate_hook.decide(bash("vocabbot commit --confirm 0123456789abcdef", tmp_path))
    assert unknown == gate_hook.TEXT["unknown"]


def test_other_calls_pass(tmp_path: Path) -> None:
    for command in ("python3 vocabbot.pyz today --json", "git commit -m x", "ls"):
        assert gate_hook.decide(bash(command, tmp_path)) is None
    write = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "notes.md")}}
    assert gate_hook.decide(write) is None


def test_a_direct_write_into_a_learner_folder_asks(tmp_path: Path) -> None:
    learner = make_learner(tmp_path / "nauka", ["de:a1"])
    target = learner.root / "log" / "reviews.jsonl"
    reason = gate_hook.decide({"tool_name": "Edit", "tool_input": {"file_path": str(target)}})
    assert reason is not None and "log/reviews.jsonl" in reason


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs sh")
def test_the_shell_wrapper_runs_the_gate(tmp_path: Path) -> None:
    learner = make_learner(tmp_path / "nauka", ["de:a1"])
    target = str(learner.root / "registers" / "plan.json")
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": target}})
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run(
        ["sh", str(HOOKS / "gate.sh")], input=payload, capture_output=True, text=True, env=env
    )
    answer = json.loads(done.stdout)
    assert answer["hookSpecificOutput"]["permissionDecision"] == "ask"
    quiet = subprocess.run(
        ["sh", str(HOOKS / "gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**env, "VOCABBOT_HOOK": "off"},
    )
    assert quiet.stdout.strip() == ""
