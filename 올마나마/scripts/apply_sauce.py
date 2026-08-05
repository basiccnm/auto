# -*- coding: utf-8 -*-
# sauce_data.py 큐레이션을 menu_ingredients.composition 에 반영.
#  - composition 컬럼 없으면 추가.
#  - 소스 재료줄마다: MID_OVERRIDE(mid) 우선 → MENU_COMP(menu_id) → 없으면 NULL(블록 미표시).
import sqlite3, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sauce_data import MENU_COMP, MID_OVERRIDE

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SAUCE = ('sauce_honey', 'sauce_normal', 'malatang_base', 'pizza_sauce', 'jajang_paste')

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
cols = {r[1] for r in cur.execute("PRAGMA table_info(menu_ingredients)")}
if "composition" not in cols:
    cur.execute("ALTER TABLE menu_ingredients ADD COLUMN composition TEXT")
    print("+ 컬럼 추가: menu_ingredients.composition")

rows = cur.execute(f"""SELECT mi.id mid, mi.menu_id, m.name mname, b.name bn
    FROM menu_ingredients mi JOIN menus m ON mi.menu_id=m.id JOIN brands b ON m.brand_id=b.id
    WHERE mi.ingredient_key IN ({','.join('?'*len(SAUCE))}) ORDER BY mi.id""", SAUCE).fetchall()

set_n = hide_n = 0
hidden = []
for r in rows:
    if r["mid"] in MID_OVERRIDE:
        comp = MID_OVERRIDE[r["mid"]]
    else:
        comp = MENU_COMP.get(r["menu_id"], "__MISSING__")
    if comp == "__MISSING__":
        # 큐레이션 누락 → 건드리지 않고 경고
        hidden.append(f'  ⚠ 누락 menu_id={r["menu_id"]} {r["bn"]} {r["mname"]}')
        continue
    cur.execute("UPDATE menu_ingredients SET composition=? WHERE id=?", (comp, r["mid"]))
    if comp is None:
        hide_n += 1; hidden.append(f'  (숨김) {r["bn"]} {r["mname"]}')
    else:
        set_n += 1
con.commit()
print(f"\n적용: 배합표시 {set_n}줄 / 의도적숨김 {hide_n}줄 / 큐레이션누락 {len([h for h in hidden if '누락' in h])}줄")
if hidden:
    print("\n[숨김·누락 목록]")
    print("\n".join(hidden))
con.close()
