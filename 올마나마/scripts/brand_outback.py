# -*- coding: utf-8 -*-
"""
아웃백스테이크하우스 (slug: outback) 메뉴판 수집 — 공식 홈페이지 전용 수집기

⛔ DB 를 import 하지 않는다. 결과는 data/brand_menu_list/outback.json 한 장뿐이다.
   (brands 테이블에 아직 아웃백 행이 없다. 적재는 나중에 따로 한다)

────────────────────────────────────────────────────────────────────────
뚫은 길 — ② 홈페이지 (앱 경로는 쓰지 않았다)
────────────────────────────────────────────────────────────────────────
공식 사이트: https://www.outback.co.kr/          (WebSearch 로 확인)
모바일 미러 : https://m.outback.co.kr/            (같은 CMS, 같은 값)

메뉴 카테고리는 홈 GNB 의 「MENU」 드롭다운에 그대로 적혀 있다.
  /main.do?menuIdx=<카테고리>          ← 카테고리 한 장 (목록 + 재료 + 가격)
  /menu/productView.do?menuIdx=43&cateIdx=<c>&pdtIdx=<p>   ← 상세(목록과 같은 값, 추가정보 없음)
  /menu/productList.do?menuIdx=43&cateIdx=<c>              ← 목록의 다른 주소

⚠️ HTML 주석 안에 **가짜 예시 가격**(138,900원 / 38,900원)이 통째로 들어있다.
   주석을 먼저 걷어내지 않으면 전부 오염된다.  → strip_comments()

⚠️ 페이징 없음. 카테고리 한 장에 그 카테고리 전부가 들어온다.

⚠️ 카테고리 4곳(NEW MENU · BEVERAGES＆ALCOHOL · SIDES＆ADD ON MATES · DESSERTS)은
   본문이 **이미지 한 장**이다. HTML 에 글자가 없다. 그래서 그 4곳만
   사람이 이미지를 판독한 결과를 아래 IMAGE_CATS 에 그대로 적어뒀다.
   판독한 이미지 주소는 각 항목의 src 에 남겼다 — 다시 확인할 수 있다.

────────────────────────────────────────────────────────────────────────
가격 — 홀 매장가
────────────────────────────────────────────────────────────────────────
· 사이트가 「DELIVERY」를 **별도 카테고리**로 따로 두고 거기서만 배달 가격을 낸다.
  그래서 DELIVERY 밖의 값은 전부 매장(홀) 가격이다.
· 각 메뉴 페이지 NOTICE: "모든 메뉴 가격은 부가세가 포함된 금액입니다."
· 「LUNCH SET」도 사이트가 따로 둔 런치 전용 카테고리다. 단품과 섞지 않았다.
· DELIVERY 메뉴에는 price_source="official_delivery" 로 표시해 뒀다.

스테이크는 중량·부위별로 사이트가 이름을 따로 붙여 놨다(`달링 포인트 스트립 420g`).
합치지 않고 사이트 표기 그대로 쓴다. 한 상품에 라벨 붙은 가격이 여럿이면
(`커플 세트`/`패밀리 세트`, `Glass`/`Bottle`, `토마호크 100g 당`) **각각 다른 메뉴**로 쪼갠다.
"""
import sys
import os
import re
import json
import html
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.outback.co.kr"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "brand_menu_list", "outback.json")
COLLECTED_AT = "2026-07-28"

# 홈 GNB 「MENU」 드롭다운 순서 그대로. (menuIdx, 화면에 적힌 이름, 그 카테고리의 cateIdx)
NAV = [
    (678, "NEW MENU", 73),
    (672, "BLACK LABEL SIZZLING EDITION", None),
    (665, "EASY PICK", 64),
    (338, "BEVERAGES ＆ ALCOHOL", 53),
    (339, "APPETIZERS ＆ SALADS", 54),
    (340, "SIZZLING BONE-IN STEAK", 55),
    (333, "BLACK LABEL CHEF EDITION", 52),
    (341, "SPECIAL STEAKS ＆ BACK RIBS", 57),
    (342, "SIDES ＆ ADD ON MATES", 58),
    (343, "PASTA ＆ RICE", 59),
    (344, "DESSERTS", 60),
    (257, "WINES", 38),
    (224, "LUNCH SET", 24),
    (244, "DELIVERY", 26),
]

# 한 장짜리 상품 페이지(목록이 아니라 상품 하나가 카테고리 전체인 곳)
SINGLE_PAGES = {340, 672}

# h3 섹션이 하나뿐이면 하위 카테고리로 만들지 않는다(화면에도 탭이 안 그려진다).
# `SET MENU`·`LUNCH SET상단 공통 영역` 처럼 CMS 내부 라벨인 경우가 있어서다.
# ⚠️ 단 섹션이 여럿이면 `SET MENU` 도 진짜 섹션이다 — DELIVERY 가 그렇다.

# 브랜드 공통 원산지 안내 — 메뉴 페이지 NOTICE 원문
ORIGIN_NOTE = "메뉴별 자세한 원산지 정보는 매장 내 아웃백 대표 원산지 표시판 참고 부탁드립니다."


# ──────────────────────────────────────────────────────────────
# 이미지 카테고리 4곳 — 사람이 이미지를 판독한 결과 (2026-07-28)
#   name / price / compose(설명 원문) / origin(대괄호 원산지 원문) / note(라벨)
#   ⚠️ 지어낸 값 없음. 이미지에 적혀 있지 않은 칸은 비워 뒀다.
# ──────────────────────────────────────────────────────────────
IMAGE_CATS = {
    678: {  # NEW MENU — https://www.outback.co.kr/upload/editor/20260702/20260702235102669182.png
        "src": "/upload/editor/20260702/20260702235102669182.png",
        "sections": [(None, [
            {"name": "허니 자몽 티 스파클링", "price": None,
             "compose": "곰돌이 푸가 사랑하는 달콤한 허니와 상큼한 자몽, 청량함 어우러진 리프레싱 티 스파클링"},
            {"name": "허니 크런치 오지 치즈 후라이즈", "price": None,
             "compose": "곰돌이 푸가 사랑하는 달콤한 허니에 월넛 캔디의 바삭한 식감까지 더한 아웃백 대표 메뉴 오지 치즈 후라이즈"},
            {"name": "허니 크런치 쿠카부라 윙", "price": None,
             "compose": "곰돌이 푸가 사랑하는 허니의 달콤함과 간장의 짭조름한 풍미, 월넛 캔디의 바삭한 식감까지 더한 기간 한정 치킨 윙",
             "origin": "[닭고기, 국내산]"},
            {"name": "허니 크런치 베이비 백 립", "price": None,
             "compose": "곰돌이 푸가 사랑하는 달콤한 허니 글레이즈와 바삭한 크런치 텍스처를 더한 아웃백 시그니처 베이비 백 립",
             "origin": "[폭립, 돼지고기, 외국산, 500g]"},
            {"name": "허니콤 썬더 프롬 골든 원더", "price": None,
             "compose": "곰돌이 푸가 사랑하는 벌집꿀이 통째로 올라간 썬더. 진한 브라우니와 부드러운 아이스크림, 슈가 캔디 크런치가 어우러진 풍부한 텍스처의 기간 한정 디저트"},
        ])],
    },
    338: {  # BEVERAGES ＆ ALCOHOL — /upload/editor/20260401/20260401004144030105.png
        "src": "/upload/editor/20260401/20260401004144030105.png",
        "sections": [
            ("BEVERAGES", [
                {"name": "과일 블렌디드", "price": 9700},
                {"name": "스페셜 스파클링", "price": 8700},
                {"name": "과일 에이드", "price": 6700},
                {"name": "소프트 드링크", "price": 4500},
                {"name": "원두 커피", "price": 4500},
            ]),
            ("DRAFT BEERS", [
                {"name": "테라 생맥주 (340ml)", "price": 6000, "note": "340ml", "weight": "340ml"},
                {"name": "테라 생맥주 (1700ml)", "price": 25000, "note": "1700ml", "weight": "1700ml"},
                {"name": "하이네켄 생맥주 (340ml)", "price": 8700, "note": "340ml", "weight": "340ml"},
                {"name": "하이네켄 생맥주 (1700ml)", "price": 30000, "note": "1700ml", "weight": "1700ml"},
            ]),
        ],
    },
    342: {  # SIDES ＆ ADD ON MATES — /upload/editor/20260531/20260531234224411071.png
        "src": "/upload/editor/20260531/20260531234224411071.png",
        "sections": [
            ("SIDES", [
                {"name": "씨즐링 감바스", "price": 14900},
                {"name": "브뤼셀 스프라우트 플레이트", "price": 11900},
                {"name": "스모크드 컬리플라워", "price": 9900},
                {"name": "블랙 크리스피 후라이즈", "price": 9900},
                {"name": "오지 칩", "price": 7900},
                {"name": "베이크드 포테이토", "price": 7900, "origin": "[베이컨, 돼지고기, 외국산]"},
                {"name": "베이크드 스위트 포테이토", "price": 7900},
                {"name": "프라이드 라이스", "price": 7900, "origin": "[쌀, 국내산]"},
            ]),
            ("ADD ON MATES", [
                {"name": "그릴드 치킨 시저 샐러드 [small]", "price": 9900, "origin": "[닭고기, 국내산]"},
                {"name": "부라타 샐러드", "price": 9900},
                {"name": "멜티드 치즈 (Full)", "price": 6000, "note": "Full", "origin": "[베이컨, 돼지고기, 외국산]"},
                {"name": "멜티드 치즈 (Half)", "price": 3900, "note": "Half", "origin": "[베이컨, 돼지고기, 외국산]"},
                {"name": "가든 샐러드", "price": 5900},
                {"name": "아웃백 수프", "price": 4500},
                {"name": "치킨 핑거 (1pc)", "price": 2900, "origin": "[닭고기, 국내산]"},
                {"name": "리얼 허니콤", "price": 3000},
            ]),
        ],
    },
    344: {  # DESSERTS — /upload/editor/20260702/20260702235324288184.png
        "src": "/upload/editor/20260702/20260702235324288184.png",
        "sections": [("DESSERTS", [
            {"name": "수박 그라니타 빙수", "price": 12900,
             "compose": "시원한 수박 그라니타와 부드러운 바닐라 아이스크림이 조화로운 시즌 한정 디저트"},
            {"name": "허니콤 썬더 프롬 골든 원더", "price": 14900,
             "compose": "곰돌이 푸가 사랑하는 벌집꿀이 통째로 올라간 썬더. 진한 브라우니와 부드러운 아이스크림, 슈가 캔디 크런치가 어우러진 풍부한 텍스처의 기간 한정 디저트"},
            {"name": "씨즐링 브라우니", "price": 12900,
             "compose": "뜨겁게 달군 팬 위에 진한 초콜릿 브라우니와 차가운 아이스크림, 지글거리는 초콜릿 소스가 보는 즐거움을 더하는 디저트"},
            {"name": "초콜릿 썬더 프롬 다운 언더", "price": 8900,
             "compose": "브라우니 케익에 바닐라 아이스크림과 휘핑크림을 얹은 디저트"},
            {"name": "치즈 케이크 올리비아", "price": 7900,
             "compose": "진하고 부드러운 뉴욕스타일 치즈케익"},
        ])],
    },
}


# ────────────────────────── 도우미 ──────────────────────────
def fetch(url, retry=3):
    last = None
    for _ in range(retry):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        except Exception as e:          # noqa: BLE001
            last = e
            time.sleep(3)
    raise last


def strip_comments(s):
    """HTML 주석 제거. 주석 안에 가짜 예시 가격이 들어있다 — 반드시 먼저 걷어낸다."""
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def txt(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def one(pat, s):
    m = re.search(pat, s, re.S)
    return m.group(1) if m else None


def won(s):
    s = re.sub(r"[^\d]", "", s or "")
    return int(s) if s else None


def weight_of(material):
    """재료 원문 안의 중량 표기만 뽑는다. 없으면 None. (계산·추정하지 않는다)"""
    g = re.findall(r"\d[\d,]*\s*(?:g|kg|ml|L)\b", material or "")
    return ", ".join(x.strip() for x in g) if g else None


# ────────────────────────── 파서 ──────────────────────────
def parse_price_block(blk):
    """[(라벨 or None, 금액int)] 로 돌려준다."""
    out = []
    # 라벨 붙은 가격 — <p class="txt">커플 세트</p><p class="price"><strong class="num">147,000
    for lab, num in re.findall(
            r'<p class="txt">(.*?)</p>\s*<p class="price"><strong class="num">(.*?)</strong>', blk, re.S):
        out.append((txt(lab), won(num)))
    if out:
        return out
    # Glass / Bottle / 340ml 형태 — <span class="gram-icon">Glass</span> 또는 <em>340ml</em>
    for lab, num in re.findall(
            r'<span class="gram-icon">(?:<em>)?(.*?)(?:</em>)?</span>\s*<p class="price"><strong class="num">(.*?)</strong>',
            blk, re.S):
        out.append((txt(lab), won(num)))
    if out:
        return out
    for num in re.findall(r'<p class="price"><strong class="num">(.*?)</strong>', blk, re.S):
        out.append((None, won(num)))
    return out


def parse_list_page(body):
    """카테고리 목록 페이지 → [(섹션명 or None, [item, ...])]"""
    parts = re.split(r'<h3 class="menu-list-title">(.*?)</h3>', body, flags=re.S)
    secs = []
    for k in range(1, len(parts), 2):
        sec = txt(parts[k])
        cells = re.findall(
            r'<div class="menu-list-cell menu-type-\d+">(.*?)(?=<div class="menu-list-cell menu-type-\d+">|\Z)',
            parts[k + 1], re.S)
        items = []
        for c in cells:
            ko = txt(one(r'<span class="ko-name">(.*?)</span>', c))
            if not ko:
                continue
            pblk = one(r'<div class="menu-list-price"[^>]*>(.*?)</div>\s*</div>', c) or ""
            items.append({
                "name": ko,
                "en": txt(one(r'<p class="en-title">(.*?)</p>', c)),
                "info": txt(one(r'<p class="info">(.*?)</p>', c)),
                "material": txt(one(r'<dl class="material">.*?<dd>(.*?)</dd>', c)),
                "ext_id": one(r"fnPdtView\('.',\s*'?(\d+)'?\)", c),
                "img": one(r'<p class="btn-menu-list-thumb">\s*<img src="([^"]+)"', c),
                "prices": parse_price_block(pblk),
            })
        secs.append((sec, items))
    return secs


def parse_single_page(body):
    """상품 한 개짜리 카테고리 페이지(#detail-info) → item 하나"""
    ko = txt(one(r'<h3 class="ko-title">(.*?)</h3>', body))
    if not ko:
        return None
    pw = one(r'<div class="price-wrap">(.*?)</div>\s*</div>', body) or ""
    prices = []
    for lab, num in re.findall(r'<p class="txt">(.*?)</p>\s*<p class="price"><strong class="num">(.*?)</strong>',
                               pw, re.S):
        prices.append((txt(lab), won(num)))
    if not prices:
        for num in re.findall(r'<p class="price"><em>(.*?)</em>', pw, re.S):
            prices.append((None, won(num)))
    return {
        "name": ko,
        "en": txt(one(r'<h4 class="en-title akrobat">(.*?)</h', body)),
        "info": txt(one(r'<div class="info">\s*<p class="txt">(.*?)</p>', body)),
        "material": txt(one(r'<p class="sort">(.*?)</p>', body)),
        "gram_info": txt(one(r'<p class="gram-info">(.*?)</p>', body)),
        "ext_id": None,
        "img": one(r'<div class="menu-visual" style="background-image:url\(([^)]+)\)', body),
        "prices": prices,
    }


# ────────────────────────── 본체 ──────────────────────────
def main():
    cats, menus, dropped = [], [], []
    cat_pos = {}                      # 경로 → 그 안에서 다음 자리

    def add_cat(name, parent=None, ext=None):
        path = f"{parent}/{name}" if parent else name
        if path not in cat_pos:
            cats.append({"name": name, "parent": parent,
                         "ext_id": str(ext) if ext is not None else None})
            cat_pos[path] = 0
        return path

    def slot(path):
        i = cat_pos[path]
        cat_pos[path] = i + 1
        return [path, i]

    def push(name, price, path, *, price_source, ext_id=None, price_note=None,
             compose=None, weight=None, origin=None, detail=None, image=None):
        # 메뉴가 아닌 줄 거르기 — 좁게만 잡는다
        if re.search(r"(니다|어요|세요)[.!]?$", name) or name in {c["name"] for c in cats}:
            dropped.append((name, "문장 끝맺음 또는 카테고리 이름과 같음"))
            return
        menus.append({
            "name": name, "price": price, "price_source": price_source, "price_note": price_note,
            "compose_raw": compose or None, "weight_raw": weight or None,
            "origin_raw": origin or None, "allergy_raw": None,
            "detail_url": detail, "image_url": image, "ext_id": ext_id,
            "cats": [slot(path)],
        })

    for menu_idx, cat_name, cate_idx in NAV:
        top = add_cat(cat_name, None, cate_idx)

        # ── 이미지로만 된 카테고리
        if menu_idx in IMAGE_CATS:
            spec = IMAGE_CATS[menu_idx]
            multi = len(spec["sections"]) > 1
            for sec, rows in spec["sections"]:
                path = add_cat(sec, top) if (multi and sec) else top
                for r in rows:
                    push(r["name"], r.get("price"), path,
                         price_source="official_image" if r.get("price") else None,
                         price_note=r.get("note"), compose=r.get("compose"),
                         weight=r.get("weight"), origin=r.get("origin"),
                         detail=f"{BASE}/main.do?menuIdx={menu_idx}",
                         image=BASE + spec["src"])
            print(f"[img ] {cat_name}: {sum(len(r) for _, r in spec['sections'])}개")
            continue

        url = f"{BASE}/main.do?menuIdx={menu_idx}"
        raw = strip_comments(fetch(url))
        i = raw.find('id="dBody"')
        j = raw.find('id="dFoot"')
        body = raw[i:j] if i >= 0 else raw

        # ── 상품 한 개가 카테고리 전체인 페이지
        if menu_idx in SINGLE_PAGES:
            it = parse_single_page(body)
            if not it:
                print(f"[warn] {cat_name}: 상품을 못 읽었다")
                continue
            note_tail = it.get("gram_info") or None
            many = len(it["prices"]) > 1
            for lab, price in it["prices"]:
                nm = f'{it["name"]} ({lab})' if (lab and many) else it["name"]
                pn = " / ".join(x for x in [lab, note_tail] if x) or None
                push(nm, price, top, price_source="official", price_note=pn,
                     compose=it["info"], weight=weight_of(it["material"]),
                     origin=it["material"], detail=url,
                     image=(BASE + it["img"]) if it["img"] and it["img"].startswith("/") else it["img"])
            print(f"[page] {cat_name}: {len(it['prices'])}개")
            continue

        # ── 일반 목록 페이지
        secs = parse_list_page(body)
        real_secs = [s for s, _ in secs if s and s != cat_name and s.replace("&", "＆") != cat_name]
        multi = len(secs) > 1
        n = 0
        for sec, items in secs:
            path = add_cat(sec, top) if (multi and sec in real_secs) else top
            for it in items:
                detail = (f"{BASE}/menu/productView.do?menuIdx=43&cateIdx={cate_idx}&pdtIdx={it['ext_id']}"
                          if it["ext_id"] and cate_idx else url)
                src = "official_delivery" if menu_idx == 244 else "official"
                # 라벨은 가격이 둘 이상일 때만 이름에 붙인다(그때만 «다른 메뉴»다).
                # 하나뿐이면 사이트가 보여주는 이름 그대로 두고 라벨은 price_note 로만 남긴다.
                many = len(it["prices"]) > 1
                for lab, price in (it["prices"] or [(None, None)]):
                    nm = f'{it["name"]} ({lab})' if (lab and many) else it["name"]
                    push(nm, price, path, price_source=src if price else None,
                         price_note=lab, ext_id=it["ext_id"],
                         compose=it["info"], weight=weight_of(it["material"]),
                         origin=it["material"], detail=detail,
                         image=(BASE + it["img"]) if it["img"] and it["img"].startswith("/") else it["img"])
                    n += 1
        print(f"[list] {cat_name}: {n}개  (섹션 {[s for s, _ in secs]})")
        time.sleep(1.2)

    if not menus:
        print("메뉴가 0개다 — 파일을 저장하지 않는다.")
        return 1

    if dropped:
        print("\n⚠️ 버린 줄 (지우기 전 확인용):")
        for nm, why in dropped:
            print("   -", nm, "|", why)
    else:
        print("\n버린 줄 없음")

    data = {
        "brand": "아웃백스테이크하우스",
        "slug": "outback",
        "source": ("공식 홈페이지 www.outback.co.kr — GNB 「MENU」 드롭다운의 /main.do?menuIdx=* 14개 카테고리. "
                   "HTML 주석 제거 후 파싱. 카테고리 4곳(NEW MENU·BEVERAGES＆ALCOHOL·SIDES＆ADD ON MATES·DESSERTS)은 "
                   "본문이 이미지 한 장이라 이미지를 판독해 옮겼다(scripts/brand_outback.py IMAGE_CATS, 이미지 주소 포함). "
                   "가격은 홀 매장가 — 사이트가 DELIVERY 를 별도 카테고리로 두고 거기서만 배달가를 낸다."),
        "collected_at": COLLECTED_AT,
        "origin_note": ORIGIN_NOTE,
        "cats": cats,
        "menus": menus,
    }
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    sub = sum(1 for c in cats if c["parent"])
    print(f"\n저장: {os.path.abspath(OUT)}")
    print(f"카테고리 {len(cats)}개(하위 {sub}) · 메뉴 {len(menus)}개 · "
          f"가격 {sum(1 for m in menus if m['price'])}개 · "
          f"재료 {sum(1 for m in menus if m['compose_raw'])}개 · "
          f"원산지 {sum(1 for m in menus if m['origin_raw'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
