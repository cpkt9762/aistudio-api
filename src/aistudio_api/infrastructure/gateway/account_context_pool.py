from __future__ import annotations

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
