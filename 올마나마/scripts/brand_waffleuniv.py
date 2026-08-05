# -*- coding: utf-8 -*-
"""와플대학 — /child/sub/menu/<cat>.php, <p class="product_name"> 로 메뉴명. 2026-07-31
   가격 홈페이지에 없음 → price:null."""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "waffleuniv.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "https://www.waffleuniv.com"
# (php파일, 탭이름) — 홈페이지 메뉴 나열 순서. 신메뉴/스쿨푸드 페이지는 현재 메뉴 목록이
# 없고 창업안내 템플릿으로 렌더된다(제품 0개) → 목록 제외.
CATS = [("waffle", "와플"), ("beverage", "음료"), ("gelato", "젤라또")]


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,4000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=80)
    return r.stdout.decode("utf-8", "replace")


def main():
    menus, cats, dropped = [], [], []
    for php, tab in CATS:
        url = "%s/child/sub/menu/%s.php" % (HOME, php)
        dom = render(url)
        cats.append({"name": tab, "parent": None, "ext_id": php})
        names = re.findall(r'class="product_name"[^>]*>\s*([^<]+?)\s*</', dom)
        pos = 0
        for nm in names:
            nm = nm.replace("&amp;", "&")
            nm = re.sub(r"\s+", " ", nm).strip()
            if not nm or len(nm) < 2 or not re.search(r"[가-힣]", nm):  # 영문 번역줄 제외
                dropped.append("%s/%s" % (tab, nm))
                continue
            menus.append({
                "name": nm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": url, "image_url": None,
                "ext_id": None, "cats": [[tab, pos]]})
            pos += 1
        print("  %s(%s): %d개" % (tab, php, pos), flush=True)

    data = {"brand": "와플대학", "slug": "waffleuniv", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped)


if __name__ == "__main__":
    main()
