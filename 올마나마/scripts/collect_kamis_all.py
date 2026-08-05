# -*- coding: utf-8 -*-
# KAMIS 전 카테고리 시세 통째 수집 → ingredients(kv_*) / price_history (2026-07-20)
#
# 방침(사용자 확정 2026-07-19): **품목을 고르지 말고 다 넣는다.**
#   "시세표로 보게 우리 재료랑 다르게 넣으면 되지 않아?" → 우리 원가 계산에 쓰는 재료와
#   분리된 **독립 시세표**다. 메뉴에 연결하지 않으므로 원가·원가율에 영향이 없고,
#   "양파 시세" "고등어 시세" 같은 검색 유입을 받는 콘텐츠 역할을 한다.
#
# 품목표를 코드에 박지 않는다 — **응답이 주는 item_code/item_name을 그대로 쓴다**.
#   (문서화된 dailyPriceByCategoryList에 category 값만 바꿔 조회. 경로 추측 금지 원칙 준수)
#
# 이름 충돌 처리: 우리 재료에 이미 같은 이름이 있으면 "(KAMIS)"를 붙인다.
#   예) 우리 '김'=김밥용 마른김 54,000원/kg vs KAMIS '김'=1,426원/kg → 전혀 다른 물건이라
#       같은 이름으로 두면 사이트가 거짓말을 하게 된다.
#
# 사용법: python scripts/collect_kamis_all.py
import json, os, ssl, sqlite3, sys, urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kamis_kg as K

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# KAMIS 카테고리 (100 식량작물 / 200 채소류 / 300 특용작물 / 400 과일류 / 500 축산물 / 600 수산물)
CATS = ["100", "200", "300", "400", "500", "600"]

# 이미 다른 키로 연동 중인 시계열 — 중복 행 방지 (A단계 청소와 세트, 2026-07-20)
#  9908 우유: collect_prices.py가 'milk' 키로 매일 수집한다. kv_9908을 또 만들면 시세표에 2줄.
#  641 김: KAMIS 김은 장(枚) 단위라 kg 환산 불가 — 1,426원/kg처럼 왜곡 기록됨(2026-07-20 삭제).
#          우리 '김'(김밥김 실조사 52,522원/kg)만 유지.
#  4301 '소'/4304 '돼지': 안심~갈비 여러 부위를 한 품목으로 묶은 KAMIS 응답이라 '최저 부위값'이
#          대표가처럼 보이는 무의미한 행(소 46,440=설도 1등급). 부위별은 축평원 ek_*가 담당.
#          (다른 재료들이 kamis_item_code로 이 코드를 참조하는 건 별개 — collect_prices 경로)
#  9903 계란: 개수로 세는 재료다. KAMIS 응답의 단위가 회차마다 한 판(30개)↔kg으로 뒤바뀌는데
#          아래 upsert가 base_unit을 매번 덮어써서, 시세가 아니라 단위가 바뀐 것이
#          7/19 7,042 → 7/21 4,081 (-42%)처럼 폭락으로 찍혔다(2026-07-22 삭제).
#          계란은 조사 고정단가 'egg_fresh'(개당) 하나만 쓴다. ⚠️ 개수 단위 재료에 KAMIS 금지.
EXCLUDE_CODES = {"9908", "641", "4301", "4304", "9903"}

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def item_names(cat, day):
    """{item_code: item_name} — 응답에서 직접 뽑는다(하드코딩 금지)."""
    url = K._url(cat, K.RETAIL, day, "N")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=25, context=_CTX).read().decode("utf-8"))
    except Exception:
        return {}
    rows = d.get("data", {}).get("item") if isinstance(d.get("data"), dict) else d.get("data")
    out = {}
    for r in (rows or []):
        if isinstance(r, dict) and r.get("item_code") and r.get("item_name"):
            out.setdefault(r["item_code"], r["item_name"].strip())
    return out


def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
    # 우리 재료(비 kv_)의 이름 집합 — 충돌 시 접미사를 붙이기 위함
    ours = {r[0] for r in cur.execute(
        "SELECT name FROM ingredients WHERE ingredient_key NOT LIKE 'kv!_%' ESCAPE '!'").fetchall()}
    total = 0
    for cat in CATS:
        prices, used = {}, None
        for back in range(1, 8):
            day = (date.today() - timedelta(days=back)).strftime("%Y-%m-%d")
            got = K.fetch_category(cat, K.RETAIL, day, with_units=True)
            if got:
                prices, used = got, day
                break
        if not prices:
            print(f"  {cat}: 데이터 없음"); continue
        names = item_names(cat, used)
        whole = K.fetch_category(cat, K.WHOLESALE, used)
        n = 0
        for code, pu in prices.items():
            if code in EXCLUDE_CODES:
                continue           # 다른 키로 이미 연동된 시계열(우유 등)
            p, unit = pu           # (가격, 'kg' 또는 '개'/'마리'/'손'/'포기'/'단')
            if not isinstance(p, (int, float)) or p <= 0:
                continue
            name = names.get(code)
            if not name:
                continue          # 이름을 모르면 넣지 않는다(코드만 뜬 행은 화면에 못 쓴다)
            key = f"kv_{code}"
            disp = f"{name}(KAMIS)" if name in ours else name
            w = whole.get(code)
            # 소매가 개수 단위면 kg 도매와 단위가 달라 비교 불능 → 도매는 비워 둔다.
            if unit != "kg":
                w = None
            # 도매 ≥ 소매면 단위 환산이 어긋난 것 → 도매는 비워 둔다(억지 보정 금지).
            if isinstance(w, (int, float)) and w > 0 and w >= p:
                w = None
            cur.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,kamis_cat,
                kamis_item_code,manual_price,base_unit,markup_factor,is_retail,updated_at)
                VALUES(?,?,'농축산물','live',?,?,?,?,1.0,0,datetime('now'))
                ON CONFLICT(ingredient_key) DO UPDATE SET
                  name=excluded.name, manual_price=excluded.manual_price,
                  base_unit=excluded.base_unit, type='live', updated_at=datetime('now')""",
                (key, disp, cat, code, round(p), unit))
            # 도매 갱신: 새 값이 있으면 kamis 기준으로 덮고, 없으면 kamis 것만 지운다.
            #  (researched 등 수동 조사 도매를 None으로 밀어버리면 안 된다 — 2026-07-20)
            wv = round(w) if isinstance(w, (int, float)) and w > 0 else None
            if wv is not None:
                cur.execute("UPDATE ingredients SET wholesale_price=?, wholesale_basis='kamis' WHERE ingredient_key=?", (wv, key))
            else:
                cur.execute("""UPDATE ingredients SET wholesale_price=NULL, wholesale_basis=NULL
                    WHERE ingredient_key=? AND COALESCE(wholesale_basis,'kamis')='kamis'""", (key,))
            cur.execute("DELETE FROM price_history WHERE ingredient_key=? AND price_date=?", (key, used))
            cur.execute("""INSERT INTO price_history(ingredient_key,price_date,retail_price,
                wholesale_price,source,created_at) VALUES(?,?,?,?,'kamis',datetime('now'))""",
                (key, used, round(p), round(w) if isinstance(w, (int, float)) and w > 0 else None))
            n += 1
        total += n
        print(f"  KAMIS {cat} {used}: {n}종")
    # 메뉴에 실제로 쓰이는 재료는 도매가가 없으면 원가표의 '도매 합계'가 비어 healthcheck가 잡는다.
    #  KAMIS가 도매를 안 주는 품목(계란 등)은 사이트 표준 추정계수 0.85 (2026-07-20 대표님 확정)을 적용한다.
    #  ⚠️ 메뉴에 안 쓰이는 시세표 전용 품목에는 적용하지 않는다 — 없는 도매가를 지어내면 안 된다.
    fixed = cur.execute("""UPDATE ingredients SET wholesale_price=CAST(manual_price*0.85 AS INT),
        wholesale_basis='estimated'
        WHERE (wholesale_price IS NULL OR wholesale_price=0) AND manual_price>0
          AND ingredient_key IN (SELECT DISTINCT ingredient_key FROM menu_ingredients)""").rowcount
    #  🔴 2026-07-22 추가 — 도매 > 소매 역전 자동 교정.
    #  KAMIS는 manual_price(소매)만 갱신하고 wholesale_price는 손대지 않는다. 그래서 시세가
    #  내려가면 예전 계수로 계산해둔 도매가가 그대로 남아 소매보다 커진다(실제로 7건 발생,
    #  계란 소매 4,081 < 도매 4,929). healthcheck '도매>소매 역전'이 여기서 걸린다.
    #  → 근거란에 적힌 계수를 다시 적용해 도매를 재계산한다. 계수를 못 찾으면 농축산물 0.70.
    import re as _re
    inv = cur.execute("""SELECT ingredient_key k, manual_price mp, wholesale_basis wb
        FROM ingredients WHERE wholesale_price>manual_price AND manual_price>0""").fetchall()
    for r in inv:
        m = _re.search(r"×\s*(0\.\d+)", r["wb"] or "")
        cur.execute("UPDATE ingredients SET wholesale_price=? WHERE ingredient_key=?",
                    (round(r["mp"] * (float(m.group(1)) if m else 0.70)), r["k"]))
    con.commit(); con.close()
    print(f"KAMIS 전체 갱신: {total}종 (도매 추정 보정 {fixed}종 · 역전 교정 {len(inv)}종)")


if __name__ == "__main__":
    main()
