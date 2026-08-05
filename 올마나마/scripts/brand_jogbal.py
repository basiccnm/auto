# -*- coding: utf-8 -*-
"""가장맛있는족발 메뉴판 — 공식 홈페이지에서 카테고리·메뉴를 긁어 **JSON 한 장**을 만든다. 2026-07-31

    python scripts/brand_jogbal.py

⛔ DB 를 건드리지 않는다. 만드는 건 `data/brand_menu_list/jogbal.json` 뿐이다.

사이트 실측 (2026-07-31)
------------------------
🔴 지시서의 `jogbal.co.kr` 은 **파킹/리다이렉트(광고 IP)** 로 죽어 있다.
   실제 공식 홈페이지는 **gajok.kr** 이다(사업자 (주)… 대표 최종완, 성남 분당).
🔴 메뉴는 `gajok.kr/sub/menu.php` 의 두 탭 — 서버렌더(gnuboard 계열 theme basic):
   - 족발, 보쌈  = `?tab=info`
   - 단품메뉴    = `?tab=single`
   (세트메뉴 `?tab=set` 은 HTML 에서 **주석 처리**되어 화면에 없다 → 넣지 않는다)
🔴 메뉴판은 **이미지 기반**이다. 이름은 썸네일 목록의 `<div class="list"><ol><li>…<p>이름</p>` 에 텍스트로 있다.
   **가격·원산지·구성·중량·알레르기는 사이트 어디에도 없다** → 전부 비운다(추측 금지).
   → 가격 0개가 정상이다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "jogbal.json")

BRAND = "가장맛있는족발"
SLUG = "jogbal"
ROOT = "https://gajok.kr"
MENU = ROOT + "/sub/menu.php"
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
GAP = 0.6
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 화면 탭 순서 그대로 (세트메뉴는 주석이라 제외)
TABS = [("족발, 보쌈", "info"), ("단품메뉴", "single")]

# <li class="menuN" id="hashX"> <a href="#X"> <img src="THUMB"> <p>이름</p> </a> </li>
RX_LISTBLOCK = re.compile(r'(?s)<div class="list">\s*<ol>(.*?)</ol>')
RX_LI = re.compile(
    r'(?s)<li class="menu\d+"[^>]*>\s*<a href="(#\d+)">\s*'
    r'<img src="([^"]+)">\s*<p>(.*?)</p>')


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), context=CTX, timeout=25)
    raw = r.read()
    for e in ("utf-8", "cp949"):
        try:
            return raw.decode(e)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    cats = []
    menus = []
    for tab_name, tab in TABS:
        h = get(MENU + "?tab=%s" % tab)
        time.sleep(GAP)
        cats.append({"name": tab_name, "parent": None, "ext_id": tab})
        block = RX_LISTBLOCK.search(h)
        if not block:
            print("목록 블록 못 찾음:", tab)
            continue
        order = 0
        for m in RX_LI.finditer(block.group(1)):
            anchor, thumb, name = m.group(1), m.group(2), clean(m.group(3))
            if not name:
                continue
            menus.append({
                "name": name,
                "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None,
                "origin_raw": None, "allergy_raw": None,
                "detail_url": MENU + "?tab=%s%s" % (tab, anchor),
                "image_url": thumb,
                "ext_id": anchor.lstrip("#"),
                "cats": [[tab_name, order]],
            })
            order += 1

    if not menus:
        print("메뉴 0개 — 저장하지 않는다"); return
    data = {
        "brand": BRAND, "slug": SLUG,
        "source": "공식 홈페이지 gajok.kr/sub/menu.php (탭 info 족발보쌈·single 단품). 이미지 메뉴판, 가격 미공개. 서버렌더 urllib",
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
