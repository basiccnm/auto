# -*- coding: utf-8 -*-
# 곱창고 (gobchanggo) 메뉴 수집
# 경로: 렌더DOM — id="product" 안 product-card (product-name / product-desc / img)
# 카테고리: SIGNATURE MENU 한 개. 가격: 홈페이지에 없음 → price=null. 한우곱창전문.
import sys, os, json, re, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

HOST = "http://gobchanggo.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CAT = "SIGNATURE MENU"


def clean(x):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", " ", x).strip() if x else None


def main():
    h = urllib.request.urlopen(urllib.request.Request(HOST + "/", headers=UA), timeout=25).read().decode("utf-8", "replace")
    i = h.find('id="product"')
    j = h.find('COMPETITIVE EDGE', i)
    seg = h[i:j if j > 0 else i + 12000]
    menus, seen = [], set()
    idx = 0
    for m in re.finditer(r'product-card">(.*?)(?=product-card">|\Z)', seg, re.S):
        block = m.group(1)
        nm = re.search(r'product-name">(.*?)</h3>', block, re.S)
        if not nm:
            continue
        name = clean(nm.group(1))
        if not name or name in seen:
            continue
        seen.add(name)
        d = re.search(r'product-desc">(.*?)</p>', block, re.S)
        img = re.search(r'<img src="([^"]+)"', block)
        img_url = img.group(1) if img else None
        if img_url and img_url.startswith("/"):
            img_url = HOST + img_url
        menus.append({
            "name": name, "price": None, "price_source": None, "price_note": None,
            "compose_raw": clean(d.group(1)) if d else None,
            "weight_raw": None,
            "origin_raw": "한우" if any(k in name for k in ["곱창", "대창", "막창", "특양", "염통", "육회", "갈비", "모듬"]) else None,
            "allergy_raw": None, "detail_url": None, "image_url": img_url,
            "ext_id": None, "cats": [[CAT, idx]],
        })
        idx += 1
    out = {
        "brand": "곱창고", "slug": "gobchanggo", "source": HOST + "/",
        "collected_at": "2026-07-31",
        "origin_note": "한우곱창전문 (자체 HACCP 인증 공장)",
        "cats": [{"name": CAT, "parent": None, "ext_id": None}], "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "gobchanggo.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리 1")
    for m in menus:
        print(" ", m["name"], "|", (m["compose_raw"] or "")[:30], "| o:", m["origin_raw"])


if __name__ == "__main__":
    main()
