# -*- coding: utf-8 -*-
# dish_data.py의 68종 → dish_def / dish_def_ingredient 로 이관 (2026-07-20)
#
# 이관 후에도 dish_data.py는 그대로 둔다 — gen_dishes가 "DB 우선 + 리터럴 폴백"이라
# 마이그레이션이 실패하거나 테이블이 비어도 68종은 계속 살아 있다.
#
#   python scripts/migrate_dishes_to_db.py          # 실행
#   python scripts/migrate_dishes_to_db.py --dry    # 뭐가 들어갈지만 보기
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dish_data as dd            # noqa: E402
import admin_store as st          # noqa: E402

DRY = "--dry" in sys.argv


def main():
    c = st.conn()
    st.init(c)
    cat_of = {n: cat for cat, names in dd.DISH_CAT.items() for n in names}
    n_d = n_i = 0
    for idx, (name, slug, serving, pattern, recipe) in enumerate(dd.DISHES):
        cat = cat_of.get(name)
        if not cat:
            print(f"  ⚠️ {name}: DISH_CAT에 없음 — 목록에서 고아가 된다")
        row = (slug, name, serving, pattern, cat, dd.ICON.get(name, "🍽️"), idx,
               json.dumps(list(dd.MAIN_KEYS.get(slug, ())), ensure_ascii=False),
               json.dumps(dd.MEALKIT.get(name), ensure_ascii=False) if name in dd.MEALKIT else None,
               "literal", 1, st.now(), st.now())
        if not DRY:
            c.execute("""INSERT INTO dish_def(slug,name,serving,match_pattern,category,icon,
                sort_order,main_keys_json,mealkit_json,source,active,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(slug) DO UPDATE SET
                  name=excluded.name, serving=excluded.serving, match_pattern=excluded.match_pattern,
                  category=excluded.category, icon=excluded.icon, sort_order=excluded.sort_order,
                  main_keys_json=excluded.main_keys_json, mealkit_json=excluded.mealkit_json,
                  updated_at=excluded.updated_at""", row)
            c.execute("DELETE FROM dish_def_ingredient WHERE slug=?", (slug,))
            for i, (k, a, u) in enumerate(recipe):
                c.execute("""INSERT INTO dish_def_ingredient(slug,ingredient_key,amount,unit,sort_order)
                    VALUES(?,?,?,?,?) ON CONFLICT(slug,ingredient_key) DO UPDATE SET
                      amount=excluded.amount, unit=excluded.unit""", (slug, k, a, u, i))
        n_d += 1; n_i += len(recipe)

    # PACK / SUBST도 테이블로
    n_p = n_s = 0
    if not DRY:
        for k, (qty, label) in dd.PACK.items():
            c.execute("""INSERT INTO ingredient_pack(ingredient_key,qty,label) VALUES(?,?,?)
                ON CONFLICT(ingredient_key) DO UPDATE SET qty=excluded.qty, label=excluded.label""",
                (k, qty, label)); n_p += 1
        for k, note in dd.SUBST.items():
            c.execute("""INSERT INTO ingredient_subst(ingredient_key,note) VALUES(?,?)
                ON CONFLICT(ingredient_key) DO UPDATE SET note=excluded.note""", (k, note)); n_s += 1
        c.commit()

    print(f"{'[DRY] ' if DRY else ''}요리 {n_d}종 · 재료줄 {n_i}건 · 포장 {n_p} · 대체안내 {n_s}")
    if not DRY:
        got = c.execute("SELECT count(*) FROM dish_def").fetchone()[0]
        gi = c.execute("SELECT count(*) FROM dish_def_ingredient").fetchone()[0]
        print(f"검증: dish_def {got}행 / dish_def_ingredient {gi}행")
    c.close()


if __name__ == "__main__":
    main()
