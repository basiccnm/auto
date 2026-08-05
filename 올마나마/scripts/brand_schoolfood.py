# -*- coding: utf-8 -*-
"""스쿨푸드 메뉴판 — 메뉴명·탭·순서·설명. 2026-07-31

    python scripts/brand_schoolfood.py            # 미리보기
    python scripts/brand_schoolfood.py --write    # data/brand_menu_list/schoolfood.json 저장

구조 (실측 2026-07-31): 서버 렌더링, utf-8. /menu/menu.html 한 장에 탭 5개.
    <section id="menu1..5"> 가 각 탭:  menu1 마리 / menu2 떡볶이 / menu3 라이스 / menu4 면 / menu5 사이드
    각 항목: <p class="tit">이름</p><p class="des">설명</p>
    🔴 홈페이지에 가격 없음 → price:null (홀 매장가 미공개)
    ⛔ DB import 금지. JSON 한 장만.
"""
import sys, re, json, io
sys.stdout.reconfigure(encoding="utf-8")
import requests

URL = "http://www.schoolfood.co.kr/menu/menu.html"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
LABELS = {"menu1": "마리", "menu2": "떡볶이", "menu3": "라이스", "menu4": "면", "menu5": "사이드"}
ORDER = ["menu1", "menu2", "menu3", "menu4", "menu5"]

ITEM = re.compile(
    r'class="tit"[^>]*>\s*([^<]+?)\s*</p>\s*<p class="des"[^>]*>\s*([^<]*?)\s*</p>', re.S
)

def build():
    r = requests.get(URL, headers=H, timeout=20)
    t = r.content.decode("utf-8", errors="ignore")
    secs = re.split(r'<section[^>]*id="(menu\d)"', t)  # [pre, id, body, id, body, ...]
    bodies = {secs[i]: secs[i + 1] for i in range(1, len(secs) - 1, 2)}
    cats, menus = [], []
    for sid in ORDER:
        cname = LABELS[sid]
        cats.append({"name": cname, "parent": None, "ext_id": sid})
        body = bodies.get(sid, "")
        idx = 0
        seen = set()
        for name, des in ITEM.findall(body):
            name = re.sub(r"\s+", " ", name).strip()
            des = re.sub(r"\s+", " ", des).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            menus.append({
                "name": name, "price": None, "price_source": None, "price_note": None,
                "compose_raw": des or None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": None, "image_url": None, "ext_id": None,
                "cats": [[cname, idx]],
            })
            idx += 1
    return {
        "brand": "스쿨푸드", "slug": "schoolfood", "source": f"{URL} (홈페이지, 서버렌더 utf-8)",
        "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus,
    }

if __name__ == "__main__":
    data = build()
    print(f"카테고리 {len(data['cats'])}개 · 메뉴 {len(data['menus'])}개 · 가격 0개")
    for c in data["cats"]:
        n = [m["name"] for m in data["menus"] if any(x[0] == c["name"] for x in m["cats"])]
        print(f"  [{c['name']}] {len(n)}개: {', '.join(n)}")
    if "--write" in sys.argv:
        p = "data/brand_menu_list/schoolfood.json"
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("saved", p)
