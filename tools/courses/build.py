"""Build the A1-B2 courses from CEFR-J, Wiktionary, wordfreq and Tatoeba.

Every concept enters the courses through a decision: the model review
(tools/courses/review.jsonl) or the editors (tools/courses/editor.jsonl, which
wins where both decide). A decision names the sense, the Polish meaning and the
German, Spanish and French equivalents with their gender. The builder adds
article, forms and pronunciation from the Wiktionary entries, chooses an
example sentence with a Polish translation (the decisions of the example
review live in tools/courses/examples.jsonl), orders every level by frequency
after the editors' starting list, and writes one course file per language and
level. Corrections of single entries live in tools/courses/overrides.json.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from typing import Any

import wordfreq

from concepts import EDITOR_POS, Concept
from concepts import read as read_concepts
from sources import COURSES, TOOLS, WORK
from tatoeba import Corpus, course_links, polish_links, read_sentences, tokens
from wiktionary import load

LANGS = ("en", "de", "es", "fr", "it")
TARGETS = ("de", "es", "fr", "it")
# the languages the review chose in one pass; a language added later has its own file
FIRST_TARGETS = ("de", "es", "fr")
ADDED_REVIEWS = {"it": TOOLS / "review-it.jsonl"}
COURSE_POS = {"intj": "interj"}
ARTICLES = {
    "de": {"m": "der", "f": "die", "n": "das"},
    "es": {"m": "el", "f": "la"},
    "fr": {"m": "le", "f": "la"},
    "it": {"m": "il", "f": "la"},
}
PLURAL_ARTICLES = {"de": "die", "es": {"m": "los", "f": "las"}, "fr": "les"}
IT_VOWEL = tuple("aeiouhàèéìíòóùú")
IT_PLURAL = ("i", "gli", "le")
ARTICLE_WORDS = {
    "de": {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einen",
        "einem",
        "einer",
        "eines",
    },
    "es": {"el", "la", "los", "las", "un", "una", "unos", "unas", "del", "al"},
    "fr": {"le", "la", "les", "un", "une", "des", "du", "l'"},
    "it": {
        "il",
        "lo",
        "la",
        "l'",
        "i",
        "gli",
        "le",
        "un",
        "uno",
        "una",
        "un'",
        "del",
        "dello",
        "della",
        "dei",
        "degli",
        "delle",
    },
    "en": set(),
}
VOWEL_START = tuple("aeiouyàâäéèêëîïôöûüœæ")
# French words with an aspirated h take le/la, not l'. The Wiktionary extract
# does not mark them in a field the pipeline can read, so the common ones are listed.
H_ASPIRE = frozenset(
    [
        "hache",
        "hachis",
        "haie",
        "haillon",
        "haine",
        "haïr",
        "hall",
        "halle",
        "halte",
        "hamac",
        "hamburger",
        "hameau",
        "hamster",
        "hanche",
        "handball",
        "handicap",
        "hangar",
        "hanneton",
        "hanter",
        "happer",
        "harceler",
        "hardi",
        "hareng",
        "hargne",
        "haricot",
        "harnais",
        "harpe",
        "hasard",
        "hâte",
        "hausse",
        "haut",
        "hauteur",
        "havre",
        "hennir",
        "hérisson",
        "hernie",
        "héros",
        "hêtre",
        "heurt",
        "heurter",
        "hibou",
        "hideux",
        "hiérarchie",
        "hippie",
        "hisser",
        "hit",
        "hobby",
        "hockey",
        "hollandais",
        "homard",
        "hongrois",
        "honte",
        "honteux",
        "hoquet",
        "horde",
        "hors",
        "housse",
        "houx",
        "hublot",
        "huée",
        "huer",
        "huit",
        "huitième",
        "humer",
        "hurler",
        "hurlement",
        "hutte",
    ]
)
OVERRIDES = TOOLS / "overrides.json"
EDITOR = TOOLS / "editor.jsonl"
EXAMPLES = TOOLS / "examples.jsonl"
VERSION = "2026.11.5"  # raise it with every change of the sources or of the rules
MAX_ACCEPT = 3
# parts of speech that count as function words when a level is put in order
FUNCTION_POS = frozenset({"prep", "pron", "conj", "det", "particle"})
FUNCTION_WINDOW, FUNCTION_LIMIT = 10, 3  # at most 3 function words in any 10 entries
EXAMPLE_CANDIDATES = 3  # sentences the example review judges for one entry
# Plural articles, for nouns used only in the plural (die Eltern, les gens, los padres)
PLURAL_ONLY_ARTICLES = {"de": ("die",), "es": ("los", "las"), "fr": ("les",), "it": IT_PLURAL}
# A sentence with one of these words never becomes an example, whatever the
# example review says; the review judges everything else, including violence.
VULGAR_WORDS = {
    "en": r"fuck\w*|shit\w*|bitch\w*|bastards?|assholes?|dicks?|cocks?|pussy|whores?|sluts?|"
    r"porn\w*|cunts?|wank\w*|sex|sexual\w*|sexy",
    "de": r"schei(?:ß|ss)\w*|fick\w*|huren?|arsch\w*|fotzen?|wichs\w*|titten|sex|sexuell\w*|"
    r"sexy|nutten?|schlampen?",
    "es": r"putas?|putos?|mierda\w*|joder|jodid\w*|coño\w*|pollas?|cabr[oó]n\w*|gilipollas|"
    r"follar\w*|culos?|sexo|sexual\w*|sexy|maric[oó]n\w*|pendej\w*|vergas?|chingad\w*",
    "fr": r"merde\w*|putain\w*|putes?|salope\w*|connard\w*|connasse\w*|encul\w*|bites?|"
    r"couilles?|nique\w*|foutre|sexe|sexuel\w*|sexy|cul",
    "it": r"cazz\w*|merd\w*|stronz\w*|puttan\w*|troi[ae]|vaffanculo|fanculo|coglion\w*|"
    r"fottut\w*|fott\w*|culo|figa|fica|sesso|sessual\w*|sexy|porc[oa]\s+dio",
    "pl": r"kurw\w*|chuj\w*|huj\w*|pierdol\w*|pierdziel\w*|jeb\w*|zajeb\w*|pizd\w*|dziwk\w*|"
    r"skurwysyn\w*|cip\w*|seks\w*|fiut\w*|kutas\w*|dupa|dupy|dupie|dupę|dupą|dupek|dupka",
}
VULGAR = {
    lang: re.compile(rf"(?<!\w)(?:{words})(?!\w)", re.IGNORECASE)
    for lang, words in VULGAR_WORDS.items()
}


def vulgar(text: str, lang: str) -> bool:
    return bool(VULGAR[lang].search(text))


IPA = re.compile(r"^(/[^/]+/|\[[^\]]+\])$")


def valid_ipa(value: Any) -> str | None:
    """A transcription between slashes or brackets, as the course check wants it."""
    return value if isinstance(value, str) and IPA.match(value) else None


def zipf(text: str, lang: str) -> float:
    return float(wordfreq.zipf_frequency(text, lang))


def clean(word: str) -> str | None:
    text = re.sub(r"\s*\([^)]*\)", "", word).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or len(text.split()) > 3 or any(c.isdigit() for c in text):
        return None
    if any(c in text for c in '/,;:[]{}=+*"?!.'):
        return None
    return text


@dataclass
class Lexicon:
    by_word: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))

    def find(self, word: str, pos: str) -> dict[str, Any] | None:
        records = self.by_word.get(word, [])
        found = next((r for r in records if r.get("pos") == pos), None)
        if found is None:
            for prefix in ("sich ", "se ", "s'", "się "):
                if word.startswith(prefix):
                    return self.find(word[len(prefix) :], pos)
            if word.endswith(" się"):
                return self.find(word[: -len(" się")], pos)
        return found


def back_translates(record: dict[str, Any] | None, headword: str) -> bool:
    """The word's own English meanings name the headword.

    "vermuten" translates back to "guess": its meanings are "to suppose, to guess".
    """
    if not record:
        return False
    text = " ".join(record.get("gloss", [])).casefold()
    return re.search(rf"(?<![\w-]){re.escape(headword.casefold())}(?![\w-])", text) is not None


def load_lexicons() -> dict[str, Lexicon]:
    out = {}
    for lang in (*TARGETS, "pl"):
        lexicon = Lexicon()
        for record in load(f"lexicon-{lang}.jsonl"):
            lexicon.by_word[record["word"]].append(record)
        out[lang] = lexicon
    return out


def translation_groups(records: list[dict[str, Any]]) -> list[dict[str, list[dict[str, Any]]]]:
    """Translation tables in page order, each split by language."""
    groups: list[dict[str, list[dict[str, Any]]]] = []
    index: dict[tuple[int, str], int] = {}
    for number, record in enumerate(records):
        for item in record.get("translations", []):
            key = (number, item.get("sense") or "")
            if key not in index:
                index[key] = len(groups)
                groups.append(defaultdict(list))
            groups[index[key]][item["lang"]].append(item)
    return groups


GROUP_ORDER_PENALTY = 0.25  # per table: Wiktionary lists the main sense first more often than not


BACK_TRANSLATION_BONUS = 1.5  # an equivalent whose own entry names the English word
GROUP_BACK_TRANSLATION_WEIGHT = 1.5


@dataclass
class Context:
    """What the choices of one concept need: its headword, part of speech and the dictionaries."""

    headword: str
    pos: str
    lexicons: dict[str, Lexicon]


def word_score(word: str, order: int, lang: str, ctx: Context | None) -> float:
    """Common words first; bonuses for the first one listed, for a dictionary entry with the
    same part of speech and for a word that translates back to the headword; phrases cost."""
    value = zipf(word, lang)
    if order == 0:
        value += 0.8
    if ctx is not None:
        record = ctx.lexicons[lang].find(word, ctx.pos) if lang in ctx.lexicons else None
        if record is not None:
            value += 1.0
        if back_translates(record, ctx.headword):
            value += BACK_TRANSLATION_BONUS
    if " " in word:
        value -= 0.7
    return value


def rank_words(words: list[str], lang: str, ctx: Context | None = None) -> list[str]:
    ranked = sorted(
        enumerate(words), key=lambda item: (-word_score(item[1], item[0], lang, ctx), item[0])
    )
    return [word for _, word in ranked]


def group_score(
    group: dict[str, list[dict[str, Any]]], index: int, ctx: Context | None = None
) -> float:
    """How likely a translation table is the concept's main sense.

    The main sense of a common word has common translations ("line": linia,
    Linie), and its translations name the English word in their own entries
    ("Gebäude": building), whatever the order of the tables on the page.
    """
    best = []
    back = []
    for lang in ("pl", *FIRST_TARGETS):
        words = [w for w in (clean(i["word"]) for i in group.get(lang, [])) if w]
        if not words:
            continue
        best.append(max(zipf(w, lang) for w in words))
        if ctx is not None and lang in ctx.lexicons:
            back.append(
                any(
                    back_translates(ctx.lexicons[lang].find(w, ctx.pos), ctx.headword)
                    for w in words
                )
            )
    score = (sum(best) / len(best) if best else 0.0) - GROUP_ORDER_PENALTY * index
    if back:
        score += GROUP_BACK_TRANSLATION_WEIGHT * sum(back) / len(back)
    return score


def choose_group(
    groups: list[dict[str, list[dict[str, Any]]]], ctx: Context | None = None
) -> dict[str, list[dict[str, Any]]] | None:
    full = [
        (i, g)
        for i, g in enumerate(groups)
        if g.get("pl") and sum(1 for t in FIRST_TARGETS if g.get(t)) >= 2
    ]
    if full:
        return max(full, key=lambda pair: (group_score(pair[1], pair[0], ctx), -pair[0]))[1]
    return next((g for g in groups if g.get("pl")), None)


def polish_gloss(items: list[dict[str, Any]], ctx: Context | None = None) -> str | None:
    words: list[str] = []
    for item in items:
        word = clean(item["word"])
        if word and word not in words:
            words.append(word)
    if not words:
        return None
    ranked = rank_words(words, "pl", ctx)
    gloss = [ranked[0]]
    if len(ranked) > 1 and zipf(ranked[1], "pl") >= max(2.5, zipf(ranked[0], "pl") - 1.5):
        gloss.append(ranked[1])
    return ", ".join(gloss)


def genders_of(item: dict[str, Any], lexicon: Lexicon | None, word: str) -> list[str]:
    tags = item.get("tags") or []
    found = [
        {"masculine": "m", "feminine": "f", "neuter": "n"}[t]
        for t in tags
        if t in ("masculine", "feminine", "neuter")
    ]
    if not found and lexicon is not None:
        record = lexicon.find(word, "noun")
        if record:
            found = list(record.get("gender", []))
    return list(dict.fromkeys(found))


def italian_lo(word: str) -> bool:
    """A masculine Italian noun that takes lo (gli): s and a consonant, z, gn, ps, pn, x, y,
    and i before a vowel (lo studente, lo zio, lo gnomo, lo psicologo, lo iato)."""
    lower = word.lower()
    if lower[:1] == "s" and lower[1:2] and lower[1] not in "aeiouàèéìíòóùú":
        return True
    if lower[:1] == "i" and lower[1:2] and lower[1] in "aeiouàèéìíòóùú":
        return True
    return lower.startswith(("z", "gn", "ps", "pn", "x", "y"))


def italian_article(gender: str, word: str) -> str:
    lower = word.lower()
    if gender == "m" and italian_lo(word):
        return "lo"
    if lower.startswith(IT_VOWEL) and not (lower[:1] == "i" and lower[1:2] in tuple("aeiou")):
        return "l'"
    return ARTICLES["it"][gender]


def article_for(lang: str, gender: str, word: str, record: dict[str, Any] | None) -> str:
    if lang == "it":
        return italian_article(gender, word)
    if lang == "fr":
        aspirated = word.lower() in H_ASPIRE or (record or {}).get("h_aspire")
        if word.lower().startswith(VOWEL_START) or (word.lower().startswith("h") and not aspirated):
            return "l'"
        return ARTICLES["fr"][gender]
    if lang == "es" and gender == "f":
        ipa = str((record or {}).get("ipa") or "")
        if word.lower().startswith(("a", "á", "ha", "há")) and ipa.startswith("/ˈa"):
            return "el"
    return ARTICLES[lang][gender]


def with_article(article: str, word: str) -> str:
    return f"{article}{word}" if article.endswith("'") else f"{article} {word}"


def plural_display(lang: str, gender: str, plural: str) -> str:
    if lang == "it":
        lower = plural.lower()
        if gender == "f":
            return f"le {plural}"
        return (
            f"gli {plural}" if italian_lo(plural) or lower.startswith(IT_VOWEL) else f"i {plural}"
        )
    article = PLURAL_ARTICLES[lang]
    if isinstance(article, dict):
        article = article.get(gender, "los")
    return f"{article} {plural}"


@dataclass
class Word:
    lang: str
    lemma: str
    display: str
    gender: str | None = None
    accept: list[str] = field(default_factory=list)
    forms: dict[str, str] = field(default_factory=dict)
    ipa: str | None = None
    frequency: float = 0.0
    bare: bool = False  # a noun shown without an article (Spanish and French months)


def target_word(
    lang: str, pos: str, items: list[dict[str, Any]], lexicon: Lexicon, ctx: Context | None = None
) -> Word | None:
    candidates: list[tuple[float, int, Word]] = []
    usable = [(item, clean(item["word"])) for item in items]
    order_of = {
        word: rank for rank, word in enumerate(rank_words([w for _, w in usable if w], lang, ctx))
    }
    for item, word in usable:
        if not word:
            continue
        order = order_of[word]
        record = lexicon.find(word, pos)
        if pos == "noun":
            if lang == "de" and not word[:1].isupper():
                continue  # a German noun starts with a capital letter
            genders = [g for g in genders_of(item, lexicon, word) if g in ARTICLES[lang]]
            if not genders or "plural" in (item.get("tags") or []) or plural_only(record):
                continue
            gender = genders[0]
            article = article_for(lang, gender, word, record)
            display = with_article(article, word)
            alt = [with_article(article_for(lang, g, word, record), word) for g in genders[1:]]
            built = Word(lang, word, display, gender, accept=[a for a in alt if a != display])
        else:
            built = Word(lang, word, word)
        if record:
            built.ipa = valid_ipa(record.get("ipa"))
            built.forms = target_forms(lang, pos, built.gender, record)
        built.frequency = zipf(word, lang)
        candidates.append((float(order), order, built))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    best = candidates[0][2]
    for _, _, other in candidates[1:]:
        if len(best.accept) >= MAX_ACCEPT:
            break
        if (
            other.display != best.display
            and other.display not in best.accept
            and other.frequency >= 2.5
        ):
            best.accept.append(other.display)
    return best


def target_forms(lang: str, pos: str, gender: str | None, record: dict[str, Any]) -> dict[str, str]:
    forms: dict[str, str] = {}
    if pos == "noun" and record.get("plural") and gender:
        plural = record["plural"][0]
        if plural != "-":
            forms["plural"] = plural_display(lang, gender, plural)
    if pos == "adj" and lang in ("es", "fr", "it") and record.get("feminine"):
        forms["feminine"] = record["feminine"][0]
    if pos == "adj" and lang == "de" and record.get("comparative"):
        forms["comparative"] = record["comparative"][0]
    if pos == "verb":
        if lang == "de":
            if record.get("present_3sg"):
                forms["present_3sg"] = record["present_3sg"][0]
            if record.get("past"):
                forms["past"] = record["past"][0]
            if record.get("participle"):
                aux = (
                    "ist"
                    if "sein" in record.get("auxiliary", [])
                    and "haben" not in record.get("auxiliary", [])
                    else "hat"
                )
                forms["participle"] = f"{aux} {record['participle'][0]}"
        elif record.get("participle"):
            forms["participle"] = record["participle"][0]
    if lang == "it":
        forms = {key: italian_spelling(value) for key, value in forms.items()}
    return forms


ITALIAN_STRESS = str.maketrans("àèéìíòóùú", "aeeiioouu")


def italian_spelling(word: str) -> str:
    """Wiktionary marks the stress of Italian forms (organizzàto); the spelling keeps an
    accent only on a last vowel (città, perché)."""
    return re.sub(r"[àèéìíòóùú](?=\w)", lambda m: m.group(0).translate(ITALIAN_STRESS), word)


REVIEW = TOOLS / "review.jsonl"


def load_added_reviews() -> dict[str, dict[str, Any]]:
    """Equivalents in the languages added after the first review, by concept: {"it": {...}}."""
    out: dict[str, dict[str, Any]] = defaultdict(dict)
    for lang, path in ADDED_REVIEWS.items():
        if not path.is_file():
            continue
        for line in path.read_text("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["id"]][lang] = row[lang]
    return dict(out)


def load_review() -> dict[str, dict[str, Any]]:
    """Decisions of the model review (tools/courses/review.py), by concept."""
    if not REVIEW.is_file():
        return {}
    out = {}
    for line in REVIEW.read_text("utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def load_editor() -> dict[str, dict[str, Any]]:
    """Decisions of the editors (tools/courses/editor.jsonl), by concept.

    A row holds the fields of a review decision it sets ("pl", "de", "keep",
    ...) and may add "level" (another CEFR level), "en" (false for no English
    entry, or {"word": ...} for another English word), "start" (the place in
    the A1 starting list) and "note" (why the editors decided so).
    """
    if not EDITOR.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in EDITOR.read_text("utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["id"] in out:
                raise SystemExit(f"editor.jsonl names {row['id']} twice")
            out[row["id"]] = row
    return out


def decision_of(
    review: dict[str, Any] | None, edit: dict[str, Any] | None
) -> dict[str, Any] | None:
    """The review decision with the editors' fields over it."""
    if edit is None:
        return review
    return {**(review or {}), **edit}


def split_display(text: str, lang: str) -> tuple[str | None, str]:
    if lang in ("fr", "it") and text.casefold().startswith("l'"):
        return "l'", text[2:].strip()
    head, sep, rest = text.partition(" ")
    heads = {"il", "lo", "la"} if lang == "it" else {"der", "die", "das", "el", "la", "le"}
    if sep and head.casefold() in heads:
        return head.casefold(), rest.strip()
    return None, text


def review_article(
    lang: str, gender: str, core: str, given: str | None, record: dict[str, Any] | None
) -> str:
    """The article by the pipeline's rule where it has the data.

    The reviewed article only fills the gaps: a Spanish word without a
    pronunciation, a French word with h that the list does not name.
    """
    lower = core.lower()
    if (
        lang == "es"
        and gender == "f"
        and lower.startswith(("a", "á", "ha", "há"))
        and not (record or {}).get("ipa")
    ):
        return given if given in ("el", "la") else "la"  # no pronunciation to find the stress
    if (
        lang == "fr"
        and lower.startswith("h")
        and lower not in H_ASPIRE
        and not (record or {}).get("h_aspire")
    ):
        return (
            given
            if given in ("le", "la", "l'") and (given == "l'" or given == ARTICLES["fr"][gender])
            else "l'"
        )
    return article_for(lang, gender, core, record)


PLURAL_ARTICLES_ANY = {"los", "las", "les"}


def plural_only(record: dict[str, Any] | None) -> bool:
    """A noun used only in the plural: 'Gezeiten f pl (plural only)', 'Ohrenschmerzen m pl'."""
    if not record:
        return False
    head = str(record.get("head") or "")
    word = str(record.get("word") or "")
    rest = head[len(word) :] if head.startswith(word) else head
    return "pl" in rest.split("(")[0].split() or "plural only" in head


def plural_noun(lang: str, text: str, decision: dict[str, Any], lexicon: Lexicon) -> Word | None:
    """A noun used only in the plural, with its plural article: die Eltern, les gens.

    The decision says so with the gender "pl", or Wiktionary marks the noun as
    used only in the plural. Other nouns are shown in the singular.
    """
    head, _, core = text.partition(" ")
    article = head.casefold()
    if article not in PLURAL_ONLY_ARTICLES.get(lang, ()) or not core:
        return None
    if lang == "de" and not core[:1].isupper():
        return None
    if decision.get("gender") != "pl" and not plural_only(lexicon.find(core, "noun")):
        return None
    return Word(lang, core, f"{article} {core}", "pl")


def reviewed_word(lang: str, pos: str, decision: dict[str, Any], lexicon: Lexicon) -> Word | None:
    """The reviewed equivalent, with article, forms and pronunciation from the pipeline's rules."""
    text = " ".join(str(decision.get("word", "")).split())
    if not text:
        return None
    plural = plural_noun(lang, text, decision, lexicon) if pos == "noun" else None
    if pos == "noun" and decision.get("bare"):
        # "enero", "janvier": months go without an article in Spanish and French
        gender = decision.get("gender")
        if gender not in ARTICLES[lang]:
            return None
        article, core = split_display(text, lang)
        if article is not None and core:
            text = core  # "l'internet" from the review: the word goes without its article
        word = Word(lang, text, text, gender, bare=True)
        record = lexicon.find(text, "noun")
    elif plural is not None:
        word = plural
        record = lexicon.find(word.lemma, "noun")
    elif pos == "noun":
        plural_heads = PLURAL_ARTICLES_ANY | (set(IT_PLURAL) if lang == "it" else set())
        if text.split()[0].casefold() in plural_heads or decision.get("gender") == "none":
            return None  # a noun the course would have to show in the plural
        article, core = split_display(text, lang)
        if not core or core.split()[0].casefold() in plural_heads:
            return None
        gender = decision.get("gender")
        if gender not in ARTICLES[lang]:
            gender = next((g for g, a in ARTICLES[lang].items() if a == article), None)
            if gender is None and lang == "it" and article == "lo":
                gender = "m"
        if gender is None or not core or (lang == "de" and not core[:1].isupper()):
            return None
        record = lexicon.find(core, "noun")
        if plural_only(record):
            return None
        article = review_article(lang, gender, core, article, record)
        word = Word(lang, core, with_article(article, core), gender)
    else:
        record = lexicon.find(text, pos)
        word = Word(lang, text, text)
    also = [" ".join(str(a).split()) for a in decision.get("also", [])]
    word.accept = [a for a in also if a and a.casefold() != word.display.casefold()][:MAX_ACCEPT]
    if record:
        word.ipa = valid_ipa(record.get("ipa"))
        if word.gender != "pl":
            word.forms = target_forms(lang, pos, word.gender, record)
    word.frequency = zipf(word.lemma, lang)
    return word


def gloss_parts(text: str) -> list[str]:
    """'z (kimś, czymś), wraz z' -> ['z (kimś, czymś)', 'wraz z']: commas in brackets stay."""
    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [" ".join(p.split()) for p in parts]


def reviewed_gloss(text: str) -> str | None:
    parts: list[str] = []
    for part in gloss_parts(text):
        if part and part.casefold() not in (p.casefold() for p in parts):
            parts.append(part)
    return ", ".join(parts[:2]) or None


def english_word(
    concept: Concept,
    records: list[dict[str, Any]],
    others: list[dict[str, Any]] | None = None,
    headword: str | None = None,
) -> Word:
    """The English entry; `others` (entries of other parts of speech) give only the IPA."""
    headword = headword or concept.headword
    word = Word("en", headword, headword)
    record = records[0] if records else {}
    word.ipa = next(
        (valid_ipa(r.get("ipa")) for r in [*records, *(others or [])] if valid_ipa(r.get("ipa"))),
        None,
    )
    if concept.pos == "noun" and record.get("plural"):
        word.forms["plural"] = record["plural"][0]
    if concept.pos == "verb":
        if record.get("past"):
            word.forms["past"] = record["past"][0]
        if record.get("participle"):
            word.forms["participle"] = record["participle"][0]
    if concept.pos == "adj" and record.get("comparative"):
        word.forms["comparative"] = record["comparative"][0]
    word.frequency = zipf(headword, "en")
    return word


@dataclass
class Draft:
    concept: Concept
    gloss: str
    words: dict[str, Word]
    sense: str
    reviewed: bool = False
    edited: bool = False
    start: int | None = None  # place in the A1 starting list


def drafts(concepts: list[Concept]) -> tuple[list[Draft], Counter[str]]:
    """One draft per concept with a decision of the review or of the editors."""
    english: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    any_pos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in load("english.jsonl"):
        english[(record["word"], record["pos"])].append(record)
        any_pos[record["word"]].append(record)
    lexicons = load_lexicons()
    reviews = load_review()
    added = load_added_reviews()
    editor = load_editor()
    unknown = sorted(set(editor) - {c.id for c in concepts})
    if unknown:
        raise SystemExit(f"editor.jsonl names concepts that do not exist: {', '.join(unknown)}")
    out: list[Draft] = []
    missing: Counter[str] = Counter()
    for concept in concepts:
        review = reviews.get(concept.id)
        edit = editor.get(concept.id)
        decision = decision_of(review, edit)
        if decision is None:
            missing["no decision of the review or the editors"] += 1
            continue
        for lang, choice in added.get(concept.id, {}).items():
            if lang not in (edit or {}):
                # Italian months go without an article, as the Spanish and French ones do
                spanish = decision.get("es") or {}
                if spanish.get("bare"):
                    gender = choice.get("gender")
                    if gender not in ("m", "f"):
                        gender = spanish.get("gender")  # a month: masculine in both languages
                    choice = {**choice, "bare": True, "gender": gender}
                decision = {**decision, lang: choice}
        if not decision.get("keep", True):
            missing["left out by the review or the editors"] += 1
            continue
        gloss = reviewed_gloss(str(decision.get("pl") or ""))
        if gloss is None:
            missing["no Polish meaning"] += 1
            continue
        level = str(decision.get("level") or concept.level)
        start = decision.get("start")
        if start is not None and level != "a1":
            raise SystemExit(f"{concept.id} is on the starting list but not at level A1")
        pos = str(decision.get("pos") or concept.pos)
        if pos not in EDITOR_POS:
            raise SystemExit(f"{concept.id} has the unknown part of speech {pos!r}")
        concept = replace(concept, level=level, pos=pos)
        words: dict[str, Word] = {}
        en = decision.get("en", True)
        if en is not False:
            headword = str(en["word"]) if isinstance(en, dict) else concept.headword
            words["en"] = english_word(
                concept, english.get((headword, concept.pos), []), any_pos.get(headword), headword
            )
            if isinstance(en, dict):
                words["en"].accept = [str(a) for a in en.get("also", [])][:MAX_ACCEPT]
        for lang in TARGETS:
            word = reviewed_word(lang, concept.pos, decision.get(lang) or {}, lexicons[lang])
            if word is not None:
                words[lang] = word
            else:
                missing[f"no {lang} equivalent"] += 1
        out.append(
            Draft(
                concept,
                gloss,
                words,
                str(decision.get("sense") or ""),
                reviewed=review is not None,
                edited=edit is not None,
                start=int(start) if start is not None else None,
            )
        )
    return out, missing


# ---------------------------------------------------------------- examples


def find_gap(text: str, word: Word, pos: str) -> tuple[str, bool] | None:
    """The part of `text` the learner fills in, and whether it is the citation form."""
    if len(re.findall(rf"(?<!\w){re.escape(word.lemma)}(?!\w)", text, re.IGNORECASE)) != 1:
        return None  # a second occurrence would show the answer
    phrases = [word.display, word.lemma] if word.display != word.lemma else [word.lemma]
    for phrase in phrases:
        found = list(re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.IGNORECASE))
        if len(found) != 1:
            continue
        match = found[0]
        if phrase == word.display:
            return match.group(0), True
        start = match.start()
        if pos == "noun" and word.lang == "de" and not match.group(0)[:1].isupper():
            return None  # a German noun is capitalised; "unentschieden" is the adjective
        if pos == "noun" and word.lang in ARTICLES:
            before = text[:start]
            previous = re.search(r"(\w+'|\w+\s)$", before)
            if previous and previous.group(1).strip().casefold() in ARTICLE_WORDS[word.lang]:
                start = previous.start(1)
            elif start == 0:
                return None  # "Schlag einen Nagel ein": at the start without an article, a verb
        gap = text[start : match.end()]
        if len(re.findall(rf"(?<!\w){re.escape(gap)}(?!\w)", text)) != 1:
            continue
        return gap, word.display == word.lemma
    return None


def stems(gloss: str) -> list[str]:
    """Beginnings of the Polish words of a meaning, to find them inflected in a sentence."""
    words = [w for part in gloss.split(",") for w in part.split() if len(w) >= 3]
    return [w[: max(3, len(w) - 3)].casefold() for w in words]


def article_homograph(word: Word, pos: str) -> bool:
    """A pronoun, numeral or other word spelt like an article ("la", "les", "das")."""
    return pos not in ("det", "article") and word.lemma.casefold() in ARTICLE_WORDS[word.lang]


def used_as_article(text: str, gap: str) -> bool:
    """In German an article is followed by a capitalised noun: "das Buch", not "das ist"."""
    found = re.search(rf"(?<!\w){re.escape(gap)}\s+(\w)", text)
    return bool(found and found.group(1).isupper())


def example_candidates(
    word: Word, pos: str, gloss: str, corpus: Corpus, limit: int = EXAMPLE_CANDIDATES
) -> list[dict[str, Any]]:
    """The best sentences for an entry, best first: a direct Polish translation, a
    translation that names the meaning, the citation form, about seven words."""
    if article_homograph(word, pos) and word.lang != "de":
        # a sentence cannot tell "la" the pronoun from "la" the article without a parser,
        # so these entries are asked without a sentence
        return []
    scored: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    polish_stems = stems(gloss)
    for sid in corpus.candidates(word.lemma):
        sentence = corpus.sentences[sid]
        found = find_gap(sentence.text, word, pos)
        if found is None:
            continue
        gap, citation = found
        if article_homograph(word, pos) and used_as_article(sentence.text, gap):
            continue
        polish, route = corpus.polish[sid]
        if vulgar(sentence.text, word.lang) or vulgar(polish.text, "pl"):
            continue
        indirect = 0 if route == "direct" else 1 if route == "en" else 3 if "+" in route else 2
        count = len(tokens(sentence.text))
        mentions = any(s in polish.text.casefold() for s in polish_stems)
        if route != "direct" and not mentions:
            continue  # a translation through another language must still carry the meaning
        score = (indirect, not mentions, not citation, abs(count - 7), len(sentence.text), sid)
        scored.append(
            (
                score,
                {
                    "sid": sid,
                    "text": sentence.text,
                    "gap": gap,
                    "pl": polish.text,
                    "source": f"tatoeba:{sid}",
                    "pl_source": f"tatoeba:{polish.id}",
                    "users": [sentence.user, polish.user],
                },
            )
        )
    scored.sort(key=lambda item: item[0])
    return [example for _, example in scored[:limit]]


def load_examples() -> dict[str, dict[str, Any]]:
    """Decisions of the example review (tools/courses/examples.py), by entry."""
    if not EXAMPLES.is_file():
        return {}
    out = {}
    for line in EXAMPLES.read_text("utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["entry"]] = row
    return out


def pick_example(
    candidates: list[dict[str, Any]], decision: dict[str, Any] | None, used: set[int]
) -> tuple[dict[str, Any] | None, str]:
    """The example of an entry and how it was chosen: reviewed, rejected or unreviewed.

    The example review chose among the same candidates, so its choice holds
    while the sources stay the same. Without a decision the first sentence no
    other entry uses wins.
    """
    if decision is not None:
        chosen = decision.get("sentence")
        if chosen is None:
            return None, "rejected"
        match = next((c for c in candidates if c["sid"] == chosen), None)
        if match is not None:
            used.add(chosen)
            return match, "reviewed"
    if not candidates:
        return None, "none"
    choice = next((c for c in candidates if c["sid"] not in used), candidates[0])
    used.add(choice["sid"])
    return choice, "unreviewed"


# ---------------------------------------------------------------- assembly


def apply_overrides(entries: dict[str, dict[str, dict[str, Any]]]) -> int:
    if not OVERRIDES.is_file():
        return 0
    data = json.loads(OVERRIDES.read_text("utf-8"))
    applied = 0
    for key, change in data.items():
        if key.startswith("_"):
            continue
        lang, _, concept = key.partition("-")
        if lang == "all":
            for per_lang in entries.values():
                if concept in per_lang and change.get("drop"):
                    del per_lang[concept]
                    applied += 1
            continue
        entry = entries.get(lang, {}).get(concept)
        if entry is None:
            continue
        if change.get("drop"):
            del entries[lang][concept]
        else:
            for field_name, value in change.items():
                if value is None:
                    entry.pop(field_name, None)
                else:
                    entry[field_name] = value
        applied += 1
    return applied


def entry_of(draft: Draft, word: Word, example: dict[str, Any] | None) -> dict[str, Any]:
    concept = draft.concept
    entry: dict[str, Any] = {
        "id": f"{word.lang}-{concept.id}",
        "concept": concept.id,
        "lang": word.lang,
        "level": concept.level,
        "rank": 0,
        "pos": COURSE_POS.get(concept.pos, concept.pos),
        "lemma": word.lemma,
        "display": word.display,
    }
    if word.gender:
        entry["gender"] = word.gender
    if word.bare:
        entry["bare"] = True
    if word.forms:
        entry["forms"] = word.forms
    if word.accept:
        entry["accept"] = word.accept
    entry["gloss"] = {"pl": draft.gloss}
    if word.ipa:
        entry["ipa"] = word.ipa
    if example:
        entry["example"] = {k: example[k] for k in ("text", "gap", "pl", "source", "pl_source")}
    entry["sources"] = (
        (["cefrj"] if concept.from_cefrj else [])
        + ["enwiktionary", "wordfreq"]
        + (["review"] if draft.reviewed else [])
        + (["editor"] if draft.edited else [])
        + (["tatoeba"] if example else [])
    )
    entry["checked"] = False
    entry["_frequency"] = word.frequency
    # where one form serves several concepts, the more basic concept keeps it
    english = draft.words.get("en")
    entry["_concept_frequency"] = english.frequency if english else zipf(concept.headword, "en")
    entry["_start"] = draft.start if draft.start is not None else 10**6
    entry["_users"] = example["users"] if example else []
    return entry


MERGES: list[tuple[str, str, str, str, str]] = []


def synonyms(a: str, b: str, lang: str, families: dict[str, dict[str, str]]) -> bool:
    """Two concepts with one Polish meaning are synonyms.

    That holds when another course language has one word for both.
    """
    first, second = families.get(a, {}), families.get(b, {})
    return any(
        other not in (lang, "en") and first.get(other) and first.get(other) == second.get(other)
        for other in ("en", *FIRST_TARGETS)
    )


def merge_duplicates(
    entries: dict[str, dict[str, Any]], families: dict[str, dict[str, str]]
) -> int:
    """One entry per answer in a language.

    Entries with one Polish meaning become one entry with more accepted
    answers when they are synonyms. Polish homonyms ("rakieta" for racket and
    rocket) stay apart with a hint naming the English word; in the English
    course such a hint would give the answer away, so the rarer one goes.
    """
    order = sorted(
        entries.values(),
        key=lambda e: (
            e["level"],
            e.get("_start", 10**6),
            -e["_frequency"],
            -e.get("_concept_frequency", 0.0),
            e["concept"],
        ),
    )
    # one answer may serve two parts of speech ("work": praca, pracować), not one meaning twice
    by_display: dict[tuple[str, str, str], dict[str, Any]] = {}
    merged = 0
    by_meaning: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in order:
        display = entry["display"]
        gloss = entry["gloss"]["pl"].casefold()
        meaning = (gloss, entry["pos"])
        keeper = by_display.get(("pos", display, entry["pos"])) or by_display.get(
            ("gloss", display.casefold(), gloss)
        )
        if keeper is None:
            keeper = next(
                (
                    k
                    for k in by_meaning[meaning]
                    if synonyms(k["concept"], entry["concept"], entry["lang"], families)
                ),
                None,
            )
        if keeper is None and by_meaning[meaning] and entry["lang"] == "en":
            keeper = by_meaning[meaning][0]
            MERGES.append(
                (
                    entry["lang"],
                    keeper["display"],
                    entry["display"],
                    "homonym dropped",
                    entry["gloss"]["pl"],
                )
            )
            del entries[entry["concept"]]
            merged += 1
            continue
        if keeper is None:
            if by_meaning[meaning]:
                for other in [*by_meaning[meaning], entry]:
                    english = families.get(other["concept"], {}).get("en")
                    if english:
                        other["hint"] = f"ang. {english}"
            by_display[("pos", display, entry["pos"])] = entry
            by_display[("gloss", display.casefold(), gloss)] = entry
            by_meaning[meaning].append(entry)
            continue
        MERGES.append(
            (
                entry["lang"],
                keeper["display"],
                entry["display"],
                keeper["gloss"]["pl"],
                entry["gloss"]["pl"],
            )
        )
        accept = keeper.setdefault("accept", [])
        if (
            entry["display"] != keeper["display"]
            and entry["display"] not in accept
            and len(accept) < MAX_ACCEPT + 2
        ):
            accept.append(entry["display"])
        del entries[entry["concept"]]
        merged += 1
    return merged


def ordered(items: list[dict[str, Any]], start: dict[str, int]) -> list[dict[str, Any]]:
    """The entries of one level: the editors' starting list, then frequency.

    Any ten entries in a row hold at most three function words, so the first
    sessions bring nouns, verbs and adjectives next to "und", "in" and "zu".
    """
    first = sorted((e for e in items if e["concept"] in start), key=lambda e: start[e["concept"]])
    pending = sorted(
        (e for e in items if e["concept"] not in start),
        key=lambda e: (-e["_frequency"], e["concept"]),
    )
    out = list(first)
    while pending:
        recent = out[-(FUNCTION_WINDOW - 1) :]
        crowded = sum(1 for e in recent if e["pos"] in FUNCTION_POS) >= FUNCTION_LIMIT
        index = 0
        if crowded:
            index = next((i for i, e in enumerate(pending) if e["pos"] not in FUNCTION_POS), 0)
        out.append(pending.pop(index))
    return out


def build(sample_only: bool = False) -> dict[str, Any]:
    concepts = read_concepts()
    built, missing = drafts(concepts)
    polish = read_sentences("pl")
    to_polish = polish_links()
    between = course_links()
    corpora = {lang: Corpus(lang, polish, to_polish, between) for lang in LANGS}
    decisions = load_examples()
    entries: dict[str, dict[str, dict[str, Any]]] = {lang: {} for lang in LANGS}
    candidates: dict[str, list[dict[str, Any]]] = {}
    how: dict[str, str] = {}
    for lang in LANGS:
        used: set[int] = set()
        for draft in sorted(
            built, key=lambda d: (d.concept.level, -d.words.get(lang, Word(lang, "", "")).frequency)
        ):
            word = draft.words.get(lang)
            if word is None:
                continue
            entry_id = f"{lang}-{draft.concept.id}"
            found = example_candidates(word, draft.concept.pos, draft.gloss, corpora[lang])
            example, how[entry_id] = pick_example(found, decisions.get(entry_id), used)
            candidates[entry_id] = found
            entry = entry_of(draft, word, example)
            entry["_sense"] = draft.sense
            entry["_headword"] = draft.concept.headword
            entries[lang][draft.concept.id] = entry
    families: dict[str, dict[str, str]] = defaultdict(dict)
    for lang in LANGS:
        for concept, entry in entries[lang].items():
            families[concept][lang] = entry["display"]
    merged = {lang: merge_duplicates(entries[lang], families) for lang in LANGS}
    overrides = apply_overrides(entries)
    start = {d.concept.id: d.start for d in built if d.start is not None}
    report: dict[str, Any] = {
        "concepts": len(concepts),
        "drafts": len(built),
        "missing": dict(missing),
        "merged": merged,
        "overrides": overrides,
        "examples": dict(
            Counter(how[f"{lang}-{concept}"] for lang in LANGS for concept in entries[lang])
        ),
        "languages": {},
    }
    for lang in LANGS:
        by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in entries[lang].values():
            by_level[entry["level"]].append(entry)
        stats = {}
        for level in sorted(by_level):
            items = ordered(by_level[level], start)
            by_level[level] = items
            for rank, entry in enumerate(items, 1):
                entry["rank"] = rank
            stats[level] = {
                "entries": len(items),
                "examples": sum(1 for e in items if "example" in e),
                "ipa": sum(1 for e in items if "ipa" in e),
            }
        report["languages"][lang] = stats
        if not sample_only:
            write_course(lang, by_level)
    write_candidates(entries, candidates)
    (WORK / "entries.json").write_bytes(json.dumps(entries, ensure_ascii=False).encode("utf-8"))
    merges = "".join("\t".join(m) + "\n" for m in MERGES)
    (WORK / "merges.tsv").write_bytes(merges.encode("utf-8"))
    (WORK / "report.json").write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return report


def write_candidates(
    entries: dict[str, dict[str, dict[str, Any]]], candidates: dict[str, list[dict[str, Any]]]
) -> None:
    """The candidate sentences of every entry in the courses, for the example review."""
    lines = []
    for lang in LANGS:
        for _concept, entry in sorted(entries[lang].items()):
            found = candidates.get(entry["id"], [])
            if not found:
                continue
            row = {
                "entry": entry["id"],
                "lang": lang,
                "word": entry["display"],
                "pos": entry["pos"],
                "meaning": entry["gloss"]["pl"],
                "headword": entry["_headword"],
                "sense": entry["_sense"],
                "candidates": [
                    {"sid": c["sid"], "text": c["text"], "gap": c["gap"], "pl": c["pl"]}
                    for c in found
                ],
            }
            lines.append(json.dumps(row, ensure_ascii=False))
    (WORK / "example-candidates.jsonl").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def write_course(lang: str, by_level: dict[str, list[dict[str, Any]]]) -> None:
    folder = COURSES / lang
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.jsonl"):
        old.unlink()
    attribution: list[str] = []
    for level, items in by_level.items():
        lines = []
        for entry in items:
            public = {k: v for k, v in entry.items() if not k.startswith("_")}
            lines.append(json.dumps(public, ensure_ascii=False))
            if "example" in entry:
                users = entry["_users"]
                attribution.append(
                    "\t".join(
                        [
                            entry["id"],
                            entry["example"]["source"],
                            users[0],
                            entry["example"]["pl_source"],
                            users[1],
                        ]
                    )
                )
        (folder / f"{level}.jsonl").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    attribution.sort()
    header = "entry\tsentence\tauthor\tpolish_sentence\tpolish_author"
    (folder / "sentences.tsv").write_bytes(
        ("\n".join([header, *attribution]) + "\n").encode("utf-8")
    )
    meta = {
        "lang": lang,
        "base": "pl",
        "title": "VocabBot A1–B2",
        "version": VERSION,
        "levels": {level: len(items) for level, items in sorted(by_level.items())},
        "license": "CC BY-SA 4.0",
        "sources": [
            {
                "id": "cefrj",
                "name": "The CEFR-J Wordlist Version 1.5, compiled by Yukio Tono, "
                "Tokyo University of Foreign Studies (levels of the concepts)",
                "url": "https://github.com/openlanguageprofiles/olp-en-cefrj",
            },
            {
                "id": "enwiktionary",
                "name": "English Wiktionary, extracted by wiktextract (kaikki.org), "
                "dump of 2026-10-01",
                "license": "CC BY-SA 4.0 and GFDL",
                "url": "https://kaikki.org/dictionary/",
            },
            {
                "id": "wordfreq",
                "name": "wordfreq 3.1.1 (order of the words)",
                "license": "CC BY-SA 4.0",
                "url": "https://github.com/rspeer/wordfreq",
            },
            {
                "id": "tatoeba",
                "name": "Tatoeba example sentences; authors in sentences.tsv",
                "license": "CC BY 2.0 FR",
                "url": "https://tatoeba.org",
            },
            {
                "id": "review",
                "name": "Review by Claude Sonnet 5.5: senses and equivalents "
                "(tools/courses/review.jsonl) and example sentences (tools/courses/examples.jsonl)",
            },
            {
                "id": "editor",
                "name": "VocabBot editors: basic words, meanings and the starting list "
                "(tools/courses/editor.jsonl)",
                "license": "CC BY-SA 4.0",
            },
        ],
    }
    (folder / "meta.json").write_bytes(
        (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
