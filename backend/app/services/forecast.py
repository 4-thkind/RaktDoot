"""Shortage Radar (F1): forecast per (district, component, group) whether usable stock drops below a
threshold in the next 72 h, explain why, and start a pre-emptive donor drive.

Model: Holt's linear exponential smoothing on the daily district total, times a weekday factor
learned from the same series; risk = P(min forecast over 3 days < threshold) under a normal error
whose spread is the series' one-step residual std. Small, explainable, no heavy dependencies.

Data: stock_history rows from real lookups (replay / agent / batch). Until a series has
MIN_REAL_DAYS of real history, a CLEARLY LABELLED synthetic history is used for the demo
(weekday dips, dengue season for platelets, festival dips). Real and synthetic are never mixed."""
import math
import random
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.compatibility import GROUPS, normalize_component
from ..core.geo import haversine_km
from ..db import utcnow
from ..models import BloodBank, Request, Signal, StockHistory

HORIZON_DAYS = 3
MIN_REAL_DAYS = 14
SYN_DAYS = 120
GROUP_BASE = {"O+": 110, "B+": 100, "A+": 70, "AB+": 26, "O-": 7, "B-": 6, "A-": 5, "AB-": 2}
COMPONENT_SCALE = {"prbc": 1.0, "platelets": 0.35, "plasma": 0.8, "whole_blood": 0.2}
FESTIVALS = {date(2026, 3, 4): "Holi", date(2026, 11, 8): "Diwali", date(2026, 10, 20): "Dussehra", date(2027, 3, 22): "Holi"}
SYN_COMPONENTS = ("prbc", "platelets")


def districts(db: Session) -> list[tuple[str, str]]:
    rows = db.execute(select(BloodBank.state, BloodBank.district).distinct()).all()
    return sorted({(s, d) for s, d in rows if d})


# ---------------------------------------------------------------- synthetic history (labelled)
def synth_value(rng: random.Random, group: str, component: str, day: date, scale: float) -> int:
    base = GROUP_BASE[group] * COMPONENT_SCALE[component] * scale
    wd = {0: 0.86, 1: 0.9, 2: 1.0, 3: 1.04, 4: 1.06, 5: 1.0, 6: 0.92}[day.weekday()]  # weekend camps refill by Thursday
    season = 1.0
    if component == "platelets" and day.month in (9, 10, 11):
        season = 0.55 + 0.1 * math.cos((day.timetuple().tm_yday - 290) / 20)  # dengue: platelet demand spikes
    fest = 1.0
    for f in FESTIVALS:
        if 0 <= (day - f).days <= 4 or 0 <= (f - day).days <= 2:
            fest = 0.75  # donors travel, camps pause
    v = base * wd * season * fest * rng.uniform(0.82, 1.18)
    if group.endswith("-") and rng.random() < 0.12:
        v = 0
    return max(0, int(round(v)))


def ensure_history(db: Session, today: date | None = None) -> int:
    """Generate the labelled synthetic history once (bulk insert). Returns rows written."""
    if db.scalar(select(func.count()).select_from(StockHistory).where(StockHistory.synthetic.is_(True))):
        return 0
    today = today or date.today()
    rng = random.Random(2026)
    rows = []
    for state, district in districts(db):
        scale = rng.uniform(0.5, 1.6)
        for comp in SYN_COMPONENTS:
            for g in GROUPS:
                for k in range(SYN_DAYS, 0, -1):
                    day = today - timedelta(days=k)
                    rows.append({"state": state, "district": district, "component": comp, "bank_name": "district total (synthetic)",
                                 "blood_group": g, "units": synth_value(rng, g, comp, day, scale), "source": "synthetic",
                                 "synthetic": True, "observed_at": datetime.combine(day, datetime.min.time()) + timedelta(hours=10)})
    if rows:
        db.execute(insert(StockHistory), rows)
    return len(rows)


# ---------------------------------------------------------------- series
def daily_series(db: Session, district: str, component: str, group: str, synthetic: bool) -> list[tuple[date, int]]:
    """District total per day (last snapshot of each bank that day, summed)."""
    rows = db.execute(select(StockHistory.observed_at, StockHistory.bank_name, StockHistory.units).where(
        StockHistory.district == district, StockHistory.component == component, StockHistory.blood_group == group,
        StockHistory.synthetic.is_(synthetic)).order_by(StockHistory.observed_at)).all()
    per_day: dict[date, dict[str, int]] = defaultdict(dict)
    for at, bank, units in rows:
        per_day[at.date()][bank] = units
    return [(d, sum(v.values())) for d, v in sorted(per_day.items())]


def holt_fit(values: list[float], alpha: float = 0.5, beta: float = 0.15):
    """Holt's linear method on deseasonalised values. Returns (level, trend, residual_std)."""
    level, trend = values[0], (values[min(7, len(values) - 1)] - values[0]) / max(1, min(7, len(values) - 1))
    resid = []
    for v in values[1:]:
        pred = level + trend
        resid.append(v - pred)
        new_level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
    std = math.sqrt(sum(r * r for r in resid) / max(1, len(resid))) if resid else 1.0
    return level, trend, max(std, 0.5)


def weekday_factors(series: list[tuple[date, int]]) -> dict[int, float]:
    mean = sum(v for _, v in series) / max(1, len(series)) or 1.0
    acc: dict[int, list[float]] = defaultdict(list)
    for d, v in series:
        acc[d.weekday()].append(v / mean)
    return {wd: (sum(x) / len(x) if x else 1.0) for wd, x in ((w, acc.get(w, [])) for w in range(7))}


def predict(series: list[tuple[date, int]], horizon: int = HORIZON_DAYS) -> dict:
    """Forecast the next `horizon` days after the last observation."""
    wf = weekday_factors(series)
    deseason = [v / max(0.2, wf[d.weekday()]) for d, v in series]
    level, trend, std = holt_fit(deseason)
    last_day = series[-1][0]
    out = []
    for h in range(1, horizon + 1):
        day = last_day + timedelta(days=h)
        out.append((day, max(0.0, (level + trend * h) * wf[day.weekday()])))
    return {"forecast": out, "level": level, "trend": trend, "std": std * (sum(wf.values()) / 7), "weekday": wf}


def threshold_for(series: list[tuple[date, int]], group: str) -> float:
    """Shortage line for one series: the configured units, but never above a third of the series' usual
    (30-day median) level, so rare groups that always hold 1-2 units are flagged only when about to hit zero."""
    recent = sorted(v for _, v in series[-30:]) or [0]
    median = recent[len(recent) // 2]
    base = settings.shortage_threshold_units * (0.4 if group.endswith("-") else 1.0)
    return max(1.0, min(base, round(median / 3, 1)))


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def risk_of(pred: dict, threshold: float) -> tuple[float, int | None]:
    """(probability the minimum forecast falls below threshold, hours until the first such day)."""
    lows = [v for _, v in pred["forecast"]]
    p = 1.0 - math.prod(1 - _phi((threshold - v) / pred["std"]) for v in lows)
    first = next((h for h, v in enumerate(lows, 1) if v < threshold), None)
    return round(min(1.0, p), 3), first * 24 if first else None


def factors(pred: dict, series, component: str, signals: int, today: date) -> list[str]:
    f = []
    if pred["trend"] < -0.3:
        f.append(f"stock falling ~{abs(pred['trend']):.1f} units/day")
    elif pred["trend"] > 0.3:
        f.append(f"stock rising ~{pred['trend']:.1f} units/day")
    days = [d for d, _ in pred["forecast"]]
    low_wd = [d.strftime("%a") for d in days if pred["weekday"][d.weekday()] < 0.93]
    if low_wd:
        f.append("weekday dip on " + "/".join(low_wd))
    if component == "platelets" and today.month in (9, 10, 11):
        f.append("dengue season (platelet demand)")
    if any(0 <= (fd - today).days <= 4 or 0 <= (today - fd).days <= 2 for fd in FESTIVALS):
        f.append("festival week (fewer camps)")
    if signals:
        f.append(f"{signals} news signal(s) this week")
    recent = [v for _, v in series[-7:]]
    month = [v for _, v in series[-30:]]
    if recent and month and sum(recent) / len(recent) < 0.8 * sum(month) / len(month):
        f.append("7-day level 20%+ below the 30-day average")
    return f or ["stable"]


# ---------------------------------------------------------------- radar
_cache: dict = {}


def radar(db: Session, component: str = "prbc", today: date | None = None, use_cache: bool = True) -> dict:
    component = normalize_component(component)
    key = component
    if use_cache and key in _cache and time.monotonic() - _cache[key][0] < 600:
        return _cache[key][1]
    today = today or date.today()
    if settings.forecast_enabled:
        ensure_history(db, today)
    week_ago = utcnow() - timedelta(days=7)
    sig = dict(db.execute(select(Signal.district, func.count()).where(Signal.observed_at > week_ago).group_by(Signal.district)).all())
    cells = []
    for state, district in districts(db):
        for g in GROUPS:
            real = daily_series(db, district, component, g, synthetic=False)
            synthetic = len(real) < MIN_REAL_DAYS
            series = daily_series(db, district, component, g, synthetic=True) if synthetic else real
            if len(series) < 10:
                continue
            pred = predict(series)
            thr = threshold_for(series, g)
            risk, hours = risk_of(pred, thr)
            cells.append({"state": state, "district": district, "group": g, "component": component, "synthetic": synthetic,
                          "current": series[-1][1], "forecast": [round(v, 1) for _, v in pred["forecast"]],
                          "threshold": thr, "risk": risk, "hours_to_shortage": hours,
                          "factors": factors(pred, series, component, sig.get(district, 0), today)})
    out = {"component": component, "generated_at": utcnow().isoformat(timespec="seconds") + "Z",
           "synthetic": any(c["synthetic"] for c in cells), "cells": cells,
           "at_risk": sorted([c for c in cells if c["risk"] >= 0.5], key=lambda c: -c["risk"])}
    _cache[key] = (time.monotonic(), out)
    return out


def shortage_near(db: Session, lat: float, lng: float, component: str = "prbc") -> dict | None:
    """Groups at risk in the district nearest to a point (used by the 'why you' line)."""
    if not _cache.get(normalize_component(component)):
        return None  # only use a radar the ticker already computed; never compute on the alert path
    banks = db.scalars(select(BloodBank)).all()
    nearest = min(banks, key=lambda b: haversine_km(lat, lng, b.lat, b.lng), default=None)
    if not nearest:
        return None
    data = _cache[normalize_component(component)][1]
    groups = [c["group"] for c in data["at_risk"] if c["district"] == nearest.district]
    return {"district": nearest.district, "groups": groups} if groups else None


# ---------------------------------------------------------------- backtest
def backtest(db: Session, component: str = "prbc", days: int = 30, today: date | None = None) -> dict:
    """Rolling-origin backtest over the last `days` days of each series: MAE of the 1..3-day forecast,
    and precision/recall for 'drops below threshold within 72 h' vs a naive last-value baseline."""
    today = today or date.today()
    ensure_history(db, today)
    abs_err, naive_err, n = 0.0, 0.0, 0
    tp = fp = fn = ntp = nfp = nfn = 0
    synthetic_used = False
    for _state, district in districts(db):
        for g in GROUPS:
            real = daily_series(db, district, component, g, False)
            synth = len(real) < MIN_REAL_DAYS
            synthetic_used |= synth
            series = daily_series(db, district, component, g, True) if synth else real
            if len(series) < days + 20:
                continue
            for cut in range(len(series) - days, len(series) - HORIZON_DAYS):
                hist, future = series[:cut], [v for _, v in series[cut:cut + HORIZON_DAYS]]
                thr = threshold_for(hist, g)
                pred = predict(hist)
                fc = [v for _, v in pred["forecast"]]
                last = hist[-1][1]
                for a, f in zip(future, fc):
                    abs_err += abs(a - f)
                    naive_err += abs(a - last)
                    n += 1
                actual = min(future) < thr
                said = risk_of(pred, thr)[0] >= 0.5
                naive = last < thr
                tp, fp, fn = tp + (said and actual), fp + (said and not actual), fn + (actual and not said)
                ntp, nfp, nfn = ntp + (naive and actual), nfp + (naive and not actual), nfn + (actual and not naive)
    def pr(a, b, c):
        return (round(a / (a + b), 3) if a + b else None, round(a / (a + c), 3) if a + c else None)
    p, r = pr(tp, fp, fn)
    np_, nr = pr(ntp, nfp, nfn)
    return {"component": component, "points": n, "mae": round(abs_err / n, 2) if n else None,
            "naive_mae": round(naive_err / n, 2) if n else None, "precision": p, "recall": r,
            "naive_precision": np_, "naive_recall": nr, "synthetic": synthetic_used}


# ---------------------------------------------------------------- donor drive
def start_drive(db: Session, district: str, group: str, component: str = "prbc", units: int = 4) -> Request:
    """Pre-emptive drive: alert eligible, compatible donors near the at-risk district's main blood bank.
    Uses the same SQL filters (rest period, 24 h limit, quiet hours) as emergencies, under kind='drive'."""
    from . import dispatch
    from .whatsapp import normalize_phone

    banks = db.scalars(select(BloodBank).where(BloodBank.district == district)).all()
    if not banks:
        raise ValueError(f"no blood bank in {district}")
    bank = sorted(banks, key=lambda b: (b.category not in ("Govt.", "Government"), b.name))[0]
    req = Request(patient_group=group, group_confirmed=True, units=units, patient_age=0, patient_gender="O",
                  hospital_name=bank.name, hospital_address=bank.address, hospital_lat=bank.lat, hospital_lng=bank.lng,
                  hospital_verified=True, hospital_check={"score": 1.0, "verified": True, "evidence": [{"source": "directory", "title": bank.name}]},
                  requester_name="Rakt Doot donor drive", requester_phone=normalize_phone(settings.whatsapp_business_number) or "919999999999",
                  component=normalize_component(component), kind="drive", allow_o_neg=group == "O-",
                  target_acceptances=units, expires_at=utcnow() + timedelta(hours=48))
    db.add(req)
    db.flush()
    dispatch.start_dispatch(db, req)
    return req
