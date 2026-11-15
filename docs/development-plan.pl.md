# Plan implementacji VocabBot

[English](development-plan.md) · **Polski**

Stan: 2026-11-15, po Etapie 4 (wersja 1.0.0-rc.3, w pakiecie Pythona
1.0.0rc3). Plan zaakceptowałeś 14.11.2026, a Etapy 4 i 5 dodałeś 15.11.2026.
Silnik, program `vocabbot` z nową sesją w terminalu, kursy A1–B2 dla czterech
języków (23 095 haseł) oraz wtyczka z czterema umiejętnościami dla Claude'a
i Codexa działają; wyniki etapów opisuje rozdział 10. Na GitHubie i w PyPI
leży wydanie `v1.0.0-rc.2`, a wersja rc.3 czeka w lokalnym repozytorium na
Twoją zgodę na push i wydanie. Do wersji 1.0 pozostają testy sesyjne
z modelem na wersji rc.3 (po Twojej zgodzie) oraz pilotaż według
`docs/pilot.pl.md`; Etap 5 (harmonogram dopasowany do uczącego się)
korzysta z dziennika pilotażu. Wersję angielską planu zawiera
`development-plan.md`.

---

## 1. Cel i definicja ukończenia

VocabBot jest otwartym narzędziem do nauki słownictwa w jednym, dwóch lub
trzech językach obcych równocześnie, na poziomach A1–A2 i B1–B2, dla osoby
mówiącej po polsku. Nauka przebiega tak jak w kursach słownictwa SuperMemo:
uczący się poznaje nowe słowa w kolejności od najczęstszych, ocenia każdą
odpowiedź jedną z trzech ocen i wraca do słowa w dniu wyznaczonym przez
algorytm powtórek. Narzędzie udostępnia jeden silnik dwiema drogami: przez
własny program `vocabbot` w terminalu oraz przez rozmowę z Claude'em lub
Codexem, którą prowadzi wtyczka z umiejętnościami w standardzie Agent Skills.

Wersja 1.0 jest ukończona, gdy spełnione są wszystkie warunki:

1. Uczący się przechodzi pełną ścieżkę bez pomocy autora: instalację, wybór
   języków i poziomów, codzienną sesję w terminalu i w czacie, przegląd
   postępów oraz zmianę planu.
2. Kursy angielskiego, niemieckiego, hiszpańskiego i francuskiego obejmują
   poziomy A1–A2 i B1–B2, przechodzą `vocabbot course check` bez błędów
   i spełniają progi jakości z Etapu 2.
3. Każdy termin powtórki pochodzi z silnika, którego wyniki zgadzają się
   z biblioteką wzorcową FSRS.
4. Każda ocena w dzienniku pochodzi z odpowiedzi uczącego się ocenionej przez
   silnik albo z jego własnej oceny. Model nie podnosi ocen i nie pokazuje
   odpowiedzi przed zapisaniem odpowiedzi uczącego się, co potwierdzają testy.
5. Zmiana planu lub kursu wykonuje się wyłącznie po pokazaniu podglądu
   i potwierdzeniu tokenem.
6. Pakiet przechodzi `ruff`, `mypy`, `pytest`, walidator repozytorium oraz
   `claude plugin validate --profile directory --strict`.
7. Pilotaż, czyli Twoja nauka przez co najmniej dwa tygodnie w dwóch lub
   trzech językach, kończy się bez błędów blokujących.

---

## 2. Ustalenia wejściowe

### 2.1 Twoje decyzje z 14.11.2026

| Pytanie | Decyzja |
|---|---|
| Miejsce codziennej sesji | czat oraz własny CLI |
| Języki pierwszych kursów | angielski, niemiecki, hiszpański, francuski; język bazowy polski |
| Nazwa robocza | `vocabbot`, repozytorium lokalne w `Documents\GitHub\vocabbot` |
| Kolejność pracy | najpierw ten plan, potem kod; minimalna liczba etapów; najnowsze stabilne wersje narzędzi i bibliotek |

### 2.2 Wzorzec funkcjonalny: kursy słownictwa SuperMemo

Ustalenia pochodzą ze stron supermemo.com sprawdzonych 14.11.2026 (lista
źródeł na końcu dokumentu).

| Cecha kursów SuperMemo | Ustalenie |
|---|---|
| Kursy słownictwa | seria Extreme: Basic A1–A2 (2226 stron), Intermediate B1–B2 (9844 strony), jedna strona na słowo lub wyrażenie |
| Kolejność materiału | słowa ułożone według częstości, od najczęstszych |
| Zawartość strony | słowo, definicja w języku nauki, zdanie przykładowe, obraz, nagranie lektora, tłumaczenie na język uczącego się |
| Sekcje nauki | nauka nowych stron, powtórki, utrwalanie |
| Oceny | „wiem”, „prawie”, „nie wiem” |
| Skutek ocen | „wiem” wydłuża odstęp; „prawie” również wydłuża odstęp i kieruje stronę do utrwalania tego samego dnia; „nie wiem” skraca odstęp i kieruje stronę do utrwalania |
| Utrwalanie | strony ocenione „prawie” lub „nie wiem” wracają po zakończeniu powtórek zaplanowanych na dany dzień |
| Cel algorytmu | powtórka w chwili, gdy prawdopodobieństwo przypomnienia wynosi około 90% |
| Algorytm | historycznie SM-2, obecnie SM-20 (własność SuperMemo, niedostępny do ponownego użycia) |
| Plan | liczba kart dziennie, przewidywany czas trwania kursu, kalendarz z wyłączonymi dniami |
| Kilka kursów naraz | powtórki mieszane z materiałem wszystkich kursów uczącego się |
| Ceny | kurs Extreme na rok 69,90–89,90 zł; Premium 35,99 zł miesięcznie |

Treść kursów SuperMemo jest chroniona, dlatego VocabBot odwzorowuje sposób
nauki i buduje słownictwo z otwartych źródeł (rozdział 3, decyzja D12).

### 2.3 Wzorzec architektoniczny: HouseholdBot

| Element HouseholdBota | W VocabBocie | Uzasadnienie |
|---|---|---|
| Rekord w folderze użytkownika, zwykłe pliki | przejęty | folder nauki z planem, dziennikiem powtórek i własnymi słowami |
| Skrypty dowodzą, model ocenia | przejęty | silnik liczy harmonogram, kolejkę i ocenę odpowiedzi; model wyjaśnia, dobiera przykłady i prowadzi rozmowę |
| Gwarancja w skrypcie zamiast w instrukcji | przejęty | polecenie `next` nie zwraca odpowiedzi, polecenie `answer` wylicza ocenę, zmiany planu przechodzą przez podgląd i token |
| Zapis dwufazowy z tokenem | dostosowany | obejmuje plan i kursy; oceny trafiają do dziennika bez bramki, ponieważ odpowiedź uczącego się jest samą czynnością nauki |
| Prawo jako dane ze wskazanym źródłem | dostosowany | kurs jako dane: każde hasło ze źródłem, każdy plik z licencją, kontrola `course check` |
| Język oddzielony od kraju | przejęty | język bazowy oddzielony od języków nauki; komunikaty w `data/i18n` |
| Każda umiejętność samowystarczalna | dostosowany | każda umiejętność niesie jeden plik `vocabbot.pyz` z całym silnikiem i kursami |
| Skrypty wyłącznie na bibliotece standardowej | przejęty dla silnika | od Etapu 4 także sesja w terminalu korzysta wyłącznie z biblioteki standardowej (`term.py`) |
| Tekst z zewnątrz poza wierszem poleceń | przejęty | odpowiedzi i własne słowa trafiają do silnika na wejściu standardowym |
| Cztery poziomy weryfikacji | przejęte | struktura, arytmetyka, zachowanie, użycie |
| Dwa manifesty i dwa katalogi marketplace | przejęte | Claude oraz Codex z jednego folderu wtyczki |
| Router, łańcuchy umiejętności, agent tylko do odczytu, cookbook agenta zarządzanego | pominięte | cztery umiejętności obywają się bez routera; nauka nie wymaga pracy bez nadzoru |
| Hook potwierdzenia | przejęty w wersji 1.0.0-rc.2 | przejście ścieżki pokazało, że model potrafi zapisać zmianę bez potwierdzenia; hook przenosi potwierdzenie do okna zgody gospodarza w Claude Code i Coworku |
| Ścieżka bez Pythona | pominięta | ręczny rachunek nie daje rzetelnych terminów powtórek; bez wykonania silnika umiejętność informuje o tym i proponuje ćwiczenie bez zapisu |

### 2.4 Nauka kilku języków równocześnie

| Wynik badań | Reguła w silniku |
|---|---|
| Przeplatanie dwóch języków w jednej sesji dało lepsze wyniki niż nauka blokami (Waisman Center, UW–Madison; niemiecki i polski u osób anglojęzycznych) | jedna kolejka dnia z przeplataniem języków jako ustawienie domyślne; ustawienie `mix: blocks` dla osób, które wolą bloki |
| Nauka odpowiednika w nowym języku obniża bezpośrednio potem przypominanie słowa z wcześniej poznanego języka obcego (MPI Nijmegen, 2024) | odstęp `sibling_gap_days` (domyślnie 3 dni) między wprowadzeniem tego samego pojęcia w dwóch językach oraz rozdzielenie takich kart w kolejce |
| Interferencja rośnie dla słów podobnych do słów ze znanych już języków i maleje z czasem (Bartolotti i Marian, Northwestern) | wykrywanie odpowiedzi udzielonej w innym z uczonych języków oraz pole `confusable` w haśle |
| Wyniki badań nad przeplataniem różnią się zależnie od materiału | ustawienie pozostaje do wyboru; `status` pokazuje zmierzoną trwałość osobno dla każdego języka |

---

## 3. Decyzje projektowe

**D1. Jeden pakiet Pythona, silnik bez zależności.** Cały kod mieszka
w `src/vocabbot/`. Moduły silnika importują wyłącznie bibliotekę standardową,
dzięki czemu ten sam kod działa w programie instalowanym na komputerze
i w piaskownicy gospodarza, która nie pozwala niczego instalować.

**D2. Dwa wejścia do jednego silnika.** Program `vocabbot` instalowany przez
`uv tool install vocabbot` od Etapu 4 nie ma zależności, a jego sesja
w terminalu wygląda tak samo jak w pliku `vocabbot.pyz`. Plik `vocabbot.pyz`
(archiwum `zipapp` z silnikiem i kursami) uruchamia się poleceniem
`python vocabbot.pyz` bez żadnej instalacji i trafia do każdej umiejętności.
Oba wejścia mają te same polecenia i tę samą opcję `--json`, która zwraca
wynik dla umiejętności.

**D3. Rekord nauki w folderze uczącego się.** Uczący się wybiera folder przy
`vocabbot init`. Program zapisuje wskaźnik do folderu w
`~/.vocabbot/config.json`, przy czym zmienna `VOCABBOT_HOME` i opcja
`--learner` mają pierwszeństwo. Jeden folder odpowiada jednej osobie.

**D4. Dziennik jest źródłem prawdy.** Plik `log/reviews.jsonl` przyjmuje jeden
wiersz na każdą ocenioną odpowiedź i nigdy nie jest przepisywany. Każde
polecenie odtwarza stan kart z dziennika, dlatego ten sam dziennik i ta sama
data zawsze dają tę samą kolejkę. Scalenie dzienników z dwóch komputerów
polega z tego samego powodu na połączeniu wierszy.

**D5. Harmonogram FSRS-6.** Silnik zawiera własną implementację FSRS-6
z opublikowanymi parametrami domyślnymi (21 liczb). Testy porównują ją
z biblioteką `fsrs` 6.3.3 na zapisanych wektorach oraz na losowych ciągach
ocen. Algorytm FSRS jest opublikowany i ma bibliotekę wzorcową na licencji
MIT. Harmonogram celuje w zadaną trwałość, domyślnie 0,9, czyli w wartość
stosowaną w kursach SuperMemo.

**D6. Trzy oceny i „znałem”.** Oceny `know`, `almost`, `dont_know`
odpowiadają przyciskom „wiem”, „prawie”, „nie wiem” i ocenom FSRS Good, Hard,
Again. Ocena `known` („znałem to słowo przed kursem”) jest dostępna wyłącznie
przy pierwszym pokazaniu, odpowiada ocenie Easy i nie zużywa dziennego limitu
nowych słów.

**D7. Utrwalanie nie zmienia harmonogramu.** Druga i kolejne odpowiedzi na tę
samą kartę tego samego dnia zapisują się w dzienniku jako utrwalanie
i pozostawiają termin powtórki bez zmian. Karta opuszcza utrwalanie po
odpowiedzi „wiem”.

**D8. Jedna kolejka dla kilku języków.** Plan obejmuje od jednego do trzech
języków z wagami. Silnik dzieli dzienny limit nowych słów według wag,
wstrzymuje wprowadzenie pojęcia poznanego niedawno w innym języku, przeplata
języki i rozdziela karty tego samego pojęcia. Czwarty język wymaga jawnego
podniesienia ustawienia `max_languages`.

**D9. Odpowiedź ocenia silnik.** Karta produkcji (polskie znaczenie i zdanie
z luką, odpowiedź w języku nauki) wymaga wpisania odpowiedzi. Silnik
porównuje ją z hasłem według reguł danego języka i proponuje ocenę: zgodność
daje „wiem”, drobna różnica (znak diakrytyczny, jedna literówka w dłuższym
słowie, brak lub błąd rodzajnika, wielkość litery) daje „prawie”, pozostałe
odpowiedzi dają „nie wiem”. W terminalu uczący się zatwierdza propozycję
klawiszem Enter albo zmienia ją jednym klawiszem. W czacie polecenie
`regrade` zmienia ocenę wyłącznie na wyraźną prośbę uczącego się i oznacza
taki wiersz w dzienniku.

**D10. Kurs jako dane.** Kurs to pliki `data/courses/<język>/<poziom>.jsonl`
z jednym hasłem w wierszu oraz plik `meta.json` ze źródłami, datami
i licencją. Wspólny identyfikator pojęcia łączy hasła różnych języków. Własne
słowa uczącego się trafiają do jego folderu w tym samym formacie.

**D11. Bramka zmian planu i kursu.** Polecenia `plan set` i `words add`
tworzą podgląd z tokenem ważnym 30 minut. Wyłącznie polecenie
`commit --confirm <token>` wykonuje pokazaną zmianę. Każda zatwierdzona
zmiana dostaje wiersz w `log/decisions.md`.

**D12. Treść kursów z otwartych źródeł.** Potok buduje kursy z listy CEFR-J
(poziomy), angielskiego Wikisłownika w ekstrakcie kaikki.org (tłumaczenia,
rodzaj, formy, wymowa), danych wordfreq (częstość) i zdań Tatoeba
(przykłady). Kod ma licencję Apache-2.0, kursy licencję CC BY-SA 4.0
z wykazem źródeł w pliku `NOTICE`.

**D13. Cztery umiejętności.** Wtyczka zawiera `vocab-start` (ustawienie nauki
i zmiany planu), `vocab-session` (codzienna sesja w czacie), `vocab-coach`
(wyjaśnienia, skojarzenia, zestawienia mylonych słów, ćwiczenie poznanych słów
w zdaniach, przegląd tygodnia) oraz `vocab-words` (własne słowa z tekstu lub
listy).

**D14. Powierzchnie wersji 1.0.** Wtyczka działa w Claude Code (terminal, IDE,
karta Code w aplikacji desktopowej), w Cowork i w Codex CLI. Program
`vocabbot` działa w każdym terminalu z Pythonem. Sesja na telefonie i sama
strona claude.ai należą do rozszerzeń po wersji 1.0 (rozdział 14).

**D15. Zakres wersji 1.0 obejmuje tekst.** Karta zawiera słowo, znaczenie,
zdanie przykładowe i zapis wymowy IPA. Obrazy, nagrania i rozpoznawanie mowy
należą do rozszerzeń po wersji 1.0.

---

## 4. Narzędzia i biblioteki

Wersje sprawdzone 14.11.2026 w PyPI, rejestrze npm, GitHub Releases
i endoflife.date. Plik `uv.lock` przypina dokładne wersje. Każdy etap zaczyna
się od `uv lock --upgrade` i ponownego sprawdzenia tej tabeli.

| Narzędzie lub biblioteka | Wersja | Wydanie | Rola |
|---|---|---|---|
| Python | 3.15.2 | seria 3.15 od 2026-10-09 | interpreter rozwojowy i CI |
| uv | 0.13.8 | 2026-11-12 | środowisko, plik blokady, budowanie, instalacja CLI, publikacja |
| uv-build | 0.13.8 | 2026-11-12 | backend budowania pakietu |
| ruff | 0.17.5 | 2026-11-12 | linter i formatowanie |
| mypy | 2.4.1 | 2026-10-28 | kontrola typów |
| pytest | 9.2.0 | 2026-10-27 | testy |
| fsrs (py-fsrs) | 6.3.3 | 2026-11-13 | wzorzec harmonogramu w testach |
| rich | 15.0.0 | 2026-04-12 | wygląd sesji w terminalu do Etapu 3; od Etapu 4 zastępuje ją `term.py` |
| wordfreq | 3.1.1 | 2023-11-21 | częstość słów w potoku kursów (ostatnie wydanie biblioteki) |
| actions/checkout | v7.0.1 | 2026-07-20 | CI |
| astral-sh/setup-uv | v10.3.3 | 2026-10-28 | CI |
| actions/setup-node | v7.1.0 | 2026-10-08 | CI, `claude plugin validate` (dodane w Etapie 3) |
| actions/upload-artifact | v7.0.2 | 2026-10-07 | przepływ wydania (dodane w Etapie 3) |
| actions/download-artifact | v8.0.2 | 2026-10-07 | przepływ wydania (dodane w Etapie 3) |
| pypa/gh-action-pypi-publish | v1.14.3 | 2026-10-20 | publikacja w PyPI |
| Claude Code | 2.1.325 | npm | gospodarz, `claude plugin validate` |
| Codex CLI | 0.169.0 | npm | gospodarz |

Stan Twojego komputera: Python 3.14.3, uv 0.11.18, Claude Code 2.1.323, Codex
CLI 0.153.4. Etap 1 zaczyna się od `uv self update` oraz
`uv python install 3.15`, które instaluje nowy interpreter obok obecnego.
Aktualizacja Claude Code i Codex CLI pozostaje po Twojej stronie.

Rozwój i CI działają na Pythonie 3.15. Kod silnika zachowuje zgodność
z wersją 3.10, ponieważ plik `vocabbot.pyz` uruchamia interpreter dostępny
w piaskownicy gospodarza. Etap 3 sprawdza wersje Pythona u gospodarzy
i ustala ostateczną dolną granicę. CI uruchamia testy na 3.10 i 3.15.

Biblioteki rozważone i niewybrane:

| Biblioteka | Wersja | Powód |
|---|---|---|
| Typer | 0.29.1 | moduł poleceń musi działać w pliku `.pyz` bez zależności, dlatego polecenia obsługuje `argparse` z biblioteki standardowej |
| Textual | 8.2.8 | sesja kart ma przebieg sekwencyjny, który `term.py` obsługuje w całości; pełnoekranowy interfejs nie wnosi tu funkcji |
| prompt_toolkit | 3.0.53 | odczyt pojedynczego klawisza zapewniają `msvcrt` i `termios` z biblioteki standardowej |
| ty | 0.0.104 | narzędzie ma wersję poniżej 1.0, dlatego kontrolę typów wykonuje stabilny mypy |

Źródła danych kursów:

| Źródło | Stan | Licencja | Wykorzystanie |
|---|---|---|---|
| kaikki.org, ekstrakt angielskiego Wikisłownika | zrzut 2026-10-01, plik `.gz` 2,9 GB | CC BY-SA 4.0 i GFDL (treść Wikisłownika) | tłumaczenia na de, es, fr, pl; rodzaj; wymowa |
| kaikki.org, ekstrakty edycji de, es, fr | bieżące | CC BY-SA 4.0 i GFDL | liczba mnoga, formy, wymowa |
| CEFR-J Vocabulary Profile | 1.5 | użycie badawcze i komercyjne bez opłat z podaniem źródła | poziom A1–B2 dla hasła angielskiego, przenoszony na pojęcie |
| wordfreq | dane wydania 3.1.1 | CC BY-SA 4.0 | kolejność haseł i wybór najczęstszego odpowiednika |
| Tatoeba | eksport tygodniowy | CC BY 2.0 FR, część zdań CC0 | zdania przykładowe z polskim tłumaczeniem |

---

## 5. Struktura repozytorium

```
vocabbot/
  pyproject.toml  uv.lock  .python-version  LICENSE  NOTICE  CLAUDE.md
  src/vocabbot/
    fsrs.py        harmonogram FSRS-6
    store.py       folder nauki: plan, dziennik, wskaźnik folderu, kopie konfliktowe
    book.py        odtworzenie stanu kart z dziennika
    queue.py       kolejka dnia dla kilku języków, prognoza
    answers.py     normalizacja i ocena odpowiedzi
    courses.py     katalog kursów i kontrola haseł
    gate.py        podgląd i commit zmian planu oraz kursów
    cli.py         polecenia i wyjście JSON
    drill.py       sesja interaktywna
    term.py        kolory, symbole i szerokości w terminalu
    data/courses/<język>/<poziom>.jsonl  meta.json
    data/lang/<język>.json               reguły oceny odpowiedzi
    data/i18n/pl.json                    komunikaty
  plugin/                                wtyczka (Etap 3)
    .claude-plugin/plugin.json  plugin.json
    skills/<umiejętność>/SKILL.md  reference/  shared/rules.md  bin/vocabbot.pyz
  .claude-plugin/marketplace.json  .agents/plugins/marketplace.json
  rules/                                 reguły wspólne (źródło kopii w umiejętnościach)
  tools/courses/                         potok budowy kursów (Etap 2)
  scripts/build.py  validate.py  session_test.py
  sessions/                              pliki testów sesyjnych
  tests/  tests/fixtures/
  docs/
  .github/workflows/validate.yml  release.yml
```

Skrypt `scripts/build.py` generuje pliki `shared/rules.md`
i `bin/vocabbot.pyz` w umiejętnościach. Walidator odrzuca kopię starszą od
źródła.

---

## 6. Model danych

### 6.1 Folder nauki

```
registers/plan.json     języki, poziomy, wagi, limit nowych słów, trwałość, dni wolne
log/reviews.jsonl       dziennik: jeden wiersz na ocenioną odpowiedź
log/decisions.md        jeden wiersz na zatwierdzoną zmianę planu lub kursu
log/flags.jsonl         zgłoszenia błędów w hasłach
courses/<język>/own.jsonl   własne słowa
registers/.pending/     podglądy czekające na potwierdzenie
```

### 6.2 Plan

```json
{
  "schema": 1,
  "base": "pl",
  "languages": [
    {"code": "en", "levels": ["b1", "b2"], "weight": 2},
    {"code": "de", "levels": ["a1", "a2"], "weight": 1},
    {"code": "es", "levels": ["a1", "a2"], "weight": 1, "paused": false}
  ],
  "new_per_day": 15,
  "retention": 0.9,
  "directions": ["produce"],
  "sibling_gap_days": 3,
  "sibling_distance": 5,
  "mix": "interleaved",
  "review_limit": null,
  "days_off": ["sun"],
  "day_starts_at": 4,
  "leech_lapses": 4,
  "max_languages": 3
}
```

### 6.3 Wiersz dziennika

```json
{"ts": "2026-11-16T18:22:05.123456Z", "day": "2026-11-16", "card": "de-a1-0042#p",
 "lang": "de", "grade": "almost", "auto": "almost", "kind": "review",
 "error": "gender", "given": "das Hund", "ms": 4200, "source": "cli"}
```

Pole `kind` przyjmuje wartości `learn`, `review`, `drill`. Odtworzenie stanu
wylicza rodzaj wiersza samodzielnie z kolejności wierszy, dlatego druga
odpowiedź tego samego dnia nigdy nie zmienia harmonogramu.

### 6.4 Hasło kursu

```json
{"id": "de-a1-0042", "concept": "c00042", "rank": 42, "pos": "noun",
 "lemma": "Hund", "display": "der Hund", "gender": "m",
 "forms": {"plural": "die Hunde"}, "accept": ["der Hund"],
 "gloss": {"pl": "pies"}, "ipa": "/hʊnt/",
 "example": {"text": "Der Hund schläft im Garten.", "gap": "Hund",
             "pl": "Pies śpi w ogrodzie.", "source": "tatoeba:1234567"},
 "confusable": ["en-a1-0057"], "sources": ["cefrj", "enwiktionary", "wordfreq"],
 "checked": true}
```

### 6.5 Karta i rodzina kart

Karta to hasło z kierunkiem: `<id>#p` oznacza produkcję (polskie znaczenie,
odpowiedź w języku nauki), `<id>#r` oznacza rozpoznawanie. Wersja 1.0 włącza
domyślnie produkcję, którą silnik ocenia z wpisanej odpowiedzi; rozpoznawanie
jest opcją planu z oceną własną uczącego się. Karty tego samego pojęcia
w różnych językach oraz oba kierunki jednego hasła tworzą rodzinę.

---

## 7. Zasady działania silnika

### 7.1 Harmonogram

Stan karty to stabilność, trudność i dzień ostatniej powtórki. Silnik
wylicza termin z bieżącej stabilności i trwałości z planu, dlatego zmiana
trwałości od razu przelicza wszystkie terminy. Odstęp jest liczbą pełnych dni
i wynosi co najmniej jeden dzień. Dzień nauki zaczyna się o godzinie
`day_starts_at`.

### 7.2 Kolejka dnia

1. Powtórki: karty z terminem do dziś włącznie, w kolejności terminów,
   z opcjonalnym limitem `review_limit`; karty ponad limit przechodzą na
   następny dzień i wynik podaje ich liczbę.
2. Nowe słowa: limit `new_per_day` dzielony według wag metodą największych
   reszt, z rotacją języka otrzymującego resztę. Kandydaci idą w kolejności
   kursu. Silnik pomija dziś hasło, którego rodzina zawiera kartę
   wprowadzoną w ciągu ostatnich `sibling_gap_days` dni.
3. Kolejność sesji: powtórki, potem nowe słowa, na końcu utrwalanie. Języki
   przeplatają się proporcjonalnie do liczby kart. Silnik zachowuje między
   kartami jednej rodziny odstęp co najmniej `sibling_distance` pozycji.
4. Lista dnia jest funkcją dziennika sprzed danego dnia, planu i kursu,
   dlatego przerwana sesja wznawia się w tym samym porządku w terminalu
   i w czacie.
5. Dzień wolny z `days_off` ma pustą kolejkę i zaległe powtórki przechodzą
   na najbliższy dzień nauki.

### 7.3 Zabezpieczenia zapisu ocen

Silnik przyjmuje ocenę nowej karty wyłącznie wtedy, gdy karta należy do
listy dnia (opcja `--extra` pozwala uczącemu się dodać słowa ponad limit).
Silnik przyjmuje powtórkę przed terminem wyłącznie z opcją `--ahead`. Ocena
`known` jest dostępna wyłącznie przy pierwszym pokazaniu. Silnik odrzuca
wiersz z datą wcześniejszą niż ostatni wiersz dziennika.

### 7.4 Ocena odpowiedzi

Reguły języka w `data/lang/<język>.json` określają rodzajniki, znaki
zastępcze (na przykład `ss` za `ß`, `ae` za `ä`), elementy opcjonalne
(angielskie `to` przed czasownikiem) oraz znaki pomijane. Silnik rozpoznaje
klasy błędów: `diacritic`, `typo`, `article`, `gender`, `case`,
`wrong_language` (odpowiedź zgodna z hasłem tego samego pojęcia w innym
uczonym języku). Silnik zapisuje klasę błędu w dzienniku, z którego
korzystają zestawienia `status` oraz umiejętność `vocab-coach`.

### 7.5 Prognoza i postęp

`status` podaje dla każdego języka liczbę poznanych kart, powtórki na dziś
i na siedem dni, liczbę pomyłek, trudne słowa (od `leech_lapses` pomyłek),
trwałość zmierzoną z ostatnich 30 dni oraz udział ocen zmienionych przez
uczącego się. `forecast` symuluje kolejne dni przy bieżącym planie i podaje
dzienne obciążenie oraz datę ukończenia wybranych poziomów.

---

## 8. Polecenia programu

| Polecenie | Działanie |
|---|---|
| `vocabbot init [FOLDER] --base pl --lang en:b1-b2:2 --lang de:a1-a2 --new 15` | tworzy folder nauki i plan |
| `vocabbot today` | plan dnia: powtórki, nowe słowa i utrwalanie dla każdego języka |
| `vocabbot drill` | sesja interaktywna w terminalu |
| `vocabbot next --count 10 --json` | kolejne karty bez odpowiedzi; nowe słowa z pełną treścią do pokazania |
| `vocabbot answer --card ID --stdin --json` | ocenia wpisaną odpowiedź, zapisuje wiersz, zwraca poprawną odpowiedź i przykład |
| `vocabbot grade --card ID --grade known` | ocena własna: „znałem” oraz karty rozpoznawania |
| `vocabbot regrade --card ID --grade know` | zmiana ostatniej oceny na prośbę uczącego się, z oznaczeniem w dzienniku |
| `vocabbot status` | postęp i trwałość dla każdego języka, trudne słowa, klasy błędów |
| `vocabbot forecast --days 30` | dzienne obciążenie i data ukończenia poziomów |
| `vocabbot plan show`, `vocabbot plan set KLUCZ=WARTOŚĆ` | plan; zmiana jako podgląd z tokenem |
| `vocabbot words add --lang de --stdin` | własne słowa jako podgląd z tokenem |
| `vocabbot commit --confirm TOKEN` | wykonuje pokazaną zmianę |
| `vocabbot course list`, `vocabbot course check` | kursy z licznikami; kontrola struktury i spójności haseł |
| `vocabbot flag --card ID --stdin` | zgłoszenie błędu w haśle |
| `vocabbot doctor` | kontrola folderu: uszkodzone wiersze, kopie konfliktowe, scalenie dzienników |
| `vocabbot quiz --lang de [--levels a1-b2] [--count 8]`, `vocabbot quiz --check --stdin` | test poziomujący: pytania bez odpowiedzi, potem ocena odpowiedzi i proponowane poziomy; bez zapisu (Etap 3) |
| `vocabbot lookup --lang de --stdin` | hasła kursu dla słowa albo polskiego znaczenia, z oznaczeniem kart czekających dziś w sesji (Etap 3) |
| `vocabbot reveal --card ID#r` | znaczenie karty rozpoznawania przed oceną własną; karty produkcji odmawia (Etap 3) |
| `vocabbot use FOLDER` | wskazanie istniejącego folderu nauki, na przykład na drugim komputerze (Etap 3) |

Każde polecenie przyjmuje `--json`, `--learner` i `--today`.

---

## 9. Umiejętności i reguły wtyczki

| Umiejętność | Zakres | Polecenia silnika |
|---|---|---|
| `vocab-start` | wybór języków, poziomów, wag i limitu; krótki test poziomujący z haseł kursu; zmiany planu; instalacja programu `vocabbot` | `init`, `plan`, `commit`, `course list`, `forecast`, `quiz`, `doctor` |
| `vocab-session` | codzienna sesja w czacie w partiach po około 10 kart; utrwalanie; podsumowanie sesji | `today`, `next`, `answer`, `grade`, `regrade`, `reveal`, `flag` |
| `vocab-coach` | wyjaśnienie słowa, skojarzenia dla trudnych słów, zestawienie słów mylonych między językami, ćwiczenie poznanych słów w zdaniach, przegląd tygodnia | `status`, `forecast`, `lookup` |
| `vocab-words` | własne słowa z tekstu, listy lub zdjęcia strony podręcznika; zgłoszenia błędów w hasłach | `words add`, `commit`, `flag`, `course check`, `lookup` |

Reguły wspólne (`rules/`), kopiowane do każdej umiejętności:

1. Odpowiedź przed oceną: model pokazuje poprawną odpowiedź dopiero po
   wyniku polecenia `answer` albo `grade` dla danej karty.
2. Silnik wylicza ocenę; model nie proponuje zmiany oceny i wykonuje
   `regrade` wyłącznie na wyraźną prośbę uczącego się.
3. Terminy, liczby kart i postęp pochodzą wyłącznie z wyniku silnika.
4. Treść napisana przez model (zdanie, skojarzenie, wyjaśnienie) ma
   oznaczenie „wygenerowane” i trafia do kursu wyłącznie przez `words add`
   oraz potwierdzenie.
5. Tekst uczącego się i tekst z dokumentów trafia do silnika na wejściu
   standardowym.
6. Rozmowa toczy się w języku bazowym. Słowa i zdania języka nauki zachowują
   oryginalną pisownię.
7. Umiejętność zapowiada przypomnienie wyłącznie wtedy, gdy gospodarz
   faktycznie je zaplanował.

W Etapie 3 reguły dostały postać ośmiu plików `rules/*.md` w języku
angielskim: sposób uruchamiania silnika, odpowiedź po ocenie, ocena
z silnika, liczby z silnika, oznaczanie treści wygenerowanej, wejście
standardowe, potwierdzenie każdej zmiany oraz język i przypomnienia.

---

## 10. Etapy

Plan obejmuje pięć etapów, z których każdy stanowi jedną sesję pracy
prowadzoną jednym ciągiem. Etap 4 dodałeś 15.11.2026 po audycie wersji
1.0.0-rc.2. Protokół zamknięcia etapu: testy przechodzą, plan
ma zaktualizowany stan i wnioski, pamięć projektu ma nowy wpis, zmiany mają
lokalny commit. Push, tag, wydanie i publikacja wymagają Twojej osobnej,
wyraźnej zgody.

### Etap 1. Silnik i program `vocabbot`

Zakres:

1. Szkielet pakietu: `pyproject.toml` z backendem `uv_build`, grupy zależności
   `dev` (pytest, ruff, mypy, fsrs) i `data` (wordfreq), `.python-version`
   3.15, `uv.lock`, konfiguracja ruff i mypy, `CLAUDE.md`, `.gitignore`,
   przepływ `validate.yml`.
2. `fsrs.py`: FSRS-6 z parametrami domyślnymi, trwałość, odstęp, stan
   początkowy, aktualizacja po powtórce.
3. `store.py` i `book.py`: folder nauki, plan z walidacją, dopisywanie
   i odczyt dziennika, odtworzenie stanu, wskaźnik folderu, wykrywanie
   uszkodzonych wierszy i kopii konfliktowych, zapis z końcami wierszy LF.
4. `queue.py`: powtórki, dobór nowych słów, przeplatanie, utrwalanie, limity,
   dni wolne, prognoza.
5. `answers.py` i reguły czterech języków: normalizacja, klasy błędów,
   wykrywanie odpowiedzi w innym języku.
6. `courses.py`: katalog, format hasła, `course check`; kurs startowy
   60 pojęć w czterech językach (240 haseł) napisany i sprawdzony ręcznie,
   z rodzajnikami, liczbą mnogą i zdaniami przykładowymi.
7. `gate.py`: podgląd, token, termin ważności, kontrola zmian plików od
   podglądu, dziennik decyzji.
8. `cli.py`: wszystkie polecenia z rozdziału 8 oraz wyjście JSON.
9. `drill.py`: sesja w terminalu z Rich i wersja tekstowa dla `.pyz`; kolor
   i znacznik języka przy każdej karcie; zapis każdej odpowiedzi od razu;
   klawisz wyjścia z zachowaniem postępu.
10. `scripts/build.py`: budowa `vocabbot.pyz` modułem `zipapp`.

Kryteria akceptacji:

- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src`
  i `uv run pytest` przechodzą na Pythonie 3.15; `pytest` przechodzi również
  na 3.10.
- Harmonogram zgadza się z `fsrs` 6.3.3 na dziewięciu zapisanych
  scenariuszach dla trwałości 0,9 i 0,85 oraz na 200 losowych ciągach ocen
  (stabilność i trudność z dokładnością 1e-6, odstęp co do dnia).
- Testy potwierdzają: podział limitu według wag, odstęp między językami dla
  jednego pojęcia, rozdzielenie rodziny w kolejce, niezmienność listy dnia po
  przerwaniu sesji, utrwalanie bez zmiany harmonogramu, odrzucenie oceny
  spoza listy dnia, odrzucenie `known` przy powtórce, zgodność odtworzenia
  stanu dla dziennika scalonego z dwóch źródeł, ocenę odpowiedzi dla każdej
  klasy błędu w każdym z czterech języków, bramkę zmian (token, termin,
  zmiana pliku po podglądzie), polecenie `next` bez odpowiedzi w wyniku.
- `python vocabbot.pyz` wykonuje pełny dzień nauki w trybie izolowanym
  (`python -I`), bez zainstalowanych bibliotek.
- Symulacja 30 dni nauki trzech języków na kursie startowym przechodzi bez
  błędów i daje ten sam wynik w dwóch uruchomieniach.
- Ręczna próba: `vocabbot init`, `vocabbot drill` i `vocabbot status`
  w Windows Terminal z wpisywaniem znaków ä, ß, ñ, é.

#### Wynik Etapu 1 (14.11.2026, wersja 1.0.0.dev1)

Wszystkie kryteria akceptacji Etapu 1 są spełnione; tabela podaje wyniki.
Środowisko: uv 0.13.8 (zaktualizowany z 0.11.18),
Python 3.15.2 i 3.10.20 zainstalowane przez uv obok Pythona 3.14.3,
ruff 0.17.5, mypy 2.4.1, pytest 9.2.0, rich 15.0.0, fsrs 6.3.3.

| Kryterium | Wynik |
|---|---|
| ruff, ruff format, mypy, pytest na 3.15 | bez uwag; mypy w trybie strict z celem 3.10; 117 testów |
| pytest na 3.10 | 117 testów w osobnym środowisku `.venv-py310` |
| zgodność z `fsrs` 6.3.3 | 9 scenariuszy dla trwałości 0,9 i 0,85 oraz 200 losowych ciągów ocen; stabilność i trudność zgodne do 1e-6, odstępy co do dnia |
| zachowania silnika | testy obejmują podział limitu według wag, odstęp 3 dni między językami, rozdzielenie rodziny w kolejce, niezmienną kolejność po przerwaniu sesji, utrwalanie bez zmiany terminu, odmowę oceny spoza listy dnia, odmowę „znałem” przy powtórce, zgodność stanu po scaleniu dwóch dzienników, ocenę każdej klasy błędu w czterech językach, bramkę zmian i `next` bez odpowiedzi |
| `vocabbot.pyz` | archiwum 74 KiB; pełny dzień nauki dwóch języków z `python -I -S`, czyli bez żadnych pakietów spoza biblioteki standardowej |
| symulacja 30 dni | trzy języki, 12 nowych słów dziennie, niedziele wolne; dwa przebiegi dają identyczny dziennik bajt w bajt, lista dnia nie zmienia się po odpowiedziach; odstęp między językami dla każdego pojęcia wynosi co najmniej 3 dni |
| próba w konsoli | pseudokonsola ConPTY, z której korzysta Windows Terminal: `vocabbot init` z odpowiedzią „t” na pytanie o zapis, sesja ze słowami wpisanymi znak po znaku (der Bär, süß, el señor, mañana, le café, la fête) ocenionymi „wiem”, ekran `vocabbot status` |

Etap wprowadził rozwiązania, które uzupełniają plan:

1. Identyfikator hasła ma postać `<język>-<pojęcie>` (`de-c90002`), dzięki
   czemu karta zachowuje tożsamość, gdy hasło zmieni poziom w Etapie 2.
   Kurs startowy używa pojęć c90001–c90060. Własne słowa dostają
   identyfikatory losowe (`de-u3f9a1c`).
2. Silnik pokazuje nowe słowa partiami po pięć (słowo, znaczenie, formy,
   wymowa, przykład) i zaraz po partii sprawdza je pytaniem; pierwsza
   wpisana odpowiedź ustala stan początkowy karty.
3. Ocena odpowiedzi ma dwie dodatkowe klasy: `form` (inna forma tego samego
   słowa, na przykład liczba mnoga, daje „prawie”) i `blank` (pusta
   odpowiedź). Ustawienie planu `diacritics=lenient` pozwala uczącym się
   bez klawiatury z é lub ñ zaliczać odpowiedzi bez znaków diakrytycznych;
   dziennik nadal zapisuje taki błąd.
4. Bramka obejmuje także `vocabbot init` i naprawy z `vocabbot doctor`. Podgląd
   nowego folderu czeka w `~/.vocabbot/pending`. W terminalu program sam
   zadaje pytanie „Zapisać tę zmianę? [t/N]”. W trybie `--json` zwraca
   token, który umiejętność przekazuje do `vocabbot commit`.
5. Dodatkowe nowe słowa z `vocabbot today --extra N` trafiają do
   `registers/day.json`, więc obowiązują w terminalu i w czacie do końca dnia.
6. Wstrzymany język nie dostaje nowych słów i nadal ma powtórki;
   `lang.xx=off` usuwa język z planu. Hasło zgłoszone poleceniem `flag` czeka
   poza kolejką do czasu `flag --clear`.
7. Oprócz modułów z rozdziału 5 pakiet ma moduły `assets`, `errors`,
   `session` (następne karty, odpowiedzi, oceny), `plans`, `words`,
   `progress` (postęp i prognoza) oraz `doctor`.

Etap przyniósł trzy wnioski.

1. Symulacja wykryła błąd, którego nie pokazały testy pojedynczych funkcji:
   limit języka z wyczerpanym kursem przechodził na pozostałe języki przy
   każdym przeliczeniu kolejki od nowa, przez co jeden język dostał 15 nowych
   słów przy limicie 12. Silnik wybiera teraz całą listę dnia ze stanu sprzed
   tego dnia i układa kolejność na pełnej liście; kolejne odpowiedzi usuwają
   z niej tylko karty już przerobione.
2. Odtwarzanie całego dziennika przy każdej odpowiedzi wydłużało symulację do
   283 s. Dziennik czytany raz na proces i stan sprzed dnia liczony raz na
   dzień skróciły ją do 28 s; zapis z `fsync` kosztuje w Windows około 2,6 ms
   na odpowiedź i zostaje dla bezpieczeństwa dziennika.
3. Python 3.15 domyślnie pracuje w trybie UTF-8. Na Pythonie 3.10 program
   sam ustawia UTF-8 dla wejścia i wyjścia, ponieważ bez tego znak ñ nie
   przechodzi przez potok w kodowaniu cp1250.

Możesz przeprowadzić próbę w samej aplikacji Windows Terminal. Polecenie
`uv tool install .` w katalogu repozytorium instaluje program `vocabbot`,
po czym `vocabbot init`, `vocabbot drill` i `vocabbot status` prowadzą
przez całą ścieżkę.

### Etap 2. Kursy A1–B2 dla czterech języków

Zakres:

1. `fetch`: pobranie źródeł do `.cache/` poza repozytorium (około 5 GB,
   przetwarzane strumieniowo z plików `.gz`), z zapisem adresu, daty i sumy
   SHA-256 każdego pliku.
2. `concepts`: lista pojęć z CEFR-J A1–B2 (hasło, część mowy, poziom) ze
   stałymi identyfikatorami, uporządkowana według poziomu i częstości.
3. `align`: wybór znaczenia w angielskim Wikisłowniku (pierwsze znaczenie
   z tłumaczeniami na co najmniej trzy z czterech pozostałych języków),
   odpowiedniki de, es, fr i pl z rodzajem; odpowiednik główny według
   częstości w języku docelowym, pozostałe w polu `accept`.
4. `enrich`: liczba mnoga, formy podstawowe i wymowa IPA z edycji de, es, fr
   oraz z haseł angielskich.
5. `examples`: zdania Tatoeba o długości 4–10 słów z formą hasła i polskim
   tłumaczeniem, z identyfikatorem zdania do wykazu autorów.
6. `emit`: pliki kursów, `meta.json`, `NOTICE` i wykaz zdań z autorami.
7. Kontrola automatyczna: `vocabbot course check` oraz raport potoku
   (pokrycie na poziom, brakujące pola, homonimy, to samo polskie znaczenie
   dla dwóch różnych odpowiedzi w jednym języku, które wymaga zdania z luką
   albo dopisku rozróżniającego).
8. Przegląd próby: 150 losowych haseł na język i parę poziomów (1200 haseł
   łącznie) porównanych ze źródłami; klasy błędów wracają do reguł potoku,
   a potok uruchamia się ponownie.
9. Uzupełnienie reguł `data/lang` o przypadki znalezione w kursach.

Kryteria akceptacji:

- `vocabbot course check` zwraca 0 błędów dla wszystkich ośmiu plików kursów.
- Każdy język ma co najmniej 1500 haseł A1–A2 i co najmniej 3000 haseł
  B1–B2 z kompletem pól wymaganych: odpowiedź, polskie znaczenie, część
  mowy, rodzaj dla rzeczowników de, es i fr, źródła.
- Co najmniej 80% haseł A1–A2 i 60% haseł B1–B2 ma zdanie przykładowe
  z polskim tłumaczeniem.
- Udział haseł z błędnym znaczeniem, odpowiednikiem lub rodzajem w próbie
  wynosi najwyżej 3% dla A1–A2 i najwyżej 5% dla B1–B2.
- Potok uruchomiony dwukrotnie na tych samych plikach źródłowych daje
  identyczne pliki kursów.
- Plan zawiera rzeczywiste liczby haseł, pokrycia i wyniki próby.

Punkt decyzyjny etapu: gdy próba B1–B2 przekracza próg po dwóch przebiegach
potoku, przedstawię dwie drogi do wyboru. Pierwszą jest dodatkowa sesja
przeglądu w ramach tej rozmowy bez kosztów modeli. Drugą jest przebieg
wsadowy przez API modelu z wyceną przedstawioną przed uruchomieniem.

#### Wynik Etapu 2 (14.11.2026, wersja 1.0.0.dev2)

Kursy A1–B2 dla czterech języków przechodzą kontrolę kursu bez błędów i mają
w próbie 1200 haseł 1,2% błędów. Angielski spełnia też kryterium pokrycia
przykładami B1–B2, które dla niemieckiego, hiszpańskiego i francuskiego
pozostaje niespełnione; tabela podaje wyniki.

| Kryterium | Wynik |
|---|---|
| `vocabbot course check` | 0 błędów i 0 ostrzeżeń w 16 plikach kursów (cztery języki, po cztery poziomy) |
| hasła A1–A2 (próg 1500) | angielski 2036, niemiecki 2036, hiszpański 2020, francuski 2014 |
| hasła B1–B2 (próg 3000) | angielski 3583, niemiecki 3353, hiszpański 3442, francuski 3435 |
| przykłady z polskim tłumaczeniem, A1–A2 (próg 80%) | angielski 98,3%, niemiecki 88,3%, hiszpański 87,8%, francuski 87,5% |
| przykłady z polskim tłumaczeniem, B1–B2 (próg 60%) | angielski 74,5%; niemiecki 53,8%, hiszpański 49,9% i francuski 51,7% poniżej progu |
| błędy znaczenia, odpowiednika lub rodzaju w próbie (progi 3% i 5%) | A1–A2: 8 na 600 (1,3%); B1–B2: 6 na 600 (1,0%) |
| powtarzalność | dwa przebiegi potoku dają identyczne 24 pliki kursów |
| testy | 131 na Pythonie 3.15; 124 na Pythonie 3.10, gdzie testy potoku wymagają grupy `data` |

Potok w `tools/courses` pobiera źródła (3,2 GB poza repozytorium), przechodzi
raz przez ekstrakt Wikisłownika w około 3 minuty i buduje kursy w około
3 minuty. Pierwsze przebiegi z samymi regułami miały w próbkach 9–16% błędów,
głównie z powodu wieloznaczności słów (coke jako koks, fan jako wachlarz, line
jako lina), której reguły oparte na częstości i tłumaczeniu wstecznym nie
rozstrzygają. W punkcie decyzyjnym wybrałeś przegląd wsadowy: Claude Sonnet 5.5
przejrzał przez Message Batches API 6600 pojęć w 264 zapytaniach (2,15 mln
tokenów wejścia, 0,78 mln wyjścia, koszt 6,04 USD) i wskazał znaczenie, polskie
znaczenie oraz odpowiedniki z rodzajem. Decyzje przeglądu leżą
w `tools/courses/review.jsonl`, dzięki czemu kolejne budowy nie wymagają API.
Potok nadal sam ustala rodzajniki, formy i wymowę według swoich reguł
i słowników.
Próba po przeglądzie doprowadziła do trzech nowych reguł (rzeczownik
z rodzajnikiem liczby mnogiej albo występujący tylko w liczbie mnogiej odpada,
polskie znaczenie nie powtarza słowa) i do dziewięciu ręcznych poprawek decyzji
przeglądu, oznaczonych w pliku polem `corrected`.

Pokrycie przykładami B1–B2 zależy od Tatoeby, która ma zdania z większością
tych słów, często jednak bez polskiego tłumaczenia. Potok szuka go także przez
tłumaczenia na inne języki, w jednym albo dwóch krokach, i przyjmuje takie
zdanie tylko wtedy, gdy polskie tłumaczenie zawiera polskie znaczenie hasła.
Warunek powstał po przeglądzie próby, który znajdował pary zdań o różnej
treści (na przykład „Disco” przetłumaczone jako „puszka”), i obniżył pokrycie
B1–B2 o około 8 punktów procentowych.
Uzupełnienie wymaga zdań z innego źródła albo zdań przygotowanych przez model
z osobną wyceną; ta decyzja nie blokuje Etapu 3.

Etap wprowadził rozwiązania, które uzupełniają plan:

1. Jedno przejście przez surowy ekstrakt Wikisłownika (3,08 GB) daje hasła
   angielskie z tłumaczeniami oraz hasła niemieckie, hiszpańskie, francuskie
   i polskie, więc osobne pliki edycji de, es i fr okazały się zbędne.
2. Hasła o tym samym polskim znaczeniu łączą się w jedno hasło z dodatkowymi
   odpowiedziami tylko wtedy, gdy inny język potwierdza synonimię. Polskie
   homonimy dostają dopisek z angielskim słowem, na przykład „rakieta (ang.
   racket)” i „rakieta (ang. rocket)”; w kursie angielskim zostaje częstsze
   z nich.
3. Ocena odpowiedzi rozpoznaje czasownik zwrotny wpisany bez zaimka
   („ändern” dla „sich ändern”, „levantar” dla „levantarse”) jako „prawie”
   z klasą błędu „zaimek zwrotny”.
4. Kontrola kursu wymaga pól z planu (odpowiedź, polskie znaczenie, część
   mowy, rodzaj rzeczownika, źródła) i podaje pokrycie wymową oraz przykładami.
5. Każdy kurs ma plik `sentences.tsv` z autorami użytych zdań Tatoeby oraz
   plik `meta.json` z wersją kursów (`2026.11.2`) i źródłami z licencjami.
6. Kurs startowy pozostał danymi testowymi w `tests/fixtures/courses`.

Etap przyniósł trzy wnioski.

1. Reguły oparte na częstości słów i tłumaczeniu wstecznym obniżyły błędy
   z 16% do 9–14%. Dopiero przegląd znaczeń przez model, który kosztował
   6,04 USD, obniżył błędy w próbie do 1,2%.
2. Łączenie haseł o tym samym polskim znaczeniu wymaga potwierdzenia w innym
   języku, ponieważ polskie homonimy (rakieta, spadek, zmiana) sklejały różne
   słowa.
3. Próba po przeglądzie znalazła błędy samego potoku (rodzajnik liczby mnogiej
   dodany przez potok, rzeczowniki występujące tylko w liczbie mnogiej);
   reguły, które je usuwają, działają teraz dla całego kursu.

### Etap 3. Wtyczka, weryfikacja i wydanie kandydujące

Zakres:

1. Cztery umiejętności z plikami `reference/` oraz reguły wspólne.
2. Manifesty dla Claude i Codexa, dwa katalogi marketplace, zgodność wersji
   z `pyproject.toml`.
3. `scripts/validate.py`: zgodność manifestów, samowystarczalność
   umiejętności, aktualność kopii `rules.md` i `vocabbot.pyz`, zakaz
   wywołań zmieniających plan bez podglądu, brak danych osobowych
   w plikach repozytorium.
4. Sprawdzenie wersji Pythona u gospodarzy (Claude Code, Cowork, Codex)
   i ustalenie dolnej granicy.
5. Pliki testów sesyjnych z kontrolami deterministycznymi (stan dziennika
   i planu po sesji) oraz kontrola plików sesji bez modelu.
6. Dokumentacja w języku angielskim i polskim: README, QUICKSTART, PRIVACY,
   `docs/architecture.md`, CHANGELOG, angielska wersja planu.
7. Przepływ `release.yml`: tag uruchamia testy, budowę pakietu, pliku `.pyz`
   i paczki wtyczki oraz utworzenie wydania.
8. Instalacja lokalna wtyczki w Claude Code i w Codex CLI oraz przejście
   pełnej ścieżki na folderze próbnym.
9. Protokół pilotażu.

Kryteria akceptacji:

- `claude plugin validate ./plugin --profile directory --strict`
  i `scripts/validate.py` przechodzą bez błędów i ostrzeżeń.
- Każda umiejętność uruchamia silnik z własnego folderu w Claude Code
  i w Codex CLI.
- Wszystkie kontrole z Etapów 1 i 2 nadal przechodzą.
- Paczki wydania budują się lokalnie: koło i archiwum źródłowe pakietu,
  `vocabbot.pyz`, paczka wtyczki, archiwa pojedynczych umiejętności.

Czynności po Twojej zgodzie, każda osobno: utworzenie repozytorium
`dithiothreitol/vocabbot` i push, tag `v1.0.0-rc.1` z wydaniem, publikacja
pakietu w PyPI, płatne testy sesyjne.

#### Wynik Etapu 3 (14.11.2026, wersja 1.0.0-rc.1)

Kryteria akceptacji Etapu 3 są spełnione w części, która nie wymaga modelu
ani Twojej zgody. Przejście pełnej ścieżki z modelem w Claude Code
i w Codex CLI oraz testy sesyjne z modelem czekają na zgodę z wyceną;
mechaniczną część ścieżki (instalacja wtyczki i silnik uruchamiany z folderu
każdej umiejętności) sprawdziłem bez modelu. Tabela podaje wyniki.

| Kryterium | Wynik |
|---|---|
| `claude plugin validate ./plugin --profile directory --strict` | bez uwag; katalog marketplace (`claude plugin validate . --strict`) również |
| `scripts/validate.py` | 0 błędów i 0 ostrzeżeń: manifesty i wersje, 43 wywołania silnika w 17 poleceniach porównane z parserem programu, aktualność kopii, tłumaczenia dokumentów, brak sekretów i ścieżek domowych |
| silnik z folderu umiejętności | Claude Code 2.1.323 i Codex CLI 0.153.4 instalują wtyczkę z lokalnego marketplace w odizolowanych katalogach konfiguracji; każda z czterech umiejętności uruchamia `bin/vocabbot.pyz` z folderu w pamięci podręcznej gospodarza (`init`, `commit`, `today`, `status`, `words add`) |
| kontrole Etapów 1 i 2 | ruff i mypy bez uwag; 150 testów na Pythonie 3.15 oraz 143 na 3.10 (po poprawkach z przejścia ścieżki), gdzie testy potoku wymagają grupy `data`; `course check` bez błędów |
| paczki wydania | `scripts/build.py package` buduje koło i archiwum źródłowe 1.0.0rc1, `vocabbot.pyz` (2,3 MB), `vocabbot.plugin` (9,3 MB), cztery archiwa umiejętności i `SHA256SUMS` |
| testy sesyjne | 7 sesji w pięciu grupach (konfiguracja, odpowiedź po ocenie, oceny, zgoda na zapis, liczby) z 13 turami; `session_test.py --check` przygotowuje wszystkie bez modelu; testy jednostkowe potwierdzają, że kontrole wychwytują przeciek odpowiedzi i zapis planu bez zgody |
| wersje Pythona u gospodarzy | Claude Code i Codex CLI korzystają z Pythona komputera (tutaj 3.14); Cowork ma według relacji społeczności Pythona 3.10.12 na Ubuntu 22.04; claude.ai i narzędzie code execution mają według dokumentacji Pythona 3.11.12; dolna granica pozostaje 3.10 |

Etap wprowadził rozwiązania, które uzupełniają plan:

1. Test poziomujący `vocabbot quiz` wybiera słowa równomiernie z całej
   długości poziomu, czyli od najczęstszych do najrzadszych, i preferuje
   hasła z przykładem. Poziom liczy się jako znany od 80% trafnych odpowiedzi,
   przy czym ocena „prawie” liczy się w połowie. Test w terminalu kończy się
   na pierwszym nieznanym poziomie.
2. Polecenie `words add` przesuwa słowo obecne w kursie na początek kolejki
   zamiast je kopiować (wiersz `{"ref": ...}` w `own.jsonl`), pomija słowa
   będące już w nauce i ostrzega o tym samym polskim znaczeniu oraz o języku
   spoza planu.
3. Wynik `status` podaje słowa poznane w ostatnich siedmiu dniach (`recent`)
   i odpowiedzi udzielone w innym języku (`confusions`), a polecenie `lookup`
   znajduje hasła dla słowa albo polskiego znaczenia. Karty czekające dziś
   w sesji mają znacznik `waiting_today`, dzięki któremu trener nie zdradza
   ich odpowiedzi.
4. Polecenie `reveal` pokazuje znaczenie karty rozpoznawania i odmawia kart
   produkcji, więc reguła odpowiedzi po ocenie ma oparcie w silniku także dla
   kart rozpoznawania.
5. Silnik znajduje folder nauki w folderze bieżącym, gdy ten zawiera plan,
   co obsługuje Cowork i folder projektu. Polecenie `vocabbot use` wskazuje
   istniejący folder na drugim komputerze, a `init --set` przyjmuje dowolne
   ustawienia planu w pierwszym podglądzie.
6. Każda umiejętność ma oprócz `shared/rules.md` plik `shared/labels.md`
   z polskimi nazwami ocen, klas błędów i części mowy, generowany z tekstów
   silnika.
7. Plik `vocabbot.pyz` powstaje z posortowanych wpisów o stałym czasie.
   Cztery kopie w umiejętnościach są identyczne, więc git przechowuje plik
   raz, a kontrola aktualności porównuje zawartość archiwum niezależnie od
   wersji biblioteki zlib.

Etap przyniósł trzy wnioski.

1. Kurs zaczyna się od krótkich słów funkcyjnych (an, sie, ich, la), które
   występują w zwykłym tekście zbyt często, aby ich obecność w odpowiedzi
   modelu dowodziła przecieku. Kontrola przecieku w testach sesyjnych
   korzysta dlatego z uczącego się na poziomach B1–B2 i ze słów od czterech
   liter.
2. Przykład słowa funkcyjnego bywa zdaniem z inną częścią mowy tej samej
   formy, na przykład hiszpańskie „la” jako zaimek ma przykład, w którym „la”
   jest rodzajnikiem. To ograniczenie potoku z Etapu 2 dotyczy homografów;
   pilotaż pokaże jego skalę, a poprawka należy do potoku kursów.
3. Na tym komputerze `py -3` wskazuje usunięty interpreter, podczas gdy
   `python3` i `python` działają, dlatego reguła silnika podaje kolejność
   `python3`, `python`, `py -3`.

Do wersji 1.0 prowadzą czynności z tabeli; każda czeka na Twoją osobną
zgodę.

| Czynność | Koszt | Uwagi |
|---|---|---|
| testy sesyjne z modelem: `session_test.py --model sonnet` (7 sesji, 13 tur) | szacunkowo 3–6 USD przy Claude Sonnet 5.5 | skrypt przerywa pracę po przekroczeniu `--max-cost-usd` |
| przejście ścieżki z modelem w Claude Code i w Codex CLI na folderze próbnym | zwykła sesja pracy na Twoich kontach | instalacja i silnik sprawdzone bez modelu |
| repozytorium `dithiothreitol/vocabbot` i push | brak | |
| tag `v1.0.0-rc.1` i wydanie przez `release.yml` | brak | wydanie zawiera paczki z tabeli wyników |
| publikacja w PyPI | brak | zaufane publikowanie, zmienna repozytorium `PUBLISH_PYPI` |
| pilotaż według `docs/pilot.pl.md` | brak | po wydaniu |

#### Przejście ścieżki z modelem (15.11.2026)

Za Twoją zgodą z 15.11.2026 przeszedłem pełną ścieżkę w Claude Code
(wtyczka z folderu repozytorium, model Sonnet 5.5, 17 tur, 5,24 USD według
`claude -p`) oraz w Codex CLI (wtyczka z lokalnego marketplace, model
gpt-6-astra, 6 tur na Twoim koncie), na folderach próbnych w katalogu
tymczasowym. Ścieżka objęła konfigurację z testem poziomującym, sesję
z utrwalaniem i zmianą oceny na prośbę, własne słowa z dopiskiem, trenera
oraz zmianę planu. Każda ocena w dziennikach pochodzi z silnika. Tabela
zestawia obserwacje z poprawkami, które weszły do wersji 1.0.0-rc.1.

| Obserwacja | Poprawka |
|---|---|
| W dniu wolnym model proponował powtórki przed terminem, które nowemu uczącemu się nie dają żadnych słów | instrukcja sesji wskazuje `today --extra` dla nowych słów w dniu wolnym |
| Model podawał kody klas błędów („wrong”, „article”) i nazwy pól wyniku | silnik zwraca polskie nazwy (`grade_pl`, `errors_pl`, `errors_30_pl`), a reguła wyklucza z rozmowy polecenia, pola i identyfikatory |
| Ostrzeżenie o tym samym znaczeniu brzmiało jak zapowiedź dopisku, więc model obiecał dopisek nieobecny w podglądzie | nowa treść ostrzeżenia; instrukcja `vocab-words` prowadzi do nowego podglądu z dopiskiem i traktuje „tak, ale…” jako prośbę o nowy podgląd |
| Piaskownica Codexa blokuje zapis poza folderem roboczym, dlatego `init` kończył się śladem stosu przy tworzeniu `~/.vocabbot/pending` | podgląd nowego folderu czeka awaryjnie w samym folderze, wskaźnik w `~/.vocabbot` jest opcjonalny (pole `skipped`), `commit` szuka podglądu także w folderze bieżącym i w folderze z `--learner`, a odmowa zapisu daje błąd `io_error` w JSON |
| Codex obszedł tę blokadę, podmieniając katalog domowy w opakowaniu Pythona, i zapisał plan w tej samej turze co podgląd, bez potwierdzenia | reguły zakazują obchodzenia silnika, każą zakończyć turę na pytaniu o zapis i wyjaśniają, że prośba z kompletem ustawień nie zastępuje potwierdzenia; w ponownej próbie Codex zatrzymał się na podglądzie i zapisał plan dopiero po „tak” |
| Codex pokazał nowe słowa i pytania o nie w jednej wiadomości | instrukcja sesji rozdziela wprowadzenie słów i pytania |
| Własne słowo podane jako obiekt JSON dostawało lemat z rodzajnikiem | silnik wyznacza lemat rzeczownika bez rodzajnika |

Przejście przyniosło trzy wnioski.

1. Reguła potwierdzenia zależy od modelu, ponieważ silnik nie rozróżnia,
   kto powiedział „tak”. Jeden z dwóch modeli złamał ją przy pierwszej
   próbie. Hook potwierdzenia w Claude Code (wzorzec HouseholdBota)
   przeniósłby potwierdzenie do okna gospodarza; rozdział 2.3 go pominął,
   dlatego jego dodanie pozostaje Twoją decyzją.
2. Kursy zaczynają się od słów funkcyjnych, których przykłady często
   pokazują inną część mowy tej samej formy (francuskie „la” i „le” jako
   zaimki z przykładami z rodzajnikami, niemieckie „das”, hiszpańskie
   „lo más”), więc uczący się trafia na nie w pierwszej sesji. Poprawka
   w potoku, na przykład pytanie bez zdania dla takich haseł, wymaga nowej
   budowy kursów i jest decyzją przed pilotażem.
3. Nakładka `codex.CMD` z npm obcina argument na pierwszym znaku nowej linii,
   dlatego skrypt przejścia przekazuje treść tury na wejściu standardowym
   (`codex exec -`).

#### Repozytorium i wydanie (15.11.2026)

| Czynność | Wynik |
|---|---|
| repozytorium | publiczne `github.com/dithiothreitol/vocabbot` z opisem i tematami, środowisko `pypi` do zaufanego publikowania |
| CI | zielone na Pythonie 3.10 i 3.15 oraz w zadaniu wtyczki po dwóch poprawkach: `astral-sh/setup-uv` nie ma ruchomego tagu `v10`, dlatego przepływy przypinają `v10.3.3`; ruff klasyfikuje moduły potoku kursów jawnie, ponieważ lokalny katalog `build/` zmieniał kolejność importów |
| tag i wydanie | `v1.0.0-rc.1`, wydanie przedpremierowe z kołem, archiwum źródłowym, `vocabbot.pyz`, `vocabbot.plugin`, czterema archiwami umiejętności i `SHA256SUMS`; sumy pobranych plików zgadzają się |
| instalacja z GitHuba | `claude plugin install vocabbot --marketplace dithiothreitol/vocabbot` w odizolowanej konfiguracji oraz `uvx --from git+https://github.com/dithiothreitol/vocabbot@v1.0.0-rc.1 vocabbot` działają |
| PyPI | `vocabbot 1.0.0rc1` opublikowany 15.11.2026 tokenem z Twojego konta: koło i archiwum źródłowe pobrane z wydania na GitHubie i sprawdzone sumami; `uv tool install vocabbot` i `pip` instalują tę wersję. Kolejne wydania mogą korzystać z zaufanego wydawcy (projekt `vocabbot`, właściciel `dithiothreitol`, repozytorium `vocabbot`, przepływ `release.yml`, środowisko `pypi`) |

#### Wersja 1.0.0-rc.2 (15.11.2026)

Obie decyzje z przejścia ścieżki zatwierdziłeś 15.11.2026, a wersja
1.0.0-rc.2 je wprowadza.

| Zmiana | Wynik |
|---|---|
| hook potwierdzenia (`plugin/hooks/`) | w Claude Code i Coworku każdy `commit` silnika oraz każdy bezpośredni zapis w folderze nauki trafia do okna zgody gospodarza z treścią podglądu; zmienna `VOCABBOT_HOOK=off` wyłącza okno w testach bez człowieka; 4 testy, kontrola w `validate.py`, `claude plugin validate --profile directory --strict` bez uwag |
| przykłady słów funkcyjnych (kursy 2026.11.3) | słowo pisane jak rodzajnik, ale będące inną częścią mowy (francuskie i hiszpańskie „la”, „le”, „les”, „los”, „un”, „unos”), dostaje pytanie bez zdania; niemieckie „das” zachowuje przykład tylko wtedy, gdy po nim nie stoi rzeczownik; zmieniło się 7 haseł, a kilka sąsiednich dostało inne przykłady; `course check` bez błędów, dwie budowy identyczne |
| grafiki (`docs/assets/`) | logo na początku obu README, widoczne także na stronie PyPI, oraz obraz do udostępniania repozytorium 1280×640; źródła HTML i polecenie renderowania leżą obok plików PNG |
| testy | 154 na Pythonie 3.15 i 147 na 3.10; CI zielone |
| wydanie | tag `v1.0.0-rc.2`, wydanie przedpremierowe na GitHubie z kompletem paczek, `vocabbot 1.0.0rc2` w PyPI (pliki z wydania sprawdzone sumami), wtyczka w Twoim Codexie odświeżona do rc.2 |

Obraz do udostępniania wymaga jednorazowego wgrania w ustawieniach
repozytorium (Settings, Social preview), ponieważ GitHub nie udostępnia do
tego interfejsu programistycznego.

---

### Etap 4. Treść kursów, mechanika i sesja w terminalu

Audyt z 15.11.2026, wykonany przed testami sesyjnymi, porównał silnik, kursy
i program w terminalu z kursami SuperMemo. Silnik odwzorowuje przebieg nauki
SuperMemo: sekcje powtórek, nowych słów i utrwalania, trzy oceny, utrwalanie
bez wpływu na harmonogram oraz cel trwałości 90%. Kursom brakuje części
podstawowego słownictwa, około 6% przykładów używa słowa w innym znaczeniu
lub innej części mowy, a sesja w terminalu wypisuje zwykły tekst. Etap 4
zatwierdziłeś 15.11.2026 razem z czterema decyzjami: kolejność prac (treść,
mechanika, terminal, testy sesyjne), uzupełnienie podstaw bez kosztów
modeli, przegląd przykładów modelem oraz ocena „nie wiem” za zły rodzajnik.

| Obszar | Ustalenie audytu |
|---|---|
| podstawowe słowa | kursy nie mają między innymi angielskich yes, no, with, house, hello, thanks i nazw miesięcy, niemieckich ja, nein, kein, du, danke, Eltern, Leute, kennen, heißen, hiszpańskich sí, gracias, estar, haber, tú, conocer ani francuskich oui, non, merci, tu, chez, il y a, gens, combien |
| przyczyny w potoku | 1018 pojęć bez polskiego tłumaczenia w tabeli tej samej części mowy, 133 pojęcia bez angielskiego hasła tej części mowy (nazwy miesięcy są w Wikisłowniku nazwami własnymi), określniki CEFR-J poza mapą części mowy, około 1000 scaleń na język, 64 angielskie hasła usunięte jako homonimy (wśród nich with i house), rzeczowniki występujące tylko w liczbie mnogiej odrzucone |
| początek A1 | słowa funkcyjne stanowią 87–97% pierwszych 30 haseł, a część z nich ma niejednoznaczne lub zawężone znaczenie (niemieckie „mit” jako „razem”) |
| przykłady | 11 z 180 zdań w losowej próbie używa słowa w innym znaczeniu lub innej części mowy; kilkadziesiąt zdań z Tatoeby ma treść wulgarną |
| harmonogram | terminy nie mają rozrzutu, więc słowa poznane jednego dnia wracają razem; „prawie” za zły rodzajnik wydłuża odstęp; parametry FSRS są domyślne dla każdego uczącego się |
| terminal | zwykły tekst, kolor tylko z pakietem Rich, dwa potwierdzenia na każdą kartę, prognoza jako lista 30 wierszy |

Zakres:

1. Potok kursów odzyskuje pojęcia: określniki CEFR-J dostają swoją część
   mowy, pojęcie bez tabeli tłumaczeń korzysta z tabeli innej części mowy
   tego samego hasła (wykrzyknik, nazwa własna), a rzeczownik występujący
   tylko w liczbie mnogiej wchodzi do kursu z rodzajnikiem liczby mnogiej
   (die Eltern, les gens). Odzyskane pojęcie wchodzi do kursu wyłącznie
   z decyzją przeglądu modelem albo redakcji.
2. Plik redakcji `tools/courses/editor.jsonl` zawiera decyzje dla
   odzyskanych pojęć A1–A2, pojęcia właściwe jednemu językowi (estar,
   haber, kein, chez, kennen, conocer, connaître i podobne), rozdzielenie
   częstych synonimów i homonimów dopiskiem w polskim znaczeniu (house
   i home, with i of) oraz poprawki znaczeń słów funkcyjnych. Redakcja nie
   korzysta z płatnych modeli.
3. Poziom A1 zaczyna się od listy startowej redakcji: powitań, „tak”
   i „nie”, zaimków osobowych oraz podstawowych czasowników i rzeczowników.
   Dalsze hasła każdego poziomu idą według częstości, a każde kolejne
   dziesięć haseł zawiera najwyżej trzy słowa funkcyjne.
4. Claude Sonnet 5.5 przez Message Batches API ocenia do trzech zdań
   kandydujących na każde hasło (znaczenie, część mowy, wierność polskiego
   tłumaczenia, stosowność treści) i wybiera pierwsze poprawne albo żadne.
   Decyzje leżą w `tools/courses/examples.jsonl`, dzięki czemu kolejne
   budowy nie wymagają API, a filtr wulgaryzmów w potoku chroni hasła bez
   decyzji. Limit kosztu wynosi 8 USD.
5. Silnik rozrzuca terminy od 3 dni wzwyż według zakresów FSRS. Rozrzut
   wynika z identyfikatora karty i dnia odpowiedzi, więc oba komputery
   widzą te same terminy. W niemieckim, hiszpańskim i francuskim rodzajnik
   innego rodzaju albo jego brak przy rzeczowniku, którego rodzajnik
   pokazuje rodzaj, daje ocenę „nie wiem”. Reguły odpowiedzi i kontrola
   kursu obsługują rzeczowniki w liczbie mnogiej.
6. Silnik dopasowuje początkowe odstępy, czyli pierwsze cztery parametry
   FSRS-6, do dziennika uczącego się, gdy dziennik ma wystarczająco wiele
   drugich odpowiedzi. `status` porównuje zmierzoną trwałość z docelową.
7. Nowy moduł `term.py` na bibliotece standardowej wykrywa możliwości
   terminala (`NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, tryb VT w Windows),
   zastępuje znaki Unicode znakami ASCII tam, gdzie terminal ich nie
   pokazuje, i zawija tekst z uwzględnieniem szerokości znaków. Pakiet Rich
   przestaje być potrzebny.
8. `vocabbot drill` dostaje nowy wygląd sesji, a `vocabbot` bez polecenia
   pokazuje ekran startowy z planem dnia. Sesja pokazuje zwartą kartę,
   zapisuje poprawną odpowiedź bez dodatkowego klawisza, pokazuje różnicę
   znak po znaku, zwija kartę po odpowiedzi do jednego wiersza i przyjmuje
   polecenia `/cofnij`, `/znam`, `/koniec` i `/pomoc`. Wiersz postępu
   pokazuje miejsce w sesji, a podsumowanie podaje wynik, słowa do poprawy,
   jutrzejsze obciążenie i aktywność ostatnich tygodni.
9. `today`, `status` i `forecast` dostają paski postępu poziomów, wykres
   obciążenia i zwięzły układ liczb.
10. Wersja 1.0.0-rc.3: manifesty, `pyproject.toml`, CHANGELOG, dokumentacja
    w obu językach i plan.

Kryteria akceptacji:

- `vocabbot course check` przechodzi bez błędów, a każde słowo z listy
  kontrolnej audytu jest w kursie albo ma w planie opisany powód
  nieobecności.
- Każde hasło z przykładem ma decyzję przeglądu przykładów albo pochodzi
  z budowy po przeglądzie i przeszło filtr wulgaryzmów.
- Pierwsze 30 haseł A1 każdego języka zawiera najwyżej 9 słów funkcyjnych.
- Testy obejmują rozrzut terminów, ocenę rodzajnika, rzeczowniki w liczbie
  mnogiej, dopasowanie parametrów oraz moduł terminala w trybie bez
  kolorów i ze znakami ASCII.
- Kontrole z Etapów 1–3 przechodzą, a dwie budowy kursów dają identyczne
  pliki.

Czynności po Twojej zgodzie, każda osobno: testy sesyjne na wersji rc.3,
push, tag i wydanie rc.3. Wszystkie zatwierdziłeś 15.11.2026.

#### Wynik Etapu 4 (15.11.2026, wersja 1.0.0-rc.3)

Etap 4 domknął treść kursów, mechanikę i sesję w terminalu. Kursy w wersji
2026.11.4 mają 23 095 haseł zamiast 21 919, każde słowo z listy kontrolnej
audytu jest w kursie, a każde zdanie przykładowe przeszło przegląd modelem.

| Kryterium | Wynik |
|---|---|
| `vocabbot course check` | 0 błędów i 0 ostrzeżeń w 16 plikach kursów |
| hasła | angielski 6286, niemiecki 5649, hiszpański 5581, francuski 5579 |
| lista kontrolna audytu | wszystkie słowa w kursach, w tym yes, no, with, house, hello, thank you, nazwy miesięcy, ja, nein, kein, du, danke, die Eltern, die Leute, kennen, heißen, sí, gracias, estar, hay, tú, conocer, oui, non, merci, tu, chez, il y a, les gens, combien; angielskie rodzajniki the, a, an nie są kartami, ponieważ polski nie ma ich odpowiedników |
| decyzje redakcji | 229 wierszy w `tools/courses/editor.jsonl`: 10 nowych pojęć (między innymi ty, Pan, nazywać się, estar, es gibt, znać, ile, chez, rodzice, chętnie), 43 pozycje listy startowej A1, decyzje dla 24 z 46 określników CEFR-J (23 w kursach), 12 nazw miesięcy, około 90 odzyskanych pojęć A1–A2, 42 pojęcia ze znaczeniem rozdzielonym dopiskiem, 5 pojęć usuniętych |
| początek A1 | pierwsze 30 haseł zawiera 6–7 słów funkcyjnych (próg 9); poziom zaczyna się od „cześć”, „dzień dobry”, „tak”, „nie”, „dziękuję”, „proszę” |
| przegląd przykładów | Claude Sonnet 5.5 ocenił 42 156 zdań kandydujących dla 16 406 haseł w 411 zapytaniach: 14 911 zdań zostaje, 1495 haseł nie ma poprawnego zdania; pierwszy kandydat odpadł w 3406 przypadkach (najczęściej tłumaczenie, znaczenie i część mowy); koszt 6,36 USD plus 0,03 USD za zapytanie próbne |
| przykłady z polskim tłumaczeniem, A1–A2 (próg 80%) | angielski 90,0%, niemiecki 84,4%, hiszpański 82,8%, francuski 81,9% |
| przykłady z polskim tłumaczeniem, B1–B2 (próg 60%) | angielski 66,2%; niemiecki 48,5%, hiszpański 44,3% i francuski 47,1% poniżej progu, ponieważ przegląd odrzucił zdania z innym znaczeniem |
| silnik | rozrzut terminów według zakresów FSRS z kluczem karta i dzień; „nie wiem” za rodzajnik innego rodzaju i za brak rodzajnika, który pokazuje rodzaj; rzeczowniki tylko w liczbie mnogiej i miesiące bez rodzajnika; dopasowanie początkowych stabilności od 40 drugich odpowiedzi; `status` pokazuje odstępy po pierwszej odpowiedzi i trwałość względem celu |
| terminal | `term.py` na bibliotece standardowej, nowa sesja `vocabbot drill`, ekran startowy `vocabbot`, nowy wygląd `today`, `status` i `forecast`; pakiet nie zależy już od Rich |
| powtarzalność | dwie budowy kursów dają identyczne pliki |
| testy | 190 na Pythonie 3.15; 173 na Pythonie 3.10 (1 pominięty bez grupy `data`) |
| kontrole wtyczki | `validate.py` 0 błędów i 0 ostrzeżeń, `session_test.py --check` 7 z 7, `claude plugin validate --profile directory --strict` bez uwag |
| testy sesyjne z modelem (Claude Sonnet 5.5, zgoda z 15.11.2026) | pierwszy przebieg 6 z 7 za 1,78 USD; kontrola testu poziomującego uznała za przeciek słowo ze zdania podanego przez silnik, będące odpowiedzią innego pytania; po poprawce silnika (takie pytanie traci zdanie) i kontroli (zdania silnika nie są przeciekiem) test przechodzi za 0,31 USD; razem 7 z 7 za 2,09 USD |

Próba sesji w terminalu ujawniła błąd, który lista startowa uczyniła
częstym: oznaczenie słowa jako znanego przeliczało całą listę dnia, a odstęp
między językami dla jednego pojęcia blokował wtedy kartę już pokazaną
w drugim języku. Słowa planu powstają teraz najpierw i nie zmieniają się
w ciągu dnia, a słowa dodane później dochodzą po nich; test sprawdza, że
pokazana karta zostaje na liście.

Wnioski:

1. Kursy budowane wyłącznie z listy CEFR-J i reguł potoku tracą słowa
   podstawowe na styku części mowy (nazwy miesięcy jako nazwy własne,
   określniki poza mapą, angielskie czasowniki o pisowni rzeczownika). Plik
   redakcji z decyzjami człowieka uzupełnia te luki tanio i powtarzalnie.
2. Przegląd przykładów modelem odrzucił co piątego pierwszego kandydata.
   Reguły dopasowania słowa w zdaniu nie rozpoznają znaczenia, dlatego
   każde nowe zdanie wymaga takiego przeglądu.
3. Pokrycie przykładami B1–B2 dla niemieckiego, hiszpańskiego
   i francuskiego zależy od liczby zdań Tatoeby z polskim tłumaczeniem.
   Uzupełnienie wymaga zdań z innego źródła albo tłumaczeń przygotowanych
   przez model, z osobną wyceną.

---

### Etap 5. Harmonogram dopasowany do uczącego się

Etap 5 dodałeś 15.11.2026 w trakcie Etapu 4. Obejmuje trzy zagadnienia:
pełne dopasowanie parametrów FSRS do uczącego się, plan dnia świadomy jego
obecności oraz narzędzie, które odtwarza dziennik i porównuje każdy wariant
z FSRS-6. Narzędzie powstaje pierwsze, ponieważ rozstrzyga, czy dwa pozostałe
warianty poprawiają przewidywanie i obciążenie względem FSRS-6. Etap 4 wnosi
pierwszy krok dopasowania: początkowe stabilności liczone z drugich
odpowiedzi uczącego się.

| Zagadnienie | Stan na 15.11.2026 | Źródło |
|---|---|---|
| Optymalizator FSRS | py-fsrs dopasowuje parametry w dodatku `fsrs[optimizer]` z ciężkimi zależnościami; FSRS-Optimizer korzysta z PyTorch; fsrs-rs w wersji 1.2.1 zostaje przy parametrach domyślnych poniżej 64 pozycji treningowych | repozytoria open-spaced-repetition |
| Miary porównania | benchmark algorytmów powtórek porównuje log loss, RMSE(bins) i AUC na odpowiedziach przewidywanych przed poznaniem wyniku | srs-benchmark, opis Expertium |
| Plan według obecności | Anki od wersji 24.11 ma „Easy Days” (mniej powtórek w wybrane dni tygodnia, ustawiane ręcznie) i równoważenie obciążenia w granicach rozrzutu | dokumentacja FSRS Helper i Anki |

Zakres:

1. `vocabbot replay` odtwarza dziennik w kolejności czasu i dla każdej
   powtórki zapisuje przewidywaną trwałość każdego wariantu przed poznaniem
   odpowiedzi. Raport podaje log loss, RMSE(bins) i AUC dla każdego
   wariantu oraz różnicę względem FSRS-6 z parametrami domyślnymi, całość
   i osobno dla każdego języka. Dopasowanie korzysta z wcześniejszej części
   dziennika, a ocena z późniejszej, więc wariant nie widzi odpowiedzi, które
   przewiduje.
2. Ta sama komenda symuluje obciążenie: liczbę powtórek dziennie, minuty
   i przewidywaną trwałość każdego wariantu harmonogramu na kolejne tygodnie.
   Symulacja korzysta z tych samych reguł co `forecast`.
3. Pełne dopasowanie 21 parametrów FSRS-6 na bibliotece standardowej
   (spadek gradientu z regularyzacją w stronę wartości domyślnych), osobno
   dla każdego języka, gdy dziennik języka ma wystarczająco wiele powtórek.
   Silnik przyjmuje parametry dopasowane tylko wtedy, gdy `replay` pokazuje
   na późniejszej części dziennika niższy log loss niż FSRS-6 z parametrami
   domyślnymi.
4. Plan dnia świadomy obecności. Silnik liczy ze zwykłych statystyk
   dziennika, bez sieci, prawdopodobieństwo nauki w każdy dzień tygodnia
   i typową liczbę minut. Termin powtórki wybiera w granicach rozrzutu dzień
   z większą szansą obecności i mniejszym obciążeniem, liczba nowych słów
   pilnuje, żeby prognozowane minuty mieściły się w typowym czasie
   uczącego się, a przed przewidywaną przerwą sesja proponuje powtórki
   przed terminem. Wynik zostaje funkcją dziennika i planu, więc oba
   komputery liczą ten sam plan.
5. `status` i trener pokazują, które parametry obowiązują, z ilu odpowiedzi
   powstały i jak wypadają w `replay`.

Kryteria akceptacji:

- `replay` na dziennikach syntetycznych z testów odtwarza znane parametry
  generatora, a dla FSRS-6 z parametrami domyślnymi daje wyniki zgodne
  z modułem `fsrs`.
- Dopasowane parametry obowiązują wyłącznie przy lepszym wyniku
  w `replay`; w przeciwnym razie silnik zostaje przy FSRS-6.
- Plan według obecności zmniejsza w symulacji liczbę zaległych powtórek po
  dniach bez nauki bez spadku przewidywanej trwałości poniżej celu.
- Kolejka dnia pozostaje identyczna na dwóch komputerach z tym samym
  dziennikiem.

Dane: dopasowanie i plan według obecności potrzebują kilku tygodni
dziennika, dlatego narzędzie `replay` powstaje przed końcem pilotażu,
a dopasowanie i plan korzystają z dziennika pilotażu. Etap nie wymaga
kosztów modeli.

---

## 11. Weryfikacja kompletności

### 11.1 Funkcje kursów SuperMemo

| Funkcja | Wersja 1.0 | Realizacja |
|---|---|---|
| Kurs słownictwa według częstości z poziomami CEFR | tak | kursy A1–A2 i B1–B2, kolejność według częstości |
| Strona słowa: znaczenie, przykład, wymowa | tak | znaczenie polskie, zdanie z luką, IPA |
| Trzy oceny | tak | `know`, `almost`, `dont_know` |
| Nauka, powtórki, utrwalanie | tak | jedna kolejka dnia w tej kolejności |
| Powtórka przy trwałości około 90% | tak | FSRS-6, trwałość w planie, rozrzut terminów, początkowe odstępy dopasowane do dziennika; pełne dopasowanie w Etapie 5 |
| Pomijanie znanych słów | tak | ocena „znałem” i test poziomujący |
| Liczba kart dziennie, czas trwania kursu | tak | `plan`, `forecast` |
| Kalendarz z dniami wolnymi | tak | `days_off` |
| Powtórki mieszane z kilku kursów | tak | ustawienie domyślne z regułami dla rodzin kart |
| Statystyki nauki | tak | `status` |
| Rozmowa z asystentem na poznanym słownictwie | tak | `vocab-coach` |
| Synchronizacja między komputerami | tak | folder nauki w dysku synchronizowanym, scalanie dzienników w `doctor` |
| Obrazy, nagrania lektora, rozpoznawanie mowy | po 1.0 | rozdział 14 |
| Aplikacja na telefon | po 1.0 | rozdział 14 |

Funkcje wykraczające poza kursy SuperMemo: wagi języków, odstęp między
językami dla jednego pojęcia, wykrywanie odpowiedzi w innym języku,
zestawienia słów mylonych między językami, własne słowa z dowolnego tekstu.

### 11.2 Poziomy weryfikacji

| Poziom | Zakres | Narzędzie |
|---|---|---|
| 1. Struktura | pakiet, manifesty, umiejętności, kursy | `ruff`, `mypy`, `scripts/validate.py`, `vocabbot course check`, `claude plugin validate` |
| 2. Arytmetyka | harmonogram, kolejka, ocena odpowiedzi, bramka, odtworzenie stanu | `pytest`, biblioteka `fsrs` jako wzorzec |
| 3. Zachowanie | umiejętności w wieloturowych sesjach na folderze próbnym | `scripts/session_test.py` z `claude -p`, po Twojej zgodzie |
| 4. Użycie | codzienna nauka | pilotaż |

---

## 12. Koszty i zgody

| Pozycja | Koszt modeli | Zgoda |
|---|---|---|
| Etap 1 | brak | akceptacja planu |
| Etap 2, potok i przegląd próby | brak | akceptacja planu |
| Etap 2, przebieg wsadowy przez API | wycena przed uruchomieniem | osobna, wyłącznie w punkcie decyzyjnym |
| Etap 3, testy sesyjne `claude -p` | szacunkowo 3–6 USD przy Claude Sonnet 5.5 (7 sesji, 13 tur) | osobna |
| Etap 4, redakcja podstawowych słów | brak | zatwierdzona 15.11.2026 |
| Etap 4, przegląd przykładów przez Message Batches API | do 8 USD przy Claude Sonnet 5.5 | zatwierdzony 15.11.2026 |
| Etap 4, testy sesyjne na wersji rc.3 | szacunkowo 3–6 USD przy Claude Sonnet 5.5 | osobna |
| Etap 5, harmonogram dopasowany do uczącego się | brak | akceptacja etapu |
| Repozytorium GitHub, tag, wydanie, PyPI | brak | osobna dla każdej czynności |

Nazwa `vocabbot` była 14.11.2026 wolna w PyPI oraz na koncie
`dithiothreitol` w GitHub.

---

## 13. Ryzyka i sposoby postępowania

| Ryzyko | Postępowanie |
|---|---|
| Automatyczny wybór znaczenia w Wikisłowniku daje błędne odpowiedniki | próg błędu w próbie, reguły potoku poprawiane klasami błędów, pole `checked`, zgłoszenia `flag`, punkt decyzyjny Etapu 2 |
| Warunki CEFR-J nie opisują wprost dalszego rozpowszechniania | odczyt pliku licencji na początku Etapu 2; kurs podaje poziom jako cechę pojęcia z cytowaniem źródła; wariant zapasowy wyznacza poziomy z pasm częstości wordfreq |
| Liczba haseł z kompletem pól poniżej progów | raport pokrycia po pierwszym przebiegu; uzupełnienie z edycji de, es, fr i pl Wikisłownika; aktualizacja progów w planie za Twoją wiedzą |
| Starsza wersja Pythona w piaskownicy gospodarza | zgodność kodu z 3.10, test w CI, sprawdzenie gospodarzy w Etapie 3 |
| Wpisywanie znaków diakrytycznych w terminalu | znaki zastępcze w regułach języka, ocena „prawie” za brak znaku, próba ręczna w Etapie 1 |
| Dane wordfreq pochodzą z okresu do 2021 roku | słownictwo A1–B2 zmienia się wolno; częstość służy wyłącznie do kolejności |
| Model w czacie podpowiada odpowiedź | `next` bez odpowiedzi, reguła 1, test sesyjny tej reguły |

---

## 14. Rozszerzenia po wersji 1.0

- Wymowa przez syntezę mowy systemu operacyjnego oraz nagrania z Wikisłownika.
- Sesja na telefonie: serwer na własnym VPS albo strona w sieci domowej,
  korzystające z tego samego folderu nauki.
- Kolejne języki nauki i angielski jako drugi język bazowy.
- Karty rozpoznawania i karty ze zdaniem jako ustawienie domyślne dla
  poziomu B1–B2.
- Obrazy do haseł z otwartych zbiorów.

---

## Źródła

- SuperMemo, katalog kursów: https://www.supermemo.com/pl/catalog
- SuperMemo, Extreme English Basic: https://supermemo.com/en/courses/extreme-english-1
- SuperMemo, metoda: https://www.supermemo.com/en/supermemo-method
- SuperMemo, sekcja powtórek i trzy oceny: https://supermemo.com/blog/repeat-section-and-3-buttons-assessment
- SuperMemo, powtórki mieszane: https://www.supermemo.com/en/faq/mixed-repetitions
- SuperMemo, plan nauki: https://www.supermemo.com/en/faq/learning-plan
- FSRS, opis algorytmu: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
- py-fsrs: https://github.com/open-spaced-repetition/py-fsrs
- kaikki.org, dane Wikisłownika: https://kaikki.org/dictionary/rawdata.html
- CEFR-J Vocabulary Profile: https://github.com/openlanguageprofiles/olp-en-cefrj
- Tatoeba, pliki do pobrania: https://tatoeba.org/downloads
- fsrs-rs: https://docs.rs/fsrs/
- Benchmark algorytmów powtórek: https://github.com/open-spaced-repetition/srs-benchmark oraz https://expertium.github.io/Benchmark.html
- FSRS Helper (Easy Days, równoważenie obciążenia): https://github.com/open-spaced-repetition/fsrs4anki-helper
- Waisman Center, przeplatanie języków: https://www.waisman.wisc.edu/?p=36980
- MPI Nijmegen, „New in, old out”: https://forms.mpi.nl/node/55663
- Bartolotti i Marian, nauka trzeciego języka: https://bilingualism.northwestern.edu/wp-content/uploads/2018/05/BartolottiMarian2018.pdf
