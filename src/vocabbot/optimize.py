"""The full fit of the 21 FSRS-6 parameters to a learner's log, on the standard library.

The fit follows the optimizer of py-fsrs 6.3.3 (MIT, see NOTICE): the loss is
the binary cross-entropy between the predicted recall and the outcome of every
answer on a later day than the card's previous one; Adam with a learning rate
of 0.04 and cosine annealing runs five epochs over mini-batches of 512 answers
taken from the first 64 answers of each card; the parameters stay within the
bounds of py-fsrs; the parameters with the lowest loss over all answers win,
the defaults included; a log with fewer than 512 such answers keeps the
defaults. The engine replays the log without same-day steps (an answer on the
day of the previous one is drill and leaves the memory alone), so the fit
does the same. Gradients come from a small reverse-mode differentiation (Var)
instead of PyTorch.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from vocabbot.fsrs import (
    AGAIN,
    DEFAULT_PARAMETERS,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    EASY,
    HARD,
    STABILITY_MIN,
    Memory,
    Scheduler,
)

LOWER: tuple[float, ...] = (
    *(STABILITY_MIN,) * 4,
    1.0,
    0.001,
    0.001,
    0.001,
    0.0,
    0.0,
    0.001,
    0.001,
    0.001,
    0.001,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.1,
)
UPPER: tuple[float, ...] = (
    *(100.0,) * 4,
    10.0,
    4.0,
    4.0,
    0.75,
    4.5,
    0.8,
    3.5,
    5.0,
    0.25,
    0.9,
    4.0,
    1.0,
    6.0,
    2.0,
    2.0,
    0.8,
    0.8,
)
EPOCHS = 5
BATCH = 512
LEARNING_RATE = 0.04
MAX_ANSWERS = 64  # the first answers of a card that take part, as in py-fsrs
MIN_REVIEWS = 512
EPSILON = 1e-7
BETAS = (0.9, 0.999)
ADAM_EPSILON = 1e-8


class Var:
    """A number that remembers how it was computed, for reverse-mode derivatives."""

    __slots__ = ("grad", "parents", "value")

    def __init__(self, value: float, parents: tuple[tuple[Var, float], ...] = ()) -> None:
        self.value = value
        self.parents = parents
        self.grad = 0.0

    def __add__(self, other: Var | float) -> Var:
        if isinstance(other, Var):
            return Var(self.value + other.value, ((self, 1.0), (other, 1.0)))
        return Var(self.value + other, ((self, 1.0),))

    def __radd__(self, other: float) -> Var:
        return Var(other + self.value, ((self, 1.0),))

    def __sub__(self, other: Var | float) -> Var:
        if isinstance(other, Var):
            return Var(self.value - other.value, ((self, 1.0), (other, -1.0)))
        return Var(self.value - other, ((self, 1.0),))

    def __rsub__(self, other: float) -> Var:
        return Var(other - self.value, ((self, -1.0),))

    def __mul__(self, other: Var | float) -> Var:
        if isinstance(other, Var):
            return Var(self.value * other.value, ((self, other.value), (other, self.value)))
        return Var(self.value * other, ((self, other),))

    def __rmul__(self, other: float) -> Var:
        return Var(other * self.value, ((self, other),))

    def __truediv__(self, other: Var | float) -> Var:
        if isinstance(other, Var):
            value = self.value / other.value
            return Var(value, ((self, 1.0 / other.value), (other, -value / other.value)))
        return Var(self.value / other, ((self, 1.0 / other),))

    def __rtruediv__(self, other: float) -> Var:
        value = other / self.value
        return Var(value, ((self, -value / self.value),))

    def __neg__(self) -> Var:
        return Var(-self.value, ((self, -1.0),))

    def __pow__(self, exponent: Var | float) -> Var:
        if isinstance(exponent, Var):
            value = self.value**exponent.value
            return Var(
                value,
                (
                    (self, exponent.value * self.value ** (exponent.value - 1)),
                    (exponent, value * math.log(self.value)),
                ),
            )
        value = self.value**exponent
        return Var(value, ((self, exponent * self.value ** (exponent - 1)),))

    def __rpow__(self, base: float) -> Var:
        value = base**self.value
        return Var(value, ((self, value * math.log(base)),))


def exp(x: Var) -> Var:
    value = math.exp(x.value)
    return Var(value, ((x, value),))


def log(x: Var) -> Var:
    return Var(math.log(x.value), ((x, 1.0 / x.value),))


def clamp(x: Var, low: float, high: float = math.inf) -> Var:
    """The value within bounds; outside them the derivative is zero, as with torch.clamp."""
    if x.value < low:
        return Var(low)
    if x.value > high:
        return Var(high)
    return x


def smaller(a: Var, b: Var) -> Var:
    return a if a.value <= b.value else b


def total(terms: Sequence[Var]) -> Var:
    return Var(math.fsum(t.value for t in terms), tuple((t, 1.0) for t in terms))


def backward(root: Var) -> None:
    """Derivatives of `root` with respect to every Var it depends on."""
    order: list[Var] = []
    seen: set[int] = set()
    stack: list[tuple[Var, bool]] = [(root, False)]
    while stack:
        node, finished = stack.pop()
        if finished:
            order.append(node)
            continue
        if id(node) in seen:
            continue
        seen.add(id(node))
        stack.append((node, True))
        stack.extend((parent, False) for parent, _ in node.parents if id(parent) not in seen)
    root.grad = 1.0
    for node in reversed(order):
        for parent, local in node.parents:
            parent.grad += node.grad * local


class Model:
    """The steps of fsrs.Scheduler on Var numbers (without same-day steps)."""

    def __init__(self, w: Sequence[Var]) -> None:
        self.w = w
        self.decay = -w[20]
        self.factor = exp(math.log(0.9) / self.decay) - 1.0

    def recall(self, stability: Var, days: float) -> Var:
        return (1.0 + self.factor * days / stability) ** self.decay

    def initial_difficulty(self, rating: int) -> Var:
        return self.w[4] - exp(self.w[5] * float(rating - 1)) + 1.0

    def first(self, rating: int) -> tuple[Var, Var]:
        stability = clamp(self.w[rating - 1], STABILITY_MIN)
        difficulty = clamp(self.initial_difficulty(rating), DIFFICULTY_MIN, DIFFICULTY_MAX)
        return stability, difficulty

    def review(self, s: Var, d: Var, rating: int, days: float) -> tuple[Var, Var]:
        w = self.w
        r = self.recall(s, days)
        if rating == AGAIN:
            long_term = w[11] * d ** (-w[12]) * ((s + 1.0) ** w[13] - 1.0) * exp((1.0 - r) * w[14])
            short_term = s / exp(w[17] * w[18])
            stability = smaller(long_term, short_term)
        else:
            boost = exp(w[8]) * (11.0 - d) * s ** (-w[9]) * (exp((1.0 - r) * w[10]) - 1.0)
            if rating == HARD:
                boost = boost * w[15]
            elif rating == EASY:
                boost = boost * w[16]
            stability = s * (1.0 + boost)
        delta = -(w[6] * float(rating - 3))
        damped = d + (10.0 - d) * delta / 9.0
        reverted = w[7] * self.initial_difficulty(EASY) + (1.0 - w[7]) * damped
        return (
            clamp(stability, STABILITY_MIN),
            clamp(reverted, DIFFICULTY_MIN, DIFFICULTY_MAX),
        )


@dataclass(frozen=True)
class Answer:
    """One answer of a card in the replay: the rating, the days since the previous answer
    (0 for the first) and whether the card was recalled."""

    rating: int
    days: int
    recalled: bool


def reviews_in(histories: Sequence[Sequence[Answer]]) -> int:
    return sum(max(0, min(len(h), MAX_ANSWERS) - 1) for h in histories)


def loss(histories: Sequence[Sequence[Answer]], parameters: Sequence[float]) -> float:
    """Mean binary cross-entropy of the predicted recall over every review."""
    scheduler = Scheduler(parameters=tuple(parameters))
    total_loss = 0.0
    count = 0
    for history in histories:
        memory: Memory | None = None
        for answer in history[:MAX_ANSWERS]:
            if memory is None:
                memory = scheduler.first(answer.rating)
                continue
            p = min(max(scheduler.retrievability(memory, answer.days), EPSILON), 1 - EPSILON)
            total_loss -= math.log(p) if answer.recalled else math.log(1 - p)
            count += 1
            memory = scheduler.review(memory, answer.rating, answer.days)
    return total_loss / count if count else 0.0


def fit(
    histories: Sequence[Sequence[Answer]],
    parameters: Sequence[float] = DEFAULT_PARAMETERS,
    *,
    epochs: int = EPOCHS,
    seed: int = 42,
) -> tuple[float, ...] | None:
    """Parameters fitted to the histories, or None with fewer than MIN_REVIEWS reviews."""
    reviews = reviews_in(histories)
    if reviews < MIN_REVIEWS:
        return None
    params = list(parameters)
    best, best_loss = list(params), loss(histories, params)
    first_moment = [0.0] * len(params)
    second_moment = [0.0] * len(params)
    updates = 0
    planned = math.ceil(reviews / BATCH) * epochs
    rng = random.Random(seed)
    order = list(range(len(histories)))

    def update(w: list[Var], terms: list[Var]) -> list[float]:
        nonlocal updates
        backward(total(terms))
        rate = LEARNING_RATE * (1 + math.cos(math.pi * updates / planned)) / 2
        updates += 1
        out = []
        for i, weight in enumerate(w):
            grad = weight.grad
            first_moment[i] = BETAS[0] * first_moment[i] + (1 - BETAS[0]) * grad
            second_moment[i] = BETAS[1] * second_moment[i] + (1 - BETAS[1]) * grad * grad
            mean = first_moment[i] / (1 - BETAS[0] ** updates)
            spread = second_moment[i] / (1 - BETAS[1] ** updates)
            value = params[i] - rate * mean / (math.sqrt(spread) + ADAM_EPSILON)
            out.append(min(max(value, LOWER[i]), UPPER[i]))
        return out

    for _ in range(epochs):
        rng.shuffle(order)
        w = [Var(p) for p in params]
        model = Model(w)
        terms: list[Var] = []
        for index in order:
            s: Var | None = None
            d: Var | None = None
            for answer in histories[index][:MAX_ANSWERS]:
                if s is None or d is None:
                    s, d = model.first(answer.rating)
                    continue
                p = clamp(model.recall(s, answer.days), EPSILON, 1 - EPSILON)
                terms.append(-log(p) if answer.recalled else -log(1.0 - p))
                s, d = model.review(s, d, answer.rating, answer.days)
                if len(terms) == BATCH:
                    params = update(w, terms)
                    w = [Var(p) for p in params]
                    model = Model(w)
                    terms = []
                    s, d = Var(s.value), Var(d.value)  # the card goes on without its history
        if terms:
            params = update(w, terms)
        epoch_loss = loss(histories, params)
        if epoch_loss < best_loss:
            best, best_loss = list(params), epoch_loss
    return tuple(round(p, 4) for p in best)
