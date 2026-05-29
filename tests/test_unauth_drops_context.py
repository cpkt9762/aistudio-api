import pytest


@pytest.mark.asyncio
async def test_handle_unauth_drops_context_in_shared_mode(monkeypatch):
    from aistudio_api.config import settings
    monkeypatch.setattr(settings, "shared_browser", True)

    dropped = []

    class FakePool:
        def drop_context_sync(self, aid):
            dropped.append(aid)

    class FakeSession:
        _pool = FakePool()

    from aistudio_api.api.state import runtime_state
    monkeypatch.setattr(runtime_state, "browser_session", FakeSession(), raising=False)

    from aistudio_api.application.api_service_common import handle_unauth_error_in_shared_mode
    result = await handle_unauth_error_in_shared_mode("acc_a")
    assert result is True
    assert dropped == ["acc_a"]


@pytest.mark.asyncio
async def test_handle_unauth_noop_in_legacy_mode(monkeypatch):
    from aistudio_api.config import settings
    monkeypatch.setattr(settings, "shared_browser", False)
    from aistudio_api.application.api_service_common import handle_unauth_error_in_shared_mode
    result = await handle_unauth_error_in_shared_mode("acc_a")
    assert result is False


@pytest.mark.asyncio
async def test_handle_unauth_noop_when_no_pool(monkeypatch):
    from aistudio_api.config import settings
    monkeypatch.setattr(settings, "shared_browser", True)

    class FakeSession:
        _pool = None

    from aistudio_api.api.state import runtime_state
    monkeypatch.setattr(runtime_state, "browser_session", FakeSession(), raising=False)

    from aistudio_api.application.api_service_common import handle_unauth_error_in_shared_mode
    result = await handle_unauth_error_in_shared_mode("acc_a")
    assert result is False
