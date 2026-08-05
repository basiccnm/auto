# -*- coding: utf-8 -*-
# 관세청 품목별 국가별 수출입실적 → 수입 육류 통관단가 (2026-07-20)
#
# 왜: 우리 재료의 상당수가 **수입 냉동육**인데(수입 삼겹살·돼지 등심·소고기 다짐육 등),
#     공공 시세가 없어 전부 '조사 고정단가'였다. 축평원은 국산 경락만 주고, KAMIS도 국내 소매다.
#     관세청 통관실적이면 **수입 육류 단가의 유일한 공공 근거**가 된다.
#
# 🔴 이건 '시세'가 아니라 **통관단가**다 — 관세·운임·창고·유통마진이 붙기 **전** 값이다.
#    실측(2026-05): 미국산 냉동 돼지 $3.21/kg ≈ 4,435원인데 우리 조사 소매가는 9,000원.
#    2배 차이가 정상이다. 화면에 반드시 "수입 통관단가"로 표기하고 소매가와 섞지 말 것.
#
# ⚠️ API 특성 (문서 + 2026-07-20 실호출로 확인)
#   · cntyCd(국가코드)가 **필수** → 국가별로 따로 호출해야 한다. 주요 수입국만 돈다.
#   · 조회기간은 1년 이내. 갱신은 **월 1회**.
#   · 응답에 '총계' 행이 섞여 온다(year='-') → 반드시 걸러낼 것.
#   · HS 4자리로 조회하면 하위 6자리 세부코드별로 여러 행이 온다.
#
# 사용법: python scripts/collect_customs_meat.py
import os, sqlite3, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publicdata.config import EKAPE_KEY, SSL_CTX

BASE = "http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eolmanama.db")

# 🔴 환율은 반드시 **당일 실환율**을 쓴다(2026-07-20 사용자 지적).
#    고정 1380을 박아뒀더니 실제 1,486원과 7% 차이 났다 = 통관단가가 통째로 7% 저평가.
#    두 곳을 받아 교차검증하고, 어긋나거나 못 받으면 마지막으로 성공한 값을 재사용한다.
#    (지어낸 환율로 계산하느니 어제 환율이 낫다)
FX_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "research", "fx_usdkrw.json")


def fetch_fx():
    import json as _json
    got = []
    for url, path in (("https://api.frankfurter.app/latest?from=USD&to=KRW", ("rates", "KRW")),
                      ("https://open.er-api.com/v6/latest/USD", ("rates", "KRW"))):
        try:
            d = _json.loads(urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=20, context=SSL_CTX).read().decode())
            v = d
            for k in path:
                v = v.get(k)
            v = float(v)
            if 800 < v < 3000:            # 명백한 이상치 방어
                got.append(v)
        except Exception:
            pass
    if len(got) == 2 and abs(got[0] - got[1]) / got[0] > 0.02:
        got = got[:1]                     # 2% 넘게 어긋나면 첫 출처만 신뢰
    if got:
        rate = round(sum(got) / len(got), 2)
        try:
            with open(FX_CACHE, "w", encoding="utf-8") as f:
                _json.dump({"rate": rate, "date": date.today().isoformat(),
                            "sources": len(got)}, f, ensure_ascii=False)
        except Exception:
            pass
        return rate, date.today().isoformat()
    try:                                   # 못 받으면 마지막 성공값
        with open(FX_CACHE, encoding="utf-8") as f:
            c = _json.load(f)
        print(f"  ⚠️ 환율 조회 실패 — 캐시 사용({c['rate']} / {c['date']})")
        return float(c["rate"]), c["date"]
    except Exception:
        raise SystemExit("환율을 못 구해 중단합니다. 틀린 환율로 단가를 만들 수는 없습니다.")

# (HS 4자리, 표시명) — 식자재로 쓰는 육류만
HS_ITEMS = [("0201", "수입 소고기(신선·냉장)"), ("0202", "수입 소고기(냉동)"),
            ("0203", "수입 돼지고기"), ("0207", "수입 닭·가금육")]
# 주요 수입국만 (전 국가를 돌면 호출이 수백 번이 된다)
COUNTRIES = {"US": "미국", "AU": "호주", "ES": "스페인", "BR": "브라질",
             "NL": "네덜란드", "CA": "캐나다", "CL": "칠레", "TH": "태국"}
MIN_KG = 10000     # 이보다 적은 물량은 대표성이 없다


def call(hs, cnty, yymm):
    q = {"serviceKey": EKAPE_KEY, "strtYymm": yymm, "endYymm": yymm, "hsSgn": hs, "cntyCd": cnty}
    req = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=40, context=SSL_CTX).read().decode("utf-8")
    return ET.fromstring(raw)


def main():
    # 갱신이 월 1회 + 공표 지연이 있어 최근 달부터 거슬러 찾는다.
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(4):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        months.append(f"{y}{m:02d}")

    USD_KRW, fx_date = fetch_fx()
    print(f"  환율 USD/KRW = {USD_KRW:,} ({fx_date} 기준)")
    con = sqlite3.connect(DB); cur = con.cursor()
    n = 0
    for hs, label in HS_ITEMS:
        best = None            # (총중량, 총금액, 기준월)
        for yymm in months:
            tot_w = tot_d = 0.0
            for cc in COUNTRIES:
                try:
                    root = call(hs, cc, yymm)
                except Exception:
                    continue
                for it in root.findall(".//item"):
                    g = lambda t: (it.findtext(t) or "").strip()
                    if g("year") in ("", "-"):      # '총계' 행 제외
                        continue
                    try:
                        w, d = float(g("impWgt") or 0), float(g("impDlr") or 0)
                    except ValueError:
                        continue
                    if w >= MIN_KG:
                        tot_w += w; tot_d += d
                time.sleep(0.2)
            if tot_w > 0:
                best = (tot_w, tot_d, yymm); break     # 데이터가 있는 최근 달 채택
        if not best:
            print(f"  {label}: 데이터 없음"); continue
        w, d, yymm = best
        krw = round(d / w * USD_KRW)                   # 물량가중 평균 단가
        key = f"cs_{hs}"
        day = f"{yymm[:4]}-{yymm[4:]}-01"
        cur.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,
            wholesale_price,wholesale_basis,base_unit,markup_factor,is_retail,subcat,updated_at)
            VALUES(?,?,'농축산물','live',?,?,'customs','kg',1.0,0,'축산',datetime('now'))
            ON CONFLICT(ingredient_key) DO UPDATE SET
              manual_price=excluded.manual_price, wholesale_price=excluded.wholesale_price,
              subcat='축산', type='live', updated_at=datetime('now')""",
            (key, f"{label} 통관단가", krw, krw))
        cur.execute("DELETE FROM price_history WHERE ingredient_key=? AND price_date=?", (key, day))
        cur.execute("""INSERT INTO price_history(ingredient_key,price_date,retail_price,
            wholesale_price,source,created_at) VALUES(?,?,?,?,'customs',datetime('now'))""",
            (key, day, krw, krw))
        n += 1
        print(f"  {label} {yymm}: {w:,.0f}kg · {krw:,}원/kg (${d/w:.2f}, 환율 {USD_KRW})")
    con.commit(); con.close()
    print(f"관세청 수입 육류: {n}종 갱신")


if __name__ == "__main__":
    main()
