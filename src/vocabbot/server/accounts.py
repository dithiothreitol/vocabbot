"""Accounts, invitations and the OAuth records of the server, in one SQLite file.

Passwords and the optional e-mail address for password recovery are kept as
scrypt hashes; invitation codes, sign-in requests, authorization codes,
tokens, device codes, browser sessions and recovery links only as SHA-256
hashes, so a copy of the file opens no account and no connection and names no
address.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
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
CREATE TABLE IF NOT EXISTS grants (
    id TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    client TEXT NOT NULL,
    created REAL NOT NULL,
    used REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS grants_account ON grants (account);
CREATE TABLE IF NOT EXISTS sessions (
    hash TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    created REAL NOT NULL,
    expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    hash TEXT PRIMARY KEY,
    user_code TEXT NOT NULL UNIQUE,
    client TEXT NOT NULL,
    account TEXT,
    expires REAL NOT NULL,
    polled REAL
);
CREATE TABLE IF NOT EXISTS resets (
    hash TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    expires REAL NOT NULL
);
"""
# columns added to tables of an earlier version, with their definitions
COLUMNS = (("accounts", "email", "TEXT"), ("accounts", "timezone", "TEXT"))
SESSION_TTL = 30 * 86400
DEVICE_TTL = 900
DEVICE_INTERVAL = 5
RESET_TTL = 1800
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")


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
class Grant:
    """One connection of an account: a chat application, the program on a computer."""

    id: str
    client: str
    name: str
    created: float
    used: float


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


def normalize_email(address: str) -> str:
    return address.strip().lower()


def valid_email(address: str) -> bool:
    return bool(EMAIL.match(normalize_email(address)))


def short_code(length: int = 8) -> str:
    """A code to type: ABCD-EFGH, without letters and digits that look alike."""
    raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(length))
    return "-".join(raw[i : i + 4] for i in range(0, length, 4)).upper()


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
            for table, column, kind in COLUMNS:
                present = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                if column not in present:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
            # connections made before the account page existed are listed on it too
            now = time.time()
            db.execute(
                "INSERT OR IGNORE INTO grants (id, account, client, created, used)"
                " SELECT grant_id, account, client, ?, ? FROM tokens GROUP BY grant_id",
                (now, now),
            )

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
            # a new password ends every connection and browser session made with the old one
            for table in ("tokens", "grants", "sessions", "resets", "devices"):
                db.execute(f"DELETE FROM {table} WHERE account = ?", (account_id,))

    def delete_account(self, account_id: str) -> None:
        with self._db() as db, _transaction(db):
            for table in ("tokens", "grants", "sessions", "resets", "devices"):
                db.execute(f"DELETE FROM {table} WHERE account = ?", (account_id,))
            db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    # ------------------------------------------------------------ e-mail and time zone

    def set_email(self, account_id: str, address: str | None) -> None:
        """Keep a hash of the address for password recovery, or with None forget it."""
        if address is not None and not valid_email(address):
            raise SignupError("bad_email")
        stored = hash_password(normalize_email(address)) if address else None
        with self._db() as db:
            db.execute("UPDATE accounts SET email = ? WHERE id = ?", (stored, account_id))

    def has_email(self, account_id: str) -> bool:
        with self._db() as db:
            row = db.execute("SELECT email FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return bool(row and row[0])

    def match_email(self, login: str, address: str) -> Account | None:
        """The account when the address is the one kept for it; as slow for any login."""
        with self._db() as db:
            row = db.execute(
                "SELECT id, login, created, seen, email FROM accounts WHERE login = ?",
                (normalize_login(login),),
            ).fetchone()
        if row is None or not row[4]:
            check_password(normalize_email(address), _dummy())
            return None
        if not check_password(normalize_email(address), row[4]):
            return None
        return Account(row[0], row[1], row[2], row[3])

    def set_timezone(self, account_id: str, zone: str, *, only_empty: bool = False) -> None:
        if not zone:
            return
        query = "UPDATE accounts SET timezone = ? WHERE id = ?"
        if only_empty:
            query += " AND (timezone IS NULL OR timezone = '')"
        with self._db() as db:
            db.execute(query, (zone, account_id))

    def timezone(self, account_id: str) -> str:
        with self._db() as db:
            row = db.execute("SELECT timezone FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return str(row[0]) if row and row[0] else ""

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
            db.execute("DELETE FROM grants WHERE id = ?", (grant,))

    def drop_grant_tokens(self, grant: str) -> None:
        """End the tokens of a connection and keep the connection (a refresh issues new ones)."""
        with self._db() as db:
            db.execute("DELETE FROM tokens WHERE grant_id = ?", (grant,))

    # ------------------------------------------------------------ connections (grants)

    def track_grant(self, grant: str, account: str, client: str, now: float) -> None:
        """Remember a connection when its first tokens are issued, and its latest use."""
        with self._db() as db:
            db.execute(
                "INSERT INTO grants (id, account, client, created, used) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET used = excluded.used",
                (grant, account, client, now, now),
            )

    def use_grant(self, grant: str, now: float) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE grants SET used = ? WHERE id = ? AND used < ?", (now, grant, now - 60)
            )

    def grants(self, account_id: str) -> list[Grant]:
        """The account's connections, the latest used first, with the application's name."""
        with self._db() as db:
            rows = db.execute(
                "SELECT g.id, g.client, c.info, g.created, g.used FROM grants g"
                " LEFT JOIN clients c ON c.id = g.client"
                " WHERE g.account = ? AND EXISTS"
                " (SELECT 1 FROM tokens t WHERE t.grant_id = g.id AND t.expires > ?)"
                " ORDER BY g.used DESC",
                (account_id, time.time()),
            ).fetchall()
        out = []
        for grant_id, client, info, created, used in rows:
            name = str(client)
            if info:
                try:
                    name = str(json.loads(info).get("client_name") or client)
                except (ValueError, AttributeError):
                    name = str(client)
            out.append(Grant(str(grant_id), str(client), name, float(created), float(used)))
        return out

    def drop_account_grant(self, account_id: str, grant: str) -> bool:
        """End one connection of the account; False for a connection of another account."""
        with self._db() as db:
            row = db.execute(
                "SELECT 1 FROM grants WHERE id = ? AND account = ?", (grant, account_id)
            ).fetchone()
        if row is None:
            return False
        self.drop_grant(grant)
        return True

    # ------------------------------------------------------------ browser sessions

    def open_session(self, account_id: str, now: float | None = None) -> str:
        now = time.time() if now is None else now
        token = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO sessions (hash, account, created, expires) VALUES (?, ?, ?, ?)",
                (digest(token), account_id, now, now + SESSION_TTL),
            )
        return token

    def session(self, token: str) -> Account | None:
        if not token:
            return None
        with self._db() as db:
            row = db.execute(
                "SELECT a.id, a.login, a.created, a.seen FROM sessions s"
                " JOIN accounts a ON a.id = s.account WHERE s.hash = ? AND s.expires > ?",
                (digest(token), time.time()),
            ).fetchone()
        return Account(*row) if row else None

    def close_session(self, token: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE hash = ?", (digest(token),))

    # ------------------------------------------------------------ device codes (RFC 8628)

    def start_device(self, client_id: str, now: float | None = None) -> tuple[str, str]:
        """A device code for the program and a short code for the learner to confirm."""
        now = time.time() if now is None else now
        device_code = secrets.token_urlsafe(32)
        user_code = short_code()
        with self._db() as db:
            db.execute(
                "INSERT INTO devices (hash, user_code, client, expires) VALUES (?, ?, ?, ?)",
                (
                    digest(device_code),
                    digest(normalize_invite(user_code)),
                    client_id,
                    now + DEVICE_TTL,
                ),
            )
        return device_code, user_code

    def device_waiting(self, user_code: str) -> bool:
        with self._db() as db:
            row = db.execute(
                "SELECT 1 FROM devices WHERE user_code = ? AND account IS NULL AND expires > ?",
                (digest(normalize_invite(user_code)), time.time()),
            ).fetchone()
        return row is not None

    def approve_device(self, user_code: str, account_id: str) -> bool:
        with self._db() as db:
            done = db.execute(
                "UPDATE devices SET account = ? WHERE user_code = ? AND account IS NULL"
                " AND expires > ?",
                (account_id, digest(normalize_invite(user_code)), time.time()),
            )
            return done.rowcount == 1

    def poll_device(self, device_code: str, client_id: str, now: float | None = None) -> str:
        """`pending`, `slow_down`, `expired`, or the account that confirmed the code (once)."""
        now = time.time() if now is None else now
        key = digest(device_code)
        with self._db() as db, _transaction(db):
            row = db.execute(
                "SELECT client, account, expires, polled FROM devices WHERE hash = ?", (key,)
            ).fetchone()
            if row is None or row[0] != client_id or row[2] <= now:
                return "expired"
            if row[1]:
                db.execute("DELETE FROM devices WHERE hash = ?", (key,))
                return str(row[1])
            db.execute("UPDATE devices SET polled = ? WHERE hash = ?", (now, key))
            if row[3] is not None and now - row[3] < DEVICE_INTERVAL - 1:
                return "slow_down"
            return "pending"

    # ------------------------------------------------------------ password recovery

    def start_reset(self, account_id: str, now: float | None = None) -> str:
        now = time.time() if now is None else now
        token = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO resets (hash, account, expires) VALUES (?, ?, ?)",
                (digest(token), account_id, now + RESET_TTL),
            )
        return token

    def reset_account(self, token: str) -> Account | None:
        """The account of a recovery link that still works, without using the link."""
        with self._db() as db:
            row = db.execute(
                "SELECT a.id, a.login, a.created, a.seen FROM resets r"
                " JOIN accounts a ON a.id = r.account WHERE r.hash = ? AND r.expires > ?",
                (digest(token), time.time()),
            ).fetchone()
        return Account(*row) if row else None

    def take_reset(self, token: str) -> Account | None:
        """Use a recovery link: once, and within its half an hour."""
        found = self.reset_account(token)
        if found is None:
            return None
        with self._db() as db:
            done = db.execute("DELETE FROM resets WHERE hash = ?", (digest(token),))
        return found if done.rowcount == 1 else None

    def purge(self, now: float | None = None) -> int:
        """Remove expired sign-in requests, codes, tokens, sessions and links."""
        now = time.time() if now is None else now
        removed = 0
        with self._db() as db:
            for table in ("requests", "codes", "tokens", "sessions", "devices", "resets"):
                removed += db.execute(f"DELETE FROM {table} WHERE expires <= ?", (now,)).rowcount
            removed += db.execute(
                "DELETE FROM grants WHERE NOT EXISTS"
                " (SELECT 1 FROM tokens t WHERE t.grant_id = grants.id)"
            ).rowcount
        return removed
