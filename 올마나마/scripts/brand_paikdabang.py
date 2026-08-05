# -*- coding: utf-8 -*-
"""빽다방(paikdabang) 공식 홈페이지 메뉴 수집 — 골격(카테고리·메뉴명·순서) 전용.

경로: 홈페이지 https://paikdabang.com (WordPress, 정적 HTML — urllib 로 그대로 읽힌다)
      메뉴 탭 5개는 홈/메뉴 페이지의 서브 네비게이션에 적힌 링크만 따라간다.
      앱(APK) 은 폰에 설치되어 있지 않아 쓰지 않았다.

⛔ DB 를 import 하지 않는다. 결과는 data/brand_menu_list/paikdabang.json 한 장.
   가격은 홈페이지에 없다 → price:null (0개여도 정상).
"""
import sys, os, re, json, time, html, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://paikdabang.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
SLEEP = 1.6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "paikdabang.json")

# 사이트 서브 네비게이션 순서 그대로 (메뉴 > 신메뉴/커피/음료/아이스크림·디저트/빽스치노)
CATS = [
    ("신메뉴",          "/menu/menu_new/"),
    ("커피",            "/menu/menu_coffee/"),
    ("음료",            "/menu/menu_drink/"),
    ("아이스크림/디저트", "/menu/menu_dessert/"),
    ("빽스치노",        "/menu/menu_ccino/"),
]

_last = [0.0]


def fetch(url):
    dt = time.time() - _last[0]
    if dt < SLEEP:
        time.sleep(SLEEP - dt)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as f:
        return f.read().decode("utf-8", "replace")


def strip_comments(h):
    return re.sub(r"<!--[\s\S]*?-->", "", h)


def text(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def section(page, cat_slug):
    """메뉴가 담긴 블록만 잘라낸다. 신메뉴 페이지만 슬라이더 구조다."""
    if cat_slug.endswith("menu_new/"):
        i = page.find("new_menu_slider")
        if i < 0:
            return ""
        j = page.find("</section>", i)
        return page[i:j if j > 0 else len(page)]
    i = page.find('class="menu_list clear"')
    if i < 0:
        return ""
    j = page.find("</section>", i)
    return page[i:j if j > 0 else len(page)]


def parse_items(block):
    """<p class="menu_tit"> / <p class="best_tit"> 를 경계로 아이템을 자른다."""
    parts = re.split(r'<p class="(?:menu_tit|best_tit)">', block)
    out = []
    for k in range(1, len(parts)):
        prev, cur = parts[k - 1], parts[k]
        name = text(cur.split("</p>", 1)[0])
        if not name:
            continue
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', prev)
        eng = ""
        m = re.search(r'class="menu_tit2[^"]*"[^>]*>([\s\S]*?)</div>', cur)
        if m:
            eng = text(m.group(1))
        desc = ""
        m = re.search(r'<p class="txt">([\s\S]*?)</p>', cur)
        if m:
            desc = text(m.group(1))
        allergy = weight = None
        for b in re.findall(r'class="menu_ingredient_basis">([\s\S]*?)</p>', cur):
            t = text(b)
            if "알레르기" in t:
                allergy = t
            elif "용량" in t or "중량" in t:
                weight = t
        out.append({
            "name": name, "name_en": eng or None, "desc": desc or None,
            "allergy": allergy, "weight": weight,
            "image": imgs[-1] if imgs else None,
        })
    return out


def looks_like_menu(name, catnames):
    """메뉴가 아닌 줄 거르기. 걸린 것은 호출부에서 목록으로 출력한다."""
    if name in catnames:
        return False, "카테고리 이름과 같음"
    if re.search(r"[.!?]$", name):
        return False, "문장부호로 끝남"
    return True, ""


def main():
    catnames = {c for c, _ in CATS}
    cats = [{"name": c, "parent": None, "ext_id": None} for c, _ in CATS]
    menus, dropped, flagged, dup_slider = [], [], [], []

    by_name = {}     # 같은 메뉴가 여러 탭에 걸린다(신메뉴 ↔ 커피). 행을 늘리지 말고 cats 를 늘린다
    for cname, path in CATS:
        page = strip_comments(fetch(BASE + path))
        block = section(page, path)
        items = parse_items(block)
        if not items:
            print("  ⚠️ %s : 0건 (블록을 못 찾음)" % cname)
            continue
        seen = set()
        pos = 0
        for it in items:
            nm = it["name"]
            if nm in seen:          # 같은 탭 안 중복(추천 슬라이더 등)
                dup_slider.append("%s / %s" % (cname, nm))
                continue
            ok, why = looks_like_menu(nm, catnames)
            if not ok:
                dropped.append("%s / %s  ← %s" % (cname, nm, why))
                continue
            if len(nm) >= 18:
                flagged.append("%s / %s (%d자 — 실제 메뉴명이라 남김)" % (cname, nm, len(nm)))
            seen.add(nm)
            m = by_name.get(nm)
            if m is None:
                m = {"name": nm, "price": None, "price_source": None,
                     "weight_raw": it["weight"], "origin_raw": None,
                     "allergy_raw": it["allergy"], "compose_raw": it["desc"],
                     "name_en": it["name_en"],
                     "detail_url": BASE + path, "image_url": it["image"],
                     "ext_id": None, "cats": []}
                by_name[nm] = m
                menus.append(m)
            m["cats"].append([cname, pos])
            pos += 1
        print("  %s : %d개" % (cname, pos))

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다.")
        return 1

    doc = {
        "brand": "빽다방", "slug": "paikdabang",
        "source": "공식 홈페이지 https://paikdabang.com — 메뉴 탭 5개(/menu/menu_new, "
                  "menu_coffee, menu_drink, menu_dessert, menu_ccino) HTML 을 urllib 로 직접 파싱. "
                  "홈페이지에 판매가 표기가 없어 price 는 전부 null. 앱 미설치로 앱 경로는 쓰지 않음.",
        "collected_at": time.strftime("%Y-%m-%d"),
        "cats": cats, "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("\n버린 줄 %d개" % len(dropped))
    for d in dropped:
        print("   ✂ " + d)
    print("탭 안 중복(추천메뉴 슬라이더) %d개 — 첫 등장만 남김" % len(dup_slider))
    for d in dup_slider:
        print("   ⧉ " + d)
    print("18자 이상이라 걸렸지만 남긴 것 %d개" % len(flagged))
    for d in flagged:
        print("   ⚠ " + d)
    print("\n카테고리 %d개 · 메뉴 %d개 · 가격 있는 것 %d개"
          % (len(cats), len(menus), sum(1 for m in menus if m["price"])))
    print("→ " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
