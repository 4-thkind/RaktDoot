"""Family guide (F13): calm, cited answers from official documents only.

Knowledge base: pages from eRaktKosh (MoHFW), the DGHS Blood Transfusion Services page and a
Government of NCT of Delhi hospital blood-bank page, fetched with TinyFish Fetch (live) or loaded
from the shipped snapshot data/guide_kb.json. Retrieval is BM25 (no keys needed); with
EMBEDDING_MODEL set, embedding similarity is blended in. With an LLM key the answer is composed
from the retrieved passages only, and must cite them; otherwise the best passage is quoted.

Rules: every answer cites a source URL; anything outside the knowledge base is refused; anything
medical or personal ends with 'ask the blood centre doctor'."""
import html
import json
import logging
import math
import re
from collections import Counter
from functools import lru_cache

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import BACKEND_DIR, settings
from ..models import GuideChunk
from . import llm

log = logging.getLogger("raktdoot.guide")
KB = BACKEND_DIR / "data" / "guide_kb.json"
SOURCES = [
    ("eRaktKosh FAQs (MoHFW)", "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/eraktkoshfaq.cnt"),
    ("eRaktKosh: About Blood Donation (MoHFW)", "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/donateblood.cnt"),
    ("DGHS: Blood Transfusion Services / NBTC (MoHFW)", "https://dghs.mohfw.gov.in/bts.php"),
    ("Blood bank, Dr. Baba Saheb Ambedkar Hospital (Govt. of NCT of Delhi)", "https://bsah.delhi.gov.in/bsah/blood-donation"),
]
MIN_SCORE = 3.0
HI_EN = {"शराब": "alcohol", "दारू": "alcohol", "उम्र": "age", "आयु": "age", "वज़न": "weight", "वजन": "weight", "कितनी बार": "how often",
         "खाना": "eat", "खाएं": "eat", "टैटू": "tattoo", "एंटीबायोटिक": "antibiotics", "दवा": "medication", "पैसे": "charges",
         "शुल्क": "charges", "फ़ीस": "charges", "क्रॉस": "cross matching", "रिप्लेसमेंट": "replacement donor", "समय": "time takes",
         "कितना समय": "how long takes minutes", "प्लेटलेट": "platelet", "कैंप": "camps", "शिविर": "camps", "जांच": "tests screening",
         "दान": "donate donation", "रक्तदान": "blood donation", "बाद": "after donation", "नुकसान": "side effects",
         "kitni baar": "how often", "kab": "how often", "daru": "alcohol", "sharab": "alcohol", "paise": "charges", "kharcha": "charges"}
# the question itself must be about blood or donation; generic words like "stock" or "age" alone are not enough
DOMAIN = re.compile(r"blood|donat|donor|platelet|plasma|transfus|eraktkosh|cross.?match|replacement card|haemo|hemo|"
                    r"thalass|nbtc|रक्त|खून|दान|डोनर|प्लेटलेट", re.I)
PERSONAL_MEDICAL = re.compile(r"\b(i|me|my|mine|main|mera|meri|mujhe|can i|should i)\b.*\b(medic|tablet|pill|antibiotic|pregnan|diabet|"
                              r"bp|pressure|surgery|operation|tattoo|fever|disease|illness|cancer|hiv|hepatitis|period|vaccine|covid)", re.I)
DOCTOR = {"en": "For your own situation, please ask the blood centre doctor.", "hi": "अपनी स्थिति के लिए कृपया ब्लड सेंटर के डॉक्टर से पूछें।"}


# ---------------------------------------------------------------- building the knowledge base
def html_to_passages(raw: str) -> list[str]:
    t = re.sub(r"(?is)<(script|style|nav|header|footer)\b.*?</\1>", " ", raw)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    lines = [re.sub(r"\s+", " ", ln).strip(" #") for ln in t.splitlines()]
    lines = [ln for ln in lines if len(ln) > 25 and (ln.endswith((".", "?", ")")) or len(ln) > 70)
             and not re.search(r"Designed and Dev|Appointment for Blood Bank|Ministry of Health and Family Welfare$", ln)]
    passages, cur = [], ""
    for ln in lines:
        if cur.endswith("?"):  # keep an FAQ question with its answer
            cur += " " + ln
            passages.append(cur)
            cur = ""
            continue
        if len(cur) + len(ln) > 420 and cur:
            passages.append(cur)
            cur = ""
        cur = (cur + " " + ln).strip()
    if cur:
        passages.append(cur)
    return [p for p in passages if len(p) > 40 and not p.endswith("?")]


def build(via: str = "auto") -> list[dict]:
    """Fetch every source (TinyFish Fetch when live, plain HTTPS otherwise) and split into passages."""
    from . import tinyfish_client

    use_tf = settings.tinyfish_live if via == "auto" else via == "tinyfish"
    pages = tinyfish_client.fetch_sync([u for _, u in SOURCES], "family_guide") if use_tf else {}
    chunks = []
    for title, url in SOURCES:
        raw = pages.get(url)
        how = "tinyfish_fetch" if raw else "direct_https"
        if not raw:
            r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (RaktDoot guide builder)"}, timeout=40)
            raw = r.content.decode("utf-8", errors="replace")
        passages = html_to_passages(raw) if "<" in raw else [p for p in re.split(r"\n{2,}", raw) if len(p) > 40]
        chunks += [{"source_title": title, "source_url": url, "text": p, "fetched_via": how} for p in passages]
    return chunks


def load(db: Session, chunks: list[dict] | None = None) -> int:
    """Replace the guide_chunks table with the snapshot (or freshly built chunks)."""
    if chunks is None:
        try:
            chunks = json.loads(KB.read_text(encoding="utf-8"))["chunks"]
        except (OSError, ValueError, KeyError):
            return 0
    db.execute(GuideChunk.__table__.delete())
    for c in chunks:
        db.add(GuideChunk(source_title=c["source_title"], source_url=c["source_url"], text=c["text"],
                          fetched_via=c.get("fetched_via", "snapshot"), embedding=c.get("embedding")))
    _index.cache_clear()
    return len(chunks)


# ---------------------------------------------------------------- retrieval
def _tok(s: str) -> list[str]:
    s = s.lower()
    for hi, en in HI_EN.items():
        if hi in s:
            s += " " + en
    return [t for t in re.findall(r"[a-z]+|\d+", s) if len(t) > 2 and t not in _STOP]


_STOP = {"the", "and", "for", "you", "your", "are", "can", "what", "how", "who", "with", "this", "that", "from", "have", "has",
         "any", "our", "will", "kya", "hai", "hain", "mein", "should", "does", "into", "there", "they", "their", "been", "about"}


@lru_cache(maxsize=1)
def _index(_version: int = 0) -> dict:
    from ..db import session_scope
    with session_scope() as db:
        rows = [(c.id, c.source_title, c.source_url, c.text, c.embedding) for c in db.scalars(select(GuideChunk)).all()]
    docs = [_tok(t) for _, _, _, t, _ in rows]
    df = Counter(t for d in docs for t in set(d))
    avg = sum(len(d) for d in docs) / max(1, len(docs))
    return {"rows": rows, "docs": [Counter(d) for d in docs], "lens": [len(d) for d in docs], "df": df, "n": len(docs), "avg": avg}


def search(query: str, k: int = 4) -> list[tuple[float, dict]]:
    ix = _index()
    q = _tok(query)
    scores = []
    for i, tf in enumerate(ix["docs"]):
        s = 0.0
        for t in set(q):
            if t not in tf:
                continue
            idf = math.log(1 + (ix["n"] - ix["df"][t] + 0.5) / (ix["df"][t] + 0.5))
            s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * ix["lens"][i] / max(1, ix["avg"])))
        if s > 0:
            cid, title, url, text, _emb = ix["rows"][i]
            scores.append((s, {"id": cid, "title": title, "url": url, "text": text}))
    scores.sort(key=lambda x: -x[0])
    return scores[:k]


def _best_sentences(text: str, query: str, n: int = 2) -> str:
    sents = re.split(r"(?<=[.?!])\s+", text)
    q = set(_tok(query))
    ranked = sorted(range(len(sents)), key=lambda i: -len(q & set(_tok(sents[i]))))
    keep = sorted(ranked[:n])
    return " ".join(sents[i] for i in keep).strip()


ANSWER_SYSTEM = """You answer questions from families and blood donors in India using ONLY the numbered passages given.
Return JSON {"answer": str or null, "citations": [passage numbers used]}. Write 1-3 short, calm sentences in {lang}.
If the passages do not answer the question, return {"answer": null, "citations": []}. Never add facts that are not in the passages.
Never give personal medical advice."""


def answer(question: str, lang: str = "en") -> dict:
    """{"answer", "sources": [{title, url}], "refused": bool, "engine"}"""
    lang = lang if lang in ("en", "hi") else "en"
    q = (question or "").strip()[:500]
    hits = search(q) if q else []
    if not q or not DOMAIN.search(q + " " + " ".join(_tok(q))) or not hits or hits[0][0] < MIN_SCORE:
        from .messages import t
        return {"answer": t("guide_refuse", lang), "sources": [], "refused": True, "engine": "rules"}
    personal = bool(PERSONAL_MEDICAL.search(q))
    text, used, engine = None, [hits[0][1]], "extractive"
    if settings.llm_api_key:
        try:
            ctx = "\n".join(f"[{i + 1}] {h['text']}" for i, (_, h) in enumerate(hits))
            raw = llm.chat_json(ANSWER_SYSTEM.replace("{lang}", "Hindi" if lang == "hi" else "English"), f"Passages:\n{ctx}\n\nQuestion: {q}", timeout=15)
            cites = [c for c in raw.get("citations") or [] if isinstance(c, int) and 1 <= c <= len(hits)]
            if isinstance(raw.get("answer"), str) and raw["answer"].strip() and cites:
                text, used, engine = raw["answer"].strip()[:700], [hits[c - 1][1] for c in cites], "llm"
            elif raw.get("answer") is None:
                from .messages import t
                return {"answer": t("guide_refuse", lang), "sources": [], "refused": True, "engine": "llm"}
        except Exception as e:  # noqa: BLE001
            log.info("guide LLM failed, extractive answer: %s", e)
    if text is None:
        text = _best_sentences(hits[0][1]["text"], q)
        if lang == "hi":
            text = "आधिकारिक स्रोत (अंग्रेज़ी में): " + text
    if personal:
        text += " " + DOCTOR[lang]
    sources = list({h["url"]: {"title": h["title"], "url": h["url"]} for h in used}.values())
    return {"answer": text, "sources": sources, "refused": False, "engine": engine}


def ensure_loaded(db: Session) -> None:
    if not db.scalar(select(func.count()).select_from(GuideChunk)):
        load(db)
