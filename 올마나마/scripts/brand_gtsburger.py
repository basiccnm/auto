# -*- coding: utf-8 -*-
"""GTS버거(slug gtsburger, brand_id 43) 메뉴판 수집 — 카테고리·메뉴·순서. 2026-07-28

    python scripts/brand_gtsburger.py
    → data/brand_menu_list/gtsburger.json  (DB 는 건드리지 않는다)

사이트 실측 (2026-07-28)
------------------------
공식 홈페이지 `http://gtsburger.com/` — **imweb** 으로 만든 사이트다(홈 501KB).

🔴 **imweb 이지만 SPA 가 아니다.** 호식이(`9922.co.kr`)와 같은 구조로,
   `gallery2` 위젯이 **서버에서 다 렌더돼 온다.** 그래서 순수 HTTP 로 충분하다.
   브라우저로 열어 대조했고 **DOM 순서 = 화면 순서**였다(BURGER 9개 · SIDES&SHAKE 7개 그대로).
   「더보기」 버튼이 2개 있지만 AJAX 가 아니라 **이미 DOM 에 있는 걸 보여주기만** 한다.

메뉴 탭은 **홈의 네비게이션에서 찾았다**(주소를 조합하지 않았다).
`li.depth-01 > a` 의 `data-code` 가 imweb 메뉴코드다:

    /home  HOME          ← 메뉴 아님
    /16    ABOUT US      ← 메뉴 아님(브랜드 소개)
    /20    JOIN GTS      ← 메뉴 아님(가맹문의)
    /17    BURGER SHOP   ← 메뉴 아님. **매장 찾기 폴더**(하위 서울·경기·인천·대전·전라)
    /18    BURGER        ★ 메뉴 9개
    /19    SIDES&SHAKE   ★ 메뉴 7개

🔴 **이름은 메뉴 카드 블록 안(`div[id^=caption_] > h4`)에서만** 집는다.
   페이지 전체 텍스트를 훑으면 `알림`·`뒤로`·`Alarm`·`로그아웃`·`서울`·`site search` 같은
   화면 글자가 메뉴로 들어간다 — **기존 DB 의 GTS버거 14행이 전부 그것이다**(실제 사고).
   `h4` 안의 `<span>` 은 영문명이라 `name_en` 으로 뺀다.

🔴 **가격은 사이트 어디에도 없다.** 홈·/16·/17·/18·/19·/20 여섯 쪽에서 `숫자+원` **0건**,
   브라우저로 렌더한 DOM 에서도 **0건**. 그래서 전부 `price: null` 이다. 짐작해 넣지 않는다.
   메뉴 이미지도 음식 사진뿐이라 판독할 가격표가 없다(/18 에 썸네일 9 + 로고·배너 3).

   ⚠️ **버거킹처럼 「응답에는 들어 있는」 경우인지 imweb 쇼핑몰 쪽까지 다시 팠다(2026-07-28).**
      버거킹은 자체 API 가 `dineInprc`(홀 판매가)를 줬지만 **GTS 는 그런 게 없다.** 근거:

      - **메뉴판이 쇼핑몰 상품이 아니라 `gallery2`(사진 갤러리) 위젯이다.**
        페이지 위젯 목록 = `inline_menu·inline_logo·inline_icon·inline_menu_btn·inline_login_btn·
        inline_search_btn·padding·text·gallery2·code·hr` — **상품 위젯(`prod_list` 등)이 아예 없다.**
        `.shop-content, .prod_list, [class*=product]` 요소 **0개**
      - 카드의 `data-*` 는 `bg·src·sub-html·no·org` 뿐 — **가격 필드가 없다.**
        캡션(`caption_<번호>`)에도 한글명·영문명만 들어 있다
      - **화면이 부르는 자원에 상품/가격 API 가 없다**(`performance.getEntriesByType('resource')`).
        `site_shop*.js`·`recent_product.js`·`oms-shop-bridge` 가 뜨지만 **imweb 이 모든 사이트에 항상 얹는
        쇼핑몰 엔진 스크립트**일 뿐이고, 상품을 받아오는 호출은 한 건도 없다. `RECENT_PRODUCT` 도 함수뿐
      - 인라인 스크립트에서 `"...price/prc/amt/cost": <숫자>` **0건**. 갤러리 캡션 번호(`32556170`)가
        **어떤 스크립트에도 안 나온다** → 갤러리는 순수 HTML 이고 뒤에 JSON 데이터층이 없다
      - ⚠️ HTML 을 그냥 grep 하면 `price` 가 11건 잡히는데 **전부 CSS 선택자와 테마 설정**이다
        (`.shop-content .price`, `"prod_list_price_font_size":0`). `LOCALIZE.타이틀_원산지` 와 같은
        **껍데기지 값이 아니다.** 숫자가 붙은 실제 상품 데이터가 아닌지 반드시 확인할 것

      결론: **imweb 카드·전역변수·화면이 부르는 API 까지 확인했고 가격이 공개돼 있지 않다.**

🔴 **원산지 표기가 없다.** 여섯 쪽에서 `원산지` 문자열은 2건씩 나오지만 전부
   imweb 쇼핑몰 JS 의 번역 사전(`LOCALIZE.타이틀_원산지`)이지 표기가 아니다.
   알레르기·중량도 0건. 그래서 `origin_raw`·`allergy_raw`·`weight_raw` 는 비운다.

⚠️ 상세페이지가 없다 — 갤러리 카드에 `item_container` 링크가 **하나도 없다**(`detail_url: null`).
   `ext_id` 는 imweb 갤러리의 `caption_<번호>` 번호를 쓴다.
"""
import io
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "GTS버거"                      # DB brands.name (slug gtsburger, id 43)
SLUG = "gtsburger"
BASE = "http://gtsburger.com"
COLLECTED = "2026-07-28"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")
CACHE = os.path.join(tempfile.gettempdir(), "olmanama_gtsburger")

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
GAP = 1.6                              # 요청 간격 1.5초 이상
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 홈 네비게이션 순서 그대로. ext_id 는 imweb 메뉴코드(li 의 data-code)
TABS = [
    ("BURGER", "/18", "m202605183f981d8b87a8a"),
    ("SIDES&SHAKE", "/19", "m202605186e55c6a56ceb2"),
]
# 메뉴가 아니라서 안 훑는 쪽 — 훑었다는 근거는 남긴다
NOT_MENU = [("/home", "HOME"), ("/16", "ABOUT US"), ("/20", "JOIN GTS"),
            ("/17", "BURGER SHOP (매장찾기 폴더 · 하위 서울/경기/인천/대전/전라)")]

RX_ITEM_SPLIT = '<div class="_item item_gallary'
RX_CAP = re.compile(r'(?s)<div id="caption_(\d+)"[^>]*>\s*(.*?)\s*</div>')
RX_H4 = re.compile(r"(?s)<h4>(.*?)</h4>")
RX_SPAN = re.compile(r"(?s)<span[^>]*>(.*?)</span>")
RX_HREF = re.compile(r'class="item_container _item_container[^"]*"\s*href="([^"]*)"')
RX_IMG = re.compile(r'data-src="([^"]+)"')
RX_WON = re.compile(r"[0-9][0-9,]{2,}\s*원")


def fetch(path):
    fn = os.path.join(CACHE, re.sub(r"[^0-9A-Za-z_.-]", "_", path.strip("/") or "root") + ".html")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < 86400:
        return io.open(fn, encoding="utf-8").read()
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(BASE + path, headers=HDRS)
    html = urllib.request.urlopen(req, timeout=45, context=CTX).read().decode("utf-8", "replace")
    io.open(fn, "w", encoding="utf-8").write(html)
    time.sleep(GAP)
    return html


def decomment(html):
    """HTML 주석을 먼저 걷어낸다"""
    return re.sub(r"(?s)<!--.*?-->", " ", html)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).replace("&nbsp;", " ").strip()


def reject_reason(name, cat_names):
    """메뉴 아닌 것 걸러내기 — 걸린 것은 지우기 전에 목록으로 출력한다"""
    if not name:
        return "이름 없음(빈 갤러리 칸)"
    if re.search(r"[.!?]$", name):
        return "문장부호로 끝남"
    if len(name) >= 18:
        return "18자 이상"
    if name in cat_names:
        return "카테고리 이름과 같음"
    return None


def parse_tab(html):
    """메뉴 카드 블록 안에서만 집는다 — 페이지 전체 텍스트를 훑지 않는다"""
    out = []
    for blk in html.split(RX_ITEM_SPLIT)[1:]:
        blk = blk[:9000]
        cap = RX_CAP.search(blk)
        name = name_en = None
        cap_id = None
        if cap:
            cap_id = cap.group(1)
            h4 = RX_H4.search(cap.group(2))
            if h4:
                raw = h4.group(1)
                sp = RX_SPAN.search(raw)
                name_en = strip_tags(sp.group(1)) if sp else None
                name = strip_tags(re.sub(r"(?s)<span[^>]*>.*?</span>", " ", raw))
        href = RX_HREF.search(blk)
        img = RX_IMG.search(blk)
        out.append({"name": name, "name_en": name_en, "ext_id": cap_id,
                    "href": href.group(1) if href and href.group(1) else None,
                    "img": img.group(1) if img else None})
    return out


def main():
    cat_names = [t[0] for t in TABS]
    cats = [{"name": n, "parent": None, "ext_id": e} for n, _, e in TABS]

    print("메뉴 아닌 쪽 (훑지 않음)")
    for p, why in NOT_MENU:
        print(f"    - {p:<7} {why}")

    menus = []
    dropped = []
    won_hits = 0
    for cname, path, _ in TABS:
        html = decomment(fetch(path))
        won_hits += len(RX_WON.findall(html))
        items = parse_tab(html)
        kept = 0
        for idx, it in enumerate(items):
            why = reject_reason(it["name"], cat_names)
            if why:
                dropped.append((cname, idx, it["name"], why))
                continue
            menus.append({
                "name": it["name"],
                "name_en": it["name_en"],
                "price": None,
                "price_source": None,
                "price_note": None,
                "compose_raw": None,
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "detail_url": (BASE + it["href"]) if it["href"] else None,
                "image_url": it["img"],
                "ext_id": it["ext_id"],
                "cats": [[cname, kept]],
            })
            kept += 1
        print(f"{cname:<12} {path:<5} 갤러리칸 {len(items):>2} → 메뉴 {kept}")

    if not menus:
        print("❌ 메뉴 0개 — 저장하지 않는다")
        return 1

    data = {
        "brand": BRAND,
        "slug": SLUG,
        "source": BASE + "/18 · " + BASE + "/19",
        "collected_at": COLLECTED,
        "origin_note": None,
        "price_note_all": "공식 홈페이지에 판매가가 공개돼 있지 않다 — 홈·/16·/17·/18·/19·/20 "
                          "여섯 쪽에서 「숫자+원」 %d건. 브라우저로 렌더한 DOM 에서도 0건이다. "
                          "버거킹처럼 응답에만 숨어 있는지 imweb 쇼핑몰 쪽까지 확인했으나 없다 — "
                          "메뉴판이 상품이 아니라 gallery2(사진 갤러리) 위젯이라 상품 위젯·상품 요소가 0개이고, "
                          "카드 data-* 에 가격 필드가 없고, 화면이 부르는 자원에 상품/가격 API 가 없다"
                          "(site_shop*.js 는 imweb 이 모든 사이트에 얹는 엔진일 뿐 상품 호출 0건). "
                          "HTML 의 price 11건은 전부 CSS 선택자·테마 설정이지 값이 아니다" % won_hits,
        "origin_note_all": "공식 홈페이지에 원산지 표기가 없다 — 「원산지」 문자열은 쪽마다 2건씩 나오지만 "
                           "전부 imweb 쇼핑몰 JS 의 번역 사전(LOCALIZE.타이틀_원산지)이다. 알레르기·중량도 0건",
        "cats": cats,
        "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))

    print("\n버린 줄 %d개" % len(dropped))
    for c, i, n, why in dropped:
        print(f"    - [{c} #{i}] {n!r} — {why}")
    npar = sum(1 for c in cats if c["parent"])
    npr = sum(1 for m in menus if m["price"] is not None)
    nco = sum(1 for m in menus if m["compose_raw"])
    nor = sum(1 for m in menus if m["origin_raw"])
    print(f"\n✅ {OUT}")
    print(f"   카테고리 {len(cats)}개(하위 {npar}) · 메뉴 {len(menus)}개 · "
          f"가격 있는 것 {npr}개 · 구성 {nco}개 · 원산지 {nor}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
