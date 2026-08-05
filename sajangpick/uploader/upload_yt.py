# -*- coding: utf-8 -*-
"""유튜브 쇼츠 업로드 (2026-07-21)

    python upload_yt.py              대기열 첫 편을 올리되 **게시 직전에 멈춘다** (기본값)
    python upload_yt.py --publish    끝까지 게시
    python upload_yt.py --id bbq_golden

🔴 기본값이 "게시 안 함"인 이유: 셀렉터 하나만 어긋나도 엉뚱한 상태로 공개될 수 있다.
   눈으로 확인하고 --publish 를 붙이는 흐름이 안전하다.

🔴 SEL 딕셔너리가 이 파일의 전부다. 스튜디오 UI가 바뀌면 **여기만** 고치면 된다.
   깨졌을 때: python upload_yt.py --pause 로 띄워놓고 F12로 실제 셀렉터를 확인할 것.
"""
import argparse
import sys
import time

from playwright.sync_api import sync_playwright

from common import (close_browser, human_pause, load_queue, log, mark,
                    need_file, next_pending, open_browser)

UPLOAD_URL = "https://www.youtube.com/upload"

SEL = {
    "file":      'input[type="file"]',
    "title":     '#title-textarea #textbox',
    "desc":      '#description-textarea #textbox',
    "thumb":     'input#file-loader',
    "not_kids":  'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]',
    "next":      '#next-button',
    "public":    'tp-yt-paper-radio-button[name="PUBLIC"]',
    "private":   'tp-yt-paper-radio-button[name="PRIVATE"]',
    "done":      '#done-button',
    "signin":    'accounts.google.com',
}


def upload(page, video, publish=False, visibility="public"):
    mp4 = need_file(video["file_yt"], "유튜브용 영상")
    if not mp4:
        return "fail", "영상 파일 없음"

    log("스튜디오 여는 중…", "YT")
    page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    if SEL["signin"] in page.url or "signin" in page.url:
        return "fail", "로그인 필요 → python login.py yt"

    # ① 파일 — 보이지 않는 input에 직접 넣는다 (파일탐색기 창을 띄우지 않는 방법)
    log("영상 올리는 중: {}".format(mp4), "YT")
    page.set_input_files(SEL["file"], mp4)

    # ② 제목·설명 — contenteditable이라 fill이 아니라 지우고 타이핑
    page.wait_for_selector(SEL["title"], timeout=120000)
    human_pause()
    box = page.locator(SEL["title"])
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    box.type(video["title"], delay=25)
    log("제목: {}".format(video["title"]), "YT")

    tags = " ".join("#" + t for t in video.get("tags", []))
    desc = video.get("desc", "")
    if tags:
        desc = desc + "\n\n" + tags
    d = page.locator(SEL["desc"])
    d.click()
    d.type(desc, delay=4)

    # ③ 썸네일
    # 🔴 `input#file-loader` 하나만 노리다 TimeoutError로 계속 실패했다(2026-07-21).
    #    업로드 대화상자에는 file input이 **여러 개**(영상용/썸네일용) 있고 id도 고정이 아니다.
    #    → 페이지의 모든 file input을 훑어 **accept에 image가 들어간 것**을 고른다.
    #      찾은 내용을 로그에 남겨서 다음에 바로 고칠 수 있게 한다.
    thumb = video.get("thumb")
    if thumb:
        tp = need_file(thumb, "썸네일")
        if tp:
            page.wait_for_timeout(2500)
            # 🔴 page.evaluate(document.querySelectorAll)로는 0개가 나온다(2026-07-21).
            #    스튜디오는 Polymer 웹컴포넌트라 file input이 **shadow DOM 안**에 있다.
            #    Playwright 로케이터는 shadow DOM을 뚫으므로 이걸 써야 한다.
            files = page.locator('input[type="file"]')
            n = files.count()
            found = []
            for i in range(n):
                try:
                    found.append({
                        "i": i,
                        "id": files.nth(i).get_attribute("id") or "",
                        "accept": files.nth(i).get_attribute("accept") or "",
                    })
                except Exception:
                    pass
            log("file input {}개: {}".format(n, found), "YT")

            idx = None
            for d in found:
                if "image" in (d.get("accept") or "").lower():
                    idx = d["i"]
                    break
            if idx is None and len(found) > 1:
                idx = found[-1]["i"]   # 보통 마지막에 붙는 게 썸네일용

            if idx is None:
                log("⚠️ 썸네일 입력칸을 못 찾음 — 첨부 건너뜀", "YT")
            else:
                try:
                    page.locator('input[type="file"]').nth(idx).set_input_files(tp, timeout=15000)
                    page.wait_for_timeout(3000)
                    log("✅ 썸네일 첨부 (input #{})".format(idx), "YT")
                except Exception as e:
                    log("⚠️ 썸네일 첨부 실패 ({}) — 건너뜀".format(type(e).__name__), "YT")

    # ④ 아동용 아님 — 이걸 안 고르면 다음으로 못 넘어간다
    human_pause()
    page.locator(SEL["not_kids"]).click()

    # ⑤ 다음 3번 (세부정보 → 동영상 요소 → 검토 → 공개상태)
    for i in range(3):
        human_pause()
        page.locator(SEL["next"]).click()
        log("다음 {}/3".format(i + 1), "YT")

    # ⑥ 공개 상태
    human_pause()
    page.locator(SEL[visibility if visibility in ("public", "private") else "public"]).click()
    log("공개상태: {}".format(visibility), "YT")

    if not publish:
        log("⏸ 게시 직전에서 멈춤. 화면 확인 후 --publish 로 다시 돌리세요.", "YT")
        return "hold", "게시 안 함 (--publish 없음)"

    page.locator(SEL["done"]).click()
    page.wait_for_timeout(6000)
    log("✅ 게시 완료", "YT")
    return "done", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="실제로 게시까지")
    ap.add_argument("--id", help="대기열에서 이 id만")
    ap.add_argument("--visibility", default="public", choices=["public", "private"])
    ap.add_argument("--pause", action="store_true", help="끝나고 창 열어둠 (셀렉터 확인용)")
    args = ap.parse_args()

    q = load_queue()
    if args.id:
        video = next((v for v in q["videos"] if v["id"] == args.id), None)
    else:
        video = next_pending(q, "yt")
    if not video:
        log("올릴 게 없음"); sys.exit(0)

    log("대상: {} ({})".format(video["brand"], video["id"]), "YT")

    with sync_playwright() as pw:
        ctx = open_browser(pw, headed=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            state, note = upload(page, video, args.publish, args.visibility)
        except Exception as e:
            state, note = "fail", "{}: {}".format(type(e).__name__, e)
            log("❌ " + note, "YT")
            try:
                page.screenshot(path="log/yt_fail.png", full_page=True)
                log("실패 화면 → log/yt_fail.png", "YT")
            except Exception:
                pass

        if state != "hold":
            mark(q, video["id"], "yt", state, note)

        # 🔴 백그라운드로 돌리면 stdin이 없다. input()을 무조건 부르면 즉시 터진다.
        if (args.pause or state != "done") and sys.stdin and sys.stdin.isatty():
            input("\n창 닫으려면 엔터 ▶ ")
        elif state == "hold":
            log("창을 열어둡니다 — 확인 후 이 스크립트를 다시 돌리세요", "YT")
            time.sleep(600)
        close_browser(ctx)


if __name__ == "__main__":
    main()
