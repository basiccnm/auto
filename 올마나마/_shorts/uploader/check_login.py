# -*- coding: utf-8 -*-
"""로그인 상태 확인 (2026-07-21)

    python check_login.py

🔴 왜 따로 있나 — login.py가 탭을 "지켜보는" 방식은 세 번 다 틀렸다(2026-07-21).
     ① 탭을 막 열면 리다이렉트 전이라 로그인된 것처럼 보인다 (틱톡 오판 2회)
     ② 대표님이 탭을 옮겨 다니면 붙잡고 있던 탭이 딴 페이지가 된다 (유튜브 오판)
   → 지켜보지 않는다. **새 탭을 열어 직접 찾아가 보고 최종 주소로 판정한다.**
     이건 브라우저가 실제로 하는 일과 같아서 틀릴 수가 없다.

로그인 창을 닫은 뒤에 돌려야 한다(프로필을 동시에 못 연다).
"""
from playwright.sync_api import sync_playwright

from common import PLATFORM_NAME, close_browser, log, open_browser

# (확인하러 갈 주소, 로그인 안 됐을 때 튕기는 주소 조각)
PROBE = [
    ("yt", "https://studio.youtube.com",
     ["accounts.google.com", "youtube.com/signin", "ServiceLogin"]),
    ("tt", "https://www.tiktok.com/tiktokstudio/upload",
     ["/login", "/signup"]),
    ("ig", "https://www.instagram.com/",
     ["/accounts/login", "/accounts/signup"]),
]


def main():
    result = {}
    with sync_playwright() as pw:
        ctx = open_browser(pw, headed=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for key, url, bad in PROBE:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                # 🔴 리다이렉트가 끝날 때까지 기다린다. 이걸 안 해서 계속 틀렸다.
                page.wait_for_timeout(4000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                final = page.url
            except Exception as e:
                result[key] = (False, "{}: {}".format(type(e).__name__, e))
                continue
            ok = not any(b in final for b in bad)
            result[key] = (ok, final)

        close_browser(ctx)

    print()
    print("=" * 58)
    for key, _, _ in PROBE:
        ok, info = result.get(key, (False, "확인 못 함"))
        mark = "✅ 로그인됨  " if ok else "❌ 로그인 필요"
        print("  {:6} {}  {}".format(PLATFORM_NAME[key], mark, info[:60]))
    print("=" * 58)

    need = [PLATFORM_NAME[k] for k, _, _ in PROBE if not result.get(k, (False,))[0]]
    if need:
        log("로그인 필요: {} → python login.py {}".format(
            ", ".join(need),
            " ".join(k for k, _, _ in PROBE if not result.get(k, (False,))[0])))
    else:
        log("✅ 전부 로그인됨 — 업로드 진행 가능")


if __name__ == "__main__":
    main()
