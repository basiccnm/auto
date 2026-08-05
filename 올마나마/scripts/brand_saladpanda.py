# -*- coding: utf-8 -*-
# 샐러드판다 (slug=saladpanda) — https://saladpanda.co.kr (Cafe24)
# 카테고리 목록: /product/list.html?cate_no=<no>&page=<n>
# 상품 li: id="anchorBoxId_<product_no>", 이름=<p class="name"><a>...</a>, 가격=data-price(정수), 세일=data-sale
# GNB(헤더 메뉴) 순서 그대로 상위→하위. 상품은 여러 카테고리에 중복 진열되므로 product_no 로 dedupe 후 다중 cats.
import sys, json, os, re, time, urllib.request
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "brand_menu_list", "saladpanda.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# GNB 트리: (상위명, 상위cate, [(하위명, 하위cate), ...])  하위 없으면 상위 자신을 leaf 로
TREE = [
    ("세트메뉴", "58", [("세트메뉴", "134"), ("판다의 타임세일", "174")]),
    ("정기배송", "44", [("고정 식단", "52"), ("선택 식단", "53"), ("블럭 식단", "153"), ("랜덤 식단", "154"),
                     ("하루 한 끼", "146"), ("하루 두 끼", "148"), ("하루 세 끼", "149"),
                     ("1주 식단", "230"), ("2주 식단", "158"), ("4주 식단", "159")]),
    ("샐러드", "164", [("프리미엄 샐러드", "222"), ("슬로우 샐러드", "242"), ("보틀샐러드", "165"),
                    ("그린 샐러드", "225"), ("세끼판다 샐러드", "166"), ("누들 샐러드", "167"),
                    ("그레인볼 샐러드", "185"), ("쉬라즈 샐러드", "238"), ("두유면 샐러드", "239")]),
    ("샌드위치", "145", [("샐러드 샌드위치", "201"), ("모닝 샌드&스프레드", "202"), ("랩 샌드위치", "184")]),
    ("저당 드레싱", "236", []),
    ("간식", "75", []),
]

LI_RE = re.compile(r'id="anchorBoxId_(\d+)"')
NAME_RE = re.compile(r'<p class="name\s*"><a [^>]*>(.*?)</a>', re.S)
PRICE_RE = re.compile(r'class="rate_box"[^>]*data-price="(\d*)"[^>]*data-sale="(\d*)"')


def fetch(cate, page):
    u = f"https://saladpanda.co.kr/product/list.html?cate_no={cate}&page={page}"
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def parse_page(html):
    """return list of (product_no, name, price, sale) in DOM order, only inside prdList area."""
    j = html.find("prdList")
    if j < 0:
        return []
    body = html[j:]
    # cut off footer/other lists: stop at recommend/review sections is hard; rely on anchorBoxId blocks
    items = []
    idxs = [(m.start(), m.group(1)) for m in LI_RE.finditer(body)]
    for k, (pos, pno) in enumerate(idxs):
        seg = body[pos: idxs[k + 1][0] if k + 1 < len(idxs) else pos + 4000]
        nm = NAME_RE.search(seg)
        pr = PRICE_RE.search(seg)
        name = strip_tags(nm.group(1)) if nm else None
        price = int(pr.group(1)) if (pr and pr.group(1)) else None
        sale = int(pr.group(2)) if (pr and pr.group(2)) else None
        if name:
            items.append((pno, name, price, sale))
    return items


def collect(cate):
    out, seen = [], set()
    for page in range(1, 12):
        try:
            html = fetch(cate, page)
        except Exception as e:
            print("  fetch err", cate, page, e); break
        items = parse_page(html)
        fresh = [it for it in items if it[0] not in seen]
        if not fresh:
            break
        for it in fresh:
            seen.add(it[0]); out.append(it)
        time.sleep(0.5)
        if len(items) < 1:
            break
    return out


def main():
    cats = []
    leaves = []   # (leaf_name, leaf_cate)
    for top, tcate, subs in TREE:
        cats.append({"name": top, "parent": None, "ext_id": tcate})
        if subs:
            for sname, scate in subs:
                cats.append({"name": sname, "parent": top, "ext_id": scate})
                leaves.append((sname, scate))
        else:
            leaves.append((top, tcate))

    menus = {}   # product_no -> dict
    order = []
    for lname, lcate in leaves:
        items = collect(lcate)
        print(f"  {lname}({lcate}): {len(items)}")
        for pos, (pno, name, price, sale) in enumerate(items):
            note = None
            p = price
            if sale:
                note = f"할인가 {sale}"
            if pno not in menus:
                menus[pno] = {
                    "name": name, "price": p, "price_source": "official" if p else None,
                    "price_note": note,
                    "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": f"https://saladpanda.co.kr/product/detail.html?product_no={pno}",
                    "image_url": None, "ext_id": pno, "cats": [],
                }
                order.append(pno)
            menus[pno]["cats"].append([lname, pos])

    out = {
        "brand": "샐러드판다", "slug": "saladpanda",
        "source": "공식 saladpanda.co.kr Cafe24 /product/list.html?cate_no= — GNB 카테고리별, data-price 파싱",
        "collected_at": str(date.today()), "origin_note": None,
        "cats": cats, "menus": [menus[k] for k in order],
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    prices = sum(1 for k in order if menus[k]["price"])
    print(f"cats {len(cats)}(leaf {len(leaves)}) · menus {len(order)} · prices {prices}")


if __name__ == "__main__":
    main()
