def test_runtime_state_has_browser_session_field():
    from aistudio_api.api import state as state_mod
    assert hasattr(state_mod.runtime_state, "browser_session")
    assert state_mod.runtime_state.browser_session is None


def test_runtime_state_wired_after_startup(monkeypatch):
    monkeypatch.setenv("AISTUDIO_API_KEY", "testkey")
    import importlib
    import aistudio_api.api.app as app_mod
    importlib.reload(app_mod)
    from fastapi.testclient import TestClient
    from aistudio_api.api import state as state_mod
    with TestClient(app_mod.app):
        assert state_mod.runtime_state.client is not None
        assert state_mod.runtime_state.browser_session is not None
