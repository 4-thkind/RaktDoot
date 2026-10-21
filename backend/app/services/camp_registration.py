"""Assisted camp registration (A2), on the donor's explicit consent.

Rakt Doot fills the camp's sign-up form for the donor with the details they gave us at JOIN (name,
mobile, date of birth, gender, blood group), solves the captcha, submits, and then passes on the OTP
the donor receives. Aadhaar is asked for at that moment, sent once to the portal, and never stored
by Rakt Doot (the chat log keeps a masked copy).

Engines:
- form_filler: reads the form's HTML and posts it like a browser would (works offline; used for the
  built-in MOCK portal at /mock-portal).
- tinyfish_agent: when CAMP_PORTAL_URL points at a public portal and TINYFISH_API_KEY is set, a TinyFish
  Agent fills the details page (captcha included) and the OTP step is posted directly."""
import logging
import re
import time

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Camp, CampRegistration, Donor
from . import tinyfish_client

log = logging.getLogger("raktdoot.campreg")

AGENT_GOAL = """This is a blood donation camp registration form. Fill it in exactly with:
Full name: {name}; Mobile number: {mobile}; Date of birth: {dob}; Gender: {gender}; Blood group: {group}; Aadhaar number: {aadhaar}.
Solve the captcha shown on the page, then click "Get OTP". Do not submit anything else.
Return the value of the hidden "session" field of the OTP form, and whether the page says an OTP was sent."""
AGENT_SCHEMA = {"type": "object", "properties": {"session": {"type": "string", "nullable": True}, "otp_sent": {"type": "boolean"},
                                                 "error": {"type": "string", "nullable": True}}, "required": ["otp_sent"]}


def portal_base() -> str:
    return (settings.camp_portal_url or f"{settings.public_api_base.rstrip('/')}/mock-portal").rstrip("/")


def _client() -> httpx.Client:
    return httpx.Client(base_url=portal_base(), timeout=30, follow_redirects=True)


def _hidden(html: str, name: str) -> str | None:
    m = re.search(rf'name="{name}" value="([^"]+)"', html)
    return m.group(1) if m else None


def solve_captcha(html: str) -> str | None:
    """Arithmetic captcha ('What is 7 + 4?'). Image captchas would go to the TinyFish agent instead."""
    m = re.search(r"What is (\d+)\s*([+\-x*])\s*(\d+)", html)
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    return str(a + b if op == "+" else a - b if op == "-" else a * b)


def _error(html: str) -> str:
    m = re.search(r"id='error'>([^<]+)<", html)
    return m.group(1) if m else "unexpected page"


def details_for(donor: Donor) -> dict:
    return {"name": donor.name, "mobile": donor.phone[-10:], "mobile_full": donor.phone, "dob": donor.dob.isoformat() if donor.dob else "",
            "gender": donor.gender, "blood_group": donor.blood_group}


def _fill_form(reg: CampRegistration, camp: Camp, details: dict, aadhaar: str) -> str:
    with _client() as c:
        for attempt in (1, 2):
            page = c.get(f"/camps/{camp.id}/register").text
            session, answer = _hidden(page, "session"), solve_captcha(page)
            reg.steps = reg.steps + [f"opened sign-up form (attempt {attempt})", f"solved captcha: {answer}"]
            if not session or not answer:
                raise RuntimeError("form layout not recognised")
            res = c.post(f"/camps/{camp.id}/register", data={**details, "aadhaar": aadhaar, "captcha": answer, "session": session}).text
            if "id=\"otp-sent\"" in res:
                reg.steps = reg.steps + ["submitted details", "portal sent OTP to the donor's mobile"]
                return _hidden(res, "session") or session
            reg.steps = reg.steps + [f"portal said: {_error(res)}"]
            if "captcha" not in _error(res).lower():
                raise RuntimeError(_error(res))
    raise RuntimeError("captcha not accepted")


def _agent_fill(reg: CampRegistration, camp: Camp, details: dict, aadhaar: str) -> str:
    from tinyfish import TinyFish

    started = time.monotonic()
    goal = AGENT_GOAL.format(name=details["name"], mobile=details["mobile"], dob=details["dob"], gender=details["gender"],
                             group=details["blood_group"], aadhaar=aadhaar)
    run = TinyFish(api_key=settings.tinyfish_api_key, timeout=120).agent.run(url=f"{portal_base()}/camps/{camp.id}/register",
                                                                              goal=goal, output_schema=AGENT_SCHEMA)
    result = run.result or {}
    ok = str(run.status).endswith("COMPLETED") and result.get("otp_sent") and result.get("session")
    tinyfish_client.record_run("agent", "camp_register", "ok" if ok else "failed", started, camp.title[:80], run.run_id,
                               run.num_of_steps, None if ok else str(result.get("error") or run.error), source="camp_portal")
    if not ok:
        raise RuntimeError(str(result.get("error") or "agent could not submit the form"))
    reg.steps = reg.steps + [f"TinyFish agent filled the form and solved the captcha (run {run.run_id})", "portal sent OTP"]
    return result["session"]


def start(db: Session, camp: Camp, details: dict, aadhaar: str, donor_id: str | None = None) -> CampRegistration:
    """Fill the details page. The Aadhaar number is used here once and not stored."""
    reg = CampRegistration(camp_id=camp.id, donor_id=donor_id, phone=details["mobile_full"], steps=[], status="started",
                           engine="tinyfish_agent" if settings.camp_portal_url and settings.tinyfish_live else "form_filler")
    db.add(reg)
    db.commit()  # the portal writes its own rows (the OTP SMS); don't hold a SQLite write lock across the call
    try:
        fill = _agent_fill if reg.engine == "tinyfish_agent" else _fill_form
        reg.portal_session = fill(reg, camp, details, re.sub(r"\D", "", aadhaar))
        reg.status = "otp_sent"
    except Exception as e:  # noqa: BLE001
        log.warning("camp registration failed: %s", e)
        reg.status, reg.error = "failed", str(e)[:200]
    db.commit()
    return reg


def finish(db: Session, reg: CampRegistration, otp: str) -> CampRegistration:
    db.commit()
    with _client() as c:
        res = c.post("/otp", data={"session": reg.portal_session or "", "otp": re.sub(r"\D", "", otp)}).text
    m = re.search(r"id='reg-no'>([^<]+)<", res)
    if m:
        reg.status, reg.portal_ref = "registered", m.group(1)
        reg.steps = reg.steps + ["entered OTP", f"registered: {reg.portal_ref}"]
    else:
        reg.steps = reg.steps + [f"OTP rejected: {_error(res)}"]
    db.commit()
    return reg


def mask_aadhaar(text: str) -> str:
    return re.sub(r"\b(\d{4})\s?(\d{4})\s?(\d{4})\b", lambda m: f"XXXX XXXX {m.group(3)}", text or "")
