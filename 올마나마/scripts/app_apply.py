# -*- coding: utf-8 -*-
"""식자재 앱에서 뽑은 단가를 ingredients 에 반영한다.

정책 (2026-07-24 확정):
  도매 = 앱 **상시 판매가**(28% 줄).  쿠폰가(36%)는 할인에 할인이라 쓰지 않는다.
  소매 = 앱 **정가**.  우리 기존 소매 ÷ 앱 정가가 중간값 0.89x라 정가가 곧 소매 수준이었다.
         → 따로 계수(α)를 얹지 않는다.

이 반영의 의미: 기존 도매값 상당수가 `coef070`·`×0.70` 같은 **추정 계수**로 만든 값이었다.
그게 실제 업소 판매가보다 20~40% 싸서 원가율을 실제보다 낮게 보이게 하고 있었다.

반영하지 않는 것은 SKIP 목록에 이유와 함께 남긴다 — 다음 사람이 왜 뺐는지 알아야 한다.
"""
import json, io, os, sqlite3, sys, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "research", "식자재앱-단가-20260724.json")
STAMP = "2026-07-24 19:00"

# 반영할 재료 — 앱에서 고른 상품이 우리 재료와 같은 물건임이 확인된 것만
APPLY = ["양파", "당근", "대파", "감자", "무", "애호박", "콩나물", "팽이버섯",
         "옥수수", "시금치", "미나리", "건두부", "당면", "떡볶이 떡", "튀김가루",
         "페퍼로니", "치즈", "우유", "홍합", "바지락"]

# 뺀 것 + 이유
SKIP = {
    "생강": "앱이 잡은 건 '해울초생강'(절임 초생강)이라 생강 원물이 아니다",
    "참깨": "앱 8,200 vs 우리 26,053 — 3배 차이. 원산지(수입 추정) 확인 전엔 못 쓴다",
    "고춧가루": "앱은 '중식용' 9,320. 국산 고춧가루와 물건이 다를 가능성이 높다",
    "상추": "앱이 잡은 건 '양상추'. 우리 '상추'와 같은 재료인지 불명",
    "청양고추": "앱은 '홍청양고추'(붉은 것). 일반 청양고추와 다르다",
    "양배추": "우리 값은 실거래 조사 기반이라 그쪽이 더 신뢰도 높다(대표 확인 건)",
    "깻잎": "20g 소포장이 잡혀 원/kg가 46,500원으로 튄다. 업소용 대용량을 다시 봐야",
    "새우": "200g 소포장. 위와 같은 이유",
    "치킨무": "우리 단위가 '개'라 kg 환산이 필요 — 별도 처리",
    "라면 사리": "우리 단위가 '개'",
    "브로콜리": "우리 단위가 '개'",
}


def main():
    dry = "--apply" not in sys.argv
    picked = {o["kw"]: o for o in json.load(io.open(SRC, encoding="utf-8"))
              if o["status"] == "OK"}
    c = sqlite3.connect(DB)
    cur = c.cursor()

    n = 0
    print("%-12s %10s %10s   %10s %10s" % ("재료", "도매(전)", "도매(후)", "소매(전)", "소매(후)"))
    print("-" * 60)
    for name in APPLY:
        o = picked.get(name)
        if not o:
            print("  ! %s — 수집 결과에 없음" % name)
            continue
        row = cur.execute(
            "select ingredient_key, manual_price, wholesale_price from ingredients where name=?",
            (name,)).fetchone()
        if not row:
            print("  ! %s — DB에 없음" % name)
            continue
        key, mp_old, wp_old = row
        wp_new = o["won_per_kg"]                       # 도매 = 상시 판매가
        mp_new = round(o["list"] / o["pack_kg"])       # 소매 = 정가
        basis = "오늘얼마 식자재몰 %s %s %s %s / 정가 %s원 → 상시가 %s원(%s)" % (
            STAMP, o["code"], o["name"], "", f"{o['list']:,}", f"{o['price']:,}", o["rate"])
        print("%-12s %10s %10s   %10s %10s" % (
            name, f"{wp_old or 0:,}", f"{wp_new:,}", f"{mp_old or 0:,}", f"{mp_new:,}"))
        if not dry:
            cur.execute(
                "update ingredients set wholesale_price=?, wholesale_basis=?, "
                "manual_price=?, updated_at=? where ingredient_key=?",
                (wp_new, basis, mp_new, STAMP, key))
        n += 1

    print("\n[반영 제외]")
    for k, why in SKIP.items():
        print("  %-10s %s" % (k, why))

    if dry:
        print("\n※ 미리보기입니다. 실제로 쓰려면  python scripts/app_apply.py --apply")
    else:
        c.commit()
        print("\n%d종 반영 완료." % n)


main()
