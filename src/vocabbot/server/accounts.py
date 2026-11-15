"""Accounts, invitations and the OAuth records of the server, in one SQLite file.

Passwords are kept as scrypt hashes; invitation codes, sign-in requests,
authorization codes and tokens only as SHA-256 hashes, so a copy of the file
opens no account and no connection.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path

LOGIN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
PASSWORD_MIN = 12
PASSWORD_MAX = 200
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
# invitation codes avoid letters and digits that look alike
INVITE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created REAL NOT NULL,
    seen REAL
);
CREATE TABLE IF NOT EXISTS invites (
    hash TEXT PRIMARY KEY,
    created REAL NOT NULL,
    expires REAL NOT NULL,
    uses INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    info TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    hash TEXT PRIMARY KEY,
    client TEXT NOT NULL,
    params TEXT NOT NULL,
    expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS codes (
    hash TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    client TEXT NOT NULL,
    account TEXT NOT NULL,
    scopes TEXT NOT NULL,
    resource TEXT,
    grant_id TEXT NOT NULL,
    expires REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS tokens_grant ON tokens (grant_id);
CREATE INDEX IF NOT EXISTS tokens_account ON tokens (account);
"""


class SignupError(Exception):
    """A sign-up or a password the server refuses; `code` names the reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Account:
    id: str
    login: str
    created: float
    seen: float | None


@dataclass(frozen=True)
class Invite:
    created: float
    expires: float
    uses: int
    note: str


@dataclass(frozen=True)
class TokenRow:
    kind: str  # access or refresh
    client: str
    account: str
    scopes: list[str]
    resource: str | None
    grant: str  # the sign-in the token comes from; a refresh keeps it
    expires: float


def digest(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(key)}"


def check_password(password: str, stored: str) -> bool:
    try:
        kind, n, r, p, salt, key = stored.split("$")
        expected = base64.b64decode(key)
        got = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return kind == "scrypt" and hmac.compare_digest(got, expected)


@cache
def _dummy() -> str:
    """A hash to check an unknown login against, so its answer takes as long as a known one."""
    return hash_password(secrets.token_hex(PASSWORD_MIN))


def normalize_login(login: str) -> str:
    return login.strip().lower()


def normalize_invite(code: str) -> str:
    return "".join(ch for ch in code.lower() if ch in INVITE_ALPHABET)


@contextmanager
def _transaction(db: sqlite3.Connection) -> Iterator[None]:
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        db.execute("ROLLBACK")
        raise
    db.execute("COMMIT")


class Registry:
    """The server's SQLite file; every call opens its own short connection."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            yield db
        finally:
            db.close()

    # ------------------------------------------------------------ accounts

    def signup(self, login: str, password: str, invite: str | None, open_signup: bool) -> Account:
        """A new account; without open sign-up it uses one use of a valid invitation."""
        login = normalize_login(login)
        if not LOGIN.match(login):
            raise SignupError("bad_login")
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise SignupError("bad_password")
        stored = hash_password(password)
        now = time.time()
        with self._db() as db, _transaction(db):
            if not open_signup:
                code = digest(normalize_invite(invite or ""))
                row = db.execute(
                    "SELECT uses, expires FROM invites WHERE hash = ?", (code,)
                ).fetchone()
                if not invite or row is None or row[0] < 1 or row[1] < now:
                    raise SignupError("bad_invite")
            if db.execute("SELECT 1 FROM accounts WHERE login = ?", (login,)).fetchone():
                raise SignupError("login_taken")
            if not open_signup:
                db.execute("UPDATE invites SET uses = uses - 1 WHERE hash = ?", (code,))
            account = Account(uuid.uuid4().hex, login, now, None)
            db.execute(
                "INSERT INTO accounts (id, login, password, created) VALUES (?, ?, ?, ?)",
                (account.id, account.login, stored, account.created),
            )
        return account

    def verify(self, login: str, password: str) -> Account | None:
        with self._db() as db:
            row = db.execute(
                "SELECT id, login, password, created, seen FROM accounts WHERE login = ?",
                (normalize_login(login),),
            ).fetchone()
        if row is None:
            check_password(password, _dummy())
            return None
        if not check_password(password, row[2]):
            return None
        return Account(row[0], row[1], row[3], row[4])

    def account(self, account_id: str) -> Account | None:
        with self._db() as db:
            row = db.execute(
                "SELECT id, login, created, seen FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
        return Account(*row) if row else None

    def find(self, login: str) -> Account | None:
        with self._db() as db:
            row = db.execute(
                "SELECT id, login, created, seen FROM accounts WHERE login = ?",
                (normalize_login(login),),
            ).fetchone()
        return Account(*row) if row else None

    def accounts(self) -> list[Account]:
        with self._db() as db:
            rows = db.execute("SELECT id, login, created, seen FROM accounts ORDER BY created")
            return [Account(*row) for row in rows.fetchall()]

    def set_password(self, account_id: str, password: str) -> None:
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise SignupError("bad_password")
        stored = hash_password(password)
        with self._db() as db, _transaction(db):
            db.execute("UPDATE accounts SET password = ? WHERE id = ?", (stored, account_id))
            # a new password ends every connection made with the old one
            db.execute("DELETE FROM tokens WHERE account = ?", (account_id,))

    def delete_account(self, account_id: str) -> None:
        with self._db() as db, _transaction(db):
            db.execute("DELETE FROM tokens WHERE account = ?", (account_id,))
            db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def touch(self, account_id: str, now: float) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE accounts SET seen = ? WHERE id = ? AND (seen IS NULL OR seen < ?)",
                (now, account_id, now - 60),
            )

    # ------------------------------------------------------------ invitations

    def create_invite(self, uses: int = 1, days: float = 14, note: str = "") -> str:
        if uses < 1 or days <= 0:
            raise ValueError("an invitation needs at least one use and a positive lifetime")
        raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(12))
        now = time.time()
        with self._db() as db:
            db.execute(
                "INSERT INTO invites (hash, created, expires, uses, note) VALUES (?, ?, ?, ?, ?)",
                (digest(raw), now, now + days * 86400, uses, note),
            )
        # shown in capitals, which read and copy better; any case is accepted
        return "-".join(raw[i : i + 4] for i in range(0, 12, 4)).upper()

    def invites(self) -> list[Invite]:
        with self._db() as db:
            rows = db.execute("SELECT created, expires, uses, note FROM invites ORDER BY created")
            return [Invite(*row) for row in rows.fetchall()]

    # ------------------------------------------------------------ OAuth clients

    def save_client(self, client_id: str, info: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO clients (id, info, created) VALUES (?, ?, ?)",
                (client_id, info, time.time()),
            )

    def client(self, client_id: str) -> str | None:
        with self._db() as db:
            row = db.execute("SELECT info FROM clients WHERE id = ?", (client_id,)).fetchone()
        return str(row[0]) if row else None

    # ------------------------------------------------------------ sign-in requests

    def save_request(self, client_id: str, params: str, ttl: float) -> str:
        request_id = secrets.token_urlsafe(24)
        with self._db() as db:
            db.execute(
                "INSERT INTO requests (hash, client, params, expires) VALUES (?, ?, ?, ?)",
                (digest(request_id), client_id, params, time.time() + ttl),
            )
        return request_id

    def request(self, request_id: str) -> tuple[str, str] | None:
        """The client and the parameters of a sign-in that waits for the learner."""
        with self._db() as db:
            row = db.execute(
                "SELECT client, params FROM requests WHERE hash = ? AND expires > ?",
                (digest(request_id), time.time()),
            ).fetchone()
        return (str(row[0]), str(row[1])) if row else None

    def drop_request(self, request_id: str) -> bool:
        with self._db() as db:
            done = db.execute("DELETE FROM requests WHERE hash = ?", (digest(request_id),))
            return done.rowcount == 1

    # ------------------------------------------------------------ authorization codes

    def save_code(self, code: str, data: str, expires: float) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO codes (hash, data, expires) VALUES (?, ?, ?)",
                (digest(code), data, expires),
            )

    def code(self, code: str) -> str | None:
        with self._db() as db:
            row = db.execute(
                "SELECT data FROM codes WHERE hash = ? AND expires > ?", (digest(code), time.time())
            ).fetchone()
        return str(row[0]) if row else None

    def take_code(self, code: str) -> bool:
        """Remove a code; True only for the one call that removed it (a code is used once)."""
        with self._db() as db:
            return db.execute("DELETE FROM codes WHERE hash = ?", (digest(code),)).rowcount == 1

    # ------------------------------------------------------------ tokens

    def save_token(self, token: str, row: TokenRow) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO tokens (hash, kind, client, account, scopes, resource, grant_id,"
                " expires) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    digest(token),
                    row.kind,
                    row.client,
                    row.account,
                    " ".join(row.scopes),
                    row.resource,
                    row.grant,
                    row.expires,
                ),
            )

    def token(self, token: str, kind: str) -> TokenRow | None:
        with self._db() as db:
            row = db.execute(
                "SELECT kind, client, account, scopes, resource, grant_id, expires FROM tokens"
                " WHERE hash = ? AND kind = ? AND expires > ?",
                (digest(token), kind, time.time()),
            ).fetchone()
        if row is None:
            return None
        return TokenRow(row[0], row[1], row[2], str(row[3]).split(), row[4], row[5], row[6])

    def take_token(self, token: str, kind: str) -> TokenRow | None:
        """Remove a token and return it; None when another call removed it first."""
        found = self.token(token, kind)
        if found is None:
            return None
        with self._db() as db:
            done = db.execute(
                "DELETE FROM tokens WHERE hash = ? AND kind = ?", (digest(token), kind)
            )
        return found if done.rowcount == 1 else None

    def drop_grant(self, grant: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM tokens WHERE grant_id = ?", (grant,))

    def purge(self, now: float | None = None) -> int:
        """Remove expired sign-in requests, codes and tokens."""
        now = time.time() if now is None else now
        removed = 0
        with self._db() as db:
            for table in ("requests", "codes", "tokens"):
                removed += db.execute(f"DELETE FROM {table} WHERE expires <= ?", (now,)).rowcount
        return removed
