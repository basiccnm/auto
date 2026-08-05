# -*- coding: utf-8 -*-
"""네이버 쇼핑 시세 수집 (2026-07-20)

쿠팡 API를 시간상 포기하고 네이버로 간다. 쿠팡이 줬을 '판매량 랭킹'이 네이버엔 없어서
(응답에 리뷰수·판매량이 안 들어온다) **정확도순(sim) 상위권 = 많이 팔리는 것**으로 대신한다.

🔴 절대 하면 안 되는 것: sort=asc(가격 낮은 순)로 최저가 집기.
   업소용 20kg·해외직구·미끼상품이 1등으로 올라온다. 식용유 5,830원 사고가 그것이었다.
   여기서는 **가격 정렬을 아예 쓰지 않는다.**

흐름:
   재료명 → (선택) 데이터랩으로 후보 키워드 중 제일 많이 찾는 말 고르기
          → 검색 API sort=sim 상위 40
          → 상품명에서 용량 파싱 (못 뽑으면 버림)
          → 가정용 규격만 남김 (업소용·묶음·해외직구 제외)
          → 원/kg 환산 후 **중앙값** 채택
          → ingredients.naver_* 컬럼에만 기록 (manual_price는 안 건드림)

  python scripts/naver_shop.py --check          키 확인만 (호출 1회)
  python scripts/naver_shop.py --limit 30       30종 수집
  python scripts/naver_shop.py --key soy_sauce  1종만
"""
import argparse
import json
import os
import re
import sqlite3
import statistics
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

CID = os.environ.get("NAVER_CLIENT_ID", "")
CSEC = os.environ.get("NAVER_CLIENT_SECRET", "")
SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"

# ── 상품이 아닌 것만 버린다 ─────────────────────────────────────
#  🔴 2026-07-20 방침 변경: 대용량·업소용을 **버리지 않는다.**
#     "20kg가 나오면 리스트업해놓고 나중에 그걸 검색에 쓰면 되잖아" (대표님)
#     → 20kg는 곧 프랜차이즈 매입가에 가깝다. 지금 '도매 ×0.7'로 추정하던 자리를
#       실측으로 대체할 유일한 재료라 버리면 영영 못 만든다.
#     여기서는 **상품이 아닌 것**(사은품·체험단 등)만 걸러내고 나머지는 전부 담는다.
NG_WORDS = ("체험단", "샘플", "쿠폰", "사은품", "증정품", "공병", "무료나눔")

# 🔴 식재료가 아닌 것 (2026-07-20): '걸이형 마늘 양파 보관망(WFJ233L)'이 모델명 233L을
#    용량으로 읽혀 10원/kg으로 들어왔다. 주방용품·포장재는 시세가 아니다.
#    ⚠️ 단어를 좁게 쓴다 — '칼'만 넣으면 **칼국수**가 걸린다.
NOT_FOOD = ("보관망", "보관용기", "밀폐용기", "채칼", "슬라이서", "다지기", "도마",
            "지퍼백", "위생장갑", "주방저울", "진공포장기", "밀폐",
            "수납", "정리함", "거치대", "받침대",
            # 🔴 씨앗·모종은 식재료가 아니다(2026-07-20). '조선무'로 검색했더니
            #    "조선대형봄무씨앗 5g"이 잡혀 720,000원/kg으로 들어왔다.
            "씨앗", "종자", "종묘", "모종", "재배키트", "파종",
            # 식품이 아닌 생활용품 — '무'에 "무불소 치약"이 걸렸다
            "치약", "샴푸", "세제", "비누", "화장품", "영양제", "건강기능",
            # 식품이 아닌 공예·공업용 (전기 가마 유리공예 파우더가 335,000원/L로 들어왔다)
            "공예", "DIY", "핸드페인트", "페인트", "유약", "글레이즈", "공업용", "비식용",
            # 🔴 세트 상품 제외 (2026-07-20 대표님 지시) — 구성이 제각각이라 단가가 성립 안 됨
            "세트", "SET", "선물", "종세트", "모음전", "골라담기", "체험팩")

# ── 규격 구간 ──────────────────────────────────────────────────
#  같은 재료라도 어느 축에 쓰느냐에 따라 골라야 할 구간이 다르다.
#    레시피(집밥) → 소포장·가정용
#    브랜드(매장) → 대용량·업소용
TIERS = (("소포장", 0.0, 0.6),      # 300g 팩, 500ml 병
         ("가정용", 0.6, 3.0),      # 1kg, 1.8L
         ("대용량", 3.0, 10.0),     # 5kg, 4L
         ("업소용", 10.0, 1e9))     # 20kg 포대, 18L 말통


# 🔴 업소용 시작점은 재료 성격마다 다르다(2026-07-20 대표님).
#    "소스는 대용량 업체 기본이 2kg, 파우치 형태로 완전 달라"
#    밀가루 2kg은 가정용이지만 소스 2kg은 업소용이다. 하나의 무게 기준으로는 못 가른다.
#    (대용량 시작, 업소용 시작) — kg 또는 L
BIZ_FROM = {"소스": (1.5, 2.0),      # 소스 2kg 파우치가 곧 업소용 기본
            "정육": (3.0, 5.0),      # "마라탕은 우삼겹 5kg가 기본"
            "채소": (5.0, 10.0),     # 양배추 15kg 박스
            "가루": (3.0, 10.0),     # 밀가루 20kg 포대
            "쌀":  (10.0, 20.0),     # 쌀만 예외 — 집에서도 10kg, 식당이 20kg
            "수산": (1.5, 2.0),      # 연어 반마리 2.2kg = 업소용
            "기본": (3.0, 10.0)}
_CAT_WORD = {
    "소스": ("소스", "양념", "장", "드레싱", "케첩", "마요", "시럽", "육수", "다대기",
           "간장", "된장", "고추장", "춘장", "쌈장", "식초", "맛술", "액젓", "젓갈"),
    "정육": ("고기", "육", "살", "삼겹", "목살", "등심", "안심", "갈비", "닭", "돈", "우",
           "곱창", "대창", "막창", "족발", "베이컨", "햄", "소시지"),
    "채소": ("배추", "무", "파", "양파", "당근", "감자", "고구마", "오이", "호박", "상추"),
    "가루": ("가루", "분", "밀가루", "전분", "설탕", "소금", "쌀"),
    "수산": ("연어", "생선", "필렛", "고등어", "참치", "새우", "오징어", "낙지",
           "문어", "조개", "꼬막", "전복", "미역", "다시마", "명태", "대구"),
}
# 업소용을 직접 말해주는 표기. 파우치는 업소용 소스의 전형적인 형태다.
_BIZ_WORD = ("업소용", "식자재", "도매", "반마리", "파우치", "말통", "박스", "포대", "BOX")


# 🔴 쌀만 예외 (2026-07-20 대표님): "곡물 업소용 시작 20kg 안 됩니다. 쌀만입니다."
#    쌀은 집에서도 10kg을 사고 식당이 20kg을 쓴다. 밀가루·설탕 같은 다른 가루는
#    10kg이면 이미 업소용이라 곡물 전체에 20kg을 적용하면 안 된다.
#    ⚠️ '쌀국수·쌀떡·쌀가루'는 쌀이 아니다 — 이름 전체로 판정한다.
_RICE_NAMES = ("쌀", "백미", "현미", "찹쌀", "멥쌀", "흑미")


# ── 등급 기준 (2026-07-20 대표님: "무농약 GAP 이런 거 쓰면 돼") ──────
#  같은 '느타리버섯'이 파지 2,750원 ~ 특품 19,500원 ~ 건조품 78,000원까지 7배 벌어졌다.
#  기준을 정하지 않으면 어떤 값을 골라도 근거가 없다.
#    · 기준품  = 무농약·GAP·친환경 (마트에서 파는 보통 등급)
#    · 아래로  = 파지·못난이 (정상품 아님)
#    · 위로    = 특품·프리미엄 (일반 소비자 기준 아님)
#    · 별개    = 건조·분말·칩 (가공품이라 kg 단가 자체가 다른 물건)
GRADE_STD = ("무농약", "GAP", "친환경", "유기농")
GRADE_LOW = ("파지", "못난이", "흠집", "B급", "실속", "자투리", "잔품")
GRADE_HIGH = ("특품", "프리미엄", "명품", "선물용", "최상급", "대왕", "왕특")
PROCESSED = ("건조", "말린", "건", "분말", "파우더", "칩", "튀김", "슬라이스칩", "동결건조")


def grade_class(title):
    """상품명 → '기준' | '저급' | '고급' | '가공' | '일반'"""
    t = title or ""
    if any(w in t for w in PROCESSED[:2]) or "칩" in t or "분말" in t or "파우더" in t:
        return "가공"
    if any(w in t for w in GRADE_LOW):
        return "저급"
    if any(w in t for w in GRADE_HIGH):
        return "고급"
    if any(w in t for w in GRADE_STD):
        return "기준"
    return "일반"


def cat_of_name(name):
    n = (name or "").strip()
    if n in _RICE_NAMES:
        return "쌀"
    for cat, words in _CAT_WORD.items():
        if any(w in n for w in words):
            return cat
    return "기본"


# 🔴 포장 단위가 곧 신호다 (2026-07-20 대표님, 이게 제일 정확했다).
#    "팽이는 봉단위로 팔면 소매, 1box = XX봉은 업소용"
#    무게로 자르려 하면 재료마다 기준이 달라 끝이 없다(쌀은 집에서도 10kg, 소스는 2kg이 업소용).
#    상품명이 스스로 말해주는 걸 먼저 믿는다.
_UNIT_BIZ = ("박스", "BOX", "Box", "box", "케이스", "포대", "말통", "1BOX", "1박스", "한박스")
_UNIT_HOME = ("봉", "개입", "팩", "병", "캔", "포기", "단")


def tier_of(qty, title="", name=""):
    """구간 판정 — ① 포장 단위 표기 ② 업소용 명시 ③ 무게 순으로 본다."""
    t = title or ""
    # ① 박스·포대·말통이면 무게와 상관없이 업소용
    if any(w in t for w in _UNIT_BIZ):
        return "업소용"
    # ② 상품명이 업소용을 직접 말하면 대용량 이상
    biz_word = any(w in t for w in _BIZ_WORD)
    big, biz = BIZ_FROM[cat_of_name(name or title)]
    if qty >= biz:
        return "업소용"
    if qty >= big:
        return "대용량"
    if biz_word:
        return "대용량"
    # ③ 봉·팩·병 같은 소매 단위면 무게가 좀 나가도 가정용으로 둔다
    return "소포장" if qty <= 0.6 else "가정용"


# ── 원산지 ─────────────────────────────────────────────────────
#  축이 갈린다(2026-07-20 대표님): 집밥=국산(소비자가 국산을 산다),
#  매장=수입 포함(싸니까 식당은 수입을 쓴다). 그래서 버리지 않고 표시만 한다.
_IMPORT = ("수입", "미국산", "호주산", "캐나다산", "브라질", "스페인", "칠레", "덴마크",
           "네덜란드", "노르웨이", "중국산", "베트남", "태국산", "러시아", "페루", "유럽산")
_DOMESTIC = ("국산", "국내산", "한우", "한돈", "제주", "무안", "밀양", "여주", "횡성")


def origin_of(title):
    t = title or ""
    if any(w in t for w in _IMPORT):
        return "수입"
    if any(w in t for w in _DOMESTIC):
        return "국산"
    return "미표기"


# ── 축산 등급 ──────────────────────────────────────────────────
#  한우는 등급에 따라 kg당 몇 만원씩 벌어진다. 등급 없이 한 값으로 계산하면 의미가 없다.
_GRADE_RE = re.compile(r"(1\+\+|1\+|1등급|2등급|3등급|투뿔|원뿔)")
_GRADE_NORM = {"투뿔": "1++", "원뿔": "1+"}


def grade_of(title):
    m = _GRADE_RE.search(title or "")
    if not m:
        return None
    g = m.group(1)
    return _GRADE_NORM.get(g, g)


# ── 통·구·망 (채소) ────────────────────────────────────────────
#  "수입 양배추 특 6구 15KG" → 15kg에 6통 = 한 통 2.5kg.
#  대표님: 유통은 kg, 소비자는 통. 양배추 1통이 2~3kg이고 쪼개면 단계당 +50%.
_PIECES_RE = re.compile(r"(\d+)\s*(?:구|통|망|포기)\b")


def pieces_of(title):
    m = _PIECES_RE.search(title or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if 1 <= n <= 60 else None


# ── 품종 오염 (부분일치 함정) ───────────────────────────────────
#  🔴 프로젝트 상습 함정: '양배추'에 방울양배추, '쌀'에 쌀식초, '고추냉이'에 생고추.
#     재료명 바로 앞에 수식어가 붙으면 대개 **다른 물건**이다.
#     단 원산지·상태를 나타내는 말은 같은 물건이므로 통과시킨다.
#  통과시킬 수식어 = **원산지·상태**만. 그 외 수식어가 붙으면 다른 물건으로 본다.
#  🔴 2026-07-20 대표님: "키워드랑 제목이 겹쳐서 생긴 거임, 다른 상품임"
#     '치즈'에 스트링치즈·프로틴치즈, '떡볶이떡'에 조랭이떡, '꼬막'에 새꼬막이 걸린다.
#     낱말이 들어 있다고 같은 물건이 아니다 — 앞에 뭐가 붙었는지를 봐야 한다.
_OK_PREFIX = ("국산", "국내산", "수입", "신선", "생", "햇", "손질", "냉동", "냉장",
              "유기농", "친환경", "무농약", "특", "대", "중", "소", "왕",
              # 산지명 — 같은 물건이다
              "제주", "무안", "창녕", "청도", "영양", "보성", "신안", "횡성", "안동",
              "이천", "김포", "당진", "아산", "여수", "남도", "나주", "성주", "밀양",
              "의령", "산청", "해남", "고창", "정선", "평창", "포천", "강원", "전라",
              "경북", "충남", "국내", "노르웨이", "칠레", "호주", "미국", "덴마크")


def variant_flag(name, title):
    """재료명이 더 긴 합성어의 뒷부분으로만 나오면 '다른 품종 의심'을 돌려준다."""
    t, n = (title or ""), (name or "")
    if not n or n not in t:
        return None
    for m in re.finditer(re.escape(n), t):
        head = t[:m.start()]
        mm = re.search(r"([가-힣]+)$", head)     # 바로 앞에 붙은 한글 덩어리
        if not mm:
            return None                          # 단독으로 등장 = 정상
        pre = mm.group(1)
        if any(pre.endswith(w) for w in _OK_PREFIX):
            return None
        return f"{pre}{n}"                       # 예: 방울양배추
    return None

_TAG = re.compile(r"<[^>]+>")

# ── 용량 파서 ──────────────────────────────────────────────────
#  상품명 표기가 제각각이라 여기서 대부분의 정확도가 갈린다.
#    "백설 중력밀가루 1kg"            → 1.0 kg
#    "청정원 카놀라유 900ml"          → 0.9 L
#    "비엔나 250g x 2입"              → 0.5 kg   (묶음은 곱한다)
#    "햇반 210g*12개"                 → 2.52 kg
_UNIT_KG = {"kg": 1.0, "킬로": 1.0, "g": 0.001, "그램": 0.001}
_UNIT_L = {"l": 1.0, "ℓ": 1.0, "리터": 1.0, "ml": 0.001, "밀리": 0.001, "cc": 0.001}
_NUM = r"(\d+(?:[.,]\d+)?)"
_QTY_RE = re.compile(
    _NUM + r"\s*(kg|킬로|g|그램|ml|밀리|cc|l|ℓ|리터)\b"
    r"(?:\s*[x*×]\s*(\d+))?", re.I)
# "x2", "* 3개" 처럼 곱셈기호가 있는 묶음
_MULT_RE = re.compile(r"[x*×]\s*(\d+)\s*(?:개|입|팩|봉|병|캔|포)?\b", re.I)
# 기호 없이 "100g 6개입"처럼 붙는 묶음.
#  ⚠️ 단위를 '개입·팩·봉…'으로 좁힌다. 맨 '개'까지 받으면 "500g 3개 남음" 같은
#     문구나 순위 표기를 수량으로 오인해 용량이 몇 배로 뻥튀기된다.
_MULT_BARE_RE = re.compile(r"(\d+)\s*(?:개입|입|팩|봉지|봉|병|캔|포)\b")
# 🔴 "125ml, 24개"처럼 **쉼표 뒤에 오는 개수**는 확실한 수량 표기다(2026-07-20).
#    맨 '개'를 전부 받으면 "500g 3개 남음" 같은 문구를 오인하지만, 쉼표 뒤는 안전하다.
#    이걸 못 읽어서 우유 125ml×24개가 159,200원/L로 들어왔다(실제 6,633원/L).
_MULT_COMMA_RE = re.compile(r"^\s*,\s*(\d+)\s*(?:개|입|팩|봉|병|캔|포)\b")


def parse_pack(title):
    """상품명 → (수량, 'kg'|'L') / 못 뽑으면 None.

    ⚠️ 못 뽑으면 **버린다.** 억지로 기본값 0.5kg을 넣으면 원가가 조용히 틀어진다
       (pack_of() 기본값 때문에 겪은 그 문제를 여기서 되풀이하지 않는다).
    """
    t = _TAG.sub(" ", title or "")
    if any(w in t for w in NOT_FOOD):
        return None
    # 모델명 속 숫자+단위를 용량으로 읽지 않는다 — "WFJ233L"의 233L이 그랬다.
    #  영문/숫자에 바로 붙어 있으면 규격 표기가 아니다.
    t = re.sub(r"[A-Za-z]{2,}\d+\s*(?:kg|g|ml|l|ℓ)\b", " ", t, flags=re.I)
    found = []
    for m in _QTY_RE.finditer(t):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        u = m.group(2).lower()
        mult = int(m.group(3)) if m.group(3) else 1
        # 바로 뒤에 "x 2입"이 따로 떨어져 있는 경우도 잡는다
        if mult == 1:
            tail = t[m.end():m.end() + 18]
            m2 = (_MULT_COMMA_RE.match(tail) or _MULT_RE.search(tail)
                  or _MULT_BARE_RE.search(tail))
            if m2:
                mult = int(m2.group(1))
        if u in _UNIT_KG:
            qty, unit = v * _UNIT_KG[u] * mult, "kg"
        elif u in _UNIT_L:
            qty, unit = v * _UNIT_L[u] * mult, "L"
        else:
            continue
        if qty <= 0:
            continue
        found.append((round(qty, 4), unit, mult))
    # 🔴 50kg 상한은 **두 해석 중 작은 쪽**에 건다(2026-07-20).
    #    "밀가루 1kg 150개입"은 곱하면 150kg이라 예전 코드가 통째로 버렸는데,
    #    낱개 1kg은 멀쩡하다. 곱셈 여부는 뒤에서 데이터로 정하므로 여기서 죽이면 안 된다.
    found = [f for f in found if min(f[0], f[0] / max(f[2], 1)) <= 50]
    if not found:
        return None
    # 🔴 여러 규격이 적혀 있으면 **제일 작은 것**을 쓴다(2026-07-20 확정).
    #    상품명 "생연어 300g 500g 1kg"은 옵션 안내이고, lprice는 그중 최저가 =
    #    최소 규격의 값이다. 예전엔 최대값을 골라 1kg으로 나눠 원/kg이 3.3배 낮게 나왔다.
    found.sort(key=lambda x: x[0])
    qty, unit, mult = found[0]
    return (qty, unit, len(found), mult)


def pack_candidates(title):
    """곱셈이 애매한 상품의 **두 가지 해석**을 돌려준다.

    🔴 규칙으로는 못 가른다(2026-07-20). 실제 데이터가 정반대 사례를 둘 다 준다:
         "밀가루 1kg 150개입"      → 1kg짜리가 150개  = 150kg   (곱해야 함)
         "팽이버섯 5KG 34봉(box)"  → 5kg이 박스 전체   = 5kg     (곱하면 안 됨)
       무게로도 낱개 크기로도 안 갈린다. 그래서 **같은 재료의 명확한 상품들 값과 대보고**
       더 그럴듯한 쪽을 고른다 — 판단을 규칙이 아니라 데이터에 맡긴다.
    """
    pk = parse_pack(title)
    if not pk:
        return []
    qty, unit, nopt, mult = pk
    out = [(qty, unit)]
    if mult > 1:
        base = round(qty / mult, 4)
        if 0 < base <= 50:
            out.append((base, unit))
    return out


def is_home_pack(qty, unit):
    """레시피(집밥) 축에서 쓸 만한 규격인가. 대용량은 버리지 않고 tier로만 구분한다."""
    return tier_of(qty) in ("소포장", "가정용")


# ── API ────────────────────────────────────────────────────────
def _get(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", headers={
        "X-Naver-Client-Id": CID, "X-Naver-Client-Secret": CSEC})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def search(keyword, display=40):
    """정확도순(sim) 상위 N. 🔴 sort는 절대 가격순으로 바꾸지 말 것."""
    return _get(SEARCH_URL, {"query": keyword, "display": display, "sort": "sim"})


# ── 한 재료 수집 ───────────────────────────────────────────────
def collect(keyword, base_unit):
    """정확도순 상위 N을 **전부** 규격별로 담아 돌려준다.

    돌려주는 것:
      offers  파싱된 상품 전부 (tier 붙음)  → naver_offer 테이블에 그대로 저장
      pick    레시피용 대표값 (소포장+가정용 중앙값) / 없으면 None
    """
    try:
        js = search(keyword)
    except Exception as e:
        return {"err": f"{type(e).__name__}: {e}"}
    items = js.get("items") or []
    offers = []
    for i, it in enumerate(items, 1):
        title = _TAG.sub("", it.get("title", ""))
        if any(w in title for w in NG_WORDS):
            continue
        pk = parse_pack(title)
        if not pk:
            continue            # 용량 못 뽑은 건 원/kg 계산이 불가능해서만 버린다
        qty, unit, nopt, _mult = pk
        try:
            lp = int(it.get("lprice") or 0)
        except ValueError:
            continue
        if lp <= 0:
            continue
        vf = variant_flag(keyword, title)
        offers.append({"price": lp, "pack": qty, "unit": unit, "per": lp / qty,
                       "tier": tier_of(qty, title, keyword), "title": title,
                       "mall": it.get("mallName", ""), "rank": i,
                       "pid": it.get("productId", ""), "link": it.get("link", ""),
                       "origin": origin_of(title), "grade": grade_of(title),
                       "pieces": pieces_of(title), "opt": nopt, "vf": vf,
                       # 품종이 다른 것으로 의심되면 대표값 계산에서 뺀다(표에는 남긴다)
                       "usable": 0 if vf else 1})
    if not offers:
        return {"err": "용량을 뽑을 수 있는 상품 0건", "raw": len(items), "offers": []}

    # 레시피용 대표값 — 소포장·가정용만 모아 **중앙값**.
    #  🔴 최저가가 아니다. 상위권이라도 미끼 하나가 튄다.
    #  집밥 축은 **국산**(대표님 2026-07-20: 소비자는 국산을 산다). 국산이 하나도 없으면
    #  미표기까지 받아들이되, 수입만 있는 경우는 그대로 쓴다(연어·수입육은 수입이 정상).
    _ok = [o for o in offers if o["usable"] and o["tier"] in ("소포장", "가정용")]
    home = [o for o in _ok if o["origin"] == "국산"] or \
           [o for o in _ok if o["origin"] != "수입"] or _ok
    pick = None
    if home:
        med = statistics.median(sorted(o["per"] for o in home))
        pick = min(home, key=lambda o: abs(o["per"] - med))
        pick = dict(pick, n=len(home))
    return {"offers": offers, "pick": pick, "raw": len(items),
            "by_tier": {t: sum(1 for o in offers if o["tier"] == t)
                        for t, _, _ in TIERS}}


def save_offers(con, key, keyword, offers):
    """이 재료의 이전 수집분을 지우고 새로 담는다 (재실행해도 안 쌓인다)."""
    con.execute("DELETE FROM naver_offer WHERE ingredient_key=?", (key,))
    con.executemany(
        """INSERT INTO naver_offer(ingredient_key,keyword,title,mall,price,pack_qty,
           pack_unit,per_unit,tier,rank_sim,product_id,link,origin,grade,pieces,
           opt_multi,variant_flag,usable,checked_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
        [(key, keyword, o["title"], o["mall"], o["price"], o["pack"], o["unit"],
          round(o["per"], 2), o["tier"], o["rank"], o["pid"], o["link"],
          o["origin"], o["grade"], o["pieces"], o["opt"], o["vf"], o["usable"])
         for o in offers])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--key")
    ap.add_argument("--sleep", type=float, default=0.15)
    a = ap.parse_args()

    if not CID or not CSEC:
        print("❌ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.")
        print("   (setx 직후 열린 창은 모릅니다 — 새 창에서 실행하세요)")
        sys.exit(1)

    if a.check:
        try:
            js = search("백설 밀가루", display=3)
            print(f"✅ 키 정상 — 총 {js.get('total', 0):,}건")
            for it in js.get("items", [])[:3]:
                t = _TAG.sub("", it["title"])
                print(f"   {it['lprice']:>8}원  {t}  [{parse_pack(t)}]")
        except Exception as e:
            print(f"❌ 호출 실패: {type(e).__name__}: {e}")
            sys.exit(1)
        return

    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    if a.key:
        rows = con.execute("SELECT ingredient_key k,name,base_unit bu FROM ingredients "
                           "WHERE ingredient_key=?", (a.key,)).fetchall()
    else:
        # manual(사람이 조사한 고정단가)만. live는 공공API 시세라 이미 정확하다.
        # 원가 영향 큰 순 = 실제로 쓰이는 것부터.
        # 전수(--limit 0) 또는 상위 N. live도 포함한다 — 야채·축산·수산이 거기 있고,
        # 그쪽 값이 지금 경락가라 제일 못 믿을 자리다(2026-07-20).
        # 이름에 '(경락)'·'(KAMIS)' 같은 출처 꼬리표가 붙은 건 검색어에서 떼고 던진다.
        rows = con.execute("""SELECT i.ingredient_key k, i.name, i.base_unit bu
            FROM ingredients i LEFT JOIN menu_ingredients mi USING(ingredient_key)
            WHERE i.ingredient_key<>'water' AND i.type IN ('manual','live')
            GROUP BY i.ingredient_key
            ORDER BY COALESCE(SUM(mi.line_cost),0) DESC LIMIT ?""",
            (a.limit if a.limit > 0 else 100000,)).fetchall()

    ok = ng = 0
    for i, r in enumerate(rows, 1):
        # 출처 꼬리표는 검색어가 아니다 — "한우 등심(경락)"으로 검색하면 0건이 나온다.
        kw = search_keyword(r["name"])
        res = collect(kw, r["bu"])
        if res.get("err"):
            ng += 1
            print(f"  {i:>3}. ✗ {r['name'][:20]:20} {res['err']}")
            time.sleep(a.sleep); continue
        # 규격은 대용량까지 전부 담는다 (브랜드 매입가 추정에 쓸 재료)
        save_offers(con, r["k"], kw, res["offers"])
        bt = res["by_tier"]
        tier_s = " ".join(f"{t[:2]}{bt[t]}" for t, _, _ in TIERS if bt[t])
        p = res["pick"]
        if p:
            ok += 1
            con.execute("""UPDATE ingredients SET naver_price=?, naver_pack=?, naver_unit=?,
                naver_title=?, naver_mall=?, naver_kw=?, naver_n=?,
                naver_checked_at=datetime('now','localtime') WHERE ingredient_key=?""",
                (round(p["per"]), p["pack"], p["unit"], p["title"], p["mall"],
                 kw, p["n"], r["k"]))
            print(f"  {i:>3}. ✓ {r['name'][:20]:20} {round(p['per']):>8,}원/{p['unit']}"
                  f"  [{tier_s}]  {p['title'][:30]}")
        else:
            ng += 1
            print(f"  {i:>3}. △ {r['name'][:20]:20} 가정용 규격 없음 (대용량만) [{tier_s}]")
        con.commit()
        time.sleep(a.sleep)
    tot = con.execute("SELECT COUNT(*) FROM naver_offer").fetchone()[0]
    con.close()
    print(f"\n완료 — 대표값 {ok}종 / 실패 {ng}종 · 규격 리스트 {tot:,}건 적재")
    print("→ 비교표: python scripts/naver_compare.py --html")



# ── 검색어 정리 ────────────────────────────────────────────────
# 🔴 재료명을 그대로 검색어로 쓰면 안 되는 것들이 있다(2026-07-20 실측 90종).
#    · 브랜드·용량이 붙은 이름  "해찬들 고기전용 쌈장 500g" → 그 상품 하나만 나오거나 0건
#    · 한 글자·모호한 이름       "무" → 알타리·총각·순무·레디쉬가 전부 걸림
#    · 사내 용어                "전용유" → 튀김전용유 아님, 온갖 기름
_KW_FIX = {
    # ── 2026-07-20 2차 (대표님 추가 지시) ─────────────────────
    "베이컨용햄": "베이컨",
    "머리고기순대돈족": "돼지 머리고기",     # 머리고기·순대·돈족 따로 검색해 평균
    "허니/프리미엄 소스": "허니간장소스",
    "가마로파우더": "치킨 튀김가루",
    "와플베이크믹스생지": "와플생지",
    "만두피가루": "만두피",
    "구이용밀떡": "밀떡볶이떡",
    "자숙소곱창/전골곱창": "소곱창 자숙",
    # ── 2026-07-20 대표님이 직접 불러주신 매핑 ─────────────────────
    #  원칙: "없는 걸 찾으려 하지 말고 비슷한 걸 넣어야 돼"
    #  브랜드 전용품은 시중에 없다 → 같은 성격의 일반 상품으로 대체한다.
    "쌀국수 건면": "라이스누들", "김밥용 속재료 세트": "김밥재료",
    "맑은사골액": "사골육수", "가공설렁탕액": "사골농축액",
    "백설탕(백설 1kg)": "백설탕", "전지돈육": "목전지",
    "대왕오징어(수입 냉동)": "대왕오징어", "머리고기순대돈족": "머리고기",
    "와플베이크믹스생지": "와플생지",          # 생지 = 반죽까지 된 것(믹스보다 가공됨)
    "청정원 요리한수 제육볶음양념 175g": "제육볶음양념",
    "청정원 베이컨앤크림 까르보나라소스 350g": "까르보나라소스",
    "감자탕돈뼈(수입 냉동)": "돼지등뼈", "베이컨용햄": "베이컨",
    "계란(특란)": "계란 30구", "신선 계란(개당)": "계란 30구",
    "염지닭 10호": "염지닭 10호", "만두피가루": "만두피",
    "구이용밀떡": "사리용밀떡", "필드도넛반죽생지": "도넛생지",
    "자숙소곱창/전골곱창": "소곱창", "함박고기": "함박스테이크",
    "탕수돈육등심": "돼지고기 등심", "돈육다짐만두소": "만두소",
    "허브탕수소수": "탕수육 소스", "멜론원단/시럽": "멜론시럽",
    "냉동츄러스생지": "츄러스 생지", "당침당밤조림": "밤조림",
    "브라우니조각": "브라우니", "글레이즈슈가코팅": "도넛 슈가코팅",
    "기본겉절이": "겉절이",
    # 양지 계열 — 전부 소고기 양지
    "슬라이스양지쇠고기": "소고기 양지", "양지고기": "소고기 양지",
    "양지수육고기": "소고기 양지", "소양지고기": "소고기 양지",
    "채썬쇠고기양지": "소고기 양지", "소고기 국거리/양지": "소고기 양지",
    # 국밥 다대기 계열 — 전부 국밥다대기 기반
    "사골다대기": "국밥다대기", "캡사이신다대기": "국밥다대기",
    "매운볶음다대기": "국밥다대기", "사골얼큰다대기": "국밥다대기",
    "고추장사골다대기": "국밥다대기", "된장사골다대기": "국밥다대기",
    "해장국다대기": "국밥다대기", "한식 육수 다대기": "국밥다대기",
    # 부대찌개 햄 계열
    "모둠햄": "부대찌개 모둠햄", "놀부모둠햄": "부대찌개 모둠햄",
    "부대모둠햄": "부대찌개 모둠햄", "킹콩모둠햄": "부대찌개 모둠햄",
    "프리미엄햄": "부대찌개 모둠햄", "부대찌개용 모둠햄(벌크)": "부대찌개 모둠햄",
    # 🔴 퓨레 = 과일을 걸쭉하게 한 것 = 과일시럽으로 본다(대표님).
    #    완전히 같은 물건은 아니지만 성격이 같은 상품으로 대체한다.
    "딸기과일퓨레": "딸기시럽", "블루베리과일퓨레": "블루베리시럽",
    "망고농축시럽퓨레": "망고시럽", "애플망고시럽퓨레": "망고시럽",
    "딸기복숭아믹스시럽퓨레": "딸기시럽", "냉동딸기시럽퓨레": "딸기시럽",
    "녹차시럽퓨레": "녹차시럽", "유기농녹차시럽": "녹차시럽",
    "모카칩시럽퓨레": "모카시럽", "자바칩초코퓨레": "초코시럽",
    "오레오토핑퓨레": "초코시럽", "쿨라임베이스퓨레": "라임시럽",
    "가공초코시럽": "초코시럽", "바닐라가공시럽": "바닐라시럽",
    "액상바닐라시럽": "바닐라시럽",
    # 생지 = 빵 반죽. 전부 같은 성격.
    "단과자생지": "빵생지", "단과자소보루생지": "소보루 생지",
    "데니쉬반죽생지": "데니쉬 생지", "모카브레드반죽생지": "모카빵 생지",
    "초코케익도넛생지": "도넛생지", "이스트링도넛생지": "도넛생지",
    "츄이스티타피오카생지": "도넛생지", "고로케반죽": "고로케 반죽",
    "롤스폰지케익시트": "롤케이크 시트",
    # 나머지
    "건포도/에센스": "건포도",              # 에센스는 별개 재료로 분리 예정
    "무": "무 세척무", "무(KAMIS)": "무 세척무", "파": "대파", "콩": "흰콩 백태",
    "전용유": "튀김유", "라면 사리": "라면사리 건면", "우동사리": "우동면 생면",
    "치킨무": "치킨무 절임", "핫도그 빵": "핫도그번", "버거 번": "햄버거번",
    "전분가루": "감자전분", "튀김가루": "치킨 튀김가루",   # '부침'을 붙였더니 부침가루가 잡혔다
    "통깨(볶음)": "볶음참깨", "참깨": "볶음참깨",
    "천일염": "천일염 굵은소금", "가마로파우더": "치킨 튀김가루",
}
_VOL_TAIL = re.compile(r"\s*\d+(\.\d+)?\s*(kg|g|ml|L|리터)\s*$", re.I)
_BRANDS_KW = ("해찬들", "청정원", "오뚜기", "백설", "샘표", "CJ", "대상", "동원",
              "사조", "곰곰", "풀무원", "하림", "롯데", "농심", "코다노", "친수")


def search_keyword(name):
    """DB 재료명 → 네이버에 던질 검색어."""
    n = (name or "").strip()
    if n in _KW_FIX:
        return _KW_FIX[n]
    n = re.sub(r"\s*\((경락|KAMIS|kamis|참가격|통관단가)\)\s*", " ", n).strip()
    n = re.sub(r"\s*\([^)]*\)\s*", " ", n).strip()   # 괄호 주석 제거
    n = _VOL_TAIL.sub("", n).strip()                  # 끝의 용량 제거
    for b in _BRANDS_KW:                              # 앞의 브랜드 제거
        if n.startswith(b):
            n = n[len(b):].strip()
            break
    return _KW_FIX.get(n, n) or (name or "")


# ── 관련성 검사 ────────────────────────────────────────────────
# 🔴 검색 결과가 재료와 다른 물건인 경우가 많다(2026-07-20 대표님 지적).
#    "한식 육수 다대기"로 찾았는데 육수만 나오고 다대기가 없는 식이다.
#    상품명에 재료의 핵심 낱말이 하나도 없으면 그건 다른 물건이다 — 값을 쓰지 않는다.
_KW_STOP = {"국산", "국내산", "수입", "냉동", "냉장", "신선", "기본", "일반", "생",
            "한식", "용", "및", "기타", "세트", "믹스", "가공", "시판", "개당",
            # 🔴 일반 수식어는 '주인'이 될 수 없다 — '족발 생육'의 주인은 족발이다.
            #    이걸 안 빼면 머리말이 '생육'이 되어 멀쩡한 족발 상품을 전부 잘라낸다.
            "생육", "정육", "원육", "벌크", "파지", "손질", "절단", "슬라이스",
            "냉동벌크", "자숙", "구이용", "찌개용", "볶음용", "국거리"}


def core_tokens(name):
    """재료명에서 검색 대조에 쓸 핵심 낱말들."""
    n = re.sub(r"\([^)]*\)", " ", name or "")
    n = re.sub(r"\d+(\.\d+)?\s*(kg|g|ml|L|리터)", " ", n, flags=re.I)
    n = re.sub(r"[·/+,]", " ", n)
    out = []
    for w in n.split():
        w = w.strip()
        if len(w) >= 2 and w not in _KW_STOP:
            out.append(w)
    return out


def is_relevant(name, title):
    """상품명이 재료와 같은 물건인가.

    한국어는 **끝말이 주인**이다 — '한식 육수 다대기'의 주인은 다대기지 육수가 아니다.
    앞말만 맞춰 통과시키면 다대기 자리에 육수가 들어온다(2026-07-20 대표님 지적).
    그래서 **마지막 핵심 낱말**이 상품명에 있어야 같은 물건으로 본다.
    """
    toks = core_tokens(name)
    if not toks:
        return True
    t = re.sub(r"\s+", "", title or "")
    head = toks[-1]
    if head in t:
        return True
    if len(head) >= 3 and (head[:-1] in t or head[1:] in t):   # 어미 한 글자 차이
        return True
    whole = "".join(toks)                                       # 붙여쓴 이름도 대조
    return len(whole) >= 3 and whole in t

if __name__ == "__main__":
    main()
