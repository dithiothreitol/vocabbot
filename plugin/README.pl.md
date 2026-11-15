# VocabBot

[English](README.md) · **Polski**

VocabBot uczy słownictwa w jednym, dwóch lub trzech językach równocześnie:
angielskim, niemieckim, hiszpańskim i francuskim, od poziomu A1 do B2, dla
osób, których językiem bazowym jest polski. Nowe słowa pojawiają się według
częstości, każdą wpisaną odpowiedź ocenia silnik, a każda karta wraca w dniu
wyznaczonym przez algorytm FSRS-6, gdy uczący się pamięta jeszcze około
dziewięciu na dziesięć słów.

## Umiejętności

| Umiejętność | Zakres |
|---|---|
| `vocab-start` | Konfiguracja: języki, poziomy, liczba nowych słów dziennie, test poziomujący, folder nauki. Później zmiany planu, prognoza, kontrola folderu i program w terminalu. |
| `vocab-session` | Codzienna sesja: powtórki, nowe słowa i utrwalanie słów z błędną odpowiedzią, po jednej karcie jak w SuperMemo (albo po kilka, według ustawienia `batch` w planie). |
| `vocab-coach` | Wyjaśnienia, skojarzenia do trudnych słów, zestawienia słów mylonych między językami, ćwiczenie w zdaniach i przegląd tygodnia. |
| `vocab-words` | Własne słowa z tekstu, listy lub zdjęcia strony, przesunięcie słów z kursu na początek kolejki, zgłoszenia błędów w hasłach. |

## Instalacja

Claude Code:

```
/plugin install vocabbot --marketplace dithiothreitol/vocabbot
```

albo w dwóch krokach: `/plugin marketplace add dithiothreitol/vocabbot`,
potem `/plugin install vocabbot@vocabbot`. Konfigurację uruchamia prośba
„skonfiguruj VocabBota” albo polecenie `/vocabbot:vocab-start`.

Codex CLI:

```
codex plugin marketplace add dithiothreitol/vocabbot
codex plugin add vocabbot@vocabbot
```

## Wymagania

Python 3.10 lub nowszy na komputerze albo w piaskownicy gospodarza. Każda
umiejętność niesie silnik ze wszystkimi kursami w jednym pliku,
`bin/vocabbot.pyz`, który nie wymaga żadnego innego pakietu.

## Potwierdzenia

Każda zmiana planu i własnych słów pojawia się najpierw jako podgląd i trafia
do folderu nauki dopiero po potwierdzeniu. W Claude Code i w Coworku hook
wtyczki dodatkowo pyta w oknie zgody gospodarza, zanim silnik zapisze zmianę.

## Dane uczącego się

Plan, dziennik odpowiedzi i własne słowa zostają w folderze wybranym przez
uczącego się; [PRIVACY.pl.md](PRIVACY.pl.md) opisuje, co i gdzie jest
przechowywane.

## Licencja

Kod jest udostępniony na licencji Apache-2.0 ([LICENSE](LICENSE)). Kursy mają
licencję CC BY-SA 4.0 i powstały z list CEFR-J, Wikisłownika (przez
kaikki.org), danych wordfreq oraz zdań Tatoeby; [NOTICE](NOTICE) wymienia
źródła i ich warunki.
