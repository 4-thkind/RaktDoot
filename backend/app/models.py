"""Database tables. Locations are plain lat/lng floats with an index, so the same schema
runs on SQLite (local dev) and Postgres (deploy). See README for the PostGIS upgrade path."""
import secrets
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text
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
    donations_verified: Mapped[int] = mapped_column(Integer, default=0)  # confirmed from a donor-card photo (F9)
    recurring_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)  # willing to join a thalassemia rota (F7)
    voice_replies: Mapped[bool] = mapped_column(Boolean, default=False)  # also send bot messages as voice notes (TTS)
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
    hospital_check: Mapped[dict] = mapped_column(JSON, default=dict)  # score + evidence from TinyFish Search / directory
    component: Mapped[str] = mapped_column(String(16), default="prbc")  # prbc | platelets | plasma | whole_blood
    kind: Mapped[str] = mapped_column(String(12), default="emergency")  # emergency | drive | recurring
    allow_o_neg: Mapped[bool] = mapped_column(Boolean, default=False)  # O- donors held in reserve until allowed
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
    variant: Mapped[str] = mapped_column(String(16), default="standard")  # alert wording arm (F11)
    segment: Mapped[str] = mapped_column(String(24), default="all")
    reason: Mapped[str] = mapped_column(String(200), default="")  # "why you" line (F12)
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
    eraktkosh_code: Mapped[str | None] = mapped_column(String(16), nullable=True)  # hospitalCode on eRaktKosh
    geo_quality: Mapped[str] = mapped_column(String(16), default="approximate")  # geocoded | approximate | district


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


# ---------------------------------------------------------------- TinyFish: Sense / Verify / Act / Learn
class TinyFishRun(Base):
    """Telemetry for every TinyFish call (W6): what ran, how long, which path served it."""
    __tablename__ = "tinyfish_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16))  # agent | replay | search | fetch | batch | monitor
    purpose: Mapped[str] = mapped_column(String(60), default="")
    source: Mapped[str] = mapped_column(String(40), default="eraktkosh")
    target: Mapped[str] = mapped_column(String(160), default="")  # e.g. "Delhi/South/prbc"
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | failed
    run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Recipe(Base):
    """A learned, replayable path through a site (Section 2.4). Versioned; the newest active one is used."""
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    learned: Mapped[dict] = mapped_column(JSON, default=dict)  # option codes the Agent reported (state/district/component)
    created_from_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    verify_ok: Mapped[int] = mapped_column(Integer, default=0)
    verify_mismatch: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StockHistory(Base):
    """Append-only stock snapshots (S1). Feeds the Shortage Radar (F1)."""
    __tablename__ = "stock_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(80))
    district: Mapped[str] = mapped_column(String(80))
    component: Mapped[str] = mapped_column(String(16))
    bank_name: Mapped[str] = mapped_column(String(200))
    blood_group: Mapped[str] = mapped_column(String(3))
    units: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # agent | replay | batch | synthetic
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_hist_series", "district", "component", "blood_group", "observed_at"),)


class Camp(Base):
    """Upcoming blood donation camps from eRaktKosh (A1). No organiser names or phone numbers are stored."""
    __tablename__ = "camps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    external_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    camp_date: Mapped[date] = mapped_column(Date, index=True)
    time_text: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300), default="")
    district: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(80), default="")
    organiser: Mapped[str] = mapped_column(String(200), default="")  # the blood centre running it
    register_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="eraktkosh")  # eraktkosh | sample
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Forward(Base):
    """Forwarded blood pleas we have checked (F2). Text and phone are stored as hashes only."""
    __tablename__ = "forwards"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    text_hash: Mapped[str] = mapped_column(String(64), index=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reporter_hash: Mapped[str] = mapped_column(String(64), default="")
    fields: Mapped[dict] = mapped_column(JSON, default=dict)  # extracted fields, phone masked
    verdict: Mapped[str] = mapped_column(String(20))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DispatchDecision(Base):
    """One step of the agentic dispatcher (F5): state seen, action chosen, why."""
    __tablename__ = "dispatch_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    engine: Mapped[str] = mapped_column(String(12))  # llm | rules | fallback
    action: Mapped[str] = mapped_column(String(32))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(String(300), default="")
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BanditArm(Base):
    """Beta-Bernoulli posterior for one alert wording in one donor segment (F11)."""
    __tablename__ = "bandit_arms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant: Mapped[str] = mapped_column(String(16))
    segment: Mapped[str] = mapped_column(String(24), default="all")
    alpha: Mapped[float] = mapped_column(Float, default=1.0)
    beta: Mapped[float] = mapped_column(Float, default=1.0)
    pulls: Mapped[int] = mapped_column(Integer, default=0)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    history: Mapped[list] = mapped_column(JSON, default=list)  # [pulls, posterior mean] points for the admin chart

    __table_args__ = (Index("ix_arm", "variant", "segment", "simulated", unique=True),)


class RecurringNeed(Base):
    """A patient who needs transfusions on a schedule, e.g. thalassemia (F7)."""
    __tablename__ = "recurring_needs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    manage_token: Mapped[str] = mapped_column(String(64), default=lambda: secrets.token_urlsafe(24))
    patient_label: Mapped[str] = mapped_column(String(80))  # a nickname, not the full name
    patient_group: Mapped[str] = mapped_column(String(3))
    component: Mapped[str] = mapped_column(String(16), default="prbc")
    units: Mapped[int] = mapped_column(Integer, default=1)
    interval_days: Mapped[int] = mapped_column(Integer, default=21)
    next_due: Mapped[date] = mapped_column(Date)
    hospital_name: Mapped[str] = mapped_column(String(200))
    hospital_lat: Mapped[float] = mapped_column(Float)
    hospital_lng: Mapped[float] = mapped_column(Float)
    requester_name: Mapped[str] = mapped_column(String(80))
    requester_phone: Mapped[str] = mapped_column(String(20))
    max_km: Mapped[float] = mapped_column(Float, default=15)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecurringSlot(Base):
    __tablename__ = "recurring_slots"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    need_id: Mapped[str] = mapped_column(ForeignKey("recurring_needs.id", ondelete="CASCADE"), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    donor_id: Mapped[str | None] = mapped_column(ForeignKey("donors.id", ondelete="SET NULL"), nullable=True)
    # planned | reminded | confirmed | declined | done | unfilled
    status: Mapped[str] = mapped_column(String(12), default="planned")
    request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    donor: Mapped[Donor | None] = relationship()


class GuideChunk(Base):
    """Family guide knowledge base (F13): passages from official documents with their source URL."""
    __tablename__ = "guide_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_title: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(400))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fetched_via: Mapped[str] = mapped_column(String(20), default="snapshot")  # snapshot | tinyfish_fetch
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MediaFile(Base):
    """Generated voice replies (TTS), served at /api/media/{id} and pruned after a week."""
    __tablename__ = "media_files"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    mime: Mapped[str] = mapped_column(String(40))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    engine: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class CampRegistration(Base):
    """A donor's camp sign-up done for them on the camp portal (A2). Aadhaar is never stored here."""
    __tablename__ = "camp_registrations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    camp_id: Mapped[str] = mapped_column(String(32), index=True)
    donor_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    portal_session: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="started")  # started | otp_sent | registered | failed
    portal_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)
    engine: Mapped[str] = mapped_column(String(24), default="form_filler")  # form_filler | tinyfish_agent
    steps: Mapped[list] = mapped_column(JSON, default=list)  # what the automation did, for the demo log
    error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MockPortalEntry(Base):
    """State of the MOCK camp portal (stands in for a government sign-up form with captcha, OTP and
    Aadhaar). Synthetic data only; Aadhaar is kept as its last 4 digits."""
    __tablename__ = "mock_portal_entries"
    session: Mapped[str] = mapped_column(String(64), primary_key=True)
    camp_id: Mapped[str] = mapped_column(String(32))
    captcha_answer: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(80), default="")
    mobile: Mapped[str] = mapped_column(String(20), default="")
    aadhaar_last4: Mapped[str] = mapped_column(String(4), default="")
    blood_group: Mapped[str] = mapped_column(String(3), default="")
    otp: Mapped[str] = mapped_column(String(6), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    registration_no: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Signal(Base):
    """External signals for the forecaster, e.g. TinyFish Monitor / Search news hits (F1)."""
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(24))  # dengue_news | accident_news | festival
    district: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(400), default="")
    source: Mapped[str] = mapped_column(String(20), default="search")  # search | monitor
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
