# -*- coding: utf-8 -*-
"""밀키트 대체품 조사 — 실행 드라이버 (쿠팡 검색 + 필터 + 선정)

mealkit_kw_plan.json 을 읽어 메뉴별로 대체 키워드를 순서대로 조회하고,
비조리 제외 필터를 통과한 상품 중 로켓/인기 우선으로 1개를 고른다.

- 캐시: data/research/coupang/<키워드>.json 재사용(있으면 API 안 부름)
- 결과: data/research/mealkit_all.json (menu_id 키, 이어하기 가능)
- 못 찾음: mealkit_notfound.json
- 간격 >=2초, 429 즉시 중단, 메뉴당 실제 호출 최대 3회
- 실행당 호출 예산(--budget, 기본 170)으로 나눠 돌린다

사용법:
  python scripts/mealkit_run.py [--budget=170] [--gap=2.2]
"""
import os, sys, io, json, re, time, hmac, hashlib, ssl
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "data", "research")
CACHE = os.path.join(RES, "coupang")
PLAN = os.path.join(RES, os.environ.get("MEALKIT_PLAN", "mealkit_kw_plan.json"))
OUT = os.path.join(RES, os.environ.get("MEALKIT_OUT", "mealkit_all.json"))
NOTFOUND = os.path.join(RES, "mealkit_notfound.json")
# 같은 상품이 여러 메뉴에 붙는 것 방지(2026-07-25: 421건 중 50%가 중복 매칭이었다).
#  MEALKIT_UNIQUE=1 이면 이미 다른 메뉴가 채택한 productId 는 건너뛴다.
UNIQUE = os.environ.get("MEALKIT_UNIQUE") == "1"
LOG = os.path.join(RES, "mealkit_run.log")

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
LIMIT = 10
MAX_FETCH_PER_MENU = 3

# 비조리(제외) — 상품명에 있으면 버린다
EXCLUDE = re.compile(
    r"(교환권|상품권|기프트|기프티|쿠폰|바우처|"
    r"소스\b|양념장|양념\s*장|드레싱|시즈닝|시즈닝|분말|파우더|다시다|"
    r"과자|스낵|칩스|포테토칩|감자칩|나초|젤리|사탕|캔디|초콜릿|초코바|"
    r"음료|콜라|사이다|주스|쥬스|이온음료|커피믹스|캡슐커피|"
    r"사료|간식캔|장난감|굿즈|티셔츠|의류|양말|"
    r"강아지|반려견|반려묘|애견|애묘|반려동물|고양이|댕댕|멍멍|펫\b|수제간식|"
    r"영양제|비타민|유산균|콜라겐|프로틴바|생수|미네랄워터|"
    r"식용유|참기름|들기름|올리브유|설탕|소금\b|밀가루|전분|"
    r"세제|비누|섬유유연제|밀폐용기|그릇|접시|수세미)")

# 조리형 신호 — 이게 있으면 진짜 밀키트/HMR일 가능성 높음(우선 채택)
COOKSIG = re.compile(
    r"(냉동|밀키트|간편식|HMR|즉석|에어프라이어|에어프라이|데우|해동|"
    r"만두|돈[까가]스|가라아게|강정|튀김|너겟|핫도그|피자|파스타|"
    r"국\b|탕\b|찌개|전골|육개장|해장국|쌀국수|짜장|짬뽕|볶음|덮밥|"
    r"떡볶이|순대|어묵|족발|보쌈|곱창|스테이크|함박|규동|포케)")

# 원물/생재료 — 밀키트가 아니라 손질 안 된 원재료. 후순위로 밀어냄
RAWSIG = re.compile(r"(생닭|생물|손질|정육|원육|원물|다짐육|절단육|통마리\s*생)")


def load_env():
    env = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def sign(method, url_path, secret, access):
    parts = url_path.split("?")
    path, query = parts[0], (parts[1] if len(parts) > 1 else "")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return ("CEA algorithm=HmacSHA256, access-key=%s, signed-date=%s, signature=%s"
            % (access, dt, sig))


def api_search(keyword, ak, sk):
    url_path = "%s?keyword=%s&limit=%d" % (PATH, urllib.parse.quote(keyword), LIMIT)
    req = urllib.request.Request(DOMAIN + url_path, method="GET")
    req.add_header("Authorization", sign("GET", url_path, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=25,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def cache_path(kw):
    return os.path.join(CACHE, kw.replace("/", "_") + ".json")


def get_items(kw, ak, sk, state):
    """캐시에 있으면 로드(호출 0), 없으면 API. (items, from_cache, ok)"""
    cp = cache_path(kw)
    if os.path.exists(cp):
        try:
            d = json.load(io.open(cp, encoding="utf-8"))
            return d.get("items", []), True, True
        except Exception:
            pass
    # 예산/429 체크
    if state["used"] >= state["budget"]:
        return [], False, "BUDGET"
    try:
        body = api_search(kw, ak, sk)
        state["used"] += 1
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:120]
        log(state, "[HTTP %s] %s %s" % (e.code, kw, raw))
        if e.code == 429:
            return [], False, "429"
        return [], False, "ERR"
    except Exception as e:
        log(state, "[ERR] %s %s" % (kw, str(e)[:80]))
        return [], False, "ERR"
    if str(body.get("rCode")) != "0":
        log(state, "[rCode %s] %s" % (body.get("rCode"), kw))
        return [], False, "ERR"
    items = (body.get("data") or {}).get("productData") or []
    rec = {"keyword": kw, "fetched_at": datetime.now().isoformat(timespec="seconds"),
           "count": len(items),
           "items": [{"name": it.get("productName"), "price": it.get("productPrice"),
                      "rocket": it.get("isRocket"), "free": it.get("isFreeShipping"),
                      "id": it.get("productId"), "url": it.get("productUrl"),
                      "image": it.get("productImage")} for it in items]}
    os.makedirs(CACHE, exist_ok=True)
    io.open(cp, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
    time.sleep(state["gap"])
    return rec["items"], False, True


def pick(items, anchors, taken_ids=None):
    """비조리 제외 후 최적 1개 선정. 반환 (item, anchored_bool) or (None, False).

    정렬 우선순위: 카테고리 앵커 일치 > 조리신호 > (원물 후순위) > 로켓 > API 노출순.
    anchored_bool = 뽑힌 상품이 카테고리 앵커에 맞는지(약한 매칭이면 상위 키워드로 승격 시도).
    taken_ids = 이미 다른 메뉴가 채택한 productId 집합(중복 매칭 방지).
    """
    anch = [a for a in (anchors or [])]
    good = []
    for idx, it in enumerate(items):
        nm = it.get("name") or ""
        if EXCLUDE.search(nm):
            continue
        if taken_ids and it.get("id") in taken_ids:
            continue
        if not it.get("url") or not it.get("image"):
            continue
        # 가격 상식 필터: 소비자용 밀키트/냉동식품 범위 밖(도매·오류가·초고가)은 제외
        pr = it.get("price")
        try:
            pr = float(pr)
        except (TypeError, ValueError):
            continue
        if pr <= 0 or pr > 150000:
            continue
        a = 1 if (anch and any(x in nm for x in anch)) else 0
        cook = 1 if COOKSIG.search(nm) else 0
        raw = 1 if RAWSIG.search(nm) else 0
        good.append((it, idx, a, cook, raw))
    if not good:
        return None, False
    good.sort(key=lambda t: (-t[2], -t[3], t[4], 0 if t[0].get("rocket") else 1, t[1]))
    best = good[0]
    return best[0], bool(best[2])


def log(state, msg):
    line = "%s %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    state["logf"].write(line + "\n")
    state["logf"].flush()


def main():
    budget = 170
    gap = 2.2
    for a in sys.argv[1:]:
        if a.startswith("--budget="):
            budget = int(a.split("=", 1)[1])
        if a.startswith("--gap="):
            gap = float(a.split("=", 1)[1])
    gap = max(gap, 2.0)

    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 쿠팡 키가 없습니다.")
        return 1

    plan = json.load(io.open(PLAN, encoding="utf-8"))
    results = {}
    if os.path.exists(OUT):
        try:
            results = json.load(io.open(OUT, encoding="utf-8"))
        except Exception:
            results = {}

    # 이미 채택된 상품 id (이어하기 시에도 중복 방지가 유지되도록 기존 결과에서 복원)
    taken_ids = set()
    if UNIQUE:
        for v in results.values():
            if v.get("status") == "found" and v.get("productId"):
                taken_ids.add(v["productId"])

    state = {"used": 0, "budget": budget, "gap": gap,
             "logf": io.open(LOG, "a", encoding="utf-8")}
    log(state, "=== RUN start budget=%d gap=%.1f 기존결과=%d ===" % (budget, gap, len(results)))

    processed = 0
    found = 0
    for p in plan:
        mid = str(p["menu_id"])
        if mid in results:
            continue
        # 음료 skip
        if p.get("skip"):
            results[mid] = {"menu_id": p["menu_id"], "brand": p["brand"], "menu": p["menu"],
                            "type": p["type"], "status": "skipped",
                            "reason": p.get("skip_reason")}
            continue

        anchors = p.get("anchors") or []
        fetched_here = 0
        chosen = None
        used_kw = None
        weak = None          # 앵커 미일치 약한 후보(폴백)
        weak_kw = None
        stop_all = False
        for kw in p["keywords"]:
            in_cache = os.path.exists(cache_path(kw))
            if not in_cache and fetched_here >= MAX_FETCH_PER_MENU:
                break
            items, from_cache, ok = get_items(kw, ak, sk, state)
            if ok == "429":
                log(state, "!!! 429 — 즉시 중단")
                stop_all = True
                break
            if ok == "BUDGET":
                stop_all = True
                break
            if not from_cache:
                fetched_here += 1
            if ok is True and items:
                c, anchored = pick(items, anchors, taken_ids if UNIQUE else None)
                if c:
                    if anchored or not anchors:
                        chosen = c
                        used_kw = kw
                        break
                    # 약한 매칭: 폴백으로 저장하고 다음 키워드에서 앵커 일치 재시도
                    if weak is None:
                        weak, weak_kw = c, kw
        if stop_all:
            break
        if chosen is None and weak is not None:
            chosen, used_kw = weak, weak_kw

        if chosen:
            brand = p.get("brand") or ""
            nm = chosen.get("name") or ""
            is_official = bool(brand) and brand.replace(" ", "")[:2] in nm.replace(" ", "")
            results[mid] = {
                "menu_id": p["menu_id"], "brand": p["brand"], "menu": p["menu"],
                "type": p["type"], "status": "found",
                "match_type": "정품" if is_official else "대체",
                "keyword": used_kw,
                "product_name": nm, "price": chosen.get("price"),
                "isRocket": bool(chosen.get("rocket")),
                "productImage": chosen.get("image"),
                "productUrl": chosen.get("url"),
                "productId": chosen.get("id"),
            }
            if UNIQUE and chosen.get("id"):
                taken_ids.add(chosen["id"])
            found += 1
            log(state, "OK  %s [%s] <- %s | %s" % (mid, p["menu"][:0] or mid, used_kw, nm[:40]))
        else:
            results[mid] = {
                "menu_id": p["menu_id"], "brand": p["brand"], "menu": p["menu"],
                "type": p["type"], "status": "notfound",
                "tried": p["keywords"][:MAX_FETCH_PER_MENU],
            }
            log(state, "--  %s notfound (%s)" % (mid, ",".join(p["keywords"][:2])))

        processed += 1
        # 매 메뉴 저장(이어하기)
        io.open(OUT, "w", encoding="utf-8").write(
            json.dumps(results, ensure_ascii=False, indent=1))

    # notfound 목록 별도 저장
    nf = [v for v in results.values() if v.get("status") == "notfound"]
    io.open(NOTFOUND, "w", encoding="utf-8").write(
        json.dumps(nf, ensure_ascii=False, indent=1))

    total = len(plan)
    done = len(results)
    st_found = sum(1 for v in results.values() if v.get("status") == "found")
    st_skip = sum(1 for v in results.values() if v.get("status") == "skipped")
    st_nf = sum(1 for v in results.values() if v.get("status") == "notfound")
    log(state, "=== RUN end 이번호출=%d 이번처리=%d 누적 %d/%d (found %d / skip %d / nf %d) ==="
        % (state["used"], processed, done, total, st_found, st_skip, st_nf))
    state["logf"].close()
    print("이번 호출 %d회 · 이번 처리 %d개" % (state["used"], processed))
    print("누적 %d/%d  (found %d / skip %d / notfound %d)" % (done, total, st_found, st_skip, st_nf))
    print("남은 메뉴 %d개" % (total - done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
