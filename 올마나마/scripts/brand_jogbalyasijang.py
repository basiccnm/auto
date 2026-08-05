# -*- coding: utf-8 -*-
# 족발야시장 (jogbalyasijang) 메뉴 수집
# 경로: 렌더DOM 아님 → 자체 AJAX (GET /html/menu_list_ajax.php?menu_sca=&menu_page=)
# jogbalyasijang.com 은 JS로 punycode 도메인(xn--ih3bm7ju8bi1cb3a.com)으로 리다이렉트한다(HTTP만).
# 가격: 홈페이지에 없음 → price=null
import sys, os, json, re, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")

HOST = "http://xn--ih3bm7ju8bi1cb3a.com"
AJAX = HOST + "/html/menu_list_ajax.php"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CATS = [("메인", "2"), ("사이드", "5")]  # 홈페이지 탭 순서 그대로 (data-sca)


def clean(x):
    return re.sub(r"<[^>]+>|\s+", " ", x).strip() if x else None


def strip_badge(name):
    # BEST/NEW/HOT 뱃지가 제목 앞에 붙어 온다 → 제거
    return re.sub(r"^(BEST|NEW|HOT|추천)\s+", "", name).strip()


def fetch(sca, page):
    u = AJAX + "?" + urllib.parse.urlencode({"menu_sca": sca, "menu_page": page})
    req = urllib.request.Request(u, headers=UA)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def main():
    menus, cats_out = [], []
    for cname, sca in CATS:
        cats_out.append({"name": cname, "parent": None, "ext_id": sca})
        seen = set()
        idx = 0
        prev_names = None
        for page in range(1, 6):
            html = fetch(sca, str(page))
            items = re.findall(r"<li class=\"menu_list.*?</li>", html, re.S)
            if not items:
                break
            page_names = []
            for it in items:
                m = re.search(r"menu_list_tit[^>]*>(.*?)</p>", it, re.S)
                if not m:
                    continue
                name = strip_badge(clean(m.group(1)))
                if not name:
                    continue
                page_names.append(name)
                if name in seen:
                    continue
                seen.add(name)
                d = re.search(r"menu_list_desc[^>]*>(.*?)</p>", it, re.S)
                img = re.search(r"<img src=\"([^\"]+)\"", it)
                img_url = img.group(1) if img else None
                if img_url and img_url.startswith("/"):
                    img_url = HOST + img_url
                menus.append({
                    "name": name, "price": None, "price_source": None, "price_note": None,
                    "compose_raw": clean(d.group(1)) if d else None,
                    "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": None, "image_url": img_url, "ext_id": None,
                    "cats": [[cname, idx]],
                })
                idx += 1
            # 페이지네이션 끝 판정: 같은 페이지가 반복되면 중단
            if page_names == prev_names:
                break
            prev_names = page_names
    out = {
        "brand": "족발야시장", "slug": "jogbalyasijang",
        "source": "http://jogbalyasijang.com/  (실도메인 http://xn--ih3bm7ju8bi1cb3a.com/html/menu.html)",
        "collected_at": "2026-07-31", "origin_note": None,
        "cats": cats_out, "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "jogbalyasijang.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리", len(cats_out))
    for m in menus:
        print(" ", m["cats"][0][0], m["name"], "|", (m["compose_raw"] or "")[:30])


if __name__ == "__main__":
    main()
