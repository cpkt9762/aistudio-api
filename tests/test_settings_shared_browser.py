import importlib
import os


def test_default_off(monkeypatch):
    monkeypatch.delenv("AISTUDIO_SHARED_BROWSER", raising=False)
    import aistudio_api.config as cfg
    importlib.reload(cfg)
    assert cfg.settings.shared_browser is False


def test_env_on(monkeypatch):
    monkeypatch.setenv("AISTUDIO_SHARED_BROWSER", "1")
    import aistudio_api.config as cfg
    importlib.reload(cfg)
    assert cfg.settings.shared_browser is True
