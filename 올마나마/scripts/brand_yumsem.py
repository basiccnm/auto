# -*- coding: utf-8 -*-
"""얌샘김밥 — WordPress/Elementor. 메뉴는 두 페이지(베이직/플러스), 이름은 theme-post-title
   heading, 상세는 /yumsem-menu/<slug>/. 가격 홈페이지에 없음 → price:null. 2026-07-31"""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "yumsem.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "https://www.yumsem.com"
CATS = [("https://yumsem.com/yumsem-gimbap/yumsem-basic/", "얌샘김밥 베이직"),
        ("https://yumsem.com/yumsem-gimbap/yumsem-plus/", "얌샘김밥 플러스")]
ITEM = re.compile(
    r'theme-post-title[^>]*>.*?elementor-heading-title[^>]*>([^<]+)</div>'
    r'(?:.*?/yumsem-menu/([a-z0-9\-]+)/)?', re.S)


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,6000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def main():
    menus, cats, dropped = [], [], []
    for url, tab in CATS:
        dom = render(url)
        cats.append({"name": tab, "parent": None, "ext_id": None})
        pos = 0
        seen = set()
        # 제목마다 뒤따르는 첫 productUrl 슬러그를 붙인다
        for m in re.finditer(r'theme-post-title[^>]*>.*?elementor-heading-title[^>]*>([^<]+)</div>', dom, re.S):
            nm = re.sub(r"\s+", " ", m.group(1)).strip()
            slug = None
            tail = dom[m.end():m.end() + 1500]
            sm = re.search(r'/yumsem-menu/([a-z0-9\-]+)/', tail)
            if sm:
                slug = sm.group(1)
            if not nm or len(nm) < 2 or nm in seen:
                if nm:
                    dropped.append("%s/%s(중복)" % (tab, nm))
                continue
            seen.add(nm)
            menus.append({
                "name": nm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None,
                "detail_url": "https://yumsem.com/yumsem-menu/%s/" % slug if slug else None,
                "image_url": None, "ext_id": slug, "cats": [[tab, pos]]})
            pos += 1
        print("  %s: %d개" % (tab, pos), flush=True)

    data = {"brand": "얌샘김밥", "slug": "yumsem", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped[:20])


if __name__ == "__main__":
    main()
