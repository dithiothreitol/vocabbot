# The VocabBot server

[Polski](server.pl.md)

The server makes VocabBot available in chat applications that connect to
remote MCP servers: Claude on the web, on the desktop and on the phone,
ChatGPT, Claude Code and Codex. Every learner has an account on the server.
The chat application signs in with OAuth and calls VocabBot's tools; the
server keeps the plan and the log of each account. The chat application's
model runs the conversation on the learner's own subscription, so the
server itself uses no model.

## How it works

| Address | Purpose |
|---|---|
| `/mcp` | the MCP endpoint with 23 tools; every call needs an access token, which names the account |
| `/.well-known/oauth-protected-resource/mcp` | where the tokens come from (RFC 9728) |
| `/.well-known/oauth-authorization-server` | the authorization server's metadata (RFC 8414) |
| `/register`, `/authorize`, `/token`, `/revoke` | OAuth 2.1: dynamic client registration, PKCE with S256, refresh tokens that change at every use, the resource indicator (RFC 8707) and the issuer in the sign-in response (RFC 9207) |
| `/login` | the page where the learner signs in or opens an account with an invitation code |
| `/`, `/privacy`, `/health` | the start page, the privacy note and the health check |
| `/static/vocabbot.png`, `/favicon.ico` | VocabBot's avatar: the favicon of the pages and the icon the server names in its MCP information (`icons`) |
| `/sync` | the synchronisation of a learning folder linked to the account (`vocabbot login`), with the same access token as `/mcp` |
| `/device`, `/device/authorize`, `/device/token` | the program's sign-in with a code confirmed on another device (the device flow, RFC 8628) |
| `/app/`, `/app/login`, `/api/<name>` | the session page in a browser, its sign-in and its calls of the engine |
| `/account`, `/account/export` | the account page: connections, the data as a zip, the e-mail address, removing the account |
| `/recover`, `/recover/<token>` | password recovery with a link sent to the e-mail address typed |

- The tools run the commands of the `vocabbot` program on the account's
  folder (`learners/<account>/`) and return the same JSON as the plugin's
  skills read. The guarantees stay the same: a card under review shows only
  its question, the engine grades every answer, and a change of the plan or
  own words waits for a preview and the learner's yes.
- `vocab_guide` gives the model the rules and the steps of the plugin's
  skills, with the tools in place of the commands: the daily session, the
  setup and the plan, the coach, own words.
- `accounts.db` holds the logins with scrypt hashes of the passwords.
  Invitation codes, sign-in requests, authorization codes and tokens are
  kept only as SHA-256 hashes. An access token is valid for an hour and a
  refresh token for 90 days.
- After a sign-in, the server sends the learner back only to the addresses
  of Claude (`claude.ai`, `claude.com`), ChatGPT (`chatgpt.com`) and to the
  learner's own computer (`localhost`, `127.0.0.1`).
- The learning day of an account starts in the plan's time zone (the
  setting `timezone`; a new account gets the zone its browser reports), and
  for a plan without one in the server's zone (`Europe/Warsaw` by default),
  always at the hour of the plan's `day_starts_at`.

## Running the server

The repository holds a Docker setup in `deploy/`: the server and Caddy, which
obtains and renews the TLS certificate. It needs a machine with Docker, a
domain whose DNS record points at that machine, and free ports 80 and 443.

```
git clone https://github.com/dithiothreitol/vocabbot
cd vocabbot
cp deploy/example.env deploy/.env      # set VOCABBOT_DOMAIN
docker compose -f deploy/compose.yaml up -d --build
docker compose -f deploy/compose.yaml exec vocabbot vocabbot-server invite --note "Ola"
```

`https://<domain>/health` answers with the version once the server runs. The
data of every account lives in the `vocabbot-data` volume; a copy of that
volume is a complete backup.

A server whose Caddy already serves other sites in Docker takes VocabBot as
one more site. `scripts/deploy_vps.sh` builds the image on your computer, sends
it over SSH, starts it in the Caddy's network as `vocabbot-app`, installs the
site in Caddy's folder of sites after a validation (an invalid configuration
brings back the previous state) and adds a daily backup to
`/opt/vocabbot/backups`:

```
VPS=root@203.0.113.7 DOMAIN=vocab.example.org PROXY_NETWORK=proxy_net \
CADDY=proxy-caddy-1 CADDY_SITES=/opt/caddy/conf.d scripts/deploy_vps.sh
```

A machine that already runs a reverse proxy (nginx, Caddy, Traefik) can also
run the program without Docker and point the proxy at `127.0.0.1:8000`:

```
uv tool install "vocabbot[server]"
vocabbot-server --data /var/lib/vocabbot serve --url https://<domain>
```

Every option has an environment variable: `VOCABBOT_SERVER_URL`,
`VOCABBOT_SERVER_DATA`, `VOCABBOT_SERVER_TIMEZONE`,
`VOCABBOT_SERVER_OPEN_SIGNUP` and `VOCABBOT_SERVER_PROXIES` (the proxies whose
`X-Forwarded-For` the server trusts).

## Accounts

An account opens with an invitation code. The administrator manages the
accounts with the same program (in Docker, after
`docker compose -f deploy/compose.yaml exec vocabbot`):

| Command | What it does |
|---|---|
| `vocabbot-server invite --note "Ola" [--uses 1] [--days 14]` | a new invitation code |
| `vocabbot-server accounts` | the accounts with their last activity, and the invitations |
| `vocabbot-server password <login>` | a new password from standard input; the account's connections end |
| `vocabbot-server delete <login> --yes` | removes the account with its plan, log and own words |

`--open-signup` (or `VOCABBOT_OPEN_SIGNUP=1` in `deploy/.env`) lets anyone
open an account without an invitation.

## The session page, the account page and folders

- **The session page** (`/app/`) runs the session in a browser, also on a
  phone and from its home screen, without a chat application and without a
  model: the day's cards with the choice of stage, typing and "pokaż" with
  the learner's own grade, recordings, notes, words put aside, more words and
  reviews, progress with an activity map and the forecast, changes of the
  plan as previews and the first plan with a placement test. Every step runs
  a command of the engine through `/api/<name>`, so a question comes without
  its answer and the engine grades. The browser signs in on `/app/login` and
  gets a session cookie for 30 days (`HttpOnly`, `SameSite=Strict`, `Secure`
  on https); every write needs the form token and the server's own origin.
- **The account page** (`/account`) lists the connected applications and
  computers with their last use and disconnects any of them, gives the data
  as a zip in the form of a learning folder, keeps an optional e-mail address
  for password recovery (only as a scrypt hash) and removes the account after
  the password.
- **Learning folders.** `vocabbot login` signs the program in (through the
  browser, or with a code confirmed on `/device`) and links a folder to the
  account. `/sync` takes the lines the account lacks and returns the ones
  the folder lacks; a line sent again adds nothing, and the server refuses a
  row of an unknown card or one from the future. The tools and the
  synchronisation of one account run one after another.
- **Password recovery** needs an SMTP account: `VOCABBOT_SERVER_SMTP_HOST`,
  `_PORT`, `_USER`, `_PASSWORD`, `_FROM` and `_SECURITY` (`starttls`, `ssl`
  or `none`). The page `/recover` answers the same for every login and
  address, and the link works once for 30 minutes. A server without these
  settings asks for no address, and the administrator sets a new password.

## Connecting a chat application

The server's address for every application is `https://<domain>/mcp`.

- **Claude** (web, desktop, phone): Settings, Connectors, Add custom
  connector, the name VocabBot and the address. After Connect, the learner
  signs in on the server's page and returns to Claude. Custom connectors are
  available on every plan; the free plan allows one. A connector added on the
  web is also available in the phone app.
- **ChatGPT** (a paid plan): Settings, Integrations, Plugins, the plus
  button and a custom MCP server with the address and OAuth as the
  authentication; developer mode is no longer needed. The tools that save
  data (answers, plan changes) work: a pilot account in ChatGPT saved its plan
  and answers on 15.11.2026.
- **Claude Code**: `claude mcp add --transport http vocabbot https://<domain>/mcp`,
  then `/mcp` and the sign-in in the browser.
- **Codex**: `codex mcp add vocabbot --url https://<domain>/mcp`, then
  `codex mcp login vocabbot`.

A new conversation starts the session with "sesja" or "zaczynamy naukę
słówek". The first conversation sets up the plan: languages, levels and new
words a day, with an optional placement test.

## The card in the chat

Chat applications that support MCP Apps (Claude on the web and in the
desktop application, ChatGPT) show VocabBot's card with the results of
`vocab_today`, `vocab_next`, `vocab_answer`, `vocab_grade`, `vocab_reveal`
and `vocab_add_today`: the day's counter, the three stages (reviews, new
words, drill) with the cards left in each, the word with its IPA and a
button that plays its recording, the learner's note, the question, the
grades to choose after "pokaż", and the new words of the day. A button
under a sentence shows its translation, or the translation stands under it
with the plan's `sentence_translation=shown`. The recordings come from Wikimedia
Commons (Wiktionary and Lingua Libre) and play straight from
`upload.wikimedia.org`, the only address the card may load. A word or a
sentence without a recording is read by the browser's speech synthesis. The
card shows a question without its word and never plays it, so it keeps the
answer back as the messages do. Applications without MCP Apps show the same
session as text, with a link to the recording beside the IPA.

## Data and privacy

The server keeps the login, the password hash, the plan, the log of answers,
own words, notes, reports of mistakes in the course, the account's time zone
and the list of connected applications and computers with their last use.
The e-mail address is optional and reaches the server only as a hash. The
server needs no name. The chat application processes the conversation under its own
terms and sends the server only the calls of VocabBot's tools. The page
`/privacy` tells the learner the same in Polish.

## Checks

```
uv run pytest tests/test_server.py tests/test_web.py tests/test_e2e.py
```

The tests run the server over HTTP and connect the MCP SDK's own OAuth
client, as a chat application does: registration, the sign-in page, the
token, the tools, two accounts side by side, a refresh and a revoked token.
