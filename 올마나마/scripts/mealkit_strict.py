# -*- coding: utf-8 -*-
"""밀키트·냉동 후보 수집 — **엄격 매칭판**. 2026-07-25 전면 재작성

## 왜 다시 만드나
1차(mealkit_run.py)는 키워드 폴백("양념 치킨 냉동")으로 뭉뚱그려서
**421건 중 50%가 중복**(한 상품이 최대 14개 메뉴에 붙음)이었고, 엉뚱한 상품이 섞였다.
대표 지적: "저쪽에는 있는데 이쪽에는 없고 너무 그지같이 매칭시켰어. 한개씩 제대로 붙여서 해."

## 이번 원칙
- **메뉴 하나당 쿼리를 따로 만든다.** 카테고리 일반어 폴백 금지.
- 쿼리 순서: ①`브랜드 메뉴명` ②`브랜드 핵심어` ③`메뉴명 냉동` ④`메뉴명`
- **상품명이 실제로 겹쳐야 채택**한다(핵심 토큰 일치). 카테고리만 같은 건 버린다.
- 브랜드명이 상품명에 있으면 **정품**(최우선).
- 같은 상품이 다른 메뉴에 이미 붙었으면 **중복 배제**.
- 못 찾으면 그냥 비운다. 억지로 채우지 않는다(대표: "없는건 패싱").

사용법: python scripts/mealkit_strict.py [--budget=150] [--only=1,2,3]
결과: data/research/mealkit_strict.json  (menu_id → 후보 리스트, 이어하기 지원)
"""
import io, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mealkit_run as mk          # get_items·cache_path·load_env 재사용
import sqlite3

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "mealkit_strict.json")
FLAVOR = os.path.join(BASE, "data", "research", "menu_flavor.json")
TOPN = 6

# 메뉴별 맛 프로필 — 브랜드 메뉴명은 쿠팡에 없지만 '맛'으로는 찾을 수 있다.
#  대표 지시(2026-07-25): "교촌 오리지날은 간장이고 허니콤보는 허니간장, 이런식으로 생각해서 대체식품 찾아봐"
try:
    with io.open(FLAVOR, encoding="utf-8") as _f:
        FLAV = {k: v for k, v in json.load(_f).items() if not k.startswith("_")}
except FileNotFoundError:
    FLAV = {}

# 비조리·굿즈·비식품 — 이전 검수에서 실제로 섞여 들어온 것들
EXCLUDE = re.compile(
    r"(교환권|상품권|기프트|기프티|쿠폰|바우처|금액권|이용권|"
    r"포스터|스티커|간판|메뉴판|유니폼|앞치마|"
    r"소스\b|양념장|시즈닝|드레싱\b|분말|파우더|다시다|"
    r"과자|스낵|칩스|포카칩|포테토칩|감자칩|젤리|사탕|캔디|초콜릿|"
    r"음료|콜라|사이다|주스|쥬스|커피믹스|캡슐커피|생수|"
    r"사료|간식캔|장난감|굿즈|티셔츠|의류|양말|욕실화|슬리퍼|"
    r"강아지|반려견|반려묘|애견|애묘|반려동물|고양이|펫\b|"
    r"영양제|비타민|유산균|콜라겐|프로틴바|"
    r"식용유|참기름|들기름|올리브유|설탕|소금\b|밀가루|전분|"
    r"세제|비누|섬유유연제|밀폐용기|그릇|접시|수세미|용기\b|봉투|"
    r"충전기|케이블|이어폰|필름|케이스|거치대|훈연칩|우드칩|톱밥|"
    # 2026-07-25 1차 블록에서 실제로 섞인 것 — 메뉴명 토큰이 우연히 겹친 비식품
    r"골프|퍼터|그립|드라이버|볼마커|운동화|가방|지갑|시계|반지|목걸이|"
    r"화장품|샴푸|린스|바디워시|치약|칫솔|마스크팩|기저귀|물티슈|"
    r"도서|책\b|문제집|퍼즐|블록|색칠|완구|피규어|"
    # 재료 단품은 대체식품이 아니다 — 완성품만 붙인다(청년피자 리얼치즈에 '피자치즈'가 붙었다)
    r"피자치즈|모짜렐라\s?치즈$|치즈\s?1kg|슈레드치즈|튀김가루|빵가루|밀가루|"
    r"우롱티|홍차|녹차티|티백|차\s?세트|"
    # 업소용 원료는 소비자 대체식품이 아니다 — "집에서 사 먹을 것"을 붙이는 자리다
    r"생지|휴면반죽|반죽\b|도포물|프리믹스|믹스가루|"
    r"통원두|원두\b|말차가루|미숫가루|분말가루|베이킹용|라떼용)")

# 메뉴명에서 의미 없는 꾸밈말 — 토큰 매칭에서 뺀다
STOP = re.compile(r"(단품|세트|정식|한상|반상|기본|오리지날|오리지널|스페셜|프리미엄|"
                  r"[가-힣]?사이즈|라지|미디움|스몰|[LMRS]\b|\d+인분?|\d+p\b|\d+개|\d+호|"
                  r"매운맛|순한맛|반반|추천)")
BRAND_SUFFIX = re.compile(r"(치킨|피자|버거|분식|떡볶이|샐러드|김밥|설렁탕|국밥|족발|보쌈|"
                          r"돈까스|초밥|커피|카페|김선생|도시락)$")


def norm(s):
    # 소문자 통일 — 안 하면 'bhc'가 'BHC 안심촉촉'에 안 걸려 경쟁브랜드가 통과한다(2026-07-25 실제 발생)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", (s or "").lower())


def brand_core(b):
    return BRAND_SUFFIX.sub("", (b or "").replace(" ", ""))


def menu_tokens(menu):
    """메뉴명에서 매칭에 쓸 핵심 토큰. 2글자 이상 한글 덩어리."""
    s = STOP.sub(" ", menu or "")
    s = re.sub(r"[()\[\]/·,]", " ", s)
    toks = [t for t in re.split(r"\s+", s) if len(t) >= 2 and re.search(r"[가-힣]", t)]
    return toks


def load_menus(only=None, cat=None):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT m.id, m.name AS menu, b.name AS brand, c.name AS cat
                          FROM menus m JOIN brands b ON b.id=m.brand_id
                          LEFT JOIN categories c ON c.id=b.category_id
                          ORDER BY c.name, b.name, m.id""").fetchall()
    con.close()
    out = [dict(r) for r in rows]
    if only:
        keep = set(only)
        out = [r for r in out if r["id"] in keep]
    if cat:   # 카테고리별로 블록 나눠 돌린다(대표 지시 2026-07-25)
        out = [r for r in out if (r["cat"] or "") == cat]
    return out


def queries(m):
    """메뉴 하나에 대한 쿼리들. 구체적인 것부터. 일반어 단독 금지.

    순서: ①브랜드+메뉴명(정품 노림) → ②**맛 프로필**(대체품 노림) → ③메뉴명
    맛 프로필이 핵심이다 — "허니콤보"는 상품에 없지만 "허니간장 치킨"은 있다.
    """
    brand, menu = m["brand"] or "", m["menu"] or ""
    bc = brand_core(brand)
    mn = STOP.sub("", menu).strip()
    qs = []
    if brand and mn:
        qs.append("%s %s" % (brand, mn))
    if bc and bc != brand and mn:
        qs.append("%s %s" % (bc, mn))
    qs += (FLAV.get(str(m["id"])) or {}).get("검색") or []
    if mn:
        qs.append("%s 냉동" % mn)
        qs.append(mn)
    seen, out = set(), []
    for q in qs:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q); out.append(q)
    return out


def score(item, m, taken):
    """채택 점수. None이면 탈락.

    핵심: **상품명이 메뉴명 토큰과 실제로 겹쳐야 한다.** 브랜드 일치는 가점.
    """
    nm = item.get("name") or ""
    if not nm or not item.get("url") or not item.get("image"):
        return None
    if EXCLUDE.search(nm):
        return None
    if item.get("id") in taken:            # 다른 메뉴가 이미 쓴 상품
        return None
    try:
        pr = float(item.get("price"))
    except (TypeError, ValueError):
        return None
    if pr <= 0 or pr > 200000:
        return None

    nn = norm(nm)
    toks = menu_tokens(m["menu"])
    hit = sum(1 for t in toks if norm(t) and norm(t) in nn)
    # 맛 프로필 토큰도 인정한다 — 브랜드 메뉴명이 상품에 없어도 '맛'이 같으면 대체품으로 맞다.
    #  예: 교촌 허니콤보 ← "소이허니 순살"(허니 토큰 일치)
    fl = FLAV.get(str(m["id"])) or {}
    ftoks = []
    for q in (fl.get("검색") or []):
        ftoks += [t for t in re.split(r"\s+", q) if len(t) >= 2 and t not in ("냉동", "업소용", "순살", "치킨")]
    fhit = sum(1 for t in set(ftoks) if norm(t) and norm(t) in nn)
    if not hit and not fhit:
        return None                        # ← 핵심. 이름도 맛도 안 겹치면 버린다
    hit = hit * 2 + fhit                   # 메뉴명 직접일치를 맛일치보다 우대
    bc = norm(brand_core(m["brand"]))
    official = bool(bc) and len(bc) >= 2 and bc in nn
    # 경쟁 프랜차이즈 배제는 호출부에서(브랜드 목록 필요)
    return {"official": official, "hit": hit, "price": pr,
            "rocket": bool(item.get("rocket")), "item": item}


def main():
    budget, only, cat = 150, None, None
    for a in sys.argv[1:]:
        if a.startswith("--budget="):
            budget = int(a.split("=", 1)[1])
        if a.startswith("--only="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x.strip()]
        if a.startswith("--cat="):
            cat = a.split("=", 1)[1]

    env = mk.load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 쿠팡 키가 없습니다."); return 1

    # 경쟁 브랜드 핵심어(내 브랜드 아닌 것이 상품명에 있으면 배제)
    con = sqlite3.connect(DB)
    cores = {brand_core(r[0]) for r in con.execute("SELECT DISTINCT name FROM brands")}
    con.close()
    cores = {norm(c) for c in cores if len(norm(c)) >= 2}

    menus = load_menus(only, cat)
    res = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    taken = {c["id"] for v in res.values() for c in v.get("candidates", [])}

    state = {"used": 0, "budget": budget, "gap": 2.2,
             "logf": io.open(os.path.join(BASE, "data", "research", "mealkit_strict.log"),
                             "a", encoding="utf-8")}
    done = found = 0
    for m in menus:
        mid = str(m["id"])
        if mid in res:                      # 이어하기
            continue
        if state["used"] >= budget:
            print("예산 소진 — 남은 메뉴 %d개" % (len(menus) - done))
            break
        mycore = norm(brand_core(m["brand"]))
        rivals = {c for c in cores if c != mycore}
        cands, stop = [], False
        for q in queries(m):
            items, cached, ok = mk.get_items(q, ak, sk, state)
            if ok == "429":
                print("!!! 429 — 중단"); stop = True; break
            if ok == "BUDGET":
                stop = True; break
            if ok is not True or not items:
                continue
            for it in items:
                s = score(it, m, taken)
                if not s:
                    continue
                nn = norm(it.get("name") or "")
                if any(rv in nn for rv in rivals):   # 경쟁 브랜드 제품
                    continue
                s["kw"] = q
                cands.append(s)
            # 정품이 잡혔으면 더 안 찾는다
            if any(c["official"] for c in cands):
                break
        if stop:
            break
        # 🔴 4단 우선순위 (대표 확정 2026-07-25) — 이 순서를 바꾸지 말 것
        #   ① 동일브랜드+로켓  ② 동일브랜드+일반  ③ 대체+로켓  ④ 대체+일반
        #   "로켓 없으면 일반, 일반도 없으면 대체 로켓, 대체 로켓 없으면 대체 일반"
        #   그 안에서만 이름겹침(hit) 많은 순 → 저가 순.
        cands.sort(key=lambda c: (not c["official"], not c["rocket"], -c["hit"], c["price"]))
        picked = []
        for c in cands[:TOPN]:
            it = c["item"]
            picked.append({"id": it["id"], "name": it["name"], "price": c["price"],
                           "rocket": c["rocket"], "image": it.get("image"),
                           "url": it.get("url"), "kw": c["kw"],
                           "official": c["official"], "hit": c["hit"]})
        res[mid] = {"menu_id": m["id"], "brand": m["brand"], "menu": m["menu"],
                    "category": m["cat"], "candidates": picked}
        json.dump(res, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        done += 1
        if picked:
            found += 1
            tag = "정품" if picked[0]["official"] else "대체"
            print("OK  %-4s %-12s %-18s [%s] %s" % (
                mid, (m["brand"] or "")[:12], (m["menu"] or "")[:18], tag,
                picked[0]["name"][:34]), flush=True)
        else:
            print("--  %-4s %-12s %-18s 후보없음" % (
                mid, (m["brand"] or "")[:12], (m["menu"] or "")[:18]), flush=True)

    state["logf"].close()
    scope_menus = load_menus(cat=cat)
    total = len(scope_menus)
    inscope = len([m for m in scope_menus if str(m["id"]) in res])
    print("\n호출 %d회 · 이번 처리 %d개 · 후보있음 %d" % (state["used"], done, found))
    print("%s누적 %d/%d · 남은 메뉴 %d개"
          % (("[%s] " % cat) if cat else "", inscope, total, total - inscope))
    return 0


sys.exit(main())
