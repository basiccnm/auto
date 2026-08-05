# -*- coding: utf-8 -*-
"""묶음 상품을 배제하고 **1개짜리 최저가**로 바꾼다. 2026-07-26

🔴 왜 필요한가 (대표 지적)
  *"입력한것중에 1개짜리있는거있을수 있으니 확인하고"*
  통과된 것 중 10종이 묶음 상품이었다. 소매는 **집에서 1~2인분 쓰는 값**이라
  묶음을 사게 하면 안 된다.
    · 식용유(107개 메뉴)  1.5L **6개** 34,430원  ←  1개짜리 11,120원이 있었다
    · 국밥용 양념장         2kg **6개** 92,800원
    · 부대찌개 모둠햄       1kg **3개** 30,450원

고르는 규칙
  ① 로켓배송  ② 먹는 것(categoryName)  ③ **묶음이 아닌 것**  ④ 품목 일치  ⑤ 가격 최저
  묶음밖에 없으면 그건 그대로 둔다(어쩔 수 없음).

    python scripts/retail_single.py            # 보고만
    python scripts/retail_single.py --apply    # 1개짜리로 갈아끼운다
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

# 묶음 표기 — 상품명 끝의 "…, 6개" / "…x 10개" / "(6개)" 꼴
_B1 = re.compile(r"[,·]\s*(\d+)\s*(?:개|팩|입|봉|병|캔|매)\s*$")
_B2 = re.compile(r"[xX×]\s*(\d+)\s*(?:개|팩|입|봉)?")
_B3 = re.compile(r"\(\s*(\d+)\s*(?:개|팩|입|봉)\s*\)")


def bundle_count(nm):
    """묶음 개수. 1이거나 없으면 0을 준다."""
    n = 0
    for rx in (_B1, _B3, _B2):
        m = rx.search(nm or "")
        if m:
            v = int(m.group(1))
            if 2 <= v <= 60:
                n = max(n, v)
    return n


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    rej = {}
    for r in c.execute("SELECT ingredient_key, product_id FROM retail_rejected"):
        rej.setdefault(r[0], set()).add(r[1])

    rows = [r for r in c.execute("""
        SELECT x.ingredient_key k, x.name pn, x.price pr, x.product_id pid, x.status,
               i.name inm, i.base_unit bu,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=x.ingredient_key) uses
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE x.status IN ('ok','pending') ORDER BY uses DESC""")]

    changed, kept = [], 0
    for r in rows:
        cur_b = bundle_count(r["pn"])
        pool, seen = [], set()
        for kw in dict.fromkeys(RR.kw_candidates(r["inm"]) + [RF.keyword(r["inm"])]):
            fp = RF.cpath(kw)
            if not os.path.exists(fp):
                continue
            try:
                items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
            except Exception:
                continue
            cw = [t for t in kw.split() if len(t) >= 2]
            for p in items:
                pid, pn, pr = p.get("productId"), p.get("productName") or "", p.get("productPrice")
                if not pr or pid in seen or not p.get("isRocket"):
                    continue
                if pid in rej.get(r["k"], set()) or not RF.is_food(p) or RF.JUNK.search(pn):
                    continue
                if not any(w in re.sub(r"\s+", "", pn) for w in cw):
                    continue
                if [x for x in CI.PROCESSED if re.search(x, pn) and not re.search(x, r["inm"])]:
                    continue
                seen.add(pid)
                pool.append({"pid": pid, "name": pn, "price": pr,
                             "bundle": bundle_count(pn),
                             "premium": 1 if CI.PREMIUM.search(pn) else 0,
                             "pack_g": RF.pack_g(pn),
                             "image": p.get("productImage"), "url": p.get("productUrl")})
        # ③ 묶음이 아닌 것 우선 → 프리미엄 후순위 → ⑤ 가격 최저
        pool.sort(key=lambda x: (1 if x["bundle"] else 0, x["premium"], x["price"]))
        if not pool:
            continue
        b = pool[0]
        # 지금이 묶음인데 1개짜리가 있으면 바꾼다. 값이 더 싸도 바꾼다.
        # 🔴 묶음을 1개짜리로 바꿀 때 **더 비싸지면 바꾸지 않는다.**
        #    소곱창 3개 18,870원(개당 6,290) → 1개 22,310원 은 손해다.
        #    묶음 개수로 나눈 개당 값보다 싸야 진짜 이득이다.
        per_now = (r["pr"] or 10 ** 9) / (cur_b or 1)
        better = (b["price"] < (r["pr"] or 10 ** 9) * 0.98) and (b["price"] <= per_now * 1.05 or not cur_b)
        if better and b["pid"] != r["pid"]:
            changed.append((r, b, cur_b))
        else:
            kept += 1

    changed.sort(key=lambda t: -t[0]["uses"])
    print("통과·대기 %d종 검사 → 바꿀 것 %d종 · 그대로 %d종" % (len(rows), len(changed), kept))
    print()
    print("%-20s %4s %10s %5s %10s %5s  %s" % ("재료", "메뉴", "지금", "묶음", "바꿀것", "묶음", "상품"))
    print("-" * 116)
    for r, b, cb in changed[:40]:
        print("%-20s %3d개 %9s원 %4s %9s원 %4s  %s" % (
            r["inm"][:20], r["uses"], format(round(r["pr"] or 0), ","),
            ("%d개" % cb) if cb else "-", format(b["price"], ","),
            ("%d개" % b["bundle"]) if b["bundle"] else "1개", b["name"][:36]))
    print("-" * 116)

    if apply:
        cur = c.cursor()
        for r, b, cb in changed:
            cur.execute("""INSERT OR REPLACE INTO ingredient_retail
                (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
                VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                        (r["k"], b["pid"], b["name"], b["price"], b["pack_g"],
                         b["image"], b["url"]))
        c.commit()
        print()
        print("✅ %d종 갈아끼움 — 검수 대기로 올렸습니다" % len(changed))
    else:
        print()
        print("DB 미반영. 반영은 --apply")
    c.close()


if __name__ == "__main__":
    main()
