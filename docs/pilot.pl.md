# Protokół pilotażu

[English](pilot.md) · **Polski**

Pilotaż jest ostatnim warunkiem wersji 1.0 (rozdział 1 planu, warunek 7):
dwa tygodnie codziennej nauki w dwóch lub trzech językach, w czacie
i w terminalu, kończą się bez otwartego błędu blokującego. Pilotaż odbywa
się na wersji 1.0.0-rc.1.

## Przed pierwszą sesją

- **VocabBot 1.0.0-rc.1** zainstalowany jako wtyczka w Claude Code (oraz
  w Codex CLI, jeśli pilotaż obejmuje Codexa) i jako program `vocabbot`
  (`uv tool install` z repozytorium). Wersję pokazuje `vocabbot --version`.
- **Folder nauki poza repozytorium**, najlepiej w folderze synchronizowanym,
  na przykład `OneDrive/VocabBot`. Folder nauki nigdy nie trafia do
  repozytorium.
- **Python 3.10 lub nowszy** w ścieżce PATH; `python --version` odpowiada.
- **Ten plik i plik notatek** obok siebie, według szablonu poniżej.

## Scenariusze

| # | Scenariusz | Prośba albo polecenie | Co sprawdzić |
|---|---|---|---|
| 1 | Konfiguracja z testem | „skonfiguruj VocabBota”, test dla jednego języka | test pokazuje pytania bez odpowiedzi; plan powstaje po jednym potwierdzeniu; prognoza pochodzi z silnika |
| 2 | Sesja w czacie | „sesja” przez trzy dni | partie po około 10 kart; żadna odpowiedź przed oceną; utrwalanie na końcu |
| 3 | Sesja w terminalu | `vocabbot drill` przez trzy dni | wpisywanie ä, ß, ñ, é, ç; klawisze ocen; przerwanie klawiszem q |
| 4 | Zmiana drogi w trakcie dnia | początek w czacie, dokończenie w terminalu | ta sama kolejność, bez powtórzonych kart |
| 5 | Słowo znane przed kursem | „to słowo znałem” | ocena „znałem” tylko przy pierwszym pokazaniu; limit nowych słów bez zmian |
| 6 | Zmiana oceny | „to była literówka, zalicz” | zmiana tylko tej karty; wiersz oznaczony w dzienniku |
| 7 | Własne słowa | tekst albo zdjęcie strony | podgląd z podziałem na własne, przesunięte i pominięte; zapis po potwierdzeniu |
| 8 | Zgłoszenie błędu w haśle | „to tłumaczenie jest złe” | karta znika z kolejki do wycofania zgłoszenia |
| 9 | Zmiana planu | „mniej nowych słów”, „dodaj trzeci język” | podgląd, potwierdzenie, nowa prognoza |
| 10 | Trener | „przegląd tygodnia”, „ciągle mylę …” | liczby zgodne ze `vocabbot status`; treść modelu oznaczona jako wygenerowana |
| 11 | Dzień wolny i zaległości | dzień bez nauki, potem sesja | zaległe powtórki następnego dnia; prognoza się aktualizuje |
| 12 | Dwa komputery | ten sam folder na drugim komputerze (`vocabbot use`) | wspólny stan; `vocabbot doctor` wykrywa kopie konfliktowe i łączy je po potwierdzeniu |

## Mierniki

| Miernik | Cel | Pomiar |
|---|---|---|
| Odpowiedzi pokazane przed oceną | 0 | obserwacja każdej partii w czacie |
| Oceny niepochodzące z silnika | 0 | `vocabbot status` (udział zmienionych ocen) i własne zmiany |
| Zmiany bez potwierdzenia | 0 | każdy wiersz `log/decisions.md` odpowiada Twojemu potwierdzeniu |
| Błędne hasła | zapisane | zgłoszenia `flag` z notatką; cel z Etapu 2 to najwyżej 3% dla A1–A2 i 5% dla B1–B2 |
| Minuty dziennie | zapisane | porównanie z prognozą `vocabbot forecast` |
| Trwałość z 30 dni | blisko 90% | `vocabbot status` po dwóch tygodniach |

## Błędy

**Blokujące:** odpowiedź pokazana przed oceną, ocena lub termin spoza
silnika, zapis bez potwierdzenia, utrata albo uszkodzenie dziennika, awaria
przerywająca sesję. Każdy taki błąd zostaje odtworzony na danych
syntetycznych, dostaje test i poprawkę przed wersją 1.0.

**Nieblokujące:** sformułowania, kolejność informacji, błędne hasło
pojedynczego słowa, wolne działanie. Każdy zostaje zapisany i poprawiony,
gdy poprawka jest tania; błędne hasła wracają do potoku kursów.

## Szablon notatek

Notatki opisują przebieg własnymi słowami i nie zawierają danych osobowych.

```
Scenariusz: 2 · sesja w czacie
Data: <dzień> · Gospodarz: Claude Code <wersja> · Model: <model>
O co poprosiłem:
Co się stało:
Czego oczekiwałem:
Blokujący: tak / nie
Karta lub hasło (identyfikator z wyniku):
```

## Koniec pilotażu

Pilotaż kończy się po dwóch tygodniach nauki, gdy wszystkie scenariusze
zostały przeprowadzone (scenariusz, który nie pasuje, dostaje notatkę), żaden
błąd blokujący nie pozostaje otwarty, a mierniki są zapisane. Notatki
otwierają prace nad wersją 1.0.
