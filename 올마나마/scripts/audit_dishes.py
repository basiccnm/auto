# -*- coding: utf-8 -*-
# 요리 페이지 상식 점검 (2026-07-20)
#
# 왜 만들었나: healthcheck는 "단위가 호환되는가"만 본다. 그래서
#   · 계란 833개(단위는 개↔개라 통과) → 탕수육 22만원
#   · 튀김 기름 1,010ml 전액 계산 → 기름값만 6,543원
#   · "백설탕"이 "탕"으로 표기
#   같은 것들이 전부 통과했고, 결국 사용자가 화면을 보고 하나씩 짚어줬다.
#   그건 역할이 뒤바뀐 것이라, **보고 전에 스스로 훑는** 검사를 여기 모은다.
#
#   python scripts/audit_dishes.py          # 반영된 요리 전부
#   python scripts/audit_dishes.py tangsuyuk
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
PREV = os.path.join(BASE, "_preview")

# 가정에서 한 끼에 이만큼 쓰면 이상한 양 (재료 성격별 상한, g/ml)
SANE_MAX = {"양념": 200, "기름": 300, "가루": 400}
FINDINGS = []


def flag(dish, kind, msg):
    FINDINGS.append((dish, kind, msg))


def audit(con, slug, name):
    cur = con.cursor()
    rows = cur.execute("""SELECT i.ingredient_key k, i.name inm, i.manual_price mp, i.base_unit bu,
        i.subcat sc, di.amount, di.unit, p.qty pq, p.label plabel
        FROM dish_ingredients di JOIN dishes d ON di.dish_id=d.id
        JOIN ingredients i ON di.ingredient_key=i.ingredient_key
        LEFT JOIN ingredient_pack p ON p.ingredient_key=i.ingredient_key
        WHERE d.slug=?""", (slug,)).fetchall()
    if not rows:
        return
    lines = []
    for r in rows:
        q = r["amount"] / 1000 if r["unit"] in ("g", "ml") else r["amount"]
        lines.append((r, round((r["mp"] or 0) * q)))
    total = sum(c for _, c in lines)

    for r, cost in lines:
        tail = (r["sc"] or "").split("/")[-1]
        # ① 한 재료가 요리값을 독식
        if total > 2000 and cost > total * 0.6 and cost > 8000:
            flag(name, "독식", f'{r["inm"]} {cost:,}원 = 전체 {total:,}원의 {cost/total*100:.0f}%')
        # ② 양념·기름·가루를 한 끼에 너무 많이
        for grp, cap in SANE_MAX.items():
            if grp in tail and r["unit"] in ("g", "ml") and r["amount"] > cap:
                flag(name, "과다", f'{r["inm"]} {r["amount"]:g}{r["unit"]} — {grp}류 상한 {cap} 초과')
        # ③ 개수 재료 폭주
        if r["bu"] == "개" and r["unit"] == "개" and r["amount"] > 20:
            flag(name, "개수", f'{r["inm"]} {r["amount"]:g}개')
        # ④ 포장 정보 없음 → 장보기 금액이 기본값으로 틀어짐
        if not r["pq"] and r["k"] != "water":
            flag(name, "포장없음", f'{r["inm"]} — 최소구매 단위 미지정(기본값 0.5kg로 계산됨)')
        # ⑤ 포장이 가정용치고 너무 큼 (물·김치는 예외)
        if (r["pq"] and r["bu"] in ("kg", "L") and r["pq"] >= 3
                and r["k"] != "water" and "김치" not in r["inm"]):
            flag(name, "대용량", f'{r["inm"]} 포장 {r["plabel"]} — 업소용 규격 의심')
        # ⑥ 이름은 **화면 표시명**으로 본다. DB 이름에 브랜드가 있어도 plain_name이 떼므로
        #    DB만 보면 전부 오탐이 된다(2026-07-20 실측 40여 건).

    # ⑦ 페이지 텍스트 점검
    p = os.path.join(PREV, f"dish_{slug}.html")
    if os.path.exists(p):
        h = open(p, encoding="utf-8").read()
        if "도매" in h:
            flag(name, "잔재", "페이지에 '도매' 표기가 남음(레시피는 집밥 축만)")
        for shown in re.findall(r'<div class="inm">(.*?)</div>', h):
            if len(shown.strip()) <= 1:
                flag(name, "이름", f'화면 재료명이 한 글자로 잘림: "{shown}"')
            if re.search(r"\(.*\d+\s*(kg|g|ml|L).*\)|\d+\s*(kg|g|ml|L)\s*$", shown):
                flag(name, "이름", f'화면 재료명에 용량이 남음: "{shown}"')
        if len(re.findall(rf"recipe/{slug}_\d\.png", h)) not in (0, 3):
            flag(name, "사진", "사진이 3장이 아님")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    # ⚠️ .fetchall()로 먼저 다 읽는다 — 루프 안에서 audit()이 같은 커넥션으로 재쿼리하면
    #    순회가 첫 행에서 끊긴다(healthcheck가 잡는 '커서 재사용' 함정).
    q = "SELECT slug, name FROM dishes WHERE COALESCE(recipe_serving,'')<>'' ORDER BY name"
    for r in con.execute(q).fetchall():
        if only and r["slug"] != only:
            continue
        audit(con, r["slug"], r["name"])
    con.close()

    if not FINDINGS:
        print("✅ 이상 없음")
        return
    print(f"⚠️ 확인할 것 {len(FINDINGS)}건\n")
    cur_dish = None
    for dish, kind, msg in FINDINGS:
        if dish != cur_dish:
            print(f"[{dish}]"); cur_dish = dish
        print(f"   {kind:6s} {msg}")


if __name__ == "__main__":
    main()
