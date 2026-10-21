"""eRaktKosh page knowledge: option codes and parsers for the JSON the site's own pages load.

The public Stock Availability, Blood Bank Directory and Camp Schedule pages fill their tables
from `nearbyBB.cnt?hmode=...` XHR calls that return {"data": [[cells...], ...]} with HTML in the
cells. These parsers turn those rows into our schema. They are used by the Browser-API replay
(Section 2.4), the TinyFish Fetch directory refresh (W2) and the camp finder (A1).

Only public, non-personal data is kept: blood-centre names, addresses, institutional phone
numbers and stock. Emails, camp organiser names and organiser phone numbers are dropped."""
import html
import re
from datetime import date, datetime

from ..core.compatibility import normalize_group

ORIGIN = "https://eraktkosh.mohfw.gov.in"
STOCK_PAGE = f"{ORIGIN}/BLDAHIMS/bloodbank/stockAvailability.cnt"
API = "/BLDAHIMS/bloodbank/nearbyBB.cnt"

# "Select State" option values on the live page (checked 2026-10-20)
STATE_CODES = {
    "Andaman and Nicobar Islands": "35", "Andhra Pradesh": "28", "Arunachal Pradesh": "12", "Assam": "18", "Bihar": "10",
    "Chandigarh": "94", "Chhattisgarh": "22", "Dadra And Nagar Haveli And Daman And Diu": "25", "Delhi": "97", "Goa": "30",
    "Gujarat": "24", "Haryana": "96", "Himachal Pradesh": "92", "Jammu and Kashmir": "91", "Jharkhand": "20",
    "Karnataka": "29", "Kerala": "32", "Ladakh": "37", "Lakshadweep": "31", "Madhya Pradesh": "23", "Maharashtra": "27",
    "Manipur": "14", "Meghalaya": "17", "Mizoram": "15", "Nagaland": "13", "Odisha": "21", "Puducherry": "34",
    "Punjab": "93", "Rajasthan": "98", "Sikkim": "11", "Tamil Nadu": "33", "Telangana": "36", "Tripura": "16",
    "Uttarakhand": "95", "Uttar Pradesh": "99", "West Bengal": "19",
}
STATE_ALIASES = {"nct of delhi": "Delhi", "national capital territory of delhi": "Delhi", "orissa": "Odisha"}


def state_code(state: str) -> str | None:
    s = (state or "").strip()
    s = STATE_ALIASES.get(s.lower(), s)
    for name, code in STATE_CODES.items():
        if name.lower() == s.lower():
            return code
    return None


def _norm(s: str) -> str:
    s = re.sub(r"\b(district|dist\.?)\b", "", (s or "").lower())
    s = s.replace("gurgaon", "gurugram").replace("noida", "gautam buddha nagar")
    return re.sub(r"[^a-z]+", " ", s).strip()


def match_district(wanted: str, records: list[dict]) -> str | None:
    """District option value for a district name; records are [{"id": label, "value": code}]."""
    w = _norm(wanted)
    w = re.sub(r"\bdelhi\b", "", w).strip() or w  # Nominatim says "South Delhi", eRaktKosh says "South"
    best = None
    for r in records:
        label = _norm(str(r.get("id", "")))
        if label == w:
            return str(r.get("value"))
        if w and label and (w in label or label in w) and best is None:
            best = str(r.get("value"))
    return best


def _text(cell) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", str(cell or ""))).strip()


def _lines(cell) -> list[str]:
    parts = re.split(r"<br\s*/?>", str(cell or ""), flags=re.I)
    return [re.sub(r"\s+", " ", _text(p)).strip(" ,") for p in parts]


def _phone(contact: str) -> str | None:
    m = re.search(r"Phone:\s*([^,]+)", contact or "")
    if not m:
        return None
    p = m.group(1).strip()
    return p if re.search(r"\d{6,}", p.replace(" ", "")) else None


def parse_availability(cell: str) -> tuple[dict[str, int], str]:
    text = _text(cell)
    stock = {}
    for label, n in re.findall(r"([ABO]{1,2}[+-]\s*Ve)\s*:\s*(\d+)", text, flags=re.I):
        g = normalize_group(label)
        if g:
            stock[g] = int(n)
    return stock, re.sub(r"\s+", " ", text)[:300]


def parse_stock_rows(payload: dict) -> list[dict]:
    """Rows: [sno, "name<br/>address<br/>Phone: .., Fax: .., Email: ..", category, availability html, updated, type]."""
    banks = []
    for row in (payload or {}).get("data") or []:
        if not isinstance(row, list) or len(row) < 4:
            continue
        lines = _lines(row[1])
        name = lines[0] if lines and lines[0] not in ("", "-") else None
        address = lines[1] if len(lines) > 1 and lines[1] not in ("", "-") else None
        if not name and address:  # some rows have no name: label them by the first wordy address part
            part = next((p.strip() for p in address.split(",") if re.search(r"[A-Za-z]{3}", p)), address)
            name = f"Blood centre, {part}"
        if not name:
            continue
        stock, avail = parse_availability(row[3])
        updated = _text(row[4]) if len(row) > 4 else ""
        if not updated and "live_stock" in str(row[4] if len(row) > 4 else ""):
            updated = "live"
        banks.append({
            "name": name[:200], "address": (address or "")[:300] or None, "phone": _phone(lines[2] if len(lines) > 2 else ""),
            "category": _text(row[2]) if _text(row[2]) not in ("", "null") else None,
            "type": _text(row[5]) if len(row) > 5 else None, "last_updated": updated or None,
            "availability_text": avail, "stock": stock,
        })
    return banks


def parse_directory_rows(payload: dict) -> list[dict]:
    """Rows: [sno, name, address ("..., Dist. South West"), phone, email, category, -, links html, type]."""
    out = []
    for row in (payload or {}).get("data") or []:
        if not isinstance(row, list) or len(row) < 6:
            continue
        name, address = _text(row[1]), _text(row[2])
        m = re.search(r"Dist\.\s*([^,]+)$", address)
        code = re.search(r"hospitalCode=(\d+)", str(row[7] if len(row) > 7 else ""))
        phone = _text(row[3])
        out.append({
            "name": name[:200], "address": re.sub(r",?\s*Dist\.\s*[^,]+$", "", address)[:300],
            "district": m.group(1).strip() if m else "", "phone": phone if re.search(r"\d{6,}", phone) else None,
            "category": _text(row[5]) or None, "eraktkosh_code": code.group(1) if code else None,
        })  # row[4] (email) is deliberately not kept
    return out


def parse_camp_rows(payload: dict, state: str = "") -> list[dict]:
    """Rows: [sno, "20-Oct-2026<br/>...", title, address, state, district, organiser phone, blood centre,
    organiser name, register link, time]. Organiser phone (6) and name (8) are personal: dropped."""
    out = []
    for row in (payload or {}).get("data") or []:
        if not isinstance(row, list) or len(row) < 6:
            continue
        m = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", str(row[1]))
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%d-%b-%Y").date()
        except ValueError:
            continue
        link = re.search(r"href='([^']+campid=(\d+)[^']*)'", str(row[9] if len(row) > 9 else ""))
        out.append({
            "camp_date": d, "title": _text(row[2])[:200] or "Blood donation camp", "address": _text(row[3])[:300],
            "state": _text(row[4]) or state, "district": _text(row[5]).strip(),
            "organiser": (_text(row[7]) if len(row) > 7 and _text(row[7]) != "-" else "")[:200],
            "register_url": (ORIGIN + link.group(1).replace("&amp;", "&")) if link else None,
            "external_id": link.group(2) if link else None, "time_text": _text(row[10])[:40] if len(row) > 10 else "",
        })
    return out


def stock_url(state_code_: str, district_code: str, component_code: str) -> str:
    return f"{API}?hmode=GETNEARBYSTOCKDETAILS&stateCode={state_code_}&districtCode={district_code}&bloodGroup=all&bloodComponent={component_code}&lang=0"


def district_url(state_code_: str) -> str:
    return f"{API}?hmode=GETDISTRICTLIST&selectedStateCode={state_code_}"


def directory_url(state_code_: str, district_code: str = "-1") -> str:
    return f"{ORIGIN}/BLDAHIMS/bloodbank/nearbyBBRed.cnt?hmode=GETNEARBYBLOODBANK&stateCode={state_code_}&districtCode={district_code}"


def camps_url(state_code_: str, on: date, district_code: str = "-1") -> str:
    return f"{ORIGIN}{API}?hmode=GETNEARBYCAMPS&stateCode={state_code_}&districtCode={district_code}&campDate={on.isoformat()}"
