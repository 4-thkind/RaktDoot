"""Wave dispatch: notify a few well-ranked donors, wait, widen the radius, stop as soon as
enough donors are connected, and tell everyone still pending that they are not needed."""
import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core import eligibility, explain, ranking
from ..core.compatibility import compatible_donors, normalize_component
from ..core.geo import bbox, haversine_km
from ..db import utcnow
from ..models import Donor, Notification, Request
from . import bandit, whatsapp
from .messages import GENDER_WORD, b, component_word, t

PENDING = ("sent", "delivered", "read")
CONNECTED = ("connected", "donated", "deferred")
ACTIVE_REQUEST = ("dispatching", "matched", "needs_public_share")
QUIET_START, QUIET_END = 23, 7


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def local_today() -> date:
    return local_now().date()


def in_quiet_hours(hour: int) -> bool:
    return hour >= QUIET_START or hour < QUIET_END


def find_candidates(db: Session, req: Request, radius_km: float, now: datetime | None = None, local_hour: int | None = None) -> list[dict]:
    """Compatible, consenting, eligible-today donors within radius, best first.
    Rest period, pause, opt-out and the 24 h alert limit are enforced in SQL, so a donor in
    their rest period cannot be selected even by mistake."""
    now = now or utcnow()
    today = local_today()
    local_hour = local_now().hour if local_hour is None else local_hour
    lat0, lat1, lng0, lng1 = bbox(req.hospital_lat, req.hospital_lng, radius_km)
    rest_m = today - timedelta(days=eligibility.rest_days("M"))
    rest_f = today - timedelta(days=eligibility.rest_days("F"))
    already = select(Notification.donor_id).where(Notification.request_id == req.id)
    component = normalize_component(req.component)
    groups = compatible_donors(req.patient_group, component)
    if o_neg_reserved(req):
        groups = [g for g in groups if g != "O-"]

    q = select(Donor).where(
        Donor.blood_group.in_(groups),
        Donor.consent.is_(True),
        Donor.opted_out.is_(False),
        Donor.weight_ok.is_(True),
        Donor.lat.between(lat0, lat1),
        Donor.lng.between(lng0, lng1),
        Donor.phone != req.requester_phone,
        Donor.id.not_in(already),
        or_(Donor.paused_until.is_(None), Donor.paused_until < now),
        or_(Donor.last_alerted_at.is_(None), Donor.last_alerted_at < now - timedelta(hours=24)),
        or_(
            Donor.last_donation_date.is_(None),
            and_(Donor.gender == "M", Donor.last_donation_date <= rest_m),
            and_(Donor.gender != "M", Donor.last_donation_date <= rest_f),
        ),
    )
    if settings.respect_quiet_hours and in_quiet_hours(local_hour):
        q = q.where(Donor.night_ok.is_(True))

    max_radius = max(settings.wave_radii_km)
    out = []
    for d in db.scalars(q).all():
        if not eligibility.age_ok(d.dob, today):
            continue
        dist = haversine_km(req.hospital_lat, req.hospital_lng, d.lat, d.lng)
        if dist > radius_km:
            continue
        feats = ranking.features(d, req.patient_group, dist, max_radius, local_hour, now, component)
        out.append({"donor": d, "distance_km": round(dist, 2), "features": feats, "score": ranking.score(feats)})
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def o_neg_reserved(req: Request) -> bool:
    """O- red cells suit every patient, so O- donors are held back until the request allows them
    (wave 3+, scarce groups, or an unconfirmed group; see dispatch_agent)."""
    return normalize_component(req.component) in ("prbc", "whole_blood") and req.patient_group != "O-" and not req.allow_o_neg


def alerts_left(db: Session, req: Request, now: datetime | None = None) -> int:
    """Hard caps per request: total alerts, and alerts in the last hour."""
    now = now or utcnow()
    total = db.scalar(select(func.count()).select_from(Notification).where(Notification.request_id == req.id)) or 0
    hour = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.request_id == req.id, Notification.sent_at > now - timedelta(hours=1))) or 0
    return max(0, min(settings.max_alerts_per_request - total, settings.max_alerts_per_hour - hour))


def pick_wave(cands: list[dict], size: int, seed: str) -> list[dict]:
    """Top-ranked donors, plus one lower-ranked donor for exploration so new donors build a history."""
    if len(cands) <= size:
        return cands
    explore = 1 if size >= 4 else 0
    chosen = cands[: size - explore]
    rng = random.Random(seed)
    chosen += rng.sample(cands[size - explore:], explore)
    return chosen


def connected_count(db: Session, req: Request) -> int:
    return db.scalar(select(func.count()).select_from(Notification).where(Notification.request_id == req.id, Notification.status.in_(CONNECTED))) or 0


def alert_params(req: Request, donor: Donor, distance_km: float, reason: str = "") -> dict:
    lang = donor.language if donor.language in ("en", "hi") else "en"
    return {
        "group": req.patient_group, "donor_group": donor.blood_group, "units": req.units,
        "age": req.patient_age if req.patient_age else ("not given" if lang == "en" else "पता नहीं"),
        "gender": GENDER_WORD[req.patient_gender][lang],
        "hospital": req.hospital_name, "distance": f"{distance_km:.1f}", "component": component_word(req.component, lang),
        "reason": reason or explain.why_you({}, distance_km, donor.blood_group, req.patient_group, lang),
        "bank": req.hospital_name, "hours": 72,
    }


def _shortage_near(db: Session, req: Request) -> dict | None:
    try:
        from . import forecast
        return forecast.shortage_near(db, req.hospital_lat, req.hospital_lng, normalize_component(req.component))
    except Exception:  # noqa: BLE001  (the radar is optional; alerts must still go out)
        return None


def notify(db: Session, req: Request, cand: dict, wave: int, shortage: dict | None = None) -> Notification:
    donor: Donor = cand["donor"]
    lang = donor.language
    seg = bandit.segment(donor)
    variant = "drive" if req.kind == "drive" else bandit.choose(db, seg)
    reason = explain.why_you(cand["features"], cand["distance_km"], donor.blood_group, req.patient_group, lang, shortage)
    n = Notification(request_id=req.id, donor_id=donor.id, wave=wave, status="sent", variant=variant, segment=seg,
                     reason=reason[:200], score=cand["score"], distance_km=cand["distance_km"], features=cand["features"])
    db.add(n)
    db.flush()
    params = alert_params(req, donor, cand["distance_km"], reason)
    key = "drive_alert" if variant == "drive" else "alert" if variant == "standard" else f"alert_{variant}"
    msg = whatsapp.send(
        db, donor.phone, t(key, lang, **params),
        buttons=[(f"acc:{n.id}", b("can_donate", lang)), (f"dec:{n.id}", b("not_today", lang))],
        template=(key, params, lang),
    )
    n.wa_message_id = msg.wa_message_id
    if settings.whatsapp_mode == "mock" and "error" not in msg.payload:
        n.status, n.delivered_at = "delivered", utcnow()
    donor.last_alerted_at = utcnow()
    donor.alerts_sent += 1
    return n


def run_wave(db: Session, req: Request, now: datetime | None = None) -> int:
    """Send the next wave. Radii widen per wave; a radius with nobody new is skipped at once."""
    now = now or utcnow()
    radii = settings.wave_radii_km
    max_waves = len(radii) + 2  # keep pulling from the widest ring for two more waves
    left = alerts_left(db, req, now)
    if left <= 0:
        req.next_wave_at = now + timedelta(minutes=settings.wave_interval_min)
        return 0
    shortage = _shortage_near(db, req)
    while req.wave < max_waves:
        req.wave += 1
        radius = radii[min(req.wave - 1, len(radii) - 1)]
        cands = find_candidates(db, req, radius, now)
        if cands:
            chosen = pick_wave(cands, min(settings.wave_size, left), f"{req.id}:{req.wave}")
            for c in chosen:
                notify(db, req, c, req.wave, shortage)
            req.radius_km = radius
            req.next_wave_at = now + timedelta(minutes=settings.wave_interval_min)
            return len(chosen)
        req.radius_km = radius
    req.next_wave_at = None
    if connected_count(db, req) < req.target_acceptances and req.status != "needs_public_share":
        req.status = "needs_public_share"
        tell_requester_all_asked(db, req)
    return 0


def tell_requester_all_asked(db: Session, req: Request) -> None:
    if req.kind == "drive" or not req.requester_phone:
        return
    lang = req.language or "en"
    p = {"hospital": req.hospital_name, "link": f"{settings.public_base_url.rstrip('/')}/r/{req.share_slug}"}
    whatsapp.send(db, req.requester_phone, t("rq_all_asked", lang, **p), template=("rq_all_asked", p, lang))


def start_dispatch(db: Session, req: Request) -> int:
    if req.status != "open":
        raise ValueError(f"request is {req.status}")
    from . import dispatch_agent

    req.status = "dispatching"
    req.dispatched_at = utcnow()
    sent = run_wave(db, req)
    dispatch_agent.log_start(db, req, sent)
    return sent


def close_pending(db: Session, req: Request, message_key: str) -> int:
    """Stop all outstanding alerts and tell those donors they are not needed (no zombie forwards)."""
    count = 0
    for n in db.scalars(select(Notification).where(Notification.request_id == req.id, Notification.status.in_(PENDING + ("accepted",)))).all():
        key = "already_covered" if n.status == "accepted" else message_key
        if n.status in PENDING and utcnow() - n.sent_at > timedelta(minutes=15):
            bandit.update(db, n.variant, n.segment, 0)  # had time to answer and did not: a non-acceptance
        n.status = "cancelled"
        lang = n.donor.language
        whatsapp.send(db, n.donor.phone, t(key, lang, hospital=req.hospital_name),
                      template=(key, {"hospital": req.hospital_name}, lang) if key != "already_covered" else None)
        count += 1
    return count


def check_target(db: Session, req: Request) -> None:
    if req.status in ("dispatching", "needs_public_share") and connected_count(db, req) >= req.target_acceptances:
        req.status = "matched"
        req.next_wave_at = None
        close_pending(db, req, "covered")


def reopen_if_short(db: Session, req: Request) -> None:
    """A connected donor dropped out: resume waves if the request is still open."""
    if req.status == "matched" and connected_count(db, req) < req.target_acceptances:
        req.status = "dispatching"
        req.next_wave_at = utcnow()
        if req.wave >= len(settings.wave_radii_km) + 2:
            req.wave = len(settings.wave_radii_km) + 1  # allow one more wave at the widest radius


def fulfil(db: Session, req: Request) -> None:
    if req.status in ("fulfilled", "expired", "cancelled"):
        return
    req.status, req.closed_at, req.next_wave_at = "fulfilled", utcnow(), None
    close_pending(db, req, "fulfilled_notice")
    for n in db.scalars(select(Notification).where(Notification.request_id == req.id, Notification.status == "connected")).all():
        whatsapp.send(db, n.donor.phone, t("fulfilled_notice", n.donor.language, hospital=req.hospital_name),
                      template=("fulfilled_notice", {"hospital": req.hospital_name}, n.donor.language))


def close(db: Session, req: Request, status: str) -> None:
    req.status, req.closed_at, req.next_wave_at = status, utcnow(), None
    close_pending(db, req, "closed_notice")
