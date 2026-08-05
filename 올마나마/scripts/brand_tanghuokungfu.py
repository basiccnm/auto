# -*- coding: utf-8 -*-
# 탕화쿵푸마라탕 (tanghuokungfu) 메뉴 수집
# 출처: https://tanghuokungfu.co.kr/default/brand/menu/menu.php  (cafe24 빌더, EUC-KR)
#   www 루트는 frameset → default/index.php(브랜드/프랜차이즈 선택 스플래시)
#   → 브랜드 홈 /default/brand/index.php → 메뉴 /default/brand/menu/menu.php
#   메뉴 페이지는 셀프바 재료를 탭 6개로 보여준다(면류/두부/해산물&어묵/채소/버섯/기타).
#   각 <li> = <h5>이름</h5><p>한줄설명</p> + 이미지(menuNN.webp). 가격 표기 없음(무게과금).
#   #menu-list1..6 이 탭 1..6 에 대응. 탭 라벨은 나열 순서 그대로.
# DB import 금지. 얻지 못하면 저장하지 않는다.
import sys, os, re, json, requests, urllib3
sys.stdout.reconfigure(encoding="utf-8")
urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
URL = "https://tanghuokungfu.co.kr/default/brand/menu/menu.php"
IMG_BASE = "https://tanghuokungfu.co.kr"

def main():
    r = requests.get(URL, headers=UA, timeout=25, verify=False)
    h = r.content.decode("euc-kr", "replace")

    # 탭 라벨: #menu-list<n> -> 라벨
    tab = {}
    for n, lbl in re.findall(r'#?menu-list(\d+)[\'"][^>]*>\s*([^<\s][^<]*?)\s*<', h):
        lbl = re.sub(r"\s+", " ", lbl).strip()
        if lbl and n not in tab:
            tab[n] = lbl

    # 각 리스트 블록 파싱(문서 순서 유지)
    cats = []
    menus = []
    for mm in re.finditer(r'id="menu-list(\d+)"[^>]*>(.*?)(?=id="menu-list\d+"|</section>)', h, re.S):
        n = mm.group(1); body = mm.group(2)
        cname = tab.get(n)
        if not cname:
            continue
        items = re.findall(r'<h5>\s*(.*?)\s*</h5>\s*<p>\s*(.*?)\s*</p>', body, re.S)
        imgs = re.findall(r'<div class="menu-img"><img src="([^"]+)"', body)
        if not items:
            continue
        cats.append({"name": cname, "parent": None, "ext_id": n})
        for idx, (nm, tag) in enumerate(items):
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nm)).strip()
            tagline = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", tag)).strip()
            img = imgs[idx] if idx < len(imgs) else None
            image_url = (IMG_BASE + img) if img and img.startswith("/") else img
            menus.append({
                "name": name,
                "price": None,
                "price_source": None,
                "price_note": None,
                "compose_raw": tagline or None,
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "detail_url": None,
                "image_url": image_url,
                "ext_id": None,
                "cats": [[cname, idx]],
            })

    if not menus:
        print("메뉴 0개 — 저장하지 않음")
        return

    doc = {
        "brand": "탕화쿵푸마라탕",
        "slug": "tanghuokungfu",
        "source": "tanghuokungfu.co.kr/default/brand/menu/menu.php (cafe24 빌더, EUC-KR)",
        "collected_at": "2026-07-31",
        "origin_note": "메뉴 탭은 셀프바 재료 목록(6탭). 마라탕은 무게과금이라 개별 가격 표기 없음.",
        "cats": cats,
        "menus": menus,
    }
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "tanghuokungfu.json"))
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"저장: {out}")
    print(f"카테고리 {len(cats)}개 · 메뉴 {len(menus)}개 · 가격 0개")
    for c in cats:
        n = sum(1 for m in menus if m["cats"][0][0] == c["name"])
        print(f"  - {c['name']}: {n}개")

if __name__ == "__main__":
    main()
