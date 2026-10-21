"""Speech to text for WhatsApp voice notes (F4). Pluggable providers:

- sarvam:  Sarvam AI speech-to-text (Indian languages incl. Hindi/Hinglish), STT_API_KEY
- openai:  any OpenAI-compatible /audio/transcriptions (Whisper), STT_API_KEY or LLM_API_KEY
- local:   faster-whisper on CPU, if installed (optional; not in requirements.txt)
- demo:    the bundled SAMPLE voice notes return their fixed transcript; anything else fails gracefully

auto = sarvam if STT_API_KEY is set, else openai if LLM_API_KEY is set, else local if installed, else demo.
Audio is processed in memory and dropped."""
import hashlib
import importlib.util
import logging
import os
import tempfile

import httpx

from ..config import settings
from .vision import _manifest

log = logging.getLogger("raktdoot.stt")
MAX_BYTES = 16 * 1024 * 1024


def provider() -> str:
    p = settings.stt_provider.lower()
    if p != "auto":
        return p
    if settings.stt_api_key:
        return "sarvam"
    if settings.llm_api_key:
        return "openai"
    if importlib.util.find_spec("faster_whisper"):
        return "local"
    return "demo"


def _demo(data: bytes) -> dict | None:
    h = hashlib.sha256(data).hexdigest()
    for _name, m in _manifest().items():
        if m.get("kind") == "audio" and m.get("sha256") == h:
            return {"text": m["transcript"], "engine": "sample", "language": m.get("language"), "sample": True}
    return None


def _sarvam(data: bytes, mime: str) -> dict:
    files = {"file": ("voice" + _ext(mime), data, mime or "audio/ogg")}
    form = {"model": settings.stt_model or "saaras:v3", "language_code": "unknown"}
    r = httpx.post("https://api.sarvam.ai/speech-to-text", headers={"api-subscription-key": settings.stt_api_key},
                   files=files, data=form, timeout=30)
    r.raise_for_status()
    body = r.json()
    return {"text": body.get("transcript", ""), "engine": f"sarvam:{form['model']}", "language": body.get("language_code")}


def _openai(data: bytes, mime: str) -> dict:
    key = settings.stt_api_key or settings.llm_api_key
    files = {"file": ("voice" + _ext(mime), data, mime or "audio/ogg")}
    model = settings.stt_model or "whisper-1"
    r = httpx.post(f"{settings.llm_base_url.rstrip('/')}/audio/transcriptions", headers={"Authorization": f"Bearer {key}"},
                   files=files, data={"model": model}, timeout=40)
    r.raise_for_status()
    return {"text": r.json().get("text", ""), "engine": f"whisper:{model}", "language": None}


_local_model = None


def decode_16k(data: bytes, mime: str):
    """Audio bytes -> mono float32 at 16 kHz (what Whisper expects). WAV via the stdlib; OGG/Opus
    (WhatsApp voice notes), MP3, WebM and the rest via ffmpeg (installed in the Docker image)."""
    import io
    import shutil
    import subprocess
    import wave

    import numpy as np

    try:
        with wave.open(io.BytesIO(data)) as w:
            raw, ch, rate, width = w.readframes(w.getnframes()), w.getnchannels(), w.getframerate(), w.getsampwidth()
        if width != 2:
            raise wave.Error("not 16-bit PCM")
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            x = x.reshape(-1, ch).mean(axis=1)
        if rate != 16000:
            n = int(len(x) * 16000 / rate)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        return x
    except (wave.Error, EOFError):
        pass
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to decode this audio format")
    with tempfile.NamedTemporaryFile(suffix=_ext(mime), delete=False) as f:  # delete=False: Windows can't reopen an open temp file
        f.write(data)
    try:
        out = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", f.name, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                             capture_output=True, timeout=60, check=True).stdout
    finally:
        os.unlink(f.name)
    return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0


def warm() -> None:
    """Load the local Whisper model in the background at startup so the first voice note is fast."""
    global _local_model
    if provider() != "local" or _local_model is not None:
        return
    try:
        from faster_whisper import WhisperModel
        _local_model = WhisperModel(settings.stt_model or "base", device="cpu", compute_type="int8")
        log.info("local speech model ready")
    except Exception as e:  # noqa: BLE001
        log.warning("local speech model unavailable: %s", e)


def _local(data: bytes, mime: str) -> dict:
    """faster-whisper on CPU (model 'base' by default, downloaded once and cached)."""
    global _local_model
    from faster_whisper import WhisperModel

    if _local_model is None:
        _local_model = WhisperModel(settings.stt_model or "base", device="cpu", compute_type="int8")
    audio = decode_16k(data, mime)
    # Pass 1: romanised Hinglish (Whisper writes Hindi speech in Urdu script unless steered; a generic prompt steers it).
    en, _ = _local_model.transcribe(audio, language="en", initial_prompt=HINGLISH_PROMPT)
    text = " ".join(s.text.strip() for s in en).strip()
    # Pass 2: Devanagari, appended only when it carries request details the first pass missed.
    from .extraction import FIELDS, rule_extract
    got = rule_extract(text)
    if any(got[k] is None for k in ("patient_group", "hospital", "units")):
        hi, _ = _local_model.transcribe(audio, language="hi")
        hi_text = " ".join(s.text.strip() for s in hi).strip()
        extra = rule_extract(hi_text)
        if any(got[k] is None and extra[k] is not None for k in FIELDS):
            text = f"{text} / {hi_text}"
    return {"text": text, "engine": "whisper-local", "language": "hi-en"}


HINGLISH_PROMPT = "Haan, main aa raha hoon. Mujhe A positive, O negative blood chahiye, AIIMS hospital mein, teen unit. Jaldi hai."


def _ext(mime: str) -> str:
    return {"audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/webm": ".webm",
            "audio/mp4": ".m4a", "audio/aac": ".aac", "audio/amr": ".amr"}.get((mime or "").split(";")[0], ".ogg")


def transcribe(data: bytes, mime: str = "audio/ogg") -> dict:
    """{"text", "engine", "language"} or {"text": "", "error": ...}. Never raises."""
    if not data or len(data) > MAX_BYTES:
        return {"text": "", "error": "audio missing or too large", "engine": "none"}
    sample = _demo(data)
    p = provider()
    if p == "demo":
        return sample or {"text": "", "error": "Speech-to-text is not configured (STT_PROVIDER / STT_API_KEY).", "engine": "demo"}
    try:
        out = {"sarvam": _sarvam, "openai": _openai, "local": _local}[p](data, mime)
        if not out.get("text", "").strip():
            raise ValueError("empty transcript")
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("stt %s failed: %s", p, e)
        return sample or {"text": "", "error": f"{p} failed", "engine": p}
