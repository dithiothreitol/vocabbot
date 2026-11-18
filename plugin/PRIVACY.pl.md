# Prywatność

[English](PRIVACY.md) · **Polski**

VocabBot to zestaw instrukcji oraz jeden lokalny program z kursami. Nie
potrzebuje serwera ani konta i nie ma analityki, a program niczego nie
wysyła przez sieć, chyba że uczący się połączy folder z kontem na serwerze
VocabBota.

## Gdzie są przechowywane dane uczącego się

- **Folder nauki.** Plan, dziennik odpowiedzi (z odpowiedziami w wpisanej
  postaci), własne słowa, notatki do słów, zgłoszenia błędów, słowa odłożone
  i lista zatwierdzonych zmian
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
- **Konto, gdy uczący się je połączy.** Po `vocabbot login` folder
  synchronizuje się z kontem na serwerze wybranym przez uczącego się: trafiają
  tam wiersze dziennika z wpisanymi odpowiedziami, notatki, własne słowa,
  zgłoszenia i zmiany planu, a wiersze konta wracają do folderu. Program
  przechowuje swoje tokeny w pliku `~/.vocabbot/credentials.json` dostępnym
  tylko dla właściciela, a `vocabbot logout` kończy połączenie. Serwer
  przechowuje dane tak, jak opisuje jego strona prywatności (`/privacy`).

## Czego VocabBot nie zbiera

VocabBot nie prosi o imię, adres ani inne dane osobowe; konto na serwerze
może przechowywać adres e-mail do odzyskania hasła, wyłącznie jako skrót
i tylko wtedy, gdy uczący się go poda. Dziennik zawiera odpowiedzi na
pytania o słowa wraz z czasem ich udzielenia.

## Usunięcie danych

Usunięcie folderu nauki oraz folderu `~/.vocabbot/` usuwa wszystkie dane
VocabBota, ponieważ poza nimi VocabBot nie tworzy żadnych kopii, z wyjątkiem
konta połączonego przez uczącego się: strona konta na jego serwerze usuwa
konto razem ze wszystkimi danymi.
