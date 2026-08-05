# -*- coding: utf-8 -*-
"""네이버 플레이스 **매장 메뉴판**에서 이름·가격을 읽는다. 2026-07-28

    python scripts/place_menu_read.py 1133583874 스타벅스
    python scripts/place_menu_read.py 1133583874 스타벅스 --apply

🔴 경로는 `place` 다 — 전에 `restaurant` 만 써서 **카페가 통째로 안 잡혔다**(2026-07-28).
       https://m.place.naver.com/place/{매장id}/menu/list
   카페·식당 가리지 않고 이 경로면 열린다. 스타벅스가 이걸로 뚫렸다.

⛔ 지도 화면으로 가지 않는다. **매장 id 를 받아** 메뉴판 주소를 바로 연다.
⚠️ 플레이스 가격은 **그 매장 값**이다. 프랜차이즈는 대체로 같지만
   본사 권장가와 다를 수 있어 출처를 `naver_place` 로 남긴다.
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

ADB = r"D:\Android\Sdk\platform-tools\adb.exe"
# «이름 설명 4,700원» 한 줄로 붙어 나온다 — 뒤에서 가격을 떼고 앞을 이름으로 본다
RX = re.compile(r"^(.{2,60}?)\s+([\d]{1,3}(?:,[\d]{3})+)\s*원$")


def sh(dev, *a, timeout=90):
    return subprocess.run([ADB, "-s", dev] + list(a),
                          capture_output=True, timeout=timeout).stdout.decode("utf-8", "replace")


def dump(dev):
    sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
    x = sh(dev, "shell", "cat", "/sdcard/ui.xml")
    return [t for t in re.findall(r'text="([^"]+)"', x) if t.strip()]


def screen(dev):
    m = re.search(r"(\d+)x(\d+)", sh(dev, "shell", "wm", "size"))
    return (int(m.group(1)), int(m.group(2))) if m else (1600, 900)


def clean_name(s):
    """«카페 아메리카노 강렬한 에스프레소 샷에…» → 앞의 짧은 이름만 남긴다."""
    s = s.strip()
    # 설명은 대개 이름 뒤에 이어 붙는다. 문장부호가 나오면 거기서 자른다.
    s = re.split(r"[.,·]|\s{2,}", s)[0].strip()
    # 그래도 길면 앞 6어절까지
    w = s.split()
    if len(w) > 6:
        s = " ".join(w[:6])
    return s


def main():
    pid = sys.argv[1]
    brand = sys.argv[2]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "emulator-5554"
    rounds = int(sys.argv[sys.argv.index("--scroll") + 1]) if "--scroll" in sys.argv else 22
    apply_ = "--apply" in sys.argv

    url = "https://m.place.naver.com/place/%s/menu/list" % pid
    print("■ %s" % url, flush=True)
    sh(dev, "shell", "am", "force-stop", "com.android.chrome")
    time.sleep(2)
    sh(dev, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "'%s'" % url)
    for _ in range(10):
        time.sleep(3)
        if any(re.search(r"[\d,]{3,7}\s*원", t) for t in dump(dev)):
            break

    w, h = screen(dev)
    seen = {}
    for i in range(rounds):
        for t in dump(dev):
            m = RX.match(t.strip())
            if not m:
                continue
            nm = clean_name(m.group(1))
            pr = int(m.group(2).replace(",", ""))
            if nm and 500 <= pr <= 200000 and nm not in seen:
                seen[nm] = pr
        sh(dev, "shell", "input", "swipe", str(w // 2), str(int(h * 0.80)),
           str(w // 2), str(int(h * 0.25)), "400")
        time.sleep(1.4)

    print("\n― %s 메뉴 %d개 ―" % (brand, len(seen)))
    for k, v in seen.items():
        print("   %-40s %8s원" % (k[:40], format(v, ",")))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    import menu_price_store as PS
    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (brand,)).fetchone()
    if not br:
        print("🔴 DB 에 «%s» 브랜드가 없다" % brand)
        return
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    st = {"new": 0, "changed": 0, "same": 0, "skip": 0}
    for nm, pr in seen.items():
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_PLACE,
                   note="네이버 플레이스 1개 지점", now=now)
        db.commit()
        st[r] = st.get(r, 0) + 1
    print("\n저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))


if __name__ == "__main__":
    main()
