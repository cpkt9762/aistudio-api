from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from aistudio_api.infrastructure.browser.browser_engine import (
    build_browser_context_options,
    sync_launch_browser,
)


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
        self._browser = None
        self._playwright = None
        self._cf = None
        self._lock = threading.RLock()

    def browser_is_alive(self) -> bool:
        return self._browser is not None

    def _launch_browser_sync(self):
        return sync_launch_browser()

    def ensure_browser_sync(self):
        with self._lock:
            if self._browser is not None:
                return self._browser
            result = self._launch_browser_sync()
            if isinstance(result, tuple) and len(result) == 3:
                self._browser, self._cf, self._playwright = result
            else:
                self._browser = result
            return self._browser

    def close_browser_sync(self):
        with self._lock:
            for state in list(self._states.values()):
                ctx = state.context
                if ctx is not None:
                    try:
                        ctx.close()
                    except Exception:
                        pass
                state.context = None
                state.hook_page = None
                state.installed_hooks = False
            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:
                    pass
            self._browser = None
            self._playwright = None
            self._cf = None

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

    def ensure_context_sync(self, account_id: str, *, auth_state: dict | None = None):
        with self._lock:
            self.ensure_browser_sync()
            state = self._states.get(account_id)
            if state is None:
                state = self.register(account_id)
            if state.context is not None:
                state.last_used_ts = time.time()
                return state.context
            options = build_browser_context_options()
            if auth_state is not None:
                options["storage_state"] = auth_state
            state.context = self._browser.new_context(**options)
            state.last_used_ts = time.time()
            return state.context

    def drop_context_sync(self, account_id: str) -> None:
        with self._lock:
            state = self._states.get(account_id)
            if state is None:
                return
            ctx = state.context
            state.context = None
            state.hook_page = None
            state.installed_hooks = False
            state.templates.clear()
            state.snap_key = None
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass

    def health_snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {
                aid: {
                    "context_alive": state.context is not None,
                    "hook_page_alive": state.hook_page is not None,
                    "last_used_ts": state.last_used_ts,
                    "is_active": aid == self._active_id,
                }
                for aid, state in self._states.items()
            }
