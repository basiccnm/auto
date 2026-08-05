# -*- coding: utf-8 -*-
"""인스타 릴스 업로드 (2026-07-21)

    python upload_ig.py            공유 직전까지만 (기본값)
    python upload_ig.py --publish  공유까지

🔴 인스타는 '만들기(새로운 게시물)' → '게시물'을 눌러야 파일칸이 뜬다.
   /create/select/ 같은 주소로 직접 가면 **'create'라는 계정 페이지**로 간다(2026-07-21 헛짚음).
🔴 세로 영상을 올리면 인스타가 알아서 릴스로 만든다. 별도 메뉴 없음.
🔴 BGM 없는 파일을 올리고, 음원은 앱에서 얹는다.
"""
import argparse
import json
import os
import sys

from playwright.sync_api import sync_playwright

from common import HERE, close_browser, log, need_file, open_browser

LOGDIR = os.path.join(HERE, "log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--id")
    args = ap.parse_args()

    q = json.load(open(os.path.join(HERE, "queue.json"), encoding="utf-8"))
    v = None
    for x in q["videos"]:
        if args.id is None or x["id"] == args.id:
            v = x
            break
    if not v:
        log("올릴 게 없음", "IG"); sys.exit(0)

    mp4 = need_file(v["file_nobgm"], "BGM 없는 영상")
    if not mp4:
        sys.exit(1)

    cap = v.get("desc", "") + "\n\n" + " ".join("#" + t for t in v.get("tags", []))

    with sync_playwright() as pw:
        ctx = open_browser(pw, headed=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30000)

        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(7000)
        if "/accounts/login" in page.url:
            log("❌ 로그인 필요 → python login.py ig", "IG")
            close_browser(ctx); sys.exit(1)
        log("로그인 확인", "IG")

        # 만들기 → 게시물
        page.locator('svg[aria-label="새로운 게시물"]').first.click()
        page.wait_for_timeout(2500)
        for sel in ['a:has-text("게시물")', 'div[role="button"]:has-text("게시물")',
                    'span:text-is("게시물")']:
            try:
                loc = page.locator(sel).first
                if loc.count():
                    loc.click(timeout=6000)
                    log("게시물 메뉴 열림", "IG")
                    break
            except Exception:
                continue

        page.wait_for_timeout(5000)
        fi = page.locator('input[type="file"]')
        if not fi.count():
            log("❌ 파일칸 못 찾음", "IG")
            page.screenshot(path=os.path.join(LOGDIR, "ig_nofile.png"))
            close_browser(ctx); sys.exit(1)

        fi.first.set_input_files(mp4, timeout=120000)
        log("영상 넣음 — 처리 대기", "IG")
        page.wait_for_timeout(20000)
        page.screenshot(path=os.path.join(LOGDIR, "ig_1_loaded.png"))

        # 다음 2번 (자르기 → 필터 → 문구)
        for i in range(2):
            try:
                nxt = page.locator('div[role="button"]:has-text("다음")').first
                if nxt.count():
                    nxt.click(timeout=10000)
                    page.wait_for_timeout(4000)
                    log("다음 {}/2".format(i + 1), "IG")
            except Exception as e:
                log("다음 {} 실패 ({})".format(i + 1, type(e).__name__), "IG")

        # 문구
        try:
            box = page.locator('div[contenteditable="true"][role="textbox"]').first
            box.click()
            box.type(cap, delay=3)
            log("문구 입력", "IG")
        except Exception as e:
            log("문구 입력 실패 ({})".format(type(e).__name__), "IG")

        page.wait_for_timeout(2500)
        page.screenshot(path=os.path.join(LOGDIR, "ig_2_caption.png"))

        if not args.publish:
            log("⏸ 공유 직전에서 멈춤. 화면 확인 후 --publish", "IG")
            return

        page.locator('div[role="button"]:has-text("공유하기")').first.click()
        page.wait_for_timeout(15000)
        page.screenshot(path=os.path.join(LOGDIR, "ig_3_done.png"))
        log("✅ 공유 완료", "IG")


if __name__ == "__main__":
    main()
