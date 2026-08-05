# -*- coding: utf-8 -*-
"""식자재왕몰(ewangmart, 고도몰) 채소·과일 도매 시세 수집.

미트박스처럼 사이트 자체 AJAX를 그대로 호출한다(경로 추측 아님).
  POST https://www.ewangmart.com/exts/goods_list_ajax.do
  body: cate=<카테고리>&page=<n>   (application/x-www-form-urlencoded)
  응답: 상품 <li class="goods-item"> HTML 조각

정책:
  - **정가(원가)** 를 쓴다. 할인가는 미끼상품이라 상시가로 안 본다(원칙 §3, 쿠폰가 배제와 동일).
  - 원산지로 나눈다(2026-07-25 대표 지시). 상품명 앞의 `국내산/중국산/...` 를 뽑는다.
  - 등급은 상품명의 `(특)` `(상)` 등.
  - 규격이 kg 이면 원/kg 환산, `단/개/망/봉` 은 환산 못 하니 그대로 둔다(추측 금지).

⚠️ 요청 간격 3초. 과거 IP 차단 사고가 있어 천천히 받는다.
"""
import json, os, re, sys, time, html, urllib.request, urllib.parse, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "data", "research", "ewang")
API = "https://www.ewangmart.com/exts/goods_list_ajax.do"
GAP = 3.0

# 채소/과일 카테고리 (2026-07-25 확인)
CATS = [
    ("39", "양파대파마늘생강"), ("40", "당근무뿌리채소"), ("41", "고추오이열매채소"),
    ("42", "배추깻잎잎채소"), ("43", "새싹어린잎"), ("44", "감자고구마마토란"),
    ("45", "버섯류"), ("46", "콩나물숙주생나물"), ("47", "무말랭이건나물"),
    ("48", "고사리자숙나물"), ("49", "향신채소"), ("51", "국산과일"),
    ("124", "수입과일"), ("52", "냉동채소과일"), ("125", "건과일"),
    ("53", "대추밤생견과류"),
]

# 수입국을 먼저 본다 — '중국산'에 '국산'이 들어 있어 순서가 중요하다.
ORIGINS = ["중국산", "미국산", "호주산", "칠레산", "뉴질랜드산", "필리핀산", "베트남산",
           "태국산", "페루산", "이집트산", "스페인산", "멕시코산", "국내산", "국산", "수입"]
GRADE = re.compile(r"\(\s*(특|상|중|하|왕특|대|중대|소)\s*[_)]")
KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
G = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I)


def won(s):
    m = re.search(r"([\d,]+)\s*원", s or "")
    return int(m.group(1).replace(",", "")) if m else None


def origin_of(name):
    for o in ORIGINS:
        if o in name:
            return "국산" if o in ("국내산", "국산") else o
    return None


def pack_kg(name):
    """총 중량(kg). kg/g 만 환산. 단·개·망 등은 None."""
    m = KG.search(name)
    if m:
        return float(m.group(1))
    m = G.search(name)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def parse(html_text):
    items, seen = [], set()
    for block in re.split(r'<li class="goods-item"', html_text)[1:]:
        # 상품명 — class="goods-title"
        nm = re.search(r'class="goods-title"[^>]*>(.*?)</', block, re.S)
        name = html.unescape(re.sub(r"<[^>]+>", "", nm.group(1))).strip() if nm else None
        name = re.sub(r"\s+", " ", name) if name else None
        if not name:
            continue
        # 가격 — 값이 <em>590</em>원 처럼 태그로 감싸여 있다. 태그 제거 후 숫자를 뽑는다.
        # 정가(sale-price 없을 때)·할인가 둘 다 나올 수 있어, 900,000 미만 최댓값=정가.
        flat = re.sub(r"<[^>]+>", " ", block)
        prices = [won(x + "원") for x in re.findall(r"([\d,]+)\s*원", flat)]
        prices = [p for p in prices if p and p < 900000]      # 999,999 는 '개당 미설정' 더미
        gno = re.search(r"gno=(\d+)", block)
        gkey = gno.group(1) if gno else name
        if gkey in seen:                 # 같은 상품이 목록에 두 번 렌더된다(PC/모바일 블록)
            continue
        seen.add(gkey)
        items.append({
            "name": name,
            "list_price": max(prices) if prices else None,     # 정가(상시가)
            "sale_price": min(prices) if prices else None,      # 할인가(참고)
            "origin": origin_of(name),
            "grade": (GRADE.search(name).group(1) if GRADE.search(name) else None),
            "pack_kg": pack_kg(name),
            "soldout": ("품절" in block),
            "gno": gno.group(1) if gno else None,
        })
    return items


def call(cate, page):
    data = urllib.parse.urlencode({"cate": cate, "page": page}).encode()
    req = urllib.request.Request(API, data=data, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.ewangmart.com",
        "Referer": "https://www.ewangmart.com/goods/category.do?cate=%s" % cate,
        "User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    allrows, req_n = [], 0
    for cate, name in CATS:
        got, page = [], 1
        while page <= 20:
            try:
                items = parse(call(cate, page))
            except urllib.error.HTTPError as e:
                print("  !! %s p%d HTTP %s — 중단" % (name, page, e.code)); break
            except Exception as e:
                print("  !! %s p%d %s — 중단" % (name, page, e)); break
            req_n += 1
            if not items:
                break
            for it in items:
                it["cate"] = name
            got += items
            page += 1
            time.sleep(GAP)
        allrows += got
        with open(os.path.join(OUTDIR, "%s.json" % name), "w", encoding="utf-8") as f:
            json.dump(got, f, ensure_ascii=False, indent=1)
        wkg = sum(1 for x in got if x["pack_kg"])
        print("%-16s %4d건 (kg규격 %d · 원산지 %d)"
              % (name, len(got), wkg, sum(1 for x in got if x["origin"])), flush=True)

    with open(os.path.join(OUTDIR, "_전량.json"), "w", encoding="utf-8") as f:
        json.dump(allrows, f, ensure_ascii=False, indent=1)
    print("\n총 %d건 / 요청 %d회 → data/research/ewang/" % (len(allrows), req_n))


if __name__ == "__main__":
    main()
