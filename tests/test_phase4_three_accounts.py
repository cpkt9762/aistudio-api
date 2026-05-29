import os
import time
import importlib
import pytest
from fastapi.testclient import TestClient

from aistudio_api.config import settings


def _list_account_dirs():
    return sorted(d for d in os.listdir("data/accounts") if d.startswith("acc_"))


@pytest.mark.skipif(
    not os.getenv("AISTUDIO_TEST_THREE_ACCOUNTS"),
    reason="set AISTUDIO_TEST_THREE_ACCOUNTS=1 to run with >=3 real AI-Studio-activated fixtures",
)
def test_three_accounts_serial_isolation(monkeypatch):
    monkeypatch.setenv("AISTUDIO_SHARED_BROWSER", "1")
    monkeypatch.setenv("AISTUDIO_REPLAY_MODE", "http")
    monkeypatch.setenv("AISTUDIO_API_KEY", "testkey")
    monkeypatch.setenv("AISTUDIO_PROXY", "http://127.0.0.1:6152")
    monkeypatch.setattr(settings, "shared_browser", True)

    import aistudio_api.config as cfg_mod
    importlib.reload(cfg_mod)
    import aistudio_api.api.app as app_mod
    importlib.reload(app_mod)

    account_ids = _list_account_dirs()[:3]
    markers = ["AAA_OK", "BBB_OK", "CCC_OK"]

    with TestClient(app_mod.app) as client:
        switch_latencies = []
        last_switch = None
        for aid, marker in zip(account_ids, markers):
            t0 = time.time()
            r = client.post(
                f"/accounts/{aid}/activate",
                headers={"Authorization": "Bearer testkey"},
                timeout=60,
            )
            switch_dt = time.time() - t0
            assert r.status_code == 200, r.text
            if last_switch is not None:
                switch_latencies.append(switch_dt)
            last_switch = aid

            r = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer testkey", "Content-Type": "application/json"},
                json={
                    "model": "gemma-4-31b-it",
                    "messages": [{"role": "user", "content": f"Reply only with: {marker}"}],
                },
                timeout=90,
            )
            assert r.status_code == 200, r.text
            assert marker in r.json()["choices"][0]["message"]["content"]

        assert all(dt < 0.5 for dt in switch_latencies), f"account switch over 500ms: {switch_latencies}"
