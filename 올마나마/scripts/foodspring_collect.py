# -*- coding: utf-8 -*-
"""식봄(foodspring, 중계 플랫폼) 채소·기타 시세 수집 — GraphQL.

식봄은 업체 수백 곳이 들어온 중계몰이라 한 품목에 수백 상품이 뜬다 → 최저가가 좋다.
GraphQL 을 사이트의 거대한 쿼리(19KB) 대신 **필요한 필드만** 담은 최소 쿼리로 호출한다.
  POST https://api.foodspring.co.kr/v2/graphql
  goodsSearch(first, input:{keyword, sort}, areaId){ edges{ node{ name origin price{salePrice} } } }

가격은 `salePrice` = **상시 판매가**(업체 경쟁가). 정가도 쿠폰가도 아니다.
  - 쿠폰가: 첫구매 미끼라 무의미(대표 확인). 안 쓴다.
  - salePrice 가 곧 우리가 쓸 값.

⚠️ areaId(지역)에 따라 가격이 다르다. area_324 기준(사이트 게스트 기본값).
⚠️ '샘플'(200g, 500~1000원) 상품 제외. 중량 파싱 안 되는 건 원/kg 없이 둔다(추측 금지).
⚠️ 고기는 이 소스로 안 쓴다 — 오매칭(삼겹살↔김치)·봉단위 혼란이 심해 미트박스가 낫다.
   채소·과일·쌀·가공 위주로만 쓴다.
"""
import json, os, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "data", "research", "foodspring")
API = "https://api.foodspring.co.kr/v2/graphql"
AREA = "area_324"
GAP = 2.0

# 최소 필드만. origin·vendor·pricePerQuantity 는 스키마 모양이 달라 통째로 에러난다.
# 원산지는 상품명에서 파싱하므로 name + salePrice 면 충분하다.
QUERY = ("query($input:GoodsSearchInput!,$areaId:ID){"
         "goodsSearch(first:80,input:$input,areaId:$areaId){"
         "totalCount edges{node{name price{salePrice}}}}}")

ORIGINS = ["중국산", "미국산", "호주산", "칠레산", "뉴질랜드산", "필리핀산", "베트남산",
           "태국산", "페루산", "이집트산", "스페인산", "멕시코산", "덴마크산", "독일산",
           "네덜란드산", "국내산", "국산", "수입산", "수입"]
GRADE = re.compile(r"[\(\[]\s*(특|상|중|하|왕특|대|중대|소|1번|2번|3번)\s*[_)\]/]")
KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
G = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I)

# ── 총중량 파싱 (2026-07-25 버그수정) ─────────────────────────────
#  🔴 전엔 이름의 **첫 kg/g 숫자만** 읽어서, "5kg2팩"·"2.5kg*6입 15Kg/BOX" 같은
#     묶음 상품의 won_per_kg 가 통째로 틀렸다. 캐시 고유 상품 **562건**이 오염됐고,
#     우리는 "받을 수 있는 최저가"를 쓰기 때문에 **버그로 낮게 나온 행이 자동 채택**됐다.
#     (예: 국내산 돈등심이 1,800원/kg 으로 잡혀 최저가로 뽑힘)
#  · 배수 표기: "5kg2팩" · "2.5kg*6입" · "500Gx20봉지" · "1L x 12개입" · "150g*10입"
#  · 괄호/슬래시 총량: "(10kg)" · "15Kg/BOX"
#  · ⚠️ "1.8kg (10매)" 처럼 **괄호 앞에서 끊기는 것은 배수가 아니다**(1.8kg 안의 장수).
#       그래서 배수 정규식은 괄호를 건너뛰지 않는다. 이 구분이 핵심이다.
_UNIT_KG = {"kg": 1.0, "g": 0.001, "l": 1.0, "ml": 0.001}   # L은 물 밀도 1로 근사
_MULT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*x×X]?\s*(\d+)\s*"
    r"(?:개입|개|입|팩|봉지|봉|매|장|ea|병|캔|포|pack)", re.I)
#  🔴 2026-08-02: 「삼립 모카빵 생지 (165g*10)」 처럼 **뒤에 단위말이 없는 배수**를 놓쳤다.
#     0.165kg 으로 읽혀 63,030원/kg (실제 6,303원) — 10배. 위 _MULT 는 개·입·봉 같은
#     꼬리말을 요구한다. 여기서는 `*`·`x` 를 **반드시** 끼고 있을 때만 배수로 본다.
#     ⚠️ 구분이 핵심이다 — "1.8kg (10매)" 는 곱셈기호가 없으니 여기 안 걸린다(그건 총량 안의 장수).
_MULT_BARE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*x×X]\s*(\d+)(?![0-9a-z가-힣])", re.I)
_BOX = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g)\s*/\s*(?:box|박스)", re.I)
_PAREN = re.compile(r"[(\[]\s*(\d+(?:\.\d+)?)\s*(kg|g)\s*[)\]]", re.I)
#  🔴 «1봉 가격»·«낱개 가격» — **가격 기준이 낱개**라고 이름에 적힌 것(2026-08-02 신설).
#     이게 있으면 총량 배수를 쓰면 안 된다. 실제로
#     「BOX_고구마치즈고로케 600gx12봉_1봉 가격」 을 7.2kg 으로 읽어 722원/kg 이 됐다(실제 8,667원).
_PER_UNIT = re.compile(r"(?:1|한)\s*(?:봉|팩|개|입|ea)\s*(?:당\s*)?가격|낱개\s*가격|개당\s*가격", re.I)
#  액체 폴백 — 이게 없어서 「사골육수 1.8L」 같은 행이 통째로 0원/kg 이 됐다(2026-08-02)
_L = re.compile(r"(\d+(?:\.\d+)?)\s*(?:l|ℓ|리터)(?![a-z가-힣0-9])", re.I)
_ML = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ml|㎜)(?![a-z가-힣0-9])", re.I)


def pack_kg(name):
    """상품명에서 **총 중량(kg)** 을 뽑는다. (kg, 어떻게 구했는지) 튜플 반환.

    후보를 여러 개 만들고 **가장 큰 값**을 쓴다 — 총중량은 늘 부분중량보다 크다.
    """
    n = name.replace(",", "")
    cands = []                                    # (kg, how)
    #  이름이 «1봉 가격» 이라고 말하면 그 말을 따른다 — 총량으로 나누면 배수만큼 싸진다
    per_unit = bool(_PER_UNIT.search(n))
    if per_unit:
        m = KG.search(n)
        if m:
            return float(m.group(1)), "단일 kg·1봉가"
        #  「600gx12봉」처럼 g 뒤에 x·숫자가 붙어도 잡아야 한다 — 여기선 이미 kg 를 먼저
        #  확인했고 «1봉 가격» 이 명시된 상태라, 첫 g 수치가 곧 낱개 중량이다.
        m = re.search(r"(\d+(?:\.\d+)?)\s*g", n, re.I)
        if m:
            return float(m.group(1)) / 1000.0, "단일 g·1봉가"

    for _rx, _tag in ((_MULT, "배수"), (_MULT_BARE, "배수(꼬리말없음)")):
        m = _rx.search(n)
        if m:
            base = float(m.group(1)) * _UNIT_KG[m.group(2).lower()]
            cands.append((base * int(m.group(3)),
                          "%s %s%s×%s" % (_tag, m.group(1), m.group(2), m.group(3))))
    m = _BOX.search(n)
    if m:
        cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "BOX총량 " + m.group(0)))
    m = _PAREN.search(n)
    if m:
        cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "괄호총량 " + m.group(0)))

    if cands:
        kg, how = max(cands)
        return kg, how

    m = KG.search(n)
    if m:
        return float(m.group(1)), "단일 kg"
    m = G.search(n)
    if m:
        return float(m.group(1)) / 1000.0, "단일 g"
    # "500Gx20봉지" 처럼 g 뒤에 바로 글자가 붙어 \b 가 안 걸리는 경우의 마지막 폴백
    m = re.search(r"(\d+(?:\.\d+)?)\s*g(?![a-z가-힣])", n, re.I)
    if m:
        return float(m.group(1)) / 1000.0, "단일 g(경계없음)"
    #  액체는 1L≈1kg 로 본다(밀도 근사). 이게 없으면 L 표기 상품이 통째로 버려진다
    m = _L.search(n)
    if m:
        return float(m.group(1)), "단일 L"
    m = _ML.search(n)
    if m:
        return float(m.group(1)) / 1000.0, "단일 ml"
    return None, None


# 묶음 표기가 이름에 있는데 배수를 못 읽었으면 그 행은 못 믿는다.
_HINT = re.compile(r"\d+\s*(?:개입|입|팩|봉지|봉|매|장|ea|병|캔|포)|/\s*(?:box|박스)", re.I)


def pack_suspect(name, kg, how, won_per_kg):
    """단가를 믿지 못할 이유가 있으면 그 이유를 돌려준다(없으면 None).

    ⚠️ 이 값이 붙은 행은 **최저가 자동 채택에서 빼라.** 계산을 고쳐도 이상치일 수 있다.
    """
    if kg is None:
        return "중량 파싱 실패"
    if how and how.startswith("단일") and _HINT.search(name):
        return "이름에 묶음 표기가 있는데 배수를 못 읽음"
    if won_per_kg is not None and won_per_kg < 300:
        return "kg당 %d원 — 업소용 식자재로 비현실적" % won_per_kg
    return None


def origin_of(name):
    for o in ORIGINS:
        if o in name:
            return ("국산" if o in ("국내산", "국산")
                    else "수입" if o in ("수입산", "수입") else o)
    return None


#  ⚠️ 2026-08-02 — 여기 **옛 `pack_kg` 가 하나 더 있었다.** 파이썬은 나중 정의가 이기므로
#     위(58행)의 고쳐진 파서가 통째로 무시되고 「5kg2팩」 배수가 안 읽혔다.
#     올마나마 식봄 캐시 562건이 그래서 틀렸다. **같은 이름을 두 번 정의하지 말 것.**

def call(keyword, sort="ACCURACY_DESC", origin=None):
    inp = {"keyword": keyword, "sort": sort}
    if origin:                       # origin:"DOMESTIC" → 국산만. 수입 enum 은 막혀 있어 이름으로 판단.
        inp["origin"] = origin
    body = json.dumps({"query": QUERY,
                       "variables": {"input": inp, "areaId": AREA}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Device-Type": "pc",
        "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
        "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    return j["data"]["goodsSearch"]


def search(keyword):
    """두 패스: (1) 국산 필터(DOMESTIC) → origin=국산 확정, (2) 전체 → 수입은 이름으로.
    국산 상품 id 를 국산패스로 확정하고, 전체패스의 나머지는 이름으로 원산지를 본다."""
    dom = {e["node"]["name"] for e in call(keyword, origin="DOMESTIC")["edges"]}
    d = call(keyword)
    rows = []
    for e in d["edges"]:
        n = e["node"]
        name = n["name"]
        if "샘플" in name:
            continue
        sp = (n.get("price") or {}).get("salePrice")
        if not sp:
            continue
        kg, how = pack_kg(name)
        wpk = round(sp / kg) if kg else None
        # 국산 필터에 잡혔으면 국산 확정. 아니면 이름으로(중국산 등). 이름에도 없으면 미표기.
        o = "국산" if name in dom else origin_of(name)
        rows.append({
            "keyword": keyword, "name": name, "sale_price": sp, "origin": o,
            "grade": (GRADE.search(name).group(1) if GRADE.search(name) else None),
            "pack_kg": kg, "pack_how": how,
            "won_per_kg": wpk,
            "suspect": pack_suspect(name, kg, how, wpk),
        })
    return d["totalCount"], rows


# ── 카테고리 수집 (nid 기반) ─────────────────────────────────────
# 검색어는 형태가 섞이지만(마른↔냉동↔생) 카테고리는 형태별로 딱 나뉜다(대표 지시 2026-07-25).
#   goodsCategory(nid){goodsList(sort,first){edges{node{name price{salePrice}}}}}
CAT_QUERY = ("query($nid:Int!,$sort:GoodsSortKind!,$first:Int!){"
             "goodsCategory(nid:$nid){name goodsList(sort:$sort,first:$first){"
             "totalCount edges{node{name price{salePrice}}}}}}")

# 수산 카테고리 nid (2026-07-25 확인). 형태가 확실한 잎 카테고리로 긁는다.
SEAFOOD_CATS = {
    "고등어": 80, "동태": 81, "삼치": 82, "갈치": 83, "꽁치": 84, "조기": 85,
    "코다리": 86, "장어": 87, "오징어": 89, "낙지": 90, "문어": 91, "쭈꾸미": 92,
    "한치": 93, "전복": 95, "소라": 96, "바지락": 97, "홍합": 98,
    "새우": 484, "게": 101, "날치알": 102, "명란알": 103,
    "마른멸치": 105, "건새우": 106, "마른오징어": 107, "쥐포": 108, "어포": 109,
    "마른미역": 111, "건다시마": 112, "파래": 113,
}


def cat_call(nid, sort="POPULAR_DESC", first=80):
    body = json.dumps({"query": CAT_QUERY,
                       "variables": {"nid": nid, "sort": sort, "first": first}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Device-Type": "pc",
        "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
        "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    return j["data"]["goodsCategory"]


def cat_search(nid):
    d = cat_call(nid)
    rows = []
    for e in d["goodsList"]["edges"]:
        n = e["node"]
        name = n["name"]
        if "샘플" in name:
            continue
        sp = (n.get("price") or {}).get("salePrice")
        if not sp:
            continue
        kg, how = pack_kg(name)
        wpk = round(sp / kg) if kg else None
        rows.append({"name": name, "sale_price": sp, "origin": origin_of(name),
                     "grade": (GRADE.search(name).group(1) if GRADE.search(name) else None),
                     "pack_kg": kg, "pack_how": how, "won_per_kg": wpk,
                     "suspect": pack_suspect(name, kg, how, wpk)})
    return d["goodsList"]["totalCount"], rows


def main_cat():
    """카테고리 수집: python foodspring_collect.py --cat  (SEAFOOD_CATS 전부)"""
    os.makedirs(OUTDIR, exist_ok=True)
    out = {}
    for label, nid in SEAFOOD_CATS.items():
        try:
            total, rows = cat_search(nid)
        except Exception as e:
            print("  !! %s(nid %s) %s" % (label, nid, e)); continue
        out[label] = rows
        priced = [r for r in rows if r["won_per_kg"]]
        lo = min(priced, key=lambda r: r["won_per_kg"]) if priced else None
        print("%-10s(nid %3d) 총%4d·파싱%3d · 최저 %s" % (
            label, nid, total, len(priced),
            "%s원/kg %s %s" % (f"{lo['won_per_kg']:,}", lo["origin"] or "-", lo["name"][:26])
            if lo else "환산불가"), flush=True)
        time.sleep(GAP)
    with open(os.path.join(OUTDIR, "_카테고리.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n→ data/research/foodspring/_카테고리.json")


def main():
    if "--cat" in sys.argv:
        return main_cat()
    kws = sys.argv[1:]
    if not kws:
        print("사용법: python scripts/foodspring_collect.py 검색어 [검색어...]")
        print("   또는 python scripts/foodspring_collect.py --file 목록.json")
        return 1
    if kws[0] == "--file":
        kws = json.load(open(kws[1], encoding="utf-8"))

    os.makedirs(OUTDIR, exist_ok=True)
    allrows = {}
    for kw in kws:
        try:
            total, rows = search(kw)
        except urllib.error.HTTPError as e:
            print("  !! %s HTTP %s — 중단" % (kw, e.code)); break
        except Exception as e:
            print("  !! %s %s" % (kw, e)); continue
        allrows[kw] = rows
        priced = [r for r in rows if r["won_per_kg"]]
        lo = min(priced, key=lambda r: r["won_per_kg"]) if priced else None
        print("%-12s 총%4d · 파싱%3d · 최저 %s" % (
            kw, total, len(priced),
            "%s원/kg (%s %s)" % (f"{lo['won_per_kg']:,}", lo["origin"] or "-",
                                 lo["name"][:24]) if lo else "환산불가"),
              flush=True)
        time.sleep(GAP)

    with open(os.path.join(OUTDIR, "_수집.json"), "w", encoding="utf-8") as f:
        json.dump(allrows, f, ensure_ascii=False, indent=1)
    print("\n→ data/research/foodspring/_수집.json")


if __name__ == "__main__":
    main()
