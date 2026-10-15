"""Geocoding via OpenStreetMap Nominatim, with an offline fallback so the flow never blocks."""
import logging
import re

import httpx

from ..config import settings

log = logging.getLogger("raktdoot.geocode")
NOMINATIM = "https://nominatim.openstreetmap.org"
HEADERS = {"User-Agent": "RaktDoot/1.0 (hackathon project; emergency blood finder)"}

# shortcut: coarse pincode-prefix centroids for Delhi NCR only; Nominatim handles the rest of India
PIN_PREFIX = {
    "110": (28.6139, 77.2090, "Delhi"),
    "122": (28.4595, 77.0266, "Gurugram"),
    "121": (28.4089, 77.3178, "Faridabad"),
    "201": (28.5355, 77.3910, "Noida / Ghaziabad"),
    "124": (28.8955, 76.6066, "Rohtak"),
    "131": (28.9931, 77.0151, "Sonipat"),
}


def _get(path: str, params: dict) -> list | dict | None:
    if settings.geocoder != "nominatim":
        return None
    try:
        r = httpx.get(f"{NOMINATIM}/{path}", params={**params, "format": "jsonv2", "countrycodes": "in"}, headers=HEADERS, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.info("nominatim %s failed: %s", path, e)
        return None


def search(query: str, limit: int = 5) -> list[dict]:
    """Free-text place search. Returns [{name, address, lat, lng}]."""
    res = _get("search", {"q": query, "limit": limit, "addressdetails": 1}) or []
    out = []
    for item in res if isinstance(res, list) else []:
        out.append({
            "name": item.get("name") or item.get("display_name", "").split(",")[0],
            "address": item.get("display_name"),
            "lat": float(item["lat"]),
            "lng": float(item["lon"]),
        })
    return out


def pincode(code: str) -> dict | None:
    code = re.sub(r"\D", "", code or "")
    if len(code) != 6:
        return None
    hits = _get("search", {"postalcode": code, "limit": 1})
    if isinstance(hits, list) and hits:
        return {"lat": float(hits[0]["lat"]), "lng": float(hits[0]["lon"]), "label": hits[0].get("display_name", code).split(",")[0], "approximate": False}
    pref = PIN_PREFIX.get(code[:3])
    if pref:
        return {"lat": pref[0], "lng": pref[1], "label": f"{pref[2]} ({code})", "approximate": True}
    return None


def reverse(lat: float, lng: float) -> dict | None:
    """Coordinates to {state, district}. eRaktKosh searches by state + district."""
    res = _get("reverse", {"lat": lat, "lon": lng, "zoom": 10, "addressdetails": 1})
    if not isinstance(res, dict) or "address" not in res:
        return None
    a = res["address"]
    district = a.get("state_district") or a.get("county") or a.get("city_district") or a.get("city")
    state = a.get("state") or a.get("territory")
    if not (district and state):
        return None
    district = re.sub(r"\s+(district|tehsil)$", "", district, flags=re.I)
    return {"state": state, "district": district}
