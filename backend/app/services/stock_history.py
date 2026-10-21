"""Append-only stock snapshots (S1). Every successful live lookup, replay or batch sweep adds one row
per (bank, group). Synthetic rows (for the radar demo) are flagged and never mixed up with real ones."""
import logging

from ..db import session_scope, utcnow
from ..models import StockHistory

log = logging.getLogger("raktdoot.history")


def record(state: str, district: str, component: str, banks: list[dict], source: str) -> int:
    """Never raises: history is a by-product of a lookup and must not break it."""
    now = utcnow()
    n = 0
    try:
        with session_scope() as db:
            for b in banks:
                for g, units in (b.get("stock") or {}).items():
                    db.add(StockHistory(state=state, district=district, component=component, bank_name=b["name"][:200],
                                        blood_group=g, units=int(units), source=source, synthetic=False, observed_at=now))
                    n += 1
    except Exception as e:  # noqa: BLE001
        log.warning("history write failed: %s", e)
        return 0
    return n
