"""Thalassemia autopilot (F7): a fair donor rota for patients who need transfusions every few weeks.

Greedy with hard constraints, date by date (light, deterministic and testable; CP-SAT would be
overkill for one patient's 6-month horizon):
  hard: compatible, consented, opted in to recurring rotas, within max_km, age 18-65,
        rest period since their last (real or planned) donation, at most 4 (men) / 3 (women)
        planned whole-blood donations in any 365 days, one slot per donor per date
  soft: prefer reliable, responsive, nearer donors; penalise donors already on the rota (fairness)
The ticker reminds each donor a few days ahead (confirm / can't), refills declined slots, and
opens a normal request two days ahead for any slot still unfilled."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core import eligibility
from ..core.compatibility import compatible_donors
from ..core.geo import haversine_km
from ..db import utcnow
from ..models import Donation, Donor, RecurringNeed, RecurringSlot, Request

MAX_PER_YEAR = {"M": 4, "F": 3, "O": 3}


def candidates(db: Session, need: RecurringNeed, today: date) -> list[Donor]:
    q = select(Donor).where(Donor.blood_group.in_(compatible_donors(need.patient_group, need.component)),
                            Donor.consent.is_(True), Donor.opted_out.is_(False), Donor.recurring_opt_in.is_(True),
                            Donor.weight_ok.is_(True), Donor.lat.is_not(None))
    return [d for d in db.scalars(q).all()
            if eligibility.age_ok(d.dob, today) and haversine_km(need.hospital_lat, need.hospital_lng, d.lat, d.lng) <= need.max_km]


def due_dates(need: RecurringNeed, horizon_days: int, today: date) -> list[date]:
    out, d = [], need.next_due
    while d <= today + timedelta(days=horizon_days):
        if d >= today:
            out.append(d)
        d += timedelta(days=need.interval_days)
    return out


def plan(donors: list[Donor], need: RecurringNeed, dates: list[date], history: dict[str, list[date]],
         fixed: dict[date, list[str]] | None = None) -> dict[date, list[str | None]]:
    """Pure function: assign donors to dates. `history` = past donation dates per donor id.
    `fixed` = already confirmed donor ids per date (kept)."""
    fixed = fixed or {}
    taken: dict[str, list[date]] = {d.id: sorted(history.get(d.id, [])) for d in donors}
    load = {d.id: 0 for d in donors}
    for day, ids in fixed.items():
        for i in ids:
            taken.setdefault(i, []).append(day)
            load[i] = load.get(i, 0) + 1
    out: dict[date, list[str | None]] = {}
    for day in dates:
        chosen = list(fixed.get(day, []))
        while len(chosen) < need.units:
            best, best_score = None, -1e9
            for d in donors:
                if d.id in chosen or not ok_on(d, day, taken.get(d.id, [])):
                    continue
                reliability = 1.0 - d.no_shows / (d.alerts_accepted + 2)
                response = (d.alerts_responded + 2) / (d.alerts_sent + 4)
                near = 1.0 - min(1.0, haversine_km(need.hospital_lat, need.hospital_lng, d.lat, d.lng) / max(need.max_km, 1))
                s = reliability + 0.5 * response + 0.3 * near + 0.15 * (d.donations_verified or 0) - 0.6 * load[d.id]
                if s > best_score:
                    best, best_score = d.id, s
            if best is None:
                chosen.append(None)
                break
            chosen.append(best)
            taken.setdefault(best, []).append(day)
            taken[best].sort()
            load[best] += 1
        out[day] = (chosen + [None] * need.units)[:need.units]
    return out


def ok_on(donor: Donor, day: date, donations: list[date]) -> bool:
    """Rest period from every other (real or planned) donation, and the yearly cap, around `day`."""
    rest = eligibility.rest_days(donor.gender)
    if any(abs((day - d).days) < rest for d in donations):
        return False
    window = [d for d in donations if abs((day - d).days) < 365]
    return len(window) < MAX_PER_YEAR.get(donor.gender, 3)


def violations(donors: list[Donor], history: dict[str, list[date]], schedule: dict[date, list[str | None]]) -> list[str]:
    """Independent check used by tests and the API: rest periods and yearly caps."""
    per: dict[str, list[date]] = {d.id: list(history.get(d.id, [])) for d in donors}
    for day, ids in schedule.items():
        for i in ids:
            if i:
                per.setdefault(i, []).append(day)
    by_id = {d.id: d for d in donors}
    out = []
    for i, days in per.items():
        days.sort()
        rest = eligibility.rest_days(by_id[i].gender)
        for a, b in zip(days, days[1:]):
            if (b - a).days < rest:
                out.append(f"{i}: {a} -> {b} is {(b - a).days} days (< {rest})")
        for k, a in enumerate(days):
            if sum(1 for b in days[k:] if (b - a).days < 365) > MAX_PER_YEAR.get(by_id[i].gender, 3):
                out.append(f"{i}: more than {MAX_PER_YEAR.get(by_id[i].gender, 3)} donations within a year from {a}")
    return out


def history_for(db: Session, donors: list[Donor]) -> dict[str, list[date]]:
    ids = [d.id for d in donors]
    hist: dict[str, list[date]] = {d.id: ([d.last_donation_date] if d.last_donation_date else []) for d in donors}
    for don in db.scalars(select(Donation).where(Donation.donor_id.in_(ids))).all():
        if don.donated_on not in hist[don.donor_id]:
            hist[don.donor_id].append(don.donated_on)
    return hist


def rebuild(db: Session, need: RecurringNeed, horizon_days: int = 182, today: date | None = None) -> list[RecurringSlot]:
    """(Re)plan all future slots that are not yet confirmed/done; confirmed slots are kept."""
    today = today or date.today()
    donors = candidates(db, need, today)
    slots = db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id, RecurringSlot.due_date >= today)).all()
    fixed: dict[date, list[str]] = {}
    for s in slots:
        if s.status in ("confirmed", "reminded", "done") and s.donor_id:
            fixed.setdefault(s.due_date, []).append(s.donor_id)
        else:
            db.delete(s)
    db.flush()
    declined = {(s.due_date, s.donor_id) for s in slots if s.status == "declined"}
    hist = history_for(db, donors)
    schedule = plan(donors, need, due_dates(need, horizon_days, today), hist, fixed)
    keep_ids = {(s.due_date, s.donor_id) for s in slots if s.status in ("confirmed", "reminded", "done")}
    for day, ids in schedule.items():
        for i in ids:
            if (day, i) in keep_ids:
                continue
            if (day, i) in declined:
                i = None
            db.add(RecurringSlot(need_id=need.id, due_date=day, donor_id=i, status="planned" if i else "unfilled"))
    db.flush()
    return db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id).order_by(RecurringSlot.due_date)).all()


def refill(db: Session, slot: RecurringSlot) -> RecurringSlot | None:
    """A donor said they can't: offer the date to the next best donor (excluding everyone who declined it)."""
    need = db.get(RecurringNeed, slot.need_id)
    today = date.today()
    declined = {s.donor_id for s in db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id,
                                                                         RecurringSlot.due_date == slot.due_date,
                                                                         RecurringSlot.status == "declined")).all()}
    on_date = {s.donor_id for s in db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id,
                                                                        RecurringSlot.due_date == slot.due_date)).all()}
    donors = [d for d in candidates(db, need, today) if d.id not in declined and d.id not in on_date]
    hist = history_for(db, donors)
    for s in db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id, RecurringSlot.donor_id.is_not(None),
                                                    RecurringSlot.status.in_(("planned", "reminded", "confirmed")))).all():
        if s.donor_id in hist:
            hist[s.donor_id].append(s.due_date)
    one = RecurringNeed(units=1, hospital_lat=need.hospital_lat, hospital_lng=need.hospital_lng, max_km=need.max_km)
    pick = plan(donors, one, [slot.due_date], hist).get(slot.due_date, [None])[0]
    new = RecurringSlot(need_id=need.id, due_date=slot.due_date, donor_id=pick, status="planned" if pick else "unfilled")
    db.add(new)
    db.flush()
    return new


def open_gap_requests(db: Session, today: date) -> int:
    """Two days before a date with unfilled slots, open a normal request so waves fill the gap."""
    from . import dispatch

    made = 0
    soon = today + timedelta(days=2)
    for need in db.scalars(select(RecurringNeed).where(RecurringNeed.active.is_(True))).all():
        slots = db.scalars(select(RecurringSlot).where(RecurringSlot.need_id == need.id, RecurringSlot.due_date == soon)).all()
        filled = sum(1 for s in slots if s.status in ("planned", "reminded", "confirmed"))
        gap = max(0, need.units - filled)
        if not slots or not gap or any(s.request_id for s in slots):  # no slots = not a rota date (else a new request every tick)
            continue
        req = Request(patient_group=need.patient_group, group_confirmed=True, units=gap, patient_age=0, patient_gender="O",
                      hospital_name=need.hospital_name, hospital_lat=need.hospital_lat, hospital_lng=need.hospital_lng,
                      requester_name=need.requester_name, requester_phone=need.requester_phone, component=need.component,
                      kind="recurring", target_acceptances=gap, expires_at=utcnow() + timedelta(hours=72),
                      hospital_check={"score": 1.0, "verified": True, "evidence": [{"source": "registered recurring need"}]})
        db.add(req)
        db.flush()
        for s in slots:
            s.request_id = req.id
        dispatch.start_dispatch(db, req)
        made += 1
    return made


def as_json(need: RecurringNeed, slots: list[RecurringSlot]) -> dict:
    def donor_label(s):
        if not s.donor:
            return None
        parts = s.donor.name.split()
        return parts[0] + (f" {parts[-1][0]}." if len(parts) > 1 else "")
    return {"id": need.id, "patient_label": need.patient_label, "group": need.patient_group, "component": need.component,
            "units": need.units, "interval_days": need.interval_days, "next_due": need.next_due.isoformat(),
            "hospital": need.hospital_name, "synthetic": need.synthetic,
            "slots": [{"id": s.id, "date": s.due_date.isoformat(), "status": s.status, "donor": donor_label(s),
                       "donor_group": s.donor.blood_group if s.donor else None} for s in slots],
            "reminder_days": settings.recurring_reminder_days}
