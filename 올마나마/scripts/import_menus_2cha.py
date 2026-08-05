# 2차 딥리서치(310개) → menus + menu_ingredients 임포트
# - 브랜드 매칭(홈페이지 없으면 제외), 재료명 alias+fuzzy 매핑, 나머지 자동생성(manual)
# - 2차는 라인단가 없음 → line_cost는 비워두고 나중에 price로 계산. est_cost는 Gemini값 사용.
import json, re, sqlite3, os, hashlib

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = r"C:\Users\hardb\.claude\projects\C--Users-hardb-Desktop--------------API\d7b5e9fe-4fa7-44ab-9652-0407db96dfda\tool-results\mcp-80c2493c-7e1d-4dd3-8de1-3542f548ed2c-read_file_content-1784140413634.txt"

def clean(s):
    return s.replace("*", "").replace("\\", "").strip()

# 정확 매핑 (2차 casual명 → 키코드)
ALIAS2 = {
    "쌀": "rice_uncooked", "백미": "rice_uncooked", "현미밥": "rice_uncooked",
    "현미귀리밥": "rice_uncooked", "밥": "rice_uncooked",
    "계란": "egg_fresh", "식용유": "frying_oil", "튀김유": "frying_oil", "도넛튀김유": "frying_oil",
    "튀김가루": "frying_powder", "떡": "tteok", "어묵": "fish_cake", "치즈": "mozzarella_cheese",
    "비엔나": "vienna_sausage", "두부": "tofu_noodles", "김": "gim",
    "연어": "salmon_raw", "생연어": "salmon_raw", "광어": "white_fish_raw", "생광어": "white_fish_raw",
    "등심": "pork_loin_tangsuyuk", "돈까스등심": "pork_loin_donkasu", "제육용돼지": "pork_loin_tangsuyuk",
    "소고기": "beef_slices", "소불고기": "beef_slices", "양지수육": "beef_stew", "우삼겹": "beef_slices",
    "우삼겹구이": "beef_slices", "우삼겹불고기": "beef_slices",
    "닭가슴살": "chicken_boneless", "순살치킨정육": "chicken_boneless", "치킨정육": "chicken_boneless",
    "새우": "seafood_mix", "초밥새우": "seafood_mix", "한치": "seafood_mix",
    "쌀국수건면": "noodles_rice", "라면사리": "noodles_ramen", "중식생면": "noodles_fresh",
    "김밥속": "gimbap_filling", "커피원두": "coffee_bean", "에스프레소 원두": "coffee_bean",
    "우유": "milk", "살균 우유": "milk", "우유베이스": "milk", "우유얼음": "milk", "우유믹스": "milk", "우유": "milk",
}
# 부분일치 퍼지 (순서대로 검사)
FUZZY = [
    ("야채", "vegetables_fresh"), ("양상추", "salad_greens"), ("로메인", "salad_greens"),
    ("샐러드", "salad_greens"), ("부추", "vegetables_fresh"), ("숙주", "vegetables_fresh"),
    ("드레싱", "sauce_normal"), ("소스", "sauce_normal"), ("간장", "sauce_normal"),
    ("육수", "malatang_base"), ("양념", "sauce_normal"), ("마요", "sauce_normal"), ("촛물", "sauce_normal"),
    ("원두", "coffee_bean"), ("에스프레소", "coffee_bean"), ("우유", "milk"), ("크림", "milk"),
    ("쌀", "rice_uncooked"), ("밥", "rice_uncooked"), ("치즈", "mozzarella_cheese"),
    ("연어", "salmon_raw"), ("광어", "white_fish_raw"), ("새우", "seafood_mix"), ("한치", "seafood_mix"),
    ("돼지", "pork_loin_tangsuyuk"), ("제육", "pork_loin_tangsuyuk"), ("삼겹", "pork_belly_import"),
    ("소고기", "beef_slices"), ("우삼겹", "beef_slices"), ("불고기", "beef_slices"),
    ("치킨", "chicken_boneless"), ("닭", "chicken_boneless"), ("튀김", "frying_powder"),
    ("빵", "burger_bun"), ("도우", "pizza_dough"), ("면", "noodles_fresh"), ("김치", "sidedish_set"),
    ("깍두기", "sidedish_set"), ("단무지", "sidedish_set"), ("락교", "sidedish_set"), ("반찬", "sidedish_set"),
]

con = sqlite3.connect(DB); cur = con.cursor()

# 신규 키코드 보강
NEW_ING = [
    ("gim", "김", "가공품", 15000), ("gimbap_filling", "김밥 속재료", "가공품", 6000),
    ("coffee_bean", "커피 원두", "가공품", 30000), ("milk", "우유", "농축산물", 3000),
]
for k, nm, cl, pr in NEW_ING:
    cur.execute("INSERT OR IGNORE INTO ingredients (ingredient_key,name,class,type,manual_price,base_unit,markup_factor,updated_at) "
                "VALUES (?,?,?,'manual',?,'kg',1.0,datetime('now'))", (k, nm, cl, pr))
# 우유는 KAMIS 9908로 live 승격
cur.execute("UPDATE ingredients SET type='live',kamis_cat='500',kamis_item_code='9908',manual_price=NULL WHERE ingredient_key='milk'")

def map_ing(name):
    n = name.strip()
    if n in ALIAS2:
        return ALIAS2[n], False
    for sub, key in FUZZY:
        if sub in n:
            return key, False
    # 자동 생성 (manual)
    slug = "x_" + hashlib.md5(n.encode("utf-8")).hexdigest()[:10]
    cur.execute("INSERT OR IGNORE INTO ingredients (ingredient_key,name,class,type,base_unit,markup_factor,updated_at) "
                "VALUES (?,?,'가공품','manual','kg',1.0,datetime('now'))", (slug, n))
    return slug, True

# 브랜드 매칭
brands = cur.execute("SELECT id,name FROM brands").fetchall()
def match_brand(mb):
    mb_n = mb.replace(" ", "").lower()
    for bid, bn in brands:
        if bn.replace(" ", "").lower() == mb_n: return bid
    for bid, bn in brands:
        if bn.replace(" ", "").lower().startswith(mb_n): return bid
    for bid, bn in brands:
        if mb_n.startswith(bn.replace(" ", "").lower()): return bid
    return None

d = json.load(open(SRC, encoding="utf-8"))
t = d["fileContent"]

def won(s):
    m = re.search(r"([\d,]+)", s)
    return int(m.group(1).replace(",", "")) if m else None

n_menu, n_ing, auto, skipped = 0, 0, 0, []
for line in t.split("\n"):
    if line.count("|") < 6: continue
    cells = [clean(c) for c in line.split("|")]
    if len(cells) < 7 or not cells[1].isdigit(): continue
    gid = int(cells[1])
    bm = cells[2]
    brand = bm.split(" / ")[0].strip() if " / " in bm else (bm.split()[0] if bm.split() else bm)
    mname = bm.split(" / ",1)[1].strip() if " / " in bm else bm
    sell = won(cells[3]); cost = won(cells[4])
    ratio = float(cells[5].replace("%","").strip()) if "%" in cells[5] else None
    ing_text = cells[6]; source = cells[7].strip() if len(cells) > 7 else ""

    bid = match_brand(brand)
    if not bid:
        skipped.append(brand); continue
    # 중복 방지 (이미 임포트된 gemini_id면 skip)
    if cur.execute("SELECT 1 FROM menus WHERE gemini_id=?", (gid,)).fetchone():
        continue
    cur.execute("INSERT INTO menus (brand_id,name,slug,sell_price,est_cost,cost_ratio,source,gemini_id,sort_order,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))",
                (bid, mname, f"m{gid}", sell, cost, ratio, source, gid, gid))
    mid = cur.lastrowid; n_menu += 1
    for so, part in enumerate(ing_text.split(",")):
        part = part.strip()
        if not part: continue
        m = re.match(r"(.+?)\s+([\d.]+)\s*(kg|g|L|ml|개|장|알|컵|스푼|줌|세트)?\s*$", part)
        if m:
            name, amt, unit = m.group(1).strip(), float(m.group(2)), (m.group(3) or "개")
        else:
            name, amt, unit = part, 1.0, "개"
        key, is_auto = map_ing(name)
        if is_auto: auto += 1
        cur.execute("INSERT INTO menu_ingredients (menu_id,ingredient_key,amount,unit,sort_order) VALUES (?,?,?,?,?)",
                    (mid, key, amt, unit, so))
        n_ing += 1

con.commit()
from collections import Counter
sk = Counter(skipped)
print(f"2차 임포트: 메뉴 {n_menu}개, 재료연결 {n_ing}건 (자동생성 {auto}건)")
print(f"제외 브랜드(홈페이지 없음): {dict(sk)}")
tot = cur.execute("SELECT COUNT(*) FROM menus").fetchone()[0]
print(f"전체 메뉴 누적: {tot}개")
con.close()
