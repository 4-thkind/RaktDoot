"""Blood requests: create, dispatch, live dashboard, fulfil, public share page."""
import asyncio
import json
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request as HttpRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..core.compatibility import compatible_donors, normalize_group
from ..db import get_db, session_scope, utcnow
from ..models import Notification, Request
from ..services import dispatch, tinyfish_client
from ..services.messages import GENDER_WORD
from ..services.whatsapp import normalize_phone
from .common import SSE_HEADERS, iso

router = APIRouter(prefix="/api")
OPEN_STATES = ("open",) + dispatch.ACTIVE_REQUEST


class RequestIn(BaseModel):
    patient_group: str
    group_confirmed: bool = True
    units: int = Field(ge=1, le=12)
    patient_age: int = Field(ge=0, le=120)
    patient_gender: str
    hospital_name: str = Field(min_length=2, max_length=200)
    hospital_address: str | None = Field(default=None, max_length=300)
    hospital_lat: float = Field(ge=6, le=38)    # India bounding box
    hospital_lng: float = Field(ge=68, le=98)
    requester_name: str = Field(min_length=1, max_length=80)
    requester_phone: str
    language: str = "en"

    @field_validator("patient_group")
    @classmethod
    def _g(cls, v):
        g = normalize_group(v)
        if not g:
            raise ValueError("unknown blood group")
        return g

    @field_validator("patient_gender")
    @classmethod
    def _gender(cls, v):
        v = (v or "").upper()[:1]
        if v not in ("M", "F", "O"):
            raise ValueError("gender must be M, F or O")
        return v

    @field_validator("requester_phone")
    @classmethod
    def _phone(cls, v):
        p = normalize_phone(v)
        if not p:
            raise ValueError("enter a valid mobile number")
        return p

    @field_validator("language")
    @classmethod
    def _lang(cls, v):
        return v if v in ("en", "hi") else "en"


def preview_text(r: Request) -> str:
    """The plea a family would otherwise type themselves, with the compatible groups worked out."""
    return (
        "URGENT BLOOD REQUEST (Rakt Doot)\n"
        f"Patient needs: {r.patient_group} ({r.units} unit{'s' if r.units > 1 else ''})"
        f"{'' if r.group_confirmed else ' - group not yet confirmed by hospital'}\n"
        f"Can receive from: {', '.join(compatible_donors(r.patient_group))}\n"
        f"Patient: {r.patient_age}, {GENDER_WORD[r.patient_gender]['en']}\n"
        f"Hospital: {r.hospital_name}\n"
        f"Details and updates: {settings.public_base_url.rstrip('/')}/r/{r.share_slug}"
    )


def _get(db: Session, rid: str, token: str) -> Request:
    r = db.get(Request, rid)
    if not r or not secrets.compare_digest(r.manage_token, token or ""):
        raise HTTPException(404, "Request not found")
    return r


@router.post("/requests", status_code=201)
async def create_request(body: RequestIn):
    open_count = await run_in_threadpool(_open_count, body.requester_phone)
    if open_count >= settings.max_open_requests_per_phone:
        raise HTTPException(429, "This number already has several open requests. Close one before opening another.")
    verified = await tinyfish_client.verify_hospital(body.hospital_name, body.hospital_address or "")
    with session_scope() as db:
        r = Request(**body.model_dump(), hospital_verified=verified,
                    target_acceptances=min(body.units * 2, 12),  # over-recruit: some donors will be deferred
                    expires_at=utcnow() + timedelta(hours=settings.request_ttl_hours))
        db.add(r)
        db.flush()
        return {"id": r.id, "manage_token": r.manage_token, "share_slug": r.share_slug,
                "preview": preview_text(r), "compatible": compatible_donors(r.patient_group),
                "hospital_verified": verified}


def _open_count(phone: str) -> int:
    with session_scope() as db:
        return db.scalar(select(func.count()).select_from(Request).where(Request.requester_phone == phone, Request.status.in_(OPEN_STATES))) or 0


@router.post("/requests/{rid}/dispatch")
def start(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    r = _get(db, rid, t)
    if r.status == "open":
        sent = dispatch.start_dispatch(db, r)
        db.commit()
        return {"status": r.status, "sent": sent}
    return {"status": r.status, "sent": 0}


@router.post("/requests/{rid}/fulfil")
def fulfil(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    r = _get(db, rid, t)
    dispatch.fulfil(db, r)
    db.commit()
    return snapshot(db, r)


@router.post("/requests/{rid}/cancel")
def cancel(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    r = _get(db, rid, t)
    if r.status in OPEN_STATES:
        dispatch.close(db, r, "cancelled")
        db.commit()
    return snapshot(db, r)


@router.post("/requests/{rid}/extend")
def extend(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    """'Still need blood?' Renew for another day."""
    r = _get(db, rid, t)
    if r.status not in OPEN_STATES:
        raise HTTPException(409, f"Request is {r.status}")
    r.expires_at = utcnow() + timedelta(hours=settings.request_ttl_hours)
    db.commit()
    return snapshot(db, r)


@router.post("/requests/{rid}/widen")
def widen(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    """Send the next wave now instead of waiting for the timer."""
    r = _get(db, rid, t)
    if r.status not in ("dispatching", "needs_public_share"):
        raise HTTPException(409, f"Request is {r.status}")
    if r.status == "needs_public_share":
        r.status = "dispatching"
        r.wave = max(0, len(settings.wave_radii_km) - 1)
    sent = dispatch.run_wave(db, r)
    db.commit()
    return {**snapshot(db, r), "sent_now": sent}


@router.get("/requests/{rid}")
def get_request(rid: str, t: str = Query(...), db: Session = Depends(get_db)):
    return snapshot(db, _get(db, rid, t))


def snapshot(db: Session, r: Request) -> dict:
    notes = db.scalars(select(Notification).where(Notification.request_id == r.id).order_by(Notification.sent_at)).all()
    counts: dict[str, int] = {}
    for n in notes:
        counts[n.status] = counts.get(n.status, 0) + 1
    radii = settings.wave_radii_km
    rings = []
    for i, radius in enumerate(radii):
        inner = radii[i - 1] if i else 0
        rings.append({"radius_km": radius, "notified": sum(1 for n in notes if (i == 0 or inner < n.distance_km) and n.distance_km <= radius)})
    donors = []
    for n in notes:
        if n.status not in ("accepted", "connected", "donated", "deferred", "no_show"):
            continue
        d = n.donor
        parts = d.name.split()
        donors.append({
            "id": n.id, "name": parts[0] + (f" {parts[-1][0]}." if len(parts) > 1 else ""), "group": d.blood_group,
            "distance_km": round(n.distance_km, 1), "status": n.status, "eta_minutes": n.eta_minutes,
            # the number is revealed only once the donor has accepted and passed the pre-screen
            "phone": d.phone if n.status in ("connected", "donated") else None,
            "since": iso(n.connected_at or n.responded_at),
        })
    first = (r.first_acceptance_at - r.dispatched_at).total_seconds() if r.first_acceptance_at and r.dispatched_at else None
    return {
        "id": r.id, "status": r.status, "patient_group": r.patient_group, "group_confirmed": r.group_confirmed,
        "compatible": compatible_donors(r.patient_group), "units": r.units, "patient_age": r.patient_age,
        "patient_gender": r.patient_gender, "hospital": {"name": r.hospital_name, "address": r.hospital_address,
                                                         "lat": r.hospital_lat, "lng": r.hospital_lng, "verified": r.hospital_verified},
        "requester_name": r.requester_name, "target": r.target_acceptances, "wave": r.wave, "radius_km": r.radius_km,
        "next_wave_at": iso(r.next_wave_at), "created_at": iso(r.created_at), "dispatched_at": iso(r.dispatched_at),
        "expires_at": iso(r.expires_at), "closed_at": iso(r.closed_at), "seconds_to_first_donor": first,
        "funnel": {
            "notified": len(notes),
            "delivered": sum(1 for n in notes if n.delivered_at),
            "read": sum(1 for n in notes if n.read_at),
            "responded": sum(1 for n in notes if n.responded_at),
            "connected": sum(1 for n in notes if n.status in dispatch.CONNECTED),
        },
        "counts": counts, "rings": rings, "donors": donors,
        "share_url": f"{settings.public_base_url.rstrip('/')}/r/{r.share_slug}", "share_slug": r.share_slug,
        "preview": preview_text(r),
    }


@router.get("/requests/{rid}/events")
async def events(rid: str, request: HttpRequest, t: str = Query(...)):
    """Live dashboard feed. Polls the database (works across processes) and pushes on change."""
    def snap() -> str:
        with session_scope() as db:
            return json.dumps(snapshot(db, _get(db, rid, t)), default=str)

    first = await run_in_threadpool(snap)  # 404 before the stream opens if the token is wrong

    async def gen():
        last, idle = first, 0
        yield f"data: {first}\n\n"
        while not await request.is_disconnected():
            await asyncio.sleep(1.5)
            cur = await run_in_threadpool(snap)
            if cur != last:
                last, idle = cur, 0
                yield f"data: {cur}\n\n"
            else:
                idle += 1
                if idle % 10 == 0:
                    yield ": keep-alive\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/share/{slug}")
def share(slug: str, db: Session = Depends(get_db)):
    """Public page data. No phone numbers or names of anyone."""
    r = db.scalar(select(Request).where(Request.share_slug == slug))
    if not r:
        raise HTTPException(404, "Request not found")
    return {
        "status": r.status, "patient_group": r.patient_group, "group_confirmed": r.group_confirmed,
        "compatible": compatible_donors(r.patient_group), "units": r.units, "patient_age": r.patient_age,
        "patient_gender": r.patient_gender, "hospital": {"name": r.hospital_name, "address": r.hospital_address,
                                                         "lat": r.hospital_lat, "lng": r.hospital_lng},
        "created_at": iso(r.created_at), "expires_at": iso(r.expires_at), "closed_at": iso(r.closed_at),
        "connected": db.scalar(select(func.count()).select_from(Notification).where(Notification.request_id == r.id, Notification.status.in_(dispatch.CONNECTED))) or 0,
        "target": r.target_acceptances,
    }
