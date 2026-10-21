"""Free-text intent parser for donor replies (English, Hindi, Hinglish).

Uses any OpenAI-compatible chat endpoint when LLM_API_KEY is set; otherwise (or on any
failure) falls back to a keyword parser. Output is always validated here, and it never
triggers messaging another person directly: the bot decides what to do with it."""
import json
import logging
import re

import httpx

from ..config import settings

log = logging.getLogger("raktdoot.llm")

INTENTS = {"accept", "decline", "eta_update", "location_update", "question", "eligibility_answer", "stop", "pause", "unknown"}

SYSTEM = """You parse WhatsApp replies from blood donors in India. Messages may be English, Hindi (Devanagari) or Hinglish.
Return ONLY a JSON object with keys:
intent: one of accept, decline, eta_update, location_update, question, eligibility_answer, stop, pause, unknown
eta_minutes: integer or null
location_text: place name or null
eligibility_answer: true (the donor says YES to the question asked), false (NO), or null
pause_days: integer or null
confidence: number 0..1
reply_language: en, hi or hinglish
Context tells you whether an eligibility question is pending. If it is, decide whether the reply means yes or no to that exact question.
Example: question "alcohol in the last 24 hours?", reply "kal raat ek peg liya tha" -> eligibility_answer true.
Never give medical advice."""


def _empty(intent: str = "unknown", confidence: float = 0.0, **kw) -> dict:
    out = {"intent": intent, "eta_minutes": None, "location_text": None, "eligibility_answer": None,
           "pause_days": None, "confidence": confidence, "reply_language": "en", "engine": "rules"}
    out.update(kw)
    return out


def _validate(raw: dict) -> dict:
    out = _empty(engine="llm")
    intent = raw.get("intent")
    out["intent"] = intent if intent in INTENTS else "unknown"
    for k in ("eta_minutes", "pause_days"):
        v = raw.get(k)
        out[k] = int(v) if isinstance(v, (int, float)) and 0 < v < 100000 else None
    loc = raw.get("location_text")
    out["location_text"] = loc.strip()[:80] if isinstance(loc, str) and loc.strip() else None
    ea = raw.get("eligibility_answer")
    out["eligibility_answer"] = ea if isinstance(ea, bool) else None
    try:
        out["confidence"] = max(0.0, min(1.0, float(raw.get("confidence", 0))))
    except (TypeError, ValueError):
        out["confidence"] = 0.0
    lang = raw.get("reply_language")
    out["reply_language"] = lang if lang in ("en", "hi", "hinglish") else "en"
    return out


YES = r"\b(yes|yeah|yep|haan|han|ha|haa|ji|sure|ok|okay|theek|thik|bilkul|aa raha|aa rahi|aaunga|aaungi|aa sakta|aa sakti|coming|on my way|ready)\b|हाँ|हां|जी|आ रहा|आ रही|आऊंगा"
NO = r"\b(no|nope|nahi|nahin|nai|na|not today|cant|can't|cannot|busy|sorry|nahi ho payega)\b|नहीं|नही"
DRANK = r"\b(peg|beer|daru|drink|drank|sharab|wine|alcohol|whisky|vodka)\b|शराब|पी थी"


NUMBER_WORDS = {"बीस": "20", "दस": "10", "पंद्रह": "15", "तीस": "30", "पांच": "5", "पाँच": "5", "पच्चीस": "25", "चालीस": "40",
                "पैंतालीस": "45", "bees": "20", "bis": "20", "das": "10", "pandrah": "15", "tees": "30", "paanch": "5", "pachees": "25", "chalis": "40"}


def rule_parse(text: str, pending_question: str | None = None) -> dict:
    s = (text or "").strip().lower()
    for w, n in NUMBER_WORDS.items():  # "बीस मिनट" / "bees minute" -> "20 मिनट"
        s = re.sub(rf"(?<![\wऀ-ॿ]){w}(?=\s*(min|मिनट))", n, s)
    if not s:
        return _empty()
    if re.fullmatch(r"stop|unsubscribe|band karo", s):
        return _empty("stop", 0.95)
    m = re.fullmatch(r"pause\s*(\d{1,3})?", s)
    if m:
        return _empty("pause", 0.95, pause_days=int(m.group(1) or 30))
    yes, no = bool(re.search(YES, s)), bool(re.search(NO, s))
    if pending_question:
        if pending_question == "alcohol_24h" and re.search(DRANK, s) and not re.search(r"\b(nahi|no|never)\b", s):
            return _empty("eligibility_answer", 0.8, eligibility_answer=True)
        if yes != no:
            return _empty("eligibility_answer", 0.75, eligibility_answer=yes)
    eta = re.search(r"(\d{1,3})\s*(min|mins|minute|minutes|मिनट)", s)
    loc = re.search(r"\b(?:i'?m|i am|main|mai)\s+(?:in|at)\s+([a-z][a-z .]{1,40}?)(?:\s+(?:this|till|until|for|hoon|hun|hu)\b|[.,!]|$)", s)
    if loc and not yes:
        return _empty("location_update", 0.75, location_text=loc.group(1).strip().title())
    if s.endswith("?") or re.match(r"(is|can|what|how|kya|kab|kaise|should)\b", s):
        return _empty("question", 0.7)
    if yes and not no:
        return _empty("accept", 0.8, eta_minutes=int(eta.group(1)) if eta else None)
    if no and not yes:
        return _empty("decline", 0.8)
    if eta:
        return _empty("eta_update", 0.75, eta_minutes=int(eta.group(1)))
    return _empty()


def chat_json(system: str, user: str | list, model: str | None = None, timeout: float = 20) -> dict:
    """One JSON-mode chat completion on the configured OpenAI-compatible endpoint. Raises on any
    failure; callers own the fallback. `user` may be a content list (text + image_url parts)."""
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY not set")
    r = httpx.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={"model": model or settings.llm_model, "temperature": 0, "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=timeout,
    )
    r.raise_for_status()
    data = json.loads(r.json()["choices"][0]["message"]["content"])
    if not isinstance(data, dict):
        raise ValueError("LLM did not return a JSON object")
    return data


def parse_intent(text: str, context: str, pending_question: str | None = None) -> dict:
    if settings.llm_api_key:
        try:
            raw = chat_json(SYSTEM, f"Context: {context}\nPending eligibility question: {pending_question or 'none'}\nDonor message: {text}", timeout=12)
            return _validate(raw)
        except Exception as e:
            log.warning("LLM parse failed, using rules: %s", e)
    return rule_parse(text, pending_question)
