"""Database tables. Locations are plain lat/lng floats with an index, so the same schema
runs on SQLite (local dev) and Postgres (deploy). See README for the PostGIS upgrade path."""
import secrets
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


def _id() -> str:
    return uuid.uuid4().hex


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Supabase user id
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_welcome_status: Mapped[str] = mapped_column(String(10), default="pending")
    whatsapp_welcomed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Donor(Base):
    __tablename__ = "donors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # E.164 without '+', e.g. 919812345678
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    gender: Mapped[str] = mapped_column(String(1))  # M | F | O
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    night_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    last_donation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eligible_again_notified: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_alerted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alerts_sent: Mapped[int] = mapped_column(Integer, default=0)
    alerts_responded: Mapped[int] = mapped_column(Integer, default=0)
    alerts_accepted: Mapped[int] = mapped_column(Integer, default=0)
    no_shows: Mapped[int] = mapped_column(Integer, default=0)
    donations_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    reply_hours: Mapped[list] = mapped_column(JSON, default=list)  # local hours of past replies, for time-of-day fit
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_donor_latlng", "lat", "lng"),)


class Request(Base):
    __tablename__ = "requests"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    manage_token: Mapped[str] = mapped_column(String(64), default=lambda: secrets.token_urlsafe(24))
    share_slug: Mapped[str] = mapped_column(String(16), unique=True, default=lambda: secrets.token_urlsafe(8))
    patient_group: Mapped[str] = mapped_column(String(3))
    group_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    units: Mapped[int] = mapped_column(Integer)
    patient_age: Mapped[int] = mapped_column(Integer)
    patient_gender: Mapped[str] = mapped_column(String(1))
    hospital_name: Mapped[str] = mapped_column(String(200))
    hospital_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    hospital_lat: Mapped[float] = mapped_column(Float)
    hospital_lng: Mapped[float] = mapped_column(Float)
    hospital_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    requester_name: Mapped[str] = mapped_column(String(80))
    requester_phone: Mapped[str] = mapped_column(String(20), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    # open | dispatching | matched | needs_public_share | fulfilled | expired | cancelled
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    wave: Mapped[int] = mapped_column(Integer, default=0)
    radius_km: Mapped[float] = mapped_column(Float, default=0)
    target_acceptances: Mapped[int] = mapped_column(Integer, default=2)
    next_wave_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_acceptance_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notifications: Mapped[list["Notification"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class Notification(Base):
    """One donor alerted for one request."""
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    donor_id: Mapped[str] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), index=True)
    wave: Mapped[int] = mapped_column(Integer)
    # sent | delivered | read | accepted | declined | ineligible | connected | donated | no_show | cancelled
    status: Mapped[str] = mapped_column(String(16), default="sent", index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    distance_km: Mapped[float] = mapped_column(Float, default=0)
    features: Mapped[dict] = mapped_column(JSON, default=dict)  # logged for the future ML ranker
    eligibility_answers: Mapped[dict] = mapped_column(JSON, default=dict)
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wa_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    onway_asked: Mapped[bool] = mapped_column(Boolean, default=False)
    followup_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    request: Mapped[Request] = relationship(back_populates="notifications")
    donor: Mapped[Donor] = relationship()


class Donation(Base):
    __tablename__ = "donations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    donor_id: Mapped[str] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id", ondelete="SET NULL"), nullable=True)
    donated_on: Mapped[date] = mapped_column(Date)
    confirmed_by: Mapped[str] = mapped_column(String(16), default="donor")


class BloodBank(Base):
    __tablename__ = "blood_banks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    district: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(80))
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="seed")


class StockCache(Base):
    __tablename__ = "stock_cache"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    state: Mapped[str] = mapped_column(String(80))
    district: Mapped[str] = mapped_column(String(80))
    component: Mapped[str] = mapped_column(String(60))
    results: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(16))  # live | demo
    source_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    streaming_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_stock_key", "state", "district", "component", unique=True),)


class Conversation(Base):
    """WhatsApp bot state per phone number (donor or someone onboarding)."""
    __tablename__ = "conversations"
    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    state: Mapped[str] = mapped_column(String(40), default="idle")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    last_buttons: Mapped[list] = mapped_column(JSON, default=list)  # ids of the last buttons sent, so "1"/"2" replies work
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # opens the 24 h service window
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ChatMessage(Base):
    """Log of every message in and out. In mock mode this is the whole WhatsApp channel."""
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(3))  # out | in
    kind: Mapped[str] = mapped_column(String(16))  # text | buttons | list | location | template
    body: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    wa_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
