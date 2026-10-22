"""Team-only controls for the demo (X-Admin-Token header)."""
import asyncio
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..db import get_db, session_scope, utcnow
from ..jobs.ticker import tick
from ..models import BloodBank, Donation, Donor, Notification, Recipe, Request, StockHistory, TinyFishRun
from ..seed import reset_and_seed
from ..services import bandit, camps, directory, dispatch, guide, stt, tinyfish_client
from ..services.whatsapp import click_to_chat_link
from .common import iso, require_admin

router = APIRouter(prefix="/api")
_jobs: set = set()


@router.get("/config")
def public_config():
    return {
        "whatsapp_mode": settings.whatsapp_mode,
        "tinyfish_mode": "live" if settings.tinyfish_live else "demo",
        "join_link": click_to_chat_link("JOIN"),
        "component": settings.eraktkosh_component,
        "radii_km": settings.wave_radii_km,
        "quiet_hours": settings.respect_quiet_hours,
        "llm": "live" if settings.llm_live else "rules",
        "vision": "live" if settings.llm_live else "sample",
        "stt": stt.provider(),
        "replay": settings.tinyfish_replay_enabled,
        "proxy_country": settings.tinyfish_proxy_country,
        "dispatch_agent": "llm" if settings.dispatch_agent_enabled and settings.llm_live else "rules" if settings.dispatch_agent_enabled else "off",
        "bandit": settings.bandit_enabled,
        "intel_sklearn": settings.use_intel_sklearn,
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
    top = db.scalars(select(Donor).where(Donor.donations_confirmed > 0)
                     .order_by(Donor.donations_verified.desc(), Donor.donations_confirmed.desc()).limit(10)).all()
    return {
        "donors": count(Donor), "donors_synthetic": count(Donor, Donor.synthetic.is_(True)),
        "blood_banks": count(BloodBank), "blood_banks_eraktkosh": count(BloodBank, BloodBank.source == "eraktkosh"),
        "requests": count(Request), "notifications": count(Notification),
        "donations": count(Donation), "donations_verified": count(Donation, Donation.confirmed_by == "photo"),
        "stock_history_real": count(StockHistory, StockHistory.synthetic.is_(False)),
        "stock_history_synthetic": count(StockHistory, StockHistory.synthetic.is_(True)),
        "leaderboard": [{"name": d.name.split()[0] + (f" {d.name.split()[-1][0]}." if len(d.name.split()) > 1 else ""),
                         "group": d.blood_group, "verified": d.donations_verified, "donations": d.donations_confirmed} for d in top],
        "recent": [{"id": r.id, "group": r.patient_group, "units": r.units, "hospital": r.hospital_name, "kind": r.kind,
                    "component": r.component, "status": r.status, "created_at": iso(r.created_at), "manage_token": r.manage_token} for r in reqs],
    }


# ---------------------------------------------------------------- TinyFish panel (W6, 2.4, 2.5)
@router.get("/admin/tinyfish", dependencies=[Depends(require_admin)])
def tinyfish_panel(db: Session = Depends(get_db)):
    runs = db.scalars(select(TinyFishRun).order_by(TinyFishRun.id.desc()).limit(40)).all()
    agg = db.execute(select(TinyFishRun.kind, TinyFishRun.status, func.count(), func.avg(TinyFishRun.duration_ms))
                     .group_by(TinyFishRun.kind, TinyFishRun.status)).all()
    recipes = db.scalars(select(Recipe).order_by(Recipe.version.desc()).limit(5)).all()
    return {
        "mode": "live" if settings.tinyfish_live else "demo",
        "runs": [{"id": r.id, "kind": r.kind, "purpose": r.purpose, "target": r.target, "status": r.status, "run_id": r.run_id,
                  "duration_s": round(r.duration_ms / 1000, 1), "steps": r.steps, "error": r.error, "at": iso(r.created_at),
                  "link": f"https://agent.tinyfish.ai/runs/{r.run_id}" if r.kind == "agent" and r.run_id else None} for r in runs],
        "summary": [{"kind": k, "status": s, "count": c, "avg_s": round((a or 0) / 1000, 1)} for k, s, c, a in agg],
        "recipes": [{"version": r.version, "active": r.active, "success": r.success_count, "fail": r.fail_count,
                     "verified_ok": r.verify_ok, "verified_mismatch": r.verify_mismatch, "learned_codes": sum(len(v) for v in (r.learned or {}).values()),
                     "from_run": r.created_from_run_id, "last_ok": iso(r.last_ok_at)} for r in recipes],
        "unmatched_banks": sorted(({"name": k, **v} for k, v in directory.UNMATCHED.items()), key=lambda x: -x["count"])[:20],
    }


@router.post("/admin/tinyfish/sweep", dependencies=[Depends(require_admin)])
async def sweep(component: str = "prbc"):
    """S1: queue a batch of Agent runs over the configured districts (results land in stock_history)."""
    targets = [tuple(x.split("/", 1)) for x in settings.stock_sweep_districts if "/" in x]
    if not settings.tinyfish_live:
        return {"mode": "demo", "queued": 0, "note": "Set TINYFISH_API_KEY to sweep live stock."}
    task = asyncio.create_task(tinyfish_client.batch_sweep(targets, component))
    _jobs.add(task)
    task.add_done_callback(_jobs.discard)
    return {"mode": "live", "queued": len(targets), "note": "Runs queued; results appear in stock history as they finish."}


@router.post("/admin/tinyfish/monitors", dependencies=[Depends(require_admin)])
async def monitors():
    """S2: a Topic monitor for dengue / blood-shortage news in Delhi NCR, and a Page monitor on eRaktKosh notifications."""
    a = await tinyfish_client.create_monitor("search", {"query": "dengue cases Delhi NCR platelets", "recency_minutes": 1440, "result_limit": 10},
                                             "0 */6 * * *", "Rakt Doot: dengue news", "A new report of dengue cases or a platelet shortage in Delhi NCR")
    b = await tinyfish_client.create_monitor("fetch", {"url": "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/notification.cnt", "format": "markdown"},
                                             "0 8 * * *", "Rakt Doot: eRaktKosh notices", "A new notice about blood availability or camps")
    return {"topic": a, "page": b}


@router.post("/admin/directory/refresh", dependencies=[Depends(require_admin)])
async def refresh_directory():
    def work():
        with session_scope() as db:
            return directory.refresh_live(db)
    return await run_in_threadpool(work)


@router.post("/admin/camps/refresh", dependencies=[Depends(require_admin)])
async def refresh_camps():
    with session_scope() as db:
        return await camps.refresh(db)


@router.post("/admin/guide/rebuild", dependencies=[Depends(require_admin)])
async def rebuild_guide():
    def work():
        chunks = guide.build()
        with session_scope() as db:
            return {"chunks": guide.load(db, chunks), "via": sorted({c["fetched_via"] for c in chunks})}
    return await run_in_threadpool(work)


# ---------------------------------------------------------------- bandit (F11)
@router.get("/admin/bandit", dependencies=[Depends(require_admin)])
def bandit_stats(db: Session = Depends(get_db)):
    return {"enabled": settings.bandit_enabled, "real": bandit.posteriors(db, False), "simulated": bandit.posteriors(db, True),
            "true_rates_simulation": bandit.SIM_TRUE_RATES}


@router.post("/admin/bandit/simulate", dependencies=[Depends(require_admin)])
def bandit_simulate(n: int = Query(600, ge=50, le=5000), db: Session = Depends(get_db)):
    out = bandit.simulate(db, n, seed=int(utcnow().timestamp()) % 10000)
    db.commit()
    return out

# ---------------------------------------------------------------- running requests (a kill switch for forgotten ones)
RUNNING = ("open",) + dispatch.ACTIVE_REQUEST

@router.get("/admin/requests/running", dependencies=[Depends(require_admin)])
def running_requests(db: Session = Depends(get_db)):
    rows = db.scalars(select(Request).where(Request.status.in_(RUNNING)).order_by(Request.created_at.desc())).all()
    return [{"id": r.id, "group": r.patient_group, "units": r.units, "component": r.component, "hospital": r.hospital_name,
             "kind": r.kind, "status": r.status, "created_at": iso(r.created_at), "expires_at": iso(r.expires_at)} for r in rows]

@router.post("/admin/requests/stop", dependencies=[Depends(require_admin)])
def stop_requests(rid: str | None = None, db: Session = Depends(get_db)):
    """Stop one request (rid) or, without rid, every running one. Donors get the usual 'no longer needed' notice."""
    q = select(Request).where(Request.status.in_(RUNNING))
    rows = db.scalars(q.where(Request.id == rid) if rid else q).all()
    for r in rows:
        dispatch.close(db, r, "cancelled")
    db.commit()
    return {"stopped": len(rows)}
