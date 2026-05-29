import pytest
from aistudio_api.config import settings
from aistudio_api.infrastructure.gateway.replay import RequestReplayService


class FakeSession:
    def __init__(self, cookies):
        self._cookies = cookies

    async def get_cookies_for_active_account(self):
        return self._cookies


@pytest.mark.asyncio
async def test_replay_uses_session_cookies_in_shared_mode(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    fake = FakeSession({"SAPISID": "from-session", "HSID": "x"})
    svc = RequestReplayService(session=fake)
    got = await svc._fetch_cookies_for_replay()
    assert got == {"SAPISID": "from-session", "HSID": "x"}


@pytest.mark.asyncio
async def test_replay_uses_auth_file_in_non_shared_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "shared_browser", False)
    svc = RequestReplayService(session=None)
    got = await svc._fetch_cookies_for_replay()
    assert isinstance(got, dict)
