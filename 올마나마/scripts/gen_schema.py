# -*- coding: utf-8 -*-
# schema.sql을 **실제 DB에서** 다시 뽑는다 (2026-07-17)
#
# 🔴 왜 만들었나: schema.sql이 손으로 관리되다 실제 DB와 크게 벌어져 있었다.
#    HANDOFF에는 "D1 시딩 — data/eolmanama.db → D1 (schema.sql 기준)"이라 적혀 있는데,
#    그 schema.sql에는 다음이 **전부 빠져 있었다**:
#      · 테이블 4개: dishes, dish_ingredients, dish_menus, brand_origins  → 요리사전 35개가 통째로 죽는다
#      · ingredients: is_retail, wholesale_price, wholesale_basis
#      · menus: store_cost, store_ratio                                  → 매장 원가율(사이트 헤드라인)이 죽는다
#      · menu_ingredients: composition, wholesale_cost                    → 소스 배합·도매 단일출처가 죽는다
#      · brands: logo_rejected, logo_pending                              → 틀린 로고 재수집 가드가 죽는다
#    ALTER TABLE로 컬럼을 늘려온 게 schema.sql에 반영되지 않은 것. 손으로 맞추면 또 벌어진다.
#
# 사용법: python scripts/gen_schema.py   (스키마를 바꾼 뒤엔 반드시)
import sqlite3, os
from datetime import datetime, timezone

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "schema.sql")

con = sqlite3.connect(DB)
rows = con.execute("""SELECT type, name, sql FROM sqlite_master
    WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
    ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END, name""").fetchall()

head = f"""-- 얼마남아 (음식 원가 계산기) B2C DB 스키마
-- SQLite 로컬 개발 / Cloudflare D1 배포 공용
--
-- ⚠️ 이 파일은 **자동 생성**된다. 손으로 고치지 말 것.
--    실제 DB에서 뽑는다:  python scripts/gen_schema.py
--    손으로 관리하다 실제 DB와 벌어져서, D1에 시딩하면 요리사전(dish 4테이블)과
--    매장원가(store_cost/store_ratio) 등 11개 컬럼이 통째로 빠지는 상태였다(2026-07-17 발견).
--
-- 생성일: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} (UTC)
-- 구조: categories → brands → menus → menu_ingredients ← ingredients → price_history
--       dishes → dish_ingredients / dish_menus  (요리사전 축)
"""

body = ""
for typ, name, sql in rows:
    body += f"\n-- {typ}: {name}\n{sql.strip()};\n"

open(OUT, "w", encoding="utf-8").write(head + body)

tables = [r[1] for r in rows if r[0] == "table"]
print(f"schema.sql 재생성: 테이블 {len(tables)}개")
for t in tables:
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"   {t:20} 컬럼 {len(cols):>2}개 · 행 {n:>5}개")
con.close()
