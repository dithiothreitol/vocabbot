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

- Nowe słowo pojawia się od razu jako pytanie, tak jak w SuperMemo. Słowo,
  które znasz, wpisujesz: poprawna pierwsza odpowiedź oznacza słowo znane
  przed kursem i takie słowo zostawia dzienny limit bez zmian. Przy słowie
  jeszcze nieznanym wpisujesz „?”: wynik pokazuje słowo z formami, wymową
  i przykładem, a słowo wraca tego samego dnia w utrwalaniu. Ustawienie
  planu `new_words=show` pokazuje każde nowe słowo przed pytaniem.
- Pytanie pokazuje polskie znaczenie i zdanie z luką. Rzeczowniki
  niemieckie, hiszpańskie, francuskie i włoskie wymagają rodzajnika. Zamiast
  wpisywania możesz napisać „pokaż”, zobaczyć odpowiedź i ocenić się: wiem,
  prawie albo nie wiem. Znak „?” oznacza „nie wiem”. W terminalu sam Enter
  pokazuje odpowiedź do własnej oceny.
- Silnik ocenia każdą odpowiedź od razu: wiem, prawie (z opisem potknięcia)
  albo nie wiem. Słowa z błędną odpowiedzią wracają pod koniec sesji.
- W terminalu poprawna odpowiedź zapisuje się od razu i zwija się do
  jednego wiersza. Po pomyłce sesja pokazuje Twoją odpowiedź obok poprawnej
  z zaznaczonymi różnicami; Enter zapisuje proponowaną ocenę, a klawisze 1,
  2 i 3 wybierają inną (utrwalanie ma dwie oceny, 1 i 3). Przy odpowiedzi polecenie `/znam` oznacza nowe słowo jako
  znane, `/cofnij` zmienia ocenę poprzedniej odpowiedzi, `/pomoc` pokazuje
  polecenia, a `/koniec` (albo q przy wyborze klawisza) kończy sesję
  z zachowaniem postępu.
- Wybierasz, czego się uczysz. W czacie hasło „nowe” przenosi sesję do
  nowych słów przy czekających powtórkach, „powtórki” wraca do powtórek,
  „więcej słów” dodaje nowe słowa ponad dzienną liczbę, „jeszcze powtórki”
  zaczyna następną turę powtórek. W terminalu te same wybory dają polecenia
  `/nowe`, `/powtorki`, `/utrwalanie` i `/wiecej`, a po liście dnia sesja
  proponuje klawisze n (5 kolejnych nowych słów), p (następna tura 10
  powtórek) i Enter (koniec). Powtórki odłożone na później zachowują termin
  i otwierają następny dzień.
- Karta ma więcej możliwości, tak jak w SuperMemo. Tłumaczenie zdania podaje
  hasło „tłumaczenie” (w terminalu `/t`, na karcie przycisk). Ustawienie
  planu `answer_mode=type` zostawia samo wpisywanie, a
  `sentence_translation=shown` pokazuje każde tłumaczenie od razu. Hasło „nie chcę tego słowa” (w terminalu
  `/pomin`) odkłada słowo, a „przywróć słowo …” je przywraca. Hasło „zapisz
  notatkę: …” (w terminalu `/notatka …` po odpowiedzi) zapisuje Twoją
  notatkę, którą odtąd widać przy odpowiedzi na to słowo.
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

## 6. Kilka urządzeń

Zalecaną drogą jest konto na serwerze VocabBota, które przechowuje zapis
nauki dla każdego urządzenia:

- **Komputer.** `vocabbot login` loguje program przez przeglądarkę i łączy
  folder nauki z kontem. Gdy folder i konto mają różne plany, wybierasz
  opcją `--plan folder` albo `--plan account`; połączenie jest podglądem
  z liczbą odpowiedzi po obu stronach i zapisuje się po potwierdzeniu. Na
  komputerze bez folderu `vocabbot login` pobiera konto do `~/VocabBot`. Bez
  przeglądarki na tym komputerze `vocabbot login --code` pokazuje kod do
  potwierdzenia w telefonie.
- **Na co dzień.** Folder synchronizuje się sam: pobiera przed `today`,
  `next`, `drill` i `status`, a wysyła po każdej odpowiedzi. Bez sieci
  odpowiedzi czekają w folderze; `vocabbot status` pokazuje ostatnią
  synchronizację i to, co czeka, a `vocabbot sync` synchronizuje od razu.
- **Telefon.** Aplikacja czatu połączona z serwerem albo strona sesji
  serwera (`https://<serwer>/app/`) w przeglądarce, którą dodasz do ekranu
  głównego. Sesja zaczęta na jednym urządzeniu toczy się dalej na innym od
  tej samej karty.
- **Strona konta** (`/account`) pokazuje połączone aplikacje i komputery
  i je odłącza, pobiera dane jako archiwum zip (`vocabbot import <plik.zip>`
  otwiera je jako folder), przechowuje opcjonalny adres e-mail do
  odzyskania hasła i usuwa konto. `vocabbot logout` kończy połączenie
  komputera.

Bez konta folder nauki w folderze synchronizowanym działa na obu
komputerach. Na drugim komputerze polecenie `vocabbot use <folder>` raz
wskazuje go programowi, a opcja `--learner <folder>` albo zmienna
`VOCABBOT_HOME` robią to samo dla jednego polecenia lub jednej powłoki.
Wiersze kopii konfliktowych, które tworzy synchronizacja dysku, liczą się od
razu, a `vocabbot doctor --merge` porządkuje pliki po potwierdzeniu.

## 7. Usunięcie

Usunięcie folderu nauki i folderu `~/.vocabbot/` usuwa dane. Wtyczkę
odinstalowuje `/plugin uninstall vocabbot` (Claude Code) albo
`codex plugin remove vocabbot`, a program `uv tool uninstall vocabbot`.
