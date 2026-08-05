# -*- coding: utf-8 -*-
"""브랜드를 **딸린 행까지 안전하게** 지운다. 2026-07-28 신설

    python scripts/brand_delete.py 유로코피자              # 무엇이 지워지는지만 보여준다(기본)
    python scripts/brand_delete.py 유로코피자 --apply      # 실제 삭제
    python scripts/brand_delete.py 유로코피자 --apply --force   # 원가 낸 메뉴가 있어도 강행

⛔ **되돌릴 수 없다.** 그래서 기본은 미리보기이고, `--apply` 를 붙여야만 지운다.
⛔ **원가를 낸 메뉴(`menus`)가 있으면 기본적으로 거부한다.** 사람이 재료를 하나씩 확인해 만든
   작업물이라 실수로 날리면 복구가 안 된다. 정말 지우려면 `--force` 를 명시해야 한다.

왜 만들었나
----------
2026-07-28 하루에 코코이찌방야·순수치킨·유로코피자·태리로제 4곳을 지웠는데, 그때마다
«어느 테이블에 딸린 행이 있나» 를 손으로 확인하고 DELETE 를 직접 짰다. 브랜드가 달라도
지워야 할 테이블은 **늘 같다.** 하나라도 빠뜨리면 고아 행이 남는다.

지운 뒤에는 반드시:
    python scripts/publish.py --apply     ← 페이지 재생성·고아정리·배포까지
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

# brand_id 로 바로 걸리는 것
BY_BRAND = ["menu_cat_link", "brand_menu_cat", "brand_menu_official", "brand_origins",
            "menu_image"]
# menu_id 로 걸리는 것 — `menus` 를 지우기 전에 먼저 치운다
BY_MENU = ["menu_ingredients", "mi_removed", "dish_menus", "menu_coupang", "menu_mealkit",
           "mealkit_rejected", "menu_name_audit", "menu_sikbom", "menu_verified"]


def table_exists(c, t):
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    key = args[0]
    apply_ = "--apply" in sys.argv
    force = "--force" in sys.argv

    c = store.connect()
    b = c.execute("SELECT * FROM brands WHERE name=? OR slug=?", (key, key)).fetchone()
    if not b:
        cand = c.execute("SELECT name,slug FROM brands WHERE name LIKE ?",
                         ("%" + key + "%",)).fetchall()
        raise SystemExit("브랜드를 못 찾았다: %s%s" % (
            key, ("\n비슷한 것: " + ", ".join(r["name"] for r in cand)) if cand else ""))
    bid = b["id"]
    cat = c.execute("SELECT name FROM categories WHERE id=?", (b["category_id"],)).fetchone()

    print("=" * 66)
    print("■ %s  (id=%d · slug=%s · %s · 가맹 %s)"
          % (b["name"], bid, b["slug"], cat["name"] if cat else "-", b["frcs_cnt"] or "-"))
    print("=" * 66)

    mids = [r["id"] for r in c.execute("SELECT id FROM menus WHERE brand_id=?", (bid,))]
    plan = []
    for t in BY_MENU:
        if not table_exists(c, t) or not mids:
            continue
        n = c.execute("SELECT count(*) FROM %s WHERE menu_id IN (%s)"
                      % (t, ",".join("?" * len(mids))), mids).fetchone()[0]
        if n:
            plan.append((t, "menu_id", n))
    if mids:
        plan.append(("menus", "brand_id", len(mids)))
    for t in BY_BRAND:
        if not table_exists(c, t):
            continue
        n = c.execute("SELECT count(*) FROM %s WHERE brand_id=?" % t, (bid,)).fetchone()[0]
        if n:
            plan.append((t, "brand_id", n))
    plan.append(("brands", "id", 1))

    print("\n지워질 행:")
    for t, k, n in plan:
        print("   %-22s %s  %d행" % (t, k, n))

    if mids:
        print("\n🔴 **원가를 낸 메뉴가 %d개 있다** — 사람이 재료를 확인해 만든 작업물이다:" % len(mids))
        for r in c.execute("""SELECT name, sell_price sp, COALESCE(store_ratio,cost_ratio) sr
                              FROM menus WHERE brand_id=?""", (bid,)):
            print("     · %-24s %s원 · %s%%" % (r["name"][:24], r["sp"], r["sr"]))

    if not apply_:
        print("\n(미삭제 — 실제로 지우려면 --apply)")
        return
    if mids and not force:
        raise SystemExit("\n❌ 원가 낸 메뉴가 있어 지우지 않았다.\n"
                         "   정말 지우려면 --force 를 함께 줄 것.\n"
                         "   (메뉴만 살리고 싶으면 scripts/menu_delete.py 로 골라 지운다)")

    for t, k, n in plan:
        if k == "menu_id":
            c.execute("DELETE FROM %s WHERE menu_id IN (%s)"
                      % (t, ",".join("?" * len(mids))), mids)
        elif t == "brands":
            c.execute("DELETE FROM brands WHERE id=?", (bid,))
        else:
            c.execute("DELETE FROM %s WHERE brand_id=?" % t, (bid,))
        print("   %-22s %d행 지움" % (t, n))
    c.commit()

    left = c.execute("SELECT count(*) FROM brands WHERE id=?", (bid,)).fetchone()[0]
    print("\n✅ 지웠다 (남은 행 %d)" % left)
    print("\n다음을 반드시 돌릴 것 — 옛 페이지가 라이브에 남는다:")
    print("   python scripts/publish.py --apply")


if __name__ == "__main__":
    main()
