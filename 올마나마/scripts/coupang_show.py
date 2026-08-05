# -*- coding: utf-8 -*-
"""`coupang_search.py` 결과에서 **용량이 상품명에 박힌 후보**를 보여준다. 2026-07-27

🔴 저장 구조를 매번 잘못 읽어 «0건»을 반복했다. 정본은 이것이다:
   `{keyword, fetched_at, count, items:[{name, price, rocket, free, id, url, image}]}`
   → `items` · `name` · `price` · `rocket` (`productData`·`productName` 아니다)

    python scripts/coupang_show.py "휘핑크림 200ml" "생크림 500ml"
    python scripts/coupang_show.py --all --max 2500        # 저장된 전부, 용량 상한
"""
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(BASE, "data", "research", "coupang")
sys.stdout.reconfigure(encoding="utf-8")

RX_MULT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*[x×*]\s*(\d+)", re.I)
RX_CNT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*,\s*(\d+)\s*(?:개|입|봉|팩|병)", re.I)
RX_ONE = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\b", re.I)
BAD = re.compile(r"선물|기프트|세트박스|체험|샘플")


def g_of(v, u):
    v = float(str(v).replace(",", ""))
    return v * 1000 if u.lower() in ("kg", "l") else v


def pack(nm):
    """(총 g, 표기). 배수 표기를 반드시 반영한다 — `500g 2개입` = 1kg."""
    for rx in (RX_MULT, RX_CNT):
        m = rx.search(nm)
        if m:
            one, n = g_of(m.group(1), m.group(2)), int(m.group(3))
            if 1 <= n <= 60 and 1 <= one <= 30000:
                return one * n, m.group(0).strip()
    m = RX_ONE.search(nm)
    if m:
        one = g_of(m.group(1), m.group(2))
        if 1 <= one <= 60000:
            return one, m.group(0).strip()
    return None, ""


def main():
    mx = 60000
    skip = set()
    if "--max" in sys.argv:
        i = sys.argv.index("--max")
        mx = float(sys.argv[i + 1])
        skip.add(sys.argv[i + 1])          # 옵션 값이 키워드로 새지 않게
    kws = [a for a in sys.argv[1:] if not a.startswith("--") and a not in skip]
    if "--all" in sys.argv or not kws:
        kws = [f[:-5] for f in sorted(os.listdir(DIR)) if f.endswith(".json")]

    for kw in kws:
        p = os.path.join(DIR, kw + ".json")
        if not os.path.exists(p):
            print("✗ %s — 파일 없음" % kw)
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        items = d.get("items") or []
        rows, nosize = [], 0
        for it in items:
            nm = it.get("name") or ""
            pr = it.get("price") or 0
            if not nm or not pr or BAD.search(nm):
                continue
            g, desc = pack(nm)
            if not g or g > mx:
                nosize += 1
                continue
            rows.append((pr, g, nm, it.get("rocket"), it.get("id")))
        rows.sort()
        print("=" * 96)
        print("● %s  (수집 %d건 · 용량 확인 %d건)" % (kw, len(items), len(rows)))
        print("=" * 96)
        for n, (pr, g, nm, rk, pid) in enumerate(rows, 1):
            print("  %2d) %8s원 %7gg %9s원/kg %-5s %s"
                  % (n, format(int(pr), ","), g, format(round(pr / (g / 1000.0)), ","),
                     "로켓" if rk else "일반", nm[:52]))
        if not rows:
            print("  ⛔ 용량이 상품명에 박힌 후보 없음 (걸러진 %d건)" % nosize)
        elif nosize:
            print("  (용량 모름·상한 초과 %d건 제외)" % nosize)
        print()


if __name__ == "__main__":
    main()
