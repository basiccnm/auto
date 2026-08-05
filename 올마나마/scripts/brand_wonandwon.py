# -*- coding: utf-8 -*-
# 원할머니보쌈 (wonandwon) 메뉴 수집
# 출처: 원앤원 그룹 통합사이트 https://wonandone.co.kr/bossam/menu.asp?KeyCtgM=<n>
#   (wonandwon.co.kr 는 wonandone.co.kr 로 리다이렉트된다)
#   페이지 인코딩 UTF-8. 카테고리는 KeyCtgM 파라미터, 탭 순서대로.
#   메뉴명 <strong>, 가격 <p>\9,500</p>(₩=역슬래시), 설명 <p>...</p>, 이미지 xMenu.
#   가격은 도시락 카테고리에만 노출, 나머지는 없음(null).
#   원산지·중량·알레르기는 메뉴 페이지에 없음 → 비움(추측 금지).
# DB import 금지. 얻지 못하면 저장하지 않는다.
import sys, os, re, json, requests, urllib3
sys.stdout.reconfigure(encoding="utf-8")
urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
BASE = "https://wonandone.co.kr/bossam/menu.asp?KeyCtgM="
# 보쌈 탭 순서(KeyCtgM). 16/17 은 박가부대라 제외.
CAT_ORDER = [1, 12, 4, 6, 8, 14]
IMG_BASE = "https://wonandone.co.kr"

S = requests.Session(); S.headers.update(UA)

def get(k):
    r = S.get(BASE + str(k), timeout=25, verify=False)
    return r.content.decode("utf-8")

def cat_names(h):
    d = {}
    for m in re.finditer(r'KeyCtgM=(\d+)"[^>]*>([^<]+)<', h):
        k = int(m.group(1)); nm = re.sub(r"\s+", " ", m.group(2)).strip()
        if k not in d:
            d[k] = nm
    return d

def parse_items(h):
    """<ul class="menu_list"> 안의 각 <li> 를 순서대로."""
    out = []
    for ul in re.findall(r'<ul class="menu_list">(.*?)</ul>', h, re.S):
        for li in re.findall(r'<li>(.*?)</li>', ul, re.S):
            nm = re.search(r'<strong>\s*(.*?)\s*</strong>', li, re.S)
            if not nm:
                continue
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nm.group(1))).strip()
            if not name:
                continue
            img = re.search(r'<img[^>]+src="([^"]+)"', li)
            image_url = (IMG_BASE + img.group(1)) if img and img.group(1).startswith("/") else (img.group(1) if img else None)
            # info 영역의 <p> 들
            info = re.search(r'<div class="info">(.*?)</div>', li, re.S)
            price = None; desc = None
            if info:
                ps = re.findall(r'<p[^>]*>(.*?)</p>', info.group(1), re.S)
                for p in ps:
                    ptxt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip()
                    mprice = re.search(r'[\\￦]\s*([\d,]{3,})', ptxt)
                    if mprice and price is None:
                        price = int(mprice.group(1).replace(",", ""))
                    elif ptxt and not re.fullmatch(r'[\\￦\s\d,]+', ptxt):
                        # 설명(가격 아닌 텍스트) — 첫 유효 설명만
                        if desc is None:
                            desc = ptxt
            out.append({"name": name, "price": price, "compose_raw": desc, "image_url": image_url})
    return out

def main():
    pages = {k: get(k) for k in CAT_ORDER}
    names = cat_names(pages[CAT_ORDER[0]])
    cats = [{"name": names.get(k, str(k)), "parent": None, "ext_id": str(k)} for k in CAT_ORDER]

    menus = []
    for k in CAT_ORDER:
        cname = names.get(k, str(k))
        items = parse_items(pages[k])
        for idx, it in enumerate(items):
            menus.append({
                "name": it["name"],
                "price": it["price"],
                "price_source": "official" if it["price"] is not None else None,
                "price_note": None,
                "compose_raw": it["compose_raw"],
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "detail_url": None,
                "image_url": it["image_url"],
                "ext_id": None,
                "cats": [[cname, idx]],
            })

    if not menus:
        print("메뉴 0개 — 저장하지 않음")
        return

    doc = {
        "brand": "원할머니보쌈",
        "slug": "wonandwon",
        "source": "wonandone.co.kr/bossam/menu.asp?KeyCtgM= (탭별 HTML, UTF-8)",
        "collected_at": "2026-07-31",
        "origin_note": None,
        "cats": cats,
        "menus": menus,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "wonandwon.json")
    out = os.path.abspath(out)
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    priced = sum(1 for m in menus if m["price"] is not None)
    print(f"저장: {out}")
    print(f"카테고리 {len(cats)}개 · 메뉴 {len(menus)}개 · 가격 {priced}개")
    for k in CAT_ORDER:
        n = sum(1 for m in menus if m["cats"][0][0] == names.get(k, str(k)))
        print(f"  - {names.get(k)}: {n}개")

if __name__ == "__main__":
    main()
