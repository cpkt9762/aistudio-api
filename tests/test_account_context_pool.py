from aistudio_api.infrastructure.gateway.account_context_pool import AccountContextState


def test_account_context_state_init_defaults():
    state = AccountContextState(account_id="acc_xyz")
    assert state.account_id == "acc_xyz"
    assert state.context is None
    assert state.hook_page is None
    assert state.templates == {}
    assert state.snap_key is None
    assert state.installed_hooks is False
    assert state.last_used_ts == 0.0
