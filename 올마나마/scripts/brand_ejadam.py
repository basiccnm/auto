# -*- coding: utf-8 -*-
"""자담치킨(ejadam) 메뉴판 수집 — JSON 파일 하나만 만든다. 2026-07-28

    python scripts/brand_ejadam.py

결과: data/brand_menu_list/ejadam.json
⛔ DB 를 import 하지 않는다. 읽기도 쓰기도 안 한다.

사이트 실측 (2026-07-28)
------------------------
`ejadam.co.kr` 은 **그누보드**다. 메뉴 탭은 홈 상단 「메뉴」 드롭다운
(`div.category_submenu_box-inner > li.first-child_0 > dl.category_submenu`)에 적혀 있고
화면 순서 그대로 아래 넷이다. 나머지 두 개(E-쿠폰·제품 영양정보)는 메뉴판이 아니라 제외한다.

    신메뉴        /bbs/content.php?co_id=new_menu      (게시판이 아니라 홍보 페이지)
    치킨          /bbs/board.php?bo_table=menuChicken  Total 33 · 2쪽 · 하위 2개
    피자/파스타   /bbs/board.php?bo_table=menuPizza    Total 6
    사이드메뉴    /bbs/board.php?bo_table=menuEtc      Total 34

- 하위 카테고리는 `<ul id="bo_cate_ul">` 의 `sca=` 링크다. **치킨에만 있다**
  (치킨메뉴 31 · 세트메뉴 2 = 33, 전체와 수가 맞는다).
- 목록은 `<ul id="grid" class="group">` 의 `<li>`. 제목은 `<div class="details"><h3>`.
  검색어 하이라이트 `<b class="sch_word">순살</b>` 가 이름 안에 섞여 들어오니 태그를 벗긴다.
- 상세는 별도 URL 이 아니라 **같은 쪽 안의 모달** `<li id="infoN">` 이다.
  → 설명·알레르기·원본 크기 사진이 거기 있다. 그래서 상세 요청을 따로 보내지 않는다.
- ⚠️ **치킨 목록은 한 쪽에 18개뿐이다.** 첫 쪽만 읽으면 15개가 통째로 빠진다.

🔴 가격 — **사이트 어디에도 없다.** 4쪽 전부에서 `원` 으로 끝나는 금액이 0건이다.
   그래서 전 메뉴 `price: null` 이다. 짐작해 넣지 않는다.

🔴 원산지 — **원산지 표시 페이지가 원산지 표시가 아니다.**
   상단 메뉴에 `content.php?co_id=Country`(「원산지 표시」) 링크가 **주석 처리된 채** 남아 있어
   열어봤더니, 붙어 있는 이미지는 원산지표가 아니라 **옛 영양성분·알레르기 표**였다.
   푸터에도 원산지 표기가 없다. 그래서 원산지는 **메뉴 설명문에 적힌 것만** 살린다
   (`국내산`·`수입`·`원산지` 가 들어간 줄을 원문 그대로 `origin_raw` 로).

중량 — 「제품 영양정보」(`co_id=nutrition`)가 **이미지 한 장**이라 코드로 못 읽는다.
   사람이 눈으로 읽어 옮긴 5건만 `WEIGHT_FROM_IMAGE` 에 박아뒀다(그 외는 표에도 없다).
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "자담치킨"
SLUG = "ejadam"
ROOT = "https://www.ejadam.co.kr"
HOME = ROOT + "/"
GAP = 1.6
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "brand_menu_list", "ejadam.json")

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/126 Safari/537.36"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 「제품 영양정보」 이미지(사람이 판독). 표에 중량이 적힌 것만.
# https://www.ejadam.co.kr/data/editor/2606/4b7cc260ed0f7ef7b3d68a05e75b49a5_1782694477_0059.jpg
WEIGHT_FROM_IMAGE = {
    "치즈화덕피자(7inch)": "192g",
    "페퍼로니화덕피자(7inch)": "201g",
    "맵슐랭화덕피자(7inch)": "225g",
    "소떡소떡": "1개, 130g",
    "조아떡볶이": "총 내용량 290g",
}

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
# ⚠️ 홈에는 같은 모양의 드롭다운이 **두 벌** 있다. 앞의 한 벌은 통째로 주석(`<!-- //임시 메뉴`)이라
#    그걸 집으면 브랜드소개 링크만 나오고 메뉴 탭이 0개가 된다. 주석을 먼저 걷어낸다.
RX_SUBNAV = re.compile(r'(?s)<dl class="category_submenu">(.*?)</dl>')
RX_DD = re.compile(r'(?s)<dd><a href="([^"]+)"[^>]*>(.*?)</a></dd>')
RX_TITLE = re.compile(r'(?s)<h2 id="container_title"[^>]*>(.*?)</h2>')
RX_CATE_UL = re.compile(r'(?s)<ul id="bo_cate_ul">(.*?)</ul>')
RX_A = re.compile(r'(?s)<a href="([^"]*)"[^>]*>(.*?)</a>')
RX_GRID = re.compile(r'(?s)<ul id="grid" class="group">(.*?)</ul>')
RX_CARD = re.compile(r'(?s)<div class="details">\s*<h3>(.*?)</h3>.*?'
                     r'<a class="more" href="#(info\d+)"><img src="([^"]*)"')
RX_MODAL = re.compile(r'(?s)<li id="(info\d+)">(.*?)</li>')
RX_FULLIMG = re.compile(r'(?s)class="view_image"><img src="([^"]*)"')
RX_H4 = re.compile(r'(?s)<h4>(.*?)</h4>')
RX_P = re.compile(r"(?s)<p>(.*?)</p>")
RX_TOTAL = re.compile(r"Total (\d+)건")
RX_PAGE = re.compile(r"page=(\d+)")
RX_MONEY = re.compile(r"[\d,]{3,9}\s*원")
RX_ORIGIN = re.compile(r"(국내산|수입산|수입|원산지|브라질)")

# 신메뉴(홍보 페이지)
RX_NEWSEC = re.compile(r'(?s)<section class="new_menu_list"[^>]*>(.*?)</section>')
RX_NEWNAME = re.compile(r"(?s)<h2><span[^>]*>(.*?)</span></h2>")
RX_NEWIMG = re.compile(r'(?s)<div class="newmenu_postimg"><img src="([^"]*)"')

_dropped = []          # 메뉴가 아니라고 본 줄 (지우기 전에 반드시 출력한다)


def strip_tags(s):
    s = re.sub(r"(?is)<br\s*/?>", "\n", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">"), ("​", "")):
        s = s.replace(a, b)
    return s


def one_line(s):
    return re.sub(r"[ \t]+", " ", re.sub(r"\s+", " ", strip_tags(s))).strip()


def key_of(name):
    return re.sub(r"\s+", "", name)


def dash_null(s):
    """사이트가 「없음」을 - 로 적으면 비운다."""
    if s is None:
        return None
    t = s.strip()
    return None if t in ("", "-", "–", "—") else t


def get(url):
    r = urllib.request.Request(url, headers=HDRS)
    return urllib.request.urlopen(r, timeout=40, context=CTX).read().decode("utf-8", "replace")


def looks_not_menu(name, cat_names):
    """메뉴가 아닌 줄인가 — 문장부호로 끝남 / 18자 이상 / 카테고리 이름과 같음."""
    why = []
    if re.search(r"[.!?~…,;:]$", name):
        why.append("문장부호로 끝남")
    if len(name) >= 18:
        why.append("18자 이상")
    if name in cat_names:
        why.append("카테고리 이름과 같음")
    return why


def parse_board(html, page_url):
    """[(이름, 사진, 설명, 알레르기, 앵커)] — 화면 순서 그대로."""
    g = RX_GRID.search(html)
    if not g:
        return []
    modals = {}
    for anc, body in RX_MODAL.findall(html):
        full = RX_FULLIMG.search(body)
        h4 = RX_H4.search(body)
        desc, allergy = [], []
        if h4:
            parts = [one_line(p) for p in RX_P.findall(h4.group(1))]
            parts = [p for p in parts if p]
            hit = None
            for i, p in enumerate(parts):
                if "알레르기" in p and "표시" in p:
                    hit = i
                    break
            desc = parts[:hit] if hit is not None else parts
            allergy = parts[hit + 1:] if hit is not None else []
        modals[anc] = (full.group(1) if full else None,
                       " ".join(desc) or None, " ".join(allergy) or None)
    out = []
    for raw, anc, thumb in RX_CARD.findall(g.group(1)):
        nm = one_line(raw)
        if not nm:
            continue
        img, desc, allergy = modals.get(anc, (None, None, None))
        # 상세는 별도 주소가 아니라 **같은 쪽 안의 모달**(`#infoN`)이다. 그 앵커까지 붙여 남긴다.
        out.append((nm, img or thumb, desc, allergy, page_url + "#" + anc))
    return out


def board_all_pages(url):
    """페이징을 끝까지 따라간 결과 + 사이트가 스스로 말한 Total."""
    rows, seen_anchor, page, total = [], set(), 1, None
    while True:
        purl = url + ("&page=%d" % page if page > 1 else "")
        html = get(purl)
        if total is None:
            m = RX_TOTAL.search(html)
            total = int(m.group(1)) if m else None
        if RX_MONEY.search(html):
            print("   ⚠️ 이 쪽에 금액 표기가 있다 — 가격 파서를 새로 붙일 것: %s" % url)
        got = 0
        for row in parse_board(html, purl):
            k = row[4]
            if k in seen_anchor:
                continue
            seen_anchor.add(k)
            rows.append(row)
            got += 1
        last = max([int(x) for x in RX_PAGE.findall(html)] or [1])
        if got == 0 or page >= last or page >= 20:
            break
        page += 1
        time.sleep(GAP)
    return rows, total, page


def parse_new_menu(html):
    out = []
    for body in RX_NEWSEC.findall(html):
        n = RX_NEWNAME.search(body)
        if not n:
            continue
        nm = one_line(n.group(1))
        img = RX_NEWIMG.search(body)
        if nm:
            out.append((nm, img.group(1) if img else None, None, None, None))
    return out


def abs_url(u):
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return ROOT + u
    return u


def main():
    print("● %s — %s" % (BRAND, HOME), flush=True)
    home = get(HOME)
    time.sleep(GAP)

    # ── 1. 홈에 적힌 메뉴 탭만 따라간다 (주소를 조합하지 않는다)
    live = RX_COMMENT.sub(" ", home)
    sub = next((b for b in RX_SUBNAV.findall(live) if "bo_table=menu" in b), None)
    if not sub:
        print("🔴 홈에서 메뉴 드롭다운을 못 찾았다 — 화면 구조가 바뀌었다")
        return
    tabs = []
    for href, label in RX_DD.findall(sub):
        nm = one_line(label)
        u = abs_url(href.replace("&amp;", "&"))
        if "bo_table=menu" in u:
            ext = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)["bo_table"][0]
            tabs.append((nm, u, ext, "board"))
        elif "co_id=new_menu" in u:
            tabs.append((nm, u, "new_menu", "content"))
        else:
            _dropped.append((nm, u, "메뉴판이 아니다(상단메뉴의 부가 페이지)"))
    print("   탭 %d개: %s" % (len(tabs), " → ".join(n for n, *_ in tabs)), flush=True)

    cats, cat_names, menus, order = [], set(), {}, []

    def take(path, rows, kind="board"):
        # 같은 메뉴가 「신메뉴」 홍보 페이지에는 `뿌슐랭 치킨`, 게시판에는 `뿌슐랭치킨` 으로 적혀 있다.
        # 띄어쓰기를 지운 키로 합치고, **이름·사진은 메뉴판(게시판) 쪽을 정본**으로 쓴다.
        for pos, (nm, img, desc, allergy, anc) in enumerate(rows):
            k = key_of(nm)
            if k in menus and kind == "board" and menus[k].get("_src") == "content":
                menus[k]["name"] = nm
                menus[k]["image_url"] = abs_url(img)
                menus[k]["_src"] = "board"
            if k not in menus:
                menus[k] = {
                    "name": nm, "price": None, "price_source": None, "price_note": None,
                    "weight_raw": WEIGHT_FROM_IMAGE.get(k),
                    "origin_raw": None, "allergy_raw": None,
                    "detail_url": None, "image_url": abs_url(img),
                    "ext_id": None, "cats": [], "_src": kind,
                }
                order.append(k)
            it = menus[k]
            if not it["image_url"]:
                it["image_url"] = abs_url(img)
            if allergy and not it["allergy_raw"]:
                it["allergy_raw"] = dash_null(allergy)
            if desc and not it["origin_raw"]:
                hit = [ln.strip() for ln in strip_tags(desc).split("\n")
                       if RX_ORIGIN.search(ln)]
                # 설명은 이미 한 줄로 합쳐져 있어 문장 단위로 다시 자른다
                if not hit:
                    hit = [s.strip() for s in re.split(r"(?<=[.!])\s+", desc)
                           if RX_ORIGIN.search(s)]
                if hit:
                    it["origin_raw"] = dash_null(" ".join(hit))
            if not it["detail_url"] and anc:
                it["detail_url"] = anc
            if [path, pos] not in it["cats"]:
                it["cats"].append([path, pos])

    for nm, url, ext, kind in tabs:
        cats.append({"name": nm, "parent": None, "ext_id": ext})
        cat_names.add(nm)
        if kind == "content":
            rows = parse_new_menu(get(url))
            total = None
            print("   %-10s %2d개 (홍보 페이지)" % (nm, len(rows)), flush=True)
        else:
            rows, total, npg = board_all_pages(url)
            print("   %-10s %2d개 (%d쪽 / 사이트 Total %s)"
                  % (nm, len(rows), npg, total), flush=True)
        if total is not None and total != len(rows):
            print("   ⚠️ %s — 사이트는 %s건이라는데 %d건만 읽혔다" % (nm, total, len(rows)))
        take(nm, rows, kind)

        # 하위 카테고리 (sca=) — 목록 페이지에 적힌 것만 따라간다
        if kind == "board":
            html = get(url)
            time.sleep(GAP)
            m = RX_CATE_UL.search(html)
            subs = []
            for href, label in (RX_A.findall(m.group(1)) if m else []):
                lb = one_line(label)
                if "sca=" not in href or lb in ("전체", ""):
                    continue
                subs.append((lb, abs_url(href.replace("&amp;", "&"))))
            for lb, su in subs:
                cats.append({"name": lb, "parent": nm, "ext_id":
                             urllib.parse.unquote(su.split("sca=")[-1].split("&")[0])})
                cat_names.add(lb)
                srows, stotal, snpg = board_all_pages(su)
                print("     └ %-8s %2d개 (%d쪽 / Total %s)"
                      % (lb, len(srows), snpg, stotal), flush=True)
                take(nm + "/" + lb, srows)
                time.sleep(GAP)
        time.sleep(GAP)

    items = [menus[k] for k in order]
    for it in items:
        it.pop("_src", None)
    if not items:
        print("🔴 0건 — 저장하지 않는다. 화면 구조가 바뀌었다")
        return

    # ── 메뉴 아닌 줄 검사 (지우지 않고 목록으로 보여준다)
    flagged = [(it["name"], looks_not_menu(it["name"], cat_names)) for it in items]
    flagged = [(n, w) for n, w in flagged if w]
    if flagged:
        print("\n⚠️ 길이·형태 규칙에 걸린 줄 %d개 — **지우지 않았다**(메뉴 카드에서 나온 이름이다):"
              % len(flagged))
        for n, w in flagged:
            print("     %-30s %s" % (n, " · ".join(w)))
    if _dropped:
        print("\n버린 줄 %d개:" % len(_dropped))
        for n, u, why in _dropped:
            print("     %-16s %-60s %s" % (n, u, why))

    doc = {
        "brand": BRAND, "slug": SLUG,
        "source": HOME, "collected_at": "2026-07-28",
        "origin_note": None,
        "cats": cats, "menus": items,
    }
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    n_price = sum(1 for x in items if x["price"] is not None)
    print("\n저장 → %s" % os.path.normpath(os.path.abspath(OUT)))
    print("   카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 %d개 · 연결 %d건"
          % (len(cats), sum(1 for c in cats if c["parent"]), len(items), n_price,
             sum(len(x["cats"]) for x in items)))


if __name__ == "__main__":
    main()
