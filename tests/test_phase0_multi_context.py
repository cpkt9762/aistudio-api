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


async def probe_snapshot_independence():
    state_a = _load_state(AUTH_A)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx_a = await browser.new_context(storage_state=state_a)
        ctx_b = await browser.new_context(storage_state=state_a)

        async def get_visit_id(ctx):
            page = await ctx.new_page()
            await page.goto("https://aistudio.google.com/prompts/new_chat", wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(4_000)
            return await page.evaluate("() => localStorage.getItem('aistudio.visitorId') || document.cookie.length")

        marker_a = await get_visit_id(ctx_a)
        marker_b = await get_visit_id(ctx_b)
        await browser.close()
        return marker_a is not None and marker_b is not None


async def probe_concurrent_eval():
    state_a = _load_state(AUTH_A)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        contexts = [await browser.new_context(storage_state=state_a) for _ in range(5)]
        pages = []
        for ctx in contexts:
            page = await ctx.new_page()
            await page.goto("about:blank")
            pages.append(page)

        async def heavy(p, i):
            return await p.evaluate("(i) => { const t=Date.now(); while(Date.now()-t<150) {} return i*2; }", i)

        import time
        start = time.time()
        results = await asyncio.gather(*(heavy(p, i) for i, p in enumerate(pages)))
        wall = time.time() - start
        await browser.close()
        return results == [0, 2, 4, 6, 8] and wall < 1.0


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "isolation"
    if mode == "isolation":
        ok = asyncio.run(probe_isolation())
    elif mode == "snapshot":
        ok = asyncio.run(probe_snapshot_independence())
    elif mode == "concurrent":
        ok = asyncio.run(probe_concurrent_eval())
    else:
        raise SystemExit(f"unknown mode {mode}")
    print(f"{mode.upper()}_{'OK' if ok else 'FAIL'}")
