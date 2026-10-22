"""Voice-first requests, family updates, voice replies (TTS), and assisted camp registration on the MOCK portal."""
import json
from datetime import date, timedelta

from app.db import SessionLocal
from app.models import Camp, CampRegistration, ChatMessage, Donor, MediaFile, Notification, Request
from app.services import extraction, tts

ADMIN = {"X-Admin-Token": "test-admin"}


def say(c, phone, text="", button=None, **media):
    r = c.post("/api/mock/inbound", json={"phone": phone, "text": text, "button_id": button, **media})
    assert r.status_code == 200, r.text
    return r.json()


def outs(chat):
    return [m for m in chat["messages"] if m["direction"] == "out"]


def options(chat):
    return [o["id"] for m in outs(chat) for o in (m.get("options") or [])]


# ---------------------------------------------------------------- extraction on speech output
def test_extraction_handles_asr_output():
    garbled = extraction.rule_extract("POP-A-K-O-B positive blood-cha-hi, SAF-DAR-JING hospital main, DO-UNIT. Urgent high.")
    assert (garbled["patient_group"], garbled["units"], garbled["hospital"]) == ("B+", 2, "Safdarjung Hospital")
    hi = extraction.rule_extract("मेरे पापा को बी पॉज़िटिव खून चाहिए, सफदरजंग अस्पताल में, दो यूनिट। बहुत जल्दी है।")
    assert (hi["patient_group"], hi["units"], hi["hospital"]) == ("B+", 2, "Safdarjung Hospital")
    assert extraction.rule_extract("mummy ko O negative chahiye saket city hospital me 3 unit")["hospital"] == "Saket City Hospital"
    # verbatim local-Whisper outputs for the sample voice notes
    for heard in ("Papa kubi positive blood chahiye, Safdar jung hospital mein, do unit.",
                  "Mere papa ko bhi positive khun chahiye, Saftar jaan hospital mein, 2 unit. Bhoot jaldi hai.",
                  "मेरे बापा को बी पॉज़िटिव कून जाहिए, सफदरजं अस्पताल में, दो यूनिट।"):
        f = extraction.rule_extract(heard)
        assert (f["patient_group"], f["units"], f["hospital"]) == ("B+", 2, "Safdarjung Hospital"), heard
    assert extraction.rule_extract("O bhi positive hai")["patient_group"] != "B+"  # 'bhi' after a group letter is not B
    assert extraction.is_request("B+ blood chahiye AIIMS") and not extraction.is_forward("B+ blood chahiye AIIMS")
    assert extraction.is_forward("A+ needed at Apollo, call 9811122233, please share")


# ---------------------------------------------------------------- the whole request by voice
def test_voice_request_end_to_end(fresh):
    c, p = fresh, "919811100099"
    chat = say(c, p, media_kind="audio", media_sample="voice_request.mp3")
    confirm = next(m for m in outs(chat) if m.get("options") and any(o["id"] == "rq:yes" for o in m["options"]))
    assert "2" in confirm["body"] and "Safdarjung" in confirm["body"]
    chat = say(c, p, button="rq:yes")
    assert "being alerted" in chat["messages"][-1]["body"] or "अलर्ट" in chat["messages"][-1]["body"]
    with SessionLocal() as db:
        r = db.query(Request).filter_by(requester_phone=p).one()
        assert (r.patient_group, r.units, r.status, r.language) == ("B+", 2, "dispatching", "hi")
        assert r.hospital_check["verified"] and db.query(Notification).filter_by(request_id=r.id).count() > 0


def test_typed_request_asks_only_whats_missing(fresh):
    c, p = fresh, "919811100098"
    chat = say(c, p, "mujhe O negative blood chahiye")
    assert outs(chat)[-1]["body"].startswith(("Which hospital", "मरीज़ किस"))
    chat = say(c, p, "AIIMS Delhi")
    assert set(options(chat)) >= {"u:1", "u:2", "u:3"}
    chat = say(c, p, button="u:2")
    assert "rq:yes" in options(chat)
    say(c, p, button="rq:yes")
    with SessionLocal() as db:
        r = db.query(Request).filter_by(requester_phone=p).one()
        assert (r.patient_group, r.units, r.allow_o_neg) == ("O-", 2, True)


def test_unknown_group_and_cancel(fresh):
    c, p = fresh, "919811100097"
    say(c, p, "blood chahiye urgently for my father B+ at Imaginary Clinic Xyzw")
    chat = c.get(f"/api/mock/chats/{p}").json()
    assert "Which hospital" in outs(chat)[-1]["body"] or "मरीज़ किस" in outs(chat)[-1]["body"]
    chat = say(c, p, button="rq:no")
    assert "nothing was sent" in chat["messages"][-1]["body"] or "कुछ नहीं भेजा" in chat["messages"][-1]["body"]


def test_family_told_when_donor_connects(fresh):
    from tests.test_flow import accept_and_pass
    c, p = fresh, "919811100096"
    say(c, p, "B+ blood chahiye Safdarjung hospital 1 unit")
    say(c, p, button="rq:yes")
    with SessionLocal() as db:
        r = db.query(Request).filter_by(requester_phone=p).one()
        donor_phone = db.query(Notification).filter_by(request_id=r.id).first().donor.phone
    accept_and_pass(c, donor_phone)
    fam = c.get(f"/api/mock/chats/{p}").json()
    assert any("is coming to donate" in m["body"] or "आ रहे हैं" in m["body"] for m in outs(fam))


# ---------------------------------------------------------------- voice replies
def test_voice_in_gets_voice_out(fresh, monkeypatch):
    monkeypatch.setattr(tts, "synthesize", lambda text, lang="en": (b"ID3-fake-mp3", "audio/mpeg", "fake"))
    chat = say(fresh, "919811100095", media_kind="audio", media_sample="voice_request.mp3")
    audio = [m for m in outs(chat) if m["kind"] == "audio"]
    assert len(audio) == 1 and audio[0]["audio"].startswith("/api/media/")
    r = fresh.get(audio[0]["audio"])
    assert r.status_code == 200 and r.content == b"ID3-fake-mp3"
    # typed messages from someone who never asked for voice stay text-only
    chat = say(fresh, "919811100094", "B+ blood chahiye Safdarjung hospital 1 unit")
    assert not [m for m in outs(chat) if m["kind"] == "audio"]


def test_voice_on_for_donors(fresh, monkeypatch):
    monkeypatch.setattr(tts, "synthesize", lambda text, lang="en": (b"RIFF-fake", "audio/wav", "fake"))
    with SessionLocal() as db:
        phone = db.query(Donor).first().phone
    say(fresh, phone, "VOICE ON")
    chat = say(fresh, phone, "is it ok to donate after drinking alcohol?")
    assert [m for m in outs(chat) if m["kind"] == "audio"]
    with SessionLocal() as db:
        assert db.query(Donor).filter_by(phone=phone).one().voice_replies
        assert db.query(MediaFile).count() >= 2


def test_tts_text_cleanup_and_off():
    assert tts.speakable("Live page: http://x.test/r/abc\n- one\n- two") == "Live page:. one. two"
    assert tts.synthesize("hello") is None  # TTS_PROVIDER=off in tests


# ---------------------------------------------------------------- assisted camp registration (MOCK portal)
def _camp_and_donor():
    with SessionLocal() as db:
        d = db.query(Donor).filter(Donor.lat.is_not(None)).first()
        camp = Camp(camp_date=date.today() + timedelta(days=4), title="Camp at Test College (sample)", address="Test College", district="South",
                    state="Delhi", lat=d.lat, lng=d.lng, source="sample")
        db.add(camp)
        db.commit()
        return camp.id, d.phone, d.id


def test_camp_registration_on_whatsapp(fresh):
    c = fresh
    camp_id, phone, donor_id = _camp_and_donor()
    chat = say(c, phone, button=f"cr:{camp_id}")
    assert f"crok:{camp_id}" in options(chat)
    chat = say(c, phone, button=f"crok:{camp_id}")
    assert "Aadhaar" in chat["messages"][-1]["body"] or "आधार" in chat["messages"][-1]["body"]
    bad = say(c, phone, "1234")["messages"][-1]["body"]
    assert "12-digit" in bad or "12 अंकों" in bad  # invalid -> asked again
    chat = say(c, phone, "3456 7890 1234")
    sms = [m for m in chat["messages"] if m["kind"] == "sms"]
    assert sms and "OTP" in sms[-1]["body"]
    otp = sms[-1]["body"].split(":")[1].split()[0]
    chat = say(c, phone, "000000")  # wrong first
    chat = say(c, phone, otp)
    assert "MOCK-" in chat["messages"][-1]["body"]
    with SessionLocal() as db:
        reg = db.query(CampRegistration).filter_by(donor_id=donor_id).one()
        assert reg.status == "registered" and reg.portal_ref.startswith("MOCK-") and any("captcha" in s for s in reg.steps)
        logged = " ".join(m.body for m in db.query(ChatMessage).filter_by(phone=phone).all()) + json.dumps([r.steps for r in db.query(CampRegistration).all()])
        assert "345678901234" not in logged.replace(" ", "") and "XXXX XXXX 1234" in logged  # Aadhaar never kept in clear


def test_camp_registration_on_web(fresh):
    camp_id, _, _ = _camp_and_donor()
    body = {"name": "Test Donor (synthetic)", "phone": "9876500123", "dob": "1998-05-04", "gender": "F", "blood_group": "O+",
            "aadhaar": "234567890123", "consent": True}
    r = fresh.post(f"/api/camps/{camp_id}/register", json=body).json()
    assert r["status"] == "otp_sent" and "OTP" in r["demo_sms"]
    otp = r["demo_sms"].split(":")[1].split()[0]
    done = fresh.post(f"/api/camps/registrations/{r['id']}/otp", json={"otp": otp}).json()
    assert done["status"] == "registered" and done["ref"].startswith("MOCK-")
    assert fresh.post(f"/api/camps/{camp_id}/register", json={**body, "consent": False}).status_code == 422


def test_mock_portal_rejects_bad_input(fresh):
    camp_id, _, _ = _camp_and_donor()
    page = fresh.get(f"/mock-portal/camps/{camp_id}/register").text
    assert "MOCK PORTAL" in page and "captcha-q" in page
    session = page.split('name="session" value="')[1].split('"')[0]
    bad = fresh.post(f"/mock-portal/camps/{camp_id}/register", data={"session": session, "name": "X Y", "mobile": "9876500123", "dob": "1998-01-01",
                                                                       "gender": "M", "blood_group": "O+", "aadhaar": "12345", "captcha": "999"}).text
    assert "Wrong captcha" in bad and "12 digits" in bad


def test_voice_parse_endpoint(fresh):
    r = fresh.post("/api/voice/parse", params={"sample": "voice_request_hi.mp3"}).json()
    assert r["fields"]["patient_group"] == "B+" and r["fields"]["units"] == 2 and "Safdarjung" in r["fields"]["hospital"]
    e = fresh.post("/api/extract", json={"text": "Papa ko A negative chahiye RML hospital 2 unit"}).json()
    assert e["fields"]["patient_group"] == "A-" and e["fields"]["units"] == 2


# ---------------------------------------------------------------- rota confirmation runs the health pre-screen
def _reminded_slot(c):
    from app.models import RecurringSlot
    c.post("/api/admin/tick", headers=ADMIN)
    with SessionLocal() as db:
        s = db.query(RecurringSlot).filter_by(status="reminded").first()
        return s.id, s.donor.phone


def test_rota_confirm_asks_health_questions(fresh):
    from app.models import RecurringSlot
    sid, phone = _reminded_slot(fresh)
    chat = say(fresh, phone, button=f"rc:{sid}:y")
    tapped = [m for m in chat["messages"] if m["direction"] == "in"][-1]["body"]
    assert "rc:" not in tapped and tapped in ("Yes, I'll come", "हाँ, आऊँगा")  # the button title, not its id
    assert any(o.startswith(f"rs:{sid}:alcohol_24h:") for o in options(chat))
    chat = say(fresh, phone, button=f"rs:{sid}:alcohol_24h:y")
    assert "alcohol" in chat["messages"][-1]["body"] or "शराब" in " ".join(m["body"] for m in outs(chat)[-3:])
    with SessionLocal() as db:
        assert db.get(RecurringSlot, sid).status == "declined"


def test_rota_confirm_after_all_no(fresh):
    from app.core import eligibility
    from app.models import RecurringSlot
    sid, phone = _reminded_slot(fresh)
    say(fresh, phone, button=f"rc:{sid}:y")
    for q in eligibility.questions():
        chat = say(fresh, phone, button=f"rs:{sid}:{q['id']}:n")
    with SessionLocal() as db:
        assert db.get(RecurringSlot, sid).status == "confirmed"
    assert len(eligibility.questions()) == 5 and "medication_now" in {q["id"] for q in eligibility.questions()}
