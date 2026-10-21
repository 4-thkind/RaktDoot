"""One request-shaped schema for messy input (F2 forwarded pleas, F3 requisition slips, F4 voice
transcripts): group, units, component, hospital, city, ward, urgency, date, phone, patient name,
plus a confidence per field and a money-ask flag.

The LLM extracts when a key is set; a rule extractor always runs and fills gaps (and is the whole
engine without a key). Output is validated here: the LLM never invents a blood group outside the
eight groups, a phone outside Indian mobile format, or units outside 1..12."""
import re
from datetime import date, datetime, timedelta

from ..core.compatibility import normalize_component, normalize_group
from . import llm

FIELDS = ["patient_group", "units", "component", "hospital", "city", "ward", "urgency", "date", "phone", "patient_name"]

SYSTEM = """You extract a blood request from a message, transcript or hospital form (English, Hindi, Hinglish).
Return ONLY JSON: {"patient_group": "A+|A-|B+|B-|AB+|AB-|O+|O-" or null, "units": int or null,
"component": "prbc|platelets|plasma|whole_blood" or null, "hospital": str or null, "city": str or null, "ward": str or null,
"urgency": "routine|urgent|emergency" or null, "date": "YYYY-MM-DD" or null (date the need was written, if any),
"phone": str or null, "patient_name": str or null,
"confidence": {<each field>: number 0..1}}
Copy values that are present; never guess missing ones (use null). Never give medical advice."""

GROUP_RE = re.compile(
    r"\b(AB|A|B|O)\s*(?:\(\s*)?(\+\s*ve|-\s*ve|\+|-|−|–|positive|negative|pos|neg|\+?ve\+?|पॉज़िटिव|पॉजिटिव|नेगेटिव)(?=\W|$)", re.I)
HI_GROUP = {"बी": "B", "ए": "A", "ओ": "O", "एबी": "AB"}
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
             "paanch": 5, "panch": 5, "chhe": 6, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5}
UNITS_RE = re.compile(r"\b(\d{1,2}|" + "|".join(NUM_WORDS) + r")\s*(units?|unit|bottles?|pints?|यूनिट|बोतल)", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")
COMPONENT_RE = [("platelets", r"platelet|प्लेटलेट|\bsdp\b|\brdp\b|apheresis"), ("plasma", r"plasma|\bffp\b|प्लाज़्मा|प्लाज्मा"),
                ("whole_blood", r"whole\s*blood"), ("prbc", r"\bprbc\b|\bpcv\b|packed\s*(red)?\s*cells?|red\s*cells?")]
KNOWN_HOSPITALS = ["AIIMS", "Safdarjung", "Ram Manohar Lohia", "RML", "LNJP", "Lok Nayak", "GTB", "Guru Teg Bahadur", "Sir Ganga Ram",
                   "Ganga Ram", "Max", "Fortis", "Apollo", "Medanta", "Artemis", "BLK", "Moolchand", "Batra", "Holy Family",
                   "Deen Dayal", "DDU", "Hindu Rao", "St Stephen", "Lady Hardinge", "Kalawati", "Rajiv Gandhi Cancer", "Dharamshila",
                   "Primus", "Manipal", "Jaypee", "Kailash", "Yatharth", "Sharda", "Metro", "Paras", "ESIC"]
CITIES = ["Delhi", "New Delhi", "Noida", "Greater Noida", "Gurugram", "Gurgaon", "Faridabad", "Ghaziabad", "Mumbai", "Pune",
          "Bengaluru", "Bangalore", "Kolkata", "Chennai", "Hyderabad", "Jaipur", "Lucknow", "Chandigarh", "Saket", "Dwarka"]
MONEY_RE = re.compile(r"\bupi\b|g\s?pay|google\s*pay|phone\s?pe|paytm|\bpay\b|payment|transport\s*charge|charges?\b|\bfees?\b|"
                      r"\brs\.?\s*\d|₹|rupees|account\s*(no|number)|\bifsc\b|advance|deposit|donation\s*amount|पैसे|भुगतान|"
                      r"paise|bhej\s*do|send\s*money|cash", re.I)
URGENT_RE = re.compile(r"urgent|emergency|critical|asap|immediately|turant|jaldi|abhi|तुरंत|जल्दी|ज़रूरी|icu", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _group(text: str) -> str | None:
    m = GROUP_RE.search(text)
    if m:
        sign = m.group(2).lower()
        g = normalize_group(m.group(1) + ("-" if re.search(r"-|−|–|neg|नेगेटिव", sign) else "+"))
        if g:
            return g
    m = re.search(r"(एबी|बी|ए|ओ)\s*(पॉज़िटिव|पॉजिटिव|नेगेटिव)", text)
    if m:
        return normalize_group(HI_GROUP[m.group(1)] + ("-" if "नेगेटिव" in m.group(2) else "+"))
    return None


def _date(text: str, today: date) -> str | None:
    t = text.lower()
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:,?\s*(\d{4}))?", t)
    if m:
        try:
            return date(int(m.group(3) or today.year), MONTHS[m.group(2)], int(m.group(1))).isoformat()
        except ValueError:
            pass
    if re.search(r"\b(today|aaj)\b|आज", t):
        return today.isoformat()
    if re.search(r"\byesterday\b|\bkal raat\b", t):
        return (today - timedelta(days=1)).isoformat()
    return None


HI_HOSPITALS = {"सफदरजंग": "Safdarjung", "सफ़दरजंग": "Safdarjung", "एम्स": "AIIMS", "गंगा राम": "Sir Ganga Ram", "गंगाराम": "Sir Ganga Ram",
                "राम मनोहर लोहिया": "Ram Manohar Lohia", "लोहिया": "Ram Manohar Lohia", "लोक नायक": "Lok Nayak", "अपोलो": "Apollo",
                "मैक्स": "Max", "फोर्टिस": "Fortis", "मेदांता": "Medanta", "जीटीबी": "GTB", "दीन दयाल": "Deen Dayal", "बत्रा": "Batra",
                "होली फैमिली": "Holy Family", "हिंदू राव": "Hindu Rao"}
_NOT_NAME = {"mein", "me", "main", "ko", "at", "in", "the", "papa", "mummy", "blood", "chahiye", "needed", "need", "urgent", "a", "of",
             "for", "my", "is", "hai", "admitted", "bhai", "ka", "ki", "ke"}


ASR_GROUPS = [  # how speech recognisers spell blood groups heard in Hinglish ("ko bi positive" -> "kubi positive")
    (r"(?<!\b[AaBbOo] )\b(?:ko|ku)?(?:bhi|bee|bi|be)\s+(positive|negative)", r"B \1"),  # not "O bhi positive"
    (r"\b(?:ay|ae|ei)\s+(positive|negative)", r"A \1"),
    (r"\b(?:oh|ou)\s+(positive|negative)", r"O \1"),
    (r"\b(?:a\s?bee|ebi|abi)\s+(positive|negative)", r"AB \1"),
]


def asr_clean(text: str) -> str:
    """Speech-recognition output often splits words into syllables ('SAF-DAR-JING') and spells letters as words."""
    t = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", " ", text or "")
    for pat, rep_ in ASR_GROUPS:
        t = re.sub(pat, rep_, t, flags=re.I)
    return t


def _fuzzy_known(text: str) -> str | None:
    """'saf dar jing hospital' -> 'Safdarjung': compare 1-3 word windows, spaces removed, with known hospital names."""
    from difflib import SequenceMatcher

    words = re.findall(r"[a-z]+", text.lower())
    best, score = None, 0.0
    for h in KNOWN_HOSPITALS:
        target = h.lower().replace(" ", "")
        if len(target) < 5:
            continue
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                r = SequenceMatcher(None, "".join(words[i:i + n]), target).ratio()
                if r > score:
                    best, score = h, r
    return best if score >= 0.68 else None  # ASR misspells names ("Saftar jaan"); long names only (len >= 5 above)


def _hospital(text: str) -> str | None:
    for hi, en in HI_HOSPITALS.items():
        if hi in text or (len(hi) >= 5 and hi[:-1] in text):  # ASR often drops the last letter ("सफदरजं")
            return f"{en} Hospital" if en not in ("AIIMS",) else en
    text = asr_clean(text)
    m = re.search(r"((?:[A-Z][\w.&'-]*\s+){0,5}(?:Hospital|Medical College|Institute|Medicity|Nursing Home|Clinic|Blood (?:Bank|Centre)))", text)
    if m:
        name = re.sub(r"^(?:at|in|admitted|the|Patient|Hospital:)\s+", "", m.group(1).strip(), flags=re.I)
        if len(name) > 6:
            return name[:120]
    for h in KNOWN_HOSPITALS:
        if re.search(r"\b" + re.escape(h) + r"\b", text, re.I):
            m2 = re.search(r"\b" + re.escape(h) + r"(?:\s+[A-Z][a-z]+){0,3}", text, re.I)
            name = (m2.group(0) if m2 else h).strip()
            return re.sub(r"\s+(mein|me|main|par|pe|ka|ki|ke)\b.*$", "", name, flags=re.I)[:120]  # Hinglish postpositions
    m = re.search(r"hospital\s*[:-]\s*([^\n,]{3,80})", text, re.I)
    if m:
        return m.group(1).strip()
    fuzzy = _fuzzy_known(text)
    if fuzzy:
        return f"{fuzzy} Hospital"
    m = re.search(r"((?:[A-Za-z][\w.'&]*\s+){1,3})hospital\b", text, re.I)  # lowercase speech: "saket city hospital"
    if m:
        words = [w for w in m.group(1).split() if w.lower() not in _NOT_NAME]
        if words:
            return " ".join(w.capitalize() if w.islower() else w for w in words[-3:]) + " Hospital"
    return None


FIRST_PERSON = re.compile(r"\b(mujhe|mere|meri|mera|hume|humein|hamein|papa|mummy|maa|mom|dad|father|mother|bhai|bhaiya|behen|didi|wife|"
                          r"husband|beta|beti|nana|nani|dada|dadi|my|i need|we need)\b|मुझे|मेरे|मेरी|पापा|मम्मी|माँ|भाई|बहन|पत्नी|पति|बेटा|बेटी", re.I)
FORWARD_HINT = re.compile(r"forward|share|fwd|circulate|pls help|आगे भेजें|शेयर", re.I)


def is_request(text: str) -> bool:
    """A blood request in someone's own words, typed or spoken: a group plus a need word. Short is fine."""
    t = asr_clean(text)
    return len(t) >= 12 and bool(_group(t)) and bool(re.search(
        r"blood|khoon|khun|chahiye|chaiye|need|required|unit|hospital|platelet|plasma|खून|रक्त|चाहिए|यूनिट|अस्पताल", t, re.I))


def is_forward(text: str) -> bool:
    """Forwarded plea (someone else's contact number, or 'please forward') vs a first-person request."""
    return bool(PHONE_RE.search(text) or FORWARD_HINT.search(text))


def rule_extract(text: str, today: date | None = None) -> dict:
    today = today or date.today()
    text = asr_clean(text)
    out: dict = {k: None for k in FIELDS}
    conf: dict = {k: 0.0 for k in FIELDS}
    g = _group(text)
    if g:
        out["patient_group"], conf["patient_group"] = g, 0.9
    m = UNITS_RE.search(text)
    if m:
        v = m.group(1).lower()
        n = int(v) if v.isdigit() else NUM_WORDS.get(v)
        if n and 1 <= n <= 12:
            out["units"], conf["units"] = n, 0.85
    for comp, pat in COMPONENT_RE:
        if re.search(pat, text, re.I):
            out["component"], conf["component"] = comp, 0.85
            break
    phones = PHONE_RE.findall(text)
    if phones:
        out["phone"], conf["phone"] = "91" + re.sub(r"\D", "", phones[0]), 0.95
    h = _hospital(text)
    if h:
        out["hospital"], conf["hospital"] = h, 0.7
    for c in CITIES:
        if re.search(r"\b" + re.escape(c) + r"\b", text, re.I):
            out["city"], conf["city"] = c, 0.7
            break
    m = re.search(r"\bward\s*(?:no\.?)?\s*[:-]?\s*([\w-]{1,12})", text, re.I)
    if m:
        out["ward"], conf["ward"] = m.group(1), 0.7
    d = _date(text, today)
    if d:
        out["date"], conf["date"] = d, 0.8
    m = re.search(r"(?:patient(?:'s)?\s*name|patient|name|मरीज़? का नाम)\s*[:-]\s*([A-Za-zऀ-ॿ .]{2,40}?)(?:\n|,|\.|$)", text, re.I)
    if m:
        out["patient_name"], conf["patient_name"] = m.group(1).strip(), 0.7
    if URGENT_RE.search(text):
        out["urgency"], conf["urgency"] = "urgent", 0.7
    out["confidence"] = conf
    return out


def validate(raw: dict, today: date | None = None) -> dict:
    """Clean an LLM/vision result into the schema. Unknown or out-of-range values become null."""
    today = today or date.today()
    out: dict = {k: None for k in FIELDS}
    conf_in = raw.get("confidence") if isinstance(raw.get("confidence"), dict) else {}
    out["patient_group"] = normalize_group(str(raw.get("patient_group") or "")) if raw.get("patient_group") else None
    try:
        u = int(raw.get("units")) if raw.get("units") is not None else None
        out["units"] = u if u and 1 <= u <= 12 else None
    except (TypeError, ValueError):
        pass
    comp = str(raw.get("component") or "")
    out["component"] = normalize_component(comp) if comp else None
    for k, n in (("hospital", 120), ("city", 60), ("ward", 20), ("patient_name", 60)):
        v = raw.get(k)
        out[k] = v.strip()[:n] if isinstance(v, str) and v.strip() and v.strip().lower() not in ("null", "none", "n/a") else None
    urg = str(raw.get("urgency") or "").lower()
    out["urgency"] = urg if urg in ("routine", "urgent", "emergency") else None
    try:
        d = date.fromisoformat(str(raw.get("date"))[:10]) if raw.get("date") else None
        out["date"] = d.isoformat() if d and d <= today + timedelta(days=1) else None
    except ValueError:
        pass
    ph = re.sub(r"\D", "", str(raw.get("phone") or ""))[-10:]
    out["phone"] = "91" + ph if re.fullmatch(r"[6-9]\d{9}", ph) else None
    conf = {}
    for k in FIELDS:
        try:
            c = float(conf_in.get(k, 0.8 if out[k] is not None else 0.0))
        except (TypeError, ValueError):
            c = 0.0
        conf[k] = round(max(0.0, min(1.0, c)), 2) if out[k] is not None else 0.0
    out["confidence"] = conf
    return out


def extract(text: str, today: date | None = None) -> dict:
    """LLM first (when configured), rules fill any field the LLM left empty. Never raises."""
    text = (text or "")[:4000]
    rules = rule_extract(text, today)
    out, engine = rules, "rules"
    if llm.settings.llm_api_key:
        try:
            got = validate(llm.chat_json(SYSTEM, text, timeout=15), today)
            for k in FIELDS:
                if got[k] is None and rules[k] is not None:
                    got[k], got["confidence"][k] = rules[k], rules["confidence"][k]
            out, engine = got, "llm+rules"
        except Exception as e:  # noqa: BLE001
            llm.log.warning("extraction LLM failed, rules only: %s", e)
    out["money_ask"] = bool(MONEY_RE.search(text))
    out["engine"] = engine
    return out


def low_confidence(fields: dict, threshold: float = 0.6) -> list[str]:
    return [k for k in FIELDS if fields.get(k) is not None and fields.get("confidence", {}).get(k, 0) < threshold]


def is_plea(text: str) -> bool:
    """A forwarded blood plea or a first-person request: some length, a blood group, and a phone,
    hospital or blood keyword. Short replies like 'haan 20 min' never match."""
    if len(text or "") < 40:
        return False
    if not _group(text):
        return False
    return bool(PHONE_RE.search(text) or _hospital(text) or re.search(r"blood|khoon|khun|खून|रक्त|donor|units?", text, re.I))
