# -*- coding: utf-8 -*-
# 이화수전통육개장 (ihwasoo) 메뉴 수집
# 경로: 렌더DOM (gnuboard 갤러리 게시판) — bo_table=menu&sca=<카테고리>
# 가격: 홈페이지에 없음 → price=null. 설명(bo_con)에 원산지(국내산 등)가 섞여 있어 compose_raw 로 보존.
import sys, os, json, re, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")

HOST = "http://ihwasoo.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CATS = ["메인 메뉴", "스페셜 메뉴", "곁들임 메뉴"]  # 홈페이지 nav 순서


def clean(x):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", " ", x).strip() if x else None


def fetch(sca):
    u = HOST + "/bbs/board.php?bo_table=menu&sca=" + urllib.parse.quote(sca)
    req = urllib.request.Request(u, headers=UA)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def main():
    menus, cats_out = [], []
    for cname in CATS:
        cats_out.append({"name": cname, "parent": None, "ext_id": None})
        html = fetch(cname)
        blocks = re.findall(r"<li class=\"gall_li.*?</li>", html, re.S)
        idx = 0
        for b in blocks:
            m = re.search(r'class="bo_tit">\s*<a[^>]*>(.*?)</a>', b, re.S)
            if not m:
                continue
            name = clean(m.group(1))
            if not name:
                continue
            d = re.search(r'class="bo_con">\s*<a[^>]*>(.*?)</a>', b, re.S)
            desc = clean(d.group(1)) if d else None
            img = re.search(r"background-image:url\(([^)]+)\)", b)
            img_url = img.group(1).strip("'\"") if img else None
            origin = None
            if desc and re.search(r"국내산|수입|호주산|한우", desc):
                mm = re.search(r"[^.,!]*?(?:국내산|수입|호주산|한우)[^.,!]*", desc)
                origin = mm.group(0).strip() if mm else None
            menus.append({
                "name": name, "price": None, "price_source": None, "price_note": None,
                "compose_raw": desc, "weight_raw": None, "origin_raw": origin,
                "allergy_raw": None, "detail_url": None, "image_url": img_url,
                "ext_id": None, "cats": [[cname, idx]],
            })
            idx += 1
    out = {
        "brand": "이화수전통육개장", "slug": "ihwasoo", "source": "http://ihwasoo.com/",
        "collected_at": "2026-07-31", "origin_note": None,
        "cats": cats_out, "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "ihwasoo.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리", len(cats_out))
    for m in menus:
        print(" ", m["cats"][0][0], m["name"], "|", (m["compose_raw"] or "")[:25])


if __name__ == "__main__":
    main()
