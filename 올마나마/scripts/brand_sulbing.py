# -*- coding: utf-8 -*-
"""설빙(sulbing) 메뉴판 수집 — data/brand_menu_list/sulbing.json 한 장만 만든다.

경로 (앱)
---------
설빙 앱(com.sulbing.mobile.app)은 Expo 껍데기이고 APK assets/app.config 의
  "WEBVIEW_URL": "https://sapp.sulbing.com"
가 실제 화면이다. 그 페이지는 Nuxt SPA(data-ssr:false)라 --dump-dom 으로는 아무것도 안 나온다.
대신 페이지가 부트할 때 심어놓은 설정에 자체 API 주소가 그대로 적혀 있다:

  https://sapp.sulbing.com/menu
    -> window.__NUXT__.config.public.apiHost = "https://app-api.easymembership.co.kr/api/v1"
    -> window.__NUXT__.config.public.apiCode = "HE9"          (헤더 Headquarters-Code)
    -> /_nuxt/CUN2H2i7.js 의 GET 래퍼가 헤더 {accept, Headquarters-Code, Content-Type} 를 붙인다
    -> 같은 파일의 getList(): "/products/all/" + storeId  또는  "/products/all/noStore"

  최종:  GET /api/v1/products/all/noStore   (Headquarters-Code: HE9)
         -> {"content":[{categoryId, categoryName, sort, categoryProducts:[...]}, ...]}
         카테고리 11개 · 상품 163행이 한 번에 온다. 페이지를 넘길 필요가 없다.

⚠️ 앱 화면의 /menu?type= 은 카테고리가 아니다. /_nuxt/CkXotTmM.js 의 탭 정의가
   menu:[{label:"전체 메뉴",value:"all"},{label:"마이 메뉴",value:"my"}]
   두 개뿐이다. 그래서 카테고리 ext_id 는 사이트가 실제로 쓰는 categoryId 를 넣는다.

⛔ DB 를 import 하지 않는다. 이 스크립트는 JSON 한 장만 쓴다.
"""
import sys
import io
import os
import json
import urllib.request
import datetime

sys.stdout.reconfigure(encoding="utf-8")

API = "https://app-api.easymembership.co.kr/api/v1/products/all/noStore"
HDR = {
    "accept": "*/*",
    "Headquarters-Code": "HE9",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Origin": "https://sapp.sulbing.com",
    "Referer": "https://sapp.sulbing.com/",
}
DETAIL = "https://sapp.sulbing.com/menu/detail?productId={}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "sulbing.json")

SOURCE = ("설빙 앱 WebView(sapp.sulbing.com, Nuxt SPA)의 자체 API — "
          "GET https://app-api.easymembership.co.kr/api/v1/products/all/noStore "
          "(헤더 Headquarters-Code: HE9). apiHost/apiCode 는 /menu 페이지의 "
          "window.__NUXT__.config, 엔드포인트는 /_nuxt/CUN2H2i7.js 의 getList() 에서 확인")


def fetch():
    req = urllib.request.Request(API, headers=HDR)
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    return json.loads(raw)


NAV = {"NEW", "BEST", "매장찾기", "이벤트", "전체", "전체 메뉴", "마이 메뉴",
       "SIGNATURE", "할인", "최저"}


def looks_not_a_menu(name, cat_names):
    """메뉴가 아닌 줄(홍보문구·탭이름·네비게이션) 후보를 잡아낸다.
    반환: (사유, 버릴지 여부). 걸린 것은 버리든 남기든 전부 목록으로 출력한다."""
    n = (name or "").strip()
    if not n:
        return "빈 이름", True
    if n[-1] in ".!?~,":
        return "문장부호로 끝남", True
    if n in cat_names:
        return "카테고리 이름과 같음", True
    if n.upper() in NAV:
        return "네비게이션/UI 문자열", True
    if len(n) >= 18:
        # POS 상품 피드라 홍보문구가 섞일 자리가 없다. 길이만으로 버리면
        # 「하겐다즈딸기아이스크림2스쿱(토핑)」 같은 진짜 상품이 날아간다.
        return "18자 이상 (POS 상품코드·가격이 있어 남김)", False
    return None, False


def main():
    data = fetch()
    content = data.get("content") or []
    if not content:
        print("❌ 카테고리를 하나도 못 얻었다 — 파일을 저장하지 않는다.")
        return 2

    cat_names = {c.get("categoryName") for c in content}

    cats = []
    menus = []          # 화면에 처음 나온 순서
    by_name = {}        # 이름 -> menus 안의 dict (같은 메뉴가 여러 탭에 진열된다)
    dropped = []
    flagged = []

    for c in content:
        cname = c.get("categoryName")
        cats.append({"name": cname, "parent": None,
                     "ext_id": str(c.get("categoryId"))})
        for idx, p in enumerate(c.get("categoryProducts") or []):
            # 사이트 표기 그대로. viewProductName 이 비면 productName 이 화면에 나간다.
            name = (p.get("viewProductName") or p.get("productName") or "").strip()
            why, drop = looks_not_a_menu(name, cat_names)
            if why:
                (dropped if drop else flagged).append(
                    (cname, name, p.get("productPrice"), why))
            if drop:
                continue

            m = by_name.get(name)
            if m is None:
                desc = " ".join(x for x in [(p.get("description") or "").strip(),
                                            (p.get("description2") or "").strip()] if x)
                price = p.get("productPrice")
                m = {
                    "name": name,
                    "price": price if isinstance(price, int) and price > 0 else None,
                    "price_source": "official",
                    "weight_raw": None,     # 앱/POS 어디에도 용량·중량이 없다
                    "origin_raw": None,     # 원산지 표기 없음
                    "allergy_raw": None,    # 알레르기 표기 없음
                    "compose_raw": desc or None,
                    "detail_url": DETAIL.format(p.get("id")),
                    "image_url": p.get("productImage") or None,
                    "ext_id": p.get("productCode"),
                    "cats": [],
                }
                by_name[name] = m
                menus.append(m)
            m["cats"].append([cname, idx])

    out = {
        "brand": "설빙",
        "slug": "sulbing",
        "source": SOURCE,
        "collected_at": datetime.date.today().isoformat(),
        "cats": cats,
        "menus": menus,
    }

    if dropped:
        print("— 버린 줄 (%d) —" % len(dropped))
        for cn, nm, pr, why in dropped:
            print("   [%s] %r  %s  ← %s" % (cn, nm, pr, why))
    else:
        print("— 버린 줄 없음 —")
    if flagged:
        print("— 걸렸지만 남긴 줄 (%d) —" % len(flagged))
        for cn, nm, pr, why in flagged:
            print("   [%s] %r  %s  ← %s" % (cn, nm, pr, why))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    rows = sum(len(m["cats"]) for m in menus)
    priced = sum(1 for m in menus if m["price"])
    print("카테고리 %d개(하위 0) · 메뉴 %d개 · 가격 있는 것 %d개 · 진열 %d건"
          % (len(cats), len(menus), priced, rows))
    print("경로: 앱(sapp.sulbing.com WebView) 자체 API")
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
