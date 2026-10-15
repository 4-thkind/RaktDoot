"""Upgrade path from the heuristic ranker to a learned one.

Every notification stores the ranking features it was sent with and its outcome. This script
trains a logistic regression (plain Python, no extra dependencies) on those rows and compares
it with the heuristic using AUC.

    python scripts/train_ranker.py --synthetic 3000   # demo on clearly synthetic logs
    python scripts/train_ranker.py                    # real logs from the database

Synthetic logs are generated from an assumed response model and prove the pipeline only,
not real-world accuracy."""
import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.ranking import WEIGHTS, score  # noqa: E402

KEYS = list(WEIGHTS)


def synthetic_logs(n: int, seed: int = 7) -> list[tuple[dict, int]]:
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        f = {k: rng.random() for k in KEYS}
        f["group_preference"] = rng.choice([1.0, 0.6, 0.3])
        # assumed truth: distance and past behaviour dominate
        z = -2.2 + 2.4 * f["proximity"] + 1.8 * f["response_rate"] + 0.9 * f["reliability"] + 0.8 * f["time_of_day_fit"] + 0.3 * f["freshness"]
        rows.append((f, int(rng.random() < 1 / (1 + math.exp(-z)))))
    return rows


def db_logs() -> list[tuple[dict, int]]:
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Notification

    accepted = {"accepted", "connected", "donated", "deferred", "ineligible", "no_show"}
    with SessionLocal() as db:
        return [({k: float(n.features.get(k, 0)) for k in KEYS}, int(n.status in accepted))
                for n in db.scalars(select(Notification)).all() if n.features and n.status != "cancelled"]


def auc(scores: list[float], labels: list[int]) -> float:
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def train(rows, epochs=300, lr=0.5) -> tuple[list[float], float]:
    w, b = [0.0] * len(KEYS), 0.0
    for _ in range(epochs):
        gw, gb = [0.0] * len(KEYS), 0.0
        for f, y in rows:
            x = [f[k] for k in KEYS]
            p = 1 / (1 + math.exp(-(sum(wi * xi for wi, xi in zip(w, x)) + b)))
            for i, xi in enumerate(x):
                gw[i] += (p - y) * xi
            gb += p - y
        w = [wi - lr * g / len(rows) for wi, g in zip(w, gw)]
        b -= lr * gb / len(rows)
    return w, b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=int, default=0)
    args = ap.parse_args()
    rows = synthetic_logs(args.synthetic) if args.synthetic else db_logs()
    if len(rows) < 50:
        sys.exit(f"Only {len(rows)} labelled notifications. Collect more, or run with --synthetic 3000.")
    random.Random(1).shuffle(rows)
    cut = int(len(rows) * 0.8)
    tr, te = rows[:cut], rows[cut:]
    w, b = train(tr)
    labels = [y for _, y in te]
    lr_scores = [sum(wi * f[k] for wi, k in zip(w, KEYS)) + b for f, _ in te]
    print(f"rows: {len(rows)} ({'synthetic' if args.synthetic else 'real'})")
    print(f"heuristic AUC: {auc([score(f) for f, _ in te], labels):.3f}")
    print(f"logistic  AUC: {auc(lr_scores, labels):.3f}")
    print("learned weights:", {k: round(v, 3) for k, v in zip(KEYS, w)}, "bias", round(b, 3))
