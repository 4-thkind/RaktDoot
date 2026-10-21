"""Camp placement (F10): where should an NGO or college hold its next blood donation camp?

Weighted coverage over candidate sites (seeded venues, plus KMeans 'demand areas' when
scikit-learn is installed; USE_INTEL_SKLEARN=true runs it through Intel Extension for
Scikit-learn, see F14). For each site:
  donor pool      consenting donors within 5 km (people who can actually turn up)
  shortage        Shortage Radar risk for districts with a blood centre within 8 km (F1)
  unmet need      requests nearby in the last 60 days that never reached their target
  overlap         an upcoming camp within 3 km, or a blood centre within 1 km (collection already easy)
score = 0.4 donors + 0.35 shortage + 0.25 unmet (each scaled 0..1) - 0.3 overlap; picked greedily,
with sites within 4 km of an already-picked site penalised so the top-k spread out."""
import csv
import io
import time
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.geo import haversine_km
from ..db import utcnow
from ..models import BloodBank, Camp, Donor, Notification, Request

# Real venues, APPROXIMATE coordinates (good to ~1 km), for illustration.
VENUES = [
    ("Guru Gobind Singh Indraprastha University, Dwarka", 28.5946, 77.0187, "college"),
    ("IIT Delhi, Hauz Khas", 28.5450, 77.1926, "college"), ("Jamia Millia Islamia", 28.5617, 77.2803, "college"),
    ("JNU", 28.5402, 77.1662, "college"), ("Delhi University North Campus", 28.6889, 77.2100, "college"),
    ("Delhi Technological University, Rohini", 28.7499, 77.1170, "college"), ("NSUT, Dwarka", 28.6096, 77.0386, "college"),
    ("IIIT Delhi, Okhla", 28.5459, 77.2732, "college"), ("Amity University, Noida", 28.5444, 77.3330, "college"),
    ("JIIT, Sector 62 Noida", 28.6302, 77.3727, "college"), ("ABES Engineering College, Ghaziabad", 28.6337, 77.4466, "college"),
    ("KIET Group of Institutions, Ghaziabad", 28.7524, 77.4974, "college"), ("Manav Rachna University, Faridabad", 28.4497, 77.2860, "college"),
    ("Siri Fort Auditorium", 28.5502, 77.2190, "community"), ("Dilli Haat, INA", 28.5733, 77.2079, "community"),
    ("Talkatora Stadium", 28.6280, 77.1980, "community"), ("Noida Stadium, Sector 21A", 28.5798, 77.3485, "community"),
    ("Leisure Valley Park, Gurugram", 28.4720, 77.0700, "community"), ("Cyber Hub, Gurugram", 28.4950, 77.0890, "community"),
    ("Rajouri Garden Community Centre", 28.6450, 77.1210, "community"), ("Laxmi Nagar District Centre", 28.6310, 77.2770, "community"),
    ("Rohini Sector 10 Community Centre", 28.7160, 77.1150, "community"), ("Janakpuri District Centre", 28.6290, 77.0810, "community"),
    ("Nehru Place", 28.5490, 77.2510, "community"),
]
DONOR_KM, SHORT_KM, UNMET_KM, CAMP_KM, BANK_KM, SPREAD_KM = 5, 8, 8, 3, 1, 4


def kmeans_sites(points: list[tuple[float, float]], k: int = 6) -> tuple[list[tuple[float, float]], dict]:
    """Demand-area centroids. Returns (centroids, {"engine", "ms"}); ([], ...) if scikit-learn is absent."""
    try:
        if settings.use_intel_sklearn:
            from sklearnex.cluster import KMeans  # Intel oneDAL-accelerated drop-in
        else:
            from sklearn.cluster import KMeans
    except ImportError:
        return [], {"engine": "none", "ms": 0}
    if len(points) < k:
        return [], {"engine": "too few points", "ms": 0}
    t = time.perf_counter()
    km = KMeans(n_clusters=k, n_init=5, random_state=0).fit(points)
    engine = "sklearnex" if settings.use_intel_sklearn else "sklearn"
    return [tuple(c) for c in km.cluster_centers_], {"engine": engine, "ms": round((time.perf_counter() - t) * 1000, 1)}


def score_sites(sites: list[dict], donors: list[tuple[float, float]], risk_by_bank: list[tuple[float, float, float, str]],
                unmet: list[tuple[float, float]], camps: list[tuple[float, float, date]], banks: list[tuple[float, float]]) -> list[dict]:
    """Pure scoring (unit-tested). risk_by_bank = (lat, lng, risk, label)."""
    raw = []
    for s in sites:
        lat, lng = s["lat"], s["lng"]
        pool = sum(1 for a, b in donors if haversine_km(lat, lng, a, b) <= DONOR_KM)
        near_risk = {}
        for a, b, r, label in risk_by_bank:
            if haversine_km(lat, lng, a, b) <= SHORT_KM:
                near_risk[label] = max(near_risk.get(label, 0), r)
        shortage = sum(near_risk.values())
        un = sum(1 for a, b in unmet if haversine_km(lat, lng, a, b) <= UNMET_KM)
        camp_d = min((haversine_km(lat, lng, a, b) for a, b, _ in camps), default=None)
        bank_d = min((haversine_km(lat, lng, a, b) for a, b in banks), default=None)
        overlap = (camp_d is not None and camp_d <= CAMP_KM) or (bank_d is not None and bank_d <= BANK_KM)
        raw.append({**s, "donor_pool": pool, "shortage": round(shortage, 2), "at_risk": sorted(near_risk, key=lambda k: -near_risk[k])[:3],
                    "unmet": un, "nearest_camp_km": round(camp_d, 1) if camp_d is not None else None,
                    "nearest_bank_km": round(bank_d, 1) if bank_d is not None else None, "overlap": overlap})
    mx = {k: max([r[k] for r in raw] + [1e-9]) for k in ("donor_pool", "shortage", "unmet")}
    for r in raw:
        r["score"] = round(0.4 * r["donor_pool"] / mx["donor_pool"] + 0.35 * r["shortage"] / mx["shortage"]
                           + 0.25 * r["unmet"] / mx["unmet"] - (0.3 if r["overlap"] else 0), 3)
    return raw


def pick(scored: list[dict], k: int) -> list[dict]:
    chosen = []
    pool = sorted(scored, key=lambda r: -r["score"])
    while pool and len(chosen) < k:
        best = max(pool, key=lambda r: r["score"] - 0.25 * sum(1 for c in chosen if haversine_km(r["lat"], r["lng"], c["lat"], c["lng"]) < SPREAD_KM))
        chosen.append(best)
        pool.remove(best)
    for r in chosen:
        bits = [f"covers ~{r['donor_pool']} registered donors within {DONOR_KM} km"]
        if r["at_risk"]:
            bits.append("shortage risk: " + ", ".join(r["at_risk"]))
        if r["unmet"]:
            bits.append(f"{r['unmet']} recent request(s) nearby fell short")
        bits.append(f"nearest upcoming camp {r['nearest_camp_km']} km" if r["nearest_camp_km"] is not None else "no upcoming camp nearby")
        r["reason"] = "; ".join(bits)
    return chosen


def recommend(db: Session, k: int = 5, component: str = "prbc") -> dict:
    from . import forecast

    donors = [(d.lat, d.lng) for d in db.scalars(select(Donor).where(Donor.consent.is_(True), Donor.opted_out.is_(False), Donor.lat.is_not(None))).all()]
    banks = db.scalars(select(BloodBank)).all()
    radar = forecast.radar(db, component)
    by_district: dict[str, list[tuple[str, float]]] = {}
    for c in radar["at_risk"]:
        by_district.setdefault(c["district"], []).append((c["group"], c["risk"]))
    risk_by_bank = [(b.lat, b.lng, r, f"{g} in {b.district}") for b in banks for g, r in by_district.get(b.district, [])]
    since = utcnow() - timedelta(days=60)
    unmet = []
    for r in db.scalars(select(Request).where(Request.created_at > since, Request.status.in_(("needs_public_share", "expired")))).all():
        got = db.scalar(select(Notification.id).where(Notification.request_id == r.id, Notification.status.in_(("connected", "donated"))).limit(1))
        if not got:
            unmet.append((r.hospital_lat, r.hospital_lng))
    camps = [(c.lat, c.lng, c.camp_date) for c in db.scalars(select(Camp).where(Camp.camp_date >= date.today(), Camp.lat.is_not(None))).all()]
    sites = [{"name": n, "lat": la, "lng": lo, "type": t, "approximate": True} for n, la, lo, t in VENUES]
    # shortcut: clusters unweighted donor locations; weight by local deficit once real history accumulates
    cents, km_meta = kmeans_sites(donors, k=6)
    sites += [{"name": f"Demand area {i + 1} (KMeans centroid)", "lat": round(a, 4), "lng": round(b, 4), "type": "area", "approximate": True}
              for i, (a, b) in enumerate(cents)]
    scored = score_sites(sites, donors, risk_by_bank, unmet, camps, [(b.lat, b.lng) for b in banks])
    return {"component": component, "synthetic_inputs": radar["synthetic"], "kmeans": km_meta,
            "sites": pick(scored, k), "candidates": len(sites)}


def to_csv(rec: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "name", "type", "lat", "lng", "score", "donor_pool", "at_risk", "unmet", "nearest_camp_km", "reason"])
    for i, s in enumerate(rec["sites"], 1):
        w.writerow([i, s["name"], s["type"], s["lat"], s["lng"], s["score"], s["donor_pool"], "; ".join(s["at_risk"]), s["unmet"],
                    s["nearest_camp_km"], s["reason"]])
    return buf.getvalue()
