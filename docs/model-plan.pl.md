# Plan modelu harmonogramu powtórek

Stan: 2026-11-15. Plan powstał 15.11.2026 i czeka na Twoją akceptację; żaden
etap nie jest rozpoczęty. Wykonane dotąd: odczyt licencji zbiorów Duolingo
i MaiMemo oraz statystyki zbioru Duolingo (rozdział 2.5). Rodzina modeli nie
ma jeszcze nazwy; nazwa robocza to `vocabbot-model`. Model dostanie osobne
repozytorium i wtedy ten plik do niego przejdzie. Wersji angielskiej jeszcze
nie ma. Etapy mają litery A–H, żeby nie myliły się z etapami VocabBota
z `development-plan.pl.md`.

---

## 1. Cel i definicja ukończenia

Celem jest własny, wyspecjalizowany model, który wspomaga i przyspiesza naukę
słownictwa opartą na powtórkach. Osoba ucząca się kilku języków naraz ma
dzięki niemu pamiętać więcej słów na minutę nauki niż przy FSRS-6. Model
zaczyna od statystycznego uczącego się i z każdą sesją przesuwa się ku
historii konkretnej osoby: jej postępom, sposobowi nauki, systematyczności
i tempu zapamiętywania. Rodzina wag w kilku rozmiarach jest opublikowana na
Hugging Face.

Model nie prowadzi rozmowy i nie pisze tekstu. Dostaje stan uczącego się
i pytania o znanym kształcie odpowiedzi, a zwraca prawdopodobieństwa. Decyzję
o terminie powtórki i o planie dnia podejmuje silnik VocabBota.

Wersja 1 modelu jest ukończona, gdy spełnione są wszystkie warunki:

1. Model przewiduje wynik powtórki trafniej niż oba punkty odniesienia
   (rozdział 5.5) na osobach, których nie widział w treningu.
2. Przewaga jest widoczna przy nowych słowach i u nowych osób oraz utrzymuje
   się po 90 dniach historii.
3. Model przewiduje obecność uczącego się trafniej niż statystyka jego
   ostatnich tygodni.
4. Przewaga dotyczy także osób uczących się dwóch i więcej języków.
5. Test na uczących się potwierdza, że plan oparty na modelu daje więcej
   pamiętanych słów na minutę nauki niż FSRS-6.
6. Co najmniej trzy rozmiary wag są opublikowane z kartą modelu, plikami
   kalibracji i skryptami, które odtwarzają podane wyniki.
7. VocabBot korzysta z modelu jako opcji, a bez niego liczy terminy tak jak
   dziś.

---

## 2. Ustalenia wejściowe

### 2.1 Twoje decyzje z 15.11.2026

| Pytanie | Decyzja |
|---|---|
| Rodzaj modelu | własny model wyspecjalizowany w nauce słownictwa i powtórkach; Jev i basal są przykładami podejścia, a nie podstawą do klonowania ani strojenia |
| Zadanie | planowanie powtórek przy nauce kilku języków naraz, lepsze niż w standardowych algorytmach |
| Dostosowanie | do aktualnych postępów, sposobu nauki, systematyczności i tempa zapamiętywania uczącego się |
| Punkt startu | ogólne statystyki i typowe zachowania statystycznego uczącego się; potem dostosowanie na podstawie gromadzonej historii |
| Publikacja | Hugging Face, kilka rozmiarów wag |
| Licencja pierwszego wydania | badawcza, CC BY-NC 4.0 |
| Repozytorium | osobne, poza VocabBotem |
| Sprzęt | na początek bez kosztów: laptop oraz Kaggle |

Decyzje otwarte opisuje rozdział 11.

### 2.2 Wzorce podejścia

| Wzorzec | Co z niego wynika |
|---|---|
| Jev (TypeSafe AI, wrzesień 2026) | model dostaje stan i pytania typowane, zwraca wybór albo wynik z prawdopodobieństwem w jednym przebiegu, bez pisania tekstu; wagi nie są publiczne |
| Kev (otwarty odpowiednik Jev) | adapter LoRA rzędu 16 i mała głowica odczytu na zamrożonej bazie Qwen3.5 w rozmiarach 0,8, 4 i 9 mld; według opisów ok. 12 tys. przykładów i ok. 95 USD za GPU |
| basal (Remek Kinas) | odpowiedź to rozkład po kodach opcji z jednego przebiegu; kalibracja temperaturą osobno dla typu pytania; rozmiary 1,5, 4,5 i 11 mld na Bieliku v3 oraz linia na Gemma 4 i Qwen3.5; najmniejszy model destylowany z największego; Apache-2.0; karta modelu podaje, że arytmetyka w jednym przebiegu jest słaba |

Z tych wzorców plan bierze technikę: pytania typowane, odczyt z logitów
opcji, kalibrację i destylację. Format pytań, dane i wagi są własne.

### 2.3 Stan wiedzy o przewidywaniu pamięci

Publiczny benchmark srs-benchmark porównuje modele na 10 000 kolekcji Anki
(727 mln powtórek; ocena na 349,9 mln powtórek bez powtórek z tego samego
dnia). Log loss to błąd przewidywania, niższy jest lepszy.

| Model | Parametry | Log loss | AUC | Wejście |
|---|---|---|---|---|
| FSRS-6 (jest w VocabBocie) | 21 | 0,3460 | 0,7034 | historia karty; parametry dopasowane do osoby |
| FSRS-7 | 34 | 0,3401 | 0,7167 | historia karty |
| GRU | 503 | 0,3328 | 0,7324 | historia karty |
| LSTM | 8 869 | 0,3332 | 0,7329 | historia karty i czas odpowiedzi |
| RWKV-Curve | 2,76 mln | 0,3193 | 0,7683 | strumień powtórek osoby, karty pokrewne, obciążenie dnia; bez dopasowania do osoby |
| RWKV-Instant | 2,76 mln | 0,2773 | 0,8329 | jak wyżej; przewiduje tylko w chwili powtórki |

Wnioski:

- Sama historia karty jest prawie wyczerpana: sieć na tych samych danych co
  FSRS-6 daje 4% niższy błąd.
- Zysk pochodzi z kontekstu. RWKV-Curve, który daje krzywą nadającą się do
  planowania, ma błąd niższy o 8%.
- Dostosowanie przez sam strumień powtórek działa: RWKV nie jest dopasowywany
  do osoby, a przewiduje trafniej niż FSRS-6 dopasowany do każdej osoby.
- Żaden model w benchmarku nie korzysta z treści kart, bo dane Anki jej nie
  zawierają.

Pozostałe ustalenia z literatury:

- KAR3L (model z treścią kart) wypadł w badaniu z ludźmi porównywalnie
  z FSRS; LECTOR zyskał 1,8 punktu procentowego w symulacji.
- NTKT i CLST podają, że modele językowe strojone do przewidywania odpowiedzi
  uczniów wygrywają z klasycznymi sieciami, zwłaszcza dla nowych osób
  i nowych pytań. Badania dotyczą innych przedmiotów niż słownictwo.
- Praca z NLP4CALL 2026 szacuje, że samo słowo wyjaśnia najwyżej ok. 15%
  trudności; reszta zależy od tego, co uczący się już zna.
- Badania nad trzecim językiem pokazują, że słowa pokrewne wchodzą szybciej,
  a wcześniej poznany język obcy przeszkadza mocniej niż ojczysty.

Lepsze przewidywanie nie oznacza jeszcze szybszej nauki. Żadne znalezione
badanie nie mierzy planowania dla osoby nieregularnej ani dla kilku języków
naraz.

### 2.4 Publiczne dane

| Zbiór | Rozmiar | Zawartość | Licencja | Czego brakuje |
|---|---|---|---|---|
| Anki 10k (`open-spaced-repetition/anki-revlogs-10k`) | 10 000 osób, 727 mln powtórek, 15,7 GB | numer dnia, ocena 1–4, stan karty, czas odpowiedzi, odstęp w dniach i sekundach, karta, notatka, talia | własna, za bramką; nieodczytana | treści kart, dni tygodnia |
| MaiMemo (doi:10.7910/DVN/VAGUL0) | 220 mln wierszy; pliki 1,7 GB i 0,8 GB | pisownia słowa, ciąg odstępów i wyników, odstęp, wynik; słowa angielskie | CC BY-NC 4.0 | innych języków, profilu osoby |
| Duolingo, regresja półtrwania (doi:10.7910/DVN/N8XJME) | 12 854 226 wierszy, 115 222 osoby, 13 dni (28.02–12.03.2013) | słowo z opisem gramatycznym, język nauki i język interfejsu, odstęp od poprzedniej powtórki, liczniki wcześniejszych i bieżących odpowiedzi | CC BY-NC 4.0 | ciągu odstępów, długich historii, polskiej bazy |
| Duolingo SLAM 2018 (doi:10.7910/DVN/8SWHNO) | ponad 6 000 osób, pierwsze 30 dni nauki | błędy na poziomie słów w zdaniu; angielski, hiszpański, francuski | do sprawdzenia | długich historii; zbiór opcjonalny |
| Dziennik VocabBota | ok. 40 tys. powtórek na osobę rocznie | polska baza, wpisana odpowiedź oceniona przez silnik, klasa błędu, czas, język, rodzina pojęcia | własny, po zgodzie uczącego się | liczby osób: dziś jest jedna |

Pary języków w Duolingo (język nauki ← język interfejsu): angielski ←
hiszpański 3,64 mln wierszy, hiszpański ← angielski 3,41 mln, francuski ←
angielski 1,87 mln, niemiecki ← angielski 1,45 mln, angielski ← portugalski
0,95 mln, włoski ← angielski 0,79 mln, angielski ← włoski 0,42 mln,
portugalski ← angielski 0,31 mln.

Kilku języków naraz uczy się w Duolingo 2 849 osób (2,5%), w tym 336 osób
trzech lub więcej. Mają 821 039 wierszy (6,4%), a 2 017 z nich ćwiczyło dwa
języki tego samego dnia. Najczęstsze pary to hiszpański z francuskim (660
osób), niemiecki z francuskim (484) i niemiecki z hiszpańskim (460), czyli
języki VocabBota.

Na zbiorze Duolingo nie da się policzyć FSRS-6, bo ma tylko liczniki
wcześniejszych odpowiedzi. Punktem odniesienia jest tam regresja półtrwania,
czyli model samego Duolingo. FSRS-6 da się policzyć na MaiMemo i Anki.

### 2.5 Statystyczny uczący się w danych Duolingo

Statystyki policzone 15.11.2026 na całym zbiorze.

| Cecha | Wartość |
|---|---|
| Poprawne odpowiedzi | 90,5% |
| Rozrzut między osobami (51 359 osób z co najmniej 100 odpowiedziami) | 84,7% u najsłabszej dziesiątej części, 91,1% w środku, 96,2% u najlepszej dziesiątej części |
| Rozrzut między językami | od 89,3% (francuski) do 91,2% (włoski, portugalski) |
| Nauka tylko jednego dnia z 13 | 52,2% osób |
| Nauka w co najmniej 3, 5, 7 i 10 dniach z 13 | 27,8%, 11,6%, 5,1% i 1,3% osób |
| Typowa przerwa między dniami nauki (osoby z co najmniej 3 dniami) | 1,5 dnia; 46,7% tych osób uczy się zwykle dzień po dniu |

Rozrzut między osobami jest kilka razy większy niż między językami, więc
średnia nadaje się na start, a najwięcej daje dostosowanie do osoby.

Trafność według czasu od poprzedniej powtórki słowa:

| Czas | Trafność | Udział wierszy |
|---|---|---|
| do 10 minut | 91,9% | 26,5% |
| 10–60 minut | 91,1% | 12,1% |
| 1–24 godziny | 90,2% | 14,3% |
| 1–2 dni | 90,2% | 8,8% |
| 2–7 dni | 89,9% | 17,3% |
| 7–30 dni | 89,4% | 14,1% |
| ponad 30 dni | 88,2% | 6,8% |

Trafność spada tu tylko o 3,7 punktu, bo aplikacja pokazuje później te
słowa, które uczący się zna lepiej. Zapominania nie da się więc odczytać
z prostych średnich; opisuje je dopasowany model pamięci. Zwykłe statystyki
dobrze opisują zachowanie: rytm, długość sesji i poziom trafności.

Liczby pochodzą od użytkowników innej aplikacji, z innym językiem bazowym
i innym rodzajem ćwiczeń. W VocabBocie, gdzie odpowiedź się wpisuje,
trafność będzie zapewne niższa.

### 2.6 Sprzęt i narzędzia

| Zasób | Stan na 15.11.2026 |
|---|---|
| Laptop | karta NVIDIA GeForce RTX 5070 Laptop z 8 GB pamięci; 280 GB wolnego dysku |
| Kaggle | bezpłatnie karta P100 albo dwie T4 po 16 GB; ok. 30 godzin GPU tygodniowo, sesja do 12 godzin; źródła podają limity niejednolicie, a czas liczy się także przy bezczynnym notatniku |
| Hugging Face | brak konta zalogowanego w terminalu; narzędzie `hf` niezainstalowane |
| Kaggle w terminalu | narzędzie `kaggle` niezainstalowane, brak pliku z kluczem |

### 2.7 Powiązanie z Etapem 5 VocabBota

Etap 5 planu VocabBota („Harmonogram dopasowany do uczącego się”) daje
w samym silniku, na bibliotece standardowej:

- `vocabbot replay`, które odtwarza dziennik i porównuje każdy wariant
  z FSRS-6 miarami log loss, RMSE(bins) i AUC;
- pełne dopasowanie 21 parametrów FSRS-6 do dziennika, osobno dla każdego
  języka, z regularyzacją w stronę wartości domyślnych;
- plan dnia świadomy obecności, liczony ze zwykłych statystyk dziennika.

Plan modelu korzysta z tego trojako. `replay` jest stanowiskiem pomiarowym
na własnych dziennikach, a model wchodzi do niego jako kolejny wariant.
Dopasowane parametry są wejściem modelu. Plan świadomy obecności jest
punktem odniesienia dla planisty z etapu E. Etap B tego planu dodaje tylko
to, czego Etap 5 nie obejmuje.

### 2.8 Wersje Qwen na 15.11.2026

Stan sprawdzony w wykazie modeli organizacji Qwen na Hugging Face.

| Generacja | Data | Otwarte wagi | Licencja | Przydatność |
|---|---|---|---|---|
| Qwen3.5 | luty 2026 | 0,8, 2, 4 i 9 mld, każdy także w wersji `-Base`; do tego 27, 35, 122 i 397 mld | Apache-2.0 | drabinka rozmiarów rodziny |
| Qwen3.6 | kwiecień 2026 | 27 i 35 mld | Apache-2.0 | brak małych rozmiarów |
| Qwen3.8 | sierpień 2026 | 27 mld | Apache-2.0; warianty Flash-Next i 2.4T mają inną licencję | możliwy nauczyciel w etapie F |
| Qwen 4 | zapowiedź | brak; podgląd Max od 11.11.2026 działa tylko jako usługa | brak | do obserwacji |

Najnowsze małe modele Qwen to nadal Qwen3.5. Generacje 3.6 i 3.8 nie mają
rozmiarów poniżej 27 mld.

| Model | Parametry łącznie | Pamięć wag w BF16 |
|---|---|---|
| `Qwen/Qwen3.5-0.8B-Base` | 0,87 mld | ok. 1,7 GB |
| `Qwen/Qwen3.5-2B-Base` | 2,27 mld | ok. 4,5 GB |
| `Qwen/Qwen3.5-4B-Base` | 4,66 mld | ok. 9,3 GB |
| `Qwen/Qwen3.5-9B-Base` | 9,65 mld | ok. 19,3 GB |

Wersje `-Base` są tylko wstępnie wytrenowane i według karty modelu służą do
strojenia, a nie do rozmowy. Karta podaje, że tokeny sterujące są
przygotowane do strojenia LoRA bez strojenia osadzeń. Repozytoria nie mają
bramki.

Qwen3.5 obejmuje 201 języków i dialektów. Jest modelem z koderem obrazu,
z którego ten plan nie korzysta. Warstwy mają budowę hybrydową (Gated
DeltaNet i uwaga), inną niż w starszych modelach, dlatego etap D zaczyna
się od próby zgodności na laptopie.

---

## 3. Decyzje projektowe

| Decyzja | Uzasadnienie |
|---|---|
| Model powstaje z surowej otwartej bazy na licencji Apache-2.0 | ma być własny; Qwen3.5 ma rozmiary 0,8, 2, 4 i 9 mld, Bielik v3 ma 1,5, 4,5 i 11 mld |
| Z Qwen3.5 używamy wersji `-Base` | są przeznaczone do strojenia, a model nie prowadzi rozmowy |
| Pytania typowane, odpowiedź odczytana z logitów opcji w jednym przebiegu | odpowiedź nigdy nie wychodzi poza podane opcje i ma prawdopodobieństwo |
| Odpowiedzią na pytanie o harmonogram jest krzywa zapominania | jeden przebieg daje termin dla dowolnej docelowej trwałości |
| Liczby liczy silnik i podaje modelowi gotowe | modele językowe słabo liczą w jednym przebiegu; model uczy się tylko, kiedy FSRS się myli |
| Etykietą jest rzeczywisty wynik powtórki albo wynik planisty w symulacji | model uczony na opiniach dużego modelu mógłby najwyżej je naśladować |
| Dostosowanie do osoby przez stan wejściowy, bez osobnych wag dla osoby | tak działa najlepszy model w benchmarku; osobne wagi wymagają GPU u uczącego się i więcej danych, niż ma jedna osoba |
| Plan dnia układa silnik z przewidywań modelu | zasada VocabBota: skrypty dowodzą, model ocenia |
| Model jest osobnym pakietem, a silnik czyta plik z przewidywaniami | silnik zostaje na bibliotece standardowej i działa w piaskownicy gospodarza |
| Bez pliku z przewidywaniami silnik liczy terminy z FSRS-6 | model jest opcją; warunek 3 wersji 1.0 VocabBota obowiązuje w trybie domyślnym |
| Zmiana planu (liczba nowych słów, wagi języków) pozostaje propozycją z podglądem | warunek 5 wersji 1.0 VocabBota; terminy powtórek silnik zmienia bez pytania |
| Dwa punkty odniesienia i mała sieć na samej historii | model językowy ma dowieść, że wiedza o słowach daje zysk ponad to, co daje sama historia |
| Bramka po najmniejszym modelu | większe rozmiary mają sens dopiero wtedy, gdy najmniejszy wygrywa |
| Pierwsze wydanie badawcze, CC BY-NC 4.0; kod na Apache-2.0 | dane Duolingo i MaiMemo są na CC BY-NC 4.0; to, czy ograniczenie przechodzi na wagi, nie jest rozstrzygnięte prawnie |
| Surowych zbiorów nie rozpowszechniamy; publikujemy skrypty, które je pobierają i przetwarzają | licencje zbiorów; odtwarzalność |
| Trening zapisuje punkty kontrolne i daje się wznowić | sesje Kaggle mają limit czasu, a laptop bywa potrzebny do pracy |

---

## 4. Dane

### 4.1 Rekord zestawu

Rekord to stan uczącego się, pytania i odpowiedzi wzięte z dziennika. Nazwy
pól są propozycją; ustali je etap C.

```json
{"learner": {"base": "pl", "langs": ["en:b1", "de:a1", "es:a1"],
             "active_days_30": 19, "gap_days": 2, "backlog": 34},
 "card": {"lang": "de", "lemma": "Hund", "gloss": "pies", "pos": "noun", "gender": "m"},
 "history": [[0, "know"], [1, "know"], [4, "almost:gender"]],
 "family": [{"lang": "en", "lemma": "dog", "stability_days": 41}],
 "ask": {"recall_after_days": 9, "session_tomorrow": null},
 "truth": {"recall": 1, "session_tomorrow": 0}}
```

| Blok | Zawartość |
|---|---|
| `learner` | profil uczącego się z rozdziału 4.2 |
| `card` | język, hasło, polskie znaczenie, część mowy, rodzaj, poziom i miejsce w kursie |
| `history` | ostatnie powtórki karty: odstęp w dniach, ocena, klasa błędu, czas odpowiedzi; do tego stabilność, trudność i szansa przypomnienia policzone przez FSRS |
| `family` | karty tego samego pojęcia w innych językach i słowa mylone, z ich stanem pamięci |
| `ask` | pytania typowane z rozdziału 5.2 |
| `truth` | rzeczywisty wynik; `null` oznacza brak etykiety dla danego pytania |

Zbiory publiczne wypełniają tylko te bloki, do których mają dane. Rekord
z Anki nie ma treści karty, a rekord z Duolingo nie ma ciągu odstępów.

### 4.2 Profil uczącego się

Silnik liczy profil z dziennika po każdej sesji, w oknach 7, 30 i 90 dni.
Każda wartość ma liczbę obserwacji, z których powstała.

| Grupa | Co silnik liczy z dziennika | Na co wpływa |
|---|---|---|
| Aktualne postępy | poznane słowa w każdym języku i poziomie, zmierzona trwałość, zaległości | tempo nowych słów, podział między języki |
| Sposób nauki | pora i długość sesji, czas odpowiedzi, udział utrwalania, poprawki ocen, czat albo terminal | wielkość dziennej porcji |
| Systematyczność | dni aktywne w tygodniu, rytm tygodniowy, długość przerw, odsetek dokończonych sesji | powtórki przed spodziewaną przerwą, mniej nowych słów przy rosnących zaległościach |
| Tempo zapamiętywania | wynik pierwszej powtórki, przyrost odstępów, odsetek pomyłek, osobno dla każdego języka | odstęp każdej karty |

Dziennik VocabBota ma pola potrzebne do wszystkich czterech grup: czas,
dzień, kartę, język, ocenę, ocenę silnika, rodzaj wiersza, klasę błędu, czas
odpowiedzi i źródło. Profil liczony z Anki korzysta z numerów dni, więc rytm
tygodniowy jest tam opisany jako pozycja dnia w siedmiodniowym cyklu.

### 4.3 Trzy poziomy dostosowania

1. **Statystyczny uczący się.** Średnie z publicznych danych. Dla pamięci
   taką średnią są domyślne parametry FSRS-6.
2. **Typ uczącego się.** Typowe wzorce zachowania wyznaczone z długich
   historii w Anki, na przykład nauka codzienna, kilka razy w tygodniu albo
   zrywami. Nową osobę przypisuje się do typu po pierwszym tygodniu. Liczbę
   typów i ich opis ustali etap A.
3. **Konkretna osoba.** Waga własnych danych wynosi n / (n + k), gdzie n to
   liczba własnych obserwacji. Przy k = 50 własne dane ważą 17% po 10
   obserwacjach, połowę po 50 i 80% po 200. Wartość k dobiera się na danych.

Profil w rekordzie zawiera dla każdej cechy trzy wartości: średnią, wartość
dla typu i wartość własną z liczbą obserwacji. Model sam uczy się, ile
zaufać każdej z nich. Reguła ważenia z punktu 3 jest punktem odniesienia,
który model ma pokonać.

Poza stanem wejściowym działają jeszcze dwa mechanizmy. Silnik dopasowuje
dla każdej osoby kilka liczb kalibracji do jej ostatnich wyników. Wspólny
model jest trenowany ponownie, gdy przybywa przekazanych dzienników.

### 4.4 Zasady budowy zestawu

- Profil i historia w rekordzie pochodzą wyłącznie z odpowiedzi wcześniejszych
  niż ta, którą rekord przewiduje.
- Podział na trening, walidację i test przebiega po osobach. Lista osób
  testowych jest zamrożona i służy wyłącznie do bramek etapów.
- Wynik to „pamięta” albo „nie pamięta”. W VocabBocie „nie wiem” oznacza
  „nie pamięta”, a „wiem”, „prawie” i „znałem” oznaczają „pamięta”. W Anki
  ocena 1 oznacza „nie pamięta”. Wiersz Duolingo liczy się tyle razy, ile
  odpowiedzi opisuje.
- Odpowiedź z tego samego dnia co poprzednia odpowiedź na kartę nie tworzy
  rekordu pamięci, tak jak w silniku i w tabeli benchmarku.
- Rekord z własnego dziennika nie zawiera wpisanej odpowiedzi ani dat; ma
  klasę błędu i numery dni.
- Treść własnych słów uczącego się nie wchodzi do zestawu.

### 4.5 Warstwy zestawu

| Warstwa | Źródło | Czego uczy |
|---|---|---|
| Powtórki z treścią słowa | MaiMemo, Duolingo | pamięci zależnej od słowa i pary języków |
| Nauka kilku języków naraz | podzbiór Duolingo | wpływu jednego języka na drugi |
| Długie historie bez treści | Anki 10k | zapominania w skali lat, zaległości, przerw, typów zachowania |
| Planowanie | symulacja z planistą | ilu nowych słów uczyć, co powtórzyć przed przerwą, jak dzielić czas między języki |
| Dziennik VocabBota | przekazane dzienniki | polskiej bazy, klas błędów, rodzin pojęć |
| Opis słów | kursy VocabBota (23 095 haseł), przebieg wsadowy dużym modelem | cech wejściowych: pokrewieństwa z polskim, fałszywych przyjaciół |

Opis słów jest cechą wejściową, nigdy etykietą pamięci.

---

## 5. Model

### 5.1 Bazy i rozmiary

Etap D porównuje dwie bazy w najmniejszym rozmiarze:
`Qwen/Qwen3.5-0.8B-Base` i Bielik v3 1,5 mld. Oczekiwanie do sprawdzenia:
Bielik lepiej radzi sobie z polskimi znaczeniami, a baza wielojęzyczna ze
słowami niemieckimi, hiszpańskimi i francuskimi. Rodzina rozmiarów powstaje
na drabince wybranej bazy: 0,8, 2, 4 i 9 mld dla Qwen3.5 (wersje `-Base`)
albo 1,5, 4,5 i 11 mld dla Bielika.

Jeśli przed etapem F ukażą się małe modele nowszej generacji Qwen, próba baz
zostaje powtórzona z nimi. Potok danych i format pytań nie zależą od bazy.

### 5.2 Pytania pierwszej wersji

**Krzywa zapominania.** Pytanie: przy jakiej trwałości pamięci jest ta karta
po ostatniej odpowiedzi. Opcjami są poziomy trwałości w skali
logarytmicznej, od ułamka dnia do kilku lat; liczbę i granice poziomów
ustali etap C. Model zwraca prawdopodobieństwo p_k każdego poziomu S_k.
Szansa przypomnienia po t dniach wynosi

```
R(t) = suma po k z  p_k * (1 + factor * t / S_k) ^ decay
```

z tymi samymi `factor` i `decay` co w `fsrs.py`. Silnik szuka dnia, w którym
R(t) spada do trwałości z planu, i nakłada rozrzut terminów tak jak dziś.

**Obecność.** Dwa pytania: czy uczący się odbędzie sesję jutro (tak albo
nie) oraz za ile dni odbędzie następną sesję (poziomy: 1, 2, 3, 4–7, 8–14,
15 i więcej).

Pytania kolejnych wersji: czy wpisana odpowiedź jest dopuszczalnym
odpowiednikiem; z którym znanym słowem uczący się pomyli nowe; w jakiej
kolejności wprowadzać nowe słowa; jaka klasa błędu jest najbardziej
prawdopodobna.

### 5.3 Odczyt i kalibracja

Model wykonuje jeden przebieg i nie generuje tekstu. Odpowiedź to rozkład
po logitach kodów opcji w miejscu odpowiedzi. Kalibracja to jedna
temperatura na typ pytania, dopasowana na osobach walidacyjnych. Plik
kalibracji i plik formatu pytań są publikowane razem z wagami.

### 5.4 Trening

- **Funkcja straty krzywej.** Entropia krzyżowa między R(t) w rzeczywistym
  dniu powtórki a rzeczywistym wynikiem. Nie potrzeba etykiety trwałości,
  której nikt nie obserwuje.
- **Funkcja straty obecności.** Entropia krzyżowa względem rzeczywistego
  przebiegu dni nauki.
- **Sposób strojenia.** Adapter LoRA na laptopie. Pełne strojenie
  najmniejszego rozmiaru na karcie z 16 GB, jeśli próba pokaże zysk.
- **Wielkość zestawu.** Ustalana z krzywej uczenia: 100 tys., 300 tys.
  i 1 mln rekordów. Zestaw rośnie, dopóki błąd na walidacji spada.
- **Większe rozmiary.** Największy model jest nauczycielem; mniejsze uczą
  się z rzeczywistych wyników i z jego prawdopodobieństw.

### 5.5 Miary i punkty odniesienia

Miary są takie jak w srs-benchmark i w `vocabbot replay`: log loss,
RMSE(bins) jako błąd kalibracji oraz AUC. Wyniki podawane są osobno dla
zbioru, języka, numeru powtórki słowa, długości historii osoby i dla osób
z kilkoma językami.

| Punkt odniesienia | Gdzie |
|---|---|
| FSRS-6 z parametrami domyślnymi | Anki, MaiMemo, dzienniki VocabBota |
| FSRS-6 dopasowany do osoby | Anki, MaiMemo, dzienniki VocabBota |
| Reguła statystyczna: średnia, typ i własna historia ważone według rozdziału 4.3 | wszystkie zbiory |
| Mała sieć rekurencyjna na samej historii karty | Anki, MaiMemo |
| Regresja półtrwania | Duolingo |
| Częstość sesji z ostatnich tygodni | pytania o obecność |

### 5.6 Uruchamianie

Model jest osobnym pakietem Pythona. Po sesji czyta dziennik, liczy
przewidywania dla kart z nowymi odpowiedziami i zapisuje je do pliku
w folderze nauki razem z wersją modelu i kalibracji. Plik jest funkcją
dziennika i wersji modelu, więc dwa komputery z tym samym folderem mają ten
sam plan. Silnik korzysta z przewidywań tam, gdzie są aktualne, a dla
pozostałych kart liczy termin z FSRS-6.

Model nie działa w piaskownicy gospodarza czatu. Uczący się w czacie
korzysta z przewidywań policzonych na swoim komputerze albo zostaje przy
harmonogramie z Etapu 5 VocabBota. Nazwę pliku i polecenia ustali etap B.

---

## 6. Cele

| # | Cel | Miara | Próg |
|---|---|---|---|
| 1 | Trafniejsze przewidywanie pamięci | log loss na osobach spoza treningu | co najmniej 3% niżej niż FSRS-6 dopasowany do osoby i niż reguła statystyczna; docelowo 8% |
| 2 | Lepszy start nowych słów i nowych osób | log loss dla pierwszych trzech powtórek słowa i pierwszego tygodnia osoby | niżej niż oba punkty odniesienia i niż mała sieć |
| 3 | Wiarygodne prawdopodobieństwa | RMSE(bins) | niżej niż FSRS-6 |
| 4 | Dostosowanie do osoby | log loss w zależności od długości historii | maleje z tygodniami; przewaga utrzymana po 90 dniach |
| 5 | Przewidywanie systematyczności | log loss pytań o obecność | niżej niż częstość z ostatnich tygodni |
| 6 | Kilka języków naraz | log loss dla osób z dwoma i więcej językami | niżej niż punkty odniesienia; osobny wynik dla słów ze znanym odpowiednikiem w innym języku |
| 7 | Szybsza nauka | słowa pamiętane po 180 dniach na minutę nauki | więcej niż przy FSRS-6, w symulacji i w teście na uczących się |
| 8 | Publikacja | rodzina wag na Hugging Face | co najmniej 3 rozmiary; wyniki odtwarzalne z opublikowanych plików |
| 9 | Użyteczność | czas policzenia przewidywań po sesji na laptopie bez GPU | próg po pierwszym pomiarze |

Progi 3% i 8% są wstępne. 8% to wynik RWKV-Curve w benchmarku. Ostateczne
progi powstaną po policzeniu punktów odniesienia w etapie A.

---

## 7. Etapy

### Etap A. Dane, statystyczny uczący się i punkty odniesienia

Zakres:

1. Potok pobiera MaiMemo, Duolingo i Anki 10k do folderu poza gitem
   i zamienia je na rekordy z rozdziału 4.1.
2. Jedna komenda liczy tabelę statystycznego uczącego się: trafność, rytm,
   przerwy, długość sesji, czas odpowiedzi, wynik pierwszej powtórki.
3. Typy zachowań z historii Anki: grupowanie osób według rytmu, przerw
   i wielkości sesji; opis każdego typu i reguła przypisania nowej osoby po
   pierwszym tygodniu.
4. Podział osób na trening, walidację i test; zamrożona lista osób
   testowych.
5. Punkty odniesienia z rozdziału 5.5 na każdym zbiorze, na którym da się je
   policzyć.
6. Ostateczne progi celów 1–6.

Kryteria akceptacji:

- FSRS-6 dopasowany do osoby daje na Anki log loss zgodny z benchmarkiem
  (0,346, w granicach podanego tam przedziału ±0,004).
- Dwa przebiegi potoku dają identyczne rekordy.
- Przypisanie osoby do typu po 7 dniach poprawia przewidywanie jej obecności
  w dniach 8–30 względem średniej; w przeciwnym razie typy wypadają z planu.
- Żaden rekord nie zawiera odpowiedzi późniejszej niż ta, którą przewiduje.

Koszt: brak kosztów modeli; kilkadziesiąt GB dysku. Zależności: Anki 10k
wymaga Twojego konta Hugging Face (rozdział 11); MaiMemo i Duolingo pobierają
się bez logowania.

### Etap B. Start statystyczny w silniku VocabBota

Etap rozszerza Etap 5 VocabBota i zmienia silnik, więc zaczyna się po nim.

Zakres:

1. Wartości startowe nowej osoby pochodzą ze statystycznego uczącego się
   i z typu, a nie wyłącznie z wartości domyślnych FSRS-6.
2. Silnik liczy po każdej sesji profil z rozdziału 4.2 i zapisuje go
   w folderze nauki.
3. Polecenie eksportu zapisuje dziennik do przekazania: bez wpisanych
   odpowiedzi, bez treści własnych słów, z numerami dni zamiast dat
   i z losowym identyfikatorem. Program niczego nie wysyła; plik wysyła
   uczący się. PRIVACY zmienia się w obu językach.
4. Silnik czyta plik z przewidywaniami modelu i wraca do FSRS-6, gdy pliku
   nie ma, jest nieaktualny albo pochodzi z nieznanej wersji.
5. `vocabbot replay` przyjmuje model jako kolejny wariant.

Kryteria akceptacji:

- Kolejka dnia jest identyczna na dwóch komputerach z tym samym folderem
  nauki, z plikiem przewidywań i bez niego.
- Bez pliku przewidywań terminy są takie same jak przed etapem.
- Plik eksportu nie zawiera wpisanej odpowiedzi, daty ani treści własnego
  słowa, co sprawdza test.
- Kontrole VocabBota przechodzą na bibliotece standardowej i Pythonie 3.10.

Koszt: brak.

### Etap C. Format pytań i odczyt

Zakres:

1. Specyfikacja stanu: kolejność bloków, zapis liczb w przedziałach, długość
   historii karty, liczba kart rodziny.
2. Specyfikacja pytań z rozdziału 5.2, w tym liczba i granice poziomów
   trwałości.
3. Biblioteka w repozytorium modelu: budowa tekstu wejściowego z rekordu,
   odczyt rozkładu z logitów, krzywa z rozkładu, termin z krzywej,
   kalibracja.
4. Funkcje straty z rozdziału 5.4.

Kryteria akceptacji:

- Rozkład skupiony na jednym poziomie trwałości daje ten sam termin co
  `fsrs.py` dla tej samej stabilności.
- Na danych syntetycznych z generatora o znanych parametrach trening małej
  sieci z tą funkcją straty odtwarza krzywą generatora.
- Ten sam rekord daje ten sam tekst wejściowy na każdym komputerze.

Koszt: brak. Etap może iść równolegle z etapem A.

### Etap D. Pierwszy model i bramka

Zakres:

1. Próba zgodności na laptopie: wczytanie każdej bazy, jeden krok strojenia
   LoRA, odczyt logitów opcji i pomiar zajętej pamięci karty.
2. Próba dwóch baz z rozdziału 5.1 na 100 tys. rekordów, z tymi samymi
   ustawieniami, oceniana na walidacji.
3. Krzywa uczenia wybranej bazy na 100 tys., 300 tys. i 1 mln rekordów.
4. Trening najmniejszego rozmiaru na zestawie o wielkości wybranej z krzywej
   uczenia.
5. Kalibracja na osobach walidacyjnych.
6. Ocena na zamrożonym zbiorze testowym wobec wszystkich punktów odniesienia.

Kryteria akceptacji, czyli bramka:

- Cele 1–4 są spełnione na progu minimalnym.
- Wynik podaje błąd osobno dla każdego zbioru i dla pierwszych trzech
  powtórek słowa.

Jeśli bramka nie przechodzi, zmienia się sposób podawania historii
liczbowej (osobne osadzenia liczb zamiast tekstu w przedziałach) i etap się
powtarza. Etapy F i G nie zaczynają się przed przejściem bramki.

Koszt: 0 USD przy treningu na laptopie i na Kaggle. Zależności: etapy A i C.

### Etap E. Planista i symulacja

Zakres:

1. Planista w silniku liczy plan dnia z krzywych i z przewidywanej
   obecności: kolejność powtórek przy ograniczonym czasie, powtórki
   przesunięte przed spodziewaną przerwę, liczba nowych słów zależna od
   prognozowanych zaległości.
2. Symulator z osobami losowanymi z rozkładów policzonych w etapie A:
   parametry pamięci, rytm obecności, czas na powtórkę.
3. Porównanie trzech harmonogramów: FSRS-6, plan z Etapu 5 VocabBota oraz
   model z planistą.

Kryteria akceptacji:

- Cel 5 na zamrożonym zbiorze testowym.
- Cel 7 w symulacji: więcej słów pamiętanych po 180 dniach na minutę nauki
  niż w obu pozostałych harmonogramach, osobno dla każdego typu uczącego się.
- Plan dnia pozostaje funkcją plików w folderze nauki.

Symulacja sprawdza planistę. Pamięci w symulacji nie da się sprawdzić, bo
symulator sam korzysta z modelu pamięci; przewidywanie pamięci ocenia
wyłącznie zbiór testowy z prawdziwymi wynikami.

Koszt: brak.

### Etap F. Rodzina rozmiarów

Zakres:

1. Trening kolejnych rozmiarów drabinki wybranej bazy.
2. Największy rozmiar jako nauczyciel; destylacja do mniejszych. Nauczycielem
   może być też `Qwen/Qwen3.8-27B`, najnowszy otwarty model Qwen, co wymaga
   wynajętego GPU.
3. Wersje skwantyzowane każdego rozmiaru; przy bazie Qwen3.5 najpierw próba,
   czy narzędzia do kwantyzacji obsługują jej budowę warstw.
4. Tabela jakości i szybkości według rozmiaru.

Kryteria akceptacji:

- Każdy rozmiar spełnia cele 1–3.
- Wersja skwantyzowana ma log loss gorszy najwyżej o 1% od pełnej.
- Cel 9 ma zmierzony czas dla każdego rozmiaru.

Koszt: rozmiary do 4 mld na Kaggle bez kosztów, wolno; rozmiar 9 mld
i większe wymagają wynajętego GPU. Szacunek to setki USD; wycena i Twoja
zgoda przed każdym uruchomieniem.

### Etap G. Wydanie badawcze

Zakres:

1. Repozytorium na Hugging Face dla każdego rozmiaru: wagi, plik kalibracji,
   plik formatu pytań.
2. Karta modelu: dane z licencjami, wyniki wobec punktów odniesienia na
   każdym zbiorze, kalibracja, ograniczenia (języki bazowe danych, inne
   aplikacje), przeznaczenie.
3. Pakiet do uruchamiania modelu oraz skrypty oceny i budowy zestawu.
4. Opcja modelu w VocabBocie i jej opis w dokumentacji w obu językach.

Kryteria akceptacji:

- Na czystym komputerze opublikowane wagi i skrypty odtwarzają wyniki
  z karty modelu.
- VocabBot z plikiem przewidywań układa plan dnia, a bez niego daje plan
  taki jak wcześniej.

Koszt: brak. Każda publikacja wymaga Twojej osobnej zgody.

### Etap H. Własne dane i wersja 1

Zakres:

1. Zbieranie dzienników przekazanych przez uczących się. Etap zaczyna się
   przy co najmniej 30 osobach z historią 60 dni (propozycja).
2. Test na uczących się: karty jednej osoby są dzielone losowo, według
   skrótu identyfikatora karty, między FSRS-6 a model. Miary to trafność
   przy powtórkach wobec docelowej trwałości oraz liczba powtórek i minut na
   kartę. Szczegóły protokołu powstaną na początku etapu.
3. Dostrojenie na polskiej bazie i na rodzinach pojęć.
4. Pytania o słowa z rozdziału 5.2.
5. Publikacja zbioru przekazanych dzienników, jeśli uczący się zgodzili się
   na publikację.
6. Wydanie na Apache-2.0, jeśli wagi powstaną wyłącznie z danych, które na
   to pozwalają.

Kryteria akceptacji:

- Cele 6 i 7 potwierdzone na uczących się.
- Warunki z rozdziału 1 spełnione.

Lżejszą drogą zbierania dowodów jest raport `vocabbot replay` z modelem
jako wariantem: uczący się przekazuje same liczby, bez dziennika.

Koszt: GPU według wyceny przed uruchomieniem.

---

## 8. Kolejność i zależności

| Etap | Zależy od | Kiedy |
|---|---|---|
| A | konta Hugging Face dla zbioru Anki | od razu dla MaiMemo i Duolingo |
| C | niczego | od razu, równolegle z A |
| B | Etapu 5 VocabBota | po wersji 1.0 VocabBota |
| D | A i C | po nich |
| E | D; planista może powstawać wcześniej na krzywych FSRS | po bramce |
| F | bramki z etapu D | po bramce |
| G | F oraz B | po rodzinie rozmiarów |
| H | B (eksport dziennika) i liczby przekazanych dzienników | termin otwarty |

Pilotaż VocabBota to Twoja nauka przez dwa tygodnie, więc nie daje danych
treningowych. Dane z polską bazą powstaną dopiero z dzienników przekazanych
przez użytkowników.

---

## 9. Koszty i zgody

| Pozycja | Koszt | Zgoda |
|---|---|---|
| Etapy A, B, C, E | brak | akceptacja planu |
| Etap D na laptopie i na Kaggle | 0 USD | akceptacja planu |
| Etap F, rozmiary wymagające wynajętego GPU | szacunkowo setki USD; wycena przed uruchomieniem | osobna dla każdego uruchomienia |
| Etap H, dostrojenie | wycena przed uruchomieniem | osobna |
| Przebieg wsadowy dużym modelem dla opisu słów | wycena przed uruchomieniem | osobna |
| Repozytorium na GitHubie, pakiet w PyPI, wagi i zbiór na Hugging Face | brak | osobna dla każdej czynności |
| Wgranie danych na Kaggle | brak | osobna; dane Anki dopiero po odczytaniu licencji |

---

## 10. Ryzyka i sposoby postępowania

| Ryzyko | Postępowanie |
|---|---|
| Model językowy nie wygrywa z punktami odniesienia | bramka po etapie D; zmiana sposobu podawania historii; bez przejścia bramki nie powstają większe rozmiary, a VocabBot zostaje przy harmonogramie z Etapu 5 |
| Licencja Anki 10k nie pozwala trenować albo publikować modelu | odczyt licencji przed pobraniem; w razie zakazu Anki służy do statystyk i oceny, jeśli na to pozwala, a długie historie pochodzą z MaiMemo; pytanie do opiekunów zbioru o zgodę |
| Ograniczenie niekomercyjne danych a licencja wag | wydanie badawcze na CC BY-NC 4.0; wydanie na Apache-2.0 dopiero z własnych danych |
| Statystyki startowe pochodzą z innych aplikacji i języków bazowych | są wartościami początkowymi; cel 4 mierzy, czy własna historia je zastępuje |
| Proste średnie fałszują zapominanie | pamięć opisuje wyłącznie dopasowany model; średnie opisują zachowanie |
| Dane zebrane pod harmonogramem z trwałością bliską 90% mają mało obserwacji przy innych odstępach | rozrzut terminów w silniku różnicuje odstępy; karta modelu podaje zakres, w którym model był sprawdzany |
| Symulacja korzysta z modelu pamięci, który sama ocenia | symulacja ocenia tylko planistę; dowodem szybszej nauki jest test na uczących się |
| Za mało przekazanych dzienników | próg 30 osób; raporty `replay` jako lżejszy dowód; termin etapu H pozostaje otwarty |
| 8 GB pamięci karty nie wystarcza na większe rozmiary | Kaggle z kartą 16 GB; wynajęte GPU po Twojej zgodzie |
| Budowa warstw Qwen3.5 nie działa z narzędziami do strojenia albo kwantyzacji na Windows | próba zgodności na początku etapu D; w razie kłopotów trening na Kaggle (Linux) albo Bielik jako baza |
| Ukazuje się nowsza generacja małych modeli Qwen | powtórzenie próby baz; potok danych i format pytań nie zależą od bazy |
| Plik przewidywań narusza zgodność planu na dwóch komputerach | plik jest funkcją dziennika i wersji modelu, zawiera obie wersje i leży w folderze nauki; test zgodności w etapie B |
| Przekazany dziennik ujawnia dane uczącego się | eksport bez wpisanych odpowiedzi, dat i własnych słów; osobna zgoda na publikację zbioru; program niczego nie wysyła |

---

## 11. Otwarte decyzje

| Decyzja | Stan |
|---|---|
| Nazwa rodziny modeli i repozytorium | do wyboru; roboczo `vocabbot-model`; dostępność w GitHubie, PyPI i na Hugging Face do sprawdzenia po wyborze |
| Dostęp do Anki 10k | potrzebne konto Hugging Face, zgoda na warunki na stronie zbioru i logowanie terminala poleceniem `hf auth login`; potem odczyt licencji |
| Wynajęte GPU dla największych rozmiarów | decyzja po bramce z etapu D |
| Próg rozpoczęcia etapu H | propozycja: 30 osób z historią 60 dni |
| Angielska wersja planu | powstanie razem z repozytorium modelu |

---

## Źródła

- srs-benchmark: https://github.com/open-spaced-repetition/srs-benchmark
- Anki 10k: https://huggingface.co/datasets/open-spaced-repetition/anki-revlogs-10k
- MaiMemo, SSP-MMC-Plus: https://github.com/maimemo/SSP-MMC-Plus oraz https://doi.org/10.7910/DVN/VAGUL0
- Duolingo, regresja półtrwania: https://github.com/duolingo/halflife-regression oraz https://doi.org/10.7910/DVN/N8XJME
- Duolingo SLAM 2018: https://sharedtask.duolingo.com/2018.html
- KAR3L: https://arxiv.org/abs/2402.12291
- LECTOR: https://arxiv.org/abs/2508.03275
- NTKT: https://arxiv.org/abs/2511.02599
- CLST: https://arxiv.org/abs/2406.10296
- NLP4CALL 2026, obciążenie nauką u osób wielojęzycznych: https://aclanthology.org/2026.nlp4call-1.12.pdf
- Xue i in. 2022, słowa pokrewne w trzecim języku: https://www.frontiersin.org/articles/10.3389/fpsyg.2022.1003199/full
- basal: https://github.com/rkinas/basal oraz https://huggingface.co/Remek/basal-2.0-mini
- Kev: https://thenewstack.io/kev-skips-text-generation/
- Jev: https://infoq.com/news/2026/10/typesafe-ai-jev-released
- Qwen, wykaz modeli: https://huggingface.co/Qwen
- Qwen3.5 0,8 mld, wersja do strojenia: https://huggingface.co/Qwen/Qwen3.5-0.8B-Base
