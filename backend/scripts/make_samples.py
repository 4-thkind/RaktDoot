"""Generate the SYNTHETIC sample images used by demo mode and the eval set (F3 slips, F9 donor cards).

    python scripts/make_samples.py      (needs Pillow; dev-only, not a runtime dependency)

Every image says SAMPLE and uses invented names. Gold labels go to data/samples/manifest.json
(demo parses) and eval/data/slips.json (field-level accuracy)."""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "samples"
EVAL = ROOT / "eval" / "data"
FONTS = ["C:/Windows/Fonts/segoesc.ttf", "C:/Windows/Fonts/Inkfree.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
PRINT_FONTS = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


SLIPS = [
    {"file": "requisition_slip.jpg", "hospital": "Safdarjung Hospital", "ward": "Surgery Ward 12", "patient_name": "R. Kumar (sample)",
     "patient_group": "B+", "units": 2, "component": "prbc", "component_text": "PRBC", "urgency": "urgent", "date": "2026-10-19"},
    {"file": "slip_platelets.jpg", "hospital": "Sir Ganga Ram Hospital", "ward": "Medicine 4", "patient_name": "S. Devi (sample)",
     "patient_group": "O+", "units": 4, "component": "platelets", "component_text": "RDP (Platelets)", "urgency": "emergency", "date": "2026-10-18"},
    {"file": "slip_plasma.jpg", "hospital": "Lok Nayak Hospital", "ward": "Burns ICU", "patient_name": "A. Khan (sample)",
     "patient_group": "AB-", "units": 3, "component": "plasma", "component_text": "FFP", "urgency": "urgent", "date": "2026-10-17"},
    {"file": "slip_whole.jpg", "hospital": "AIIMS", "ward": "Trauma Centre", "patient_name": "M. Singh (sample)",
     "patient_group": "A-", "units": 1, "component": "whole_blood", "component_text": "Whole Blood", "urgency": "routine", "date": "2026-10-16"},
]
CARD = {"file": "donor_card.jpg", "donation_date": "2026-10-20", "centre": "Indian Red Cross Society Blood Bank, New Delhi"}


def slip(s: dict) -> Image.Image:
    img = Image.new("RGB", (900, 1100), (250, 247, 238))
    d = ImageDraw.Draw(img)
    pf, hf = font(PRINT_FONTS, 30), font(FONTS, 38)
    d.text((40, 30), f"{s['hospital'].upper()}", font=font(PRINT_FONTS, 40), fill=(20, 20, 60))
    d.text((40, 85), "BLOOD REQUISITION FORM  (SAMPLE, NOT REAL)", font=pf, fill=(150, 20, 20))
    y = 170
    dd = s["date"].split("-")
    rows = [("Date", f"{dd[2]}/{dd[1]}/{dd[0]}"), ("Patient name", s["patient_name"]), ("Ward / Bed", s["ward"]),
            ("Blood group", s["patient_group"].replace("+", " +ve").replace("-", " -ve")), ("Component", s["component_text"]),
            ("No. of units", str(s["units"])), ("Urgency", s["urgency"].capitalize())]
    for label, val in rows:
        d.text((40, y), f"{label}:", font=pf, fill=(30, 30, 30))
        d.line((300, y + 40, 860, y + 40), fill=(120, 120, 120), width=2)
        d.text((310, y - 6), val, font=hf, fill=(10, 40, 140))
        y += 105
    d.text((40, y + 40), "Doctor's signature: ______________", font=pf, fill=(30, 30, 30))
    return img.rotate(1.2, expand=False, fillcolor=(250, 247, 238)).filter(ImageFilter.GaussianBlur(0.6))


def card(c: dict) -> Image.Image:
    img = Image.new("RGB", (900, 560), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 900, 90), fill=(160, 20, 40))
    d.text((30, 22), "BLOOD DONOR CARD  (SAMPLE)", font=font(PRINT_FONTS, 40), fill=(255, 255, 255))
    pf = font(PRINT_FONTS, 30)
    dd = c["donation_date"].split("-")
    for i, (k, v) in enumerate([("Donor", "Aman Verma (sample)"), ("Blood group", "O +ve"), ("Date of donation", f"{dd[2]}-{dd[1]}-{dd[0]}"),
                                ("Blood centre", c["centre"]), ("Bag no.", "SAMPLE-0042")]):
        d.text((30, 120 + i * 80), f"{k}: {v}", font=pf, fill=(20, 20, 20))
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    EVAL.mkdir(parents=True, exist_ok=True)
    manifest = {}
    gold = []
    for s in SLIPS:
        p = OUT / s["file"]
        slip(s).save(p, "JPEG", quality=82)
        fields = {k: s[k] for k in ("hospital", "ward", "patient_name", "patient_group", "units", "component", "urgency", "date")}
        manifest[s["file"]] = {"kind": "slip", "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "fields": fields}
        gold.append({"file": s["file"], "fields": fields})
    p = OUT / CARD["file"]
    card(CARD).save(p, "JPEG", quality=85)
    manifest[CARD["file"]] = {"kind": "donor_card", "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                              "fields": {"donation_date": CARD["donation_date"], "centre": CARD["centre"]}}
    old = json.loads((OUT / "manifest.json").read_text(encoding="utf-8")) if (OUT / "manifest.json").exists() else {}
    old.update(manifest)
    (OUT / "manifest.json").write_text(json.dumps(old, indent=1, ensure_ascii=False), encoding="utf-8")
    (EVAL / "slips.json").write_text(json.dumps(gold, indent=1), encoding="utf-8")
    print(f"wrote {len(manifest)} images to {OUT}", file=sys.stderr)
