"""Live path of the TinyFish client with the SDK's network layer replaced by recorded events."""
import asyncio

import tinyfish
from tinyfish import CompleteEvent, ProgressEvent, StartedEvent, StreamingUrlEvent

from app.config import settings
from app.services import tinyfish_client

RESULT = {"district_selected": "South Delhi", "banks": [
    {"name": "AIIMS Main Blood Bank", "category": "Govt", "last_updated": "14-10-2026 10:00",
     "availability_text": "B+Ve: 6, O-Ve: 1", "stock": {"B+": 6, "O-": 1}},
    {"name": "Some Unknown Blood Centre", "stock": {"B+": 0}},
]}


def _events(result, status="COMPLETED"):
    ts = "2026-10-14T10:00:00Z"
    return [
        StartedEvent(type="STARTED", run_id="run_123", timestamp=ts),
        StreamingUrlEvent(type="STREAMING_URL", run_id="run_123", streaming_url="https://example.test/live", timestamp=ts),
        ProgressEvent(type="PROGRESS", run_id="run_123", purpose="Selecting state Delhi", timestamp=ts),
        CompleteEvent(type="COMPLETE", run_id="run_123", status=status, timestamp=ts, result_json=result, error=None),
    ]


class FakeStream:
    def __init__(self, events):
        self.events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    def __aiter__(self):
        async def gen():
            for e in self.events:
                yield e
        return gen()


def _patch(monkeypatch, events):
    class FakeAgent:
        def stream(self, **kw):
            assert "Stock Availability" in kw["goal"] and kw["url"] == settings.eraktkosh_stock_url
            return FakeStream(events)

    class FakeClient:
        def __init__(self, api_key=None):
            self.agent = FakeAgent()

    monkeypatch.setattr(tinyfish, "AsyncTinyFish", FakeClient)
    monkeypatch.setattr(settings, "tinyfish_api_key", "test-key")
    monkeypatch.setattr(settings, "tinyfish_mode", "live")


def _run(state="Delhi", district="Live Test District"):
    seen = []

    async def emit(ev):
        seen.append(ev)

    out = asyncio.run(tinyfish_client.lookup_stock(state, district, (28.5672, 77.21), emit))
    return out, seen


def test_live_success(fresh, monkeypatch):
    _patch(monkeypatch, _events(RESULT))
    out, seen = _run()
    assert out["source"] == "live" and out["run_id"] == "run_123" and out["streaming_url"]
    assert out["banks"][0]["name"] == "AIIMS Main Blood Bank" and out["banks"][0]["distance_km"] is not None
    assert out["banks"][1]["distance_km"] is None  # not in our directory, still listed
    assert any(e["type"] == "agent_view" for e in seen)
    again, _ = _run()
    assert again["source"] == "cache"


def test_live_blocked_falls_back(fresh, monkeypatch):
    _patch(monkeypatch, _events({"error": "captcha"}))
    out, _ = _run(district="Blocked District")
    assert out["source"] == "unavailable" and out["suggest_donor_search"] and out["reason"] == "captcha"


def test_live_failed_status(fresh, monkeypatch):
    _patch(monkeypatch, _events(None, status="FAILED"))
    out, _ = _run(district="Failed District")
    assert out["source"] == "unavailable" and out["suggest_donor_search"]
