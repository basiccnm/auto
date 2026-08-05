# -*- coding: utf-8 -*-
"""아비꼬 — /sub/sub02_01.php?boardid=menuN (탭별 gnuboard). 아이템은 div.tit(이름)·div.cate·thumb.
   가격 홈페이지에 없음 → price:null. 2026-07-31"""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "abiko.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "https://abiko.kr"
# boardid → 탭이름 (메뉴 안내 스와이퍼 순서)
CATS = [("menu1", "카레라이스"), ("menu2", "하야시라이스"), ("menu3", "카레우동"),
        ("menu4", "크림카레파스타"), ("menu5", "돈부리"), ("menu6", "세트"), ("menu7", "토핑")]


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,4000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=80)
    return r.stdout.decode("utf-8", "replace")


def main():
    menus, cats, dropped = [], [], []
    for bid, tab in CATS:
        dom = render("%s/sub/sub02_01.php?boardid=%s" % (HOME, bid))
        dom = re.sub(r"<!--.*?-->", "", dom, flags=re.S)  # 비활성 템플릿 제거
        cats.append({"name": tab, "parent": None, "ext_id": bid})
        pos = 0
        seen = set()
        # 아이템 앵커: <a ...> ... <div class="tit">NAME</div> ... </a>
        for m in re.finditer(r'<a[^>]*>(.*?)</a>', dom, re.S):
            blk = m.group(1)
            tm = re.search(r'<div class="tit">([^<]*)</div>', blk)
            if not tm:
                continue
            nm = re.sub(r"\s+", " ", tm.group(1)).replace("&amp;", "&").strip()
            if not nm or len(nm) < 2:
                continue
            if nm in ("카레라이스", "하야시라이스", "카레우동", "크림카레파스타",
                      "돈부리", "세트", "토핑") or nm in seen:
                if nm in seen:
                    continue
                dropped.append("%s/%s(탭명)" % (tab, nm))
                continue
            seen.add(nm)
            img = re.search(r'<div class="thumb">\s*<img src="([^"]+)"', blk)
            menus.append({
                "name": nm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None,
                "detail_url": "%s/sub/sub02_01.php?boardid=%s" % (HOME, bid),
                "image_url": img.group(1) if img else None,
                "ext_id": bid, "cats": [[tab, pos]]})
            pos += 1
        print("  %s(%s): %d개" % (tab, bid, pos), flush=True)

    data = {"brand": "아비꼬", "slug": "abiko", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped)


if __name__ == "__main__":
    main()
