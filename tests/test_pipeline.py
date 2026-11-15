"""Rules of the course pipeline (tools/courses) that are easy to break."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("wordfreq")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "courses"))

import build
import wiktionary


def test_spanish_feminine_nouns_with_stressed_a_take_el() -> None:
    assert build.article_for("es", "f", "agua", {"ipa": "/ˈaɡwa/"}) == "el"
    assert build.article_for("es", "f", "hambre", {"ipa": "/ˈambɾe/"}) == "el"
    assert build.article_for("es", "f", "abeja", {"ipa": "/aˈbexa/"}) == "la"
    assert build.article_for("es", "m", "año", {"ipa": "/ˈaɲo/"}) == "el"


def test_french_elision_and_aspirated_h() -> None:
    assert build.article_for("fr", "f", "école", None) == "l'"
    assert build.article_for("fr", "m", "homme", {}) == "l'"
    assert build.article_for("fr", "m", "haricot", {"h_aspire": True}) == "le"
    assert build.with_article("l'", "école") == "l'école"
    assert build.with_article("die", "Katze") == "die Katze"


def test_gap_prefers_the_citation_form() -> None:
    word = build.Word("de", "Hund", "der Hund", "m")
    assert build.find_gap("Der Hund schläft.", word, "noun") == ("Der Hund", True)
    assert build.find_gap("Ich sehe den Hund.", word, "noun") == ("den Hund", False)
    assert build.find_gap("Der Hund sieht den Hund.", word, "noun") is None
    french = build.Word("fr", "eau", "l'eau", "f")
    assert build.find_gap("Je bois de l'eau.", french, "noun") == ("l'eau", True)


def test_reviewed_words_follow_the_article_rules() -> None:
    lexicon = build.Lexicon()
    lexicon.by_word["agua"].append(
        {"word": "agua", "pos": "noun", "ipa": "/ˈaɡwa/", "plural": ["aguas"]}
    )
    water = build.reviewed_word(
        "es", "noun", {"word": "la agua", "gender": "f", "also": []}, lexicon
    )
    assert (
        water is not None and water.display == "el agua" and water.forms == {"plural": "las aguas"}
    )
    school = build.reviewed_word(
        "fr", "noun", {"word": "école", "gender": "f", "also": ["l'établissement"]}, build.Lexicon()
    )
    assert (
        school is not None and school.display == "l'école" and school.accept == ["l'établissement"]
    )
    assert (
        build.reviewed_word("de", "noun", {"word": "der hund", "gender": "m", "also": []}, lexicon)
        is None
    )
    assert (
        build.reviewed_word("de", "verb", {"word": "", "gender": "none", "also": []}, lexicon)
        is None
    )
    assert build.reviewed_gloss(" kola,  napój gazowany , extra") == "kola, napój gazowany"


def test_clean_drops_notes_and_long_phrases() -> None:
    assert build.clean("Hund (animal)") == "Hund"
    assert build.clean("a b c d") is None
    assert build.clean("2nd") is None


def test_head_genders() -> None:
    assert wiktionary.head_genders("Hund m (strong, genitive Hundes, plural Hunde)", "Hund") == [
        "m"
    ]
    assert wiktionary.head_genders("Single m or f (plural Singles)", "Single") == ["m", "f"]
    assert wiktionary.head_genders("agua f (plural aguas)", "agua") == ["f"]


def entry(concept: str, lang: str, display: str, gloss: str, level: str = "a1") -> dict:
    return {
        "concept": concept,
        "lang": lang,
        "level": level,
        "display": display,
        "gloss": {"pl": gloss},
        "pos": "noun",
        "_frequency": 5.0,
    }


def test_synonyms_merge_and_homonyms_get_hints() -> None:
    families = {
        "c1": {"en": "big", "de": "groß", "es": "grande"},
        "c2": {"en": "large", "de": "groß", "es": "amplio"},
        "c3": {"en": "racket", "de": "der Schläger", "es": "la raqueta"},
        "c4": {"en": "rocket", "de": "die Rakete", "es": "el cohete"},
    }
    spanish = {
        "c1": entry("c1", "es", "grande", "duży"),
        "c2": entry("c2", "es", "amplio", "duży", "b1"),
        "c3": entry("c3", "es", "la raqueta", "rakieta"),
        "c4": entry("c4", "es", "el cohete", "rakieta", "a2"),
    }
    assert build.merge_duplicates(spanish, families) == 1
    assert spanish["c1"]["accept"] == ["amplio"]
    assert spanish["c3"]["hint"] == "ang. racket" and spanish["c4"]["hint"] == "ang. rocket"
    english = {
        "c3": entry("c3", "en", "racket", "rakieta"),
        "c4": entry("c4", "en", "rocket", "rakieta", "a2"),
    }
    assert build.merge_duplicates(english, families) == 1
    assert list(english) == ["c3"] and "hint" not in english["c3"]


def test_gloss_keeps_commas_inside_brackets() -> None:
    assert build.gloss_parts("z (kimś, czymś), wraz z") == ["z (kimś, czymś)", "wraz z"]
    assert build.reviewed_gloss("wysoki (o człowieku, budynku), duży, trzeci") == (
        "wysoki (o człowieku, budynku), duży"
    )


def test_nouns_used_only_in_the_plural() -> None:
    lexicon = build.Lexicon()
    lexicon.by_word["Leute"].append({"word": "Leute", "pos": "noun", "head": "Leute pl"})
    lexicon.by_word["Katzen"].append({"word": "Katzen", "pos": "noun", "head": "Katzen"})
    people = build.reviewed_word(
        "de", "noun", {"word": "die Leute", "gender": "none", "also": []}, lexicon
    )
    assert people is not None and people.display == "die Leute" and people.gender == "pl"
    parents = build.reviewed_word(
        "fr", "noun", {"word": "les parents", "gender": "pl", "also": []}, build.Lexicon()
    )
    assert parents is not None and parents.gender == "pl" and parents.forms == {}


def test_months_go_without_an_article_where_the_language_says_so() -> None:
    january = build.reviewed_word(
        "es", "noun", {"word": "enero", "gender": "m", "also": [], "bare": True}, build.Lexicon()
    )
    assert january is not None and january.display == "enero" and january.bare
    entry = build.entry_of(
        build.Draft(build.Concept("c03653", "January", "noun", "a1", 0), "styczeń", {}, ""),
        january,
        None,
    )
    assert entry["bare"] is True and entry["sources"][0] == "cefrj"


def test_editor_concepts_have_their_own_ids(tmp_path: Path) -> None:
    import concepts

    path = tmp_path / "editor.jsonl"
    path.write_text(
        '{"id": "c09002", "new": {"headword": "be called", "pos": "verb", "level": "a1"}}\n'
        '{"id": "c00042", "pl": "coś"}\n',
        encoding="utf-8",
    )
    found = concepts.editor_concepts(10, path)
    assert [(c.id, c.headword, c.order, c.from_cefrj) for c in found] == [
        ("c09002", "be called", 11, False)
    ]
    path.write_text(
        '{"id": "c00043", "new": {"headword": "x", "pos": "verb", "level": "a1"}}\n',
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        concepts.editor_concepts(0, path)


def test_editor_fields_win_over_the_review() -> None:
    review = {"id": "c1", "pl": "dom", "de": {"word": "das Haus"}, "keep": True}
    assert build.decision_of(review, None) is review
    assert build.decision_of(review, {"id": "c1", "pl": "dom (budynek)"}) == {
        "id": "c1",
        "pl": "dom (budynek)",
        "de": {"word": "das Haus"},
        "keep": True,
    }
    assert build.decision_of(None, {"id": "c2", "pl": "ty"}) == {"id": "c2", "pl": "ty"}


def level_entry(concept: str, pos: str, frequency: float) -> dict:
    return {"concept": concept, "pos": pos, "_frequency": frequency}


def test_a_level_starts_with_the_list_and_spreads_function_words() -> None:
    items = [level_entry(f"f{i}", "prep", 7.0 - i / 10) for i in range(4)]
    items += [level_entry(f"n{i}", "noun", 5.0 - i / 10) for i in range(12)]
    items.append(level_entry("hello", "interj", 3.0))
    order = [e["concept"] for e in build.ordered(items, {"hello": 1})]
    assert order[:5] == ["hello", "f0", "f1", "f2", "n0"]
    assert order.index("f3") == 11  # it waits until f0 leaves the last ten entries
    for start in range(len(order) - 9):
        assert sum(1 for c in order[start : start + 10] if c.startswith("f")) <= 3
    # function words that find no content word left go last, one after another
    tail = build.ordered([level_entry(f"f{i}", "pron", 6.0 - i) for i in range(5)], {})
    assert [e["concept"] for e in tail] == ["f0", "f1", "f2", "f3", "f4"]


def test_one_form_serves_two_parts_of_speech() -> None:
    families: dict[str, dict[str, str]] = {}
    english = {
        "c1": {**entry("c1", "en", "work", "praca"), "pos": "noun"},
        "c2": {**entry("c2", "en", "work", "pracować"), "pos": "verb"},
        "c3": {**entry("c3", "en", "today", "dzisiaj"), "pos": "adv"},
        "c4": {**entry("c4", "en", "today", "dzisiaj"), "pos": "noun"},
        "c5": {**entry("c5", "en", "March", "marzec"), "pos": "noun"},
        "c6": {**entry("c6", "en", "march", "marsz", "b1"), "pos": "noun"},
    }
    assert build.merge_duplicates(english, families) == 1
    assert sorted(english) == ["c1", "c2", "c3", "c5", "c6"]


def test_the_more_basic_concept_keeps_a_shared_form() -> None:
    german = {
        "c1": {**entry("c1", "de", "der Freund", "chłopak"), "_concept_frequency": 4.6},
        "c2": {**entry("c2", "de", "der Freund", "przyjaciel"), "_concept_frequency": 5.6},
    }
    assert build.merge_duplicates(german, {}) == 1
    assert list(german) == ["c2"]


def test_vulgar_sentences_are_left_out() -> None:
    assert build.vulgar("Es un asqueroso hijo de puta.", "es")
    assert build.vulgar("To pieprzony skurwysyn.", "pl")
    assert not build.vulgar("Es el sexto día.", "es")
    assert not build.vulgar("Der Hund wedelt mit dem Schwanz.", "de")
    assert not build.vulgar("Il marche avec technique.", "fr")


def test_example_decisions() -> None:
    first = {"sid": 1, "text": "a"}
    second = {"sid": 2, "text": "b"}
    used: set[int] = set()
    assert build.pick_example([first, second], {"sentence": 2}, used) == (second, "reviewed")
    assert build.pick_example([first, second], {"sentence": None}, used) == (None, "rejected")
    assert build.pick_example([first, second], None, {1}) == (second, "unreviewed")
    assert build.pick_example([], None, set()) == (None, "none")
    # a decision about a sentence that is no longer a candidate falls back to the rule
    assert build.pick_example([first], {"sentence": 9}, set()) == (first, "unreviewed")
