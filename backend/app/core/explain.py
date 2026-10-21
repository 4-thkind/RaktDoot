"""'Why you' line for donor alerts (F12). Deterministic templating from the ranking features and the
shortage signal: cheap, safe, fast, and testable. No LLM."""
from ..core.compatibility import GROUPS

RARE = {g for g in GROUPS if g.endswith("-")}

TEXT = {
    "near": {"en": "You're {d} km away", "hi": "आप सिर्फ़ {d} किमी दूर हैं"},
    "short": {"en": "{g} is short in {district} today", "hi": "आज {district} में {g} की कमी है"},
    "rare_exact": {"en": "your group {g} is rare and an exact match", "hi": "आपका ग्रुप {g} दुर्लभ है और बिल्कुल मेल खाता है"},
    "exact": {"en": "your group is an exact match", "hi": "आपका ग्रुप बिल्कुल मेल खाता है"},
    "responsive": {"en": "you've answered quickly before", "hi": "आपने पहले भी जल्दी जवाब दिया है"},
    "time": {"en": "you usually reply around this time", "hi": "आप अक्सर इस समय जवाब देते हैं"},
    "can_give": {"en": "you can give to this patient", "hi": "आप इस मरीज़ को दे सकते हैं"},
    "and": {"en": " and ", "hi": " और "},
}


def _t(key: str, lang: str, **kw) -> str:
    entry = TEXT[key]
    return entry.get(lang, entry["en"]).format(**kw)


def reasons(features: dict, distance_km: float, donor_group: str, patient_group: str, shortage: dict | None = None) -> list[str]:
    """Reason keys in priority order. `shortage` = {"district": str, "groups": [groups at risk]} from the radar."""
    out = []
    if shortage and patient_group in (shortage.get("groups") or []):
        out.append("short")
    if distance_km <= 3:
        out.append("near")
    if donor_group == patient_group:
        out.append("rare_exact" if donor_group in RARE else "exact")
    if features.get("response_rate", 0) >= 0.7:
        out.append("responsive")
    if features.get("time_of_day_fit", 0) >= 0.6:
        out.append("time")
    if "near" not in out:
        out.append("near")  # distance is always true and useful as a fallback
    return out


def why_you(features: dict, distance_km: float, donor_group: str, patient_group: str, lang: str = "en",
            shortage: dict | None = None) -> str:
    """One line, two reasons at most: 'You're 2.1 km away and B− is short in South Delhi today.'"""
    keys = reasons(features, distance_km, donor_group, patient_group, shortage)[:2]
    kw = {"d": f"{distance_km:.1f}", "g": patient_group.replace("-", "−"), "district": (shortage or {}).get("district", "")}
    if "near" in keys:  # lead with distance, it reads naturally
        keys = ["near"] + [k for k in keys if k != "near"]
    parts = [_t(k, lang, **kw) for k in keys]
    line = _t("and", lang).join(parts)
    return line[0].upper() + line[1:] + ("।" if lang == "hi" else ".")
