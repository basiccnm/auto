# -*- coding: utf-8 -*-
"""이미 받아둔 캐시 **전부**를 합쳐 재료별 로켓 최저가를 다시 고른다. 2026-07-26

🔴 왜 필요한가 (대표 지적)
  *"이런건 1개짜리가 있는데 왜 4개짜리 올리지?"*
  `신선 생크림` 에 34,500원 밀락 골드 휘핑크림이 붙었다. 그런데 같은 캐시 안에
  **4,290원 프레지덩 미니 휘핑크림 200ml** 가 있었다.
  원인: 수집기가 **검색어 하나에서 로켓이 나오면 거기서 멈췄다.**
       `휘핑크림` 으로 찾아 34,500원을 잡고, `신선 생크림 1L` 캐시는 안 봤다.

  → 검색어 하나에서 멈추지 말고 **그 재료의 모든 검색어 결과를 합쳐** 최저가를 고른다.
    API 호출은 0회 — 이미 받아둔 캐시만 다시 읽는다.

고르는 규칙 (소매)
  ① 로켓배송만  ② 품목이 맞는지(검색어 토큰 하나 이상 포함)  ③ **가격 최저**
  프리미엄·가공품·화장품은 후순위/제외. 미인정(retail_rejected)한 상품은 뺀다.

    python scripts/retail_lowest.py            # 보고만
    python scripts/retail_lowest.py --apply    # 더 싼 게 있으면 갈아끼운다
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI    # noqa: E402
import retail_fill as RF           # noqa: E402
import retail_retry as RR          # noqa: E402


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    rej = {}
    for r in c.execute("SELECT ingredient_key, product_id FROM retail_rejected"):
        rej.setdefault(r[0], set()).add(r[1])

    rows = [r for r in c.execute("""
        SELECT x.ingredient_key k, x.name cur_name, x.price cur_price, x.product_id cur_pid,
               x.status, i.name inm, i.base_unit bu,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=x.ingredient_key) uses
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE x.status IN ('ok','pending','skip')
        ORDER BY uses DESC""")]

    better, same, none = [], 0, 0
    for r in rows:
        # 이 재료에 쓰일 수 있는 검색어 전부 (retry 쪽 규칙이 더 넓다)
        kws = list(dict.fromkeys(RR.kw_candidates(r["inm"]) + [RF.keyword(r["inm"])]))
        pool, seen = [], set()
        for kw in kws:
            fp = RF.cpath(kw)
            if not os.path.exists(fp):
                continue
            try:
                items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
            except Exception:
                continue
            cw = [t for t in kw.split() if len(t) >= 2]
            for p in items:
                pid, pn, price = p.get("productId"), p.get("productName") or "", p.get("productPrice")
                if not price or pid in seen or not p.get("isRocket"):
                    continue
                if pid in rej.get(r["k"], set()):
                    continue
                if not RF.is_food(p) or RF.JUNK.search(pn):
                    continue
                if not any(w in re.sub(r"\s+", "", pn) for w in cw):
                    continue
                if [b for b in CI.PROCESSED if re.search(b, pn) and not re.search(b, r["inm"])]:
                    continue
                seen.add(pid)
                pool.append({"pid": pid, "name": pn, "price": price, "kw": kw,
                             "premium": 1 if CI.PREMIUM.search(pn) else 0,
                             "pack_g": RF.pack_g(pn),
                             "image": p.get("productImage"), "url": p.get("productUrl")})
        if not pool:
            none += 1
            continue
        pool.sort(key=lambda x: (x["premium"], x["price"]))
        b = pool[0]
        cur = r["cur_price"] or 10 ** 9
        if b["price"] < cur * 0.98:
            better.append((r, b, len(pool)))
        else:
            same += 1

    better.sort(key=lambda t: -(t[0]["uses"]))
    print("캐시 전체를 합쳐 다시 고름 (API 0회)")
    print("  더 싼 게 있는 재료 %d종 · 지금이 이미 최저 %d종 · 후보 없음 %d종"
          % (len(better), same, none))
    print()
    print("%-20s %4s %10s %10s  %s" % ("재료", "메뉴", "지금", "최저가", "상품"))
    print("-" * 110)
    for r, b, npool in better[:30]:
        print("%-20s %3d개 %9s원 %9s원  %s" % (
            r["inm"][:20], r["uses"],
            format(round(r["cur_price"] or 0), ","), format(b["price"], ","), b["name"][:40]))
    print("-" * 110)

    if apply:
        cur = c.cursor()
        for r, b, npool in better:
            # 이미 통과(ok)한 것도 갈아끼운다 — 더 싼 게 있으면 그게 소매값이다.
            #   다만 status 는 pending 으로 되돌려 대표가 다시 확인하게 한다.
            cur.execute("""INSERT OR REPLACE INTO ingredient_retail
                (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
                VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                        (r["k"], b["pid"], b["name"], b["price"], b["pack_g"],
                         b["image"], b["url"]))
        c.commit()
        print()
        print("✅ %d종 갈아끼움 (검수 대기로 올림)" % len(better))
    else:
        print()
        print("DB 미반영. 반영은 --apply")
    c.close()


if __name__ == "__main__":
    main()
