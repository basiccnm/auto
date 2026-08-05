# -*- coding: utf-8 -*-
"""죠스떡볶이 메뉴판 — 메뉴명·탭·순서. 2026-07-31

    python scripts/brand_jawsfood.py            # 미리보기
    python scripts/brand_jawsfood.py --write    # data/brand_menu_list/jawsfood.json 저장

구조 (실측 2026-07-31): 서버 렌더링, utf-8. 3개 메뉴 페이지.
    /menu/menu.html      메인메뉴
    /menu/setmenu.html   세트메뉴
    /menu/side.html      사이드메뉴
  각 항목: <a href="...view.html?seq=N"> ... <h3 class="tit">이름</h3> <p class="desc">설명</p>
  🔴 홈페이지에 가격 없음 → price:null (홀 매장가 미공개)
  ⛔ DB import 금지. JSON 한 장만.
"""
import sys, re, json, io
sys.stdout.reconfigure(encoding="utf-8")
import requests

BASE = "https://www.jawsfood.co.kr"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
PAGES = [
    ("메인메뉴", "/menu/menu.html"),
    ("세트메뉴", "/menu/setmenu.html"),
    ("사이드메뉴", "/menu/side.html"),
]

def fetch(path):
    r = requests.get(BASE + path, headers=H, timeout=20)
    r.encoding = "utf-8"
    return r.text

# 각 항목 블록: view.html?seq=N 로 시작하는 앵커 안에 tit/desc
ITEM = re.compile(
    r'view\.html\?seq=(\d+)"[\s\S]*?class="tit">\s*([^<]+?)\s*</h3>'
    r'(?:[\s\S]*?class="desc">\s*([^<]*?)\s*</p>)?',
    re.S,
)

SETNAV = re.compile(r'href="#SET\d+">\s*([^<]+?)\s*</a>')

def parse(html):
    out = []
    seen = set()
    for m in ITEM.finditer(html):
        seq, name, desc = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        name = re.sub(r"\s+", " ", name)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({"seq": seq, "name": name, "desc": desc})
    if out:
        return out
    # 세트메뉴: view.html 링크가 없고 풀페이지 앵커(#SET0..)로만 나열된다
    for name in SETNAV.findall(html):
        name = re.sub(r"\s+", " ", name).strip()
        if name and name not in seen:
            seen.add(name)
            out.append({"seq": None, "name": name, "desc": ""})
    return out

def build():
    cats, menus = [], []
    for ci, (cname, path) in enumerate(PAGES):
        cats.append({"name": cname, "parent": None, "ext_id": None})
        items = parse(fetch(path))
        for idx, it in enumerate(items):
            menus.append({
                "name": it["name"], "price": None, "price_source": None, "price_note": None,
                "compose_raw": it["desc"] or None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None,
                "detail_url": f"{BASE}/menu/view.html?seq={it['seq']}",
                "image_url": None, "ext_id": it["seq"],
                "cats": [[cname, idx]],
            })
    return {
        "brand": "죠스떡볶이", "slug": "jawsfood", "source": f"{BASE}/menu/ (홈페이지, 서버렌더 utf-8)",
        "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus,
    }

if __name__ == "__main__":
    data = build()
    print(f"카테고리 {len(data['cats'])}개 · 메뉴 {len(data['menus'])}개 · 가격 0개")
    for c in data["cats"]:
        n = [m["name"] for m in data["menus"] if any(x[0] == c["name"] for x in m["cats"])]
        print(f"  [{c['name']}] {len(n)}개: {', '.join(n)}")
    if "--write" in sys.argv:
        p = "data/brand_menu_list/jawsfood.json"
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("saved", p)
