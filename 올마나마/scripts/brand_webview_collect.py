# -*- coding: utf-8 -*-
"""**앱이 띄우는 웹사이트**에서 메뉴판을 받는다. 2026-07-28

    python scripts/brand_webview_collect.py --only 설빙
    python scripts/brand_webview_collect.py --apply

🔴 왜 이 길이 제일 좋은가
   브랜드 홈페이지에 가격이 없는 곳이 대부분이다(24곳 훑어보니 23곳이 «화면에 가격 없음»).
   그런데 **앱에는 가격이 다 있다.** 그래서 앱을 뜯었더니 — 껍데기였다.

       설빙 APK `assets/app.config`
           "WEBVIEW_URL": "https://sapp.sulbing.com"

   즉 **앱이 여는 그 주소를 그냥 열면 된다.** 폰도, 에뮬도, 화면 긁기도 필요 없다.
   앱 화면을 읽던 방식(탭 눌러가며 스크롤)은 사람이 붙어야 하고 49개에서 멈췄다.

⛔ 주소를 추측하지 않는다. **APK 안에 적힌 것**만 쓴다.
   찾는 법: `assets/app.config`(Expo) · `strings.xml` · JS 번들에서 `WEBVIEW_URL`·`BASE_URL` 검색.
"""
import io
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GAP = 4

# 브랜드 → 앱이 띄우는 주소 (APK 에서 확인한 것만)
SITES = {
    "설빙": "https://sapp.sulbing.com/menu",
}

RX_PRICE = re.compile(r"^([0-9]{1,3}(?:,[0-9]{3})+)\s*원$")
# 메뉴명이 아닌 줄 — 탭 이름·뱃지
SKIP = {"메뉴", "전체 메뉴", "마이 메뉴", "신메뉴", "NEW", "BEST", "HOT", "품절",
        "설빙", "컵설빙", "세트", "커피", "음료", "스무디/에이드", "차", "사이드",
        "토핑", "기타", "추천메뉴", "이벤트"}


def render(url, budget=20000):
    r = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
         "--hide-scrollbars", "--window-size=430,8000",
         "--virtual-time-budget=%d" % budget, "--dump-dom", url],
        capture_output=True, timeout=200)
    return r.stdout.decode("utf-8", "replace")


def to_lines(dom):
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", dom)
    s = re.sub(r"<[^>]+>", "\n", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return [x.strip() for x in s.split("\n") if x.strip()]


def pairs(lines):
    """«이름» 바로 위/아래에 «16,500원». 탭 이름·NEW 뱃지는 건너뛴다."""
    out, seen = [], set()
    for i, t in enumerate(lines):
        m = RX_PRICE.match(t)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        if not (500 <= price <= 200000):
            continue
        for j in range(i - 1, max(-1, i - 4), -1):
            nm = lines[j].strip()
            if nm in SKIP or RX_PRICE.match(nm):
                continue
            if 2 <= len(nm) <= 34 and re.search(r"[가-힣A-Za-z]", nm):
                k = re.sub(r"\s+", "", nm)
                if k not in seen:
                    seen.add(k)
                    out.append((nm, price))
                break
    return out


def main():
    apply_ = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    db = PS.connect()
    cur = db.cursor()
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")

    for bname, url in SITES.items():
        if only and only not in bname:
            continue
        print("■ %-8s %s" % (bname, url), flush=True)
        dom = render(url)
        if not dom:
            print("  🔴 렌더 실패", flush=True)
            continue
        got = pairs(to_lines(dom))
        if not got:
            print("  🔴 이름+가격 0개 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것",
                  flush=True)
            continue
        print("  메뉴 %d개 · 예: %s" % (len(got), " / ".join(
            "%s %s원" % (n, format(p, ",")) for n, p in got[:3])), flush=True)
        if not apply_:
            continue
        br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
        if not br:
            print("  🔴 DB 에 «%s» 없음" % bname, flush=True)
            continue
        st, changed = {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
        for nm, pr in got:
            before = cur.execute("""SELECT price FROM brand_menu_official
                                    WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
            r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                       note="공식 앱(웹뷰) 기준", now=now)
            db.commit()
            st[r] = st.get(r, 0) + 1
            if r == "changed":
                changed.append((nm, before["price"], pr))
        print("  저장: 새로 %d · **바뀜 %d** · 그대로 %d · 사람확정 건너뜀 %d"
              % (st["new"], st["changed"], st["same"], st["skip"]), flush=True)
        for nm, a, b in changed[:15]:
            print("    💰 %-26s %s → %s" % (nm[:26], format(a or 0, ","), format(b, ",")),
                  flush=True)
        time.sleep(GAP)


if __name__ == "__main__":
    main()
