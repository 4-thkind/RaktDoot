"""WhatsApp conversation logic for donors: onboarding, alert replies, the eligibility
pre-screen, follow-ups, STOP / PAUSE. Channel-agnostic: webhooks and the simulator both
call handle_inbound()."""
import re
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import eligibility
from ..core.compatibility import GROUPS, normalize_group
from ..db import utcnow
from ..models import Donation, Donor, Notification, Profile, Request
from . import dispatch, geocode, whatsapp
from .llm import parse_intent
from .messages import b, t

CONFIDENCE_MIN = 0.7


def handle_inbound(db: Session, phone: str, text: str = "", button_id: str | None = None,
                   location: dict | None = None, wa_id: str | None = None) -> None:
    text = (text or "").strip()
    whatsapp.log_inbound(db, phone, text or (f"[button] {button_id}" if button_id else "[location]" if location else ""),
                         {"button_id": button_id, "location": location}, wa_id)
    conv = whatsapp.conversation(db, phone)
    donor = db.scalar(select(Donor).where(Donor.phone == phone))
    lang = donor.language if donor else conv.data.get("lang", "en")

    if donor:
        hours = list(donor.reply_hours or [])[-49:]
        donor.reply_hours = hours + [dispatch.local_now().hour]

    # "1" / "2" replies (Twilio, or people who type instead of tapping) map to the last buttons sent
    if not button_id and text.isdigit() and conv.last_buttons and 1 <= int(text) <= len(conv.last_buttons):
        button_id = conv.last_buttons[int(text) - 1]

    word = text.upper()
    if word in ("STOP", "UNSUBSCRIBE"):
        if donor:
            donor.opted_out = True
        for profile in db.scalars(select(Profile).where(Profile.phone == phone)):
            profile.whatsapp_consent = False
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, phone, t("stopped", lang))
        return
    m = re.fullmatch(r"PAUSE\s*(\d{1,3})?", word)
    if m and donor:
        days = int(m.group(1) or 30)
        donor.paused_until = utcnow() + timedelta(days=days)
        whatsapp.send(db, phone, t("paused", lang, days=days))
        return
    if word in ("JOIN", "START", "REGISTER", "HI", "HELLO") and not conv.state.startswith("ob_"):
        return _start_onboarding(db, conv, donor, phone)

    if conv.state.startswith("ob_"):
        return _onboarding(db, conv, phone, text, button_id, location)

    if button_id:
        return _button(db, phone, donor, conv, button_id)

    if not donor:
        whatsapp.send(db, phone, t("not_registered", lang))
        return

    if location:
        donor.lat, donor.lng, donor.location_label = location["lat"], location["lng"], location.get("name") or "shared location"
        whatsapp.send(db, phone, t("location_updated", lang, place=donor.location_label))
        return

    _free_text(db, phone, donor, conv, text)


# ------------------------------------------------------------------ buttons
def _own_notification(db: Session, phone: str, nid: str) -> Notification | None:
    n = db.get(Notification, nid)
    return n if n and n.donor.phone == phone else None  # never act on someone else's alert


def _button(db: Session, phone: str, donor: Donor | None, conv, button_id: str) -> None:
    parts = button_id.split(":")
    kind = parts[0]
    n = _own_notification(db, phone, parts[1]) if len(parts) > 1 and kind in ("acc", "dec", "el", "ow", "fu") else None
    lang = donor.language if donor else "en"
    if n is None:  # stale or foreign button
        whatsapp.send(db, phone, t("help", lang))
        return
    if kind == "acc":
        return accept(db, n, conv)
    if kind == "dec":
        return decline(db, n)
    if kind == "el" and len(parts) == 4:
        return answer(db, n, conv, parts[2], parts[3] == "y")
    if kind == "ow" and len(parts) == 3:
        return on_way(db, n, parts[2] == "y")
    if kind == "fu" and len(parts) == 3:
        return followup(db, n, parts[2])
    whatsapp.send(db, phone, t("help", lang))


def accept(db: Session, n: Notification, conv, eta: int | None = None) -> None:
    donor, req = n.donor, n.request
    lang = donor.language
    if n.status not in dispatch.PENDING:
        if n.status == "cancelled":
            whatsapp.send(db, donor.phone, t("already_covered", lang))
        return
    n.responded_at = utcnow()
    donor.alerts_responded += 1
    donor.alerts_accepted += 1
    if req.status not in ("dispatching", "needs_public_share"):
        n.status = "cancelled"
        whatsapp.send(db, donor.phone, t("already_covered", lang))
        return
    n.status = "accepted"
    n.eta_minutes = eta
    conv.state, conv.data = "prescreen", {"nid": n.id}
    whatsapp.send(db, donor.phone, t("pre_screen_intro", lang))
    _ask_next(db, n)


def _ask_next(db: Session, n: Notification) -> None:
    q = eligibility.next_question(n.eligibility_answers or {})
    lang = n.donor.language
    whatsapp.send(db, n.donor.phone, q.get(lang, q["en"]),
                  buttons=[(f"el:{n.id}:{q['id']}:y", b("yes", lang)), (f"el:{n.id}:{q['id']}:n", b("no", lang))])


def answer(db: Session, n: Notification, conv, qid: str, yes: bool) -> None:
    donor, req = n.donor, n.request
    lang = donor.language
    if n.status != "accepted":
        if n.status == "cancelled":
            whatsapp.send(db, donor.phone, t("already_covered", lang))
        return
    if eligibility.question(qid) is None:
        return
    answers = dict(n.eligibility_answers or {})
    answers[qid] = yes
    # our own records override a "no" to the recent-donation question
    if qid == "donated_recently" and eligibility.in_rest_period(donor.last_donation_date, donor.gender, dispatch.local_today()):
        answers[qid] = True
    n.eligibility_answers = answers

    if eligibility.answers_disqualify(answers):
        n.status = "ineligible"
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, donor.phone, t("ineligible", lang))
        return
    if eligibility.next_question(answers):
        return _ask_next(db, n)

    conv.state, conv.data = "idle", {}
    if req.status not in ("dispatching", "needs_public_share"):
        n.status = "cancelled"
        whatsapp.send(db, donor.phone, t("already_covered", lang))
        return
    connect(db, n)


def connect(db: Session, n: Notification) -> None:
    donor, req = n.donor, n.request
    lang = donor.language
    n.status, n.connected_at = "connected", utcnow()
    req.first_acceptance_at = req.first_acceptance_at or n.connected_at
    map_link = f"https://maps.google.com/?q={req.hospital_lat},{req.hospital_lng}"
    params = {"name": donor.name.split()[0], "hospital": req.hospital_name, "ref": req.id[:6].upper(),
              "requester": req.requester_name, "phone": req.requester_phone, "map": map_link}
    whatsapp.send(db, donor.phone, t("connected", lang, **params), template=("connected", params, lang))
    whatsapp.send(db, donor.phone, req.hospital_name,
                  location={"lat": req.hospital_lat, "lng": req.hospital_lng, "name": req.hospital_name, "address": req.hospital_address or ""})
    dispatch.check_target(db, req)


def decline(db: Session, n: Notification) -> None:
    if n.status not in dispatch.PENDING:
        return
    n.status, n.responded_at = "declined", utcnow()
    n.donor.alerts_responded += 1
    whatsapp.send(db, n.donor.phone, t("declined", n.donor.language))


def on_way(db: Session, n: Notification, yes: bool) -> None:
    lang = n.donor.language
    if n.status != "connected":
        return
    if yes:
        whatsapp.send(db, n.donor.phone, t("onway_ack", lang))
        return
    n.status = "no_show"
    n.donor.no_shows += 1
    whatsapp.send(db, n.donor.phone, t("noshow_ack", lang))
    dispatch.reopen_if_short(db, n.request)


def followup(db: Session, n: Notification, choice: str) -> None:
    donor = n.donor
    lang = donor.language
    if n.status != "connected":
        return
    if choice == "y":
        today = dispatch.local_today()
        n.status = "donated"
        donor.last_donation_date = today
        donor.donations_confirmed += 1
        db.add(Donation(donor_id=donor.id, request_id=n.request_id, donated_on=today, confirmed_by="donor"))
        whatsapp.send(db, donor.phone, t("donation_thanks", lang, days=eligibility.rest_days(donor.gender)))
    elif choice == "d":
        n.status = "deferred"
        whatsapp.send(db, donor.phone, t("deferred_ack", lang))
    else:
        n.status = "no_show"
        donor.no_shows += 1
        whatsapp.send(db, donor.phone, t("noshow_ack", lang))


# ------------------------------------------------------------------ free text
def _open_alert(db: Session, donor: Donor, statuses: tuple) -> Notification | None:
    return db.scalar(
        select(Notification).join(Request)
        .where(Notification.donor_id == donor.id, Notification.status.in_(statuses), Request.status.in_(dispatch.ACTIVE_REQUEST))
        .order_by(Notification.sent_at.desc()).limit(1)
    )


def _free_text(db: Session, phone: str, donor: Donor, conv, text: str) -> None:
    lang = donor.language
    if conv.state == "prescreen":
        n = _own_notification(db, phone, conv.data.get("nid", ""))
        if n and n.status == "accepted":
            q = eligibility.next_question(n.eligibility_answers or {})
            if q:
                parsed = parse_intent(text, f"Donor is answering: {q['en']}", q["id"])
                if parsed["intent"] == "eligibility_answer" and parsed["eligibility_answer"] is not None and parsed["confidence"] >= CONFIDENCE_MIN:
                    return answer(db, n, conv, q["id"], parsed["eligibility_answer"])
                if parsed["intent"] == "decline" and parsed["confidence"] >= CONFIDENCE_MIN:
                    conv.state, conv.data = "idle", {}
                    n.status = "declined"
                    whatsapp.send(db, phone, t("declined", lang))
                    return
                whatsapp.send(db, phone, t("retry_buttons", lang))
                return _ask_next(db, n)
        conv.state, conv.data = "idle", {}

    pending = _open_alert(db, donor, dispatch.PENDING)
    connected = _open_alert(db, donor, ("connected",))
    context = "Donor received an emergency blood alert and has not replied yet." if pending else \
        "Donor has accepted and is heading to the hospital." if connected else "No open alert."
    parsed = parse_intent(text, context)
    intent, ok = parsed["intent"], parsed["confidence"] >= CONFIDENCE_MIN

    if intent == "stop" and ok:
        donor.opted_out = True
        whatsapp.send(db, phone, t("stopped", lang))
        return
    if intent == "pause" and ok:
        days = parsed["pause_days"] or 30
        donor.paused_until = utcnow() + timedelta(days=days)
        whatsapp.send(db, phone, t("paused", lang, days=days))
        return
    if intent == "location_update" and ok and parsed["location_text"]:
        hits = geocode.search(parsed["location_text"], limit=1)
        if hits:
            donor.lat, donor.lng, donor.location_label = hits[0]["lat"], hits[0]["lng"], parsed["location_text"]
            whatsapp.send(db, phone, t("location_updated", lang, place=parsed["location_text"]))
        else:
            whatsapp.send(db, phone, t("ob_location_bad", lang))
        return
    if pending and ok and intent == "accept":
        return accept(db, pending, conv, parsed["eta_minutes"])
    if pending and ok and intent == "decline":
        return decline(db, pending)
    if connected and ok and intent in ("eta_update", "accept") and parsed["eta_minutes"]:
        connected.eta_minutes = parsed["eta_minutes"]
        whatsapp.send(db, phone, t("eta_ack", lang, eta=parsed["eta_minutes"]))
        return
    if intent == "question" and ok:
        whatsapp.send(db, phone, t("faq", lang))
        return
    if pending:
        whatsapp.send(db, phone, t("retry_buttons", lang),
                      buttons=[(f"acc:{pending.id}", b("can_donate", lang)), (f"dec:{pending.id}", b("not_today", lang))])
        return
    whatsapp.send(db, phone, t("help", lang))


# ------------------------------------------------------------------ onboarding
def _start_onboarding(db: Session, conv, donor: Donor | None, phone: str) -> None:
    if donor:
        if donor.opted_out or not donor.consent:
            donor.opted_out, donor.consent = False, True
            whatsapp.send(db, phone, t("welcome", donor.language, name=donor.name.split()[0], group=donor.blood_group))
        else:
            whatsapp.send(db, phone, t("help", donor.language))
        return
    conv.state, conv.data = "ob_lang", {}
    whatsapp.send(db, phone, t("ob_lang", "en") + "\n" + t("ob_lang", "hi"),
                  buttons=[("lang:en", "English"), ("lang:hi", "हिन्दी")])


def _parse_date(text: str) -> date | None:
    m = re.fullmatch(r"\s*(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{4})\s*", text or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _onboarding(db: Session, conv, phone: str, text: str, button_id: str | None, location: dict | None) -> None:
    data = dict(conv.data or {})
    lang = data.get("lang", "en")
    state = conv.state
    today = dispatch.local_today()

    def ask(next_state: str, key: str, **kw):
        conv.state, conv.data = next_state, data
        whatsapp.send(db, phone, t(key, data.get("lang", "en")), **kw)

    def reset(key: str):
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, phone, t(key, lang))

    if state == "ob_lang":
        choice = (button_id or "").split(":")[-1] if button_id else ("hi" if re.search(r"hindi|हिन्दी|हिंदी|^2$", text, re.I) else "en")
        data["lang"] = "hi" if choice == "hi" else "en"
        return ask("ob_name", "ob_name")

    if state == "ob_name":
        name = re.sub(r"[^\w .'-]", "", text, flags=re.UNICODE).strip()
        if not (2 <= len(name) <= 60):
            return ask("ob_name", "ob_name")
        data["name"] = name.title() if name.isascii() else name
        return ask("ob_group", "ob_group", rows=[(f"grp:{g}", g) for g in GROUPS], list_button=b("choose", lang))

    if state == "ob_group":
        g = normalize_group(button_id.split(":", 1)[1] if button_id and button_id.startswith("grp:") else text)
        if not g:
            return ask("ob_group", "ob_group", rows=[(f"grp:{x}", x) for x in GROUPS], list_button=b("choose", lang))
        data["group"] = g
        return ask("ob_dob", "ob_dob")

    if state == "ob_dob":
        dob = _parse_date(text)
        if not dob or dob >= today:
            return ask("ob_dob", "ob_dob_bad")
        if not eligibility.age_ok(dob, today):
            return reset("ob_age_no")
        data["dob"] = dob.isoformat()
        return ask("ob_gender", "ob_gender", buttons=[("g:M", b("male", lang)), ("g:F", b("female", lang)), ("g:O", b("other", lang))])

    if state == "ob_gender":
        g = button_id.split(":")[1] if button_id and button_id.startswith("g:") else {"male": "M", "m": "M", "female": "F", "f": "F"}.get(text.lower(), "O" if text else "")
        if g not in ("M", "F", "O"):
            return ask("ob_gender", "ob_gender", buttons=[("g:M", b("male", lang)), ("g:F", b("female", lang)), ("g:O", b("other", lang))])
        data["gender"] = g
        return ask("ob_weight", "ob_weight", buttons=[("w:y", b("yes", lang)), ("w:n", b("no", lang))])

    if state == "ob_weight":
        yes = button_id == "w:y" or (not button_id and re.search(r"^(yes|y|haan|ha|हाँ|हां)$", text, re.I))
        if not yes:
            return reset("ob_weight_no")
        return ask("ob_location", "ob_location")

    if state == "ob_location":
        place = None
        if location:
            place = {"lat": location["lat"], "lng": location["lng"], "label": location.get("name") or "Shared location"}
        elif re.fullmatch(r"\d{6}", text):
            hit = geocode.pincode(text)
            if hit:
                place = {"lat": hit["lat"], "lng": hit["lng"], "label": hit["label"], "pincode": text}
        elif text:
            hits = geocode.search(text, limit=1)
            if hits:
                place = {"lat": hits[0]["lat"], "lng": hits[0]["lng"], "label": text}
        if not place:
            return ask("ob_location", "ob_location_bad")
        data["place"] = place
        return ask("ob_last", "ob_last", buttons=[("last:never", b("never", lang))])

    if state == "ob_last":
        if button_id == "last:never" or re.search(r"never|kabhi nahi|कभी नहीं", text, re.I):
            data["last"] = None
        else:
            d = _parse_date(text)
            if not d or d > today:
                return ask("ob_last", "ob_last", buttons=[("last:never", b("never", lang))])
            data["last"] = d.isoformat()
        return ask("ob_consent", "ob_consent", buttons=[("c:y", b("agree", lang)), ("c:n", b("disagree", lang))])

    if state == "ob_consent":
        if button_id != "c:y" and not re.fullmatch(r"(yes|y|haan|ha|हाँ|हां)", text, re.I):
            return reset("ob_no_consent")
        place = data["place"]
        donor = Donor(
            name=data["name"], phone=phone, blood_group=data["group"], gender=data["gender"],
            dob=date.fromisoformat(data["dob"]), weight_ok=True, lat=place["lat"], lng=place["lng"],
            location_label=place["label"], pincode=place.get("pincode"), language=data.get("lang", "en"),
            consent=True, last_donation_date=date.fromisoformat(data["last"]) if data.get("last") else None,
        )
        db.add(donor)
        conv.state, conv.data = "idle", {}
        params = {"name": donor.name.split()[0], "group": donor.blood_group}
        whatsapp.send(db, phone, t("welcome", donor.language, **params), template=("welcome", params, donor.language))
        return

    conv.state, conv.data = "idle", {}
    whatsapp.send(db, phone, t("help", lang))
