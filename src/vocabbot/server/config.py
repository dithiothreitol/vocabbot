"""The server's settings: its public address, its data folder and whom it lets in."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone, tzinfo
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from vocabbot.store import zone_problem

SCOPE = "vocab"
# hosts a chat application sends the learner back to after the sign-in; the
# loopback hosts serve Claude Code, Codex and other programs on the learner's computer
REDIRECT_HOSTS = ("claude.ai", "claude.com", "chatgpt.com")
LOOPBACK = ("localhost", "127.0.0.1", "::1")


@dataclass(frozen=True)
class Mail:
    """The SMTP account that sends the links of password recovery; empty: no recovery by mail."""

    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    sender: str = ""
    security: str = "starttls"  # starttls, ssl or none

    @property
    def ready(self) -> bool:
        return bool(self.host and self.sender)


@dataclass(frozen=True)
class Settings:
    url: str  # the public address, e.g. https://vocab.example.org
    data: Path  # accounts.db and learners/<account>/
    timezone: str = "Europe/Warsaw"  # the learning day of an account without its own zone
    redirect_hosts: tuple[str, ...] = REDIRECT_HOSTS
    open_signup: bool = False  # True: an account needs no invitation
    mail: Mail = Mail()

    def __post_init__(self) -> None:
        parts = urlsplit(self.url)
        if parts.scheme not in ("https", "http") or not parts.hostname:
            raise ValueError(f"the server address must be an http(s) URL: {self.url!r}")
        if parts.scheme == "http" and parts.hostname not in LOOPBACK:
            raise ValueError("a public server address must use https")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError("the server address is a scheme and a host, without a path")
        object.__setattr__(self, "url", f"{parts.scheme}://{parts.netloc}")
        problem = zone_problem(self.timezone)
        if problem:
            raise ValueError(f"the server's {problem}")
        self.tzinfo()

    @property
    def resource(self) -> str:
        """The MCP endpoint, which is also the resource the tokens are issued for."""
        return f"{self.url}/mcp"

    @property
    def host(self) -> str:
        return urlsplit(self.url).netloc

    @property
    def secure(self) -> bool:
        """The server answers over https, so its cookies carry Secure."""
        return self.url.startswith("https://")

    @property
    def database(self) -> Path:
        return self.data / "accounts.db"

    @property
    def learners(self) -> Path:
        return self.data / "learners"

    def tzinfo(self) -> tzinfo:
        if self.timezone.upper() == "UTC":
            return timezone.utc
        return ZoneInfo(self.timezone)

    def redirect_allowed(self, uri: str) -> bool:
        """A chat application's own address over https, or a loopback address."""
        try:
            parts = urlsplit(uri)
            port = parts.port
        except ValueError:
            return False
        host = (parts.hostname or "").lower()
        if parts.username is not None or parts.password is not None or parts.fragment:
            return False
        if parts.scheme == "http" and host in LOOPBACK:
            return True
        return parts.scheme == "https" and host in self.redirect_hosts and port in (None, 443)
