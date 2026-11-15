# Szybki start

[English](QUICKSTART.md) · **Polski**

## 1. Instalacja

**Claude Code** (terminal, IDE, karta Code w aplikacji desktopowej):

```
/plugin install vocabbot --marketplace dithiothreitol/vocabbot
```

**Codex CLI**:

```
codex plugin marketplace add dithiothreitol/vocabbot
codex plugin add vocabbot@vocabbot
```

**Cowork** w aplikacji desktopowej Claude: marketplace
`dithiothreitol/vocabbot` albo plik `vocabbot.plugin` z wydania (Add >
Upload plugin), a następnie folder przeznaczony na naukę otwarty w Coworku.

**Sam terminal**: `uv tool install vocabbot` (albo `pipx install vocabbot`).

Każda droga wymaga Pythona 3.10 lub nowszego. W Windows polecenie
`python --version` pokazuje działający interpreter, ponieważ `python3` bywa
aliasem Sklepu Microsoft, który niczego nie uruchamia.

## 2. Konfiguracja

Konfigurację uruchamia prośba „skonfiguruj VocabBota” albo polecenie
`/vocabbot:vocab-start`. VocabBot pyta o:

- języki, od jednego do trzech spośród angielskiego, niemieckiego,
  hiszpańskiego, francuskiego i włoskiego;
- poziom każdego języka: A1–A2 dla początkujących, B1–B2 dla
  średniozaawansowanych albo krótki test poziomujący w razie wątpliwości;
- liczbę nowych słów dziennie dla wszystkich języków razem (domyślnie 15)
  oraz dni wolne;
- folder nauki (domyślnie `~/VocabBot`; folder synchronizowany, na przykład
  w OneDrive, pozwala uczyć się na dwóch komputerach).

VocabBot pokazuje plan jako podgląd, zapisuje go po potwierdzeniu i podaje
prognozę: minuty dziennie oraz daty wprowadzenia całych poziomów.

W terminalu ta sama konfiguracja mieści się w dwóch poleceniach:

```
vocabbot quiz --lang de
vocabbot init --lang de:a1-a2 --lang es:b1-b2:2 --new 15 --set days_off=sun
```

## 3. Codzienna sesja

Sesję w czacie rozpoczyna „sesja” albo „uczymy się”, a w terminalu polecenie
`vocabbot drill`. Obie drogi korzystają z tego samego folderu i tej samej
kolejności, więc sesja rozpoczęta w jednym miejscu może skończyć się
w drugim.

- Nowe słowa pojawiają się najpierw w całości. Słowa znane przed kursem
  dostają ocenę „znałem” i nie zużywają dziennego limitu.
- Pytanie pokazuje polskie znaczenie i zdanie z luką. Rzeczowniki
  niemieckie, hiszpańskie, francuskie i włoskie wymagają rodzajnika. Znak „?” albo
  pusta odpowiedź oznacza „nie wiem”.
- Silnik ocenia każdą odpowiedź od razu: wiem, prawie (z opisem potknięcia)
  albo nie wiem. Słowa z błędną odpowiedzią wracają pod koniec sesji.
- W terminalu poprawna odpowiedź zapisuje się od razu i zwija się do
  jednego wiersza. Po pomyłce sesja pokazuje Twoją odpowiedź obok poprawnej
  z zaznaczonymi różnicami; Enter zapisuje proponowaną ocenę, a klawisze 1,
  2 i 3 wybierają inną. Podczas wprowadzania nowych słów klawisz z oznacza
  słowo jako znane. Przy odpowiedzi polecenie `/znam` oznacza nowe słowo jako
  znane, `/cofnij` zmienia ocenę poprzedniej odpowiedzi, `/pomoc` pokazuje
  polecenia, a `/koniec` (albo q przy wyborze klawisza) kończy sesję
  z zachowaniem postępu.
- `vocabbot` bez polecenia pokazuje plan dnia, a Enter zaczyna sesję.
- Ocena zmienia się wyłącznie na wyraźną prośbę („to była literówka,
  zalicz”).

## 4. Własne słowa

Prośba „Dodaj do niemieckiego: der Feierabend = koniec dnia pracy”, wklejony
tekst albo zdjęcie strony podręcznika. VocabBot pokazuje, co doda: własne
słowa, słowa z kursu przesunięte na początek kolejki oraz słowa pominięte,
ponieważ są już w nauce. Zapis następuje dopiero po potwierdzeniu.

## 5. Postępy i plan

- „Jak mi idzie?”, „przegląd tygodnia” albo polecenia `vocabbot status`
  i `vocabbot forecast`.
- „Mniej nowych słów”, „dodaj francuski”, „wstrzymaj hiszpański”, „niedziele
  wolne” albo `vocabbot plan set new_per_day=10`. Każda zmiana powstaje
  najpierw jako podgląd.
- „Wyjaśnij mi słowo …”, „ciągle mylę …”: trener wyjaśnia słowa, proponuje
  skojarzenia i zestawia słowa z różnych języków.
- Po dwóch tygodniach plan uwzględnia Twoją obecność: terminy omijają dni
  tygodnia, w które zwykle się nie uczysz, liczba nowych słów mieści się
  w Twoim zwykłym czasie, a dzień przed takim dniem proponuje powtórki
  przed terminem. Ustawienie `presence=off` w planie to wyłącza.
- `vocabbot replay` porównuje harmonogram dopasowany do Twojego dziennika
  z FSRS-6 na późniejszej części dziennika, a `vocabbot plan fit` zapisuje
  dopasowane parametry języka tylko tam, gdzie przewidują lepiej, i dopiero
  po potwierdzeniu.

## 6. Dwa komputery

Folder nauki w folderze synchronizowanym działa na obu komputerach. Na
drugim komputerze polecenie `vocabbot use <folder>` raz wskazuje go
programowi, a opcja `--learner <folder>` albo zmienna `VOCABBOT_HOME` robią
to samo dla jednego polecenia lub jednej powłoki. Kopie konfliktowe
dziennika, które tworzy synchronizacja,
wykrywa `vocabbot doctor`, a `vocabbot doctor --merge` łączy je po
potwierdzeniu; połączony dziennik daje ten sam harmonogram.

## 7. Usunięcie

Usunięcie folderu nauki i folderu `~/.vocabbot/` usuwa dane. Wtyczkę
odinstalowuje `/plugin uninstall vocabbot` (Claude Code) albo
`codex plugin remove vocabbot`, a program `uv tool uninstall vocabbot`.
