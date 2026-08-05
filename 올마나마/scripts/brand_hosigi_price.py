# -*- coding: utf-8 -*-
"""호식이두마리치킨(slug 9292) 판매가 — 자사 스마트오더 API 에서. 2026-07-28

    python scripts/brand_hosigi_price.py            # 수집 + 미리보기
    python scripts/brand_hosigi_price.py --apply    # data/brand_menu_list/9292.json 의 price 만 갱신

⚠️ 이름·순서·카테고리·원산지는 **건드리지 않는다.** `price` / `price_note` / `price_source` 만 쓴다.
⛔ DB 는 건드리지 않는다.

━━ 어떻게 뚫었나 (다른 wmpoplus 브랜드도 같은 구조) ━━━━━━━━━━━━━━━━━━━━
공식 홈페이지(9922.co.kr)엔 가격이 **0건**이다. 가격은 **자사 스마트오더**에만 있다.

1. 폰에 깔린 APK 를 뽑아(`adb pull`) dex 문자열에서 `http` 를 전부 긁었더니 딱 둘이 나왔다:
       https://hosigi.wmpoplus.com/     ← 웹뷰가 여는 주문 사이트 (Next.js)
       https://api.wmpo.co.kr           ← 계정용
   ⚠️ dex 나머지는 전부 Google/Firebase/AppsFlyer SDK 잡음이다. **앱은 웹뷰 껍데기다.**

2. 주문 사이트의 JS 청크(`/_next/static/chunks/*.js`)에서 진짜 API 호스트가 나온다:
       E0 = "//api.thecupping.co.kr"     ← 매장·메뉴·주문 전부 여기
       qA = "https://d11u7cg79d1e8u.cloudfront.net"

3. **브랜드 구분은 호스트 첫 토막**이다 — `hosigi.wmpoplus.com` → `hosigi`:
       GET https://d11u7cg79d1e8u.cloudfront.net/sites/hosigi.json   (공개, 토큰 불필요)
       → siteID 206 · companyID 78211  ← 🔴 호식이 코드. 다른 브랜드는 자기 APK 에서 찾을 것

4. 🔴 **모든 API 가 `token` 헤더를 요구한다(없으면 401).** 로그인은 필요 없다 —
       GET https://api.thecupping.co.kr/init      → data.token (게스트 토큰, isLogin=0)
   이 토큰을 `token:` 헤더에 넣으면 나머지가 전부 열린다.

5. 매장코드는 **앱 「전체 매장」 화면이 부르는 검색 응답**에서 얻는다(추측 안 함):
       GET /stores?lat=<위도>&lon=<경도>&page=<n>&searchKeyword=<검색어>&useSearch=1
       → data[].ID · name · isPickup · isDelivery · enableReception   (호식이 전국 676곳)

6. 메뉴·가격:
       GET /stores/{storeID}/products      ← 🔴 파라미터 없음
       data.products[] = 카테고리, 그 안 products[] = 상품
       가격은 상품의 options 중 **alias=="PRICE"** 그룹 children 의
       `prices.KRW.price` (정가는 `originPrice`, 지금은 둘이 같다)
       data.origin 에 원산지·조리전중량 원문이 통째로 들어 있다

🔴 **홀/배달 가격 구분이 없다.** `products` 는 주문타입을 인자로 받지 않고 매장당 가격표가 하나다.
   (orderType=pickup/delivery 는 주문 단계 `/stores/{id}/orders` 에서만 쓰인다)
   실제로 대조했다 — 픽업전용 매장(125170 공덕점) vs 픽업+배달 매장(88580 독립문점):
   같은 이름 68개 중 **67개가 같은 값**, 다른 1개는 콜라(매장 자율가)였다.
   → 여기 담는 값은 **배달가산이 없는 매장 판매가**다.

⚠️ 가격은 **매장마다 다를 수 있다**(가맹점 자율). 그래서 전국 346개 매장을 훑어 **최빈값**을 쓴다.
   최빈값 동의율은 대부분 99% 이상이다. 시세는 날마다 바뀔 수 있다.

🔴 **콜라값을 빼서 단품가를 만들지 않는다.** 스마트오더에 세트로만 있는 메뉴
   (닭발튀김·똥집튀김·플라윙·다리·날개+다리·안심텐더 등)는 `price` 를 **null 로 둔다.**
   무엇이 얼마에 세트로 있는지는 `price_note` 에 적는다.
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

SLUG = "9292"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")

API = "https://api.thecupping.co.kr"
SITE_JSON = "https://d11u7cg79d1e8u.cloudfront.net/sites/hosigi.json"
UA = ("Mozilla/5.0 (Linux; Android 14; SM-F956N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
COLLECTED = "2026-07-28"
MIN_STORES = 50          # 이만큼은 봐야 그 값을 쓴다

COORDS = [(37.5666805, 126.9784147), (37.4562557, 126.7052062), (37.2635727, 127.0286009),
          (36.3504119, 127.3845475), (35.8714354, 128.601445), (35.1795543, 129.0756416),
          (35.1595454, 126.8526012), (37.8813153, 127.7298413), (36.8, 127.15),
          (33.4996213, 126.5311884)]

_TOKEN = [None]


def _raw(path, params=None):
    u = API + path
    if params:
        u += "?" + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, "Accept": "application/json",
         "Referer": "https://hosigi.wmpoplus.com/", "Origin": "https://hosigi.wmpoplus.com"}
    if _TOKEN[0]:
        h["token"] = _TOKEN[0]
    r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=45, context=CTX)
    return json.loads(r.read().decode("utf-8", "replace"))


def api(path, params=None, _depth=0):
    """401 이 뜨면 게스트 토큰을 새로 받아 한 번 더 — 토큰이 종종 만료된다"""
    try:
        return _raw(path, params)
    except urllib.error.HTTPError as e:
        if e.code == 401 and _depth < 2 and path != "/init":
            time.sleep(1.0 + _depth)
            guest_token()
            return api(path, params, _depth + 1)
        raise


def guest_token():
    _TOKEN[0] = None
    j = _raw("/init")
    _TOKEN[0] = j["data"]["token"]
    return j["data"]


def price_rows(prod):
    """상품 → [(옵션이름, 가격)] — alias=='PRICE' 그룹만"""
    out = []
    for g in prod.get("options") or []:
        if g.get("alias") != "PRICE":
            continue
        for c in g.get("children") or []:
            p = (c.get("prices") or {}).get("KRW") or {}
            if p.get("price") is not None:
                out.append((c.get("name") or "", p["price"]))
    return out


def survey():
    """전국 매장을 훑어 {앱메뉴명: Counter(가격)} 과 원산지 원문을 모은다"""
    guest_token()
    stores = {}
    for lat, lon in COORDS:
        for page in (1, 2):
            try:
                j = api("/stores", {"lat": lat, "lon": lon, "page": page,
                                    "searchKeyword": "", "useSearch": 1})
            except Exception as e:
                print("   매장검색 실패", lat, lon, page, e)
                continue
            for s in j.get("data") or []:
                stores[s["ID"]] = s
            time.sleep(0.3)
    print("매장 후보 %d곳 (전국 총 %s곳 중 표본)" % (len(stores), "676"))

    prices = collections.defaultdict(collections.Counter)
    origins = collections.Counter()
    ok = fail = 0
    for sid in stores:
        try:
            d = api("/stores/%d/products" % sid)["data"]
        except Exception:
            fail += 1
            continue
        if d.get("origin"):
            origins[d["origin"].strip()] += 1
        for cat in d.get("products") or []:
            for p in cat.get("products") or []:
                if p.get("isDisplay") == 0:
                    continue
                for optname, price in price_rows(p):
                    key = p["name"] if not optname else "%s | %s" % (p["name"], optname)
                    prices[key][price] += 1
        ok += 1
        time.sleep(0.25)
    print("메뉴판 %d곳 수집 · %d곳 실패" % (ok, fail))
    return ok, prices, origins


# ── 홈페이지 메뉴명 → 스마트오더 상품명 ────────────────────────────────
# 🔴 손으로 하나씩 대조한 표다. 자동 유사매칭 안 한다.
#    None = 스마트오더에 단품이 없다(세트로만 존재) → price 는 null 로 둔다.
MAP = {
    # 치킨 — 앱은 「(한마리)」 단품과 「한마리+한마리 세트」(=두마리)를 따로 판다
    "딥블랙갈릭 치킨": "[신메뉴]딥블랙갈릭치킨(한마리)",
    "깐쇼킹 치킨": "[HIT]깐쇼킹치킨(한마리)",
    "매운 간장 치킨": "[강추]매운간장치킨(한마리)",
    "크리스피골드": "크리스피 골드(국내산 순살) 단품",
    "요거치즈닝치킨(안심 순살)": "요거치즈닝치킨(쫀득안심)",
    "레몬크림탕슈(안심 순살)": "레몬크림탕슈(쫀득안심)",
    "레몬크림탕슈 (안심 순살)": "레몬크림탕슈(쫀득안심)",
    # 단품이 없는 치킨 (세트로만) → null
    "맵시크 치킨": None, "수라깐풍 치킨": None, "타코마요 치킨": None,
    "간장 치킨": None, "후라이드 치킨": None, "양념 치킨": None,
    "매운 양념 치킨": None, "청양고추마요 치킨": None,
    # 부위별 — 전부 「+콜라1」 세트로만 있다 → null
    "플라윙 세트 (윙+봉)": None, "다리 (스틱)": None,
    "날개+다리": None, "윙+다리": None, "호식이 안심텐더": None,
    "닭발 튀김": None, "똥집 튀김": None,
    # 사이드 — 이름이 거의 그대로 붙는다
    "체다마요 감자튀김": "체다마요 감자튀김",
    "치폴레 감자튀김": "치폴레 감자튀김",
    "감자볼튀김": "감자볼튀김",
    "감자튀김": "감자튀김",
    "마늘떡볶이": "마늘떡볶이",
    "로제비엔나떡볶이": "로제비엔나떡볶이",
    "쉬림프 미니튀김(칠리)": "쉬림프 미니튀김(칠리)",
    "쉬림프 미니튀김(레몬크림)": "쉬림프 미니튀김(레몬크림)",
    "치즈볼 2종세트": "치즈볼 2종 세트(6개)",
    "트리플치즈볼": "트리플치즈볼(6개)",
    "트리플 치즈볼(6개)": "트리플치즈볼(6개)",
    "허니갈릭치즈볼": "허니갈릭치즈볼(6개)",
    "허니갈릭치즈볼(6개)": "허니갈릭치즈볼(6개)",
    # 소스만 고르는 메뉴 — 두 소스가 같은 값이라 그대로 쓴다
    "크리스피 치킨넥": "크리스피 치킨넥(닭목살)+머스타드(2ea)",
    "통살가득 텐더킹": "통살가득 텐더킹(5pc)+머스타드(2ea)",
    "똥집 미니튀김": "똥집 미니튀김(조미소금)",
    "똥집미니튀김": "똥집 미니튀김(조미소금)",
    # 치킨무는 앱에 「무 추가」(500원, 옵션 추가금)만 있다 — 메뉴 판매가가 아니다
    "치킨무": None,
}

# 단품이 없을 때 근거로 남길 세트 (홈페이지메뉴 → 앱 세트명)
BUNDLE_HINT = {
    "맵시크 치킨": "[비스트라이더 세트] 맵시크치킨 한마리+한마리 세트",
    "수라깐풍 치킨": "[캐논걸 세트] 수라깐풍치킨 한마리+한마리 세트",
    "간장 치킨": "[하그 세트] 간장치킨 한마리+ 한마리 세트",
    "플라윙 세트 (윙+봉)": "(추천) 플라윙(윙+봉)세트+콜라1",
    "다리 (스틱)": "다리만+콜라1",
    "날개+다리": "날개+다리+콜라1",
    "윙+다리": "날개+다리+콜라1",
    "호식이 안심텐더": "안심텐더+치즈볼 3개",
    "닭발 튀김": "닭발튀김+콜라",
    "똥집 튀김": "똥집튀김+콜라",
    "치킨무": "무 추가",
}

# 치킨 단품에 함께 적어둘 두마리(한마리+한마리) 세트가
TWO_BIRD = {
    "딥블랙갈릭 치킨": "[신메뉴]딥블랙갈릭치킨 한마리+한마리 세트",
    "깐쇼킹 치킨": "[HIT]깐쇼킹치킨 한마리+한마리 세트",
    "매운 간장 치킨": "[강추]매운간장치킨 한마리+한마리 세트",
    "크리스피골드": "크리스피 골드(국내산 순살)+한마리 세트",
}


def mode_of(counter):
    """최빈 가격과 (동의 매장수, 관측 매장수)"""
    if not counter:
        return None, 0, 0
    price, cnt = max(counter.items(), key=lambda kv: (kv[1], -kv[0]))
    return price, cnt, sum(counter.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="9292.json 에 실제로 쓴다")
    a = ap.parse_args()

    nstores, prices, origins = survey()
    if nstores < 20:
        print("❌ 표본이 너무 적다 — 쓰지 않는다")
        return 1

    doc = json.load(io.open(OUT, encoding="utf-8"))
    filled = skipped = 0
    lines = []
    for m in doc["menus"]:
        nm = m["name"]
        if nm not in MAP:
            lines.append("   ? %-24s 매핑표에 없음 — 손대지 않음" % nm)
            continue
        app_name = MAP[nm]
        note_bits = []
        price = None
        if app_name:
            p, agree, seen = mode_of(prices.get(app_name))
            if p is not None and seen >= MIN_STORES:
                price = p
                note_bits.append("스마트오더 「%s」 %s원 (전국 %d개 매장 중 %d곳 동일)"
                                 % (app_name, format(p, ","), seen, agree))
            else:
                note_bits.append("스마트오더 「%s」 관측 %d곳뿐 — 값을 쓰지 않음" % (app_name, seen))
        hint = BUNDLE_HINT.get(nm)
        if hint:
            p2, _, seen2 = mode_of(prices.get(hint))
            if p2 is not None:
                note_bits.append("단품 없음 · 세트만 있음: 「%s」 %s원(%d곳)"
                                 % (hint, format(p2, ","), seen2))
        two = TWO_BIRD.get(nm)
        if two:
            p3, _, seen3 = mode_of(prices.get(two))
            if p3 is not None:
                note_bits.append("두마리(한마리+한마리) 「%s」 %s원(%d곳)"
                                 % (two, format(p3, ","), seen3))
        if price is not None:
            m["price"] = price
            m["price_source"] = "official_smartorder"
            filled += 1
        else:
            skipped += 1
        if note_bits:
            m["price_note"] = " / ".join(note_bits) + \
                " [출처 hosigi.wmpoplus.com 스마트오더 API · %s 수집 · 홀/픽업가(배달가산 없음) · 가격은 매장·시기에 따라 달라진다]" % COLLECTED
        lines.append("   %s %-24s %s" % ("✓" if price is not None else "·", nm,
                                         format(price, ",") + "원" if price is not None else "(비움)"))

    doc["price_note_all"] = (
        "공식 홈페이지(9922.co.kr)엔 가격이 0건. 판매가는 자사 스마트오더 "
        "(hosigi.wmpoplus.com / api.thecupping.co.kr) 에서 받았다. "
        "전국 %d개 매장 표본의 최빈값이며 홀/픽업가다(주문타입별 가격이 아예 없다). "
        "세트로만 파는 메뉴는 콜라값을 빼지 않고 비워뒀다. 가격은 매장·시기에 따라 달라진다." % nstores)
    if origins:
        doc["origin_note_smartorder"] = origins.most_common(1)[0][0]

    print("\n".join(lines))
    print("\n가격 채움 %d개 · 비움 %d개 (표본 매장 %d곳)" % (filled, skipped, nstores))
    if a.apply:
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("✅ 저장", OUT)
    else:
        print("(미리보기다. 반영하려면 --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
