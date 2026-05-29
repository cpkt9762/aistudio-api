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
