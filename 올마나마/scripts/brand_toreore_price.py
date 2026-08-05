# -*- coding: utf-8 -*-
"""또래오래 판매가 — 자사 스마트오더 API 에서. 2026-07-31

    python scripts/brand_toreore_price.py            # 수집 + 미리보기
    python scripts/brand_toreore_price.py --apply    # data/brand_menu_list/toreore.json 의 price 만 갱신

⚠️ 이름·순서·카테고리·알레르기는 **건드리지 않는다.** `price` / `price_note` / `price_source` 만 쓴다.
⛔ DB 는 건드리지 않는다.

━━ 어떻게 뚫었나 (wmpoplus 스마트오더 — 호식이·기영이와 같은 플랫폼) ━━━━━━━
공식 홈페이지(toreore.com)엔 가격이 **0건**이다. 가격은 자사 스마트오더에만 있다.
1. 앱 `com.wmpoplus.toreore` dex 문자열의 웹뷰 주소:
       https://toreore.wmpoplus.com/    ← 주문 사이트 (Next.js)
       https://api.wmpo.co.kr           ← 🔴 계정용. 여기 찌르면 401 이다. API 가 아니다
2. 브랜드 코드 (공개·토큰 불필요):
       GET https://d11u7cg79d1e8u.cloudfront.net/sites/toreore.json
       → siteID 169 · companyID 70882 · (주)농협목우촌 외식사업단
3. 진짜 API 는 `https://api.thecupping.co.kr` (주문 사이트 JS 청크의 `E0` 상수).
   GET /init → data.token (게스트 토큰). 이후 모든 요청에 `token:` 헤더.
4. 매장:  GET /stores?lat=&lon=&page=&searchKeyword=&useSearch=1
   🔴 좌표 하나로 전 페이지를 돌면 전국이 다 나온다(서울 367곳 = 제주 367곳).
5. 메뉴·가격:  GET /stores/{storeID}/products  (파라미터 없음)
       가격 = options 중 alias=="PRICE" 그룹 children[].prices.KRW.price

🔴 **홀/배달 가격 구분이 없다.** 여기 담는 값은 배달 가산이 없는 매장(홀·픽업) 판매가다.
   픽업전용 29곳 vs 픽업+배달 330곳을 대조했더니, 값이 갈린 것은 **주류·음료뿐**이고
   (소주/맥주/콜라 — 매장 자율가) **치킨·사이드는 갈리지 않았다.**

🔴 **또래오래는 가맹점 자율가다.** 치킨류 최빈값 동의율이 48~57% 밖에 안 된다
   (예: 후라이드반+양념반 363곳 중 20,500원 176곳 / 22,000원 69곳 / 23,000원 30곳).
   사이드·소스는 85~99% 로 안정적이다. 그래서 `price_note` 에 **동의율을 항상 적는다.**
   기영이(동의율 100%)와 달리 이 값은 "가장 흔한 가격"이지 "정가"가 아니다.

🔴 **`data.origin` 을 쓰지 않는다 — 또래오래 것이 아니다.**
   367곳 전부 똑같은 문자열이 들어 있는데 내용이 **맘스터치 원산지표**다
   (싸이버거·와우순살·맘스양념·후덕죽…). 또래오래 매장에 그런 상품은 **한 개도 없다.**
   플랫폼/본사가 잘못 채워둔 값이라 `origin_raw` 는 공식 홈페이지 값을 그대로 둔다.
   확인용으로 `origin_note_smartorder_rejected` 에만 원문을 남긴다.
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

SLUG = "toreore"
HOST = "toreore.wmpoplus.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")

API = "https://api.thecupping.co.kr"
SITE_JSON = "https://d11u7cg79d1e8u.cloudfront.net/sites/toreore.json"
UA = ("Mozilla/5.0 (Linux; Android 14; SM-F956N) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
COLLECTED = "2026-07-31"
MIN_STORES = 50          # 이만큼은 봐야 그 값을 쓴다

# ── 홈페이지 메뉴명 → 스마트오더 상품명 ──────────────────────────────
# 🔴 손으로 하나씩 대조한 표다. 자동 유사매칭 안 한다.
#    None = 스마트오더 표본에 사실상 없다 → price 는 null 로 둔다.
MAP = {
    "[NEW] 뿌레카치킨": "[NEW] 뿌레카치킨",
    # 오리지널 — 앱은 「오곡 ○○ 치킨」으로 띄어쓴다
    "오곡후라이드": "오곡 후라이드 치킨",
    "오곡핫양념치킨": "오곡 핫양념 치킨",
    "오곡양념치킨": "오곡 양념 치킨",
    "오곡갈릭플러스": "오곡 갈릭플러스 치킨",
    "오곡파닭": "오곡 파닭 치킨",
    "갈반핫반": "갈릭반+핫양념반",
    # 시그니처
    "카레마요": "카레마요치킨 순살(가슴살)",   # 앱에 한마리가 없다 — 순살 전용 메뉴
    "고추단짠치킨": "고추단짠치킨",
    "단짠치킨": "단짠치킨",
    "콘듀치킨": "콘듀치킨",
    "마왕치킨": None,                          # 표본 367곳 중 17곳뿐 — 값을 쓰지 않는다
    "스모키양념치킨": "스모키양념 한마리",
    "코코순살치킨": "코코순살 치킨",
    "맵부심후라이드": "맵부심후라이드",
    "맵부심양념": "맵부심양념",
    "엔젤치킨": "엔젤치킨",
    # 순살&콤보
    "순살(가슴살) 듀오": "순살(가슴살) 후라이드+갈릭플러스",   # 6개 조합 중 최저가 조합
    "내맘다강정": "내맘다강정",
    "골드치킨": "골드치킨",
    # 바베큐
    "바베큐치킨": "바베큐 치킨",
    "핫참숯통다리 바베큐치킨": "핫참숯 통다리바베큐",
    # 사이드
    "말랑피자볼": "말랑피자볼(6구)",
    "말랑단팥볼": "말랑단팥볼(6구)",
    "말랑호떡볼": "말랑호떡볼(6구)",
    "말랑삼색볼(호떡, 단팥, 피자)": "말랑삼색볼(6구)",
    "리얼치즈볼": "리얼치즈볼",
    "국물떡볶이": "국물떡볶이",
    "어포": "어포",
    "카사바칩": "카사바칩",
    "바삭한 근위튀김": "바삭한근위튀김",
    "소떡소떡": "콘듀맛소떡",                  # 앱은 맛별로 둘 — 둘 다 같은 값
    "해시브라운": "해쉬브라운(8EA)",
    "치즈스틱": "치즈스틱(4EA)",
    "후렌치후라이": "후렌치후라이",
}

# 부위별(순살·윙봉·스틱·콤보) 가격을 함께 적을 메뉴 — 앱 상품명의 앞토막
VAR_STEM = {
    "[NEW] 뿌레카치킨": "[NEW] 뿌레카치킨",
    "고추단짠치킨": "고추단짠치킨", "단짠치킨": "단짠치킨", "콘듀치킨": "콘듀치킨",
    "스모키양념치킨": "스모키양념", "맵부심후라이드": "맵부심후라이드",
    "맵부심양념": "맵부심양념",
}
VARIANTS = ("순살", "윙봉", "스틱", "콤보")

# 단품 대신·함께 적을 근거 (홈페이지메뉴 → [앱 상품명…])
ALSO = {
    "카레마요": ["카레마요치킨 순살(다리살)"],
    "소떡소떡": ["스모키양념맛소떡"],
    "내맘다강정": ["내맘다강정+찹쌀고구마치즈볼", "내맘다강정+어포"],
    "순살(가슴살) 듀오": ["순살(가슴살)  후라이드+양념", "순살(가슴살)  후라이드+핫양념",
                     "순살(가슴살)  갈릭플러스+양념", "순살(가슴살)  갈릭플러스+핫양념",
                     "순살(가슴살) 양념+핫양념"],
    "갈반핫반": ["후라이드반+양념반", "후라이드반+핫양념반", "후라이드반+갈릭반", "양념반+갈릭반"],
}
# 값을 못 쓴 이유
WHY_NULL = {
    "마왕치킨": "스마트오더 전국 367곳 중 「마왕치킨」계열이 17곳뿐 — 표본이 모자라 비웠다",
}

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
    try:
        return _raw(path, params)
    except Exception:
        if _depth < 3 and path != "/init":
            time.sleep(1.5)
            guest_token()
            return api(path, params, _depth + 1)
        raise


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

    prices = collections.defaultdict(collections.Counter)
    bygrp = {"pick": collections.defaultdict(collections.Counter),
             "both": collections.defaultdict(collections.Counter)}
    nby = {"pick": 0, "both": 0}
    origins = collections.Counter()
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
            nby[grp] += 1
        if d.get("origin"):
            origins[d["origin"].strip()] += 1
        for cat in d.get("products") or []:
            for p in cat.get("products") or []:
                if p.get("isDisplay") == 0:
                    continue
                for optname, price in price_rows(p):
                    key = p["name"] if not optname else "%s | %s" % (p["name"], optname)
                    prices[key][price] += 1
                    if grp:
                        bygrp[grp][key][price] += 1
        ok += 1
        if i % 50 == 0:
            print("   %d/%d" % (i, len(stores)))
        time.sleep(0.1)
    print("메뉴판 %d곳 수집 · %d곳 실패 (픽업전용 %d · 픽업+배달 %d)"
          % (ok, fail, nby["pick"], nby["both"]))
    return ok, prices, origins, bygrp


def mode_of(counter):
    if not counter:
        return None, 0, 0
    p, c = max(counter.items(), key=lambda kv: (kv[1], -kv[0]))
    return p, c, sum(counter.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="toreore.json 에 실제로 쓴다")
    a = ap.parse_args()

    n, prices, origins, bygrp = survey()
    if n < MIN_STORES:
        print("❌ 표본이 너무 적다 — 쓰지 않는다")
        return 1

    doc = json.load(io.open(OUT, encoding="utf-8"))
    filled = skipped = 0
    lines = []
    split = []
    for m in doc["menus"]:
        nm = m["name"]
        if nm not in MAP:
            lines.append("   ? %-22s 매핑표에 없음 — 손대지 않음" % nm)
            continue
        app = MAP[nm]
        bits = []
        price = None
        if app:
            p, agree, obs = mode_of(prices.get(app))
            if p is not None and obs >= MIN_STORES:
                price = p
                bits.append("스마트오더 「%s」 %s원 (전국 %d개 매장 중 이 메뉴를 파는 %d곳, "
                            "%d곳 동일=%.0f%%)" % (app, format(p, ","), n, obs, agree,
                                                100.0 * agree / obs))
            else:
                bits.append("스마트오더 「%s」 관측 %d곳뿐 — 값을 쓰지 않음" % (app, obs))
            pp, _, _ = mode_of(bygrp["pick"].get(app))
            pb, _, _ = mode_of(bygrp["both"].get(app))
            if pp is not None and pb is not None and pp != pb:
                bits.append("⚠️픽업전용 %s / 픽업+배달 %s" % (pp, pb))
                split.append(nm)
        if nm in WHY_NULL:
            bits.append(WHY_NULL[nm])
        # 부위별
        stem = VAR_STEM.get(nm)
        if stem:
            vs = []
            for v in VARIANTS:
                vp, _, vo = mode_of(prices.get("%s %s" % (stem, v)))
                if vp is not None and vo >= MIN_STORES:
                    vs.append("%s %s원(%d곳)" % (v, format(vp, ","), vo))
            if vs:
                bits.append("부위별: " + " / ".join(vs))
        for other in ALSO.get(nm, []):
            op, _, oo = mode_of(prices.get(other))
            if op is not None and oo >= MIN_STORES:
                bits.append("같이 파는 「%s」 %s원(%d곳)" % (other, format(op, ","), oo))
        if price is not None:
            m["price"] = price
            m["price_source"] = "official_smartorder"
            filled += 1
        else:
            skipped += 1
        if bits:
            m["price_note"] = " / ".join(bits) + (
                " [출처 %s 스마트오더 · %s 수집 · 홀/픽업가(배달 가산 없음) · "
                "또래오래는 가맹점 자율가라 매장마다 다르다 · 가격은 시기에 따라 달라진다]"
                % (HOST, COLLECTED))
        lines.append("   %s %-22s %s" % ("✓" if price is not None else "·", nm,
                                         (format(price, ",") + "원") if price is not None else "(비움)"))

    doc["price_note_all"] = (
        "공식 홈페이지(toreore.com)엔 가격이 0건. 판매가는 자사 스마트오더 "
        "(%s / api.thecupping.co.kr)에서 받았다. 전국 %d개 매장을 전부 훑은 최빈값이고 "
        "홀/픽업가다(API 에 주문타입별 가격이 아예 없다). "
        "🔴 또래오래는 가맹점 자율가라 치킨류 동의율이 48~57%%에 그친다(사이드·소스는 85~99%%). "
        "메뉴마다 동의율을 price_note 에 적었다. 가격은 매장·시기에 따라 달라진다." % (HOST, n))
    if origins:
        doc["origin_note_smartorder_rejected"] = (
            "⚠️ 스마트오더 data.origin 은 367곳 전부 동일하지만 내용이 **맘스터치 원산지표**다"
            "(싸이버거·와우순살·맘스양념 등 — 또래오래 매장에 그런 상품은 하나도 없다). "
            "본사/플랫폼이 잘못 채운 값이라 origin_raw 에 반영하지 않았다. 원문: "
            + origins.most_common(1)[0][0])

    print("\n".join(lines))
    print("\n가격 채움 %d개 · 비움 %d개 (표본 매장 %d곳)" % (filled, skipped, n))
    print("픽업전용/배달 값이 갈린 메뉴: %s" % (", ".join(split) if split else "없음"))
    if a.apply:
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("✅ 저장", OUT)
    else:
        print("(미리보기다. 반영하려면 --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
