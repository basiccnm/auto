# -*- coding: utf-8 -*-
"""네이버 쇼핑 검색 API — 시세(단위당 가격) 산출.

용도: 상품을 파는 게 아니라 **시세 지표**를 뽑는다.
      그래서 최소주문수량·사업자전용·배송비는 신경 쓰지 않는다(가격 신호만 본다).

핵심 아이디어 (2026-07-20 설계 논의):
  1) 검색어에 규격을 함께 넣는다 — "양파 1kg", "참기름 500ml".
     그냥 "양파"로 검색하면 3kg박스·깐양파·양파즙이 뒤섞여 정규화가 지옥이 된다.
  2) 그래도 다른 규격이 섞여 오므로, **응답 title에서 규격을 다시 파싱해 검증**한다.
  3) 단위당 가격의 **중간값**을 쓴다. 최저가는 미끼상품·대용량 쪽으로, 최고가는 소분·가공품 쪽으로
     치우쳐서 둘 다 시세를 대표하지 못한다.

의존성 0 (표준 라이브러리만) — 공공데이터 모듈과 같은 원칙.
"""
import json
import re
import statistics
import time
import urllib.parse
import urllib.request

from .config import CALL_INTERVAL, HTTP_TIMEOUT, USER_AGENT, credentials

API_URL = "https://openapi.naver.com/v1/search/shop.json"


class NaverShoppingError(Exception):
    pass


# ── 규격 파싱 ────────────────────────────────────────────────────────────
# 무게·부피는 g / ml 로 환산해 저장한다(레시피가 이미 최소단위로 정규화돼 있으므로 맞춰줌).
_WEIGHT_UNITS = {
    "kg": ("g", 1000.0), "킬로그램": ("g", 1000.0), "킬로": ("g", 1000.0),
    "g": ("g", 1.0), "그램": ("g", 1.0),
    "mg": ("g", 0.001),
}
_VOLUME_UNITS = {
    "l": ("ml", 1000.0), "리터": ("ml", 1000.0),
    "ml": ("ml", 1.0), "밀리리터": ("ml", 1.0), "cc": ("ml", 1.0),
}
_COUNT_UNITS = ("개입", "개", "입", "팩", "봉", "포", "병", "캔", "매", "장", "구")

_AMOUNT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|킬로그램|킬로|mg|g|그램|l|리터|ml|밀리리터|cc)\b",
    re.IGNORECASE,
)
_COUNT_RE = re.compile(r"(\d+)\s*(" + "|".join(_COUNT_UNITS) + r")")
# "500ml x 2", "1kg*3", "300g × 4" 같은 묶음 표기
_MULTIPLIER_RE = re.compile(r"[x×*]\s*(\d+)", re.IGNORECASE)
# 괄호 안 내역 — "1840g (23gX80입)"의 (…)는 총량을 쪼갠 설명이지 묶음 배수가 아니다.
_PAREN_RE = re.compile(r"\([^)]*\)")
_TAG_RE = re.compile(r"</?b>")


def clean_title(title):
    """네이버는 검색어에 <b> 태그를 씌워 돌려준다."""
    return _TAG_RE.sub("", title or "").strip()


def parse_spec(title):
    """상품명에서 규격을 뽑아 (수량, 단위)로 반환. 못 찾으면 None.

    단위는 'g' | 'ml' | '개' 중 하나로 정규화된다.
    묶음(x2, 3개입)은 곱해서 총량으로 만든다 — 단위당 가격을 내려면 총량이 필요하므로.
    """
    t = clean_title(title)
    if not t:
        return None

    m = _AMOUNT_RE.search(t)
    if m:
        value = float(m.group(1))
        raw_unit = m.group(2).lower()
        unit, factor = (_WEIGHT_UNITS.get(raw_unit) or _VOLUME_UNITS.get(raw_unit))
        total = value * factor

        # 규격 뒤쪽에 붙은 묶음 표기만 본다 ("1kg x 3"은 3kg, "3 x 양파"는 무시)
        #  ⚠️ 괄호 안은 "총량의 내역"이지 묶음이 아니다. 반드시 먼저 걷어낸다.
        #     "2kg (250g x 8개입)" → 2kg짜리 한 봉인데 x8을 곱해 16kg으로 읽혔다.
        #     그 8배 과소 단가가 바게트 생지 시세를 1.0원/g으로 만들었다(2026-07-22).
        tail = _PAREN_RE.sub(" ", t[m.end():])
        mult = _MULTIPLIER_RE.search(tail) or _COUNT_RE.search(tail)
        if mult:
            try:
                n = int(mult.group(1))
                if 1 < n <= 100:  # 100묶음 넘어가면 오탐(모델명·용량표기)으로 본다
                    total *= n
            except ValueError:
                pass
        return (total, unit)

    # 무게·부피가 없으면 개수 단위 ("양파 3개입")
    m = _COUNT_RE.search(t)
    if m:
        try:
            return (float(m.group(1)), "개")
        except ValueError:
            return None
    return None


# ── API 호출 ─────────────────────────────────────────────────────────────
def search(query, display=100, sort="sim"):
    """쇼핑 검색 원본 결과. sort: sim(유사도) | date | asc(저가) | dsc(고가)."""
    cid, sec = credentials()
    url = API_URL + "?" + urllib.parse.urlencode(
        {"query": query, "display": min(int(display), 100), "sort": sort})
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": cid,
        "X-Naver-Client-Secret": sec,
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        raise NaverShoppingError(f"{type(e).__name__}: {e}") from e

    items = []
    for it in body.get("items", []):
        price = int(it.get("lprice") or 0)
        if price <= 0:
            continue
        items.append({
            "title": clean_title(it.get("title")),
            "price": price,
            "brand": it.get("brand") or it.get("maker") or "",
            "mall": it.get("mallName") or "",
            "link": it.get("link") or "",
        })
    return items


# ── 시세 산출 ────────────────────────────────────────────────────────────
def market_price(query, unit=None, exclude=None, display=100, sort="sim", sleep=True):
    """검색어로 시세를 뽑는다.

    query   : "양파 1kg" 처럼 규격을 포함한 검색어 (그래야 원하는 규격이 상위에 온다)
    unit    : 'g' | 'ml' | '개'. 지정하면 그 단위로 파싱된 상품만 채택.
              None이면 가장 많이 나온 단위를 자동 채택한다.
    exclude : 제외 키워드 목록. "양파" 검색에 양파즙·양파분말이 섞여 들어오는 걸 막는 용도.

    반환: {
      query, unit, unit_price(중간값), n(채택 표본수), min, max,
      samples[ {title, price, amount, unit_price} ... ]  ← 검수용
    }
    채택 표본이 없으면 unit_price=None.
    """
    items = search(query, display=display, sort=sort)
    if sleep:
        time.sleep(CALL_INTERVAL)  # 연속 호출 시 차단 방지

    ex = [w for w in (exclude or []) if w]
    rows = []
    for it in items:
        if any(w in it["title"] for w in ex):
            continue
        spec = parse_spec(it["title"])
        if not spec:
            continue
        amount, u = spec
        if amount <= 0:
            continue
        rows.append({"title": it["title"], "price": it["price"], "brand": it["brand"],
                     "amount": amount, "unit": u,
                     "unit_price": it["price"] / amount})

    if unit is None and rows:
        # 가장 많이 잡힌 단위를 그 재료의 단위로 본다
        counts = {}
        for r in rows:
            counts[r["unit"]] = counts.get(r["unit"], 0) + 1
        unit = max(counts, key=counts.get)

    picked = [r for r in rows if r["unit"] == unit]
    prices = sorted(r["unit_price"] for r in picked)

    return {
        "query": query,
        "unit": unit,
        "n": len(picked),
        "unit_price": statistics.median(prices) if prices else None,
        "min": prices[0] if prices else None,
        "max": prices[-1] if prices else None,
        "samples": sorted(picked, key=lambda r: r["unit_price"]),
    }


def market_prices(queries, unit=None, exclude=None, display=100):
    """여러 재료를 한 번에. queries: ["양파 1kg", "참기름 500ml", ...]

    호출 사이에 간격을 두므로 재료가 많으면 시간이 걸린다(재료당 약 CALL_INTERVAL초).
    """
    out = {}
    for q in queries:
        try:
            out[q] = market_price(q, unit=unit, exclude=exclude, display=display)
        except NaverShoppingError as e:
            out[q] = {"query": q, "error": str(e), "unit_price": None, "n": 0}
    return out
