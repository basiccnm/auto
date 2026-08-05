# -*- coding: utf-8 -*-
"""60계치킨(㈜장스푸드) 메뉴판 — 메뉴명·순서·원산지·알레르기. 2026-07-28

    python scripts/brand_60gye.py            # 미리보기
    python scripts/brand_60gye.py --write    # data/brand_menu_list/60gye.json 저장

⚠️ 파일명이 숫자로 시작해 `import brand_60gye` 가 안 된다. **실행 전용**이다.
⚠️ DB 를 import 하지 않는다. JSON 파일 한 장만 만든다.

구조 (실측 2026-07-28)
    http://www.60chicken.com/bbs/content.php?co_id=menu   ← 그누보드, 서버 렌더링
    한 페이지 안에 목록 48개 + 팝업 상세 48개가 **같이** 들어있다.

      <div class="btnlist"><ul>
        <li><div class="menu_tit row">
              <div class="col-sm-4 img"><img src="../theme/basic/img/sub/menu_img41.png"></div>
              <div class="col-sm-8 info">
                <p class="name">참지마라치킨<span> (뼈/순살)</span></p>
                <p class="text">…설명…</p>
                <a class="btn">DETAIL</a>

      <div class="popup">…같은 48개…<p class="stxt">[주요 알레르기 성분] …</p>

🔴 반드시 **주석을 먼저 걷어낸다.** 216개 주석 블록 안에 **죽은 메뉴 12개**가 들어있다
   (짜장계란치킨·육육치킨·장스치킨·짜장치킨·짜장치킨 순한맛·6초치킨·피자볼·
    똥집튀김 5종·크랑크랑소스). 주석을 안 지우면 판매 안 하는 메뉴가 섞여 들어온다.
   주석을 지운 뒤 남는 것이 정확히 48개 — 브라우저 렌더링으로도 48개 전부 보이는 걸 확인했다.

🔴 카테고리 탭이 **없다.** `cats=[]` 다 → `브랜드메뉴판등록방식.md` 대로 표준 탭 폴백이 걸린다.
   **없는 카테고리를 지어내지 않는다.**

   ⚠️ 이건 «한 번 훑고 못 찾았다» 가 아니라 **7가지 경로를 전부 확인한 결론**이다.
   다시 뒤지기 전에 아래를 읽어라 (2026-07-28 실측):

   ① GNB 드롭다운 …… 최상위 6개(메뉴/매장/가맹문의/보도자료/이벤트/고객센터)뿐. 2차 메뉴 없음.
      사이트 전체 co_id·bo_table = company·cs·faq·fran01·menu·news·qna·store — 메뉴 계열은 `menu` 하나다
   ② 햄버거(`#hash_menu`) … 브라우저로 실제로 열어봤다. 드로어는 `#hash-hash_menu` 에 그려진다.
      `mgnb_2dul`(2차) 자리가 **비어 있고** 아코디언 JS 는 통째로 `/* */` 주석 처리돼 있다.
      링크는 GNB 와 똑같은 6개. `plugin/hash/` 는 0바이트(robots.txt 가 /plugin/ 을 막는다)
   ③ 사이트맵 ………… `sitemap.xml` 404 · `co_id=sitemap` 은 «등록된 내용이 없습니다» · robots.txt 에 Sitemap 없음
      푸터는 관리자/원산지/알레르기/개인정보/이메일수집거부 5개뿐 — 메뉴 하위 항목 없음
   ④ 섹션 구분 ……… `.btnlist` 안은 **`<ul>` 하나에 `<li>` 48개가 연달아** 있다.
      `<li>` 를 전부 지우면 `<ul></ul>` 만 남는다. h1~h6 0개 · 구분선 0개 · 중간 제목 0개
   ⑤ 팝업 상세 ……… `<li class="row">` 뿐. `data-*` 속성 0개. 분류 필드 없음
   ⑥ 모바일(375×812) … 리사이즈해서 다시 열었다. PC 와 동일 — `<ul>` 1개 · `<li>` 48개 · `select` 0개.
      모바일 전용 탭 없음(반응형으로 숨는 건 빈 `tel` 과 «메인으로» 뿐)
   ⑦ 이미지 ………… 48장 전부 `alt=""`. 파일명은 `menu_img41.png`·`menu_img_kkk.jpg` 식이라 분류어가 없다.
      배경이미지·`::before` 로 들어간 카테고리 띠도 없다(전부 `none`)

   ⛔ 알레르기 표시판(`al.php` → `pop_al_260610.jpg`)에는 「분류」 칸이 있어 치킨/소스/안주/사이드로
      갈려 있다. **그건 메뉴판 화면이 아니고** `치킨 무`·`메이플시럽`·`토마토 케찹` 같은 비메뉴가
      섞여 있어 원본 탭으로 쓰지 않는다. 대표가 쓰라고 하면 그때 넣는다.

🔴 가격이 **사이트 어디에도 없다.** 목록·팝업 상세·홈 전부 0건.
   본문의 `1,000원` 6건은 전부 «소스추가시 1,000원» 이라는 설명문이라 메뉴 가격이 아니다.
   그래서 전 메뉴 `price=None`. 홈(`/`)에도 메뉴 목록이 없다(`#hash-menu` 는 햄버거 네비다).

원산지 — 팝업 이미지 한 장이 브랜드 공통이다 (사람이 눈으로 읽었다)
    http://www.60chicken.com/theme/basic/origin.php
      → <img src="…/theme/basic/img/60origin.jpg">   (2504×3532, CMYK)
    ⚠️ 메뉴 페이지 본문에도 원산지 한 줄이 있지만 **주석 처리돼 죽어 있다.** origin.php 가 정본이다.
    아래 ORIGIN_ROWS 는 그 이미지를 내려받아 6조각으로 잘라 `Read` 로 **사람이 눈으로 읽은 값**이다.
    ✅ 닭고기 전부위 **국내산** — 원가가 2배 갈리는 값이라 이게 이 수집의 핵심이다.

알레르기 — 두 곳에 있다
    ① 메뉴 페이지 팝업의 `<p class="stxt">` (메뉴별, 원문) ← 이걸 쓴다
    ② http://www.60chicken.com/theme/basic/al.php → pop_al_260610.jpg (이미지 표)
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "60계치킨"
SLUG = "60gye"
BASE = "http://www.60chicken.com"
MENU_URL = BASE + "/bbs/content.php?co_id=menu"
ORIGIN_URL = BASE + "/theme/basic/origin.php"
ORIGIN_IMG = BASE + "/theme/basic/img/60origin.jpg"
ALLERGY_IMG = BASE + "/theme/basic/img/pop_al_260610.jpg"
COLLECTED = "2026-07-28"

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
GAP = 1.5

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "brand_menu_list", "60gye.json")

# ── 원산지 표시판 (60origin.jpg) — 사람이 눈으로 읽은 값 ──────────────────────
# 이미지를 6조각으로 잘라 Read 툴로 직접 판독했다. 8행 전부 또렷하게 읽혔고
# 짐작으로 채운 칸은 없다. 원문 그대로 옮긴다.
ORIGIN_ROWS = [
    ("닭고기(전부위)", "치킨 및 근위튀김 전메뉴", "국내산"),
    ("돼지고기", "쫀도그, 튀김만두, 오돌뼈, 소시지&나쵸", "국내산"),
    ("소고기(차돌양지)", "차돌짬뽕", "외국산"),
    ("쌀", "간지치킨(누룽지)", "국내산과 외국산 섞음"),
    ("현미", "간지치킨(누룽지)", "국내산"),
    ("오징어", "진미튀김", "페루산"),
    ("오징어", "마른안주세트(맥반석오징어포)", "중국산"),
    ("노가리", "마른안주세트(노가리)", "러시아산"),
]
ORIGIN_NOTE = "[원산지 표시판] " + " / ".join(
    "%s - %s : %s" % r for r in ORIGIN_ROWS) + "  (출처: %s, 메뉴 이미지 판독)" % ORIGIN_IMG

# 표시판이 **이름을 직접 적은** 메뉴만 per-menu 로 내린다. 나머지는 origin_note 로만 둔다.
# (「치킨 전메뉴」처럼 묶인 표현을 내 맘대로 48개에 배분하지 않는다 — 그건 추측이다)
ORIGIN_BY_NAME = {
    "쫀도그": "돼지고기 : 국내산",
    "오돌뼈": "돼지고기 : 국내산",
    "소시지&나초": "돼지고기 : 국내산",
    "차돌짬뽕": "소고기(차돌양지) : 외국산",
    "간지치킨": "닭고기(전부위) : 국내산 / 쌀(누룽지) : 국내산과 외국산 섞음 "
                "/ 현미(누룽지) : 국내산",
    "근위튀김": "닭고기(전부위) : 국내산",
    "마른안주세트": "오징어(맥반석오징어포) : 중국산 / 노가리 : 러시아산",
}

RX_COMMENT = re.compile(r"<!--.*?-->", re.S)
# 목록은 `<li>`, 팝업은 `<li class="row">` 다 — 속성을 허용해야 팝업 48개가 다 잡힌다
# (`<li>` 로만 잡았을 때 팝업이 4개로 나와 알레르기가 통째로 비었다)
RX_LI = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
RX_NAME = re.compile(r'<p class="name">(.*?)</p>', re.S)
RX_SPAN = re.compile(r"(?is)<span>(.*?)</span>")
RX_TEXT = re.compile(r'<p class="text">(.*?)</p>', re.S)
RX_STXT = re.compile(r'<p class="stxt">(.*?)</p>', re.S)
RX_IMG = re.compile(r'<img[^>]+src="((?!.*pop_icon)[^"]+)"')

# 메뉴가 아닌 줄을 거르는 기준 (문장부호로 끝남 / 18자 이상 / 카테고리명과 동일)
BAD_TAIL = ".!?~,;:"
MAXLEN = 18


def strip_tags(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def get(url):
    r = urllib.request.Request(url, headers=HDRS)
    return urllib.request.urlopen(r, timeout=30).read().decode("utf-8", "replace")


def abs_url(src):
    if not src:
        return None
    if src.startswith("http"):
        return src
    return BASE + "/" + src.lstrip("./").lstrip("/") if not src.startswith("../") \
        else BASE + "/" + src[3:]


def blocks(html, cls):
    """`<div class="btnlist">` / `<div class="popup">` 안의 <li> 들."""
    i = html.find('class="%s"' % cls)
    if i < 0:
        return []
    j = html.find('class="popup"', i + 1) if cls == "btnlist" else len(html)
    return RX_LI.findall(html[i:j if j > 0 else len(html)])


def main():
    write = "--write" in sys.argv

    raw = get(MENU_URL)
    print("메뉴 페이지 %d bytes" % len(raw))
    n_comment = len(RX_COMMENT.findall(raw))
    html = RX_COMMENT.sub("", raw)                       # 🔴 주석 먼저 제거
    print("주석 블록 %d개 제거 → %d bytes" % (n_comment, len(html)))

    dead = [strip_tags(RX_SPAN.sub("", n)) for c in RX_COMMENT.findall(raw)
            for n in RX_NAME.findall(c)]
    if dead:
        # 목록·팝업 양쪽에 같은 이름이 주석돼 있어 중복이 난다 → 고유 이름으로 센다
        uniq = sorted(set(x for x in dead if x))
        print("  주석 안의 죽은 메뉴 %d종(버림): %s" % (len(uniq), ", ".join(uniq)))

    # 카테고리 — 화면에 하나도 없다. 지어내지 않는다.
    cats = []
    if re.search(r'class="[^"]*(tab|cate|category)', html, re.I):
        print("🔴 탭 비슷한 게 생겼다 — 화면 구조가 바뀌었다. 확인할 것")

    lis = blocks(html, "btnlist")
    pops = blocks(html, "popup")
    print("목록 <li> %d개 · 팝업 <li> %d개" % (len(lis), len(pops)))

    # 팝업에서 메뉴별 알레르기 원문
    allergy = {}
    for b in pops:
        n = RX_NAME.search(b)
        s = RX_STXT.search(b)
        if not n:
            continue
        nm = strip_tags(RX_SPAN.sub("", n.group(1)))
        a = strip_tags(s.group(1)) if s else None
        if a:
            a = re.sub(r"^\[주요 알레르기 성분\]\s*", "", a).strip()
        # 사이트가 「없음」을 '-' 로 적는다 → null 로 비운다
        if a in ("-", "", "•", "• -"):
            a = None
        if nm:
            allergy[nm] = a

    menus, dropped, seen = [], [], {}
    for pos, b in enumerate(lis):
        n = RX_NAME.search(b)
        if not n:
            continue
        rawname = n.group(1)
        opt = RX_SPAN.search(rawname)
        opt = strip_tags(opt.group(1)) if opt else None
        name = strip_tags(RX_SPAN.sub("", rawname))
        if not name:
            continue

        # 메뉴 아닌 줄 거르기 — 지우기 전에 반드시 목록으로 남긴다
        why = None
        if name[-1] in BAD_TAIL:
            why = "문장부호로 끝남"
        elif len(name) >= MAXLEN:
            why = "%d자 (>=%d)" % (len(name), MAXLEN)
        elif any(name == c["name"] for c in cats):
            why = "카테고리 이름과 같음"
        if why:
            dropped.append((name, why))
            continue

        img = RX_IMG.search(b)
        if name in seen:
            continue
        seen[name] = 1
        menus.append({
            "name": name,
            "price": None,                 # 사이트에 가격이 없다
            "price_source": "official",
            "price_note": None,
            "weight_raw": None,            # 중량 표기 없음
            "origin_raw": ORIGIN_BY_NAME.get(name),
            "allergy_raw": allergy.get(name),
            "detail_url": MENU_URL,        # 상세는 같은 페이지의 팝업이다
            "image_url": abs_url(img.group(1)) if img else None,
            "ext_id": None,
            "option_raw": opt,             # 「(뼈/순살)」 같은 화면 표기 원문
            "cats": [],
        })

    if dropped:
        print("\n⚠️ 길이·문장부호 규칙에 걸린 줄 %d개 — 지우기 전에 확인:" % len(dropped))
        for nm, why in dropped:
            print("    %-30s  %s" % (nm, why))

    if not menus:
        print("🔴 메뉴 0건 — 화면 구조가 바뀌었다. **저장하지 않는다.**")
        return

    time.sleep(GAP)
    try:
        og = get(ORIGIN_URL)
        if ORIGIN_IMG.split("/")[-1] not in og:
            print("⚠️ origin.php 의 이미지 이름이 바뀌었다 — 원산지를 다시 판독할 것")
        else:
            print("원산지 이미지 확인 OK (%s)" % ORIGIN_IMG.split("/")[-1])
    except Exception as e:
        print("⚠️ origin.php 확인 실패: %s" % e)

    doc = {
        "brand": BRAND, "slug": SLUG, "source": MENU_URL, "collected_at": COLLECTED,
        "origin_note": ORIGIN_NOTE,
        "cats": cats,
        "menus": menus,
    }

    n_price = sum(1 for m in menus if m["price"] is not None)
    n_al = sum(1 for m in menus if m["allergy_raw"])
    n_or = sum(1 for m in menus if m["origin_raw"])
    print("\n● %s — 카테고리 %d개 · 메뉴 %d개 · 가격 %d개 · 알레르기 %d · 원산지(개별) %d"
          % (BRAND, len(cats), len(menus), n_price, n_al, n_or))
    for m in menus[:6]:
        print("   %-22s %-10s %s" % (m["name"], m["option_raw"] or "",
                                     (m["allergy_raw"] or "")[:40]))

    if not write:
        print("\n(미저장 — --write 를 붙여라)")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("\n저장: %s" % OUT)


if __name__ == "__main__":
    main()
