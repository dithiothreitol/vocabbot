"""The `vocabbot-server` program: run the server and look after its accounts.

    vocabbot-server serve --url https://vocab.example.org --data /var/lib/vocabbot
    vocabbot-server invite [--uses N] [--days N] [--note TEXT]
    vocabbot-server accounts
    vocabbot-server password LOGIN        (the new password on standard input)
    vocabbot-server delete LOGIN --yes

Every option has an environment variable as its default (VOCABBOT_SERVER_URL,
VOCABBOT_SERVER_DATA, VOCABBOT_SERVER_TIMEZONE, VOCABBOT_SERVER_OPEN_SIGNUP),
which suits a container.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from vocabbot import __version__

MISSING = (
    "vocabbot-server needs the packages of the server: pip install 'vocabbot[server]'"
    " (or uv tool install 'vocabbot[server]')"
)


def _when(moment: float | None) -> str:
    if moment is None:
        return "-"
    return datetime.fromtimestamp(moment, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_parser() -> argparse.ArgumentParser:
    env = os.environ.get
    parser = argparse.ArgumentParser(
        prog="vocabbot-server", description="VocabBot as a remote MCP server with accounts."
    )
    parser.add_argument("--version", action="version", version=f"vocabbot-server {__version__}")
    parser.add_argument(
        "--data",
        default=env("VOCABBOT_SERVER_DATA", "vocabbot-data"),
        help="the data folder: accounts.db and learners/ (default: ./vocabbot-data)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the server")
    serve.add_argument(
        "--url",
        default=env("VOCABBOT_SERVER_URL"),
        help="the public https address of the server, e.g. https://vocab.example.org",
    )
    serve.add_argument("--host", default=env("VOCABBOT_SERVER_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(env("VOCABBOT_SERVER_PORT", "8000")))
    serve.add_argument(
        "--timezone",
        default=env("VOCABBOT_SERVER_TIMEZONE", "Europe/Warsaw"),
        help="the time zone of the learning day (default Europe/Warsaw)",
    )
    serve.add_argument(
        "--open-signup",
        action="store_true",
        default=env("VOCABBOT_SERVER_OPEN_SIGNUP", "") in ("1", "true", "yes"),
        help="let anyone open an account without an invitation",
    )
    serve.add_argument(
        "--forwarded-allow-ips",
        default=env("VOCABBOT_SERVER_PROXIES", "127.0.0.1"),
        help="the reverse proxies whose X-Forwarded-For the server trusts",
    )

    invite = sub.add_parser("invite", help="create an invitation code")
    invite.add_argument("--uses", type=int, default=1, help="accounts it opens (default 1)")
    invite.add_argument("--days", type=float, default=14, help="days it is valid (default 14)")
    invite.add_argument("--note", default="", help="whom it is for, for your own list")

    sub.add_parser("accounts", help="list the accounts and the invitations")

    password = sub.add_parser("password", help="set a new password (read from standard input)")
    password.add_argument("login")

    delete = sub.add_parser("delete", help="delete an account and all its learning data")
    delete.add_argument("login")
    delete.add_argument("--yes", action="store_true", help="confirm the deletion")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from vocabbot.server.accounts import Registry, SignupError
        from vocabbot.server.config import Settings
    except ImportError:
        print(MISSING, file=sys.stderr)
        return 2
    data = Path(args.data).expanduser().resolve()
    if args.command == "serve":
        try:
            import uvicorn

            from vocabbot.server.app import build
        except ImportError:
            print(MISSING, file=sys.stderr)
            return 2
        if not args.url:
            print("serve needs --url (or VOCABBOT_SERVER_URL)", file=sys.stderr)
            return 2
        try:
            settings = Settings(
                url=args.url, data=data, timezone=args.timezone, open_signup=args.open_signup
            )
        except (ValueError, KeyError) as exc:
            print(f"vocabbot-server: {exc}", file=sys.stderr)
            return 2
        uvicorn.run(
            build(settings),
            host=args.host,
            port=args.port,
            proxy_headers=True,
            forwarded_allow_ips=args.forwarded_allow_ips,
            server_header=False,
            log_level="info",
        )
        return 0
    registry = Registry(data / "accounts.db")
    if args.command == "invite":
        code = registry.create_invite(uses=args.uses, days=args.days, note=args.note)
        print(code)
        return 0
    if args.command == "accounts":
        for row in registry.accounts():
            print(f"{row.login}\tcreated {_when(row.created)}\tseen {_when(row.seen)}")
        for invite in registry.invites():
            print(
                f"invitation\t{invite.note or '-'}\tuses left {invite.uses}"
                f"\tvalid until {_when(invite.expires)}"
            )
        return 0
    account = registry.find(args.login)
    if account is None:
        print(f"no account {args.login!r}", file=sys.stderr)
        return 1
    if args.command == "password":
        try:
            registry.set_password(account.id, sys.stdin.readline().rstrip("\r\n"))
        except SignupError:
            print("a password has 12 to 200 characters", file=sys.stderr)
            return 1
        print(f"new password for {account.login}; its connections were ended")
        return 0
    if not args.yes:
        print(f"delete {account.login} and all its learning data? Run again with --yes")
        return 1
    registry.delete_account(account.id)
    shutil.rmtree(data / "learners" / account.id, ignore_errors=True)
    print(f"deleted {account.login}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
