"""The server: the MCP endpoint with VocabBot's tools, the OAuth endpoints and the sign-in page.

`/mcp` answers only with a valid access token; the token names the account,
and every tool works on that account's folder. The tools take the same
arguments as the program's commands and return the same JSON.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypeVar

import anyio.to_thread
from mcp.server.apps import Apps, ResourceCsp
from mcp.server.auth.handlers.metadata import MetadataHandler, ProtectedResourceMetadataHandler
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.routes import build_metadata, cors_middleware
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.auth import ProtectedResourceMetadata
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from vocabbot import __version__
from vocabbot.server import guides, pages
from vocabbot.server.accounts import Registry
from vocabbot.server.config import SCOPE, Settings
from vocabbot.server.oauth import Provider, SignIn
from vocabbot.server.service import ASSIGNMENT, Service

READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)

Card = Annotated[
    str, Field(max_length=40, description="a card id from an earlier result, e.g. de-c00042#p")
]
Lang = Annotated[
    str, Field(pattern=r"^[a-z]{2}$", description="a course language: en, de, es, fr or it")
]
Settings_ = Annotated[
    list[Annotated[str, Field(max_length=200)]],
    Field(max_length=20, description="plan settings as KEY=VALUE, e.g. days_off=sun"),
]


class Answer(BaseModel):
    card: Card
    answer: str = Field(
        max_length=500,
        description="the learner's answer exactly as typed; an empty string when unknown",
    )


Answers = Annotated[list[Answer], Field(min_length=1, max_length=200)]
F = TypeVar("F", bound=Callable[..., Any])
# the card a chat application that supports MCP Apps shows with the session's results
CARD = "ui://vocabbot/card.html"
CARD_META: dict[str, Any] = {"ui": {"resourceUri": CARD}, "openai/outputTemplate": CARD}
RECORDINGS = "https://upload.wikimedia.org"


def _account() -> str:
    token = get_access_token()
    if token is None or not token.subject:
        raise ToolError("VocabBot needs a signed-in account")
    return token.subject


class Tools:
    """The tools of the server, bound to its engine and its accounts."""

    def __init__(self, service: Service, registry: Registry) -> None:
        self.service = service
        self.registry = registry

    async def run(self, argv: list[str], text: str = "") -> str:
        account = _account()
        self.registry.touch(account, time.time())
        data = await anyio.to_thread.run_sync(self.service.call, account, argv, text)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    async def setup(self, languages: list[str], new_per_day: int, settings: list[str]) -> str:
        account = _account()
        self.registry.touch(account, time.time())
        data = await anyio.to_thread.run_sync(
            self.service.setup, account, languages, new_per_day, settings
        )
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def register(server: MCPServer, tools: Tools) -> None:
    def tool(
        name: str, title: str, description: str, annotations: ToolAnnotations, card: bool = False
    ) -> Callable[[F], F]:
        return server.tool(
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            meta=CARD_META if card else None,
            structured_output=False,
        )

    @tool(
        "vocab_guide",
        "Zasady VocabBota",
        "The rules and steps for VocabBot. Call it before the first VocabBot step of a"
        " conversation, with the topic that fits: session (the daily session), start (setup,"
        " placement test, changes of the plan), coach (explanations, mnemonics, the weekly"
        " review) or words (own words, reports of mistakes in the course).",
        READ,
    )
    async def vocab_guide(topic: Literal["session", "start", "coach", "words"]) -> str:
        _account()
        return guides.guide(topic)

    @tool(
        "vocab_today",
        "Plan dnia",
        "The learner's day: reviews due, new words and drill per language, the minutes it"
        " takes, a day off, what is done and left in each stage with the counter line, what"
        " can still be added today (`more`), and the words first shown today. Writes nothing.",
        READ,
        card=True,
    )
    async def vocab_today() -> str:
        return await tools.run(["today"])

    @tool(
        "vocab_add_today",
        "Więcej na dziś",
        "Add to today's session, only when the learner asks for more: `count` new words on"
        " top of the day's number, or `reviews` more reviews (the next round: due cards over"
        " the limit or of a day off first, then the cards with the nearest later dates). The"
        " result says how many joined (`added`) and holds the next cards (`next`).",
        WRITE,
        card=True,
    )
    async def vocab_add_today(
        count: Annotated[int, Field(ge=0, le=100)] = 0,
        reviews: Annotated[int, Field(ge=0, le=200)] = 0,
    ) -> str:
        if count + reviews < 1:
            raise ToolError("give count (new words) or reviews, at least 1")
        argv = ["today", "--extra", str(count), "--reviews", str(reviews), "--next"]
        return await tools.run(argv)

    @tool(
        "vocab_next",
        "Następne karty",
        "The next cards of today's session: as many as the plan's batch (1 by default, one"
        " card at a time) unless `count` says otherwise. Without `stage` the engine's order"
        " holds: reviews, new words, drill. `stage` (reviews, new or drill) brings the cards"
        " of the stage the learner chose first, at any moment of the session. Every card"
        " shows only its question; a new word (phase new) holds its word for an introduction"
        " only with the plan's new_words set to show. Calling it again returns the same"
        " cards until answers come in.",
        READ,
        card=True,
    )
    async def vocab_next(
        count: Annotated[int | None, Field(ge=1, le=50)] = None,
        stage: Literal["reviews", "new", "drill"] | None = None,
    ) -> str:
        argv = ["next"]
        if count is not None:
            argv += ["--count", str(count)]
        if stage is not None:
            argv += ["--stage", stage]
        return await tools.run(argv)

    @tool(
        "vocab_answer",
        "Ocena odpowiedzi",
        "Grade the learner's typed answers to the cards of the last vocab_next, exactly as"
        " typed (an unknown answer as an empty string). Returns the engine's grade with its"
        " error classes, the right word, and what is left today; with `then_next` also the"
        " next cards (`next`) of the stage the answered card belongs to, so the session needs"
        " one call per card and stays in the stage the learner chose.",
        WRITE,
        card=True,
    )
    async def vocab_answer(answers: Answers, then_next: bool = False) -> str:
        text = "\n".join(
            json.dumps({"card": item.card, "answer": item.answer}, ensure_ascii=False)
            for item in answers
        )
        argv = ["answer", "--batch", "--stdin"]
        argv += ["--next"] if then_next else []
        return await tools.run(argv, text)

    @tool(
        "vocab_grade",
        "Własna ocena",
        "The learner's own grade of a card: known (the learner knew the word before the"
        " course; only at its first showing), or know, almost, dont_know for a recognition"
        " card after vocab_reveal. After several known words in a row the result may hold"
        " `level_hint`. With `then_next` the result also holds the next cards (`next`) of"
        " the same stage.",
        WRITE,
        card=True,
    )
    async def vocab_grade(
        card: Card,
        grade: Literal["known", "know", "almost", "dont_know"],
        then_next: bool = False,
    ) -> str:
        argv = ["grade", "--card", card, "--grade", grade]
        argv += ["--next"] if then_next else []
        return await tools.run(argv)

    @tool(
        "vocab_reveal",
        "Znaczenie karty rozpoznawania",
        "The meaning, forms and example of a recognition card (id ending in #r), after the"
        " learner tried to recall it.",
        READ,
    )
    async def vocab_reveal(card: Card) -> str:
        return await tools.run(["reveal", "--card", card])

    @tool(
        "vocab_regrade",
        "Zmiana oceny",
        "Change today's last grade of one card, only when the learner explicitly asks for"
        " that card.",
        WRITE,
    )
    async def vocab_regrade(card: Card, grade: Literal["know", "almost", "dont_know"]) -> str:
        return await tools.run(["regrade", "--card", card, "--grade", grade])

    @tool(
        "vocab_lookup",
        "Szukaj w kursie",
        "Find course entries by a word (with or without its article) or by a word of its"
        " Polish meaning: meaning, gender, forms, example. Up to ten matches.",
        READ,
    )
    async def vocab_lookup(lang: Lang, text: Annotated[str, Field(max_length=200)]) -> str:
        return await tools.run(["lookup", "--lang", lang, "--stdin"], text)

    @tool(
        "vocab_status",
        "Postępy",
        "Progress per language: words learned per level, recall over 30 days, reviews, error"
        " classes, hard words, mix-ups between languages, recent words, the streak, and the"
        " schedule in force.",
        READ,
    )
    async def vocab_status() -> str:
        return await tools.run(["status"])

    @tool(
        "vocab_forecast",
        "Prognoza",
        "The daily load in the coming days (reviews, new words, minutes) and the days when"
        " each level has been introduced in full.",
        READ,
    )
    async def vocab_forecast(days: Annotated[int, Field(ge=1, le=365)] = 30) -> str:
        return await tools.run(["forecast", "--days", str(days)])

    @tool(
        "vocab_plan",
        "Plan nauki",
        "The learner's plan: languages, levels, weights, new words a day and the other settings.",
        READ,
    )
    async def vocab_plan() -> str:
        return await tools.run(["plan", "show"])

    @tool(
        "vocab_plan_change",
        "Zmiana planu (podgląd)",
        "Preview a change of the plan from KEY=VALUE settings, e.g. new_per_day=10,"
        " lang.fr=a1-a2, lang.es=paused, days_off=sat,sun, retention=0.85. Changes nothing:"
        " vocab_commit with the token saves it after the learner's yes.",
        READ,
    )
    async def vocab_plan_change(settings: Settings_) -> str:
        for setting in settings:
            if not ASSIGNMENT.match(setting):
                raise ToolError(f"a setting is KEY=VALUE: {setting[:80]}")
        return await tools.run(["plan", "set", *settings])

    @tool(
        "vocab_plan_fit",
        "Dopasowanie harmonogramu (podgląd)",
        "Preview FSRS-6 parameters fitted to the learner's log, only for the languages where"
        " they predict the later reviews better than the defaults. Changes nothing:"
        " vocab_commit with the token saves them after the learner's yes.",
        READ,
    )
    async def vocab_plan_fit() -> str:
        return await tools.run(["plan", "fit"])

    @tool(
        "vocab_replay",
        "Porównanie harmonogramów",
        "Replay the learner's log: predictions of every review by FSRS-6 and by variants"
        " fitted to the earlier part of the log (log loss, RMSE, AUC against FSRS-6), and a"
        " simulation of the coming weeks. Writes nothing.",
        READ,
    )
    async def vocab_replay(
        share: Annotated[float, Field(ge=0.3, le=0.9)] = 0.7,
        days: Annotated[int, Field(ge=0, le=90)] = 28,
    ) -> str:
        return await tools.run(["replay", "--share", str(share), "--days", str(days)])

    @tool(
        "vocab_words_add",
        "Własne słowa (podgląd)",
        "Preview adding the learner's own words in one language, one per line:"
        " 'der Hund = pies', 'laufen [verb] = biec', 'l'ami (m) = przyjaciel | example |"
        " translation', or a JSON object per line. Changes nothing: vocab_commit with the"
        " token saves them after the learner's yes.",
        READ,
    )
    async def vocab_words_add(lang: Lang, lines: Annotated[str, Field(max_length=40000)]) -> str:
        return await tools.run(["words", "add", "--lang", lang, "--stdin"], lines)

    @tool(
        "vocab_commit",
        "Zapis zmiany",
        "Save a previewed change (the first plan, a change of the plan, fitted parameters,"
        " own words) with its token, only after the learner's explicit yes to that preview"
        " in a later message.",
        WRITE,
    )
    async def vocab_commit(token: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]) -> str:
        return await tools.run(["commit", "--confirm", token])

    @tool(
        "vocab_courses",
        "Kursy",
        "The installed courses: the languages and the number of words per level.",
        READ,
    )
    async def vocab_courses() -> str:
        return await tools.run(["course", "list"])

    @tool(
        "vocab_quiz",
        "Test poziomujący",
        "Questions of a placement test in one language, level by level, without their"
        " answers. Writes nothing.",
        READ,
    )
    async def vocab_quiz(
        lang: Lang,
        levels: Annotated[str, Field(pattern=r"^[abcABC][12]([-,][abcABC][12])*$")] = "a1-b2",
        count: Annotated[int, Field(ge=1, le=20)] = 6,
    ) -> str:
        return await tools.run(["quiz", "--lang", lang, "--levels", levels, "--count", str(count)])

    @tool(
        "vocab_quiz_check",
        "Ocena testu",
        "Grade the answers of a placement test (every answer given so far in the test)."
        " Returns the grade of each word, the levels known and the suggested levels. Writes"
        " nothing.",
        READ,
    )
    async def vocab_quiz_check(answers: Answers, lenient: bool = False) -> str:
        text = "\n".join(
            json.dumps({"card": item.card, "answer": item.answer}, ensure_ascii=False)
            for item in answers
        )
        return await tools.run(
            ["quiz", "--check", "--stdin", *(["--lenient"] if lenient else [])], text
        )

    @tool(
        "vocab_flag",
        "Zgłoszenie błędu",
        "Report a mistake in a course entry with the learner's note; the card leaves the"
        " queue until the report is withdrawn with clear true.",
        WRITE,
    )
    async def vocab_flag(
        card: Card,
        note: Annotated[str, Field(max_length=500)] = "",
        clear: bool = False,
    ) -> str:
        if clear:
            return await tools.run(["flag", "--card", card, "--clear"])
        if note.strip():
            return await tools.run(["flag", "--card", card, "--stdin"], note)
        return await tools.run(["flag", "--card", card])

    @tool(
        "vocab_setup",
        "Nowy plan (podgląd)",
        "Preview the first plan of the learner's account: languages as code:levels[:weight]"
        " (de:a1-a2, es:b1-b2:2), new words a day for all languages together, and more"
        " settings as KEY=VALUE. Changes nothing: vocab_commit with the token saves it after"
        " the learner's yes.",
        READ,
    )
    async def vocab_setup(
        languages: Annotated[
            list[Annotated[str, Field(max_length=20)]], Field(min_length=1, max_length=6)
        ],
        new_per_day: Annotated[int, Field(ge=0, le=100)] = 15,
        settings: Settings_ | None = None,
    ) -> str:
        return await tools.setup(languages, new_per_day, list(settings or []))


def build(settings: Settings) -> Starlette:
    """The whole ASGI application of the server."""
    registry = Registry(settings.database)
    registry.purge()
    service = Service(settings)
    provider = Provider(registry, settings)
    # strings, not URL objects: the models keep an issuer without a trailing slash, the
    # same string the sign-in returns as `iss`, and clients compare the two exactly
    auth = AuthSettings.model_validate(
        {
            "issuer_url": settings.url,
            "resource_server_url": settings.resource,
            "validate_token_resource": True,
            "required_scopes": [SCOPE],
            "client_registration_options": ClientRegistrationOptions(
                enabled=True, default_scopes=[SCOPE]
            ),
            "revocation_options": RevocationOptions(enabled=True),
            "service_documentation_url": settings.url + "/",
        }
    )
    apps = Apps()
    apps.add_html_resource(
        CARD,
        pages.card(),
        name="vocabbot-card",
        title=pages.card_title(),
        description="The session's card: the counter, the word with its recording, the question.",
        # the recordings come from Wikimedia Commons; nothing else leaves the frame
        csp=ResourceCsp(resource_domains=[RECORDINGS]),
        prefers_border=True,
    )
    server: MCPServer = MCPServer(
        name="vocabbot",
        title="VocabBot",
        instructions=guides.INSTRUCTIONS,
        website_url=settings.url,
        version=__version__,
        auth_server_provider=provider,
        auth=auth,
        extensions=[apps],
    )
    register(server, Tools(service, registry))
    sign_in = SignIn(registry, settings)
    resource_metadata = ProtectedResourceMetadata.model_validate(
        {
            "resource": settings.resource,
            "authorization_servers": [settings.url],
            "scopes_supported": [SCOPE],
            "resource_name": "VocabBot",
        }
    )

    async def home(request: Request) -> Response:
        return HTMLResponse(pages.home(settings.resource), headers=pages.HEADERS)

    async def privacy(request: Request) -> Response:
        return HTMLResponse(pages.privacy(), headers=pages.HEADERS)

    async def health(request: Request) -> Response:
        return JSONResponse({"ok": True, "version": __version__})

    server.custom_route("/login", methods=["GET", "POST"])(sign_in.handle)
    server.custom_route("/", methods=["GET"])(home)
    server.custom_route("/privacy", methods=["GET"])(privacy)
    server.custom_route("/health", methods=["GET"])(health)
    typeface = pages.font()

    async def font(request: Request) -> Response:
        return Response(
            typeface,
            media_type="font/woff2",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    server.custom_route(pages.FONT, methods=["GET"])(font)
    app = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[settings.host, "127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=[
                settings.url,
                *(f"https://{host}" for host in settings.redirect_hosts),
                "http://127.0.0.1:*",
                "http://localhost:*",
            ],
        ),
        host="0.0.0.0",
    )
    # the authorization server's metadata also says that the sign-in returns `iss` (RFC 9207),
    # which lets ChatGPT use its stable redirect address
    metadata = build_metadata(
        auth.issuer_url,
        auth.service_documentation_url,
        auth.client_registration_options or ClientRegistrationOptions(),
        auth.revocation_options or RevocationOptions(),
    )
    metadata.authorization_response_iss_parameter_supported = True
    replaced = False
    for index, route in enumerate(app.router.routes):
        if isinstance(route, Route) and route.path == "/.well-known/oauth-authorization-server":
            app.router.routes[index] = Route(
                route.path,
                endpoint=cors_middleware(MetadataHandler(metadata).handle, ["GET", "OPTIONS"]),
                methods=["GET", "OPTIONS"],
            )
            replaced = True
    if not replaced:
        raise RuntimeError("the SDK no longer serves the authorization server metadata")
    # clients that look for the resource metadata at the root find the same document
    app.router.routes.append(
        Route(
            "/.well-known/oauth-protected-resource",
            endpoint=cors_middleware(
                ProtectedResourceMetadataHandler(resource_metadata).handle, ["GET", "OPTIONS"]
            ),
            methods=["GET", "OPTIONS"],
        )
    )
    return app
