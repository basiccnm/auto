# KAMIS 클라이언트 — 농축산물 도매(02)/소매(01) 일별 가격
#
# ⚠️ 실측으로 확인된 주의사항 (2026-07-16, 실호출 검증)
#  1. User-Agent 헤더 필수. 없으면 차단.
#  2. https 불가 — http만 응답.
#  3. p_convert_kg_yn=Y 를 반드시 쓸 것.
#     도매(02)는 unit이 "10kg(그물망 3포기)" / "8kg" / "40kg" 같은 상자 단위라
#     N으로 받으면 상자값을 kg값으로 오인해 수배~수십배 과대집계된다.
#     (B2C collect_wholesale.py가 이 버그를 갖고 있었음: 양배추 도매 6,292원/kg → 실제 787원/kg)
#     Y로 받으면 kind_name이 "…(1kg)"으로 바뀌고 dpr1이 kg당 환산가로 내려온다.
#  4. 축산물(cat 500)은 cls=01과 cls=02 응답이 완전히 동일 = 실질 도매가 없음.
#     → 축산은 KAMIS 대신 축평원(ekape) 사용. kamis 모듈은 농산물 전용으로 쓴다.
import re

from .config import KAMIS_CERT_ID, KAMIS_CERT_KEY
from .http import FetchError, fetch_json

BASE = "http://www.kamis.or.kr/service/price/xml.do"

RETAIL = "01"
WHOLESALE = "02"

# 품목 카테고리
CAT_GRAIN = "100"      # 식량작물
CAT_VEGETABLE = "200"  # 채소류
CAT_SPECIAL = "300"    # 특용작물(참깨·버섯 등)
CAT_FRUIT = "400"      # 과일류
CAT_LIVESTOCK = "500"  # 축산물 (도매 미제공 — ekape 사용)

# convert_kg_yn=Y 적용 시 kg/L 환산이 성립한 항목만 채택하기 위한 판별
_PER_KG_RE = re.compile(r"\((1kg|1L)\)\s*$")

# 등급 선호순위. 도매 표준은 '상품'. 없으면 중품 → 그 외.
_RANK_PRIORITY = {"상품": 0, "특": 0, "중품": 1, "1등급": 1}


def _url(cat, cls, regday):
    return (
        f"{BASE}?action=dailyPriceByCategoryList"
        f"&p_product_cls_code={cls}"
        f"&p_item_category_code={cat}"
        f"&p_regday={regday}"
        f"&p_convert_kg_yn=Y"
        f"&p_cert_key={KAMIS_CERT_KEY}"
        f"&p_cert_id={KAMIS_CERT_ID}"
        f"&p_returntype=json"
    )


def fetch_category(cat, cls, regday):
    """한 카테고리의 (item_code, kind_code) → 원/kg(또는 원/L) 맵을 반환.

    반환: {(item_code, kind_code): price_int}
    실패/무데이터 시 {} (예외를 밖으로 던지지 않음 — 크론 부분실패 허용).
    """
    try:
        d = fetch_json(_url(cat, cls, regday))
    except FetchError:
        return {}

    data = d.get("data")
    # KAMIS는 데이터 없는 날 data를 빈 리스트로 주기도 함
    if not isinstance(data, dict) or str(data.get("error_code")) != "000":
        return {}

    best = {}
    for it in data.get("item") or []:
        code = it.get("item_code")
        kind = it.get("kind_code")
        if not code or not kind:
            continue
        # kg/L 환산이 성립한 행만 사용. "1포기"·"20개" 등 개수단위 품목은 제외.
        if not _PER_KG_RE.search(it.get("kind_name") or ""):
            continue
        raw = (it.get("dpr1") or "").replace(",", "").strip()
        if not raw.isdigit():
            continue
        price = int(raw)
        if price <= 0:  # 0원 = 데이터 공백. 유효값 아님.
            continue
        rank = (it.get("rank") or "").strip()
        prio = _RANK_PRIORITY.get(rank, 9)
        key = (code, kind)
        prev = best.get(key)
        if prev is None or prio < prev[0]:
            best[key] = (prio, price)
    return {k: v[1] for k, v in best.items()}


def fetch_many(cats, cls, regday):
    """여러 카테고리를 한 번에. {cat: {(item,kind): price}}"""
    return {c: fetch_category(c, cls, regday) for c in cats}
