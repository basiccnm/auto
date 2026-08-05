# -*- coding: utf-8 -*-
# 치킨 브랜드 기본 메뉴(후라이드·양념) 등록 (2026-07-20)
#
# 왜: 치킨 21개 브랜드 중 10곳이 메뉴 0개였고, 있는 곳도 기본 후라이드/양념이 빠져 있었다.
#     "교촌치킨 후라이드"처럼 없는 메뉴를 만들면 안 되므로 **미판매는 미판매로 둔다**.
#
# 🔴 가격은 조사로 확인된 것만 넣는다. 확인 불가·신뢰도 낮음은 **등록하지 않는다**.
#    (틀린 판매가는 원가율을 통째로 틀리게 만든다 — 사이트 신뢰의 근간)
import os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# (브랜드, 메뉴명, 판매가, 종류, 출처메모)  종류: fried | yangnyeom
#  전부 2026-07-20 조사. 공식 홈페이지 확인분만 채택했다.
ROWS = [
    ("BBQ치킨",       "BBQ 양념치킨",      24500, "yangnyeom", "공식 m.bbq.co.kr"),
    ("bhc치킨",       "후라이드치킨",        20000, "fried",     "가격인상 보도(서울경제)"),
    ("bhc치킨",       "양념치킨",           21000, "yangnyeom", "가격인상 보도(서울경제)"),
    ("가마로강정",     "순살후라이드(싱글)",   14000, "fried",     "공식 gamaro.co.kr · 포장 기준"),
    ("굽네치킨",       "New 오리지널",       17900, "fried",     "공식 goobne.co.kr · 오븐구이"),
    ("굽네치킨",       "양념 히어로",        19900, "yangnyeom", "공식 goobne.co.kr"),
    ("처갓집양념치킨",  "후라이드치킨",        19000, "fried",     "공식 cheogajip.co.kr"),
    # 2차 조사분 (공식 홈페이지 확인)
    ("네네치킨",       "후라이드",           20000, "fried",     "공식 nenechicken.com"),
    ("네네치킨",       "양념치킨",           22000, "yangnyeom", "공식 nenechicken.com"),
    ("노랑통닭",       "엄청 큰 양념 치킨",    23000, "yangnyeom", "공식 norangtongdak.co.kr"),
    ("멕시카나치킨",   "후라이드치킨",        19000, "fried",     "공식 mexicana.co.kr · 뼈 기준"),
    ("멕시카나치킨",   "양념치킨",           21000, "yangnyeom", "공식 mexicana.co.kr · 뼈 기준"),
    ("바른치킨",       "현미후라이드",        19900, "fried",     "공식 barunchicken.com · 뼈 기준"),
    ("바른치킨",       "양념치킨",           21900, "yangnyeom", "공식 barunchicken.com · 뼈 기준"),
    # 3차 조사분 (공식 홈페이지 확인)
    #  ★ 교촌은 '후라이드한마리'·'양념치킨한마리'를 실제로 판다 — 미판매로 알았던 게 사실이 아니었다.
    ("교촌치킨",       "후라이드한마리",       21000, "fried",     "공식 kyochon.com"),
    ("교촌치킨",       "양념치킨한마리",       22000, "yangnyeom", "공식 kyochon.com"),
    ("푸라닭치킨",     "씬 후라이드",         19900, "fried",     "공식 puradakchicken.com"),
    ("푸라닭치킨",     "달콤양념 치킨",       21900, "yangnyeom", "공식 puradakchicken.com"),
]
# ⛔ 등록하지 않은 브랜드 — 공식 가격 미공개이거나 출처 신뢰도가 낮아 값을 확정할 수 없다.
#    60계·또래오래·보드람·순수·자담·페리카나·호식이·훌랄라 (2026-07-20 조사).
#    블로그 정리글 수치는 상충하는 값이 많아 채택하지 않았다. 추측으로 채우면 원가율이 통째로 틀어진다.

# 재료 구성(추정) — 기존 치킨 메뉴와 같은 뼈대.
#  ⚠️ 튀김기름은 **흡수분만** 넣는다. 냄비에 붓는 1.5L를 넣으면 원가가 3배로 뛴다.
RECIPE = {
    "fried":     [("raw_chicken_10", 1, "kg"), ("frying_powder", 200, "g"),
                  ("frying_oil", 140, "ml"), ("sidedish_set", 1, "개")],
    "yangnyeom": [("raw_chicken_10", 1, "kg"), ("frying_powder", 200, "g"),
                  ("frying_oil", 140, "ml"), ("sauce_yangnyeom", 180, "g"),
                  ("sidedish_set", 1, "개")],
}
STEPS = {
    "fried": ("염지닭을 토막 내 물기를 제거하세요\n"
              "튀김가루 절반은 물에 개어 반죽, 절반은 덧가루로 입히세요\n"
              "170도 기름에 10분 튀긴 뒤 건져 기름을 빼세요\n"
              "180도로 올려 2분 더 튀겨 겉을 바삭하게 만드세요"),
    "yangnyeom": ("염지닭을 토막 내 튀김가루 옷을 입히세요\n"
                  "170도에서 10분, 180도에서 2분 두 번 튀기세요\n"
                  "팬에 양념소스를 데워 향을 내세요\n"
                  "튀긴 닭을 소스에 재빨리 버무려 윤기를 입히세요"),
}


def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
    added = skipped = 0
    for bname, mname, price, kind, src in ROWS:
        b = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
        if not b:
            print(f"  ⚠️ 브랜드 없음: {bname}"); continue
        if cur.execute("SELECT 1 FROM menus WHERE brand_id=? AND name=?", (b["id"], mname)).fetchone():
            skipped += 1; continue
        cur.execute("""INSERT INTO menus(brand_id,name,slug,sell_price,source,recipe_steps,sort_order,created_at)
            VALUES(?,?,'',?,?,?,0,datetime('now'))""",
            (b["id"], mname, price, f"{src} (2026-07-20 확인)", STEPS[kind]))
        mid = cur.lastrowid
        cur.execute("UPDATE menus SET slug=? WHERE id=?", (f"m{mid}", mid))
        for key, amt, unit in RECIPE[kind]:
            if not cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (key,)).fetchone():
                print(f"  ⚠️ 재료 없음: {key}"); continue
            cur.execute("INSERT INTO menu_ingredients(menu_id,ingredient_key,amount,unit) VALUES(?,?,?,?)",
                        (mid, key, amt, unit))
        added += 1
        print(f"  + {bname} {mname} {price:,}원")
    con.commit(); con.close()
    print(f"등록 {added}개 · 이미 있어 건너뜀 {skipped}개")


if __name__ == "__main__":
    main()
