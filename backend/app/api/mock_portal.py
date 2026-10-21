"""MOCK camp sign-up portal (A2 demo). It behaves like a government camp registration form
(captcha, Aadhaar, mobile OTP) so Rakt Doot's registration automation can be shown end to end
on synthetic data. It is clearly labelled, is not affiliated with any government site, and keeps
only the last 4 Aadhaar digits. The OTP "SMS" is delivered to the WhatsApp simulator."""
import html
import random
import re
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from ..db import session_scope
from ..models import Camp, MockPortalEntry
from ..services import whatsapp

router = APIRouter(prefix="/mock-portal", include_in_schema=False)
BANNER = ("<div style='background:#8a6412;color:#fff;padding:8px 12px;font:600 14px sans-serif'>MOCK PORTAL for the Rakt Doot demo. "
          "Synthetic data only. Not a government website.</div>")
STYLE = ("<style>body{font:16px sans-serif;margin:0;background:#f6f6f6}main{max-width:520px;margin:20px auto;background:#fff;padding:20px;"
         "border:1px solid #ddd}label{display:block;margin:10px 0 4px}input,select{width:100%;padding:8px;box-sizing:border-box}"
         "button{margin-top:16px;padding:10px 18px}.err{color:#a00}</style>")


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>{STYLE}</head>"
                        f"<body>{BANNER}<main><h1>{html.escape(title)}</h1>{body}</main></body></html>")


def _camp(db, camp_id: str) -> Camp:
    c = db.get(Camp, camp_id)
    if c is None:
        raise HTTPException(404, "camp not found")
    return c


def form_html(camp: Camp, session: str, a: int, b: int, error: str = "") -> HTMLResponse:
    err = f"<p class='err' id='error'>{html.escape(error)}</p>" if error else ""
    return page("Donor registration for blood donation camp", f"""
<p>{html.escape(camp.title)}, {camp.camp_date.isoformat()}, {html.escape(camp.address or camp.district)}</p>{err}
<form method="post" action="/mock-portal/camps/{camp.id}/register" id="reg">
<input type="hidden" name="session" value="{session}">
<label for="name">Full name</label><input id="name" name="name" required>
<label for="mobile">Mobile number</label><input id="mobile" name="mobile" required>
<label for="dob">Date of birth</label><input id="dob" name="dob" type="date" required>
<label for="gender">Gender</label><select id="gender" name="gender"><option>M</option><option>F</option><option>O</option></select>
<label for="blood_group">Blood group</label><select id="blood_group" name="blood_group">
{''.join(f'<option>{g}</option>' for g in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Don't know"])}</select>
<label for="aadhaar">Aadhaar number (12 digits)</label><input id="aadhaar" name="aadhaar" required>
<label for="captcha">Captcha: <span id="captcha-q">What is {a} + {b}?</span></label><input id="captcha" name="captcha" required>
<button type="submit">Get OTP</button></form>""")


@router.get("/camps/{camp_id}/register")
def register_form(camp_id: str):
    with session_scope() as db:
        camp = _camp(db, camp_id)
        a, b = random.randint(2, 9), random.randint(2, 9)
        session = secrets.token_urlsafe(16)
        db.add(MockPortalEntry(session=session, camp_id=camp_id, captcha_answer=str(a + b)))
        return form_html(camp, session, a, b)


@router.post("/camps/{camp_id}/register")
async def register_submit(camp_id: str, request: Request):
    f = {k: str(v).strip() for k, v in (await request.form()).items()}
    with session_scope() as db:
        camp = _camp(db, camp_id)
        entry = db.get(MockPortalEntry, f.get("session", ""))
        a, b = random.randint(2, 9), random.randint(2, 9)
        problems = []
        if entry is None or entry.camp_id != camp_id:
            raise HTTPException(400, "session expired")
        if f.get("captcha") != entry.captcha_answer:
            problems.append("Wrong captcha")
        aadhaar = re.sub(r"\D", "", f.get("aadhaar", ""))
        if not re.fullmatch(r"[2-9]\d{11}", aadhaar):
            problems.append("Aadhaar must be 12 digits")
        mobile = re.sub(r"\D", "", f.get("mobile", ""))[-10:]
        if not re.fullmatch(r"[6-9]\d{9}", mobile) and not mobile.startswith("00000"):
            problems.append("Enter a valid mobile number")
        if len(f.get("name", "")) < 2:
            problems.append("Enter your name")
        if problems:  # a fresh captcha, like real portals
            entry.captcha_answer = str(a + b)
            return form_html(camp, entry.session, a, b, "; ".join(problems))
        entry.name, entry.mobile, entry.aadhaar_last4, entry.blood_group = f["name"][:80], mobile, aadhaar[-4:], f.get("blood_group", "")[:3]
        entry.otp = f"{random.randint(0, 999999):06d}"
        full = f.get("mobile_full") or ("91" + mobile)
        whatsapp.send_sms_mock(db, full, "MOCK-PORTAL",
                               f"MOCK-PORTAL: {entry.otp} is your OTP for blood donation camp registration. Do not share it with anyone.")
        return page("Verify your mobile", f"""
<p id="otp-sent">An OTP has been sent to ******{mobile[-4:]}.</p>
<form method="post" action="/mock-portal/otp" id="otp-form"><input type="hidden" name="session" value="{entry.session}">
<label for="otp">Enter OTP</label><input id="otp" name="otp" required><button type="submit">Verify and register</button></form>""")


@router.post("/otp")
async def verify_otp(request: Request):
    f = {k: str(v).strip() for k, v in (await request.form()).items()}
    with session_scope() as db:
        entry = db.scalar(select(MockPortalEntry).where(MockPortalEntry.session == f.get("session", "")))
        if entry is None:
            raise HTTPException(400, "session expired")
        if entry.registration_no:
            return page("Registered", f"<p>Registration number: <b id='reg-no'>{entry.registration_no}</b></p>")
        entry.attempts += 1
        if f.get("otp") != entry.otp or entry.attempts > 3:
            return page("Verify your mobile", f"""<p class='err' id='error'>Invalid OTP</p>
<form method="post" action="/mock-portal/otp" id="otp-form"><input type="hidden" name="session" value="{entry.session}">
<label for="otp">Enter OTP</label><input id="otp" name="otp" required><button type="submit">Verify and register</button></form>""")
        entry.registration_no = f"MOCK-{random.randint(100000, 999999)}"
        return page("Registered", f"<p>You are registered. Registration number: <b id='reg-no'>{entry.registration_no}</b></p>")
