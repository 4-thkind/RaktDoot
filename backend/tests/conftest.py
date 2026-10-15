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
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fresh(client):
    r = client.post("/api/admin/reset", headers={"X-Admin-Token": "test-admin"})
    assert r.status_code == 200, r.text
    return client
