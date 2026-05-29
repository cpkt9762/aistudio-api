from aistudio_api.infrastructure.cache.snapshot_cache import SnapshotCache


def test_snapshots_isolated_by_account():
    cache = SnapshotCache()
    cache.set_account_scope("acc_a")
    cache.put("prompt-1", "snap-a1", "url", {}, "body-a")
    cache.set_account_scope("acc_b")
    assert cache.get("prompt-1") is None
    cache.put("prompt-1", "snap-b1", "url", {}, "body-b")
    cache.set_account_scope("acc_a")
    cached = cache.get("prompt-1")
    assert cached is not None
    assert cached[0] == "snap-a1"


def test_clear_only_active_account_scope():
    cache = SnapshotCache()
    cache.set_account_scope("acc_a")
    cache.put("p", "sa", "u", {}, "b")
    cache.set_account_scope("acc_b")
    cache.put("p", "sb", "u", {}, "b")
    cache.clear()
    assert cache.get("p") is None
    cache.set_account_scope("acc_a")
    assert cache.get("p") is not None
