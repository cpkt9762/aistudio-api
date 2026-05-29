import os
import pytest

from aistudio_api.config import settings


@pytest.mark.skipif(not os.path.exists(
    os.path.expanduser("~/Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json")
), reason="acc_browseros fixture missing")
def test_session_shared_mode_routes_to_pool(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    from aistudio_api.infrastructure.gateway.session import BrowserSession
    sess = BrowserSession(port=0)
    assert hasattr(sess, "_pool")
    assert sess._pool is not None
    assert sess._pool.browser_is_alive() is False


def test_switch_active_account_is_fast(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    from aistudio_api.infrastructure.gateway.session import BrowserSession
    sess = BrowserSession(port=0)
    sess._pool.register("acc_a")
    sess._pool.register("acc_b")
    import time
    t0 = time.time()
    sess.switch_active_account_sync("acc_b")
    dt = time.time() - t0
    assert sess._pool.active_account_id == "acc_b"
    assert dt < 0.05


@pytest.mark.skipif(not os.path.exists(
    os.path.expanduser("~/Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json")
), reason="acc_browseros fixture missing")
def test_ensure_context_under_shared_mode(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    from aistudio_api.infrastructure.gateway.session import BrowserSession
    sess = BrowserSession(port=0)
    sess._pool.register("acc_browseros")
    sess._pool.set_active("acc_browseros")
    ctx = sess._ensure_browser_sync()
    assert ctx is not None
    sess._pool.close_browser_sync()


@pytest.mark.skipif(not os.path.exists(
    os.path.expanduser("~/Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json")
), reason="acc_browseros fixture missing")
def test_get_cookies_for_active_account(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    from aistudio_api.infrastructure.gateway.session import BrowserSession
    sess = BrowserSession(port=0)
    sess._pool.register("acc_browseros")
    sess._pool.set_active("acc_browseros")
    sess._ensure_browser_sync()
    cookies = sess.get_cookies_for_active_account_sync()
    assert "SAPISID" in cookies
    sess._pool.close_browser_sync()


import importlib
from fastapi.testclient import TestClient


@pytest.mark.skipif(not os.path.exists(
    os.path.expanduser("~/Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json")
), reason="acc_browseros fixture missing")
def test_chat_end_to_end_shared_http(monkeypatch):
    monkeypatch.setenv("AISTUDIO_SHARED_BROWSER", "1")
    monkeypatch.setenv("AISTUDIO_REPLAY_MODE", "http")
    monkeypatch.setenv("AISTUDIO_API_KEY", "testkey")
    monkeypatch.setenv("AISTUDIO_PROXY", "http://127.0.0.1:6152")

    import aistudio_api.config as cfg_mod
    importlib.reload(cfg_mod)
    import aistudio_api.api.app as app_mod
    importlib.reload(app_mod)

    with TestClient(app_mod.app) as client:
        r = client.post(
            "/accounts/acc_browseros/activate",
            headers={"Authorization": "Bearer testkey"},
            timeout=60,
        )
        assert r.status_code == 200, r.text

        r = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer testkey", "Content-Type": "application/json"},
            json={
                "model": "gemma-4-31b-it",
                "messages": [{"role": "user", "content": "Reply with exactly: PHASE2_OK"}],
            },
            timeout=90,
        )
        assert r.status_code == 200, r.text
        assert "PHASE2_OK" in r.json()["choices"][0]["message"]["content"]
