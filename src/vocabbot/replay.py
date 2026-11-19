"""Replays the learner's log and compares variants of the schedule with FSRS-6.

Each variant predicts the recall of every review from the answers before it,
before its outcome is known. A variant fitted to the log learns from the
earlier part (the first 70% of the reviews in order of time) and is scored on
the later part, so it never sees the answers it predicts. The scores are those
of the benchmark of spaced-repetition algorithms: log loss, RMSE(bins) with
the bins of fsrs-optimizer (interval, number of the answer and lapses on
logarithmic grids) and AUC. Given the concept of each card, the scores are also
given apart for the reviews of cards whose concept the learner had already met
in another language of the log (`sibling`) and for the rest.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from vocabbot import optimize
from vocabbot.book import RATING, Book, replay, second_answers
from vocabbot.fsrs import AGAIN, DEFAULT_PARAMETERS, Scheduler, fit_initial

SHARE = 0.7  # the earlier part of the reviews a fitted variant learns from
MIN_TEST = 30  # reviews in the later part before the scores mean anything
EPSILON = 1e-7

Parameters = tuple[float, ...]
Histories = dict[str, tuple[str, list[tuple[date, optimize.Answer]]]]


@dataclass(frozen=True)
class Prediction:
    """The recall a variant predicted for one review, and what happened."""

    lang: str
    days: int
    number: int  # the answer's place in the card's history; the first answer is 1
    lapses: int  # reviews forgotten before this one
    recalled: bool
    p: float
    sibling: bool = False  # the concept was met in another language by the day of the review


def histories(book: Book) -> Histories:
    """Every card's first answer and reviews, without drill, in order of time."""
    out: Histories = {}
    last: dict[str, date] = {}
    for row in book.rows:
        if row.kind == "drill":
            continue
        answer_of = optimize.Answer
        rating = RATING[row.grade]
        recalled = row.grade != "dont_know"
        if row.kind == "learn":
            out[row.card] = (row.lang, [(row.day, answer_of(rating, 0, recalled))])
        elif row.card in out:
            days = (row.day - last[row.card]).days
            out[row.card][1].append((row.day, answer_of(rating, days, recalled)))
        last[row.card] = row.day
    return out


def answers_only(hist: Histories, lang: str | None = None) -> list[list[optimize.Answer]]:
    return [[a for _, a in answers] for code, answers in hist.values() if lang in (None, code)]


Elsewhere = Callable[[str, str, date], bool]


def met_elsewhere(hist: Histories, concept_of: Callable[[str], str | None]) -> Elsewhere:
    """Whether a card's concept had a first answer in another language by a given day."""
    first: dict[str, dict[str, date]] = defaultdict(dict)
    for card, (lang, answers) in hist.items():
        concept = concept_of(card)
        if concept and answers:
            known = first[concept].get(lang)
            first[concept][lang] = min(known, answers[0][0]) if known else answers[0][0]

    def check(card: str, lang: str, day: date) -> bool:
        concept = concept_of(card)
        if not concept:
            return False
        return any(code != lang and met <= day for code, met in first[concept].items())

    return check


def predict(
    hist: Histories,
    parameters: Callable[[str], Parameters],
    since: date | None = None,
    elsewhere: Elsewhere | None = None,
) -> list[Prediction]:
    """Predictions of every review on or after `since` (every review without it)."""
    schedulers: dict[Parameters, Scheduler] = {}
    out: list[Prediction] = []
    for card, (lang, answers) in hist.items():
        params = parameters(lang)
        scheduler = schedulers.setdefault(params, Scheduler(parameters=params))
        memory = None
        lapses = 0
        for number, (day, answer) in enumerate(answers, 1):
            if memory is None:
                memory = scheduler.first(answer.rating)
                continue
            p = scheduler.retrievability(memory, answer.days)
            if since is None or day >= since:
                sibling = elsewhere is not None and elsewhere(card, lang, day)
                out.append(
                    Prediction(lang, answer.days, number, lapses, answer.recalled, p, sibling)
                )
            if answer.rating == AGAIN:
                lapses += 1
            memory = scheduler.review(memory, answer.rating, answer.days)
    return out


def log_loss(predictions: Sequence[Prediction]) -> float:
    total = 0.0
    for x in predictions:
        p = min(max(x.p, EPSILON), 1 - EPSILON)
        total -= math.log(p) if x.recalled else math.log(1 - p)
    return total / len(predictions)


def _grid(value: int, scale: float, base: float, digits: int) -> float:
    return round(scale * base ** math.floor(math.log(value) / math.log(base)), digits)


def rmse_bins(predictions: Sequence[Prediction]) -> float:
    """RMSE between the mean recall and the mean prediction of bins, weighted by size."""
    bins: dict[tuple[float, float, float], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for x in predictions:
        key = (
            _grid(max(1, x.days), 2.48, 3.62, 2),
            _grid(x.number, 1.99, 1.89, 0),
            _grid(x.lapses, 1.65, 1.73, 0) if x.lapses else 0.0,
        )
        cell = bins[key]
        cell[0] += 1
        cell[1] += x.recalled
        cell[2] += x.p
    size = sum(cell[0] for cell in bins.values())
    squares = sum(cell[0] * (cell[1] / cell[0] - cell[2] / cell[0]) ** 2 for cell in bins.values())
    return math.sqrt(squares / size)


def auc(predictions: Sequence[Prediction]) -> float | None:
    """The chance that a recalled review got a higher prediction than a forgotten one."""
    positives = sum(1 for x in predictions if x.recalled)
    negatives = len(predictions) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(predictions, key=lambda x: x.p)
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1].p == ordered[index].p:
            end += 1
        average = (index + end) / 2 + 1
        rank_sum += average * sum(1 for x in ordered[index : end + 1] if x.recalled)
        index = end + 1
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def scores(predictions: Sequence[Prediction]) -> dict[str, Any]:
    if not predictions:
        return {"reviews": 0}
    area = auc(predictions)
    return {
        "reviews": len(predictions),
        "log_loss": round(log_loss(predictions), 4),
        "rmse_bins": round(rmse_bins(predictions), 4),
        "auc": round(area, 4) if area is not None else None,
    }


@dataclass
class Variant:
    name: str
    parameters: Callable[[str], Parameters] | None  # None: the variant cannot be built
    note: dict[str, Any]


def variants(train: Book, languages: Sequence[str]) -> list[Variant]:
    """FSRS-6 and the variants fitted to the earlier part of the log."""
    hist = histories(train)
    out = [Variant("fsrs6", lambda lang: DEFAULT_PARAMETERS, {})]
    initial = fit_initial(second_answers(train))
    have = sum(len(p) for p in second_answers(train).values())
    out.append(
        Variant(
            "initial",
            (lambda lang: initial) if initial != DEFAULT_PARAMETERS else None,
            {"second_answers": have},
        )
    )
    reviews = optimize.reviews_in(answers_only(hist))
    fitted = optimize.fit(answers_only(hist))
    out.append(
        Variant(
            "fit",
            (lambda lang: fitted) if fitted is not None else None,
            {"reviews": reviews, "needed": optimize.MIN_REVIEWS},
        )
    )
    per_lang: dict[str, Parameters] = {}
    counts: dict[str, int] = {}
    for lang in languages:
        own = answers_only(hist, lang)
        counts[lang] = optimize.reviews_in(own)
        found = optimize.fit(own)
        if found is not None:
            per_lang[lang] = found
    fallback = fitted or DEFAULT_PARAMETERS
    out.append(
        Variant(
            "fit_lang",
            (lambda lang: per_lang.get(lang, fallback)) if per_lang else None,
            {"reviews": counts, "needed": optimize.MIN_REVIEWS, "fitted": sorted(per_lang)},
        )
    )
    return out


def compare(
    rows: Sequence[dict[str, Any]],
    *,
    share: float = SHARE,
    current: Callable[[str], Parameters] | None = None,
    concept_of: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    """Scores of every variant on the later part of the log, and their difference from FSRS-6.

    With `concept_of` (a card's concept, from the courses) every variant also has
    `groups`: the scores of reviews whose concept the learner had met in another
    language (`sibling`) and of the rest (`alone`).
    """
    book = replay(list(rows))
    hist = histories(book)
    elsewhere = met_elsewhere(hist, concept_of) if concept_of is not None else None
    days = sorted(row.day for row in book.rows if row.kind == "review")
    if not days:
        return {"reviews": 0, "test_reviews": 0, "variants": []}
    since = days[min(len(days) - 1, int(len(days) * share))]
    limit = since.isoformat()
    train = replay([r for r in rows if isinstance(r.get("day"), str) and r["day"] < limit])
    languages = sorted({lang for lang, _ in hist.values()})
    found = variants(train, languages)
    if current is not None:
        found.append(Variant("current", current, {}))
    base = scores(predict(hist, lambda lang: DEFAULT_PARAMETERS, since))
    results = []
    for variant in found:
        if variant.parameters is None:
            results.append({"name": variant.name, "available": False, **variant.note})
            continue
        made = predict(hist, variant.parameters, since, elsewhere)
        result: dict[str, Any] = {
            "name": variant.name,
            "available": True,
            **variant.note,
            "scores": scores(made),
            "languages": {lang: scores([x for x in made if x.lang == lang]) for lang in languages},
        }
        if elsewhere is not None:
            result["groups"] = {
                "sibling": scores([x for x in made if x.sibling]),
                "alone": scores([x for x in made if not x.sibling]),
            }
        if base.get("reviews"):
            result["delta"] = {
                key: round(result["scores"][key] - base[key], 4)
                for key in ("log_loss", "rmse_bins")
                if result["scores"].get(key) is not None
            }
        results.append(result)
    test = base.get("reviews", 0)
    usable = [r for r in results if r.get("available") and test >= MIN_TEST]
    best = min(usable, key=lambda r: r["scores"]["log_loss"])["name"] if usable else None
    return {
        "since": limit,
        "reviews": len(days),
        "train_reviews": len(days) - test,
        "test_reviews": test,
        "enough": test >= MIN_TEST,
        "variants": results,
        "best": best,
    }


def fit_languages(
    rows: Sequence[dict[str, Any]], languages: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """Parameters fitted to the whole log for every language whose fit wins in `compare`.

    A language with enough reviews of its own gets its own fit; another one
    gets the fit of the whole log when that fit wins on its reviews.
    """
    result = compare(rows)
    if not result.get("enough"):
        return {}
    book = replay(list(rows))
    hist = histories(book)
    by_name = {v["name"]: v for v in result["variants"] if v.get("available")}
    base = by_name["fsrs6"]["languages"]
    out: dict[str, dict[str, Any]] = {}
    whole: Parameters | None = None
    for lang in languages:
        before = base.get(lang, {})
        if before.get("reviews", 0) < MIN_TEST:
            continue
        own = by_name.get("fit_lang", {}).get("languages", {}).get(lang, {})
        shared = by_name.get("fit", {}).get("languages", {}).get(lang, {})
        own_fitted = lang in by_name.get("fit_lang", {}).get("fitted", [])
        choice = None
        if own_fitted and own.get("log_loss", math.inf) < before["log_loss"]:
            choice = ("own", own)
        elif shared.get("log_loss", math.inf) < before["log_loss"]:
            choice = ("shared", shared)
        if choice is None:
            continue
        if choice[0] == "own":
            params = optimize.fit(answers_only(hist, lang))
        else:
            whole = whole or optimize.fit(answers_only(hist))
            params = whole
        if params is None:
            continue
        out[lang] = {
            "parameters": list(params),
            "source": choice[0],
            "reviews": optimize.reviews_in(
                answers_only(hist, lang if choice[0] == "own" else None)
            ),
            "log_loss": choice[1]["log_loss"],
            "log_loss_fsrs6": before["log_loss"],
            "since": result["since"],
        }
    return out


def plan_parameters(params: Mapping[str, Sequence[float]]) -> Callable[[str], Parameters]:
    """The parameters of a plan as a function of the language, FSRS-6 for the others."""
    return lambda lang: tuple(params[lang]) if lang in params else DEFAULT_PARAMETERS
