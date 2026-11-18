# Plan implementacji VocabBot

[English](development-plan.md) · **Polski**

Stan: 2026-11-16, po Etapie 7 (wersja 1.0.0-rc.6, w pakiecie Pythona
1.0.0rc6). Plan zaakceptowałeś 14.11.2026, a Etapy 4, 5, 6 i 7 dodałeś
15.11.2026. Etap 7 dał kurs włoski i sesję po jednej karcie. Etapy 8 i 9
(uwagi z pilotażu: wymowa, przykłady, licznik, ChatGPT oraz karta w oknie
czatu) zrealizowałem 16.11.2026 i za Twoją zgodą wydałem jako `v1.0.0-rc.7`
na GitHubie i w PyPI oraz wdrożyłem na serwer. Etap 10 (etapy sesji jak
w SuperMemo: wybór etapu, kolejne słowa, kolejne tury powtórek, nowe słowo
jako pytanie, dwie oceny w utrwalaniu i kolejność powtórek) dodałeś
16.11.2026; za Twoją zgodą wydałem go jako `v1.0.0-rc.8` na GitHubie
i w PyPI oraz wdrożyłem na serwer. Etap 11 (obsługa karty jak w aplikacji
SuperMemo: samoocena, tłumaczenie zdania na żądanie, termin powtórki przy
wyniku, wyłączenie słowa i notatka do słowa) zaakceptowałeś i zrealizowałem
16.11.2026, a za Twoją zgodą wydałem go jako `v1.0.0-rc.9` na GitHubie
i w PyPI oraz wdrożyłem na serwer. Na Twoją propozycję samoocena
i tłumaczenie na żądanie są od tego samego dnia wartościami domyślnymi,
wydanymi za Twoją zgodą jako `v1.0.0-rc.10` i wdrożonymi na serwer.
Silnik, program `vocabbot` z nową sesją w terminalu, kursy A1–B2 dla czterech
języków (23 095 haseł) oraz wtyczka z czterema umiejętnościami dla Claude'a
i Codexa działają; wyniki etapów opisuje rozdział 10. Wydanie `v1.0.0-rc.3`
jest opublikowane na GitHubie i w PyPI (15.11.2026), a testy sesyjne
z modelem przechodzą 7 z 7. Etap 5 (harmonogram dopasowany do uczącego się)
zakończył się wydaniem `v1.0.0-rc.4` na GitHubie i w PyPI (15.11.2026).
Etap 6 (serwer dla aplikacji czatu) zakończył się wydaniem `v1.0.0-rc.5` na
GitHubie i w PyPI (15.11.2026), a serwer działa pod `https://vocab.archxs.com`.
Etapy 12 i 13 (konto jako wspólny rekord nauki na wszystkich urządzeniach
oraz sesja w przeglądarce telefonu) zaakceptowałeś 18.11.2026 i tego samego
dnia zrealizowałem je razem jako wersję `1.0.0-rc.11`, za Twoją zgodą
wydaną na GitHubie i w PyPI oraz wdrożoną na serwer. Do wersji 1.0 pozostaje
pilotaż według
`docs/pilot.pl.md`. Wersję angielską planu zawiera `development-plan.md`.

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
8. Uczący się kontynuuje naukę na innym urządzeniu bez ręcznych kroków:
   folder połączony z kontem synchronizuje się sam, a sesja działa
   w przeglądarce telefonu bez aplikacji czatu (Etapy 12 i 13, warunek
   dodany 18.11.2026).

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
4. Lista dnia jest funkcją dziennika sprzed danego dnia, planu, kursu
   i rejestru dnia, dlatego przerwana sesja wznawia się w tym samym porządku
   w terminalu i w czacie.
5. Dzień wolny z `days_off` ma pustą kolejkę i zaległe powtórki przechodzą
   na najbliższy dzień nauki.
6. Uczący się wybiera etap (powtórki, nowe słowa, utrwalanie) w dowolnej
   chwili: sesja podaje najpierw karty wybranego etapu, a pozostałe karty
   zachowują kolejność silnika (Etap 10).
7. Uczący się dopisuje do dnia kolejne nowe słowa i kolejne powtórki.
   Dodatkowe słowa dochodzą po jednym w stałej kolejności języków według
   wag. Dodatkowe powtórki obejmują najpierw zaległe karty spoza listy dnia,
   potem karty o najbliższych terminach jako powtórki przed terminem.
   Liczby dopisanych kart przechowuje `registers/day.json` (Etap 10).
8. Nowe słowo przychodzi od razu jako pytanie (`new_words: ask`) albo po
   prezentacji (`new_words: show`). Powtórki dnia idą w kolejności z planu
   (`review_order`). Utrwalanie ma dwie oceny (Etap 10).

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
| `vocabbot note --card ID --stdin`, `vocabbot flag --card ID --skip` | notatka do słowa pokazywana przy jego odpowiedzi; słowo odłożone bez zgłoszenia błędu, przywracane przez `flag --clear` (Etap 11) |
| `vocabbot today --extra N`, `vocabbot today --reviews N` | kolejne nowe słowa i kolejna tura powtórek na dziś; z `--next` wynik zawiera następne karty (Etap 10) |
| `vocabbot drill` | sesja interaktywna w terminalu |
| `vocabbot next --count 10 --json` | kolejne karty bez odpowiedzi; nowe słowa z pełną treścią do pokazania; `--stage reviews\|new\|drill` podaje najpierw karty wybranego etapu (Etap 10) |
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
tego interfejsu programistycznego. Wgrałeś go 15.11.2026.

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
| wydanie | tag `v1.0.0-rc.3`, wydanie przedpremierowe na GitHubie z kompletem paczek; `vocabbot 1.0.0rc3` w PyPI przez zaufane publikowanie (przepływ `release.yml` uruchomiony dla tagu, bez tokenu), sumy plików zgodne z wydaniem na GitHubie; pakiet bez zależności; wtyczka w Twoim Codexie odświeżona do rc.3 |
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

#### Wynik Etapu 5 (15.11.2026, wersja 1.0.0-rc.4)

Etap 5 dał silnikowi narzędzie porównania z FSRS-6, pełne dopasowanie
parametrów i plan według obecności. Wszystkie trzy części działają na
bibliotece standardowej i wynikają z dziennika, więc oba komputery liczą ten
sam plan.

| Kryterium | Wynik |
|---|---|
| `vocabbot replay` | przewiduje każdą powtórkę przed jej wynikiem; dla FSRS-6 z parametrami domyślnymi daje te same wartości co moduł `fsrs`; podaje log loss, RMSE(bins) z przedziałami fsrs-optimizer i AUC każdego wariantu oraz różnicę względem FSRS-6, całość i dla każdego języka; symuluje cztery tygodnie każdego harmonogramu z dniami bez nauki według profilu obecności |
| pełne dopasowanie (`optimize.py`) | przebieg zgodny z modułem `fsrs` do 1e-12, pochodne zgodne z różnicami skończonymi; 2272 powtórki w 0,6–2 s; na sześciu syntetycznych uczących się strata na danych testowych spadła średnio z 0,3582 (FSRS-6) do 0,3548, przy 0,3529 dla parametrów generatora |
| odtworzenie parametrów generatora | jakość przewidywania zbliża się do generatora, natomiast pojedyncze parametry, na przykład stabilność po ocenie „znałem”, nie dają się odczytać z kilku tysięcy powtórek; u uczącego się różniącego się od FSRS-6 tylko początkowymi stabilnościami dopasowanie przewidziało część testową gorzej niż wartości domyślne |
| bramka `plan fit` | język dostaje własne parametry tylko wtedy, gdy na późniejszej części dziennika przewidują lepiej niż FSRS-6; w przeciwnym razie podgląd kończy się komunikatem i plan zostaje bez zmian |
| plan według obecności | na syntetycznym uczącym się, który pomija weekendy (56 dni, 901 powtórek), udział spóźnionych powtórek spadł w symulacji z 34% do 19%, średnie spóźnienie z 0,43 do 0,24 dnia, a przewidywana trwałość pozostała 0,89 przy celu 0,90 |
| tempo nowych słów i powtórki przed przerwą | `today` i sesja w czacie podają mniejszą liczbę nowych słów, gdy dzień przekroczyłby zwykłe minuty o ponad jedną czwartą, oraz proponują powtórki przed dniem wolnym albo zwykle pomijanym |
| testy | 14 nowych testów w `tests/test_schedule.py`; razem 204 na Pythonie 3.15 i 187 na 3.10 (1 pominięty bez grupy `data`); kontrole wtyczki bez uwag |
| wydanie | za Twoją zgodą z 15.11.2026: tag `v1.0.0-rc.4`, wydanie przedpremierowe na GitHubie z kompletem paczek, `vocabbot 1.0.0rc4` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone, wtyczka w Twoim Codexie odświeżona do rc.4 |

Wnioski:

1. Na dzienniku jednego uczącego się po kilku tygodniach pełne dopasowanie
   nie musi przewidywać lepiej niż FSRS-6, dlatego bramka porównania na
   późniejszej części dziennika jest warunkiem jego użycia, a nie dodatkiem.
2. Plan według obecności zmniejsza zaległości bez kosztu dla trwałości, bo
   przesuwa terminy wyłącznie w granicach rozrzutu FSRS.
3. Wyniki na dzienniku pilotażu rozstrzygną, czy pełne dopasowanie trafi do
   planu którejkolwiek z Twoich nauk; `vocabbot replay` pokaże to po dwóch
   tygodniach.

### Etap 6. Serwer dla aplikacji czatu

Etap 6 dodałeś 15.11.2026 po analizie serwisu z oknem czatu i subskrypcją.
Zamiast własnego okna czatu VocabBot działa jako zdalny serwer MCP z kontami:
Claude w przeglądarce, w aplikacji desktopowej i w telefonie, ChatGPT,
Claude Code oraz Codex łączą się z nim jak z każdym łącznikiem, a model
aplikacji czatu prowadzi rozmowę w ramach subskrypcji uczącego się. Serwer
mierzy zainteresowanie bez kosztów modeli po Twojej stronie i działa na
Twoim VPS w Hetznerze.

| Zagadnienie | Stan na 15.11.2026 | Źródło |
|---|---|---|
| SDK MCP dla Pythona | wersja 2.3.0 (02.10.2026): `MCPServer`, transport Streamable HTTP, serwer autoryzacji z dynamiczną rejestracją klientów, PKCE i tokenami odświeżania | PyPI, kod pakietu |
| Łączniki w Claude | własne łączniki zdalnych serwerów MCP działają w każdym planie (plan bezpłatny: jeden łącznik); adres zwrotny `https://claude.ai/api/mcp/auth_callback`, w przyszłości również `claude.com` | centrum pomocy Anthropic |
| Aplikacje w ChatGPT | serwer MCP przez Streamable HTTP z OAuth 2.1, metadanymi zasobu i wskaźnikiem `resource`; stały adres zwrotny przy obsłudze RFC 9207; narzędzia zapisujące w trybie dewelopera według centrum pomocy w planach Business, Enterprise i Edu | dokumentacja Apps SDK, centrum pomocy OpenAI |

Zakres:

1. Pakiet `vocabbot.server` z programem `vocabbot-server` w dodatku
   `vocabbot[server]`; silnik i `vocabbot.pyz` pozostają na bibliotece
   standardowej.
2. Konta z kodami zaproszeń, hasła w scrypt, rekordy OAuth w SQLite jako
   skróty SHA-256, strona logowania i zakładania konta po polsku.
3. Serwer autoryzacji OAuth 2.1 z SDK MCP: dynamiczna rejestracja klientów
   z listą dozwolonych adresów zwrotnych, PKCE, token dostępu na godzinę,
   token odświeżania wymieniany przy każdym użyciu, wskaźnik zasobu i
   wystawca w odpowiedzi logowania.
4. Narzędzia MCP, które uruchamiają polecenia programu na folderze konta
   i zwracają ten sam JSON co wtyczka, oraz przewodniki dla modelu zgodne
   z umiejętnościami wtyczki.
5. Silnik dla wielu kont w jednym procesie: wspólny katalog kursów, podgląd
   nowego planu w folderze konta bez wskaźnika, dzień nauki w strefie
   czasowej serwera.
6. Uruchomienie w Dockerze za Caddy z certyfikatem TLS oraz dokument
   `docs/server.pl.md`.

Kryteria akceptacji:

- Klient OAuth z SDK MCP, działający jak aplikacja czatu, rejestruje się,
  loguje przez stronę serwera i korzysta z narzędzi; dwa konta pracują
  rozdzielnie i żadna odpowiedź nie zdradza ścieżek serwera.
- Gwarancje silnika obowiązują przez serwer: pytanie bez odpowiedzi, ocena
  silnika, zmiana tylko przez podgląd i token, tekst uczącego się poza
  opcjami polecenia.
- Obraz Dockera przechodzi całą ścieżkę na prawdziwych kursach, również
  za Caddy z TLS.
- Testy wszystkich modułów przechodzą na Pythonie 3.10 i 3.15.

#### Wynik Etapu 6 (15.11.2026, wersja 1.0.0-rc.5)

Etap 6 dał VocabBotowi serwer z kontami dla aplikacji czatu. Serwer korzysta
z tych samych poleceń silnika co program i wtyczka, więc sesja w Claude na
telefonie przebiega według tych samych reguł co sesja w Claude Code.

| Kryterium | Wynik |
|---|---|
| OAuth 2.1 | klient referencyjny SDK MCP przechodzi wykrywanie zasobu, rejestrację, logowanie na stronie serwera, wymianę kodu z PKCE i sprawdzenie wystawcy (RFC 9207); token odświeżania działa jeden raz, a po odświeżeniu poprzedni token dostępu wygasa |
| zabezpieczenia logowania | adresy zwrotne wyłącznie do Claude, ChatGPT i komputera uczącego się; limit nieudanych prób na login i na adres; kod autoryzacji jednorazowy; nowe hasło kończy połączenia konta |
| narzędzia | 22 narzędzia z adnotacjami odczytu i zapisu; wartości przekazane jako opcje polecenia kończą się błędem `bad_arguments`, a ustawienia planu muszą mieć postać KLUCZ=WARTOŚĆ |
| rozdzielność kont | drugie konto nie widzi planu pierwszego i nie zatwierdzi jego podglądu; odpowiedzi podają ścieżki względem folderu konta |
| silnik dla wielu kont | katalog kursów wczytuje się raz (0,33 s i 70 MB), a każde konto dostaje jego kopię z własnymi słowami bez ponownego wczytania |
| obraz Dockera | na prawdziwych kursach wszystkie 22 narzędzia działają z czasem odpowiedzi od 11 do 87 ms; ta sama ścieżka przechodzi za Caddy z TLS z poprawnymi adresami w metadanych i w nagłówku `WWW-Authenticate` |
| zgodność z klientami | Claude Code łączy się z serwerem z tokenem i bez tokenu rozpoznaje logowanie OAuth; połączenia z claude.ai i ChatGPT wymagają adresu publicznego, czyli wdrożenia na VPS |
| testy | 14 nowych testów w `tests/test_server.py` i test paczki sesji; razem 219 na Pythonie 3.15 i 202 na 3.10 (1 pominięty bez grupy `data`); kontrole repozytorium bez uwag |
| wdrożenie | za Twoją zgodą z 15.11.2026 serwer działa pod `https://vocab.archxs.com` na Twoim VPS w Hetznerze jako kolejna strona wspólnego Caddy, z certyfikatem Let's Encrypt, limitem 384 MB (zajmuje 132 MB) i codzienną kopią zapasową o 4:00; pozostałe strony serwera działają bez przerwy; `scripts/deploy_vps.sh` powtarza wdrożenie |
| test na produkcji | wszystkie 22 narzędzia przez klienta OAuth z SDK MCP na prawdziwych kursach; metadane, nagłówek `WWW-Authenticate` i odmowa obcego adresu zwrotnego zgodne z testami lokalnymi |
| test z modelem | Claude Code z Claude Sonnet 5.5, połączony wyłącznie z serwerem, przeszedł 8 tur za 1,54 USD: konfigurację z podglądem i zapisem dopiero po „tak”, sesję z przedstawieniem nowych słów, pytania bez odpowiedzi, ocenę odpowiedzi przekazanych bez zmian (pusta za „?”), utrwalanie i podsumowanie; dziennik konta na serwerze zgadza się z rozmową |
| wydanie | za Twoją zgodą z 15.11.2026: tag `v1.0.0-rc.5`, wydanie przedpremierowe na GitHubie z kompletem paczek, `vocabbot 1.0.0rc5` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem (z dodatkiem `server`), CI zielone, wtyczka w Twoim Codexie odświeżona do rc.5 |
| poprawka silnika | test z modelem pokazał zdanie z odpowiedzią innej karty tej samej paczki („„___, danke.”” obok pytania o „danke”); paczka sesji ukrywa teraz takie zdania tak samo jak test poziomujący |

Wnioski:

1. Serwer MCP z kontami daje okno czatu w Claude i ChatGPT, także na
   telefonie, bez kosztów modeli po stronie serwera, więc nadaje się do
   sprawdzenia zainteresowania przed decyzją o własnym serwisie.
2. W ChatGPT narzędzia zapisujące zależą od planu konta; próba w planie
   Plus albo Pro pokaże, czy odpowiedzi z sesji trafiają do dziennika.
3. Połączenie z claude.ai i ChatGPT z Twojego konta zamyka sprawdzenie
   serwera; potem serwer może przyjąć pierwszych uczących się z
   zaproszeniami.

### Etap 7. Język włoski i sesja po jednej karcie

Etap 7 dodałeś 15.11.2026 dwiema prośbami: język włoski jako piąty język
kursów oraz sesję w czacie, która jak SuperMemo pokazuje jedną kartę naraz,
z liczbą kart w wiadomości ustawianą w planie. Przegląd modelem zatwierdziłeś
z limitem 7 USD.

Zakres:

1. Ustawienie planu `batch` (od 1 do 20, domyślnie 1): przy 1 wiadomość
   zawiera wynik ostatniej odpowiedzi i następną kartę, a nowe słowo pojawia
   się samo przed swoim pytaniem; `answer --next` zwraca od razu następne
   karty.
2. Włoskie źródła: hasła i tłumaczenia z Wikisłownika oraz zdania Tatoeby
   z linkami, w których włoski jest pierwszy, tak aby ścieżki tłumaczeń
   pozostałych kursów zostały bez zmian.
3. Reguły odpowiedzi: `lo` obok `il`, elizja `l'` i `un'`, liczba mnoga `i`,
   `gli`, `le`, czasowniki zwrotne na `-si`.
4. Reguły kursu: rodzajnik według pierwszego dźwięku, liczba mnoga, miesiące
   bez rodzajnika, pisownia form bez akcentu pomocniczego Wikisłownika.
5. Przegląd dodanego języka (`review_lang.py`): model wybiera włoski
   odpowiednik sensu, który kurs już ma, widząc polskie znaczenie i słowa
   kursów niemieckiego, hiszpańskiego i francuskiego.

#### Wynik Etapu 7 (15.11.2026)

| Kryterium | Wynik |
|---|---|
| sesja po jednej karcie | `next` bez `--count` zwraca `batch` kart, `today` podaje `batch`, `answer --next` i `then_next` w serwerze oszczędzają jedno wywołanie na kartę; umiejętność, przewodnik serwera i klucz planu opisują oba tryby; wdrożone na serwerze 15.11.2026 |
| kurs włoski | 5576 haseł (A1 1003, A2 1134, B1 1681, B2 1758), kursy w wersji 2026.11.5, kontrola kursów bez uwag |
| przegląd znaczeń | 6705 decyzji za 2,28 USD (Claude Sonnet 5.5, Message Batches); 27 pojęć bez jednego włoskiego słowa |
| przegląd przykładów | 3264 hasła za 1,26 USD; zdanie ma 89% haseł A1, 68% A2, 50% B1 i 29% B2 |
| próba jakości | 40 losowych haseł: znaczenia, odpowiedniki, rodzajniki i rodzaj poprawne; próba wykazała akcent pomocniczy w 887 imiesłowach (organizzàto), który budowa teraz usuwa; dwie z 40 list dodatkowych odpowiedzi są zbyt szerokie (il calore przy il bagliore) |
| pozostałe kursy | angielski bez zmian; w niemieckim, hiszpańskim i francuskim 7 haseł ma nowe lub inne zdanie przykładowe dzięki włoskim tłumaczeniom w Tatoebie |
| koszt | 3,54 USD z limitu 7 USD |
| wydanie | za Twoją zgodą z 15.11.2026: tag `v1.0.0-rc.6`, wydanie przedpremierowe na GitHubie z kompletem paczek, `vocabbot 1.0.0rc6` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone, wtyczka w Twoim Codexie odświeżona do rc.6 |

Wnioski:

1. Kolejny język kursów wymaga przede wszystkim decyzji przeglądu dla
   każdego pojęcia; reguły rodzajników i pisowni są krótkie, a przegląd
   jednego języka kosztuje około 3,5 USD.
2. Pokrycie przykładami na B1–B2 jest dla włoskiego niższe niż dla
   pozostałych języków, bo Tatoeba ma niewiele bezpośrednich tłumaczeń
   włosko-polskich.

### Etap 8. Uwagi z pilotażu: wymowa, przykłady, licznik i ChatGPT

Etap 8 dodałeś 16.11.2026 po uwagach pierwszej osoby z pilotażu, która uczy
się angielskiego w ChatGPT. Stan: zrealizowany 16.11.2026, wynik poniżej.

#### Weryfikacja uwag (16.11.2026)

| Uwaga | Stan faktyczny | Zmiana |
|---|---|---|
| podłączenie w ChatGPT wygląda inaczej niż w instrukcji | centrum pomocy OpenAI opisuje dodanie serwera we Wtyczkach (przycisk plus, własny serwer MCP) bez trybu dewelopera; dziennik konta na serwerze potwierdza zapis planu i 18 odpowiedzi z ChatGPT | punkt 1 |
| brak odsłuchu słowa | kursy nie zawierają nagrań; aplikacja czatu pokazuje tekst i odnośniki | punkt 3 |
| brak czytania słowa | zapis IPA ma od 74% do 98% haseł zależnie od języka i poziomu; `vocab_next` zwraca go przy nowym słowie i przewodnik każe go pokazać, wynik odpowiedzi go nie powtarza; uwaga może dotyczyć zapisu wymowy albo czytania na głos, co rozstrzyga pytanie do pilotażysty | punkt 3 |
| nie każde nowe słowo ma przykład | 10 738 z 28 671 haseł nie ma zdania: od 7% do 11% haseł A1 i od 45% do 71% haseł B2; wśród 18 kart pilotażysty bez zdania było 6 (for, all, one, over, take, IT); zdania pochodzą wyłącznie z Tatoeby i reguły zabraniają modelowi czatu dopisywania danych kursu | punkt 4 |
| licznik przerobionych słów | `vocab_today` podaje wykonane powtórki i nowe słowa każdego języka; `vocab_answer` i `vocab_next` podają tylko pozostałe karty i przewodnik nie każe pokazywać licznika; sesja w terminalu ma licznik z paskiem postępu | punkt 2 |

Dziennik pokazuje też 14 odpowiedzi „znałem” wśród 15 pierwszych nowych słów
A2, po których pilotażysta zmienił poziomy na B1–B2 (punkt 5).

Zakres:

1. **ChatGPT.** Ścieżka Ustawienia, Integracje, Wtyczki, przycisk plus
   i własny serwer MCP z uwierzytelnianiem OAuth w `docs/server.md`,
   `docs/server.pl.md`, na stronie głównej serwera (`server.home_chatgpt`)
   i w zaproszeniu dla pilotażu. Wiersz ryzyka o odczycie w ChatGPT podaje
   wynik z 16.11.2026.
2. **Licznik.** Wyniki `answer`, `grade`, `regrade` i `next` podają obok
   `left` także `done`, czyli powtórki, nowe słowa i utrwalanie wykonane
   danego dnia. Przewodnik serwera i umiejętność `vocab-session` zaczynają
   każdą wiadomość sesji linią licznika, na przykład „7 z 25 · nowe 3/15 ·
   powtórki 4/10”. `today` podaje nowe słowa dnia, więc podsumowanie na
   koniec sesji zawiera ich liczbę i listę.
3. **Wymowa.** Potok zapisuje w haśle nazwę pliku nagrania z Wikimedia
   Commons. Nagrania angielskie, niemieckie i francuskie pochodzą
   z Wikisłownika (dla angielskiego najpierw brytyjskie, zgodnie z IPA
   kursu). Nagrania hiszpańskie i włoskie pochodzą z Lingua Libre, bo
   wyciąg Wikisłownika pomija nagrania z szablonów wymowy tych języków.
   `presentation` zwraca adres pliku MP3 liczony z nazwy według schematu
   Commons, więc pakiet zawiera wyłącznie nazwy plików. Przewodnik
   i umiejętność pokazują przy nowym słowie oraz w wyniku „prawie” i „nie
   wiem” zapis IPA i odnośnik „🔊 wymowa”. `NOTICE` i README podają źródło
   i licencje nagrań. Pokrycie według pomiaru z 16.11.2026: angielski
   98–100%, niemiecki 95–98%, francuski 87–95%, hiszpański 63–91%,
   włoski 27–81%.
4. **Przykłady.** Krok potoku `tools/courses/generate.py
   prepare|submit|collect` (Message Batches API, Claude Sonnet 5.5) pisze
   dla każdego hasła bez zdania z Tatoeby jedno krótkie zdanie na poziomie
   hasła, w znaczeniu kursu, z polskim tłumaczeniem. Przegląd przykładów
   (`examples.py`) ocenia je tak samo jak zdania z Tatoeby. Decyzje trafiają
   do `generated.jsonl` w repozytorium, więc budowa powtarza się bez API.
   Zdanie ma w haśle źródło `generated`. Najpierw próbka 200 haseł i ocena
   40 losowych, potem pełny przebieg po Twojej zgodzie z wyceną z próbki.
   Cel: zdanie w co najmniej 95% haseł każdego poziomu.
5. **Za niski poziom.** Gdy w jednym języku co najmniej 8 z 10 ostatnich
   nowych słów dostaje „znałem”, wynik `grade` zawiera `level_hint`.
   Przewodnik proponuje wtedy test poziomujący albo wyższy poziom przez
   podgląd zmiany planu.
6. **Sprawdzenie i wydanie.** Testy silnika dla `done`, `level_hint`
   i adresu nagrania, test potoku dla nazw nagrań, `session_test.py
   --check`, testy serwera, ręczna próba odnośnika do nagrania w Claude
   i ChatGPT w przeglądarce i na telefonie. Wydanie `v1.0.0-rc.7`
   i wdrożenie na serwer, każde za osobną zgodą.

#### Wynik Etapu 8 (16.11.2026)

Etapy 8 i 9 zaakceptowałeś 16.11.2026 jednym poleceniem z prośbą o
potwierdzenie działania, symulacje i przegląd kodu. Pełny przebieg zdań
z modelem zatwierdziłeś z limitem 12 USD po wycenie z próbki.

| Kryterium | Wynik |
|---|---|
| ChatGPT | ścieżka Ustawienia, Integracje, Wtyczki i własny serwer MCP w `docs/server.md`, `docs/server.pl.md`, na stronie głównej serwera i w zaproszeniu dla pilotażu |
| licznik | `done` i `counter` w wynikach `next`, `answer`, `grade`, `regrade` i `today`, lista `learned_today` w `today`; przewodnik serwera i umiejętność `vocab-session` zaczynają każdą wiadomość licznikiem i kończą sesję listą nowych słów dnia |
| wymowa | 23 368 haseł (81,5%) z nagraniem w Wikimedia Commons: angielski 98–99%, niemiecki 92–95%, francuski 86–94%, hiszpański 63–91%, włoski 27–79% według poziomu; czasownik zwrotny i słowo o dwóch wymowach nie dostają nagrania innej formy; nagrania z Wikisłownika, dla hiszpańskiego i włoskiego z list Lingua Libre (`audio.py`); IPA i nagranie z innej części mowy tego samego słowa o jednej wymowie dały IPA 196 kolejnym hasłom (razem 91,4% haseł) |
| przykłady | 10 738 haseł bez zdania z Tatoeby; model napisał zdanie dla każdego, przegląd przykładów przyjął 10 380 zdań w pierwszym przebiegu i 222 z 358 po jednej poprawce; razem 10 602 zdania (`generated.jsonl`) i przykład w 99,5% haseł, na każdym poziomie co najmniej 99% |
| próba jakości | w 40 losowych zdaniach próbki 38 poprawnych, w dwóch błąd czasu w tłumaczeniu (regañar) i znaczenie w złożeniu (sex education); przegląd odrzucił 356 zdań pierwszego przebiegu, najczęściej jako nienaturalne (137), z błędem tłumaczenia (76), znaczenia (46) albo części mowy (43) |
| za niski poziom | `level_hint` w wyniku `grade` albo `answer`, gdy 8 z 10 ostatnich nowych słów na bieżących poziomach było znanych, z ustawieniem planu do zmiany, najwyżej raz dziennie dla tych samych poziomów; w terminalu jeden wiersz podpowiedzi |
| poprawka silnika | zmiana poziomów w trakcie dnia nie dokłada już nowych słów ponad dzienny limit; błąd wykryła symulacja z modelem (licznik 10/35 zamiast 10/25 po dziesięciu „znałem” i zmianie poziomów) |
| kursy | wersja 2026.11.6; względem wersji 2026.11.5 wyłącznie dopisane pola: nagranie w 23 368 hasłach, przykład w 10 602, IPA w 196; żadne istniejące zdanie ani IPA się nie zmieniło; kontrola kursów bez uwag |
| symulacja bez modelu | dwoje uczących się przez 10 dni (angielski od A2 z 12 słowami „znałem” pierwszego dnia i zmianą na B1–B2; włoski, hiszpański i niemiecki od A1): 2496 sprawdzeń licznika, 804 odpowiedzi, 550 nowych słów (548 ze zdaniem, 537 z nagraniem, 531 z IPA), jedna podpowiedź poziomu, każdy dzień zakończony bez zaległych kart, zero naruszeń; nagrania wszystkich pięciu języków odpowiadają z Commons jako `audio/mpeg` |
| symulacja z modelem | 9 tur Claude Code (model Sonnet) przez lokalny serwer z kontem syntetycznym, 1,84 USD: licznik w każdej wiadomości, nowe słowo z IPA i odnośnikiem do nagrania, podpowiedź poziomu raz, zmiana poziomów przez podgląd i „tak”, podsumowanie z listą słów dnia; w wyniku „nie wiem” model pominął odnośnik do nagrania, więc przykłady wyników w przewodniku i umiejętności pokazują go wprost; druga sesja po poprawkach z przeglądu kodu (6 tur, 1,02 USD) potwierdziła licznik 10/25 po zmianie poziomów, jedną podpowiedź poziomu bez przerwy w sesji i odnośnik do nagrania w wyniku „nie wiem” |
| przegląd kodu | 15 potwierdzonych usterek, wszystkie poprawione: ponowny wybór nowych słów na zużytych generatorach i przestawianie przydziału między językami (zastąpione z góry policzonymi miejscami słów spoza planu w ich języku), lista słów dnia z odpowiedziami kart czekających w utrwalaniu, podpowiedź poziomu powtarzana lub nieobecna po wpisanej odpowiedzi (teraz najwyżej raz dziennie dla bieżących poziomów), licznik bez powtórek przed terminem, zgłoszona karta w utrwalaniu, odtwarzanie poprzedniego słowa przez syntezę w karcie, głos innej odmiany języka, powtórne zebranie partii i zdania przypisane do zmienionego hasła, ucięta lista Lingua Libre przy błędzie API, nagranie czasownika bez zaimka zwrotnego, kopia reguł w przewodniku serwera, zbędne przeliczenia dnia w terminalu; po poprawkach 139 haseł straciło błędne nagranie |
| testy | 248 na Pythonie 3.15 i 220 na Pythonie 3.10 (1 pominięty bez wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 z 7), `claude plugin validate --strict` i kontrola kursów bez uwag |
| wydanie | za Twoją zgodą z 16.11.2026: tag `v1.0.0-rc.7`, wydanie przedpremierowe na GitHubie z kompletem paczek, `vocabbot 1.0.0rc7` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone, wtyczka w Twoim Codexie odświeżona do rc.7 |
| koszt | 8,32 USD za zdania (próbka 0,09, generowanie 4,82, przegląd 3,14, poprawka 0,27) z limitu 12 USD oraz 2,86 USD za dwie symulacje z modelem |

Wnioski:

1. Zdania z modelu z przeglądem uzupełniają kurs tanio: luka 37% haseł
   kosztowała 8,32 USD, a przegląd przyjął 98,7% zdań.
2. Wikisłownik daje nagrania dla angielskiego, niemieckiego i francuskiego;
   dla hiszpańskiego i włoskiego pomaga Lingua Libre, a słowa bez nagrania
   obsługuje synteza mowy w karcie z Etapu 9.
3. Symulacja z prawdziwym modelem wykryła błąd silnika, którego nie
   pokazały testy jednostkowe, więc warto ją powtarzać przed wydaniem.

### Etap 9 (warunkowy). Karta w oknie czatu

MCP Apps pozwalają narzędziu pokazać w rozmowie interaktywną kartę w osobnej
ramce. Według ogłoszenia z 26.01.2026 obsługują je Claude w przeglądarce
i w aplikacji desktopowej oraz ChatGPT; ogłoszenie nie wspomina aplikacji na
telefon ani odtwarzania dźwięku. Karta VocabBota pokazywałaby licznik, słowo,
zapis IPA i przycisk odtwarzania nagrania. Słowa i zdania bez nagrania
odczytywałaby synteza mowy przeglądarki. Etap zaczyna się od próby: obsługa
rozszerzenia w MCP Python SDK, zasady CSP dla plików z
`upload.wikimedia.org` oraz odtwarzanie w Claude i ChatGPT na komputerze i na
telefonie. Etap zrealizowałem 16.11.2026 razem z Etapem 8 na Twoje
polecenie, wynik poniżej.

#### Wynik Etapu 9 (16.11.2026)

| Kryterium | Wynik |
|---|---|
| SDK | MCP Python SDK 2.3.0 ma rozszerzenie `Apps`; serwer ogłasza `io.modelcontextprotocol/ui`, narzędzia `vocab_today`, `vocab_next`, `vocab_answer` i `vocab_grade` wskazują kartę w `_meta.ui.resourceUri` oraz w `openai/outputTemplate`, a zasób `ui://vocabbot/card.html` ma typ `text/html;profile=mcp-app` |
| karta | `server/static/card.html` bez zależności zewnętrznych: `ui/initialize`, `tool-result`, zgłaszanie rozmiaru, motyw i zmienne gospodarza; etykiety z `pl.json`; obramowanie rysuje gospodarz (`prefersBorder`); pytanie nie pokazuje ani nie odtwarza słowa |
| dźwięk | przycisk odtwarza MP3 z `upload.wikimedia.org`, jedynej domeny w CSP karty; słowa i zdania bez nagrania odczytuje synteza mowy przeglądarki, oznaczona przerywaną obwódką przycisku |
| próba | host testowy w Edge z prawdziwymi wynikami narzędzi: karta przechodzi handshake i pokazuje nowe słowo, wynik z utrwalaniem i podsumowanie dnia w motywie jasnym i ciemnym, bez błędów JavaScriptu; test serwera sprawdza metadane narzędzi, zasób i CSP |
| wdrożenie | serwer 1.0.0rc7 pod `https://vocab.archxs.com` od 16.11.2026; test dymny z krótko ważnym tokenem konta testowego, unieważnionym po teście: 22 narzędzia, karta w czterech narzędziach, zasób karty z CSP i etykietami, licznik w `vocab_today`, nagranie i przykład w `vocab_lookup` |
| do sprawdzenia | wyświetlanie karty w Claude i ChatGPT na komputerze i na telefonie z Twojego konta |

### Etap 10. Etapy sesji jak w SuperMemo: wybór etapu, kolejne słowa i kolejne tury powtórek

Etap 10 dodałeś 16.11.2026 po porównaniu sesji VocabBota z aplikacją
SuperMemo (dwa zrzuty ekranu kursu niemieckiego). Stan: zrealizowany,
wydany jako `v1.0.0-rc.8` i wdrożony 16.11.2026, wynik poniżej.

#### Mechanika SuperMemo (stan na 16.11.2026)

| Mechanizm | SuperMemo | Źródło |
|---|---|---|
| trzy etapy dnia | pasek aplikacji ma trzy liczniki: powtórki, nowy materiał i utrwalenia; kurs otwiera się na powtórkach, potem na nowym materiale, potem na utrwaleniach | FAQ „Powtórki i utrwalenia”, wpis „How to start learning with a course” |
| przejście między etapami | uczący się zmienia tryb w dowolnej chwili (w przeglądarce klawiszem Tab) | FAQ o skrótach klawiszowych |
| nowy materiał | liczba kart dziennie w planie kursu (5, 10, 20, 30 albo własna) jest punktem startu i po jej wykonaniu kurs podaje kolejne strony | wpis „Customize your learning with SuperMemo”, obserwacja aplikacji |
| powtórki | powtórki niewykonane danego dnia przechodzą na kolejne dni, nowy odstęp wynika z rzeczywistego czasu od poprzedniej powtórki, kalendarz ma dzienny limit powtórek i dni wyłączone | FAQ „Repetition limit”, wpis „Sort your repetitions” |
| powtórka przed terminem | SuperMemo dla Windows wykonuje powtórkę w środku odstępu z korektą algorytmu; pomoc aplikacji kursowej takiej funkcji nie opisuje | pomoc SuperMemo, hasło „Mid-interval repetition” |
| utrwalanie | karta z oceną „nie wiem” albo „prawie” wraca tego samego dnia aż do skutku, w stałej kolejności; oceny z utrwalania w SuperMemo dla Windows zachowują odstępy | FAQ „Powtórki i utrwalenia”, pomoc SuperMemo, hasło „Final drill” |
| oceny | „wiem” wydłuża odstęp, „prawie” wydłuża odstęp i kieruje kartę do utrwalania, „nie wiem” skraca odstęp | wpis „Repeat section and 3 buttons assessment” |
| pierwszy kontakt | pierwszy kontakt ze słowem liczy się jako nauka, a następne jako powtórki | wpis „How to learn with SuperMemo” |

#### Zakres i wynik Etapu 10 (16.11.2026)

| Twoja uwaga | Realizacja |
|---|---|
| 1. wybór między nowymi słowami a powtórkami | `next --stage reviews\|new\|drill` (na serwerze `vocab_next` z parametrem `stage`) podaje najpierw karty wybranego etapu; wynik nazywa etap (`stage`), etap bez kart (`stage_empty`) i liczbę kart pozostałych w trzech etapach (`left`); bez wyboru obowiązuje kolejność silnika: powtórki, nowe słowa, utrwalanie |
| 2. dzienna liczba nowych słów jako punkt startu | `today --extra N --next` (`vocab_add_today` z `count`) dopisuje słowa ponad liczbę z planu dowolną liczbę razy, do 100 dziennie; `more.new` podaje liczbę słów dostępnych na poziomach planu, a sesja proponuje kolejne słowa po liście dnia |
| 3. pominięcie powtórek | przejście do etapu `new` zostawia powtórki nietknięte: karta z ekranu czeka w swoim etapie, a powtórki niewykonane danego dnia zachowują termin i otwierają następny dzień |
| 4. przejście do nowych słów w trakcie powtórek | odpowiedź z `--next` (`then_next`) podaje kolejną kartę tego etapu, do którego należała karta z odpowiedzią, więc wybrany etap trwa bez dodatkowych parametrów; po ostatniej karcie etapu sesja przechodzi do następnego w kolejności silnika |
| 4. nowy cykl powtórek po wykonaniu wszystkich | `today --reviews N --next` (`vocab_add_today` z `reviews`) dopisuje następną turę: najpierw zaległe powtórki spoza listy dnia (ponad `review_limit` albo z dnia wolnego), potem karty o najbliższych terminach jako powtórki przed terminem; silnik liczy następny termin z rzeczywistego odstępu (FSRS), wiersz dziennika ma znacznik `ahead`, a karta z dzisiejszą odpowiedzią do kolejnej tury już nie wchodzi |
| utrwalanie | bez zmian w zasadzie: karta z oceną „prawie” albo „nie wiem” wraca do odpowiedzi „wiem” i jej termin już się tego dnia nie zmienia; etap `drill` można wybrać wcześniej |
| rejestr dnia | `registers/day.json` przechowuje dodatkowe nowe słowa i dodatkowe powtórki jednego dnia, więc lista dnia pozostaje funkcją dziennika sprzed dnia, planu, kursu i tego pliku, a przerwana sesja wznawia się w tym samym miejscu w terminalu i w czacie |
| terminal | `vocabbot drill` przyjmuje przy odpowiedzi `/nowe`, `/powtorki`, `/utrwalanie` i `/wiecej`, przy nowym słowie klawisz `p`, a po liście dnia proponuje `n` (5 nowych słów), `p` (następna tura 10 powtórek) i Enter (koniec) |
| czat | przewodnik `session` i umiejętność `vocab-session` mają rozdział „The stages and more cards”: start od powtórek z jedną linią o wyborze, hasła „nowe”, „powtórki”, „utrwalanie”, „więcej słów” i „jeszcze powtórki”, jedna linia przy końcu etapu oraz propozycja po liście dnia |
| serwer i karta | `vocab_next` ma `stage`, `vocab_grade` ma `then_next`, `vocab_add_today` ma `count` i `reviews` oraz zwraca `added` i `next`; parametr `ahead` zniknął z narzędzi, bo powtórki przed terminem wchodzą do dnia przez `vocab_add_today`; karta pokazuje trzy etapy z liczbą pozostałych kart i wyróżnia etap w toku |
| usterka znaleziona w symulacji | druga dokładka nowych słów przy trzech językach dawała 28 słów zamiast 25: podział metodą największych reszt przesuwał miejsce między językami i słowo już pokazane zostawało poza wyborem; dodatkowe słowa dochodzą teraz po jednym w stałej kolejności języków według wag, więc większa liczba tylko dopisuje (dotyczy też słowa dokładanego po ocenie „znałem”) |
| tempo dnia | powtórki dopisane przez uczącego się zostawiają bez zmian liczbę nowych słów wyznaczoną z profilu obecności |
| testy | 255 na Pythonie 3.15 i 227 na Pythonie 3.10 (1 pominięty bez wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 z 7) i `claude plugin validate --strict` bez uwag; nowe testy: wybór etapu i etap bez kart, tura powtórek przed terminem, zaległe powtórki ponad limit jako pierwsze, dzień wolny z powtórkami na prośbę, kolejna karta w wybranym etapie przez polecenia, etapy i dokładki w terminalu, dokładki nowych słów przy trzech językach, narzędzia serwera z `stage`, `then_next` i `reviews` |
| symulacja | pełne kursy (de A1–A2, es A1, it A1, 15 nowych słów dziennie) przez polecenia programu: 1206 sprawdzeń bez usterki; licznik sumuje się po każdej odpowiedzi, kolejna karta zostaje w wybranym etapie, dwie dokładki dają 25 nowych słów, cztery tury dają 35 powtórek przed terminem bez powtórzeń, a tura przy wszystkich kartach z dzisiejszą odpowiedzią jest pusta; symulację z modelem opisuje tabela poniżej |

#### Wyrównanie trzech różnic do SuperMemo (16.11.2026, za Twoją zgodą)

| Różnica | Realizacja |
|---|---|
| nowe słowo | ustawienie planu `new_words` z wartością domyślną `ask`: `next` podaje nową kartę jako pytanie bez słowa, wynik pierwszej odpowiedzi pokazuje słowo w całości (formy, IPA, nagranie, znaczenie, przykład), a słowo z odpowiedzią „nie wiem” wraca tego samego dnia w utrwalaniu; poprawna pierwsza odpowiedź dostaje ocenę `known` (słowo znane przed kursem), dodaje do dnia kolejne nowe słowo i liczy się do podpowiedzi poziomu; `new_words=show` zachowuje prezentację słowa przed pytaniem; plany zapisane wcześniej dostają `ask` |
| dwie oceny w utrwalaniu | odpowiedź w utrwalaniu inna niż „wiem” zostawia kartę w utrwalaniu i trafia do dziennika jako `dont_know`; werdykt silnika z klasami błędów zostaje w polu `auto`; terminal proponuje w utrwalaniu klawisze 1 i 3, a zmiana oceny przyjmuje tam `know` albo `dont_know` |
| kolejność powtórek | ustawienie planu `review_order`: `due` (od najbardziej zaległych, wartość domyślna), `course` (kolejność kursu), `interval` (od najkrótszych odstępów), `random` (losowa, stała przez cały dzień); powtórki dopisane w ciągu dnia dochodzą po zaplanowanych |
| prognoza | `forecast` bierze udział poprawnych pierwszych odpowiedzi z dziennika, a przed zebraniem 20 takich odpowiedzi przyjmuje 20% dla planu z pytaniem od razu i 80% dla planu z prezentacją |
| czat, terminal i karta | przewodnik, umiejętność `vocab-session` i reguła o odpowiedzi po ocenie opisują nowe słowo jako pytanie, wynik „✓ znane wcześniej” i dwie oceny utrwalania; terminal pyta o nowe słowo bez wcześniejszej prezentacji i po poprawnej odpowiedzi pokazuje formy i przykład; karta pokazuje nowe słowo w całości przy wyniku pierwszej odpowiedzi |
| testy | 260 na Pythonie 3.15 i 232 na Pythonie 3.10 (1 pominięty bez wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (7 z 7) i `claude plugin validate --strict` bez uwag; nowe testy: nowe słowo jako pytanie i ocena `known`, dwie oceny utrwalania z odmową oceny „prawie”, cztery kolejności powtórek, ustawienia planu przez polecenia, sesja w terminalu z pytaniem od razu |
| symulacja programu | pełne kursy przez polecenia przy planie domyślnym: 1407 sprawdzeń bez usterki w 131 odpowiedziach (55 nowych słów nieznanych, 16 znanych wcześniej, 41 odpowiedzi utrwalania wyłącznie z ocenami `know` i `dont_know`); żadna karta nie podała słowa przed oceną, a cztery kolejności powtórek obejmują te same karty |
| symulacja z modelem | lokalny serwer i Claude Code z modelem Sonnet, 10 tur za 1,79 USD: start od powtórek z linią o wyborze, „nowe” (`vocab_next` ze `stage: new`), nowe słowo jako pytanie, pełna prezentacja po „?”, „✓ znane wcześniej” po poprawnej odpowiedzi, „daj jeszcze 3 słowa” (`vocab_add_today` z `count: 3`), powrót do powtórek, następna tura (`vocab_add_today` z `reviews: 5`, dołączyły 4 dostępne karty) i przejście do utrwalania; każda tura zgodna z przewodnikiem |
| wydanie i wdrożenie | za Twoją zgodą z 16.11.2026: tag `v1.0.0-rc.8`, wydanie przedpremierowe na GitHubie z kompletem 9 paczek, `vocabbot 1.0.0rc8` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone, wtyczka w Twoim Codexie odświeżona do rc.8; serwer 1.0.0rc8 pod `https://vocab.archxs.com`, test dymny z krótko ważnym tokenem konta testowego, unieważnionym po teście: 22 narzędzia, karta w pięciu narzędziach (z `vocab_add_today`), zasób karty z CSP i etykietami, licznik w `vocab_today`, nagranie i przykład w `vocab_lookup` |
| do sprawdzenia | sesja z Twojego konta w Claude i ChatGPT: nowe słowo jako pytanie, hasła „nowe”, „powtórki”, „więcej słów” i „jeszcze powtórki”, karta z trzema etapami; plany kont na serwerze, także konta z pilotażu, mają teraz `new_words=ask` |

### Etap 11. Obsługa karty jak w aplikacji SuperMemo

Etap 11 zaproponowałem 16.11.2026 po Twoim pytaniu o różnice w obsłudze
(bez algorytmów) między VocabBotem a aplikacją SuperMemo. Stan:
zaakceptowany z wartościami domyślnymi `answer_mode=type`
i `sentence_translation=shown`, zrealizowany, wydany jako `v1.0.0-rc.9`
i wdrożony 16.11.2026, wynik poniżej. Zakres obejmuje
wyłącznie różnice potwierdzone: stan VocabBota sprawdzony w repozytorium,
stan SuperMemo widoczny na Twoich zrzutach ekranu albo opisany dosłownie
w FAQ SuperMemo. Etap mieści się w jednej sesji pracy, wymaga Twojej
akceptacji przed rozpoczęciem i kończy się wersją `1.0.0-rc.9`.

#### Podstawa zakresu

| Różnica | SuperMemo | VocabBot w rc.8 | Pewność |
|---|---|---|---|
| samoocena | przycisk „Check” odsłania odpowiedź, potem uczący się wybiera jedną z trzech ocen; pole do wpisania odpowiedzi jest elementem włączanym w ustawieniach kursu | karta produkcji wymaga wpisanego słowa i ocenia ją silnik; własną ocenę mają tylko karty rozpoznawania | zrzuty ekranu, FAQ o konfiguracji kursów Extreme, kod |
| tłumaczenie zdania | tłumaczenie zdania przykładowego otwiera ikona pod zdaniem | pytanie pokazuje tłumaczenie od razu | zrzuty ekranu, przewodnik sesji |
| termin następnej powtórki | przełącznik „Show the number of days until the next repetition” | terminal pokazuje termin przy każdej odpowiedzi, czat podaje go na prośbę | FAQ, kod |
| wyłączenie słowa | „Disable repetitions” i „Enable repetitions” dla karty | słowo opuszcza kolejkę tylko przez zgłoszenie błędu w haśle | FAQ, kod |
| notatka do słowa | ikona edycji na karcie (jej działania nie sprawdziłem) | skojarzenia od trenera żyją tylko w rozmowie; folder nauki nie ma notatek | kod; po stronie SuperMemo sama obecność ikony |

#### Zakres

1. **Samoocena obok pisania.** Ustawienie planu `answer_mode` przyjmuje
   `type` (wartość domyślna, obecne zachowanie) albo `self`.
   - Silnik: w trybie `self` polecenie `reveal` przyjmuje kartę produkcji
     z dzisiejszej listy, a `grade` przyjmuje dla niej `know`, `almost`
     i `dont_know`. W trybie `type` oba polecenia odmawiają jak dotąd,
     z komunikatem wskazującym ustawienie. Wpisana odpowiedź zachowuje
     ocenę silnika w obu trybach. Wiersz dziennika z własną oceną nie ma
     pola `auto`, tak jak wiersze kart rozpoznawania.
   - Reguły wspólne z rc.8 obowiązują bez zmian: pierwsza ocena „wiem”
     nowego słowa daje `known`, utrwalanie ma dwie oceny.
   - Czat: hasło „pokaż” albo „sprawdź” wywołuje `vocab_reveal`, wiadomość
     pokazuje słowo w całości i pyta o ocenę, a odpowiedź uczącego się
     trafia do `vocab_grade` z `then_next`. Model przekazuje ocenę dokładnie
     tak, jak ją podał uczący się, i sam żadnej nie proponuje (reguła
     `03-engine-grades`).
   - Terminal: w trybie `self` pusty Enter pokazuje odpowiedź i prosi o ocenę
     klawiszami 1, 2, 3; wpisane słowo ocenia silnik. W trybie `type` pusty
     Enter oznacza „nie wiem” jak dotąd.
   - Karta w oknie czatu: wynik `vocab_reveal` pokazuje słowo z nagraniem
     i wiersz z trzema ocenami do wpisania.
2. **Tłumaczenie zdania na żądanie.** Ustawienie planu
   `sentence_translation` przyjmuje `shown` (wartość domyślna) albo `hidden`.
   - Silnik zwraca `sentence_pl` jak dotąd, a `today` podaje ustawienie.
   - Karta: przy `hidden` tłumaczenie otwiera przycisk pod zdaniem, bez
     udziału modelu i serwera.
   - Czat: przy `hidden` pytanie pomija tłumaczenie, a hasło „tłumaczenie”
     dopisuje je z danych, które model już ma.
   - Terminal: przy `hidden` polecenie `/t` pokazuje tłumaczenie.
   - Wartość domyślna zostaje `shown`, ponieważ w czacie prośba
     o tłumaczenie kosztuje dodatkową turę modelu. Zmiana wartości domyślnej
     na `hidden` jest Twoją decyzją przy akceptacji etapu.
3. **Termin następnej powtórki przy wyniku.** Ustawienie planu `next_review`
   przyjmuje `shown` (wartość domyślna) albo `hidden`.
   - Silnik dodaje do wyniku odpowiedzi pole `back` z gotowym tekstem
     („wróci jutro”, „wróci za 4 dni”, „wróci dziś w utrwalaniu”). Teksty
     przechodzą z sekcji terminala do wspólnej sekcji `pl.json`, więc czat,
     karta i terminal pokazują to samo.
   - Czat i karta kończą wiersz wyniku tekstem `back`.
4. **Wyłączenie słowa.** Polecenie `flag --card ID --skip` odkłada słowo bez
   zgłaszania błędu, a `flag --card ID --clear` je przywraca.
   - Silnik: wiersz w `log/flags.jsonl` dostaje znacznik `skip`; słowo
     opuszcza kolejkę, utrwalanie i wybór nowych słów tak jak słowo
     zgłoszone. `status` podaje listę `skipped` osobno od zgłoszeń.
   - Serwer: `vocab_flag` dostaje parametr `skip`.
   - Czat: hasła „nie chcę tego słowa” i „pomiń to słowo” odkładają słowo,
     „przywróć słowo …” je przywraca (kartę znajduje `vocab_lookup`).
   - Terminal: polecenie `/pomin` przy odpowiedzi.
5. **Notatka do słowa.** Polecenie `note --card ID --stdin` zapisuje własną
   notatkę uczącego się (do 500 znaków), a `note --card ID --clear` ją usuwa.
   - Silnik: plik `log/notes.jsonl` tylko rośnie i obowiązuje ostatni wiersz
     dla hasła. Notatka wraca jako `word.note` w wyniku odpowiedzi,
     w `reveal` i w `lookup`. Pytanie nigdy jej nie zawiera, ponieważ
     notatka może zdradzać odpowiedź.
   - Serwer: nowe narzędzie `vocab_note` (23 narzędzia zamiast 22).
   - Czat: hasło „zapisz notatkę: …” zapisuje tekst uczącego się. Trener po
     podaniu skojarzenia proponuje jego zapis i zapisuje je wyłącznie po
     odpowiedzi „tak”.
   - Terminal: polecenie `/notatka tekst` zapisuje notatkę do poprzedniej
     karty.
   - `doctor --merge` scala kopie konfliktowe pliku notatek tak jak
     dziennik, a `PRIVACY` wymienia notatki wśród danych w folderze nauki.

#### Pliki

| Warstwa | Pliki |
|---|---|
| silnik | `store.py` (ustawienia planu, plik notatek, znacznik `skip`), `session.py` (`reveal`, `self_grade`, pole `back`, notatka w wynikach), `plans.py`, `progress.py` (`skipped` w `status`), `doctor.py`, `cli.py` (`note`, `flag --skip`), `data/i18n/pl.json` |
| terminal | `drill.py` (pusty Enter w trybie `self`, `/t`, `/pomin`, `/notatka`) |
| serwer | `server/app.py` (`vocab_note`, `vocab_flag` ze `skip`, karta przy `vocab_reveal`), `server/static/card.html`, `server/guides/session.md`, `coach.md`, `start.md`, `rules.md` |
| wtyczka | `rules/02-answer-after-grade.md`, `rules/03-engine-grades.md`, `vocab-session` (`SKILL.md`, `reference/`), `vocab-coach`, `vocab-start/reference/plan-keys.md`, pliki generowane przez `scripts/build.py skills` |
| dokumenty | `README`, `QUICKSTART`, `docs/server`, `docs/pilot`, `plugin/PRIVACY`, `CHANGELOG`, ten plan; każdy dokument po angielsku i po polsku |
| testy | `tests/test_engine.py`, `test_cli.py`, `test_drill.py`, `test_server.py`, sesja `sessions/session-self-assessment.json` dla `session_test.py --check` |

#### Kolejność pracy w sesji

1. Silnik i polecenia dla pięciu punktów, z testami każdego punktu.
2. Terminal.
3. Serwer, karta, przewodniki, reguły i umiejętności; `build.py skills`
   i walidacje.
4. Symulacja przez polecenia na pełnych kursach oraz podgląd karty w hoście
   testowym w motywie jasnym i ciemnym.
5. Dokumenty, plan, pamięć projektu i lokalny commit.
6. Za Twoją osobną zgodą: symulacja z modelem, wydanie `v1.0.0-rc.9`
   i wdrożenie.

#### Kryteria ukończenia

| Kryterium | Sprawdzenie |
|---|---|
| tryb `type` zachowuje obecne gwarancje | testy odmów `reveal_production` i `production_needs_answer`; test sesyjny kontroli przecieku odpowiedzi bez zmian |
| tryb `self` zapisuje ocenę uczącego się | test: `reveal`, potem `grade`, wiersz bez pola `auto`, termin jak dla tej samej oceny silnika |
| odpowiedź pojawia się tylko po ocenie albo po `reveal` | symulacja: żadne `next` nie zawiera słowa ani notatki |
| słowo odłożone i przywrócone | test: karta opuszcza kolejkę i utrwalanie, `status` ją wymienia, `--clear` przywraca ją z dotychczasowym terminem |
| notatka | test: zapis, zmiana, usunięcie, obecność w wyniku i w `lookup`, brak w pytaniu, scalenie kopii konfliktowej |
| pole `back` | test: te same teksty w wyniku polecenia, w terminalu i w karcie |
| kontrole repozytorium | `ruff`, `mypy`, `pytest` na Pythonie 3.15 i 3.10, `validate.py`, `session_test.py --check`, `claude plugin validate --strict` |

#### Koszty i decyzje

| Pozycja | Koszt | Zgoda |
|---|---|---|
| implementacja, testy, symulacja przez polecenia | brak kosztów modeli | akceptacja etapu |
| symulacja sesji z modelem przez lokalny serwer | szacunkowo 1–2 USD (Sonnet w Claude Code, limit 2 USD) | osobna |
| push, tag, wydanie na GitHubie, PyPI, wdrożenie | brak | osobna dla każdej czynności |

Decyzje przy akceptacji: wartość domyślna `sentence_translation` (`shown`
według propozycji) oraz wartość domyślna `answer_mode` (`type` według
propozycji).

#### Wynik Etapu 11 (16.11.2026)

| Kryterium | Wynik |
|---|---|
| samoocena | `answer_mode=self`: `reveal` pokazuje słowo karty produkcji czekającej dziś w sesji z fazą, ocenami do wyboru (w utrwalaniu dwie) i licznikiem dnia, `grade` zapisuje ocenę uczącego się bez pola `auto`; termin jest taki sam jak po tej samej ocenie silnika; przy `answer_mode=type` obie odmowy działają jak dotąd, a ich komunikaty wskazują ustawienie |
| tłumaczenie zdania | `sentence_translation=hidden`: karta pokazuje przycisk „Tłumaczenie” pod każdym zdaniem, czat podaje tłumaczenie na hasło „tłumaczenie”, terminal na `/t` przy pytaniu i klawisz `t` przy prezentacji słowa |
| termin powtórki | pole `back` w wyniku odpowiedzi z tekstem ze wspólnej sekcji `back` w `pl.json`; terminal, karta i czat pokazują ten sam tekst; `next_review=hidden` usuwa pole |
| ustawienia w wynikach | `view` w wynikach `next`, `answer`, `grade`, `reveal` i `today` (`new_words`, `answer_mode`, `sentence_translation`, `next_review`) |
| odłożone słowo | `flag --skip` i `vocab_flag` ze `skip`; słowo opuszcza kolejkę, utrwalanie i wybór nowych słów, `status` podaje `skipped` osobno od `reported`, `--clear` przywraca słowo z dotychczasowym terminem; terminal ma `/pomin` |
| notatka | `note --card ID --stdin` i `vocab_note` (23 narzędzia); `log/notes.jsonl` tylko rośnie, obowiązuje ostatni wiersz hasła; notatka wraca w wyniku odpowiedzi, w `reveal` i w `lookup`, nigdy w `next`; terminal ma `/notatka`, trener proponuje zapis skojarzenia i zapisuje je po „tak”; reguła o zgodzie opisuje notatki |
| usterka znaleziona w testach | `doctor --merge` nie scalał kopii konfliktowych notatek; teraz scala je razem z dziennikiem i zgłoszeniami, a wiersze zgłoszeń i notatek układa według czasu, bo obowiązuje ostatni wiersz hasła |
| przewodniki i reguły | przewodnik `session`, umiejętność `vocab-session` z przykładem „pokaż”, `coach`, `words`, `start` i `plan-keys`; reguły o odpowiedzi po ocenie, o ocenie silnika i o zgodzie, z kopią w przewodniku `rules` serwera |
| testy | 268 na Pythonie 3.15 i 240 na Pythonie 3.10 (1 pominięty bez wordfreq); ruff, mypy, `validate.py`, `session_test.py --check` (8 z 8, nowa sesja `session-self-assessment`) i `claude plugin validate --strict` bez uwag; nowe testy silnika, poleceń, terminala i serwera dla każdego z pięciu punktów |
| symulacja przez polecenia | pełne kursy (de A1–A2, es A1, it A1, 15 nowych słów dziennie), trzy dni nauki z samooceną, tłumaczeniem na żądanie i notatkami, potem dzień z ukrytym terminem: 6140 sprawdzeń bez usterki w 199 odpowiedziach (66 ocen uczącego się we wszystkich odmianach, 29 notatek, 11 słów odłożonych); żadne `next` nie zawierało słowa ani notatki, a odpowiedź spoza dzisiejszej sesji została odrzucona |
| podgląd karty | host testowy w Edge w motywie jasnym i ciemnym: pytanie z ukrytym tłumaczeniem, odpowiedź po „pokaż” z notatką i trzema ocenami, w utrwalaniu z dwiema, wynik z terminem powrotu |
| symulacja z modelem | lokalny serwer i Claude Code z modelem Sonnet, plan z `answer_mode=self` i `sentence_translation=hidden`, 8 tur za 1,32 USD (limit 2 USD): pytanie bez tłumaczenia z podpowiedzią „pokaż”, „tłumaczenie” podane z tego samego wyniku bez wywołania narzędzia, „pokaż” (`vocab_reveal`) z pełną odpowiedzią i pytaniem o ocenę, „prawie” przekazane dosłownie do `vocab_grade` (wiersz bez `auto`) z terminem „wróci dziś w utrwalaniu”, notatka przez `vocab_note`, wpisana odpowiedź przez `vocab_answer` z terminem „wróci za 2 dni”, „nie chcę tego słowa” (`vocab_flag` ze `skip`) bez pokazania odpowiedzi i przywrócenie słowa nazwanego polskim znaczeniem; jedyna usterka: po przywróceniu słowa model pokazał licznik sprzed zmiany, ponieważ wynik `vocab_flag` nie miał licznika; wynik `flag` zawiera teraz licznik dnia po zmianie |
| wydanie i wdrożenie | za Twoją zgodą z 16.11.2026: tag `v1.0.0-rc.9`, wydanie przedpremierowe na GitHubie z kompletem 9 paczek, `vocabbot 1.0.0rc9` w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone, wtyczka w Twoim Codexie odświeżona do rc.9; serwer 1.0.0rc9 pod `https://vocab.archxs.com`, test dymny tylko do odczytu z krótko ważnym tokenem konta testowego, unieważnionym po teście: 23 narzędzia z `vocab_note`, karta w sześciu narzędziach (z `vocab_reveal`), `view` w `vocab_today`, odmowa `reveal_production` przy `answer_mode=type`, nagranie i przykład w `vocab_lookup` |
| do sprawdzenia | sesja z Twojego konta w Claude i ChatGPT po zmianie planu na `answer_mode=self` i `sentence_translation=hidden`: „pokaż”, przycisk „Tłumaczenie” w karcie, „nie chcę tego słowa”, „zapisz notatkę: …” |

#### Zmiana wartości domyślnych (16.11.2026, na Twoją propozycję)

Po wydaniu rc.9 zaproponowałeś włączenie nowych możliwości domyślnie.
Domyślne są teraz `answer_mode=self` i `sentence_translation=hidden`, tak jak
w kursie SuperMemo z Twojego zrzutu ekranu, który ma przycisk „Check” i trzy
oceny bez pola do wpisywania. Wpisywanie zostaje, a wpisane słowo nadal
ocenia silnik. Hasło „pokaż” kosztuje w czacie tekstowym dwie wiadomości na
kartę zamiast jednej, a prośba o tłumaczenie jedną wiadomość więcej; karta
w oknie czatu pokazuje tłumaczenie przyciskiem bez udziału modelu. Na starcie
sesji model wymienia hasła „pokaż” i „tłumaczenie”, ponieważ w czacie
tekstowym nic innego o nich nie informuje. Plan zapisany przed rc.9 dostaje
nowe wartości domyślne; na serwerze dotyczy to obu kont, ponieważ żaden plan
nie zapisał tych ustawień pod rc.9. Testy zakładające tryb wpisywania mają go
teraz jawnie, a testy planu domyślnego sprawdzają nowe zachowanie.

Wydanie i wdrożenie za Twoją zgodą z 16.11.2026: tag `v1.0.0-rc.10`, wydanie
przedpremierowe na GitHubie z kompletem 9 paczek, `vocabbot 1.0.0rc10`
w PyPI przez zaufane publikowanie z sumami zgodnymi z GitHubem, CI zielone,
wtyczka w Twoim Codexie odświeżona; serwer 1.0.0rc10 pod
`https://vocab.archxs.com`. Test dymny tylko do odczytu z krótko ważnym
tokenem konta testowego, unieważnionym po teście, pokazał w `vocab_today`
`answer_mode: self` i `sentence_translation: hidden`, a `vocab_reveal`
pokazał odpowiedź karty czekającej w sesji.

#### Poza zakresem do czasu prób

| Temat | Brakujące potwierdzenie |
|---|---|
| interaktywna karta (pole odpowiedzi i przyciski wołające serwer bez modelu) | Twoje sprawdzenie, że obecna karta wyświetla się w Claude i ChatGPT na komputerze i na telefonie; próba, czy te aplikacje pozwalają karcie wołać narzędzia serwera |
| drugie zdanie, kolokacje, nagrania zdań | policzenie pokrycia w źródłach (Wikisłownik, Tatoeba) i licencji nagrań; wycena przebiegu modelu przed uruchomieniem |
| obrazy przy hasłach | próba trafności doboru na próbce haseł |
| podsumowanie tygodnia i kalendarz powtórek jako ekrany | wygląd tych ekranów w aplikacji SuperMemo znam tylko z opisów |
| własna strona sesji pod `vocab.archxs.com` | od 18.11.2026 Etap 13, na Twoją decyzję przed wersją 1.0 |

### Etap 12. Konto jako wspólny rekord nauki

Etap 12 zaproponowałem 18.11.2026 po Twoim pytaniu o wspólny folder dla
komputera i telefonu oraz o najwygodniejszą kontynuację nauki na wielu
urządzeniach. Stan: zaakceptowany i zrealizowany 18.11.2026 razem z Etapem
13 jako wersja `1.0.0-rc.11`, wynik poniżej Etapu 13. Twoje decyzje z tego dnia: konto na serwerze jest drogą
zalecaną, a folder bez konta zostaje dla osób, które nie chcą serwera;
synchronizacja po połączeniu działa samoczynnie; Etap 13 wchodzi przed
wersją 1.0; odzyskiwanie hasła korzysta z opcjonalnego adresu e-mail. Etap
kończy się wersją `1.0.0-rc.11`.

Po etapie konto na serwerze jest wspólnym miejscem rekordu, a folder nauki
na komputerze jego kopią, która działa bez sieci i sama się synchronizuje.
Terminal, wtyczka i czat w telefonie pokazują wtedy ten sam stan.

#### Podstawa zakresu

| Zagadnienie | Stan w rc.10 | Źródło |
|---|---|---|
| dwa rekordy | folder nauki (terminal, wtyczka) i konto na serwerze (czat w przeglądarce, w aplikacji i w telefonie) nie mają połączenia; serwer nie ma importu ani eksportu | `store.py`, `server/service.py`, `docs/server.pl.md` |
| dwa komputery | dysk synchronizowany, `vocabbot use` i ręczne `doctor --merge`; oba komputery piszą do jednego `log/reviews.jsonl`, więc dysk tworzy kopie konfliktowe | `QUICKSTART.pl.md`, `doctor.py` |
| scalanie | `book._apply` układa wiersze według dnia, czasu i karty i sam wylicza rodzaj wiersza, więc suma wierszy z dowolnych urządzeń daje jeden harmonogram; zgłoszenia i notatki stosują ostatni wiersz hasła | `book.py`, `store.py` |
| kolejność wierszy w pliku | `session._next_ts` bierze największy czas w dzienniku, a nie ostatni wiersz pliku; `presence.py` czyta 500 ostatnich wierszy, a `queue.py` dzieli wiersze dla `extend`, więc te dwa miejsca wymagają sprawdzenia | kod |
| identyfikatory | hasło kursu ma identyfikator `<język>-<pojęcie>` z pojęciem trzymanym na stałe w `concepts.tsv`; własne słowo dostaje losowy identyfikator `<język>-u<6 znaków>`, więc dwa urządzenia nie nadają tego samego | `tools/courses/build.py`, `words.py` |
| dzień nauki | komputer liczy dzień w swojej strefie, a serwer w jednej strefie dla wszystkich kont; `_next_ts` odrzuca odpowiedź, gdy dziennik ma wiersz z późniejszego dnia | `store.learning_day`, `session.py` |
| logowanie programu | serwer odsyła po logowaniu także na `localhost` i `127.0.0.1` | `server/config.py` |
| hasło | nowe hasło nadaje wyłącznie administrator; serwer nie zna adresu e-mail | `docs/server.pl.md` |

#### Zakres

1. **Synchronizacja na serwerze.** Adres `/sync` przyjmuje token dostępu
   konta, ten sam co `/mcp`. Urządzenie wysyła wiersze dopisane od
   poprzedniej synchronizacji i podaje, ile wierszy konta już ma. Serwer
   dopisuje wiersze, których nie ma, i zwraca te, których nie ma urządzenie.
   - Wiersz rozpoznaje jego pełna treść, tak jak w `doctor --merge`, więc
     powtórzone wysłanie niczego nie podwaja.
   - Serwer przyjmuje wiersz dziennika, gdy przechodzi `valid_row`, jego
     karta istnieje w kursie albo we własnych słowach konta, a jego czas nie
     leży w przyszłości. Żądanie ma limit rozmiaru i częstości.
   - Narzędzia i synchronizacja jednego konta wykonują się po kolei, pod tą
     samą blokadą konta.
2. **Sposób łączenia danych.**

   | Dane | Sposób łączenia |
   |---|---|
   | `log/reviews.jsonl`, `log/flags.jsonl`, `log/notes.jsonl` | suma wierszy; pobrane wiersze dopisują się na końcu pliku, więc dziennik nadal tylko rośnie, a `Learner.rows()` zwraca wiersze w porządku dziennika niezależnie od kolejności w pliku |
   | `courses/<język>/own.jsonl`, `log/decisions.md` | suma wierszy |
   | plan | każda zatwierdzona zmiana dostaje wiersz w nowym `log/plan.jsonl` (czas i zmienione ustawienia); dla każdego ustawienia obowiązuje ostatni wiersz, a `registers/plan.json` jest po synchronizacji przeliczany z tych wierszy i sprawdzany przez `plan_problems` |
   | `registers/day.json` | większa z liczb dla tego samego dnia |
   | `registers/.pending/` | zostaje na urządzeniu |

3. **Logowanie programu.** `vocabbot login [ADRES]` otwiera stronę logowania
   serwera w przeglądarce i odbiera wynik na `127.0.0.1` (OAuth z PKCE).
   W środowisku bez przeglądarki program pokazuje adres i krótki kod do
   potwierdzenia na innym urządzeniu. Hasło uczący się wpisuje wyłącznie na
   stronie serwera. Tokeny trafiają do `~/.vocabbot/` z prawami tylko dla
   właściciela, nigdy do folderu nauki ani do wyniku polecenia.
   `vocabbot logout` odłącza folder od konta i unieważnia tokeny.
4. **Synchronizacja samoczynna.** Program pobiera przed `today`, `next`,
   `drill` i `status`, a wysyła po każdym zapisie (`answer`, `grade`,
   `regrade`, `flag`, `note`, `commit`, `today --extra`). Sesja w terminalu
   wysyła w tle, pojedyncze polecenie czeka najwyżej kilka sekund. Bez sieci
   program działa jak dotąd, a zaległe wiersze wysyła następne polecenie.
   `status` i `doctor` podają czas ostatniej synchronizacji i liczbę
   czekających wierszy; `vocabbot sync` synchronizuje na żądanie.
5. **Pierwsze połączenie i nowy komputer.** Połączenie folderu, który ma już
   dziennik, z kontem, które ma już dziennik, powstaje jako podgląd: liczba
   wierszy po obu stronach, liczba po połączeniu i wybór planu (z folderu
   albo z konta). Zapis następuje po potwierdzeniu, więc to samo polecenie
   importuje dotychczasową naukę z folderu na konto. `vocabbot login` na
   komputerze bez folderu nauki pobiera konto do `~/VocabBot`.
6. **Strona konta i przenoszenie danych.** Strona `/account` po zalogowaniu
   pokazuje połączone urządzenia i aplikacje z datą ostatniego użycia
   i odłączaniem, pobranie danych jako archiwum w formacie folderu nauki,
   adres e-mail do odzyskiwania hasła i usunięcie konta. Program dostaje
   `vocabbot export PLIK` i `vocabbot import PLIK` (import jako podgląd),
   więc rekord przechodzi także między serwerami.
7. **Odzyskiwanie hasła przez opcjonalny e-mail.** Uczący się może podać
   adres przy zakładaniu konta albo na stronie konta. Serwer trzyma
   wyłącznie skrót adresu (scrypt z solą konta). Strona „nie pamiętam hasła”
   pyta o login i adres; gdy skrót się zgadza, serwer wysyła na wpisany
   adres jednorazowy odnośnik ważny 30 minut. Odpowiedź strony jest taka
   sama dla każdego loginu i adresu. Nowe hasło kończy połączenia konta, tak
   jak `vocabbot-server password`. Wysyłka korzysta z `smtplib` i ustawień
   `VOCABBOT_SERVER_SMTP_*`; serwer bez tych ustawień nie pyta o adres,
   a hasło zmienia administrator jak dotąd.
8. **Strefa czasowa konta.** Ustawienie planu `timezone` (nazwa strefy IANA,
   na przykład `Europe/Warsaw`) wyznacza dzień nauki na serwerze i na każdym
   połączonym urządzeniu. Strona zakładania konta odczytuje strefę
   z przeglądarki, a konta sprzed etapu dostają strefę serwera. Program
   czyta strefę przez `zoneinfo`; gdy system nie ma danych stref (Windows
   bez pakietu `tzdata`), liczy dzień w strefie komputera jak dotąd.
9. **Zgodność wersji.** Żądanie `/sync` podaje wersję programu i kursu.
   Urządzenie ze starszym kursem zachowuje wiersze kart, których nie zna,
   pomija je w kolejce i radzi aktualizację w `status`.
10. **Ścieżka bez konta.** Program czyta kopie konfliktowe dziennika,
    zgłoszeń i notatek razem z plikami głównymi, więc folder w dysku
    synchronizowanym nie wymaga ręcznego scalenia. `doctor --merge` zostaje
    do uporządkowania plików.
11. **Umiejętności, przewodniki i dokumenty.** `vocab-start` proponuje
    połączenie folderu z kontem i prowadzi przez `login`; reguły w `rules/`
    obejmują stan synchronizacji jako liczby z silnika; przewodniki serwera
    idą za umiejętnościami. `README`, `QUICKSTART`, `docs/server`,
    `plugin/PRIVACY` i strona `/privacy` opisują konto jako drogę zalecaną,
    dane wysyłane na serwer (wiersze dziennika z wpisanymi odpowiedziami,
    notatki, własne słowa) i opcjonalny adres e-mail.

Skutki łączenia, które dokumenty opisują wprost:

- Ta sama karta oceniona na dwóch urządzeniach bez sieci: wcześniejsza
  odpowiedź przesuwa termin, późniejsza liczy się jako utrwalanie.
- Dwa urządzenia bez sieci mogą razem wprowadzić więcej nowych słów niż
  dzienna liczba z planu; po synchronizacji `today` podaje faktyczną liczbę.
- Dwie zmiany tego samego ustawienia planu bez sieci: obowiązuje późniejsza.

#### Do sprawdzenia na początku etapu

- `presence.py` i `queue.py` po dopisaniu wierszy z wcześniejszym czasem na
  końcu pliku.
- Dostęp `vocabbot.pyz` do sieci w piaskownicach Coworka i Codexa. Gospodarz
  bez sieci zostawia folder lokalny, a umiejętność proponuje łącznik serwera.
- Logowanie krótkim kodem w serwerze autoryzacji z SDK MCP. Gdy SDK go nie
  udostępnia, program loguje się wyłącznie przez `127.0.0.1`, a kod dochodzi
  jako własne adresy serwera.

#### Pliki

| Warstwa | Pliki |
|---|---|
| silnik | nowy `sync.py` (żądanie przez `urllib`, kursory, łączenie), `store.py` (porządek wierszy, kopie konfliktowe w odczycie, `log/plan.jsonl`, `timezone`), `gate.py` i `plans.py` (wiersz zmiany planu), `session.py`, `doctor.py`, `progress.py`, `cli.py` (`login`, `logout`, `sync`, `export`, `import`), `data/i18n/pl.json` |
| terminal | `drill.py` (wysyłanie w tle, stan synchronizacji w podsumowaniu) |
| serwer | `server/app.py` (`/sync`, `/account`, odzyskiwanie hasła), `server/service.py`, `server/accounts.py` (skrót adresu, odnośniki, urządzenia), `server/oauth.py`, `server/pages.py`, `server/config.py` (SMTP), `deploy/example.env` |
| wtyczka | `rules/`, `vocab-start` (`SKILL.md`, `reference/`), przewodniki `server/guides/`, pliki generowane przez `scripts/build.py skills` |
| dokumenty | `README`, `QUICKSTART`, `docs/server`, `docs/pilot`, `plugin/README`, `plugin/PRIVACY`, `CHANGELOG`, ten plan; każdy dokument po angielsku i po polsku |
| testy | nowy `tests/test_sync.py`, `test_engine.py`, `test_cli.py`, `test_drill.py`, `test_server.py`, sesja dla `session_test.py --check` |

#### Kryteria ukończenia

| Kryterium | Sprawdzenie |
|---|---|
| zbieżność | test losowy: trzy urządzenia i konto; odpowiedzi, notatki, zgłoszenia, własne słowa i zmiany planu w losowej kolejności z synchronizacją w losowych chwilach; po ostatniej synchronizacji każda strona ma te same wiersze, ten sam stan kart i tę samą kolejkę co jeden dziennik |
| powtarzalność | przerwane i powtórzone wysłanie nie podwaja wierszy; synchronizacja od zera daje ten sam stan |
| dziennik tylko rośnie | po każdej synchronizacji wcześniejsza treść każdego dziennika jest początkiem nowej |
| praca bez sieci | przy niedostępnym serwerze polecenia i sesja działają, `status` podaje liczbę czekających wierszy, a następna synchronizacja je wysyła |
| ciągłość sesji | sesja zaczęta w terminalu kończy się przez narzędzia serwera na tej samej karcie i odwrotnie |
| ta sama karta na dwóch urządzeniach | wcześniejsza odpowiedź przesuwa termin, późniejsza jest utrwalaniem; termin jest ten sam po obu stronach |
| pierwsze połączenie | podgląd z liczbami wierszy i wyborem planu; bez potwierdzenia żadna strona się nie zmienia |
| nowy komputer | `vocabbot login` w pustym środowisku daje folder, którego `today` zgadza się z kontem |
| zabezpieczenia `/sync` | odmowa dla wiersza nieznanej karty, wiersza z przyszłości, żądania ponad limit i tokenu innego konta; token nie występuje w folderze nauki ani w wyniku polecenia |
| strefa czasowa | urządzenie i serwer w różnych strefach liczą ten sam dzień nauki; brak danych stref daje dzień komputera bez błędu |
| eksport i import | archiwum konta otwarte jako folder nauki i zaimportowane na drugie konto daje ten sam stan kart |
| odzyskiwanie hasła | ta sama odpowiedź dla każdego loginu i adresu; odnośnik działa raz i przez 30 minut; baza zawiera wyłącznie skrót adresu; nowe hasło kończy połączenia konta |
| ścieżka bez konta | kopia konfliktowa dziennika wchodzi do stanu kart bez `doctor --merge` |
| kontrole repozytorium | `ruff`, `mypy`, `pytest` na Pythonie 3.15 i 3.10, `validate.py`, `session_test.py --check`, `claude plugin validate --strict`; silnik zostaje na bibliotece standardowej |

#### Koszty i decyzje

| Pozycja | Koszt | Zgoda |
|---|---|---|
| implementacja i testy | brak kosztów modeli | akceptacja etapu 18.11.2026 |
| symulacja z modelem: połączenie folderu z kontem przez umiejętność i dokończenie sesji w czacie | szacunkowo 1–2 USD (Sonnet w Claude Code, limit 2 USD) | osobna |
| konto SMTP serwera dla odzyskiwania hasła | według dostawcy poczty; ustawienia podajesz przy wdrożeniu | osobna, przy wdrożeniu |
| push, tag, wydanie na GitHubie, PyPI, wdrożenie | brak | osobna dla każdej czynności |

### Etap 13. Sesja w przeglądarce telefonu

Etap 13 zaproponowałem 18.11.2026 razem z Etapem 12. Stan: zaakceptowany
18.11.2026 z Twoją decyzją, że wchodzi przed wersją 1.0, i zrealizowany tego
samego dnia razem z Etapem 12. Na Twoje polecenie wykonania całego planu
w jak najmniejszej liczbie sesji oba etapy weszły do jednej wersji
`1.0.0-rc.11` zamiast `rc.11` i `rc.12`.

W rc.10 telefon ma sesję wyłącznie w aplikacji czatu: każda karta kosztuje
turę modelu i zużywa limit subskrypcji uczącego się. Strona sesji daje to
samo co `vocabbot drill`, w przeglądarce i bez modelu. Silnik ocenia wpisaną
odpowiedź, a samoocena jest od rc.10 wartością domyślną, więc sesja nie
potrzebuje modelu.

#### Zakres

1. **Strona sesji `/app`.** Uczący się loguje się kontem, w tej samej sesji
   przeglądarki co strona konta z Etapu 12. Karta ma układ `card.html`:
   licznik dnia, trzy etapy z liczbą kart, polskie znaczenie i zdanie
   z luką, pole odpowiedzi, „pokaż” z trzema ocenami (w utrwalaniu dwiema),
   tłumaczenie zdania pod przyciskiem, nagranie, notatka, odłożenie słowa,
   zmiana oceny poprzedniej odpowiedzi, kolejne nowe słowa, kolejna tura
   powtórek i podsumowanie dnia.
2. **Adresy `/api/…`.** Każdy adres wykonuje polecenie silnika przez
   `Service.call`, tak jak narzędzie MCP, więc gwarancje zostają: pytanie
   bez odpowiedzi, ocena z silnika, zmiana planu przez podgląd i token.
   Sesja przeglądarki korzysta z ciasteczka `HttpOnly`, `Secure`
   i `SameSite=Strict`, a każdy zapis wymaga żetonu CSRF. Polityka CSP
   dopuszcza poza serwerem tylko nagrania z `upload.wikimedia.org`.
3. **Plan i postęp.** Pierwszy plan (języki, poziomy, liczba nowych słów,
   dni wolne, opcjonalny test poziomujący z `quiz`) i jego zmiany powstają
   w formularzu jako podgląd z potwierdzeniem. Wyniki `status` i `forecast`
   mają własny ekran.
4. **Ekran główny telefonu.** Manifest aplikacji internetowej i ikony
   z awatara pozwalają dodać stronę do ekranu głównego. Przeglądarka
   przechowuje same pliki strony; odpowiedzi wymagają sieci.
5. **Układ.** Strona powstaje najpierw dla szerokości telefonu. Na
   komputerze działa klawiatura (Enter, 1, 2, 3). Motyw jasny i ciemny idą
   za systemem, a każdy tekst pochodzi z `pl.json`.
6. **Bez modelu.** Wyjaśnienia trenera oraz własne słowa z tekstu i ze zdjęć
   zostają w czacie.

#### Pliki

| Warstwa | Pliki |
|---|---|
| serwer | `server/app.py` (`/app`, `/api/…`), nowy `server/web.py` (sesja przeglądarki, CSRF), `server/pages.py`, `server/static/` (strona sesji, manifest, ikony), `data/i18n/pl.json` |
| dokumenty | `README`, `QUICKSTART`, `docs/server`, `docs/pilot`, `plugin/PRIVACY`, `CHANGELOG`, ten plan; każdy dokument po angielsku i po polsku |
| testy | `tests/test_server.py` oraz nowy `tests/test_web.py` |

#### Kryteria ukończenia

| Kryterium | Sprawdzenie |
|---|---|
| ten sam dziennik | pełny dzień nauki przez `/api` daje te same wiersze co te same odpowiedzi przez polecenia |
| pytanie bez odpowiedzi | żadna odpowiedź `/api` z pytaniem nie zawiera słowa ani notatki, dla wszystkich kart dnia |
| sesja przeglądarki | zapis bez żetonu CSRF i żądanie z obcego źródła są odrzucane; drugie konto nie widzi danych pierwszego; wylogowanie kończy sesję |
| ciągłość | sesja przerwana na stronie kończy się w terminalu po synchronizacji i odwrotnie |
| plan | formularz zapisuje plan dopiero po potwierdzeniu podglądu |
| układ | przejście sesji w przeglądarce przy szerokości 360 px i na komputerze, w motywie jasnym i ciemnym, bez przewijania w poziomie |
| telefon | Twoje sprawdzenie: dodanie do ekranu głównego, sesja i nagrania na Twoim telefonie |
| kontrole repozytorium | `ruff`, `mypy`, `pytest` na Pythonie 3.15 i 3.10, `validate.py`, `session_test.py --check`, `claude plugin validate --strict` |

#### Koszty i decyzje

| Pozycja | Koszt | Zgoda |
|---|---|---|
| implementacja, testy, przejście w przeglądarce | brak kosztów modeli | akceptacja etapu 18.11.2026 |
| push, tag, wydanie na GitHubie, PyPI, wdrożenie | brak | osobna dla każdej czynności |

#### Poza zakresem do czasu prób

| Temat | Brakujące potwierdzenie |
|---|---|
| sesja na stronie bez sieci | wymaga listy dnia z odpowiedziami w telefonie i oceny po stronie przeglądarki; wiersze przyjąłby `/sync` z Etapu 12; decyzja po Twojej nauce na stronie |
| przypomnienia o powtórkach w telefonie | próba powiadomień przeglądarki na Twoim telefonie |
| aplikacja ze sklepu | wynik pilotażu strony sesji |

#### Wynik Etapów 12 i 13 (18.11.2026, wersja 1.0.0-rc.11)

Oba etapy powstały w jednej sesji pracy. Silnik dostał moduły `sync.py`
(strumienie wierszy, strona konta i strona folderu, eksport i import)
i `remote.py` (logowanie programu, tokeny, połączenie z `/sync`,
synchronizacja wokół poleceń), a serwer moduły `web.py` (strony
przeglądarki i `/api`) i `mail.py` (odnośnik odzyskiwania hasła).

| Kryterium | Wynik |
|---|---|
| zbieżność | test losowy w zestawie (3 przebiegi) oraz jednorazowe sprawdzenie 60 dalszych przebiegów: trzy urządzenia i konto, odpowiedzi, notatki, słowa odłożone i przywrócone, własne słowa i zmiany planu w losowej kolejności z synchronizacją w losowych chwilach; po ostatniej synchronizacji każda strona ma te same wiersze, te same stany kart, tę samą kolejkę dnia, ten sam plan, notatki i zgłoszenia |
| powtarzalność | to samo żądanie wysłane ponownie nie zmienia dziennika konta; synchronizacja od zera (bez kursorów i epoki) nie zmienia żadnego dziennika |
| dziennik tylko rośnie | po każdej synchronizacji wcześniejsza treść dziennika na urządzeniach i na koncie jest początkiem nowej |
| praca bez sieci | przy niedostępnym serwerze `remote.auto` zapisuje niepowodzenie w powiązaniu, `status` podaje liczbę czekających wierszy, przez minutę polecenia nie czekają na sieć, a następna synchronizacja wysyła wiersze |
| ciągłość sesji | testy silnika, HTTP i e2e: karta, którą pokazałby telefon, jest następną kartą w terminalu; odpowiedź z przeglądarki dociera do folderu przed jego kolejnym poleceniem |
| ta sama karta na dwóch urządzeniach | wcześniejsza odpowiedź przesuwa termin, późniejsza jest utrwalaniem; stan jest ten sam po obu stronach |
| pierwsze połączenie | podgląd z liczbami odpowiedzi, notatek i zgłoszeń po obu stronach i po połączeniu oraz z planem, który zostaje; przed potwierdzeniem nie powstaje nawet powiązanie; przy różnych planach `login` kończy się błędem `choose_plan` z oboma planami, a w terminalu program pyta sam |
| nowy komputer | `vocabbot login` w pustym środowisku pobiera konto i zapisuje wskaźnik folderu, a licznik `today` zgadza się z kontem |
| zabezpieczenia `/sync` | odmowa dla wiersza nieznanej karty, z przyszłości, uszkodzonego, niebędącego wierszem, ponad 5000 wierszy jednego pliku w jednym żądaniu, bez tokenu i z fałszywym tokenem; drugie konto nie widzi danych pierwszego; tokeny są tylko w `~/.vocabbot/credentials.json`, nigdy w wyniku polecenia |
| strefa czasowa | ustawienie planu `timezone` wyznacza dzień nauki w programie i na serwerze; nowe konto dostaje strefę z przeglądarki, a połączenie folderu bez strefy daje mu strefę konta |
| eksport i import | archiwum ze strony konta otwarte poleceniem `vocabbot import` daje te same wiersze i stany kart; import do folderu z planem dodaje tylko brakujące wiersze i zostawia plan |
| odzyskiwanie hasła | ta sama strona dla każdego loginu i adresu; odnośnik działa raz i przez 30 minut; baza ma tylko skrót adresu; nowe hasło kończy połączenia i sesje przeglądarki |
| ścieżka bez konta | wiersze kopii konfliktowych dziennika, notatek i zgłoszeń liczą się bez `doctor --merge` |
| ten sam dziennik przez `/api` | dzień nauki przez stronę sesji i te same odpowiedzi przez polecenia dają te same karty, oceny, rodzaje wierszy, klasy błędów i dni |
| pytanie bez odpowiedzi | żadna odpowiedź `/api/next` nie zawiera słowa ani notatki karty |
| sesja przeglądarki | zapis bez żetonu formularza albo z obcym pochodzeniem jest odrzucany; drugie konto nie widzi danych pierwszego; wylogowanie kończy sesję |
| układ | przejście w Chromium przy szerokości 375 px w motywie jasnym i ciemnym od założenia konta i pierwszego planu przez pytanie, „Pokaż” z kafelkami ocen, wynik, notatkę, zmianę etapu, postępy i zmianę planu do ekranu końca dnia: bez przewijania w poziomie i bez błędów skryptu |
| e2e | osobne procesy serwera i programu na dwóch „komputerach” z własnymi katalogami konfiguracji oraz „telefon” przez HTTP: konto z zaproszeniem, plan i odpowiedzi na stronie sesji, pobranie konta kodem potwierdzonym na telefonie, ta sama karta w terminalu, połączenie drugiego folderu z planem konta, trzy jednakowe dzienniki, eksport i import, wylogowanie widoczne na stronie konta |
| kontrole repozytorium | ruff, mypy, `validate.py`, `build.py skills --check`, `session_test.py --check` (8 z 8) i `claude plugin validate --strict` bez uwag; testy: 304 na Pythonie 3.15 i 276 na 3.10 (1 pominięty bez wordfreq) |

Usterki znalezione w testach i poprawione:

1. Kolejność własnych słów zależała od kolejności wierszy w `own.jsonl`,
   inna na każdym urządzeniu. Teraz wynika z rangi wiersza, rodzaju wiersza
   i identyfikatora, a słowo kursu przesunięte na początek dostaje własną
   rangę.
2. Urządzenie, którego zmiana planu przegrała z późniejszą zmianą innego
   urządzenia, mogło zostać przy własnym planie. Każda synchronizacja
   przelicza teraz plan z historii.
3. Chrome wysyła `Origin: null` przy polityce `no-referrer`, więc kontrola
   pochodzenia odrzucała formularze z własnych stron serwera. Strony mają
   teraz `Referrer-Policy: same-origin`, a przy `Origin: null` serwer
   sprawdza `Sec-Fetch-Site`.
4. Formularz unieważnienia tokenu w SDK MCP wymaga pola `client_secret`
   także od klienta publicznego; program wysyła je puste.

Przegląd kodu (`/code-review`, 12 kierunków wyszukiwania, każda usterka
sprawdzona osobno) zgłosił 15 głównych usterek i ponad 30 drobniejszych.
Poprawiłem wszystkie główne, każdą z testem:

1. Wiersz dopisany podczas trwającej wymiany (odpowiedź w terminalu przy
   wysyłaniu w tle) był zapisywany jako wysłany i nigdy nie trafiał na konto.
   Folder uznaje teraz za wysłane tylko to, co faktycznie poszło, oraz
   wiersze pobrane, gdy plik ma dokładnie oczekiwany układ.
2. Zalogowanie programu na inne konto tego samego serwera łączyło po cichu
   zapisy dwóch osób. Folder podaje teraz swoje konto, a serwer i program
   odmawiają wymiany z innym kontem (`other_account`).
3. Konto albo folder z dziennikiem, ale bez planu (plan konta odrzucony przez
   kontrolę), mogło zostać wyczyszczone przez nowy plan albo import. Nowy plan
   zostawia istniejące dzienniki, import do takiego folderu odmawia
   (`folder_not_empty`), a pobranie konta z planem nie do przyjęcia kończy się
   błędem `account_plan_invalid` z prośbą o aktualizację programu.
4. Wiersze odrzucone z przyczyny przejściowej (zegar przed serwerem, kurs albo
   wersja, których konto jeszcze nie ma) przepadały. Wracają teraz z każdą
   synchronizacją, aż konto je przyjmie, i liczą się jako czekające.
5. Wiersz z nieistniejącym dniem (`2026-02-30`) albo wiersz planu z wartością
   złego typu psuł każde późniejsze odtworzenie dziennika. Silnik pomija taki
   wiersz w odtworzeniu, serwer go nie przyjmuje, a błąd jednego konta nie
   kończy wywołania błędem serwera.
6. Treść żądań `/api` i `/sync` była czytana w całości przed sprawdzeniem
   rozmiaru. Serwer czyta ją teraz strumieniowo do limitu.
7. Kopie konfliktowe historii planu blokowały zmiany planu, kopia dziennika
   dłuższa niż jedno żądanie nie dochodziła na konto w całości, a eksport
   pomijał wiersze kopii. Kopie historii planu liczą się teraz jak inne
   dzienniki i łączy je `doctor --merge`, kopie idą w kolejnych żądaniach,
   a eksport zawiera ich wiersze.
8. Adres e-mail do odzyskiwania hasła zmieniało samo ciasteczko sesji.
   Zmiana i usunięcie adresu wymagają teraz hasła.
9. Strefa czasowa przyjęta na jednym systemie mogła zostać odrzucona na
   innym i zatrzymać plan. Nazwa strefy musi teraz mieć dokładną pisownię
   z listy IANA, serwer sprawdza swoją strefę przy starcie, a nieznana strefa
   wypada z planu zamiast go zatrzymywać.
10. Zmiany dwóch różnych języków planu na dwóch urządzeniach nadpisywały się
    nawzajem. Historia planu zapisuje teraz zmianę każdego języka osobno.
11. Wiersz planu z ustawieniem nowszej wersji był odrzucany w całości.
    Nieznane ustawienia zostają w historii i są pomijane przy wyliczaniu
    planu.
12. Na stronie sesji drugi Enter po „Pokaż” wybierał ocenę „wiem”, a na
    ekranie końca dnia dodawał nowe słowa. Enter działa teraz tylko tam,
    gdzie przejście dalej jest bezpieczne.
13. Karta postępów pokazywała trudne słowa czekające dziś w sesji razem
    z odpowiedzią. Takie słowa nie są teraz wyświetlane.
14. Sesja uruchomiona z ekranu startowego (`vocabbot`, Enter) i zmiany
    zatwierdzane od razu w terminalu nie były synchronizowane. Obie drogi
    korzystają teraz z tej samej synchronizacji.
15. Pierwsza synchronizacja połączenia mogła przyjąć plan konta wbrew
    wyborowi „plan folderu”, a każda nieudana próba dopisywała kolejny wiersz
    połączenia. Wiersz połączenia powstaje teraz raz, a wysyłanie w tle czeka
    na pierwszą pełną synchronizację.

Poprawiłem też większość drobniejszych uwag, między innymi: jedną
synchronizację folderu naraz w procesie, plik tokenów tworzony od razu tylko
dla właściciela, porównywanie adresu serwera bez względu na wielkość liter,
stronę powrotu po nieudanym logowaniu, datę połączenia zachowaną przy
odświeżeniu tokenu, unieważnianie kodów urządzeń przy zmianie hasła, licznik
odzyskiwania hasła liczony dla adresu i loginu razem, wspólny licznik
nieudanych logowań, połączenia sprzed aktualizacji widoczne na stronie konta,
komunikaty błędów `/api`, odczyt archiwum z limitem i bez powtórzonych nazw,
podział wierszy importu wyłącznie po LF, decyzję importu bez lokalnej
ścieżki, przeładowanie strony sesji po wygaśnięciu sesji, brak strony konta
w pamięci service workera i odczyt kursów tylko przy zmianie planu.
Bez zmian zostały: kolejność zgłoszeń i notatek przy cofniętym zegarze,
kolejność starych wierszy `own.jsonl` bez rangi, strona `/device` bez nazwy
programu proszącego o kod oraz czas pierwszego połączenia bardzo dużego
dziennika.

Zmiany względem zakresu:

- SDK MCP nie ma przepływu urządzenia, więc kod potwierdzany na innym
  urządzeniu działa na własnych adresach serwera (`/device`,
  `/device/authorize`, `/device/token`), tak jak przewidywał punkt „Do
  sprawdzenia na początku etapu”.
- Odczyt dziennika w kolejności dziennika (`Learner.rows()`) usunął
  zależność `presence.py` i `queue.py` od kolejności wierszy w pliku.
- `status` podaje `activity`, czyli liczbę odpowiedzi z każdego z ostatnich
  84 dni, z której korzysta mapa aktywności strony sesji.
- Wygląd strony sesji przeprojektowałem 18.11.2026 na Twoją prośbę według
  wzorców Vercel (Geist): pierścień postępu dnia, przełącznik etapów
  z liczbami, kafelki ocen z ikonami i klawiszami zamiast pełnych kolorowych
  przycisków, pasek wyniku z terminem powrotu, karty statystyk, mapa
  aktywności z 12 tygodni, pierścień trwałości z kreską celu, wykres
  prognozy, wybór języków kafelkami i ikony w kartach nawigacji.

Wdrożenie za Twoją zgodą z 18.11.2026: serwer 1.0.0rc11 (obraz
`vocabbot-server:1.0.0rc11-1a982db`) działa pod `https://vocab.archxs.com`.
`/health` podaje wersję, strony `/app/login`, `/recover`, `/device`
i manifest odpowiadają, `/app/` bez sesji odsyła do logowania, a `/sync` bez
tokenu odpowiada 401. Odzyskiwanie hasła wysyła pocztę z konta
pocztowego w domenie serwera przez `smtp.mail.ovh.net` na porcie 587 ze STARTTLS, bo
Hetzner blokuje wychodzący port 465; logowanie SMTP z kontenera działa, a hasło
leży na serwerze w pliku `/opt/vocabbot/smtp.env` dostępnym tylko dla roota.
Pierwsze wdrożenie pokazało, że docker compose podstawia `$` w pliku
zmiennych, więc skrypt zapisuje teraz wartości w pojedynczych cudzysłowach
(commit `1a982db`).

Wydanie za Twoją zgodą z 18.11.2026: tag `v1.0.0-rc.11` na commicie
`1a982db`, wydanie przedpremierowe na GitHubie z kompletem 9 paczek (koło,
źródła, `vocabbot.pyz`, `vocabbot.plugin`, cztery archiwa umiejętności,
`SHA256SUMS`) i `vocabbot 1.0.0rc11` w PyPI przez zaufane publikowanie,
uruchomione ręcznie dla tagu, z sumami zgodnymi z GitHubem. CI jest zielone:
testy na Pythonie 3.10 i 3.15 z testem e2e oraz kontrole wtyczki. Pierwszy
push odrzucił GitHub, bo aktywne konto `gh` (`dithiothreitol-gpf`) nie ma
uprawnień do repozytorium; wypchnąłem z konta `dithiothreitol` po Twojej
decyzji, a potem przywróciłem poprzednie konto.

Strony serwera przeprojektowałem 18.11.2026 na Twoją prośbę. Strona
startowa, prywatność, logowania, konto, odzyskiwanie hasła i `/device` mają
wygląd zgodny z Geist i są dostępne po polsku i po angielsku: język wynika
z przełącznika (ciasteczko `vocabbot_lang`), a bez niego z nagłówka
`Accept-Language`, wiadomość odzyskiwania hasła wychodzi w języku strony.
Teksty zredagowałem w formalnym, naturalnym rejestrze, bez potoczności
i długich myślników. Akcenty kolorystyczne pochodzą z awatara (niebieski,
granat i bursztyn) zamiast gradientów i poświat. Strona startowa pokazuje
przykładową sesję w aplikacji czatu, metodę, konfigurację z kopiowaniem
adresu i poleceń oraz granatowe wezwanie do działania. Styl leży
w `static/site.css` (adres ze skrótem treści, pamięć podręczna na rok),
angielskie teksty w `data/i18n/en.json`. Za Twoją zgodą z 18.11.2026 zmiana
wchodzi do wersji `1.0.0-rc.12` razem z przeniesieniem na nową domenę.

Nowa domena na Twoją prośbę z 18.11.2026: serwis przenosi się pod adres
`https://vocabbot.run`. Program domyślnie łączy się z nowym adresem, a skrypt
wdrożenia przekierowuje `vocab.archxs.com` i `www.vocabbot.run` na nową
domenę na stałe (308, zmienna `REDIRECT_FROM`). Domena korzysta
z serwerów nazw hostido.net.pl i do 18.11.2026 wskazywała stronę parkingową
(185.110.51.x), więc przed wdrożeniem rekordy A domeny `vocabbot.run`
i `www.vocabbot.run` muszą wskazywać serwer 167.233.57.77. Zmiana domeny
zmienia wystawcę OAuth i adres MCP: aplikacje czatu trzeba połączyć ponownie,
przeglądarkę zalogować jeszcze raz, a połączony folder nauki połączyć
poleceniem `vocabbot login --server https://vocabbot.run`. Wiadomości
odzyskiwania hasła wysyła odtąd skrzynka pomocy w domenie `vocabbot.run` przez
`mail.vocabbot.run` na porcie 587 ze STARTTLS (port 465 Hetzner blokuje);
logowanie z kontenera na serwerze działa, certyfikat obejmuje
`*.vocabbot.run`, a hasło jest takie samo jak dotychczasowe. Rekord
`mail.vocabbot.run` pozostaje przy serwerach hostido.

Wydanie i wdrożenie za Twoją zgodą z 18.11.2026: commit `0ff2397`, tag
`v1.0.0-rc.12`, wydanie przedpremierowe na GitHubie z kompletem 9 paczek
i `vocabbot 1.0.0rc12` w PyPI przez zaufane publikowanie, z sumami zgodnymi
z GitHubem. CI jest zielone: testy na Pythonie 3.10 i 3.15 oraz kontrole
wtyczki. Po zmianie rekordów A w hostido serwer
`vocabbot-server:1.0.0rc12-0ff2397` działa pod `https://vocabbot.run`
z certyfikatami Let's Encrypt dla `vocabbot.run` i `www.vocabbot.run`.
Adresy `vocab.archxs.com` i `www.vocabbot.run` przekierowują kodem 308
z zachowaniem ścieżki i parametrów, metadane OAuth podają wystawcę
`https://vocabbot.run` i zasób `https://vocabbot.run/mcp`, `/mcp` bez tokenu
odpowiada 401, a logowanie SMTP z kontenera działa. Rekord A ma TTL jednej
godziny, więc przez ten czas pamięć podręczna DNS u części użytkowników może
jeszcze wskazywać stronę hostido.

Strona startowa z ruchem i widocznością w wyszukiwarkach na Twoją prośbę
z 18.11.2026: nagłówek wsuwa się linia po linii, obok unoszą się słowa
z kursów, a przykładowa rozmowa odtwarza się w pętli z wpisywaną odpowiedzią
i oceną silnika. Sekcje pojawiają się przy przewijaniu, rysunki metody rysują
się same, liczby się odliczają. Nowe sekcje: kursy w liczbach, trzy etapy
dnia, pięć kursów z liczbą haseł na poziom i dziesięć pytań z odpowiedziami.
Ruch to CSS i jeden mały skrypt dopuszczony skrótem; `prefers-reduced-motion`
go wyłącza. Strony indeksowane mają adres kanoniczny, linki `hreflang`
z `x-default`, Open Graph i karty X z obrazem 1200 na 630 dla każdego języka
(`scripts/make_social.py`) oraz dane schema.org (SoftwareApplication,
FAQPage i inne). Serwer podaje `/robots.txt`, `/sitemap.xml` i `/llms.txt`.
Commit `70d7a50` działa pod `https://vocabbot.run` od 18.11.2026, a za Twoją
zgodą z tego dnia zmiana wchodzi do wersji `1.0.0-rc.13`.

Do sprawdzenia poza sesją pracy:

| Temat | Potrzebne |
|---|---|
| nowa domena | ponowne połączenie Claude i ChatGPT z adresem `https://vocabbot.run/mcp`, ponowne logowanie na `https://vocabbot.run/app/` oraz `vocabbot login` w połączonych folderach (od wersji rc.12 domyślnie nowy adres) |
| telefon | Twoje sprawdzenie strony `https://vocabbot.run/app/` na telefonie: dodanie do ekranu głównego, sesja i nagrania |
| wyszukiwarki | dodanie `vocabbot.run` w Google Search Console i Bing Webmaster Tools oraz zgłoszenie `https://vocabbot.run/sitemap.xml` (wymaga Twoich kont) |
| piaskownice gospodarzy | czy Cowork i Codex pozwalają `vocabbot.pyz` łączyć się z serwerem; bez sieci folder działa lokalnie, a synchronizacja czeka |
| poczta | jedna prawdziwa wiadomość odzyskiwania z Twojego konta: adres na stronie konta, potem „Nie pamiętam hasła” |
| sesja z modelem | symulacja połączenia folderu przez umiejętność `vocab-start` (koszt modeli, osobna zgoda) |

---

## 11. Weryfikacja kompletności

### 11.1 Funkcje kursów SuperMemo

| Funkcja | Wersja 1.0 | Realizacja |
|---|---|---|
| Kurs słownictwa według częstości z poziomami CEFR | tak | kursy A1–A2 i B1–B2, kolejność według częstości |
| Strona słowa: znaczenie, przykład, wymowa | tak | znaczenie polskie, zdanie z luką, IPA |
| Trzy oceny | tak | `know`, `almost`, `dont_know`; w utrwalaniu dwie oceny (Etap 10) |
| Nauka, powtórki, utrwalanie | tak | trzy etapy dnia w tej kolejności, z wyborem etapu przez uczącego się, kolejnymi nowymi słowami i kolejnymi turami powtórek (Etap 10) |
| Powtórka przy trwałości około 90% | tak | FSRS-6, trwałość w planie, rozrzut terminów, początkowe odstępy dopasowane do dziennika, pełne dopasowanie dla języka po wygranej w `replay`, terminy według obecności |
| Pomijanie znanych słów | tak | ocena „znałem” i test poziomujący |
| Liczba kart dziennie, czas trwania kursu | tak | `plan`, `forecast` |
| Kalendarz z dniami wolnymi | tak | `days_off` |
| Powtórki mieszane z kilku kursów | tak | ustawienie domyślne z regułami dla rodzin kart |
| Statystyki nauki | tak | `status` |
| Rozmowa z asystentem na poznanym słownictwie | tak | `vocab-coach` |
| Synchronizacja między urządzeniami | tak | konto na serwerze jako wspólny rekord z samoczynną synchronizacją folderu (Etap 12); bez konta folder nauki w dysku synchronizowanym |
| Obrazy, nagrania lektora, rozpoznawanie mowy | po 1.0 | rozdział 14 |
| Sesja w telefonie | tak | czat przez serwer (Etap 6) i strona sesji w przeglądarce (Etap 13) |
| Aplikacja na telefon ze sklepu | po 1.0 | rozdział 14 |

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
| Etap 6, serwer dla aplikacji czatu | brak | akceptacja etapu 15.11.2026 |
| Etap 6, test sesji z modelem przez łącznik | 1,54 USD przy Claude Sonnet 5.5 (szacunek 1–3 USD) | zatwierdzony 15.11.2026 |
| Etap 6, wdrożenie na VPS | brak kosztów modeli | zatwierdzone 15.11.2026 |
| Etap 7, przegląd włoskich znaczeń i przykładów | 3,54 USD przy Claude Sonnet 5.5 (limit 7 USD) | zatwierdzony 15.11.2026 |
| Etap 8, zdania przykładowe z modelu dla 10 738 haseł | 8,32 USD przy Claude Sonnet 5.5 (próbka 0,09 USD, limit 12 USD) | zatwierdzony 16.11.2026 po próbce |
| Etap 8, symulacje sesji z modelem przez lokalny serwer | 2,86 USD (9 i 6 tur, model Sonnet w Claude Code) | w ramach polecenia z 16.11.2026 |
| Etap 10, symulacja sesji z modelem przez lokalny serwer | 1,79 USD (10 tur, model Sonnet w Claude Code; szacunek 1–2 USD) | zatwierdzona 16.11.2026 |
| Etap 11, symulacja sesji z modelem przez lokalny serwer | 1,32 USD (8 tur, model Sonnet w Claude Code; limit 2 USD) | zatwierdzona 16.11.2026 |
| Etap 12, konto jako wspólny rekord nauki | brak | akceptacja etapu 18.11.2026 |
| Etap 12, symulacja z modelem: połączenie folderu z kontem i dokończenie sesji w czacie | szacunkowo 1–2 USD (Sonnet w Claude Code, limit 2 USD) | osobna |
| Etap 12, konto SMTP serwera dla odzyskiwania hasła | brak kosztów modeli; opłata według dostawcy poczty | osobna, przy wdrożeniu |
| Etap 13, sesja w przeglądarce telefonu | brak | akceptacja etapu 18.11.2026 |
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
| Publiczny serwer przyciąga nieproszone konta i próby logowania | konta wyłącznie z kodem zaproszenia, limit nieudanych prób, hasła w scrypt, tokeny jako skróty, adresy zwrotne z listy dozwolonych |
| ChatGPT w planach Plus i Pro udostępnia własnym łącznikom tylko odczyt | Claude jako pierwsza aplikacja pilotażu; 16.11.2026 konto pilotażysty w ChatGPT zapisało plan i 18 odpowiedzi przez serwer dodany we Wtyczkach |
| Zdanie wygenerowane przez model ma błąd albo inne znaczenie słowa | przegląd przykładów jak dla zdań z Tatoeby, próbka 40 haseł przed pełnym przebiegiem, źródło `generated` w haśle, zgłoszenia `flag` |
| Nagranie w Commons zmienia nazwę albo znika | nazwy odświeżane przy każdej budowie kursu; hasło bez nagrania pokazuje sam zapis IPA |
| Zegar albo strefa czasowa urządzenia różni się od konta | dzień nauki w strefie konta, odmowa serwera dla wierszy z przyszłości, dotychczasowa odmowa `day_before_last` |
| Urządzenia mają różne wersje programu albo kursu | stałe identyfikatory haseł; `/sync` podaje wersje; starsze urządzenie zachowuje wiersze nieznanych kart i radzi aktualizację |
| Token programu wycieka z komputera | token w `~/.vocabbot/` z prawami tylko dla właściciela, poza folderem nauki; odłączenie urządzenia na stronie konta; token odświeżania wymieniany przy każdym użyciu |
| Adres e-mail powiększa zakres danych osobowych | adres opcjonalny, na serwerze wyłącznie jego skrót; `PRIVACY` i `/privacy` opisują zmianę |
| Strona sesji otwiera serwer na ataki przez przeglądarkę | ciasteczko `HttpOnly`, `Secure` i `SameSite=Strict`, żeton CSRF przy zapisie, polityka CSP, dotychczasowy limit prób logowania |

---

## 14. Rozszerzenia po wersji 1.0

- Wymowa w sesji w terminalu (odtwarzanie nagrań i synteza mowy systemu
  operacyjnego); nagrania w czacie obejmuje Etap 8, kartę z odtwarzaniem
  Etap 9.
- Sesja na stronie z Etapu 13 bez sieci, przypomnienia o powtórkach
  w telefonie i aplikacja ze sklepu.
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
- SuperMemo, powtórki i utrwalenia: https://www.supermemo.com/pl/faq/powtorki-i-utrwalenia
- SuperMemo, pierwsze kroki z kursem: https://www.supermemo.com/en/blog/how-to-start-learning-with-a-course-5-easy-steps
- SuperMemo, skróty klawiszowe: https://www.supermemo.com/en/faq/which-keyboard-shortcuts-can-i-use-in-supermemo
- SuperMemo, liczba kart dziennie: https://www.supermemo.com/en/blog/customize-your-learning-with-supermemo
- SuperMemo, limit powtórek: https://www.supermemo.com/en/faq/repetition-limit
- SuperMemo, kolejność powtórek: https://www.supermemo.com/en/blog/new-at-supermemo-sort-your-repetitions
- SuperMemo, jak się uczyć: https://www.supermemo.com/en/blog/how-to-learn-with-supermemo
- SuperMemo dla Windows, słownik pojęć (Final drill, Mid-interval repetition): https://www.super-memory.com/help/g.htm
- FSRS, opis algorytmu: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
- py-fsrs: https://github.com/open-spaced-repetition/py-fsrs
- kaikki.org, dane Wikisłownika: https://kaikki.org/dictionary/rawdata.html
- CEFR-J Vocabulary Profile: https://github.com/openlanguageprofiles/olp-en-cefrj
- Tatoeba, pliki do pobrania: https://tatoeba.org/downloads
- MCP, autoryzacja: https://modelcontextprotocol.io/specification/draft/basic/authorization
- SDK MCP dla Pythona: https://github.com/modelcontextprotocol/python-sdk
- Anthropic, własne łączniki przez zdalny MCP: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Anthropic, budowa łączników: https://support.anthropic.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers
- OpenAI, uwierzytelnianie w Apps SDK: https://developers.openai.com/apps-sdk/build/auth
- OpenAI, tryb dewelopera i aplikacje MCP: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- fsrs-rs: https://docs.rs/fsrs/
- Benchmark algorytmów powtórek: https://github.com/open-spaced-repetition/srs-benchmark oraz https://expertium.github.io/Benchmark.html
- FSRS Helper (Easy Days, równoważenie obciążenia): https://github.com/open-spaced-repetition/fsrs4anki-helper
- Waisman Center, przeplatanie języków: https://www.waisman.wisc.edu/?p=36980
- MPI Nijmegen, „New in, old out”: https://forms.mpi.nl/node/55663
- Bartolotti i Marian, nauka trzeciego języka: https://bilingualism.northwestern.edu/wp-content/uploads/2018/05/BartolottiMarian2018.pdf
