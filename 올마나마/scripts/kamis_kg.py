# KAMIS 카테고리 조회 공용 헬퍼 — 원/kg(원/L) 정규화
#
# ⚠️ 실측으로 확인된 제약 (2026-07-16 실호출 검증)
#    상세 §8.3은 삭제된 B2B 프로젝트 설계서에 있다 → 보관본 D:\_보관\얼마남아-b2b-기획\web\설계서.md
#  1. User-Agent 헤더 필수. 없으면 차단. https 불가 — http만 응답.
#  2. 도매(cls=02)는 unit이 "8kg" / "15kg" / "10kg(그물망 3포기)" 같은 상자 단위다.
#     p_convert_kg_yn=N으로 받으면 상자값을 kg값으로 오인해 8~15배 과대집계된다.
#     (실측: 양배추 도매 7,196원/8kg → 잘못 7,196원/kg 기록. 실제 900원/kg)
#     → 도매는 반드시 p_convert_kg_yn=Y.
#  3. ★ convert_kg_yn=Y가 바꾸는 건 kind_name과 dpr1 뿐. unit 필드는 상자 단위 그대로다.
#     따라서 Y 응답에 UNIT_TO_KG를 또 곱하면 이중환산이 된다. 판별은 kind_name으로 할 것.
#     예) 상추 도매 Y: kind_name="적(1kg)" dpr1=6,125 / unit="4kg" ← unit 쓰면 4배 틀림
#  4. Y로도 환산 안 되는 품목이 있다. 개수 단위(양배추 "1포기", 배추 "1포기")는
#     소매에서 kind_name이 "(1포기)"로 남는다. → kg 단가 없음.
#  5. 축산물(cat 500)은 cls=01과 cls=02 응답이 완전히 동일 = 실질 도매가 없음.
#     이 모듈로 축산 도매를 받으면 안 된다. 호출측에서 cat 500을 제외할 것.
#  6. 품종/등급 min() 대표가는 금지. 등급은 '상품'(도소매 표준)을 우선한다.
#     min()을 쓰면 도매만 중품, 소매는 상품처럼 등급이 어긋나 도매/소매 비율이 왜곡된다.
import json
import re
import ssl
import urllib.request

CERT_KEY = "638151fe-2bcd-45dc-90d4-60983e536c91"
CERT_ID = "dndmotor1@gmail.com"

RETAIL = "01"
WHOLESALE = "02"

# 소매 unit → kg/L 환산계수. 소매는 이미 소비자 단위(100g/1kg)라 N으로 받아 이 표를 쓴다.
#  '10구'/'30구' = 계란 전용(특란 개당 60g 기준 환산 — 축산물 등급규격. 2026-07-20 단위사고 수정:
#  특란10구 4,225원이 kg값처럼 저장돼 계란이 4,225원/kg로 왜곡됐었다 → 실제 7,042원/kg)
UNIT_TO_KG = {"100g": 10.0, "500g": 2.0, "20kg": 0.05, "1kg": 1.0, "600g": 1 / 0.6,
              "200g": 5.0, "1L": 1.0, "1l": 1.0, "10구": 1 / 0.6, "30구": 1 / 1.8}

# convert_kg_yn=Y로 kg/L 환산이 성립한 행 판별 (kind_name 접미사)
_PER_KG_RE = re.compile(r"\((1kg|1L)\)\s*$", re.I)

# 등급 우선순위. 낮을수록 우선. 도소매 표준은 '상품'.
_RANK_PRIORITY = {"상품": 0, "특": 0, "중품": 1, "1등급": 1}

# 개수 단위 판별: "1개" "1마리" "1손" "1포기" "1단" → 단위 라벨("개" 등) 추출
_PIECE_UNIT_RE = re.compile(r"^1(\D+)$")

# 품종(원산지) 우선순위 — 같은 등급 안에서 국산을 우선한다 (2026-07-20 근본수정).
#   왜: 고춧가루가 국산/중국 경합에서 '최저가 채택' 규칙 때문에 중국산(13,478원/kg)으로
#   집혔다. 가정식 재료 시세표이므로 국산 기준이 맞다. 국산 품종이 없으면 기존대로 최저가.
_IMPORT_WORDS = ("중국", "수입", "미국", "칠레", "호주", "베트남", "노르웨이", "태국", "러시아")

def _kind_priority(kind_name):
    if "국산" in kind_name or "국내" in kind_name: return 0
    if any(w in kind_name for w in _IMPORT_WORDS): return 2
    return 1

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _url(cat, cls, regday, convert):
    return ("http://www.kamis.or.kr/service/price/xml.do?action=dailyPriceByCategoryList"
            f"&p_product_cls_code={cls}&p_item_category_code={cat}&p_regday={regday}"
            f"&p_convert_kg_yn={convert}&p_cert_key={CERT_KEY}&p_cert_id={CERT_ID}"
            "&p_returntype=json")


def _items(cat, cls, regday, convert):
    req = urllib.request.Request(_url(cat, cls, regday, convert),
                                 headers={"User-Agent": "Mozilla/5.0"})  # UA 필수!
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=25, context=_ctx).read().decode("utf-8"))
    except Exception:
        return []
    data = d.get("data")
    # 데이터 없는 날 data를 빈 리스트로 주기도 함
    if not isinstance(data, dict) or str(data.get("error_code")) != "000":
        return []
    return data.get("item") or []


def _price(it):
    raw = (it.get("dpr1") or "").replace(",", "").strip()
    if not raw.isdigit():
        return None
    v = int(raw)
    return v if v > 0 else None  # 0원 = 데이터 공백. 유효값 아님.


def fetch_category(cat, cls, regday, verbose=False, with_units=False):
    """{item_code: 원/kg} (with_units=True면 {item_code: (가격, 단위)}). 실패/무데이터 시 {}.

    도매(02)는 convert_kg_yn=Y로 받아 kg 환산된 행만 채택한다.
    소매(01)는 N + UNIT_TO_KG (소매 단위가 이미 소비자 단위라 Y가 불필요하고,
    Y로 받으면 '1포기' 품목이 통째로 빠져 야채지수 바스켓이 도매와 어긋난다).

    ★ 개수 단위(1개/1마리/1손/1포기/1단) 처리 (2026-07-20 근본수정):
      예전엔 factor=1.0으로 개당 가격을 kg값처럼 저장했다(호박 987원/개→987원/kg,
      고등어 3,218원/마리→3,218원/kg 사고). 이제는:
      - with_units=True  → (개당 가격, '개'/'마리'/…)로 정직하게 반환. 호출측이 base_unit에 저장.
      - with_units=False → 개수 단위 품목은 제외(kg값을 지어내지 않는다).

    같은 item_code에 여러 품종/등급이 오면 '상품' 등급 우선 → 국산 우선 → 최저가.
    (품종 코드 직접 지정은 ingredients.kamis_kind_code 채우면 전환. 설계서 §8.3-5)
    """
    convert = "Y" if cls == WHOLESALE else "N"
    best = {}   # item_code -> (rank_prio, kind_prio, price, unit)
    kinds = {}  # item_code -> set(kind_name)  (품종 경합 경고용)
    for it in _items(cat, cls, regday, convert):
        code = it.get("item_code")
        price = _price(it)
        if not code or price is None:
            continue
        kind_name = (it.get("kind_name") or "").strip()
        if cls == WHOLESALE:
            # ★ Y 응답은 kind_name으로 판별. unit은 상자 단위 그대로라 쓰면 안 된다.
            if not _PER_KG_RE.search(kind_name):
                continue  # kg 환산 불가 품목(개수 단위 등) — 도매가 없음으로 처리
            perkg, unit = price, "kg"
        else:
            raw_unit = (it.get("unit") or "").strip()
            factor = UNIT_TO_KG.get(raw_unit)
            if factor is not None:
                perkg, unit = round(price * factor), "kg"
            else:
                m = _PIECE_UNIT_RE.match(raw_unit)
                if not m:
                    continue          # 알 수 없는 단위 — 지어내지 않는다
                perkg, unit = price, m.group(1).strip()   # 개당 가격 그대로 + 단위 라벨
                if not with_units:
                    continue          # kg 사전을 원하는 호출자에게 개당 값을 kg로 주지 않는다
        prio = _RANK_PRIORITY.get((it.get("rank") or "").strip(), 9)
        kprio = _kind_priority(kind_name)
        kinds.setdefault(code, set()).add(kind_name)
        prev = best.get(code)
        if prev is None or (prio, kprio, perkg) < prev[:3]:
            best[code] = (prio, kprio, perkg, unit)
    if verbose:
        for code, ks in sorted(kinds.items()):
            if len(ks) > 1:
                print(f"    [경합] {cat}/{code} 품종 {len(ks)}종 {sorted(ks)} → 상품등급>국산>최저가")
    if with_units:
        return {c: (v[2], v[3]) for c, v in best.items()}
    return {c: v[2] for c, v in best.items()}


def fetch_many(cats, cls, regday, verbose=False):
    """{cat: {item_code: 원/kg}}"""
    return {c: fetch_category(c, cls, regday, verbose) for c in cats}
