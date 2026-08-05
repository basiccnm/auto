# 2차 딥리서치 파일에서 재료표(키코드·이름·단가) 파싱 → ingredients 시드 SQL 생성
# 매핑(live/manual, KAMIS 코드)은 아래 MAP 딕셔너리로 코드에서 결정.
import json, re, sys

SRC = r"C:\Users\hardb\.claude\projects\C--Users-hardb-Desktop--------------API\d7b5e9fe-4fa7-44ab-9652-0407db96dfda\tool-results\mcp-80c2493c-7e1d-4dd3-8de1-3542f548ed2c-read_file_content-1784140413634.txt"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\seed_ingredients.sql"

# 키코드 → 매핑. (type, kamis_cat, kamis_item_code, composite, markup)
# live: KAMIS 직접 / live_composite: 가중평균 / manual: 고정값
MAP = {
    # ── 농축산물 live (KAMIS) ──
    "raw_chicken_10":    ("live", "500", "9901", None, 1.15),  # 닭 절단육 + 염지 마크업
    "chicken_parts":     ("live", "500", "9901", None, 1.25),  # 부분육
    "chicken_boneless":  ("live", "500", "9901", None, 1.20),
    "pork_trotter":      ("live", "500", "4304", None, 1.10),  # 돼지 근사
    "pork_belly_import": ("live", "500", "4402", None, 1.00),  # 수입돼지 삼겹 정확
    "pork_loin_tangsuyuk":("live","500", "4304", None, 1.00),
    "pork_loin_donkasu": ("live", "500", "4304", None, 1.05),
    "beef_patty":        ("live", "500", "4401", None, 1.00),  # 수입소
    "beef_slices":       ("live", "500", "4401", None, 1.05),
    "beef_stew":         ("live", "500", "4301", None, 1.00),  # 국산소
    "egg_fresh":         ("live", "500", "9903", None, 1.00),  # 계란
    "rice_uncooked":     ("live", "100", "111",  None, 1.00),  # 쌀
    # ── 농축산물 live_composite (야채 지수) ──
    # 245=양파 · 246=파 · 212=양배추 (KAMIS 채소류 200. 코드표: data/research/kamis_item_codes.json)
    # ⚠️ 이 3품목 평균이라 '일반 볶음/토핑 채소'에는 맞지만, 보쌈 쌈채소(배추·무)나
    #    마라탕 채소(청경채·숙주)에 쓰면 품목 자체가 다르다. 양 많은 메뉴는 실채소로 분리할 것.
    "vegetables_fresh":  ("live_composite", None, None,
                          [{"code":"245","w":0.4},{"code":"246","w":0.3},{"code":"212","w":0.3}], 1.0),
    "salad_greens":      ("live", "200", "214", None, 1.30),  # 상추 근사 + 프리미엄
    # ── 농축산물 manual (수산 미조회) ──
    "seafood_mix":       ("manual", None, None, None, 1.0),
    "salmon_raw":        ("manual", None, None, None, 1.0),
    "white_fish_raw":    ("manual", None, None, None, 1.0),
    # ── 가공품 manual (참가격 승격 후보 포함) ──
    "mozzarella_cheese": ("manual", None, None, None, 1.0),
    "tteok":             ("manual", None, None, None, 1.0),
    "fish_cake":         ("manual", None, None, None, 1.0),
    "vienna_sausage":    ("manual", None, None, None, 1.0),
    "spam_ham_mix":      ("manual", None, None, None, 1.0),
    "frying_powder":     ("manual", None, None, None, 1.0),
    "frying_oil":        ("manual", None, None, None, 1.0),
    "pizza_dough":       ("manual", None, None, None, 1.0),
    "pizza_sauce":       ("manual", None, None, None, 1.0),
    "sauce_honey":       ("manual", None, None, None, 1.0),
    "sauce_normal":      ("manual", None, None, None, 1.0),
    "malatang_base":     ("manual", None, None, None, 1.0),
    "tofu_noodles":      ("manual", None, None, None, 1.0),
    "jajang_paste":      ("manual", None, None, None, 1.0),
    "noodles_fresh":     ("manual", None, None, None, 1.0),
    "noodles_rice":      ("manual", None, None, None, 1.0),
    "noodles_ramen":     ("manual", None, None, None, 1.0),
    "burger_bun":        ("manual", None, None, None, 1.0),
}

def clean(s):
    return s.replace("*", "").replace("\\", "").strip()

d = json.load(open(SRC, encoding="utf-8"))
t = d["fileContent"]

rows = []
for line in t.split("\n"):
    if line.count("|") < 5:
        continue
    cells = [clean(c) for c in line.split("|")]
    # 재료표 행: [ , 분류(농축산물/가공품), 키코드, 이름, 단가, 비고, ]
    if len(cells) < 6:
        continue
    cls, key, name, price = cells[1], cells[2], cells[3], cells[4]
    if cls not in ("농축산물", "가공품"):
        continue
    if not re.match(r"^[a-z][a-z0-9_]+$", key):
        continue
    # 단가에서 숫자 추출 + 단위 (원/kg, 원/L, 원/개)
    m = re.search(r"([\d,]+)\s*원\s*/\s*(kg|L|개|세트|ml|g)", price)
    won = int(m.group(1).replace(",", "")) if m else None
    unit = m.group(2) if m else "kg"
    rows.append((key, name, cls, won, unit))

# SQL 생성
out = ["-- 얼마남아 재료 마스터 시드 (2차 딥리서치 재료표 파싱 + 매핑)", "-- 자동생성: gen_ingredients_seed.py", ""]
seen = set()
mapped = 0
for key, name, cls, won, unit in rows:
    if key in seen:
        continue
    seen.add(key)
    mp = MAP.get(key)
    if mp:
        typ, kcat, kcode, comp, markup = mp
        mapped += 1
    else:
        typ, kcat, kcode, comp, markup = "manual", None, None, None, 1.0
    base_unit = "L" if unit == "L" else ("개" if unit in ("개", "세트") else "kg")
    comp_json = json.dumps(comp, ensure_ascii=False) if comp else None
    manual_price = won if typ == "manual" else None

    def q(v):
        return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"

    out.append(
        "INSERT INTO ingredients (ingredient_key,name,class,type,kamis_cat,kamis_item_code,"
        "composite_formula,manual_price,base_unit,markup_factor,updated_at) VALUES "
        f"({q(key)},{q(name)},{q(cls)},{q(typ)},{q(kcat)},{q(kcode)},{q(comp_json)},"
        f"{manual_price if manual_price is not None else 'NULL'},{q(base_unit)},{markup},datetime('now'));"
    )

open(OUT, "w", encoding="utf-8").write("\n".join(out))
print(f"파싱된 재료: {len(seen)}종, 매핑 적용: {mapped}종, 미매핑(manual기본): {len(seen)-mapped}종")
print(f"저장: {OUT}")
