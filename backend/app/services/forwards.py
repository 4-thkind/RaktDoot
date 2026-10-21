"""Forward Checker (F2): is a forwarded blood plea fresh, real and not already handled?

Pipeline: shared extraction -> signals -> verdict -> action.
Signals: age of the date in the text, how often we have seen this text / phone (hashes only),
match against Rakt Doot requests, hospital verification (W5), TinyFish Search on the phone number
(V3), TinyFish Fetch on any link inside, and scam patterns (money, UPI, "transport charges").
Verdicts: likely_stale | likely_fulfilled | unverified | looks_genuine | possible_scam."""
import asyncio
import concurrent.futures
import hashlib
import re
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.compatibility import compatible_donors, normalize_component
from ..db import utcnow
from ..models import BloodBank, Forward, Request
from . import directory, extraction, geocode, tinyfish_client

VERDICTS = ["likely_stale", "likely_fulfilled", "unverified", "looks_genuine", "possible_scam"]
STALE_DAYS = 3

REASONS = {
    "money": {"en": "It asks for money (UPI, fees or 'transport charges'). Blood is never sold.",
              "hi": "इसमें पैसे मांगे गए हैं (UPI, फ़ीस या 'ट्रांसपोर्ट चार्ज')। खून कभी बेचा नहीं जाता।"},
    "date_old": {"en": "The date in it is {days} days old.", "hi": "इसमें लिखी तारीख {days} दिन पुरानी है।"},
    "date_fresh": {"en": "The date in it is recent.", "hi": "इसमें लिखी तारीख हाल की है।"},
    "seen": {"en": "We have seen this same message {n} times before.", "hi": "यही संदेश हम पहले {n} बार देख चुके हैं।"},
    "phone_seen": {"en": "This phone number was in {n} earlier forwards.", "hi": "यह फ़ोन नंबर पहले {n} फ़ॉरवर्ड में था।"},
    "web_old": {"en": "The number appears in {n} older posts online.", "hi": "यह नंबर ऑनलाइन {n} पुरानी पोस्ट में है।"},
    "closed_request": {"en": "A matching Rakt Doot request is already closed ({status}).", "hi": "रक्त दूत पर मिलता-जुलता अनुरोध पहले ही बंद है ({status})।"},
    "open_request": {"en": "A matching request is open on Rakt Doot: {link}", "hi": "रक्त दूत पर मिलता-जुलता अनुरोध खुला है: {link}"},
    "link_closed": {"en": "The link inside says the need is closed.", "hi": "इसके लिंक में लिखा है कि ज़रूरत पूरी हो गई।"},
    "hospital_ok": {"en": "The hospital checks out ({source}).", "hi": "अस्पताल सही पाया गया ({source})।"},
    "hospital_unknown": {"en": "We could not verify the hospital.", "hi": "अस्पताल की पुष्टि नहीं हो सकी।"},
    "no_group": {"en": "No blood group is mentioned.", "hi": "कोई ब्लड ग्रुप नहीं लिखा है।"},
    "no_contact": {"en": "There is no number to call.", "hi": "कॉल करने के लिए कोई नंबर नहीं है।"},
}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ]+", " ", (text or "").lower()).strip()


def _run(coro):
    """Run a coroutine from sync code whether or not an event loop is running in this thread."""
    with concurrent.futures.ThreadPoolExecutor(1) as ex:
        return ex.submit(asyncio.run, coro).result(timeout=40)


def reason_text(key: str, lang: str, **kw) -> str:
    entry = REASONS[key]
    return entry.get(lang, entry["en"]).format(**kw)


def locate_hospital(db: Session, name: str | None, city: str | None) -> dict | None:
    if not name:
        return None
    banks = db.scalars(select(BloodBank)).all()
    best, score = directory.best_match({"name": name, "address": city or ""}, banks)
    if best is not None:
        return {"name": name, "lat": best.lat, "lng": best.lng, "address": best.address, "via": "directory"}
    hits = geocode.search(f"{name} {city or ''}".strip(), limit=1)
    if hits:
        return {"name": name, "lat": hits[0]["lat"], "lng": hits[0]["lng"], "address": hits[0]["address"], "via": "openstreetmap"}
    return None


def _matching_request(db: Session, fields: dict) -> Request | None:
    since = utcnow() - timedelta(days=14)
    conds = []
    if fields.get("phone"):
        conds.append(Request.requester_phone == fields["phone"])
    rows = db.scalars(select(Request).where(Request.created_at > since, or_(*conds) if conds else Request.patient_group == fields.get("patient_group"))).all()
    for r in rows:
        if fields.get("phone") and r.requester_phone == fields["phone"]:
            return r
        if fields.get("hospital") and r.patient_group == fields.get("patient_group") and \
                directory.similarity({"name": fields["hospital"]}, {"name": r.hospital_name, "phone": None, "address": None}) >= 0.6:
            return r
    return None


def _web_signals(fields: dict, urls: list[str]) -> dict:
    out = {"phone_web_hits": None, "link_closed": False, "hospital": None}

    async def go():
        tasks = [tinyfish_client.verify_hospital(fields.get("hospital") or "", fields.get("city") or "")] if fields.get("hospital") else []
        if fields.get("phone"):
            tasks.append(tinyfish_client.search(f'"{fields["phone"][-10:]}" blood', "forward_phone"))
        if urls:
            tasks.append(tinyfish_client.fetch(urls[:3], "forward_link"))
        return await asyncio.gather(*tasks, return_exceptions=True)

    res = _run(go())
    i = 0
    if fields.get("hospital"):
        out["hospital"] = res[i] if isinstance(res[i], dict) else None
        i += 1
    if fields.get("phone"):
        hits = res[i] if isinstance(res[i], list) else None
        out["phone_web_hits"] = len(hits) if hits is not None else None
        i += 1
    if urls and isinstance(res[i], dict):
        out["link_closed"] = any(re.search(r"\b(fulfilled|closed|arranged|no longer needed|got blood)\b", t, re.I) for t in res[i].values())
    return out


def check(db: Session, text: str, reporter_phone: str = "", today: date | None = None) -> dict:
    today = today or date.today()
    fields = extraction.extract(text, today)
    if not fields.get("phone") and reporter_phone.isdigit():
        fields["phone"] = reporter_phone  # first-person request on WhatsApp: the sender is the contact
    th = _hash(normalize_text(text))
    ph = _hash(fields["phone"]) if fields.get("phone") else None
    seen = db.scalar(select(func.count()).select_from(Forward).where(Forward.text_hash == th)) or 0
    phone_seen = db.scalar(select(func.count()).select_from(Forward).where(Forward.phone_hash == ph, Forward.text_hash != th)) if ph else 0
    urls = re.findall(r"https?://\S+", text)
    share = next((m.group(1) for u in urls for m in [re.search(r"/r/([\w-]{6,16})", u)] if m), None)
    match = db.scalar(select(Request).where(Request.share_slug == share)) if share else _matching_request(db, fields)
    web = _web_signals(fields, [u for u in urls if "/r/" not in u])

    reasons: list[tuple[str, dict]] = []
    age = None
    if fields.get("date"):
        age = (today - date.fromisoformat(fields["date"])).days
    if fields.get("money_ask"):
        verdict = "possible_scam"
        reasons.append(("money", {}))
    elif match is not None and match.status in ("fulfilled", "expired", "cancelled") or web["link_closed"]:
        verdict = "likely_fulfilled"
        reasons.append(("closed_request", {"status": match.status}) if match is not None and match.status in ("fulfilled", "expired", "cancelled") else ("link_closed", {}))
    elif (age is not None and age > STALE_DAYS) or seen >= 3 or (web["phone_web_hits"] or 0) >= 5:
        verdict = "likely_stale"
        if age is not None and age > STALE_DAYS:
            reasons.append(("date_old", {"days": age}))
        if seen >= 3:
            reasons.append(("seen", {"n": seen}))
        if (web["phone_web_hits"] or 0) >= 5:
            reasons.append(("web_old", {"n": web["phone_web_hits"]}))
    else:
        hosp = web["hospital"]
        ok = bool(hosp and hosp.get("verified"))
        if not fields.get("patient_group"):
            reasons.append(("no_group", {}))
        if ok:
            reasons.append(("hospital_ok", {"source": (hosp["evidence"][0]["source"] if hosp.get("evidence") else "check")}))
        else:
            reasons.append(("hospital_unknown", {}))
        if age is not None:
            reasons.append(("date_fresh", {}))
        if not fields.get("phone"):
            reasons.append(("no_contact", {}))
        verdict = "looks_genuine" if ok and fields.get("patient_group") and fields.get("phone") else "unverified"
    if match is not None and match.status not in ("fulfilled", "expired", "cancelled"):
        reasons.append(("open_request", {"link": f"{settings.public_base_url.rstrip('/')}/r/{match.share_slug}"}))
    if phone_seen and verdict != "possible_scam":
        reasons.append(("phone_seen", {"n": phone_seen}))

    place = locate_hospital(db, fields.get("hospital"), fields.get("city")) if verdict == "looks_genuine" else None
    n_donors = _donors_near(db, fields, place) if place else 0
    masked = {**{k: v for k, v in fields.items() if k != "phone"}, "phone": ("+91 ••••• " + fields["phone"][-5:]) if fields.get("phone") else None}
    fw = Forward(text_hash=th, phone_hash=ph, reporter_hash=_hash(reporter_phone or "web"), verdict=verdict,
                 fields={**masked, "place": place}, reasons=[k for k, _ in reasons],
                 request_id=match.id if match is not None else None)
    db.add(fw)
    db.flush()
    return {
        "id": fw.id, "verdict": verdict, "fields": masked, "engine": fields.get("engine"),
        "reasons": [{"key": k, "en": reason_text(k, "en", **kw), "hi": reason_text(k, "hi", **kw)} for k, kw in reasons[:4]],
        "offer": {"hospital": fields.get("hospital"), "donors": n_donors} if place and n_donors else None,
        "signals": {"date_age_days": age, "seen_before": seen, "phone_seen": phone_seen, "phone_web_hits": web["phone_web_hits"],
                    "hospital_check": web["hospital"], "matched_request": match.status if match is not None else None},
    }


def _donors_near(db: Session, fields: dict, place: dict) -> int:
    from . import dispatch

    if not fields.get("patient_group"):
        return 0
    probe = Request(patient_group=fields["patient_group"], component=normalize_component(fields.get("component")),
                    hospital_lat=place["lat"], hospital_lng=place["lng"], requester_phone="", allow_o_neg=False, units=1)
    return len(dispatch.find_candidates(db, probe, 10))


def create_request(db: Session, forward_id: str, reporter_phone: str, reporter_name: str, lang: str = "en") -> Request:
    """Turn a checked plea into a request, with the reporter as the family's contact (consent asked first)."""
    from . import dispatch

    fw = db.get(Forward, forward_id)
    if fw is None or fw.verdict != "looks_genuine":
        raise ValueError("only a plea that looks genuine can be turned into a request")
    if fw.request_id:
        r = db.get(Request, fw.request_id)
        if r is not None:
            return r
    f, place = fw.fields, fw.fields.get("place")
    if not place or not f.get("patient_group"):
        raise ValueError("hospital location or blood group missing")
    r = Request(patient_group=f["patient_group"], group_confirmed=True, units=f.get("units") or 1, patient_age=0, patient_gender="O",
                hospital_name=f.get("hospital") or place["name"], hospital_address=place.get("address"), hospital_lat=place["lat"],
                hospital_lng=place["lng"], requester_name=reporter_name[:80] or "Forwarded request", requester_phone=reporter_phone,
                language=lang, component=normalize_component(f.get("component")), kind="emergency",
                target_acceptances=min((f.get("units") or 1) * 2, 12), expires_at=utcnow() + timedelta(hours=settings.request_ttl_hours))
    db.add(r)
    db.flush()
    fw.request_id = r.id
    dispatch.start_dispatch(db, r)
    return r


def compatible_line(fields: dict) -> str:
    g = fields.get("patient_group")
    return ", ".join(compatible_donors(g, normalize_component(fields.get("component")))) if g else ""
