"""Blood-bank stock (TinyFish -> eRaktKosh), nearby banks, places."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..core.compatibility import COMPONENTS, GROUPS, compatible_donors, normalize_component, normalize_group
from ..core.geo import bearing_deg, haversine_km
from ..db import get_db, session_scope
from ..models import BloodBank
from ..services import geocode, tinyfish_client
from .common import SSE_HEADERS, iso, sse

router = APIRouter(prefix="/api")
NEAR_KM = 25  # beyond this, or with no stock, the UI suggests asking donors


def _group(group: str) -> str:
    g = normalize_group(group)
    if not g:
        raise HTTPException(422, f"Unknown blood group. Use one of {', '.join(GROUPS)}")
    return g


def hospital_name(bank_name: str) -> str:
    """'Blood Centre, Max Super Specialty Hospital (A Unit Of ...)' -> 'Max Super Specialty Hospital'."""
    from ..services.directory import clean_name
    return clean_name(bank_name).replace(" Blood Bank", "").replace(" ,", ",").strip(", ")


NOT_HOSPITAL = BloodBank.category.like("Charitable%")  # standalone charitable blood banks are not hospitals


def _nearest_bank(db: Session, lat: float, lng: float) -> BloodBank | None:
    banks = db.scalars(select(BloodBank)).all()
    return min(banks, key=lambda b: haversine_km(lat, lng, b.lat, b.lng), default=None)


def locate(lat: float, lng: float) -> dict:
    """Coordinates -> eRaktKosh state + district. Falls back to the nearest known blood bank."""
    hit = geocode.reverse(lat, lng)
    if hit:
        return {**hit, "source": "geocoder"}
    with session_scope() as db:
        b = _nearest_bank(db, lat, lng)
        if b:
            return {"state": b.state, "district": b.district, "source": "nearest blood bank"}
    raise HTTPException(404, "Could not work out the district for this location")


def shape(result: dict, group: str, origin: tuple[float, float], component: str = "prbc") -> dict:
    """Reduce full stock tables to what a family needs: units of the patient's group and of compatible groups."""
    compat = compatible_donors(group, component)
    banks = []
    for b in result["banks"]:
        stock = b.get("stock") or {}
        compatible = {g: stock[g] for g in compat if g in stock}
        out = {
            "name": b["name"], "address": b.get("address"), "phone": b.get("phone"), "category": b.get("category"),
            "last_updated": b.get("last_updated"), "distance_km": b.get("distance_km"),
            "bearing": round(bearing_deg(origin[0], origin[1], b["lat"], b["lng"])) if b.get("lat") is not None else None,
            "lat": b.get("lat"), "lng": b.get("lng"),
            "exact_units": stock.get(group), "compatible_units": compatible,
            "total_compatible": sum(compatible.values()) if compatible else None,
            "availability_text": b.get("availability_text") or None, "match_score": b.get("match_score"),
        }
        banks.append(out)
    stocked = [b for b in banks if (b["total_compatible"] or 0) > 0]
    near = [b for b in stocked if b["distance_km"] is not None and b["distance_km"] <= NEAR_KM]
    nearest = min((b["distance_km"] for b in stocked if b["distance_km"] is not None), default=None)
    return {
        "source": result["source"], "sample": result.get("sample", False), "fetched_at": iso(result.get("fetched_at")),
        "run_id": result.get("run_id"), "streaming_url": result.get("streaming_url"), "reason": result.get("reason"),
        "component": result.get("component", component), "component_label": result.get("component_label"),
        "served_by": result.get("served_by"), "duration_s": result.get("duration_s"), "steps": result.get("steps"), "group": group, "compatible_groups": compat, "banks": banks,
        "summary": {
            "banks_checked": len(banks), "banks_with_stock": len(stocked), "nearest_stock_km": nearest,
            "near_threshold_km": NEAR_KM, "suggest_donors": not near,
        },
    }


@router.get("/stock/stream")
async def stock_stream(request: Request, lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180),
                       group: str = Query(...), component: str = Query("prbc")):
    """Server-sent events: progress lines while the TinyFish agent works, then one `result`."""
    group, component = _group(group), normalize_component(component)
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(ev: dict) -> None:
        await queue.put(("progress", ev))

    async def work():
        try:
            place = await run_in_threadpool(locate, lat, lng)
            await queue.put(("progress", {"type": "located", "message": f"Searching {place['district']}, {place['state']} on eRaktKosh.", **place}))
            res = await tinyfish_client.lookup_stock(place["state"], place["district"], (lat, lng), emit, component)
            await queue.put(("result", {**shape(res, group, (lat, lng), component), "place": place}))
        except HTTPException as e:
            await queue.put(("result", {"source": "unavailable", "reason": e.detail, "banks": [], "group": group,
                                        "compatible_groups": compatible_donors(group, component), "component": component, "summary": {"suggest_donors": True, "banks_checked": 0, "banks_with_stock": 0}}))
        except Exception as e:  # never leave the family staring at a spinner
            await queue.put(("result", {"source": "unavailable", "reason": str(e)[:200], "banks": [], "group": group,
                                        "compatible_groups": compatible_donors(group, component), "component": component, "summary": {"suggest_donors": True, "banks_checked": 0, "banks_with_stock": 0}}))
        await queue.put(("done", {}))

    async def gen():
        task = asyncio.create_task(work())
        try:
            while True:
                try:
                    kind, data = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield sse(data, kind)
                if kind == "done":
                    break
                if await request.is_disconnected():
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/stock")
async def stock(lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180), group: str = Query(...),
                component: str = Query("prbc")):
    group, component = _group(group), normalize_component(component)

    async def noop(_):
        return None

    place = await run_in_threadpool(locate, lat, lng)
    res = await tinyfish_client.lookup_stock(place["state"], place["district"], (lat, lng), noop, component)
    return {**shape(res, group, (lat, lng), component), "place": place}


@router.get("/compatible/{group}")
def compatible(group: str, component: str = "prbc"):
    g = _group(group)
    return {"group": g, "component": normalize_component(component), "can_receive_from": compatible_donors(g, component)}


@router.get("/components")
def components():
    """Component picker options. Plasma/platelet compatibility tables: verify against NBTC guidance."""
    return {c: {g: compatible_donors(g, c) for g in GROUPS} for c in COMPONENTS}


@router.get("/banks/nearby")
def banks_nearby(lat: float, lng: float, limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    rows = sorted(((haversine_km(lat, lng, b.lat, b.lng), b) for b in db.scalars(select(BloodBank)).all()), key=lambda x: x[0])
    return [{"name": b.name, "address": b.address, "phone": b.phone, "lat": b.lat, "lng": b.lng,
             "district": b.district, "state": b.state, "distance_km": round(d, 1)} for d, b in rows[:limit]]


@router.get("/places/search")
async def places_search(q: str = Query(..., min_length=2, max_length=120), lat: float | None = None, lng: float | None = None):
    """Hospital / place / pincode search: our blood-centre list first, then OpenStreetMap."""
    ql = q.lower()
    with session_scope() as db:
        local = [{"name": hospital_name(b.name), "address": b.address, "lat": b.lat, "lng": b.lng, "source": "directory"}
                 for b in db.scalars(select(BloodBank).where(~NOT_HOSPITAL | BloodBank.category.is_(None))).all()
                 if ql in b.name.lower() or ql in (b.address or "").lower()][:6]
    if q.strip().isdigit():
        hit = await run_in_threadpool(geocode.pincode, q)
        remote = [{"name": hit["label"], "address": f"Pincode {q}", "lat": hit["lat"], "lng": hit["lng"], "source": "pincode"}] if hit else []
    else:
        remote = [{**r, "source": "openstreetmap"} for r in await run_in_threadpool(geocode.search, q, 6)]
    results = local + remote
    if lat is not None and lng is not None:
        for r in results:
            r["distance_km"] = round(haversine_km(lat, lng, r["lat"], r["lng"]), 1)
    return results[:10]


@router.get("/places/nearby-hospitals")
def nearby_hospitals(lat: float, lng: float, db: Session = Depends(get_db)):
    """Hospitals with a blood centre near a point (used to pre-fill the hospital field)."""
    rows = sorted(((haversine_km(lat, lng, b.lat, b.lng), b) for b in db.scalars(select(BloodBank).where(~NOT_HOSPITAL | BloodBank.category.is_(None))).all()),
                  key=lambda x: x[0])
    return [{"name": hospital_name(b.name), "address": b.address,
             "lat": b.lat, "lng": b.lng, "distance_km": round(d, 1)} for d, b in rows[:6]]
