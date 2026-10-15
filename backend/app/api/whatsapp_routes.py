"""Inbound WhatsApp: Meta Cloud API webhook, Twilio webhook, and the mock channel used by
the web simulator. All three end in bot.handle_inbound()."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db, session_scope, utcnow
from ..models import ChatMessage, Donor, Notification
from ..services import bot, whatsapp
from .common import iso

router = APIRouter()
log = logging.getLogger("raktdoot.webhooks")


# ------------------------------------------------------------------ Meta Cloud API
@router.get("/webhooks/whatsapp")
def verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
           challenge: str = Query("", alias="hub.challenge")):
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return PlainTextResponse(challenge)
    raise HTTPException(403, "verification failed")


@router.post("/webhooks/whatsapp")
async def cloud_inbound(request: Request):
    raw = await request.body()
    if not whatsapp.verify_cloud_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(401, "bad signature")
    data = json.loads(raw or b"{}")
    with session_scope() as db:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for st in value.get("statuses", []):
                    _status(db, st.get("id"), st.get("status"))
                for m in value.get("messages", []):
                    phone, kind = m.get("from"), m.get("type")
                    text, button, loc = "", None, None
                    if kind == "text":
                        text = m["text"].get("body", "")
                    elif kind == "interactive":
                        it = m["interactive"]
                        button = (it.get("button_reply") or it.get("list_reply") or {}).get("id")
                    elif kind == "button":  # quick reply on a template
                        button = m["button"].get("payload")
                        text = m["button"].get("text", "")
                    elif kind == "location":
                        loc = {"lat": m["location"]["latitude"], "lng": m["location"]["longitude"], "name": m["location"].get("name")}
                    if phone:
                        bot.handle_inbound(db, phone, text, button, loc, m.get("id"))
    return {"ok": True}


def _status(db: Session, wa_id: str | None, status: str | None) -> None:
    if not wa_id:
        return
    n = db.scalar(select(Notification).where(Notification.wa_message_id == wa_id))
    if not n:
        return
    if status == "delivered" and not n.delivered_at:
        n.delivered_at = utcnow()
        if n.status == "sent":
            n.status = "delivered"
    elif status == "read":
        n.read_at = n.read_at or utcnow()
        n.delivered_at = n.delivered_at or n.read_at
        if n.status in ("sent", "delivered"):
            n.status = "read"


# ------------------------------------------------------------------ Twilio sandbox
@router.post("/webhooks/twilio")
async def twilio_inbound(request: Request):
    form = {k: str(v) for k, v in (await request.form()).items()}
    url = settings.twilio_webhook_url or str(request.url)  # must be the exact URL Twilio calls
    if not whatsapp.verify_twilio_signature(url, form, request.headers.get("X-Twilio-Signature")):
        raise HTTPException(401, "bad signature")
    phone = whatsapp.normalize_phone(form.get("From", "").replace("whatsapp:", ""))
    loc = None
    if form.get("Latitude") and form.get("Longitude"):
        loc = {"lat": float(form["Latitude"]), "lng": float(form["Longitude"]), "name": form.get("Address")}
    if phone:
        with session_scope() as db:
            bot.handle_inbound(db, phone, form.get("Body", ""), form.get("ButtonPayload") or None, loc, form.get("MessageSid"))
    return PlainTextResponse("<Response></Response>", media_type="application/xml")


# ------------------------------------------------------------------ mock channel (simulator)
def mock_only() -> None:
    if settings.whatsapp_mode != "mock":
        raise HTTPException(404, "The simulator is only available when WHATSAPP_MODE=mock")


class MockInbound(BaseModel):
    phone: str
    text: str = Field(default="", max_length=1000)
    button_id: str | None = Field(default=None, max_length=120)
    lat: float | None = None
    lng: float | None = None


@router.get("/api/mock/chats", dependencies=[Depends(mock_only)])
def mock_chats(q: str = "", group: str = "", limit: int = Query(40, le=200), db: Session = Depends(get_db)):
    """Phones for the simulator: anyone with messages first (newest first), then other donors."""
    last = select(ChatMessage.phone, func.max(ChatMessage.id).label("mid")).group_by(ChatMessage.phone).subquery()
    rows = db.execute(select(ChatMessage).join(last, ChatMessage.id == last.c.mid).order_by(ChatMessage.id.desc())).scalars().all()
    donors = {d.phone: d for d in db.scalars(select(Donor)).all()}
    out, seen = [], set()

    def add(phone: str, msg: ChatMessage | None):
        d = donors.get(phone)
        if q and q.lower() not in ((d.name if d else "") + phone).lower():
            return
        if group and (not d or d.blood_group != group):
            return
        out.append({"phone": phone, "name": d.name if d else None, "group": d.blood_group if d else None,
                    "location": d.location_label if d else None,
                    "last": msg.body[:90] if msg else None, "last_at": iso(msg.created_at) if msg else None,
                    "last_direction": msg.direction if msg else None})
        seen.add(phone)

    for m in rows:
        add(m.phone, m)
    for phone in donors:
        if phone not in seen and len(out) < limit:
            add(phone, None)
    return out[:limit]


@router.get("/api/mock/chats/{phone}", dependencies=[Depends(mock_only)])
def mock_chat(phone: str, db: Session = Depends(get_db)):
    msgs = db.scalars(select(ChatMessage).where(ChatMessage.phone == phone).order_by(ChatMessage.id)).all()
    # opening the chat counts as reading the alert, like blue ticks
    for n in db.scalars(select(Notification).join(Donor).where(Donor.phone == phone, Notification.status.in_(("sent", "delivered")))).all():
        n.read_at, n.status = utcnow(), "read"
        n.delivered_at = n.delivered_at or n.read_at
    db.commit()
    d = db.scalar(select(Donor).where(Donor.phone == phone))
    return {
        "phone": phone,
        "donor": {"name": d.name, "group": d.blood_group, "language": d.language, "location": d.location_label,
                  "last_donation_date": d.last_donation_date.isoformat() if d.last_donation_date else None,
                  "opted_out": d.opted_out} if d else None,
        "messages": [{"id": m.id, "direction": m.direction, "kind": m.kind, "body": m.body,
                      "options": m.payload.get("options"), "location": m.payload.get("location"),
                      "at": iso(m.created_at)} for m in msgs],
    }


@router.post("/api/mock/inbound", dependencies=[Depends(mock_only)])
def mock_inbound(body: MockInbound, db: Session = Depends(get_db)):
    phone = body.phone if body.phone.isdigit() and len(body.phone) >= 11 else whatsapp.normalize_phone(body.phone)
    if not phone:
        raise HTTPException(422, "invalid phone")
    loc = {"lat": body.lat, "lng": body.lng, "name": "Shared location"} if body.lat is not None and body.lng is not None else None
    bot.handle_inbound(db, phone, body.text, body.button_id, loc)
    db.commit()
    return mock_chat(phone, db)
