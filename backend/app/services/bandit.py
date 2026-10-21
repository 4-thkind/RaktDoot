"""Message bandit (F11): learn online which donor-alert wording gets the most acceptances.

Thompson sampling with a Beta-Bernoulli posterior per (variant, segment). Reward = the donor
tapped "I can donate" (1) or declined / never answered within the alert's life (0).
Segments: language x first-time/repeat donor.

WhatsApp constraint: an alert to a donor outside the 24 h service window must be an approved
template, so every variant is registered as its own template (docs/whatsapp-templates.md);
inside the window the same text goes out as a free-form message."""
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import BanditArm

VARIANTS = ["standard", "urgent", "distance", "why_you", "short"]
HISTORY_MAX = 300


def segment(donor) -> str:
    lang = donor.language if donor.language in ("en", "hi") else "en"
    return f"{lang}:{'repeat' if (donor.donations_confirmed or 0) > 0 else 'new'}"


def _arm(db: Session, variant: str, seg: str, simulated: bool) -> BanditArm:
    arm = db.scalar(select(BanditArm).where(BanditArm.variant == variant, BanditArm.segment == seg, BanditArm.simulated.is_(simulated)))
    if arm is None:
        arm = BanditArm(variant=variant, segment=seg, alpha=1.0, beta=1.0, pulls=0, simulated=simulated, history=[])
        db.add(arm)
        db.flush()
    return arm


def choose(db: Session, seg: str, rng: random.Random | None = None, simulated: bool = False) -> str:
    if not settings.bandit_enabled and not simulated:
        return "standard"
    rng = rng or random.Random()
    best, best_draw = "standard", -1.0
    for v in VARIANTS:
        arm = _arm(db, v, seg, simulated)
        draw = rng.betavariate(arm.alpha, arm.beta)
        if draw > best_draw:
            best, best_draw = v, draw
    return best


def update(db: Session, variant: str, seg: str, reward: int, simulated: bool = False) -> None:
    if variant not in VARIANTS:
        return
    arm = _arm(db, variant, seg, simulated)
    arm.alpha += 1 if reward else 0
    arm.beta += 0 if reward else 1
    arm.pulls += 1
    hist = list(arm.history or [])
    hist.append([arm.pulls, round(arm.alpha / (arm.alpha + arm.beta), 4)])
    arm.history = hist[-HISTORY_MAX:]


def posteriors(db: Session, simulated: bool = False) -> list[dict]:
    rows = db.scalars(select(BanditArm).where(BanditArm.simulated.is_(simulated)).order_by(BanditArm.segment, BanditArm.variant)).all()
    return [{"variant": a.variant, "segment": a.segment, "mean": round(a.alpha / (a.alpha + a.beta), 4), "pulls": a.pulls,
             "accepts": int(a.alpha - 1), "history": a.history or []} for a in rows]


# Hidden "true" acceptance rates used ONLY by the labelled simulation on /admin and in tests.
SIM_TRUE_RATES = {"standard": 0.18, "urgent": 0.22, "distance": 0.20, "why_you": 0.30, "short": 0.15}


def simulate(db: Session, n: int = 600, seed: int = 7, true_rates: dict | None = None, seg: str = "sim") -> dict:
    """Simulated donors with a hidden true rate per variant (clearly labelled synthetic)."""
    rates = true_rates or SIM_TRUE_RATES
    rng = random.Random(seed)
    counts = {v: 0 for v in VARIANTS}
    for _ in range(n):
        v = choose(db, seg, rng, simulated=True)
        counts[v] += 1
        update(db, v, seg, int(rng.random() < rates[v]), simulated=True)
    best_true = max(rates, key=rates.get)
    return {"pulls": counts, "true_best": best_true, "chosen_most": max(counts, key=counts.get), "true_rates": rates}
