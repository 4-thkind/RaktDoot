import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "WHATSAPP_MODE": "mock",
    "TINYFISH_MODE": "demo",
    "TINYFISH_API_KEY": "",
    "GEOCODER": "off",
    "LLM_API_KEY": "",
    "RESPECT_QUIET_HOURS": "false",
    "ADMIN_TOKEN": "test-admin",
    "TICKER_SECONDS": "3600",
    "FORECAST_ENABLED": "false",  # radar tests switch it on explicitly
    "STT_PROVIDER": "demo",  # local Whisper is exercised in Docker; tests use the fixed sample transcripts
    "STT_API_KEY": "",
    "TINYFISH_REPLAY_ENABLED": "true",
    "TTS_PROVIDER": "off",  # voice-reply tests swap in a fake synthesizer
    "CAMP_PORTAL_URL": "",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        from app.services import camp_registration
        # the registration automation talks HTTP to the portal; point it at the in-process MOCK portal
        class PortalClient(TestClient):  # no lifespan: app startup (which clears mock chats) must run only once
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

        camp_registration._client = lambda: PortalClient(app, base_url="http://testserver/mock-portal")
        yield c


@pytest.fixture()
def fresh(client):
    r = client.post("/api/admin/reset", headers={"X-Admin-Token": "test-admin"})
    assert r.status_code == 200, r.text
    return client
