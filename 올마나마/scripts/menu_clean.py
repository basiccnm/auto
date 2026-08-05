# -*- coding: utf-8 -*-
"""수집한 공식 메뉴에서 **원가 계산에 쓸 것만** 남긴다. 2026-07-27

🔴 왜 필요한가
   `brand_menu_list.py` 로 긁은 목록에는 메뉴가 아닌 것이 섞여 있다(BBQ 124개 중 절반).
     · 술·음료·소스 — 콜라 · 생맥주 · 소주 · BBQ 시즈닝 · 치킨무
     · 설명문이 이름 자리에 들어간 것 — "바삭한 식감이 오래 유지되는 치킨 24,500원"
     · 카테고리·버튼 글자 — 떡볶이 · 튀김류 · 그외
   이걸 그대로 쓰면 또 "반 이상 이상한" 데이터가 된다([[never-report-done-without-verifying]]).

⛔ **버리지 않고 갈라만 놓는다.** `keep` / `drop` 을 이유와 함께 남겨서 사람이 되돌릴 수 있게 한다.
   판정이 애매한 것은 `keep` 에 두고 `note` 를 붙인다 — 빠뜨리는 것보다 남기는 게 낫다.

    python scripts/menu_clean.py --brand BBQ
    python scripts/menu_clean.py                 # 공개 브랜드 전체
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "brand_menu_list")
OUT = os.path.join(BASE, "data", "research", "menu_clean.json")

# ── 원가 계산에 안 쓰는 것 ──────────────────────────────
DRINK = re.compile(
    r"(콜라|사이다|스프라이트|환타|펩시|음료|주스|쥬스|에이드|아이스티|커피|아메리카노|라떼|"
    r"물\s*\d|생수|탄산|제로|레몬보이|밀키스|칠성|델몬트|미란다|welch|zero)", re.I)
ALCOHOL = re.compile(r"(맥주|소주|막걸리|와인|하이볼|칵테일|사케|청하|카스|테라|켈리|처음처럼|"
                     r"참이슬|진로|바이젠|페일에일|생맥|병맥|논알코올|beer)", re.I)
SAUCE = re.compile(r"(시즈닝|디핑소스|컵소스|치밥소스|소스\s*(추가|선택)?$|무\s*추가|치킨무|단무지|"
                   r"핫소스$|케찹|머스타드|마요네즈$|피클$|드레싱$)", re.I)
UTIL = re.compile(r"(포장|봉투|용기|수저|나이프|포크|빨대|쇼핑백|배달비|배달팁|이벤트|쿠폰|굿즈|"
                  r"상품권|기프트|증정|리뷰)", re.I)
# 카테고리·버튼 글자 (단독으로 쓰인 것)
CATEGORY = ("떡볶이", "튀김류", "라이스", "그외", "치킨", "피자", "사이드", "음료", "세트",
            "버거", "면류", "밥류", "분식", "디저트", "신메뉴", "베스트", "추천", "인기",
            "전체", "메뉴", "주류", "소스", "토핑", "옵션", "구이", "양념", "후라이드")
# 설명문 신호 — 이름 자리에 들어온 문장
RX_DESC = re.compile(r"(맛있|바삭|촉촉|부드러|고소|매콤|달콤|풍미|제격|진리|가득|어울리|담은|"
                     r"입니다|합니다|하세요|더한|만든|사용|넣어|넣은|즐기|느낄|위에|으로)")


def judge(name, price):
    """(keep?, 이유). 애매하면 keep 쪽으로 둔다."""
    t = (name or "").strip()
    bare = re.sub(r"^\s*[\[(【][^\])】]{1,12}[\])】]\s*", "", t).strip()
    if not t:
        return False, "이름 없음"
    if ALCOHOL.search(t):
        return False, "주류"
    if DRINK.search(t):
        return False, "음료"
    if SAUCE.search(t):
        return False, "소스·부속"
    if UTIL.search(t):
        return False, "포장·이벤트"
    if bare in CATEGORY or t in CATEGORY:
        return False, "카테고리 글자"
    # 설명문 — 길고 서술어가 있으면 이름이 아니다
    if len(t) >= 18 and RX_DESC.search(t):
        return False, "설명문(이름 아님)"
    if len(t) >= 30:
        return False, "너무 긺(설명문 의심)"
    if re.search(r"\d[\d,]{2,}\s*원", t):
        return False, "이름에 가격이 섞임"
    return True, ""


def main():
    only = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.id, b.name, b.slug FROM brands b WHERE b.published=1
        ORDER BY COALESCE(b.frcs_cnt,0) DESC""")]
    if only:
        rows = [r for r in rows if only in r["name"]]

    result = []
    for b in rows:
        fp = os.path.join(SRC, "%s.json" % b["slug"])
        if not os.path.exists(fp):
            continue
        ms = json.load(io.open(fp, encoding="utf-8")).get("menus") or []
        if not ms:
            continue
        keep, drop = [], []
        for m in ms:
            ok, why = judge(m["name"], m["price"])
            (keep if ok else drop).append(dict(m, reason=why))
        result.append({"brand": b["name"], "slug": b["slug"],
                       "total": len(ms), "keep": keep, "drop": drop})

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False, indent=1))

    print("%-16s %5s %5s %5s %5s %s" % ("브랜드", "수집", "남김", "버림", "가격", "중량"))
    print("-" * 56)
    tk = td = 0
    for r in result:
        pr = sum(1 for m in r["keep"] if m["price"])
        wg = sum(1 for m in r["keep"] if m["weight_raw"])
        tk += len(r["keep"]); td += len(r["drop"])
        print("%-16s %5d %5d %5d %5d %5d" % (
            r["brand"][:16], r["total"], len(r["keep"]), len(r["drop"]), pr, wg))
    print("-" * 56)
    print("남김 %d개 · 버림 %d개 → %s" % (tk, td, OUT))
    if only and result:
        r = result[0]
        print()
        print("■ 남긴 것 (%d개)" % len(r["keep"]))
        for m in r["keep"]:
            print("   %-32s %9s %s" % (m["name"][:32],
                                       (format(m["price"], ",") + "원") if m["price"] else "-",
                                       m["weight_raw"] or ""))
        print()
        print("■ 버린 것 (%d개) — 이유별" % len(r["drop"]))
        from collections import defaultdict
        by = defaultdict(list)
        for m in r["drop"]:
            by[m["reason"]].append(m["name"])
        for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
            print("   [%s] %d개" % (k, len(v)))
            print("      " + " / ".join(x[:22] for x in v[:12]))


if __name__ == "__main__":
    main()
