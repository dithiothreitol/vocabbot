# How the cards look in the chat

The examples use invented cards; the real ones come from `next`.

## One card at a time (`batch` 1)

A new word, alone in its message, under the counter:

```
Postęp: 6/25 · nowe 3/15 · powtórki 3/10

Nowe słowo · DE
der Hund (r.m., l.mn. die Hunde) /hʊnt/ [🔊 wymowa](https://upload.wikimedia.org/…) = pies
Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.

Napisz „dalej”, gdy będziesz gotowy, albo „znałem”, jeśli znałeś to słowo przed kursem.
```

Its question, after "dalej":

```
DE · pies (rzeczownik, z rodzajnikiem)
___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
```

The result of the answer and the next card in one message:

```
✓ wiem · der Hund

ES · stół (rzeczownik, z rodzajnikiem)
___ es de madera. · Stół jest z drewna.
```

```
≈ prawie (rodzajnik) · la mesa /ˈme.sa/ [🔊 wymowa](https://upload.wikimedia.org/…)
La mesa es de madera. · Stół jest z drewna.

FR · czytać (czasownik)
J'aime ___ le soir. · Lubię czytać wieczorem.
```

## Several cards (`batch` 2 or more)

### Introducing new words

```
Nowe słowa (3):

DE  der Hund (r.m., l.mn. die Hunde) /hʊnt/ = pies
    Der Hund ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
ES  la mesa (r.ż., l.mn. las mesas) /ˈme.sa/ = stół
    La mesa es de madera. · Stół jest z drewna.
FR  lire (czasownik) /liʁ/ = czytać
    J'aime lire le soir. · Lubię czytać wieczorem.

Przeczytaj je spokojnie. Jeśli któreś słowo było Ci znane przed kursem, napisz które.
```

### Questions

```
1. DE · pies (rzeczownik, z rodzajnikiem)
   ___ ist das treueste aller Tiere. · Pies jest najwierniejszy z wszystkich zwierząt.
2. ES · stół (rzeczownik, z rodzajnikiem)
   ___ es de madera. · Stół jest z drewna.
3. FR · czytać (czasownik)
   J'aime ___ le soir. · Lubię czytać wieczorem.

Odpowiedz numerami, np. „1. …”. Gdy nie pamiętasz, wpisz „?”.
```

A review looks the same as a new word's question. Keep the order of `next`:
the engine spreads the languages and keeps the cards of one concept apart.

### Results

```
1. ✓ wiem · der Hund
2. ≈ prawie (rodzajnik) · la mesa /ˈme.sa/ [🔊 wymowa](https://upload.wikimedia.org/…)
   La mesa es de madera. · Stół jest z drewna.
3. ✗ nie wiem · lire /liʁ/ [🔊 wymowa](https://upload.wikimedia.org/…)
   J'aime lire le soir. · Lubię czytać wieczorem.
```

Error classes and parts of speech are named as in `shared/labels.md`. The
next due date of each card is in the result (`next_due`); show it only when
the learner asks.
