# The format of own words

One word per line on standard input. Lines starting with `#` are skipped.

## Short lines

```
der Hund = pies
laufen [verb] = biec, biegać
l'ami (m) = przyjaciel | L'ami attend à la gare. | Przyjaciel czeka na dworcu.
la mano = ręka
take off [phrase] = startować (o samolocie)
```

- Left of `=`: the word as the learner should type it. Nouns of German,
  Spanish, French and Italian take their article (`der`, `die`, `das`; `el`,
  `la`; `le`, `la`; `il`, `lo`, `la`), which also sets the gender.
- `(m)`, `(f)` or `(n)` gives the gender where the article does not show it
  (French and Italian `l'`, Spanish `el agua`).
- `[noun]`, `[verb]`, `[adj]`, `[adv]`, `[phrase]` and the other parts of
  speech of the course set the part of speech; without it, a word with an
  article is a noun and any other word gets "słowo".
- Right of `=`: the Polish meaning, as the question will show it.
- After `|`: an example sentence with the word, then its Polish translation.
  The example becomes the sentence with a gap.

## JSON lines

For more fields, one JSON object per line with the fields of a course entry:

```
{"display": "die Tasse", "gender": "f", "pos": "noun", "gloss": {"pl": "filiżanka"}, "forms": {"plural": "die Tassen"}, "accept": ["das Häferl"]}
```

`display` and `gloss.pl` are required; `accept` lists other answers the
engine takes as right; `hint` tells two words with one Polish meaning apart.
