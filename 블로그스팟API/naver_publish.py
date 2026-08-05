# -*- coding: utf-8 -*-
"""네이버 블로그 자동 발행 모듈 (Playwright 브라우저 자동화).

네이버 글쓰기 API가 2020년에 종료되어, 실제 브라우저(전용 프로필)로 스마트에디터를
조작해서 발행한다. 로그인은 최초 1회만 사용자가 직접 하고(비밀번호는 코드가 다루지 않음),
이후에는 naver_browser_profile/ 폴더에 세션이 유지된다.

안전 수칙 (2026-07-09 확정):
- 발행량은 하루 1~2개, 그 이상 늘리지 않음
- 실제 발행은 반드시 headed(창 보이는) 모드로 — 헤드리스 금지
- 발행 시각은 매일 고정하지 말고 일정 범위 내 무작위로 (스케줄러 붙일 때 적용)
- 자동화 계정은 1개만 (2번째 계정 동시 자동화 금지)
- 클릭/타이핑 사이 무작위 지연(_pause) 적용됨
- 본문 입력은 검증된 클립보드 붙여넣기 방식 (이미지 자동 업로드됨)
"""

import os
import re
import time
import random

from playwright.sync_api import sync_playwright


def _pause(a=0.6, b=1.8):
    """사람처럼 보이는 무작위 지연 (자동화 탐지 완화)."""
    time.sleep(random.uniform(a, b))

# 주의: 프로젝트 폴더는 경로에 한글이 있어 chromium 실행(spawn)이 실패한다.
# 프로필은 반드시 ASCII 경로에 둔다.
PROFILE_DIR = os.path.join(os.path.expanduser("~"), "naver_browser_profile")

# 로그인 세션 쿠키 백업 파일. "로그인 상태 유지"를 체크 안 하면 NID 쿠키가
# 브라우저 종료 시 사라지는 세션 쿠키라서, 로그인 성공 시 여기 저장해뒀다가
# 매 실행 때 주입한다 (체크박스 의존 제거 — 2026-07-09 세션 소실 원인).
SESSION_FILE = os.path.join(PROFILE_DIR, "naver_session.json")


def save_session(ctx, log=print):
    """현재 컨텍스트의 네이버 쿠키를 파일로 백업한다."""
    import json
    try:
        cookies = [c for c in ctx.cookies() if "naver.com" in c.get("domain", "")]
        os.makedirs(PROFILE_DIR, exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f)
    except Exception as e:
        log(f"  세션 백업 실패(무시 가능): {e}")


def restore_session(ctx):
    """백업해둔 네이버 쿠키를 컨텍스트에 주입한다."""
    import json
    if not os.path.exists(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        if cookies:
            ctx.add_cookies(cookies)
    except Exception:
        pass
WRITE_URL = "https://blog.naver.com/GoBlogWrite.naver"
SHOT_DIR = "naver_publish_logs"


def _launch(p, headless=False):
    # Playwright 내장 chromium이 이 PC에서 side-by-side 구성 오류로 실행 불가(2026-07-09)라
    # 시스템에 설치된 진짜 Chrome(channel="chrome")을 사용한다. 탐지 회피에도 더 유리함.
    ctx = p.chromium.launch_persistent_context(
        PROFILE_DIR,
        channel="chrome",
        headless=headless,
        viewport={"width": 1280, "height": 900},
        locale="ko-KR",
        args=["--disable-blink-features=AutomationControlled"],
    )
    # 본문 붙여넣기는 브라우저 내부 클립보드(JS ClipboardItem)를 쓰므로 권한을 미리 준다.
    # (OS 클립보드 의존을 없애서 headless에서도 동일하게 동작)
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://blog.naver.com")
    restore_session(ctx)  # 백업해둔 로그인 세션 쿠키 주입 (세션 쿠키 소실 대비)
    return ctx


def _set_browser_clipboard_html(frame, html):
    """페이지 컨텍스트에서 브라우저 클립보드에 text/html을 넣는다 (headless에서도 동작)."""
    frame.evaluate(
        """async (html) => {
            const blob = new Blob([html], { type: 'text/html' });
            const item = new ClipboardItem({ 'text/html': blob });
            await navigator.clipboard.write([item]);
        }""",
        html,
    )


def _editor_frame(page):
    """스마트에디터가 들어있는 프레임을 찾는다 (mainFrame iframe 안일 수도, 바로일 수도 있음)."""
    for _ in range(30):
        for frame in page.frames:
            try:
                if frame.locator(".se-title-text").count() > 0:
                    return frame
            except Exception:
                pass
        time.sleep(1)
    raise RuntimeError("스마트에디터를 찾지 못했습니다 (로그인이 풀렸거나 페이지 구조 변경)")


def _dismiss_popups(frame, log):
    """이어쓰기 팝업, 도움말 패널 등을 닫는다."""
    for selector, name in [
        (".se-popup-button-cancel", "이어쓰기 취소"),
        (".se-help-panel-close-button", "도움말 닫기"),
        ("button.se-popup-close-button", "팝업 닫기"),
    ]:
        try:
            btn = frame.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                log(f"  팝업 처리: {name}")
                time.sleep(0.5)
        except Exception:
            pass


def _has_login_cookies(ctx):
    """네이버 로그인 세션 쿠키(NID_AUT, NID_SES)가 실제로 생겼는지 확인한다."""
    try:
        names = {c["name"] for c in ctx.cookies("https://www.naver.com")}
        return "NID_AUT" in names and "NID_SES" in names
    except Exception:
        return False


def _session_alive(page):
    """글쓰기 페이지가 실제로 열리는지로 세션 유효성을 판정한다 (쿠키 존재만으론 불충분 —
    만료된 쿠키가 남아 있으면 '이미 로그인됨'으로 착각해 창이 바로 닫히는 버그가 있었음)."""
    try:
        page.goto(WRITE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        return "nid.naver.com" not in page.url
    except Exception:
        return False


def ensure_login(log=print, wait_minutes=10):
    """로그인 상태를 확인하고, 안 되어 있으면 창을 열어 사용자가 직접 로그인하게 한다.

    - 판정: 실제로 글쓰기 페이지가 열리는지 (만료 쿠키에 안 속음)
    - 세션이 죽어 있으면 만료 쿠키를 지우고 깨끗한 상태에서 로그인 대기
    - 로그인 완료 판정: 쿠키 생성 + 글쓰기 페이지 진입 확인, 그 후에만 창을 닫음
    """
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if _session_alive(page):
            ctx.close()
            log("네이버 로그인 확인 완료 (기존 세션 유효)")
            return True

        # 만료된 쿠키가 남아 있으면 판정을 방해하므로 싹 지우고 시작
        try:
            ctx.clear_cookies()
        except Exception:
            pass
        page.goto(WRITE_URL, wait_until="domcontentloaded")
        time.sleep(2)

        log("네이버 로그인이 필요합니다. 열린 브라우저 창에서 직접 로그인해주세요...")
        log(f"({wait_minutes}분 안에 로그인하면 됩니다. '로그인 상태 유지'를 꼭 체크해주세요)")
        deadline = time.time() + wait_minutes * 60
        while time.time() < deadline:
            if _has_login_cookies(ctx):
                break
            time.sleep(3)
        else:
            ctx.close()
            raise RuntimeError("로그인 대기 시간 초과")

        log("로그인 쿠키 확인됨. 글쓰기 페이지 진입 검증 중...")
        time.sleep(3)
        ok = _session_alive(page)
        if ok:
            save_session(ctx, log)  # 세션 쿠키 백업 (로그인 상태 유지 미체크 대비)
        time.sleep(2)  # 쿠키 디스크 반영 여유
        ctx.close()
        if ok:
            log("네이버 로그인 확인 완료 (세션이 naver_browser_profile에 저장됨)")
        else:
            log("경고: 쿠키는 생겼지만 글쓰기 페이지 진입 실패 — 다시 시도해주세요")
        return ok


def _set_schedule(frame, page, schedule_dt, log):
    """발행 패널에서 '예약'을 선택하고 날짜/시각을 설정한다 (네이버 자체 예약발행 기능).

    실측 DOM (2026-07-09): 날짜=input.input_date__xxx(readonly, 클릭 시 jQuery UI 달력),
    시=select.hour_option__xxx(00~23), 분=select.minute_option__xxx(10분 단위)
    """
    frame.locator('label:has-text("예약")').first.click()
    _pause()
    page.screenshot(path=os.path.join(SHOT_DIR, "3a_schedule_panel.png"))

    # 날짜: 오늘이 아니면 달력에서 해당 일자 클릭
    today = time.localtime()
    if (schedule_dt.year, schedule_dt.month, schedule_dt.day) != (today.tm_year, today.tm_mon, today.tm_mday):
        frame.locator('input[class*="input_date"]').first.click()
        _pause()
        # 달력에서 다음달 이동이 필요한 경우 (제목이 "7월" 형식)
        for _ in range(3):
            month_text = frame.locator('.ui-datepicker-month').first.inner_text(timeout=5000).strip()
            if month_text == f"{schedule_dt.month}월":
                break
            frame.locator('button.ui-datepicker-next').first.click()
            _pause(0.5, 1.0)
        # 지난 날짜는 td.ui-state-disabled — 선택 가능한 날만, 일자는 정확히 일치(:text-is)
        frame.locator(
            f'.ui-datepicker td:not(.ui-state-disabled) button:text-is("{schedule_dt.day}")'
        ).first.click()
        _pause()

    # 시/분 셀렉트 (분은 10분 단위 내림)
    frame.locator('select[class*="hour_option"]').first.select_option(f"{schedule_dt.hour:02d}")
    _pause(0.3, 0.7)
    minute = (schedule_dt.minute // 10) * 10
    frame.locator('select[class*="minute_option"]').first.select_option(f"{minute:02d}")
    _pause()
    log(f"  예약 설정: {schedule_dt.strftime('%Y-%m-%d %H:%M')} (분은 10분 단위 내림)")


def publish_to_naver(title, html_fragment, tags=None, visibility="private", log=print,
                     headless=False, schedule_dt=None, _page=None):
    """네이버 블로그에 글을 발행한다.

    visibility: "private"(비공개) 또는 "public"(전체공개)
    schedule_dt: datetime — 지정하면 네이버 자체 예약발행으로 등록 (visibility는 무시되고 전체공개 예약)
    _page: 배치 등록용 — 이미 열린 페이지를 재사용 (한 세션에 여러 글)
    반환: 발행된 글 URL (예약 등록이면 None일 수 있음)
    """
    if _page is not None:
        return _publish_on_page(_page, title, html_fragment, tags, visibility, schedule_dt, log)

    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            result = _publish_on_page(page, title, html_fragment, tags, visibility, schedule_dt, log)
            save_session(ctx, log)  # 갱신된 세션 쿠키 재백업
            return result
        finally:
            ctx.close()


def edit_naver_post(naver_url, title, html_fragment, log=print):
    """이미 네이버에 등록된 글을 수정한다 (저장 리스트의 최신본으로 통째 교체 후 재발행).

    naver_url: 등록 시 저장된 글 URL (예: https://blog.naver.com/hardbar/223xxx)
    주의: 태그는 그대로 유지된다 (기존 태그 삭제 자동화는 오탐 위험이 있어 제외).
    가끔 특정 글 하나 고치는 용도 — 대량 수정은 접속 패턴이 늘어나므로 자제.
    """
    m = re.search(r"blog\.naver\.com/([^/]+)/(\d+)", naver_url or "")
    if not m:
        raise RuntimeError(f"글 URL에서 blogId/logNo를 찾지 못함: {naver_url}")
    blog_id, log_no = m.group(1), m.group(2)
    edit_url = f"https://blog.naver.com/PostUpdateForm.naver?blogId={blog_id}&logNo={log_no}"

    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            log("수정 에디터 여는 중...")
            page.goto(edit_url, wait_until="domcontentloaded")
            time.sleep(5)
            if "nid.naver.com" in page.url:
                raise RuntimeError("로그인이 필요합니다. 먼저 네이버 로그인을 해주세요.")
            frame = _editor_frame(page)
            _dismiss_popups(frame, log)
            _pause()

            # 제목 교체
            log("제목 교체 중...")
            frame.locator(".se-title-text").first.click()
            _pause()
            page.keyboard.press("Control+A")
            _pause(0.2, 0.5)
            page.keyboard.press("Delete")
            _pause()
            for ch in title:
                page.keyboard.type(ch, delay=random.uniform(40, 140))
            _pause()

            # 본문 교체
            log("본문 교체 중...")
            _set_browser_clipboard_html(frame, html_fragment)
            frame.locator(".se-component.se-text .se-text-paragraph").first.click()
            _pause()
            page.keyboard.press("Control+A")
            _pause(0.2, 0.5)
            page.keyboard.press("Delete")
            _pause()
            page.keyboard.press("Control+V")
            log("  이미지 업로드 대기 중 (10초)...")
            time.sleep(10)
            page.screenshot(path=os.path.join(SHOT_DIR, "edit_1_after_paste.png"))
            _pause(1.5, 3.0)

            # 발행 (수정 반영) — 공개 설정/예약은 기존 값 유지
            log("수정 발행 중...")
            frame.locator('button[class*="publish_btn"]').first.click()
            _pause(1.5, 3.0)
            page.screenshot(path=os.path.join(SHOT_DIR, "edit_2_panel.png"))
            frame.locator('button:visible', has_text="발행").last.click()

            for _ in range(30):
                time.sleep(1)
                if "PostUpdateForm" not in page.url and "Write" not in page.url:
                    break
            time.sleep(2)
            page.screenshot(path=os.path.join(SHOT_DIR, "edit_3_done.png"))
            log(f"수정 반영 완료: {page.url}")
            return page.url
        except Exception as e:
            try:
                page.screenshot(path=os.path.join(SHOT_DIR, "edit_error.png"))
            except Exception:
                pass
            log(f"수정 실패: {e}")
            raise
        finally:
            ctx.close()


def edit_scheduled_post(title_match, new_title, html_fragment, schedule_dt, log=print):
    """아직 공개 전인 '예약 발행' 글을 수정한다.

    흐름: 글쓰기 화면 → 상단 "예약 발행 N건" → 목록에서 제목으로 글 찾기 → 클릭해 에디터로
    불러오기 → 제목/본문 교체 → 예약 시각을 다시 설정해서 재등록 (실측 DOM 2026-07-09:
    목록 팝업 button.article_button__xxx, 삭제 button.delete_button__xxx)

    schedule_dt: 유지할 예약 시각 (에디터로 불러올 때 예약 설정이 풀릴 수 있어 항상 재설정)
    """
    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            log("에디터 여는 중...")
            page.goto(WRITE_URL, wait_until="domcontentloaded")
            time.sleep(4)
            if "nid.naver.com" in page.url:
                raise RuntimeError("로그인이 필요합니다. 먼저 네이버 로그인을 해주세요.")
            frame = _editor_frame(page)
            _dismiss_popups(frame, log)
            _pause()

            log("예약 발행 목록 여는 중...")
            frame.locator('button[class*="reserve_btn"]').first.click()
            _pause(1.5, 2.5)
            page.screenshot(path=os.path.join(SHOT_DIR, "sched_1_list.png"))

            # 제목 앞부분으로 대상 글 찾기 (따옴표 등 특수문자 회피를 위해 15자만)
            needle = title_match[:15]
            item = frame.locator(f'button[class*="article_button"]', has_text=needle).first
            if item.count() == 0:
                raise RuntimeError(f"예약 목록에서 글을 찾지 못함: {needle}")
            item.click()
            log("  예약 글을 에디터로 불러오는 중...")
            time.sleep(4)
            _dismiss_popups(frame, log)
            page.screenshot(path=os.path.join(SHOT_DIR, "sched_2_loaded.png"))

            # 제목 교체
            log("제목 교체 중...")
            frame.locator(".se-title-text").first.click()
            _pause()
            page.keyboard.press("Control+A")
            _pause(0.2, 0.5)
            page.keyboard.press("Delete")
            _pause()
            for ch in new_title:
                page.keyboard.type(ch, delay=random.uniform(40, 140))
            _pause()

            # 본문 교체
            log("본문 교체 중...")
            _set_browser_clipboard_html(frame, html_fragment)
            frame.locator(".se-component.se-text .se-text-paragraph").first.click()
            _pause()
            page.keyboard.press("Control+A")
            _pause(0.2, 0.5)
            page.keyboard.press("Delete")
            _pause()
            page.keyboard.press("Control+V")
            log("  이미지 업로드 대기 중 (10초)...")
            time.sleep(10)
            page.screenshot(path=os.path.join(SHOT_DIR, "sched_3_replaced.png"))
            _pause(1.5, 3.0)

            # 발행 패널 → 예약 시각 재설정 (불러오기 과정에서 풀릴 수 있으므로 항상 재적용)
            log("발행 패널 여는 중...")
            frame.locator('button[class*="publish_btn"]').first.click()
            _pause(1.5, 3.0)
            _set_schedule(frame, page, schedule_dt, log)
            page.screenshot(path=os.path.join(SHOT_DIR, "sched_4_panel.png"))

            log("예약 재등록 중...")
            frame.locator('button:visible', has_text="발행").last.click()
            for _ in range(30):
                time.sleep(1)
                if "Redirect=Write" not in page.url and "GoBlogWrite" not in page.url:
                    break
            time.sleep(2)
            page.screenshot(path=os.path.join(SHOT_DIR, "sched_5_done.png"))
            save_session(ctx, log)
            log(f"예약 글 수정 완료 ({schedule_dt.strftime('%m/%d %H:%M')} 공개 예정 유지)")
            return True
        except Exception as e:
            try:
                page.screenshot(path=os.path.join(SHOT_DIR, "sched_error.png"))
            except Exception:
                pass
            log(f"예약 글 수정 실패: {e}")
            raise
        finally:
            ctx.close()


def cancel_scheduled_post(title_match, log=print):
    """네이버 '예약 발행' 목록에서 해당 글의 예약을 취소(삭제)한다.

    실측 DOM: 목록 항목 li 안에 button.delete_button__xxx (title="삭제")
    """
    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        # 네이티브 confirm 대화상자가 뜨면 수락
        page.on("dialog", lambda d: d.accept())
        try:
            log("에디터 여는 중...")
            page.goto(WRITE_URL, wait_until="domcontentloaded")
            time.sleep(4)
            if "nid.naver.com" in page.url:
                raise RuntimeError("로그인이 필요합니다. 먼저 네이버 로그인을 해주세요.")
            frame = _editor_frame(page)
            _dismiss_popups(frame, log)
            _pause()

            log("예약 발행 목록 여는 중...")
            frame.locator('button[class*="reserve_btn"]').first.click()
            _pause(1.5, 2.5)

            needle = title_match[:15]
            item = frame.locator('li', has=frame.locator(f'button[class*="article_button"]', has_text=needle)).first
            if item.count() == 0:
                raise RuntimeError(f"예약 목록에서 글을 찾지 못함: {needle}")
            # 삭제 버튼은 항목에 마우스를 올려야만 보이는(hover) 버튼 — 호버 후 클릭, 실패 시 JS 클릭
            item.hover()
            _pause(0.5, 1.0)
            del_btn = item.locator('button[class*="delete_button"]').first
            try:
                del_btn.click(timeout=5000)
            except Exception:
                del_btn.evaluate("el => el.click()")
            log("  삭제 버튼 클릭, 확인 대기...")
            _pause(1.0, 2.0)
            # 커스텀 확인 레이어가 뜨는 경우 처리
            for text in ("삭제", "확인"):
                try:
                    btn = frame.locator(f'[class*="popup"] button:visible:has-text("{text}"), '
                                        f'[class*="layer"] button:visible:has-text("{text}")').last
                    if btn.count() > 0:
                        btn.click()
                        _pause()
                        break
                except Exception:
                    pass
            time.sleep(2)
            page.screenshot(path=os.path.join(SHOT_DIR, "cancel_done.png"))
            # 검증: 목록에서 사라졌는지
            gone = frame.locator(f'button[class*="article_button"]', has_text=needle).count() == 0
            save_session(ctx, log)
            if gone:
                log("예약 취소 완료 (목록에서 제거 확인)")
            else:
                log("경고: 삭제 후에도 목록에 남아 있음 — cancel_done.png 확인 필요")
            return gone
        except Exception as e:
            try:
                page.screenshot(path=os.path.join(SHOT_DIR, "cancel_error.png"))
            except Exception:
                pass
            log(f"예약 취소 실패: {e}")
            raise
        finally:
            ctx.close()


def batch_register_scheduled(entries, log=print):
    """여러 글을 한 브라우저 세션으로 네이버 예약발행 등록한다 (하루 1개씩 분산, 최대 10개).

    entries: [(title, html_fragment, tags, schedule_dt, callback), ...]
      callback(성공여부, url) — 각 글 등록 후 호출 (대기열 상태 갱신용)
    """
    import random as _r
    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for i, (title, html_fragment, tags, schedule_dt, callback) in enumerate(entries):
                if i > 0:
                    wait = _r.uniform(25, 70)
                    log(f"  다음 글까지 {wait:.0f}초 대기 (자연스러운 간격)...")
                    time.sleep(wait)
                try:
                    url = _publish_on_page(page, title, html_fragment, tags,
                                           "public", schedule_dt, log)
                    callback(True, url)
                except Exception as e:
                    log(f"  등록 실패: {title} / {e}")
                    callback(False, None)
            save_session(ctx, log)  # 갱신된 세션 쿠키 재백업
        finally:
            ctx.close()


def _publish_on_page(page, title, html_fragment, tags, visibility, schedule_dt, log):
    tags = tags or []
    if True:  # 기존 들여쓰기 유지용
        try:
            log("에디터 여는 중...")
            page.goto(WRITE_URL, wait_until="domcontentloaded")
            time.sleep(4)
            if "nid.naver.com" in page.url:
                raise RuntimeError("로그인이 필요합니다. 먼저 ensure_login()을 실행하세요.")

            frame = _editor_frame(page)
            _dismiss_popups(frame, log)
            _pause()

            # 1) 제목 입력 (사람처럼 무작위 속도로 타이핑)
            log("제목 입력 중...")
            frame.locator(".se-title-text").first.click()
            _pause()
            for ch in title:
                page.keyboard.type(ch, delay=random.uniform(40, 140))
            _pause()

            # 2) 본문: 브라우저 클립보드에 HTML을 넣고 붙여넣기 (이미지 자동 업로드)
            # 자동저장 초안이 복원돼 있을 수 있으므로 붙여넣기 전에 본문을 전체선택-삭제한다 (중복 방지)
            log("본문 붙여넣는 중...")
            _set_browser_clipboard_html(frame, html_fragment)
            body = frame.locator(".se-component.se-text .se-text-paragraph").first
            body.click()
            _pause()
            page.keyboard.press("Control+A")
            _pause(0.2, 0.5)
            page.keyboard.press("Delete")
            _pause()
            page.keyboard.press("Control+V")
            log("  이미지 업로드 대기 중 (10초)...")
            time.sleep(10)  # 외부 이미지의 네이버 서버 업로드 대기

            page.screenshot(path=os.path.join(SHOT_DIR, "1_after_paste.png"))
            _pause(1.5, 3.5)

            # 3) 발행 버튼 (에디터 상단 우측 초록 버튼)
            # 주의: 'button:has-text("발행")'은 숨겨진 "예약 발행"(reserve_btn)을 먼저 잡으므로
            # publish_btn 클래스로 특정한다 (네이버는 클래스명 뒤에 해시가 붙음: publish_btn__xxxx)
            log("발행 패널 여는 중...")
            frame.locator('button[class*="publish_btn"]').first.click()
            _pause(1.5, 3.0)
            page.screenshot(path=os.path.join(SHOT_DIR, "2_publish_panel.png"))

            # 4) 공개 설정 (예약발행이면 전체공개가 기본 — 예약 시점에 공개됨)
            if schedule_dt is None and visibility == "private":
                try:
                    frame.locator('label:has-text("비공개")').first.click()
                    log("  공개설정: 비공개")
                    _pause()
                except Exception:
                    log("  경고: 비공개 설정 실패 — 기본값으로 발행됨")

            # 4-1) 예약발행 설정 (네이버 자체 기능)
            if schedule_dt is not None:
                _set_schedule(frame, page, schedule_dt, log)

            # 5) 태그 입력 (사람처럼 무작위 속도)
            if tags:
                try:
                    tag_input = frame.locator('input[class*="tag_input"], input[placeholder*="태그"]').first
                    tag_input.click()
                    for tag in tags:
                        page.keyboard.type(tag.replace(" ", ""), delay=random.uniform(40, 120))
                        page.keyboard.press("Enter")
                        _pause(0.3, 0.9)
                    log(f"  태그 {len(tags)}개 입력")
                except Exception as e:
                    log(f"  경고: 태그 입력 실패 ({e}) — 태그 없이 발행")

            page.screenshot(path=os.path.join(SHOT_DIR, "3_before_confirm.png"))

            # 6) 최종 발행 확인 버튼 — 패널이 열린 뒤 화면에 보이는 "발행" 버튼 중
            # 마지막 것(DOM상 패널 내부의 [✓ 발행])을 클릭한다.
            log("최종 발행 중...")
            confirm = frame.locator('button:visible', has_text="발행").last
            confirm.click()

            # 7) 발행 완료 확인 — 에디터를 벗어나면(글 페이지/블로그홈) 성공으로 본다
            for _ in range(30):
                time.sleep(1)
                cur = page.url
                if "PostWriteForm" not in cur and "Redirect=Write" not in cur and "GoBlogWrite" not in cur:
                    break
            time.sleep(2)
            final_url = page.url
            page.screenshot(path=os.path.join(SHOT_DIR, "4_published.png"))
            if schedule_dt is not None:
                log(f"예약 등록 완료 ({schedule_dt.strftime('%m/%d %H:%M')} 공개 예정)")
            else:
                log(f"발행 완료: {final_url}")
            return final_url

        except Exception as e:
            try:
                page.screenshot(path=os.path.join(SHOT_DIR, "error.png"))
                log(f"오류 발생 (스크린샷: {SHOT_DIR}/error.png): {e}")
            except Exception:
                log(f"오류 발생: {e}")
            raise
