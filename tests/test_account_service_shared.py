import os
import pytest
from aistudio_api.config import settings


@pytest.mark.skipif(not os.path.exists(
    os.path.expanduser("~/Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json")
), reason="acc_browseros fixture missing")
def test_activate_account_under_shared_mode_does_not_close(monkeypatch):
    monkeypatch.setattr(settings, "shared_browser", True)
    closed = {"hit": False}

    from aistudio_api.infrastructure.gateway.session import BrowserSession
    sess = BrowserSession(port=0)
    sess._pool.register("acc_browseros")

    def fake_close():
        closed["hit"] = True

    monkeypatch.setattr(sess, "_close_sync", fake_close)
    sess.switch_active_account_sync("acc_browseros")
    assert closed["hit"] is False
