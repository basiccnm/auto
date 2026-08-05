# -*- coding: utf-8 -*-
# 신참떡볶이 (sincham) 메뉴 수집
# 출처: http://sincham.com/  (그누보드 계열, 메뉴는 doc/menuNN.php)
#   메뉴 탭(순서): 신메뉴 · 전체 메뉴 · 떡볶이 메뉴 · 튀김 메뉴 · 친구 메뉴
#     신메뉴  = /pg/bbs/content.php?co_id=menunew  (게시판 이미지, 항목 텍스트 없음)
#     전체    = /doc/menu00.php  (통합 이미지, 항목 텍스트 없음)
#     떡볶이  = /doc/menu01.php
#     튀김    = /doc/menu02.php
#     친구    = /doc/menu03.php
#   각 항목: <li><div class="img"><img></div><div class="txt">메뉴명</div></li>
#   사진만 이미지, 이름은 txt 텍스트. 가격은 사이트에 없음(null).
# DB import 금지. 얻지 못하면 저장하지 않는다.
import sys, os, re, json, requests, urllib3
sys.stdout.reconfigure(encoding="utf-8")
urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
# 탭 순서 그대로
PAGES = [
    ("신메뉴", "http://sincham.com/pg/bbs/content.php?co_id=menunew"),
    ("전체 메뉴", "http://sincham.com/doc/menu00.php"),
    ("떡볶이 메뉴", "http://sincham.com/doc/menu01.php"),
    ("튀김 메뉴", "http://sincham.com/doc/menu02.php"),
    ("친구 메뉴", "http://sincham.com/doc/menu03.php"),
]
IMG_BASE = "http://sincham.com"

def items_of(h):
    out = []
    for m in re.finditer(r'<div class="img"><img([^>]*)></div>\s*<div class="txt">\s*(.*?)\s*</div>', h, re.S):
        img = re.search(r'src="([^"]+)"', m.group(1))
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if not name:
            continue
        image_url = None
        if img:
            src = img.group(1).split("?")[0]
            image_url = (IMG_BASE + src) if src.startswith("/") else src
        out.append((name, image_url))
    return out

def main():
    S = requests.Session(); S.headers.update(UA)
    cats = []
    menus = []
    for cat, u in PAGES:
        r = S.get(u, timeout=25, verify=False)
        h = r.content.decode("utf-8", "replace")
        cats.append({"name": cat, "parent": None, "ext_id": u.split("/")[-1]})
        for idx, (name, image_url) in enumerate(items_of(h)):
            menus.append({
                "name": name,
                "price": None,
                "price_source": None,
                "price_note": None,
                "compose_raw": None,
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "detail_url": u,
                "image_url": image_url,
                "ext_id": None,
                "cats": [[cat, idx]],
            })

    if not menus:
        print("메뉴 0개 — 저장하지 않음")
        return

    doc = {
        "brand": "신참떡볶이",
        "slug": "sincham",
        "source": "sincham.com/doc/menuNN.php (li>div.txt 메뉴명, 이미지는 사진만, UTF-8)",
        "collected_at": "2026-07-31",
        "origin_note": "가격은 홈페이지에 없음. '신메뉴'·'전체 메뉴' 탭은 통합 이미지라 항목 텍스트가 없다.",
        "cats": cats,
        "menus": menus,
    }
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "sincham.json"))
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"저장: {out}")
    print(f"카테고리 {len(cats)}개 · 메뉴 {len(menus)}개 · 가격 0개")
    for c in cats:
        n = sum(1 for m in menus if m["cats"][0][0] == c["name"])
        print(f"  - {c['name']}: {n}개")

if __name__ == "__main__":
    main()
