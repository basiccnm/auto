# -*- coding: utf-8 -*-
"""재료 가격을 **여러 줄**로 담는 표를 만들고 채운다. (2026-07-25 확정 구조)

지금까지는 재료 한 줄에 도매값 하나뿐이라, 같은 삼겹살의
`(한돈) 14,500` `(스페인) 6,400` `(네덜란드) 7,000` 을 담을 자리가 없었다.

    ingredient_price
      재료 × 단계(tier) × 축종 × 원산지 × 등급 × 형태  →  원/kg 한 줄

단계(tier) 3단:
    도매    미트박스 원물(박스)
    도소매  미트박스 낱개 · 육마트(1kg)
    소매    쿠팡 로켓 → 쿠팡 일반 → 외부

`ingredients.wholesale_price` 는 그대로 둔다 — 화면·원가계산이 그걸 읽는다.
표에서 **기본 행(is_default=1)** 을 골라 그 값으로 동기화한다. 그래야 기존 코드가 안 깨진다.

행은 그룹별 **최저가 1건씩만** 넣는다(7,774건을 다 넣지 않는다).
"""
import json, io, os, re, sqlite3, sys, shutil, collections
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
MB = os.path.join(BASE, "data", "research", "meatbox", "_전량.json")
CP = os.path.join(BASE, "data", "research", "coupang")
STAMP = "2026-07-25"

DDL = """
create table if not exists ingredient_price (
  id integer primary key autoincrement,
  ingredient_key text not null,
  tier      text not null,          -- 도매 / 도소매 / 소매
  kind      text,                   -- 축종: 한돈 · 수입돼지 · 한우암소 · 수입소 …
  origin    text,                   -- 국산 · 스페인 · 미국 …
  part      text,                   -- 부위
  grade     text,                   -- 등급(한우는 1++(9) 처럼 번호까지)
  brand     text,
  form      text,                   -- 원물 / 세절&분쇄 / 낱개 / 육마트 / 소매
  price     integer not null,       -- base_unit 당 값(육류는 원/kg)
  pack_kg   real,
  bulk_only integer default 0,      -- 최소수량 조건이 붙은 대량상품
  bulk_note text,
  source    text not null,          -- 미트박스 · 쿠팡 · 식자재왕몰 · 오늘얼마
  basis     text,
  url       text,
  is_default integer default 0,     -- 화면·원가계산이 쓰는 기준 행
  checked_at text,
  unique(ingredient_key, tier, kind, origin, part, grade, brand, form)
);
create index if not exists idx_ip_key on ingredient_price(ingredient_key, tier);
"""

BEEF = {"한우암소", "한우거세", "한우수소", "육우암소", "육우거세", "수입소"}
PORK = {"한돈", "수입돼지"}
CHICK = {"국산계육", "수입계육"}
IMP_BEEF, IMP_PORK = {"수입소"}, {"수입돼지"}
KOR_CHICK, IMP_CHICK = {"국산계육"}, {"수입계육"}
DROP_PARTS = {"잡육", "지방", "지방(A)", "지방돈피/돼지껍데기", "돈피/돼지껍데기",
              "반골(꼬리제외)", "알꼬리(반골제외)", "꼬리반골"}

# 재료키, 부위후보, 도매형태, 기본값으로 쓸 축종, 쿠팡 검색어
MAPPING = [
    # ── 소 ──
    ("beef_slices",       ["삼겹양지", "차돌양지"], "세절&분쇄", IMP_BEEF, ["우삼겹", "우삼겹 대패", "차돌양지"]),
    ("beef_stew",         ["삼겹양지", "차돌양지", "양지"], "원물", IMP_BEEF, ["소고기 양지", "한우 양지", "소고기 양지 국거리", "소고기 국거리"]),
    ("x_chadol",          ["차돌박이"], "원물", IMP_BEEF, ["차돌박이", "소고기 차돌박이", "소 차돌박이 구이"]),
    ("beef_patty",        ["분쇄육"], "원물", IMP_BEEF, ["소고기 다짐육"]),
    ("x_ffd92fa2a9",      ["분쇄육"], "원물", IMP_BEEF, ["소고기 다짐육"]),
    ("beef_bulgogi",      ["앞다리/전각", "알전각/볼라전각", "설도", "우둔"], "원물", IMP_BEEF, ["소고기 불고기용", "소고기 불고기감", "소불고기용 쇠고기"]),
    ("beef_cube_steak",   ["알목심"], "원물", IMP_BEEF, ["소고기 큐브 스테이크", "소고기 큐브스테이크"]),
    ("kv_4401",           ["등심"], "원물", IMP_BEEF, ["소고기 등심"]),
    ("beef_bone_sagol",   ["사골"], "원물", {"한우암소", "한우거세", "육우거세", "육우암소"}, ["사골", "소고기 사골"]),
    ("beef_bone_misc",    ["잡뼈", "갈비잡뼈"], "원물", {"한우암소", "한우거세", "육우거세", "육우암소"}, ["소 잡뼈"]),
    ("beef_bone_foot",    ["우족"], "원물", {"한우암소", "한우거세", "육우거세", "육우암소"}, ["우족", "소 우족"]),
    ("beef_oxtail",       ["꼬리"], "원물", {"한우암소", "한우거세", "육우거세", "육우암소"}, ["소꼬리"]),
    # ── 돼지 ──
    ("pork_loin_tangsuyuk", ["등심"], "원물", IMP_PORK, ["돼지 등심", "돼지고기 등심", "탕수육용 돼지등심"]),
    ("pork_loin_donkasu",   ["등심"], "원물", IMP_PORK, ["돼지 등심", "돼지고기 등심", "돈까스용 돼지등심", "돈까스용 등심"]),
    ("x_2255eba1be",        ["등심"], "원물", IMP_PORK, ["돼지 등심", "돼지고기 등심"]),
    ("x_9470ee444a",        ["등심"], "원물", IMP_PORK, ["돼지 등심", "돼지고기 등심"]),
    ("pork_belly_import",   ["삼겹살"], "원물", IMP_PORK, ["삼겹살", "수입 삼겹살"]),
    ("pork_front_leg",      ["전지/앞다리"], "원물", IMP_PORK, ["돼지 앞다리살", "제육용 돼지 앞다리살"]),
    ("x_1294333d76",        ["전지/앞다리"], "원물", IMP_PORK, ["돼지 앞다리살"]),
    # 돼지 다짐육은 목전지를 갈아 파는 상품이 실제로 있다(업소용-목전지 다짐육)
    ("x_e6d782c93c",        ["목전지", "전지/앞다리"], "세절&분쇄", IMP_PORK, ["돼지고기 다짐육"]),
    # 돈뼈는 수입산을 많이 쓴다(대표 확인). 국산 등뼈도 표에 함께 남는다
    ("x_2458074f8e",        ["목뼈", "등뼈"], "원물", IMP_PORK, ["감자탕 등뼈", "감자탕돈뼈"]),
    ("pork_trotter",        ["장족"], "원물", PORK, ["족발", "족발 생육"]),
    ("x_hangjeong",         ["항정살"], "원물", IMP_PORK, ["항정살"]),
    ("pork_stomach",        ["오소리감투"], "원물", IMP_PORK, ["오소리감투", "돼지 오소리감투"]),
    ("x_80a38156df",        ["오돌뼈"], "원물", PORK, ["돼지 오돌뼈"]),
    ("x_d191a7196b",        ["돈두(머리)"], "원물", PORK, []),
    # ── 닭 (뼈=국산, 순살=수입 기본. 계육절단은 이상값이라 부위후보에서 뺀다) ──
    ("raw_chicken_10",      ["통닭10호", "통닭(한마리)"], {"원물", "세절&분쇄"}, KOR_CHICK, ["염지닭"]),
    ("raw_chicken_8",       ["통닭8호", "통닭(한마리)"], {"원물", "세절&분쇄"}, KOR_CHICK, []),
    ("nc_1415849ca7",       ["도리육", "통닭10호"], {"원물", "세절&분쇄"}, KOR_CHICK, []),
    ("chicken_boneless",    ["(계육)다리살", "닭다리살"], {"원물", "세절&분쇄"}, IMP_CHICK, ["닭다리살 정육", "닭정육"]),
    ("chicken_leg_import",  ["(계육)다리살", "닭다리살"], {"원물", "세절&분쇄"}, IMP_CHICK, []),
    ("chicken_parts",       ["닭봉", "닭윙", "날개", "미들윙", "통날개"], {"원물", "세절&분쇄"}, KOR_CHICK, ["닭봉", "닭윙"]),
    ("chicken_breast",      ["(계육)가슴살", "닭가슴살"], {"원물", "세절&분쇄"}, IMP_CHICK, ["닭가슴살"]),
    ("chicken_feet_bone",   ["닭발"], {"원물", "세절&분쇄"}, KOR_CHICK, ["닭발"]),
    ("chicken_feet",        ["닭발", "깐닭발"], {"원물", "세절&분쇄"}, IMP_CHICK, []),
]
FORMS = {"도매": {"원물"}, "도소매": {"낱개"}}

# 상품명에 이 말이 있어야 하는 재료 — 부위·형태만으로는 안 갈리는 것들
# 돼지 다짐육은 '전지/앞다리 슬라이스'(5,720)가 세절로 같이 잡힌다. 슬라이스는 다짐이 아니다.
NAME_MUST = {"x_e6d782c93c": re.compile(r"다짐|민찌|분쇄")}
# 가공품 차단. coupang_link_map.py 의 BAD 리스트를 병합했다(2026-07-25).
#   ⚠️ BAD 중 육류와 충돌하는 토큰은 일부러 뺐다:
#      돈까스(=돈까스'용' 원육) · 구이(구이'용') · 튀김(탕수육/튀김'용') ·
#      조림(장'조림'용) · 무침 · 세트(단품도 'N세트'로 팔림) → 이걸 넣으면 정상 원육이 걸러진다.
BAD_CP = re.compile(
    r"곰탕|육수|진국|사골국|만두|라면|즉석|레토르트|파우치|캔|소스|양념장|"
    r"선물세트|세트선물|건강식품|영양제|사료|간식|개껌|면도기|갈고리|부추|"
    # ↓ coupang_link_map.BAD 병합분(충돌 토큰 제외)
    r"말랭이|스틱|칩|과자|쿠키|케이크|샐러드|김밥|볶음밥|고로케|크로켓|동그랑땡|"
    r"후라이|지단|너겟|음료|주스|라떼|에이드|시럽|잼|선물|베이글|곤약|컵밥|밀키트|장아찌")

# 교차오염 제외 — 상품명에 다른 축종 표식이 있으면 버린다.
#   소 재료에 '돼지/한돈'이, 돼지 재료에 '소고기/한우'가 섞여 들어오는 것을 막는다.
#   ⚠️ 맨 '소'·'우'·'돈'은 소스/소포장/구이/뒷다리 등에 붙어 오탐이 커서 쓰지 않는다.
PORK_MARK = re.compile(r"돼지|한돈|돈육|돈까스|돈등심|돈후지|하이포크|오겹|뒷고기")
BEEF_MARK = re.compile(r"소고기|쇠고기|한우|육우|청정우")

# 부위 혼동 제외 — 축종 표식만으론 못 거르는 것들.
#   등심 재료엔 '안심', 양지 재료엔 '사태'가 검색어로 딸려 온다(안심≠등심, 사태≠양지).
RETAIL_EXCLUDE = {
    "kv_4401":             ["안심"],
    "pork_loin_tangsuyuk": ["안심"],
    "pork_loin_donkasu":   ["안심"],
    "x_2255eba1be":        ["안심"],
    "x_9470ee444a":        ["안심"],
    "beef_stew":           ["사태"],
    "beef_slices":         ["사태"],
}

# 소매 오매칭 방지 — 상품명에 이 토큰 중 하나가 있어야 그 재료로 인정한다.
# (검색어로 긁으면 '삼겹살'에 뒷고기모듬, '등심'에 안심이 섞여 들어온다. 2026-07-25)
RETAIL_REQUIRE = {
    "beef_slices":   ["우삼겹", "삼겹양지", "차돌양지"],
    "beef_stew":     ["양지", "국거리"],
    "x_chadol":      ["차돌"],
    "beef_patty":    ["다짐", "민찌", "분쇄"],
    "x_ffd92fa2a9":  ["다짐", "민찌", "분쇄"],
    "beef_bulgogi":  ["불고기"],
    "beef_cube_steak": ["큐브"],
    "kv_4401":       ["등심"],
    "beef_bone_sagol": ["사골"],
    "beef_bone_misc":  ["잡뼈", "사골잡뼈"],
    "beef_bone_foot":  ["우족"],
    "beef_oxtail":     ["꼬리"],
    "pork_loin_tangsuyuk": ["등심"],
    "pork_loin_donkasu":   ["등심", "돈까스"],
    "x_2255eba1be":  ["등심"],
    "x_9470ee444a":  ["등심"],
    "pork_belly_import":   ["삼겹"],
    "pork_front_leg":  ["앞다리", "전지"],
    "x_1294333d76":    ["앞다리", "전지"],
    "x_e6d782c93c":  ["다짐", "민찌", "분쇄"],
    "x_2458074f8e":  ["등뼈", "목뼈", "감자탕"],
    "pork_trotter":  ["족발"],
    "x_hangjeong":   ["항정"],
    "pork_stomach":  ["오소리"],
    "x_80a38156df":  ["오돌뼈", "오도독"],
    "chicken_parts": ["봉", "윙", "날개", "콤보"],
    "chicken_boneless": ["다리살", "정육"],
    "chicken_leg_import": ["다리살", "정육"],
    "chicken_breast": ["가슴살"],
    "chicken_feet_bone": ["닭발"],
    "chicken_feet":  ["닭발"],
    "raw_chicken_10": ["염지", "치킨", "통닭"],
    "raw_chicken_8":  ["염지", "치킨", "통닭"],
}


def grade(name):
    p = (name or "").split(" - ")
    if len(p) < 2:
        return None
    last = p[-1].strip()
    return None if ("|" in last or not last) else last


def cp_kg(name):
    """상품명에서 총 중량(kg). 못 읽으면 None.

    ⚠️ 'N개/세트/팩'을 무조건 곱하지 않는다. 쿠팡은 `3KG/냉장, 3개`처럼
       총량 뒤에 소분 수량을 붙여 파는 경우가 많아, 곱하면 3배 뻥튀기된다
       (국내산닭날개 3KG,3개 → 9kg → 2,500원/kg 오류, 2026-07-25).
       `1kg X 5팩` `500g*10` `1kg(1개), 10개` 처럼 **단위중량 × 수량**이
       명시된 묶음일 때만 곱한다."""
    s = name.replace(",", "")
    mm = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g)\s*[x*(]\s*.*?(\d+)\s*(?:개|팩|입|ea)", s, re.I)
    if mm:
        unit = float(mm.group(1)) / (1000.0 if mm.group(2).lower() == "g" else 1.0)
        kg = unit * int(mm.group(3))
        return kg if 0.05 <= kg <= 60 else None
    m = re.findall(r"(\d+(?:\.\d+)?)\s*(kg|g)\b", s, re.I)
    if not m:
        return None
    v, u = m[-1]
    kg = float(v) / (1000.0 if u.lower() == "g" else 1.0)
    return kg if 0.05 <= kg <= 50 else None


def cp_origin(name):
    for k in ("국내산", "국산", "한우", "육우", "미국산", "호주산", "뉴질랜드산",
              "멕시코산", "캐나다산", "브라질산", "스페인산", "칠레산", "독일산", "네덜란드산"):
        if k in name:
            return k
    return None


def main():
    dry = "--apply" not in sys.argv
    mb = json.load(io.open(MB, encoding="utf-8"))
    for r in mb:
        r["등급"] = grade(r.get("상품명"))

    if not dry:
        bak = DB + ".bak-20260725-pricetable"
        shutil.copy2(DB, bak)
        print("백업:", os.path.basename(bak))

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript(DDL)

    n_rows = n_def = 0
    print("\n%-22s %6s %10s   %s" % ("재료", "행수", "기본값", "기본 행 키"))
    print("-" * 96)

    for key, parts, wform, defkinds, cpkws in MAPPING:
        row = cur.execute("select name, base_unit from ingredients where ingredient_key=?",
                          (key,)).fetchone()
        if not row:
            print("  ! %s — DB에 없는 재료키" % key)
            continue
        name, unit = row
        kinds = BEEF | PORK | CHICK
        cand = [r for r in mb if r.get("부위") in parts and r.get("축종") in kinds
                and r.get("원per_kg") and r.get("부위") not in DROP_PARTS]
        must = NAME_MUST.get(key)
        if must:
            cand = [r for r in cand if must.search(r.get("상품명") or "")]

        # 그룹별 최저 1건 — 도매(원물/세절) · 도소매(낱개)
        buckets = collections.defaultdict(list)
        for r in cand:
            wset = wform if isinstance(wform, (set, frozenset)) else {wform}
            if r["가공방법"] in wset:        # 지정 형태만 도매로 본다.
                tier = "도매"                #  ⚠️ 소고기 '다짐육'에 '원물'을 함께 넣으면
                                            #     통고기(전지 4,950)가 잡힌다. 재료마다 형태를 지정한다.
            elif r["가공방법"] == "낱개":
                tier = "도소매"
            else:
                continue
            buckets[(tier, r["축종"], r["원산지"], r["부위"], r["등급"], r["가공방법"])].append(r)

        inserted = []
        for k, rs in buckets.items():
            rs.sort(key=lambda r: r["원per_kg"])
            b = rs[0]
            basis = "미트박스 %s %s / %s%s = %s원/kg%s" % (
                STAMP, b.get("상품명"), b.get("가격표기") or "",
                " · 총 %skg" % b["총중량kg"] if b.get("총중량kg") else "",
                f"{b['원per_kg']:,}",
                " ⚠️%s" % b["대량조건"] if b.get("대량조건") else "")
            inserted.append((key, k[0], k[1], k[2], k[3], k[4], b.get("브랜드"), k[5],
                             b["원per_kg"], b.get("총중량kg"),
                             1 if b.get("대량상품") else 0, b.get("대량조건"),
                             "미트박스", basis, b.get("링크"), 0, STAMP))

        # 소매 유효범위 = 도매 최저가 기준. 소매는 도매보다 싸면 오매칭/파싱오류,
        # 5배 넘으면 소포장 튐. 그 밖은 채택하지 않는다(2026-07-25 닭날개 2,500 사고).
        dom_prices = [t[8] for t in inserted if t[1] == "도매"]
        dom_lo = min(dom_prices) if dom_prices else None

        # 쿠팡 소매 — 원산지별 최저 1건(로켓 우선)
        require = RETAIL_REQUIRE.get(key)
        excl = RETAIL_EXCLUDE.get(key, [])
        is_beef = bool(defkinds & BEEF)   # 소 재료 → 돼지 표식 상품 제외
        is_pork = bool(defkinds & PORK)   # 돼지 재료 → 소 표식 상품 제외
        for kw in cpkws:
            p = os.path.join(CP, kw + ".json")
            if not os.path.exists(p):
                continue
            byo = {}
            for it in json.load(io.open(p, encoding="utf-8"))["items"]:
                nm = it["name"]
                if BAD_CP.search(nm):
                    continue
                # 오매칭 방지: 상품명에 재료 핵심어가 없으면 버린다(삼겹살↔뒷고기모듬 등).
                if require and not any(t in nm for t in require):
                    continue
                # 교차오염 제외: 다른 축종 표식(돼지↔소) 상품 버린다(차돌박이↔한돈차돌 등).
                if is_beef and PORK_MARK.search(nm):
                    continue
                if is_pork and BEEF_MARK.search(nm):
                    continue
                # 부위 혼동 제외: 등심↔안심, 양지↔사태.
                if excl and any(t in nm for t in excl):
                    continue
                kg = cp_kg(nm)
                if not kg:
                    continue
                pk = round(it["price"] / kg)
                o = cp_origin(nm) or "미표기"
                # 소매 유효범위: 도매 최저가보다 싸거나 5배 넘으면 오매칭/파싱오류로 버린다.
                if dom_lo and (pk < dom_lo or pk > dom_lo * 5):
                    continue
                curbest = byo.get(o)
                # 로켓 우선, 그다음 원/kg
                score = (0 if it["rocket"] else 1, pk)
                if not curbest or score < curbest[0]:
                    byo[o] = (score, it, kg, pk)
            for o, (_, it, kg, pk) in byo.items():
                basis = "쿠팡 %s %s%s / %s원 · %skg = %s원/kg" % (
                    STAMP, "로켓 " if it["rocket"] else "", it["name"],
                    f"{it['price']:,}", kg, f"{pk:,}")
                inserted.append((key, "소매", None, o, None, None, None,
                                 "로켓" if it["rocket"] else "일반",
                                 pk, kg, 0, None, "쿠팡", basis, it["url"], 0, STAMP))

        if not inserted:
            print("  ! %s — 후보 없음" % name)
            continue

        # 기본 행 = 도매 중 지정 축종의 최저가
        dom = [t for t in inserted if t[1] == "도매" and t[2] in defkinds]
        best = min(dom, key=lambda t: t[8]) if dom else min(
            [t for t in inserted if t[1] == "도매"] or inserted, key=lambda t: t[8])
        inserted = [tuple(list(t[:15]) + [1 if t is best else 0, t[16]]) for t in inserted]

        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source in ('미트박스','쿠팡')", (key,))
            cur.executemany(
                "insert or replace into ingredient_price(ingredient_key,tier,kind,origin,part,"
                "grade,brand,form,price,pack_kg,bulk_only,bulk_note,source,basis,url,"
                "is_default,checked_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", inserted)
            if unit == "kg":
                cur.execute("update ingredients set wholesale_price=?, updated_at=? "
                            "where ingredient_key=?", (best[8], STAMP, key))
        n_rows += len(inserted)
        n_def += 1
        print("%-22s %6d %10s   (%s·%s)(%s)(%s) %s" % (
            name, len(inserted), f"{best[8]:,}", best[2], best[3], best[4],
            best[5] or "-", best[7]))
        if dry:  # 소매 근거 상품 확인용(미리보기 전용)
            retail = [t for t in inserted if t[1] == "소매"]
            if retail:
                for t in sorted(retail, key=lambda t: t[8]):
                    print("        └ 소매 %-6s %9s원/kg  %s" % (t[3], f"{t[8]:,}", t[13]))
            else:
                print("        └ 소매 후보 없음")

    if dry:
        print("\n※ 미리보기다. 쓰려면  python scripts/ingredient_price_init.py --apply")
    else:
        con.commit()
        print("\n표에 %d행 · 재료 %d종 기본값 동기화 완료." % (n_rows, n_def))


main()
