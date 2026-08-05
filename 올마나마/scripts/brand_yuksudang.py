# -*- coding: utf-8 -*-
"""육수당 메뉴판 — 메뉴명·탭·순서. 2026-07-31

    python scripts/brand_yuksudang.py            # 미리보기
    python scripts/brand_yuksudang.py --write    # data/brand_menu_list/yuksudang.json 저장

구조 (실측 2026-07-31): 그누보드 게시판, 서버 렌더링, utf-8.
    /board/index.php?board=menu_01&sca=N  카테고리별 페이지
       sca=2 서울식 국밥 / sca=4 서울식 국수 / sca=5 식탐해소 곁들임 / sca=6 육수당 육수 선생
    각 항목: <p class="menu_stext">지역·수식어</p><p class="menu_name">메뉴명</p>
       메뉴명은 stext(부산/전주 등)와 합쳐 "부산 순대국밥" 형태로 저장
    🔴 홈페이지에 가격 없음 → price:null (홀 매장가 미공개)
    ⛔ DB import 금지. JSON 한 장만.
"""
import sys, re, json, io
sys.stdout.reconfigure(encoding="utf-8")
import requests

BASE = "https://www.yuksudang.com"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
CATS = [("서울식 국밥", "2"), ("서울식 국수", "4"), ("식탐해소 곁들임", "5"), ("육수당 육수 선생", "6")]

PAT = re.compile(
    r'menu_stext[^>]*>\s*([^<]*?)\s*</p>\s*<p class="menu_name[^>]*>\s*([^<]+?)\s*</p>', re.S
)

def fetch(sca):
    r = requests.get(f"{BASE}/board/index.php?board=menu_01&sca={sca}", headers=H, timeout=20)
    return r.content.decode("utf-8", errors="ignore")

def build():
    cats, menus = [], []
    for cname, sca in CATS:
        cats.append({"name": cname, "parent": None, "ext_id": sca})
        html = fetch(sca)
        idx = 0
        seen = set()
        for stext, name in PAT.findall(html):
            stext, name = re.sub(r"\s+", " ", stext).strip(), re.sub(r"\s+", " ", name).strip()
            full = (stext + " " + name).strip() if stext else name
            if not name or full in seen:
                continue
            seen.add(full)
            menus.append({
                "name": full, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                "detail_url": f"{BASE}/board/index.php?board=menu_01&sca={sca}",
                "image_url": None, "ext_id": None, "cats": [[cname, idx]],
            })
            idx += 1
    return {
        "brand": "육수당", "slug": "yuksudang", "source": f"{BASE}/board/menu_01 (홈페이지, 서버렌더 utf-8)",
        "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus,
    }

if __name__ == "__main__":
    data = build()
    print(f"카테고리 {len(data['cats'])}개 · 메뉴 {len(data['menus'])}개 · 가격 0개")
    for c in data["cats"]:
        n = [m["name"] for m in data["menus"] if any(x[0] == c["name"] for x in m["cats"])]
        print(f"  [{c['name']}] {len(n)}개: {', '.join(n)}")
    if "--write" in sys.argv:
        p = "data/brand_menu_list/yuksudang.json"
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("saved", p)
