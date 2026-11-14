# VocabBot

[English](README.md) · **Polski**

VocabBot uczy słownictwa w jednym, dwóch lub trzech językach równocześnie:
angielskim, niemieckim, hiszpańskim i francuskim, od poziomu A1 do B2, dla
osób, których językiem bazowym jest polski. Nauka przebiega tak jak w kursach
słownictwa SuperMemo: nowe słowa według częstości, trzy oceny każdej
odpowiedzi, powtórki w dniu wyznaczonym przez algorytm oraz utrwalanie słów
z błędną odpowiedzią. Jeden silnik obsługuje dwie drogi nauki: program
`vocabbot` w terminalu oraz wtyczkę dla Claude'a i Codexa, która prowadzi tę
samą sesję w czacie.

## Przebieg nauki

- **Dzień.** Najpierw powtórki zaplanowane na dziś, potem nowe słowa, na
  końcu utrwalanie: każda karta z błędną odpowiedzią wraca pod koniec sesji
  aż do odpowiedzi „wiem”. Odpowiedź w utrwalaniu nie zmienia terminu
  powtórki.
- **Karty.** Karta pokazuje polskie znaczenie, część mowy i zdanie
  przykładowe z luką, a uczący się wpisuje słowo. Nowe słowo pojawia się
  najpierw z rodzajem, formami, wymową IPA i przykładem.
- **Oceny.** Silnik porównuje wpisaną odpowiedź z hasłem według reguł języka.
  Zgodność daje „wiem”, drobne potknięcie (znak diakrytyczny, jedna litera,
  rodzajnik, wielkość litery, inna forma słowa) daje „prawie”, pozostałe
  odpowiedzi dają „nie wiem”. Ocena „znałem” przy pierwszym pokazaniu
  oznacza słowo znane przed kursem.
- **Harmonogram.** FSRS-6 wyznacza kolejną powtórkę dla trwałości 90%, czyli
  dla wartości stosowanej w kursach SuperMemo. Wyniki zgadzają się
  z biblioteką py-fsrs 6.3.3.
- **Kilka języków.** Silnik dzieli dzienny limit nowych słów między języki
  według wag, przeplata języki w jednej sesji, wprowadza jedno pojęcie
  w dwóch językach w odstępie co najmniej trzech dni i rozpoznaje odpowiedź
  udzieloną w innym z uczonych języków.
- **Plan.** Języki, poziomy, wagi, liczba nowych słów, dni wolne, docelowa
  trwałość i kolejność języków są ustawieniami planu. Każda zmiana planu
  i własnych słów powstaje najpierw jako podgląd i trafia do folderu nauki
  dopiero po potwierdzeniu.

## Kursy

| Język | A1 | A2 | B1 | B2 |
|---|---|---|---|---|
| angielski | 955 | 1081 | 1743 | 1840 |
| niemiecki | 949 | 1087 | 1679 | 1674 |
| hiszpański | 947 | 1073 | 1714 | 1728 |
| francuski | 932 | 1082 | 1708 | 1727 |

Kursy powstały z otwartych danych: poziomy z listy CEFR-J, tłumaczenia,
rodzaj, formy i wymowa z Wikisłownika (przez kaikki.org), kolejność z danych
wordfreq, a zdania przykładowe z polskimi tłumaczeniami z Tatoeby. Claude
Sonnet 5.5 przejrzał znaczenia i odpowiedniki wszystkich 6600 pojęć. W próbie
1200 haseł błędne znaczenie, odpowiednik lub rodzaj miało 1,2% haseł. Własne
słowa z dowolnego tekstu uzupełniają kurs.

## Instalacja

Wtyczka w Claude Code:

```
/plugin install vocabbot --marketplace dithiothreitol/vocabbot
```

Wtyczka w Codex CLI:

```
codex plugin marketplace add dithiothreitol/vocabbot
codex plugin add vocabbot@vocabbot
```

Program w terminalu, przez uv:

```
uv tool install vocabbot
vocabbot init --lang de:a1-a2 --lang es:a1-a2 --new 10
vocabbot drill
```

Jedynym wymaganiem jest Python 3.10 lub nowszy. [QUICKSTART.pl.md](QUICKSTART.pl.md)
prowadzi przez pierwszy tydzień nauki.

## Dokumenty

- [QUICKSTART.pl.md](QUICKSTART.pl.md): instalacja, konfiguracja i codzienna sesja.
- [plugin/README.pl.md](plugin/README.pl.md) i [plugin/PRIVACY.pl.md](plugin/PRIVACY.pl.md): wtyczka i miejsce przechowywania danych.
- [docs/architecture.md](docs/architecture.md): silnik, gwarancje i kontrole (po angielsku).
- [docs/development-plan.pl.md](docs/development-plan.pl.md): plan etapów i ich wyniki.
- [docs/pilot.pl.md](docs/pilot.pl.md): protokół pilotażu przed wersją 1.0.
- [CHANGELOG.md](CHANGELOG.md): wersje (po angielsku).

## Rozwój

```
uv sync
uv run ruff format --check && uv run ruff check && uv run mypy && uv run pytest
uv run python scripts/build.py skills      # silnik i reguły w każdej umiejętności
uv run python scripts/validate.py          # kontrole repozytorium
uv run python scripts/session_test.py --check
```

Plik `CLAUDE.md` opisuje układ repozytorium i zasady zmian, a katalog
`tools/courses/` zawiera potok budowy kursów.

## Licencja

Kod jest udostępniony na licencji Apache-2.0 ([LICENSE](LICENSE)), przy czym
harmonogram jest przeniesieniem biblioteki py-fsrs (MIT). Kursy mają licencję
CC BY-SA 4.0. Plik [NOTICE](NOTICE) wymienia źródła i ich warunki.
