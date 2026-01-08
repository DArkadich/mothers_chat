import os
import importlib

import pytest
from fastapi.testclient import TestClient


APP_MODULE = os.getenv("APP_MODULE", "backend.main_newold")
LIMITER_MODULE = os.getenv("LIMITER_MODULE", "backend.core.limiter")

app_mod = importlib.import_module(APP_MODULE)
lim_mod = importlib.import_module(LIMITER_MODULE)

app = getattr(app_mod, "app")


@pytest.fixture()
def client(monkeypatch):
    # small limit for test
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")

    # ensure limiter uses small limit and clear state
    try:
        lim_mod.limiter.limit = 2
        lim_mod.limiter.store.clear()
    except Exception:
        pass

    with TestClient(app) as c:
        yield c


def test_rate_limit_happy(monkeypatch, client):
    # Patch time in limiter module so requests are in the same window
    monkeypatch.setattr(lim_mod.time, "time", lambda: 1_000_000.0)

    r1 = client.get("/health")
    r2 = client.get("/health")

    assert r1.status_code in (200, 204, 200), r1.text
    assert r2.status_code in (200, 204, 200), r2.text


def test_rate_limit_deny_third_request(monkeypatch, client):
    monkeypatch.setattr(lim_mod.time, "time", lambda: 1_000_000.0)

    r1 = client.get("/health")
    r2 = client.get("/health")
    r3 = client.get("/health")

    assert r1.status_code in (200, 204, 200), r1.text
    assert r2.status_code in (200, 204, 200), r2.text
    assert r3.status_code == 429, r3.text
