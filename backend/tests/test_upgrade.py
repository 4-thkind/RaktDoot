"""Tests for the upgrade: components, eRaktKosh parsing, directory matching, replay + healing, hospital
evidence, extraction, forward checker, vision, voice, agentic dispatcher, bandit, why-you, rota,
radar, camp placement, family guide, migrations, proof of donation."""
import asyncio
import json
from datetime import date, timedelta

import pytest

from app.config import settings
from app.core import explain
from app.core.compatibility import compatible_donors, normalize_component, receives_from
from app.db import SessionLocal
from app.models import (BanditArm, Donation, Donor, Forward, Notification, Recipe, RecurringNeed,
                        RecurringSlot, Request, StockHistory)
from app.services import (bandit, camp_placement, directory, dispatch, dispatch_agent, eraktkosh, extraction, forecast,
                          forwards, guide, recurring, replay, stt, tinyfish_client, vision)

ADMIN = {"X-Admin-Token": "test-admin"}
SAKET = {"hospital_name": "Max Super Speciality Hospital, Saket", "hospital_lat": 28.5276, "hospital_lng": 77.2117}


def say(c, phone, text="", button=None, **media):
    r = c.post("/api/mock/inbound", json={"phone": phone, "text": text, "button_id": button, **media})
    assert r.status_code == 200, r.text
    return r.json()


def make_request(c, group="B+", units=1, phone="9876543210", **kw):
    body = {"patient_group": group, "units": units, "patient_age": 34, "patient_gender": "M",
            "requester_name": "Riya", "requester_phone": phone, **SAKET, **kw}
    r = c.post("/api/requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- W1 components
def test_component_tables():
    assert compatible_donors("AB+", "plasma") == ["AB+", "AB-"]          # AB plasma only for AB patients
    assert set(receives_from("O+", "plasma")) == {"O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"}
    assert all(g.endswith("-") for g in receives_from("A-", "platelets"))  # Rh- patient: Rh- platelets
    assert compatible_donors("A+", "platelets")[0] == "A+"
    assert compatible_donors("B+", "whole_blood") == compatible_donors("B+")
    assert normalize_component("Don't know") == "prbc" and normalize_component("FFP") == "plasma" and normalize_component("SDP") == "platelets"


def test_stock_api_component(fresh):
    data = fresh.get("/api/stock", params={"lat": 28.5276, "lng": 77.2117, "group": "AB+", "component": "plasma"}).json()
    assert data["component"] == "plasma" and data["compatible_groups"] == ["AB+", "AB-"]
    assert data["component_label"] == "Fresh Frozen Plasma" and data["served_by"] == "sample"
    r = make_request(fresh, group="O+", component="platelets")
    snap = fresh.get(f"/api/requests/{r['id']}", params={"t": r["manage_token"]}).json()
    assert snap["component"] == "platelets" and "Component: Random Donor Platelets" in snap["preview"]


# ---------------------------------------------------------------- eRaktKosh parsing (real row shapes)
STOCK_ROWS = {"data": [
    ["1", "-<br/>1, Red Cross Road, Sansad Marg Area, New Delhi<br/>-", "null", "<p class='text-danger'><b>Packed Red Blood Cells</b>Not Available", "2026-07-13 11:14:24", "Blood Bank"],
    ["2", "ABVIMS, Dr Ram Manohar Lohia Hospital<br/>Baba Kharak Singh Marg, New Delhi<br/>Phone: 23404286 ,Fax: 23361758  , Email: x@y.com", "Govt.",
     "<p class='text-success'>Available, B-Ve:5, A+Ve:43, Oh+VE:1, O-Ve:6</p>", "<img src='../live_stock.png'>", "Blood Bank"]]}


def test_eraktkosh_parsers():
    banks = eraktkosh.parse_stock_rows(STOCK_ROWS)
    assert banks[0]["name"] == "Blood centre, Red Cross Road" and banks[0]["stock"] == {}
    assert banks[1]["stock"] == {"B-": 5, "A+": 43, "O-": 6} and banks[1]["phone"] == "23404286" and banks[1]["last_updated"] == "live"
    d = eraktkosh.parse_directory_rows({"data": [["1", "Blood Bank of AIIMS", "Ansari Nagar East, New Delhi, Dist. South West", "9868397041",
                                                  "someone@gmail.com", "Govt.", "-", "<a href='x?hospitalCode=324'>Camps</a>", "Blood Bank"]]})
    assert d[0]["district"] == "South West" and d[0]["eraktkosh_code"] == "324" and "gmail" not in json.dumps(d)
    camps_ = eraktkosh.parse_camp_rows({"data": [["1", "20-Oct-2026<br/>x", "Camp", "Addr", "Haryana", "Palwal", "9991912976", "Apna Blood Centre",
                                                  "Dipu Kalra", "<a href='/BLDAHIMS/x.cnt?&campid=1245004&type=0'>Reg</a>", "10:00-15:00"]]})
    assert camps_[0]["camp_date"] == date(2026, 10, 20) and camps_[0]["external_id"] == "1245004"
    assert "9991912976" not in json.dumps(camps_, default=str) and "Dipu" not in json.dumps(camps_, default=str)  # organiser PII dropped
    assert eraktkosh.match_district("South Delhi", [{"id": "South", "value": "98"}, {"id": "South West", "value": "97"}]) == "98"


def test_directory_matching():
    dir_ = [{"name": "Blood Bank of AIIMS", "phone": "9868397041", "address": "Ansari Nagar East"},
            {"name": "Blood Centre, Max Super Specialty Hospital", "phone": "1126515050", "address": "Press Enclave Road, Saket"}]
    assert directory.best_match({"name": "AIIMS Main Blood Bank"}, dir_)[0] is dir_[0]
    best, score = directory.best_match({"name": "Max Hospital Blood Centre", "phone": "011-26515050"}, dir_)
    assert best is dir_[1] and score > 1.0  # phone match boosts
    assert directory.best_match({"name": "Totally Different Place"}, dir_)[0] is None
    assert directory.clean_name("Blood Bank, Fortis Flt.Lt. Rajan Dhall Hospital (A Unit Of X") == "Fortis Flt.Lt. Rajan Dhall Hospital"


# ---------------------------------------------------------------- 2.4 replay + healing
class FakePage:
    def __init__(self, district_json, stock_json):
        self.responses = [district_json, stock_json]
        self.visited = []

    async def goto(self, url, **kw):
        self.visited.append(url)

    async def evaluate(self, js, url):
        self.visited.append(url)
        return self.responses.pop(0)


def test_replay_execute_success_and_failure():
    dist = json.dumps({"records": [{"id": "South", "value": "98"}]})
    page = FakePage(dist, json.dumps(STOCK_ROWS))
    v = replay.variables({}, "Delhi", "South Delhi", "prbc")
    banks = asyncio.run(replay.execute(page, replay.DEFAULT_STEPS, v))
    assert banks[1]["stock"]["A+"] == 43 and "districtCode=98" in page.visited[-1] and "bloodComponent=12" in page.visited[-1]
    with pytest.raises(replay.ReplayError):
        asyncio.run(replay.execute(FakePage(dist, "<html>Error</html>"), replay.DEFAULT_STEPS, replay.variables({}, "Delhi", "South", "prbc")))
    with pytest.raises(replay.ReplayError):
        asyncio.run(replay.execute(FakePage(json.dumps({"records": []}), "{}"), replay.DEFAULT_STEPS, replay.variables({}, "Delhi", "Nowhere", "prbc")))
    learned = {"components": {"platelets": "99"}}
    assert replay.variables(learned, "Delhi", "South", "platelets")["component_code"] == "99"  # learned code wins


def _live(monkeypatch):
    monkeypatch.setattr(settings, "tinyfish_api_key", "test-key")
    monkeypatch.setattr(settings, "tinyfish_mode", "live")


def _emit_sink():
    seen = []

    async def emit(ev):
        seen.append(ev)
    return seen, emit


def test_lookup_served_by_replay(fresh, monkeypatch):
    _live(monkeypatch)

    async def fake_run(steps, learned, state, district, component):
        return eraktkosh.parse_stock_rows(STOCK_ROWS), {"session_id": "s1", "warm": True, "duration_ms": 900, "district_code": "98"}
    monkeypatch.setattr(replay, "run", fake_run)
    seen, emit = _emit_sink()
    out = asyncio.run(tinyfish_client.lookup_stock("Delhi", "Replay District", (28.6262, 77.2004), emit, "prbc"))
    assert out["source"] == "live" and out["served_by"] == "replay" and out["run_id"].startswith("recipe-v")
    with SessionLocal() as db:
        assert db.query(StockHistory).filter_by(district="Replay District", source="replay").count() == 3  # B-, A+, O- rows
        assert db.query(Recipe).filter_by(active=True).one().success_count == 1


def test_replay_failure_falls_back_to_agent_and_heals(fresh, monkeypatch):
    from tests.test_tinyfish_live import FakeStream, _events
    import tinyfish
    _live(monkeypatch)

    async def broken(*a, **kw):
        raise replay.ReplayError("stock payload has no data table")
    monkeypatch.setattr(replay, "run", broken)
    result = {"district_selected": "South", "form_values": {"state_value": "97", "district_value": "98", "component_value": "12"},
              "banks": [{"name": "AIIMS Main Blood Bank", "stock": {"B+": 6}}]}
    calls = []

    class Agent:
        def stream(self, **kw):
            calls.append(kw)
            return FakeStream(_events(result))

    class Client:
        def __init__(self, api_key=None, timeout=None):
            self.agent = Agent()
    monkeypatch.setattr(tinyfish, "AsyncTinyFish", Client)
    with SessionLocal() as db:
        before = db.query(Recipe).count()
    seen, emit = _emit_sink()
    out = asyncio.run(tinyfish_client.lookup_stock("Delhi", "Heal District", (28.5672, 77.21), emit, "prbc"))
    assert out["served_by"] == "agent" and out["source"] == "live"
    kw = calls[0]
    assert kw["output_schema"]["properties"]["banks"]["type"] == "array"                       # W3
    assert kw["proxy_config"].model_dump(exclude_none=True) == {"enabled": True, "country_code": "IN"}  # W4
    with SessionLocal() as db:
        recipes = db.query(Recipe).order_by(Recipe.version).all()
        assert len(recipes) > before and recipes[-1].active and recipes[-1].created_from_run_id == "run_123"
        assert recipes[0].fail_count == 1 and not recipes[0].active  # the failing version was replaced
        assert recipes[-1].learned["districts"]["Delhi/Heal District"] == "98"                    # learned, re-saved
        assert db.query(StockHistory).filter_by(district="Heal District", source="agent").count() == 1


def test_hospital_check_has_evidence(fresh):
    r = make_request(fresh)
    check = r["hospital_check"]
    assert check["verified"] is True and check["evidence"][0]["source"].endswith("directory") and check["score"] >= 0.6
    r2 = make_request(fresh, phone="9876500001", hospital_name="Imaginary Clinic Xyz")
    assert r2["hospital_check"]["verified"] is None  # demo mode: no web search, so 'could not verify', not 'fake'


# ---------------------------------------------------------------- shared extraction + F2 forward checker
PLEA = ("URGENT!! B+ve blood needed for my father at Safdarjung Hospital, 2 units PRBC, ward 12. "
        "Contact Rahul 98765 12345. Date: {d}. Please forward to all groups")


def test_extraction_rules():
    f = extraction.rule_extract(PLEA.format(d="19/10/2026"), date(2026, 10, 20))
    assert (f["patient_group"], f["units"], f["component"], f["phone"], f["date"], f["ward"]) == ("B+", 2, "prbc", "919876512345", "2026-10-19", "12")
    assert "Safdarjung" in f["hospital"]
    h = extraction.rule_extract("Papa ko B positive blood chahiye, Safdarjung hospital mein, do unit. Urgent hai.")
    assert h["patient_group"] == "B+" and h["units"] == 2 and h["urgency"] == "urgent"
    assert extraction.rule_extract("मरीज़ को ओ नेगेटिव खून चाहिए")["patient_group"] == "O-"
    v = extraction.validate({"patient_group": "C+", "units": 40, "phone": "12345", "confidence": {"units": 2}})
    assert v["patient_group"] is None and v["units"] is None and v["phone"] is None
    assert extraction.is_plea(PLEA.format(d="today")) and not extraction.is_plea("haan aa raha hun, 20 min")


def test_forward_verdicts(fresh):
    c = fresh
    today = date.today()
    res = c.post("/api/forwards/check", json={"text": PLEA.format(d=today.strftime("%d/%m/%Y"))}).json()
    assert res["verdict"] == "looks_genuine", res
    assert res["fields"]["phone"].endswith("12345") and "98765" not in res["fields"]["phone"]  # masked
    assert res["reasons"][0]["en"] and res["reasons"][0]["hi"]
    old = c.post("/api/forwards/check", json={"text": PLEA.format(d=(today - timedelta(days=9)).strftime("%d/%m/%Y"))}).json()
    assert old["verdict"] == "likely_stale" and any(r["key"] == "date_old" for r in old["reasons"])
    scam = c.post("/api/forwards/check", json={"text": "O-ve blood needed at AIIMS urgently, send Rs 2000 transport charges on UPI 98765 00000 first"}).json()
    assert scam["verdict"] == "possible_scam"
    dup = "A+ blood required at Apollo hospital, call 9811122233, please share widely"
    for _ in range(3):
        c.post("/api/forwards/check", json={"text": dup})
    assert c.post("/api/forwards/check", json={"text": dup}).json()["verdict"] == "likely_stale"
    with SessionLocal() as db:
        assert all("98765" not in json.dumps(f.fields) for f in db.query(Forward).all())  # hashes + masked only


def test_forward_in_simulator_and_create(fresh):
    c, p = fresh, "919822233344"
    chat = say(c, p, PLEA.format(d=date.today().strftime("%d/%m/%Y")))
    bodies = [m["body"] for m in chat["messages"] if m["direction"] == "out"]
    assert any("looks genuine" in b for b in bodies)
    opts = [o["id"] for m in chat["messages"] if m.get("options") for o in m["options"]]
    alert = next(i for i in opts if i.startswith("fw:alert:"))
    chat = say(c, p, button=alert)
    assert "being alerted" in chat["messages"][-1]["body"]
    with SessionLocal() as db:
        r = db.query(Request).filter_by(requester_phone=p).one()
        assert r.status == "dispatching" and r.patient_group == "B+" and r.units == 2


# ---------------------------------------------------------------- F3 / F9 vision, F4 voice
def test_slip_scan_sample_and_confidence(fresh):
    out = fresh.post("/api/vision/slip", params={"sample": "requisition_slip.jpg"}).json()
    assert out["sample"] and out["fields"]["patient_group"] == "B+" and out["fields"]["component"] == "prbc"
    assert "ward" in out["low_confidence"]
    bad = fresh.post("/api/vision/slip", files={"file": ("x.jpg", b"not really an image", "image/jpeg")}).json()
    assert bad["fields"] is None and "sample" in bad["error"]
    assert fresh.get("/api/samples/requisition_slip.jpg").status_code == 200
    assert fresh.get("/api/samples/..%2F..%2Fapp%2Fconfig.py").status_code == 404


def test_card_validation():
    today = date(2026, 10, 20)
    assert vision.validate_card({"donation_date": "2026-10-25"}, today)["donation_date"] is None       # future
    assert vision.validate_card({"donation_date": "2026-10-01"}, today, date(2026, 10, 19))["donation_date"] is None  # before the alert
    ok = vision.validate_card({"donation_date": "2026-10-19", "centre": "AIIMS", "confidence": {"donation_date": 0.9}}, today, date(2026, 10, 18))
    assert ok["donation_date"] == date(2026, 10, 19) and ok["confidence"] == 0.9


def test_stt_demo():
    data = vision.sample_bytes("voice_request.mp3")
    assert stt.transcribe(data, "audio/wav")["text"].startswith("Papa ko B positive")
    assert stt.transcribe(b"random", "audio/ogg")["text"] == ""


def _pending_donor(c):
    req = make_request(c)
    c.post(f"/api/requests/{req['id']}/dispatch", params={"t": req["manage_token"]})
    with SessionLocal() as db:
        n = db.query(Notification).filter_by(request_id=req["id"]).first()
        return req, n.donor.phone, n.id


def test_voice_note_accepts_alert(fresh):
    req, phone, nid = _pending_donor(fresh)
    chat = say(fresh, phone, media_kind="audio", media_sample="voice_accept.mp3")
    voice = next(m for m in chat["messages"] if m["direction"] == "in" and m.get("media") == "audio")
    assert voice["transcript"].startswith("हाँ") and "[voice note]" in voice["body"]
    with SessionLocal() as db:
        assert db.get(Notification, nid).status == "accepted"


def test_voice_note_request_goes_to_checker(fresh):
    """A spoken first-person request skips the forward checker and goes straight to the request flow."""
    chat = say(fresh, "919811100099", media_kind="audio", media_sample="voice_request.mp3")
    outs = [m for m in chat["messages"] if m["direction"] == "out"]
    assert any("Alert compatible donors" in m["body"] or "अलर्ट करें" in m["body"] for m in outs)
    assert any(o["id"] == "rq:yes" for m in outs for o in (m.get("options") or []))


def test_proof_of_donation_photo(fresh):
    from tests.test_flow import accept_and_pass, last_options
    c = fresh
    req, phone, nid = _pending_donor(c)
    accept_and_pass(c, phone)
    c.post("/api/admin/tick", params={"advance_hours": 25}, headers=ADMIN)
    chat = c.get(f"/api/mock/chats/{phone}").json()
    chat = say(c, phone, button=next(i for i in last_options(chat) if i.startswith("fu:") and i.endswith(":y")))
    assert "photo" in chat["messages"][-1]["body"]
    chat = say(c, phone, media_kind="image", media_sample="donor_card.jpg")
    assert "Verified" in chat["messages"][-1]["body"] or "पुष्टि" in chat["messages"][-1]["body"]
    with SessionLocal() as db:
        d = db.query(Donor).filter_by(phone=phone).one()
        assert d.donations_verified == 1 and db.query(Donation).filter_by(donor_id=d.id).one().confirmed_by == "photo"


# ---------------------------------------------------------------- F5 agentic dispatcher
def test_dispatch_agent_fallback_and_llm(fresh, monkeypatch):
    req, _, _ = _pending_donor(fresh)
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(dispatch_agent.llm, "chat_json", lambda *a, **k: {"action": "message_donor_directly", "args": {}})
    with SessionLocal() as db:
        r = db.get(Request, req["id"])
        d = dispatch_agent.step(db, r)
        assert d.engine == "fallback" and d.action in dispatch_agent.ACTIONS
        monkeypatch.setattr(dispatch_agent.llm, "chat_json", lambda *a, **k: {"action": "include_o_negative", "args": {}, "reason": "x"})
        st = dispatch_agent.state(db, r, r.dispatched_at)
        assert not dispatch_agent.o_neg_allowed(st) and dispatch_agent.validate({"action": "include_o_negative"}, st) is None  # policy
        monkeypatch.setattr(dispatch_agent.llm, "chat_json", lambda *a, **k: {"action": "wait", "args": {"minutes": 99}, "reason": "give donors time"})
        d = dispatch_agent.step(db, r)
        assert d.engine == "llm" and d.args == {"minutes": 30}  # clamped
        db.commit()
    snap = fresh.get(f"/api/requests/{req['id']}", params={"t": req["manage_token"]}).json()
    assert len(snap["decisions"]) >= 3 and "connected" in snap["decisions"][0]["reason"]


def test_alert_caps(fresh, monkeypatch):
    monkeypatch.setattr(settings, "max_alerts_per_request", 3)
    req = make_request(fresh, units=6)
    sent = fresh.post(f"/api/requests/{req['id']}/dispatch", params={"t": req["manage_token"]}).json()["sent"]
    for _ in range(3):
        fresh.post(f"/api/requests/{req['id']}/widen", params={"t": req["manage_token"]})
    with SessionLocal() as db:
        assert sent <= 3 and db.query(Notification).filter_by(request_id=req["id"]).count() <= 3


def test_o_neg_reserved_until_allowed(fresh):
    req = make_request(fresh, group="B+")
    with SessionLocal() as db:
        r = db.get(Request, req["id"])
        assert not any(c["donor"].blood_group == "O-" for c in dispatch.find_candidates(db, r, 40))
        o_neg_near = [c for c in dispatch.find_candidates(db, r, 40) if c["donor"].blood_group == "O-"]
        assert not o_neg_near
        r.allow_o_neg = True
        released = {c["donor"].blood_group for c in dispatch.find_candidates(db, r, 40)}
        has_o_neg = db.query(Donor).filter(Donor.blood_group == "O-", Donor.consent.is_(True)).count()
        assert ("O-" in released) or not has_o_neg


# ---------------------------------------------------------------- F11 bandit, F12 why-you
def test_bandit_converges(fresh):
    with SessionLocal() as db:
        out = bandit.simulate(db, n=1500, seed=3)
        db.commit()
        assert out["chosen_most"] == out["true_best"] == "why_you"
        best = db.query(BanditArm).filter_by(variant="why_you", simulated=True).one()
        assert best.pulls > 1500 * 0.4


def test_bandit_updates_from_outcomes(fresh):
    req, phone, nid = _pending_donor(fresh)
    say(fresh, phone, "nahi aaj nahi")  # decline -> reward 0
    with SessionLocal() as db:
        n = db.get(Notification, nid)
        arm = db.query(BanditArm).filter_by(variant=n.variant, segment=n.segment, simulated=False).one()
        assert arm.beta >= 2 and n.reason


def test_why_you_reasons():
    f = {"response_rate": 0.8, "time_of_day_fit": 0.2}
    en = explain.why_you(f, 2.1, "B-", "B-", "en", {"district": "South", "groups": ["B-"]})
    assert en == "You're 2.1 km away and B− is short in South today."
    hi = explain.why_you(f, 2.1, "B-", "B-", "hi", {"district": "South", "groups": ["B-"]})
    assert "किमी" in hi and "कमी" in hi
    assert explain.reasons({}, 12, "O+", "B+")[0] == "near"
    assert explain.why_you({"response_rate": 0.9}, 8, "O+", "B+") == "You're 8.0 km away and you've answered quickly before."


# ---------------------------------------------------------------- F7 rota
def test_rota_six_months_no_violations(fresh):
    with SessionLocal() as db:
        need = db.query(RecurringNeed).filter_by(synthetic=True).one()
        slots = recurring.rebuild(db, need, horizon_days=182)
        donors = recurring.candidates(db, need, date.today())
        schedule = {}
        for s in slots:
            schedule.setdefault(s.due_date, []).append(s.donor_id)
        assert len(schedule) >= 8
        assert recurring.violations(donors, recurring.history_for(db, donors), schedule) == []
        filled = sum(1 for s in slots if s.donor_id)
        assert filled >= 0.8 * len(slots)
        per = {}
        for s in slots:
            if s.donor_id:
                per[s.donor_id] = per.get(s.donor_id, 0) + 1
        assert max(per.values()) <= 3  # fairness + rest periods spread the load
        db.commit()


def test_rota_reminder_and_confirm(fresh):
    t = fresh.post("/api/admin/tick", headers=ADMIN).json()
    assert t["rota_reminders"] >= 1
    with SessionLocal() as db:
        s = db.query(RecurringSlot).filter_by(status="reminded").first()
        phone, sid = s.donor.phone, s.id
    chat = fresh.get(f"/api/mock/chats/{phone}").json()
    assert "rota" in chat["messages"][-1]["body"] or "रोटा" in chat["messages"][-1]["body"]
    say(fresh, phone, button=f"rc:{sid}:n")
    with SessionLocal() as db:
        assert db.get(RecurringSlot, sid).status == "declined"
        replacement = db.query(RecurringSlot).filter(RecurringSlot.due_date == db.get(RecurringSlot, sid).due_date,
                                                     RecurringSlot.status.in_(("planned", "unfilled")), RecurringSlot.id != sid).count()
        assert replacement >= 1
    assert fresh.get("/api/recurring/demo").json()["slots"]


# ---------------------------------------------------------------- F1 radar
def test_radar_backtest_and_drive(fresh, monkeypatch):
    monkeypatch.setattr(settings, "forecast_enabled", True)
    forecast._cache.clear()
    data = fresh.get("/api/radar", params={"component": "platelets"}).json()
    assert data["synthetic"] and data["cells"] and all(0 <= c["risk"] <= 1 for c in data["cells"])
    assert any("dengue" in f for c in data["cells"] for f in c["factors"]) or date.today().month not in (9, 10, 11)
    bt = fresh.get("/api/admin/radar/backtest", headers=ADMIN, params={"component": "prbc"}).json()
    assert bt["points"] > 1000 and bt["mae"] is not None and bt["mae"] <= bt["naive_mae"] * 1.2
    cell = data["cells"][0]
    r = fresh.post("/api/admin/radar/drive", headers=ADMIN, params={"district": cell["district"], "group": "O+", "component": "prbc"})
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        drive = db.get(Request, r.json()["id"])
        assert drive.kind == "drive"
        n = db.query(Notification).filter_by(request_id=drive.id).first()
        if n:  # donors near that bank may all be resting; when someone is alerted it is a drive message
            assert n.variant == "drive"


def test_holt_forecast_tracks_trend():
    start = date(2026, 1, 1)
    series = [(start + timedelta(days=i), 100 - 2 * i) for i in range(30)]
    pred = forecast.predict(series)
    assert pred["trend"] < -1 and pred["forecast"][-1][1] < 45
    risk, hours = forecast.risk_of(pred, 45)
    assert risk > 0.5 and hours is not None


# ---------------------------------------------------------------- F10 camp placement
def test_camp_scoring():
    sites = [{"name": "A", "lat": 28.60, "lng": 77.20}, {"name": "B", "lat": 28.40, "lng": 77.00}]
    donors = [(28.601, 77.201)] * 30 + [(28.401, 77.001)] * 5
    risk = [(28.6, 77.2, 0.9, "B- in Central")]
    scored = camp_placement.score_sites(sites, donors, risk, [(28.6, 77.21)], [], [])
    a, b = scored
    assert a["donor_pool"] == 30 and a["score"] > b["score"] and a["at_risk"] == ["B- in Central"]
    overlap = camp_placement.score_sites(sites[:1], donors, risk, [], [(28.6005, 77.2005, date.today())], [])[0]
    assert overlap["overlap"] and overlap["score"] < a["score"]
    picked = camp_placement.pick(scored, 1)
    assert picked[0]["name"] == "A" and "covers ~30" in picked[0]["reason"]


def test_placement_endpoint(fresh, monkeypatch):
    monkeypatch.setattr(settings, "forecast_enabled", True)
    out = fresh.get("/api/camps/placement", params={"k": 3}).json()
    assert len(out["sites"]) == 3 and out["sites"][0]["reason"]
    assert fresh.get("/api/camps/placement.csv").text.startswith("rank,name")


# ---------------------------------------------------------------- F13 family guide
def test_guide_cites_and_refuses(fresh):
    a = fresh.get("/api/guide/ask", params={"q": "How often can I donate blood?"}).json()
    assert not a["refused"] and a["sources"][0]["url"].startswith("https://") and "three" in a["answer"]
    assert fresh.get("/api/guide/ask", params={"q": "Who won the cricket world cup?"}).json()["refused"]
    h = fresh.get("/api/guide/ask", params={"q": "रक्तदान से पहले क्या खाएं?", "lang": "hi"}).json()
    assert not h["refused"] and h["sources"]
    p = fresh.get("/api/guide/ask", params={"q": "I am taking antibiotics, can I donate blood?"}).json()
    assert "blood centre doctor" in p["answer"]


def test_guide_on_whatsapp(fresh):
    req, phone, nid = _pending_donor(fresh)
    chat = say(fresh, phone, "is it ok to donate after drinking alcohol?")
    assert "eraktkosh" in chat["messages"][-1]["body"].lower()


# ---------------------------------------------------------------- migrations / config
def test_add_missing_columns(fresh):
    from sqlalchemy import text

    from app.db import add_missing_columns, engine
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE notifications DROP COLUMN reason"))
    assert "notifications.reason" in add_missing_columns()
    assert fresh.get("/api/config").json()["stt"] == "demo"


def test_tinyfish_panel_records_runs(fresh, monkeypatch):
    test_lookup_served_by_replay(fresh, monkeypatch)
    panel = fresh.get("/api/admin/tinyfish", headers=ADMIN).json()
    assert any(r["kind"] == "replay" and r["status"] == "ok" for r in panel["runs"]) and panel["recipes"]


def test_eligible_again_mentions_camp(fresh):
    with SessionLocal() as db:
        from app.models import Camp
        d = db.query(Donor).filter(Donor.gender == "M", Donor.lat.is_not(None)).first()
        d.last_donation_date = dispatch.local_today() - timedelta(days=90)
        d.eligible_again_notified = None
        db.add(Camp(camp_date=date.today() + timedelta(days=3), title="Camp at Test Hall", address="Test Hall", district="South",
                    state="Delhi", lat=d.lat, lng=d.lng, source="sample"))
        db.commit()
        phone = d.phone
    fresh.post("/api/admin/tick", headers=ADMIN)
    msgs = fresh.get(f"/api/mock/chats/{phone}").json()["messages"]
    assert any("rest period is over" in m["body"] and "camp" in m["body"] for m in msgs), [m["body"][:80] for m in msgs]

