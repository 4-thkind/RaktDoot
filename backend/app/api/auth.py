"""Auth with Supabase.

Supabase does signup, login, passwords and sessions. This backend only:
  - verifies the Supabase access token sent by the browser (get_current_user)
  - sends the WhatsApp welcome once per account (POST /api/auth/welcome)
"""
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Profile
from ..services.notifications import send_signup_welcome
from ..services.whatsapp import normalize_phone

router = APIRouter(prefix="/api/auth", tags=["auth"])


@dataclass
class AuthUser:
    id: str
    email: str
    meta: dict  # Supabase user_metadata (set at signup: name, phone, language, whatsapp_consent)


def supabase_user(token: str) -> dict | None:
    """Ask Supabase who this access token belongs to. Works for any signing-key type."""
    if not (settings.supabase_url and settings.supabase_anon_key):
        raise HTTPException(503, "Supabase is not configured (SUPABASE_URL / SUPABASE_ANON_KEY)")
    try:
        r = httpx.get(f"{settings.supabase_url}/auth/v1/user", timeout=10,
                      headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key})
    except httpx.HTTPError:
        raise HTTPException(503, "Could not reach Supabase")
    return r.json() if r.status_code == 200 else None


def get_current_user(authorization: str = Header(default="")) -> AuthUser:
    """Dependency for any route that needs a logged-in user."""
    scheme, _, token = authorization.partition(" ")
    data = supabase_user(token) if scheme.lower() == "bearer" and token else None
    if not data or not data.get("id"):
        raise HTTPException(401, "Please log in")
    return AuthUser(id=data["id"], email=data.get("email") or "", meta=data.get("user_metadata") or {})


def profile_json(user: AuthUser, p: Profile | None) -> dict:
    return {"id": user.id, "email": user.email, "name": p.name if p else user.meta.get("name"),
            "phone": p.phone if p else None, "whatsapp_consent": p.whatsapp_consent if p else False,
            "whatsapp_welcome": p.whatsapp_welcome_status if p else None}


@router.post("/welcome")
def welcome(background: BackgroundTasks, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Called by the frontend after signup / login. Safe to call many times: the welcome is sent once."""
    existing = db.get(Profile, user.id)
    if existing and existing.whatsapp_welcome_status != "failed":
        return {"whatsapp_welcome": existing.whatsapp_welcome_status}  # already handled
    phone = normalize_phone(str(user.meta.get("phone") or ""))
    if not phone:
        raise HTTPException(422, "No valid WhatsApp number on this account")
    consent = user.meta.get("whatsapp_consent") is True
    lang = user.meta.get("language")
    p = existing or Profile(id=user.id)
    p.name = str(user.meta.get("name") or "")[:80]
    p.phone = phone
    p.language = lang if lang in ("en", "hi") else "en"
    p.whatsapp_consent = consent
    p.whatsapp_welcome_status = "pending" if consent else "skipped"
    db.add(p)
    db.commit()
    if consent:
        background.add_task(send_signup_welcome, p.id)  # after the response: never waits on WhatsApp
    return {"whatsapp_welcome": p.whatsapp_welcome_status}


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"user": profile_json(user, db.get(Profile, user.id))}