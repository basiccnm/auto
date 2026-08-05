# -*- coding: utf-8 -*-
# 귀한족발 (kwihan) 메뉴 수집
# 경로: 렌더DOM — menu-post-item 에 data-title/data-desc/data-img 가 그대로 있다.
# 도메인은 punycode(xn--hh0b95yusj63m.com). 카테고리: MAIN MENU / SIDE MENU
# 가격: 홈페이지에 없음 → price=null. 원산지: 국내산 한돈 생족(HACCP).
import sys, os, json, re, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

HOST = "https://xn--hh0b95yusj63m.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean(x):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", " ", x).strip() if x else None


def main():
    h = urllib.request.urlopen(urllib.request.Request(HOST + "/", headers=UA), timeout=25).read().decode("utf-8", "replace")
    # 카테고리 경계 (등장 순서)
    cat_marks = [(m.start(), clean(m.group(1))) for m in re.finditer(r"menu-category-title[^>]*>(.*?)</p>", h, re.S)]
    # 중복(모바일 복제) 제거하며 순서 유지
    cats_order = []
    for _, c in cat_marks:
        if c and c not in [x[1] for x in cats_order]:
            cats_order.append((None, c))
    # 각 아이템 위치→카테고리 매핑
    def cat_at(pos):
        cur = cat_marks[0][1] if cat_marks else None
        for mpos, c in cat_marks:
            if mpos <= pos:
                cur = c
        return cur

    cats_out = [{"name": c, "parent": None, "ext_id": None} for _, c in cats_order]
    menus, seen = [], set()
    idx = {c: 0 for _, c in cats_order}
    for li in re.finditer(r'<li class="menu-post-item".*?</li>', h, re.S):
        seg = li.group(0)
        t = re.search(r'data-title="([^"]*)"', seg)
        if not t:
            continue
        name = clean(t.group(1))
        cat = cat_at(li.start())
        key = (cat, name)
        if not name or key in seen:
            continue
        seen.add(key)
        d = re.search(r'data-desc="([^"]*)"', seg)
        img = re.search(r'data-img="([^"]*)"', seg)
        img_url = img.group(1) if img else None
        if img_url and img_url.startswith("/"):
            img_url = HOST + img_url
        is_jokbal = any(k in name for k in ["족발", "보쌈"])
        menus.append({
            "name": name, "price": None, "price_source": None, "price_note": None,
            "compose_raw": clean(d.group(1)) if d else None,
            "weight_raw": None,
            "origin_raw": "국내산 한돈 생족" if is_jokbal else None,
            "allergy_raw": None, "detail_url": None, "image_url": img_url,
            "ext_id": None, "cats": [[cat, idx[cat]]],
        })
        idx[cat] += 1
    out = {
        "brand": "귀한족발", "slug": "kwihan",
        "source": "https://xn--hh0b95yusj63m.com/",
        "collected_at": "2026-07-31",
        "origin_note": "국내산 한돈 생족 (HACCP 인증)",
        "cats": cats_out, "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "kwihan.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리", len(cats_out))
    for m in menus:
        print(" ", m["cats"][0][0], m["name"], "|", (m["compose_raw"] or "")[:30])


if __name__ == "__main__":
    main()
