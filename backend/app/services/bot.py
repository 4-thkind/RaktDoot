"""WhatsApp conversation logic for donors: onboarding, alert replies, the eligibility
pre-screen, follow-ups, STOP / PAUSE. Channel-agnostic: webhooks and the simulator both
call handle_inbound()."""
import re
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core import eligibility
from ..core.compatibility import GROUPS, normalize_group
from ..db import utcnow
from ..config import settings
from ..models import Camp, ChatMessage, Donation, Donor, Notification, Profile, RecurringSlot, Request
from . import bandit, camp_registration, camps, dispatch, extraction, forwards, geocode, guide, recurring, stt, tinyfish_client, vision, whatsapp
from .llm import parse_intent
from .messages import b, t

CONFIDENCE_MIN = 0.7


def handle_inbound(db: Session, phone: str, text: str = "", button_id: str | None = None,
                   location: dict | None = None, wa_id: str | None = None, media: dict | None = None) -> None:
    """media = {"kind": "audio" | "image", "data": bytes, "mime": str}; the bytes are never stored.
    Whoever speaks to the bot gets spoken to: a voice note in -> the replies also go out as a voice note
    (TTS), and donors who sent VOICE ON always get voice notes."""
    before = db.scalar(select(func.max(ChatMessage.id))) or 0
    voice_in = bool(media and media.get("kind") == "audio")
    _handle(db, phone, text, button_id, location, wa_id, media)
    donor = db.scalar(select(Donor).where(Donor.phone == phone))
    conv = whatsapp.conversation(db, phone)
    if voice_in:
        conv.data = {**(conv.data or {}), "voice": True}
    if voice_in or (donor and donor.voice_replies):
        _voice_reply(db, phone, before)


def _voice_reply(db: Session, phone: str, after_id: int) -> None:
    msgs = db.scalars(select(ChatMessage).where(ChatMessage.phone == phone, ChatMessage.direction == "out", ChatMessage.id > after_id,
                                                ChatMessage.kind.in_(("text", "buttons", "list")))).all()
    text = "\n".join(m.body for m in msgs if m.body)
    if text:
        whatsapp.speak(db, phone, text, "hi" if re.search(r"[\u0900-\u097F]", text) else "en")


HINGLISH = re.compile(r"\b(chahiye|chaiye|mein|hai|bhai|jaldi|unit chahiye|ko)\b", re.I)


def _lang_of(text: str, donor: Donor | None, conv) -> str:
    if donor:
        return donor.language
    if re.search(r"[\u0900-\u097F]", text or "") or HINGLISH.search(text or ""):
        return "hi"
    return (conv.data or {}).get("lang", "en")


def _handle(db: Session, phone: str, text: str = "", button_id: str | None = None,
            location: dict | None = None, wa_id: str | None = None, media: dict | None = None) -> None:
    text = (text or "").strip()
    conv = whatsapp.conversation(db, phone)
    donor = db.scalar(select(Donor).where(Donor.phone == phone))
    lang = donor.language if donor else conv.data.get("lang", "en")
    if media and media.get("kind") == "audio":
        heard = stt.transcribe(media.get("data") or b"", media.get("mime") or "audio/ogg")
        transcript = heard.get("text", "").strip()
        shown = camp_registration.mask_aadhaar(transcript) if conv.state == "cr_aadhaar" else transcript
        whatsapp.log_inbound(db, phone, f"[voice note] {shown}" if shown else "[voice note]",
                             {"media": "audio", "transcript": shown, "stt": heard.get("engine"), "sample": heard.get("sample", False)}, wa_id)
        if not transcript:
            whatsapp.send(db, phone, t("voice_failed", lang))
            return
        text = transcript
    elif media and media.get("kind") == "image":
        whatsapp.log_inbound(db, phone, "[photo]", {"media": "image"}, wa_id)
        if conv.state == "await_card":
            return _donor_card(db, phone, donor, conv, media)
        whatsapp.send(db, phone, t("help", lang))
        return
    else:
        shown = camp_registration.mask_aadhaar(text) if conv.state == "cr_aadhaar" else text
        whatsapp.log_inbound(db, phone, shown or (_button_title(db, phone, button_id) if button_id else "[location]" if location else ""),
                             {"button_id": button_id, "location": location}, wa_id)

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
    if word in ("VOICE ON", "VOICE", "AWAAZ", "आवाज़", "आवाज") and donor:
        donor.voice_replies = True
        whatsapp.send(db, phone, t("voice_on", lang))
        return
    if word in ("VOICE OFF", "NO VOICE") and donor:
        donor.voice_replies = False
        whatsapp.send(db, phone, t("voice_off", lang))
        return
    if word in ("JOIN", "START", "REGISTER", "HI", "HELLO") and not conv.state.startswith("ob_"):
        return _start_onboarding(db, conv, donor, phone)

    if conv.state.startswith("ob_"):
        return _onboarding(db, conv, phone, text, button_id, location)
    if conv.state.startswith("rq_"):
        return _request_flow(db, phone, conv, donor, text, button_id, location)
    if conv.state.startswith("cr_"):
        return _camp_flow(db, phone, donor, conv, text, button_id)

    if button_id:
        return _button(db, phone, donor, conv, button_id)

    if conv.state == "await_card":
        conv.state, conv.data = "idle", {}  # SKIP, or anything else: carry on as normal
        if word in ("SKIP", "NO", "NAHI"):
            whatsapp.send(db, phone, t("card_skipped", lang))
            return

    if text and conv.state != "prescreen":
        if extraction.is_request(text) and not extraction.is_forward(text):  # someone asking for blood in their own words
            return _request_flow(db, phone, conv, donor, text, None, location, start=True)
        if extraction.is_plea(text):
            return _forward(db, phone, text, lang)

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
    if kind == "fw" and len(parts) == 3:
        return _forward_button(db, phone, parts[1], parts[2], donor.language if donor else conv.data.get("lang", "en"))
    if kind == "rc" and len(parts) == 3:
        return _rota_button(db, phone, donor, conv, parts[1], parts[2] == "y")
    if kind == "rs" and len(parts) == 4:
        return _rota_answer(db, phone, donor, conv, parts[1], parts[2], parts[3] == "y")
    if kind == "cr" and len(parts) == 2:
        return _camp_start(db, phone, donor, conv, parts[1])
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
    bandit.update(db, n.variant, n.segment, 1)
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
    if n.status != "accepted":  # a tap on an old question: say so instead of staying silent
        whatsapp.send(db, donor.phone, t("already_covered" if n.status == "cancelled" else "prescreen_done", lang))
        return
    if eligibility.question(qid) is None:
        return
    answers = dict(n.eligibility_answers or {})
    answers[qid] = yes
    # our own records override a "no" to the recent-donation question
    if qid == "donated_recently" and eligibility.in_rest_period(donor.last_donation_date, donor.gender, dispatch.local_today()):
        answers[qid] = True
    n.eligibility_answers = answers

    failed = eligibility.answers_disqualify(answers)
    if failed:
        n.status = "ineligible"
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, donor.phone, t("ineligible", lang, reason=t(f"why_{failed}", lang)))
        _suggest_camp(db, donor, dispatch.local_today() + timedelta(days=1))
        return
    if eligibility.next_question(answers):
        return _ask_next(db, n)

    conv.state, conv.data = "idle", {}
    if req.status not in ("dispatching", "needs_public_share"):
        n.status = "cancelled"
        whatsapp.send(db, donor.phone, t("already_covered", lang))
        return
    whatsapp.send(db, donor.phone, t("eligible_today", lang))
    connect(db, n)


def connect(db: Session, n: Notification) -> None:
    donor, req = n.donor, n.request
    lang = donor.language
    n.status, n.connected_at = "connected", utcnow()
    req.first_acceptance_at = req.first_acceptance_at or n.connected_at
    map_link = f"https://maps.google.com/?q={req.hospital_lat},{req.hospital_lng}"
    if req.kind == "drive":  # a donor drive has no family to call
        whatsapp.send(db, donor.phone, t("drive_connected", lang, name=donor.name.split()[0], bank=req.hospital_name, map=map_link))
    else:
        params = {"name": donor.name.split()[0], "hospital": req.hospital_name, "ref": req.id[:6].upper(), "map": map_link}
        whatsapp.send(db, donor.phone, t("connected", lang, **params), template=("connected", params, lang))
        _tell_family(db, req, n)
    whatsapp.send(db, donor.phone, req.hospital_name,
                  location={"lat": req.hospital_lat, "lng": req.hospital_lng, "name": req.hospital_name, "address": req.hospital_address or ""})
    dispatch.check_target(db, req)


def decline(db: Session, n: Notification) -> None:
    if n.status not in dispatch.PENDING:
        return
    n.status, n.responded_at = "declined", utcnow()
    n.donor.alerts_responded += 1
    bandit.update(db, n.variant, n.segment, 0)
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
        donation = Donation(donor_id=donor.id, request_id=n.request_id, donated_on=today, confirmed_by="donor")
        db.add(donation)
        db.flush()
        whatsapp.send(db, donor.phone, t("donation_thanks", lang, days=eligibility.rest_days(donor.gender)))
        conv = whatsapp.conversation(db, donor.phone)
        conv.state, conv.data = "await_card", {"donation_id": donation.id, "nid": n.id}
        whatsapp.send(db, donor.phone, t("card_ask", lang))
    elif choice == "d":
        n.status = "deferred"
        whatsapp.send(db, donor.phone, t("deferred_ack", lang))
        _suggest_camp(db, donor, dispatch.local_today() + timedelta(days=1))
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
        return _answer_question(db, phone, text, lang)
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


# ------------------------------------------------------------------ family guide (F13)
def _answer_question(db: Session, phone: str, text: str, lang: str) -> None:
    guide.ensure_loaded(db)
    ans = guide.answer(text, lang)
    body = ans["answer"] + "".join(f"\n{s['title']}: {s['url']}" for s in ans["sources"])
    whatsapp.send(db, phone, body)


# ------------------------------------------------------------------ camps (A1)
def _suggest_camp(db: Session, donor: Donor, after: date) -> None:
    if donor.lat is None:
        return
    c = camps.nearest(db, donor.lat, donor.lng, after)
    if c:
        whatsapp.send(db, donor.phone, t("next_camp", donor.language, after=after.strftime("%d %b"), camp=c.title,
                                         date=c.camp_date.strftime("%d %b"), place=c.address or c.district),
                      buttons=[(f"cr:{c.id}", b("register_me", donor.language))])


# ------------------------------------------------------------------ proof of donation (F9)
def _donor_card(db: Session, phone: str, donor: Donor | None, conv, media: dict) -> None:
    data = dict(conv.data or {})
    conv.state, conv.data = "idle", {}
    lang = donor.language if donor else "en"
    donation = db.get(Donation, data.get("donation_id", ""))
    n = db.get(Notification, data.get("nid", "")) if data.get("nid") else None
    if not donor or not donation or donation.donor_id != donor.id:
        whatsapp.send(db, phone, t("help", lang))
        return
    not_before = n.connected_at.date() if n and n.connected_at else None
    got = vision.parse_donor_card(media.get("data") or b"", media.get("mime") or "image/jpeg", dispatch.local_today(), not_before)
    if not got.get("donation_date") or got.get("confidence", 0) < 0.6:
        whatsapp.send(db, phone, t("card_unreadable", lang))
        return
    donation.donated_on, donation.confirmed_by = got["donation_date"], "photo"
    donor.last_donation_date = max(got["donation_date"], donor.last_donation_date or got["donation_date"])
    donor.donations_verified = (donor.donations_verified or 0) + 1
    whatsapp.send(db, phone, t("card_verified", lang, date=got["donation_date"].strftime("%d %b %Y"),
                               centre=got.get("centre") or (n.request.hospital_name if n else "")))


# ------------------------------------------------------------------ forward checker (F2)
def _forward(db: Session, phone: str, text: str, lang: str) -> None:
    res = forwards.check(db, text, phone)
    reasons = "\n".join(f"- {r.get(lang, r['en'])}" for r in res["reasons"])
    whatsapp.send(db, phone, t(f"fw_{res['verdict']}", lang, reasons=reasons))
    link = f"{settings.public_base_url.rstrip('/')}/find"
    if res["verdict"] == "looks_genuine":
        if res["offer"]:
            whatsapp.send(db, phone, t("fw_offer", lang, n=res["offer"]["donors"], hospital=res["offer"]["hospital"], link=link),
                          buttons=[(f"fw:alert:{res['id']}", b("alert_donors", lang)), (f"fw:no:{res['id']}", b("no_thanks", lang))])
        else:
            whatsapp.send(db, phone, t("fw_need_hospital", lang, link=link))


def _forward_button(db: Session, phone: str, choice: str, fid: str, lang: str) -> None:
    from ..models import Forward
    fw = db.get(Forward, fid)
    if fw is None or choice != "alert":
        whatsapp.send(db, phone, t("declined", lang))
        return
    if fw.reporter_hash != forwards._hash(phone):
        whatsapp.send(db, phone, t("help", lang))  # only the person who sent the plea can act on it
        return
    profile = db.scalar(select(Profile).where(Profile.phone == phone))
    donor = db.scalar(select(Donor).where(Donor.phone == phone))
    name = (profile.name if profile else None) or (donor.name if donor else None) or "Forwarded request"
    try:
        req = forwards.create_request(db, fid, phone, name, lang)
    except ValueError:
        whatsapp.send(db, phone, t("fw_need_hospital", lang, link=f"{settings.public_base_url.rstrip('/')}/find"))
        return
    link = f"{settings.public_base_url.rstrip('/')}/request/{req.id}?t={req.manage_token}"
    whatsapp.send(db, phone, t("fw_created", lang, hospital=req.hospital_name, link=link))


# ------------------------------------------------------------------ recurring rota (F7)
def _button_title(db: Session, phone: str, button_id: str) -> str:
    """Show what the person tapped ("Yes, I'll come"), not the internal button id."""
    for m in db.scalars(select(ChatMessage).where(ChatMessage.phone == phone, ChatMessage.direction == "out")
                        .order_by(ChatMessage.id.desc()).limit(30)):
        for o in (m.payload or {}).get("options") or []:
            if o.get("id") == button_id:
                return o.get("title") or button_id
    return "[button]"


def _rota_ask(db: Session, phone: str, slot: RecurringSlot, answers: dict, lang: str) -> None:
    q = eligibility.next_question(answers)
    whatsapp.send(db, phone, q.get(lang, q["en"]),
                  buttons=[(f"rs:{slot.id}:{q['id']}:y", b("yes", lang)), (f"rs:{slot.id}:{q['id']}:n", b("no", lang))])


def _rota_button(db: Session, phone: str, donor: Donor | None, conv, slot_id: str, yes: bool) -> None:
    slot = db.get(RecurringSlot, slot_id)
    lang = donor.language if donor else "en"
    if not donor or not slot or slot.donor_id != donor.id or slot.status not in ("planned", "reminded"):
        whatsapp.send(db, phone, t("help", lang))
        return
    if yes:  # same health pre-screen as an emergency alert before the slot is confirmed
        conv.state, conv.data = "rota_screen", {"slot": slot.id, "answers": {}}
        whatsapp.send(db, phone, t("pre_screen_intro", lang))
        _rota_ask(db, phone, slot, {}, lang)
    else:
        slot.status = "declined"
        whatsapp.send(db, phone, t("recurring_declined", lang))
        recurring.refill(db, slot)


def _rota_answer(db: Session, phone: str, donor: Donor | None, conv, slot_id: str, qid: str, yes: bool) -> None:
    slot = db.get(RecurringSlot, slot_id)
    lang = donor.language if donor else "en"
    data = dict(conv.data or {})
    if not donor or not slot or slot.donor_id != donor.id or conv.state != "rota_screen" or data.get("slot") != slot_id \
            or eligibility.question(qid) is None:
        whatsapp.send(db, phone, t("prescreen_done", lang))
        return
    answers = {**data.get("answers", {}), qid: yes}
    if qid == "donated_recently" and eligibility.in_rest_period(donor.last_donation_date, donor.gender, slot.due_date):
        answers[qid] = True  # our own records: still resting on the due date
    failed = eligibility.answers_disqualify(answers)
    if failed:
        conv.state, conv.data = "idle", {}
        slot.status = "declined"
        whatsapp.send(db, phone, t("ineligible", lang, reason=t(f"why_{failed}", lang)))
        recurring.refill(db, slot)
        return
    if eligibility.next_question(answers):
        conv.data = {**data, "answers": answers}
        return _rota_ask(db, phone, slot, answers, lang)
    conv.state, conv.data = "idle", {}
    slot.status = "confirmed"
    whatsapp.send(db, phone, t("eligible_today", lang))
    whatsapp.send(db, phone, t("recurring_confirmed", lang, date=slot.due_date.strftime("%d %b")))


# ------------------------------------------------------------------ family updates
def _tell_family(db: Session, req: Request, n: Notification) -> None:
    """The requester hears it on WhatsApp the moment a donor is on the way (and by voice if they spoke to us)."""
    if not req.requester_phone or req.requester_phone == n.donor.phone:
        return
    lang = req.language or "en"
    p = {"name": n.donor.name.split()[0], "group": n.donor.blood_group, "hospital": req.hospital_name,
         "distance": f"{n.distance_km:.1f}", "phone": n.donor.phone}
    whatsapp.send(db, req.requester_phone, t("rq_donor_coming", lang, **p), template=("rq_donor_coming", p, lang))
    if (whatsapp.conversation(db, req.requester_phone).data or {}).get("voice"):
        whatsapp.speak(db, req.requester_phone, t("rq_donor_coming", lang, **{**p, "phone": " ".join(p["phone"][-10:])}), lang)


# ------------------------------------------------------------------ requests by voice or text
GROUP_ROWS = [(f"grp:{g}", g) for g in GROUPS]


def _stock_line(db: Session, rq: dict, lang: str) -> str:
    """Nearby stock for the patient's group. Only from the sample/cache path, so the chat never waits on a live agent."""
    from ..api.stock import locate, shape

    if settings.tinyfish_live:
        return ""
    db.commit()  # the lookup writes its cache from another thread; don't hold the SQLite write lock
    try:
        place = rq["place"]
        where = locate(place["lat"], place["lng"])

        async def quiet(_):
            return None
        res = forwards._run(tinyfish_client.lookup_stock(where["state"], where["district"], (place["lat"], place["lng"]), quiet,
                                                         rq.get("component") or "prbc"))
        shaped = shape(res, rq["patient_group"], (place["lat"], place["lng"]), rq.get("component") or "prbc")
    except Exception:  # noqa: BLE001
        return ""
    near = [x for x in shaped["banks"] if (x.get("exact_units") or 0) > 0 and (x.get("distance_km") or 99) <= 10][:3]
    group = rq["patient_group"].replace("-", "−")
    if not near:
        return t("rq_no_stock", lang, group=group)
    banks = "; ".join(f"{x['name']} ({x['distance_km']} km, {x['exact_units']} units{', ' + x['phone'] if x.get('phone') else ''})" for x in near)
    return t("rq_stock", lang, group=group, banks=banks) + (" (sample data)" if shaped["sample"] else "")


def _request_flow(db: Session, phone: str, conv, donor: Donor | None, text: str = "", button_id: str | None = None,
                  location: dict | None = None, start: bool = False) -> None:
    from .messages import component_word

    data = {} if start else dict(conv.data or {})
    rq = dict(data.get("rq") or {})
    lang = data.get("lang") or _lang_of(text, donor, conv)
    voice = (conv.data or {}).get("voice")
    if start:
        whatsapp.send(db, phone, t("rq_start", lang))
    if button_id == "rq:no":
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, phone, t("rq_cancelled", lang))
        return
    if button_id == "rq:yes" and conv.state == "rq_confirm":
        return _create_request(db, phone, conv, donor, rq, lang)
    if button_id and button_id.startswith("grp:"):
        g = button_id.split(":", 1)[1]
        rq["patient_group"], rq["group_confirmed"] = ("O-", False) if g == "unsure" else (g, True)
    if button_id and button_id.startswith("u:"):
        rq["units"] = int(button_id[2:])
    if location and not rq.get("place"):
        from ..api.stock import hospital_name
        from ..models import BloodBank
        from ..core.geo import haversine_km
        banks = db.scalars(select(BloodBank).where(~BloodBank.category.like("Charitable%"))).all()
        near = min(banks, key=lambda x: haversine_km(location["lat"], location["lng"], x.lat, x.lng), default=None)
        if near:
            rq["hospital"] = hospital_name(near.name)
            rq["place"] = {"name": rq["hospital"], "lat": near.lat, "lng": near.lng, "address": near.address, "via": "location"}
    if text:  # every message (typed or spoken) can fill several blanks at once
        f = extraction.extract(text)
        for k in ("patient_group", "units", "component", "hospital", "city"):
            if f.get(k) and not rq.get(k):
                rq[k] = f[k]
        if conv.state == "rq_hospital" and not f.get("hospital") and not rq.get("hospital") and len(text) >= 3:
            rq["hospital"] = text.strip()[:120]
        if conv.state == "rq_units" and not rq.get("units"):
            m = re.search(r"\d{1,2}", text)
            if m and 1 <= int(m.group()) <= 12:
                rq["units"] = int(m.group())
    if rq.get("hospital") and not rq.get("place"):
        place = forwards.locate_hospital(db, rq["hospital"], rq.get("city"))
        if place:
            rq["place"] = {**place, "name": rq["hospital"]}
        else:
            rq["hospital"] = None
            if conv.state == "rq_hospital" or start:
                whatsapp.send(db, phone, t("rq_hospital_bad", lang))
    rq.setdefault("component", None)

    def ask(state: str, key: str, **kw):
        conv.state, conv.data = state, {"rq": rq, "lang": lang, **({"voice": True} if voice else {})}
        whatsapp.send(db, phone, t(key, lang), **kw)

    if not rq.get("patient_group"):
        return ask("rq_group", "rq_ask_group", rows=GROUP_ROWS + [("grp:unsure", b("not_sure", lang))], list_button=b("choose", lang))
    if not rq.get("place"):
        return ask("rq_hospital", "rq_ask_hospital")
    if not rq.get("units"):
        return ask("rq_units", "rq_ask_units", buttons=[("u:1", "1"), ("u:2", "2"), ("u:3", b("three_plus", lang))])
    comp = rq.get("component") or "prbc"
    conv.state, conv.data = "rq_confirm", {"rq": rq, "lang": lang, **({"voice": True} if voice else {})}
    whatsapp.send(db, phone, t("rq_confirm", lang, group=rq["patient_group"].replace("-", "−"), component=component_word(comp, lang),
                               units=rq["units"], hospital=rq["place"]["name"], stock=_stock_line(db, rq, lang)),
                  buttons=[("rq:yes", b("alert_donors", lang)), ("rq:no", b("cancel", lang))])


def _create_request(db: Session, phone: str, conv, donor: Donor | None, rq: dict, lang: str) -> None:
    from ..core.compatibility import normalize_component

    open_n = db.scalar(select(func.count()).select_from(Request).where(
        Request.requester_phone == phone, Request.status.in_(("open",) + dispatch.ACTIVE_REQUEST))) or 0
    if open_n >= settings.max_open_requests_per_phone:
        conv.state, conv.data = "idle", {"voice": True} if (conv.data or {}).get("voice") else {}
        whatsapp.send(db, phone, t("help", lang))
        return
    place = rq["place"]
    check = forwards._run(tinyfish_client.verify_hospital(place["name"], place.get("address") or "", place["lat"], place["lng"]))
    profile = db.scalar(select(Profile).where(Profile.phone == phone))
    name = (profile.name if profile else None) or (donor.name if donor else None) or "Family (WhatsApp)"
    units = int(rq["units"])
    req = Request(patient_group=rq["patient_group"], group_confirmed=rq.get("group_confirmed", True), units=units, patient_age=0,
                  patient_gender="O", hospital_name=place["name"][:200], hospital_address=place.get("address"), hospital_lat=place["lat"],
                  hospital_lng=place["lng"], hospital_verified=check["verified"], hospital_check=check, requester_name=name[:80],
                  requester_phone=phone, language=lang, component=normalize_component(rq.get("component")), kind="emergency",
                  allow_o_neg=rq["patient_group"] == "O-" or not rq.get("group_confirmed", True),
                  target_acceptances=min(units * 2, 12), expires_at=utcnow() + timedelta(hours=settings.request_ttl_hours))
    db.add(req)
    db.flush()
    sent = dispatch.start_dispatch(db, req)
    conv.state, conv.data = "idle", {"voice": True} if (conv.data or {}).get("voice") else {}
    link = f"{settings.public_base_url.rstrip('/')}/request/{req.id}?t={req.manage_token}"
    whatsapp.send(db, phone, t("rq_created", lang, n=sent, hospital=req.hospital_name, link=link))


# ------------------------------------------------------------------ camp registration (A2)
def _camp_start(db: Session, phone: str, donor: Donor | None, conv, camp_id: str) -> None:
    camp = db.get(Camp, camp_id)
    lang = donor.language if donor else "en"
    if not donor or not camp:
        whatsapp.send(db, phone, t("not_registered" if not donor else "help", lang))
        return
    conv.state, conv.data = "cr_consent", {"camp": camp.id}
    whatsapp.send(db, phone, t("cr_consent", lang, camp=camp.title, date=camp.camp_date.strftime("%d %b")),
                  buttons=[(f"crok:{camp.id}", b("yes_register", lang)), ("crno", b("no_thanks", lang))])


def _camp_flow(db: Session, phone: str, donor: Donor | None, conv, text: str, button_id: str | None) -> None:
    data = dict(conv.data or {})
    lang = donor.language if donor else "en"
    camp = db.get(Camp, data.get("camp", ""))
    if not donor or not camp or button_id == "crno" or (text or "").upper() in ("STOP", "CANCEL", "NO"):
        conv.state, conv.data = "idle", {}
        whatsapp.send(db, phone, t("declined", lang))
        return
    if conv.state == "cr_consent":
        if (button_id or "").startswith("crok:") or re.fullmatch(r"(yes|y|haan|ha|हाँ|हां)", text or "", re.I):
            conv.state = "cr_aadhaar"
            whatsapp.send(db, phone, t("cr_ask_aadhaar", lang))
        else:
            whatsapp.send(db, phone, t("retry_buttons", lang),
                          buttons=[(f"crok:{camp.id}", b("yes_register", lang)), ("crno", b("no_thanks", lang))])
        return
    if conv.state == "cr_aadhaar":
        digits = re.sub(r"\D", "", text or "")
        if not re.fullmatch(r"[2-9]\d{11}", digits):
            whatsapp.send(db, phone, t("cr_bad_aadhaar", lang))
            return
        conv.state, conv.data = "cr_working", data
        reg = camp_registration.start(db, camp, camp_registration.details_for(donor), digits, donor.id)
        del digits  # used once, never stored
        if reg.status != "otp_sent":
            conv.state, conv.data = "idle", {}
            whatsapp.send(db, phone, t("cr_failed", lang, reason=reg.error or "error"))
            return
        conv.state, conv.data = "cr_otp", {**data, "reg": reg.id, "tries": 0}
        whatsapp.send(db, phone, t("cr_otp_sent", lang))
        return
    if conv.state == "cr_otp":
        from ..models import CampRegistration
        reg = db.get(CampRegistration, data.get("reg", ""))
        if reg is None:
            conv.state, conv.data = "idle", {}
            return
        reg = camp_registration.finish(db, reg, text or "")
        if reg.status == "registered":
            conv.state, conv.data = "idle", {}
            whatsapp.send(db, phone, t("cr_done", lang, camp=camp.title, date=camp.camp_date.strftime("%d %b"), ref=reg.portal_ref))
            return
        tries = data.get("tries", 0) + 1
        if tries >= 3:
            conv.state, conv.data = "idle", {}
            whatsapp.send(db, phone, t("cr_failed", lang, reason="OTP"))
            return
        conv.data = {**data, "tries": tries}
        whatsapp.send(db, phone, t("cr_bad_otp", lang))
        return
    conv.state, conv.data = "idle", {}
