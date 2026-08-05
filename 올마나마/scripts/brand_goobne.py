# -*- coding: utf-8 -*-
"""굽네치킨 메뉴판 — 카테고리·순서·가격. 2026-07-28

    python scripts/brand_goobne.py            # 미리보기
    python scripts/brand_goobne.py --apply

구조 (실측)
    https://www.goobne.co.kr/menu/menu_list_p?classId=<코드>
    <a onclick="menu_view('30001', 0)" class="item">
      <h4 class="fs20 fwbold mb10">New 오리지널</h4>
      <p class="price"><b>17,900</b>원 …

🔴 화면은 `menu_list(classId,'')` 를 **POST** 로 보내지만, 그대로 흉내내면
   `{"errMsg":"업무오류발생"}` 가 온다. **GET 에 `?classId=` 를 붙이면 그냥 읽힌다.**
   (브라우저·헤드리스 크롬 없이 `urllib` 만으로 된다)

탭 6개 — 화면에 깔린 순서 그대로
    전체('') · 신제품(3) · 치킨(1) · 피자(12) · 사이드(16) · 소스&시즈닝(18)
⚠️ 「전체」 는 중복 진열 탭이지만 **브랜드가 그렇게 보여주므로 그대로 둔다**
   (`브랜드메뉴판등록방식.md`).
"""
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

BRAND = "굽네치킨"
LIST = "https://www.goobne.co.kr/menu/menu_list_p"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/126 Safari/537.36"}
GAP = 1.2

RX_TAB = re.compile(r'onclick="menu_list\((.*?)\)"[^>]*>(.*?)</a>', re.S)
RX_ITEM = re.compile(r'onclick="menu_view\((.*?)\)"\s+class="item"(.*?)</a>', re.S)
RX_NAME = re.compile(r'<h4[^>]*>(.*?)</h4>', re.S)
RX_PRICE = re.compile(r'<p class="price">\s*<b>\s*([\d,]+)\s*</b>', re.S)
RX_IMG = re.compile(r'<img src="([^"]+)"')


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def get(q=""):
    r = urllib.request.Request(LIST + q, headers=HDRS)
    return urllib.request.urlopen(r, timeout=25).read().decode("utf-8", "replace")


def tabs_of(dom):
    """(코드, 이름) 을 화면 순서 그대로. 코드가 비면 「전체」다."""
    out = []
    for args, label in RX_TAB.findall(dom):
        nm = strip(label)
        code = "".join(re.findall(r'"(\d+)"', args.replace("&quot;", '"')))
        if nm:
            out.append((code, nm))
    return out


def parse(dom):
    """[(이름, 가격, 사진주소)] — 화면에 깔린 순서 그대로."""
    out = []
    for _, body in RX_ITEM.findall(dom):
        n, p = RX_NAME.search(body), RX_PRICE.search(body)
        if not n:
            continue
        nm = strip(n.group(1))
        pr = int(p.group(1).replace(",", "")) if p else None
        img = RX_IMG.search(body)
        if nm:
            out.append((nm, pr, img.group(1) if img else None))
    return out


def main():
    apply_ = "--apply" in sys.argv

    dom = get()
    tabs = tabs_of(dom)
    if not tabs:
        print("🔴 탭을 못 읽었다 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    print("탭 %d개: %s" % (len(tabs), " → ".join(n for _, n in tabs)), flush=True)

    order, byname = [], {}
    for code, cn in tabs:
        page = dom if not code else get("?classId=%s" % code)
        rows = parse(page)
        for pos, (nm, pr, img) in enumerate(rows):
            k = re.sub(r"\s+", "", nm)
            if k not in byname:
                byname[k] = {"name": nm, "price": pr, "image_url": img,
                             "price_source": "official", "detail_url": LIST, "cats": []}
                order.append(k)
            byname[k]["cats"].append((cn, pos))
        print("  %-10s %2d개" % (cn, len(rows)), flush=True)
        if code:
            time.sleep(GAP)

    items = [byname[k] for k in order]
    if not items:
        print("🔴 0건 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    n_price = sum(1 for x in items if x["price"])
    print("\n● %s — 고유 메뉴 %d개 (가격 %d) · 연결 %d건"
          % (BRAND, len(items), n_price, sum(len(x["cats"]) for x in items)))
    for it in items[:8]:
        print("   %-26s %8s원  %s" % (it["name"][:26],
                                      format(it["price"], ",") if it["price"] else "-",
                                      ", ".join(c for c, _ in it["cats"])))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    c = store.connect()
    store.ensure(c)
    bid = store.brand_id(c, name=BRAND)
    store.replace_brand(c, bid, [{"name": n} for _, n in tabs], items,
                        collector="brand_goobne")
    c.close()


if __name__ == "__main__":
    main()
