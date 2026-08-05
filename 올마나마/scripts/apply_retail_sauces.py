# -*- coding: utf-8 -*-
# 소스 → 시판 대체제(실제 쿠팡 판매 제품) 적용.
#  원칙: 대체제 있는 유형만 교체. 없는 유형(짬뽕·간장치킨·허니·갈릭·족발양념·국밥다대기·반미 등)은 미적용(배합 유지).
#  - ingredients.is_retail=1 로 시판제품 표시 → 렌더러가 "🛒 시판 소스로 간편하게 + 복사(쿠팡)"로 출력
#  - 가격은 2026-07 조사값 기준 원/kg 환산 (파트너스 링크 시 재확인 필요)
import sqlite3, re
DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

cols = {r[1] for r in cur.execute("PRAGMA table_info(ingredients)")}
if "is_retail" not in cols:
    cur.execute("ALTER TABLE ingredients ADD COLUMN is_retail INTEGER DEFAULT 0")
    print("+ 컬럼: ingredients.is_retail")

# (키, 표시명=쿠팡 검색어, 원/kg)  ※원/kg = 조사가격 ÷ 용량
PRODUCTS = [
    ("sauce_yangnyeom", "오뚜기 양념치킨소스 490g",        10200),  # 4,980/490g
    ("sauce_gochumayo", "코다노 고추마요소스 2kg",          4500),  # 9,000/2kg
    ("cheese_seasoning","아이엠소스 뿌링클링시즈닝 500g",   17500),  # 8,760/500g
    ("sauce_tteokbokki","곰곰 매콤 떡볶이 양념 500g",        9800),  # 4,900/500g
    ("sauce_rose",      "청정원 로제 스파게티소스 600g",     9970),  # 5,980/600g
    ("sauce_cream",     "청정원 베이컨앤크림 까르보나라소스 350g", 11400),  # 3,980/350g
    ("sauce_mala",      "하오츠 마라소스 180g",             22200),  # 3,990/180g
    ("sauce_jjajang",   "청정원 맛있는 중화 춘장 250g",      14000),  # 3,500/250g
    ("sauce_tangsu",    "백설 탕수육소스 270g",             13000),  # 3,500/270g
    ("sauce_bulgogi",   "청정원 소불고기양념장 500g",        11000),  # 5,480/500g
    ("sauce_jeyuk",     "청정원 요리한수 제육볶음양념 175g", 11400),  # 2,000/175g
    ("sauce_dakgalbi",  "샘표 춘천 닭갈비 양념 180g",        22100),  # 3,980/180g
    ("sauce_ssamjang",  "해찬들 고기전용 쌈장 500g",          9000),  # 4,500/500g
    ("sauce_budae",     "CJ 다담 부대찌개 양념 140g",        22900),  # 3,200/140g
    ("sauce_kimchi",    "CJ 다담 김치찌개 양념 140g",        22900),  # 3,200/140g
    ("sauce_donkatsu",  "오뚜기 돈까스소스 470g",             5200),  # 2,430/470g
    ("sauce_caesar",    "오뚜기 시저 드레싱 215g",           16300),  # 3,500/215g
    ("sauce_balsamic",  "오뚜기 레드와인 발사믹 드레싱 215g",14900),  # 3,200/215g
    ("sauce_oriental",  "오뚜기 정통 오리엔탈 드레싱 215g",  14900),  # 3,200/215g
    ("sauce_poke",      "오타후쿠 포케소스 300ml",           26700),  # 8,000/300ml
    ("sauce_nuoccham",  "친수 느억맘 소스 500g",              7400),  # 3,700/500g
    ("sauce_padthai",   "청정원 정통 팟타이소스 380g",       19200),  # 7,290/380g
    ("sauce_burger",    "하인즈 버거소스 230g",              10000),  # 2,310/230g
]
for k, n, p in PRODUCTS:
    if cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (k,)).fetchone():
        cur.execute("UPDATE ingredients SET name=?,manual_price=?,is_retail=1,class='가공품',type='manual',base_unit='kg' WHERE ingredient_key=?", (n, p, k))
    else:
        cur.execute("INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,base_unit,markup_factor,is_retail,updated_at)"
                    " VALUES(?,?,'가공품','manual',?,'kg',1.0,1,datetime('now'))", (k, n, p))
print(f"시판 제품 {len(PRODUCTS)}종 등록/갱신")

# composition(직접배합) 텍스트 → 시판 제품 매핑 규칙 (위에서부터 먼저 맞는 것)
#  ※ 대체제 없는 유형(짬뽕/간장치킨/허니/갈릭/족발/다대기/반미/소금/밥밑간 등)은 규칙에 없음 → 미적용
RULES = [
    (r"로제|투움바|토마토페이스트 · 생크림",        "sauce_rose"),
    (r"엽기 매운양념|국물떡볶이|신전 매운양념",     "sauce_tteokbokki"),
    (r"바질페스토|까르보|생크림 · 우유 · 버터|생크림 · 연유", "sauce_cream"),
    (r"두반장|화자오",                            "sauce_mala"),
    (r"춘장",                                     "sauce_jjajang"),
    (r"물전분",                                   "sauce_tangsu"),      # 탕수육/꿔바로우 부먹
    (r"돈까스소스",                               "sauce_donkatsu"),
    (r"쌈장",                                     "sauce_ssamjang"),
    (r"배즙",                                     "sauce_bulgogi"),     # 불고기 양념
    (r"카레가루",                                 "sauce_dakgalbi"),    # 닭갈비
    (r"제육|고추장 · 고춧가루 · 설탕 · 다진마늘 · 진간장 · 생강", "sauce_jeyuk"),
    (r"다대기.*육수|고춧가루 · 다진마늘 · 간장 · 고추장 · 후추", "sauce_budae"),
    (r"김치 · 고춧가루",                          "sauce_kimchi"),
    (r"시저드레싱",                               "sauce_caesar"),
    (r"발사믹",                                   "sauce_balsamic"),
    (r"오리엔탈드레싱",                           "sauce_oriental"),
    (r"포케소스",                                 "sauce_poke"),
    (r"느억짬",                                   "sauce_nuoccham"),
    (r"팟타이소스",                               "sauce_padthai"),
    (r"고추마요|마요네즈 · 스리라차",             "sauce_gochumayo"),
    (r"고추장 · 고춧가루 · 설탕 · 물엿 · 진간장 · 다진마늘", "sauce_tteokbokki"),  # 떡볶이 양념
    (r"고추장 · 토마토케첩|케첩 · 물엿|고추장 · 케첩", "sauce_yangnyeom"),  # 양념치킨
]
BURGER_CAT = "burger"

rows = cur.execute("""SELECT mi.id, mi.menu_id, mi.composition, c.slug cs, m.name mname, i.is_retail
    FROM menu_ingredients mi JOIN menus m ON mi.menu_id=m.id JOIN brands b ON m.brand_id=b.id
    JOIN categories c ON b.category_id=c.id JOIN ingredients i ON mi.ingredient_key=i.ingredient_key
    WHERE mi.composition IS NOT NULL AND mi.composition!=''""").fetchall()
applied = {}; skipped = 0
for r in rows:
    if r["is_retail"]:      # 이미 시판제품(제육 시연분 등)
        continue
    comp = r["composition"]; key = None
    if r["cs"] == BURGER_CAT:
        key = "sauce_burger"
    # 브랜드별 커스텀 양념(매콤강정·레드·볼케이노·맛초킹 등) → 시판 양념치킨소스가 대체제
    elif r["cs"] == "chicken" and "고추장" in comp:
        key = "sauce_yangnyeom"
    # 브랜드별 커스텀 떡볶이 양념(신전 매운양념·엽기 등) → 시판 떡볶이 양념
    elif r["cs"] == "bunsik" and "떡볶이" in (r["mname"] or "") and "고추장" in comp:
        key = "sauce_tteokbokki"
    else:
        for pat, k in RULES:
            if re.search(pat, comp):
                key = k; break
    if not key:
        skipped += 1; continue
    cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE id=?", (key, r["id"]))
    applied[key] = applied.get(key, 0) + 1
con.commit()
print(f"\n적용: {sum(applied.values())}줄 시판제품 교체 / 미적용(대체제 없음) {skipped}줄")
name = {k: n for k, n, _ in PRODUCTS}
for k, v in sorted(applied.items(), key=lambda x: -x[1]):
    print(f"  {v:>3}줄  {name.get(k,k)}")
con.close()
