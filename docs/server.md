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
- The learning day of every account starts in the server's time zone
  (`Europe/Warsaw` by default) at the hour of the plan's `day_starts_at`.

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
grades to choose after "pokaż", and the new words of the day. With the
plan's `sentence_translation=hidden` a button under a sentence shows its
translation. The recordings come from Wikimedia
Commons (Wiktionary and Lingua Libre) and play straight from
`upload.wikimedia.org`, the only address the card may load. A word or a
sentence without a recording is read by the browser's speech synthesis. The
card shows a question without its word and never plays it, so it keeps the
answer back as the messages do. Applications without MCP Apps show the same
session as text, with a link to the recording beside the IPA.

## Data and privacy

The server keeps the login, the password hash, the plan, the log of answers,
own words and reports of mistakes in the course. It needs no e-mail address
and no name. The chat application processes the conversation under its own
terms and sends the server only the calls of VocabBot's tools. The page
`/privacy` tells the learner the same in Polish.

## Checks

```
uv run pytest tests/test_server.py
```

The tests run the server over HTTP and connect the MCP SDK's own OAuth
client, as a chat application does: registration, the sign-in page, the
token, the tools, two accounts side by side, a refresh and a revoked token.
