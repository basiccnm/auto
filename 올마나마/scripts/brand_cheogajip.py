# -*- coding: utf-8 -*-
"""처갓집양념치킨 메뉴판 — 카테고리·순서·가격. 2026-07-28

    python scripts/brand_cheogajip.py            # 미리보기
    python scripts/brand_cheogajip.py --apply

사이트 실측 (2026-07-28)
------------------------
🔴 **공식 첫 화면(`cheogajip.co.kr`)은 「5 Challenge」 캠페인 페이지라 메뉴가 아예 없다.**
   그래서 지금까지 «0쪽 = 못 뚫는 곳» 으로 잘못 판단했고 DB 에 3개만 들어와 있었다.
   메뉴는 **그누보드 게시판**에 있다:

       /bbs/board.php?bo_table=allmenu                 전체 32개
       /bbs/board.php?bo_table=allmenu&sca=<카테고리>   탭 5개

   탭: 한마리메뉴 · 반반메뉴 · 다리.날개메뉴 · 반마리메뉴 · 사이드메뉴

    <li class="gall_li">
      <!-- <p class="bo_cate_link">한마리메뉴</p> -->     ← 카테고리가 **주석 안**에 있다
      미트칠리 양념치킨  <hr class="subjectunder">        ← 메뉴명은 맨 텍스트
      <ul class="menutag"><li>#한마리</li><li>#순살</li>…  ← 고를 수 있는 부위
      <p class="menuprice">19,000원+<strong>4,000원</strong></p>

🔴 가격이 **「본품가 + 옵션 추가금」** 이다(bhc 와 같은 구조).
   `price` 에는 **본품가**(한마리 기준)를 넣고, 원문은 `price_note` 에 그대로 남긴다.
   추가금을 더해 넣으면 실제보다 비싼 값이 된다.
⚠️ 목록에 **페이징**이 있다(`page=2`). 첫 쪽만 읽으면 메뉴가 잘린다.
⚠️ SSL 인증서가 말썽이라 검증을 끈다.
"""
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

BRAND = "처갓집양념치킨"
BOARD = "https://www.cheogajip.co.kr/bbs/board.php?bo_table=allmenu"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/126 Safari/537.36"}
GAP = 1.2

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RX_TABLINK = re.compile(r'href="[^"]*sca=([^"&]+)"[^>]*>(.{0,60}?)</a>', re.S)
RX_ITEM = re.compile(r'(?s)<li class="gall_li[^"]*"[^>]*>(.*?)</ul>\s*</li>')
RX_CATE = re.compile(r'class="bo_cate_link">(.*?)</p>', re.S)
RX_NAME = re.compile(r'(?s)(?:-->|</li>)\s*([^<>\n][^<>]*?)\s*<hr class="subjectunder">')
RX_PRICE = re.compile(r'(?s)class="menuprice">(.*?)</p>')
RX_IMG = re.compile(r'<img src="([^"]+)"')
RX_TAG = re.compile(r"<li>#(.*?)</li>")
RX_PAGE = re.compile(r"page=(\d+)")


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def get(url):
    r = urllib.request.Request(url, headers=HDRS)
    return urllib.request.urlopen(r, timeout=30, context=CTX).read().decode("utf-8", "replace")


def parse(html):
    """[(이름, 본품가, 가격원문, 사진, 부위태그)] — 화면 순서 그대로."""
    out = []
    for body in RX_ITEM.findall(html):
        n = RX_NAME.search(body)
        if not n:
            continue
        nm = strip(n.group(1))
        p = RX_PRICE.search(body)
        raw = strip(p.group(1)) if p else ""
        nums = [int(x.replace(",", "")) for x in re.findall(r"([\d,]{3,9})\s*원", raw)]
        base = nums[0] if nums else None            # 🔴 첫 숫자가 본품가. 더하지 않는다
        img = RX_IMG.search(body)
        tags = [strip(t) for t in RX_TAG.findall(body)]
        if nm:
            out.append((nm, base, raw or None, img.group(1) if img else None, tags))
    return out


def pages_of(url):
    """페이징을 따라가며 모든 쪽을 이어붙인 결과."""
    rows, n = [], 1
    while True:
        html = get(url + ("&page=%d" % n if n > 1 else ""))
        rows += parse(html)
        last = max([int(x) for x in RX_PAGE.findall(html)] or [1])
        if n >= last or n >= 20:
            break
        n += 1
        time.sleep(GAP)
    return rows, n


def main():
    apply_ = "--apply" in sys.argv

    home = get(BOARD)
    tabs, seen = [], set()
    for sca, label in RX_TABLINK.findall(home):
        nm = strip(label)
        if nm and nm not in seen:
            seen.add(nm)
            tabs.append((sca, nm))
    if not tabs:
        print("🔴 탭을 못 읽었다 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    print("탭 %d개: %s" % (len(tabs), " → ".join(n for _, n in tabs)), flush=True)

    order, byname = [], {}

    def take(cat, rows):
        for pos, (nm, base, raw, img, tags) in enumerate(rows):
            k = re.sub(r"\s+", "", nm)
            if k not in byname:
                byname[k] = {"name": nm, "price": base, "image_url": img,
                             "price_source": "official" if base else None,
                             "price_note": raw, "detail_url": BOARD, "cats": []}
                order.append(k)
            byname[k]["cats"].append((cat, pos))

    for sca, cn in tabs:
        rows, np_ = pages_of(BOARD + "&sca=" + sca)
        take(cn, rows)
        print("  %-12s %2d개 (%d쪽)" % (cn, len(rows), np_), flush=True)
        time.sleep(GAP)

    # 어느 탭에도 안 걸린 메뉴가 있는지 — 전체 목록과 대조한다(조용히 빠지면 모른다)
    allrows, _ = pages_of(BOARD)
    miss = [nm for nm, *_ in allrows if re.sub(r"\s+", "", nm) not in byname]
    if miss:
        print("  ⚠️ 어느 탭에도 없는 메뉴 %d개: %s" % (len(miss), ", ".join(miss[:8])))

    items = [byname[k] for k in order]
    if not items:
        print("🔴 0건 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    n_price = sum(1 for x in items if x["price"])
    print("\n● %s — 고유 메뉴 %d개 (가격 %d) · 연결 %d건 · 전체목록 %d개"
          % (BRAND, len(items), n_price, sum(len(x["cats"]) for x in items), len(allrows)))
    for it in items[:8]:
        print("   %-24s %8s원  [%s]  %s" % (
            it["name"][:24], format(it["price"], ",") if it["price"] else "-",
            it["price_note"] or "", ", ".join(c for c, _ in it["cats"])))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    c = store.connect()
    store.ensure(c)
    bid = store.brand_id(c, name=BRAND)
    store.replace_brand(c, bid, [{"name": n} for _, n in tabs], items,
                        collector="brand_cheogajip")
    c.close()


if __name__ == "__main__":
    main()
