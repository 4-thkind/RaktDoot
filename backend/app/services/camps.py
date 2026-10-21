"""Camp finder (A1): upcoming blood donation camps from eRaktKosh's public Camp Schedule, read with
TinyFish Fetch. Used in the 'eligible again' message, the deferred-donor message, the dispatcher's
suggest_camp action and camp placement (F10).

A2 (assisted registration) is deliberately NOT automated: eRaktKosh's camp sign-up form
(portalDonorRegistrationNew.cnt) requires a captcha, a mobile OTP and Aadhaar details, checked
2026-10-20. Automating that on someone's behalf is neither possible nor appropriate, so we link
the donor to the official form instead.

Without a key, labelled SAMPLE camps are generated near real blood centres so the flows can be shown."""
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.geo import haversine_km
from ..models import BloodBank, Camp
from . import directory, eraktkosh, geocode

NCR_DISTRICTS = {"gurgaon", "gurugram", "faridabad", "gautam buddha nagar", "ghaziabad"}
STATES = ["Delhi", "Haryana", "Uttar Pradesh"]


def _in_scope(c: dict) -> bool:
    return c["state"] == "Delhi" or c["district"].strip().lower() in NCR_DISTRICTS


async def refresh(db: Session, days: int = 10) -> dict:
    """Live: TinyFish Fetch of the camp schedule for each state and day (10 URLs per call)."""
    from . import tinyfish_client

    if not settings.tinyfish_live:
        return {"mode": "demo", "sample_camps": seed_sample(db)}
    today = date.today()
    urls = [eraktkosh.camps_url(eraktkosh.state_code(s), today + timedelta(days=d)) for s in STATES for d in range(days)]
    found = []
    for i in range(0, len(urls), 10):
        pages = await tinyfish_client.fetch(urls[i:i + 10], "camp_schedule", fmt="html")
        for u, text in pages.items():
            try:
                payload = directory._parse_json_text(text)
            except ValueError:
                continue
            state = next((s for s in STATES if f"stateCode={eraktkosh.state_code(s)}&" in u), "")
            found += [c for c in eraktkosh.parse_camp_rows(payload, state) if _in_scope(c)]
    return {"mode": "live", **upsert(db, found)}


def upsert(db: Session, camps: list[dict]) -> dict:
    added = 0
    for c in camps:
        if c.get("external_id") and db.scalar(select(Camp).where(Camp.external_id == c["external_id"])):
            continue
        hits = geocode.search(f"{c['address']}, {c['district']}", limit=1) if c.get("address") else []
        db.add(Camp(**{k: c[k] for k in ("camp_date", "title", "address", "state", "district", "organiser", "register_url",
                                          "external_id", "time_text")},
                    lat=hits[0]["lat"] if hits else None, lng=hits[0]["lng"] if hits else None, source="eraktkosh"))
        added += 1
    return {"camps": len(camps), "added": added}


def seed_sample(db: Session, n: int = 14, seed: int = 11) -> int:
    """Labelled sample camps hosted by real directory blood centres over the next 3 weeks."""
    if db.scalar(select(Camp).where(Camp.source == "sample").limit(1)):
        return 0
    rng = random.Random(seed)
    banks = db.scalars(select(BloodBank)).all()
    venues = ["Community Centre", "College Campus", "RWA Park", "Gurudwara Hall", "Metro Station Plaza", "Corporate Park"]
    today = date.today()
    for i in range(min(n, len(banks))):
        b = rng.choice(banks)
        db.add(Camp(camp_date=today + timedelta(days=rng.randint(1, 21)), time_text="10:00-15:00",
                    title=f"Blood donation camp (SAMPLE) at {rng.choice(venues)}", address=f"Near {b.address or b.district}",
                    district=b.district, state=b.state, organiser=b.name, register_url=None,
                    lat=b.lat + rng.uniform(-0.02, 0.02), lng=b.lng + rng.uniform(-0.02, 0.02), source="sample"))
    return min(n, len(banks))


def nearest(db: Session, lat: float, lng: float, after: date | None = None, within_km: float = 15) -> Camp | None:
    after = after or date.today()
    rows = db.scalars(select(Camp).where(Camp.camp_date >= after, Camp.lat.is_not(None)).order_by(Camp.camp_date)).all()
    near = [c for c in rows if haversine_km(lat, lng, c.lat, c.lng) <= within_km]
    return near[0] if near else None


def as_json(c: Camp, lat: float | None = None, lng: float | None = None) -> dict:
    return {"id": c.id, "date": c.camp_date.isoformat(), "time": c.time_text, "title": c.title, "address": c.address,
            "district": c.district, "organiser": c.organiser, "register_url": c.register_url, "lat": c.lat, "lng": c.lng,
            "source": c.source, "sample": c.source == "sample",
            "distance_km": round(haversine_km(lat, lng, c.lat, c.lng), 1) if lat is not None and c.lat is not None else None}

