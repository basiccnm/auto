# -*- coding: utf-8 -*-
"""
맘스터치(slug=momstouch) 전용 메뉴판 수집기 — JSON 만 만든다. DB 는 건드리지 않는다.

## 어떻게 뚫었나 (2026-07-28)
- `https://momstouch.co.kr/` 는 5.6KB **인트로 스플래시**다(메뉴 링크 없음).
  버튼이 `onclick="location.href='/home.php'"` 였다 → **`/home.php` 가 진짜 브랜드 홈**이다.
- `/home.php`(47KB) 의 GNB 에 메뉴 주소가 그대로 있었다: `/menu/new.php?s_sect1=CG00xx`.
- **SPA 가 아니라 평범한 PHP 서버렌더**다. 브라우저 없이 urllib 로 전부 읽힌다.
- 탭(상위 카테고리)은 메뉴 페이지의 `<nav class="nav-tabs">` 가 정본이다.
  ⚠️ GNB 드롭다운과 **순서가 다르고 항목도 다르다**(GNB 는 「또잇 치킨」을 끼워넣는다). 아래 §또잇 참고.
- 하위 카테고리는 nav-tabs 안 `<ul>` 에 `?s_sect1=X&s_sect2=Y` 로 들어 있다(버거·치킨·피자만 있다).
- 페이징이 있다(버거 3쪽·치킨 3쪽·사이드 2쪽). `<ul class="pagination">` 의 **href 를 그대로 따라간다**
  — 주소를 조립하지 않는다.
- 상세는 `javascript:go_view('N')` 이고, 함수 본문은 **`<!-- -->` 주석 안에 들어 있는 인라인 스크립트**다.
  🔴 그래서 주석을 먼저 걷어내면 go_view 가 사라진다. 이 스크립트는 **주석 제거 전 원문**에서 템플릿을 읽는다.
        function go_view(no){ location.href = "view.php?idx="+no+"&pageNo=1&...&s_sect1=CG0005&..."; }

## 🔴 가격 — 브랜드 홈페이지엔 없다. **자사 주문 사이트에 있다** (2026-07-28 추가)
`momstouch.co.kr` 의 메뉴 목록·상세에는 가격이 **한 건도** 없다. 그런데 가격은 다른 데서 나온다.

- 홈페이지 「맘스터치 APP」 버튼이 `newmomstouch.page.link/?link=https://online.momstouch.co.kr/` 였다
  → **`online.momstouch.co.kr` 이 자사 주문(스마트오더) 사이트**다.
- 폰에 깔린 APK(`kr.co.momstouch.moms`) 의 dex 문자열을 확인했다 — `online.momstouch.co.kr`(BASE_URL) ·
  `onlineapi.momstouch.co.kr`(API) 뿐이고 가격 로직이 없다. **앱은 이 웹을 감싼 WebView 껍데기**다.
  → 「앱 가격」과 「이 사이트 가격」은 같은 값이다(실제로 DB의 앱 수집값 129건과 숫자가 일치했다).
- 화면이 실제로 부르는 것:
      GET /product/productList          (서버렌더 · 인라인 `g_data` 에 JSON 이 통째로 들어 있다)
      GET /product/productDetail?prodCd=…   (세트 SKU · 옵션)
      GET /commonapi/ajax?apiUrl=…      (백엔드 프록시 — 매장 상세·쿠폰 등)
  🔴 **`/product/productList` 는 매장이 세션에 없으면 500** 이다. 쿠키 `storeCd` + `orderType` 이 필요하다.
     매장코드는 추측하지 않았다 — 화면(매장검색 「강남」)에서 나온 `E10295`(강남대성학원점)를 쓴다.
- 응답 필드를 `price·amt·prc·uprc` 로 훑었더니 가격 필드는 **`saleUprc` 하나뿐**이다
  (dineIn/takeOut 처럼 갈리는 필드가 없다).

### 이 값이 배달가인가? — 아니다
같은 매장에서 `orderType=pick`(픽업/스마트오더) 과 `orderType=dely`(배달) 로 각각 받아 108건을 대조했다.
**두 채널의 `saleUprc` 가 전부 같다(다른 항목 0건).** 즉 자사 채널은 단일가이고, 그 값이
「매장에서 받는 주문(픽업)」 가격과 같다 → **홀 매장가 기준으로 쓴다**.
(배민 등 외부 배달앱의 배달 전용가는 이 값과 다를 수 있으나 우리가 쓰는 값이 아니다.)

### 이름이 안 맞는 것은 비운다 — 계산도 추측도 하지 않는다
홈페이지 메뉴명과 주문사이트 상품명이 다르다(홈페이지는 규격을 합쳐 보여준다).
- **정확일치**(공백만 무시) → 채운다
- **후보가 딱 하나**(한쪽이 다른 쪽을 포함) → 채우되 `price_note` 에 **API 원문 상품명**을 남긴다
- **후보가 여럿**(케이준양념감자 중/대 처럼 규격이 갈림) → **비운다.** 후보와 각 가격을 `price_note` 에 적어
  사람이 고르게 한다
- **후보 없음** → 비운다
⛔ 세트=단품+2,500 으로 계산해 채우지 않는다. 세트도 주문사이트가 **자기 가격을 준다**(예: 치버세트 17,500).

## 원산지 · 알레르기 · 영양성분 = 전 메뉴 공통 **이미지 한 장씩**
상세페이지의 모달 3개는 메뉴가 달라도 URL 이 같다(6개 메뉴로 대조 확인).
  영양성분 /upload_file/delv_guide/1784766788-ZVIDP.png
  알레르기 /upload_file/delv_guide/1784766825-VTGTD.png
  원산지   /upload_file/delv_guide/1784766836-NBWLK.png
- **원산지 이미지는 진짜 원산지 표시판이 맞다**(내용을 눈으로 확인함). PNG 라 텍스트가 없어
  사람이 읽어 아래 ORIGIN_NOTE 에 **원문 그대로** 옮겼다(자동 OCR 아님).
- 메뉴별 `origin_raw` 는 표의 「제품명」에 **이름이 글자 그대로 있는 것만** 채운다(공백만 무시).
  ⚠️ 표의 이름이 사이트 메뉴명과 다른 경우가 많다(사이트 `어메이징매콤마요버거` ↔ 표 `어메이징매콤마요싸이버거`).
     비슷하다고 갖다 붙이지 않는다 — 못 맞춘 것은 실행할 때 목록으로 출력한다.
- **알레르기**는 20열짜리 점 매트릭스 이미지, **영양성분**은 총중량(g)까지 있는 표 이미지다.
  둘 다 150행 가까이 되고 한 칸만 틀려도 가짜 정보가 되므로 **값을 채우지 않았다.** 출처만 남긴다.
  (영양성분표에 총중량이 있으니 중량이 필요해지면 거기서 사람이 옮겨야 한다 — 자동 파싱 불가)

## 또잇(간편식) 을 왜 안 담았나
- GNB 드롭다운에는 「또잇 치킨」(`new.php?s_sect1=CG0045`)이 있지만 그 주소는 **상품 0건**이다.
- 실제 상품 3개는 `/menu/ttoeat.php` 에 있고, 이건 GNB 에서 「맘스터치 간편식」이라는
  **별도 항목**(프로모션·공지사항과 형제)으로 걸려 있다. 매장 메뉴판의 탭이 아니다.
- 메뉴 페이지의 nav-tabs 에도 없다 → **화면 그대로**를 지켜 담지 않는다. 매번 다시 확인하고 경고를 띄운다.

## 단품과 세트
이름을 다듬지 않는다. 「맘스세트」 탭과 「피자 > 피자 세트」 하위가 세트를 따로 진열한다.
상세의 `.menu-view-originalset`(h3 「세트구성」) 에 붙는 품목명을 `compose_raw` 에 원문 그대로 담는다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://momstouch.co.kr"
MENU = BASE + "/menu/new.php"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
GAP = 2.0  # 요청 간격(초) — 2초 이상
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "momstouch.json")
COLLECTED = "2026-07-28"

# nav-tabs 에 안 나오지만 GNB 에 있는 것 — 매번 상품이 생겼는지 확인만 한다(담지는 않는다)
PROBE = [("CG0045", MENU + "?s_sect1=CG0045"), ("ttoeat", BASE + "/menu/ttoeat.php?s_sect1=CG0045")]

# ── 자사 주문(스마트오더) 사이트 — 가격은 여기서만 나온다 ────────────────────
ORDER = "https://online.momstouch.co.kr"
ORDER_LIST = ORDER + "/product/productList"
# 매장코드는 추측하지 않는다. 화면(매장검색)에서 나온 실제 코드다.
ORDER_STORE = ("E10295", "강남대성학원점", "서울 강남구 강남대로78길 33")
ORDER_TYPES = ("pick", "dely")  # 픽업(매장수령) · 배달 — 값이 같은지 매번 대조한다

ORIGIN_SRC = BASE + "/upload_file/delv_guide/1784766836-NBWLK.png"
ALLERGY_SRC = BASE + "/upload_file/delv_guide/1784766825-VTGTD.png"
NUTRI_SRC = BASE + "/upload_file/delv_guide/1784766788-ZVIDP.png"

# ── 원산지 표시판 (PNG) 원문 ────────────────────────────────────────────────
# 사람이 이미지를 확대해 옮겨 적은 것이다. 표 순서·표기를 그대로 둔다.
ORIGIN_ROWS = [
    # (원료명, 구분, 원산지, [제품명 …])
    ("닭고기", None, "국내산", [
        "핫치즈밤 치킨", "핫치즈밤 와우순살", "핫치즈밤 와우순살맥스", "골든갈릭 치킨",
        "골든갈릭 와우순살", "골든갈릭 와우순살맥스", "핫치즈 치킨", "핫치즈 와우순살",
        "핫치즈 와우순살맥스", "후라이드 치킨", "후라이드 와우순살", "후라이드 와우순살맥스",
        "맘스양념치킨", "맘스양념 와우순살", "맘스양념 와우순살맥스", "간장마늘치킨",
        "간장마늘 와우순살", "간장마늘 와우순살맥스", "반반치킨", "후라이드통다리",
        "언빌리버블버거", "딥치즈버거", "휠렛버거", "마살라버거", "화이트갈릭버거",
        "할라피뇨너겟", "케이준떡강정", "치파오떡강정", "간장마늘떡강정", "닭강정트리오",
        "와우스모크디럭스버거", "셰프스 버번 치킨", "셰프스 버번 와우순살",
        "셰프스 버번 와우순살맥스", "셰프스 크림디종 치킨", "셰프스 크림디종 와우순살",
        "셰프스 크림디종 와우순살맥스", "후덕죽 치킨", "후덕죽 와우순살",
        "후덕죽 와우순살맥스", "치킨치즈스틱", "치즈스낵업", "트리플스낵업",
        "매직퐁 치킨", "매직퐁 와우순살", "매직퐁 와우순살맥스",
        "갓빠삭 치킨", "갓빠삭 와우순살", "갓빠삭 와우순살맥스",
    ]),
    ("닭고기", None, "브라질산, 태국산 (제주지역: 브라질산)", [
        "골든갈릭 빅싸이순살", "골든갈릭 빅싸이순살맥스", "핫치즈밤 빅싸이순살",
        "핫치즈밤 빅싸이순살맥스", "후라이드 빅싸이순살", "후라이드 빅싸이순살맥스",
        "맘스양념 빅싸이순살", "맘스양념 빅싸이순살맥스", "간장마늘 빅싸이순살",
        "간장마늘 빅싸이순살맥스", "핫치즈 빅싸이순살", "핫치즈빅싸이순살맥스",
        "셰프스 버번 빅싸이순살", "셰프스 버번 빅싸이순살맥스", "셰프스 크림디종 빅싸이순살",
        "셰프스 크림디종 빅싸이순살맥스", "후덕죽빅싸이순살", "후덕죽 빅싸이순살맥스",
        "싸이버거", "불싸이버거", "싸이플렉스버거", "화이트갈릭싸이버거", "딥치즈싸이버거",
        "쉬림프싸이플렉스버거", "아라비아따치즈버거", "셰프스 베이컨 싸이버거",
        "셰프스 K 싸이버거", "후덕죽싸이버거", "한라봉싸이버거", "매직퐁 싸이버거",
        "매직퐁 빅싸이순살", "매직퐁 빅싸이순살맥스", "어메이징매콤마요싸이버거",
        "갓빠삭 빅싸이순살", "갓빠삭 빅싸이순살맥스", "내슈빌핫치킨버거",
    ]),
    ("닭고기", None, "국내산, 브라질산", ["팝콘볼"]),
    ("닭고기", None, "브라질산", ["슈퍼싸이더블KICK"]),
    ("불고기패티", "쇠고기 / 돼지고기 / 닭고기", "호주산 / 국내산 / 국내산",
     ["디럭스불고기버거", "불고기버거", "새우불고기버거"]),
    ("햄", "닭고기 / 돼지고기", "국내산", ["화이트갈릭버거", "화이트갈릭싸이버거"]),
    ("비프패티", "쇠고기", "호주산",
     ["그릴드비프버거", "그릴드더블비프버거", "비프스테이크버거",
      "셰프스 베이컨 비프버거", "셰프스 K 비프버거", "매직퐁 비프버거"]),
    ("미트패티", "돼지고기 / 쇠고기 / 닭고기", "국내산", ["시그니처불고기버거"]),
    ("쿡베이컨", "돼지고기", "스페인산", ["셰프스 K 싸이버거", "셰프스 K 비프버거"]),
    ("베이컨토핑", "돼지고기 / 돼지지방", "외국산 / 국내산",
     ["셰프스 베이컨 싸이버거", "셰프스 베이컨 비프버거"]),
]
ORIGIN_FOOT = "※ 비프 메뉴, 미트 패티 메뉴는 일부 매장에서만 판매합니다."


def origin_note_text():
    L = ["원산지 표시판  [배포일자 : 2026. 07. 23 (N) / 맘스터치]",
         "원료명 | 구분 | 원산지 | 제품명"]
    for nm, gu, org, prods in ORIGIN_ROWS:
        L.append("%s | %s | %s | %s" % (nm, gu or "", org, ", ".join(prods)))
    L.append(ORIGIN_FOOT)
    L.append("출처(이미지) : " + ORIGIN_SRC)
    return "\n".join(L)


def nrm(s):
    """공백만 지운 비교용 키. 글자는 바꾸지 않는다."""
    return re.sub(r"\s+", "", s or "")


ORIGIN_INDEX = {}
for _nm, _gu, _org, _prods in ORIGIN_ROWS:
    for _p in _prods:
        ORIGIN_INDEX.setdefault(nrm(_p), []).append(
            "%s%s : %s" % (_nm, (" (%s)" % _gu) if _gu else "", _org))


# ── HTTP ────────────────────────────────────────────────────────────────────
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        h = r.read().decode("utf-8", "replace")
    time.sleep(GAP)
    return h


def strip_comments(h):
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(s):
    """textContent 기준 — 태그 제거 + 엔티티 해제 + 공백 정리."""
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()


def money(s):
    m = re.search(r"([\d,]{3,})\s*원", s)
    return int(m.group(1).replace(",", "")) if m else None


# ── 목록 ────────────────────────────────────────────────────────────────────
def tabs(html):
    """메뉴 페이지의 nav-tabs — 상위 탭 **순서**(화면 그대로).
    🔴 하위 카테고리 <ul> 은 **그 탭이 current 일 때만** 렌더된다 → 여기서는 안 나온다.
       하위는 각 카테고리 페이지에서 subs_of() 로 따로 읽는다."""
    nav = re.search(r'<nav class="nav-tabs">(.*?)</nav>', html, re.S)
    if not nav:
        return []
    return [(sid, txt(lab)) for sid, lab in
            re.findall(r'<a href="new\.php\?s_sect1=([A-Za-z0-9]+)">(.*?)</a>', nav.group(1), re.S)]


def subs_of(html):
    """그 카테고리 페이지의 nav-tabs 안 하위 링크. 「전체」(s_sect2 없음)는 하위가 아니다."""
    nav = re.search(r'<nav class="nav-tabs">(.*?)</nav>', html, re.S)
    if not nav:
        return []
    out = []
    for s1, s2, lab in re.findall(
            r'new\.php\?s_sect1=([A-Za-z0-9]+)&s_sect2=([A-Za-z0-9]+)">(.*?)</a>', nav.group(1), re.S):
        if (s2, txt(lab)) not in out:
            out.append((s2, txt(lab)))
    return out


def parse_items(html):
    """menu-list 안의 li → 이름·설명·이미지·idx."""
    ml = re.search(r'<div class="menu-list">(.*?)</div>', html, re.S)
    if not ml:
        return []
    items = []
    for li in re.findall(r"<li>(.*?)</li>", ml.group(1), re.S):
        idx = re.search(r"go_view\('(\d+)'\)", li)
        h3 = re.search(r"<h3>(.*?)</h3>", li, re.S)
        if not h3:
            continue
        raw = h3.group(1)
        eng = re.search(r"<span>(.*?)</span>", raw, re.S)
        name = txt(re.sub(r"<span>.*?</span>", "", raw, flags=re.S))
        img = re.search(r"background-image:\s*url\('([^']+)'\)", li)
        sub = re.search(r'<p class="sub-text">(.*?)</p>', li, re.S)
        items.append({
            "name": name,
            "eng": txt(eng.group(1)) if eng else None,
            "sub": txt(sub.group(1)) if sub else None,
            "idx": idx.group(1) if idx else None,
            "img": urllib.parse.urljoin(BASE, img.group(1)) if img else None,
        })
    return items


def next_pages(html, cur_url):
    """pagination 의 href 를 그대로 돌려준다 — 주소를 조립하지 않는다."""
    pg = re.search(r'<ul class="pagination">(.*?)</ul>', html, re.S)
    if not pg:
        return []
    return [urllib.parse.urljoin(cur_url, unescape(h))
            for h in re.findall(r'<a href="([^"]+)"', pg.group(1))]


def view_tpl(raw_html):
    """go_view 는 <!-- --> 주석 안에 있다 → 주석 제거 **전** 원문에서 읽는다."""
    m = re.search(r'function go_view\(no\)\s*\{\s*location\.href\s*=\s*"([^"]*)"\s*\+\s*no\s*\+\s*"([^"]*)"',
                  raw_html)
    return (m.group(1), m.group(2)) if m else None


def collect_list(url):
    """한 카테고리(또는 하위)의 전 페이지를 순서대로 모은다."""
    raw = get(url)
    tpl = view_tpl(raw)
    h = strip_comments(raw)
    items = parse_items(h)
    seen = {url}
    for nx in next_pages(h, url):
        if nx in seen:
            continue
        seen.add(nx)
        raw2 = get(nx)
        items += parse_items(strip_comments(raw2))
    return raw, h, items, tpl


# ── 상세 ────────────────────────────────────────────────────────────────────
def detail(url):
    h = strip_comments(get(url))
    sec = re.search(r'<div class="menu-view-detail">(.*?)</div>\s*</div>\s*</div>', h, re.S)
    seg = sec.group(1) if sec else h
    name = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    typ = re.search(r'<p class="type">(.*?)</p>', seg, re.S)
    desc = re.search(r'<p class="description">(.*?)</p>', seg, re.S)
    img = re.search(r'<figure><img src="([^"]+)"', seg)
    # 세트구성
    comp = None
    box = re.search(r'<div class="menu-view-originalset[^"]*">(.*?)</div>\s*</div>\s*</div>', h, re.S)
    if box:
        head = re.search(r"<h3>(.*?)</h3>", box.group(1), re.S)
        parts = [txt(x) for x in re.findall(r"<h4>(.*?)</h4>", box.group(1), re.S)]
        parts = [p for p in parts if p]
        if parts:
            comp = "%s: %s" % (txt(head.group(1)) if head else "세트구성", ", ".join(parts))
    # 모달 이미지 (전 메뉴 공통인지 확인용)
    mods = {}
    for kind in ("nutrition", "allergy", "origin"):
        m = re.search(r'<div class="modal %s" id="modal-%s">(.*?)<button' % (kind, kind), h, re.S)
        im = re.search(r'<img src="([^"]+)"', m.group(1)) if m else None
        mods[kind] = im.group(1) if im else None
    return {
        "name": txt(name.group(1)) if name else None,
        "type": txt(typ.group(1)) if typ else None,
        "desc": txt(desc.group(1)) if desc else None,
        "image": urllib.parse.urljoin(BASE, img.group(1)) if img else None,
        "compose": comp,
        "price": money(txt(seg)),   # 사이트에 가격이 생기면 잡히도록 열어둔다
        "mods": mods,
    }


# ── 가격 (자사 주문 사이트) ─────────────────────────────────────────────────
def order_products(order_type):
    """/product/productList 의 인라인 g_data 를 그대로 읽는다.
    🔴 쿠키에 매장이 없으면 500 이다. 주소를 조합해 API 를 찌르지 않는다 — 화면이 쓰는 이 경로만."""
    hdr = dict(UA)
    hdr["Cookie"] = "storeCd=%s; orderType=%s" % (ORDER_STORE[0], order_type)
    req = urllib.request.Request(ORDER_LIST, headers=hdr)
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read().decode("utf-8", "replace")
    time.sleep(GAP)
    m = re.search(r"g_data = '(.*?)';", b, re.S)
    if not m:
        return None
    return json.loads(m.group(1))["data"]["result"]["productList"]


def price_fields(obj, out=None, path=""):
    """가격으로 보이는 필드를 부분 문자열로 재귀 검색 — 채널이 갈리는 필드가 있는지 확인용."""
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if re.search(r"price|uprc|prc|amt", k, re.I) and not isinstance(v, (dict, list)):
                out[k] = out.get(k, 0) + 1
            price_fields(v, out, path + "/" + k)
    elif isinstance(obj, list):
        for v in obj[:40]:
            price_fields(v, out, path)
    return out


def attach_prices(menus, warn):
    chans = {}
    for ot in ORDER_TYPES:
        try:
            chans[ot] = order_products(ot)
        except Exception as e:
            warn.append("주문사이트 %s 조회 실패: %s" % (ot, e))
    if not chans.get("pick"):
        warn.append("주문사이트에서 상품을 못 받았다 — 가격을 채우지 않는다")
        return 0, [], []

    P = chans["pick"]
    print("\n[가격] 주문사이트 %s(%s) · 상품 %d건" % (ORDER_STORE[1], ORDER_STORE[0], len(P)))
    print("       가격 필드: %s" % price_fields(P))

    # 픽업 vs 배달 — 값이 갈리면 홀가가 아니므로 멈춘다
    same = True
    if chans.get("dely"):
        d = {p["prodNm"]: p["saleUprc"] for p in chans["dely"]}
        diff = [(p["prodNm"], p["saleUprc"], d[p["prodNm"]])
                for p in P if p["prodNm"] in d and p["saleUprc"] != d[p["prodNm"]]]
        if diff:
            same = False
            warn.append("픽업≠배달 가격이 %d건 — 어느 쪽이 홀가인지 확인 전까지 채우지 않는다" % len(diff))
            for x in diff[:10]:
                warn.append("   %s 픽업%s / 배달%s" % x)
        else:
            print("       픽업 == 배달 (다른 항목 0건) → 자사 채널 단일가 = 매장가")
    if not same:
        return 0, [], []

    by = {}
    for p in P:
        by.setdefault(nrm(p["prodNm"]), []).append(p)

    filled, ambiguous, absent = 0, [], []
    src = "%s (매장 %s %s · orderType=pick)" % (ORDER_LIST, ORDER_STORE[0], ORDER_STORE[1])
    for m in menus.values():
        k = nrm(m["name"])
        exact = by.get(k)
        if exact:
            p = exact[0]
            m["price"] = p["saleUprc"]
            m["price_source"] = "official_smartorder"
            m["price_note"] = "자사 주문(스마트오더) saleUprc · prodCd=%s · 상품명 «%s» · %s" % (
                p["prodCd"], p["prodNm"], src)
            filled += 1
            continue
        cand = [p for p in P if k in nrm(p["prodNm"]) or nrm(p["prodNm"]) in k]
        if len(cand) == 1:
            p = cand[0]
            m["price"] = p["saleUprc"]
            m["price_source"] = "official_smartorder"
            m["price_note"] = ("자사 주문(스마트오더) saleUprc · prodCd=%s · ⚠️ 이름이 완전히 같지 않다 — "
                               "API 원문 상품명 «%s» · %s" % (p["prodCd"], p["prodNm"], src))
            filled += 1
        elif len(cand) > 1:
            lst = ", ".join("%s %s원" % (p["prodNm"], format(p["saleUprc"], ",")) for p in cand)
            m["price_note"] = ("⚠️ 규격이 갈려 자동으로 못 고른다 — 사람이 고를 것. 후보: %s · %s"
                               % (lst, src))
            ambiguous.append((m["name"], lst))
        else:
            m["price_note"] = "자사 주문(스마트오더) 상품 목록에 같은 이름이 없다 · " + src
            absent.append(m["name"])
    return filled, ambiguous, absent


# ── 메뉴가 아닌 것 ──────────────────────────────────────────────────────────
def sentence_check(n, cat_names, has_idx):
    hit = None
    if not n:
        return "이름 없음", True
    if n in cat_names:
        hit = "카테고리 이름과 동일"
    elif len(n) >= 18:
        hit = "18자 이상"
    elif n.endswith(("?", "!", ".", "다", "요", "니다")):
        hit = "문장부호/종결어미로 끝남"
    if hit and has_idx:
        return hit + " → 상세페이지가 있어 **살림**", False
    return (hit, True) if hit else (None, False)


def main():
    top = collect_list(MENU + "?s_sect1=new")
    tab_list = tabs(top[1])
    if not tab_list:
        print("nav-tabs 를 못 읽었다 — 중단")
        return 1

    cats, menus, dropped, kept, warn = [], {}, [], [], []

    # ── 1차: 카테고리 페이지를 훑어 하위 카테고리와 목록을 모은다 ──
    plan = []   # (sid, nm, [(경로, items, tpl) …])
    for sid, nm in tab_list:
        url = MENU + "?s_sect1=" + sid
        raw, h, items, tpl = (top if sid == "new" else collect_list(url))
        subs = subs_of(h)
        print("[cat] %-8s %-6s 기본 %2d건  하위 %d" % (sid, nm, len(items), len(subs)))
        groups = [(nm, items, tpl)]
        subcats = []
        for s2, lab in subs:
            subcats.append((s2, lab))
            surl = "%s?s_sect1=%s&s_sect2=%s" % (MENU, sid, s2)
            _, _, sitems, stpl = collect_list(surl)
            print("   [sub] %-10s %2d건" % (lab, len(sitems)))
            groups.append(("%s/%s" % (nm, lab), sitems, stpl or tpl))
        plan.append((sid, nm, subcats, groups))

    cat_names = {nm for _, nm in tab_list}
    for _, _, subcats, _ in plan:
        cat_names |= {lab for _, lab in subcats}

    # ── 2차: 카테고리·메뉴로 쌓는다 (상위를 먼저, 그 뒤 자식) ──
    for sid, nm, subcats, groups in plan:
        cats.append({"name": nm, "parent": None, "ext_id": sid})
        for s2, lab in subcats:
            cats.append({"name": lab, "parent": nm, "ext_id": "%s&%s" % (sid, s2)})

        for path, its, t in groups:
            pos = 0
            for it in its:
                why, drop = sentence_check(it["name"], cat_names, bool(it["idx"]))
                if drop:
                    dropped.append((path, it["name"], why))
                    continue
                if why:
                    kept.append((path, it["name"], why))
                durl = None
                if it["idx"] and t:
                    durl = urllib.parse.urljoin(BASE + "/menu/", t[0] + it["idx"] + t[1])
                m = menus.setdefault(it["name"], {
                    "name": it["name"], "price": None, "price_source": None, "price_note": None,
                    "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": durl, "image_url": it["img"], "ext_id": it["idx"], "cats": [],
                })
                m["cats"].append([path, pos])
                if not m["image_url"]:
                    m["image_url"] = it["img"]
                if not m["detail_url"]:
                    m["detail_url"] = durl
                pos += 1

    # 담지 않기로 한 곳 — 매번 확인
    for tag, u in PROBE:
        its = parse_items(strip_comments(get(u)))
        if tag == "CG0045" and its:
            warn.append("new.php?s_sect1=CG0045 (또잇 치킨) 에 상품 %d건이 생겼다 — 탭 추가 검토" % len(its))
        elif tag == "ttoeat":
            print("\n[probe] ttoeat.php(맘스터치 간편식) %d건 — 메뉴판 탭이 아니라 담지 않음: %s"
                  % (len(its), ", ".join(x["name"] for x in its)))
        else:
            print("[probe] %s 0건 — 담지 않음" % tag)

    # 상세
    print("\n[detail] %d건" % len(menus))
    modset = {"nutrition": set(), "allergy": set(), "origin": set()}
    npx = 0
    for n, m in menus.items():
        if not m["detail_url"]:
            warn.append("«%s» 상세주소 없음" % n)
            continue
        d = detail(m["detail_url"])
        m["compose_raw"] = d["compose"]
        if d["image"]:
            m["image_url"] = d["image"]
        if d["price"]:
            m["price"] = d["price"]
            m["price_source"] = "official"
            npx += 1
            warn.append("«%s» 에 가격 %s 이 생겼다 — 사이트가 가격을 공개하기 시작한 것" % (n, d["price"]))
        for k in modset:
            modset[k].add(d["mods"][k])
        if d["name"] and nrm(d["name"]) != nrm(n):
            warn.append("목록명 «%s» ≠ 상세명 «%s» (idx=%s)" % (n, d["name"], m["ext_id"]))
        print("   %-30s %s" % (n, ("구성: " + d["compose"]) if d["compose"] else ""))

    for k, v in modset.items():
        if len(v) > 1:
            warn.append("%s 모달 이미지가 메뉴마다 다르다(%d종) — 공통 한 장 가정이 깨졌다" % (k, len(v)))

    # 원산지 — 표에 이름이 글자 그대로 있는 것만
    hit = miss = 0
    for n, m in menus.items():
        rows = ORIGIN_INDEX.get(nrm(n))
        if rows:
            m["origin_raw"] = " / ".join(rows)
            hit += 1
        else:
            miss += 1

    # 가격 — 자사 주문 사이트
    npx, ambiguous, absent = attach_prices(menus, warn)
    if ambiguous:
        print("\n[가격 못 채움 — 규격이 갈림] %d개 (사람이 고를 것)" % len(ambiguous))
        for n, lst in ambiguous:
            print("   %-22s %s" % (n, lst))
    if absent:
        print("\n[가격 못 채움 — 주문사이트에 없음] %d개" % len(absent))
        for n in absent:
            print("   " + n)

    if kept:
        print("\n[규칙에 걸렸지만 살린 줄] %d개" % len(kept))
        for p, n, w in kept:
            print("   %-18s %-28s %s" % (p, n, w))
    if dropped:
        print("\n[걸러낸 줄] %d개 — 지우기 전에 확인할 것" % len(dropped))
        for p, n, w in dropped:
            print("   %-18s %-28s %s" % (p, n, w))
    else:
        print("\n[걸러낸 줄] 없음")
    print("\n[원산지] 표시판과 이름이 일치 %d개 · 불일치 %d개" % (hit, miss))
    for n, m in menus.items():
        if not m["origin_raw"]:
            print("   (원산지 못 붙임) " + n)
    for w in warn:
        print("⚠️ " + w)

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다.")
        return 1

    out = {
        "brand": "맘스터치",
        "slug": "momstouch",
        "source": MENU + "?s_sect1=CG0005",
        "price_source_url": ORDER_LIST,
        "collected_at": COLLECTED,
        "price_note_all":
            "골격(카테고리·메뉴명·순서)은 브랜드 홈페이지 momstouch.co.kr/menu/new.php 에서 받았다 — "
            "여기엔 가격이 한 건도 없다. 가격은 자사 주문(스마트오더) 사이트 "
            + ORDER_LIST + " 의 인라인 g_data `saleUprc` 다. 매장 " + ORDER_STORE[0] + " "
            + ORDER_STORE[1] + "(" + ORDER_STORE[2] + ") 기준. "
            "같은 매장에서 orderType=pick(픽업/매장수령) 과 dely(배달) 를 대조해 108건 전부 값이 같음을 "
            "확인했다 → 배달 할증이 없는 자사 단일가이므로 홀 매장가로 쓴다. "
            "가격 필드는 saleUprc 하나뿐이다(dineIn/takeOut 처럼 갈리는 필드 없음). "
            "맘스터치 앱은 이 사이트를 감싼 WebView 라 앱 가격도 같은 값이다. "
            "⛔ 세트=단품+2,500 으로 계산한 값은 하나도 없다 — 세트도 주문사이트가 준 값이다. "
            "매장·시기에 따라 가격은 달라질 수 있다.",
        "origin_note": origin_note_text(),
        "origin_source": ORIGIN_SRC,
        "allergy_note": "알레르기 유발식품 표시는 이미지(PNG) 한 장 — 20열 점 매트릭스라 자동 판독하지 않았다. "
                        "배포일자 2026. 07. 20. 출처 : " + ALLERGY_SRC,
        "weight_note": "총중량(g)은 영양성분 표시 이미지(PNG)에 있다. 표가 이미지라 자동으로 못 읽어 "
                       "weight_raw 를 비워뒀다. 배포일자 2026. 07. 20. 출처 : " + NUTRI_SRC,
        "cats": cats,
        "menus": [menus[k] for k in menus],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n저장: %s\n  카테고리 %d(하위 %d) · 메뉴 %d · 가격 %d · 구성 %d · 원산지 %d"
          % (OUT, len(cats), sum(1 for c in cats if c["parent"]), len(out["menus"]),
             sum(1 for m in out["menus"] if m["price"]),
             sum(1 for m in out["menus"] if m["compose_raw"]),
             sum(1 for m in out["menus"] if m["origin_raw"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
