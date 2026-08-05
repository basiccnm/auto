# -*- coding: utf-8 -*-
"""최초 1회 로그인 (2026-07-21)

    python login.py            4곳 전부 (탭 4개가 한꺼번에 열린다)
    python login.py yt nv      골라서

🔴 비밀번호는 **대표님이 직접 창에 입력**하신다. 스크립트는 창만 띄우고 지켜본다.
   저장되는 건 로그인 뒤의 세션 쿠키뿐이고, 그건 uploader_profile\ 폴더에 남는다.
🔴 uploader_profile\ 은 로그인된 계정 그 자체다.
   gdrive_backup.ps1 의 제외목록에 넣어놨다 — 폴더명 바꾸면 클라우드로 새어나간다.

🔴 엔터를 기다리지 않는다(2026-07-21).
   백그라운드로 돌리면 stdin이 없어서 input()이 즉시 터진다.
   대신 **탭 주소가 로그인 페이지를 벗어나는지 3초마다 훔쳐본다.**
   4곳 다 끝나면 알아서 저장하고 닫는다. 창을 직접 닫아도 저장된다.
"""
import sys
import time

from playwright.sync_api import sync_playwright

from common import PLATFORM_NAME, PLATFORMS, close_browser, log, open_browser

# (열 주소, 아직 로그인 안 된 상태를 뜻하는 주소 조각들)
CHECK = {
    "yt": ("https://studio.youtube.com",
           ["accounts.google.com", "youtube.com/signin", "/ServiceLogin"]),
    "tt": ("https://www.tiktok.com/tiktokstudio/upload",
           ["/login", "/signup"]),
    "ig": ("https://www.instagram.com/",
           ["/accounts/login", "/accounts/signup"]),
    "nv": ("https://nid.naver.com/nidlogin.login",
           ["nidlogin", "nid.naver.com/login"]),
}

WAIT_LIMIT = 30 * 60   # 30분이면 충분. 넘으면 알아서 끝낸다


def logged_in(url, bad_bits):
    return not any(b in url for b in bad_bits)


def main():
    want = [a for a in sys.argv[1:] if a in PLATFORMS] or PLATFORMS

    with sync_playwright() as pw:
        ctx = open_browser(pw, headed=True, slow=0)

        # 탭을 플랫폼 수만큼 준비
        tabs = {}
        for i, p in enumerate(want):
            page = ctx.pages[0] if (i == 0 and ctx.pages) else ctx.new_page()
            url, _ = CHECK[p]
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                log("{} 첫 로딩 실패 ({}) — 탭에서 직접 열어주세요".format(
                    PLATFORM_NAME[p], type(e).__name__))
            tabs[p] = page

        print()
        print("  ┌──────────────────────────────────────────────┐")
        print("  │  탭 {}개가 열렸습니다. 각 탭에서 로그인해 주세요.   │".format(len(want)))
        print("  │  다 되면 이 스크립트가 알아서 저장하고 닫습니다.    │")
        print("  └──────────────────────────────────────────────┘")
        print()

        # 🔴 한 번 보고 바로 "로그인됨"으로 굳히면 안 된다(2026-07-21 사고).
        #    탭을 막 열었을 때는 아직 로그인 페이지로 **리다이렉트되기 전**이라
        #    주소가 멀쩡해 보인다. 틱톡을 이렇게 잘못 통과시켰다.
        #    → 3초 간격으로 연속 STABLE번 멀쩡해야 인정한다.
        STABLE = 3
        streak = dict((p, 0) for p in want)

        # 🔴 감지 결과로 창을 닫지 않는다(2026-07-21).
        #    로그인 도중에 잘못 통과시켜 창을 닫아버리는 사고가 반복됐다.
        #    여기서는 **창을 열어두기만** 하고, 실제 판정은 check_login.py가 한다.
        done = set()
        t0 = time.time()
        last_report = 0
        while time.time() - t0 < WAIT_LIMIT:
            time.sleep(3)

            # 🔴 창을 닫아도 크롬 프로세스가 남아 헛도는 사고(2026-07-21).
            #    페이지가 하나도 없거나 주소를 못 읽으면 = 창이 죽은 것. 미련 없이 끝낸다.
            try:
                alive = [pg for pg in ctx.pages if not pg.is_closed()]
            except Exception:
                log("브라우저 연결 끊김 — 여기까지 저장됨")
                break
            if not alive:
                log("창이 모두 닫혔습니다 — 여기까지 저장됨")
                break

            for p in want:
                if p in done:
                    continue
                page = tabs[p]
                if page.is_closed():
                    done.add(p)
                    log("{} 탭 닫힘 — 건너뜀".format(PLATFORM_NAME[p]))
                    continue
                try:
                    url = page.url
                except Exception:
                    continue
                _, bad = CHECK[p]
                if url and url != "about:blank" and logged_in(url, bad):
                    streak[p] += 1
                    if streak[p] >= STABLE:
                        done.add(p)
                        log("✅ {} 로그인 확인  ({})".format(PLATFORM_NAME[p], url[:70]))
                else:
                    streak[p] = 0

            # 30초마다 어디까지 됐는지 알려준다 (백그라운드에서도 보이게)
            if time.time() - last_report > 30:
                last_report = time.time()
                waiting = [PLATFORM_NAME[p] for p in want if p not in done]
                log("…대기 중: {}".format(", ".join(waiting) if waiting else "없음"))

        left = [PLATFORM_NAME[p] for p in want if p not in done]
        if left:
            log("⚠️ 아직 안 된 곳: {}".format(", ".join(left)))
        else:
            log("✅ 4곳 전부 로그인 저장 완료")

        close_browser(ctx)   # 여기서 프로필에 쿠키가 기록되고 프로세스도 죽는다
        log("프로필 저장됨 → uploader_profile\\")


if __name__ == "__main__":
    main()
