# -*- coding: utf-8 -*-
"""쿠팡이츠 앱 화면을 **원본 그대로** 받아 적는다 (uiautomator). 2026-07-31

    python scripts/brand_coupangeats.py <slug> [<device>]

    → data/brand_menu_list/_ce_raw/<slug>.tsv     화면에 그려진 글자 전부(원본)
    그 다음:  python scripts/brand_coupangeats_parse.py <slug>
    →         data/brand_menu_list/<slug>_delivery.json

🔴 왜 쿠팡이츠인가 (2026-07-31 확인)
   홈페이지엔 가격이 없다(파바·뚜레·던킨). 배민 앱은 **가격이 uiautomator 에 안 잡히고**
   API 는 403. 쿠팡이츠 앱만 화면 글자가 그대로 잡힌다 — 유일하게 뚫린 길이다.
   ※ OCR 아니다. 화면에 그려진 **텍스트 노드**를 읽는다(정확·무료·차단 없음).

🔴 왜 «원본 저장 → 나중에 가공» 인가 (2026-07-31 대표 지시)
   전엔 스크롤하면서 «가격 줄 + 바로 위 줄» 규칙을 그 자리에서 적용해 이름·가격만 남겼다.
   그러면 **규칙이 틀린 걸 나중에 알면 8분을 다시 긁어야 한다.** 실제로 카테고리 제목이
   메뉴로 섞였는데 원본이 없어 확인도 못 했다. 원본을 남기면 파싱은 몇 번이든 다시 한다.
   XML 통째로는 수백 MB 라서 **텍스트 노드만** (화면번호·y·x·글자) 로 적는다.

🔴 스크롤은 «작게, 겹치게» (2026-07-31 — 228개 중 80개만 받은 사고)
   폭이 크면 화면이 통째로 건너뛴다. 원본을 저장해도 **한 번도 안 그려진 화면은 XML 에 없다.**
   그래서 ① 폭을 화면 절반 이하로 두고 ② **겹침을 검사**한다 — 직전 화면의 마지막 줄이
   새 화면에 안 보이면 너무 뛴 것이라 되돌려 다시 읽는다.

🔴 받는 즉시 append 한다. 마지막에 한 번만 저장하면 중간에 끊길 때 전부 날아간다(실제 사고).
⛔ 뒤로가기(keyevent 4) 넣지 마라 — 두 번 눌려 검색 화면까지 나갔다. 사람이 가게를 열어둔다.
"""
import io
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "brand_menu_list", "_ce_raw")
ADB = r"D:\Android\Sdk\platform-tools\adb.exe"

RX_NODE = re.compile(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
# 목록의 끝 — 마지막 메뉴 다음에 「비슷한 … 맛집」 + 「광고」 가 나오고 그 아래는 남의 가게다.
# 🔴 「추천해요」 단독은 쓰지 마라 — 메뉴·리뷰의 「추천」 에 걸려 첫 화면에서 끝나버린다
#    (2026-07-31 포케올데이가 46줄로 조기종료). 「비슷한 맛집」·「광고」 로 좁힌다.
END_MARK = re.compile(r"^광고$|비슷한.{0,12}맛집|맛집.{0,6}추천")

STEP_MAX = 600          # 넉넉히. 끝은 광고로 판정한다
SWIPE = ("450", "1200", "450", "820")   # 화면 1/3 — 촘촘히 겹치게 내린다
#  🔴 2026-07-31 맥도날드에서 34화면 만에 끝나 세트·버거 구간을 얇게 훑었다.
#     폭을 더 줄였다 — 느려지지만 빠지는 것보다 낫다(대표: *"천천히 다 읽어라"*).
DUR = "400"
WAIT = 0.6


def sh(dev, *a, t=40):
    return subprocess.run([ADB, "-s", dev, *a], capture_output=True, timeout=t
                          ).stdout.decode("utf-8", "replace")


def nodes(dev):
    """화면에 그려진 글자를 (y, x, 글자) 로 전부 돌려준다. 거르지 않는다 — 가공은 나중에.

    🔴 `exec-out … /dev/tty` 로 **한 번에** 받는다. 예전처럼 폰에 XML 을 쓰고 다시 `cat` 하면
       화면 한 장에 adb 왕복이 2번이라 느리다(대표 지적 2026-07-31). 실패하면 옛 방식으로 돈다.
    """
    xml = subprocess.run([ADB, "-s", dev, "exec-out", "uiautomator", "dump", "/dev/tty"],
                         capture_output=True, timeout=40).stdout.decode("utf-8", "replace")
    if "bounds=" not in xml:
        sh(dev, "shell", "uiautomator", "dump", "/sdcard/ce.xml")
        xml = sh(dev, "shell", "cat", "/sdcard/ce.xml")
    out = []
    for t, x1, y1, x2, y2 in RX_NODE.findall(xml):
        t = t.replace("&#10;", " ").replace("&amp;", "&").strip()
        if t:
            out.append((int(y1), int(x1), t))
    return sorted(out)


def append(fp, step, rows):
    """화면 하나를 그대로 덧붙인다. **매 화면 flush** — 끊겨도 여기까지는 남는다."""
    with io.open(fp, "a", encoding="utf-8") as f:
        for y, x, t in rows:
            f.write("%d\t%d\t%d\t%s\n" % (step, y, x, t.replace("\t", " ")))
        f.flush()
        os.fsync(f.fileno())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("사용법: python scripts/brand_coupangeats.py <slug> [device]")
    slug = args[0]
    dev = args[1] if len(args) > 1 else "emulator-5554"

    os.makedirs(RAW, exist_ok=True)
    fp = os.path.join(RAW, "%s.tsv" % slug)
    if os.path.exists(fp):                       # 옛 원본을 덮지 않는다 — 옆에 쌓는다
        os.replace(fp, fp + ".bak")
    io.open(fp, "w", encoding="utf-8").close()

    rows = nodes(dev)
    print("화면 글자 %d줄 · slug=%s → %s" % (len(rows), slug, fp), flush=True)
    append(fp, 0, rows)

    n_line, back = len(rows), 0
    for step in range(1, STEP_MAX):
        if any(END_MARK.search(t) for _, _, t in rows):
            print("   광고 구간 도달 - 끝", flush=True)
            break
        sh(dev, "shell", "input", "swipe", *SWIPE, DUR)
        time.sleep(WAIT)
        new = nodes(dev)
        if not new:
            print("   빈 화면 - 한 번 더 기다린다", flush=True)
            time.sleep(1.2)
            new = nodes(dev)

        # 🔴 겹침 검사 — 직전 화면 아래쪽 글자가 새 화면에 하나도 없으면 **건너뛴 것**이다.
        #    반쯤 되돌려 그 사이를 다시 읽는다. (2026-07-31 65% 유실 사고의 재발 방지)
        prev_tail = {t for _, _, t in rows[len(rows) // 2:]}
        cur = {t for _, _, t in new}
        if prev_tail and not (prev_tail & cur) and back < 3:
            back += 1
            print("   ↩ 건너뛴 듯 — 되돌려 다시 읽는다 (%d회)" % back, flush=True)
            sh(dev, "shell", "input", "swipe", "450", "700", "450", "1100", "500")
            time.sleep(WAIT)
            new = nodes(dev)
        else:
            back = 0

        rows = new
        append(fp, step, rows)
        n_line += len(rows)
        if step % 10 == 0:
            print("   화면 %d · 누적 %d줄" % (step, n_line), flush=True)

    print("✅ 원본 %d줄 -> %s" % (n_line, fp))
    print("   다음:  python scripts/brand_coupangeats_parse.py %s" % slug)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
