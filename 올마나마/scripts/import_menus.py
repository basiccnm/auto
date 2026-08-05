# 1차 메뉴 데이터(menu_1cha.txt) → menus + menu_ingredients 임포트
# - 브랜드명 정규화 매칭 (BBQ→BBQ치킨). 브랜드 미매칭(홈페이지 없음)이면 메뉴 제외.
# - 재료명 → 키코드 별칭 매핑. Gemini 제공 라인 단가(괄호값) 파싱.
import re, sqlite3, os

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "menu_1cha.txt")

# 재료명 → ingredient_key 별칭
ING_ALIAS = {
    "염지닭 10호": "raw_chicken_10",
    "닭날개/다리 정육": "chicken_parts",
    "닭다리살 정육": "chicken_boneless",
    "족발 생육": "pork_trotter",
    "수입 삼겹살(보쌈용)": "pork_belly_import",
    "수입 삼겹살": "pork_belly_import",
    "돼지 등심(탕수육용)": "pork_loin_tangsuyuk",
    "돼지 등심": "pork_loin_tangsuyuk",
    "소고기 패티용 다짐육": "beef_patty",
    "수입 우삼겹": "beef_slices",
    "신선 야채": "vegetables_fresh",
    "신선 채소": "vegetables_fresh",
    "해물 믹스": "seafood_mix",
    "마라탕 소스": "malatang_base",
    "모짜렐라 치즈": "mozzarella_cheese",
    "떡볶이 떡": "tteok",
    "사각 어묵": "fish_cake",
    "비엔나 소시지": "vienna_sausage",
    "허니/프리미엄 소스": "sauce_honey",
    "토마토 피자소스": "pizza_sauce",
    "건두부/중국당면/푸주": "tofu_noodles",
    "버거 소스": "sauce_normal",
    "일반 양념 소스": "sauce_normal",
    "피자 도우": "pizza_dough",
    "치킨파우더": "frying_powder",
    "식용유": "frying_oil",
    "춘장": "jajang_paste",
    "중식 생면": "noodles_fresh",
    "버거 번": "burger_bun",
    "치킨무": "sidedish_set",
    "기본찬 세트": "sidedish_set",
}

def parse_won(s):
    m = re.search(r"([\d,]+)\s*원", s)
    return int(m.group(1).replace(",", "")) if m else None

def parse_ingredients(text):
    # "[농축산물] 염지닭 10호 1.0kg (5,500원) [가공품] 치킨파우더 0.2kg (500원), ..."
    result = []
    cur_class = None
    # [분류] 태그로 분리
    parts = re.split(r"\[(농축산물|가공품)\]", text)
    # parts: ['', '농축산물', ' 염지닭...', '가공품', ' 치킨...']
    i = 1
    while i < len(parts):
        cls = parts[i]
        body = parts[i+1] if i+1 < len(parts) else ""
        # 콤마로 항목 분리 (괄호 안 콤마 주의 → 단가는 콤마 포함이라 '원)' 뒤 콤마로만 분리)
        items = re.split(r"\)\s*,", body)
        for it in items:
            it = it.strip().rstrip(")")
            if not it:
                continue
            # "염지닭 10호 1.0kg (5,500원" → 이름, 수량+단위, 단가
            m = re.match(r"(.+?)\s+([\d.]+)\s*(kg|g|L|ml|개|세트)\s*\(([\d,]+)원?", it)
            if not m:
                continue
            name = m.group(1).strip()
            amount = float(m.group(2))
            unit = m.group(3)
            line = int(m.group(4).replace(",", ""))
            result.append((cls, name, amount, unit, line))
        i += 2
    return result

def slugify_menu(name, idx):
    # 한글 메뉴명 → 간단 슬러그(로마자 없음 → id기반 + 정제). URL은 menu-{gemini_id}로.
    return f"m{idx}"

con = sqlite3.connect(DB)
cur = con.cursor()

# 브랜드 매칭용: brands 테이블 로드
brands = cur.execute("SELECT id,name FROM brands").fetchall()
def match_brand(mb):
    mb_n = mb.replace(" ", "").lower()
    # 1. exact
    for bid, bn in brands:
        if bn.replace(" ", "").lower() == mb_n:
            return bid
    # 2. 브랜드테이블명이 메뉴브랜드로 시작 (BBQ치킨 ⊃ BBQ)
    for bid, bn in brands:
        if bn.replace(" ", "").lower().startswith(mb_n):
            return bid
    # 3. 메뉴브랜드가 브랜드테이블명으로 시작
    for bid, bn in brands:
        if mb_n.startswith(bn.replace(" ", "").lower()):
            return bid
    return None

# 필요한 사이드디시 키코드 없으면 추가
cur.execute("INSERT OR IGNORE INTO ingredients (ingredient_key,name,class,type,manual_price,base_unit,markup_factor) "
            "VALUES ('sidedish_set','치킨무/기본찬 세트','가공품','manual',500,'개',1.0)")

n_menu, n_ing, skipped, unmatched_ing = 0, 0, [], set()
for line in open(SRC, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip():
        continue
    cols = line.split("|")
    if len(cols) < 7:
        continue
    gid = int(cols[0])
    brand_menu = cols[1].strip()
    sell = parse_won(cols[2])
    cost = parse_won(cols[3])
    ratio = float(cols[4].replace("%", "").strip()) if "%" in cols[4] else None
    ing_text = cols[5]
    source = cols[6].strip()

    # 브랜드/메뉴 분리 (첫 공백 기준)
    sp = brand_menu.split(" ", 1)
    mbrand = sp[0]
    mname = sp[1] if len(sp) > 1 else brand_menu

    bid = match_brand(mbrand)
    if not bid:
        skipped.append((gid, mbrand, mname))
        continue

    cur.execute(
        "INSERT INTO menus (brand_id,name,slug,sell_price,est_cost,cost_ratio,source,gemini_id,sort_order,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))",
        (bid, mname, slugify_menu(mname, gid), sell, cost, ratio, source, gid, gid))
    menu_id = cur.lastrowid
    n_menu += 1

    for so, (cls, name, amount, unit, linecost) in enumerate(parse_ingredients(ing_text)):
        key = ING_ALIAS.get(name)
        if not key:
            unmatched_ing.add(name)
            continue
        cur.execute(
            "INSERT INTO menu_ingredients (menu_id,ingredient_key,amount,unit,line_cost,sort_order) "
            "VALUES (?,?,?,?,?,?)", (menu_id, key, amount, unit, linecost, so))
        n_ing += 1

con.commit()
print(f"메뉴 임포트: {n_menu}개, 재료연결: {n_ing}건")
print(f"제외된 메뉴(홈페이지 없는 브랜드): {len(skipped)}개")
for gid, mb, mn in skipped:
    print(f"  - [{gid}] {mb} / {mn}")
if unmatched_ing:
    print(f"미매핑 재료명: {unmatched_ing}")
con.close()
