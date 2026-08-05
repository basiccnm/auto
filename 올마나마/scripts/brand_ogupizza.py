# -*- coding: utf-8 -*-
"""59쌀피자(오구피자) 메뉴판 — 이름 + 사이즈별 가격. 2026-07-28

    python scripts/brand_ogupizza.py            # 미리보기
    python scripts/brand_ogupizza.py --apply

구조 (실측 — 상세 페이지)
    <h4>꿀담은고구마피자</h4>
    <ul class="price">
      <li><strong>L</strong><p>14,900</p></li>
      <li><strong>R</strong><p>11,900</p></li>
    </ul>
    <mark>매장 방문 시 가격입니다. 배달 시 가격이 상이…</mark>

🔴 **목록에는 가격이 없다.** 상세(`viewMode=view&idx=`)로 들어가야 나온다.
   그래서 목록에서 `idx` 를 먼저 걷고, 상세를 하나씩 연다.
✅ 사이트가 «매장 방문 시 가격» 이라고 **직접 밝힌다** — 우리 기준(홀 매장가)과 맞다.
🔴 가격에 「원」이 없다(`14,900`). 일반 파서가 0건으로 본 이유다.
"""
import os
import re
import ssl
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

BRAND = "59쌀피자"
HOST = "https://xn--2e0b622b4gcxwb8x8a.kr"
LIST = HOST + "/_subpage/kor/menu/list.php?ca_id=%s"
VIEW = (HOST + "/_subpage/kor/menu/list.php?viewMode=view&ca_id=%s"
        "&sel_search=&txt_search=&page=1&idx=%s")
CATS = ["01", "02", "03", "04", "05", "06", "07"]
GAP = 2.0

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9", "Referer": HOST + "/"}

RX_IDX = re.compile(r"idx=(\d+)")
RX_H4 = re.compile(r"(?is)<h4[^>]*>(.*?)</h4>")
RX_PRICE = re.compile(r"(?is)<li>\s*<strong>(.*?)</strong>\s*<p>\s*([\d,]{3,9})\s*</p>\s*</li>")


def get(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                      timeout=30, context=ctx).read().decode("utf-8", "replace")
    except Exception:
        return ""


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def main():
    apply_ = "--apply" in sys.argv
    seen, got = set(), []
    for ca in CATS:
        html = get(LIST % ca)
        if not html:
            print("  ca_id=%s  목록 못 받음" % ca, flush=True)
            continue
        idxs = list(dict.fromkeys(RX_IDX.findall(html)))
        n0 = len(got)
        for idx in idxs:
            d = get(VIEW % (ca, idx))
            if not d:
                continue
            h = RX_H4.search(d)
            if not h:
                continue
            nm = strip(h.group(1))
            for size, price in RX_PRICE.findall(d):
                sz = strip(size)
                try:
                    pr = int(price.replace(",", ""))
                except ValueError:
                    continue
                if not nm or not (1000 <= pr <= 300000):
                    continue
                # 🔴 사이즈 칸이 「가격」인 메뉴가 있다(단일 사이즈) — 이름에 붙이면
                #    「치즈링 가격」 이 되어 버린다. L/R 같은 진짜 사이즈만 붙인다.
                sz = "" if sz in ("가격", "", "-") else sz
                full = "%s %s" % (nm, sz) if sz else nm
                k = re.sub(r"\s+", "", full)
                if k not in seen:
                    seen.add(k)
                    got.append((full, pr))
            time.sleep(GAP)
        print("  ca_id=%s  상세 %2d개 → 새로 %d" % (ca, len(idxs), len(got) - n0), flush=True)

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
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                   note="공식 홈페이지 · 매장 방문 기준", now=now)
        db.commit()
        st[r] = st.get(r, 0) + 1
    print("\n저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))


if __name__ == "__main__":
    main()
