# -*- coding: utf-8 -*-
"""반올림피자(banolimpizza) 전용 메뉴판 수집기 — 2026-07-28

만드는 것: data/brand_menu_list/banolimpizza.json  (JSON 한 개. DB 에는 쓰지 않는다)

■ 어떻게 뚫었나
  - 목록·상세 모두 **평범한 서버렌더 HTML** 이다. SPA 가 아니라 브라우저 없이 urllib 로 다 읽힌다.
    (WebFetch 는 링크를 지워서 spOid 를 못 얻는다 → 원본 HTML 을 직접 받아 정규식으로 걷는다)
  - 탭 9개는 목록 페이지의 `<ul class="_tab">` 에 그대로 있다(onclick=location.href 로 주소까지).
  - 피자 카드에는 `data-spOid` / `data-productId` 가 붙어 있다 → 상세 주소를 조립한다.
    ⛔ spOid 를 숫자만 바꿔 찔러보지 않는다. 목록에 실제로 적힌 값만 쓴다.
  - 세트는 `changeUrl(<setId>, '<이름>', <가격>)`, 사이드·음료는 이미지 파일명(`.../side/new/1145.png`)
    에 상품 id 가 들어 있다. 이 id 가 진짜 상품 id 라는 건 아래 AJAX 의 pdId 와 대조해 확인했다
    (1145=마늘빵을 입은 소시지, 1060=반올림핫콤보 … 전부 일치).
  - 원산지·알레르기·영양(중량)은 상세 페이지 팝업이 부르는 자체 AJAX 3개다.
    페이지 안 스크립트(getOrigin/getAllergy/getNutrition)에 주소가 그대로 적혀 있다:
        /etc/w_origin  /etc/w_allergy  /etc/w_nutrition
    · w_origin  : 재료 단위 브랜드 공통표(베이컨=돼지고기(외국산…)) → 최상위 origin_note
    · w_allergy : pdId=spOid 단위 → 메뉴별 allergy_raw
    · w_nutrition: pdId + pdSize(레귤러/라지), val10 = 무게(g) → 메뉴별 weight_raw
      (컬럼 대응은 페이지의 setNutrition() 주석 그대로: val2=총제공량, val1=1회제공량, val10=무게)

■ 사이즈 규칙 (피자 브랜드 사고 방지)
  - 사이즈가 다르면 다른 메뉴다. 합치지 않고 **각각 한 줄**.
  - 이름 뒤에 사이트 표기 그대로 붙인다 — 상세의 사이즈 라디오가 `Regular` / `Large` 다.
    (목록 카드는 R/L 로 줄여 쓰지만, 값의 출처인 상세 표기를 쓴다)
  - 세트메뉴는 이름 자체에 (L)/(R) 이 들어 있어 덧붙이지 않는다.

■ 안 담는 것
  - 도우(오리지널/치즈링/콘치즈/크림치즈/골드/스위트 골드/소보로) · 토핑추가(…추가 (8개)) → **옵션**이다
  - 빌더 페이지(w_productHalf / w_productOne / w_productPick)의 피자 선택 목록 → 옵션이다.
    이 페이지들에선 **사이즈·가격만** 읽는다.
  - `상품금액` 같은 UI 문자열
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.banolimpizza.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "banolimpizza.json")
COLLECTED_AT = "2026-07-28"
SLEEP = 2.0

# 탭(카테고리) — 목록 페이지 <ul class="_tab"> 에 적힌 순서·이름 그대로
TABS = [
    ("신메뉴", "new", "/menu/w_productNewPizza"),
    ("추천 베스트 메뉴", "best", "/menu/w_productBest"),
    ("시그니처", "signature", "/menu/w_productSignature"),
    ("클래식", "classic", "/menu/w_productPizza"),
    ("스페셜", "specialty", "/menu/w_productSpecialty"),
    ("꿀조합 한판", "variety", "/menu/w_productVariety"),
    ("세트메뉴", "set", "/menu/w_productSet"),
    ("사이드메뉴", "side", "/menu/w_productSide"),
    ("음료&소스", "drink", "/menu/w_productDrink"),
]

_last = [0.0]


def get(url, ajax=False):
    wait = SLEEP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}
    if ajax:
        h["X-Requested-With"] = "XMLHttpRequest"
        h["Referer"] = BASE + "/menu/w_productPizza"
    req = urllib.request.Request(url, headers=h)
    body = urllib.request.urlopen(req, timeout=40).read()
    _last[0] = time.time()
    return body.decode("utf-8", "replace")


def nocomment(h):
    """HTML 주석을 먼저 걷어낸다. 반올림은 숨긴 메뉴를 주석으로 남겨둔다(<!-- 나만의 픽 숨기기 -->)."""
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def text(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&amp;", "&").replace("&nbsp;", " ")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", s).strip()


def won(s):
    return int(s.replace(",", ""))


# ---------------------------------------------------------------- 목록
def list_items(path):
    """목록 페이지의 productList 안 <li> 를 화면 순서대로 뽑는다."""
    h = nocomment(get(BASE + path))
    i = h.find("productList")
    j = h.find("</ul>", i)
    seg = h[i:j]
    out = []
    for p in re.split(r"<li\b", seg)[1:]:
        head = p[:p.find(">")]
        tit = re.search(r'class="tit">(.*?)</div>', p, re.S)
        if not tit:
            continue
        name = text(tit.group(1))
        if not name:
            continue
        img = re.search(r'<img\s+src="([^"]+)"', p)
        spo = re.search(r'data-spOid="(\d+)"', head)
        pid = re.search(r'data-productId="(\d+)"', head)
        chg = re.search(r"changeUrl\((\d+),\s*'(.*?)',\s*(\d+)\)", head)
        href = re.search(r"location\.href='([^']*)'", head)
        boxes = re.findall(r'class="size">\s*([^<]*?)\s*</div>\s*'
                           r'<div class="price">\s*([\d,]+)\s*원', p, re.S)
        flat = re.findall(r'class="price">\s*([\d,]+)\s*원', p)
        out.append({
            "name": name,
            "spOid": spo.group(1) if spo else None,
            "productId": pid.group(1) if pid else None,
            "setId": chg.group(1) if chg else None,
            "href": href.group(1) if href else None,
            "img": img.group(1) if img else None,
            "list_sizes": [(a, won(b)) for a, b in boxes],
            "list_prices": [won(x) for x in flat],
        })
    return out


# ---------------------------------------------------------------- 상세
def detail(url):
    """상세 페이지에서 설명(compose_raw)과 사이즈별 판매가를 읽는다."""
    h = nocomment(get(url))
    desc = None
    m = re.search(r'class="name">(.*?)</div>\s*<div class="txt">(.*?)</div>', h, re.S)
    if m:
        desc = text(m.group(2)) or None
    # 사이즈 라디오 — <span>Regular</span> 21,900 원  /  <span>Regular 20,900원</span> 두 형태
    sizes = []
    i = h.find('id="ppdSizeWrap"')
    if i >= 0:
        j = h.find("</ul>", i)
        for li in re.split(r"<li\b", h[i:j])[1:]:
            lab = re.search(r"<span>\s*(Regular|Large)", li)
            pr = re.search(r"([\d,]+)\s*원", li)
            if lab and pr:
                sizes.append((lab.group(1), won(pr.group(1))))
    img = None
    m = re.search(r'class="productImg[^"]*">.*?<img src="([^"]+)"', h, re.S)
    if m:
        img = m.group(1)
    return desc, sizes, img


# ---------------------------------------------------------------- AJAX
def etc(name):
    return json.loads(get(BASE + "/etc/" + name, ajax=True))


def img_id(url):
    """이미지 파일명에서 상품 id. .../side/new/1145.png -> 1145 , .../drink/1038_500ml.png -> 1038"""
    if not url:
        return None
    stem = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    m = re.match(r"(\d+)", stem)
    return m.group(1) if m else None


def main():
    origin = etc("w_origin")
    allergy = etc("w_allergy")
    nutrition = etc("w_nutrition")

    # 원산지 — 재료 단위 브랜드 공통표 (메뉴별이 아니다) → origin_note
    origin_note = " / ".join(
        "%s: %s" % (o.get("val8") or "", (o.get("val3") or "").strip())
        for o in origin if o.get("val8") and o.get("val3")
    )
    origin_note = ("제품 출시 및 식재료 수급 상황에 따라 일부 내용이 변경될 수 있습니다. "
                   + origin_note) if origin_note else None

    alg = {}
    for o in allergy:
        if o.get("val3"):
            alg.setdefault(str(o["pdId"]), text(o["val3"]))

    SZ = {"레귤러": "Regular", "라지": "Large"}
    nut = {}
    for o in nutrition:
        key = (str(o["pdId"]), SZ.get(o.get("pdSize") or "", o.get("pdSize")))
        bits = []
        if o.get("val2"):
            bits.append("총 제공량 %s" % o["val2"])
        if o.get("val1"):
            bits.append("1회 제공량 %s" % o["val1"])
        if o.get("val10"):
            bits.append("무게 %sg" % o["val10"])
        if bits:
            nut.setdefault(key, " · ".join(bits))

    def weight_of(pid, size):
        if not pid:
            return None
        return nut.get((pid, size)) or nut.get((pid, None))

    cats = [{"name": n, "parent": None, "ext_id": e} for n, e, _ in TABS]
    menus = []
    dropped = []
    dcache = {}

    for cname, _cext, path in TABS:
        pos = 0
        for it in list_items(path):
            nm = it["name"]
            # UI 문자열·옵션 걸러내기 (지우기 전에 목록으로 남긴다)
            if nm in ("상품금액", "정상가", "주문 금액") or nm.endswith("추가") \
               or re.search(r"추가 \(\d+", nm):
                dropped.append((cname, nm, "옵션/UI 문자열"))
                continue

            durl = None
            desc = None
            sizes = []
            ext = None
            if it["spOid"]:
                ext = it["spOid"]
                durl = "%s/menu/productPizzaDetail?spOid=%s&productId=%s" % (
                    BASE, it["spOid"], it["productId"])
                if durl not in dcache:
                    dcache[durl] = detail(durl)
                desc, sizes, _ = dcache[durl]
            elif it["href"] and it["href"].startswith("/menu/"):
                # 하프 앤 하프 · 1+1 · 내맘대로pick — 빌더 페이지. 사이즈·가격만 읽는다
                durl = BASE + it["href"]
                if durl not in dcache:
                    dcache[durl] = detail(durl)
                desc, sizes, _ = dcache[durl]
                desc = None                       # 빌더 페이지엔 메뉴 설명이 없다
            elif it["setId"]:
                ext = it["setId"]                 # 세트는 spOid 가 없다. changeUrl 의 세트 id
            else:
                ext = img_id(it["img"])           # 사이드·음료는 이미지 파일명의 상품 id

            if not sizes:                         # 상세가 없거나 사이즈가 하나뿐인 메뉴
                if it["list_sizes"]:
                    sizes = [(a, b) for a, b in it["list_sizes"]]
                elif it["list_prices"]:
                    sizes = [(None, it["list_prices"][0])]
                else:
                    sizes = [(None, None)]

            # 이름에 이미 사이즈가 박혀 있으면(세트 `…세트(L)` · `내맘대로pick(L)`) 덧붙이지 않는다
            keep_plain = bool(re.search(r"\((?:L|R)\)\s*$", nm))
            for label, price in sizes:
                if label and not keep_plain:
                    name = "%s %s" % (nm, label)
                else:
                    name = nm
                menus.append({
                    "name": name,
                    "price": price,
                    "price_source": "official",
                    "price_note": "오리지널 도우 기준" if it["spOid"] else None,
                    "compose_raw": desc,
                    "weight_raw": weight_of(ext, label),
                    "origin_raw": None,           # 원산지는 브랜드 공통표 → origin_note
                    "allergy_raw": alg.get(ext),
                    "detail_url": durl,
                    "image_url": it["img"],
                    "ext_id": ext,
                    "cats": [[cname, pos]],
                })
                pos += 1

    if not menus:
        print("메뉴 0개 — 저장하지 않는다")
        return 1

    doc = {
        "brand": "반올림피자",
        "slug": "banolimpizza",
        "source": BASE + "/menu/w_productPizza",
        "collected_at": COLLECTED_AT,
        "origin_note": origin_note,
        "cats": cats,
        "menus": menus,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("저장:", OUT)
    print("카테고리 %d개 · 메뉴 %d개 · 가격 %d개 · 구성 %d개 · 알레르기 %d개 · 중량 %d개" % (
        len(cats), len(menus),
        sum(1 for m in menus if m["price"] is not None),
        sum(1 for m in menus if m["compose_raw"]),
        sum(1 for m in menus if m["allergy_raw"]),
        sum(1 for m in menus if m["weight_raw"]),
    ))
    if dropped:
        print("버린 줄 %d개:" % len(dropped))
        for c, n, why in dropped:
            print("  -", c, "|", n, "|", why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
