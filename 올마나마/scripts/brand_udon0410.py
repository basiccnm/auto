# -*- coding: utf-8 -*-
"""역전우동0410 메뉴판 — 메뉴명·탭·순서·설명. 2026-07-31

    python scripts/brand_udon0410.py            # 미리보기
    python scripts/brand_udon0410.py --write    # data/brand_menu_list/udon0410.json 저장

구조 (실측 2026-07-31): WordPress, 서버 렌더링, utf-8. /menu/ 한 장에 탭 3개.
    div.tab-content.menu_page  가 DOM 순서대로 3개 = 탭 순서:
       ① 우동 & 면류  ② 덮밥 & 돈까스  ③ 세트 & 사이드
    각 항목: li.menu-right > <h2>이름</h2><p>설명</p>
       세트 콤보는 <h2>제육돈까스<br>우동/모밀세트</h2> 처럼 <br> 가 들어있다 → 태그 제거 후 합침
    🔴 가격은 price div 가 비어있다 → price:null (홀 매장가 미공개)
    ⛔ DB import 금지. JSON 한 장만.
"""
import sys, re, json, io
sys.stdout.reconfigure(encoding="utf-8")
import requests

URL = "https://udon0410.com/menu/"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
TABS = ["우동 & 면류", "덮밥 & 돈까스", "세트 & 사이드"]

def clean(x):
    x = re.sub(r"<[^>]+>", "", x)          # <br> 등 태그 제거
    return re.sub(r"\s+", " ", x).strip()

ITEM = re.compile(r"<h2>(.*?)</h2>\s*<p>(.*?)</p>", re.S)

def build():
    r = requests.get(URL, headers=H, timeout=20); r.encoding = "utf-8"
    parts = re.split(r"tab-content menu_page", r.text)[1:]  # 3개 섹션
    if len(parts) != 3:
        print(f"⚠️ 섹션이 3개가 아니다: {len(parts)}개 — 페이지 구조가 바뀌었다")
    cats, menus = [], []
    for ci, sec in enumerate(parts[:3]):
        cname = TABS[ci]
        cats.append({"name": cname, "parent": None, "ext_id": None})
        idx = 0
        seen = set()
        for m in ITEM.finditer(sec):
            name, desc = clean(m.group(1)), clean(m.group(2))
            if not name or name in seen:
                continue
            seen.add(name)
            menus.append({
                "name": name, "price": None, "price_source": None, "price_note": None,
                "compose_raw": desc or None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": None, "image_url": None, "ext_id": None,
                "cats": [[cname, idx]],
            })
            idx += 1
    return {
        "brand": "역전우동0410", "slug": "udon0410", "source": f"{URL} (홈페이지, 서버렌더 utf-8)",
        "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus,
    }

if __name__ == "__main__":
    data = build()
    print(f"카테고리 {len(data['cats'])}개 · 메뉴 {len(data['menus'])}개 · 가격 0개")
    for c in data["cats"]:
        n = [m["name"] for m in data["menus"] if any(x[0] == c["name"] for x in m["cats"])]
        print(f"  [{c['name']}] {len(n)}개: {', '.join(n)}")
    if "--write" in sys.argv:
        p = "data/brand_menu_list/udon0410.json"
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("saved", p)
