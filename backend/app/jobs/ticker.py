"""Periodic jobs. State lives in the database, so a restart loses nothing: each tick just
looks for work that is due. Runs in-process (one backend instance)."""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, select

from ..config import settings
from ..core import eligibility
from ..db import session_scope, utcnow
from ..models import Donor, Notification, Request
from ..services import dispatch, whatsapp
from ..services.messages import b, t

log = logging.getLogger("raktdoot.ticker")
ONWAY_AFTER = timedelta(hours=2)
FOLLOWUP_AFTER = timedelta(hours=24)


def tick(db, now: datetime | None = None) -> dict:
    now = now or utcnow()
    done = {"waves": 0, "expired": 0, "onway": 0, "followups": 0, "eligible_again": 0}

    # 1. next dispatch wave
    for req in db.scalars(select(Request).where(Request.status == "dispatching", Request.next_wave_at <= now)).all():
        if dispatch.connected_count(db, req) >= req.target_acceptances:
            dispatch.check_target(db, req)
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

    # 5. rest period over
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
        params = {"name": d.name.split()[0]}
        whatsapp.send(db, d.phone, t("eligible_again", d.language, **params), template=("eligible_again", params, d.language))
        done["eligible_again"] += 1
    return done


async def run_forever() -> None:
    while True:
        try:
            await asyncio.to_thread(_tick_once)
        except Exception:
            log.exception("tick failed")
        await asyncio.sleep(settings.ticker_seconds)


def _tick_once() -> None:
    with session_scope() as db:
        tick(db)
