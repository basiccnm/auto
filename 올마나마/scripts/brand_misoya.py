# -*- coding: utf-8 -*-
"""미소야 — imweb /menu/. 아이템은 갤러리 caption 의 <h4><strong>이름</strong></h4><p>설명</p>.
   섹션(카테고리)은 id=s2023... 앵커(KATSU/UDON/…). 가격 홈페이지에 없음 → price:null. 2026-07-31"""
import io, os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "misoya.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HOME = "http://www.misoya.co.kr"
MENU = HOME + "/menu/"
# 섹션 id → 탭이름. since2000 은 브랜드 소개(슬로건)라 메뉴 아님.
SEC = {"s202308259e427b0471581": "since2000",
       "s202308259e07f5b37dd2a": "KATSU",
       "s20230825f39511d5277c7": "UDON",
       "s2023082538ab088d8cbc1": "SOBA",
       "s20230825b805701aee83c": "RICE BOWL",
       "s20230825136a0428d3501": "HOT POT",
       "s20230927a48fe51daf1ae": "SUSHI",
       "s202310101f514c41c12d5": "ADD ON"}
SKIP_SEC = {"since2000"}
# 브랜드 슬로건 caption(메뉴 아님). DOM 상 KATSU 섹션 뒤에도 복제돼 섞인다.
SKIP_NAMES = {"맛있습니다", "건강합니다", "신선합니다"}


def render(url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--mute-audio", "--disable-extensions", "--hide-scrollbars",
        "--window-size=1280,8000", "--virtual-time-budget=11000", "--dump-dom", url],
        capture_output=True, timeout=100)
    return r.stdout.decode("utf-8", "replace")


def main():
    dom = render(MENU)
    # 섹션 경계(정렬된 위치)
    bounds = []
    for sid, lbl in SEC.items():
        m = re.search(r'id="' + sid + r'"', dom)
        if m:
            bounds.append((m.start(), lbl))
    bounds.sort()

    def sec_of(pos):
        cur = None
        for start, lbl in bounds:
            if pos >= start:
                cur = lbl
            else:
                break
        return cur

    # 카테고리 순서(메뉴 섹션만, DOM 순)
    cat_order = [lbl for _, lbl in bounds if lbl not in SKIP_SEC]
    cats = [{"name": c, "parent": None, "ext_id": None} for c in cat_order]
    poscnt = {c: 0 for c in cat_order}

    menus, dropped = [], []
    seen = set()
    for m in re.finditer(r'id="caption_\d+"[^>]*>\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', dom, re.S):
        name = re.sub(r"<[^>]+>", "", m.group(1))
        name = re.sub(r"\s+", " ", name).strip()
        desc = re.sub(r"<[^>]+>", " ", m.group(2))
        desc = re.sub(r"\s+", " ", desc).strip()
        cat = sec_of(m.start())
        key = (cat, name)
        if not name or len(name) < 2:
            continue
        if name in SKIP_NAMES:
            dropped.append("%s/%s(슬로건)" % (cat, name))
            continue
        if cat in SKIP_SEC or cat is None:
            dropped.append("%s/%s(섹션제외)" % (cat, name))
            continue
        if key in seen:
            continue
        seen.add(key)
        pos = poscnt[cat]
        poscnt[cat] += 1
        menus.append({
            "name": name, "price": None, "price_source": None, "price_note": None,
            "compose_raw": desc or None, "weight_raw": None, "origin_raw": None,
            "allergy_raw": None, "detail_url": MENU, "image_url": None,
            "ext_id": None, "cats": [[cat, pos]]})

    data = {"brand": "미소야", "slug": "misoya", "source": HOME,
            "collected_at": "2026-07-31", "origin_note": None, "cats": cats, "menus": menus}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    for c in cat_order:
        print("  %s: %d개" % (c, poscnt[c]))
    print("총 메뉴 %d · 카테고리 %d · 버림 %d" % (len(menus), len(cats), len(dropped)))
    if dropped:
        print("버린 줄:", dropped[:15])


if __name__ == "__main__":
    main()
