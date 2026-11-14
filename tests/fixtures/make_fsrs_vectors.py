"""Wektory wzorcowe FSRS-6 z py-fsrs: (ocena, dni od poprzedniej powtorki) -> stabilnosc, trudnosc, interwal."""
import json
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating, Scheduler

CASES = {
    "all_know_on_time": [(3, None)] + [(3, "due")] * 6,
    "almost_then_know": [(2, None), (2, "due"), (3, "due"), (3, "due"), (2, "due")],
    "lapse_and_recover": [(3, None), (3, "due"), (1, "due"), (3, "due"), (3, "due"), (1, "due"), (3, "due")],
    "start_unknown": [(1, None), (1, "due"), (3, "due"), (3, "due")],
    "already_known": [(4, None), (3, "due"), (3, "due")],
    "late_reviews": [(3, None), (3, 10), (3, 40), (1, 200), (3, 3)],
    "early_reviews": [(3, None), (3, 1), (3, 1), (2, 2), (3, 5)],
    "same_day_again": [(3, None), (1, 0), (3, 0), (3, 4)],
    "hard_road": [(1, None), (2, 1), (1, 1), (2, 2), (3, 3), (3, 8)],
}


def run(retention):
    sched = Scheduler(desired_retention=retention, learning_steps=(), relearning_steps=(),
                      enable_fuzzing=False)
    out = {}
    for name, steps in CASES.items():
        card = Card()
        now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        rows = []
        for grade, gap in steps:
            if gap == "due":
                now = card.due
            elif gap is not None:
                now = now + timedelta(days=gap)
            elapsed = None if card.last_review is None else (now - card.last_review).days
            card, _ = sched.review_card(card, Rating(grade), review_datetime=now)
            interval = (card.due - now).days
            rows.append({"grade": grade, "elapsed": elapsed, "s": round(card.stability, 9),
                         "d": round(card.difficulty, 9), "interval": interval})
        out[name] = rows
    return out


print(json.dumps({"0.9": run(0.9), "0.85": run(0.85)}, indent=1))
