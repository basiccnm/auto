# -*- coding: utf-8 -*-
"""신전떡볶이 — /doc/menuNN.php, <li class="cars"> 안 <span>메뉴명</span>(이미지). 2026-07-31
   가격 홈페이지에 없음 → price:null."""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "sinjeon.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "http://www.sinjeon.co.kr"
# GoPage 코드 → 탭이름 (홈페이지 나열 순서)
CATS = [("menu01", "기본메뉴"), ("menu02", "음료/빙수"), ("menu03", "떡볶이"),
        ("menu04", "튀김"), ("menu05", "라이스"), ("menu06", "기타")]


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,4000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=80)
    return r.stdout.decode("utf-8", "replace")


def main():
    menus, cats, dropped = [], [], []
    for code, tab in CATS:
        dom = render("%s/doc/%s.php" % (HOME, code))
        dom = re.sub(r"<!--.*?-->", "", dom, flags=re.S)  # 비활성(주석) 메뉴 제외
        cats.append({"name": tab, "parent": None, "ext_id": code})
        pos = 0
        seen = set()
        for b in re.split(r"<li[ >]", dom)[1:]:
            b = b[:b.find("</li>")] if "</li>" in b else b
            if "/img/sub/menu" not in b:  # 메뉴 이미지가 있는 li 만
                continue
            pm = re.search(r"<p>(.*?)</p>", b, re.S)
            if not pm:
                continue
            nm = re.sub(r"<em.*?</em>", "", pm.group(1), flags=re.S)  # kcal 제거
            nm = re.sub(r"<[^>]+>", "", nm)
            nm = re.sub(r"\s+", " ", nm).strip()
            img = re.search(r'src="(/img/sub/menu[^"]+)"', b)
            if not nm or len(nm) < 2 or nm in seen:
                if nm:
                    dropped.append("%s/%s(중복)" % (tab, nm))
                continue
            seen.add(nm)
            menus.append({
                "name": nm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": "%s/doc/%s.php" % (HOME, code),
                "image_url": HOME + img.group(1) if img else None,
                "ext_id": None, "cats": [[tab, pos]]})
            pos += 1
        print("  %s(%s): %d개" % (tab, code, pos), flush=True)

    data = {"brand": "신전떡볶이", "slug": "sinjeon", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped)


if __name__ == "__main__":
    main()
