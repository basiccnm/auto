# -*- coding: utf-8 -*-
"""재료명에서 상표·용량을 뗀다. 2026-07-27

🔴 왜 — 재료명은 **손님이 복사해 쿠팡에 붙여넣는 검색어**다(화면에 «복사» 버튼이 있다).
   대표 지시: *"상표가 안보이게 저게 파우더면 치킨용 파우더 이런식으로.
   소스가 정해져 있으면 맛초킹용소스 뿌링클시즈닝 이런식으로 변경해서
   상표는 안보여줘야 우리 사이트에서 더 오래있고 쿠팡 배너를 더 만들수 있을것 같아"*

🔴 브랜드 **메뉴명**은 남긴다 — `뿌링클 시즈닝` · `맛초킹용 소스` 는 대표가 직접 지시한 형태고,
   실제로 그 말로 검색하는 사람이 있다. 지우는 것은 **제조사 상표**(뫼루니·백설·해표…)다.

🔴 **옛 이름을 버리지 않는다.** `ingredients.name_note` 에 남긴다 —
   나중에 가격을 재검증할 때 어느 상품이었는지 알아야 한다([[keep-product-names]]).

⛔ 이 표에 없는 재료는 건드리지 않는다. 자동 판정 금지 —
   `생닭(치킨용)` 의 괄호는 용도, `올리브 블렌딩유(EV 50%+해바라기 50%)` 의 괄호는
   대표가 만든 계산식이다. 지우면 근거가 사라진다.

    python scripts/name_strip_brand.py            # 미리보기
    python scripts/name_strip_brand.py --apply
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

# (재료키, 새 이름) — 하나씩 사람이 정했다
RENAME = [
    # ── bhc·교촌: «시판용» 은 검색이 안 된다. 브랜드 메뉴명은 남긴다 ──
    ("cheese_seasoning",      "뿌링클 시즈닝"),
    ("sauce_goldking",        "골드킹 소스"),
    ("sauce_matchoking",      "맛초킹용 소스"),
    ("sauce_bburing_dip",     "뿌링클 디핑소스"),
    ("sauce_yangnyeom_bhc",   "매콤달콤 양념소스"),
    ("breading_bhc_bburing",  "뿌링클용 튀김파우더"),
    ("breading_kyochon",      "간장치킨용 튀김파우더"),   # «교촌» 은 브랜드 상표라 뺀다
    # ── 도매 상품명이 그대로 남은 것 ──
    ("sauce_garlic_soy",      "마늘간장 소스"),
    ("powder_bake",           "오븐구이용 파우더"),
    ("breading_gangjeong",    "닭강정용 파우더"),
    ("sauce_gangjeong",       "닭강정 소스"),
    ("sauce_teriyaki_bulk",   "데리야끼 소스"),
    ("sauce_oriental",        "오리엔탈 드레싱"),
    ("sauce_poke",            "하와이안 포케소스"),
    ("sauce_nuoccham",        "느억맘 소스"),
    ("sauce_mala",            "마라소스"),
    # ── 집에서 쓰는 기본 조리재료: 상표·용량을 뗀다 ──
    ("cg_flour_strong",       "강력 밀가루"),
    ("cg_gochujang",          "고추장"),
    ("cg_salt",               "꽃소금"),
    ("cg_sugar_white",        "백설탕"),
    ("cg_vinegar",            "사과식초"),
    ("cg_noodle_somyeon",     "소면"),
    ("cg_cooking_oil",        "식용유"),
    ("cg_soy_sauce_brew",     "양조간장"),
    ("cg_soy_sauce_jin",      "진간장"),
    ("cg_oligo_syrup",        "올리고당"),
    # ── 용량이 이름에 박힌 것 (양은 amount 로 관리한다) ──
    ("cola_can",              "콜라"),
]


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    done, skip, dup = 0, 0, 0
    for key, new in RENAME:
        r = cur.execute("SELECT name, name_note FROM ingredients WHERE ingredient_key=?",
                        (key,)).fetchone()
        if not r:
            print("  ✗ %-24s 없는 키" % key)
            skip += 1
            continue
        old = r["name"] or ""
        if old == new:
            print("  · %-24s 이미 «%s»" % (key, new))
            skip += 1
            continue
        # 같은 이름이 이미 있으면 멈춘다 — 이름은 재료 페이지 슬러그라 겹치면 파일이 덮인다
        ex = cur.execute("SELECT ingredient_key FROM ingredients WHERE name=? AND ingredient_key<>?",
                         (new, key)).fetchone()
        if ex:
            print("  ⚠ %-24s «%s» 는 이미 %s 가 쓰는 이름 — 건너뜀" % (key, new, ex[0]))
            dup += 1
            continue
        note = r["name_note"] or ""
        # 옛 이름은 버리지 않는다
        add = "옛 이름: %s" % old
        note = (note + " | " + add) if note and add not in note else (note or add)
        print("  ✅ %-24s %-40s → %s" % (key, old[:40], new))
        if apply:
            cur.execute("UPDATE ingredients SET name=?, name_note=? WHERE ingredient_key=?",
                        (new, note, key))
        done += 1

    if apply:
        c.commit()
    print()
    print("바꿈 %d · 그대로 %d · 이름충돌 %d%s" % (
        done, skip, dup, "  (DB 반영)" if apply else "  ← 미반영, --apply 를 붙여라"))
    if apply and done:
        print()
        print("⚠️ 재료명을 바꿨으니 다음을 확인할 것 (CLAUDE.md):")
        print("   1) dish_def.match_pattern 이 옛 이름을 가리키는지")
        print("   2) menus.recipe_steps 본문에 옛 이름이 글자로 박혔는지")
        print("   3) price_<옛이름>.html 고아 파일 — 삭제 후 gen_sitemap 재실행")


if __name__ == "__main__":
    main()
