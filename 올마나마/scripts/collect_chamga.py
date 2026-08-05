# -*- coding: utf-8 -*-
# 참가격(한국소비자원) 가공식품 소비자가 수집 → cg_* 재료 갱신 (2026-07-18)
#
#  · 코드/포장중량 출처: publicdata/catalog.py 의 CHAMGA_ITEMS (chamga_goods.tsv에서 발췌·검증)
#  · 참가격은 '포장 1개 가격' → pack(중량/용량)으로 나눠 kg/L 단가로 환산
#  · 소비자가(소매)만 제공 → wholesale은 NULL. type=live, is_retail=1(시판)
#  · '먹는 것'만 (사용자 지시 2026-07-18): CHAMGA_ITEMS가 이미 식품 20종뿐
#
# 사용법: python scripts/collect_chamga.py   (매일 시세 갱신 파이프라인에 포함)
import sys, os, datetime, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publicdata import chamgagyeok as cg
from publicdata.catalog import CHAMGA_ITEMS

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eolmanama.db")
con = sqlite3.connect(DB); cur = con.cursor()

# 참가격은 주간 조사 — 최근 데이터 있는 조사일 1회만 탐색(첫 품목으로 프로브)
today = datetime.date.today()
day = cg.find_recent_inspect_day(CHAMGA_ITEMS[0][2], today, lookback_days=45)
if not day:
    print("❌ 참가격 조사일을 못 찾음 (API 무응답/차단?) — 갱신 중단"); sys.exit(1)

ok, fail = 0, []
for key, name, gid, pack, unit in CHAMGA_ITEMS:
    med = cg.median(cg.fetch_good(gid, day))
    if not med:
        fail.append(name); continue
    per = round(med / pack)                     # 포장 1개 → kg/L 단가
    ikey = "cg_" + key
    cur.execute("""INSERT OR REPLACE INTO ingredients
      (ingredient_key,name,class,type,chamgagyeok_key,manual_price,base_unit,markup_factor,updated_at,is_retail,wholesale_price,wholesale_basis)
      VALUES(?,?,?,?,?,?,?,?,datetime('now'),?,?,?)""",
      (ikey, name, "가공품", "live",
       json.dumps({"goodId": gid, "pack": pack}, ensure_ascii=False),
       per, unit, 1.0, 1, None, None))
    try:
        cur.execute("INSERT OR REPLACE INTO price_history(ingredient_key,price_date,retail_price) VALUES(?,?,?)",
                    (ikey, day, per))
    except sqlite3.Error:
        pass
    ok += 1

con.commit()
print(f"참가격 {day} 갱신: {ok}종" + (f" · 실패 {len(fail)}: {fail}" if fail else ""))
con.close()
