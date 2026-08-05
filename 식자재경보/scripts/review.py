# -*- coding: utf-8 -*-
"""review.py — 페이지에 올리기 전 **검수**. 통과 못 하면 배포하지 않는다.

왜 만들었나 (2026-08-02)
    필터를 아무리 짜도 «상품명이 그럴듯한가» 만 봤지 «이걸 정말 사도 되나» 를 안 봤다.
    그 결과 시금치 씨앗·잡채말이어묵·상추 줄기장아찌가 페이지까지 나갔고,
    대표가 눈으로 보고 잡아냈다. **사람이 잡아낼 걸 코드가 먼저 잡아야 한다.**

    검수는 두 겹이다.
      · 기계 검수 (이 파일)  — 셀 수 있는 것만 본다. 중복·용량미상·단가역전·가격이상
      · 사람 검수            — 아래 표를 눈으로 본다. `python scripts/review.py` 한 줄

    ⚠️ 기계 검수는 «맞는가» 를 못 본다. 풋고추 대신 청양고추를 권해도 코드는 모른다.
       그건 재료 지식이라 제미나이가 준 대체표(ALT_HINT)를 믿는 수밖에 없다.
       그러니 **대체표를 바꿀 때는 반드시 사람이 한 번 본다.**

쓰는 법
    python scripts/review.py            # 검수표 출력. 문제 있으면 종료코드 1
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from coupang import coupang_api as cp          # noqa: E402

DATA = os.path.join(ROOT, "site", "data.json")

# 이 배수를 넘으면 표에 표시해 사람이 보게 한다. **불합격 사유는 아니다.**
# 피치가 「더 싸다」가 아니라 「폐기율 0·인건비 0·1년 고정 단가」 라서
# 가공품이 kg 당 비싼 건 당연하다 (회신11). 다만 터무니없는 값은 눈에 띄어야 한다.
MAX_RATIO = 5.0


def per_kg(name, price):
    """상품명에서 총량을 읽어 원/kg. 못 읽으면 None."""
    g, u = cp.parse_pack(name)
    if u not in ("g", "ml") or not g:
        return None
    return round(price / (g / 1000.0))


def check(data):
    """문제 목록을 돌려준다. 비어 있으면 통과."""
    problems = []

    # 대체재도 상시도 하나도 없으면 팔 게 없는 페이지다. 그건 올릴 이유가 없다.
    if not any(r["alts"] for r in data["items"]) and not data.get("always"):
        problems.append("팔 물건이 하나도 없다 — 대체재도 상시 품목도 0건")

    # 상시 품목은 «폭등에 대한 대체» 가 아니라 늘 파는 물건이라, 도매가와 견줄 대상이 없다.
    # 값이 말이 되는지만 본다.
    for a in data.get("always", []):
        a["per_kg"] = per_kg(a["name"], a["price"])
        if a["price"] < 1000 or a["price"] > 500000:
            problems.append(f"상시: 가격 이상 {a['price']:,}원 — {a['name'][:40]}")

    for r in data["items"]:
        base = r["now"]                        # 생물 도매 원/kg
        seen_names = set()
        for a in r["alts"]:
            t = a["name"]

            # ① 같은 상품이 두 번 — 옵션 다른 같은 물건이 나란히 뜨면 사기처럼 보인다
            key = t[:30]
            if key in seen_names:
                problems.append(f"{r['name']}: 같은 상품 중복 — {t[:40]}")
            seen_names.add(key)

            # ② 용량 미상 — **불합격이 아니다** (회신11 룰3).
            #    쿠팡은 중량을 이름에 안 적는 일이 흔하다. 그걸 다 버리면 진짜 대체재가
            #    전멸한다. 노출하되 «가격 비교만 생략» 한다. 클릭해서 보게 하는 게 목적이다.
            pk = per_kg(t, a["price"])
            a["per_kg"] = pk
            if pk is None:
                continue

            # ③ 단가가 너무 높으면 표시만 해 둔다. **불합격은 아니다.**
            #    피치가 「더 싸다」에서 「폐기율 0·인건비 0·고정 단가」로 바뀌었으므로
            #    가공품이 kg 당 비싼 건 당연하다. 다만 배수가 터무니없으면 사람이 봐야 한다.
            if pk > base * MAX_RATIO:
                a["flag"] = f"도매의 {pk / base:.1f}배"

            # ④ 값이 말이 안 되는 것 (오타·묶음 오인)
            if a["price"] < 1000 or a["price"] > 500000:
                problems.append(f"{r['name']}: 가격 이상 {a['price']:,}원 — {t[:40]}")
    return problems


def table(data):
    out = []
    n_alt = sum(1 for r in data["items"] if r["alts"])
    out.append(f"기준 {data['base_date']} → {data['date']}   "
               f"{len(data['items'])}개 품목 (대체재 있음 {n_alt}개)\n")
    for r in data["items"]:
        mark = "" if r["alts"] else "   ← 대체 불가 (시세만 노출)"
        out.append(f"■ {r['name']}  +{r['pct']}%   도매 {r['now']:,}원/kg{mark}")
        for a in r["alts"]:
            pk = a.get("per_kg")
            unit = f"{pk:,}원/kg" if pk else "용량미상"
            ratio = f"  ×{pk / r['now']:.1f}" if pk else ""
            flag = f"  ⚑{a['flag']}" if a.get("flag") else ""
            out.append(f"    {a['price']:>8,}원  {unit:>12}{ratio:>7}{flag}   {a['name'][:44]}")
        out.append("")
    if data.get("always"):
        out.append("■ 상시 — 주방 인건비 절감템")
        for a in data["always"]:
            out.append(f"    {a['price']:>8,}원   {a['name'][:52]}")
        out.append("")
    return "\n".join(out)


def main():
    if not os.path.exists(DATA):
        print("site/data.json 이 없다. 먼저 build.py 를 돌릴 것")
        return 1
    data = json.load(io.open(DATA, encoding="utf-8"))
    problems = check(data)
    print(table(data))
    if problems:
        print(f"⛔ 검수 불합격 — {len(problems)}건")
        for p in problems:
            print(f"   · {p}")
        return 1
    print("✅ 검수 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
