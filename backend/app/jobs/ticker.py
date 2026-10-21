"""Periodic jobs. State lives in the database, so a restart loses nothing: each tick just
looks for work that is due. Runs in-process (one backend instance)."""
import asyncio
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import or_, select

from ..config import settings
from ..core import eligibility
from ..db import session_scope, utcnow
from ..models import Donor, Notification, RecurringNeed, RecurringSlot, Request
from ..services import camps, dispatch, dispatch_agent, forecast, recurring, tinyfish_client, whatsapp
from ..services.messages import b, t

log = logging.getLogger("raktdoot.ticker")
ONWAY_AFTER = timedelta(hours=2)
FOLLOWUP_AFTER = timedelta(hours=24)


def tick(db, now: datetime | None = None) -> dict:
    now = now or utcnow()
    done = {"waves": 0, "expired": 0, "onway": 0, "followups": 0, "eligible_again": 0, "rota_reminders": 0, "gap_requests": 0}

    # 1. next dispatch step: the agentic dispatcher (F5) chooses; rules decide when it can't
    for req in db.scalars(select(Request).where(Request.status == "dispatching", Request.next_wave_at <= now)).all():
        if dispatch.connected_count(db, req) >= req.target_acceptances:
            dispatch.check_target(db, req)
        elif settings.dispatch_agent_enabled:
            dispatch_agent.step(db, req, now)
            done["waves"] += 1
        else:
            dispatch.run_wave(db, req, now)
            done["waves"] += 1

    # 2. expire stale requests (no zombie forwards)
    for req in db.scalars(select(Request).where(Request.status.in_(("open",) + dispatch.ACTIVE_REQUEST), Request.expires_at <= now)).all():
        dispatch.close(db, req, "expired")
        done["expired"] += 1

    # 3. "are you on your way?" 2 h after connecting
    q = select(Notification).join(Request).where(
        Notification.status == "connected", Notification.onway_asked.is_(False),
        Notification.connected_at <= now - ONWAY_AFTER, Request.status.in_(dispatch.ACTIVE_REQUEST))
    for n in db.scalars(q).all():
        n.onway_asked = True
        lang = n.donor.language
        params = {"hospital": n.request.hospital_name}
        whatsapp.send(db, n.donor.phone, t("onway", lang, **params), template=("onway", params, lang),
                      buttons=[(f"ow:{n.id}:y", b("on_my_way", lang)), (f"ow:{n.id}:n", b("cant_make_it", lang))])
        done["onway"] += 1

    # 4. "did you donate?" 24 h after connecting
    q = select(Notification).where(Notification.status == "connected", Notification.followup_sent.is_(False),
                                   Notification.connected_at <= now - FOLLOWUP_AFTER)
    for n in db.scalars(q).all():
        n.followup_sent = True
        lang = n.donor.language
        params = {"hospital": n.request.hospital_name}
        whatsapp.send(db, n.donor.phone, t("followup", lang, **params), template=("followup", params, lang),
                      buttons=[(f"fu:{n.id}:y", b("donated", lang)), (f"fu:{n.id}:d", b("deferred", lang)),
                               (f"fu:{n.id}:c", b("couldnt_go", lang))])
        done["followups"] += 1

    # 5. rest period over (with the nearest upcoming camp, A1)
    today = dispatch.local_today()
    q = select(Donor).where(
        Donor.last_donation_date.is_not(None), Donor.opted_out.is_(False),
        Donor.last_donation_date <= today - timedelta(days=eligibility.rest_days("M")),
        Donor.last_donation_date >= today - timedelta(days=eligibility.rest_days("F") + 7),
        or_(Donor.eligible_again_notified.is_(None), Donor.eligible_again_notified != Donor.last_donation_date))
    for d in db.scalars(q).all():
        again = eligibility.eligible_again_on(d.last_donation_date, d.gender)
        if again > today or again < today - timedelta(days=7):  # only freshly eligible donors
            continue
        d.eligible_again_notified = d.last_donation_date
        camp = camps.nearest(db, d.lat, d.lng, today) if d.lat is not None else None
        if camp:
            params = {"name": d.name.split()[0], "date": camp.camp_date.strftime("%d %b"), "camp": camp.title,
                      "place": camp.address or camp.district}
            whatsapp.send(db, d.phone, t("eligible_again_camp", d.language, **params), template=("eligible_again_camp", params, d.language),
                          buttons=[(f"cr:{camp.id}", b("register_me", d.language))])
        else:
            params = {"name": d.name.split()[0]}
            whatsapp.send(db, d.phone, t("eligible_again", d.language, **params), template=("eligible_again", params, d.language))
        done["eligible_again"] += 1

    # 6. recurring rotas (F7): reminders ahead of each date, gap requests, roll the schedule forward
    horizon = today + timedelta(days=settings.recurring_reminder_days)
    for s in db.scalars(select(RecurringSlot).join(RecurringNeed).where(
            RecurringNeed.active.is_(True), RecurringSlot.status == "planned", RecurringSlot.donor_id.is_not(None),
            RecurringSlot.due_date <= horizon, RecurringSlot.due_date >= today)).all():
        need, donor = db.get(RecurringNeed, s.need_id), s.donor
        s.status = "reminded"
        params = {"patient": need.patient_label, "group": need.patient_group, "hospital": need.hospital_name,
                  "date": s.due_date.strftime("%d %b")}
        whatsapp.send(db, donor.phone, t("recurring_reminder", donor.language, **params), template=("recurring_reminder", params, donor.language),
                      buttons=[(f"rc:{s.id}:y", b("confirm", donor.language)), (f"rc:{s.id}:n", b("cant", donor.language))])
        done["rota_reminders"] += 1
    done["gap_requests"] = recurring.open_gap_requests(db, today)
    for need in db.scalars(select(RecurringNeed).where(RecurringNeed.active.is_(True), RecurringNeed.next_due < today)).all():
        for s in db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id, RecurringSlot.due_date < today,
                                                        RecurringSlot.status.in_(("confirmed", "reminded")))).all():
            s.status = "done"
        while need.next_due < today:
            need.next_due += timedelta(days=need.interval_days)

    # 7. voice replies are kept a week, then dropped
    from ..models import MediaFile
    db.execute(MediaFile.__table__.delete().where(MediaFile.created_at < now - timedelta(days=7)))
    return done


# ---------------------------------------------------------------- background loop
_last = {"radar": 0.0, "sweep": 0.0}


def _hourly(db) -> None:
    """Shortage Radar refresh and, when configured, automatic pre-emptive drives (F1)."""
    if not settings.forecast_enabled:
        return
    for comp in ("prbc", "platelets"):
        data = forecast.radar(db, comp, use_cache=False)
        if settings.auto_drives:
            for cell in data["at_risk"][:2]:
                open_drive = db.scalar(select(Request.id).where(Request.kind == "drive", Request.status.in_(dispatch.ACTIVE_REQUEST),
                                                                Request.patient_group == cell["group"]).limit(1))
                if not open_drive and cell["risk"] >= 0.7:
                    forecast.start_drive(db, cell["district"], cell["group"], comp)


async def run_forever() -> None:
    _last["radar"] = time.monotonic() - 3600 + 30  # first radar ~30 s after startup, not during it
    while True:
        try:
            await asyncio.to_thread(_tick_once)
            if time.monotonic() - _last["radar"] > 3600:
                _last["radar"] = time.monotonic()
                await asyncio.to_thread(_radar_once)
            if settings.stock_sweep_hours and settings.tinyfish_live and time.monotonic() - _last["sweep"] > settings.stock_sweep_hours * 3600:
                _last["sweep"] = time.monotonic()
                targets = [tuple(x.split("/", 1)) for x in settings.stock_sweep_districts if "/" in x]
                asyncio.create_task(tinyfish_client.batch_sweep(targets))  # S1: heavy work off the request path
        except Exception:
            log.exception("tick failed")
        await asyncio.sleep(settings.ticker_seconds)


def _tick_once() -> None:
    with session_scope() as db:
        tick(db)


def _radar_once() -> None:
    with session_scope() as db:
        _hourly(db)
