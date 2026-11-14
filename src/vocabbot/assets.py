"""Data shipped inside the package: language rules, interface texts and courses.

Everything is read through importlib.resources, so the same code works from an
installed package and from vocabbot.pyz. VOCABBOT_COURSES points the engine at
another course folder (the tests use it).
"""

from __future__ import annotations

import json
import os
import sys
from functools import cache
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from importlib.resources.abc import Traversable
    else:
        from importlib.abc import Traversable

    Resource = Traversable | Path


def data_root() -> Resource:
    return resources.files("vocabbot") / "data"


def course_root() -> Resource:
    override = os.environ.get("VOCABBOT_COURSES")
    if override:
        return Path(override)
    return data_root() / "courses"


def read_json(resource: Resource) -> Any:
    return json.loads(resource.read_text(encoding="utf-8"))


@cache
def language(code: str) -> dict[str, Any]:
    """Answer rules and display data of one language (data/lang/<code>.json)."""
    resource = data_root() / "lang" / f"{code}.json"
    if not resource.is_file():
        raise KeyError(code)
    data: dict[str, Any] = read_json(resource)
    return data


@cache
def known_languages() -> tuple[str, ...]:
    folder = data_root() / "lang"
    return tuple(sorted(item.name[:-5] for item in folder.iterdir() if item.name.endswith(".json")))


@cache
def _texts() -> dict[str, Any]:
    data: dict[str, Any] = read_json(data_root() / "i18n" / "pl.json")
    return data


def text(name: str, /, **values: Any) -> str:
    """Interface text in the base language, with {placeholders} filled in."""
    node: Any = _texts()
    for part in name.split("."):
        if not isinstance(node, dict) or part not in node:
            return name
        node = node[part]
    if not isinstance(node, str):
        return name
    return node.format(**values) if values else node


def language_name(code: str) -> str:
    try:
        return str(language(code)["name"]["pl"])
    except KeyError:
        return code
