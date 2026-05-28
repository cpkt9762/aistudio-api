from __future__ import annotations

import hashlib
import logging
import os
import time

from aistudio_api.config import settings
from aistudio_api.infrastructure.gateway.capture import CapturedRequest
from aistudio_api.infrastructure.gateway.session import BrowserSession

logger = logging.getLogger("aistudio")


def _compute_sapisidhash_header(sapisid: str, origin: str = "https://aistudio.google.com") -> str:
    ts = int(time.time())
    raw = f"{ts} {sapisid} {origin}"
    h = hashlib.sha1(raw.encode()).hexdigest()
    return (
        f"SAPISIDHASH {ts}_{h} "
        f"SAPISID1PHASH {ts}_{h} "
        f"SAPISID3PHASH {ts}_{h}"
    )


class RequestReplayService:
    def __init__(self, session: BrowserSession | None):
        self._session = session

    async def replay(self, captured: CapturedRequest | None, body: str, timeout: int | None = None) -> tuple[int, bytes]:
        if not captured:
            return 0, b""

        if timeout is None:
            timeout = settings.timeout_replay

        headers = {k: v for k, v in captured.headers.items() if k.lower() not in ("host", "content-length")}

        mode = os.getenv("AISTUDIO_REPLAY_MODE", "browser").strip().lower()
        force_http = mode == "http"

        try:
            if self._session is not None and not force_http:
                return await self._session.send_hooked_request(
                    body=body,
                    timeout_ms=timeout * 1000,
                )

            return await self._replay_via_http(captured, body, headers, timeout)
        except Exception as exc:
            logger.error("Replay error: %s", exc)
            return 0, str(exc).encode()

    async def _replay_via_http(
        self,
        captured: CapturedRequest,
        body: str,
        headers: dict[str, str],
        timeout: int,
    ) -> tuple[int, bytes]:
        import httpx
        import json
        from pathlib import Path

        cookies = self._load_cookies_from_auth_file()

        headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
        if "SAPISID" in cookies:
            headers["Authorization"] = _compute_sapisidhash_header(cookies["SAPISID"])
        if not any(k.lower() == "origin" for k in headers):
            headers["Origin"] = "https://aistudio.google.com"
        if not any(k.lower() == "referer" for k in headers):
            headers["Referer"] = "https://aistudio.google.com/"

        proxy = os.getenv("AISTUDIO_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        t0 = time.time()
        async with httpx.AsyncClient(proxy=proxy, timeout=timeout, http2=False, follow_redirects=False) as client:
            resp = await client.post(captured.url, content=body, headers=headers, cookies=cookies)
            raw = resp.content
            logger.info(
                "HTTP replay: status=%d, body=%d bytes, cookies=%d, took=%.2fs",
                resp.status_code, len(raw), len(cookies), time.time() - t0,
            )
            return resp.status_code, raw

    def _load_cookies_from_auth_file(self) -> dict[str, str]:
        import json
        from pathlib import Path

        cookies: dict[str, str] = {}
        accounts_dir = Path("data/accounts")
        if not accounts_dir.exists():
            return cookies
        try:
            registry = json.loads((accounts_dir / "registry.json").read_text())
            active_id = registry.get("active_account_id")
            if not active_id:
                return cookies
            auth_path = accounts_dir / active_id / "auth.json"
            if not auth_path.exists():
                return cookies
            state = json.loads(auth_path.read_text())
            for c in state.get("cookies", []):
                if "google" in c.get("domain", ""):
                    cookies[c["name"]] = c["value"]
        except Exception as exc:
            logger.warning("HTTP replay: failed to load cookies from auth.json: %s", exc)
        return cookies
