# -*- coding: utf-8 -*-
"""틱톡 업로드 (2026-07-25)

    python upload_tt.py                     게시 직전까지만 (기본값)
    python upload_tt.py --publish           게시까지
    python upload_tt.py --id pizza1_domino_potato --publish

🔴 기본값이 "게시 안 함"인 이유: 셀렉터 하나만 어긋나도 엉뚱한 상태로 올라간다.
   눈으로 확인하고 --publish 를 붙이는 흐름이 안전하다. (upload_yt.py 와 같은 원칙)

🔴 **음악은 안 넣는다.** 우리 영상은 말로 설명하는 구조라 음원을 깔면 내용이 묻힌다.
   마라탕 편들도 BGM 없이 효과음만 쓴다("말이 잘 들려야 한다", 2026-07-22).
   틱톡에서 음원을 붙이면 노출엔 유리하지만 이탈이 난다. 필요하면 **앱에서 직접** 얹을 것.

🔴 틱톡 웹 업로드는 `tiktok.com/tiktokstudio/upload` 다. 로그인 세션은 uploader_profile 에 있다.
   풀렸으면 `python login.py tt`.

🔴 SEL 딕셔너리가 이 파일의 전부다. 틱톡 UI 가 바뀌면 **여기만** 고치면 된다.
"""
import argparse
import json
import os
import sys

from playwright.sync_api import sync_playwright

from common import HERE, close_browser, log, need_file, open_browser

LOGDIR = os.path.join(HERE, "log")
UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
TAG = "TT"

# 🔴 틱톡은 셀렉터를 자주 바꾼다. 후보를 여러 개 두고 먼저 잡히는 걸 쓴다
SEL = {
    "file": 'input[type="file"]',
    "caption": [
        'div[contenteditable="true"][role="combobox"]',
        'div[contenteditable="true"]',
        'div[data-e2e="caption_container"] div[contenteditable="true"]',
    ],
    # 🔴 has-text 는 **부분 일치**라 왼쪽 메뉴의 "게시물"이 먼저 걸렸다(2026-07-25 실제 사고).
    #    그걸 누르면 페이지를 떠나면서 "끝낼까요?" 창이 뜨고, 영상은 안 올라간다.
    #    → **정확히 일치(text-is)** 로 잡고, 사이드바를 제외하기 위해 폼 영역으로 좁힌다.
    "post": [
        'div[data-e2e="post_video_button"]',
        'button:text-is("게시")',
        'button:text-is("Post")',
        'div[role="button"]:text-is("게시")',
    ],
}
# 틱톡 캡션은 2,200자. 넘으면 잘려서 해시태그가 날아간다
CAP_MAX = 2200


def first_hit(page, sels, timeout=8000):
    """후보 셀렉터를 순서대로 시도해 먼저 잡히는 locator 를 준다."""
    for s in sels:
        try:
            loc = page.locator(s).first
            if loc.count():
                loc.wait_for(state="visible", timeout=timeout)
                return loc
        except Exception:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="게시까지 (없으면 직전에 멈춤)")
    ap.add_argument("--id", help="queue.json 의 특정 id 만")
    args = ap.parse_args()

    q = json.load(open(os.path.join(HERE, "queue.json"), encoding="utf-8"))
    v = None
    for x in q["videos"]:
        if args.id:
            if x["id"] == args.id:
                v = x
                break
        elif x.get("status", {}).get("tt") != "done":
            v = x
            break
    if not v:
        log("올릴 게 없다", TAG)
        sys.exit(0)

    # 🔴 BGM 없는 파일을 쓴다. 틱톡은 저작권 매칭이 세서 음악이 깔리면 통째로 음소거된다
    mp4 = need_file(v["file_nobgm"], "BGM 없는 영상")
    if not mp4:
        sys.exit(1)

    # 🔴 틱톡 전용 캡션(desc_tt)이 있으면 그걸 쓴다.
    #    유튜브 설명은 길어서 앞 100자만 보이고 나머지는 접힌다 — 틱톡에선 짧게 간다
    cap = ((v.get("desc_tt") or v.get("desc", "")) + "\n\n"
           + " ".join("#" + t for t in v.get("tags", [])))[:CAP_MAX]

    log(f"대상: {v['id']} — {v.get('brand','')}", TAG)
    log(f"파일: {os.path.basename(mp4)} ({os.path.getsize(mp4)/1e6:.1f}MB)", TAG)
    log(f"캡션 {len(cap)}자", TAG)

    os.makedirs(LOGDIR, exist_ok=True)
    with sync_playwright() as pw:
        ctx = open_browser(pw, headed=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30000)

        page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        if "/login" in page.url:
            log("❌ 로그인 필요 → python login.py tt", TAG)
            close_browser(ctx)
            sys.exit(1)
        log("업로드 화면 열림", TAG)

        # 🔴 2026-07-27: 지난번에 올리다 만 게 있으면 화면 위에
        #    "편집 중인 동영상이 저장되지 않았습니다. 계속 편집할까요?" 바가 뜬다.
        #    이게 떠 있는 동안엔 업로드 위젯이 안 붙어서 파일칸도 버튼도 못 찾는다.
        #    → **취소**를 눌러 새로 시작한다(계속을 누르면 옛 영상으로 이어진다).
        for s in ['button:has-text("취소")', 'div[role="button"]:text-is("취소")']:
            try:
                b = page.locator(s).first
                if b.count() and b.is_visible():
                    b.click()
                    log("이전 편집 알림 닫음", TAG)
                    page.wait_for_timeout(3000)
                    break
            except Exception:
                continue

        # 위젯이 붙을 때까지 기다린다 — 바로 찾으면 아직 렌더 전이라 놓친다
        try:
            page.wait_for_selector('input[type="file"], button:has-text("동영상 선택")', timeout=20000)
        except Exception:
            log("업로드 위젯이 늦게 뜬다 — 그래도 계속 시도", TAG)

        # 파일 넣기
        # 🔴 2026-07-25: 메인 프레임에 input[type=file] 이 없어서 실패했다.
        #    틱톡 스튜디오는 업로드 위젯을 **iframe 안**에 넣기도 한다.
        #    ① 모든 프레임을 뒤진다 ② 그래도 없으면 '동영상 선택'을 눌러 파일선택창으로 받는다.
        target = None
        for fr in page.frames:
            try:
                loc = fr.locator(SEL["file"])
                if loc.count():
                    target = loc.first
                    log("파일칸 발견 (frame: {})".format(fr.url[:60] or "main"), TAG)
                    break
            except Exception:
                continue

        if target:
            target.set_input_files(mp4, timeout=120000)
        else:
            log("숨은 파일칸이 없다 — 버튼을 눌러 파일선택창으로 넣는다", TAG)
            btn = first_hit(page, [
                'button:has-text("동영상 선택")',
                'button:has-text("Select video")',
                'div[role="button"]:has-text("동영상 선택")',
            ])
            if not btn:
                log("❌ 파일칸도 선택 버튼도 못 찾음", TAG)
                page.screenshot(path=os.path.join(LOGDIR, "tt_nofile.png"))
                close_browser(ctx)
                sys.exit(1)
            with page.expect_file_chooser(timeout=30000) as fc:
                btn.click()
            fc.value.set_files(mp4)
        log("영상 넣음 — 처리 대기", TAG)
        page.wait_for_timeout(25000)
        page.screenshot(path=os.path.join(LOGDIR, "tt_1_loaded.png"))

        # 캡션 — 기존 문구(파일명이 자동으로 들어간다)를 지우고 새로 넣는다
        box = first_hit(page, SEL["caption"])
        if box:
            try:
                box.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
                page.wait_for_timeout(500)
                # 🔴 type() 로 한 글자씩 치면 **한글이 깨진다**(2026-07-25 실제로 당함).
                #    "차지합니다"→"테차지합니다", "비싸다"→"사비싸다" 처럼 조합 중 글자가 섞인다.
                #    입력창이 한글 IME 조합을 못 따라가서다. delay 를 늘려도 근본 해결이 안 된다.
                #    → **클립보드 붙여넣기**로 넣는다. 조합 과정이 없어서 깨질 수가 없다.
                page.evaluate("t => navigator.clipboard.writeText(t)", cap)
                page.keyboard.press("Control+V")
                page.wait_for_timeout(1500)
                # 해시태그 자동완성 팝업이 떠 있으면 Esc 로 닫는다(그대로 두면 엉뚱한 태그가 붙는다)
                page.keyboard.press("Escape")
                log("캡션 붙여넣기", TAG)
            except Exception as e:
                log(f"캡션 입력 실패 ({type(e).__name__}) — 손으로 넣을 것", TAG)
        else:
            log("⚠️ 캡션칸 못 찾음 — 손으로 넣을 것", TAG)

        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(LOGDIR, "tt_2_caption.png"))

        if not args.publish:
            log("⏸ 게시 직전에서 멈춤. 화면 확인 후 --publish", TAG)
            log("   (브라우저는 열어둔다. 직접 게시해도 된다)", TAG)
            return

        # 🔴 게시 버튼은 **화면 아래**에 있다. 스크롤하지 않으면 안 보여서 못 찾는다(2026-07-25).
        try:
            page.keyboard.press("End")
            page.wait_for_timeout(800)
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1200)
        except Exception:
            pass

        post = first_hit(page, SEL["post"])
        if not post:
            # 마지막 수단 — 화면에 보이는 버튼 중 글자가 정확히 '게시'인 것
            try:
                cand = page.get_by_role("button", name="게시", exact=True)
                if cand.count():
                    post = cand.first
            except Exception:
                pass
        if not post:
            log("❌ 게시 버튼 못 찾음 — 손으로 누를 것", TAG)
            page.screenshot(path=os.path.join(LOGDIR, "tt_nopost.png"))
            return
        log("게시 버튼 클릭", TAG)
        post.click()
        page.wait_for_timeout(20000)
        page.screenshot(path=os.path.join(LOGDIR, "tt_3_done.png"))

        # 🔴 클릭했다고 올라간 게 아니다. **올라갔는지 눈으로 확인**하고 성공을 찍는다.
        #    (예전엔 무조건 "게시 완료"를 찍어서, 엉뚱한 버튼을 눌렀는데도 성공으로 보고했다)
        ok = False
        for pat in ["게시물이 업로드", "동영상이 업로드", "관리하기", "Your video is being uploaded"]:
            try:
                if page.get_by_text(pat, exact=False).count():
                    ok = True
                    break
            except Exception:
                pass
        if not ok and "/upload" not in page.url:
            ok = True  # 업로드 화면을 벗어났으면 통과로 본다

        if ok:
            log("✅ 게시 완료", TAG)
        else:
            log("❌ 게시 확인 못 함 — log/tt_3_done.png 를 보고 손으로 마무리할 것", TAG)
            log("   (브라우저는 열어둔다)", TAG)
            return
        close_browser(ctx)


if __name__ == "__main__":
    main()
