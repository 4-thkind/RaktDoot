"""Telegram donor registry + durable request alerts. Run ONE worker: python -m app.telegram"""
import hashlib
import logging
import os
import secrets
import time
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from .config import settings
from .db import Base, init_db, session_scope, utcnow
from .models import Request
from .api.auth import AuthUser, get_current_user
from .core.eligibility import questions
from .telegram_i18n import LANGUAGES, tr, question_text

log = logging.getLogger("telegram")
router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class TelegramDonor(Base):
    __tablename__ = "telegram_donors"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Donor")
    language: Mapped[str] = mapped_column(String(2), default="en")
    chat_id: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    token_expires: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)


class TelegramAlert(Base):
    __tablename__ = "telegram_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    retry_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("user_id", "request_id"),)


class TelegramCursor(Base):
    __tablename__ = "telegram_cursor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offset: Mapped[int] = mapped_column(Integer, default=0)


def configured():
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_BOT_USERNAME"):
        raise HTTPException(503, "Configure TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_USERNAME")


@router.post("/register")
def register(language: str = "", user: AuthUser = Depends(get_current_user)):
    # Registration is independent of notification consent or medical eligibility.
    with session_scope() as db:
        d = db.get(TelegramDonor, user.id)
        if not d:
            d = TelegramDonor(user_id=user.id, name=str(user.meta.get("name") or "Donor")[:80])
            db.add(d)
        selected = language if language in LANGUAGES else user.meta.get("language", "en")
        d.language = selected if selected in LANGUAGES else "en"
        db.flush()
        return {"registered": True, "connected": bool(d.chat_id), "active": d.active}


@router.post("/connect")
def connect(language: str = "", user: AuthUser = Depends(get_current_user)):
    configured()
    register(language=language, user=user)
    token = secrets.token_urlsafe(24)
    with session_scope() as db:
        d = db.get(TelegramDonor, user.id)
        d.token_hash = hashlib.sha256(token.encode()).hexdigest()
        d.token_expires = utcnow() + timedelta(minutes=15)
    username = os.environ["TELEGRAM_BOT_USERNAME"].strip().lstrip("@")
    return {"url": f"https://t.me/{username}?start={token}"}


class TelegramError(Exception):
    def __init__(self, code, retry=0):
        self.code, self.retry = code, retry


def call(method, **payload):
    # Never log the token-bearing URL or raw HTTP exception.
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
            json=payload, timeout=35,
        )
        data = response.json()
    except (httpx.HTTPError, ValueError):
        raise TelegramError(503) from None
    if not data.get("ok"):
        raise TelegramError(data.get("error_code", response.status_code), data.get("parameters", {}).get("retry_after", 0))
    return data["result"]


def say(chat, text):
    call("sendMessage", chat_id=chat, text=text)
    time.sleep(1.1)  # conservative per-chat limit; enough for a small demo


def handle_message(message):
    if message.get("chat", {}).get("type") != "private":
        return
    chat = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    if text.startswith("/start "):
        digest = hashlib.sha256(text.split(maxsplit=1)[1].encode()).hexdigest()
        with session_scope() as db:
            owner = db.scalar(select(TelegramDonor).where(TelegramDonor.chat_id == chat))
            d = db.scalar(select(TelegramDonor).where(TelegramDonor.token_hash == digest))
            if not d or not d.token_expires or d.token_expires < utcnow():
                reply = tr("invalid_link", d.language if d else "en")
            elif owner and owner.user_id != d.user_id:
                reply = tr("account_taken", d.language)
            elif d.chat_id and d.chat_id != chat:
                reply = tr("account_linked", d.language)
            else:
                d.chat_id, d.active, d.token_hash, d.token_expires = chat, True, None, None
                d.welcome_pending = True
                reply = None
        if reply is not None:
            say(chat, reply)
        return
    with session_scope() as db:
        d = db.scalar(select(TelegramDonor).where(TelegramDonor.chat_id == chat))
        lang = d.language if d else "en"
        if not d:
            reply = tr("notlinked", lang)
        elif text.lower() in ("/stop", "/resume"):
            d.active = text.lower() == "/resume"
            reply = tr("resumed" if d.active else "stopped", lang)
        elif not d.active:
            reply = tr("paused", lang)
        elif text.lower().startswith("/donate "):
            slug = text.split(maxsplit=1)[1]
            r = db.scalar(select(Request).where(Request.share_slug == slug))
            a = db.scalar(select(TelegramAlert).where(TelegramAlert.user_id == d.user_id, TelegramAlert.request_id == r.id)) if r else None
            if not a or r.status not in ("open", "dispatching", "needs_public_share") or (r.expires_at and r.expires_at <= utcnow()):
                reply = tr("no_request", lang)
            else:
                # One current screening per donor. Old answers never carry over.
                db.execute(update(TelegramAlert).where(TelegramAlert.user_id == d.user_id, TelegramAlert.status == "screening").values(status="sent"))
                a.status, a.answers = "screening", {}
                reply = tr("intro", lang) + "\n" + question_text(questions()[0], lang) + "\n" + tr("reply", lang)
        elif text.upper() in ("YES", "NO"):
            a = db.scalar(select(TelegramAlert).where(TelegramAlert.user_id == d.user_id, TelegramAlert.status == "screening"))
            r = db.get(Request, a.request_id) if a else None
            if not a or not r:
                reply = tr("first", lang)
            elif r.status not in ("open", "dispatching", "needs_public_share") or (r.expires_at and r.expires_at <= utcnow()):
                a.status = "closed"
                reply = tr("closed", lang)
            else:
                qs = questions()
                index = len(a.answers)
                answers = dict(a.answers)
                answers[qs[index]["id"]] = text.upper() == "YES"
                a.answers = answers
                if text.upper() == "YES":
                    a.status = "deferred"
                    reply = tr("deferred", lang)
                elif len(answers) < len(qs):
                    reply = question_text(qs[len(answers)], lang) + "\n" + tr("reply", lang)
                else:
                    a.status = "screened"
                    reply = tr("screened", lang, hospital=r.hospital_name, url=f"{settings.public_base_url.rstrip('/')}/r/{r.share_slug}")
        else:
            reply = tr("help", lang)
    say(chat, reply)



def deliver_welcomes():
    with session_scope() as db:
        ids = db.scalars(select(TelegramDonor.user_id).where(TelegramDonor.welcome_pending == True, TelegramDonor.active == True).limit(10)).all()
    for uid in ids:
        with session_scope() as db:
            d = db.get(TelegramDonor, uid)
            try:
                say(d.chat_id, tr("welcome", d.language, name=d.name))
                d.welcome_pending = False
            except TelegramError as exc:
                if exc.code == 403:
                    d.active = False
                else:
                    raise


def enqueue():
    with session_scope() as db:
        donors = db.scalars(select(TelegramDonor).where(TelegramDonor.active == True)).all()
        requests = db.scalars(select(Request).where(Request.status.in_(("open", "dispatching", "needs_public_share")))).all()
        for r in requests:
            if r.expires_at and r.expires_at <= utcnow():
                continue
            for d in donors:
                # Do not flood newly registered members with historical requests.
                if r.created_at < d.created_at:
                    continue
                existing = db.scalar(select(TelegramAlert.id).where(TelegramAlert.user_id == d.user_id, TelegramAlert.request_id == r.id))
                if not existing:
                    db.add(TelegramAlert(user_id=d.user_id, request_id=r.id))


def deliver():
    with session_scope() as db:
        ids = db.scalars(select(TelegramAlert.id).where(TelegramAlert.status == "pending", TelegramAlert.retry_at <= utcnow()).limit(10)).all()
    for aid in ids:
        with session_scope() as db:
            a = db.get(TelegramAlert, aid)
            d, r = db.get(TelegramDonor, a.user_id), db.get(Request, a.request_id)
            if not d or not d.active or not d.chat_id or not r or r.status not in ("open", "dispatching", "needs_public_share") or (r.expires_at and r.expires_at <= utcnow()):
                a.status = "skipped"
                continue
            a.attempts += 1
            try:
                say(d.chat_id, tr("alert", d.language, group=r.patient_group, component=r.component, units=r.units, hospital=r.hospital_name, slug=r.share_slug, url=f"{settings.public_base_url.rstrip('/')}/r/{r.share_slug}"))
                a.status = "sent"
            except TelegramError as exc:
                if exc.code == 403:
                    d.active, a.status = False, "blocked"
                elif a.attempts >= 8:
                    a.status = "failed"
                    log.warning("Alert %s failed after 8 attempts", aid)
                else:
                    a.retry_at = utcnow() + timedelta(seconds=max(exc.retry, min(300, 2 ** a.attempts)))
                if exc.code == 429:
                    time.sleep(min(30, max(1, exc.retry)))
                    break


def run():
    configured()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    init_db()
    with session_scope() as db:
        if not db.get(TelegramCursor, 1):
            db.add(TelegramCursor(id=1, offset=0))
    log.info("Telegram worker running. Use only one worker per bot.")
    while True:
        try:
            with session_scope() as db:
                offset = db.get(TelegramCursor, 1).offset
            updates = call("getUpdates", offset=offset, timeout=5, limit=20, allowed_updates=["message"])
            for item in updates:
                # Commands are processed in order. Commit cursor after successful handling.
                handle_message(item.get("message", {}))
                with session_scope() as db:
                    db.get(TelegramCursor, 1).offset = item["update_id"] + 1
            deliver_welcomes()
            enqueue()
            deliver()
        except TelegramError as exc:
            log.warning("Telegram error code %s (409 means another poller or webhook is active)", exc.code)
            time.sleep(min(30, max(3, exc.retry)))
        except IntegrityError:
            log.warning("Database conflict; retrying. Ensure only one worker is running.")
            time.sleep(3)
        except Exception as exc:
            log.warning("Worker error type: %s", type(exc).__name__)
            time.sleep(3)


if __name__ == "__main__":
    run()
