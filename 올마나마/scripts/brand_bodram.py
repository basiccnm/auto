# -*- coding: utf-8 -*-
"""보드람치킨(bodram) 전용 메뉴판 수집기 — data/brand_menu_list/bodram.json 만 만든다.

⛔ DB 는 import 하지 않는다. 적재는 별도 단계(brand_menu_store.replace_brand).

────────────────────────────────────────────────────────────────────────
어느 길로 뚫었나 (2026-07-28)
────────────────────────────────────────────────────────────────────────
사전 정찰은 http://www.bodram.com/ 을 "옛 게시판형(가격 0건)" 으로 봤지만,
헤더 <div class="h_menu"> 안에 게시판이 아닌 링크가 하나 더 있었다:

    <a href="/shop/shopdetail.html?branduid=3604109">MENU</a>

즉 메뉴판은 board.html 쪽이 아니라 **MakeShop 쇼핑몰(shopdetail.html)** 이다.
board 쪽 code= 4개는 메뉴가 아니었다 —
  bodram_image1 = WHAT'S NEW(신규 매장 소식) / bodram_board1 = STORE(매장찾기)
  bodram_image6 = ARCHIVE / bodram_image3 = 롤링 공지문구

**이미지 판독은 하지 않았다. 전부 HTML 텍스트로 읽혔다.**
(원산지·알레르기까지 <div id="tab-cont"> 안에 글자로 들어 있다)

메뉴 7개는 닫힌 집합이다. 상세페이지 하단 그리드(div.item-list)가 "자기 자신을 뺀
나머지 6개" 를 항상 보여준다. 3604109 의 그리드와 3604370 의 그리드를 맞대어
전체 7개·화면 순서를 확정했다. 사이트 어디에도 다른 xcode(카테고리) 링크가 없다.

페이징: 없다. 상세페이지 그리드가 전량이고 next/prev·page= 파라미터가 없다.

카테고리: 화면에 보이는 탭 이름은 헤더의 「MENU」 하나뿐이다(xcode=001).
          JSON-LD 안에는 내부 분류명이 "CHICKEN (대)" 로 들어 있다(화면에는 안 나온다).

🔴 가격은 담지 않는다 (price = null)
   소스에는 세 군데(JSON-LD offers.price / input#price / input#price_wh)에 18,000 이
   들어 있지만 **7개 메뉴가 전부 18,000 으로 똑같다.** 통날개와 순살이 같은 값일 수 없고,
   화면에는 «18,000» 도 «원» 도 한 글자도 렌더링되지 않는다(태그 밖 텍스트에 0건).
   대신 상세페이지가 직접 이렇게 말한다 —
       "*매장 별 판매 가격은 일부 상이할 수 있습니다."
   장바구니가 살아있지 않은 프랜차이즈 소개형 메이크샵이라 템플릿 기본값으로 판단했다.
   판단 근거는 각 메뉴 price_note 에 남겨두었으니 다음 사람이 대조할 수 있다.
────────────────────────────────────────────────────────────────────────
"""
import sys, os, re, json, time, io, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://www.bodram.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "brand_menu_list", "bodram.json")
COLLECTED_AT = "2026-07-28"

# 홈 헤더에 적힌 MENU 링크 (여기서만 출발한다 — 주소를 조합하지 않는다)
ENTRY = "/shop/shopdetail.html?branduid=3604109"

# ── 화면 순서 (상세페이지 그리드 2장을 맞대어 확정) ───────────────────
#   3604109 의 그리드 : 370 371 372 374 373 375        (자기 자신 제외)
#   3604370 의 그리드 : 109 371 372 374 373 375        (자기 자신 제외)
#   → 전체 순서       : 109 370 371 372 374 373 375
#   ※ sku 순서(001000000001~7)와 다르다. 화면 순서를 쓴다.
ORDER = ["3604109", "3604370", "3604371", "3604372", "3604374", "3604373", "3604375"]

CAT_NAME = "MENU"     # 헤더 h_menu 의 탭 라벨 (화면에 보이는 유일한 메뉴 탭)
CAT_EXT = "001"       # xcode=001

# ── 대조표 (2026-07-28 수집 당시 값) ────────────────────────────────
# ⚠️ 이미지 판독은 하지 않았다. 아래는 HTML 텍스트에서 읽은 값 그대로다.
#    다음 사람이 돌렸을 때 값이 바뀌면 스크립트가 ⚠️ 로 알려준다.
#    branduid   화면 h3 (=한글 메뉴명)          화면 h2 (영문)
REFERENCE = {
    "3604109": "보드람 후라이드",             # BODRAM ORIGINAL FRIED CHICKEN
    "3604370": "콤보 후라이드",               # CHICKEN COMBO (DRUMSTICKS + WINGS)
    "3604371": "통다리 후라이드",             # Chicken Drumsticks
    "3604372": "통날개 후라이드",             # Chicken Wings
    "3604374": "안심크로켓",                  # CHICKEN CROQUETTES
    "3604373": "순살 후라이드(다리살/가슴살)",  # BONELESS FRIED CHICKEN (DRUMSTICK/BREAST)
    "3604375": "스윗블랙페퍼 순살 치킨",       # SWEET BLACKPEPPER BONELESS CHICKEN
}
# 원산지는 7개 전부 동일했다: "- 닭고기(국내산)"
REFERENCE_ORIGIN = "- 닭고기(국내산)"


def fetch(path):
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_comments(h):
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(s):
    """태그·엔티티를 지우고 줄바꿈을 살려 원문 그대로 뽑는다."""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&amp;", "&").replace("&nbsp;", " ")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#169;", "(c)")
          .replace("&ensp;", " ").replace("&quot;", '"'))
    return "\n".join(x.strip() for x in s.split("\n")).strip()


def grid(h):
    """상세페이지 하단 그리드의 branduid 를 진열 순서대로."""
    return re.findall(
        r'class="item-list">\s*<a href="/shop/shopdetail\.html\?branduid=(\d+)', h)


def parse_detail(h, uid):
    h = strip_comments(h)
    out = {"ext_id": uid}

    # ① JSON-LD — 한글 메뉴명·가격·sku·내부분류가 여기 다 있다
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', h, re.S)
    # description 안에 생 줄바꿈이 들어 있다 → strict=False
    ld = json.loads(m.group(1), strict=False) if m else {}
    out["name"] = ld.get("name")
    out["price"] = ld.get("offers", {}).get("price")
    out["sku"] = ld.get("sku")
    out["cat_internal"] = ld.get("category")
    imgs = ld.get("image") or []
    out["image_url"] = imgs[0] if imgs else None

    # ② 화면 h2(영문)·h3(한글) — JSON-LD 와 대조용
    m = re.search(r'<h2\s*>(.*?)</h2>', h, re.S)
    out["name_en"] = txt(m.group(1)).replace("\n", " ") if m else None
    m = re.search(r'<h3>(.*?)</h3>', h, re.S)
    out["name_h3"] = txt(m.group(1)) if m else None
    m = re.search(r'<h4>(.*?)</h4>', h, re.S)
    out["tagline"] = txt(m.group(1)) if m else None

    # ③ 원산지 / 알레르기 — <div id="tab-cont"> 안 두 개의 div (탭 버튼 순서와 같다)
    out["origin_raw"] = out["allergy_raw"] = None
    m = re.search(r'<div id="tab-cont">(.*?)\n\s*</div>\s*</div>', h, re.S)
    if m:
        blocks = re.findall(r'<div[^>]*>(.*?)</div>', m.group(1), re.S)
        btns = [txt(x) for x in re.findall(r'<li><a href="#">(.*?)</a></li>',
                                           h[:m.start()], re.S)][-2:]
        for lab, blk in zip(btns, blocks):
            v = txt(blk) or None
            if "원산지" in lab:
                out["origin_raw"] = v
            elif "알레르기" in lab:
                out["allergy_raw"] = v

    # ④ 판매가 원문 (JSON-LD 와 대조)
    m = re.search(r'id="price" name="price" value="([\d,]*)"', h)
    out["price_raw"] = m.group(1) or None
    return out


# ── 메뉴가 아닌 줄 걸러내기 (버리기 전에 반드시 출력한다) ──────────────
NOT_MENU = {"MENU", "STORY", "WITH US", "STORE", "ARCHIVE", "WHAT'S NEW",
            "WHAT’S NEW", "온라인문의", "Terms of Use", "Shopping Guide",
            "개인정보처리방침", "Test"}


def is_menu(name):
    if not name:
        return False, "이름 없음"
    n = name.strip()
    if n in NOT_MENU or n == CAT_NAME:
        return False, "네비·카테고리 이름"
    if len(n) >= 18:
        return False, "18자 이상"
    if n.endswith((".", "!", "?", "다", "요")):
        return False, "문장부호·서술형으로 끝남"
    return True, None


def main():
    print("[1] 홈 헤더의 MENU 링크에서 출발:", BASE + ENTRY)
    pages = {}
    for i, uid in enumerate(ORDER):
        path = ENTRY if uid == "3604109" else \
            "/shop/shopdetail.html?branduid=%s&search=&xcode=001&mcode=000&scode=" % uid
        if i:
            time.sleep(1.8)
        h = fetch(path)
        pages[uid] = (path, h)
        print("    %s  %6d bytes" % (uid, len(h)))

    # 그리드 대조 — 전체 집합이 정말 7개인지 코드로 확인한다
    seen = set(ORDER)
    for uid, (_, h) in pages.items():
        g = set(grid(strip_comments(h)))
        extra = g - seen
        if extra:
            print("    ⚠️ 그리드에 모르는 상품:", extra)
        if g | {uid} != seen:
            print("    ⚠️ %s 의 그리드가 전체와 다르다: %s" % (uid, sorted(g)))
    print("[2] 그리드 대조 완료 — 전체 %d개 (페이징 없음)" % len(ORDER))

    menus, dropped = [], []
    for pos, uid in enumerate(ORDER):
        path, h = pages[uid]
        d = parse_detail(h, uid)
        ok, why = is_menu(d["name"])
        if not ok:
            dropped.append((d["name"], why))
            continue
        if d["name"] != d["name_h3"]:
            print("    ⚠️ JSON-LD 이름과 화면 h3 가 다르다: %r vs %r"
                  % (d["name"], d["name_h3"]))
        if REFERENCE.get(uid) != d["name"]:
            print("    ⚠️ 대조표와 다르다 %s: %r → %r (사이트가 바뀐 것)"
                  % (uid, REFERENCE.get(uid), d["name"]))
        if d["origin_raw"] != REFERENCE_ORIGIN:
            print("    ⚠️ 원산지가 대조표와 다르다 %s: %r" % (uid, d["origin_raw"]))
        # ── 가격은 담지 않는다 (아래 DUMMY_PRICE 참고) ──────────────
        note = ("공식 홈페이지 표기: '*매장 별 판매 가격은 일부 상이할 수 있습니다.' "
                "/ 화면에 가격 없음. 소스에만 %s원이 있으나 7개 메뉴 전부 같은 값이라 "
                "메이크샵 템플릿 기본값으로 보고 채택하지 않음" % d["price"]) \
            if d["price"] else None
        menus.append({
            "name": d["name"],
            "price": None,
            "price_source": None,
            "price_note": note,
            "weight_raw": None,
            "origin_raw": d["origin_raw"],
            "allergy_raw": d["allergy_raw"],
            "detail_url": BASE + path,
            "image_url": d["image_url"],
            "ext_id": uid,
            "cats": [[CAT_NAME, pos]],
        })

    if dropped:
        print("[3] 버린 줄 (지우기 전 확인):")
        for n, why in dropped:
            print("    - %r  ← %s" % (n, why))
    else:
        print("[3] 버린 줄 없음")

    if not menus:
        print("메뉴 0개 — 파일을 저장하지 않는다.")
        return 1

    doc = {
        "brand": "보드람치킨",
        "slug": "bodram",
        "source": BASE + ENTRY,
        "collected_at": COLLECTED_AT,
        # 브랜드 공통 원산지 한 장은 없다. 메뉴마다 원산지 탭이 따로 있다.
        "origin_note": None,
        "cats": [{"name": CAT_NAME, "parent": None, "ext_id": CAT_EXT}],
        "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("[4] 저장:", OUT)
    print("    카테고리 %d개 · 메뉴 %d개 · 가격 %d개 · 원산지 %d개"
          % (len(doc["cats"]), len(menus),
             sum(1 for m in menus if m["price"]),
             sum(1 for m in menus if m["origin_raw"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
