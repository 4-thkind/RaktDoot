"""Deterministic eligibility rules. The LLM never decides eligibility; it only turns free
text into yes/no answers that are fed into these functions."""
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "eligibility.yaml"


@lru_cache
def rules() -> dict:
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def questions() -> list[dict]:
    return rules()["questions"]


def question(qid: str) -> dict | None:
    return next((q for q in questions() if q["id"] == qid), None)


def rest_days(gender: str) -> int:
    return rules()["static"]["rest_days"].get(gender, rules()["static"]["rest_days"]["O"])


def eligible_again_on(last_donation: date | None, gender: str) -> date | None:
    if not last_donation:
        return None
    return last_donation + timedelta(days=rest_days(gender))


def in_rest_period(last_donation: date | None, gender: str, today: date) -> bool:
    again = eligible_again_on(last_donation, gender)
    return again is not None and today < again


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def age_ok(dob: date | None, today: date) -> bool:
    if dob is None:
        return False
    s = rules()["static"]
    return s["min_age"] <= age_on(dob, today) <= s["max_age"]


def answers_disqualify(answers: dict) -> str | None:
    """Return the id of the first question answered 'yes' (disqualifying), else None."""
    for q in questions():
        if answers.get(q["id"]) is True:
            return q["id"]
    return None


def next_question(answers: dict) -> dict | None:
    return next((q for q in questions() if q["id"] not in answers), None)
