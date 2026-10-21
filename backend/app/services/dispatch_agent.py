"""Agentic dispatcher (F5): an LLM picks the next step for an open request from a FIXED, SAFE action
set, and every decision is logged and streamed to the dashboard as a mission-control line.

Guardrails:
- Donors are only ever selected by dispatch.find_candidates (SQL: consent, rest period, 24 h limit,
  quiet hours). The agent cannot name, pick or message a donor.
- Hard caps on alerts per request and per hour (dispatch.alerts_left) apply to every action.
- include_o_negative is checked against policy before it runs.
- No key, a timeout, invalid JSON or a disallowed action -> the deterministic rules below decide.
  The rules are today's wave logic, written as the same actions with a templated reason."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.compatibility import normalize_component
from ..db import utcnow
from ..models import DispatchDecision, Notification, Request, StockCache
from . import dispatch, llm

log = logging.getLogger("raktdoot.dispatch_agent")
ACTIONS = ["wait", "send_next_wave", "widen_radius", "include_o_negative", "recheck_stock", "suggest_camp",
           "suggest_public_share", "close_if_fulfilled"]

SYSTEM = """You are the dispatcher for an emergency blood request in India. Choose ONE next action from this fixed set:
wait(minutes 1-30) | send_next_wave | widen_radius | include_o_negative | recheck_stock | suggest_camp | suggest_public_share | close_if_fulfilled
Facts: donors usually reply within 10 minutes; O- red cells are universal and kept in reserve; at night fewer donors reply;
each wave messages a few more donors further out; you cannot contact donors directly.
Return ONLY JSON {"action": str, "args": {"minutes": int} or {}, "reason": "one short line a family can read"}."""


def state(db: Session, req: Request, now: datetime) -> dict:
    notes = db.scalars(select(Notification).where(Notification.request_id == req.id)).all()
    last_sent = max((n.sent_at for n in notes), default=None)
    radii = settings.wave_radii_km
    nxt = radii[min(req.wave, len(radii) - 1)]
    stock = db.scalars(select(StockCache).where(StockCache.component == normalize_component(req.component))
                       .order_by(StockCache.fetched_at.desc()).limit(3)).all()
    stocked = sum(1 for s in stock for b in (s.results or []) if (b.get("stock") or {}).get(req.patient_group))
    return {
        "group": req.patient_group, "component": req.component, "units": req.units, "kind": req.kind,
        "target": req.target_acceptances, "connected": sum(1 for n in notes if n.status in dispatch.CONNECTED),
        "accepted": sum(1 for n in notes if n.status == "accepted"), "pending": sum(1 for n in notes if n.status in dispatch.PENDING),
        "declined": sum(1 for n in notes if n.status in ("declined", "ineligible")), "notified": len(notes),
        "wave": req.wave, "radius_km": req.radius_km, "next_radius_km": nxt, "max_waves": len(radii) + 2,
        "minutes_since_dispatch": int((now - req.dispatched_at).total_seconds() // 60) if req.dispatched_at else 0,
        "minutes_since_last_wave": int((now - last_sent).total_seconds() // 60) if last_sent else None,
        "local_time": dispatch.local_now().strftime("%H:%M"), "quiet_hours": dispatch.in_quiet_hours(dispatch.local_now().hour),
        "o_neg_reserved": dispatch.o_neg_reserved(req), "scarce_group": req.patient_group.endswith("-"),
        "alerts_left": dispatch.alerts_left(db, req, now), "banks_with_group_in_cache": stocked,
        "candidates_next_radius": len(dispatch.find_candidates(db, req, nxt, now)),
    }


def o_neg_allowed(st: dict) -> bool:
    """Policy for releasing O- donors: wave 2+, or a scarce (negative) group, or 20+ minutes without enough donors."""
    return st["o_neg_reserved"] and (st["wave"] >= 2 or st["scarce_group"] or st["minutes_since_dispatch"] >= 20)


def summary(st: dict) -> str:
    return (f"{st['connected']}/{st['target']} connected · {st['pending']} pending · wave {st['wave']} at {st['radius_km']:g} km"
            f" · {st['local_time']}" + (" · scarce group" if st["scarce_group"] else ""))


def rules(st: dict) -> dict:
    """Deterministic policy (also the fallback)."""
    if st["connected"] >= st["target"]:
        return {"action": "close_if_fulfilled", "args": {}, "reason": "enough donors connected"}
    if st["alerts_left"] <= 0:
        return {"action": "wait", "args": {"minutes": 10}, "reason": "alert cap reached for this hour, waiting"}
    since = st["minutes_since_last_wave"]
    if st["pending"] and since is not None and since < settings.wave_interval_min:
        return {"action": "wait", "args": {"minutes": settings.wave_interval_min - since},
                "reason": f"{st['pending']} donors still deciding, giving them time"}
    if o_neg_allowed(st) and st["wave"] >= 2:
        return {"action": "include_o_negative", "args": {}, "reason": "not enough donors yet, allowing O− donors too"}
    if st["wave"] >= st["max_waves"] and not st["candidates_next_radius"]:
        return {"action": "suggest_public_share", "args": {}, "reason": "everyone eligible in reach has been asked"}
    return {"action": "send_next_wave", "args": {}, "reason": f"widening to {st['next_radius_km']:g} km"}


def validate(raw: dict, st: dict) -> dict | None:
    if not isinstance(raw, dict) or raw.get("action") not in ACTIONS:
        return None
    args = raw.get("args") if isinstance(raw.get("args"), dict) else {}
    if raw["action"] == "wait":
        try:
            args = {"minutes": max(1, min(30, int(args.get("minutes", 5))))}
        except (TypeError, ValueError):
            return None
    else:
        args = {}
    if raw["action"] == "include_o_negative" and not o_neg_allowed(st):
        return None  # policy: O- stays in reserve
    if raw["action"] == "close_if_fulfilled" and st["connected"] < st["target"]:
        return None
    reason = str(raw.get("reason") or "").strip()[:160] or raw["action"]
    return {"action": raw["action"], "args": args, "reason": reason}


def decide(st: dict) -> tuple[dict, str]:
    if not (settings.dispatch_agent_enabled and settings.llm_api_key):
        return rules(st), "rules"
    try:
        got = validate(llm.chat_json(SYSTEM, f"Request state: {st}", timeout=10), st)
        if got:
            return got, "llm"
    except Exception as e:  # noqa: BLE001
        log.info("dispatch agent LLM failed, rules decide: %s", e)
    return rules(st), "fallback"


def execute(db: Session, req: Request, choice: dict, now: datetime) -> str:
    a = choice["action"]
    interval = timedelta(minutes=settings.wave_interval_min)
    if a == "wait":
        req.next_wave_at = now + timedelta(minutes=choice["args"]["minutes"])
        return f"next check in {choice['args']['minutes']} min"
    if a in ("send_next_wave", "widen_radius"):
        sent = dispatch.run_wave(db, req, now)
        return f"messaged {sent} donors within {req.radius_km:g} km" if sent else f"no new donors within {req.radius_km:g} km"
    if a == "include_o_negative":
        req.allow_o_neg = True
        sent = dispatch.run_wave(db, req, now)
        return f"O− allowed; messaged {sent} donors within {req.radius_km:g} km"
    if a == "recheck_stock":
        req.next_wave_at = now + interval
        st = state(db, req, now)
        return f"{st['banks_with_group_in_cache']} recently checked blood centres list {req.patient_group}"
    if a == "suggest_camp":
        from . import camps
        req.next_wave_at = now + interval
        c = camps.nearest(db, req.hospital_lat, req.hospital_lng)
        return f"nearest camp: {c.title}, {c.camp_date.isoformat()}" if c else "no camp nearby in the next weeks"
    if a == "suggest_public_share":
        if req.status != "needs_public_share":
            req.status = "needs_public_share"
            dispatch.tell_requester_all_asked(db, req)
        req.next_wave_at = None
        return "asked the family to share the request link"
    if a == "close_if_fulfilled":
        dispatch.check_target(db, req)
        return f"status {req.status}"
    return "no-op"


def step(db: Session, req: Request, now: datetime | None = None) -> DispatchDecision:
    now = now or utcnow()
    st = state(db, req, now)
    choice, engine = decide(st)
    result = execute(db, req, choice, now)
    d = DispatchDecision(request_id=req.id, engine=engine, action=choice["action"], args=choice["args"],
                         reason=f"{summary(st)} → {choice['reason']}", state=st, result=result[:200])
    db.add(d)
    return d


def log_start(db: Session, req: Request, sent: int) -> None:
    db.add(DispatchDecision(request_id=req.id, engine="rules", action="send_next_wave", args={},
                            reason=f"new {req.kind} request · {req.units} unit(s) {req.patient_group} → first wave at {req.radius_km:g} km",
                            state={}, result=f"messaged {sent} donors"))


def decisions_count(db: Session, req: Request) -> int:
    return db.scalar(select(func.count()).select_from(DispatchDecision).where(DispatchDecision.request_id == req.id)) or 0
