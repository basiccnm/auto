# -*- coding: utf-8 -*-
# 감탄떡볶이 (gamtan) 메뉴 수집
# 출처: http://gamtan.co.kr/main/sub_page.php?page_idx=<n>  (자체 CMS, UTF-8)
#   메뉴 탭(3차 탭, 순서): 신메뉴(174) · 세트메뉴(155) · 메인메뉴(156) · 사이드메뉴(158)
#   각 항목: <li data-idx><div class="set-Img"><img alt="이름"></div>
#            <div class="set-Txt"><strong>이름<span>(옵션)</span></strong><span>9,000원</span></div></li>
#   가격은 홈페이지에 표기됨(원문 그대로).
# DB import 금지. 얻지 못하면 저장하지 않는다.
import sys, os, re, json, requests, urllib3
sys.stdout.reconfigure(encoding="utf-8")
urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
BASE = "http://gamtan.co.kr/main/sub_page.php?page_idx="
# 탭 순서 그대로 (라벨, page_idx)
CATS = [("신메뉴", "174"), ("세트메뉴", "155"), ("메인메뉴", "156"), ("사이드메뉴", "158")]
IMG_BASE = "http://gamtan.co.kr/main/"

def parse_items(h):
    out = []
    for li in re.findall(r'<li data-idx="\d+">(.*?)</li>', h, re.S):
        st = re.search(r'<div class="set-Txt">(.*?)</div>', li, re.S)
        if not st:
            continue
        block = st.group(1)
        strong = re.search(r'<strong>(.*?)</strong>', block, re.S)
        if not strong:
            continue
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", strong.group(1))).strip()
        if not name:
            continue
        # 가격: strong 뒤의 <span>...원</span>
        after = block[strong.end():]
        pm = re.search(r'([\d][\d,]{2,})\s*원', re.sub(r"<[^>]+>", " ", after))
        price = int(pm.group(1).replace(",", "")) if pm else None
        img = re.search(r'<img[^>]+src="([^"]+)"', li)
        image_url = None
        if img:
            src = img.group(1)
            image_url = src if src.startswith("http") else (IMG_BASE + src.lstrip("/"))
        out.append((name, price, image_url))
    return out

def main():
    S = requests.Session(); S.headers.update(UA)
    cats = []
    menus = []
    for label, idx in CATS:
        r = S.get(BASE + idx, timeout=25, verify=False)
        h = r.content.decode("utf-8", "replace")
        cats.append({"name": label, "parent": None, "ext_id": idx})
        for i, (name, price, image_url) in enumerate(parse_items(h)):
            menus.append({
                "name": name,
                "price": price,
                "price_source": "official" if price is not None else None,
                "price_note": None,
                "compose_raw": None,
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "detail_url": BASE + idx,
                "image_url": image_url,
                "ext_id": None,
                "cats": [[label, i]],
            })

    if not menus:
        print("메뉴 0개 — 저장하지 않음")
        return

    doc = {
        "brand": "감탄떡볶이",
        "slug": "gamtan",
        "source": "gamtan.co.kr/main/sub_page.php?page_idx=174/155/156/158 (자체 CMS, UTF-8)",
        "collected_at": "2026-07-31",
        "origin_note": None,
        "cats": cats,
        "menus": menus,
    }
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "gamtan.json"))
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    priced = sum(1 for m in menus if m["price"] is not None)
    print(f"저장: {out}")
    print(f"카테고리 {len(cats)}개 · 메뉴 {len(menus)}개 · 가격 {priced}개")
    for c in cats:
        n = sum(1 for m in menus if m["cats"][0][0] == c["name"])
        print(f"  - {c['name']}: {n}개")

if __name__ == "__main__":
    main()
