# -*- coding: utf-8 -*-
"""메뉴를 지운다 — 딸린 행까지 함께. 2026-07-27

🔴 왜 스크립트로 하나 — 메뉴 하나를 지우면 **6개 테이블**을 건드려야 한다.
   손으로 하면 `dish_menus`·`menu_mealkit` 이 남아 요리 페이지가
   `TypeError: 'NoneType' object is not subscriptable` 로 죽는다(2026-07-27 실제 발생).

🔴 지우기 전에 **무엇을 지우는지 전부 출력**하고, 옛 값을 화면에 남긴다.
   `menus` 행은 복구할 수 없으니 이 출력이 유일한 기록이다.

⛔ `brand_menu_official` 행은 **지우지 않는다** — 브랜드가 실제로 파는 메뉴라는 사실은 그대로다.
   우리 원가 메뉴와의 연결(`menu_id`)만 끊는다.

    python scripts/menu_delete.py 3 8
    python scripts/menu_delete.py 3 8 --apply
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

# (테이블, 지울지) — False 면 menu_id 만 NULL 로 끊는다
TABLES = [
    ("menu_ingredients", True),
    ("menu_verified", True),
    ("dish_menus", True),
    ("menu_mealkit", True),
    ("mealkit_rejected", True),
    ("menu_coupang", True),
    ("menu_sikbom", True),
    ("mi_removed", True),
    ("menu_name_audit", True),
    ("brand_menu_official", False),
]


def main():
    ids = [a for a in sys.argv[1:] if a.isdigit()]
    apply = "--apply" in sys.argv
    if not ids:
        print("쓰는 법: python scripts/menu_delete.py <메뉴id> [<메뉴id>…] [--apply]")
        return

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    for mid in ids:
        m = cur.execute("""SELECT m.*, b.name bn FROM menus m JOIN brands b ON b.id=m.brand_id
                           WHERE m.id=?""", (mid,)).fetchone()
        if not m:
            print("✗ menu %s 없음" % mid)
            continue
        print("=" * 74)
        print("menu %s — %s / %s" % (mid, m["bn"], m["name"]))
        print("=" * 74)
        print("  판매 %s · 소매 %s(%s%%) · 도매 %s(%s%%)" % (
            m["sell_price"], round(m["est_cost"] or 0),
            round(m["cost_ratio"] or 0, 1), round(m["store_cost"] or 0),
            round(m["store_ratio"] or 0, 1)))
        print("  재료:")
        for r in cur.execute("""SELECT i.name, mi.amount a, mi.unit u, mi.line_cost lc,
                                       mi.wholesale_cost wc, mi.composition cp
                                FROM menu_ingredients mi
                                JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
                                WHERE mi.menu_id=? ORDER BY mi.sort_order""", (mid,)):
            print("    %-30s %6g%-4s  도매%6s 소매%6s%s" % (
                r["name"][:30], r["a"], r["u"], r["wc"] or 0, r["lc"] or 0,
                ("  | " + r["cp"][:40]) if r["cp"] else ""))
        if m["recipe_steps"]:
            print("  레시피:")
            for ln in (m["recipe_steps"] or "").split("\n"):
                if ln.strip():
                    print("    %s" % ln.strip()[:80])

        print("  딸린 행:")
        for tbl, drop in TABLES:
            try:
                n = cur.execute("SELECT COUNT(*) FROM %s WHERE menu_id=?" % tbl, (mid,)).fetchone()[0]
            except Exception:
                continue
            if n:
                print("    %-22s %d행 %s" % (tbl, n, "지움" if drop else "연결만 끊음"))

        if not apply:
            continue
        for tbl, drop in TABLES:
            try:
                if drop:
                    cur.execute("DELETE FROM %s WHERE menu_id=?" % tbl, (mid,))
                else:
                    cur.execute("UPDATE %s SET menu_id=NULL WHERE menu_id=?" % tbl, (mid,))
            except Exception as e:
                print("    ⚠️ %s: %s" % (tbl, str(e)[:50]))
        cur.execute("DELETE FROM menus WHERE id=?", (mid,))
        print("  ✅ 지웠다")

    if apply:
        c.commit()
        print()
        print("반영 완료. 다음을 순서대로 돌릴 것:")
        print("  python scripts/compute_line_costs.py")
        print("  python scripts/gen_dishes.py · gen_preview_html.py · gen_sitemap.py")
        print("  python scripts/preview_orphans.py --apply     ← 지운 메뉴의 옛 페이지 삭제")
    else:
        print()
        print("← 미반영. --apply 를 붙여라")


if __name__ == "__main__":
    main()
