"""The server's own OAuth 2.1 authorization server: clients, the sign-in page and tokens.

The MCP SDK handles the protocol (metadata, dynamic client registration, PKCE,
the token endpoint); this module keeps the records and signs the learner in.
A chat application registers itself, sends the learner to `/authorize`, and
the learner signs in or opens an account on `/login`. The application then
gets an access token for an hour and a refresh token that changes at every use.
"""

from __future__ import annotations

import secrets
import time
import uuid
from urllib.parse import urlencode, urlsplit

import anyio.to_thread
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from vocabbot.server import pages
from vocabbot.server.accounts import Account, Registry, SignupError, TokenRow
from vocabbot.server.config import SCOPE, Settings

ACCESS_TTL = 3600
REFRESH_TTL = 90 * 86400
CODE_TTL = 300
REQUEST_TTL = 900  # time to sign in or open an account


def same_resource(given: str, ours: str) -> bool:
    def canonical(url: str) -> tuple[str, str, str]:
        parts = urlsplit(url)
        return parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/")

    try:
        return canonical(given) == canonical(ours)
    except ValueError:
        return False


class Provider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """The records behind the SDK's OAuth endpoints."""

    def __init__(self, registry: Registry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        info = self.registry.client(client_id)
        return OAuthClientInformationFull.model_validate_json(info) if info else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        uris = [str(uri) for uri in client_info.redirect_uris or []]
        if not uris:
            raise RegistrationError("invalid_redirect_uri", "a client needs a redirect URI")
        for uri in uris:
            if not self.settings.redirect_allowed(uri):
                raise RegistrationError(
                    "invalid_redirect_uri", f"this server does not send sign-ins to {uri}"
                )
        if not client_info.client_id:
            raise RegistrationError("invalid_client_metadata", "the client has no id")
        self.registry.save_client(client_info.client_id, client_info.model_dump_json())

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        if params.resource is not None and not same_resource(
            params.resource, self.settings.resource
        ):
            raise AuthorizeError(
                "invalid_target", f"this server issues tokens for {self.settings.resource}"
            )
        request_id = self.registry.save_request(
            str(client.client_id), params.model_dump_json(), REQUEST_TTL
        )
        return f"{self.settings.url}/login?{urlencode({'request': request_id})}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        data = self.registry.code(authorization_code)
        if data is None:
            return None
        code = AuthorizationCode.model_validate_json(data)
        return code if code.client_id == client.client_id else None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if not self.registry.take_code(authorization_code.code):
            raise TokenError("invalid_grant", "the authorization code was used already")
        account = authorization_code.subject
        if not account or self.registry.account(account) is None:
            raise TokenError("invalid_grant", "the account no longer exists")
        return self._issue(
            str(client.client_id), account, authorization_code.scopes, uuid.uuid4().hex
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        row = self.registry.token(refresh_token, "refresh")
        if row is None or row.client != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=row.client,
            scopes=row.scopes,
            expires_at=int(row.expires),
            resource=row.resource,
            subject=row.account,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        row = self.registry.take_token(refresh_token.token, "refresh")
        if row is None:
            raise TokenError("invalid_grant", "the refresh token was used already")
        # the access token of the old pair ends with it
        self.registry.drop_grant(row.grant)
        if self.registry.account(row.account) is None:
            raise TokenError("invalid_grant", "the account no longer exists")
        return self._issue(str(client.client_id), row.account, scopes or row.scopes, row.grant)

    async def load_access_token(self, token: str) -> AccessToken | None:
        row = self.registry.token(token, "access")
        if row is None:
            return None
        return AccessToken(
            token=token,
            client_id=row.client,
            scopes=row.scopes,
            expires_at=int(row.expires),
            resource=row.resource,
            subject=row.account,
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        for kind in ("access", "refresh"):
            row = self.registry.token(token.token, kind)
            if row is not None:
                self.registry.drop_grant(row.grant)

    def _issue(self, client_id: str, account: str, scopes: list[str], grant: str) -> OAuthToken:
        now = time.time()
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        resource = self.settings.resource
        self.registry.save_token(
            access,
            TokenRow("access", client_id, account, scopes, resource, grant, now + ACCESS_TTL),
        )
        self.registry.save_token(
            refresh,
            TokenRow("refresh", client_id, account, scopes, resource, grant, now + REFRESH_TTL),
        )
        return OAuthToken(
            access_token=access,
            expires_in=ACCESS_TTL,
            scope=" ".join(scopes),
            refresh_token=refresh,
        )


class Throttle:
    """Failed sign-ins per address and per login within a quarter of an hour."""

    WINDOW = 900.0
    PER_LOGIN = 10
    PER_ADDRESS = 30

    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [moment for moment in self._failures.get(key, []) if now - moment < self.WINDOW]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def blocked(self, address: str, login: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return (
            len(self._recent(f"address:{address}", now)) >= self.PER_ADDRESS
            or len(self._recent(f"login:{login.strip().lower()}", now)) >= self.PER_LOGIN
        )

    def fail(self, address: str, login: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        for key in (f"address:{address}", f"login:{login.strip().lower()}"):
            self._failures.setdefault(key, []).append(now)


class SignIn:
    """`/login`: the page that signs the learner in and sends the chat application a code."""

    def __init__(self, registry: Registry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings
        self.throttle = Throttle()

    def _client(self, client_id: str) -> tuple[str, str]:
        """The application's name and the host the learner returns to."""
        info = self.registry.client(client_id)
        if info is None:
            return client_id, ""
        client = OAuthClientInformationFull.model_validate_json(info)
        uris = [str(uri) for uri in client.redirect_uris or []]
        host = (urlsplit(uris[0]).hostname or "") if uris else ""
        return client.client_name or host or client_id, host

    def _form(
        self,
        request_id: str,
        client_id: str,
        error: str | None = None,
        login: str = "",
        tab: str = "login",
    ) -> HTMLResponse:
        app, host = self._client(client_id)
        page = pages.sign_in(request_id, app, host, self.settings.open_signup, error, login, tab)
        status = 429 if error == "throttled" else 400 if error else 200
        return HTMLResponse(page, status_code=status, headers=pages.HEADERS)

    async def handle(self, request: Request) -> Response:
        if request.method == "GET":
            request_id = request.query_params.get("request", "")
            found = self.registry.request(request_id) if request_id else None
            if found is None:
                return HTMLResponse(pages.expired(), status_code=400, headers=pages.HEADERS)
            return self._form(request_id, found[0])
        form = await request.form()
        request_id = str(form.get("request") or "")
        found = self.registry.request(request_id) if request_id else None
        if found is None:
            return HTMLResponse(pages.expired(), status_code=400, headers=pages.HEADERS)
        client_id, params_json = found
        login = str(form.get("login") or "")[:100]
        password = str(form.get("password") or "")
        address = request.client.host if request.client else "unknown"
        tab = "signup" if form.get("action") == "signup" else "login"
        if self.throttle.blocked(address, login):
            return self._form(request_id, client_id, "throttled", login, tab)
        account: Account | None
        if tab == "signup":
            if password != str(form.get("password2") or ""):
                return self._form(request_id, client_id, "password_mismatch", login, tab)
            invite = str(form.get("invite") or "")
            try:
                account = await anyio.to_thread.run_sync(
                    self.registry.signup, login, password, invite, self.settings.open_signup
                )
            except SignupError as exc:
                if exc.code == "bad_invite":
                    self.throttle.fail(address, login)
                return self._form(request_id, client_id, exc.code, login, tab)
        else:
            account = await anyio.to_thread.run_sync(self.registry.verify, login, password)
            if account is None:
                self.throttle.fail(address, login)
                return self._form(request_id, client_id, "wrong_credentials", login)
        if not self.registry.drop_request(request_id):
            return HTMLResponse(pages.expired(), status_code=400, headers=pages.HEADERS)
        params = AuthorizationParams.model_validate_json(params_json)
        code = AuthorizationCode(
            code=secrets.token_urlsafe(32),
            scopes=[SCOPE],
            expires_at=time.time() + CODE_TTL,
            client_id=client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.settings.resource,
            subject=account.id,
        )
        self.registry.save_code(code.code, code.model_dump_json(), code.expires_at)
        target = construct_redirect_uri(
            str(params.redirect_uri), code=code.code, state=params.state, iss=self.settings.url
        )
        return RedirectResponse(target, status_code=303, headers={"Cache-Control": "no-store"})
