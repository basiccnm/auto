# -*- coding: utf-8 -*-
"""인스타·스레드 토큰 갱신 (2026-07-24)

    python refresh_token.py          둘 다 갱신
    python refresh_token.py ig       인스타만
    python refresh_token.py th       스레드만

🔴 월 1회 돌리면 된다. 갱신하면 다시 60일이 된다(횟수 제한 없음).
🔴 ⚠️ 60일 지나 **완전히 만료되면 갱신도 안 된다.** 그땐 앱 대시보드에서
   새로 발급받아 .env에 손으로 넣어야 한다 — 그러니 스케줄러를 꼭 걸어둘 것.
🔴 갱신은 토큰 발급 후 24시간이 지나야 된다(메타 정책). 발급 직후 돌리면 실패한다.

작업 스케줄러 등록 (관리자 PowerShell에서 한 번만):
  schtasks /create /tn "메타토큰갱신" /tr "python \"<이 파일 경로>\"" /sc monthly /d 1 /st 10:00
"""
import sys
import time

from meta_common import IG_BASE, TH_BASE, api, load_env, log, save_env


def refresh(kind, env):
    """kind = 'ig' | 'th'"""
    if kind == "ig":
        base, key, grant, name = IG_BASE, "IG_ACCESS_TOKEN", "ig_refresh_token", "인스타"
    else:
        base, key, grant, name = TH_BASE, "TH_ACCESS_TOKEN", "th_refresh_token", "스레드"

    token = env.get(key)
    if not token:
        log("{} 토큰이 .env에 없다 — 건너뜀".format(name), "SKIP")
        return None

    r = api(base + "/refresh_access_token", {"grant_type": grant, "access_token": token})
    new = r.get("access_token")
    days = round(r.get("expires_in", 0) / 86400, 1)
    if not new:
        log("{} 갱신 실패: {}".format(name, r), "FAIL")
        return None

    log("{} 갱신 완료 — 앞으로 {}일".format(name, days), "OK")
    return {key: new}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    env = load_env()
    updates = {}

    for kind in (["ig", "th"] if which == "all" else [which]):
        got = refresh(kind, env)
        if got:
            updates.update(got)
        time.sleep(1)  # 연속 호출 사이 숨 — 메타가 가끔 튕긴다

    if updates:
        save_env(updates)
        log(".env 저장 완료 ({}개)".format(len(updates)), "SAVE")
    else:
        log("갱신된 토큰 없음", "WARN")


if __name__ == "__main__":
    main()
