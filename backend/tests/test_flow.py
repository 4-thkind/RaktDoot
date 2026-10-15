"""End to end in mock-WhatsApp mode: request -> stock -> waves -> donor accepts -> pre-screen ->
connected -> target met -> pending donors told -> donation -> rest period enforced."""
from datetime import date, timedelta

from app.core import eligibility
from app.core.compatibility import compatible_donors
from app.core.geo import haversine_km
from app.db import SessionLocal
from app.models import Donor, Notification
from app.services import dispatch

ADMIN = {"X-Admin-Token": "test-admin"}
SAKET = {"hospital_name": "Max Super Speciality Hospital, Saket", "hospital_lat": 28.5276, "hospital_lng": 77.2117}


def make_request(c, group="B+", units=1, phone="9876543210", **kw):
    body = {"patient_group": group, "units": units, "patient_age": 34, "patient_gender": "M",
            "requester_name": "Riya", "requester_phone": phone, **SAKET, **kw}
    r = c.post("/api/requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def say(c, phone, text="", button=None):
    r = c.post("/api/mock/inbound", json={"phone": phone, "text": text, "button_id": button})
    assert r.status_code == 200, r.text
    return r.json()


def last_options(chat):
    return [o["id"] for o in next(m for m in reversed(chat["messages"]) if m["direction"] == "out" and m.get("options"))["options"]]


def accept_and_pass(c, phone):
    chat = c.get(f"/api/mock/chats/{phone}").json()
    acc = next(i for i in last_options(chat) if i.startswith("acc:"))
    chat = say(c, phone, button=acc)
    for _ in range(len(eligibility.questions())):
        no = next(i for i in last_options(chat) if i.startswith("el:") and i.endswith(":n"))
        chat = say(c, phone, button=no)
    return chat


def test_stock_demo_and_compat(fresh):
    r = fresh.get("/api/stock", params={"lat": 28.5276, "lng": 77.2117, "group": "B+"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sample"] is True and data["banks"], data
    assert data["compatible_groups"] == ["B+", "B-", "O+", "O-"]
    assert data["banks"][0]["distance_km"] <= data["banks"][-1]["distance_km"]
    assert set(data["banks"][0]["compatible_units"]) <= {"B+", "B-", "O+", "O-"}
    # second call is served from cache
    assert fresh.get("/api/stock", params={"lat": 28.5276, "lng": 77.2117, "group": "B+"}).json()["source"] == "cache"
    assert fresh.get("/api/stock", params={"lat": 28.5, "lng": 77.2, "group": "Z+"}).status_code == 422


def test_stock_stream_events(fresh):
    with fresh.stream("GET", "/api/stock/stream", params={"lat": 28.5276, "lng": 77.2117, "group": "O-"}) as r:
        body = "".join(r.iter_text())
    assert "event: progress" in body and "event: result" in body and "event: done" in body


def test_full_flow(fresh):
    c = fresh
    req = make_request(c, units=1)  # target = 2 connected donors
    rid, tok = req["id"], req["manage_token"]
    assert "Can receive from: B+, B-, O+, O-" in req["preview"]
    assert c.get(f"/api/requests/{rid}", params={"t": "wrong"}).status_code == 404

    r = c.post(f"/api/requests/{rid}/dispatch", params={"t": tok})
    assert r.status_code == 200 and 0 < r.json()["sent"] <= 10, r.text

    with SessionLocal() as db:
        notes = db.query(Notification).filter_by(request_id=rid).all()
        today = dispatch.local_today()
        for n in notes:
            d = n.donor
            assert d.blood_group in compatible_donors("B+")
            assert haversine_km(SAKET["hospital_lat"], SAKET["hospital_lng"], d.lat, d.lng) <= 5.0 + 1e-6
            assert not eligibility.in_rest_period(d.last_donation_date, d.gender, today)
        phones = [n.donor.phone for n in sorted(notes, key=lambda n: -n.score)]

    snap = c.get(f"/api/requests/{rid}", params={"t": tok}).json()
    assert snap["status"] == "dispatching" and snap["funnel"]["notified"] == len(phones)
    assert all(d["phone"] is None for d in snap["donors"])

    # donor 1 declines by free text, donor 2 fails the pre-screen, donors 3 and 4 pass
    say(c, phones[0], "aaj nahi ho payega")
    chat = c.get(f"/api/mock/chats/{phones[1]}").json()
    chat = say(c, phones[1], button=next(i for i in last_options(chat) if i.startswith("acc:")))
    say(c, phones[1], "kal raat ek peg liya tha")  # free-text answer to the alcohol question -> deferred
    accept_and_pass(c, phones[2])
    chat = accept_and_pass(c, phones[3])
    assert any("Family contact" in m["body"] for m in chat["messages"])

    snap = c.get(f"/api/requests/{rid}", params={"t": tok}).json()
    assert snap["status"] == "matched", snap["counts"]
    assert snap["counts"].get("declined") == 1 and snap["counts"].get("ineligible") == 1
    assert snap["counts"].get("connected") == 2
    assert all(d["phone"] for d in snap["donors"] if d["status"] == "connected")
    if len(phones) > 4:  # everyone still pending was told they are not needed
        pending_chat = c.get(f"/api/mock/chats/{phones[4]}").json()
        assert "covered" in pending_chat["messages"][-1]["body"]

    # a late tap on an old alert gets a polite "already covered"
    if len(phones) > 4:
        old = c.get(f"/api/mock/chats/{phones[4]}").json()
        late = say(c, phones[4], button=next(i for m in old["messages"] for o in (m.get("options") or []) for i in [o["id"]] if i.startswith("acc:")))
        assert "already got help" in late["messages"][-1]["body"]

    # 24 h later the bot asks "did you donate?"; donor 3 says yes
    t = c.post("/api/admin/tick", params={"advance_hours": 3}, headers=ADMIN).json()
    assert t["onway"] == 2 and t["followups"] == 0
    t = c.post("/api/admin/tick", params={"advance_hours": 25}, headers=ADMIN).json()
    assert t["followups"] == 2 and t["expired"] == 1
    chat = c.get(f"/api/mock/chats/{phones[2]}").json()
    say(c, phones[2], button=next(i for i in last_options(chat) if i.startswith("fu:") and i.endswith(":y")))
    with SessionLocal() as db:
        d = db.query(Donor).filter_by(phone=phones[2]).one()
        assert d.last_donation_date == dispatch.local_today() and d.donations_confirmed >= 1

    # a new request: the donor who just donated is in rest and must not be messaged
    c.post(f"/api/requests/{rid}/fulfil", params={"t": tok})
    with SessionLocal() as db:  # clear the 24 h alert limit so only the rest period can exclude them
        for d in db.query(Donor).all():
            d.last_alerted_at = None
        db.commit()
    req2 = make_request(c, phone="9876500000", units=6)
    c.post(f"/api/requests/{req2['id']}/dispatch", params={"t": req2["manage_token"]})
    for _ in range(6):
        c.post(f"/api/requests/{req2['id']}/widen", params={"t": req2["manage_token"]})
    with SessionLocal() as db:
        donated = db.query(Donor).filter_by(phone=phones[2]).one()
        assert not db.query(Notification).filter_by(request_id=req2["id"], donor_id=donated.id).count()


def test_share_page_has_no_pii(fresh):
    req = make_request(fresh)
    data = fresh.get(f"/api/share/{req['share_slug']}").json()
    flat = str(data)
    assert "9876543210" not in flat and "Riya" not in flat
    assert data["compatible"] == ["B+", "B-", "O+", "O-"]


def test_rate_limit_per_phone(fresh):
    for _ in range(3):
        make_request(fresh, phone="9000000001")
    r = fresh.post("/api/requests", json={"patient_group": "A+", "units": 1, "patient_age": 30, "patient_gender": "F",
                                          "requester_name": "X", "requester_phone": "9000000001", **SAKET})
    assert r.status_code == 429


def test_onboarding_and_stop(fresh):
    c, p = fresh, "919811112222"
    say(c, p, "JOIN")
    say(c, p, button="lang:en")
    say(c, p, "Aman Verma")
    say(c, p, button="grp:O+")
    chat = say(c, p, "01-01-2015")
    assert "18 and 65" in chat["messages"][-1]["body"]  # under-18 declined

    say(c, p, "JOIN")
    say(c, p, "2")             # numbered reply -> second button (Hindi)
    say(c, p, "Aman Verma")
    say(c, p, "o positive")
    say(c, p, "14-08-1999")
    say(c, p, button="g:M")
    say(c, p, button="w:y")
    r = c.post("/api/mock/inbound", json={"phone": p, "lat": 28.53, "lng": 77.21})
    say(c, p, button="last:never")
    chat = say(c, p, button="c:y")
    assert "पंजीकरण" in chat["messages"][-1]["body"]
    with SessionLocal() as db:
        d = db.query(Donor).filter_by(phone=p).one()
        assert d.blood_group == "O+" and d.language == "hi" and d.consent and d.dob == date(1999, 8, 14)
    say(c, p, "STOP")
    with SessionLocal() as db:
        assert db.query(Donor).filter_by(phone=p).one().opted_out


def test_rest_period_excluded_in_sql(fresh):
    with SessionLocal() as db:
        d = db.query(Donor).filter(Donor.blood_group == "B+").first()
        d.lat, d.lng, d.gender = SAKET["hospital_lat"], SAKET["hospital_lng"], "F"
        d.last_donation_date = dispatch.local_today() - timedelta(days=100)  # women: 120 days
        d.last_alerted_at, d.paused_until = None, None
        db.commit()
        did = d.id
    req = make_request(fresh)
    with SessionLocal() as db:
        from app.models import Request
        r = db.get(Request, req["id"])
        assert did not in {c["donor"].id for c in dispatch.find_candidates(db, r, 40)}
        d = db.get(Donor, did)
        d.last_donation_date = dispatch.local_today() - timedelta(days=121)
        db.commit()
        assert did in {c["donor"].id for c in dispatch.find_candidates(db, r, 40)}


def test_cloud_webhook_signature_and_parse(fresh, monkeypatch):
    import hashlib
    import hmac
    import json as _json

    from app.config import settings
    monkeypatch.setattr(settings, "whatsapp_app_secret", "s3cret")
    body = _json.dumps({"entry": [{"changes": [{"value": {"messages": [
        {"from": "919800000001", "id": "wamid.1", "type": "text", "text": {"body": "JOIN"}}]}}]}]}).encode()
    assert fresh.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": "sha256=bad"}).status_code == 401
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert fresh.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": sig}).status_code == 200
    chat = fresh.get("/api/mock/chats/919800000001").json()
    assert chat["messages"][-1]["options"][0]["id"] == "lang:en"
    r = fresh.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": settings.whatsapp_verify_token, "hub.challenge": "42"})
    assert r.text == "42"
