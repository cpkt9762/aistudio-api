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
