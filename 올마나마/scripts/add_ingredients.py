# -*- coding: utf-8 -*-
# 신규 재료 일괄 등록 (2026-07-20)
#
# 레시피가 부르는데 DB에 없는 재료를 등록한다. 관리페이지의 '신규 재료 등록' 폼이
# 나중에 같은 함수를 부르게 만들 예정이라, 로직을 여기 한 곳에만 둔다.
#
# 각 항목에 반드시 있어야 하는 것:
#   key/name/class/base_unit/manual_price  — 없으면 원가가 0으로 나온다
#   pack(qty,label)                        — 없으면 장보기 금액이 기본값 0.5kg으로 틀어진다
#   alias                                  — 레시피가 쓰는 다른 표기를 미리 이어둔다
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import admin_store as st                    # noqa: E402
from recipe_mapping import normalize        # noqa: E402


def add(spec, log=print):
    """spec: list of dict. 이미 있으면 가격만 갱신한다."""
    c = st.conn()
    st.init(c)
    n_new = n_upd = 0
    for s in spec:
        exists = c.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (s["key"],)).fetchone()
        c.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,
            wholesale_price,wholesale_basis,base_unit,markup_factor,is_retail,subcat,origin,updated_at)
            VALUES(?,?,?,'manual',?,?,?,?,1.0,?,?,?,?)
            ON CONFLICT(ingredient_key) DO UPDATE SET
              manual_price=excluded.manual_price,
              wholesale_price=COALESCE(excluded.wholesale_price, ingredients.wholesale_price),
              wholesale_basis=excluded.wholesale_basis, subcat=excluded.subcat,
              updated_at=excluded.updated_at""",
            (s["key"], s["name"], s.get("class", "가공품"), s["price"],
             s.get("wholesale"), "researched" if s.get("wholesale") else None,
             s.get("unit", "kg"), s.get("is_retail", 1), s.get("subcat"),
             s.get("origin"), st.now()))
        if s.get("pack"):
            qty, label = s["pack"]
            c.execute("""INSERT INTO ingredient_pack(ingredient_key,qty,label) VALUES(?,?,?)
                ON CONFLICT(ingredient_key) DO UPDATE SET qty=excluded.qty, label=excluded.label""",
                (s["key"], qty, label))
        if s.get("subst"):
            c.execute("""INSERT INTO ingredient_subst(ingredient_key,note) VALUES(?,?)
                ON CONFLICT(ingredient_key) DO UPDATE SET note=excluded.note""",
                (s["key"], s["subst"]))
        for a in s.get("alias", []):
            c.execute("""INSERT INTO ingredient_alias(alias_norm,alias_raw,ingredient_key,source,created_at)
                VALUES(?,?,?,'human',?) ON CONFLICT(alias_norm) DO UPDATE SET
                  ingredient_key=excluded.ingredient_key""",
                (normalize(a), a, s["key"], st.now()))
        if exists:
            n_upd += 1
        else:
            n_new += 1
        log(f"  {'갱신' if exists else '신규'} {s['name']:22s} {s['price']:>8,}원/{s.get('unit','kg')}"
            + (f" · 도매 {s['wholesale']:,}" if s.get("wholesale") else "")
            + (f" · {s['pack'][1]}" if s.get("pack") else ""))
    c.commit()
    c.close()
    log(f"신규 {n_new}종 · 갱신 {n_upd}종")
    return n_new, n_upd


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("사용법: python scripts/add_ingredients.py <spec.json>")
        sys.exit(1)
    add(json.load(open(sys.argv[1], encoding="utf-8")))
