# Serwer VocabBota

[English](server.md) · **Polski**

Serwer udostępnia VocabBota aplikacjom czatu, które łączą się ze zdalnymi
serwerami MCP: Claude w przeglądarce, w aplikacji desktopowej i w telefonie,
ChatGPT, Claude Code oraz Codex. Każdy uczący się ma na serwerze własne konto.
Aplikacja czatu loguje się przez OAuth i wywołuje narzędzia VocabBota, a
serwer przechowuje plan i dziennik każdego konta. Rozmowę prowadzi model
aplikacji czatu w ramach subskrypcji uczącego się, dlatego sam serwer nie
korzysta z żadnego modelu.

## Działanie

| Adres | Przeznaczenie |
|---|---|
| `/mcp` | punkt MCP z 23 narzędziami; każde wywołanie wymaga tokenu dostępu, który wskazuje konto |
| `/.well-known/oauth-protected-resource/mcp` | informacja o źródle tokenów (RFC 9728) |
| `/.well-known/oauth-authorization-server` | metadane serwera autoryzacji (RFC 8414) |
| `/register`, `/authorize`, `/token`, `/revoke` | OAuth 2.1: dynamiczna rejestracja klientów, PKCE z S256, tokeny odświeżania wymieniane przy każdym użyciu, wskaźnik zasobu (RFC 8707) i wystawca w odpowiedzi logowania (RFC 9207) |
| `/login` | strona logowania i zakładania konta z kodem zaproszenia |
| `/`, `/privacy`, `/health` | strona startowa, informacja o prywatności i kontrola działania |
| `/static/vocabbot.png`, `/favicon.ico` | awatar VocabBota: ikona stron w przeglądarce i ikona, którą serwer podaje w informacjach MCP (`icons`) |
| `/robots.txt`, `/sitemap.xml`, `/llms.txt` | zasady dla robotów wyszukiwarek (strony publiczne otwarte, formularze i API zamknięte), strony do indeksowania w obu językach oraz opis VocabBota w Markdown dla modeli AI |
| `/static/social-pl.png`, `/static/social-en.png` | obrazy udostępnionego linku do strony startowej (tworzy je `scripts/make_social.py`) |
| `/static/site.css` | arkusz stylów stron; strony odwołują się do niego ze skrótem treści, więc przeglądarki przechowują go przez rok |
| `/sync` | synchronizacja folderu nauki połączonego z kontem (`vocabbot login`), z tym samym tokenem dostępu co `/mcp` |
| `/device`, `/device/authorize`, `/device/token` | logowanie programu kodem potwierdzonym na innym urządzeniu (przepływ urządzenia, RFC 8628) |
| `/app/`, `/app/login`, `/api/<nazwa>` | strona sesji w przeglądarce, jej logowanie i wywołania silnika |
| `/account`, `/account/export` | strona konta: połączenia, dane jako archiwum zip, adres e-mail, usunięcie konta |
| `/recover`, `/recover/<token>` | odzyskiwanie hasła odnośnikiem wysłanym na podany adres e-mail |

- Narzędzia uruchamiają polecenia programu `vocabbot` na folderze konta
  (`learners/<konto>/`) i zwracają ten sam JSON, który czytają umiejętności
  wtyczki. Gwarancje pozostają te same: karta w powtórce pokazuje tylko
  pytanie, każdą odpowiedź ocenia silnik, a zmiana planu lub własnych słów
  czeka na podgląd i potwierdzenie uczącego się.
- Narzędzie `vocab_guide` przekazuje modelowi zasady i kroki umiejętności
  wtyczki, w których miejsce poleceń zajmują narzędzia: codzienną sesję,
  konfigurację i plan, trenera oraz własne słowa.
- Plik `accounts.db` przechowuje loginy ze skrótami haseł w scrypt. Kody
  zaproszeń, żądania logowania, kody autoryzacji i tokeny trafiają tam
  wyłącznie jako skróty SHA-256. Token dostępu działa godzinę, a token
  odświeżania 90 dni.
- Po zalogowaniu serwer odsyła uczącego się wyłącznie na adresy Claude
  (`claude.ai`, `claude.com`), ChatGPT (`chatgpt.com`) oraz na jego własny
  komputer (`localhost`, `127.0.0.1`).
- Dzień nauki konta zaczyna się w strefie czasowej planu (ustawienie
  `timezone`; nowe konto dostaje strefę odczytaną z przeglądarki), a dla
  planu bez strefy w strefie serwera (domyślnie `Europe/Warsaw`), zawsze
  o godzinie z ustawienia `day_starts_at`.
- Strony serwera (strona startowa, prywatność, logowania, konto,
  odzyskiwanie hasła i `/device`) są dostępne po polsku i po angielsku.
  Język wynika z parametru `?lang=`, następnie z ciasteczka `vocabbot_lang`
  ustawianego przełącznikiem, a potem z nagłówka `Accept-Language`
  przeglądarki; domyślny jest polski. Teksty angielskie znajdują się
  w `data/i18n/en.json`, a brakujący tekst zastępuje polski; wiadomość
  odzyskiwania hasła wychodzi w języku strony. Strona sesji, karta i teksty
  silnika pozostają po polsku, tak jak kurs.

## Uruchomienie serwera

Repozytorium zawiera w folderze `deploy/` konfigurację Dockera: serwer oraz
Caddy, który uzyskuje i odnawia certyfikat TLS. Wymaga ona maszyny z
Dockerem, domeny z rekordem DNS wskazującym tę maszynę oraz wolnych portów 80
i 443.

```
git clone https://github.com/dithiothreitol/vocabbot
cd vocabbot
cp deploy/example.env deploy/.env      # ustaw VOCABBOT_DOMAIN
docker compose -f deploy/compose.yaml up -d --build
docker compose -f deploy/compose.yaml exec vocabbot vocabbot-server invite --note "Ola"
```

Adres `https://<domena>/health` po uruchomieniu odpowiada numerem wersji.
Dane wszystkich kont znajdują się w wolumenie `vocabbot-data`, więc kopia tego
wolumenu stanowi pełną kopię zapasową.

Na serwerze, na którym Caddy w Dockerze obsługuje już inne strony, VocabBot
staje się kolejną stroną. Skrypt `scripts/deploy_vps.sh` buduje obraz na
Twoim komputerze, przesyła go przez SSH, uruchamia go w sieci Caddy jako
`vocabbot-app`, instaluje stronę w folderze stron Caddy po sprawdzeniu
konfiguracji (przy błędzie przywraca poprzedni stan) i dodaje codzienną kopię
zapasową w `/opt/vocabbot/backups`:

```
VPS=root@203.0.113.7 DOMAIN=vocab.example.org PROXY_NETWORK=proxy_net \
CADDY=proxy-caddy-1 CADDY_SITES=/opt/caddy/conf.d scripts/deploy_vps.sh
```

Po przeniesieniu serwisu na nową domenę zmienna `REDIRECT_FROM` wskazuje
dotychczasowe adresy (oraz ewentualny adres z `www.`): Caddy przekierowuje je
na `DOMAIN` na stałe, z zachowaniem metody żądania (308). Każdy z tych adresów
wymaga rekordu A wskazującego serwer. Nowa domena zmienia wystawcę OAuth
i adres MCP, dlatego aplikacje czatu trzeba połączyć ponownie z nowym
adresem, w przeglądarce zalogować się jeszcze raz, a połączony folder nauki
połączyć poleceniem `vocabbot login --server https://<nowa domena>`.

```
... DOMAIN=vocab.example.org REDIRECT_FROM="old.example.org www.vocab.example.org" scripts/deploy_vps.sh
```

Odzyskiwanie hasła przez e-mail wymaga konta SMTP: polecenie dostaje
`SMTP_HOST`, `SMTP_USER`, `SMTP_FROM`, `SMTP_PORT` i `SMTP_SECURITY`, a hasło
pochodzi z `SMTP_PASSWORD` (w środowisku albo w pliku `.env` repozytorium,
który git pomija). Skrypt zapisuje ustawienia w pliku
`/opt/vocabbot/smtp.env`, dostępnym tylko dla roota. Niektóre serwery
blokują wychodzący port 465 (Hetzner domyślnie); działa tam port 587
z `SMTP_SECURITY=starttls`:

```
... SMTP_HOST=smtp.example.org SMTP_PORT=587 SMTP_SECURITY=starttls \
SMTP_USER=vocab@example.org SMTP_FROM="VocabBot <vocab@example.org>" scripts/deploy_vps.sh
```

Na maszynie z działającym już serwerem pośredniczącym (nginx, Caddy, Traefik)
program działa również bez Dockera, a serwer pośredniczący kieruje ruch na
`127.0.0.1:8000`:

```
uv tool install "vocabbot[server]"
vocabbot-server --data /var/lib/vocabbot serve --url https://<domena>
```

Każda opcja ma swoją zmienną środowiskową: `VOCABBOT_SERVER_URL`,
`VOCABBOT_SERVER_DATA`, `VOCABBOT_SERVER_TIMEZONE`,
`VOCABBOT_SERVER_OPEN_SIGNUP` oraz `VOCABBOT_SERVER_PROXIES` (serwery
pośredniczące, którym serwer ufa w nagłówku `X-Forwarded-For`).

## Konta

Konto powstaje z kodem zaproszenia. Administrator zarządza kontami tym samym
programem (w Dockerze po `docker compose -f deploy/compose.yaml exec vocabbot`):

| Polecenie | Działanie |
|---|---|
| `vocabbot-server invite --note "Ola" [--uses 1] [--days 14]` | nowy kod zaproszenia |
| `vocabbot-server accounts` | konta z ostatnią aktywnością oraz zaproszenia |
| `vocabbot-server password <login>` | nowe hasło ze standardowego wejścia; połączenia konta wygasają |
| `vocabbot-server delete <login> --yes` | usunięcie konta razem z planem, dziennikiem i własnymi słowami |

Opcja `--open-signup` (albo `VOCABBOT_OPEN_SIGNUP=1` w `deploy/.env`)
pozwala zakładać konta bez zaproszenia.

## Strona sesji, strona konta i foldery

- **Strona sesji** (`/app/`) prowadzi sesję w przeglądarce, także
  w telefonie i z ekranu głównego, bez aplikacji czatu i bez modelu: karty
  dnia z wyborem etapu, wpisywanie i „pokaż” z własną oceną, nagrania,
  notatki, odkładanie słów, kolejne słowa i powtórki, postępy z mapą
  aktywności i prognozą, zmiany planu jako podgląd oraz pierwszy plan
  z testem poziomującym. Każdy krok wykonuje polecenie silnika przez
  `/api/<nazwa>`, więc pytanie przychodzi bez odpowiedzi i ocenia silnik.
  Przeglądarka loguje się na `/app/login` i dostaje ciasteczko sesji na
  30 dni (`HttpOnly`, `SameSite=Strict`, `Secure` przy https); każdy zapis
  wymaga żetonu formularza i pochodzenia z adresu serwera. Przełącznik
  języka stron zapisuje wybór w drugim ciasteczku, `vocabbot_lang`
  (`SameSite=Lax`, rok), wyłącznie wtedy, gdy uczący się go użyje.
- **Strona konta** (`/account`) pokazuje połączone aplikacje i komputery
  z datą ostatniego użycia i odłącza każde z nich, pobiera dane jako
  archiwum zip w postaci folderu nauki, przechowuje opcjonalny adres e-mail
  do odzyskania hasła (wyłącznie jako skrót scrypt) i usuwa konto po
  podaniu hasła.
- **Foldery nauki.** `vocabbot login` loguje program na serwerze (przez
  przeglądarkę albo kodem potwierdzonym na `/device`) i łączy folder
  z kontem. `/sync` przyjmuje wiersze, których konto nie ma, i oddaje te,
  których nie ma folder; wiersz wysłany drugi raz niczego nie dodaje,
  a wiersz nieznanej karty albo z przyszłości serwer odrzuca. Narzędzia
  i synchronizacja jednego konta wykonują się po kolei.
- **Odzyskiwanie hasła** wymaga konta SMTP: `VOCABBOT_SERVER_SMTP_HOST`,
  `_PORT`, `_USER`, `_PASSWORD`, `_FROM` i `_SECURITY` (`starttls`, `ssl`
  albo `none`). Strona `/recover` odpowiada tak samo dla każdego loginu
  i adresu, a odnośnik działa raz przez 30 minut. Serwer bez tych ustawień
  nie pyta o adres, a nowe hasło nadaje administrator.

## Podłączenie aplikacji czatu

Adres serwera jest dla każdej aplikacji taki sam: `https://<domena>/mcp`.

- **Claude** (przeglądarka, aplikacja desktopowa, telefon): Ustawienia,
  Łączniki, Dodaj własny łącznik, nazwa VocabBot i adres. Po kliknięciu
  Połącz uczący się loguje się na stronie serwera i wraca do Claude. Własne
  łączniki działają w każdym planie, a plan bezpłatny pozwala na jeden.
  Łącznik dodany w przeglądarce działa również w aplikacji na telefonie.
- **ChatGPT** (plan płatny): Ustawienia, Integracje, Wtyczki, przycisk „+”
  i własny serwer MCP z adresem serwera oraz uwierzytelnianiem OAuth. Tryb
  dewelopera nie jest już potrzebny. Narzędzia zapisujące dane (odpowiedzi,
  zmiany planu) działają, co potwierdziło konto pilotażowe, które 15.11.2026
  zapisało w ChatGPT plan i odpowiedzi.
- **Claude Code**: `claude mcp add --transport http vocabbot https://<domena>/mcp`,
  następnie `/mcp` i logowanie w przeglądarce.
- **Codex**: `codex mcp add vocabbot --url https://<domena>/mcp`, następnie
  `codex mcp login vocabbot`.

Nową sesję otwiera w rozmowie słowo „sesja” albo prośba „zaczynamy naukę
słówek”. Pierwsza rozmowa tworzy plan: języki, poziomy i liczbę nowych słów
dziennie, z opcjonalnym testem poziomującym.

## Karta w czacie

Aplikacje czatu, które obsługują MCP Apps (Claude w przeglądarce
i w aplikacji desktopowej, ChatGPT), pokazują przy wynikach `vocab_today`,
`vocab_next`, `vocab_answer`, `vocab_grade`, `vocab_reveal`
i `vocab_add_today` kartę VocabBota: licznik dnia, trzy etapy (powtórki,
nowe słowa, utrwalanie) z liczbą pozostałych kart, słowo z zapisem IPA
i przyciskiem odtwarzania nagrania, notatkę uczącego się, pytanie, oceny do
wyboru po haśle „pokaż” oraz nowe słowa dnia. Tłumaczenie zdania
pokazuje przycisk pod zdaniem, a przy ustawieniu planu
`sentence_translation=shown` tłumaczenie stoi od razu pod zdaniem. Nagrania pochodzą z Wikimedia Commons (Wikisłownik i Lingua
Libre) i odtwarzają się bezpośrednio z `upload.wikimedia.org`, jedynego
adresu, z którego karta może pobierać pliki. Słowo albo zdanie bez nagrania
odczytuje synteza mowy przeglądarki. Pytanie na karcie nie pokazuje ani nie
odtwarza słowa, o które pyta, więc karta zachowuje odpowiedź tak samo jak
wiadomości. Aplikacje bez MCP Apps pokazują tę samą sesję jako tekst
z odnośnikiem do nagrania obok zapisu IPA.

## Dane i prywatność

Serwer przechowuje login, skrót hasła, plan, dziennik odpowiedzi, własne
słowa, notatki, zgłoszenia błędów w kursie, strefę czasową konta oraz listę
połączonych aplikacji i komputerów z datą ostatniego użycia. Adres e-mail
jest opcjonalny i trafia na serwer wyłącznie jako skrót. Serwer nie
potrzebuje imienia.
Aplikacja czatu przetwarza rozmowę według własnych zasad i przekazuje
serwerowi wyłącznie wywołania narzędzi VocabBota. Strona `/privacy` podaje
uczącemu się te same informacje po polsku i po angielsku.

## Kontrole

```
uv run pytest tests/test_server.py tests/test_web.py tests/test_e2e.py
```

Testy uruchamiają serwer przez HTTP i łączą z nim klienta OAuth z SDK MCP w
taki sam sposób jak aplikacja czatu: rejestracja, strona logowania, token,
narzędzia, dwa konta obok siebie, odświeżenie tokenu i token unieważniony.
