"""AI features: slip scan (F3), forward checker (F2), family guide (F13), shortage radar (F1),
camps + placement (A1, F10), recurring rotas (F7), TinyFish webhooks (S1/S2)."""
import re
import secrets
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request as HttpRequest, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..core.compatibility import normalize_component, normalize_group
from ..db import get_db, session_scope
from ..models import Forward, RecurringNeed, RecurringSlot, Request, Signal
from ..services import camp_placement, camps, forecast, forwards, guide, recurring, tinyfish_client, vision
from ..services.whatsapp import normalize_phone
from .common import require_admin

router = APIRouter(prefix="/api")
hooks = APIRouter()


# ---------------------------------------------------------------- F3 slip scan
@router.post("/vision/slip")
async def scan_slip(file: UploadFile | None = File(default=None), sample: str = Query("")):
    """Photo of the hospital requisition slip -> pre-filled request fields with a confidence each.
    The image is processed in memory and dropped."""
    if sample:
        data, mime = vision.sample_bytes(sample) or b"", "image/jpeg"
        if not data:
            raise HTTPException(404, "unknown sample")
    elif file is not None:
        data, mime = await file.read(vision.MAX_BYTES + 1), file.content_type or "image/jpeg"
    else:
        raise HTTPException(422, "send a photo or ?sample=requisition_slip.jpg")
    out = await run_in_threadpool(vision.parse_slip, data, mime)
    del data
    return out


@router.get("/media/{mid}")
def media(mid: str, db: Session = Depends(get_db)):
    """Generated voice replies (TTS)."""
    from ..models import MediaFile
    m = db.get(MediaFile, mid)
    if m is None:
        raise HTTPException(404, "not found")
    return Response(m.data, media_type=m.mime, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/samples/{name}")
def sample_file(name: str):
    """Bundled SAMPLE images / voice notes used by demo mode (whitelisted by the manifest)."""
    data = vision.sample_bytes(name)
    if data is None:
        raise HTTPException(404, "not a sample")
    return Response(data, media_type="audio/mpeg" if name.endswith(".mp3") else "audio/wav" if name.endswith(".wav") else "image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"})


# ---------------------------------------------------------------- F4 voice on the web
class ExtractIn(BaseModel):
    text: str = Field(min_length=2, max_length=2000)


@router.post("/extract")
def extract_request(body: ExtractIn):
    """Text (e.g. from the browser's own speech recognition) -> request fields with confidences."""
    from ..services import extraction
    return {"transcript": body.text, "fields": extraction.extract(body.text), "engine": "browser"}


@router.post("/voice/parse")
async def voice_parse(file: UploadFile | None = File(default=None), sample: str = Query("")):
    """A recorded voice note -> transcript (STT) -> request fields. The audio is dropped after transcription."""
    from ..services import extraction, stt
    if sample:
        data, mime = vision.sample_bytes(sample) or b"", "audio/mpeg"
        if not data:
            raise HTTPException(404, "unknown sample")
    elif file is not None:
        data, mime = await file.read(stt.MAX_BYTES + 1), file.content_type or "audio/webm"
    else:
        raise HTTPException(422, "send an audio file or ?sample=voice_request.mp3")
    heard = await run_in_threadpool(stt.transcribe, data, mime)
    del data
    text = heard.get("text", "")
    return {"transcript": text, "engine": heard.get("engine"), "sample": heard.get("sample", False), "error": heard.get("error"),
            "fields": extraction.extract(text) if text else None}


# ---------------------------------------------------------------- A2 camp registration on the web
class CampRegIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str
    dob: date
    gender: str = Field(pattern="^[MFO]$")
    blood_group: str
    aadhaar: str = Field(min_length=12, max_length=14)
    consent: bool

    @field_validator("phone")
    @classmethod
    def _p(cls, v):
        p = normalize_phone(v)
        if not p:
            raise ValueError("enter a valid mobile number")
        return p


@router.post("/camps/{camp_id}/register", status_code=201)
def register_for_camp(camp_id: str, body: CampRegIn, db: Session = Depends(get_db)):
    """Rakt Doot fills the camp portal for the donor (captcha solved); the donor then sends the OTP."""
    from ..models import Camp
    from ..services import camp_registration
    if not body.consent:
        raise HTTPException(422, "Registration needs your consent")
    camp = db.get(Camp, camp_id)
    if camp is None:
        raise HTTPException(404, "Camp not found")
    details = {"name": body.name, "mobile": body.phone[-10:], "mobile_full": body.phone, "dob": body.dob.isoformat(),
               "gender": body.gender, "blood_group": normalize_group(body.blood_group) or "Don't know"}
    reg = camp_registration.start(db, camp, details, body.aadhaar)
    return _reg_json(db, reg)


def _reg_json(db: Session, reg) -> dict:
    from ..models import ChatMessage
    sms = None
    if settings.whatsapp_mode == "mock" and not settings.camp_portal_url:  # demo: show the mock portal's OTP SMS on screen
        m = db.scalar(select(ChatMessage).where(ChatMessage.phone == reg.phone, ChatMessage.kind == "sms").order_by(ChatMessage.id.desc()).limit(1))
        sms = m.body if m else None
    return {"id": reg.id, "status": reg.status, "steps": reg.steps, "ref": reg.portal_ref, "error": reg.error, "engine": reg.engine,
            "demo_sms": sms}


class OtpIn(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


@router.post("/camps/registrations/{rid}/otp")
def registration_otp(rid: str, body: OtpIn, db: Session = Depends(get_db)):
    from ..models import CampRegistration
    from ..services import camp_registration
    reg = db.get(CampRegistration, rid)
    if reg is None or reg.status not in ("otp_sent",):
        raise HTTPException(404, "Registration not waiting for an OTP")
    return _reg_json(db, camp_registration.finish(db, reg, body.otp))


# ---------------------------------------------------------------- F2 forward checker
class ForwardIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)


@router.post("/forwards/check")
def check_forward(body: ForwardIn, db: Session = Depends(get_db)):
    res = forwards.check(db, body.text, "web")
    db.commit()
    return res


class ForwardAlertIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: str
    consent: bool

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        p = normalize_phone(v)
        if not p:
            raise ValueError("enter a valid mobile number")
        return p


@router.post("/forwards/{fid}/alert", status_code=201)
def alert_from_forward(fid: str, body: ForwardAlertIn, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(422, "Only alert donors with the family's consent")
    open_count = db.scalar(select(func.count()).select_from(Request).where(
        Request.requester_phone == body.phone, Request.status.in_(("open", "dispatching", "matched", "needs_public_share")))) or 0
    if open_count >= settings.max_open_requests_per_phone:
        raise HTTPException(429, "This number already has several open requests.")
    if db.get(Forward, fid) is None:
        raise HTTPException(404, "Check not found")
    try:
        r = forwards.create_request(db, fid, body.phone, body.name)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return {"id": r.id, "manage_token": r.manage_token, "share_slug": r.share_slug}


# ---------------------------------------------------------------- F13 family guide
@router.get("/guide/ask")
def ask_guide(q: str = Query(..., min_length=2, max_length=500), lang: str = "en", db: Session = Depends(get_db)):
    guide.ensure_loaded(db)
    db.commit()
    return guide.answer(q, lang)


# ---------------------------------------------------------------- F1 shortage radar
@router.get("/radar")
def radar(component: str = "prbc", db: Session = Depends(get_db)):
    data = forecast.radar(db, normalize_component(component))
    db.commit()
    return data


@router.post("/admin/radar/drive", dependencies=[Depends(require_admin)], status_code=201)
def start_drive(district: str, group: str, component: str = "prbc", db: Session = Depends(get_db)):
    g = normalize_group(group)
    if not g:
        raise HTTPException(422, "unknown blood group")
    try:
        req = forecast.start_drive(db, district, g, component)
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return {"id": req.id, "manage_token": req.manage_token, "status": req.status, "hospital": req.hospital_name}


@router.get("/admin/radar/backtest", dependencies=[Depends(require_admin)])
def backtest(component: str = "prbc", db: Session = Depends(get_db)):
    out = forecast.backtest(db, normalize_component(component))
    db.commit()
    return out


# ---------------------------------------------------------------- A1 camps, F10 placement
@router.get("/camps")
def upcoming_camps(lat: float | None = None, lng: float | None = None, days: int = Query(30, le=90), db: Session = Depends(get_db)):
    from ..models import Camp
    rows = db.scalars(select(Camp).where(Camp.camp_date >= date.today(), Camp.camp_date <= date.today() + timedelta(days=days))
                      .order_by(Camp.camp_date)).all()
    out = [camps.as_json(c, lat, lng) for c in rows]
    if lat is not None:
        out.sort(key=lambda c: (c["distance_km"] is None, c["distance_km"] or 0))
    return {"camps": out[:50], "registration_note": "eRaktKosh camp sign-up needs a captcha, OTP and Aadhaar, so donors register on the official form themselves."}


@router.get("/camps/placement")
def placement(k: int = Query(5, ge=1, le=15), component: str = "prbc", db: Session = Depends(get_db)):
    out = camp_placement.recommend(db, k, normalize_component(component))
    db.commit()
    return out


@router.get("/camps/placement.csv")
def placement_csv(k: int = Query(10, ge=1, le=30), component: str = "prbc", db: Session = Depends(get_db)):
    rec = camp_placement.recommend(db, k, normalize_component(component))
    return PlainTextResponse(camp_placement.to_csv(rec), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=raktdoot-camp-sites.csv"})


# ---------------------------------------------------------------- F7 recurring needs
class RecurringIn(BaseModel):
    patient_label: str = Field(min_length=1, max_length=80)
    patient_group: str
    component: str = "prbc"
    units: int = Field(ge=1, le=4)
    interval_days: int = Field(ge=7, le=60)
    next_due: date
    hospital_name: str = Field(min_length=2, max_length=200)
    hospital_lat: float = Field(ge=6, le=38)
    hospital_lng: float = Field(ge=68, le=98)
    requester_name: str = Field(min_length=1, max_length=80)
    requester_phone: str
    max_km: float = Field(default=15, ge=2, le=40)

    @field_validator("patient_group")
    @classmethod
    def _g(cls, v):
        g = normalize_group(v)
        if not g:
            raise ValueError("unknown blood group")
        return g

    @field_validator("requester_phone")
    @classmethod
    def _p(cls, v):
        p = normalize_phone(v)
        if not p:
            raise ValueError("enter a valid mobile number")
        return p


@router.post("/recurring", status_code=201)
def create_recurring(body: RecurringIn, db: Session = Depends(get_db)):
    if body.next_due < date.today():
        raise HTTPException(422, "next due date is in the past")
    need = RecurringNeed(**{**body.model_dump(), "component": normalize_component(body.component)})
    db.add(need)
    db.flush()
    slots = recurring.rebuild(db, need)
    db.commit()
    return {"id": need.id, "manage_token": need.manage_token, **recurring.as_json(need, slots)}


def _need(db: Session, nid: str, t: str) -> RecurringNeed:
    need = db.get(RecurringNeed, nid)
    if need is None or not (need.synthetic or secrets.compare_digest(need.manage_token, t or "")):
        raise HTTPException(404, "Not found")
    return need


@router.get("/recurring/demo")
def recurring_demo(db: Session = Depends(get_db)):
    """The SYNTHETIC demo patient's rota, viewable without a token."""
    need = db.scalar(select(RecurringNeed).where(RecurringNeed.synthetic.is_(True)).limit(1))
    if need is None:
        raise HTTPException(404, "No demo patient. Reset the database from /admin.")
    slots = db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id).order_by(RecurringSlot.due_date)).all()
    return recurring.as_json(need, slots)


@router.get("/recurring/{nid}")
def get_recurring(nid: str, t: str = "", db: Session = Depends(get_db)):
    need = _need(db, nid, t)
    slots = db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id).order_by(RecurringSlot.due_date)).all()
    return recurring.as_json(need, slots)


@router.post("/recurring/{nid}/replan")
def replan(nid: str, t: str = "", db: Session = Depends(get_db)):
    need = _need(db, nid, t)
    slots = recurring.rebuild(db, need)
    db.commit()
    return recurring.as_json(need, slots)


# ---------------------------------------------------------------- TinyFish webhooks (S1, S2)
def _hook_key(key: str) -> None:
    if not settings.tinyfish_webhook_secret or not secrets.compare_digest(key or "", settings.tinyfish_webhook_secret):
        raise HTTPException(404, "Not found")


@hooks.post("/webhooks/tinyfish")
async def tinyfish_run_hook(request: HttpRequest, background: BackgroundTasks, key: str = ""):
    """run.completed for a batch sweep run. The payload is NOT trusted: we re-fetch the run by id with our key."""
    _hook_key(key)
    body = await request.json()
    rid = str(body.get("run_id") or "")[:80]
    if rid:
        background.add_task(_store_run, rid)
    return {"ok": True}


async def _store_run(run_id: str) -> None:
    from ..services import stock_history

    run = await tinyfish_client._client(timeout=30).runs.get(run_id)
    m = re.search(r'choose "([^"]+)"\.\n2\..*?matches "([^"]+)".*?Component" choose "([^"]+)"', run.goal or "", re.S)
    if not m or not str(run.status).endswith("COMPLETED"):
        return
    comp = next((k for k, (label, _) in tinyfish_client.ERAKTKOSH_COMPONENT.items() if label == m.group(3)), "prbc")
    banks, error = tinyfish_client.validate_result(run.result)
    if banks:
        tinyfish_client._store(m.group(1), m.group(2), comp, banks, "live", run_id, None)
        stock_history.record(m.group(1), m.group(2), comp, banks, "batch")


SIGNAL_RE = {"dengue_news": re.compile(r"dengue|platelet", re.I), "accident_news": re.compile(r"accident|collapse|fire|blast|crash", re.I)}


@hooks.post("/webhooks/tinyfish/monitor")
async def tinyfish_monitor_hook(request: HttpRequest, key: str = ""):
    """Scheduled Monitor results -> news signals for the radar (titles and URLs only)."""
    _hook_key(key)
    body = await request.json()
    added = 0
    with session_scope() as db:
        for r in (body.get("results") or [])[:20]:
            text = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('text', '')[:500]}"
            for kind, rx in SIGNAL_RE.items():
                if rx.search(text):
                    district = next((d for _, d in forecast.districts(db) if d and re.search(rf"\b{re.escape(d)}\b", text, re.I)), "")
                    db.add(Signal(kind=kind, district=district, title=str(r.get("title", ""))[:300], url=str(r.get("url", ""))[:400], source="monitor"))
                    added += 1
    return {"ok": True, "signals": added}
