# -*- coding: utf-8 -*-
"""뚜레쥬르 메뉴 수집 — 공식 홈페이지. 2026-07-31 신설

    python scripts/brand_tlj.py

경로 (2026-07-31 확인 · **사이트 자체 스크립트에서 읽은 것**. 추측 아님)
    GET /product/list.asp?ref={대}[&cg_num={소}]            첫 화면 (15개)
    GET /product/list_ajax.asp?ref={대}&cg_num={소}&page=N   무한스크롤 다음 장
        → 더 없으면 본문이 정확히 `x` 로 온다. 그때 멈춘다.

  대분류 ref: 1 NEW · 2 빵 · 3 케이크 · 4 델리 · 6 디저트&스낵 · 9 선물
  소분류 cg_num 은 **첫 화면에서 읽는다.** 번호를 추측해 찔러보지 않는다.

🔴 **인코딩은 euc-kr.** utf-8 로 읽으면 글자가 통째로 깨진다(브라우저 fetch 로 받았다가 겪음).
🔴 상품명은 목록에서 «…» 로 잘려 나온다. **`title=` 속성에 전체 이름**이 있으니 그걸 쓴다.
🔴 **가격이 없다.** 뚜레쥬르 공식은 제품명·설명만 싣는다 → 이름만 넣고 가격은 뒤 단계에서.
⚠️ 요청 간격 1초 이상. 파리바게트에서 파라미터를 바꿔 방화벽에 막힌 날이라 더 조심한다.

결과: data/brand_menu_list/tlj.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
ROOT = "https://www.tlj.co.kr/product"
TOPS = [("NEW", 1), ("빵", 2), ("케이크", 3), ("델리", 4), ("디저트&스낵", 6), ("선물", 9)]
GAP = 1.1
MAX_PAGE = 30                    # 안전장치 — 무한루프 방지

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": ROOT + "/list.asp", "X-Requested-With": "XMLHttpRequest"}

RX_ITEM = re.compile(r'<li[^>]*class="[^"]*item_wrap[^"]*"[^>]*>(.*?)</li>', re.S | re.I)
RX_ALT = re.compile(r'\salt="([^"]{2,60})"')
RX_TITLE = re.compile(r'title="([^"]{1,60})"')
# 🔴 페이지에 목록이 **둘** 있다 — 위쪽 «추천제품»(product_list) 과 실제 목록(#product_list).
#    둘 다 긁으면 중복이 생기고 추천 쪽 이름이 더 심하게 잘려 있다(2026-07-31).
RX_REAL = re.compile(r'id="product_list"(.*)$', re.S)
RX_NAME = re.compile(r'<span[^>]*class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</span>', re.S | re.I)
RX_SUB = re.compile(r'href="[^"]*cg_num=(\d+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{1,20})', re.I)


def get(path):
    req = urllib.request.Request(ROOT + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("euc-kr", "replace")


def txt(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def items_of(html, only_real=True):
    """한 덩이(li.item_wrap)에서 **전체 이름**을 하나만 뽑는다.

    🔴 이름이 세 군데 있는데 길이가 다 다르다(2026-07-31 확인):
         `.name`   «그대로 구워먹는 꿀 토스트...»   ← 잘림
         `title=`  «그대로 구워먹는 꿀 토스»        ← 더 심하게 잘림
         `img alt` «그대로 구워먹는 꿀 토스트 식빵»  ← **전체 이름**
       그래서 alt 를 1순위로 본다.
    🔴 `only_real` — 위쪽 «추천제품» 블록을 건너뛰고 `#product_list` 만 읽는다.
       추천은 목록에도 다시 나오므로 같이 읽으면 중복이 된다.
    """
    if only_real:
        m = RX_REAL.search(html)
        if m:
            html = m.group(1)
    out = []
    for blk in RX_ITEM.findall(html):
        # 🔴 한 덩이에 title 이 여러 개다(이미지 alt·앵커·MORE 버튼). 그중 **잘리지 않은 것**을
        #    골라야 한다. 첫 번째를 집었다가 「그대로 구워먹는 꿀 토스」 처럼 잘린 이름이 들어갔다
        #    (2026-07-31). 가장 긴 후보가 전체 이름이다.
        cand = [txt(x) for x in RX_ALT.findall(blk)]          # alt 가 전체 이름
        cand += [txt(x) for x in RX_TITLE.findall(blk)]
        m = RX_NAME.search(blk)
        if m:
            cand.append(txt(m.group(1)))
        cand = [c for c in cand if c and c.upper() not in ("MORE", "NEW", "BEST")]
        cand = [c.rstrip(". ").rstrip("…").strip() for c in cand]
        cand = [c for c in cand if len(c) >= 2]
        if not cand:
            continue
        out.append(max(cand, key=len))
    # 한 덩이가 두 번 잡히는 경우가 있어 순서를 지키며 중복 제거
    seen, res = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res


def subs_of(html):
    out, seen = [], set()
    for num, label in RX_SUB.findall(html):
        lb = txt(label)
        if lb and lb != "전체" and num not in seen:
            seen.add(num)
            out.append((lb, num))
    return out


def all_items(ref, cg=None):
    """첫 화면 + 무한스크롤 다음 장을 **사이트가 하는 그대로** 이어받는다."""
    q = "?ref=%d" % ref + ("&cg_num=%s" % cg if cg else "")
    got = items_of(get("/list.asp" + q))
    page = 1
    while page < MAX_PAGE:
        page += 1
        time.sleep(GAP)
        body = get("/list_ajax.asp" + q + "&page=%d" % page)
        if body.strip() == "x":
            break
        more = items_of(body, only_real=False)
        if not more:
            break
        before = len(got)
        for n in more:
            if n not in got:
                got.append(n)
        if len(got) == before:          # 같은 것만 오면 끝난 것으로 본다
            break
    return got


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for top, ref in TOPS:
        head = get("/list.asp?ref=%d" % ref)
        subs = subs_of(head)
        print("■ %s (ref=%d) — 소분류 %d개" % (top, ref, len(subs)), flush=True)
        time.sleep(GAP)
        if not subs:
            got = all_items(ref)
            if got:
                cats.append({"name": top, "parent": None, "ext_id": str(ref)})
                for i, n in enumerate(got):
                    nm = n if n not in seen else "%s (%s)" % (n, top)
                    seen.add(nm)
                    menus.append({"name": nm, "price": None, "price_source": None,
                                  "cats": [[top, i]]})
                print("   · %-18s %3d개" % ("(소분류 없음)", len(got)))
            continue
        cats.append({"name": top, "parent": None, "ext_id": str(ref)})
        for lb, num in subs:
            got = all_items(ref, num)
            if not got:
                print("   - %-18s 0개" % lb[:18])
                continue
            cats.append({"name": lb, "parent": top, "ext_id": num})
            path = "%s/%s" % (top, lb)
            for i, n in enumerate(got):
                nm = n if n not in seen else "%s (%s)" % (n, lb)
                seen.add(nm)
                menus.append({"name": nm, "price": None, "price_source": None,
                              "cats": [[path, i]]})
            print("   · %-18s %3d개" % (lb[:18], len(got)))
            time.sleep(GAP)

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스에서 빈 JSON 으로 덮은 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 화면 구조를 확인할 것.")
        return 1
    p = os.path.join(OUT, "tlj.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "뚜레쥬르", "slug": "tlj", "source": ROOT + "/list.asp?ref=2",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지 제품 목록(euc-kr · 무한스크롤 list_ajax.asp). "
                   "뚜레쥬르는 공식에 **가격을 싣지 않는다** — 이름만.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
