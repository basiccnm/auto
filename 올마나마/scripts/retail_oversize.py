# -*- coding: utf-8 -*-
"""소매 상품이 **일반 소비자가 살 만한 규격**인지 검사한다. 2026-07-27

🔴 대표 확정 규격 상한 (2026-07-27)
   > *"소스가 비싸지 않으면 20000원선이면 일반 소비자도 살수 있으니깐"*
   > *"그런데 5kg이런거는 못사 최대 2.5kg으로 목박자"*

   · **용량 상한 2.5kg / 2.5L** — 5kg 은 소매가 아니다
   · **가격 상한 20,000원선** — 그 이상이면 일반 소비자가 안 산다
   · 둘 중 하나만 넘어도 소매로는 부적합 → 소포장을 다시 찾거나 비운다

⚠️ 예외: 생닭·고기·야채 같은 **원물**은 필요량 자체가 커서 상한을 넘을 수 있다.
   상한은 **소스·파우더·시즈닝·기름** 같은 «양념류»에 적용한다.

    python scripts/retail_oversize.py
"""
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

MAX_G = 2500          # 2.5kg / 2.5L
MAX_WON = 20000       # 20,000원선
# 양념류 — 상한을 적용할 재료
RX_SAUCE = re.compile(r"소스|양념|시즈닝|파우더|튀김가루|분말|드레싱|시럽|기름|유$|식용유|"
                      r"장$|간장|고추장|된장|쌈장|마요|케첩|식초|설탕|소금|후추|다시|육수")


def main():
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT COALESCE(i.display_name, i.name) n, i.ingredient_key k, i.name raw,
               x.name pn, x.price p, x.pack_g g, x.status s,
               (SELECT COUNT(DISTINCT b.id) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=i.ingredient_key AND b.published=1) nb,
               (SELECT GROUP_CONCAT(DISTINCT b.name) FROM menu_ingredients mi
                  JOIN menus m ON m.id=mi.menu_id JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=i.ingredient_key AND b.published=1) bl
        FROM ingredients i JOIN ingredient_retail x ON x.ingredient_key=i.ingredient_key
        WHERE x.price > 0 AND COALESCE(x.status,'') NOT IN ('store','none')
        ORDER BY x.price DESC""")]

    big_g, big_won, ok = [], [], 0
    for r in rows:
        if not r["nb"]:
            continue
        sauce = bool(RX_SAUCE.search(r["n"] or "") or RX_SAUCE.search(r["raw"] or ""))
        over_g = sauce and (r["g"] or 0) > MAX_G
        over_won = r["p"] > MAX_WON
        if over_g:
            big_g.append(r)
        if over_won and not over_g:
            big_won.append(r)
        if not (over_g or over_won):
            ok += 1

    print("=" * 92)
    print("소매 규격 검사 — 양념류 상한 %gkg · 가격 상한 %s원" % (MAX_G / 1000, format(MAX_WON, ",")))
    print("=" * 92)
    print()
    print("🔴 용량 초과 (%gkg 넘는 양념류) %d건 — 일반 소비자가 못 산다" % (MAX_G / 1000, len(big_g)))
    for r in sorted(big_g, key=lambda x: -(x["g"] or 0)):
        print("   %-20s %7gg %8s원  %s" % (r["n"][:20], r["g"], format(round(r["p"]), ","),
                                         (r["pn"] or "")[:46]))
        print("        쓰는 곳 %d곳: %s" % (r["nb"], (r["bl"] or "")[:60]))
    print()
    print("⚠️ 가격 초과 (%s원 넘음) %d건" % (format(MAX_WON, ","), len(big_won)))
    for r in sorted(big_won, key=lambda x: -x["p"]):
        print("   %-20s %7sg %8s원  %s" % (r["n"][:20], r["g"] or "?",
                                         format(round(r["p"]), ","), (r["pn"] or "")[:46]))
        print("        쓰는 곳 %d곳: %s" % (r["nb"], (r["bl"] or "")[:60]))
    print()
    print("✅ 통과 %d건" % ok)


if __name__ == "__main__":
    main()
