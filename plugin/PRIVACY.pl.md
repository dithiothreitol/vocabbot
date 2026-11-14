# Prywatność

[English](PRIVACY.md) · **Polski**

VocabBot to zestaw instrukcji oraz jeden lokalny program z kursami. Nie ma
serwera, konta ani analityki, a program niczego nie wysyła przez sieć.

## Gdzie są przechowywane dane uczącego się

- **Folder nauki.** Plan, dziennik odpowiedzi (z odpowiedziami w wpisanej
  postaci), własne słowa, zgłoszenia błędów i lista zatwierdzonych zmian
  znajdują się w folderze wybranym przez uczącego się. VocabBot czyta
  i zapisuje wyłącznie tam oraz w dwóch miejscach folderu `~/.vocabbot/`:
  w pliku `config.json` ze ścieżką folderu nauki i w podfolderze `pending/`,
  gdzie podgląd nowego folderu czeka najwyżej 30 minut na potwierdzenie.
  Podglądy późniejszych zmian czekają w samym folderze nauki
  (`registers/.pending/`), również najwyżej 30 minut.
- **Czat.** W Claude i w Codexie karty, odpowiedzi uczącego się i wyniki
  silnika przechodzą przez model gospodarza na własnym koncie uczącego się
  i na warunkach tego konta.
- **Terminal.** Program `vocabbot` działa bez dostępu do sieci.

## Czego VocabBot nie zbiera

VocabBot nie prosi o imię, adres, e-mail ani inne dane osobowe. Dziennik
zawiera odpowiedzi na pytania o słowa wraz z czasem ich udzielenia.

## Usunięcie danych

Usunięcie folderu nauki oraz folderu `~/.vocabbot/` usuwa wszystkie dane
VocabBota, ponieważ poza nimi VocabBot nie tworzy żadnych kopii.
