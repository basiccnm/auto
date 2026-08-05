# -*- coding: utf-8 -*-
# 돼지고기 오매핑 교정 2차 (2026-07-17) — 공식 원산지표로 확정된 것만
#  근거: data/research/pork_mismap_audit.json
#  ⚠️ 재료 품목만 바꾸고 **양은 절대 건드리지 않는다**(1차에서 무심코 양을 바꿨다가 DRY에서 잡힘).
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
DRY = os.environ.get("DRY") == "1"

# ── 항정살 신규 (수입 냉동 B2B 중앙값 16,000/kg — 미트박스 실거래 13,000~19,000)
#  삼겹살(마리당 7~8kg)과 달리 항정살은 마리당 500g~1kg뿐이라 구조적으로 1.3~1.6배 비싸다.
#  ⚠️ 국산 냉장 항정살은 32,000~40,000/kg이니 섞지 말 것. 프랜차이즈는 수입·냉동·벌크.
if not cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key='x_hangjeong'").fetchone():
    cur.execute("""INSERT INTO ingredients (ingredient_key,name,class,type,manual_price,base_unit,markup_factor)
        VALUES ('x_hangjeong','항정살(수입 냉동)','농축산물','manual',16000,'kg',1.0)""")
    print("  + 신규: 항정살(수입 냉동) 16,000원/kg")

# (menu_id, 기존키 → 새키, 근거)
SWAP = [
    (58, "pork_belly_import", "x_0ebb70edeb",
     "맥도날드 1955 버거 — 공식 원산지표에 '베이컨_돼지고기: 외국산(아일랜드/스페인/캐나다)' 명시. 삼겹살 원육 아님"),
    (34, "pork_belly_import", "x_0ebb70edeb",
     "도미노 포테이토 피자 — 공식 원산지표에 '포테이토 — 베이컨(돼지고기:외국산)'. 이 피자의 유일한 육류 토핑이 베이컨"),
    (395, "pork_belly_import", "x_hangjeong",
     "핵밥 매운항정살덮밥 — 메뉴명이 항정살. 삼겹살(복부)과 완전히 다른 부위(목덜미살). 삼겹 단가는 30~55% 과소계상"),
]
for mid, old, new, why in SWAP:
    row = cur.execute("SELECT id, amount, unit FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                      (mid, old)).fetchone()
    if not row:
        print(f"  ⚠️ [{mid}] {old} 줄 없음 — 건너뜀")
        continue
    nm = cur.execute("SELECT m.name, b.name bn FROM menus m JOIN brands b ON m.brand_id=b.id WHERE m.id=?", (mid,)).fetchone()
    cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE id=?", (new, row["id"]))
    print(f"  [{mid}] {nm['bn']} {nm['name']}: {old} → {new}  (양 {row['amount']:g}{row['unit']} 유지)")

# 레시피에서 우리가 만든 근사표기 제거
for mid, old, new in [(395, "항정살(삼겹) 160g", "항정살 160g")]:
    r = cur.execute("SELECT recipe_steps FROM menus WHERE id=?", (mid,)).fetchone()
    if r and r["recipe_steps"] and old in r["recipe_steps"]:
        cur.execute("UPDATE menus SET recipe_steps=? WHERE id=?", (r["recipe_steps"].replace(old, new), mid))
        print(f"  레시피 [{mid}]: '{old}' → '{new}'")

if DRY:
    con.rollback(); print("\n[DRY] 롤백함")
else:
    con.commit(); print("\n커밋 완료")

print("""
❌ 근거 없어 손대지 않은 것:
  [48] 빽보이피자 울트라빽보이 L — ⚠️ **더본코리아 공식 라인업 13종에 이 메뉴가 없다(단종 의심)**.
        삼겹살 80g 근거 전무. 3자 배달몰상 베이스는 '매콤불고기: 돼지고기(국내산)' = 수입도 삼겹살도 아님.
        → 부위 교정이 아니라 '메뉴를 유지할지'부터 결정해야 함
  [394] 핵밥 고기듬뿍덮밥 — 항정살덮밥과 별개 메뉴(10,900 vs 11,900)인데 같은 부위로 묶여 있었다.
        실제 부위 공식 근거 없음 → 추측 금지 (소대창→돼지등심 사고와 같은 유형)
""")
con.close()
