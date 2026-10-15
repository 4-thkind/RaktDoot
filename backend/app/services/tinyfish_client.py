"""TinyFish integration.

eRaktKosh shows live blood stock per blood centre but has no public API. A TinyFish web
agent operates its Stock Availability form (state, district, group, component), reads the
results table and returns structured JSON. Results are cached per (state, district,
component) so cost scales with districts, not users, and the government server sees fewer
requests than a person refreshing the page.

Modes: live (TINYFISH_API_KEY set) or demo (sample stock generated from our blood-bank
table, clearly labelled as sample data in the API and the UI)."""
import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Awaitable, Callable

from sqlalchemy import select

from ..config import settings
from ..core.compatibility import GROUPS, normalize_group
from ..core.geo import haversine_km
from ..db import session_scope, utcnow
from ..models import BloodBank, StockCache

log = logging.getLogger("raktdoot.tinyfish")
Emit = Callable[[dict], Awaitable[None]]

GOAL_TEMPLATE = """You are on the eRaktKosh "Stock Availability" page of the Government of India.
1. In "Select State" choose "{state}".
2. Wait for the district list to load. In "Select District" choose the option that best matches "{district}". If nothing is close, choose "All".
3. In "Select Blood Group" choose "All Blood Groups".
4. In "Select Blood Component" choose "{component}".
5. Click Search and wait for the results table. Read the "Government Blood Banks" tab and the "Other Blood Banks" tab.

Return ONLY a JSON object of this shape:
{{"district_selected": "<district option you chose>",
  "banks": [{{"name": str, "address": str or null, "phone": str or null, "category": str or null,
             "type": str or null, "last_updated": str or null, "availability_text": str,
             "stock": {{"A+": int, "A-": int, "B+": int, "B-": int, "AB+": int, "AB-": int, "O+": int, "O-": int}}}}]}}
Rules:
- At most 25 banks, in the order shown.
- The Blood Bank cell often contains the name, address and phone together; split them into the fields.
- "stock" holds the number of units shown for each group. Use 0 for a group shown as not available. Leave out groups that are not mentioned. Ignore Bombay groups (Oh+Ve, Oh-Ve).
- Copy the Availability cell text into availability_text exactly as shown.
- If the table is empty, return {{"district_selected": "<district>", "banks": []}}.
- If a captcha, an error page or an access block appears, return {{"error": "<short reason>"}}."""

_locks: dict[tuple, asyncio.Lock] = {}


def _clean_banks(raw_banks: list) -> list[dict]:
    banks = []
    for b in raw_banks[:25]:
        if not isinstance(b, dict) or not str(b.get("name") or "").strip():
            continue
        stock = {}
        for k, v in (b.get("stock") or {}).items():
            g = normalize_group(str(k))
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if g and n >= 0:
                stock[g] = n
        banks.append({
            "name": str(b["name"]).strip()[:200],
            "address": (str(b.get("address")).strip()[:300] or None) if b.get("address") else None,
            "phone": (str(b.get("phone")).strip()[:40] or None) if b.get("phone") else None,
            "category": b.get("category"),
            "type": b.get("type"),
            "last_updated": b.get("last_updated"),
            "availability_text": str(b.get("availability_text") or "")[:300],
            "stock": stock,
        })
    return banks


def validate_result(result) -> tuple[list[dict] | None, str | None]:
    """COMPLETED does not mean the goal succeeded. Return (banks, error)."""
    if isinstance(result, str):
        return None, "agent returned text, not JSON"
    if isinstance(result, list):  # tolerate a bare list of banks
        return _clean_banks(result), None
    if not isinstance(result, dict):
        return None, "empty result"
    if result.get("error"):
        return None, str(result["error"])[:200]
    banks = result.get("banks")
    if not isinstance(banks, list):
        return None, "bad_shape"
    text = str(result).lower()
    if not banks and any(w in text for w in ("captcha", "blocked", "access denied")):
        return None, "blocked"
    return _clean_banks(banks), None


def _tokens(name: str) -> set[str]:
    stop = {"blood", "bank", "centre", "center", "hospital", "the", "of", "and", "govt", "government", "ltd", "pvt", "delhi", "new"}
    return {t for t in re.findall(r"[a-z]+", name.lower()) if t not in stop and len(t) > 2}


def attach_locations(banks: list[dict], directory: list[BloodBank], origin: tuple[float, float] | None) -> list[dict]:
    """eRaktKosh's table has no coordinates; match names against our directory to get distance."""
    for b in banks:
        bt = _tokens(b["name"])
        best, best_score = None, 0.0
        for d in directory:
            dt = _tokens(d.name)
            if not bt or not dt:
                continue
            s = len(bt & dt) / min(len(bt), len(dt))
            if s > best_score:
                best, best_score = d, s
        if best and best_score >= 0.6:
            b["lat"], b["lng"] = best.lat, best.lng
            b["phone"] = b.get("phone") or best.phone
            b["address"] = b.get("address") or best.address
        if origin and b.get("lat") is not None:
            b["distance_km"] = round(haversine_km(origin[0], origin[1], b["lat"], b["lng"]), 1)
        else:
            b.setdefault("distance_km", None)
    banks.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return banks


def _demo_banks(state: str, district: str, origin: tuple[float, float] | None) -> list[dict]:
    """Deterministic sample stock (changes hourly) so the full flow can be shown without a key."""
    with session_scope() as db:
        rows = db.scalars(select(BloodBank)).all()
    if origin:
        rows = sorted(rows, key=lambda r: haversine_km(origin[0], origin[1], r.lat, r.lng))[:12]
    else:
        rows = [r for r in rows if r.district.lower() == district.lower()][:12]
    hour = utcnow().strftime("%Y%m%d%H")
    banks = []
    for r in rows:
        stock = {}
        for g in GROUPS:
            h = int(hashlib.sha256(f"{r.name}{g}{hour}".encode()).hexdigest(), 16)
            scarce = g.endswith("-")
            stock[g] = 0 if h % (2 if scarce else 4) == 0 else h % (4 if scarce else 18)
        banks.append({"name": r.name, "address": r.address, "phone": r.phone, "category": r.category,
                      "type": "Blood Centre", "last_updated": datetime.now(ZoneInfo(settings.timezone)).strftime("%d-%m-%Y %H:00"),
                      "availability_text": "", "stock": stock, "lat": r.lat, "lng": r.lng})
    return banks


async def lookup_stock(state: str, district: str, origin: tuple[float, float] | None, emit: Emit) -> dict:
    """Live stock for one district. Never raises: on any failure returns cached data or an
    'unavailable' result with suggest_donor_search=True, so the emergency flow never blocks."""
    component = settings.eraktkosh_component
    key = (state.lower(), district.lower(), component)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        with session_scope() as db:
            cached = db.scalar(select(StockCache).where(StockCache.state == state, StockCache.district == district, StockCache.component == component))
            cache = None
            if cached:
                cache = {"results": cached.results, "fetched_at": cached.fetched_at, "source": cached.source,
                         "run_id": cached.source_run_id, "streaming_url": cached.streaming_url}
            directory = db.scalars(select(BloodBank)).all()
            db.expunge_all()

        fresh = cache and utcnow() - cache["fetched_at"] < timedelta(minutes=settings.stock_cache_ttl_min)
        mode = "live" if settings.tinyfish_live else "demo"
        if fresh and cache["source"] == mode:
            await emit({"type": "progress", "message": "Using results fetched in the last few minutes."})
            return _result("cache", cache["results"], cache["fetched_at"], cache["run_id"], cache["streaming_url"], directory, origin, sample=mode == "demo")

        if mode == "demo":
            await emit({"type": "progress", "message": "TinyFish key not set. Showing sample stock."})
            await asyncio.sleep(0.6)
            banks = _demo_banks(state, district, origin)
            _store(state, district, component, banks, "demo", None, None)
            return _result("demo", banks, utcnow(), None, None, directory, origin, sample=True)

        goal = GOAL_TEMPLATE.format(state=state, district=district, component=component)
        run_id = streaming_url = None
        try:
            from tinyfish import AsyncTinyFish, BrowserProfile, CompleteEvent, ProgressEvent, StartedEvent, StreamingUrlEvent

            client = AsyncTinyFish(api_key=settings.tinyfish_api_key)
            result = None
            async with asyncio.timeout(settings.stock_timeout_s):
                async with client.agent.stream(url=settings.eraktkosh_stock_url, goal=goal, browser_profile=BrowserProfile.STEALTH) as stream:
                    async for event in stream:
                        if isinstance(event, StartedEvent):
                            run_id = event.run_id
                            await emit({"type": "progress", "message": "Agent opened eRaktKosh.", "run_id": run_id})
                        elif isinstance(event, StreamingUrlEvent):
                            streaming_url = event.streaming_url
                            await emit({"type": "agent_view", "streaming_url": streaming_url})
                        elif isinstance(event, ProgressEvent):
                            await emit({"type": "progress", "message": event.purpose})
                        elif isinstance(event, CompleteEvent):
                            run_id = event.run_id or run_id
                            if str(event.status).upper().endswith("COMPLETED"):
                                result = event.result_json
                            else:
                                raise RuntimeError(f"run {event.status}: {event.error}")
                            break
            banks, error = validate_result(result)
            if error:
                raise RuntimeError(error)
        except Exception as e:
            reason = "timeout" if isinstance(e, TimeoutError) else str(e)[:200]
            log.warning("tinyfish lookup %s/%s failed: %s", state, district, reason)
            if cache:
                out = _result("stale_cache", cache["results"], cache["fetched_at"], cache["run_id"], cache["streaming_url"], directory, origin, sample=cache["source"] == "demo")
            else:
                out = {"source": "unavailable", "fetched_at": None, "banks": [], "run_id": run_id, "streaming_url": streaming_url, "sample": False}
            out["reason"] = reason
            out["suggest_donor_search"] = True
            return out

        _store(state, district, component, banks, "live", run_id, streaming_url)
        return _result("live", banks, utcnow(), run_id, streaming_url, directory, origin, sample=False)


def _store(state, district, component, banks, source, run_id, streaming_url) -> None:
    clean = [{k: v for k, v in b.items() if k not in ("distance_km",)} for b in banks]
    with session_scope() as db:
        row = db.scalar(select(StockCache).where(StockCache.state == state, StockCache.district == district, StockCache.component == component))
        if row is None:
            row = StockCache(state=state, district=district, component=component)
            db.add(row)
        row.results, row.source, row.source_run_id, row.streaming_url, row.fetched_at = clean, source, run_id, streaming_url, utcnow()


def _result(source, banks, fetched_at, run_id, streaming_url, directory, origin, sample) -> dict:
    banks = attach_locations([dict(b) for b in banks], directory, origin)
    return {"source": source, "fetched_at": fetched_at, "banks": banks, "run_id": run_id,
            "streaming_url": streaming_url, "sample": sample, "component": settings.eraktkosh_component}


async def verify_hospital(name: str, near: str = "") -> bool | None:
    """Anti-fake-request signal via TinyFish Search. None = could not check."""
    if not settings.tinyfish_live:
        return None
    try:
        from tinyfish import AsyncTinyFish

        client = AsyncTinyFish(api_key=settings.tinyfish_api_key)
        async with asyncio.timeout(8):
            res = await client.search.query(f"{name} hospital {near}".strip(), location="IN", language="en")
        words = _tokens(name)
        return any(words and len(words & _tokens(r.title + " " + r.snippet)) >= max(1, len(words) // 2) for r in res.results[:5])
    except Exception as e:
        log.info("hospital verify failed: %s", e)
        return None
