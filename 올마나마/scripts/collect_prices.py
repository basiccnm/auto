# KAMIS 실시세 수집기 (얼마남아 publicdata ETL)
# live/live_composite 재료의 소매가를 KAMIS에서 가져와 price_history에 저장.
# 매일 크론으로 실행 예정. 단위는 kg/L 기준으로 정규화.
# 단위 환산·등급 선택 규칙은 kamis_kg 모듈 주석 참조.
#
# 사용법: python collect_prices.py [YYYY-MM-DD]  (날짜 생략 시 최근 영업일)
import json
import os
import re
import ssl
import sqlite3
import sys
import urllib.request

from collect_wholesale import LIVESTOCK_CAT, VEG_CAT, wholesale_of
from kamis_kg import RETAIL, WHOLESALE, fetch_many

CERT_KEY_EKAPE = os.environ.get("EKAPE_KEY", "01d41ee31954bf8a99a618c1c206dd53aff2ce5fe2e53cec92fd3bd371e70dda")
DB_PATH = os.environ.get("EOLMANAMA_DB", r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db")

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

CHICKEN_KEYS = {"raw_chicken_10", "chicken_parts", "chicken_boneless"}

# 축평원 닭 육계. 부위/등급을 직접 특정한다 — min() 대표가 금지(설계서 §8.3-5).
CHICKEN_JUDGE_KIND = "9901"
CHICKEN_ITEM = ("99", "구분없음")  # (itemCd, grdNm) = 육계(kg) / 등급 구분없음

# 축평원 unit → 원/kg(원/L) 계수
_EKAPE_UNIT_FACTOR = {"원/kg": 1.0, "원/1kg": 1.0, "원/100g": 10.0, "원/500g": 2.0,
                      "원/1l": 1.0, "원/l": 1.0}


def ekape_chicken(regday):
    """축평원 닭 육계 소비자가격 (원/kg). KAMIS 닭(9901)이 0을 주는 문제 대체.

    ⚠️ 응답에 standYmd='평년'(과거 평균 기준선) 행이 요청일자 행과 함께 내려온다.
       예전 코드는 min(ntslPrc)를 취해 항상 더 싼 '평년'값을 실시세로 기록했다.
       (실측 2026-07-10: 실제 6,200 / 평년 5,882 → min이 평년을 채택)
       → 요청일자와 일치하는 행만 채택할 것. 설계서 §8.3-2
    """
    ymd = regday.replace("-", "")
    url = ("http://data.ekape.or.kr/openapi-data/service/user/grade/consumerPriceDaily"
           f"?serviceKey={CERT_KEY_EKAPE}&standYmd={ymd}&judgeKind={CHICKEN_JUDGE_KIND}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        body = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8")
    except Exception:
        return None
    if not re.search(r"<resultCode>0*0</resultCode>", body):
        return None
    for m in re.finditer(r"<item>(.*?)</item>", body, re.S):
        blk = m.group(1)

        def f(tag):
            g = re.search(rf"<{tag}>(.*?)</{tag}>", blk, re.S)
            return g.group(1).strip() if g else ""

        if f("standYmd") != ymd:            # ★ '평년' 기준선 행 배제
            continue
        if (f("itemCd"), f("grdNm")) != CHICKEN_ITEM:   # ★ 부위/등급 직접 특정
            continue
        factor = _EKAPE_UNIT_FACTOR.get(f("unit").lower())
        raw = f("ntslPrc")
        if factor is None or not raw.isdigit() or int(raw) <= 0:
            continue
        return round(int(raw) * factor)
    return None


def recent_bizday():
    # 간단히 어제 날짜 사용(주말 보정은 KAMIS가 최근값 반환하므로 생략 가능)
    import datetime  # noqa (크론 환경용, 로컬 실행 전용)
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def retail_of(catmap, typ, kcat, kcode, comp):
    """재료 1건의 원/kg 소매가. 값 없으면 None."""
    if typ == "live" and kcat and kcode:
        return catmap.get(kcat, {}).get(kcode)
    if typ == "live_composite" and comp:
        veg = catmap.get(VEG_CAT, {})
        vals = [veg[p["code"]] * p["w"] for p in json.loads(comp) if veg.get(p["code"])]
        return round(sum(vals)) if vals else None
    return None


def main():
    regday = sys.argv[1] if len(sys.argv) > 1 else recent_bizday()
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    ings = cur.execute(
        "SELECT ingredient_key,type,kamis_cat,kamis_item_code,composite_formula,markup_factor "
        "FROM ingredients WHERE type IN ('live','live_composite')").fetchall()

    # 필요한 카테고리 미리 조회(캐시)
    retail_cats, whole_cats = set(), set()
    for _, typ, kcat, _, comp, _ in ings:
        if typ == "live" and kcat:
            retail_cats.add(kcat)
            if kcat != LIVESTOCK_CAT:   # 축산은 도매 없음 → 조회 자체를 안 함
                whole_cats.add(kcat)
        if typ == "live_composite" and comp:
            retail_cats.add(VEG_CAT); whole_cats.add(VEG_CAT)
    catprice = fetch_many(retail_cats, RETAIL, regday)      # 소매
    catwhole = fetch_many(whole_cats, WHOLESALE, regday)    # 도매
    chicken_perkg = ekape_chicken(regday)  # 축평원 닭 육계 (원/kg, 소매)

    n = 0
    for key, typ, kcat, kcode, comp, markup in ings:
        retail = chicken_perkg if (key in CHICKEN_KEYS and chicken_perkg) else \
            retail_of(catprice, typ, kcat, kcode, comp)
        whole = wholesale_of(catwhole, typ, kcat, kcode, comp)  # 축산·닭은 None
        if retail is None and whole is None:
            continue
        r = round(retail * (markup or 1.0)) if retail else None
        w = round(whole * (markup or 1.0)) if whole else None
        if r and w and w >= r:
            # 도매 ≥ 소매는 환산/등급 오류의 신호. 조용히 저장하지 말고 드러낸다.
            print(f"    [경고] {key}: 도매 {w} >= 소매 {r} — 도매 기록 보류")
            w = None
        cur.execute(
            "INSERT OR REPLACE INTO price_history (ingredient_key,price_date,retail_price,wholesale_price,source,created_at) "
            "VALUES (?,?,?,?,?,datetime('now'))", (key, regday, r, w, "kamis"))
        n += 1
        print(f"  {key}: 소매 {r} / 도매 {w} (원/kg, {regday})")
    con.commit(); con.close()
    print(f"저장 완료: {n}건 ({regday})")


if __name__ == "__main__":
    main()
