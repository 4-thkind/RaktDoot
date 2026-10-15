"""Outbound WhatsApp. One interface, three channels:

- cloud:  Meta WhatsApp Business Cloud API (interactive buttons, templates, locations)
- twilio: Twilio WhatsApp sandbox (plain text; buttons become "Reply 1 / Reply 2")
- mock:   nothing leaves the server; the web simulator at /simulator plays the donor's phone

Every message in either direction is logged in chat_messages."""
import base64
import hashlib
import hmac
import logging
import re
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import ChatMessage, Conversation
from ..seed import SYNTHETIC_PREFIX
from .messages import TEMPLATES

log = logging.getLogger("raktdoot.whatsapp")
GRAPH = "https://graph.facebook.com/v21.0"


def normalize_phone(raw: str) -> str | None:
    """Return digits-only E.164 (e.g. 919812345678). Bare 10-digit numbers are taken as Indian."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        digits = "91" + digits
    if 11 <= len(digits) <= 15:
        return digits
    return None


def conversation(db: Session, phone: str) -> Conversation:
    conv = db.get(Conversation, phone)
    if conv is None:
        conv = Conversation(phone=phone, state="idle", data={}, last_buttons=[])
        db.add(conv)
        db.flush()
    return conv


def in_service_window(db: Session, phone: str) -> bool:
    conv = db.get(Conversation, phone)
    return bool(conv and conv.last_inbound_at and utcnow() - conv.last_inbound_at < timedelta(hours=23, minutes=50))


def send(
    db: Session,
    phone: str,
    text: str,
    *,
    buttons: list[tuple[str, str]] | None = None,
    rows: list[tuple[str, str]] | None = None,
    list_button: str = "Choose",
    location: dict | None = None,
    template: tuple[str, dict, str] | None = None,
) -> ChatMessage:
    """Send one message. `template` = (message key, params, lang) is used by the cloud channel
    when the donor is outside the 24-hour service window."""
    options = buttons or rows or []
    kind = "location" if location else "buttons" if buttons else "list" if rows else "text"
    payload: dict = {}
    if options:
        payload["options"] = [{"id": i, "title": title} for i, title in options]
        conv = conversation(db, phone)
        conv.last_buttons = [i for i, _ in options]
    if location:
        payload["location"] = location

    wa_id, error = None, None
    mode = settings.whatsapp_mode
    if mode != "mock" and phone.startswith(SYNTHETIC_PREFIX):
        mode = "mock"  # synthetic seed donors are never messaged on a real channel
        payload["skipped"] = "synthetic donor"
    try:
        if mode == "cloud":
            wa_id = _send_cloud(db, phone, text, kind, buttons, rows, list_button, location, template)
        elif mode == "twilio":
            wa_id = _send_twilio(phone, text, options, location)
    except Exception as e:  # a failed send must never break the request flow
        error = str(e)[:300]
        log.warning("whatsapp send to %s failed: %s", phone, error)
    if error:
        payload["error"] = error

    msg = ChatMessage(phone=phone, direction="out", kind=kind, body=text, payload=payload, wa_message_id=wa_id)
    db.add(msg)
    db.flush()
    return msg


def log_inbound(db: Session, phone: str, text: str, payload: dict | None = None, wa_id: str | None = None) -> None:
    db.add(ChatMessage(phone=phone, direction="in", kind="text", body=text, payload=payload or {}, wa_message_id=wa_id))
    conv = conversation(db, phone)
    conv.last_inbound_at = utcnow()


# ---------------------------------------------------------------- cloud
def _cloud_post(body: dict) -> str | None:
    if not (settings.whatsapp_token and settings.whatsapp_phone_number_id):
        raise RuntimeError("WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set")
    r = httpx.post(
        f"{GRAPH}/{settings.whatsapp_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
        json={"messaging_product": "whatsapp", **body},
        timeout=15,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"cloud api {r.status_code}: {r.text[:200]}")
    msgs = r.json().get("messages") or [{}]
    return msgs[0].get("id")


def _send_cloud(db, phone, text, kind, buttons, rows, list_button, location, template) -> str | None:
    if template and not in_service_window(db, phone):
        key, params, lang = template
        name, order = TEMPLATES[key]
        components: list[dict] = [{"type": "body", "parameters": [{"type": "text", "text": str(params[k])} for k in order]}]
        for idx, (bid, _title) in enumerate(buttons or []):
            components.append({"type": "button", "sub_type": "quick_reply", "index": str(idx), "parameters": [{"type": "payload", "payload": bid}]})
        code = settings.whatsapp_template_lang if lang == "en" else lang
        return _cloud_post({"to": phone, "type": "template", "template": {"name": name, "language": {"code": code}, "components": components}})
    if kind == "location":
        return _cloud_post({"to": phone, "type": "location", "location": {
            "latitude": location["lat"], "longitude": location["lng"], "name": location.get("name", ""), "address": location.get("address", "")}})
    if kind == "buttons":
        return _cloud_post({"to": phone, "type": "interactive", "interactive": {
            "type": "button", "body": {"text": text[:1024]},
            "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}} for i, t in buttons[:3]]}}})
    if kind == "list":
        return _cloud_post({"to": phone, "type": "interactive", "interactive": {
            "type": "list", "body": {"text": text[:1024]},
            "action": {"button": list_button[:20], "sections": [{"title": list_button[:24], "rows": [{"id": i, "title": t[:24]} for i, t in rows[:10]]}]}}})
    return _cloud_post({"to": phone, "type": "text", "text": {"body": text[:4096]}})


def verify_cloud_signature(raw_body: bytes, header: str | None) -> bool:
    if not settings.whatsapp_app_secret:
        return False
    expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return bool(header) and hmac.compare_digest(expected, header)


# ---------------------------------------------------------------- twilio
def _send_twilio(phone: str, text: str, options: list[tuple[str, str]], location: dict | None) -> str | None:
    if not (settings.twilio_account_sid and settings.twilio_auth_token):
        raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set")
    body = text
    if options:
        body += "\n\n" + "\n".join(f"Reply {n}: {title}" for n, (_i, title) in enumerate(options, 1))
    if location:
        body += f"\nhttps://maps.google.com/?q={location['lat']},{location['lng']}"
    r = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        data={"From": settings.twilio_from, "To": f"whatsapp:+{phone}", "Body": body[:1600]},
        timeout=15,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"twilio {r.status_code}: {r.text[:200]}")
    return r.json().get("sid")


def verify_twilio_signature(url: str, form: dict, header: str | None) -> bool:
    if not settings.twilio_auth_token or not header:
        return False
    data = url + "".join(k + form[k] for k in sorted(form))
    digest = base64.b64encode(hmac.new(settings.twilio_auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(digest, header)


def click_to_chat_link(text: str = "JOIN") -> str:
    return f"https://wa.me/{settings.whatsapp_business_number}?{urlencode({'text': text})}"
