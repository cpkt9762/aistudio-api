import pytest

from aistudio_api.infrastructure.gateway.account_context_pool import (
    AccountContextPool,
    AccountContextState,
)


def test_account_context_state_init_defaults():
    state = AccountContextState(account_id="acc_xyz")
    assert state.account_id == "acc_xyz"
    assert state.context is None
    assert state.hook_page is None
    assert state.templates == {}
    assert state.snap_key is None
    assert state.installed_hooks is False
    assert state.last_used_ts == 0.0


def test_pool_register_and_get():
    pool = AccountContextPool(max_contexts=5)
    pool.register("acc_a")
    pool.register("acc_b")
    assert pool.has("acc_a")
    assert pool.has("acc_b")
    assert not pool.has("acc_c")
    state_a = pool.get("acc_a")
    assert state_a.account_id == "acc_a"


def test_pool_active_account_swap():
    pool = AccountContextPool(max_contexts=5)
    pool.register("acc_a")
    pool.register("acc_b")
    pool.set_active("acc_b")
    assert pool.active_account_id == "acc_b"
    assert pool.active.account_id == "acc_b"


def test_pool_eviction_when_over_capacity():
    pool = AccountContextPool(max_contexts=2)
    pool.register("acc_a")
    pool.register("acc_b")
    pool.register("acc_c")
    assert pool.has("acc_c")
    assert sum(1 for k in ("acc_a", "acc_b") if pool.has(k)) == 1


def test_pool_set_active_unknown_raises():
    pool = AccountContextPool(max_contexts=5)
    with pytest.raises(KeyError):
        pool.set_active("acc_missing")


def test_pool_starts_without_browser():
    pool = AccountContextPool(max_contexts=5)
    assert pool.browser_is_alive() is False


def test_pool_ensure_browser_idempotent(monkeypatch):
    pool = AccountContextPool(max_contexts=5)
    launches = {"count": 0}

    def fake_launch():
        launches["count"] += 1
        return object()

    monkeypatch.setattr(pool, "_launch_browser_sync", fake_launch)
    pool.ensure_browser_sync()
    pool.ensure_browser_sync()
    assert launches["count"] == 1


def test_pool_ensure_context_uses_browser(monkeypatch):
    pool = AccountContextPool(max_contexts=5)
    calls = {"new_context": 0}

    class FakeBrowser:
        def new_context(self, **kwargs):
            calls["new_context"] += 1
            return f"ctx_{calls['new_context']}"

    monkeypatch.setattr(pool, "_launch_browser_sync", lambda: FakeBrowser())
    pool.register("acc_a")
    pool.ensure_context_sync("acc_a", auth_state={"cookies": [], "origins": []})
    pool.ensure_context_sync("acc_a", auth_state={"cookies": [], "origins": []})
    assert calls["new_context"] == 1
    assert pool.get("acc_a").context == "ctx_1"


def test_pool_health_reports_per_account():
    pool = AccountContextPool(max_contexts=5)
    pool.register("acc_a")
    pool.register("acc_b")
    health = pool.health_snapshot()
    assert set(health.keys()) == {"acc_a", "acc_b"}
    for entry in health.values():
        assert "context_alive" in entry
        assert "last_used_ts" in entry


def test_drop_context_keeps_browser():
    pool = AccountContextPool(max_contexts=5)

    class FakeBrowser:
        def __init__(self):
            self.contexts_created = 0

        def new_context(self, **kwargs):
            self.contexts_created += 1

            class FakeCtx:
                def close(inner): pass

            return FakeCtx()

    monkeypatch_browser = FakeBrowser()
    pool._browser = monkeypatch_browser
    pool.register("acc_a")
    pool.ensure_context_sync("acc_a")
    pool.drop_context_sync("acc_a")
    assert pool.get("acc_a").context is None
    assert pool._browser is monkeypatch_browser
