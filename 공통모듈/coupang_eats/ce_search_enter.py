# -*- coding: utf-8 -*-
"""쿠팡이츠 앱에서 **브랜드를 검색해 가게에 진입**한다 (에뮬/폰). 2026-08-01

    python ce_search_enter.py <device> "<검색어>" "<진입할 가게 부분일치>"
    예)  python ce_search_enter.py emulator-5554 "한신포차" "한신포차"

이 스크립트가 하는 일 (수집 전 단계)
    ① 지금 가게 상세에 있으면 **뒤로 나가** 검색 화면으로 (음식배달 탭이 보일 때까지)
    ② 상단 검색창을 눌러 기존 글자를 지우고 검색어 입력 → 엔터
    ③ 검색 결과 목록에서 **가게명이 부분일치하는 항목**을 눌러 진입
    ④ 진입하면 맨 위로 올린다 (수집 시작점)

🔴 왜 필요한가 (2026-07-31 사고)
   검색 결과 **목록**에서 그대로 수집하면 「광고」에 걸려 30~80줄로 끝난다.
   반드시 항목을 눌러 **가게 상세**로 들어간 뒤 수집해야 한다.
   진입 성공은 화면에 「매장∙원산지정보」가 있는지로 확인한다.

🔴 한글 입력은 **ADBKeyboard** 가 있어야 한다 (에뮬 기본 IME 는 중국어뿐).
   설치:  adb install ADBKeyboard.apk
   활성:  adb shell ime enable  com.android.adbkeyboard/.AdbIME
          adb shell ime set     com.android.adbkeyboard/.AdbIME
   입력:  adb shell am broadcast -a ADB_INPUT_TEXT --es msg '한글'

⚠️ 두 기기를 **동시에** 조작하지 마라 — adb 명령이 충돌해 swipe 가 씹힌다.
   검색·진입은 순차로, 수집(brand_coupangeats.py)도 한 번에 하나씩.
"""
import re
import subprocess
import sys
import time

ADB = r"D:\Android\Sdk\platform-tools\adb.exe"


def sh(dev, *a, t=40):
    return subprocess.run([ADB, "-s", dev, *a], capture_output=True, timeout=t
                          ).stdout.decode("utf-8", "replace")


def dump(dev):
    """화면 노드 → (y, x, y2, text). 세로 중앙 좌표로 탭하기 위해 y2 도 준다."""
    x = subprocess.run([ADB, "-s", dev, "exec-out", "uiautomator", "dump", "/dev/tty"],
                       capture_output=True, timeout=40).stdout.decode("utf-8", "replace")
    return [(int(b), int(a), int(d), t) for t, a, b, c, d in re.findall(
        r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x) if t.strip()]


def key(dev, name):
    return name in "".join(t for _, _, _, t in dump(dev))


def to_search(dev):
    """가게 상세면 뒤로 나가 검색 화면으로. 「음식배달」 탭이 보이면 검색 목록이다."""
    for _ in range(3):
        if any("음식배달" in t for _, _, _, t in dump(dev)):
            return
        sh(dev, "shell", "input", "keyevent", "4")
        time.sleep(1.5)


def enter_brand(dev, keyword, want):
    to_search(dev)
    sh(dev, "shell", "input", "tap", "300", "60")          # 상단 검색창
    time.sleep(1)
    for _ in range(25):
        sh(dev, "shell", "input", "keyevent", "67")        # 기존 글자 지우기
    time.sleep(0.4)
    sh(dev, "shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", keyword)
    time.sleep(1)
    sh(dev, "shell", "input", "keyevent", "66")            # 엔터
    time.sleep(3)
    # 검색 결과에서 want 포함 항목 탭
    for _ in range(6):
        hit = [(y, x, y2, t) for y, x, y2, t in dump(dev)
               if want in t and y > 150 and ("점" in t or "지점" in t)]
        if hit:
            y, x, y2, t = hit[0]
            print("진입:", t[:32], flush=True)
            sh(dev, "shell", "input", "tap", "300", str((y + y2) // 2))
            break
        sh(dev, "shell", "input", "swipe", "450", "1000", "450", "600", "300")
        time.sleep(1)
    else:
        print("검색 결과에 없음 — 지역(주소)이 다르거나 배달 미운영")
        return False
    time.sleep(3.5)
    ok = any("원산지" in t for _, _, _, t in dump(dev))
    if not ok:
        print("진입 실패 — 화면 확인 필요")
        return False
    for _ in range(15):                                    # 맨 위로 (수집 시작점)
        sh(dev, "shell", "input", "swipe", "450", "450", "450", "1250", "250")
        time.sleep(0.12)
    print("진입·상단 정렬 완료 → 이제 brand_coupangeats.py 로 수집")
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 4:
        raise SystemExit('사용법: python ce_search_enter.py <device> "<검색어>" "<가게 부분일치>"')
    ok = enter_brand(sys.argv[1], sys.argv[2], sys.argv[3])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
