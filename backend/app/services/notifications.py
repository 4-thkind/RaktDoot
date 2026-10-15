"""Send WhatsApp messages to website users (a Supabase login + its Profile row).

This is the reusable entry point for the WhatsApp integration. Today it is used for the
signup welcome. Later features (request updates, password reset codes, ...) should call
`notify_user()` with a new message key instead of talking to whatsapp.send() directly, so
consent and failure handling stay in one place.

To add a new message:
  1. add its text (en + hi) to TEXT and, if it is business-initiated, to TEMPLATES in messages.py
  2. register the template in Meta (see docs/whatsapp-templates.md)
  3. call notify_user(db, user, "<key>", **params)
"""
import logging

from sqlalchemy.orm import Session

from ..db import session_scope, utcnow
from ..models import Profile
from . import whatsapp
from .messages import TEMPLATES, t

log = logging.getLogger("raktdoot.notifications")


def notify_user(db: Session, user: Profile, key: str, **params) -> bool:
    """Send message `key` to the user's WhatsApp. Returns True if it was handed to the channel.
    Never raises: a WhatsApp problem must not break signup or any other request."""
    if not user.whatsapp_consent:
        return False
    try:
        text = t(key, user.language, **params)
        template = (key, params, user.language) if key in TEMPLATES else None
        msg = whatsapp.send(db, user.phone, text, template=template)
        return "error" not in (msg.payload or {})
    except Exception as e:  # noqa: BLE001
        log.warning("notify_user(%s) failed for user %s: %s", key, user.id, e)
        return False


def send_signup_welcome(user_id: str) -> None:
    """Runs in a background task after signup, with its own DB session."""
    with session_scope() as db:
        user = db.get(Profile, user_id)
        if user is None:
            return
        if not user.whatsapp_consent:
            user.whatsapp_welcome_status = "skipped"
            return
        ok = notify_user(db, user, "account_welcome", name=user.name)
        user.whatsapp_welcome_status = "sent" if ok else "failed"
        if ok:
            user.whatsapp_welcomed_at = utcnow()