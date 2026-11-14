"""The starter course: 60 concepts in English, German, Spanish and French.

Written by hand for VocabBot (CC BY-SA 4.0). Stage 2 replaces the packaged
course with the A1-B2 courses built from open data; the tests keep using this
one from tests/fixtures/courses.

    python tools/courses/starter.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
# Since Stage 2 the packaged courses come from tools/courses/pipeline.py; the
# starter course stays as the test fixture.
TARGETS = [REPO / "tests" / "fixtures" / "courses"]
LANGS = ("en", "de", "es", "fr")
VERSION = "2026-11-14"


def w(display, gender, ipa, forms, text, gap, accept=(), pl=None):
    return {
        "display": display,
        "gender": gender,
        "ipa": ipa,
        "forms": forms,
        "text": text,
        "gap": gap,
        "accept": list(accept),
        "pl": pl,
    }


# (number, level, part of speech, Polish meaning, Polish sentence, words by language)
CONCEPTS: list[tuple[int, str, str, str, str, dict[str, dict[str, Any]]]] = [
    (
        1,
        "a1",
        "noun",
        "dom",
        "Dom jest bardzo duży.",
        {
            "en": w(
                "house", None, "/haʊs/", {"plural": "houses"}, "The house is very big.", "house"
            ),
            "de": w(
                "das Haus",
                "n",
                "/haʊ̯s/",
                {"plural": "die Häuser"},
                "Das Haus ist sehr groß.",
                "Das Haus",
            ),
            "es": w(
                "la casa",
                "f",
                "/ˈkasa/",
                {"plural": "las casas"},
                "La casa es muy grande.",
                "La casa",
            ),
            "fr": w(
                "la maison",
                "f",
                "/mɛzɔ̃/",
                {"plural": "les maisons"},
                "La maison est très grande.",
                "La maison",
            ),
        },
    ),
    (
        2,
        "a1",
        "noun",
        "pies",
        "Pies śpi w ogrodzie.",
        {
            "en": w(
                "dog",
                None,
                "/dɒɡ/",
                {"plural": "dogs"},
                "The dog is sleeping in the garden.",
                "dog",
            ),
            "de": w(
                "der Hund",
                "m",
                "/hʊnt/",
                {"plural": "die Hunde"},
                "Der Hund schläft im Garten.",
                "Der Hund",
            ),
            "es": w(
                "el perro",
                "m",
                "/ˈpero/",
                {"plural": "los perros"},
                "El perro duerme en el jardín.",
                "El perro",
            ),
            "fr": w(
                "le chien",
                "m",
                "/ʃjɛ̃/",
                {"plural": "les chiens"},
                "Le chien dort dans le jardin.",
                "Le chien",
            ),
        },
    ),
    (
        3,
        "a1",
        "noun",
        "kot",
        "Kot pije mleko.",
        {
            "en": w("cat", None, "/kæt/", {"plural": "cats"}, "The cat is drinking milk.", "cat"),
            "de": w(
                "die Katze",
                "f",
                "/ˈkat͡sə/",
                {"plural": "die Katzen"},
                "Die Katze trinkt Milch.",
                "Die Katze",
            ),
            "es": w(
                "el gato", "m", "/ˈɡato/", {"plural": "los gatos"}, "El gato bebe leche.", "El gato"
            ),
            "fr": w(
                "le chat", "m", "/ʃa/", {"plural": "les chats"}, "Le chat boit du lait.", "Le chat"
            ),
        },
    ),
    (
        4,
        "a1",
        "noun",
        "woda",
        "Woda jest zimna.",
        {
            "en": w("water", None, "/ˈwɔːtə/", {}, "The water is cold.", "water"),
            "de": w("das Wasser", "n", "/ˈvasɐ/", {}, "Das Wasser ist kalt.", "Das Wasser"),
            "es": w(
                "el agua", "f", "/ˈaɡwa/", {"plural": "las aguas"}, "El agua está fría.", "El agua"
            ),
            "fr": w("l'eau", "f", "/o/", {"plural": "les eaux"}, "L'eau est froide.", "L'eau"),
        },
    ),
    (
        5,
        "a1",
        "noun",
        "chleb",
        "Chleb jest świeży.",
        {
            "en": w("bread", None, "/bred/", {}, "The bread is fresh.", "bread"),
            "de": w(
                "das Brot",
                "n",
                "/bʁoːt/",
                {"plural": "die Brote"},
                "Das Brot ist frisch.",
                "Das Brot",
            ),
            "es": w(
                "el pan", "m", "/pan/", {"plural": "los panes"}, "El pan está fresco.", "El pan"
            ),
            "fr": w(
                "le pain", "m", "/pɛ̃/", {"plural": "les pains"}, "Le pain est frais.", "Le pain"
            ),
        },
    ),
    (
        6,
        "a1",
        "noun",
        "mleko",
        "Mleko jest w lodówce.",
        {
            "en": w("milk", None, "/mɪlk/", {}, "The milk is in the fridge.", "milk"),
            "de": w("die Milch", "f", "/mɪlç/", {}, "Die Milch ist im Kühlschrank.", "Die Milch"),
            "es": w("la leche", "f", "/ˈletʃe/", {}, "La leche está en la nevera.", "La leche"),
            "fr": w("le lait", "m", "/lɛ/", {}, "Le lait est dans le frigo.", "Le lait"),
        },
    ),
    (
        7,
        "a1",
        "noun",
        "jabłko",
        "Jabłko jest czerwone.",
        {
            "en": w("apple", None, "/ˈæpəl/", {"plural": "apples"}, "The apple is red.", "apple"),
            "de": w(
                "der Apfel",
                "m",
                "/ˈapfl̩/",
                {"plural": "die Äpfel"},
                "Der Apfel ist rot.",
                "Der Apfel",
            ),
            "es": w(
                "la manzana",
                "f",
                "/manˈθana/",
                {"plural": "las manzanas"},
                "La manzana es roja.",
                "La manzana",
            ),
            "fr": w(
                "la pomme",
                "f",
                "/pɔm/",
                {"plural": "les pommes"},
                "La pomme est rouge.",
                "La pomme",
            ),
        },
    ),
    (
        8,
        "a1",
        "noun",
        "książka",
        "Książka leży na stole.",
        {
            "en": w(
                "book", None, "/bʊk/", {"plural": "books"}, "The book is on the table.", "book"
            ),
            "de": w(
                "das Buch",
                "n",
                "/buːx/",
                {"plural": "die Bücher"},
                "Das Buch liegt auf dem Tisch.",
                "Das Buch",
            ),
            "es": w(
                "el libro",
                "m",
                "/ˈlibɾo/",
                {"plural": "los libros"},
                "El libro está en la mesa.",
                "El libro",
            ),
            "fr": w(
                "le livre",
                "m",
                "/livʁ/",
                {"plural": "les livres"},
                "Le livre est sur la table.",
                "Le livre",
            ),
        },
    ),
    (
        9,
        "a1",
        "noun",
        "szkoła",
        "Szkoła jest blisko.",
        {
            "en": w(
                "school",
                None,
                "/skuːl/",
                {"plural": "schools"},
                "The school is close by.",
                "school",
            ),
            "de": w(
                "die Schule",
                "f",
                "/ˈʃuːlə/",
                {"plural": "die Schulen"},
                "Die Schule ist in der Nähe.",
                "Die Schule",
            ),
            "es": w(
                "la escuela",
                "f",
                "/esˈkwela/",
                {"plural": "las escuelas"},
                "La escuela está cerca.",
                "La escuela",
            ),
            "fr": w(
                "l'école",
                "f",
                "/ekɔl/",
                {"plural": "les écoles"},
                "L'école est tout près.",
                "L'école",
            ),
        },
    ),
    (
        10,
        "a1",
        "noun",
        "przyjaciel",
        "Przyjaciel czeka na dworcu.",
        {
            "en": w(
                "friend",
                None,
                "/frend/",
                {"plural": "friends"},
                "My friend is waiting at the station.",
                "friend",
                pl="Mój przyjaciel czeka na dworcu.",
            ),
            "de": w(
                "der Freund",
                "m",
                "/fʁɔʏ̯nt/",
                {"plural": "die Freunde"},
                "Der Freund wartet am Bahnhof.",
                "Der Freund",
            ),
            "es": w(
                "el amigo",
                "m",
                "/aˈmiɡo/",
                {"plural": "los amigos", "feminine": "la amiga"},
                "El amigo espera en la estación.",
                "El amigo",
            ),
            "fr": w(
                "l'ami",
                "m",
                "/ami/",
                {"plural": "les amis", "feminine": "l'amie"},
                "L'ami attend à la gare.",
                "L'ami",
            ),
        },
    ),
    (
        11,
        "a1",
        "noun",
        "miasto",
        "Miasto jest piękne.",
        {
            "en": w(
                "city", None, "/ˈsɪti/", {"plural": "cities"}, "The city is beautiful.", "city"
            ),
            "de": w(
                "die Stadt",
                "f",
                "/ʃtat/",
                {"plural": "die Städte"},
                "Die Stadt ist schön.",
                "Die Stadt",
            ),
            "es": w(
                "la ciudad",
                "f",
                "/θjuˈdad/",
                {"plural": "las ciudades"},
                "La ciudad es bonita.",
                "La ciudad",
            ),
            "fr": w(
                "la ville",
                "f",
                "/vil/",
                {"plural": "les villes"},
                "La ville est belle.",
                "La ville",
            ),
        },
    ),
    (
        12,
        "a1",
        "noun",
        "ulica",
        "Ulica jest długa.",
        {
            "en": w(
                "street", None, "/striːt/", {"plural": "streets"}, "The street is long.", "street"
            ),
            "de": w(
                "die Straße",
                "f",
                "/ˈʃtʁaːsə/",
                {"plural": "die Straßen"},
                "Die Straße ist lang.",
                "Die Straße",
            ),
            "es": w(
                "la calle",
                "f",
                "/ˈkaʎe/",
                {"plural": "las calles"},
                "La calle es larga.",
                "La calle",
            ),
            "fr": w("la rue", "f", "/ʁy/", {"plural": "les rues"}, "La rue est longue.", "La rue"),
        },
    ),
    (
        13,
        "a1",
        "noun",
        "samochód",
        "Samochód stoi przed domem.",
        {
            "en": w(
                "car", None, "/kɑː/", {"plural": "cars"}, "The car is in front of the house.", "car"
            ),
            "de": w(
                "das Auto",
                "n",
                "/ˈaʊ̯to/",
                {"plural": "die Autos"},
                "Das Auto steht vor dem Haus.",
                "Das Auto",
                accept=["der Wagen"],
            ),
            "es": w(
                "el coche",
                "m",
                "/ˈkotʃe/",
                {"plural": "los coches"},
                "El coche está delante de la casa.",
                "El coche",
                accept=["el carro", "el auto"],
            ),
            "fr": w(
                "la voiture",
                "f",
                "/vwatyʁ/",
                {"plural": "les voitures"},
                "La voiture est devant la maison.",
                "La voiture",
            ),
        },
    ),
    (
        14,
        "a1",
        "noun",
        "dzień",
        "Zimą dzień jest krótki.",
        {
            "en": w("day", None, "/deɪ/", {"plural": "days"}, "In winter the day is short.", "day"),
            "de": w(
                "der Tag",
                "m",
                "/taːk/",
                {"plural": "die Tage"},
                "Im Winter ist der Tag kurz.",
                "der Tag",
            ),
            "es": w(
                "el día",
                "m",
                "/ˈdia/",
                {"plural": "los días"},
                "En invierno el día es corto.",
                "el día",
            ),
            "fr": w(
                "le jour",
                "m",
                "/ʒuʁ/",
                {"plural": "les jours"},
                "En hiver, le jour est court.",
                "le jour",
            ),
        },
    ),
    (
        15,
        "a1",
        "noun",
        "noc",
        "Noc jest ciemna.",
        {
            "en": w("night", None, "/naɪt/", {"plural": "nights"}, "The night is dark.", "night"),
            "de": w(
                "die Nacht",
                "f",
                "/naxt/",
                {"plural": "die Nächte"},
                "Die Nacht ist dunkel.",
                "Die Nacht",
            ),
            "es": w(
                "la noche",
                "f",
                "/ˈnotʃe/",
                {"plural": "las noches"},
                "La noche es oscura.",
                "La noche",
            ),
            "fr": w(
                "la nuit", "f", "/nɥi/", {"plural": "les nuits"}, "La nuit est sombre.", "La nuit"
            ),
        },
    ),
    (
        16,
        "a1",
        "noun",
        "rok",
        "Rok ma dwanaście miesięcy.",
        {
            "en": w(
                "year", None, "/jɪə/", {"plural": "years"}, "A year has twelve months.", "year"
            ),
            "de": w(
                "das Jahr",
                "n",
                "/jaːɐ̯/",
                {"plural": "die Jahre"},
                "Das Jahr hat zwölf Monate.",
                "Das Jahr",
            ),
            "es": w(
                "el año",
                "m",
                "/ˈaɲo/",
                {"plural": "los años"},
                "El año tiene doce meses.",
                "El año",
            ),
            "fr": w(
                "l'année",
                "f",
                "/ane/",
                {"plural": "les années"},
                "L'année a douze mois.",
                "L'année",
            ),
        },
    ),
    (
        17,
        "a1",
        "noun",
        "dziecko",
        "Dziecko bawi się w parku.",
        {
            "en": w(
                "child",
                None,
                "/tʃaɪld/",
                {"plural": "children"},
                "The child is playing in the park.",
                "child",
                accept=["kid"],
            ),
            "de": w(
                "das Kind",
                "n",
                "/kɪnt/",
                {"plural": "die Kinder"},
                "Das Kind spielt im Park.",
                "Das Kind",
            ),
            "es": w(
                "el niño",
                "m",
                "/ˈniɲo/",
                {"plural": "los niños", "feminine": "la niña"},
                "El niño juega en el parque.",
                "El niño",
            ),
            "fr": w(
                "l'enfant",
                "m",
                "/ɑ̃fɑ̃/",
                {"plural": "les enfants"},
                "L'enfant joue dans le parc.",
                "L'enfant",
            ),
        },
    ),
    (
        18,
        "a1",
        "noun",
        "kobieta",
        "Kobieta czyta gazetę.",
        {
            "en": w(
                "woman",
                None,
                "/ˈwʊmən/",
                {"plural": "women"},
                "The woman is reading a newspaper.",
                "woman",
            ),
            "de": w(
                "die Frau",
                "f",
                "/fʁaʊ̯/",
                {"plural": "die Frauen"},
                "Die Frau liest eine Zeitung.",
                "Die Frau",
            ),
            "es": w(
                "la mujer",
                "f",
                "/muˈxeɾ/",
                {"plural": "las mujeres"},
                "La mujer lee un periódico.",
                "La mujer",
            ),
            "fr": w(
                "la femme",
                "f",
                "/fam/",
                {"plural": "les femmes"},
                "La femme lit un journal.",
                "La femme",
            ),
        },
    ),
    (
        19,
        "a1",
        "noun",
        "mężczyzna",
        "Mężczyzna pije kawę.",
        {
            "en": w("man", None, "/mæn/", {"plural": "men"}, "The man is drinking coffee.", "man"),
            "de": w(
                "der Mann",
                "m",
                "/man/",
                {"plural": "die Männer"},
                "Der Mann trinkt Kaffee.",
                "Der Mann",
            ),
            "es": w(
                "el hombre",
                "m",
                "/ˈombɾe/",
                {"plural": "los hombres"},
                "El hombre bebe café.",
                "El hombre",
            ),
            "fr": w(
                "l'homme", "m", "/ɔm/", {"plural": "les hommes"}, "L'homme boit un café.", "L'homme"
            ),
        },
    ),
    (
        20,
        "a1",
        "noun",
        "ręka, dłoń",
        "Ręka jest zimna.",
        {
            "en": w("hand", None, "/hænd/", {"plural": "hands"}, "The hand is cold.", "hand"),
            "de": w(
                "die Hand", "f", "/hant/", {"plural": "die Hände"}, "Die Hand ist kalt.", "Die Hand"
            ),
            "es": w(
                "la mano", "f", "/ˈmano/", {"plural": "las manos"}, "La mano está fría.", "La mano"
            ),
            "fr": w(
                "la main", "f", "/mɛ̃/", {"plural": "les mains"}, "La main est froide.", "La main"
            ),
        },
    ),
    (
        21,
        "a1",
        "verb",
        "pić",
        "Chcę pić wodę.",
        {
            "en": w(
                "drink",
                None,
                "/drɪŋk/",
                {"past": "drank", "participle": "drunk"},
                "I want to drink water.",
                "drink",
            ),
            "de": w(
                "trinken",
                None,
                "/ˈtʁɪŋkn̩/",
                {"past": "trank", "participle": "hat getrunken"},
                "Ich möchte Wasser trinken.",
                "trinken",
            ),
            "es": w("beber", None, "/beˈbeɾ/", {}, "Quiero beber agua.", "beber"),
            "fr": w(
                "boire",
                None,
                "/bwaʁ/",
                {"present_1sg": "je bois", "participle": "bu"},
                "Je veux boire de l'eau.",
                "boire",
            ),
        },
    ),
    (
        22,
        "a1",
        "verb",
        "jeść",
        "Chcę teraz jeść.",
        {
            "en": w(
                "eat",
                None,
                "/iːt/",
                {"past": "ate", "participle": "eaten"},
                "I want to eat now.",
                "eat",
            ),
            "de": w(
                "essen",
                None,
                "/ˈɛsn̩/",
                {"present_3sg": "isst", "past": "aß", "participle": "hat gegessen"},
                "Ich möchte jetzt essen.",
                "essen",
            ),
            "es": w("comer", None, "/koˈmeɾ/", {}, "Quiero comer ahora.", "comer"),
            "fr": w(
                "manger",
                None,
                "/mɑ̃ʒe/",
                {"participle": "mangé"},
                "Je veux manger maintenant.",
                "manger",
            ),
        },
    ),
    (
        23,
        "a1",
        "verb",
        "iść, jechać",
        "Muszę iść do pracy.",
        {
            "en": w(
                "go",
                None,
                "/ɡəʊ/",
                {"past": "went", "participle": "gone"},
                "I have to go to work.",
                "go",
            ),
            "de": w(
                "gehen",
                None,
                "/ˈɡeːən/",
                {"past": "ging", "participle": "ist gegangen"},
                "Ich muss zur Arbeit gehen.",
                "gehen",
            ),
            "es": w(
                "ir",
                None,
                "/iɾ/",
                {"present_1sg": "voy", "participle": "ido"},
                "Tengo que ir al trabajo.",
                "ir",
            ),
            "fr": w(
                "aller",
                None,
                "/ale/",
                {"present_1sg": "je vais", "participle": "allé"},
                "Je dois aller au travail.",
                "aller",
            ),
        },
    ),
    (
        24,
        "a1",
        "verb",
        "mówić",
        "Chcę mówić powoli.",
        {
            "en": w(
                "speak",
                None,
                "/spiːk/",
                {"past": "spoke", "participle": "spoken"},
                "I want to speak slowly.",
                "speak",
            ),
            "de": w(
                "sprechen",
                None,
                "/ˈʃpʁɛçn̩/",
                {"present_3sg": "spricht", "past": "sprach", "participle": "hat gesprochen"},
                "Ich möchte langsam sprechen.",
                "sprechen",
            ),
            "es": w("hablar", None, "/aˈblaɾ/", {}, "Quiero hablar despacio.", "hablar"),
            "fr": w(
                "parler",
                None,
                "/paʁle/",
                {"participle": "parlé"},
                "Je veux parler lentement.",
                "parler",
            ),
        },
    ),
    (
        25,
        "a1",
        "verb",
        "pisać",
        "Chcę napisać list.",
        {
            "en": w(
                "write",
                None,
                "/raɪt/",
                {"past": "wrote", "participle": "written"},
                "I want to write a letter.",
                "write",
            ),
            "de": w(
                "schreiben",
                None,
                "/ˈʃʁaɪ̯bn̩/",
                {"past": "schrieb", "participle": "hat geschrieben"},
                "Ich möchte einen Brief schreiben.",
                "schreiben",
            ),
            "es": w(
                "escribir",
                None,
                "/eskɾiˈbiɾ/",
                {"participle": "escrito"},
                "Quiero escribir una carta.",
                "escribir",
            ),
            "fr": w(
                "écrire",
                None,
                "/ekʁiʁ/",
                {"participle": "écrit"},
                "Je veux écrire une lettre.",
                "écrire",
            ),
        },
    ),
    (
        26,
        "a1",
        "verb",
        "czytać",
        "Chcę przeczytać książkę.",
        {
            "en": w(
                "read",
                None,
                "/riːd/",
                {"past": "read", "participle": "read"},
                "I want to read a book.",
                "read",
            ),
            "de": w(
                "lesen",
                None,
                "/ˈleːzn̩/",
                {"present_3sg": "liest", "past": "las", "participle": "hat gelesen"},
                "Ich möchte ein Buch lesen.",
                "lesen",
            ),
            "es": w(
                "leer", None, "/leˈeɾ/", {"participle": "leído"}, "Quiero leer un libro.", "leer"
            ),
            "fr": w("lire", None, "/liʁ/", {"participle": "lu"}, "Je veux lire un livre.", "lire"),
        },
    ),
    (
        27,
        "a1",
        "verb",
        "spać",
        "Chcę teraz spać.",
        {
            "en": w(
                "sleep",
                None,
                "/sliːp/",
                {"past": "slept", "participle": "slept"},
                "I want to sleep now.",
                "sleep",
            ),
            "de": w(
                "schlafen",
                None,
                "/ˈʃlaːfn̩/",
                {"present_3sg": "schläft", "past": "schlief", "participle": "hat geschlafen"},
                "Ich möchte jetzt schlafen.",
                "schlafen",
            ),
            "es": w(
                "dormir",
                None,
                "/doɾˈmiɾ/",
                {"present_1sg": "duermo"},
                "Quiero dormir ahora.",
                "dormir",
            ),
            "fr": w(
                "dormir",
                None,
                "/dɔʁmiʁ/",
                {"participle": "dormi"},
                "Je veux dormir maintenant.",
                "dormir",
            ),
        },
    ),
    (
        28,
        "a1",
        "verb",
        "mieszkać",
        "Chcemy mieszkać w Krakowie.",
        {
            "en": w(
                "live",
                None,
                "/lɪv/",
                {"past": "lived", "participle": "lived"},
                "We want to live in Kraków.",
                "live",
            ),
            "de": w(
                "wohnen",
                None,
                "/ˈvoːnən/",
                {"past": "wohnte", "participle": "hat gewohnt"},
                "Wir möchten in Krakau wohnen.",
                "wohnen",
            ),
            "es": w("vivir", None, "/biˈbiɾ/", {}, "Queremos vivir en Cracovia.", "vivir"),
            "fr": w(
                "habiter",
                None,
                "/abite/",
                {"participle": "habité"},
                "Nous voulons habiter à Cracovie.",
                "habiter",
            ),
        },
    ),
    (
        29,
        "a1",
        "verb",
        "pracować",
        "Muszę dziś pracować.",
        {
            "en": w(
                "work",
                None,
                "/wɜːk/",
                {"past": "worked", "participle": "worked"},
                "I have to work today.",
                "work",
            ),
            "de": w(
                "arbeiten",
                None,
                "/ˈaʁbaɪ̯tn̩/",
                {"past": "arbeitete", "participle": "hat gearbeitet"},
                "Ich muss heute arbeiten.",
                "arbeiten",
            ),
            "es": w("trabajar", None, "/tɾabaˈxaɾ/", {}, "Tengo que trabajar hoy.", "trabajar"),
            "fr": w(
                "travailler",
                None,
                "/tʁavaje/",
                {"participle": "travaillé"},
                "Je dois travailler aujourd'hui.",
                "travailler",
            ),
        },
    ),
    (
        30,
        "a1",
        "verb",
        "kupować",
        "Chcę kupić chleb.",
        {
            "en": w(
                "buy",
                None,
                "/baɪ/",
                {"past": "bought", "participle": "bought"},
                "I want to buy bread.",
                "buy",
            ),
            "de": w(
                "kaufen",
                None,
                "/ˈkaʊ̯fn̩/",
                {"past": "kaufte", "participle": "hat gekauft"},
                "Ich möchte Brot kaufen.",
                "kaufen",
            ),
            "es": w("comprar", None, "/komˈpɾaɾ/", {}, "Quiero comprar pan.", "comprar"),
            "fr": w(
                "acheter",
                None,
                "/aʃte/",
                {"present_1sg": "j'achète", "participle": "acheté"},
                "Je veux acheter du pain.",
                "acheter",
            ),
        },
    ),
    (
        31,
        "a1",
        "adj",
        "duży",
        "Ten pies jest duży.",
        {
            "en": w(
                "big",
                None,
                "/bɪɡ/",
                {"comparative": "bigger"},
                "This dog is big.",
                "big",
                accept=["large"],
            ),
            "de": w(
                "groß", None, "/ɡʁoːs/", {"comparative": "größer"}, "Dieser Hund ist groß.", "groß"
            ),
            "es": w("grande", None, "/ˈɡɾande/", {}, "Este perro es grande.", "grande"),
            "fr": w("grand", None, "/ɡʁɑ̃/", {"feminine": "grande"}, "Ce chien est grand.", "grand"),
        },
    ),
    (
        32,
        "a1",
        "adj",
        "mały",
        "Ten kot jest mały.",
        {
            "en": w(
                "small",
                None,
                "/smɔːl/",
                {"comparative": "smaller"},
                "This cat is small.",
                "small",
                accept=["little"],
            ),
            "de": w(
                "klein",
                None,
                "/klaɪ̯n/",
                {"comparative": "kleiner"},
                "Diese Katze ist klein.",
                "klein",
            ),
            "es": w(
                "pequeño",
                None,
                "/peˈkeɲo/",
                {"feminine": "pequeña"},
                "Este gato es pequeño.",
                "pequeño",
            ),
            "fr": w("petit", None, "/pəti/", {"feminine": "petite"}, "Ce chat est petit.", "petit"),
        },
    ),
    (
        33,
        "a1",
        "adj",
        "dobry",
        "Ten chleb jest dobry.",
        {
            "en": w(
                "good", None, "/ɡʊd/", {"comparative": "better"}, "This bread is good.", "good"
            ),
            "de": w(
                "gut", None, "/ɡuːt/", {"comparative": "besser"}, "Dieses Brot ist gut.", "gut"
            ),
            "es": w(
                "bueno", None, "/ˈbweno/", {"feminine": "buena"}, "Este pan es bueno.", "bueno"
            ),
            "fr": w("bon", None, "/bɔ̃/", {"feminine": "bonne"}, "Ce pain est bon.", "bon"),
        },
    ),
    (
        34,
        "a1",
        "adj",
        "nowy",
        "Ten nauczyciel jest nowy.",
        {
            "en": w("new", None, "/njuː/", {"comparative": "newer"}, "This teacher is new.", "new"),
            "de": w(
                "neu", None, "/nɔʏ̯/", {"comparative": "neuer"}, "Dieser Lehrer ist neu.", "neu"
            ),
            "es": w(
                "nuevo", None, "/ˈnwebo/", {"feminine": "nueva"}, "Este profesor es nuevo.", "nuevo"
            ),
            "fr": w(
                "nouveau",
                None,
                "/nuvo/",
                {"feminine": "nouvelle"},
                "Ce professeur est nouveau.",
                "nouveau",
            ),
        },
    ),
    (
        35,
        "a1",
        "adj",
        "stary",
        "Ten most jest stary.",
        {
            "en": w("old", None, "/əʊld/", {"comparative": "older"}, "This bridge is old.", "old"),
            "de": w("alt", None, "/alt/", {"comparative": "älter"}, "Diese Brücke ist alt.", "alt"),
            "es": w(
                "viejo", None, "/ˈbjexo/", {"feminine": "vieja"}, "Este puente es viejo.", "viejo"
            ),
            "fr": w("vieux", None, "/vjø/", {"feminine": "vieille"}, "Ce pont est vieux.", "vieux"),
        },
    ),
    (
        36,
        "a1",
        "adj",
        "gorący",
        "Kawa jest gorąca.",
        {
            "en": w("hot", None, "/hɒt/", {"comparative": "hotter"}, "The coffee is hot.", "hot"),
            "de": w(
                "heiß", None, "/haɪ̯s/", {"comparative": "heißer"}, "Der Kaffee ist heiß.", "heiß"
            ),
            "es": w("caliente", None, "/kaˈljente/", {}, "El café está caliente.", "caliente"),
            "fr": w("chaud", None, "/ʃo/", {"feminine": "chaude"}, "Le café est chaud.", "chaud"),
        },
    ),
    (
        37,
        "a1",
        "adj",
        "zimny",
        "Sok jest zimny.",
        {
            "en": w(
                "cold", None, "/kəʊld/", {"comparative": "colder"}, "The juice is cold.", "cold"
            ),
            "de": w(
                "kalt", None, "/kalt/", {"comparative": "kälter"}, "Der Saft ist kalt.", "kalt"
            ),
            "es": w("frío", None, "/ˈfɾio/", {"feminine": "fría"}, "El zumo está frío.", "frío"),
            "fr": w("froid", None, "/fʁwa/", {"feminine": "froide"}, "Le jus est froid.", "froid"),
        },
    ),
    (
        38,
        "a1",
        "adv",
        "dzisiaj, dziś",
        "Dzisiaj jest poniedziałek.",
        {
            "en": w("today", None, "/təˈdeɪ/", {}, "Today is Monday.", "Today"),
            "de": w("heute", None, "/ˈhɔʏ̯tə/", {}, "Heute ist Montag.", "Heute"),
            "es": w("hoy", None, "/oi/", {}, "Hoy es lunes.", "Hoy"),
            "fr": w(
                "aujourd'hui", None, "/oʒuʁdɥi/", {}, "Aujourd'hui, c'est lundi.", "Aujourd'hui"
            ),
        },
    ),
    (
        39,
        "a1",
        "interj",
        "dziękuję",
        "Dziękuję za pomoc.",
        {
            "en": w(
                "thank you",
                None,
                "/ˈθæŋk juː/",
                {},
                "Thank you for your help.",
                "Thank you",
                accept=["thanks"],
            ),
            "de": w(
                "danke",
                None,
                "/ˈdaŋkə/",
                {},
                "Danke für die Hilfe.",
                "Danke",
                accept=["danke schön", "danke sehr"],
            ),
            "es": w("gracias", None, "/ˈɡɾaθjas/", {}, "Gracias por la ayuda.", "Gracias"),
            "fr": w("merci", None, "/mɛʁsi/", {}, "Merci pour ton aide.", "Merci"),
        },
    ),
    (
        40,
        "a1",
        "particle",
        "tak",
        "Tak, to prawda.",
        {
            "en": w("yes", None, "/jes/", {}, "Yes, that's true.", "Yes"),
            "de": w("ja", None, "/jaː/", {}, "Ja, das stimmt.", "Ja"),
            "es": w("sí", None, "/si/", {}, "Sí, es verdad.", "Sí"),
            "fr": w("oui", None, "/wi/", {}, "Oui, c'est vrai.", "Oui"),
        },
    ),
    (
        41,
        "a2",
        "noun",
        "lotnisko",
        "Lotnisko jest daleko od miasta.",
        {
            "en": w(
                "airport",
                None,
                "/ˈeəpɔːt/",
                {"plural": "airports"},
                "The airport is far from the city.",
                "airport",
            ),
            "de": w(
                "der Flughafen",
                "m",
                "/ˈfluːkˌhaːfn̩/",
                {"plural": "die Flughäfen"},
                "Der Flughafen ist weit von der Stadt entfernt.",
                "Der Flughafen",
            ),
            "es": w(
                "el aeropuerto",
                "m",
                "/aeɾoˈpweɾto/",
                {"plural": "los aeropuertos"},
                "El aeropuerto está lejos de la ciudad.",
                "El aeropuerto",
            ),
            "fr": w(
                "l'aéroport",
                "m",
                "/aeʁɔpɔʁ/",
                {"plural": "les aéroports"},
                "L'aéroport est loin de la ville.",
                "L'aéroport",
            ),
        },
    ),
    (
        42,
        "a2",
        "noun",
        "pociąg",
        "Pociąg odjeżdża o ósmej.",
        {
            "en": w(
                "train",
                None,
                "/treɪn/",
                {"plural": "trains"},
                "The train leaves at eight.",
                "train",
            ),
            "de": w(
                "der Zug",
                "m",
                "/t͡suːk/",
                {"plural": "die Züge"},
                "Der Zug fährt um acht ab.",
                "Der Zug",
            ),
            "es": w(
                "el tren",
                "m",
                "/tɾen/",
                {"plural": "los trenes"},
                "El tren sale a las ocho.",
                "El tren",
            ),
            "fr": w(
                "le train",
                "m",
                "/tʁɛ̃/",
                {"plural": "les trains"},
                "Le train part à huit heures.",
                "Le train",
            ),
        },
    ),
    (
        43,
        "a2",
        "noun",
        "pogoda",
        "Pogoda się zmienia.",
        {
            "en": w("weather", None, "/ˈweðə/", {}, "The weather is changing.", "weather"),
            "de": w("das Wetter", "n", "/ˈvɛtɐ/", {}, "Das Wetter ändert sich.", "Das Wetter"),
            "es": w("el tiempo", "m", "/ˈtjempo/", {}, "El tiempo está cambiando.", "El tiempo"),
            "fr": w("le temps", "m", "/tɑ̃/", {}, "Le temps change.", "Le temps"),
        },
    ),
    (
        44,
        "a2",
        "noun",
        "lekarz",
        "Lekarz jest w szpitalu.",
        {
            "en": w(
                "doctor",
                None,
                "/ˈdɒktə/",
                {"plural": "doctors"},
                "The doctor is at the hospital.",
                "doctor",
            ),
            "de": w(
                "der Arzt",
                "m",
                "/aːɐ̯t͡st/",
                {"plural": "die Ärzte", "feminine": "die Ärztin"},
                "Der Arzt ist im Krankenhaus.",
                "Der Arzt",
            ),
            "es": w(
                "el médico",
                "m",
                "/ˈmediko/",
                {"plural": "los médicos", "feminine": "la médica"},
                "El médico está en el hospital.",
                "El médico",
            ),
            "fr": w(
                "le médecin",
                "m",
                "/medsɛ̃/",
                {"plural": "les médecins"},
                "Le médecin est à l'hôpital.",
                "Le médecin",
            ),
        },
    ),
    (
        45,
        "a2",
        "noun",
        "klucz",
        "Klucz jest w drzwiach.",
        {
            "en": w("key", None, "/kiː/", {"plural": "keys"}, "The key is in the door.", "key"),
            "de": w(
                "der Schlüssel",
                "m",
                "/ˈʃlʏsl̩/",
                {"plural": "die Schlüssel"},
                "Der Schlüssel steckt in der Tür.",
                "Der Schlüssel",
            ),
            "es": w(
                "la llave",
                "f",
                "/ˈʎabe/",
                {"plural": "las llaves"},
                "La llave está en la puerta.",
                "La llave",
            ),
            "fr": w(
                "la clé",
                "f",
                "/kle/",
                {"plural": "les clés"},
                "La clé est sur la porte.",
                "La clé",
                accept=["la clef"],
            ),
        },
    ),
    (
        46,
        "a2",
        "noun",
        "okno",
        "Okno jest otwarte.",
        {
            "en": w(
                "window", None, "/ˈwɪndəʊ/", {"plural": "windows"}, "The window is open.", "window"
            ),
            "de": w(
                "das Fenster",
                "n",
                "/ˈfɛnstɐ/",
                {"plural": "die Fenster"},
                "Das Fenster ist offen.",
                "Das Fenster",
            ),
            "es": w(
                "la ventana",
                "f",
                "/benˈtana/",
                {"plural": "las ventanas"},
                "La ventana está abierta.",
                "La ventana",
            ),
            "fr": w(
                "la fenêtre",
                "f",
                "/fənɛtʁ/",
                {"plural": "les fenêtres"},
                "La fenêtre est ouverte.",
                "La fenêtre",
            ),
        },
    ),
    (
        47,
        "a2",
        "noun",
        "łóżko",
        "Łóżko jest wygodne.",
        {
            "en": w("bed", None, "/bed/", {"plural": "beds"}, "The bed is comfortable.", "bed"),
            "de": w(
                "das Bett",
                "n",
                "/bɛt/",
                {"plural": "die Betten"},
                "Das Bett ist bequem.",
                "Das Bett",
            ),
            "es": w(
                "la cama", "f", "/ˈkama/", {"plural": "las camas"}, "La cama es cómoda.", "La cama"
            ),
            "fr": w(
                "le lit", "m", "/li/", {"plural": "les lits"}, "Le lit est confortable.", "Le lit"
            ),
        },
    ),
    (
        48,
        "a2",
        "noun",
        "pieniądze",
        "Pieniądze są w portfelu.",
        {
            "en": w("money", None, "/ˈmʌni/", {}, "The money is in the wallet.", "money"),
            "de": w("das Geld", "n", "/ɡɛlt/", {}, "Das Geld ist im Portemonnaie.", "Das Geld"),
            "es": w(
                "el dinero", "m", "/diˈneɾo/", {}, "El dinero está en la cartera.", "El dinero"
            ),
            "fr": w(
                "l'argent", "m", "/aʁʒɑ̃/", {}, "L'argent est dans le portefeuille.", "L'argent"
            ),
        },
    ),
    (
        49,
        "a2",
        "noun",
        "praca",
        "Praca zaczyna się o dziewiątej.",
        {
            "en": w("work", None, "/wɜːk/", {}, "Work starts at nine.", "Work", accept=["job"]),
            "de": w(
                "die Arbeit",
                "f",
                "/ˈaʁbaɪ̯t/",
                {"plural": "die Arbeiten"},
                "Die Arbeit beginnt um neun.",
                "Die Arbeit",
            ),
            "es": w(
                "el trabajo",
                "m",
                "/tɾaˈbaxo/",
                {"plural": "los trabajos"},
                "El trabajo empieza a las nueve.",
                "El trabajo",
            ),
            "fr": w(
                "le travail",
                "m",
                "/tʁavaj/",
                {"plural": "les travaux"},
                "Le travail commence à neuf heures.",
                "Le travail",
            ),
        },
    ),
    (
        50,
        "a2",
        "noun",
        "pytanie",
        "Pytanie jest trudne.",
        {
            "en": w(
                "question",
                None,
                "/ˈkwestʃən/",
                {"plural": "questions"},
                "The question is difficult.",
                "question",
            ),
            "de": w(
                "die Frage",
                "f",
                "/ˈfʁaːɡə/",
                {"plural": "die Fragen"},
                "Die Frage ist schwierig.",
                "Die Frage",
            ),
            "es": w(
                "la pregunta",
                "f",
                "/pɾeˈɡunta/",
                {"plural": "las preguntas"},
                "La pregunta es difícil.",
                "La pregunta",
            ),
            "fr": w(
                "la question",
                "f",
                "/kɛstjɔ̃/",
                {"plural": "les questions"},
                "La question est difficile.",
                "La question",
            ),
        },
    ),
    (
        51,
        "a2",
        "noun",
        "odpowiedź",
        "Odpowiedź jest prosta.",
        {
            "en": w(
                "answer", None, "/ˈɑːnsə/", {"plural": "answers"}, "The answer is simple.", "answer"
            ),
            "de": w(
                "die Antwort",
                "f",
                "/ˈantvɔʁt/",
                {"plural": "die Antworten"},
                "Die Antwort ist einfach.",
                "Die Antwort",
            ),
            "es": w(
                "la respuesta",
                "f",
                "/resˈpwesta/",
                {"plural": "las respuestas"},
                "La respuesta es sencilla.",
                "La respuesta",
            ),
            "fr": w(
                "la réponse",
                "f",
                "/ʁepɔ̃s/",
                {"plural": "les réponses"},
                "La réponse est simple.",
                "La réponse",
            ),
        },
    ),
    (
        52,
        "a2",
        "verb",
        "zapominać",
        "Nie chcę zapomnieć daty.",
        {
            "en": w(
                "forget",
                None,
                "/fəˈɡet/",
                {"past": "forgot", "participle": "forgotten"},
                "I don't want to forget the date.",
                "forget",
            ),
            "de": w(
                "vergessen",
                None,
                "/fɛɐ̯ˈɡɛsn̩/",
                {"present_3sg": "vergisst", "past": "vergaß", "participle": "hat vergessen"},
                "Ich möchte das Datum nicht vergessen.",
                "vergessen",
            ),
            "es": w("olvidar", None, "/olbiˈdaɾ/", {}, "No quiero olvidar la fecha.", "olvidar"),
            "fr": w(
                "oublier",
                None,
                "/ublije/",
                {"participle": "oublié"},
                "Je ne veux pas oublier la date.",
                "oublier",
            ),
        },
    ),
    (
        53,
        "a2",
        "verb",
        "pomagać",
        "Chcę pomóc bratu.",
        {
            "en": w(
                "help",
                None,
                "/help/",
                {"past": "helped", "participle": "helped"},
                "I want to help my brother.",
                "help",
            ),
            "de": w(
                "helfen",
                None,
                "/ˈhɛlfn̩/",
                {"present_3sg": "hilft", "past": "half", "participle": "hat geholfen"},
                "Ich möchte meinem Bruder helfen.",
                "helfen",
            ),
            "es": w("ayudar", None, "/aʝuˈdaɾ/", {}, "Quiero ayudar a mi hermano.", "ayudar"),
            "fr": w(
                "aider", None, "/ede/", {"participle": "aidé"}, "Je veux aider mon frère.", "aider"
            ),
        },
    ),
    (
        54,
        "a2",
        "verb",
        "czekać",
        "Muszę czekać na autobus.",
        {
            "en": w(
                "wait",
                None,
                "/weɪt/",
                {"past": "waited", "participle": "waited"},
                "I have to wait for the bus.",
                "wait",
            ),
            "de": w(
                "warten",
                None,
                "/ˈvaʁtn̩/",
                {"past": "wartete", "participle": "hat gewartet"},
                "Ich muss auf den Bus warten.",
                "warten",
            ),
            "es": w("esperar", None, "/espeˈɾaɾ/", {}, "Tengo que esperar el autobús.", "esperar"),
            "fr": w(
                "attendre",
                None,
                "/atɑ̃dʁ/",
                {"participle": "attendu"},
                "Je dois attendre le bus.",
                "attendre",
            ),
        },
    ),
    (
        55,
        "a2",
        "verb",
        "szukać",
        "Muszę poszukać kluczy.",
        {
            "en": w(
                "look for",
                None,
                "/lʊk fɔː/",
                {"past": "looked for", "participle": "looked for"},
                "I have to look for my keys.",
                "look for",
                accept=["search for"],
            ),
            "de": w(
                "suchen",
                None,
                "/ˈzuːxn̩/",
                {"past": "suchte", "participle": "hat gesucht"},
                "Ich muss meine Schlüssel suchen.",
                "suchen",
            ),
            "es": w("buscar", None, "/busˈkaɾ/", {}, "Tengo que buscar mis llaves.", "buscar"),
            "fr": w(
                "chercher",
                None,
                "/ʃɛʁʃe/",
                {"participle": "cherché"},
                "Je dois chercher mes clés.",
                "chercher",
            ),
        },
    ),
    (
        56,
        "a2",
        "adj",
        "zmęczony",
        "Mój ojciec jest zmęczony.",
        {
            "en": w(
                "tired",
                None,
                "/ˈtaɪəd/",
                {"comparative": "more tired"},
                "My father is tired.",
                "tired",
            ),
            "de": w(
                "müde", None, "/ˈmyːdə/", {"comparative": "müder"}, "Mein Vater ist müde.", "müde"
            ),
            "es": w(
                "cansado",
                None,
                "/kanˈsado/",
                {"feminine": "cansada"},
                "Mi padre está cansado.",
                "cansado",
            ),
            "fr": w(
                "fatigué",
                None,
                "/fatiɡe/",
                {"feminine": "fatiguée"},
                "Mon père est fatigué.",
                "fatigué",
            ),
        },
    ),
    (
        57,
        "a2",
        "adj",
        "szczęśliwy",
        "Mój brat jest szczęśliwy.",
        {
            "en": w(
                "happy",
                None,
                "/ˈhæpi/",
                {"comparative": "happier"},
                "My brother is happy.",
                "happy",
            ),
            "de": w(
                "glücklich",
                None,
                "/ˈɡlʏklɪç/",
                {"comparative": "glücklicher"},
                "Mein Bruder ist glücklich.",
                "glücklich",
            ),
            "es": w(
                "feliz", None, "/feˈliθ/", {"plural": "felices"}, "Mi hermano es feliz.", "feliz"
            ),
            "fr": w(
                "heureux",
                None,
                "/øʁø/",
                {"feminine": "heureuse"},
                "Mon frère est heureux.",
                "heureux",
            ),
        },
    ),
    (
        58,
        "a2",
        "adj",
        "trudny",
        "Ten egzamin jest trudny.",
        {
            "en": w(
                "difficult",
                None,
                "/ˈdɪfɪkəlt/",
                {"comparative": "more difficult"},
                "This exam is difficult.",
                "difficult",
                accept=["hard"],
            ),
            "de": w(
                "schwierig",
                None,
                "/ˈʃviːʁɪç/",
                {"comparative": "schwieriger"},
                "Diese Prüfung ist schwierig.",
                "schwierig",
                accept=["schwer"],
            ),
            "es": w("difícil", None, "/diˈfiθil/", {}, "Este examen es difícil.", "difícil"),
            "fr": w("difficile", None, "/difisil/", {}, "Cet examen est difficile.", "difficile"),
        },
    ),
    (
        59,
        "a2",
        "adj",
        "łatwy",
        "To ćwiczenie jest łatwe.",
        {
            "en": w(
                "easy", None, "/ˈiːzi/", {"comparative": "easier"}, "This exercise is easy.", "easy"
            ),
            "de": w(
                "leicht",
                None,
                "/laɪ̯çt/",
                {"comparative": "leichter"},
                "Diese Übung ist leicht.",
                "leicht",
                accept=["einfach"],
            ),
            "es": w("fácil", None, "/ˈfaθil/", {}, "Este ejercicio es fácil.", "fácil"),
            "fr": w("facile", None, "/fasil/", {}, "Cet exercice est facile.", "facile"),
        },
    ),
    (
        60,
        "a2",
        "adv",
        "często",
        "Często czytam wieczorem.",
        {
            "en": w("often", None, "/ˈɒfən/", {}, "I often read in the evening.", "often"),
            "de": w(
                "oft", None, "/ɔft/", {"comparative": "öfter"}, "Ich lese oft am Abend.", "oft"
            ),
            "es": w(
                "a menudo",
                None,
                "/a meˈnudo/",
                {},
                "A menudo leo por la noche.",
                "A menudo",
                accept=["con frecuencia"],
            ),
            "fr": w("souvent", None, "/suvɑ̃/", {}, "Je lis souvent le soir.", "souvent"),
        },
    ),
]

ARTICLES = ("der ", "die ", "das ", "el ", "la ", "le ", "l'")


def lemma_of(display: str, pos: str) -> str:
    if pos == "noun":
        for article in ARTICLES:
            if display.startswith(article):
                return display[len(article) :]
    return display


def entries() -> dict[str, dict[str, list[dict[str, Any]]]]:
    out: dict[str, dict[str, list[dict[str, Any]]]] = {lang: {"a1": [], "a2": []} for lang in LANGS}
    for number, level, pos, gloss, sentence_pl, words in CONCEPTS:
        concept = f"c{90000 + number:05d}"
        rank = number if level == "a1" else number - 40
        for lang in LANGS:
            word = words[lang]
            entry: dict[str, Any] = {
                "id": f"{lang}-{concept}",
                "concept": concept,
                "lang": lang,
                "level": level,
                "rank": rank,
                "pos": pos,
                "lemma": lemma_of(word["display"], pos),
                "display": word["display"],
            }
            if word["gender"]:
                entry["gender"] = word["gender"]
            if word["forms"]:
                entry["forms"] = word["forms"]
            if word["accept"]:
                entry["accept"] = word["accept"]
            entry["gloss"] = {"pl": gloss}
            entry["ipa"] = word["ipa"]
            entry["example"] = {
                "text": word["text"],
                "gap": word["gap"],
                "pl": word["pl"] or sentence_pl,
                "source": "vocabbot",
            }
            entry["sources"] = ["vocabbot"]
            entry["checked"] = True
            out[lang][level].append(entry)
    return out


def meta(lang: str, levels: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "lang": lang,
        "base": "pl",
        "title": "Kurs startowy",
        "version": VERSION,
        "levels": {level: len(items) for level, items in levels.items()},
        "license": "CC BY-SA 4.0",
        "sources": [
            {
                "id": "vocabbot",
                "name": "VocabBot starter course, written for this project",
                "license": "CC BY-SA 4.0",
            }
        ],
    }


def main() -> None:
    data = entries()
    for target in TARGETS:
        for lang, levels in data.items():
            folder = target / lang
            folder.mkdir(parents=True, exist_ok=True)
            for level, items in levels.items():
                lines = [json.dumps(item, ensure_ascii=False) for item in items]
                (folder / f"{level}.jsonl").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
            text = json.dumps(meta(lang, levels), ensure_ascii=False, indent=2) + "\n"
            (folder / "meta.json").write_bytes(text.encode("utf-8"))
        print("wrote", target.relative_to(REPO))


if __name__ == "__main__":
    main()
