"""Shared vision pipeline (F3 requisition slips, F9 donor cards).

A vision-capable model on any OpenAI-compatible endpoint (VISION_MODEL) reads the photo into JSON,
which is validated here, with a confidence per field. Without a key, demo mode recognises the
bundled SAMPLE images (by hash) and returns their fixed parse, labelled sample. Images are only
held in memory and dropped after parsing (unless KEEP_UPLOADS=true, for debugging)."""
import base64
import hashlib
import json
import logging
import re
from datetime import date, timedelta
from functools import lru_cache

from ..config import BACKEND_DIR, settings
from . import extraction, llm

log = logging.getLogger("raktdoot.vision")
SAMPLES = BACKEND_DIR / "data" / "samples"
MAX_BYTES = 5 * 1024 * 1024

SLIP_PROMPT = """You read a hospital blood requisition form from India (often handwritten). Return ONLY JSON:
{"patient_group": "A+|A-|B+|B-|AB+|AB-|O+|O-" or null, "units": int or null, "component": "prbc|platelets|plasma|whole_blood" or null,
"hospital": str or null, "ward": str or null, "urgency": "routine|urgent|emergency" or null, "date": "YYYY-MM-DD" or null,
"patient_name": str or null, "confidence": {<field>: 0..1 for each field}}
Map PRBC/PCV/packed cells -> prbc; RDP/SDP/platelet -> platelets; FFP/plasma -> plasma. Use null for anything you cannot read.
Lower the confidence for unclear handwriting. Do not guess."""

CARD_PROMPT = """You read a blood donor card or donation receipt from an Indian blood centre. Return ONLY JSON:
{"donation_date": "YYYY-MM-DD" or null, "centre": str or null, "confidence": {"donation_date": 0..1, "centre": 0..1}}
Only the date of THIS donation, not a date of birth or an expiry date. Use null if unsure."""


@lru_cache
def _manifest() -> dict:
    try:
        return json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sample_bytes(name: str) -> bytes | None:
    if name not in _manifest():
        return None
    return (SAMPLES / name).read_bytes()


def _sample_for(data: bytes) -> tuple[str, dict] | None:
    h = hashlib.sha256(data).hexdigest()
    return next(((n, m) for n, m in _manifest().items() if m.get("sha256") == h), None)


def _ask(prompt: str, data: bytes, mime: str) -> dict:
    uri = f"data:{mime or 'image/jpeg'};base64,{base64.b64encode(data).decode()}"
    return llm.chat_json(prompt, [{"type": "text", "text": "Read this image."}, {"type": "image_url", "image_url": {"url": uri}}],
                         model=settings.vision_model, timeout=40)


def _keep(data: bytes, kind: str) -> None:
    if settings.keep_uploads:
        d = BACKEND_DIR / "data" / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{kind}-{hashlib.sha256(data).hexdigest()[:12]}.jpg").write_bytes(data)


def parse_slip(data: bytes, mime: str = "image/jpeg", today: date | None = None) -> dict:
    """Requisition slip -> request fields. Never raises; 'error' set when nothing could be read."""
    if not data or len(data) > MAX_BYTES:
        return {"error": "image missing or larger than 5 MB", "fields": None}
    _keep(data, "slip")
    sample = _sample_for(data)
    if not settings.llm_api_key:
        if sample and sample[1]["kind"] == "slip":
            f = {**{k: None for k in extraction.FIELDS}, **sample[1]["fields"]}
            f["confidence"] = {k: (0.95 if f[k] is not None else 0.0) for k in extraction.FIELDS}
            f["confidence"]["ward"] = 0.55 if f.get("ward") else 0.0  # demo: show how a low-confidence field is flagged
            return {"fields": f, "engine": "sample", "sample": True, "low_confidence": extraction.low_confidence(f)}
        return {"error": "Vision is not configured on this server (VISION_MODEL / LLM_API_KEY). Try the sample slip.", "fields": None, "sample": False}
    try:
        fields = extraction.validate(_ask(SLIP_PROMPT, data, mime), today)
    except Exception as e:  # noqa: BLE001
        log.warning("slip parse failed: %s", e)
        return {"error": "Could not read the slip. Please fill the form by hand.", "fields": None}
    return {"fields": fields, "engine": f"vision:{settings.vision_model}", "sample": False,
            "low_confidence": extraction.low_confidence(fields)}


def validate_card(raw: dict, today: date, not_before: date | None = None) -> dict:
    """A donation date must be real, not in the future, and not before the alert went out."""
    try:
        d = date.fromisoformat(str(raw.get("donation_date"))[:10])
    except ValueError:
        d = None
    if d and (d > today or (not_before and d < not_before - timedelta(days=1)) or d < today - timedelta(days=30)):
        d = None
    centre = raw.get("centre") if isinstance(raw.get("centre"), str) else None
    conf = raw.get("confidence") if isinstance(raw.get("confidence"), dict) else {}
    try:
        c = float(conf.get("donation_date", 0.8 if d else 0))
    except (TypeError, ValueError):
        c = 0.0
    return {"donation_date": d, "centre": re.sub(r"\s+", " ", centre).strip()[:120] if centre else None,
            "confidence": round(max(0.0, min(1.0, c)), 2) if d else 0.0}


def parse_donor_card(data: bytes, mime: str = "image/jpeg", today: date | None = None, not_before: date | None = None) -> dict:
    today = today or date.today()
    if not data or len(data) > MAX_BYTES:
        return {"donation_date": None, "centre": None, "confidence": 0.0, "engine": "none"}
    _keep(data, "card")
    sample = _sample_for(data)
    if not settings.llm_api_key:
        if sample and sample[1]["kind"] == "donor_card":
            # the sample card is dated for the demo day; treat it as "today" so the flow can be shown any day
            out = validate_card({"donation_date": today.isoformat(), "centre": sample[1]["fields"]["centre"]}, today, not_before)
            return {**out, "engine": "sample", "sample": True}
        return {"donation_date": None, "centre": None, "confidence": 0.0, "engine": "none", "sample": False}
    try:
        return {**validate_card(_ask(CARD_PROMPT, data, mime), today, not_before), "engine": f"vision:{settings.vision_model}"}
    except Exception as e:  # noqa: BLE001
        log.warning("card parse failed: %s", e)
        return {"donation_date": None, "centre": None, "confidence": 0.0, "engine": "error"}
