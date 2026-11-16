"""One pass over the Wiktionary extract: compact records of the words the courses need.

English entries are kept for the CEFR-J headwords, with their translations
into German, Spanish, French and Polish. German, Spanish and French entries
are kept for every lemma (not for inflected forms), with gender, plural and
other forms, and pronunciation: the IPA and the Wikimedia Commons file name of
a recording. The records go to .cache/work/*.jsonl.
"""

from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from vocabbot.courses import AUDIO_FILE

from sources import WIKTIONARY, WORK

TARGETS = ("de", "es", "fr", "it", "pl")  # Polish entries serve to check the Polish meanings
TRANSLATION_LANGS = ("de", "es", "fr", "it", "pl")
POS = {
    "noun",
    "verb",
    "adj",
    "adv",
    "pron",
    "prep",
    "conj",
    "num",
    "intj",
    "particle",
    "phrase",
    "det",
}
LANG_NAMES = {
    b'"lang": "English"': "en",
    b'"lang": "German"': "de",
    b'"lang": "Spanish"': "es",
    b'"lang": "French"': "fr",
    b'"lang": "Italian"': "it",
    b'"lang": "Polish"': "pl",
}
SKIP_TAGS = {
    "archaic",
    "obsolete",
    "dated",
    "rare",
    "vulgar",
    "slang",
    "derogatory",
    "offensive",
    "historical",
    "poetic",
    "literary",
    "nonstandard",
    "misspelling",
    "humorous",
    "euphemistic",
}
GENDERS = {"masculine": "m", "feminine": "f", "neuter": "n"}


def gender_tags(tags: list[str]) -> list[str]:
    return [GENDERS[t] for t in tags if t in GENDERS]


def head_genders(expansion: str, word: str) -> list[str]:
    """'Hund m (strong, ...)' -> ['m']; 'Single m or f' -> ['m', 'f']."""
    rest = expansion[len(word) :] if expansion.startswith(word) else expansion
    rest = rest.split("(")[0]
    return [g for g in re.findall(r"(?<![\w])([mfn])(?![\w])", rest) if g in "mfn"]


def first_ipa(sounds: list[dict[str, Any]], prefer: tuple[str, ...] = ()) -> str | None:
    ipas = [s for s in sounds if isinstance(s.get("ipa"), str)]
    for wanted in prefer:
        for sound in ipas:
            if wanted in (sound.get("tags") or []) and sound["ipa"].startswith("/"):
                return str(sound["ipa"])
    for sound in ipas:
        if sound["ipa"].startswith("/"):
            return str(sound["ipa"])
    return str(ipas[0]["ipa"]) if ipas else None


# the recording of the standard variety the course teaches comes first, regional ones last
AUDIO_PREFER = {
    "en": ("UK", "Received-Pronunciation", "Southern-England", "England", "US", "General-American"),
    "de": ("Germany",),
    "es": ("Spain",),
    "fr": ("France",),
    "it": ("Italy",),
}
AUDIO_REGIONAL = {
    "Quebec",
    "Canada",
    "Belgium",
    "Switzerland",
    "Austria",
    "Latin-America",
    "Mexico",
    "Argentina",
    "Australia",
    "India",
    "Ireland",
    "Scotland",
    "New-Zealand",
    "South-Africa",
}


def first_audio(sounds: list[dict[str, Any]], lang: str) -> str | None:
    """The Wikimedia Commons file name of the word's recording, standard variety first."""
    recordings = [
        s
        for s in sounds
        if isinstance(s.get("audio"), str)
        and AUDIO_FILE.match(s["audio"])
        and (s.get("ogg_url") or s.get("mp3_url"))
    ]
    prefer = AUDIO_PREFER.get(lang, ())

    def rank(sound: dict[str, Any]) -> tuple[int, int]:
        tags = set(sound.get("tags") or [])
        name = str(sound["audio"])
        regional = bool(tags & AUDIO_REGIONAL) or name.startswith("Qc-")
        wanted = next((i for i, tag in enumerate(prefer) if tag in tags), len(prefer))
        return (int(regional), wanted)

    recordings.sort(key=rank)  # stable: Wiktionary's order among equals
    return str(recordings[0]["audio"]) if recordings else None


def forms_with(
    forms: list[dict[str, Any]], *required: str, exclude: tuple[str, ...] = ()
) -> list[str]:
    out = []
    for item in forms:
        tags = set(item.get("tags") or [])
        form = item.get("form")
        if not isinstance(form, str) or not set(required) <= tags or tags & set(exclude):
            continue
        if tags & {
            "alternative",
            "obsolete",
            "archaic",
            "rare",
            "dated",
            "table-tags",
            "inflection-template",
        }:
            continue
        if form not in out:
            out.append(form)
    return out


def is_lemma(entry: dict[str, Any]) -> bool:
    senses = entry.get("senses") or []
    if not senses:
        return False
    return any(
        not s.get("form_of") and not s.get("alt_of") and "form-of" not in (s.get("tags") or [])
        for s in senses
    )


def compact_target(entry: dict[str, Any]) -> dict[str, Any]:
    word = entry["word"]
    forms = entry.get("forms") or []
    head = next(
        (h.get("expansion") for h in entry.get("head_templates") or [] if h.get("expansion")), ""
    )
    genders: list[str] = []
    if entry.get("pos") == "noun":
        genders = head_genders(head or "", word)
        if not genders:
            for sense in entry.get("senses") or []:
                genders += [g for g in gender_tags(sense.get("tags") or []) if g not in genders]
    record: dict[str, Any] = {
        "word": word,
        "pos": entry.get("pos"),
        "head": head[:160],
        "ipa": first_ipa(entry.get("sounds") or []),
        "audio": first_audio(entry.get("sounds") or [], str(entry.get("lang_code"))),
        # English meanings of the word, used to check that it translates back to the English concept
        "gloss": [
            g[:120] for s in (entry.get("senses") or [])[:8] for g in (s.get("glosses") or [])[-1:]
        ],
    }
    if genders:
        record["gender"] = genders
    sound_notes = " ".join(
        str(s.get("note") or "") + " " + " ".join(s.get("tags") or [])
        for s in entry.get("sounds") or []
    )
    if (
        "aspirated" in head.lower()
        or "aspirated" in sound_notes.lower()
        or "h-aspir" in sound_notes.lower()
    ):
        record["h_aspire"] = True
    plural = forms_with(forms, "plural", exclude=("genitive", "dative", "accusative", "diminutive"))
    if plural:
        record["plural"] = plural[:3]
    feminine = forms_with(forms, "feminine", exclude=("plural",))
    if feminine:
        record["feminine"] = feminine[:2]
    if entry.get("pos") == "verb":
        record["past"] = forms_with(forms, "past", exclude=("participle", "subjunctive", "plural"))[
            :1
        ]
        record["participle"] = forms_with(forms, "participle", "past")[:1]
        record["present_3sg"] = forms_with(
            forms, "present", "singular", "third-person", exclude=("subjunctive",)
        )[:1]
        record["auxiliary"] = forms_with(forms, "auxiliary")[:2]
    if entry.get("pos") == "adj":
        record["comparative"] = forms_with(forms, "comparative")[:1]
    return {k: v for k, v in record.items() if v not in (None, [], "")}


def compact_english(entry: dict[str, Any]) -> dict[str, Any]:
    forms = entry.get("forms") or []
    translations = []
    for item in entry.get("translations") or []:
        code = item.get("lang_code") or item.get("code")
        word = item.get("word")
        if code not in TRANSLATION_LANGS or not isinstance(word, str) or not word.strip():
            continue
        tags = item.get("tags") or []
        if set(tags) & SKIP_TAGS or any(t.endswith("German") for t in tags):
            continue
        translations.append(
            {
                "lang": code,
                "word": word.strip(),
                "sense": item.get("sense") or "",
                "tags": tags,
            }
        )
    record: dict[str, Any] = {
        "word": entry["word"],
        "pos": entry.get("pos"),
        "ipa": first_ipa(entry.get("sounds") or [], prefer=("Received-Pronunciation", "UK")),
        "audio": first_audio(entry.get("sounds") or [], "en"),
        "gloss": [g for s in (entry.get("senses") or [])[:4] for g in (s.get("glosses") or [])[:1]],
        "plural": forms_with(forms, "plural")[:2],
        "past": forms_with(forms, "past", exclude=("participle",))[:1],
        "participle": forms_with(forms, "participle", "past")[:1],
        "comparative": forms_with(forms, "comparative")[:1],
        "translations": translations,
    }
    return {k: v for k, v in record.items() if v not in (None, [], "")}


def lines(path: Path) -> Iterator[bytes]:
    with gzip.open(path, "rb") as fh:
        yield from fh


def extract(english_words: set[str]) -> dict[str, int]:
    """Write work/english.jsonl and work/lexicon-<lang>.jsonl; return counts."""
    WORK.mkdir(parents=True, exist_ok=True)
    out = {code: (WORK / f"lexicon-{code}.jsonl").open("wb") for code in TARGETS}
    out["en"] = (WORK / "english.jsonl").open("wb")
    counts = dict.fromkeys(out, 0)
    try:
        for raw in lines(WIKTIONARY):
            if not any(name in raw for name in LANG_NAMES):
                continue
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            code = entry.get("lang_code")
            if code not in out or not is_lemma(entry):
                continue
            # English months and the like are proper names in Wiktionary
            if entry.get("pos") not in POS and not (code == "en" and entry.get("pos") == "name"):
                continue
            if code == "en":
                if entry.get("word") not in english_words:
                    continue
                record = compact_english(entry)
            else:
                record = compact_target(entry)
            out[code].write((json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
            counts[code] += 1
    finally:
        for fh in out.values():
            fh.close()
    return counts


def load(name: str) -> list[dict[str, Any]]:
    path = WORK / name
    with path.open("rb") as fh:
        return [json.loads(line) for line in fh if line.strip()]
