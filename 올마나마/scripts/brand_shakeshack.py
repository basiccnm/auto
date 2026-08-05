# -*- coding: utf-8 -*-
"""쉐이크쉡(slug shakeshack, brand_id 42) 메뉴판 수집 — 카테고리·메뉴·순서·가격. 2026-07-28

    python scripts/brand_shakeshack.py
    → data/brand_menu_list/shakeshack.json  (DB 는 건드리지 않는다)

사이트 실측 (2026-07-28)
------------------------
🔴 **DB 홈페이지 주소 `http://www.shakeshack.kr/` 는 56바이트다.** 죽은 게 아니라 **껍데기**다 —
   내용은 이것뿐이고, 여기 적힌 곳으로만 따라갔다(다른 도메인을 추측하지 않았다):

       <script>window.location.replace('main.jsp');</script>

   `main.jsp` 의 GNB 에 `/sub/menu.jsp#tab1` 이 있다. 그게 메뉴판이다(67KB).

🔴 **탭 8개가 한 페이지 안에 전부 서버 렌더돼 있다.** JS 로 보이기만 전환할 뿐이라
   탭을 누를 필요가 없고 헤드리스도 필요 없다 — 순수 HTTP 한 번으로 51개가 다 나온다.
   (`div#tab1 ~ #tab8 .tab_content` 가 처음부터 DOM 에 있다.)

   ⚠️ **인코딩은 UTF-8 이다.** 콘솔이 cp949 라 그냥 print 하면 깨져서 EUC-KR 로 착각하기 쉽다.
      파일 헤더도 `charset=UTF-8` 이다. 그래서 `sys.stdout.reconfigure(encoding="utf-8")`.

탭 이름·순서는 화면 그대로(`.menu-tab2 li[rel=tabN]`), `ext_id` 는 해시(`#tabN`):

    #tab1 BURGERS 9 · #tab2 CHICKEN 3 · #tab3 SIDES 6 · #tab4 DOG 4 ·
    #tab5 SHAKES & CUSTARD 4 · #tab6 CONCRETES 12 · #tab7 DRINKS 9 · #tab8 BREAKFAST 4

    ⚠️ 탭 이름은 「DOG」인데 그 안의 제목은 「FLAT-TOP DOGS」다. **탭 이름을 쓴다**(화면의 카테고리 나열).
       원문 제목은 `cats[].title_raw` 에 남긴다.

🔴 **가격 표기가 `W 14,9` 꼴이다** — 「원」도 없고 뒷자리도 잘려 있다. `14,9` = **14,900원**.
   그래서 `W (\\d+),(\\d+)` 를 잡아 뒷자리를 0 으로 채워 3자리로 만든다(`9` → `900`).
   ⚠️ 한 카드에 값이 여럿이다:
       `Single W 9,2 / Double W 14,2`  (크기)
       `닭가슴살 W 9,7 / 닭다리살 W 10,7`  (부위)
       `6-count W 5,9 / 10-count W 8,4`  (수량)
   **이건 세트가 아니라 같은 메뉴의 옵션**이라 줄을 쪼개지 않는다.
   `price` 는 **맨 앞(기본) 값**을 넣고, 화면 원문은 `price_raw` 에 통째로 남긴다.
   ⚠️ 이 사이트에는 「세트」 메뉴가 아예 없다(단품만 판다).

🔴 **원산지 표기가 없다.** 메뉴판·`/sub/values.jsp`·`/sub/cs.jsp` 에서 `원산지`·`산지` **0건**.
   `values.jsp` 는 「100일 이상 곡물 사료로 키운 블랙 앵거스 비프」 같은 **브랜드 설명**이지
   원산지 표기가 아니라서 `origin_raw` 에 넣지 않는다(원문 그대로가 아니면 안 쓴다).
   알레르기 표도 없다(`알레르기` 0건).

⚠️ 중량 표기도 없다 — `weight_raw` 는 전부 비운다.
⚠️ 카드의 설명문은 구성 그대로라(`비프 패티와 함께 토마토, 양상추, 쉑소스가 토핑된 치즈버거`)
   `compose_raw` 에 **원문 그대로** 담는다.
⚠️ `menu-image` 의 뱃지(`limited` = 시즌 한정 · `recom` = 추천)는 `badge_raw` 로 남긴다.
"""
import io
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "쉐이크쉡"                      # DB brands.name (slug shakeshack, id 42)
SLUG = "shakeshack"
BASE = "http://www.shakeshack.kr"
MENU_PATH = "/sub/menu.jsp"
COLLECTED = "2026-07-28"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")
CACHE = os.path.join(tempfile.gettempdir(), "olmanama_shakeshack")

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
GAP = 1.6                              # 요청 간격 1.5초 이상
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RX_TAB = re.compile(r'<li[^>]*rel="(tab\d+)"[^>]*>(.*?)</li>', re.S)
RX_SPLIT = re.compile(r'<div id="(tab\d+)" class="tab_content">')
RX_H2 = re.compile(r"(?s)<h2>(.*?)</h2>")
RX_LI = re.compile(r"(?s)<li>(.*?)</li>")
RX_NAME = re.compile(r'(?s)<h3 class="mgb5">(.*?)</h3>')
RX_NAME_KR = re.compile(r'(?s)<h3 class="h3-kr[^"]*">(.*?)</h3>')
RX_DESC = re.compile(r'(?s)<p class="body-normal-kr[^"]*">(.*?)</p>')
RX_PRICE = re.compile(r'(?s)<p class="body-normal tx-color-dgrey">(.*?)</p>')
RX_IMG = re.compile(r"background:url\(['\"]?([^)'\"]+)")
RX_BADGE = re.compile(r'class="menu-image([^"]*)"')
RX_LINK = re.compile(r'class="[^"]*menu-link"\s*href="([^"]+)"')
RX_W = re.compile(r"W\s*([0-9]+),([0-9]+)")


def fetch(path):
    fn = os.path.join(CACHE, re.sub(r"[^0-9A-Za-z_.-]", "_", path.strip("/") or "root") + ".html")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < 86400:
        return io.open(fn, encoding="utf-8").read()
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(BASE + path, headers=HDRS)
    html = urllib.request.urlopen(req, timeout=45, context=CTX).read().decode("utf-8", "replace")
    io.open(fn, "w", encoding="utf-8").write(html)
    time.sleep(GAP)
    return html


def decomment(html):
    """HTML 주석을 먼저 걷어낸다"""
    return re.sub(r"(?s)<!--.*?-->", " ", html)


def txt(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).replace("&nbsp;", " ").strip()


def raw_line(s):
    """<br> 은 「 / 」 로 — 화면에서 줄이 나뉘던 자리를 남긴다"""
    s = re.sub(r"<br\s*/?>", " / ", s)
    s = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).replace("&nbsp;", " ").strip()
    return re.sub(r"\s*/\s*$", "", s).strip() or None


def won(s):
    """`W 14,9` → 14900. 뒷자리를 0 으로 채워 3자리로 만든다"""
    m = RX_W.search(s or "")
    if not m:
        return None
    return int(m.group(1)) * 1000 + int(m.group(2).ljust(3, "0"))


def reject_reason(name, cat_names):
    """메뉴 아닌 것 걸러내기 — 걸린 것은 지우기 전에 목록으로 출력한다"""
    if not name:
        return "이름 없음"
    if re.search(r"[.!?]$", name):
        return "문장부호로 끝남"
    if len(name) >= 18:
        return "18자 이상"
    if name in cat_names:
        return "카테고리 이름과 같음"
    return None


def main():
    # 껍데기 확인 — 여기 적힌 곳으로만 간다
    shell = fetch("/")
    print("루트(%d바이트): %s" % (len(shell), shell.strip().replace("\n", " ")))

    html = decomment(fetch(MENU_PATH))
    print("원산지 %d건 · 알레르기 %d건 · 중량 %d건"
          % (html.count("원산지"), html.count("알레르기"), html.count("중량")))

    tabs = [(t, txt(b)) for t, b in RX_TAB.findall(html)]      # 화면 순서 그대로
    cat_names = [n for _, n in tabs]
    seg_by_id = {}
    parts = RX_SPLIT.split(html)
    for i in range(1, len(parts), 2):
        seg_by_id[parts[i]] = parts[i + 1]

    cats = []
    menus = []
    dropped = []
    for tid, cname in tabs:
        seg = seg_by_id.get(tid)
        if seg is None:
            print(f"⚠️ {tid} ({cname}) — 본문 블록이 없다")
            continue
        h2 = RX_H2.search(seg)
        cats.append({"name": cname, "parent": None, "ext_id": "#" + tid,
                     "title_raw": txt(h2.group(1)) if h2 else None})
        kept = 0
        cards = 0
        for li in RX_LI.findall(seg):
            n = RX_NAME.search(li)
            if not n:
                continue
            cards += 1
            name_en = txt(n.group(1))
            k = RX_NAME_KR.search(li)
            name_kr = txt(k.group(1)) if k else None
            name = name_kr or name_en
            why = reject_reason(name, cat_names)
            if why:
                dropped.append((cname, cards - 1, name, why))
                continue
            p = RX_PRICE.search(li)
            praw = raw_line(p.group(1)) if p else None
            d = RX_DESC.search(li)
            img = RX_IMG.search(li)
            bd = RX_BADGE.search(li)
            lk = RX_LINK.search(li)
            badge = (bd.group(1).strip() or None) if bd else None
            menus.append({
                "name": name,
                "name_en": name_en or None,
                "price": won(praw),
                "price_source": "official" if won(praw) else None,
                "price_note": ("화면 표기 「%s」 (W 14,9 = 14,900원 꼴). 값이 여럿이면 맨 앞 기본값" % praw)
                              if praw and won(praw) else None,
                "price_raw": praw,
                "compose_raw": txt(d.group(1)) if d else None,
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "badge_raw": badge,
                "detail_url": None,
                "buy_url": lk.group(1) if lk else None,
                "image_url": (BASE + img.group(1)) if img else None,
                "ext_id": None,
                "cats": [[cname, kept]],
            })
            kept += 1
        print(f"{tid} {cname:<20} 카드 {cards:>2} → 메뉴 {kept}")

    if not menus:
        print("❌ 메뉴 0개 — 저장하지 않는다")
        return 1

    data = {
        "brand": BRAND,
        "slug": SLUG,
        "source": BASE + MENU_PATH + "#tab1",
        "collected_at": COLLECTED,
        "origin_note": None,
        "origin_note_all": "공식 홈페이지에 원산지 표기가 없다 — 메뉴판·/sub/values.jsp·/sub/cs.jsp 에서 "
                           "「원산지」·「산지」 0건. values.jsp 의 「100일 이상 곡물 사료로 키운 블랙 앵거스 "
                           "비프 패티」 는 브랜드 설명이지 원산지 표기가 아니라 쓰지 않았다. 알레르기 표도 없다",
        "price_note_all": "판매가는 공식 홈페이지 메뉴판 공개값. 화면 표기가 「W 14,9」 꼴이라 14,900원으로 읽었다. "
                          "Single/Double·닭가슴살/닭다리살·6-count/10-count 는 세트가 아니라 같은 메뉴의 "
                          "옵션이라 줄을 쪼개지 않고 맨 앞 기본값을 price 에, 원문은 price_raw 에 담았다. "
                          "이 브랜드에는 「세트」 메뉴가 없다",
        "cats": cats,
        "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))

    print("\n버린 줄 %d개" % len(dropped))
    for c, i, n, why in dropped:
        print(f"    - [{c} #{i}] {n!r} — {why}")
    npar = sum(1 for c in cats if c["parent"])
    npr = sum(1 for m in menus if m["price"] is not None)
    nco = sum(1 for m in menus if m["compose_raw"])
    nor = sum(1 for m in menus if m["origin_raw"])
    print(f"\n✅ {OUT}")
    print(f"   카테고리 {len(cats)}개(하위 {npar}) · 메뉴 {len(menus)}개 · "
          f"가격 있는 것 {npr}개 · 구성 {nco}개 · 원산지 {nor}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
