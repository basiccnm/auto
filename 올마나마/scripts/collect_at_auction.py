# -*- coding: utf-8 -*-
# aT 전국 공영도매시장 실시간 경매 → 품목별 도매 경락가 (2026-07-20)
#
# 왜: 우리 농산 도매가는 KAMIS 품목당 대표값 하나뿐이었다. 이 API는 전국 청과 도매시장의
#     **개별 낙찰 기록**을 하루 12만 건 준다 → 품목별 실거래 중앙값을 낼 수 있다.
#
# ⚠️ 실측 확인 (2026-07-20, 표본 4,000건)
#  1. 대분류는 **전부 농산물**이다(과실·엽경채·과채·버섯·조미채소·근채·서류·잡곡·두류…).
#     수산물은 이 API에 **없다**. 시장도 청과시장뿐(노량진 없음) — 수산은 위판장 API 담당.
#  2. numOfRows는 **최대 1000**. 3000을 요청해도 1000만 온다 → 페이지를 끝까지 돈다.
#  3. 가격 계산: `scsbd_prc`(단량당 낙찰가) ÷ `unit_qty`(단위물량) = 원/kg.
#     unit_nm이 'kg'인 행만 쓴다. 다른 단위가 섞이면 환산이 어긋난다(우유 42건 사고 유형).
#  4. 같은 품목도 품종·산지·시장에 따라 편차가 크다(깻잎 2,500 vs 11,550원/kg).
#     → 평균이 아니라 **중앙값**을 쓰고, 표본이 적으면 아예 싣지 않는다.
#
# 🔴 기존 원가 계산은 건드리지 않는다: 새 재료(at_*)로만 추가하고 메뉴에 연결하지 않는다.
#
# 사용법: python scripts/collect_at_auction.py
import json, os, sqlite3, statistics, sys, urllib.parse, urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publicdata.config import EKAPE_KEY, SSL_CTX

BASE = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eolmanama.db")

PAGE = 1000        # API 상한
MAX_PAGES = 200    # 12만 건 기준 여유
MIN_SAMPLES = 5    # 이보다 적은 품목은 대표값으로 못 쓴다

# ── A단계 마스터 청소와 세트 (cleanup_master_20260720.py, 2026-07-20) ──
# 통계 집계행(재료가 아님) — 시세표에 '기타채소 도매' 같은 유령 품목을 만든다.
EXCLUDE_ITEMS = {"기타", "기타과채", "기타근채류", "기타두류", "기타버섯", "기타버섯류",
                 "기타양채", "기타양채류", "기타엽경채류", "기타엽채", "기타엽채류",
                 "기타채소", "양상추기타", "엽경채기타", "엽경채류(기타)", "채소기타",
                 "신선해조류", "약용작물류", "수입양채",
                 # 2차 청소(2026-07-20 reclassify_fine): 집계행 추가분
                 "곡물제조", "농림가공", "농림가공류", "전분및사료제조", "묵류", "두부류",
                 "두류", "서류", "잡곡류", "수산가공류", "과일과채류", "감귤류", "과실류",
                 # 채소 집계행(3차 눈검사에서 발견, 2026-07-20)
                 "과채류", "근채류", "산채류", "쌈채류", "양채류", "엽경채류", "조미채류",
                 "조미채소류", "전처리",
                 "버섯", "버섯류", "고추"}   # 뭉뚱그림 — 양송이/느타리, 꽈리/풋/붉은이 따로 있다
# 같은 품목의 표기 변형 — 키가 갈라져 중복 행이 되는 걸 원천 통합.
ITEM_ALIAS = {"가지(표준)": "가지", "강낭콩(울타리콩)": "강낭콩",
              "고구마순(줄기)": "고구마순", "고구마순(표준)": "고구마순",
              "고추(꽈리고추)": "꽈리고추", "고추(풋고추)": "풋고추", "고추(붉은고추)": "붉은고추",
              "귤(일반)": "귤", "깻잎(표준)": "깻잎", "무청(무시래기)": "무청",
              "바나나(수입)": "바나나", "버섯(양송이)": "양송이버섯", "버섯(느타리)": "느타리버섯",
              "복숭아(표준)": "복숭아", "블루베리(일반)": "블루베리", "비트(붉은사탕무우)": "비트",
              "자두(표준)": "자두", "자몽(수입)": "자몽", "참다래(키위)": "참다래",
              "콩(콩)": "콩", "콩(강낭콩)": "강낭콩", "파(대파)": "파",
              "파세리(향미나리)": "파세리", "파인애플(수입)": "파인애플", "피망(단고추)": "피망",
              # API가 이름을 자르는 품목(브로콜리 철자 변형 2종 → 하나로)
              "브로코리(녹색꽃양배": "브로콜리", "브로콜리(녹색꽃양배": "브로콜리",
              # 버섯 이름변형(축약형 → 정식명)
              "느타리": "느타리버섯", "새송이": "새송이버섯", "팽이": "팽이버섯", "표고": "표고버섯",
              # 표기 변형(2026-07-20 3차)
              "무우": "무", "알타리무우": "알타리무",
              "브로커리": "브로콜리", "브로코리": "브로콜리",
              "아스파라가스": "아스파라거스", "세러리": "셀러리(양미나리)",
              "칼라후라워": "칼리플라워(꽃양배추)", "칼리후라워": "칼리플라워(꽃양배추)"}

# ★ 한 품목 한 줄: kv/마트 재료에 짝이 있는 aT 품목 → 그 재료의 도매 컬럼으로 (2026-07-20)
#   cleanup_master2_20260720.py가 기존 at_ 행을 병합·삭제했다. 목록 갱신 시 둘을 같이 고칠 것.
KV_WHOLESALE_TARGET = {
    "감자": "kv_152", "건고추": "kv_241", "고구마": "kv_151", "깻잎": "kv_253",
    "느타리버섯": "kv_315", "당근": "kv_232", "레몬": "kv_424", "무": "mu_mart",
    "미나리": "kv_252", "바나나": "kv_418", "방울토마토": "kv_422", "배": "kv_412",
    "배추": "baechu_mart", "복숭아": "kv_413", "붉은고추": "kv_243", "사과": "kv_411",
    "상추": "kv_214", "새송이버섯": "kv_317", "생강": "kv_247", "숙주나물": "sukju_mart",
    "시금치": "kv_213", "애호박": "aehobak_mart", "양배추": "yangbaechu_mart", "양파": "kv_245",
    "얼갈이배추": "kv_215", "열무": "kv_233", "오렌지": "kv_421", "오이": "kv_223",
    "참다래": "kv_419", "참외": "kv_222", "체리": "kv_425", "콩": "kv_141",
    "콩나물": "kongnamul_mart", "토마토": "kv_225", "파": "kv_246", "파프리카": "kv_256",
    # 팽이버섯 제외(2026-07-20): kv_316 KAMIS 소매값이 단위 불명(532)이라 경락 kg와 역전 발생
    "포도": "kv_414", "풋고추": "kv_242", "피망": "kv_255",
}


def fetch(day, page):
    q = {"serviceKey": EKAPE_KEY, "returnType": "JSON", "numOfRows": str(PAGE),
         "pageNo": str(page), "cond[trd_clcln_ymd::EQ]": day}
    url = BASE + "?" + urllib.parse.urlencode(q, safe=":[]")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=90, context=SSL_CTX).read().decode("utf-8")
    body = json.loads(raw).get("response", {}).get("body", {})
    items = body.get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    return body.get("totalCount", 0), (items or [])


def main():
    # 최근 거래정산일자를 역탐색 (주말·공휴일은 경매가 없다)
    day, total = None, 0
    for back in range(1, 8):
        d = (date.today() - timedelta(days=back)).strftime("%Y-%m-%d")
        try:
            total, items = fetch(d, 1)
        except Exception as e:
            print(f"  {d} 호출 실패: {type(e).__name__}"); continue
        # 휴일·주말엔 거래가 몇 건만 있는 날이 있다(2026-07-19 실측: 2건).
        #  그런 날을 잡으면 대표값이 안 나오므로 **실질 거래일**만 채택한다.
        if total and total >= 500 and items:
            day = d; break
        if total:
            print(f"  {d}: {total}건뿐 — 건너뜀")
    if not day:
        print("aT 경매: 최근 데이터 없음 — 중단"); return

    prices = defaultdict(list)
    lcls = defaultdict(Counter)   # 품목 → 대분류 빈도
    got = 0
    for p in range(1, MAX_PAGES + 1):
        try:
            _, items = fetch(day, p)
        except Exception as e:
            print(f"  page {p} 실패({type(e).__name__}) — 여기까지로 집계"); break
        if not items:
            break
        got += len(items)
        for r in items:
            if (r.get("unit_nm") or "").strip().lower() != "kg":
                continue
            try:
                prc = float(r.get("scsbd_prc") or 0)
                uq = float(r.get("unit_qty") or 0)
            except ValueError:
                continue
            if prc <= 0 or uq <= 0:
                continue
            per_kg = prc / uq
            if not (10 <= per_kg <= 500000):     # 명백한 이상치 제외
                continue
            nm = (r.get("corp_gds_item_nm") or "").strip()
            nm = ITEM_ALIAS.get(nm, nm)          # 이름 변형 통합(가지(표준)→가지 등)
            if nm and nm not in EXCLUDE_ITEMS:   # 통계 집계행(기타류 등)은 재료가 아니다
                prices[nm].append(per_kg)
                # 응답이 주는 대분류를 그대로 하위 분류로 쓴다(이름으로 추측 금지).
                lcls[nm][(r.get("gds_lclsf_nm") or "").strip()] += 1
        if got >= total:
            break

    # aT 대분류 → 사이트 하위 분류("대분류/하위" 전체형 — 2026-07-20 A단계 통일).
    #  매핑에 없는 건 '기타'로 두고 억지로 끼워넣지 않는다.
    SUB = {"과실류": "농산물/과일", "과일과채류": "농산물/과일", "과채류": "농산물/채소",
           "엽경채류": "농산물/채소", "조미채소류": "농산물/채소", "양채류": "농산물/채소",
           "근채류": "농산물/채소", "산채류": "농산물/채소",
           # 서류(감자·고구마)는 마트 기준 채소 코너 (2026-07-20 사용자 세분화 지시)
           "서류": "농산물/채소", "잡곡류": "농산물/곡물", "두류": "농산물/곡물",
           "버섯류": "농산물/버섯·견과", "특용작물류": "농산물/버섯·견과",
           "신선 해조류": "수산물/해조류", "수산가공": "수산물/기타",
           "농림가공": "가공식품/기타", "약용작물류": "기타", "관엽식물류": "기타", "초화류": "기타",
           "농산물종자류": "기타", "인삼류": "기타", "산림종묘": "기타", "난류": "기타"}
    con = sqlite3.connect(DB); cur = con.cursor()
    n = 0
    for nm, vals in prices.items():
        if len(vals) < MIN_SAMPLES:
            continue
        med = round(statistics.median(vals))
        # ★ 한 품목 한 줄 (2026-07-20 사용자 지시): kv/마트 재료에 짝이 있으면 별도 at_ 행을
        #   만들지 않고 그 재료의 도매 컬럼만 갱신한다. (cleanup_master2가 기존 행 병합 완료)
        if nm in KV_WHOLESALE_TARGET:
            cur.execute("""UPDATE ingredients SET wholesale_price=?, wholesale_basis='at_auction',
                updated_at=datetime('now') WHERE ingredient_key=?""",
                (med, KV_WHOLESALE_TARGET[nm]))
            n += 1
            continue
        key = "at_" + nm
        cur.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,
            wholesale_price,wholesale_basis,base_unit,markup_factor,is_retail,updated_at)
            VALUES(?,?,'농축산물','live',?,?,'at_auction','kg',1.0,0,datetime('now'))
            ON CONFLICT(ingredient_key) DO UPDATE SET
              manual_price=excluded.manual_price, wholesale_price=excluded.wholesale_price,
              type='live', updated_at=datetime('now')""",
            (key, f"{nm}(경락)", med, med))   # 이름에서 '도매' 제거(2026-07-20) — 경락 마커만
        top = lcls[nm].most_common(1)[0][0] if lcls[nm] else ""
        cur.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=?", (SUB.get(top, "기타"), key))
        cur.execute("DELETE FROM price_history WHERE ingredient_key=? AND price_date=?", (key, day))
        cur.execute("""INSERT INTO price_history(ingredient_key,price_date,retail_price,
            wholesale_price,source,created_at) VALUES(?,?,?,?,'at_auction',datetime('now'))""",
            (key, day, med, med))   # 경락가는 도매지만 표시용 대표가로도 같은 값을 쓴다
                                     # (price_history.retail_price가 NOT NULL 제약)
        n += 1
    con.commit(); con.close()
    print(f"aT 경매 {day}: {got:,}건 수집 → 품목 {n}종 (표본 {MIN_SAMPLES}건 이상만)")


if __name__ == "__main__":
    main()
