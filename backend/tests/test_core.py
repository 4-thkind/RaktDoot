from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core import eligibility, ranking
from app.core.compatibility import GROUPS, can_donate, compatible_donors, normalize_group
from app.services.llm import rule_parse
from app.services.tinyfish_client import validate_result


def _abo_rh_rule(donor: str, patient: str) -> bool:
    """Independent check: donor red-cell antigens must all be present in the patient."""
    antigens = lambda g: set(g[:-1].replace("O", "")) | ({"D"} if g.endswith("+") else set())  # noqa: E731
    return antigens(donor) <= antigens(patient)


@pytest.mark.parametrize("donor", GROUPS)
@pytest.mark.parametrize("patient", GROUPS)
def test_all_64_pairs(donor, patient):
    assert can_donate(donor, patient) == _abo_rh_rule(donor, patient)


def test_order_exact_first_o_neg_last():
    assert compatible_donors("B+") == ["B+", "B-", "O+", "O-"]
    assert compatible_donors("AB+")[0] == "AB+" and compatible_donors("AB+")[-1] == "O-"
    assert compatible_donors("O-") == ["O-"]


def test_normalize_group():
    assert normalize_group("b+ve") == "B+"
    assert normalize_group("O NEGATIVE") == "O-"
    assert normalize_group("AB−") == "AB-"
    assert normalize_group("C+") is None


def test_rest_periods():
    d = date(2024, 2, 29)  # leap day
    assert eligibility.eligible_again_on(d, "M") == date(2024, 5, 29)
    assert eligibility.eligible_again_on(d, "F") == date(2024, 6, 28)
    assert eligibility.in_rest_period(d, "M", date(2024, 5, 28))
    assert not eligibility.in_rest_period(d, "M", date(2024, 5, 29))
    assert eligibility.rest_days("O") == 120


def test_age_bounds():
    today = date(2026, 10, 14)
    assert not eligibility.age_ok(date(2008, 10, 15), today)   # 17, birthday tomorrow
    assert eligibility.age_ok(date(2008, 10, 14), today)       # 18 today
    assert not eligibility.age_ok(date(1960, 10, 13), today)   # 66
    assert not eligibility.age_ok(None, today)


def test_disqualify_and_order():
    qs = [q["id"] for q in eligibility.questions()]
    assert qs[0] == "alcohol_24h"
    assert eligibility.answers_disqualify({q: False for q in qs}) is None
    assert eligibility.answers_disqualify({"alcohol_24h": False, "tattoo_12m": True}) == "tattoo_12m"
    assert eligibility.next_question({"alcohol_24h": False})["id"] == qs[1]


def _donor(**kw):
    base = dict(blood_group="O+", alerts_sent=0, alerts_responded=0, alerts_accepted=0, no_shows=0, reply_hours=[], last_alerted_at=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_ranking_bounds_and_smoothing():
    now = datetime(2026, 10, 14, 9)
    f = ranking.features(_donor(), "B+", 2.0, 40, 14, now)
    assert f["response_rate"] == 0.5 and f["time_of_day_fit"] == 0.5
    assert 0 <= ranking.score(f) <= 1
    worst = ranking.features(_donor(blood_group="O-", alerts_sent=50, no_shows=10, last_alerted_at=now), "B+", 40, 40, 3, now)
    best = ranking.features(_donor(blood_group="B+", alerts_sent=10, alerts_responded=10, alerts_accepted=10, reply_hours=[14] * 10,
                                   last_alerted_at=now - timedelta(days=60)), "B+", 0.1, 40, 14, now)
    assert 0 <= ranking.score(worst) < ranking.score(best) <= 1


@pytest.mark.parametrize("text,pending,intent,extra", [
    ("haan aa raha hun, 20 min", None, "accept", {"eta_minutes": 20}),
    ("aaj nahi ho payega bhai", None, "decline", {}),
    ("kal raat ek peg liya tha", "alcohol_24h", "eligibility_answer", {"eligibility_answer": True}),
    ("nahi", "tattoo_12m", "eligibility_answer", {"eligibility_answer": False}),
    ("I'm in Noida this week", None, "location_update", {"location_text": "Noida"}),
    ("is it safe to donate after covid vaccine?", None, "question", {}),
    ("pause 10", None, "pause", {"pause_days": 10}),
    ("stop", None, "stop", {}),
])
def test_rule_parser(text, pending, intent, extra):
    out = rule_parse(text, pending)
    assert out["intent"] == intent, out
    for k, v in extra.items():
        assert out[k] == v, out


def test_tinyfish_validation():
    ok = {"district_selected": "South Delhi", "banks": [{"name": "AIIMS", "stock": {"B+Ve": "4", "O-Ve": 0, "Oh+Ve": 2, "bad": 1}}]}
    banks, err = validate_result(ok)
    assert err is None and banks[0]["stock"] == {"B+": 4, "O-": 0}
    assert validate_result({"district_selected": "x", "banks": []}) == ([], None)
    assert validate_result({"error": "captcha shown"})[1] == "captcha shown"
    assert validate_result(None)[1] == "empty result"
    assert validate_result("some prose")[1]
    assert validate_result({"banks": "nope"})[1] == "bad_shape"
    assert validate_result([{"name": "X", "stock": {}}, {"name": ""}])[0][0]["name"] == "X"
