# 축산물품질평가원(축평원) 클라이언트 — 소비자가격(소매) + 경매/도매가(도매)
#
# [소매] /openapi-data/service/user/grade/consumerPriceDaily
#   serviceKey / standYmd=YYYYMMDD / judgeKind=축종코드
#
# ⚠️ 실측 확인 (2026-07-16)
#  1. 같은 (itemCd, grdNm) 조합이 2행씩 내려온다. 하나는 standYmd=요청일자,
#     다른 하나는 standYmd='평년'(과거 평균 기준선). 반드시 요청일자 행만 쓸 것.
#     (B2C collect_prices.py는 min(ntslPrc)를 취해 '평년'값을 섞어 쓰고 있었음)
#  2. unit이 품목마다 다름: '원/Kg' | '원/100g' | '원/30구' | '원/1L'.
#  3. 부위별(itemNm) · 등급별(grdNm) 조회가 되므로 KAMIS의 min() 대표가 방식보다 정확.
#     → B2C의 "소고기 다짐육/우삼겹이 안심·등심값으로 잡혀 3배 과대" 문제가 해소됨
#       (양지·설도 등 실제 사용 부위를 직접 지정).
#  4. 소비자가격(소매)만 제공. 축산 도매는 아래 별도 엔드포인트 3개로 확보(2026-07-16 추가).
#
# [도매] /openapi-data/service/user/grade 하위 — 전부 2026-07-10 실호출 검증됨
#   auct/beefGrade         소고기 부분육 박스 경락(16부위, 한우/육우)
#   poultry/chickenDomae   닭 도매(도체, avg/franchise/agency/mart)
#   auct/pigGrade          돼지 지육 등급별 경락(도체 기준)
#   → 파싱·제약사항은 아래 "도매(경락/도매시세)" 섹션 주석 참고.
import datetime

from .config import EKAPE_KEY
from .http import FetchError, fetch_xml

BASE = "http://data.ekape.or.kr/openapi-data/service/user/grade/consumerPriceDaily"
GRADE_BASE = "http://data.ekape.or.kr/openapi-data/service/user/grade"

# 축종코드
KIND_BEEF = "4301"          # 소(한우)
KIND_PORK = "4304"          # 돼지
KIND_BEEF_IMPORT = "4401"   # 수입 소고기
KIND_PORK_IMPORT = "4402"   # 수입 돼지고기
KIND_CHICKEN = "9901"       # 닭
KIND_EGG = "9903"           # 계란
KIND_MILK = "9908"          # 우유

# 계란 kg 환산. 특란(XL) 1구 ≈ 64g(60~68g 등급구간 중앙값) → 30구 ≈ 1.92kg.
# '원/10구'로 내려오는 경우 대비해 구수별 계수를 둔다.
EGG_KG_PER_EGG = 0.064

# unit 문자열 → 해당 가격에 곱해 원/kg(또는 원/L)으로 만드는 계수
_UNIT_FACTOR = {
    "원/kg": 1.0,
    "원/1kg": 1.0,
    "원/100g": 10.0,
    "원/500g": 2.0,
    "원/1l": 1.0,
    "원/l": 1.0,
}


def _unit_factor(unit):
    u = (unit or "").strip().lower()
    if u in _UNIT_FACTOR:
        return _UNIT_FACTOR[u]
    # '원/30구', '원/10구' → 구(개)수 × 개당 중량으로 kg 환산
    if u.startswith("원/") and u.endswith("구"):
        digits = u[2:-1]
        if digits.isdigit() and int(digits) > 0:
            return 1.0 / (int(digits) * EGG_KG_PER_EGG)
    return None


def fetch_kind(judge_kind, ymd):
    """한 축종의 (itemCd, grdNm) → 원/kg(또는 원/L) 맵.

    ymd: 'YYYYMMDD'
    실패 시 {}.
    """
    url = f"{BASE}?serviceKey={EKAPE_KEY}&standYmd={ymd}&judgeKind={judge_kind}"
    try:
        root = fetch_xml(url)
    except FetchError:
        return {}
    if (root.findtext(".//resultCode") or "") != "00":
        return {}

    out = {}
    for it in root.findall(".//item"):
        # ★ '평년' 기준선 행 배제
        if (it.findtext("standYmd") or "") != ymd:
            continue
        raw = (it.findtext("ntslPrc") or "").strip()
        if not raw.isdigit() or int(raw) <= 0:
            continue
        factor = _unit_factor(it.findtext("unit"))
        if factor is None:
            continue
        item_cd = it.findtext("itemCd") or ""
        grd = (it.findtext("grdNm") or "").strip()
        out[(item_cd, grd)] = round(int(raw) * factor)
    return out


def fetch_many(kinds, ymd):
    """{judge_kind: {(itemCd, grdNm): price}}"""
    return {k: fetch_kind(k, ymd) for k in kinds}


# ════════════════════════════════════════════════════════════════
# 도매(경락/도매시세) — 2026-07-16 추가. 축산 wholesale의 원천.
#
# ⚠️ auct/beefGrade 는 **미문서화 API**다. WADL(리소스 목록)에는 존재하지만
#    공식 활용가이드 문서에는 없음 → 예고 없이 스펙 변경·폐쇄될 수 있는 리스크.
#    실측(2026-07-10): 안심 118,657 / 목심 25,647 / 양지 46,990 원/kg.
# ⚠️ 경매는 주말·공휴일에 없음 → 빈 결과면 fetch_wholesale_recent()가
#    최근 영업일을 역탐색한다(참가격 find_recent_inspect_day 방식).
# ⚠️ 엔드포인트마다 필드명이 전부 다름(beefGrade=hanAvgT / pigGrade=CTotAmt /
#    chickenDomae=avg). 실측으로 확인된 개별 매핑만 사용 — 공통 스키마화 금지.
# ⚠️ 여기 적힌 3개 경로 외 추측 호출 금지(웹방화벽이 공격으로 탐지·차단함).
# ════════════════════════════════════════════════════════════════

def _grade_items(path, ymd):
    """GRADE_BASE 하위 startYmd/endYmd형 엔드포인트 공통 호출. 실패·비정상 시 []."""
    url = f"{GRADE_BASE}/{path}?serviceKey={EKAPE_KEY}&startYmd={ymd}&endYmd={ymd}"
    try:
        root = fetch_xml(url)
    except FetchError:
        return []
    if (root.findtext(".//resultCode") or "") != "00":
        return []
    return root.findall(".//item")


def _ints(it, tags):
    """item 엘리먼트에서 tags의 정수 필드만 추출(음수/빈값/비숫자 제외)."""
    out = {}
    for t in tags:
        raw = (it.findtext(t) or "").strip()
        if raw.isdigit():
            out[t] = int(raw)
    return out


def fetch_beef_cut_wholesale(ymd):
    """소고기 부분육 박스 경락가 — {부위명: {hanAvgT, hanAvg_0~3, hanBoxCnt, yukAvgT, yukBoxCnt}}.

    hanAvgT=한우 전체평균, hanAvg_0~3=등급별 추정(1++/1+/1/2), yuk*=육우.
    '소계' 행은 부위가 아니므로 배제. 경매 없는 날은 {}.
    """
    out = {}
    for it in _grade_items("auct/beefGrade", ymd):
        cut = (it.findtext("cutmeatName") or "").strip()
        if not cut or cut == "소계":
            continue
        out[cut] = _ints(it, ("hanAvgT", "hanAvg_0", "hanAvg_1", "hanAvg_2", "hanAvg_3",
                              "hanBoxCnt", "yukAvgT", "yukAvg_0", "yukAvg_1", "yukAvg_2",
                              "yukAvg_3", "yukBoxCnt"))
    return out


def fetch_chicken_wholesale(ymd):
    """닭 도매가 — {typeName: {avg, franchise, agency, mart}} (원/kg).

    실측(2026-07-10): typeName='도체' 1행, avg 3,593원/kg.
    4개 필드 전부 보존한다 — franchise(프랜차이즈 납품가)가 식당 매입가에
    가장 가까울 것으로 추정되나 확정 근거가 없어, 일단 avg를 wholesale로 쓰고
    나머지는 수집 리포트로 노출해 추후 판단 근거를 쌓는다.
    """
    out = {}
    for it in _grade_items("poultry/chickenDomae", ymd):
        typ = (it.findtext("typeName") or "").strip()
        if not typ:
            continue
        out[typ] = _ints(it, ("avg", "franchise", "agency", "mart"))
    return out


def fetch_pig_grade_wholesale(ymd):
    """돼지 지육 등급별 경락가 — {gradeNm: {CTotAmt, CTotCnt}} (원/kg, ★지육/도체 기준).

    gradeNm: '1+' '1' '2' '등외' '등외제외' '모돈' '평균' (2026-07-10 실측).
    부분육이 아니라 지육 단가이므로 정육 부위가와 직접 비교 금지 — 재료명에 '지육' 명시.
    대표값은 통상 지표인 '등외제외'(등외·모돈 제외 평균)를 권장.
    """
    out = {}
    for it in _grade_items("auct/pigGrade", ymd):
        grd = (it.findtext("gradeNm") or "").strip()
        if not grd:
            continue
        out[grd] = _ints(it, ("CTotAmt", "CTotCnt"))
    return out


_WHOLESALE_FETCH = {
    "beefGrade": fetch_beef_cut_wholesale,
    "chickenDomae": fetch_chicken_wholesale,
    "pigGrade": fetch_pig_grade_wholesale,
}


def fetch_wholesale_recent(api, ymd, max_back=10):
    """ymd(YYYYMMDD)부터 최대 max_back일 역탐색해 (실제경매일ymd, data) 반환.

    주말·공휴일엔 경매가 없어 빈 응답 → 최근 영업일로 거슬러 올라간다.
    전부 실패하면 (None, {}).
    """
    d = datetime.date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    for back in range(max_back + 1):
        day = (d - datetime.timedelta(days=back)).strftime("%Y%m%d")
        data = _WHOLESALE_FETCH[api](day)
        if data:
            return day, data
    return None, {}


def pick_wholesale(data, spec):
    """카탈로그 wholesale 스펙 → 원/kg 정수 (없으면 None).

    스펙 형식(catalog.py EKAPE_WHOLESALE* 참조) — 엔드포인트별 개별 매핑:
      beefGrade    {"api":"beefGrade","cut":"안심","field":"hanAvgT"}   (육우는 field=yukAvgT)
      chickenDomae {"api":"chickenDomae","field":"avg"}                (도체 행 고정)
      pigGrade     {"api":"pigGrade","grade":"등외제외","field":"CTotAmt"}
    """
    api = spec.get("api")
    if api == "beefGrade":
        row = data.get(spec.get("cut") or "", {})
    elif api == "chickenDomae":
        row = data.get("도체", {})
    elif api == "pigGrade":
        row = data.get(spec.get("grade") or "", {})
    else:
        return None
    v = row.get(spec.get("field") or "")
    return v if isinstance(v, int) and v > 0 else None
