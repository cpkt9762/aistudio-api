"""In-memory snapshot cache."""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Optional

from aistudio_api.config import settings

logger = logging.getLogger("aistudio")


class SnapshotCache:
    def __init__(self, ttl: int | None = None, max_size: int | None = None):
        self._by_account: dict[str, OrderedDict[str, tuple]] = {}
        self._active_account: str = "__default__"
        self.ttl = ttl or settings.snapshot_cache_ttl
        self.max_size = max_size or settings.snapshot_cache_max

    @property
    def _cache(self) -> OrderedDict[str, tuple]:
        return self._by_account.setdefault(self._active_account, OrderedDict())

    def set_account_scope(self, account_id: str) -> None:
        self._active_account = account_id or "__default__"
        if self._active_account not in self._by_account:
            self._by_account[self._active_account] = OrderedDict()

    @staticmethod
    def _hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[tuple]:
        key = self._hash(prompt)
        if key not in self._cache:
            return None

        snapshot, url, headers, body, ts = self._cache[key]
        age = time.time() - ts
        if age >= self.ttl:
            del self._cache[key]
            logger.info("Snapshot 缓存过期: %s...", key[:8])
            return None

        # LRU: move to end
        self._cache.move_to_end(key)
        logger.info("Snapshot 缓存命中: %s... (%ss ago)", key[:8], int(age))
        return snapshot, url, headers, body

    def put(self, prompt: str, snapshot: str, url: str, headers: dict, body: str):
        key = self._hash(prompt)
        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.info("Snapshot 缓存淘汰: %s...", evicted_key[:8])
        self._cache[key] = (snapshot, url, headers, body, time.time())
        logger.info("Snapshot 已缓存: %s...", key[:8])

    def clear(self):
        self._cache.clear()
