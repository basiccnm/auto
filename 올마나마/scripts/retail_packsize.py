# -*- coding: utf-8 -*-
"""이미 붙어 있는 소매 상품의 **용량만** 찾아 채운다. 2026-07-27

🔴 상품을 바꾸지 않는다 (대표 지시 2026-07-27: "용량을 찾아서 넣어")
   자동으로 상품을 다시 고르면 **다른 물건이 붙는다.** 오늘 세 번 그랬다 —
     올리브 블렌딩유 → 포마스 혼합유 / 모차렐라 치즈 → 리코타 치즈 / 백설탕 → 알룰로스
   그래서 **product_id 는 그대로 두고 pack_g 만** 채운다.

왜 필요한가
   `compute_line_costs` 는 `pack_g` 가 없으면 소매 단가를 못 낸다(옛 manual_price 로 조용히 폴백).
   지금 100종이 용량 없이 붙어 있어서 쿠팡 상품을 바꿔도 원가가 안 바뀐다.

용량을 어디서 읽나
   쿠팡 상품 페이지의 **제목**에 용량이 들어 있다 — "해표 압착 올리브유, 500ml, 1개".
   API 는 용량 필드를 안 주므로 `coupang.com/vp/products/<id>` 를 헤드리스 크롬으로 열어 title 을 읽는다.

⛔ 못 읽으면 비워둔다. 표준 규격을 추측해 넣지 않는다(`ingredients-evidence-only`).

    python scripts/retail_packsize.py --limit 10        # 찾기만
    python scripts/retail_packsize.py --limit 10 --apply
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "retail_packsize.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WORKERS = 3
BUDGET = "9000"

RX_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
RX_OG = re.compile(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)')
# "…, 500ml, 1개" / "1kg" / "900ml" — 용량과 개수를 같이 본다
RX_VOL = re.compile(r"(\d[\d,.]*)\s*(kg|g|l|ml)\b", re.I)
RX_CNT = re.compile(r"[,·]\s*(\d+)\s*(?:개|입|팩|병|봉|매)\b")


def render(url):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1200,1200",
             "--virtual-time-budget=" + BUDGET, "--dump-dom", url],
            capture_output=True, timeout=70)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def title_of(dom):
    for rx in (RX_OG, RX_TITLE):
        m = rx.search(dom or "")
        if m:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            if t and "쿠팡" not in t[:4]:
                return t
    return ""


def parse_pack(title):
    """제목에서 (총 용량 g, 설명) 을 읽는다. 개수 표기가 있으면 곱한다."""
    if not title:
        return None, ""
    m = RX_VOL.search(title)
    if not m:
        return None, title
    v = float(m.group(1).replace(",", ""))
    u = m.group(2).lower()
    g = v * 1000 if u in ("kg", "l") else v
    cnt = RX_CNT.search(title)
    n = int(cnt.group(1)) if cnt else 1
    if n > 1:
        # "500ml, 4개" = 총 2,000ml. 낱개 지출이 아니라 그 상품 한 건이 총량이다
        return g * n, "%g%s × %d개" % (v, u, n)
    return g, "%g%s" % (v, u)


def job(r):
    url = r["url"] or ("https://www.coupang.com/vp/products/%s" % r["pid"])
    dom = render(url)
    title = title_of(dom)
    g, desc = parse_pack(title)
    out = dict(r, title=title, pack_g=g, pack_desc=desc)
    print("   %s %-24s %8s원  %-10s  %s" % (
        "✅" if g else "✗", r["name"][:24], format(round(r["price"] or 0), ","),
        desc if g else "못 읽음", (title or "(제목 없음)")[:44]), flush=True)
    time.sleep(0.5)
    return out


def main():
    apply = "--apply" in sys.argv
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 200
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT x.ingredient_key k, i.name, x.product_id pid, x.name pn, x.price price, x.url url,
               (SELECT COUNT(*) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=x.ingredient_key AND b.published=1) nm,
               (SELECT COUNT(*) FROM dish_ingredients d WHERE d.ingredient_key=x.ingredient_key) nd
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE x.pack_g IS NULL AND x.price > 0 AND x.product_id IS NOT NULL
          AND COALESCE(x.status,'') NOT IN ('store','none')
        ORDER BY (nm + nd) DESC LIMIT ?""", (lim,))]
    print("용량 없는 소매 상품 %d건 — 상품은 그대로 두고 용량만 읽는다" % len(rows), flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(job, rows))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))

    got = [r for r in res if r["pack_g"]]
    if apply:
        cur = c.cursor()
        for r in got:
            cur.execute("UPDATE ingredient_retail SET pack_g=? WHERE ingredient_key=?",
                        (r["pack_g"], r["k"]))
        c.commit()
    print("", flush=True)
    print("읽음 %d / %d%s → %s" % (len(got), len(res),
                                 "  (DB 반영)" if apply else "  (미반영 — --apply)", OUT), flush=True)


if __name__ == "__main__":
    main()
