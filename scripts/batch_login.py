from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import pyotp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aistudio_api.application.account_service import AccountService
from aistudio_api.infrastructure.account.account_store import AccountStore
from aistudio_api.infrastructure.account.login_service import LoginService, LoginStatus


CREDS_FILE = Path("/tmp/aistudio_creds.txt")
RESULTS_FILE = Path("/tmp/aistudio_batch_results.json")


def parse_creds(text: str) -> list[dict]:
    out: list[dict] = []
    for i, line in enumerate(text.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        parts = line.split("----")
        if len(parts) < 4:
            print(f"skip line {i}: insufficient fields", file=sys.stderr)
            continue
        email = parts[0].strip()
        password = parts[1].strip()
        recovery = parts[2].strip()
        totp_secret = parts[3].strip()
        phone = parts[5].strip() if len(parts) > 5 else ""
        sms_url = parts[6].strip() if len(parts) > 6 else ""
        out.append(
            {
                "idx": i,
                "email": email,
                "password": password,
                "recovery": recovery,
                "totp_secret": totp_secret,
                "phone": phone,
                "sms_url": sms_url,
                "name": f"acc_batch_{i + 1:02d}",
            }
        )
    return out


class BatchLoginDriver(LoginService):
    def __init__(self, *, email: str, password: str, totp_secret: str, recovery: str, port: int):
        super().__init__(port=port)
        self._email = email
        self._password = password
        self._totp_secret = totp_secret
        self._recovery = recovery
        self._unsupported_seen: set[str] = set()

    def _terminal_available(self) -> bool:
        return True

    async def _read_terminal_input(self, prompt: str, *, sensitive: bool = False) -> str:
        text = str(prompt)
        print(f"  [driver] prompt: {text.strip()}", flush=True)

        if "请输入邮箱" in text and "恢复" not in text:
            return self._email
        if "请输入密码" in text:
            return self._password
        if "验证器验证码" in text:
            code = pyotp.TOTP(self._totp_secret.upper()).now()
            print(f"  [driver] TOTP code: {code}", flush=True)
            return code
        if "恢复邮箱" in text:
            return self._recovery or ""
        if "安全码" in text:
            self._unsupported_seen.add("ootp")
            return ""
        if "手机上点击确认" in text:
            self._unsupported_seen.add("dp")
            return ""
        if "请选择登录方式" in text or "登录方式选择页" in text:
            self._unsupported_seen.add("selection")
            return ""
        if "请选择账号" in text or "账号选择页" in text:
            self._unsupported_seen.add("choose_account")
            return ""
        if "输入编号" in text:
            return ""
        return ""


async def run_one(cred: dict, port: int, timeout_s: int = 240) -> dict:
    driver = BatchLoginDriver(
        email=cred["email"],
        password=cred["password"],
        totp_secret=cred["totp_secret"],
        recovery=cred["recovery"],
        port=port,
    )
    store = AccountStore()
    service = AccountService(account_store=store, login_service=driver)

    try:
        session_id = await service.start_login(cred["name"], headless=True, ui_locale="en-US")
    except Exception as exc:
        return {"name": cred["name"], "email": cred["email"], "status": "fail", "error": f"start_login: {exc}"}

    print(f"  [driver] session_id={session_id}", flush=True)

    deadline = time.monotonic() + timeout_s
    last_status = None
    while time.monotonic() < deadline:
        session = service.get_login_status(session_id)
        if session is None:
            return {"name": cred["name"], "email": cred["email"], "status": "fail", "error": "session lost"}
        if session.status != last_status:
            print(f"  [driver] status={session.status.value}", flush=True)
            last_status = session.status
        if session.status == LoginStatus.COMPLETED:
            return {
                "name": cred["name"],
                "email": cred["email"],
                "status": "ok",
                "account_id": session.account_id,
                "detected_email": session.email,
                "unsupported_phases": sorted(driver._unsupported_seen),
            }
        if session.status == LoginStatus.FAILED:
            return {
                "name": cred["name"],
                "email": cred["email"],
                "status": "fail",
                "error": session.error or "unknown",
                "unsupported_phases": sorted(driver._unsupported_seen),
            }
        await asyncio.sleep(2)
    return {
        "name": cred["name"],
        "email": cred["email"],
        "status": "fail",
        "error": "driver timeout",
        "unsupported_phases": sorted(driver._unsupported_seen),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, default=None, help="Run only this account index (0-based)")
    parser.add_argument("--throttle", type=int, default=90, help="Seconds to sleep between accounts")
    parser.add_argument("--timeout", type=int, default=240, help="Per-account timeout seconds")
    parser.add_argument("--port-base", type=int, default=9230, help="Starting browser port")
    args = parser.parse_args()

    if not CREDS_FILE.exists():
        print(f"missing {CREDS_FILE}", file=sys.stderr)
        sys.exit(1)
    creds = parse_creds(CREDS_FILE.read_text())
    print(f"loaded {len(creds)} accounts", flush=True)

    if args.only is not None:
        creds = [c for c in creds if c["idx"] == args.only]
        if not creds:
            print(f"no account with idx={args.only}", file=sys.stderr)
            sys.exit(1)

    results: list[dict] = []
    for i, c in enumerate(creds):
        if i > 0:
            print(f"\n[throttle] sleeping {args.throttle}s...", flush=True)
            await asyncio.sleep(args.throttle)
        port = args.port_base + c["idx"]
        print(f"\n=== [{i + 1}/{len(creds)}] {c['email']} -> {c['name']} (port {port}) ===", flush=True)
        t0 = time.monotonic()
        try:
            res = await run_one(c, port, timeout_s=args.timeout)
        except Exception as exc:
            res = {"name": c["name"], "email": c["email"], "status": "fail", "error": f"exception: {exc}"}
        res["elapsed_s"] = round(time.monotonic() - t0, 1)
        print(f"=== result: {res}", flush=True)
        results.append(res)
        RESULTS_FILE.write_text(json.dumps(results, indent=2, default=str))

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n\n=== SUMMARY: {ok}/{len(results)} succeeded ===", flush=True)
    for r in results:
        print(f"  {r['name']:20s} {r['email']:40s} status={r['status']:5s} elapsed={r.get('elapsed_s', '?')}s", flush=True)
    print(f"\nresults saved to {RESULTS_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
