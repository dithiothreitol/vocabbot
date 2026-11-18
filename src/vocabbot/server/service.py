"""The engine for many accounts: one learner folder each, one call at a time per account.

A call runs a command of the `vocabbot` program through its own handler, so
the server returns the same JSON the plugin's skills read, with the same
guarantees: no answer before the grade, the engine grades, a change of the
plan only through a preview and its token. The learner's text (answers, own
words, notes) reaches the handler as the text of the call, never as an option.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timezone, tzinfo
from pathlib import Path
from typing import Any, NoReturn

from vocabbot import cli, plans, session, store, sync
from vocabbot.courses import Catalog
from vocabbot.errors import VocabError
from vocabbot.server.config import Settings

ACCOUNT = re.compile(r"^[0-9a-f]{32}$")
ASSIGNMENT = re.compile(r"^[a-z][a-z0-9_.]*=[^\n]+$")


@dataclass
class RemoteContext(cli.Context):
    """A command's context on the server: the account's folder, its time zone, its text."""

    root: Path = field(default_factory=Path)
    base: Catalog | None = None
    tz: tzinfo = timezone.utc
    given: str = ""

    def learner(self) -> store.Learner:
        if self._learner is None:
            if not (self.root / store.PLAN).is_file():
                raise VocabError("no_account_plan")
            self._learner = store.Learner(self.root.resolve())
        return self._learner

    def catalog(self) -> Catalog:
        if self._catalog is None:
            learner = self.root if (self.root / store.PLAN).is_file() else None
            self._catalog = Catalog(learner=learner, base=self.base)
        return self._catalog

    def courses(self) -> Catalog:
        return self.base if self.base is not None else Catalog()

    def day(self) -> date:
        """The learning day in the plan's time zone, or in the server's for a plan without one."""
        learner = self.learner()
        zone = learner.zone() or self.tz
        return store.learning_day(self.now, int(learner.plan()["day_starts_at"]), zone)

    def interactive(self) -> bool:
        return False

    def text(self) -> str:
        if not self.given.strip():
            raise VocabError("empty_stdin")
        return self.given

    def pending_folders(self) -> list[Path]:
        return [self.root / store.PENDING]


class Service:
    """Runs engine commands for the accounts of the server."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tz = settings.tzinfo()
        self.base = Catalog()
        self.base.installed()  # the courses are read once and shared by every account
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def folder(self, account: str) -> Path:
        if not ACCOUNT.match(account):
            raise ValueError("not an account id")
        return self.settings.learners / account

    def _lock(self, account: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(account, threading.Lock())

    def call(self, account: str, argv: list[str], text: str = "") -> dict[str, Any]:
        """Run one command for an account and return its JSON object."""
        root = self.folder(account)
        with self._lock(account):
            try:
                args = _parse([*argv, "--json"])
            except VocabError as exc:
                return self._out({"ok": False, "error": exc.as_dict()}, root)
            ctx = RemoteContext(
                args=args, now=session.now_utc(), root=root, base=self.base, tz=self.tz, given=text
            )
            return self._run(lambda: args.handler(ctx), root)

    def sync(self, account: str, payload: dict[str, Any], login: str, zone: str) -> dict[str, Any]:
        """One synchronisation of a linked folder with the account (see vocabbot.sync)."""
        root = self.folder(account)
        zone = zone if zone and store.zone_problem(zone) is None else self.settings.timezone
        expected = payload.get("account")
        if isinstance(expected, str) and expected and expected != login:
            # a folder linked to another account never joins this one
            error = VocabError("other_account", login=login, linked=expected)
            return {"ok": False, "error": error.as_dict()}
        with self._lock(account):
            try:
                out = sync.serve(
                    root,
                    payload,
                    lambda: Catalog(learner=root, base=self.base),
                    self.base.installed(),
                    session.now_utc(),
                    zone=zone,
                )
            except VocabError as exc:
                return {"ok": False, "error": exc.as_dict()}
            except OSError as exc:
                error = VocabError("io_error", path="", detail=exc.strerror or str(exc))
                return {"ok": False, "error": error.as_dict()}
        out["ok"] = True
        out["account"] = {"login": login, "timezone": zone}
        return out

    def export(self, account: str) -> bytes | None:
        """The account's record as a zip in the form of a learner's folder; None without a plan."""
        root = self.folder(account)
        with self._lock(account):
            if not (root / store.PLAN).is_file():
                return None
            return sync.archive(root, session.now_utc())

    def setup(
        self,
        account: str,
        languages: list[str],
        new_per_day: int,
        assignments: list[str],
        zone: str = "",
    ) -> dict[str, Any]:
        """The preview of the account's first plan; `commit` with its token saves it.

        `zone` is the account's time zone (read from the browser at sign-up); the plan
        gets it unless the settings name another.
        """
        root = self.folder(account)
        with self._lock(account):
            if (root / store.PLAN).is_file():
                return self._out(
                    {"ok": False, "error": VocabError("account_has_plan").as_dict()}, root
                )
            for assignment in assignments:
                if not ASSIGNMENT.match(assignment):
                    error = VocabError("bad_assignment", value=assignment[:80])
                    return self._out({"ok": False, "error": error.as_dict()}, root)
            named = any(a.startswith("timezone=") for a in assignments)
            if zone and store.zone(zone) is not None and not named:
                assignments = [*assignments, f"timezone={zone}"]
            if not languages:
                error = VocabError("bad_language_spec", value="")
                return self._out({"ok": False, "error": error.as_dict()}, root)
            root.mkdir(parents=True, exist_ok=True)
            return self._run(
                lambda: plans.init_preview(
                    root,
                    languages,
                    new_per_day,
                    self.base,
                    session.now_utc(),
                    assignments=assignments,
                    pending=root / store.PENDING,
                    pointer=False,
                ),
                root,
            )

    def remove(self, account: str) -> None:
        """Delete the account's folder, after any call of the account that runs now."""
        with self._lock(account):
            shutil.rmtree(self.folder(account), ignore_errors=True)

    def _run(self, work: Callable[[], dict[str, Any]], root: Path) -> dict[str, Any]:
        try:
            data = work()
        except VocabError as exc:
            return self._out({"ok": False, "error": exc.as_dict()}, root)
        except OSError as exc:
            error = VocabError(
                "io_error", path=str(exc.filename or ""), detail=exc.strerror or str(exc)
            )
            return self._out({"ok": False, "error": error.as_dict()}, root)
        except Exception as exc:  # one account's damaged data never takes the server down
            print(f"vocabbot-server: a call failed: {exc!r}", flush=True)
            error = VocabError("server_error", detail=type(exc).__name__)
            return self._out({"ok": False, "error": error.as_dict()}, root)
        return self._out({"ok": bool(data.get("ok", True)), **data}, root)

    def _out(self, data: dict[str, Any], root: Path) -> dict[str, Any]:
        cleaned: dict[str, Any] = _clean(json.loads(json.dumps(data, default=str)), _prefixes(root))
        return cleaned


class _Parser(argparse.ArgumentParser):
    """The program's parser that raises a mistake instead of printing it and exiting."""

    def error(self, message: str) -> NoReturn:
        raise VocabError("bad_arguments", detail=message[:200])

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        raise VocabError("bad_arguments", detail=(message or "").strip()[:200])


def _parse(argv: list[str]) -> argparse.Namespace:
    args = cli.build_parser(_Parser).parse_args(argv)
    if getattr(args, "handler", None) is None:
        raise VocabError("bad_arguments", detail=" ".join(argv[:2]))
    return args


def _prefixes(root: Path) -> list[tuple[str, str]]:
    """The account's folder as the engine may print it, and what replaces it."""
    pairs: list[tuple[str, str]] = []
    for form in {str(root), str(root.resolve()), root.as_posix(), root.resolve().as_posix()}:
        for sep in ("/", "\\"):
            pairs.append((form + sep, ""))
    for form in {str(root), str(root.resolve()), root.as_posix(), root.resolve().as_posix()}:
        pairs.append((form, "VocabBot"))
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def _clean(value: Any, prefixes: list[tuple[str, str]]) -> Any:
    """Every mention of the account's folder, with the server's paths, made relative."""
    if isinstance(value, str):
        for old, new in prefixes:
            if old in value:
                value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_clean(item, prefixes) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item, prefixes) for key, item in value.items()}
    return value
