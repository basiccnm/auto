# -*- coding: utf-8 -*-
# 백채김치찌개 (100chae) 메뉴 수집
# 경로: 렌더DOM (content.php?co_id=menu) — con08_menu_con 블록. 탭: 메인 메뉴 / 곁들임 메뉴
# 가격: 홈페이지에 없음 → price=null. 설명에 '100% 국내산 생고기' 원산지 표기.
import sys, os, json, re, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

URL = "https://100chae.co.kr/bbs/content.php?co_id=menu"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean(x):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", " ", x).strip() if x else None


def main():
    h = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=20).read().decode("utf-8", "replace")
    # 곁들임 메뉴 리스트 헤더 위치 = 메인/곁들임 경계
    side_pos = [m.start() for m in re.finditer(r"곁들임 ?메뉴", h)]
    boundary = side_pos[-1] if side_pos else len(h)
    blocks = list(re.finditer(r'con08_menu_con.*?con08_menu_desc[^>]*>(.*?)</div>', h, re.S))
    cats_out = [{"name": "메인 메뉴", "parent": None, "ext_id": None},
                {"name": "곁들임 메뉴", "parent": None, "ext_id": None}]
    menus = []
    idx = {"메인 메뉴": 0, "곁들임 메뉴": 0}
    for b in re.finditer(r'con08_menu_con.*?(?=con08_menu_con|</section|$)', h, re.S):
        seg = b.group(0)
        nm = re.search(r'con08_menu_tt[^>]*>(.*?)</div>', seg, re.S)
        if not nm:
            continue
        name = clean(nm.group(1))
        if not name:
            continue
        dm = re.search(r'con08_menu_desc[^>]*>(.*?)</div>', seg, re.S)
        desc = clean(dm.group(1)) if dm else None
        im = re.search(r'con08_menu_img[^>]*>\s*<img src=([^\s>]+)', seg)
        img = im.group(1).strip("'\"") if im else None
        cat = "메인 메뉴" if b.start() < boundary else "곁들임 메뉴"
        origin = None
        if desc and "국내산" in desc:
            mm = re.search(r"[^.!]*국내산[^.!]*", desc)
            origin = mm.group(0).strip() if mm else None
        menus.append({
            "name": name, "price": None, "price_source": None, "price_note": None,
            "compose_raw": desc, "weight_raw": None, "origin_raw": origin,
            "allergy_raw": None, "detail_url": None, "image_url": img,
            "ext_id": None, "cats": [[cat, idx[cat]]],
        })
        idx[cat] += 1
    out = {
        "brand": "백채김치찌개", "slug": "100chae", "source": URL,
        "collected_at": "2026-07-31", "origin_note": None,
        "cats": cats_out, "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "100chae.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리", len(cats_out))
    for m in menus:
        print(" ", m["cats"][0][0], m["name"], "|", (m["compose_raw"] or "")[:25], "| origin:", m["origin_raw"])


if __name__ == "__main__":
    main()
