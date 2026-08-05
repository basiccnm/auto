# -*- coding: utf-8 -*-
"""고피자 — Next.js SPA. 카테고리별 라우트(/menu, /menu/personal …)를 헤드리스로 렌더,
   /menu/detail/<id> 링크의 한글 이름을 수집. 홈페이지에 가격 없음(주문은 앱/배달) → price:null.
   2026-07-31"""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "gopizza.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "https://gopizza.kr"
# (route, 탭이름) — 홈페이지 탭 순서
CATS = [("/menu", "LARGE"), ("/menu/personal", "PERSONAL"), ("/menu/grab", "GRAB"),
        ("/menu/pasta", "PASTA"), ("/menu/topokki", "TOPOKKI"), ("/menu/sides", "SIDES"),
        ("/menu/set", "COMBO"), ("/menu/special", "SPECIAL")]


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,4000", "--virtual-time-budget=11000", "--dump-dom", url],
        capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def kor_name(inner):
    parts = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"<[^>]+>", inner)]
    for p in parts:
        p = p.replace("&amp;", "&")
        if re.search(r"[가-힣]", p):
            return p
    return None


def main():
    menus, cats, dropped = [], [], []
    for route, tab in CATS:
        dom = render(HOME + route)
        cats.append({"name": tab, "parent": None, "ext_id": route.strip("/")})
        pos = 0
        seen = set()
        for m in re.finditer(r'href="(/menu/detail/([a-z0-9]+))"[^>]*>(.*?)</a>', dom, re.S):
            slug = m.group(2)
            nm = kor_name(m.group(3))
            if not nm or len(nm) < 2 or slug in seen:
                continue
            seen.add(slug)
            menus.append({
                "name": nm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": HOME + m.group(1), "image_url": None,
                "ext_id": slug, "cats": [[tab, pos]]})
            pos += 1
        print("  %s(%s): %d개" % (tab, route, pos), flush=True)

    data = {"brand": "고피자", "slug": "gopizza", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d" % (len(menus), len(cats)))


if __name__ == "__main__":
    main()
