# -*- coding: utf-8 -*-
"""땅스부대찌개 메뉴판 — 공식 홈페이지에서 카테고리·메뉴·가격을 긁어 **JSON 한 장**을 만든다. 2026-07-31

    python scripts/brand_tsbudae.py

⛔ DB 를 건드리지 않는다. 만드는 건 `data/brand_menu_list/tsbudae.json` 뿐이다.

사이트 실측 (2026-07-31)
------------------------
서버 렌더(자체 CMS, `/brand/?c=<cat>` 쿼리). `urllib` 로 읽힌다.
🔴 홈페이지 상단 네비의 「메뉴」 아래 실제 카테고리 두 개:
   - 부대찌개  = `?c=55`  · 하위탭 땅스 부대찌개(s=55) · 신메뉴(s=56) · 사이드메뉴(s=57)
   - 떡볶이    = `?c=58`  · 하위탭 땅스떡볶이(s=58) · 신메뉴(s=59) · 사이드메뉴(s=60)
   기본(`s=` 없음) = 첫 하위탭(=땅스 …)이고 그 안에 전체가 다 나온다.
   신메뉴/사이드메뉴는 같은 상품을 다시 진열하는 필터다(사이드메뉴는 현재 비어 있음).
🔴 목록 페이지는 메뉴명을 `<img alt="...">` 로만 준다. 가격은 상세에만 있다.
🔴 상세(`&gbn=view&ix=<id>`): `product_name` · `product_summary`(구성) · `product_price`(«방문 포장 시 N원»).
   → 가격은 **방문 포장가**다(price_note 로 남긴다). 홀가·배달가는 사이트에 없다.
🔴 원산지·알레르기·중량은 사이트 어디에도 없다 → 전부 비운다(추측 금지).
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
OUT = os.path.join(BASE, "data", "brand_menu_list", "tsbudae.json")

BRAND = "땅스부대찌개"
SLUG = "tsbudae"
ROOT = "https://tsbudae.com"
LIST = ROOT + "/brand/"
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
GAP = 0.6

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 화면 순서 그대로: (상위 이름, 상위 c, [(하위 이름, s), ...])
TOPS = [
    ("부대찌개", "55", [("땅스 부대찌개", "55"), ("신메뉴", "56"), ("사이드메뉴", "57")]),
    ("떡볶이", "58", [("땅스떡볶이", "58"), ("신메뉴", "59"), ("사이드메뉴", "60")]),
]

RX_ITEM = re.compile(
    r'href="\?c=(\d+)&s=([^&"]*)&gp=1&gbn=view&ix=(\d+)"[^>]*>\s*'
    r'<div class="main_product_thumb">\s*<img[^>]*alt="([^"]*)"')
RX_NAME = re.compile(r'(?s)<div class="product_name"[^>]*>(.*?)</div>')
RX_SUMMARY = re.compile(r'(?s)<div class="product_summary"[^>]*>(.*?)</div>')
RX_PRICE = re.compile(r'(?s)<div class="product_price"[^>]*>\s*<span>([^<]*)</span>\s*([\d,]+)\s*원')
RX_IMG = re.compile(r'(?s)<div class="view_thumb[^"]*">\s*<img src="([^"]+)"')


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), context=CTX, timeout=25)
    return r.read().decode("utf-8", "replace")


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def list_items(c, s=None):
    q = "?c=%s" % c + ("&s=%s" % s if s else "")
    h = get(LIST + q)
    time.sleep(GAP)
    seen = set()
    res = []
    for m in RX_ITEM.finditer(h):
        ix = m.group(3)
        if ix in seen:
            continue
        seen.add(ix)
        res.append((ix, clean(m.group(4))))
    return res


def detail(ix):
    h = get(LIST + "?c=55&s=&gp=1&gbn=view&ix=%s" % ix)
    time.sleep(GAP)
    name = clean(RX_NAME.search(h).group(1)) if RX_NAME.search(h) else None
    summ = RX_SUMMARY.search(h)
    summ = clean(summ.group(1)) if summ else None
    pm = RX_PRICE.search(h)
    price, note = (None, None)
    if pm:
        price = int(pm.group(2).replace(",", ""))
        note = clean(pm.group(1)) or None
    img = RX_IMG.search(h)
    img = ROOT + img.group(1) if img else None
    return name, summ, price, note, img


def main():
    cats = []
    menus = []
    by_ix = {}          # ix -> menu dict
    order_in_cat = {}   # path -> running index

    for top_name, c, subs in TOPS:
        cats.append({"name": top_name, "parent": None, "ext_id": c})
        for sub_name, s in subs:
            path = "%s/%s" % (top_name, sub_name)
            cats.append({"name": sub_name, "parent": top_name, "ext_id": s})
            order_in_cat[path] = 0
            items = list_items(c, s)
            for ix, alt_name in items:
                if ix not in by_ix:
                    name, summ, price, note, img = detail(ix)
                    m = {
                        "name": name or alt_name,
                        "price": price,
                        "price_source": "official" if price else None,
                        "price_note": note,
                        "compose_raw": summ,
                        "weight_raw": None,
                        "origin_raw": None,
                        "allergy_raw": None,
                        "detail_url": LIST + "?c=%s&gbn=view&ix=%s" % (c, ix),
                        "image_url": img,
                        "ext_id": ix,
                        "cats": [],
                    }
                    by_ix[ix] = m
                    menus.append(m)
                by_ix[ix]["cats"].append([path, order_in_cat[path]])
                order_in_cat[path] += 1

    data = {
        "brand": BRAND, "slug": SLUG,
        "source": "공식 홈페이지 tsbudae.com/brand/ (c=55 부대찌개·c=58 떡볶이, 상세 gbn=view). 서버렌더 urllib",
        "collected_at": COLLECTED_AT, "origin_note": None,
        "cats": cats, "menus": menus,
    }
    priced = sum(1 for m in menus if m["price"] is not None)
    if not menus:
        print("메뉴 0개 — 저장하지 않는다"); return
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("저장:", OUT)
    print("카테고리 %d개 · 메뉴 %d개 · 가격 있는 것 %d개" % (len(cats), len(menus), priced))


if __name__ == "__main__":
    main()
