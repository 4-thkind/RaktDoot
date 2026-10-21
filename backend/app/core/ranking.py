"""Donor response-likelihood ranking.

MVP is a transparent weighted heuristic (weights shown on the deck). Every notification
logs these features plus its outcome, which is the training set for the logistic-regression
upgrade (see scripts/train_ranker.py)."""
from datetime import datetime

from .compatibility import group_preference

WEIGHTS = {
    "proximity": 0.35,
    "group_preference": 0.20,
    "response_rate": 0.20,
    "reliability": 0.10,
    "time_of_day_fit": 0.10,
    "freshness": 0.05,
}


def features(donor, patient_group: str, distance_km: float, max_radius_km: float, now_local_hour: int, now: datetime,
             component: str = "prbc") -> dict:
    proximity = max(0.0, 1.0 - distance_km / max(max_radius_km, 0.1))
    # Bayesian smoothing: a brand-new donor starts at 0.5, not 0 or 1
    response_rate = (donor.alerts_responded + 2) / (donor.alerts_sent + 4)
    reliability = 1.0 - donor.no_shows / (donor.alerts_accepted + 2)
    hours = donor.reply_hours or []
    near = sum(1 for h in hours if min(abs(h - now_local_hour), 24 - abs(h - now_local_hour)) <= 1)
    time_fit = (near + 1) / (len(hours) + 2)
    if donor.last_alerted_at is None:
        freshness = 1.0
    else:
        freshness = min(1.0, (now - donor.last_alerted_at).total_seconds() / 86400 / 30)
    return {
        "proximity": round(proximity, 4),
        "group_preference": group_preference(donor.blood_group, patient_group, component),
        "response_rate": round(response_rate, 4),
        "reliability": round(max(0.0, min(1.0, reliability)), 4),
        "time_of_day_fit": round(time_fit, 4),
        "freshness": round(freshness, 4),
    }


def score(feats: dict) -> float:
    return round(sum(WEIGHTS[k] * feats[k] for k in WEIGHTS), 4)
