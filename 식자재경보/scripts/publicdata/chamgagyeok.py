# 참가격(한국소비자원 생필품 가격정보) 클라이언트 — 가공식품 소비자가격
#
# 엔드포인트: http://openapi.price.go.kr/openApiImpl/ProductPriceInfoService/getProductPriceInfoSvc.do
#   ServiceKey / goodId / goodInspectDay=YYYYMMDD
#
# ⚠️ 실측 확인 (2026-07-16 — 키 동기화 완료되어 정상 응답함)
#  1. goodId 또는 entpId 둘 중 하나 필수. 없으면 resultCode=05.
#  2. 조사일(goodInspectDay)은 '주간' 단위. 임의 날짜를 넣으면 resultCode=00 + 빈 result.
#     → 최근 조사일을 며칠씩 되짚어 탐색해야 함(find_recent_inspect_day).
#  3. 응답은 판매처(entpId)별 낱개 가격 리스트 → 중앙값을 대표 소매가로 채택.
#  4. 소비자가격(마트 판매가)만 제공 → wholesale은 NULL.
import datetime

from .config import CHAMGA_KEY
from .http import FetchError, fetch_xml

BASE = "http://openapi.price.go.kr/openApiImpl/ProductPriceInfoService/getProductPriceInfoSvc.do"

_PRICE_TAG = "iros.openapi.service.vo.goodPriceVO"


def fetch_good(good_id, inspect_day):
    """해당 조사일의 판매처별 가격 리스트(원, 포장단위 그대로). 없으면 []."""
    url = f"{BASE}?ServiceKey={CHAMGA_KEY}&goodId={good_id}&goodInspectDay={inspect_day}"
    try:
        root = fetch_xml(url)
    except FetchError:
        return []
    if (root.findtext("resultCode") or "") != "00":
        return []
    prices = []
    for vo in root.iter(_PRICE_TAG):
        raw = (vo.findtext("goodPrice") or "").strip()
        if raw.isdigit() and int(raw) > 0:
            prices.append(int(raw))
    return prices


def median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else round((s[mid - 1] + s[mid]) / 2)


def find_recent_inspect_day(probe_good_id, end_date, lookback_days=35):
    """end_date(datetime.date)부터 거꾸로 훑어 데이터가 있는 조사일 1개를 찾는다.

    참가격은 주간 조사라 매일 값이 없다. 실패 시 None.
    """
    for back in range(lookback_days + 1):
        day = (end_date - datetime.timedelta(days=back)).strftime("%Y%m%d")
        if fetch_good(probe_good_id, day):
            return day
    return None
