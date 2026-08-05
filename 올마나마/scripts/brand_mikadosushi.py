# -*- coding: utf-8 -*-
"""미카도스시 — gnuboard 이미지 갤러리(bo_table=menu&sca=<카테고리>). 2026-07-31
   가격 홈페이지에 없음 → price:null. 메뉴명은 갤러리 링크 텍스트(워터마크 'MIKADO SUSHI' 제거)."""
import io, os, re, json, subprocess, sys, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "mikadosushi.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "http://www.mikadosushi.co.kr"
CATS = ["초밥", "롤군함", "튀김우동", "디저트", "곁들임", "포장배달", "TOGO"]


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,3000", "--virtual-time-budget=9000", "--dump-dom", url],
        capture_output=True, timeout=80)
    return r.stdout.decode("utf-8", "replace")


def clean(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&amp;", "&").replace("&nbsp;", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*MIKADO SUSHI\s*$", "", t, flags=re.I).strip()
    return t


def main():
    menus, cats, dropped = [], [], []
    for ci, cat in enumerate(CATS):
        cats.append({"name": cat, "parent": None, "ext_id": None})
        seen = {}
        order = []
        for page in range(1, 8):
            url = (HOME + "/bbs/board.php?bo_table=menu&sca=" + urllib.parse.quote(cat)
                   + "&page=" + str(page))
            dom = render(url)
            before = len(order)
            for m in re.finditer(r'href="([^"]*wr_id=(\d+)[^"]*)"[^>]*>(.*?)</a>', dom, re.S):
                wid = m.group(2)
                name = clean(m.group(3))
                if not name:
                    continue
                if wid not in seen:
                    seen[wid] = name
                    order.append(wid)
                elif len(name) > len(seen[wid]):
                    seen[wid] = name
            if len(order) == before:  # 이 페이지에서 새 항목 없음 → 끝
                break
        for pos, wid in enumerate(order):
            name = seen[wid]
            # UI 쓰레기 거르기
            if name in ("초밥", "롤군함", "튀김우동", "디저트", "곁들임", "포장배달", "TOGO",
                        "MIKADO SUSHI", "글쓰기", "목록", "이전", "다음") or len(name) < 2:
                dropped.append("%s/%s" % (cat, name))
                continue
            menus.append({
                "name": name, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None,
                "allergy_raw": None, "detail_url": HOME + "/bbs/board.php?bo_table=menu&wr_id=" + wid,
                "image_url": None, "ext_id": wid, "cats": [[cat, pos]]})
        print("  %s: %d개" % (cat, len(order)), flush=True)

    data = {"brand": "미카도스시", "slug": "mikadosushi", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped)


if __name__ == "__main__":
    main()
