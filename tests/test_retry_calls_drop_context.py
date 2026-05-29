import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_retry_loop_drops_context_before_switching(monkeypatch):
    from aistudio_api.config import settings
    monkeypatch.setattr(settings, "shared_browser", True)

    calls = []

    async def fake_drop(aid):
        calls.append(("drop", aid))
        return True

    async def fake_switch():
        calls.append(("switch", None))
        return True

    with patch("aistudio_api.application.api_service_common.handle_unauth_error_in_shared_mode", new=AsyncMock(side_effect=fake_drop)), \
         patch("aistudio_api.application.api_service_common.try_switch_account", new=AsyncMock(side_effect=fake_switch)):
        from aistudio_api.application.api_service_common import on_unauth_response
        await on_unauth_response("acc_a")

    assert calls == [("drop", "acc_a"), ("switch", None)], (
        f"expected drop_context BEFORE try_switch_account, got order: {calls}"
    )
