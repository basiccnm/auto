# -*- coding: utf-8 -*-
"""청년피자 메뉴판 — 이름 + 사이즈별 가격. 2026-07-28

    python scripts/brand_youngmanpizza.py            # 미리보기
    python scripts/brand_youngmanpizza.py --apply

구조 (실측)
    <li class="menu_box">
      <div class="menu_name md">나만의사색피자</div>
      <div class="menu_desc">…</div>
      <ul class="menu_price">
        <li><div class="size">L</div><div class="price">27,900</div></li>
        <li><div class="size">R</div><div class="price">21,900</div></li>
      </ul>
    </li>

🔴 가격에 **「원」이 없다**(`27,900`). 일반 파서가 0건으로 본 이유다.
🔴 피자는 **사이즈마다 값이 다르다** — 이름에 사이즈를 붙여 따로 저장한다
   (`나만의사색피자 L`). 안 그러면 한 메뉴에 값이 두 개라 뭐가 맞는지 알 수 없다.
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BRAND = "청년피자"
URLS = ["https://www.youngmanpizza.co.kr/sub01/menu.php"]
GAP = 4

RX_BOX = re.compile(r'(?is)<li[^>]*class="[^"]*menu_box[^"]*"[^>]*>(.*?)</li>\s*(?=<li[^>]*class="[^"]*menu_box|</ul>)')
RX_NAME = re.compile(r'(?is)<div[^>]*class="[^"]*menu_name[^"]*"[^>]*>(.*?)</div>')
RX_PAIR = re.compile(r'(?is)<div[^>]*class="size"[^>]*>(.*?)</div>\s*'
                     r'<div[^>]*class="price"[^>]*>\s*([\d,]{3,9})\s*</div>')


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def render(url, budget=15000):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,8000",
             "--virtual-time-budget=%d" % budget, "--dump-dom", url],
            capture_output=True, timeout=150)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def parse(dom):
    out = []
    for body in RX_BOX.findall(dom):
        m = RX_NAME.search(body)
        if not m:
            continue
        nm = strip(m.group(1))
        if not nm:
            continue
        for size, price in RX_PAIR.findall(body):
            sz = strip(size)
            try:
                pr = int(price.replace(",", ""))
            except ValueError:
                continue
            if 1000 <= pr <= 300000:
                out.append(("%s %s" % (nm, sz) if sz else nm, pr))
    return out


def main():
    apply_ = "--apply" in sys.argv
    seen, got = set(), []
    for u in URLS:
        rows = parse(render(u))
        for nm, pr in rows:
            k = re.sub(r"\s+", "", nm)
            if k in seen:
                continue
            seen.add(k)
            got.append((nm, pr))
        print("  %-46s %d개" % (u[-44:], len(rows)), flush=True)
        time.sleep(GAP)

    if not got:
        print("🔴 0건 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    print("\n● %s — 메뉴 %d개" % (BRAND, len(got)))
    for nm, pr in got[:12]:
        print("   %-32s %8s원" % (nm[:32], format(pr, ",")))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (BRAND,)).fetchone()
    if not br:
        print("🔴 DB 에 «%s» 브랜드가 없다" % BRAND)
        return
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    st = {"new": 0, "changed": 0, "same": 0, "skip": 0}
    for nm, pr in got:
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL, note="공식 홈페이지", now=now)
        db.commit()
        st[r] = st.get(r, 0) + 1
    print("\n저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))


if __name__ == "__main__":
    main()
