from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AccountContextState:
    account_id: str
    context: Any = None
    hook_page: Any = None
    templates: dict[str, dict[str, Any]] = field(default_factory=dict)
    snap_key: str | None = None
    installed_hooks: bool = False
    last_used_ts: float = 0.0


class AccountContextPool:
    def __init__(self, max_contexts: int = 16):
        self._max = max_contexts
        self._states: dict[str, AccountContextState] = {}
        self._active_id: str | None = None

    def has(self, account_id: str) -> bool:
        return account_id in self._states

    def get(self, account_id: str) -> AccountContextState:
        return self._states[account_id]

    @property
    def active_account_id(self) -> str | None:
        return self._active_id

    @property
    def active(self) -> AccountContextState:
        if self._active_id is None:
            raise RuntimeError("no active account")
        return self._states[self._active_id]

    def register(self, account_id: str) -> AccountContextState:
        if account_id in self._states:
            self._states[account_id].last_used_ts = time.time()
            return self._states[account_id]
        if len(self._states) >= self._max:
            self._evict_lru()
        state = AccountContextState(account_id=account_id, last_used_ts=time.time())
        self._states[account_id] = state
        if self._active_id is None:
            self._active_id = account_id
        return state

    def set_active(self, account_id: str) -> AccountContextState:
        if account_id not in self._states:
            raise KeyError(account_id)
        self._active_id = account_id
        self._states[account_id].last_used_ts = time.time()
        return self._states[account_id]

    def _evict_lru(self) -> str | None:
        if not self._states:
            return None
        evictable = [s for s in self._states.values() if s.account_id != self._active_id]
        if not evictable:
            return None
        victim = min(evictable, key=lambda s: s.last_used_ts)
        del self._states[victim.account_id]
        return victim.account_id
