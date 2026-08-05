# -*- coding: utf-8 -*-
"""북촌손만두 메뉴판 — 메뉴명·탭·순서. 2026-07-31

    python scripts/brand_mandoo.py            # 미리보기
    python scripts/brand_mandoo.py --write    # data/brand_menu_list/mandoo.json 저장

구조 (실측 2026-07-31): 자체 AJAX API. DOM 은 JS 로 채워져 requests 로는 빈다.
    화면 JS(j-default.js _get_menu): POST /common/json.common.php  data={mode:"menu-list", cate:NNN}
    응답 JSON {menu:"<html>", popup:"<html>"} — menu HTML 의 .menu_text > <h2> 가 메뉴명(utf-8)
    카테고리(data-category): 001 만두류 / 002 면류 / 003 식사류 / 004 분식류 / 005 사이드&세트 / 006 북촌몰 제품
       006 은 bukchonmall.co.kr 로 나가는 냉동 소매제품(중량 표기·detail_url 있음)
    🔴 홈페이지에 가격 없음 → price:null (홀 매장가 미공개)
    ⛔ DB import 금지. JSON 한 장만.
"""
import sys, re, json, io
sys.stdout.reconfigure(encoding="utf-8")
import requests

API = "https://www.mandoo.so/common/json.common.php"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
     "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.mandoo.so/menu/"}
CATS = [("만두류", "001"), ("면류", "002"), ("식사류", "003"),
        ("분식류", "004"), ("사이드&세트", "005"), ("북촌몰 제품", "006")]

LI = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S)
HREF = re.compile(r'<a\s+href="([^"#][^"]*)"')
H2 = re.compile(r"<h2>(.*?)</h2>", re.S)
WEIGHT = re.compile(r"(\d+(?:\.\d+)?\s*(?:kg|g|ml|L))\s*$", re.I)

def fetch(cate):
    r = requests.post(API, data={"mode": "menu-list", "cate": cate}, headers=H, timeout=20)
    return r.json().get("menu", "")

def parse(html):
    out = []
    seen = set()
    for li in LI.findall(html):
        m = H2.search(li)
        if not m:
            continue
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        href = HREF.search(li)
        wm = WEIGHT.search(name)
        out.append({"name": name, "detail_url": href.group(1) if href else None,
                    "weight_raw": wm.group(1) if wm else None})
    return out

def build():
    cats, menus = [], []
    for cname, cate in CATS:
        cats.append({"name": cname, "parent": None, "ext_id": cate})
        for idx, it in enumerate(parse(fetch(cate))):
            menus.append({
                "name": it["name"], "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": it["weight_raw"], "origin_raw": None,
                "allergy_raw": None, "detail_url": it["detail_url"], "image_url": None,
                "ext_id": None, "cats": [[cname, idx]],
            })
    return {
        "brand": "북촌손만두", "slug": "mandoo", "source": f"{API} (자체 AJAX API, mode=menu-list)",
        "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus,
    }

if __name__ == "__main__":
    data = build()
    print(f"카테고리 {len(data['cats'])}개 · 메뉴 {len(data['menus'])}개 · 가격 0개")
    for c in data["cats"]:
        n = [m["name"] for m in data["menus"] if any(x[0] == c["name"] for x in m["cats"])]
        print(f"  [{c['name']}] {len(n)}개: {', '.join(n)}")
    if "--write" in sys.argv:
        p = "data/brand_menu_list/mandoo.json"
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("saved", p)
