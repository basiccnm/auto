# -*- coding: utf-8 -*-
"""재료별 쿠팡 소매가·최소 판매단위 수집 (2026-07-26 신설)

왜 필요한가 (대표 지시):
  · **도매 = 식봄**(업소용 대용량) / **소매 = 쿠팡**(소포장) 이 원칙이다.
  · 소매를 쿠팡으로 잡아야 **실제 최소 판매 단위**(500g·300g)를 알 수 있다.
    지금은 그걸 몰라서 `pack_of()` 가 전부 "500g 팩"으로 찍고 있다(기본값 = 추측).
  · 상품이 붙으면 소매가·팩용량·딥링크가 **한꺼번에** 나온다.

수집만 한다 — DB 반영은 사람이 관리자 화면에서 고른 뒤에 한다.

    python scripts/coupang_ingredient.py --budget=60        # API 60회까지
    python scripts/coupang_ingredient.py --only=생닭         # 이름에 포함된 것만
    python scripts/coupang_ingredient.py --min-uses=5        # 5개 이상 메뉴에 쓰는 것만

⚠️ 상품명에서 용량을 읽을 때 **배수 표기**를 반드시 반영한다("500g 2개입" = 1kg).
   식봄 캐시가 그걸 안 해서 단가 3,260행이 틀렸다(2026-07-25 사고).
"""
import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mealkit_run import DOMAIN, PATH, load_env, sign  # 서명·호출은 검증된 것을 재사용

# 🔴 쿠팡 API 는 limit 최대 10 이다 — 20·50 을 넣으면 rCode=400 "limit is out of range"
#    로 **빈 배열이 조용히 돌아온다**(2026-07-26 확인). 그래서 후보를 넓히려면 limit 이
#    아니라 **검색어를 여러 개** 써야 한다.
#    재료명만 검색하면 양파·양배추 상위가 전부 10~20kg 업소용이라 가정용 소포장이
#    후보에 안 들어온다. 그래서 크기 힌트를 붙인 두 번째 검색어를 함께 쓴다.
SEARCH_LIMIT = 10


def api_search(keyword, ak, sk):
    import ssl
    import urllib.parse
    import urllib.request
    url_path = "%s?keyword=%s&limit=%d" % (PATH, urllib.parse.quote(keyword), SEARCH_LIMIT)
    req = urllib.request.Request(DOMAIN + url_path, method="GET")
    req.add_header("Authorization", sign("GET", url_path, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "ingredient_retail.json")
# 재료명 ≠ 쿠팡 검색어인 경우의 교체표. 재료명 그대로 검색하면 엉뚱한 게 나오는 것들.
#  예: 재료명 "토마토소스"의 24개 메뉴가 전부 피자 → 실제로 필요한 건 "피자소스"다.
#      그대로 검색해서 유아용 파스타소스·토마토퓨레가 잡혔다(2026-07-26).
KWMAP_PATH = os.path.join(BASE, "data", "research", "coupang_keyword.json")
CACHE = os.path.join(BASE, "data", "research", "coupang_ing")
os.makedirs(CACHE, exist_ok=True)

# ── 용량 파싱 (공통모듈 foodspring 의 고친 파서와 같은 규칙) ──────────
_UNIT = {"kg": 1.0, "g": 0.001, "l": 1.0, "ml": 0.001}
_MULT = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*x×X]?\s*(\d+)\s*"
                   r"(?:개입|개|입|팩|봉지|봉|매|장|ea|병|캔|포|pack)", re.I)
_BOX = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g)\s*/\s*(?:box|박스)", re.I)
_PAREN = re.compile(r"[(\[]\s*(\d+(?:\.\d+)?)\s*(kg|g)\s*[)\]]", re.I)
_KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
_G = re.compile(r"(\d+(?:\.\d+)?)\s*g(?![a-z가-힣])", re.I)
_ML = re.compile(r"(\d+(?:\.\d+)?)\s*ml(?![a-z가-힣])", re.I)
_L = re.compile(r"(\d+(?:\.\d+)?)\s*l(?![a-z가-힣0-9])", re.I)


def pack_kg(name):
    n = (name or "").replace(",", "")
    cands = []
    for rx, how in ((_MULT, "배수"),):
        m = rx.search(n)
        if m:
            cands.append((float(m.group(1)) * _UNIT[m.group(2).lower()] * int(m.group(3)), how))
    for rx, how in ((_BOX, "BOX총량"), (_PAREN, "괄호총량")):
        m = rx.search(n)
        if m:
            cands.append((float(m.group(1)) * _UNIT[m.group(2).lower()], how))
    if cands:
        return max(cands)
    for rx, mul, how in ((_KG, 1.0, "kg"), (_G, 0.001, "g"), (_L, 1.0, "L"), (_ML, 0.001, "ml")):
        m = rx.search(n)
        if m:
            return float(m.group(1)) * mul, how
    return None, None


# 가정용으로 볼 최대 크기(kg/L). 이걸 넘으면 업소용 취급 — 소매 후보에서 뒤로 밀린다.
#  2kg 로 잡은 근거: 마트 소포장이 보통 300g~1.5kg 이고, 쌀·밀가루만 2kg 대가 흔하다.
HOME_MAX_KG = 2.0

# 🚨 쿠팡 API 한도는 **분당 50회**다. 정지되면 밀키트까지 전부 막힌다(대표 경고 2026-07-26).
#    · 재료당 **1회만** 호출한다. 검색어를 늘려 호출을 두 배로 만들지 말 것.
#    · **병렬 금지.** 순차로만 돌린다.
#    · 2초 간격 = 분당 30회. 한도의 60%만 쓴다(1.5초=40회는 여유가 얇다).
#    가정용 후보를 못 찾은 재료는 나중에 --refine 으로 **그것만** 다시 찾는다.
SLEEP_SEC = 2.0
KWMAP = {}          # main() 에서 채운다

# 먹는 게 아닌 재료 — 소매가·링크 대상이 아니다(대표 지시: "다 먹을꺼만 붙여")
NOT_FOOD = re.compile(r"(컵|뚜껑|빨대|포장|용기|봉투|박스|비닐|랩\b|호일|이쑤시개|물티슈|"
                      r"나무젓가락|숟가락|포크|트레이|캐리어|스티커|영수지|영수증)")

# 재료로 쓸 수 없는 것 — 상품명에 있으면 버린다
EXCLUDE = re.compile(
    r"(교환권|상품권|기프[트티]|쿠폰|바우처|금액권|"
    r"사료|간식캔|장난감|굿즈|의류|양말|욕실|세제|비누|섬유유연제|"
    r"강아지|반려견|반려묘|애견|애묘|반려동물|고양이|펫\b|"
    r"영양제|비타민|유산균|콜라겐|다이어트\s*보조|"
    r"밀폐용기|그릇|접시|수세미|도마|칼\b|주방장갑|위생장갑|"
    r"체험단|리뷰|샘플|중고)", re.I)


def norm(s):
    return re.sub(r"[^0-9a-z가-힣]", "", (s or "").lower())


def plain(name):
    """브랜드·용량을 뗀 검색용 이름 — 재료 페이지에서 쓰는 것과 같은 규칙."""
    s = re.sub(r"\([^)]*\)", " ", name or "")
    s = re.sub(r"\d+(\.\d+)?\s*(kg|g|l|ml|개입|개|매|장|봉|팩)", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


# 🔴 가공형태 — 원물 재료를 찾을 때 이게 붙은 상품은 다른 물건이다(대표 지적 2026-07-26).
#    "양파즙·양파가루는 양파가 아니다." 그래서 **재료명에 없는** 가공형태만 걸러낸다.
#    재료 자체가 가공품이면(튀김가루·고춧가루) '가루'를 빼면 안 되므로 동적으로 판단한다.
#    ⚠️ '냉동'·'냉장'은 형태가 아니라 보관법이라 제외하지 않는다(냉동 원물은 정상).
PROCESSED = ["즙", "가루", "분말", "파우더", "피클", "절임", "장아찌", "엑기스", "진액",
             "환", "청", "후레이크", "플레이크", "칩", "링", "튀김", "소스", "양념",
             "시즈닝", "드레싱", "잼", "퓨레", "시럽", "통조림", "건조", "말린", "구운",
             "볶은", "조미", "농축", "차\\b", "캡슐", "정제", "젤리", "과자"]


# 🔴 프리미엄·특수 라벨 — 일반 상품이 아니라 기준가로 쓰면 안 된다(대표 지적 2026-07-26).
#    "저당"이라는 말이 붙었다는 것 자체가 이미 다이어트용 특수 제품이라는 뜻이다.
#    버리지는 않고 **후순위로 미룬다** — 일반 상품이 없으면 그거라도 써야 하니까.
PREMIUM = re.compile(
    r"(저당|저칼로리|무설탕|제로|다이어트|글루텐프리|"
    r"유기농|친환경|무항생제|동물복지|무agri|non-?gmo|"
    r"프리미엄|명품|수제|장인|한정|특선|명가|1등급|무료배송)", re.I)


def ban_re(ing_name):
    """이 재료를 찾을 때 상품명에 있으면 버릴 단어들."""
    bad = [w for w in PROCESSED if w.replace("\\b", "") not in (ing_name or "")]
    return re.compile("|".join(bad)) if bad else None


def score(it, want_norm, ban=None):
    """상품이 이 재료로 쓸 만한가. 이름이 실제로 겹쳐야 채택한다."""
    nm = it.get("productName") or ""
    if EXCLUDE.search(nm):
        return None
    if ban and ban.search(nm):
        return None
    nn = norm(nm)
    # 재료명 토큰이 하나라도 상품명에 있어야 한다(엉뚱한 매칭 방지)
    hit = sum(1 for t in want_norm if t and t in nn)
    if not hit:
        return None
    kg, how = pack_kg(nm)
    price = it.get("productPrice")
    if not price:
        return None
    # 🔴 용량을 못 읽어도 **버리지 않는다**(2026-07-26 대표 지적).
    #    로켓 상품은 상품명에 용량이 거의 없다("[로켓프레시] 국내산 깐양파 2개입").
    #    전엔 용량 없으면 탈락시켜서 **로켓 소포장이 전부 버려지고** 용량이 적힌
    #    5~10kg 대용량 일반 상품만 후보로 남았다. 장보기(소매)인데 대용량을 고른 셈.
    #    용량은 검수 화면에서 사람이 넣는다 — 추측으로 채우지 않는다.
    wpk = round(price / kg) if (kg and kg > 0) else None
    if wpk is not None and wpk < 200:   # 비현실적으로 싼 것 = 용량 파싱 오류 의심
        kg, how, wpk = None, None, None
    return {
        "product_id": it.get("productId"),
        "name": nm,
        "price": price,
        "pack_kg": round(kg, 4) if kg else None,
        "pack_how": how,
        "won_per_kg": wpk,
        "premium": 1 if PREMIUM.search(nm) else 0,
        "rocket": 1 if it.get("isRocket") else 0,
        "image": it.get("productImage"),
        "url": it.get("productUrl"),
        "hit": hit,
    }


def main():
    args = sys.argv[1:]
    budget = next((int(a.split("=")[1]) for a in args if a.startswith("--budget=")), 40)
    only = next((a.split("=", 1)[1] for a in args if a.startswith("--only=")), None)
    min_uses = next((int(a.split("=")[1]) for a in args if a.startswith("--min-uses=")), 1)
    # 🔴 --refine: 1차에서 후보 0개인 재료만 **크기 힌트를 붙여** 다시 찾는다.
    #    원인: 쿠팡 검색 결과의 productName 에 **용량이 없는 경우가 많다**("백설 튀김가루").
    #    용량은 옵션에 있어서 이름에 안 나온다 → kg당 단가를 계산할 수 없어 전부 탈락했다.
    #    검색어에 "1kg" 같은 힌트를 넣으면 이름에 용량이 붙은 상품이 올라온다.
    #    호출을 두 배로 늘리지 않기 위해 **실패한 것만** 대상으로 한다(쿠팡 분당 50회 한도).
    refine = "--refine" in args

    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")
    if not ak or not sk:
        print("❌ .env 에 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없다.")
        return 1

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [r for r in c.execute("""select i.ingredient_key k, i.name, i.base_unit,
        i.wholesale_price w, i.manual_price m,
        (select count(*) from menu_ingredients mi where mi.ingredient_key=i.ingredient_key) uses
      from ingredients i
      where (select count(*) from menu_ingredients mi where mi.ingredient_key=i.ingredient_key) >= ?
      order by uses desc""", (min_uses,))]
    if only:
        rows = [r for r in rows if only in r["name"]]

    global KWMAP
    KWMAP = {}
    if os.path.exists(KWMAP_PATH):
        KWMAP = {k: v for k, v in json.load(io.open(KWMAP_PATH, encoding="utf-8")).items()
                 if not k.startswith("_")}
        print("검색어 교체표 %d건" % len(KWMAP))

    res = {}
    if os.path.exists(OUT):
        res = json.load(io.open(OUT, encoding="utf-8"))

    used = 0
    print("대상 재료 %d개 · API 예산 %d회" % (len(rows), budget))
    for r in rows:
        key = r["k"]
        if key in res and res[key].get("cands"):
            continue
        if refine and key in res and res[key].get("refined"):
            continue          # 2차까지 해본 것은 건너뜀
        if not refine and key in res:
            continue          # 1차는 아직 안 본 재료만
        # 🔴 먹는 것만 붙인다(대표 지시 2026-07-26). 포장·소모품은 링크도 소매가도 의미가 없다.
        if NOT_FOOD.search(r["name"] or ""):
            print("  %-26s (먹는 게 아니라 건너뜀)" % r["name"][:26])
            continue
        # 교체표에 있으면 그 검색어를 쓴다(재료명 ≠ 상품명인 경우)
        kw = KWMAP.get(key) or KWMAP.get(r["name"]) or plain(r["name"])
        if not kw:
            continue
        hint = {"kg": "1kg", "L": "1L"}.get(r["base_unit"], "개입")
        if refine:
            # 크기 힌트를 붙여 이름에 용량이 나오는 상품을 끌어온다
            kw = "%s %s" % (kw, hint)

        def _cp(k):
            return os.path.join(CACHE, re.sub(r"[^0-9A-Za-z가-힣]+", "_", k)[:60] + ".json")

        # 이미 받아둔 캐시는 **평이름·힌트이름 둘 다** 읽어 합친다.
        #  1차(평이름)와 2차(--refine, 힌트이름)가 서로 다른 파일에 저장되므로, 합치면
        #  API 호출 없이 후보가 넓어진다. 재정렬만 하고 싶을 때 --budget=0 으로 돌리면 된다.
        cp = _cp(kw)
        items, from_cache = [], False
        # 🔴 교체표를 썼으면 **그 검색어 캐시만** 읽는다.
        #    옛 재료명 캐시를 같이 읽으면 판정 토큰(새 검색어)과 안 맞아 전부 탈락한다
        #    — 토마토소스가 그래서 후보 0개가 됐다(2026-07-26).
        overridden = bool(KWMAP.get(key) or KWMAP.get(r["name"]))
        _try = [kw] if overridden else [kw, plain(r["name"]), "%s %s" % (plain(r["name"]), hint)]
        for cand_kw in dict.fromkeys(_try):
            fp = _cp(cand_kw)
            if os.path.exists(fp):
                items += json.load(io.open(fp, encoding="utf-8")).get("items", [])
                from_cache = True
        if from_cache:
            # productId 로 중복 제거
            seen_id, uniq = set(), []
            for it in items:
                pid = it.get("productId")
                if pid in seen_id:
                    continue
                seen_id.add(pid)
                uniq.append(it)
            items = uniq
        else:
            if used >= budget:
                print("  (예산 소진 — 남은 재료는 다음 실행에서)")
                break
            try:
                body = api_search(kw, ak, sk)
                used += 1
            except urllib.error.HTTPError as e:
                print("  [HTTP %s] %s — 중단(쿠팡 API 정지 위험)" % (e.code, kw))
                break
            except Exception as e:
                print("  [ERR] %s %s — 중단" % (kw, str(e)[:60]))
                break
            # 🔴 rCode 를 반드시 본다. 400 이면 빈 배열이 조용히 오는데, 그걸 캐시에
            #    저장해버리면 "후보 0개"가 영구히 굳는다(2026-07-26 실제로 5건 그렇게 됐다).
            if str(body.get("rCode")) != "0":
                print("  [rCode %s] %s : %s — 중단" % (
                    body.get("rCode"), kw, (body.get("rMessage") or "")[:60]))
                break
            items = (body.get("data") or {}).get("productData") or []
            if not items:
                print("  %-26s 결과 0건 (캐시에 저장하지 않음)" % r["name"][:26])
                continue
            with io.open(cp, "w", encoding="utf-8") as f:
                json.dump({"keyword": kw, "items": items}, f, ensure_ascii=False)
            # 쿠팡 API 정지를 피하는 게 최우선이다. 속도보다 안전.
            time.sleep(SLEEP_SEC)

        # 🔴 매칭 토큰은 **재료명에서만** 뽑는다 — 검색어(kw)에서 뽑으면 안 된다(2026-07-26 사고).
        #    --refine 이 검색어에 "1kg" 힌트를 붙이는데, 그걸 토큰에 넣으면 상품명에 "1kg"만
        #    있어도 hit=1 로 통과한다. 그래서 재료와 무관한 상품이 후보로 잡혀 "후보 확보 254개"라는
        #    거짓 숫자가 나왔다(실제 181개). 힌트는 **검색에만** 쓰고 판정에는 쓰지 않는다.
        # 교체표를 썼으면 판정 토큰도 그 검색어에서 뽑아야 한다 — "토마토소스"로 판정하면
        # "피자소스" 상품이 전부 탈락한다.
        base_name = KWMAP.get(key) or KWMAP.get(r["name"]) or plain(r["name"])
        # "쌀"·"김"처럼 한 글자 재료가 통째로 빠지던 문제 — 짧으면 그대로 쓴다
        want = [t for t in re.split(r"[\s/]+", base_name) if len(t) >= 2] or [base_name]
        want_norm = [norm(t) for t in want]
        ban = ban_re(r["name"])
        cands = [x for x in (score(it, want_norm, ban) for it in items) if x]
        # 🔴 소매는 **가정용 최소 단위**를 골라야 한다(2026-07-26).
        #    kg당 최저가로 뽑으면 양파 20kg 박스·식용유 18L 같은 업소용이 1순위가 된다.
        #    그건 도매(식봄)가 할 일이고, 여기서 필요한 건 "집에서 한 번 만들려면 얼마짜리를
        #    사야 하나" 다. 그래서 가정용 크기를 우선하고, 그 안에서 kg당 싼 것을 본다.
        #  ⚠️ "제일 작은 것"도 답이 아니다 — 치킨무 170g 이 50,529원/kg 으로 잡힌다(바가지 소포장).
        #     그래서 후보들의 kg당 단가 **중앙값의 2.5배를 넘는 것은 버리고**, 살아남은 것 중
        #     가장 작은 팩을 고른다. 이게 "사람이 실제로 집어드는 크기"에 가장 가깝다.
        if cands:
            vals = sorted(x["won_per_kg"] for x in cands if x["won_per_kg"])
            med = vals[len(vals) // 2] if vals else None
            for x in cands:
                x["home"] = 1 if (x["pack_kg"] and x["pack_kg"] <= HOME_MAX_KG) else 0
                x["ripoff"] = 1 if (med and x["won_per_kg"] and x["won_per_kg"] > med * 2.5) else 0
            # 🔴 우선순위 (대표 확정 2026-07-26):
            #    ① 로켓 + 가정용   ② 가정용 일반   ③ 로켓 대용량   ④ 나머지
            #    "콩나물 400g은 일반이 팔고 로켓은 500g만 팔면 **무조건 로켓**" —
            #    즉 크기가 조금 달라도 로켓이 이긴다. 로켓이어야 실제로 집에서 받아볼 수 있고
            #    배송비가 안 붙어 소매가가 왜곡되지 않는다.
            #    단 로켓에 대용량밖에 없으면(예: 10kg) 가정용 일반으로 내려간다 —
            #    그때는 "최소 장보기 단위"를 알아내는 목적이 더 중요하다.
            #    ⚠️ 판매자로켓(로켓그로스)은 API 의 isRocket 에 안 잡히는 경우가 있다.
            #       그건 검수 화면에서 사람이 보고 고른다.
            # 🔴 장보기(소매)는 **한 번에 내는 돈이 제일 싼 것**이 기준이다(대표 지시 2026-07-26).
            #    "양파를 보고 제일 싼 걸 가져와야지" — kg당 단가로 뽑으면 5~10kg 박스가 이긴다.
            #    소량 사는 사람에게는 총 가격이 기준이다.
            #    순서: ①로켓 ②이름 일치도 ③총 가격 최저
            #  프리미엄 라벨(저당·유기농·무항생제…)은 일반 상품 뒤로 미룬다
            cands.sort(key=lambda x: (x.get("premium", 0), not x["rocket"], -x["hit"], x["price"]))
        res[key] = {"name": r["name"], "keyword": kw, "uses": r["uses"],
                    "base_unit": r["base_unit"], "now_wholesale": r["w"], "now_retail": r["m"],
                    "cands": cands[:5], "refined": 1 if refine else 0}
        top = cands[0] if cands else None
        print("  %-26s %2d메뉴 → 후보 %d개%s" % (
            r["name"][:26], r["uses"], len(cands),
            ("  ①%s원 %s %s%s" % (format(int(top["price"]), ","),
                                  "로켓" if top["rocket"] else "일반",
                                  ("%gkg " % top["pack_kg"]) if top["pack_kg"] else "(용량모름) ",
                                  top["name"][:30])) if top else ""))

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    done = sum(1 for v in res.values() if v.get("cands"))
    print()
    print("API %d회 사용 · 후보 확보 %d/%d 재료 → %s" % (used, done, len(res), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
