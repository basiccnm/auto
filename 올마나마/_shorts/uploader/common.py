# -*- coding: utf-8 -*-
"""업로더 공통 부품 (2026-07-21)

왜 API가 아니라 브라우저인가:
  · 유튜브 Data API — 감사 안 받은 프로젝트가 올린 영상은 **비공개로 잠긴다.** 나중에 손으로도 못 푼다
  · 틱톡 Content Posting API — 심사 전엔 초안/비공개만
  · 네이버 클립 — **API 자체가 없다**
  네이버가 어차피 브라우저를 강제하므로, 4곳을 한 방식으로 통일한다.

로그인:
  🔴 비밀번호는 코드에 넣지 않는다. 넣을 수도 없다.
  `python login.py` 로 창을 띄우면 **대표님이 직접 로그인**하고, 그 세션이 PROFILE 폴더에 남는다.
  그 뒤로는 스크립트가 그 프로필을 그대로 열어 쓴다.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# 🔴 폴더명이 "uploader_profile"인 건 우연이 아니다.
#    gdrive_backup.ps1 의 $excludeDirs 에 이 이름이 들어 있어서 구글드라이브 백업에서 빠진다.
#    로그인 쿠키 = 계정 그 자체다. 이름 바꾸면 다음 21:00 백업에 계정이 통째로 올라간다.
PROFILE = os.path.join(HERE, "uploader_profile")
LOGDIR = os.path.join(HERE, "log")
QUEUE = os.path.join(HERE, "queue.json")

PLATFORMS = ["yt", "tt", "ig", "nv"]
PLATFORM_NAME = {"yt": "유튜브", "tt": "틱톡", "ig": "인스타", "nv": "네이버클립"}

# 사람이 쓰는 크롬처럼 보이게 — 봇 판정 줄이는 최소한의 조치
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


# ── 로그 ───────────────────────────────────────────────────────────────────
def log(msg, tag=""):
    stamp = datetime.now().strftime("%H:%M:%S")
    line = "[{}]{} {}".format(stamp, (" " + tag) if tag else "", msg)
    print(line, flush=True)
    os.makedirs(LOGDIR, exist_ok=True)
    fname = os.path.join(LOGDIR, datetime.now().strftime("%Y-%m-%d") + ".log")
    with open(fname, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


# ── 브라우저 ────────────────────────────────────────────────────────────────
CHROME_EXE = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _chrome_path():
    for p in CHROME_EXE:
        if os.path.exists(p):
            return p
    raise RuntimeError("크롬을 찾을 수 없습니다")


def _free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def open_browser(pw, headed=True, slow=0):
    """로그인 상태가 저장된 프로필로 브라우저를 연다.

    🔴 Playwright가 받아둔 크로미움은 못 쓴다(2026-07-21).
       `side-by-side configuration is incorrect`로 실행 자체가 안 됐다.
       → PC에 깔린 **진짜 크롬**을 쓴다. 봇 판정도 이쪽이 덜하다.

    🔴 launch_persistent_context()도 못 쓴다(2026-07-21).
       대표님 프로필을 복사해 넣으니 크롬이 켜지자마자 exitCode=0으로 죽었다.
       Playwright가 쓰는 `--remote-debugging-pipe`가 이 프로필에서 안 붙는다.
       → 크롬을 **우리가 직접 띄우고**(--remote-debugging-port) connect_over_cdp로 붙는다.
         포트 방식은 같은 프로필에서 정상 동작을 확인했다.

    🔴 headless 안 쓴다. 유튜브·인스타는 headless를 잘 잡아낸다.
    """
    os.makedirs(PROFILE, exist_ok=True)
    port = _free_port()
    args = [
        _chrome_path(),
        "--user-data-dir=" + PROFILE,
        "--remote-debugging-port={}".format(port),
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "--start-maximized",
        # 🔴 여기에 about:blank를 넣으면 빈 창이 하나 더 떠서 헷갈린다(2026-07-21).
        #    시작 URL은 주지 않고, 탭은 스크립트가 직접 만든다.
    ]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # CDP가 뜰 때까지 기다린다 (최대 40초)
    import urllib.request
    endpoint = "http://127.0.0.1:{}/json/version".format(port)
    for _ in range(80):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(endpoint, timeout=2).read()
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("크롬이 바로 종료됐습니다 (exit={})".format(proc.returncode))
    else:
        proc.kill()
        raise RuntimeError("크롬 CDP가 40초 안에 안 떴습니다")

    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:{}".format(port))
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    ctx.set_default_timeout(60000)
    try:
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    except Exception:
        pass

    # 나중에 정리할 수 있게 붙여둔다
    ctx._olma = {"proc": proc, "browser": browser, "port": port}
    return ctx


def close_browser(ctx):
    """붙어 있던 크롬을 확실히 내린다.

    🔴 창만 닫고 프로세스가 남아 좀비가 된 사고(2026-07-21). 프로세스까지 죽인다.
    """
    info = getattr(ctx, "_olma", None)
    try:
        if info and info.get("browser"):
            info["browser"].close()
    except Exception:
        pass
    if info and info.get("proc"):
        p = info["proc"]
        try:
            p.terminate()
            for _ in range(20):
                if p.poll() is not None:
                    break
                time.sleep(0.2)
            if p.poll() is None:
                p.kill()
        except Exception:
            pass


def new_page(ctx, url=None):
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    if url:
        page.goto(url, wait_until="domcontentloaded")
    return page


def human_pause(a=0.6, b=1.4):
    """클릭 사이에 사람 같은 틈. 규칙적인 간격이 제일 티난다."""
    import random
    time.sleep(random.uniform(a, b))


# ── 대기열 ──────────────────────────────────────────────────────────────────
def load_queue():
    if not os.path.exists(QUEUE):
        log("❌ queue.json 없음")
        sys.exit(1)
    with open(QUEUE, encoding="utf-8") as fp:
        return json.load(fp)


def save_queue(q):
    with open(QUEUE, "w", encoding="utf-8") as fp:
        json.dump(q, fp, ensure_ascii=False, indent=2)


def next_pending(q, platform):
    """그 플랫폼에 아직 안 올라간 영상 중 첫 번째."""
    for v in q["videos"]:
        if v.get("status", {}).get(platform) != "done":
            return v
    return None


def mark(q, video_id, platform, state, note=""):
    for v in q["videos"]:
        if v["id"] == video_id:
            v.setdefault("status", {})[platform] = state
            if note:
                v.setdefault("note", {})[platform] = note
            v.setdefault("uploaded_at", {})[platform] = datetime.now().isoformat(timespec="seconds")
    save_queue(q)


def resolve(path):
    """queue.json 안의 상대경로를 uploader 폴더 기준 절대경로로."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(HERE, path))


def need_file(path, label):
    p = resolve(path)
    if not os.path.exists(p):
        log("❌ {} 파일 없음: {}".format(label, p))
        return None
    return p
