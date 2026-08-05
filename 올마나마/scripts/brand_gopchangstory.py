# -*- coding: utf-8 -*-
# 곱창이야기 (gopchangstory) 메뉴 수집
# 주의: gopchangstory.co.kr 은 '가맹모집' 사이트라 메뉴가 없다.
#       실제 메뉴는 고객용 도메인 곱창이야기.한국(xn--kb0brxg52cuzb8vj.xn--3e0b707e) 에 있다(XE).
# 카테고리: 메인 메뉴(411) / 사이드 메뉴(413). 가격은 대부분 비어 있음(price=null), 일부만 표기.
import sys, os, json, re, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

HOST = "http://xn--kb0brxg52cuzb8vj.xn--3e0b707e"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CATS = [("메인 메뉴", "411"), ("사이드 메뉴", "413")]


def clean(x):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", " ", x).strip() if x else None


def parse_price(s):
    if not s:
        return None
    m = re.search(r"([\d,]+)\s*원", s)
    return int(m.group(1).replace(",", "")) if m else None


def main():
    menus, cats_out = [], []
    for cname, srl in CATS:
        cats_out.append({"name": cname, "parent": None, "ext_id": srl})
        h = urllib.request.urlopen(urllib.request.Request(HOST + "/index.php?mid=menu&category_srl=" + srl, headers=UA), timeout=25).read().decode("utf-8", "replace")
        # 진열 순서 = menu_button_list 순서
        order = [s for s, _ in re.findall(r'data-menu_srl="(\d+)">\s*<div class="circle">(.*?)</div>', h, re.S)]
        blocks = {}
        for m in re.finditer(r'<div class="slide menubox"[^>]*data-img="([^"]*)"[^>]*>.*?id="slide_(\d+)".*?(?=<div class="slide menubox"|\Z)', h, re.S):
            blocks[m.group(2)] = (m.group(0), m.group(1))
        idx = 0
        for srl_i in order:
            if srl_i not in blocks:
                continue
            seg, img = blocks[srl_i]
            tit = re.search(r'explain_box">\s*<div class="title">(.*?)</div>', seg, re.S)
            if not tit:
                continue
            traw = tit.group(1)
            name = clean(re.sub(r'<span.*?</span>', '', traw, flags=re.S))
            if not name:
                continue
            weight = clean(re.search(r'class="weight">(.*?)</span>', traw, re.S).group(1)) if re.search(r'class="weight">(.*?)</span>', traw, re.S) else None
            pm = re.search(r'class="price">(.*?)</span>', traw, re.S)
            price = parse_price(clean(pm.group(1))) if pm else None
            ex = re.search(r'<div class="explain">(.*?)</div>', seg, re.S)
            menus.append({
                "name": name, "price": price,
                "price_source": "official" if price else None, "price_note": None,
                "compose_raw": clean(ex.group(1)) if ex else None,
                "weight_raw": weight or None,
                "origin_raw": "한우" if any(k in name for k in ["곱창", "대창", "막창", "특양", "모듬", "염통", "육회"]) else None,
                "allergy_raw": None, "detail_url": None, "image_url": img or None,
                "ext_id": srl_i, "cats": [[cname, idx]],
            })
            idx += 1
    out = {
        "brand": "곱창이야기", "slug": "gopchangstory",
        "source": "http://gopchangstory.co.kr/  (메뉴는 고객사이트 http://xn--kb0brxg52cuzb8vj.xn--3e0b707e/menu = 곱창이야기.한국)",
        "collected_at": "2026-07-31", "origin_note": None,
        "cats": cats_out, "menus": menus,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "brand_menu_list", "gopchangstory.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("메뉴", len(menus), "카테고리", len(cats_out))
    for m in menus:
        print(" ", m["cats"][0][0], m["name"], "|", m["price"], "|", (m["compose_raw"] or "")[:22])


if __name__ == "__main__":
    main()
