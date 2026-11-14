"""Build vocabbot.pyz: the engine and the courses in one file that needs only Python.

    python scripts/build.py pyz [--out build/vocabbot.pyz]

The archive holds src/vocabbot without compiled files and a __main__.py that
returns the program's exit code. It runs with `python vocabbot.pyz <command>`.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "src" / "vocabbot"
MAIN = "import sys\n\nfrom vocabbot.cli import main\n\nsys.exit(main())\n"


def build_pyz(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "app"
        shutil.copytree(
            SOURCE, staging / "vocabbot", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        (staging / "__main__.py").write_bytes(MAIN.encode("utf-8"))
        zipapp.create_archive(staging, out, interpreter="/usr/bin/env python3", compressed=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="target", required=True)
    pyz = sub.add_parser("pyz", help="build vocabbot.pyz")
    pyz.add_argument("--out", type=Path, default=REPO / "build" / "vocabbot.pyz")
    args = parser.parse_args(argv)
    path = build_pyz(args.out)
    print(f"{path} ({path.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
