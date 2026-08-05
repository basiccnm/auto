# -*- coding: utf-8 -*-
# 오매핑 교정 (2026-07-17) — healthcheck의 "메뉴명이 말하는 재료가 없음" 검출 결과
#  근거가 명확한 것만 고친다. 메뉴명/레시피가 스스로 증언하는 건들.
#  단가 출처: data/research/missing_ingredient_prices.json (전부 B2B 도매 실측, confidence high)
#  ❌ 안 고친 것: 감자핫도그·고구마통모짜·버섯소불고기 → 아래 SKIP 참조
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
DRY = os.environ.get("DRY") == "1"

# ── 1) 없는 재료 신규 등록 (B2B 도매 실측가)
NEW = [
    ("x_siraegi",       "삶은 시래기",      3550,  "농축산물", "kg"),
    ("x_cream_cheese",  "크림치즈",        13350, "가공품",   "kg"),
    ("x_chadol",        "차돌박이(수입 냉동)", 17580, "농축산물", "kg"),
    ("x_chicken_neck",  "닭목살(수입 냉동)",  2917,  "농축산물", "kg"),
]
for key, name, price, klass, unit in NEW:
    if cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (key,)).fetchone():
        cur.execute("UPDATE ingredients SET name=?, manual_price=? WHERE ingredient_key=?", (name, price, key))
        print(f"  갱신: {name} {price:,}원/{unit}")
    else:
        cur.execute("""INSERT INTO ingredients (ingredient_key,name,class,type,manual_price,base_unit,markup_factor)
            VALUES (?,?,?,'manual',?,?,1.0)""", (key, name, klass, price, unit))
        print(f"  + 신규: {name} {price:,}원/{unit}")

# ── 2) 재료 교체 (menu_id, 기존키 → 새키, 사유)
#  ⚠️ **양(amount/unit)은 절대 건드리지 않는다.** 재료 품목만 바꾼다.
#     양을 바꿀 근거는 없다. 재료가 틀렸다는 근거와 양이 틀렸다는 근거는 별개다.
#     (초안에서 새우 30g→60g, 차돌 80g→60g으로 무심코 바꿨다가 DRY에서 잡힘)
SWAP = [
    (541, "vegetables_fresh", "x_siraegi",
     "3대시래기국에 시래기가 없고 '신선 채소'(=양파·파·양배추 지수)가 들어 있었다. "
     "브랜드가 순남시래기이고 레시피도 '삶은 시래기 120g'이라고 명시. 재료표만 딴소리."),
    (344, "milk", "x_cream_cheese",
     "크림치즈호두김밥에 크림치즈가 없고 우유가 들어 있었다. 레시피는 '크림치즈를 부드럽게 풀어'라고 명시."),
    (391, "chicken_boneless", "x_chicken_neck",
     "닭목살덮밥인데 닭다리살. 닭목살은 별도 부위로 정상 유통(태국산 냉동 2,917/kg)."),
    (339, "seafood_mix", "shrimp_meat",
     "새우김밥인데 해물믹스. 새우살 재료가 이미 있는데도 쓰지 않았다."),
    # 차돌 3건: 차돌박이 ≠ 우삼겹(업진살). 레시피의 '차돌(우삼겹)'은 우리가 만든 근사표기였다.
    (29,  "beef_slices", "x_chadol", "불향차돌떡볶이 — 차돌박이는 우삼겹과 다른 부위(양지머리 vs 업진살)"),
    (511, "beef_slices", "x_chadol", "차돌쌀국수 — 〃"),
    (538, "beef_slices", "x_chadol", "차돌육개장 — 〃"),
]
for mid, old, new, why in SWAP:
    row = cur.execute("SELECT id, amount, unit FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                      (mid, old)).fetchone()
    if not row:
        print(f"  ⚠️ [{mid}] {old} 줄이 없음 — 건너뜀(이미 교정됐거나 데이터가 바뀜)")
        continue
    nm = cur.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()[0]
    cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE id=?", (new, row["id"]))
    print(f"  [{mid}] {nm}: {old} → {new}  (양 {row['amount']:g}{row['unit']} 유지)")

# ── 3) 레시피 문구 교정 (우리가 만든 근사표기 제거)
RECIPE = [
    (511, "차돌(우삼겹) 100g", "차돌박이 100g"),
    (29,  "우삼겹 150g",       "차돌박이 150g"),
    (339, "새우(해물 믹스)",    "새우살"),
    (391, "닭다리살 160g",      "닭목살 160g"),
]
for mid, old, new in RECIPE:
    r = cur.execute("SELECT recipe_steps FROM menus WHERE id=?", (mid,)).fetchone()
    if r and r["recipe_steps"] and old in r["recipe_steps"]:
        cur.execute("UPDATE menus SET recipe_steps=? WHERE id=?", (r["recipe_steps"].replace(old, new), mid))
        print(f"  레시피 [{mid}]: '{old}' → '{new}'")

if DRY:
    con.rollback(); print("\n[DRY] 롤백함")
else:
    con.commit(); print("\n커밋 완료")

# ── 안 고친 것 (근거 부족 — 지어내지 않는다)
print("""
❌ 근거 부족으로 손대지 않은 것:
  [554] 명랑핫도그 감자핫도그  — 재료에도 레시피에도 감자가 없다. 레시피 자체가 일반 핫도그.
        감자 큐브가 붙는 형태로 추정되나 공식 구성·중량 근거를 못 찾음 → 감자 g을 지어낼 수 없음
  [555] 명랑핫도그 고구마통모짜 — 레시피가 '고구마맛 빵 반죽'이라 별도 고구마 재료가 없는 게 맞을 수 있음
  [383] 본도시락 버섯소불고기  — 레시피 '버섯과 채소 120g'. 버섯/채소 배분 g의 근거가 없어 분리 불가
        (마라탕·보쌈 채소와 동일한 문제)
""")
con.close()
