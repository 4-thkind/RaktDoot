"""Blood-bank directory (W2 / V1): real eRaktKosh directory rows with geocoded addresses, and a
better matcher from eRaktKosh stock rows to directory entries (name + phone + address).

Live refresh reads eRaktKosh's public directory through TinyFish Fetch. The shipped snapshot
(data/eraktkosh_directory.json) was built by scripts/build_directory.py, so a fresh clone has real
blood centres with no keys. Banks we fail to match are counted in UNMATCHED and shown on /admin."""
import json
import logging
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

import httpx

from ..config import BACKEND_DIR, settings
from . import eraktkosh

log = logging.getLogger("raktdoot.directory")
DATA = BACKEND_DIR / "data"
SNAPSHOT = DATA / "eraktkosh_directory.json"
GEOCACHE = DATA / "geocode_cache.json"
NCR_SCOPE = [("Delhi", None), ("Haryana", ["Gurugram", "Faridabad"]), ("Uttar Pradesh", ["Gautam Buddha Nagar", "Ghaziabad"])]
UNMATCHED: dict[str, dict] = {}  # name -> {"count", "district"}; shortcut: in-memory, resets on restart
MATCH_MIN = 0.6

_STOP = {"blood", "bank", "centre", "center", "hospital", "the", "of", "and", "govt", "government", "ltd", "pvt", "delhi",
         "new", "a", "unit", "in", "at", "dr", "super", "speciality", "specialty", "multi", "institute", "medical", "rbtc"}


def _norm_name(name: str) -> str:
    s = re.sub(r"\(.*?\)", " ", (name or "").lower())
    return " ".join(t for t in re.findall(r"[a-z]+", s) if t not in _STOP and len(t) > 1)


def _tokens(s: str) -> set[str]:
    return {t for t in _norm_name(s).split() if len(t) > 2}


def _digits(phone: str | None) -> set[str]:
    """Last 8 digits of every number in a phone cell (cells often hold several numbers)."""
    return {d[-8:] for d in re.findall(r"\d{6,}", (phone or "").replace(" ", "")) if len(d) >= 6}


def similarity(a: dict, b) -> float:
    """0..1+ similarity between an eRaktKosh row `a` and a directory entry `b` (BloodBank or dict)."""
    get = (lambda o, k: o.get(k)) if isinstance(b, dict) else (lambda o, k: getattr(o, k, None))
    na, nb = _norm_name(a.get("name", "")), _norm_name(get(b, "name") or "")
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    overlap = len(ta & tb) / max(1, min(len(ta), len(tb)))
    score = max(SequenceMatcher(None, na, nb).ratio(), overlap)
    if _digits(a.get("phone")) & _digits(get(b, "phone")):
        score += 0.35
    aa, ab = _tokens(a.get("address") or ""), _tokens(get(b, "address") or "")
    if aa and ab:
        score += 0.15 * len(aa & ab) / min(len(aa), len(ab))
    return score


def best_match(bank: dict, directory: list) -> tuple[object | None, float]:
    best, best_score = None, 0.0
    for d in directory:
        s = similarity(bank, d)
        if s > best_score:
            best, best_score = d, s
    if best_score < MATCH_MIN:
        entry = UNMATCHED.setdefault(bank.get("name", "?")[:120], {"count": 0, "address": (bank.get("address") or "")[:120]})
        entry["count"] += 1
        return None, best_score
    return best, best_score


# ---------------------------------------------------------------- download + geocode
def _parse_json_text(text: str) -> dict:
    start = (text or "").find("{")
    if start < 0:
        raise ValueError("no JSON in response")
    return json.loads(text[start: text.rfind("}") + 1])


def _get_via_tinyfish(urls: list[str]) -> dict[str, dict]:
    from . import tinyfish_client
    res = tinyfish_client.fetch_sync(urls, purpose="directory")
    return {u: _parse_json_text(t) for u, t in res.items() if t}


def _get_direct(urls: list[str]) -> dict[str, dict]:
    out = {}
    for u in urls:
        r = httpx.get(u, headers={"User-Agent": "Mozilla/5.0 (RaktDoot directory builder)", "X-Requested-With": "XMLHttpRequest"}, timeout=40)
        r.raise_for_status()
        try:
            text = r.content.decode("utf-8")
        except UnicodeDecodeError:  # some rows are cp1252 (e.g. en dashes)
            text = r.content.decode("cp1252", errors="replace")
        out[u] = _parse_json_text(text)
    return out


def download(scope=NCR_SCOPE) -> tuple[list[dict], str]:
    urls = {eraktkosh.directory_url(eraktkosh.state_code(st)): (st, districts) for st, districts in scope}
    via = "tinyfish_fetch" if settings.tinyfish_live else "direct_https"
    payloads = _get_via_tinyfish(list(urls)) if via == "tinyfish_fetch" else _get_direct(list(urls))
    rows = []
    for url, (state, districts) in urls.items():
        for r in eraktkosh.parse_directory_rows(payloads.get(url) or {}):
            if districts and not any(eraktkosh._norm(d) == eraktkosh._norm(r["district"]) for d in districts):
                continue
            rows.append({**r, "state": state})
    return rows, via


def _load_cache() -> dict:
    try:
        return json.loads(GEOCACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def clean_name(name: str) -> str:
    """'Blood Bank, Fortis Flt.Lt. Rajan Dhall Hospital (A Unit Of ...)' -> 'Fortis Flt.Lt. Rajan Dhall Hospital'."""
    s = re.sub(r"\(.*?(\)|$)", "", name or "")
    s = re.sub(r"^\s*(blood\s*(bank|cent(re|er))\s*(of|,|-)?\s*)", "", s, flags=re.I)
    s = re.sub(r",?\s*blood\s*(bank|cent(re|er))\s*$", "", s, flags=re.I)
    return s.strip(" ,-") or name


CITY_CENTRE = {"Delhi": (28.6139, 77.2090), "Gurugram": (28.4595, 77.0266), "Faridabad": (28.4089, 77.3178),
               "Noida": (28.5355, 77.3910), "Ghaziabad": (28.6692, 77.4538)}
MAX_FROM_CITY_KM = 40  # Nominatim sometimes returns a same-named place in another city; reject those


def _plausible(r: dict, hit) -> bool:
    from ..core.geo import haversine_km
    c = CITY_CENTRE[_city(r)]
    return bool(hit) and haversine_km(c[0], c[1], hit[0], hit[1]) <= MAX_FROM_CITY_KM


def _city(r: dict) -> str:
    d = (r.get("district") or "").lower()
    return {"gurgaon": "Gurugram", "gurugram": "Gurugram", "faridabad": "Faridabad", "gautam buddha nagar": "Noida",
            "ghaziabad": "Ghaziabad"}.get(d, "Delhi")


def _localities(address: str) -> list[str]:
    """Wordy address parts, most specific last-but-city first: 'Vasant Kunj', 'Sector 62'."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    keep = [p for p in parts if re.search(r"[A-Za-z]{3}", p) and not re.search(r"\b(new delhi|delhi|india|dist)\b", p, re.I)]
    return list(reversed(keep[-3:]))


def geocode_rows(rows: list[dict], progress=None) -> None:
    """Nominatim, at most one request per second, cached on disk so it runs once per address."""
    from . import geocode

    cache = _load_cache()
    for i, r in enumerate(rows, 1):
        if progress:
            progress(i, len(rows))
        city = _city(r)
        name = clean_name(r["name"])
        tries = [(f"{name}, {city}", "geocoded"), (name, "geocoded")]
        tries += [(f"{loc}, {city}", "locality") for loc in _localities(r.get("address") or "")[:2]]
        tries.append((f"{r['district']} {'Delhi' if r['state'] == 'Delhi' else ''}, {r['state']}".replace("  ", " "), "district"))
        for q, quality in tries:
            if q not in cache:
                hits = geocode.search(q, limit=1)
                cache[q] = [hits[0]["lat"], hits[0]["lng"]] if hits else None
                time.sleep(1.1)  # Nominatim usage policy
            if _plausible(r, cache[q]):
                r["lat"], r["lng"], r["geo_quality"] = cache[q][0], cache[q][1], quality
                break
        else:
            r["geo_quality"] = "none"
    DATA.mkdir(exist_ok=True)
    GEOCACHE.write_text(json.dumps(cache, indent=0, ensure_ascii=False), encoding="utf-8")


def load_snapshot() -> list[dict]:
    try:
        return [r for r in json.loads(SNAPSHOT.read_text(encoding="utf-8"))["banks"] if r.get("lat") is not None]
    except (OSError, ValueError, KeyError):
        return []


def upsert(db, rows: list[dict], source: str = "eraktkosh") -> dict:
    """Insert or update BloodBank rows by eRaktKosh hospital code (or name)."""
    from sqlalchemy import select

    from ..models import BloodBank

    existing = db.scalars(select(BloodBank)).all()
    by_code = {b.eraktkosh_code: b for b in existing if b.eraktkosh_code}
    by_name = {b.name.lower(): b for b in existing}
    added = updated = 0
    for r in rows:
        if r.get("lat") is None:
            continue
        b = by_code.get(r.get("eraktkosh_code")) or by_name.get(r["name"].lower())
        if b is None:
            b = BloodBank(name=r["name"], lat=r["lat"], lng=r["lng"], district=r.get("district", ""), state=r.get("state", ""))
            db.add(b)
            added += 1
        else:
            updated += 1
        b.name, b.address, b.phone, b.category = r["name"], r.get("address"), r.get("phone"), r.get("category")
        b.district, b.state, b.lat, b.lng = r.get("district") or b.district, r.get("state") or b.state, r["lat"], r["lng"]
        b.eraktkosh_code, b.source, b.geo_quality = r.get("eraktkosh_code"), source, r.get("geo_quality", "geocoded")
    return {"added": added, "updated": updated}


def refresh_live(db) -> dict:
    """Admin action: re-read the directory through TinyFish Fetch, geocode new addresses, upsert."""
    rows, via = download()
    cache = _load_cache()
    known = [r for r in rows if f"{clean_name(r['name'])}, {_city(r)}" in cache]
    new = [r for r in rows if r not in known]
    geocode_rows(known)  # cache hits only, no network
    geocode_rows(new[:40])  # shortcut: caps fresh geocoding per click at ~45 s; click again for the rest
    return {"via": via, "rows": len(rows), **upsert(db, [r for r in rows if r.get("lat") is not None])}
