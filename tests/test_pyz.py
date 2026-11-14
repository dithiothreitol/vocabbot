"""vocabbot.pyz runs a whole day without any installed library."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build  # noqa: E402

DAY = "2026-11-16"


@pytest.fixture(scope="module")
def pyz(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build.build_pyz(tmp_path_factory.mktemp("pyz") / "vocabbot.pyz")


def run(
    pyz: Path, *argv: str, stdin: str = "", env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Run with -I (no user site, no PYTHON* variables) and -S (no site-packages at all)."""
    done = subprocess.run(
        [sys.executable, "-I", "-S", str(pyz), *argv, "--json"],
        input=stdin.encode("utf-8"),
        capture_output=True,
        env=env or dict(os.environ),
        check=False,
    )
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace") + done.stdout.decode(
        "utf-8", "replace"
    )
    data: dict[str, Any] = json.loads(done.stdout.decode("utf-8"))
    return data


def test_version_without_site_packages(pyz: Path) -> None:
    done = subprocess.run(
        [sys.executable, "-I", "-S", str(pyz), "--version"], capture_output=True, check=True
    )
    assert done.stdout.decode().startswith("vocabbot ")


def test_packaged_courses_inside_the_archive(pyz: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "VOCABBOT_COURSES"}
    result = run(pyz, "course", "check", env=env)
    assert result["ok"]
    assert set(result["counts"]) == {"de", "en", "es", "fr"}


def test_a_full_day_from_the_archive(pyz: Path, tmp_path: Path) -> None:
    folder = tmp_path / "nauka"
    token = run(pyz, "init", str(folder), "--lang", "de:a1-a2", "--lang", "es:a1-a2", "--new", "6")[
        "token"
    ]
    run(pyz, "commit", "--confirm", token)
    sys.path.insert(0, str(REPO / "src"))
    from vocabbot.courses import Catalog

    catalog = Catalog(REPO / "tests" / "fixtures" / "courses")
    while True:
        items = run(pyz, "next", "--count", "10", "--today", DAY)["items"]
        if not items:
            break
        lines = [
            json.dumps(
                {"card": i["card"], "answer": catalog.card(i["card"])["display"]},
                ensure_ascii=False,
            )
            for i in items
        ]
        result = run(pyz, "answer", "--batch", "--today", DAY, stdin="\n".join(lines))
        assert result["refused"] == 0
    status = run(pyz, "status", "--today", DAY)
    assert sum(info["cards"] for info in status["languages"].values()) == 6
    assert status["today"]["left"] == {"reviews": 0, "new": 0, "drill": 0}
