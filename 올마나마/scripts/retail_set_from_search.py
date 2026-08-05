# -*- coding: utf-8 -*-
"""`coupang_search.py` 결과에서 상품 하나를 골라 `ingredient_retail` 에 붙인다. 2026-07-27

🔴 사람이 고른 것만 넣는다 (대표 지시). 자동 판정 금지 —
   자동으로 고르다 세 번 다른 물건이 붙었다(포마스 혼합유 · 리코타 치즈 · 알룰로스).

🔴 **용량이 상품명에 박힌 상품만** 넣는다. 용량이 없으면 단위당 단가를 못 내고
   원가 계산이 옛 `manual_price` 로 조용히 넘어간다.

    python scripts/retail_set_from_search.py garlic_minced "맑은물에 국산 간편한 다진마늘" 130
    python scripts/retail_set_from_search.py garlic_minced "맑은물에" 130 --apply
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CDIR = os.path.join(BASE, "data", "research", "coupang")
sys.stdout.reconfigure(encoding="utf-8")


def items_of(path):
    d = json.load(io.open(path, encoding="utf-8"))
    if isinstance(d, list):
        return d
    for k in ("productData", "items", "data", "products"):
        v = d.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for k2 in ("productData", "items"):
                if isinstance(v.get(k2), list):
                    return v[k2]
    return []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) < 3:
        print("쓰는 법: python scripts/retail_set_from_search.py <재료키> <상품명조각> <용량g> [--apply]")
        return
    key, frag, pack_g = args[0], args[1], float(args[2])

    # ⚠️ 상품명 조각이 짧으면 **다른 검색어 파일의 동명 상품**이 먼저 걸린다
    #    (2026-07-27: `어나더소스 고추마요소스` 로 1kg 7,400원을 노렸는데 2kg 13,400원이 잡혔다).
    #    용량까지 포함한 전체 상품명을 넣을 것 — `…, 1개, 1kg` 처럼.
    hit = None
    for fn in sorted(os.listdir(CDIR)):
        if not fn.endswith(".json"):
            continue
        for it in items_of(os.path.join(CDIR, fn)):
            nm = it.get("productName") or it.get("name") or ""
            if frag in nm:
                hit = (fn, it, nm)
                break
        if hit:
            break
    if not hit:
        print("✗ '%s' 를 담은 상품을 못 찾았다 — 먼저 coupang_search.py 로 검색할 것" % frag)
        return

    fn, it, nm = hit
    price = float(it.get("productPrice") or it.get("price") or 0)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    r = cur.execute("""SELECT i.name, i.display_name dn, i.base_unit bu, i.wholesale_price wp,
                              (SELECT name FROM ingredient_retail x
                                WHERE x.ingredient_key=i.ingredient_key) old,
                              (SELECT price FROM ingredient_retail x
                                WHERE x.ingredient_key=i.ingredient_key) oldp
                       FROM ingredients i WHERE i.ingredient_key=?""", (key,)).fetchone()
    if not r:
        print("✗ 재료 %s 없음" % key)
        return

    per = price / (pack_g / 1000.0) if (r["bu"] or "").lower() in ("kg", "l") else price / pack_g
    print("● %s (%s)" % (r["dn"] or r["name"], key))
    print("   도매 %s원/%s" % (format(r["wp"] or 0, ","), r["bu"]))
    print("   옛 소매 %s / %s원" % ((r["old"] or "없음")[:44], format(int(r["oldp"] or 0), ",")))
    print("   새 소매 %s" % nm[:70])
    print("           %s원 / %gg  = %s원/%s  (검색어 파일 %s)"
          % (format(int(price), ","), pack_g, format(round(per), ","), r["bu"], fn))
    if r["wp"] and per > r["wp"] * 6:
        print("   ⚠️ 소매 단가가 도매의 %.1f배다 — 규격을 다시 볼 것" % (per / r["wp"]))

    if not apply:
        print()
        print("← 미반영. --apply 를 붙여라")
        return
    cur.execute("""INSERT INTO ingredient_retail
                   (ingredient_key, product_id, name, price, pack_g, rocket, image, url,
                    status, decided_at)
                   VALUES(?,?,?,?,?,?,?,?, 'ok', date('now'))
                   ON CONFLICT(ingredient_key) DO UPDATE SET
                     product_id=excluded.product_id, name=excluded.name,
                     price=excluded.price, pack_g=excluded.pack_g, rocket=excluded.rocket,
                     image=excluded.image, url=excluded.url,
                     status='ok', decided_at=date('now')""",
                (key, it.get("productId") or it.get("product_id"), nm, price, pack_g,
                 1 if (it.get("isRocket") or it.get("rocket")) else 0,
                 it.get("productImage") or it.get("image"),
                 it.get("productUrl") or it.get("url")))
    c.commit()
    print("   ✅ 반영")


if __name__ == "__main__":
    main()
