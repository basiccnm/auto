# -*- coding: utf-8 -*-
# 도매(업소 공급가) 반영 — 매장 원가율 전환의 전제
#  1) ingredients에 wholesale_price / wholesale_basis 컬럼 추가
#  2) 우선순위: KAMIS 도매 실측(kamis) > 웹조사(researched) > 재료군 계수(estimated)
#  3) data/research/wholesale_prices.json 에 출처·근거 영구 저장
import sqlite3, json, glob, os, sys

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SP = r"C:\Users\hardb\AppData\Local\Temp\claude\C--Users-hardb-Desktop--------------API\42c5a406-b4c6-4c3f-9036-4a06231e1eeb\scratchpad"
OUT = os.path.join(BASE, "data", "research", "wholesale_prices.json")
DRY = "--dry" in sys.argv

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
cols = {r[1] for r in cur.execute("PRAGMA table_info(ingredients)")}
for c, t in (("wholesale_price", "INTEGER"), ("wholesale_basis", "TEXT")):
    if c not in cols:
        cur.execute(f"ALTER TABLE ingredients ADD COLUMN {c} {t}")
        print(f"  + 컬럼: ingredients.{c}")

# 재료군별 도매계수 (조사 실패분 폴백). 채소 0.52는 KAMIS 실측 기준.
def coef(key, name, cls, is_retail):
    n = name or ""
    if key in ("vegetables_fresh", "salad_greens"): return 0.52
    if key == "rice_uncooked": return 0.99          # KAMIS 실측: 쌀은 도소매 차이 거의 없음
    if is_retail: return 0.60                        # 시판소스 → 업소용 벌크
    if cls == "농축산물": return 0.70
    if any(w in n for w in ("생지", "번", "빵", "도우", "시트")): return 0.75
    return 0.70

# ── 1) KAMIS 도매 실측 (live 재료)
kamis = {}
latest = cur.execute("SELECT MAX(price_date) FROM price_history").fetchone()[0]
for r in cur.execute("""SELECT ingredient_key k, retail_price rp, wholesale_price wp FROM price_history
    WHERE price_date=? AND wholesale_price>0 AND retail_price>0""", (latest,)).fetchall():
    kamis[r["k"]] = r["wp"]

# ── 2) 웹조사 결과
researched = {}; items = []
for fp in sorted(glob.glob(os.path.join(SP, "whole_out_*.json"))):
    try: data = json.load(open(fp, encoding="utf-8"))
    except Exception as e: print("ERR", fp, e); continue
    for it in data:
        items.append(it)
        w = it.get("wholesale"); conf = (it.get("confidence") or "low").lower()
        if conf == "med": conf = "medium"
        if w and conf in ("high", "medium"): researched[it["key"]] = (w, it)

# ── 3) 적용
stats = {"kamis": 0, "researched": 0, "estimated": 0}
applied = []
for r in cur.execute("""SELECT ingredient_key k,name,class,type,manual_price,base_unit,COALESCE(is_retail,0) ir
    FROM ingredients""").fetchall():
    key = r["k"]
    # live 재료는 현재 소매시세, manual은 manual_price 기준
    if r["type"] in ("live", "live_composite"):
        h = cur.execute("""SELECT retail_price FROM price_history WHERE ingredient_key=? AND retail_price>0
            ORDER BY price_date DESC LIMIT 1""", (key,)).fetchone()
        retail = h["retail_price"] if h else (r["manual_price"] or 0)
    else:
        retail = r["manual_price"] or 0
    if not retail: continue

    if key in kamis:
        w, basis = kamis[key], "kamis"
    elif key in researched:
        w, basis = researched[key][0], "researched"
    else:
        w, basis = round(retail * coef(key, r["name"], r["class"], r["ir"])), "estimated"
    w = min(w, retail)   # 도매가 소매보다 클 수 없음
    if not DRY:
        cur.execute("UPDATE ingredients SET wholesale_price=?, wholesale_basis=? WHERE ingredient_key=?", (w, basis, key))
    stats[basis] += 1
    applied.append({"key": key, "name": r["name"], "retail": retail, "wholesale": w,
                    "ratio": round(w/retail, 2), "basis": basis})
if not DRY: con.commit()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"surveyed_at": "2026-07-17",
           "note": "매장(업소) 도매 공급가. basis=kamis(공공데이터 실측)/researched(도매몰 웹조사)/estimated(재료군 계수). "
                   "계수: 채소 0.52(KAMIS실측)·쌀 0.99·시판소스 0.60·농축산물 0.70·빵생지 0.75·기타 0.70",
           "research_items": items, "applied": applied},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"\n{'[DRY] ' if DRY else ''}도매가 적용: kamis {stats['kamis']} / 조사 {stats['researched']} / 계수추정 {stats['estimated']}")
print("\n[조사·실측 반영 (영향 큰 순)]")
imp = cur.execute("""SELECT i.ingredient_key k,i.name,i.wholesale_price w,i.wholesale_basis b,i.manual_price p,
    SUM(mi.line_cost) s FROM ingredients i JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key
    WHERE i.wholesale_basis IN ('kamis','researched') GROUP BY i.ingredient_key ORDER BY s DESC LIMIT 15""").fetchall()
for r in imp:
    print(f"  {r['name']:<22} 도매 {r['w']:>7,} ({r['b']})")
print(f"\n단가표: {OUT}")
con.close()
