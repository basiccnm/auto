# -*- coding: utf-8 -*-
"""배민(LDPlayer 에뮬)에서 브랜드 메뉴·가격·중량을 긁는다. 2026-07-26

왜 배민인가 — 브랜드 홈페이지에는 **중량이 없다**(큰맘할매순대국 확인).
우리 DB의 그램수는 전부 추정값이고, 그걸 실제 값으로 바꿀 수 있는 곳이 배민이다.
공급방식(완제품/반제품)은 배민에 안 나온다 — 그건 홈페이지·웹서치 몫.

🔴 좌표를 눈으로 찍지 않는다
   스크린샷 보고 tap 하는 방식은 느리고, 화면이 조금 움직이면 엉뚱한 걸 누른다
   (2026-07-26: 붙여넣기 메뉴가 y=182→166 으로 움직여 빈 검색이 됐다).
   대신 `uiautomator dump` 로 **노드의 bounds** 를 읽어 그 중심을 누른다.

🔴 한글 입력은 adb 로 못 한다
   `adb shell input text` 는 ASCII 만 된다. 그래서 **윈도 클립보드 → 롱프레스 → 붙여넣기** 를 쓴다.
   LDPlayer 가 클립보드를 동기화해 준다. **Set-Clipboard 후 3초는 기다려야** 옛 값이 안 붙는다.

⛔ 주문·결제는 절대 누르지 않는다. 읽기만 한다.

    python scripts/baemin_scrape.py --brand 큰맘할매순대국
    python scripts/baemin_scrape.py --dump          # 지금 화면 구조만 보기
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "baemin")
ADB = r"C:\LDPlayer\LDPlayer14\adb.exe"
PKG = "com.sampleapp"
TMP = os.path.join(os.environ.get("TEMP", "."), "bm_ui.xml")


def sh(*args, timeout=40):
    r = subprocess.run([ADB] + list(args), capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def dump():
    """현재 화면의 노드 목록. [{text, desc, cls, cx, cy, w, h}]"""
    for _ in range(3):
        sh("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        sh("pull", "/sdcard/ui.xml", TMP)
        try:
            root = ET.parse(TMP).getroot()
            break
        except Exception:
            time.sleep(1)
    else:
        return []
    out = []
    for n in root.iter("node"):
        b = n.get("bounds") or ""
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({"text": (n.get("text") or "").strip(),
                    "desc": (n.get("content-desc") or "").strip(),
                    "cls": (n.get("class") or "").split(".")[-1],
                    "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2,
                    "w": x2 - x1, "h": y2 - y1, "y": y1})
    return out


def find(nodes, text=None, cls=None, contains=True):
    for n in nodes:
        blob = n["text"] + " " + n["desc"]
        if text is not None:
            if contains:
                if text not in blob:
                    continue
            elif blob.strip() != text:
                continue
        if cls and n["cls"] != cls:
            continue
        return n
    return None


def tap(n, wait=2.0):
    sh("shell", "input", "tap", str(n["cx"]), str(n["cy"]))
    time.sleep(wait)


def set_clip(s):
    """윈도 클립보드에 넣고 동기화를 기다린다."""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Set-Clipboard -Value @'\n%s\n'@" % s], capture_output=True)
    time.sleep(3)


def type_korean(field, s):
    """롱프레스 → 붙여넣기. 커서가 들어가야 메뉴가 뜨므로 **먼저 한 번 탭**한다."""
    set_clip(s)
    sh("shell", "input", "tap", str(field["cx"]), str(field["cy"]))
    time.sleep(1.5)
    for dur in ("900", "1400"):
        sh("shell", "input", "touchscreen", "swipe",
           str(field["cx"]), str(field["cy"]), str(field["cx"]), str(field["cy"]), dur)
        time.sleep(2)
        p = find(dump(), text="붙여넣기") or find(dump(), text="Paste")
        if p:
            tap(p, 2)
            return True
    return False


def screen():
    m = re.search(r"(\d+)x(\d+)", sh("shell", "wm", "size"))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (900, 1600)
    return (min(w, h), max(w, h))          # 세로 기준


def search_box(nodes):
    """검색창을 찾는다.
    🔴 힌트 텍스트로 찾으면 안 된다(2026-07-26): 홈 검색창의 힌트가 "배민클럽은 배달팁 0원에…" 라서
       `text="배민클럽"` 으로 잡으면 아래 **배민클럽 배너**를 눌러 라운지로 넘어간다.
    ✅ 배민은 접근성 라벨을 준다 — content-desc 에 **"검색 버튼"** 이 있다. 그게 가장 확실하다."""
    e = find(nodes, cls="EditText")
    if e:
        return e
    for n in nodes:
        if "검색 버튼" in n["desc"] or "검색버튼" in n["desc"]:
            return n
    w, h = screen()
    cand = [n for n in nodes if n["y"] < h * 0.13 and n["w"] > w * 0.55 and n["h"] < h * 0.09]
    return sorted(cand, key=lambda n: n["y"])[0] if cand else None


# 팝업 닫기 — ⛔ '확인'·'동의'·'허용' 은 절대 누르지 않는다(약관 동의가 될 수 있다).
# ⛔ '취소' 도 넣지 않는다(2026-07-26): 앱 자체 대화상자의 취소가 종료로 이어져 앱이 팅겼다.
CLOSE_WORDS = ("닫기", "오늘 하루 보지 않기", "다시 보지 않기", "나중에")


def close_popups(max_try=3):
    """뜬 팝업을 닫는다. 닫은 개수를 준다."""
    n = 0
    for _ in range(max_try):
        nd = dump()
        hit = None
        for x in nd:
            blob = (x["text"] + " " + x["desc"]).strip()
            if any(w == blob or w in blob for w in CLOSE_WORDS):
                hit = x
                break
        if not hit:
            break
        tap(hit, 2)
        n += 1
    return n


def go_home(nodes=None):
    """하단 '홈' 탭을 눌러 홈으로. 앱을 벗어나지 않는다."""
    nd = nodes or dump()
    w, h = screen()
    for n in nd:
        if (n["text"] == "홈" or n["desc"] == "홈") and n["y"] > h * 0.85:
            tap(n, 3)
            return True
    return False


def texts(nodes):
    seen, out = set(), []
    for n in sorted(nodes, key=lambda x: x["y"]):
        t = n["text"] or n["desc"]
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def main():
    a = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    if "--dump" in a:
        for t in texts(dump()):
            print("  ", t[:100])
        return
    brand = a[a.index("--brand") + 1] if "--brand" in a else None
    if not brand:
        raise SystemExit("--brand <브랜드명> 필요")

    print("■ %s — 배민에서 찾는다" % brand, flush=True)
    # 🔴 force-stop 하지 않는다(2026-07-26 사고: 앱을 꺼서 대표가 해둔 로그인 화면이 날아갔다).
    #    이미 켜져 있는 앱을 그대로 쓴다. 앱이 앞에 없을 때만 조용히 띄운다.
    if PKG not in sh("shell", "dumpsys", "window", "|", "grep", "-i", "mCurrentFocus"):
        sh("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(7)
    close_popups()
    # 🔴 뒤로가기(keyevent 4)를 쓰지 않는다(2026-07-26 사고): 배민에서 뒤로가기를 연달아 누르면
    #    **앱이 종료된다.** 대표가 로그인·주소를 맞춰둔 상태가 날아가서 세 번이나 팅겼다.
    #    홈으로 갈 때는 하단 '홈' 탭만 쓰고, 그것도 없으면 그냥 지금 화면에서 진행한다.
    go_home()
    nodes = dump()
    box = search_box(nodes)
    if not box:
        print("  검색창을 못 찾았다. 지금 화면:", flush=True)
        for t in texts(nodes)[:25]:
            print("    ", t[:80])
        return
    tap(box, 3)
    nodes = dump()
    box = find(nodes, cls="EditText")
    if not box:
        print("  검색 입력창이 안 열렸다. 지금 화면:", flush=True)
        for t in texts(nodes)[:20]:
            print("    ", t[:80])
        return
    if not type_korean(box, brand):
        print("  붙여넣기 메뉴가 안 나왔다", flush=True)
        return
    sh("shell", "input", "keyevent", "66")
    time.sleep(6)

    nodes = dump()
    io.open(os.path.join(OUT, "%s_검색.txt" % brand), "w", encoding="utf-8").write(
        "\n".join(texts(nodes)))
    print("  검색 결과 상위:", flush=True)
    for t in texts(nodes)[:20]:
        print("    ", t[:80])
    print(flush=True)
    print("  → data/baemin/%s_검색.txt 저장" % brand, flush=True)


if __name__ == "__main__":
    main()
