import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

AUTH_A = Path.home() / "Developer/work/AIGC/aistudio-api/data/accounts/acc_browseros/auth.json"


def _load_state(path: Path) -> dict:
    return json.loads(path.read_text())


async def probe_isolation():
    state_a = _load_state(AUTH_A)
    state_b = {"cookies": [], "origins": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx_a = await browser.new_context(storage_state=state_a)
        ctx_b = await browser.new_context(storage_state=state_b)
        page_a = await ctx_a.new_page()
        page_b = await ctx_b.new_page()
        await page_a.goto("https://aistudio.google.com/", wait_until="domcontentloaded", timeout=30_000)
        await page_b.goto("https://aistudio.google.com/", wait_until="domcontentloaded", timeout=30_000)

        cookies_a = {c["name"] for c in await ctx_a.cookies() if "SAPISID" in c["name"]}
        cookies_b = {c["name"] for c in await ctx_b.cookies() if "SAPISID" in c["name"]}
        url_a = page_a.url
        url_b = page_b.url

        await browser.close()

        assert "SAPISID" in cookies_a, f"ctx_a missing SAPISID: {cookies_a}"
        assert "SAPISID" not in cookies_b, f"ctx_b leaked SAPISID: {cookies_b}"
        assert "accounts.google.com" not in url_a, f"ctx_a should be authenticated, got {url_a}"
        # Google now lands anonymous users at aistudio.google.com/welcome instead of accounts.google.com login.
        authenticated_paths = ("/prompts/", "/app/", "/u/")
        assert not any(p in url_b for p in authenticated_paths), \
            f"ctx_b leaked into authenticated session: {url_b}"
        return True


if __name__ == "__main__":
    ok = asyncio.run(probe_isolation())
    print("ISOLATION_OK" if ok else "ISOLATION_FAIL")
