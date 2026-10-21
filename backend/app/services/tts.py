"""Text to speech for voice replies (WhatsApp voice notes for donors and families who prefer audio).

Providers (TTS_PROVIDER):
- sarvam: Sarvam AI bulbul (Indian voices, Hindi + English), uses STT_API_KEY (the same Sarvam key)
- edge:   Microsoft Edge neural voices via the free edge-tts service (hi-IN-SwaraNeural, en-IN-NeerjaNeural); no key
- openai: any OpenAI-compatible /audio/speech, uses LLM_API_KEY
- off
auto = sarvam if STT_API_KEY is set, else edge if the edge-tts package is installed, else off.
Never raises: a failed voice reply just means the text message stands alone."""
import asyncio
import base64
import concurrent.futures
import importlib.util
import logging
import re

import httpx

from ..config import settings

log = logging.getLogger("raktdoot.tts")
MAX_CHARS = 900


def provider() -> str:
    p = settings.tts_provider.lower()
    if p != "auto":
        return p
    if settings.stt_api_key:
        return "sarvam"
    if importlib.util.find_spec("edge_tts"):
        return "edge"
    return "off"


def speakable(text: str) -> str:
    """Drop links, phone-number punctuation noise and button hints; voice notes stay short."""
    t = re.sub(r"https?://\S+", "", text or "")
    t = re.sub(r"\n\s*-\s*", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([.,])", r"\1", t)
    return t[:MAX_CHARS]


def _edge(text: str, lang: str) -> tuple[bytes, str]:
    import edge_tts

    async def run() -> bytes:
        voice = settings.tts_voice_hi if lang == "hi" else settings.tts_voice_en
        buf = bytearray()
        async with asyncio.timeout(20):
            async for chunk in edge_tts.Communicate(text, voice).stream():
                if chunk["type"] == "audio":
                    buf += chunk["data"]
        return bytes(buf)

    with concurrent.futures.ThreadPoolExecutor(1) as ex:  # works whether or not a loop is running here
        return ex.submit(asyncio.run, run()).result(timeout=25), "audio/mpeg"


def _sarvam(text: str, lang: str) -> tuple[bytes, str]:
    r = httpx.post("https://api.sarvam.ai/text-to-speech", headers={"api-subscription-key": settings.stt_api_key}, timeout=25,
                   json={"text": text[:1500], "language_code": "hi-IN" if lang == "hi" else "en-IN", "model": "bulbul:v2",
                         "speaker": "anushka"})
    r.raise_for_status()
    return base64.b64decode("".join(r.json()["audios"])), "audio/wav"


def _openai(text: str, lang: str) -> tuple[bytes, str]:
    r = httpx.post(f"{settings.llm_base_url.rstrip('/')}/audio/speech", headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                   json={"model": "gpt-4o-mini-tts", "voice": "alloy", "input": text, "response_format": "mp3"}, timeout=25)
    r.raise_for_status()
    return r.content, "audio/mpeg"


def synthesize(text: str, lang: str = "en") -> tuple[bytes, str, str] | None:
    """(audio bytes, mime, engine) or None."""
    p = provider()
    text = speakable(text)
    if p == "off" or not text:
        return None
    try:
        data, mime = {"edge": _edge, "sarvam": _sarvam, "openai": _openai}[p](text, lang)
        return (data, mime, p) if data else None
    except Exception as e:  # noqa: BLE001
        log.warning("tts %s failed: %s", p, e)
        return None
