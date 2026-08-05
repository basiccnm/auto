# -*- coding: utf-8 -*-
"""죽이야기 메뉴판 — 공식 홈페이지에서 카테고리·메뉴·가격을 긁어 **JSON 한 장**을 만든다. 2026-07-31

    python scripts/brand_jukiyagi.py

⛔ DB 를 건드리지 않는다. 만드는 건 `data/brand_menu_list/jukiyagi.json` 뿐이다.

사이트 실측 (2026-07-31)
------------------------
🔴 `jukstory.com` 은 **프랜차이즈(가맹모집)** 사이트다. 지난번에 그 쪽의
   `Logger Script`·`로그아웃`·`SNS`·경쟁력·마케팅 같은 **가맹/회사소개 UI** 를 긁었다 — 그건 메뉴가 아니다.
   실제 고객 메뉴판은 **자사 홈페이지 `jukstory1.cafe24.com`** 에 있다(홈 상단 「자사몰 바로가기」).
🔴 「메뉴안내」 상단 네비 = 다섯 페이지(서버렌더 PHP, urllib 로 읽힌다):
   - 솥죽        menu1.php  · 하위탭 case=1..7 (우리바다보양죽/우리땅보양죽/건강보양죽/영양맛죽/숙취해소죽/오색별미죽/전통죽)
   - 솥밥        menu2.php  · 하위탭 하나뿐(=자기자신)이라 평평하게 담는다
   - 식사류      menu3.php  · 하위탭 볶음밥(case=2)·삼계탕(case=1, 현재 비어 있음)
   - 닥터 이유식 menu4.php  · 현재 상품 없음(빈 카테고리)
   - 사이드 메뉴 menu5.php  · 하위탭 반찬(case=1)·음료(case=2, 빔)·스낵(case=3, 빔)
🔴 목록 카드: `<a … MNT_IDX=N>` + `figure background-image`(사진) + `li.atc-ttl>p`(이름) + `li.atc-content>p`(설명).
🔴 가격은 상세(`menuN_view.php?…MNT_IDX=N`)의 `div.price>span` 에 있다(예: 14,500). 목록엔 가격이 없다.
🔴 원산지는 메뉴별이 아니라 **브랜드 공통 「원산지 표시판」 이미지**다 → origin_raw 는 비운다(추측 금지).
   설명(compose_raw)에 「완도산 전복 100%」 같은 원문이 들어가는 건 사이트 문구 그대로다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "jukiyagi.json")

BRAND = "죽이야기"
SLUG = "jukiyagi"
ROOT = "https://jukstory1.cafe24.com/"
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
GAP = 0.5
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 「메뉴안내」 네비 순서 그대로. (상위 이름, 페이지, [(하위 이름, case), ...])
# 하위탭이 []이면 그 페이지 기본 목록을 상위에 바로 담는다(평평).
TOPS = [
    ("솥죽", "menu1", [("우리바다보양죽", "1"), ("우리땅보양죽", "2"), ("건강보양죽", "3"),
                       ("영양맛죽", "4"), ("숙취해소죽", "5"), ("오색별미죽", "6"), ("전통죽", "7")]),
    ("솥밥", "menu2", []),
    ("식사류", "menu3", [("볶음밥", "2"), ("삼계탕", "1")]),
    ("닥터 이유식", "menu4", []),
    ("사이드 메뉴", "menu5", [("반찬", "1"), ("음료", "2"), ("스낵", "3")]),
]

RX_ANCHOR = re.compile(r'(?s)<a href="(menu\d+_view\.php\?[^"]*MNT_IDX=(\d+)[^"]*)">(.*?)</a>')
RX_IMG = re.compile(r"background-image:\s*url\('([^']+)'\)")
RX_TTL = re.compile(r'(?s)atc-ttl">\s*<p>(.*?)</p>')
RX_CONTENT = re.compile(r'(?s)atc-content[^>]*>\s*<p>(.*?)</p>')
RX_PRICE = re.compile(r'(?s)class="price"[^>]*>\s*<span>\s*([\d,]+)')


def get(url):
    url = urllib.parse.quote(url, safe="%/:=&?~#+!*'(),;$@[]")  # 한글 파라미터(cate=…) 인코딩
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), context=CTX, timeout=25)
    raw = r.read()
    for e in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(e)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def parse_items(h):
    """목록 카드에서 (ix, name, desc, image, href) 순서대로."""
    res = []
    for m in RX_ANCHOR.finditer(h):
        href, ix, inner = m.group(1), m.group(2), m.group(3)
        if "atc-ttl" not in inner:
            continue
        name = RX_TTL.search(inner)
        if not name:
            continue
        name = clean(name.group(1))
        desc = RX_CONTENT.search(inner)
        desc = clean(desc.group(1)) if desc else None
        img = RX_IMG.search(inner)
        img = img.group(1) if img else None
        if img and img.startswith("./"):
            img = ROOT + img[2:]
        res.append((ix, name, desc or None, img, href))
    return res


def detail_price(href):
    h = get(ROOT + href)
    time.sleep(GAP)
    m = RX_PRICE.search(h)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def main():
    cats = []
    menus = []
    price_cache = {}

    def add_item(ix, name, desc, img, href, path, order):
        if ix in price_cache:
            m = price_cache[ix]
        else:
            price = detail_price(href)
            m = {
                "name": name, "price": price,
                "price_source": "official" if price else None,
                "price_note": None,
                "compose_raw": desc, "weight_raw": None,
                "origin_raw": None, "allergy_raw": None,
                "detail_url": ROOT + href, "image_url": img,
                "ext_id": ix, "cats": [],
            }
            price_cache[ix] = m
            menus.append(m)
        m["cats"].append([path, order])

    for top_name, page, subs in TOPS:
        cats.append({"name": top_name, "parent": None, "ext_id": page})
        if not subs:
            # 평평: 기본 목록을 상위에 바로
            h = get(ROOT + page + ".php")
            time.sleep(GAP)
            for o, (ix, name, desc, img, href) in enumerate(parse_items(h)):
                add_item(ix, name, desc, img, href, top_name, o)
        else:
            for sub_name, case in subs:
                cats.append({"name": sub_name, "parent": top_name, "ext_id": case})
                path = "%s/%s" % (top_name, sub_name)
                h = get(ROOT + page + ".php?case=" + case)
                time.sleep(GAP)
                for o, (ix, name, desc, img, href) in enumerate(parse_items(h)):
                    add_item(ix, name, desc, img, href, path, o)

    if not menus:
        print("메뉴 0개 — 저장하지 않는다"); return
    data = {
        "brand": BRAND, "slug": SLUG,
        "source": "자사 홈페이지 jukstory1.cafe24.com/menu1~5.php (솥죽/솥밥/식사류/닥터이유식/사이드). "
                  "목록 서버렌더, 가격은 menuN_view.php 상세. urllib",
        "collected_at": COLLECTED_AT, "origin_note": None,
        "cats": cats, "menus": menus,
    }
    priced = sum(1 for m in menus if m["price"] is not None)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("저장:", OUT)
    print("카테고리 %d개 · 메뉴 %d개 · 가격 있는 것 %d개" % (len(cats), len(menus), priced))


if __name__ == "__main__":
    main()
