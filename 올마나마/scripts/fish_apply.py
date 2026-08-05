# -*- coding: utf-8 -*-
"""수산 도매(대용량 코너, 2026-07-24 수집)를 ingredients 에 반영한다.

⚠️ 인계서에는 '90종'으로 적혀 있으나 `fishsale_bulk.json` 에 실제로 들어 있는 건 38건이고,
   그중 2건은 중량 파싱이 비어 있다(`kg: null`). 그리고 내용이 대부분
   **젓갈·액젓·해조류·천일염**이라 우리 재료와 겹치는 게 몇 개 없다.
   수산물 원물(생선·새우·오징어)을 채우려면 다시 수집해야 한다.

정책은 app_apply.py 와 같다. 도매만 갱신하고 소매는 건드리지 않는다.
"""
import json, io, os, sqlite3, sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "research", "fishsale_bulk.json")
STAMP = "2026-07-25"
SRC_LABEL = "수산 도매몰"          # 거래처 상호는 쓰지 않는다 (원칙 §3)

# 재료키 → 상품명(전체 일치). 같은 값이 여럿이면 **업소가 실제로 받을 수 있는 최저가**를 고른다.
APPLY = {
    "kv_642": "[대용량]갯돌소리 마른미역10kg",
    "kv_651": "[대용량]보령 멸치액젓10kg",          # 곰소 4,500 · 거제 5,900 중 최저가
    "kv_650": "[대용량]더젓갈 숙성새우젓갈20kg",
}

SKIP = {
    "kv_660": "건다시마 — 잡힌 건 '파지다시마'(부스러기)뿐이다. 국물용이면 맞지만 온전한 다시마와 "
              "같은 값으로 쓸 수 없다. 쌈다시마는 이미 실거래값(1,700)이 따로 있다",
    "kv_638": "마른멸치 — '통영참멸치 자멸' 21,667원/kg 인데 지금 KAMIS 값 10,400의 2배다. "
              "국산 통영 vs 시세 기준이 달라서 그대로 덮으면 원가가 튄다. 국산/수입 확인 후에",
    "cg_salt": "꽃소금 — 잡힌 건 김장용 천일염이다. 정제 꽃소금과 다른 물건",
}

# 겹치는 재료가 없어 이번엔 안 쓴 것
UNUSED = ["IQF 냉동굴 13,800", "동죽조개 5,990", "급냉 물김 7,990", "염장미역줄기 2,390",
          "염장다시마 2,190", "명란/창란/오징어젓갈 22,000~28,000", "낙지젓갈 14,000"]


def main():
    dry = "--apply" not in sys.argv
    raw = json.load(io.open(SRC, encoding="utf-8"))
    by_name = {o["name"]: o for o in raw}
    bad = [o["name"] for o in raw if not o.get("kg")]

    c = sqlite3.connect(DB)
    cur = c.cursor()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("수집분 %d건 (중량 파싱 실패 %d건)" % (len(raw), len(bad)))
    for b in bad:
        print("  ! 중량 없음: %s" % b)
    print()
    print("%-14s %10s %10s %8s   %s" % ("재료", "도매(전)", "도매(후)", "변화", "근거 상품"))
    print("-" * 90)

    n = 0
    for key, pname in APPLY.items():
        o = by_name.get(pname)
        if not o or not o.get("kg"):
            print("  ! %s — 수집분에 '%s' 이 없거나 중량이 비었다" % (key, pname))
            continue
        row = cur.execute("select name, base_unit, wholesale_price from ingredients "
                          "where ingredient_key=?", (key,)).fetchone()
        if not row:
            print("  ! %s — DB에 없는 재료키" % key)
            continue
        name, unit, wp_old = row
        if unit != "kg":
            print("  ! %s(%s) — base_unit 이 '%s' 다. kg 단가를 그대로 넣으면 안 된다" % (name, key, unit))
            continue
        wp_new = round(o["won_per_kg"])
        pct = (wp_new - (wp_old or 0)) / (wp_old or 1) * 100
        print("%-14s %10s %10s %+7.0f%%   %s (%s원 / %skg)" % (
            name, f"{wp_old or 0:,}", f"{wp_new:,}", pct, pname, f"{o['price']:,}", o["kg"]))

        basis = "%s %s %s — %s원 / %skg = %s원/kg" % (
            SRC_LABEL, STAMP, pname, f"{o['price']:,}", o["kg"], f"{wp_new:,}")
        if not dry:
            cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                        "updated_at=? where ingredient_key=?", (wp_new, basis, STAMP, key))
            cur.execute("insert into price_history(ingredient_key, price_date, retail_price, "
                        "source, created_at, wholesale_price) values(?,?,?,?,?,?)",
                        (key, STAMP, None, "fishsale", now, wp_new))
        n += 1

    print("\n[반영 제외 — 이유]")
    for k, why in SKIP.items():
        print("  %s" % why)
    print("\n[겹치는 재료 없음 — 이번엔 안 씀]")
    print("  " + " / ".join(UNUSED))

    if dry:
        print("\n※ 미리보기다. 실제로 쓰려면  python scripts/fish_apply.py --apply")
    else:
        c.commit()
        print("\n%d종 반영 완료." % n)


main()
