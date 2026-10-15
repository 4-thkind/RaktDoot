"""Team-only controls for the demo (X-Admin-Token header)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db, utcnow
from ..jobs.ticker import tick
from ..models import BloodBank, Donation, Donor, Notification, Request
from ..seed import reset_and_seed
from ..services.whatsapp import click_to_chat_link
from .common import iso, require_admin

router = APIRouter(prefix="/api")


@router.get("/config")
def public_config():
    return {
        "whatsapp_mode": settings.whatsapp_mode,
        "tinyfish_mode": "live" if settings.tinyfish_live else "demo",
        "join_link": click_to_chat_link("JOIN"),
        "component": settings.eraktkosh_component,
        "radii_km": settings.wave_radii_km,
        "quiet_hours": settings.respect_quiet_hours,
    }


@router.get("/health")
def health():
    return {"ok": True}


@router.post("/admin/reset", dependencies=[Depends(require_admin)])
def reset(donors: int = Query(200, ge=0, le=5000), db: Session = Depends(get_db)):
    return reset_and_seed(db, donors)


@router.post("/admin/tick", dependencies=[Depends(require_admin)])
def run_tick(advance_hours: float = Query(0, ge=0, le=24 * 200), db: Session = Depends(get_db)):
    """Run the scheduler now. advance_hours pretends time has passed, to show follow-ups in a demo."""
    done = tick(db, utcnow() + timedelta(hours=advance_hours))
    db.commit()
    return done


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    count = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0  # noqa: E731
    reqs = db.scalars(select(Request).order_by(Request.created_at.desc()).limit(20)).all()
    return {
        "donors": count(Donor), "donors_synthetic": count(Donor, Donor.synthetic.is_(True)),
        "blood_banks": count(BloodBank), "requests": count(Request), "notifications": count(Notification),
        "donations": count(Donation),
        "recent": [{"id": r.id, "group": r.patient_group, "units": r.units, "hospital": r.hospital_name,
                    "status": r.status, "created_at": iso(r.created_at), "manage_token": r.manage_token} for r in reqs],
    }
