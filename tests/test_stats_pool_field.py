import importlib
from fastapi.testclient import TestClient
from aistudio_api.config import settings


def test_stats_returns_pool_in_shared_mode(monkeypatch):
    monkeypatch.setenv("AISTUDIO_SHARED_BROWSER", "1")
    monkeypatch.setenv("AISTUDIO_API_KEY", "testkey")
    monkeypatch.setattr(settings, "shared_browser", True)

    import aistudio_api.config as cfg_mod
    importlib.reload(cfg_mod)
    import aistudio_api.api.app as app_mod
    importlib.reload(app_mod)

    from aistudio_api.api import state as state_mod
    from aistudio_api.infrastructure.gateway.account_context_pool import AccountContextPool

    class FakeSession:
        _pool = AccountContextPool(max_contexts=5)

    with TestClient(app_mod.app) as client:
        state_mod.runtime_state.browser_session = FakeSession()
        state_mod.runtime_state.browser_session._pool.register("acc_x")
        r = client.get("/stats", headers={"Authorization": "Bearer testkey"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "pool" in body, body
        assert "acc_x" in body["pool"]


def test_stats_no_pool_field_in_legacy_mode(monkeypatch):
    monkeypatch.delenv("AISTUDIO_SHARED_BROWSER", raising=False)
    monkeypatch.setenv("AISTUDIO_API_KEY", "testkey")
    monkeypatch.setattr(settings, "shared_browser", False)

    import aistudio_api.config as cfg_mod
    importlib.reload(cfg_mod)
    import aistudio_api.api.app as app_mod
    importlib.reload(app_mod)

    with TestClient(app_mod.app) as client:
        r = client.get("/stats", headers={"Authorization": "Bearer testkey"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("pool") is None
