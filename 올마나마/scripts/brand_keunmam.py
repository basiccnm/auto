# -*- coding: utf-8 -*-
"""큰맘할매순대국 (brands.slug=keunmam, id 71) 메뉴판 수집 — 전용 스크립트.

결과: data/brand_menu_list/keunmam.json  (DB 는 건드리지 않는다)

── 어떻게 뚫었나 (2026-07-28) ─────────────────────────────────────────
  https://www.keunmam.co.kr/            → 게이트 페이지(3KB). 본 사이트는 /main.html
  https://www.keunmam.co.kr/sitemap.xml → 페이지 목록. 메뉴는 /html/menu.html 한 장뿐
  https://www.keunmam.co.kr/html/menu.html   ← 🔴 정본. 정적 HTML, 탭 7개가 전부 들어있다
  https://www.keunmam.co.kr/html/brand.html  → 「국내산 돈사골은 기본」 브랜드 문구(원산지 표시 아님)
  https://www.keunmam.co.kr/html/store.html  → 매장찾기(네이버지도). 메뉴·가격 없음
  https://www.keunmam.co.kr/robots.txt       → Disallow: /renew/ (실제로는 404)

  ⛔ 자사 주문·스마트오더 사이트 없음. 폰에 앱 없음. SPA 아님(정적 HTML).
  ⛔ 가격 0개 · 원산지 0개 · 알레르기 0개 · 중량 0개 — 사이트에 아예 없다. 추측하지 않는다.

── 탭 구조 (menu.html 의 .tab-controls / .tab-panel) ────────────────
  신메뉴(tab-new) · 순대국(tab-soondaesoup) · 요리류(tab-dishes)
     └ 하위: 철판류(tab-teppan) · 전골류(tab-jeongol)   ← .tab-submenu 안의 sub-tab-btn
  순대/편육(tab-soondae) · 식사류, 정식(tab-setmenu)

  ※ 「요리류」 버튼은 클릭 핸들러가 early-return 이라 tab-dishes 패널이 화면에 뜨지 않는다.
     그래도 DOM 에 카드 1장(순대 곱창 볶음)이 살아 있어 그대로 담는다.
"""
import json
import os
import re
import sys
import html
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "keunmam.json")

SITE = "https://www.keunmam.co.kr"
MENU_URL = SITE + "/html/menu.html"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")}

# tab-panel id → (화면에 적힌 탭 이름, 상위 경로)
PANELS = [
    ("tab-new",         "신메뉴",       None),
    ("tab-soondaesoup", "순대국",       None),
    ("tab-dishes",      "요리류",       None),
    ("tab-teppan",      "철판류",       "요리류"),
    ("tab-jeongol",     "전골류",       "요리류"),
    ("tab-soondae",     "순대/편육",    None),
    ("tab-setmenu",     "식사류, 정식", None),
]


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read()
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", "replace")


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def abs_url(u):
    if not u:
        return None
    if u.startswith("http"):
        return u
    if u.startswith("/"):
        return SITE + u
    return SITE + "/html/" + u.lstrip("./")


def main():
    doc = fetch(MENU_URL)
    # HTML 주석부터 걷어낸다 (주석 안에 옛 메뉴가 남아 있는 사이트가 있다)
    doc = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    doc = re.sub(r"<script.*?</script>", "", doc, flags=re.S | re.I)

    # 패널 위치를 잡아 구간으로 자른다
    marks = [(m.group(1), m.start()) for m in
             re.finditer(r'<div class="tab-panel[^"]*" id="([^"]+)"', doc)]
    pos = {pid: s for pid, s in marks}
    starts = sorted(pos.values()) + [len(doc)]

    dropped = []
    flagged = []    # 탭 이름과 같은 메뉴 — 버리지 않고 알리기만
    menus = {}      # name -> dict
    order = []      # 최초 등장 순서
    cats = []
    per_cat_count = {}

    for pid, cname, parent in PANELS:
        path = f"{parent}/{cname}" if parent else cname
        cats.append({"name": cname, "parent": parent, "ext_id": pid})
        if pid not in pos:
            print(f"⚠️ 패널 없음: {pid}")
            per_cat_count[path] = 0
            continue
        s = pos[pid]
        e = next(x for x in starts if x > s)
        seg = doc[s:e]

        idx = 0
        for card in re.findall(r'<article class="menu-card">(.*?)</article>', seg, re.S):
            mn = re.search(r"<h3>(.*?)</h3>", card, re.S)
            if not mn:
                continue
            name = clean(mn.group(1))
            md = re.search(r"<p>(.*?)</p>", card, re.S)
            desc = clean(md.group(1)) if md else None

            # 메뉴 아닌 것 거르기 — 좁게만. 문장 끝맺음일 때만 버린다.
            # ⛔ 「탭 이름과 같다」로 버리지 마라 — 「순대국」 탭의 「순대국」이 진짜 메뉴다.
            #    (첫 실행에서 실제로 죽었다. 스타벅스 「브루드 커피」와 같은 사고)
            if re.search(r"(니다|어요|세요|합니다)[.!?]?$", name):
                dropped.append((path, name, "문장 끝맺음"))
                continue
            if name in [c for _, c, _ in PANELS]:
                flagged.append((path, name))

            imgs = re.findall(r'<img[^>]*src="([^"]+)"', card)
            photo = None
            for u in imgs:
                if "/sub/menu/mu-img" in u or "/updata/menu/" in u:
                    photo = u
            if photo is None and imgs:
                photo = imgs[-1]

            if name not in menus:
                menus[name] = {
                    "name": name,
                    "price": None,
                    "price_source": None,
                    "price_note": None,
                    "compose_raw": desc,
                    "weight_raw": None,
                    "origin_raw": None,
                    "allergy_raw": None,
                    "detail_url": None,
                    "image_url": abs_url(photo),
                    "ext_id": None,
                    "cats": [],
                }
                order.append(name)
            elif desc and not menus[name]["compose_raw"]:
                menus[name]["compose_raw"] = desc

            menus[name]["cats"].append([path, idx])
            idx += 1
        per_cat_count[path] = idx

    if not menus:
        print("❌ 메뉴 0개 — 파일을 저장하지 않는다")
        return 1

    data = {
        "brand": "큰맘할매순대국",
        "slug": "keunmam",
        "source": ("https://www.keunmam.co.kr/html/menu.html — 정적 HTML(urllib). "
                   "루트는 게이트 페이지라 /main.html·/sitemap.xml 로 경로를 찾았다. "
                   ".tab-panel 7개(요리류 하위 2개 포함)의 article.menu-card 를 그대로 읽음. "
                   "가격·원산지·알레르기·중량은 사이트 어디에도 없음(brand/ceo/bi/store/news/event/"
                   "franchise 전 페이지 확인)."),
        "collected_at": str(date.today()),
        "origin_note": None,
        "cats": cats,
        "menus": [menus[n] for n in order],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"저장: {OUT}")
    print(f"카테고리 {len(cats)}개 (하위 {sum(1 for c in cats if c['parent'])})")
    for p, n in per_cat_count.items():
        print(f"  - {p}: {n}개")
    print(f"메뉴 {len(order)}개 (진열 {sum(len(m['cats']) for m in menus.values())}회)")
    print(f"가격 있는 것 {sum(1 for m in menus.values() if m['price'] is not None)}개")
    print(f"재료(compose_raw) {sum(1 for m in menus.values() if m['compose_raw'])}개")
    print(f"원산지 {sum(1 for m in menus.values() if m['origin_raw'])}개")
    if dropped:
        print("버린 줄:")
        for p, n, r in dropped:
            print(f"  - [{p}] {n} ({r})")
    else:
        print("버린 줄 없음")
    for p, n in flagged:
        print(f"⚠️ 확인 필요 — 탭 이름과 같은 메뉴(버리지 않음): [{p}] {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
