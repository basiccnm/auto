# -*- coding: utf-8 -*-
"""원가 메뉴 **자동 감사** — 재료·레시피가 틀렸을 법한 메뉴를 집어내 조사 목록을 만든다. 2026-07-31

    python scripts/menu_audit.py            # 콘솔 요약
    python scripts/menu_audit.py --md       # 원가검증-작업목록-YYYY-MM-DD.md 생성

⛔ **DB 를 절대 고치지 않는다.** SELECT 만 한다. 고치는 건 조사(웹서칭·근거 확보) 뒤
   사람이 확인하고 등록 세션이 한다.

왜 만들었나 (2026-07-31 대표 지시)
--------------------------------
*"재료나 레시피가 틀린 게 이런 거는 웹서칭을 통해 레시피 확인 → 재료 모음으로 이어질 수 있게
파이프라인 구축해줘"* — 지금까지는 시래기국에 시래기가 없는 걸 **우연히** 발견했다.
(실제 사고: 시래기국에 시래기 없음 · 빙수에 피자치즈 · 지코바 소금구이에 양념)
우연 말고 규칙으로 잡는다. 원가율이 낮으면 재료 누락 신호다.

무엇을 잡나
----------
  R1  원가율 12% 미만          — 재료 누락 의심 (여태 확인된 누락 전부 이 대역이었다)
  R2  재료 2개 이하            — 구성이 빈약 (단, 음료·빵 단품은 원래 적을 수 있어 표시만)
  R3  메뉴명 핵심재료가 목록에 없음 — 「시래기」국인데 재료에 시래기가 없다 류
  R4  미검증                  — menu_verified 에 없음 (참고용. 그 자체로는 문제 아님)

⚠️ 피자 원가율 11~20% 는 정상이다(재료 3개뿐·정상 구조). R1 에서 피자 업종은 8% 미만만 잡는다.
"""
import io
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# R3 — 메뉴명에 이 말이 있으면 재료명/조성에 이 말(들 중 하나)이 있어야 한다.
#      ⚠️ 보수적으로만 잡는다. 애매한 건 안 넣는다 — 오탐이 신뢰를 깎는다.
NAME_NEEDS = [
    ("시래기",   ["시래기", "우거지"]),
    ("치즈",     ["치즈"]),
    ("새우",     ["새우"]),
    ("오징어",   ["오징어"]),
    ("낙지",     ["낙지"]),
    ("순대",     ["순대"]),
    ("김치",     ["김치", "배추"]),
    ("떡볶이",   ["떡"]),
    ("계란",     ["계란", "달걀"]),
    ("달걀",     ["계란", "달걀"]),
    ("버섯",     ["버섯", "목이"]),
    ("감자",     ["감자"]),
    ("고구마",   ["고구마"]),
    ("불고기",   ["소고기", "우삼겹", "불고기", "돼지"]),
    ("제육",     ["돼지", "제육", "앞다리", "삼겹"]),
    ("삼겹",     ["삼겹"]),
    ("연어",     ["연어"]),
    ("광어",     ["광어"]),
    ("참치",     ["참치"]),
    ("장어",     ["장어"]),
    ("곱창",     ["곱창", "대창", "막창"]),
    ("막창",     ["막창"]),
    ("족발",     ["족", "장족", "돼지다리"]),
    ("우동",     ["우동", "면"]),
    ("소바",     ["소바", "메밀", "면"]),
    ("냉면",     ["냉면", "면"]),
    ("라면",     ["라면", "면"]),
    ("메론",     ["메론", "멜론"]),
    ("딸기",     ["딸기"]),
    ("망고",     ["망고"]),
    ("블루베리", ["블루베리"]),
    ("초코",     ["초코", "카카오", "초콜릿"]),
    ("녹차",     ["녹차", "말차"]),
    ("옥수수",   ["옥수수", "콘"]),
    ("단호박",   ["단호박", "호박"]),
]
# 음료·빵 단품은 재료가 원래 적다 — R2 에서 «표시만» 하고 조사 목록엔 안 올린다
FEW_OK_CAT = ("카페", "디저트", "빵", "베이커리")
PIZZA_CAT = ("피자",)
# 커피·음료는 원두+물+시럽이라 원가율이 원래 낮다(아메리카노 8%가 정상).
# 여기까지 «누락 의심» 으로 잡으면 오탐이 조사 시간을 태운다 → 6% 미만만 잡는다.
LOW_OK_CAT = ("카페", "디저트")


def audit():
    c = store.connect()
    rows = c.execute("""SELECT m.id, m.name, m.sell_price sp, m.recipe_steps,
        COALESCE(m.store_ratio, m.cost_ratio) sr,
        b.name bn, b.frcs_cnt f, cc.name cat,
        (SELECT count(*) FROM menu_verified v WHERE v.menu_id=m.id) ok
        FROM menus m JOIN brands b ON b.id=m.brand_id
        JOIN categories cc ON cc.id=b.category_id
        ORDER BY b.frcs_cnt DESC, m.id""").fetchall()
    out = []
    for m in rows:
        ings = c.execute("""SELECT mi.ingredient_key k, mi.amount, mi.unit, mi.composition,
                                   i.name
                            FROM menu_ingredients mi
                            JOIN ingredients i ON i.ingredient_key = mi.ingredient_key
                            WHERE mi.menu_id=? ORDER BY mi.sort_order""", (m["id"],)).fetchall()
        blob = " ".join((i["name"] or "") + " " + (i["composition"] or "") for i in ings)
        flags = []
        limit = (8 if any(p in m["cat"] for p in PIZZA_CAT)
                 else 6 if any(p in m["cat"] for p in LOW_OK_CAT) else 12)
        if m["sr"] is not None and m["sr"] < limit:
            flags.append("R1 원가율 %.1f%% (%s 기준 %d%% 미만 — 재료 누락 의심)"
                         % (m["sr"], m["cat"], limit))
        if len(ings) <= 2 and not any(p in m["cat"] for p in FEW_OK_CAT):
            flags.append("R2 재료 %d개뿐" % len(ings))
        for kw, needs in NAME_NEEDS:
            if kw in m["name"] and not any(n in blob for n in needs):
                flags.append("R3 이름에 「%s」— 재료에 %s 없음" % (kw, "/".join(needs)))
        if flags:
            out.append((m, ings, flags))
    n_unv = sum(1 for m in rows if not m["ok"])
    return rows, out, n_unv


def main():
    rows, out, n_unv = audit()
    print("=" * 70)
    print("원가 메뉴 %d개 감사 — 조사 필요 %d개 · 미검증 %d개(참고)"
          % (len(rows), len(out), n_unv))
    print("=" * 70)
    for m, ings, flags in out:
        print("\n● [%d] %s — %s (%s · 가맹 %s · %s원)"
              % (m["id"], m["name"], m["bn"], m["cat"], m["f"] or "-", m["sp"]))
        for f in flags:
            print("   ⚠️ %s" % f)
        print("   재료: %s" % ", ".join("%s %s%s" % (i["name"], i["amount"], i["unit"])
                                       for i in ings) if ings else "   재료: 없음")

    if "--md" not in sys.argv:
        print("\n(조사 목록 파일로 만들려면 --md)")
        return

    day = time.strftime("%Y-%m-%d")
    path = os.path.join(BASE, "원가검증-작업목록-%s.md" % day)
    w = io.open(path, "w", encoding="utf-8")
    w.write("# 원가 메뉴 조사 목록 — %s (menu_audit.py 자동 생성)\n\n" % day)
    w.write("> **조사 방법(파이프라인):** 메뉴마다 ①웹서칭으로 공식/후기 레시피 확인\n"
            "> (검색어: `브랜드명 메뉴명 구성`, `메뉴명 레시피 1인분`) → ②빠진 재료·양(g) 확정\n"
            "> → ③근거 URL 과 함께 아래 칸에 적기 → ④등록 세션이 확인 후 DB 반영.\n"
            "> ⛔ 근거 없이 채우지 않는다 — 빈칸이 가짜보다 낫다. 양은 넉넉히, 단가는 정확히.\n\n")
    for m, ings, flags in out:
        w.write("## [%d] %s — %s (%s · %s원 · 원가율 %s)\n"
                % (m["id"], m["name"], m["bn"], m["cat"], m["sp"],
                   ("%.1f%%" % m["sr"]) if m["sr"] is not None else "-"))
        for f in flags:
            w.write("- ⚠️ %s\n" % f)
        w.write("- 현재 재료: %s\n" % (", ".join("%s %s%s" % (i["name"], i["amount"], i["unit"])
                                                for i in ings) or "없음"))
        w.write("- 조사 결과: (여기에 — 빠진 재료·양g·근거URL)\n\n")
    w.close()
    print("\n✅ %s (%d건)" % (path, len(out)))


if __name__ == "__main__":
    main()
