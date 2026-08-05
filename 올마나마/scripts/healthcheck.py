# -*- coding: utf-8 -*-
# 상시 점검 — 데이터 무결성 + 계산 검산 + HTML 링크 + 콘텐츠 상식
#  데이터/재료/가격을 바꿀 때마다 돌릴 것. 조용히 스킵되는 버그를 잡는 게 목적.
#  사용법: python scripts/healthcheck.py
import sqlite3, os, re, glob, sys, json

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
PREV = os.path.join(BASE, "_preview")
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

FAILS = []
def chk(label, rows, show=4, warn_only=False):
    n = len(rows)
    ok = (n == 0)
    print(f"{'✅' if ok else ('⚠️ ' if warn_only else '❌')} {label}: {n}건")
    for r in rows[:show]:
        print("     ", tuple(r) if not isinstance(r, (str, tuple)) else r)
    if not ok and not warn_only: FAILS.append(label)
    return rows
def q(sql, args=()): return cur.execute(sql, args).fetchall()

print("═══ 1. 데이터 무결성 ═══")
chk("고아 menu_ingredients", q("SELECT mi.id,mi.menu_id FROM menu_ingredients mi LEFT JOIN menus m ON mi.menu_id=m.id WHERE m.id IS NULL"))
chk("고아 재료키(menu)", q("SELECT DISTINCT mi.ingredient_key FROM menu_ingredients mi LEFT JOIN ingredients i ON mi.ingredient_key=i.ingredient_key WHERE i.ingredient_key IS NULL"))
# dish도 반드시 볼 것 — menu만 보고 "안 쓰는 재료"라 판단해 지웠다가 요리사전이 깨졌다(2026-07-17).
chk("고아 재료키(dish)", q("SELECT DISTINCT di.ingredient_key FROM dish_ingredients di LEFT JOIN ingredients i ON di.ingredient_key=i.ingredient_key WHERE i.ingredient_key IS NULL"))
# ★ dish 표준레시피는 DB가 아니라 dish_data.py의 **DISHES 리터럴**에 있다.
#   DB만 보고 "고아 없음"이라 해도 스크립트가 없는 키를 부르면 gen_dishes.py가 통째로 죽는다.
#
# 🔴 2026-07-20: 예전엔 gen_dishes.py 소스를 **정규식으로 긁어** 키를 뽑았다. 데이터를 dish_data.py로
#   옮기면 그 정규식이 아무것도 못 찾아 _keys가 빈 set이 되고, 검사가 "실패"가 아니라 **조용히 통과**한다.
#   그래서 import 방식으로 바꿨다. 앞으로 데이터 위치를 또 옮기면 이 블록도 반드시 같이 고칠 것.
sys.path.insert(0, os.path.join(BASE, "scripts"))
try:
    import dish_data as _dd
    _keys = {k for d in _dd.DISHES for (k, _a, _u) in d[4]}
    _have = {r[0] for r in q("SELECT ingredient_key FROM ingredients")}
    chk("dish_data.py DISHES가 부르는 없는 재료키", sorted(_keys - _have))
    if not _keys:      # import는 됐는데 비어 있으면 그것도 이상 — 조용한 통과 방지
        chk("dish_data.DISHES가 비어 있음", ["DISHES 파싱 결과 0건"])
except Exception as _e:
    chk("dish_data.py import 실패", [str(_e)])
chk("고아 메뉴(브랜드없음)", q("SELECT m.id,m.name FROM menus m LEFT JOIN brands b ON m.brand_id=b.id WHERE b.id IS NULL"))
chk("중복 slug(brands)", q("SELECT slug,COUNT(*) c FROM brands GROUP BY slug HAVING c>1"))
chk("중복 slug(dishes)", q("SELECT slug,COUNT(*) c FROM dishes GROUP BY slug HAVING c>1"))
chk("재료 0개 메뉴", q("SELECT id,name FROM menus m WHERE NOT EXISTS(SELECT 1 FROM menu_ingredients WHERE menu_id=m.id)"))
# 같은 메뉴에 같은 재료가 두 줄이면 재료비 표에 "우유 200ml" "우유 40ml"이 따로 떠 결함으로 보인다(2026-07-17 15건).
chk("한 메뉴에 같은 재료가 중복 줄", q("""SELECT m.name, i.name, COUNT(*) c FROM menu_ingredients mi
    JOIN menus m ON mi.menu_id=m.id JOIN ingredients i ON mi.ingredient_key=i.ingredient_key
    GROUP BY mi.menu_id, mi.ingredient_key HAVING c>1"""))
# 이름이 같은 재료가 여러 키로 존재하면 단가가 갈린다(대왕오징어 5키·해물믹스 44% 차이, 2026-07-17).
chk("이름이 같은 재료가 여러 키", q("SELECT name, COUNT(*) c FROM ingredients GROUP BY name HAVING c>1"))
chk("판매가 0/NULL", q("SELECT id,name FROM menus WHERE sell_price IS NULL OR sell_price<=0"))
chk("레시피 없음", q("SELECT id,name FROM menus WHERE recipe_steps IS NULL OR recipe_steps=''"))
chk("line_cost 0/NULL", q("SELECT mi.id,m.name FROM menu_ingredients mi JOIN menus m ON mi.menu_id=m.id WHERE mi.line_cost IS NULL OR mi.line_cost=0"))
chk("store_ratio 없음", q("SELECT id,name FROM menus WHERE store_ratio IS NULL"))
chk("단가 없는 재료(사용중)", q("SELECT DISTINCT i.ingredient_key FROM ingredients i JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key WHERE i.type='manual' AND (i.manual_price IS NULL OR i.manual_price=0)"))

print("\n═══ 2. 단위 정합 (★ 2026-07-17 우유 42건 버그의 원인) ═══")
LIQ, SOL, CNT = {"ml","L"}, {"g","kg"}, {"개","세트","장","마리"}
bad = []
for r in q("""SELECT mi.id,m.name mn,i.ingredient_key k,i.base_unit bu,mi.amount,mi.unit
    FROM menu_ingredients mi JOIN ingredients i ON mi.ingredient_key=i.ingredient_key JOIN menus m ON mi.menu_id=m.id"""):
    bu, u = r["bu"], r["unit"]
    ok = (bu == "kg" and u in SOL | LIQ) or (bu == "L" and u in LIQ | SOL) or (bu == "개" and u in CNT)
    if not ok: bad.append((r["mn"], r["k"], f"{r['amount']:g}{u}", f"base={bu}"))
chk("재료 base_unit ≠ 메뉴 unit", bad)

# ★ dish도 반드시 본다 — dish 레시피는 gen_dishes.py 하드코딩이라 단위검사 밖이었다.
#   '개' 단위 라면(400원/개)을 dish에서 '100g'으로 써서 400×100=40,000원 → 부대찌개 재료비 17만원(2026-07-18).
dbad = []
for r in q("""SELECT d.name dn, i.name inm, i.base_unit bu, di.amount, di.unit
    FROM dish_ingredients di JOIN dishes d ON di.dish_id=d.id
    JOIN ingredients i ON di.ingredient_key=i.ingredient_key"""):
    bu, u = r["bu"], r["unit"]
    okd = (bu == "kg" and u in SOL | LIQ) or (bu == "L" and u in LIQ | SOL) or (bu == "개" and u in CNT)
    if not okd: dbad.append((r["dn"], r["inm"], f"{r['amount']:g}{u}", f"base={bu}"))
chk("dish 재료 base_unit ≠ dish unit", dbad)

# ★ 단위가 '맞는데도' 수량이 터무니없는 경우 — 위 검사는 단위 호환만 보지 크기는 안 본다.
#   실제 사고(2026-07-20): "달걀 50g"을 개수로 환산하며 g↔kg 환산을 빠뜨려 **833개**가 됐고,
#   단위는 개↔개로 맞아서 통과, 탕수육 재료비가 22만원으로 나왔다.
#   개 단위 재료가 한 요리에 30개 넘게 들어가는 건 정상이 아니다.
dqty = [(r["dn"], r["inm"], f'{r["amount"]:g}{r["unit"]}')
        for r in q("""SELECT d.name dn, i.name inm, di.amount, di.unit
            FROM dish_ingredients di JOIN dishes d ON di.dish_id=d.id
            JOIN ingredients i ON di.ingredient_key=i.ingredient_key
            WHERE i.base_unit='개' AND di.unit='개' AND di.amount > 30""")]
chk("dish 개수 재료가 비상식적으로 많음(>30개)", dqty)

# 한 재료 줄이 그 요리 재료비의 70%를 넘으면 단위·수량 오류일 가능성이 높다.
dline = []
_dcost = {}
for r in q("""SELECT d.name dn, i.name inm, di.amount, di.unit, i.manual_price mp, i.base_unit bu
    FROM dish_ingredients di JOIN dishes d ON di.dish_id=d.id
    JOIN ingredients i ON di.ingredient_key=i.ingredient_key WHERE i.manual_price>0"""):
    qty = r["amount"] / 1000 if r["unit"] in ("g", "ml") else r["amount"]
    _dcost.setdefault(r["dn"], []).append((r["inm"], round(r["mp"] * qty), f'{r["amount"]:g}{r["unit"]}'))
for dn, lines in _dcost.items():
    tot = sum(c for _, c, _ in lines)
    if tot < 3000:
        continue
    for inm, c, amt in lines:
        # 한우 갈비처럼 원래 비싼 주재료는 90%를 넘기도 한다 → 임계를 95%로 두고,
        # 금액도 5만원을 넘을 때만 본다. 단위오류는 보통 수십 배로 튀어 이 선을 훨씬 넘는다.
        if c > tot * 0.95 and c > 50000:
            dline.append((dn, inm, amt, f"{c:,}원 / 합계 {tot:,}원"))
chk("dish 한 재료가 재료비를 독식(단위오류 의심)", dline)

print("\n═══ 3. 계산 검산 ═══")
bad = [(r["id"], r["name"], r["est_cost"], r["s"]) for r in q(
    "SELECT m.id,m.name,m.est_cost,SUM(mi.line_cost) s FROM menus m JOIN menu_ingredients mi ON mi.menu_id=m.id GROUP BY m.id")
    if r["est_cost"] and r["s"] and abs(r["est_cost"] - r["s"]) > 1]
chk("est_cost ≠ line_cost 합계", bad)
chk("도매 > 소매 역전(재료)", q("SELECT ingredient_key,manual_price,wholesale_price FROM ingredients WHERE wholesale_price>manual_price AND manual_price>0"))
chk("store_cost > est_cost", q("SELECT id,name,est_cost,store_cost FROM menus WHERE store_cost>est_cost"))
bad = [(r["id"], r["name"], r["store_ratio"], round(r["store_cost"]/r["sell_price"]*100, 1)) for r in q(
    "SELECT id,name,sell_price,store_cost,store_ratio FROM menus WHERE store_ratio IS NOT NULL")
    if abs(round(r["store_cost"]/r["sell_price"]*100, 1) - r["store_ratio"]) > 0.15]
chk("원가율 ≠ 원가/판매가", bad)
chk("원가 > 판매가(적자)", q("SELECT id,name,sell_price,store_cost FROM menus WHERE store_cost>sell_price"))
chk("원가율 이상치(≥90 or ≤3)", q("SELECT id,name,store_ratio FROM menus WHERE store_ratio>=90 OR store_ratio<=3"))

print("\n═══ 4. 콘텐츠 상식 ═══")
allret = [(r[0], r[1]) for r in q("SELECT ingredient_key,name FROM ingredients WHERE COALESCE(is_retail,0)=1")]
bad = []
for m in q("SELECT id,name,recipe_steps FROM menus WHERE recipe_steps IS NOT NULL"):
    have = {r[0] for r in q("SELECT ingredient_key FROM menu_ingredients WHERE menu_id=?", (m["id"],))}
    havenames = " ".join(r[0] for r in q("""SELECT i.name FROM menu_ingredients mi JOIN ingredients i
        ON mi.ingredient_key=i.ingredient_key WHERE mi.menu_id=?""", (m["id"],)))
    for k, nm in allret:
        if k in have: continue
        core = re.sub(r"\s*\d+(g|ml|kg|L).*$", "", nm).strip()
        if len(core) < 6: continue
        if core in m["recipe_steps"] and core not in havenames: bad.append((m["id"], m["name"], core))
chk("레시피가 없는 시판제품 호출", bad)
bad = [(m["id"], m["name"]) for m in q("SELECT id,name,recipe_steps FROM menus WHERE recipe_steps IS NOT NULL")
       if "튀" in m["name"] and not re.search(r"튀기|튀겨|튀긴|에어프라이어|기름에", m["recipe_steps"])]
chk("튀김 메뉴에 튀김 단계 없음", bad)
# 말투: 한다체(평서형 종결)가 남아있는지로 검사. 존댓말 활용형은 워낙 다양해서
# "허용 목록"으로 잡으면 오탐만 난다(2026-07-17에 257건 전부 오탐이었음).
TONE_BAD = re.compile(r"(한다|된다|넣는다|뺀다|튀긴다|굽는다|만든다|삶는다|썬다|볶는다|"
                      r"올린다|섞는다|끓인다|낸다|입힌다|묻힌다|버무린다|담는다|짠다|푼다)\s*\.?$")
bad = [(m["id"], m["name"], s) for m in q("SELECT id,name,recipe_steps FROM menus WHERE recipe_steps IS NOT NULL")
       for s in m["recipe_steps"].split("\n") if TONE_BAD.search(s.strip())]
chk("레시피에 한다체 잔존", bad)

# 메뉴 이름이 말하는 재료가 실제로 안 들어간 경우 = 오매핑 신호.
#  '매운항정살덮밥'에 항정살이 없고 삼겹살이 들어있던 사례(2026-07-17)에서 나온 검사.
#  소대창→돼지등심 사고와 같은 계열이라 반드시 상시로 돌 것.
#  ⚠️ 검출기가 오탐을 낸다(떡갈비의 '떡' 등). NAME_OK에 사유와 함께 등록해 제외한다.
CUES = {"항정살":["항정"],"가브리살":["가브리"],"목살":["목살"],"등심":["등심"],"안심":["안심"],
        "삼겹":["삼겹"],"베이컨":["베이컨"],"차돌":["차돌","우삼겹"],"곱창":["곱창"],"대창":["대창"],
        "막창":["막창"],"오징어":["오징어"],"새우":["새우"],"연어":["연어"],"장어":["장어"],
        "낙지":["낙지"],"문어":["문어"],"전복":["전복"],"명란":["명란"],"고등어":["고등어"],
        "갈치":["갈치"],"등뼈":["등뼈","돈뼈"],"우거지":["우거지"],"시래기":["시래기"],
        "치즈":["치즈"],"감자":["감자"],"고구마":["고구마"],"버섯":["버섯"],"김치":["김치"]}
NAME_OK = {
    (338, "떡"): "떡갈비는 고기 요리 — 떡이 안 들어가는 게 맞음",
    (2, "떡"): "자메이카소떡적구이 — 레시피상 치킨 구이. 떡 없음이 맞음",
}
bad = []
# uncosted_note = 품목은 공식 근거로 확정됐으나 **중량만** 공개 안 돼 원가에 못 넣은 재료.
#  화면에 "➕ 감자 큐브 — 원가에 미포함"으로 **표시하고 이유까지 밝히므로** 숨긴 게 아니다 → 통과.
#  (g을 지어내면 '양파값 사고' 재발이라, 표시하되 계산엔 안 넣는 게 맞는 처리다)
for m in q("""SELECT m.id, m.name, b.name bn, COALESCE(m.uncosted_note,'') unc
              FROM menus m JOIN brands b ON m.brand_id=b.id"""):
    hay = m["unc"] + " " + " ".join((r[0] or "") + " " + (r[1] or "") for r in q(
        """SELECT i.name, mi.composition FROM menu_ingredients mi
           JOIN ingredients i ON mi.ingredient_key=i.ingredient_key WHERE mi.menu_id=?""", (m["id"],)))
    for cue, keys in CUES.items():
        if cue not in m["name"] or (m["id"], cue) in NAME_OK: continue
        if not any(k in hay for k in keys):
            bad.append((m["id"], f'{m["bn"]} {m["name"]}', f"이름엔 '{cue}'인데 재료에 없음"))
chk("메뉴명이 말하는 재료가 없음(오매핑)", bad, show=6)

print("\n═══ 5. 생성 HTML ═══")
if os.path.isdir(PREV):
    files = set(os.listdir(PREV)); broken = {}
    for f in glob.glob(os.path.join(PREV, "*.html")):
        s = open(f, encoding="utf-8").read()
        # 정식 URL = 확장자 없는 주소(2026-07-19). href="menu_6" → menu_6.html 존재해야 함.
        for href in re.findall(r'href="([A-Za-z0-9_\-]+)(?:#[^"]*)?"', s):
            if href + ".html" not in files: broken.setdefault(href, []).append(os.path.basename(f))
        for href in re.findall(r'href="([^"#?:]+\.html)"', s):
            if "'" in href or "+" in href: continue     # JS 문자열 결합 제외
            broken.setdefault(href + " ← .html 잔존", []).append(os.path.basename(f))
        for src in re.findall(r'src="(logos/[^"]+)"', s):
            if not os.path.exists(os.path.join(PREV, src)): broken.setdefault(src, []).append(os.path.basename(f))
    chk("깨진 링크/이미지", [(t, f"{len(v)}개 페이지", v[0]) for t, v in broken.items()])
    bad = [(os.path.basename(f), p) for f in glob.glob(os.path.join(PREV, "*.html"))
           for p in (">None<", "원가율 None", "None원", ">undefined<") if p in open(f, encoding="utf-8").read()]
    chk("None/undefined 노출", bad)
    # 화면에 찍힌 표 합계가 헤드라인 원가와 다르면 독자가 바로 알아챈다(2026-07-17 허니콤보 400원).
    bad = []
    for m in q("SELECT id,name,store_cost FROM menus WHERE store_cost IS NOT NULL"):
        p = os.path.join(PREV, f"menu_{m['id']}.html")
        if not os.path.exists(p): continue
        # ⚠️ 표 구조가 바뀌면 이 정규식이 조용히 전부 미스가 된다(2026-07-26: 양 칼럼을
        #    없애 <td></td> 가 사라지자 378개 전부 "'-'로 표기됨"으로 떨어졌다 = 가드가 죽음).
        #    그래서 빈 칼럼은 있어도 없어도 통과하게 둔다.
        mo = re.search(r'추정 재료비 합계</td>(?:<td></td>)?<td class="r domae">([\d,]+)원',
                       open(p, encoding="utf-8").read())
        if not mo: bad.append((m["id"], m["name"], "도매합계 '-'로 표기됨")); continue
        v = int(mo.group(1).replace(",", ""))
        if v != m["store_cost"]: bad.append((m["id"], m["name"], f"표={v:,} vs 헤드라인={m['store_cost']:,}"))
    chk("표의 도매합계 ≠ 헤드라인 매장원가", bad)

    # ── SEO: 이 사이트의 자산은 검색 노출이다. 2026-07-17에 전부 비어 있는 걸 발견했다.
    #    (meta description 489개 중 488개 없음 · sitemap/robots 없음 · canonical 0 · 중복 title 21종
    #     · menu_6을 통째로 복사한 sample_menu.html이 중복 콘텐츠로 발행되고 있었음)
    _pub = [f for f in sorted(glob.glob(os.path.join(PREV, "*.html")))
            if not os.path.basename(f).startswith("_")]
    _titles, _nodesc, _nocanon = {}, [], []
    for f in _pub:
        s = open(f, encoding="utf-8").read(); b = os.path.basename(f)
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        if t: _titles.setdefault(t.group(1).strip(), []).append(b)
        if not re.search(r'<meta name="description" content="[^"]{10,}"', s): _nodesc.append(b)
        if not re.search(r'rel="canonical"', s): _nocanon.append(b)
    chk("meta description 없음", _nodesc, show=3)
    chk("canonical 없음", _nocanon, show=3)
    chk("중복 title", [(k, f"×{len(v)}", v[0]) for k, v in _titles.items() if len(v) > 1], show=3)
    chk("sitemap.xml 없음", [] if os.path.exists(os.path.join(PREV, "sitemap.xml")) else ["sitemap.xml"])
    chk("robots.txt 없음", [] if os.path.exists(os.path.join(PREV, "robots.txt")) else ["robots.txt"])
    # 어디서도 링크 안 되는 발행 페이지 = 크롤러가 못 타고 사용자도 못 찾는다
    _all = {os.path.basename(f) for f in _pub}
    _linked = set()
    for f in glob.glob(os.path.join(PREV, "*.html")):
        _s = open(f, encoding="utf-8").read()
        # ⚠️ 한글 파일명(price_양파)도 링크로 인정해야 한다 — 영숫자만 보면
        #    재료 페이지 348장이 전부 '고아'로 잡힌다(2026-07-24).
        _linked |= {h + ".html" for h in re.findall(r'href="([^"/:?#]+)(?:#[^"]*)?"', _s)}
        _linked |= set(re.findall(r'href="([^"#?:]+\.html)"', _s))
    chk("어디서도 링크 안 되는 발행 페이지", sorted(_all - _linked - {"index.html"}), show=4)
    # 검수에서 탈락시킨 로고 파일이 디스크에 남으면 배포 시 R2로 그대로 올라간다(2026-07-17 17개·874KB).
    _logodir = os.path.join(PREV, "logos")
    if os.path.isdir(_logodir):
        _used = {r[0].split("/")[-1] for r in q("SELECT logo_url FROM brands WHERE logo_url IS NOT NULL")}
        _orph = sorted(os.path.basename(f) for f in glob.glob(os.path.join(_logodir, "*"))
                       if os.path.basename(f) not in _used)
        chk("DB가 안 쓰는 고아 로고 파일", _orph, show=4)
    # 구조화 데이터(JSON-LD) — 레시피 349개를 갖고도 0개라 구글 리치결과를 못 받고 있었다(2026-07-17).
    #  ⚠️ Recipe 스키마에 offers(가격)를 넣으면 안 된다 — 우리는 그 메뉴의 판매자가 아니다.
    #  2026-07-23: Search Console이 image·keywords·author·recipeCuisine·recipeInstructions[].url
    #  누락을 지적해서 회귀 가드로 추가. menu_*.html뿐 아니라 dish_*.html도 같은 방식으로 낸다.
    _ld_missing, _ld_bad, _ld_offers = [], [], []
    _ld_noimg, _ld_nofield, _ld_nourl = [], [], []
    for f in glob.glob(os.path.join(PREV, "menu_*.html")) + glob.glob(os.path.join(PREV, "dish_*.html")):
        _s = open(f, encoding="utf-8").read()
        _blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', _s, re.S)
        if not _blocks: _ld_missing.append(os.path.basename(f)); continue
        for _b in _blocks:
            try:
                _d = json.loads(_b)
                if "offers" in _d: _ld_offers.append(os.path.basename(f))
                if _d.get("@type") == "Recipe":
                    if not _d.get("image"): _ld_noimg.append(os.path.basename(f))
                    if not (_d.get("author") and _d.get("keywords") and _d.get("recipeCuisine")):
                        _ld_nofield.append(os.path.basename(f))
                    if any(not step.get("url") for step in _d.get("recipeInstructions", [])):
                        _ld_nourl.append(os.path.basename(f))
            except Exception as e:
                _ld_bad.append((os.path.basename(f), str(e)[:40]))
    chk("메뉴/요리 페이지에 JSON-LD 없음", _ld_missing, show=3)
    chk("JSON-LD 파싱 실패", _ld_bad, show=3)
    chk("Recipe에 offers(가격) 있음 — 우리는 판매자가 아니다", _ld_offers, show=3)
    chk("Recipe에 image 없음 (구글 리치결과 심각 오류)", _ld_noimg, show=3)
    chk("Recipe에 author/keywords/recipeCuisine 없음", _ld_nofield, show=3)
    chk("HowToStep에 url 없음", _ld_nourl, show=3)
    _nolazy = [os.path.basename(f) for f in _pub
               for i in re.findall(r"<img[^>]*>", open(f, encoding="utf-8").read()) if "loading=" not in i]
    chk("loading=lazy 없는 img", _nolazy, show=3)
else:
    print("  (프리뷰 미생성 — 스킵)")

    # ── SEO: 이 사이트의 자산은 검색 노출이다. 2026-07-17에 전부 비어 있는 걸 발견했다.
    #    (meta description 489개 중 488개 없음 · sitemap/robots 없음 · canonical 0 · 중복 title 21종)
    _pub = [f for f in sorted(glob.glob(os.path.join(PREV, "*.html")))
            if not os.path.basename(f).startswith("_")]
    _titles, _nodesc, _nocanon = {}, [], []
    for f in _pub:
        s = open(f, encoding="utf-8").read(); b = os.path.basename(f)
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        if t: _titles.setdefault(t.group(1).strip(), []).append(b)
        if not re.search(r'<meta name="description" content="[^"]{10,}"', s): _nodesc.append(b)
        if not re.search(r'rel="canonical"', s): _nocanon.append(b)
    chk("meta description 없음", _nodesc, show=3)
    chk("canonical 없음", _nocanon, show=3)
    chk("중복 title", [(k, f"×{len(v)}", v[0]) for k, v in _titles.items() if len(v) > 1], show=3)
    chk("sitemap.xml 없음", [] if os.path.exists(os.path.join(PREV, "sitemap.xml")) else ["sitemap.xml"])
    chk("robots.txt 없음", [] if os.path.exists(os.path.join(PREV, "robots.txt")) else ["robots.txt"])
    # 어디서도 링크 안 되는 발행 페이지 = 크롤러가 못 타고 사용자도 못 찾는다
    _all = {os.path.basename(f) for f in _pub}
    _linked = set()
    for f in glob.glob(os.path.join(PREV, "*.html")):
        _s = open(f, encoding="utf-8").read()
        _linked |= {h + ".html" for h in re.findall(r'href="([A-Za-z0-9_\-]+)(?:#[^"]*)?"', _s)}
        _linked |= set(re.findall(r'href="([^"#?:]+\.html)"', _s))
    chk("어디서도 링크 안 되는 발행 페이지", sorted(_all - _linked - {"index.html"}), show=4)
    # 검수에서 탈락시킨 로고 파일이 디스크에 남으면 배포 시 R2로 그대로 올라간다(2026-07-17 17개·874KB).
    _logodir = os.path.join(PREV, "logos")
    if os.path.isdir(_logodir):
        _used = {r[0].split("/")[-1] for r in q("SELECT logo_url FROM brands WHERE logo_url IS NOT NULL")}
        _orph = sorted(os.path.basename(f) for f in glob.glob(os.path.join(_logodir, "*"))
                       if os.path.basename(f) not in _used)
        chk("DB가 안 쓰는 고아 로고 파일", _orph, show=4)
    # 구조화 데이터(JSON-LD) — 레시피 349개를 갖고도 0개라 구글 리치결과를 못 받고 있었다(2026-07-17).
    #  ⚠️ Recipe 스키마에 offers(가격)를 넣으면 안 된다 — 우리는 그 메뉴의 판매자가 아니다.
    #  2026-07-23: Search Console이 image·keywords·author·recipeCuisine·recipeInstructions[].url
    #  누락을 지적해서 회귀 가드로 추가. menu_*.html뿐 아니라 dish_*.html도 같은 방식으로 낸다.
    _ld_missing, _ld_bad, _ld_offers = [], [], []
    _ld_noimg, _ld_nofield, _ld_nourl = [], [], []
    for f in glob.glob(os.path.join(PREV, "menu_*.html")) + glob.glob(os.path.join(PREV, "dish_*.html")):
        _s = open(f, encoding="utf-8").read()
        _blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', _s, re.S)
        if not _blocks: _ld_missing.append(os.path.basename(f)); continue
        for _b in _blocks:
            try:
                _d = json.loads(_b)
                if "offers" in _d: _ld_offers.append(os.path.basename(f))
                if _d.get("@type") == "Recipe":
                    if not _d.get("image"): _ld_noimg.append(os.path.basename(f))
                    if not (_d.get("author") and _d.get("keywords") and _d.get("recipeCuisine")):
                        _ld_nofield.append(os.path.basename(f))
                    if any(not step.get("url") for step in _d.get("recipeInstructions", [])):
                        _ld_nourl.append(os.path.basename(f))
            except Exception as e:
                _ld_bad.append((os.path.basename(f), str(e)[:40]))
    chk("메뉴/요리 페이지에 JSON-LD 없음", _ld_missing, show=3)
    chk("JSON-LD 파싱 실패", _ld_bad, show=3)
    chk("Recipe에 offers(가격) 있음 — 우리는 판매자가 아니다", _ld_offers, show=3)
    chk("Recipe에 image 없음 (구글 리치결과 심각 오류)", _ld_noimg, show=3)
    chk("Recipe에 author/keywords/recipeCuisine 없음", _ld_nofield, show=3)
    chk("HowToStep에 url 없음", _ld_nourl, show=3)
    _nolazy = [os.path.basename(f) for f in _pub
               for i in re.findall(r"<img[^>]*>", open(f, encoding="utf-8").read()) if "loading=" not in i]
    chk("loading=lazy 없는 img", _nolazy, show=3)

print("\n═══ 6. 배포 정합 ═══")
# schema.sql은 자동생성(gen_schema.py)이다. 손으로 만지거나 ALTER 후 재생성을 잊으면 실제 DB와 벌어진다.
#  HANDOFF가 "D1 시딩은 schema.sql 기준"이라 적고 있어, 벌어지면 배포 시 테이블·컬럼이 통째로 빠진다.
#  (2026-07-17 발견: dish 4테이블 + 원가 컬럼 11개가 빠진 채였다 → 배포했으면 요리사전·매장원가가 죽었다)
_sch = os.path.join(BASE, "schema.sql")
if os.path.exists(_sch):
    _src = open(_sch, encoding="utf-8").read()
    _decl = set(re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", _src, re.I))
    _act = {r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    chk("schema.sql에 없는 실제 테이블 (D1 시딩 시 누락)", sorted(_act - _decl))
    _colmiss = []
    for _t in sorted(_act & _decl):
        _real = {r[1] for r in q(f"PRAGMA table_info({_t})")}
        _m = re.search(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+" + _t + r"\s*\((.*?)\n\);", _src, re.S | re.I)
        if not _m: continue
        for _c in _real:
            if not re.search(r"\b" + re.escape(_c) + r"\b", _m.group(1)):
                _colmiss.append((_t, _c))
    chk("schema.sql에 없는 실제 컬럼", _colmiss, show=5)
else:
    chk("schema.sql 없음", ["schema.sql"])

# 생성 HTML의 canonical 도메인 = wrangler.toml의 SITE_ORIGIN 이어야 한다.
#  SITE 상수를 생성기 4곳에 각각 박아놨다가 **존재하지 않는 도메인**을 가리킨 적이 있다(2026-07-17).
#  지금은 site_config.py가 wrangler.toml에서 읽어 단일 출처로 쓴다.
_toml = os.path.join(BASE, "workers", "site-renderer", "wrangler.toml")

def _toml_src():
    """wrangler.toml에서 **주석을 걷어낸** 본문. 안 걷어내면 설명문(`# SITE_INDEXABLE = "false" → …`)을
    실제 설정으로 오인해 헛경고가 뜬다(2026-07-17에 실제로 그랬다)."""
    if not os.path.exists(_toml): return ""
    return "\n".join(l for l in open(_toml, encoding="utf-8").read().split("\n")
                     if not l.lstrip().startswith("#"))

if os.path.exists(_toml) and os.path.isdir(PREV):
    _tm = re.search(r'SITE_ORIGIN\s*=\s*"([^"]+)"', _toml_src())
    if _tm:
        _want = _tm.group(1).rstrip("/")
        _wrong = []
        for f in glob.glob(os.path.join(PREV, "*.html")):
            if os.path.basename(f).startswith("_"): continue
            _c = re.search(r'rel="canonical" href="(https?://[^/"]+)', open(f, encoding="utf-8").read())
            if _c and _c.group(1) != _want: _wrong.append((os.path.basename(f), _c.group(1)))
        chk("canonical 도메인 ≠ wrangler SITE_ORIGIN", _wrong, show=3)

# 🔴 배포해도 검색 노출이 0이 되는 조합을 잡는다.
#  wrangler.toml의 SITE_INDEXABLE="false" 인데 robots.txt는 Allow: / 라면 서로 모순이고,
#  워커가 noindex를 붙이면 sitemap·canonical·JSON-LD를 다 해놔도 **노출이 0**이다.
#  이 사이트의 자산이 검색 노출이라 배포 직전에 반드시 확인해야 한다.
if os.path.exists(_toml):
    _tsrc = _toml_src()
    _idx = re.search(r'SITE_INDEXABLE\s*=\s*"([^"]+)"', _tsrc)
    _rb = os.path.join(PREV, "robots.txt")
    _allow = os.path.exists(_rb) and "Allow: /" in open(_rb, encoding="utf-8").read()
    if _idx and _idx.group(1).lower() != "true" and _allow:
        chk("SITE_INDEXABLE=false 인데 robots.txt는 Allow — 배포해도 검색 노출 0",
            [(f'wrangler.toml SITE_INDEXABLE="{_idx.group(1)}"', "배포 전 true로 바꿀 것")], warn_only=True)
    else:
        chk("SITE_INDEXABLE vs robots.txt 모순", [])
    # 배포 실체 확인 — wrangler.toml만 있고 main 파일이 없으면 deploy가 불가능하다
    # 배포 방식은 둘 중 하나여야 한다: [assets] 정적 자산 OR main= 워커 스크립트
    _assets = re.search(r'\[assets\]', _tsrc)
    _adir = re.search(r'directory\s*=\s*"([^"]+)"', _tsrc)
    _main = re.search(r'main\s*=\s*"([^"]+)"', _tsrc)
    if _assets:
        _ap = os.path.normpath(os.path.join(os.path.dirname(_toml), _adir.group(1))) if _adir else None
        chk("배포 자산 폴더 없음 (build_dist.py 먼저)",
            [] if (_ap and os.path.isdir(_ap)) else [_adir.group(1) if _adir else "directory 미지정"], warn_only=True)
        _n = len(glob.glob(os.path.join(_ap, "*.html"))) if _ap and os.path.isdir(_ap) else 0
        chk("배포 자산에 HTML 없음", [] if _n else ["_dist HTML 0개"], warn_only=True)
    elif _main:
        _mp = os.path.join(os.path.dirname(_toml), _main.group(1))
        chk("워커 main 파일 없음 (배포 불가)", [] if os.path.exists(_mp) else [_main.group(1)], warn_only=True)
    else:
        chk("배포 방식 미지정 ([assets]도 main도 없음)", ["wrangler.toml"], warn_only=True)
    _d1 = re.search(r'database_id\s*=\s*"([^"]+)"', _tsrc)
    chk("D1 database_id 미설정", [_d1.group(1)] if (_d1 and "PLACEHOLDER" in _d1.group(1)) else [], warn_only=True)

print("\n═══ 7. 스크립트 정적검사 (커서 재사용) ═══")
# 커서를 .fetchall() 없이 직접 순회하면서 본문에서 또 쿼리하면, 안쪽 쿼리가 커서를 덮어써
# 바깥 순회가 첫 행에서 끊긴다. prices.html이 47종→2종만 나온 원인(2026-07-17).
import ast
def _isx(n): return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"
def _hasx(n): return any(_isx(x) for x in ast.walk(n))
bad = []
for f in sorted(glob.glob(os.path.join(BASE, "scripts", "*.py"))):
    try: tree = ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError as e: bad.append((os.path.basename(f), f"파싱실패: {e}")); continue
    qfuncs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and _hasx(n)}
    for loop in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        if not _isx(loop.iter): continue           # .fetchall() 붙었으면 iter가 execute가 아님
        body = ast.Module(body=loop.body, type_ignores=[])
        ind = {n.func.id for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} & qfuncs
        if _hasx(body) or ind:
            bad.append((os.path.basename(f), loop.lineno, "본문에서 재쿼리 → .fetchall() 붙일 것"))
chk("커서 재사용 루프", bad)

print("\n" + "═" * 40)
if FAILS:
    print(f"❌ 실패 {len(FAILS)}개: {', '.join(FAILS)}")
    sys.exit(1)
print("✅ 전 항목 통과")
con.close()
