# -*- coding: utf-8 -*-
"""기영이숯불치킨 메뉴판·판매가 — 자사 스마트오더 API 에서. 2026-07-31

    python scripts/brand_kiyoung.py            # 수집 + 미리보기
    python scripts/brand_kiyoung.py --apply    # data/brand_menu_list/kiyoung.json 생성

⛔ DB 는 건드리지 않는다. JSON 파일만 만든다(`brands` 테이블에 없는 새 브랜드).

━━ 어떻게 뚫었나 (wmpoplus 스마트오더 — 호식이·또래오래와 같은 플랫폼) ━━━━━━━
1. 앱 `com.wmpoplus.kiyoung2` 의 dex 문자열에 웹뷰 주소가 있다:
       https://kiyoung2.wmpoplus.com/     ← 주문 사이트 (Next.js)
       https://api.wmpo.co.kr             ← 🔴 계정용. 여기 찌르면 401 이다. API 가 아니다
2. 브랜드 코드는 **호스트 첫 토막**으로 받는다 (공개·토큰 불필요):
       GET https://d11u7cg79d1e8u.cloudfront.net/sites/kiyoung2.json
       → siteID 201 · companyID 76562 · (주)기영에프앤비
3. 진짜 API 는 `https://api.thecupping.co.kr` (주문 사이트 JS 청크의 `E0` 상수).
   모든 요청이 `token` 헤더를 요구하지만 **로그인은 필요 없다**:
       GET /init  → data.token (게스트 토큰, isLogin=0)
4. 매장:  GET /stores?lat=&lon=&page=&searchKeyword=&useSearch=1
   🔴 좌표는 아무 데나 하나면 된다. 정렬만 거리순이고 **전국이 다 나온다**
      (서울 좌표 245곳 = 제주 좌표 245곳, 차집합 0 — 2026-07-31 확인)
5. 메뉴·가격:  GET /stores/{storeID}/products   (파라미터 없음)
       data.products[] = 카테고리(categoryName) → .products[] = 상품
       가격 = options 중 alias=="PRICE" 그룹 children[].prices.KRW.price
       data.origin 에 원산지 원문이 통째로 들어 있다

🔴 **홀/배달 가격 구분이 없다.** `products` 는 주문타입을 인자로 받지 않는다.
   여기 담는 값은 **배달 가산이 없는 매장(홀·픽업) 판매가**다.

🔴 **productID 는 매장마다 다르다**(같은 「빨간양념 숯불치킨」이 244개 ID).
   그래서 `ext_id` 는 비운다. 반대로 `imageUrl` 은 245곳 전부 동일해서 그대로 쓴다.

⚠️ 전국 매장을 훑어 **최빈값**을 쓴다. 기영이는 본사 통제가 강해 대부분 동의율 100% 다.
   시세·판매가는 날마다 달라질 수 있다.
🔴 제주 매장은 「[제주]…」 라는 **별도 상품명**으로 1,000원쯤 비싸게 판다 →
   출현 매장수 기준에서 저절로 탈락한다(1곳). 육지가를 제주가로 덮어쓰지 않는다.
🔴 주류(21곳)·생맥주(4곳) 카테고리는 **매장 자율가**라 담지 않는다.
"""
import argparse
import collections
import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

SLUG = "kiyoung"
BRAND = "기영이숯불치킨"
HOST = "kiyoung2.wmpoplus.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")

API = "https://api.thecupping.co.kr"
SITE_JSON = "https://d11u7cg79d1e8u.cloudfront.net/sites/kiyoung2.json"
UA = ("Mozilla/5.0 (Linux; Android 14; SM-F956N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
COLLECTED = "2026-07-31"

MIN_STORES = 50      # 이만큼은 봐야 값을 쓴다
ADOPT = 0.5          # 전국 매장의 이 비율 이상에 있어야 「전국 메뉴」로 담는다
DROP_CATS = ("주류", "기영이 생맥주")   # 매장 자율가 — 담지 않는다

# ── 원산지 (data.origin 원문을 메뉴에 나눠 붙인다) ─────────────────────
# 🔴 원문이 이름을 대는 메뉴만 적는다. 추측하지 않는다.
CHICKEN_COMMON = "닭고기뼈 - 국내산, 닭고기순살 - 외국산, 장각 - 외국산"
ORIGIN = {
    "닭발우동숯불치킨": "닭고기순살 - 외국산, 닭발 - 국내산",
    "버터크랩 숯불치킨": CHICKEN_COMMON + ", 게 - 베트남산",
    "[박지훈 포스터] 돼껍누들 양념숯불치킨": CHICKEN_COMMON + ", 돼지껍데기 - 국내산",
    "[박지훈 중복 추천메뉴] 돼껍누들 양념숯불치킨 set (치즈볼5+통마늘칩)":
        CHICKEN_COMMON + ", 돼지껍데기 - 국내산",
    "돼껍누들 양념숯불치킨": CHICKEN_COMMON + ", 돼지껍데기 - 국내산",
    "막창누들숯불치킨": CHICKEN_COMMON + ", 돼지막창 - 스페인산",
    "무뼈닭발 떡볶이": "닭발 - 국내산",
    "튀김오뎅(5개)": "어묵(냉동연육) - 외국산(베트남, 중국, 미국 등)",
    "계란볶음밥": "쌀 - 외국산",
    "모치치(모짜렐라치즈치킨 1개)": "닭고기 - 국내산",
    "모치치(모짜렐라치즈치킨 2개)": "닭고기 - 국내산",
    "옛날통닭 반마리": "닭고기 - 국내산",
    "간장양념 닭강정": "닭고기 - 외국산",
    "후라이드 통닭다리": "닭고기 - 태국산",
    "후라이드 통닭다리 2개": "닭고기 - 태국산",
    "공기밥": "쌀 - 국내산",
    "즉석밥": "쌀 - 국내산",
    "즉석밥(비조리)": "쌀 - 국내산",
    "셀프마요주먹밥": "쌀 - 국내산",
    "[기영이] 두마리세트(숯불치킨+옛날통닭한마리)": CHICKEN_COMMON + ", 옛날통닭 닭고기 - 국내산",
    "양념숯불치킨+간장양념 닭강정": CHICKEN_COMMON + ", 닭강정 닭고기 - 외국산",
}
# 원문 「숯불치킨 전 메뉴」에 해당하는 것들 — 이름에 이 말이 들어가면 공통 원산지를 붙인다
CHICKEN_MARKS = ("숯불치킨", "숯불장각", "장각 반반", "치밥")

_TOKEN = [None]


def _raw(path, params=None):
    u = API + path
    if params:
        u += "?" + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, "Accept": "application/json",
         "Referer": "https://%s/" % HOST, "Origin": "https://%s" % HOST}
    if _TOKEN[0]:
        h["token"] = _TOKEN[0]
    r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=20, context=CTX)
    return json.loads(r.read().decode("utf-8", "replace"))


def guest_token():
    _TOKEN[0] = None
    _TOKEN[0] = _raw("/init")["data"]["token"]


def api(path, params=None, _depth=0):
    """401 이 뜨면 게스트 토큰을 새로 받아 다시 — 토큰이 종종 만료된다"""
    try:
        return _raw(path, params)
    except Exception:
        if _depth < 3 and path != "/init":
            time.sleep(1.5)
            guest_token()
            return api(path, params, _depth + 1)
        raise


def price_rows(prod):
    out = []
    for g in prod.get("options") or []:
        if g.get("alias") != "PRICE":
            continue
        for c in g.get("children") or []:
            p = (c.get("prices") or {}).get("KRW") or {}
            if p.get("price") is not None:
                out.append(p["price"])
    return out


def survey():
    guest_token()
    stores = {}
    for page in range(1, 40):
        j = api("/stores", {"lat": 37.5666805, "lon": 126.9784147, "page": page,
                            "searchKeyword": "", "useSearch": 1})
        for s in j.get("data") or []:
            stores[s["ID"]] = s
        pg = j.get("paging") or {}
        if page >= (pg.get("totalPage") or 1):
            break
    print("전국 매장 %d곳" % len(stores))

    catn = collections.Counter()
    catpos = collections.defaultdict(list)
    prod = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"n": 0, "pos": [], "price": collections.Counter(), "img": None,
                 "desc": collections.Counter()}))
    origins = collections.Counter()
    seen = {"pick": 0, "both": 0}
    pbygrp = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    ok = fail = 0
    for i, sid in enumerate(list(stores), 1):
        try:
            d = api("/stores/%s/products" % sid)["data"]
        except Exception:
            fail += 1
            continue
        s = stores[sid]
        grp = "pick" if (s.get("isPickup") and not s.get("isDelivery")) else \
              ("both" if (s.get("isPickup") and s.get("isDelivery")) else None)
        if grp:
            seen[grp] += 1
        if d.get("origin"):
            origins[d["origin"].strip()] += 1
        for ci, c in enumerate(d.get("products") or []):
            cn = c.get("categoryName") or "(무제)"
            catn[cn] += 1
            catpos[cn].append(ci)
            for pi, p in enumerate(c.get("products") or []):
                if p.get("isDisplay") == 0:
                    continue
                e = prod[cn][p["name"]]
                e["n"] += 1
                e["pos"].append(pi)
                e["img"] = e["img"] or p.get("imageUrl")
                if p.get("productDescription"):
                    e["desc"][p["productDescription"].strip()] += 1
                for pr in price_rows(p):
                    e["price"][pr] += 1
                    if grp:
                        pbygrp[grp][(cn, p["name"])][pr] += 1
        ok += 1
        if i % 50 == 0:
            print("   %d/%d" % (i, len(stores)))
        time.sleep(0.1)
    print("메뉴판 %d곳 수집 · %d곳 실패 (픽업전용 %d · 픽업+배달 %d)"
          % (ok, fail, seen["pick"], seen["both"]))
    return ok, catn, catpos, prod, origins, pbygrp, seen


def mode_of(counter):
    if not counter:
        return None, 0, 0
    p, c = max(counter.items(), key=lambda kv: (kv[1], -kv[0]))
    return p, c, sum(counter.values())


def origin_for(name):
    if name in ORIGIN:
        return ORIGIN[name]
    if any(m in name for m in CHICKEN_MARKS):
        return CHICKEN_COMMON
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="kiyoung.json 을 실제로 쓴다")
    a = ap.parse_args()

    n, catn, catpos, prod, origins, pbygrp, seen = survey()
    if n < MIN_STORES:
        print("❌ 표본이 너무 적다 — 쓰지 않는다")
        return 1

    cats = [c for c, k in catn.items() if k >= n * ADOPT and c not in DROP_CATS]
    cats.sort(key=lambda c: sum(catpos[c]) / float(len(catpos[c])))

    doc = {"brand": BRAND, "slug": SLUG,
           "source": "https://%s/ (자사 스마트오더 · api.thecupping.co.kr)" % HOST,
           "collected_at": COLLECTED, "origin_note": None,
           "cats": [{"name": c, "parent": None, "ext_id": None} for c in cats],
           "menus": []}

    mismatch = []
    npr = 0
    for c in cats:
        items = [(nm, e) for nm, e in prod[c].items() if e["n"] >= n * ADOPT]
        items.sort(key=lambda kv: sum(kv[1]["pos"]) / float(len(kv[1]["pos"])))
        for idx, (nm, e) in enumerate(items):
            p, agree, obs = mode_of(e["price"])
            note = None
            if p is not None and obs >= MIN_STORES:
                note = ("스마트오더 %s원 (전국 %d개 매장 중 이 메뉴를 파는 %d곳, %d곳 동일=%.0f%%)"
                        % (format(p, ","), n, obs, agree, 100.0 * agree / obs))
                npr += 1
            else:
                note = "관측 %d곳뿐 — 값을 쓰지 않음" % obs
                p = None
            pp, _, _ = mode_of(pbygrp["pick"].get((c, nm)))
            pb, _, _ = mode_of(pbygrp["both"].get((c, nm)))
            if pp is not None and pb is not None and pp != pb:
                note += " ⚠️픽업전용 %s / 픽업+배달 %s" % (pp, pb)
                mismatch.append(nm)
            doc["menus"].append({
                "name": nm, "price": p, "price_source": "official_smartorder",
                "price_note": note + " [출처 %s 스마트오더 · %s 수집 · 홀/픽업가(배달 가산 없음) · "
                                     "가격은 매장·시기에 따라 달라진다]" % (HOST, COLLECTED),
                "weight_raw": None,
                "origin_raw": origin_for(nm),
                "allergy_raw": None,
                "detail_url": None,
                "image_url": e["img"],
                "ext_id": None,
                "desc_raw": (e["desc"].most_common(1)[0][0] if e["desc"] else None),
                "cats": [[c, idx]],
            })
        print("  [%s] %d/%d곳 · 메뉴 %d개" % (c, catn[c], n, len(items)))

    if origins:
        doc["origin_note"] = origins.most_common(1)[0][0]
        o, k = origins.most_common(1)[0]
        print("\n원산지 원문 — %d/%d곳 동일" % (k, n))

    doc["price_note_all"] = (
        "판매가는 기영이숯불치킨 자사 스마트오더(%s / api.thecupping.co.kr)에서 받았다. "
        "전국 %d개 매장을 전부 훑은 최빈값이며 홀/픽업가다(API 에 주문타입별 가격이 아예 없다). "
        "전국 매장의 %.0f%% 이상에 있는 메뉴만 담았다. 주류·생맥주는 매장 자율가라 뺐다. "
        "제주 매장은 「[제주]…」 별도 상품명으로 더 비싸게 팔아 육지가와 섞지 않았다. "
        "가격은 매장·시기에 따라 달라진다." % (HOST, n, ADOPT * 100))

    print("\n카테고리 %d개 · 메뉴 %d개 · 가격 %d개 · 원산지 %d개"
          % (len(cats), len(doc["menus"]), npr,
             sum(1 for m in doc["menus"] if m["origin_raw"])))
    if mismatch:
        print("⚠️ 픽업전용/배달 가격이 갈린 메뉴: %s" % ", ".join(mismatch))
    else:
        print("픽업전용 매장과 픽업+배달 매장의 값이 갈린 메뉴: 없음")

    if a.apply:
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("✅ 저장", OUT)
    else:
        print("(미리보기다. 반영하려면 --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
