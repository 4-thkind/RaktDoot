from datetime import date, timedelta

from sqlalchemy import func, select

from app import telegram
from app.db import session_scope, utcnow
from app.models import Request
from app.services import recurring


def _request(db, **kw):
    r = Request(patient_group="B+", group_confirmed=True, units=1, patient_age=30, patient_gender="M",
                hospital_name="Test Hospital", hospital_lat=28.6, hospital_lng=77.2,
                requester_name="X", requester_phone="919000000009", status="dispatching", **kw)
    db.add(r)
    db.flush()
    return r


def test_gap_requests_not_reopened_every_tick(fresh):
    with session_scope() as db:
        for d in range(5):  # whatever today's rota looks like, repeat ticks must not add requests
            day = date.today() + timedelta(days=d)
            recurring.open_gap_requests(db, day)
            assert recurring.open_gap_requests(db, day) == 0


def test_new_requests_go_out_at_once_repeats_wait_5_minutes(fresh, monkeypatch):
    sent = []
    monkeypatch.setattr(telegram, "say", lambda chat, text, buttons=None: sent.append(text))
    with session_scope() as db:
        db.add(telegram.TelegramDonor(user_id="u1", chat_id="c1", active=True, created_at=utcnow() - timedelta(hours=1)))
        first = _request(db).id
        db.add(telegram.TelegramAlert(user_id="u1", request_id=first))
    telegram.deliver()
    with session_scope() as db:  # a brand-new request right after: must not wait behind the first alert
        for _ in range(2):
            db.add(telegram.TelegramAlert(user_id="u1", request_id=_request(db).id))
    telegram.remind(); telegram.deliver()
    assert len(sent) == 3
    telegram.remind(); telegram.deliver()
    assert len(sent) == 3  # no repeat of any of them before 5 minutes
    _age(); telegram.remind(); telegram.deliver()
    assert len(sent) == 6  # then each request repeats once


def test_admin_lists_and_stops_running_requests(fresh):
    h = {"X-Admin-Token": "test-admin"}
    assert fresh.get("/api/admin/requests/running").status_code == 401  # never public: it can cancel anyone's request
    with session_scope() as db:
        a, b = _request(db).id, _request(db).id
    ids = {r["id"] for r in fresh.get("/api/admin/requests/running", headers=h).json()}
    assert {a, b} <= ids
    assert fresh.post(f"/api/admin/requests/stop?rid={a}", headers=h).json() == {"stopped": 1}
    ids = {r["id"] for r in fresh.get("/api/admin/requests/running", headers=h).json()}
    assert a not in ids and b in ids
    fresh.post("/api/admin/requests/stop", headers=h)
    assert fresh.get("/api/admin/requests/running", headers=h).json() == []


def _age(minutes=6):
    """Pretend ALERT_GAP has passed: move every send/retry time into the past."""
    with session_scope() as db:
        past = utcnow() - timedelta(minutes=minutes)
        for d in db.scalars(select(telegram.TelegramDonor)).all():
            d.last_alert_at = past
        for a in db.scalars(select(telegram.TelegramAlert)).all():
            a.retry_at = past


def test_unanswered_alert_repeats_every_5_minutes_then_stops(fresh, monkeypatch):
    sent = []
    monkeypatch.setattr(telegram, "say", lambda chat, text, buttons=None: sent.append(text))
    with session_scope() as db:
        db.add(telegram.TelegramDonor(user_id="u2", chat_id="c2", active=True))
        db.add(telegram.TelegramAlert(user_id="u2", request_id=_request(db).id))
    telegram.deliver()
    telegram.remind(); telegram.deliver()
    assert len(sent) == 1  # not again within 5 minutes
    for _ in range(telegram.MAX_REMINDERS + 2):
        _age(); telegram.remind(); telegram.deliver()
    assert len(sent) == 1 + telegram.MAX_REMINDERS and len(set(sent)) == 1  # the same message, capped


def test_donate_reply_stops_reminders(fresh, monkeypatch):
    sent = []
    monkeypatch.setattr(telegram, "say", lambda chat, text, buttons=None: sent.append(text))
    with session_scope() as db:
        db.add(telegram.TelegramDonor(user_id="u3", chat_id="c3", active=True))
        r = _request(db)
        rid, slug = r.id, r.share_slug
        db.add(telegram.TelegramAlert(user_id="u3", request_id=rid))
    telegram.deliver()
    telegram.handle_message({"chat": {"id": "c3", "type": "private"}, "text": f"/donate {slug}"})
    before = len(sent)
    _age(); telegram.remind(); telegram.deliver()
    assert len(sent) == before  # screening started: no more repeats of the alert


def test_alert_and_question_buttons(fresh, monkeypatch):
    out = []
    monkeypatch.setattr(telegram, "say", lambda chat, text, buttons=None: out.append(buttons or []))
    monkeypatch.setattr(telegram, "call", lambda method, **kw: None)  # answerCallbackQuery / editMessageReplyMarkup
    with session_scope() as db:
        db.add(telegram.TelegramDonor(user_id="u4", chat_id="c4", active=True))
        r1, r2 = _request(db), _request(db)
        s1, s2 = r1.share_slug, r2.share_slug
        db.add(telegram.TelegramAlert(user_id="u4", request_id=r1.id))
        db.add(telegram.TelegramAlert(user_id="u4", request_id=r2.id))
    telegram.deliver()
    assert [c for _, c in out[0]] == [f"donate:{s1}", f"decline:{s1}"]
    tap = lambda data: telegram.handle_callback({"id": "q", "data": data, "message": {"chat": {"id": "c4", "type": "private"}, "message_id": 1}})
    tap(f"donate:{s1}")
    assert [c for _, c in out[-1]] == ["YES", "NO"]  # first health question has Yes/No buttons
    tap("NO")
    assert [c for _, c in out[-1]] == ["YES", "NO"]  # and the next one
    tap(f"decline:{s2}")
    with session_scope() as db:
        st = {a.request_id: a.status for a in db.scalars(select(telegram.TelegramAlert)).all()}
        assert st[r2.id] == "declined" and st[r1.id] == "screening"
