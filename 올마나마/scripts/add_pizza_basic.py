# -*- coding: utf-8 -*-
# 피자 기본형(치즈·페퍼로니) 메뉴 등록 (2026-07-19)
#
# 왜: 홈 프랜차이즈 비교에서 피자만 고구마·포테이토·치즈후라이·슈프림이 섞여
#     "같은 걸 파는 다른 가게" 비교가 안 됐다. 브랜드마다 **기본형**을 넣어 통일한다.
#
# 가격 출처: 각 브랜드 **공식 홈페이지** 실확인 (2026-07-20).
#   도미노 web.dominos.co.kr / 피자헛 pizzahut.co.kr / 반올림 banolimpizza.com
#   파파존스 pji.co.kr / 청년피자 youngmanpizza.co.kr / 피자스쿨 pizzaschool.net
#
# 기준 결정(사용자 확정 2026-07-19 "없으면 대중적인 걸로"):
#   · 피자헛은 정가/배달/포장 3단 표기 → **정가** 사용. 다른 브랜드가 단일 정가라
#     포장가(13,900)를 쓰면 피자헛만 반값처럼 보여 비교가 왜곡된다.
#   · 파파존스는 순수 치즈피자가 없어 **마가리타**(토마토+치즈 = 가장 기본)를 치즈 자리에 둔다.
#   · 피자스쿨은 L 규격이 없어 단일 사이즈 그대로.
import os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# (브랜드명, 메뉴명, 판매가, 종류)  종류: cheese | pepperoni
ROWS = [
    ("도미노피자",   "치즈 피자 L",        23900, "cheese"),
    ("도미노피자",   "페퍼로니 피자 L",     25900, "pepperoni"),
    ("피자헛",       "치즈 러버 피자 L",    23900, "cheese"),
    ("피자헛",       "페페로니 러버 피자 L", 25900, "pepperoni"),
    ("반올림피자",   "치즈 피자 L",        21900, "cheese"),
    ("반올림피자",   "페퍼로니 피자 L",     21900, "pepperoni"),
    ("파파존스",     "마가리타 피자 L",     23500, "cheese"),
    ("파파존스",     "페퍼로니 피자 L",     25500, "pepperoni"),
    ("청년피자",     "리얼치즈 피자 L",     23900, "cheese"),
    ("청년피자",     "리얼페페로니 피자 L",  25900, "pepperoni"),
    ("피자스쿨",     "치즈피자",           8900,  "cheese"),
    ("피자스쿨",     "페퍼로니피자",        9900,  "pepperoni"),
]

# 재료 구성(추정) — 기존 피자 dish 레시피와 같은 뼈대. L 한 판 기준.
#  치즈형은 페퍼로니 없이 치즈를 더 쓰고, 페퍼로니형은 치즈를 조금 줄이고 페퍼로니를 얹는다.
#  ⚠️ 소요량은 공개 레시피 기반 **추정치**다(사이트 전역 고지와 동일 기준).
RECIPE = {
    "cheese":    [("pizza_dough", 350, "g"), ("mozzarella_cheese", 260, "g"),
                  ("pizza_sauce", 90, "g")],
    "pepperoni": [("pizza_dough", 350, "g"), ("mozzarella_cheese", 220, "g"),
                  ("pizza_sauce", 90, "g"), ("pepperoni", 60, "g")],
}
STEPS = ("도우를 펴고 가장자리를 살짝 두툼하게 만드세요\n"
         "피자소스를 도우 전체에 얇게 펴 바르세요\n"
         "모짜렐라 치즈를 고르게 덮으세요\n"
         "220도로 예열한 오븐에서 10~12분 구우세요\n"
         "치즈가 노릇하게 녹으면 꺼내 한 김 식히고 자르세요")

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
cat = cur.execute("SELECT id FROM categories WHERE slug='pizza'").fetchone()
added = skipped = 0
for bname, mname, price, kind in ROWS:
    b = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
    if not b:
        print(f"  ⚠️ 브랜드 없음: {bname} — 건너뜀"); continue
    if cur.execute("SELECT 1 FROM menus WHERE brand_id=? AND name=?", (b["id"], mname)).fetchone():
        skipped += 1; continue
    # slug는 기존 관행대로 m{id} — id를 받아야 하니 먼저 빈 slug로 넣고 갱신한다.
    cur.execute("""INSERT INTO menus(brand_id,name,slug,sell_price,source,recipe_steps,sort_order,created_at)
        VALUES(?,?,'',?,?,?,0,datetime('now'))""", (b["id"], mname, price, "브랜드 공식 홈페이지(2026-07-20 확인)", STEPS))
    mid = cur.lastrowid
    cur.execute("UPDATE menus SET slug=? WHERE id=?", (f"m{mid}", mid))
    for key, amt, unit in RECIPE[kind]:
        if not cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (key,)).fetchone():
            print(f"  ⚠️ 재료 없음: {key}"); continue
        cur.execute("""INSERT INTO menu_ingredients(menu_id,ingredient_key,amount,unit)
            VALUES(?,?,?,?)""", (mid, key, amt, unit))
    added += 1
con.commit()
print(f"등록 {added}개 · 이미 있어 건너뜀 {skipped}개")
con.close()
