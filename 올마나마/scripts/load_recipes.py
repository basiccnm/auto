# -*- coding: utf-8 -*-
# 레시피 로더: scratchpad/recipes_*.json → menus.recipe_steps (줄바꿈 join)
#  검증: 단계 수 3~5 권장(2~6 허용), 빈 단계 제거, menu_id 존재 확인, 누락 목록 출력
import sqlite3, json, glob, os

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SP = r"C:\Users\hardb\AppData\Local\Temp\claude\C--Users-hardb-Desktop--------------API\42c5a406-b4c6-4c3f-9036-4a06231e1eeb\scratchpad"

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
valid = {r[0] for r in cur.execute("SELECT id FROM menus")}

loaded = {}; bad = []
for fp in sorted(glob.glob(os.path.join(SP, "recipes_*.json"))):
    grp = os.path.basename(fp)[8:-5]
    try: data = json.load(open(fp, encoding="utf-8"))
    except Exception as e: print("ERR", fp, e); continue
    for it in data:
        mid = it.get("menu_id"); steps = [s.strip() for s in (it.get("steps") or []) if s and s.strip()]
        if mid not in valid: bad.append((grp, mid, "menu_id 없음")); continue
        if not (2 <= len(steps) <= 6): bad.append((grp, mid, f"단계수 {len(steps)}")); continue
        if any(len(s) > 90 for s in steps): steps = [s[:90] for s in steps]
        loaded[mid] = steps

for mid, steps in loaded.items():
    cur.execute("UPDATE menus SET recipe_steps=? WHERE id=?", ("\n".join(steps), mid))
con.commit()

missing = sorted(valid - set(loaded))
print(f"레시피 저장 {len(loaded)}개 / 전체 메뉴 {len(valid)} / 누락 {len(missing)} / 불량 {len(bad)}")
if missing: print("누락 menu_id:", missing[:40])
for g, m, w in bad[:15]: print(f"  불량[{g}] {m}: {w}")
# 백업(발행 자산)
out = {str(k): v for k, v in loaded.items()}
json.dump(out, open(os.path.join(BASE, "data", "research", "recipes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("백업: data/research/recipes.json")
con.close()
