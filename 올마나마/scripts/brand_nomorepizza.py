# -*- coding: utf-8 -*-
"""노모어피자 — /menu, menu-card-item 카드. 가격 menu-price-value(천원단위, 30.8=30,800). 2026-07-31
   사이즈 P/R/L 3종 → '이름 (사이즈)' 로 각각. '-' 는 해당 사이즈 없음."""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "nomorepizza.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "http://nomorepizza.co.kr"


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,4000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=80)
    return r.stdout.decode("utf-8", "replace")


def main():
    dom = render(HOME + "/menu")
    cards = re.split(r'class="menu-card-item"', dom)[1:]
    menus, dropped = [], []
    pos = 0
    for c in cards:
        href = re.search(r'href="([^"]+)"', c)
        alt = re.search(r'<img alt="([^"]+)"', c)
        if not alt:
            continue
        name = alt.group(1).strip()
        detail = HOME + href.group(1) if href else None
        # (사이즈라벨, 값) 쌍
        pairs = re.findall(r'>([A-Z])</p><p class="menu-price-value[^>]*>([^<]*)<', c)
        if not pairs:
            dropped.append(name + "(가격없음)")
            continue
        for size, val in pairs:
            val = val.strip()
            price = None
            if re.match(r'^[0-9]+(\.[0-9]+)?$', val):
                price = int(round(float(val) * 1000))
            menus.append({
                "name": "%s (%s)" % (name, size), "price": price,
                "price_source": "homepage" if price else None,
                "price_note": "P=퍼스널·R=레귤러·L=라지" if price else None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": detail, "image_url": None,
                "ext_id": None, "cats": [["피자", pos]]})
            pos += 1

    data = {"brand": "노모어피자", "slug": "nomorepizza", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None,
            "cats": [{"name": "피자", "parent": None, "ext_id": None}], "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    p = sum(1 for m in menus if m["price"])
    print("총 메뉴 %d · 가격 %d · 버림 %d" % (len(menus), p, len(dropped)))
    if dropped:
        print("버린 줄:", dropped)


if __name__ == "__main__":
    main()
