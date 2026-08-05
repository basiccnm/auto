# -*- coding: utf-8 -*-
"""재료 **표시명**(display_name)을 만든다. 2026-07-27

🔴 대표 확정 규칙 (2026-07-27)
   *"재료명에는 (홍보나 그런거 없이 재료가 달라도) 치킨파우더 (뫼르니,, 이런거 쓰지말고)
     절대 kg 상품명 없이 하나로 통일 각메뉴별 쓰이는 상품명이 달라도"*

   ① 상표(제조사) 금지 — 뫼루니·백설·해표·곰표…
   ② 용량·규격 금지 — `5kg` · `900ml` · `1kg`
   ③ 상품명 금지 — `베이직 치킨용파우더` 같은 도매 상품 이름
   ④ **재료가 달라도 이름은 하나로 통일** — bhc·교촌·BBQ 파우더가 값이 달라도 화면엔 `치킨파우더`
   ⑤ 예외: **브랜드 메뉴명은 남긴다** — `뿌링클 시즈닝` · `맛초킹 소스`.
      대표가 직접 지시한 형태이고, 실제로 그 말로 검색하는 사람이 있다.

🔴 왜 이름을 직접 바꾸지 않고 **표시명을 따로 두나**
   재료명이 재료 페이지 슬러그(`price_<이름>.html`)다. 이름을 `치킨파우더` 하나로 합치면
   값이 다른 3개 재료(bhc 4,575 / BBQ 2,350 / 교촌)가 **같은 파일을 덮어쓴다.**
   그리고 도매가 근거를 재검증할 때 어느 상품이었는지 알아야 한다([[keep-product-names]]).
   → DB `name` 은 구분용으로 그대로, **화면에는 `display_name` 만 쓴다.**

    python scripts/display_name_build.py            # 미리보기(HTML 표)
    python scripts/display_name_build.py --apply
"""
import io
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "display_names.html")
sys.stdout.reconfigure(encoding="utf-8")

# ── ① 손으로 정한 것 — 규칙으로 못 만드는 이름 ────────────────────────────
#    파우더는 **전부 같은 표시명**으로 모은다(대표 지시 ④).
FIXED = {
    # 치킨 튀김 파우더 — 브랜드마다 실제 상품이 다르지만 화면엔 하나
    "nc_55ab25cb65":         "치킨파우더",
    "breading_bhc":          "치킨파우더",
    "breading_bhc_bburing":  "치킨파우더",
    "breading_kyochon":      "치킨파우더",
    "frying_powder":         "튀김가루",
    "breading_gangjeong":    "닭강정파우더",
    "powder_bake":           "오븐구이파우더",
    # 브랜드 메뉴명은 남기지만 **반드시 `~맛`을 붙인다** (2026-07-27 대표 지시):
    #   *"시즈닝이 뿌링클맛 시즈닝  뿌링클 시증하면 정품이란 소리같자나"*
    #   우리가 붙인 건 그 맛을 흉내 낸 **시판 유사품**이지 본사 제품이 아니다.
    #   `시판용` 접두어로도 해봤지만 그 말로는 쿠팡 검색이 안 된다 — `~맛`은 검색도 된다.
    "cheese_seasoning":      "뿌링클맛 시즈닝",
    "sauce_goldking":        "골드킹맛 소스",
    "sauce_matchoking":      "맛초킹맛 소스",
    "sauce_bburing_dip":     "뿌링클맛 디핑소스",
    "sauce_yangnyeom_bhc":   "양념치킨 소스",
    # 도매 상품명이 그대로 남은 것
    "sauce_garlic_soy":      "마늘간장 소스",
    "sauce_gangjeong":       "닭강정 소스",
    "sauce_teriyaki_bulk":   "데리야끼 소스",
    "sauce_oriental":        "오리엔탈 드레싱",
    "sauce_poke":            "포케 소스",
    "sauce_nuoccham":        "느억맘 소스",
    "sauce_mala":            "마라소스",
    "cola_can":              "콜라",
    # 도매/소매 규격 구분은 화면에서 의미가 없다 — 같은 물건이다
    "oil_sesame_bulk":       "참기름",
    "cheese_cheddar":        "체다 슬라이스 치즈",
    # 대표가 만든 계산식은 이름에서 빼고 근거에만 남긴다
    "olive_blend_oil":       "올리브 블렌딩유",
    # 무엇인지 알 수 없는 이름 — 대표가 여러 번 지우라고 했다
    "salad_greens":          "샐러드 채소",
    "gimbap_ingredients":    "김밥 재료",
    # 시장에서 쓰는 말로 (2026-07-27 대표: *"홍고추로 검색하면 되 붉은고추 말고"*)
    #   `붉은고추` 로 검색하면 식봄에서 쭈꾸미 볶음소스·건고추가 걸린다. `홍고추`가 맞는 말이다.
    "kv_243":                "홍고추",

    # ── 2026-08-03 추가 ───────────────────────────────────────────────────
    # 🔴 **사람이 정한 이름.** 규칙(`build`)을 돌리면 도매 상품명이 그대로 나와서
    #    상표가 화면에 실린다 — 「선진 로스트비프패티」·「Green one 양상추 샐러드용」.
    #    여기 못 박아 둬야 다음에 `--apply` 를 돌려도 안 덮인다
    #    ([[never-auto-overwrite-human-decisions]]).
    "patty_burger_frozen":   "냉동 버거패티",     # 선진 로스트비프패티 600g(60g×10)
    "patty_shrimp_frozen":   "냉동 새우패티",     # 리얼통살새우패티 650g(65g×10ea)
    "lettuce_head":          "양상추",           # Green one 양상추 샐러드용 6kg
    "dough_bread_milk":      "식빵 생지",         # 우유식빵 알생지(서울식품 200g×10)
    "flour_donut_yeast":     "도넛가루",          # 이스트 도넛가루(대한제분 10kg)
    # 브랜드 메뉴명은 남기되 **`~맛`을 붙인다**(위 규칙과 같다). 우리가 붙인 건
    #   본사 제품이 아니라 그 맛을 흉내 낸 시판 유사품이다 — 이름에도 `(유사품)` 이 박혀 있다.
    "sauce_zicoba_charcoal": "지코바맛 숯불매콤양념",
    "salt_seasoned_zicoba":  "지코바맛 양념소금",
    # 🔴 밀가루는 **`밀가루OO분` 한 형식으로 통일한다** (대표 지시 2026-08-03).
    #    글루텐 함량이 달라 값도 쓰임도 다르다 — 한 재료로 뭉치면 안 된다.
    #    레시피가 「밀가루」라고만 쓰면 중력분이다(가정용 기본).
    "cg_flour_strong":       "밀가루강력분",
    "cg_flour_medium":       "밀가루중력분",
    "cg_flour_cake":         "밀가루박력분",
    "cg_flour_buchim":       "부침가루",
    # 설탕도 나눈다 — 황설탕·흑설탕은 흰설탕과 값이 다르다
    "sugar_brown":           "황설탕",
    "sugar_dark":            "흑설탕",
}

# ── ② 규칙 ────────────────────────────────────────────────────────────────
# 🔴 상표 목록은 **`namemask.py` 가 정본이다** (2026-08-03 통합).
#    전에는 여기에 목록이 따로 있었고 55개만 겹쳤다. 그 결과 —
#      · 「백설탕」 보호가 저쪽에만 있어 `cg_sugar_white` 표시명이 **「탕」** 으로 나갔다
#      · 쿠팡 PB 「탐사·코멧·줌인터내셔날·자연맘」이 여기 없어 표시명에 남을 뻔했다
#    ⛔ 여기에 상표를 다시 적지 마라. `namemask._MAKERS` 에 넣는다.
from namemask import MAKERS, KEEP_WORDS, hide_keep, show_keep
# 화면에서 뺄 접두·수식어 (검색이 안 되는 말)
DROP_PRE = ("시판용", "업소용", "대용량", "소포장", "가정용", "시판", "수제", "국내산",
            "냉장", "냉동", "무항생제", "프리미엄")
# 괄호 안을 **남겨야 하는** 말 — 용도·부위·원산지는 재료를 가리키는 정보다
KEEP_PAREN = re.compile(r"(치킨용|빙수용|통다리|통편육|원물|앞발|뒷발|장족|1인분|"
                        r"국내산|수입|냉동|건조|생|다짐|슬라이스|채|분말)")
RX_PACKNUM = re.compile(r"\s*\(?\s*\d[\d,.]*\s*(kg|g|L|l|ml|ML|개|입|팩|봉|매|인분)\s*\)?", re.I)
RX_PAREN = re.compile(r"\s*[\(（]([^)）]*)[\)）]")
RX_STAR = re.compile(r"^[★◆●■▲※\*®™\s]+|[★◆●■▲®™]+")

# 🔴 상표를 품은 **일반 낱말** — 지우면 뜻이 사라진다. 치환 전에 잠시 감춘다.
#    「백설탕」에서 상표 「백설」을 떼면 **「탕」**만 남는다. 실제로 그 상태로 라이브에
#    나가 있었다(2026-08-03 발견 · `cg_sugar_white`·`mb_d9d017297c` 2종).
#    `namemask.py` 에는 같은 보호가 있었는데 여기만 빠져 있었다 — **두 곳이 같은 일을
#    따로 하고 있다.** 새 상표를 넣을 때 이 목록도 함께 본다.
KEEP_WORDS = ("백설탕",)
_RX_KEEP = re.compile("|".join(re.escape(w) for w in KEEP_WORDS))


def build(name):
    """이름에서 상표·용량·상품표기를 뗀다. 못 줄이면 원래 이름을 그대로 쓴다."""
    s = RX_STAR.sub("", name or "").strip()

    # 괄호: 용도·부위 정보면 살리고, 상품표기·용량이면 버린다
    def _paren(m):
        inner = m.group(1)
        if KEEP_PAREN.search(inner) and not any(k in inner for k in MAKERS) \
           and not re.search(r"\d\s*(kg|g|L|l|ml)", inner, re.I):
            return "(%s)" % inner
        return ""
    s = RX_PAREN.sub(_paren, s)

    # 상표 (긴 것부터 — "CJ제일제당" 이 "CJ" 보다 먼저 걸려야 한다)
    #  ⚠️ 통짜 치환이라 낱말 중간도 자른다 — 그래서 보호 낱말을 먼저 감춘다
    s = _RX_KEEP.sub(lambda m: "\x00%d\x00" % KEEP_WORDS.index(m.group(0)), s)
    for mk in sorted(MAKERS, key=len, reverse=True):
        s = s.replace(mk, " ")
    s = re.sub(r"\x00(\d+)\x00", lambda m: KEEP_WORDS[int(m.group(1))], s)

    s = RX_PACKNUM.sub(" ", s)                      # 용량
    s = re.sub(r"\s{2,}", " ", s).strip(" _-·,")

    for p in DROP_PRE:                              # 접두어
        if s.startswith(p):
            s = s[len(p):].strip()

    # 상표를 뗀 자리에 남는 군더더기 — `고추가루일반_한울[중국산]` → `고추가루일반_ [중국산]`
    #  구분자(`_`·`-`)와 여는 괄호 사이의 빈칸, 빈 괄호를 정리한다
    s = re.sub(r"[（(\[【]\s*[）)\]】]", "", s)        # 빈 괄호 — `【 】`
    s = re.sub(r"\s*([_\-·])\s*(?=[\[（(【])", r"\1", s)   # `_ [` → `_[`
    s = re.sub(r"([_\-·])\s*$", "", s)              # 끝에 남은 구분자
    s = re.sub(r"\s+(?=[\]）)】])", "", s)            # 닫는 괄호 앞 빈칸
    s = re.sub(r"\s{2,}", " ", s).strip(" _-·,")
    # 🔴 괄호는 **짝이 안 맞을 때만** 뗀다. 전에는 `strip("()（）")` 이라
    #    「닭다리살 정육(국내산)」의 닫는 괄호까지 벗겨 **「정육(국내산」** 이 됐다.
    while s and s[-1] in "()（）" and s.count("(") + s.count("（") != s.count(")") + s.count("）"):
        s = s[:-1].rstrip(" _-·,")
    while s and s[0] in "()（）":
        s = s[1:].lstrip(" _-·,")
    return s or (name or "").strip()


CSS = """body{font:14px/1.7 -apple-system,'Malgun Gothic',sans-serif;margin:0;padding:24px;
background:#f6f7f9;color:#1a1d21}h1{font-size:21px;margin:0 0 4px}
.sub{color:#6b7280;margin:0 0 20px}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden;
box-shadow:0 1px 3px rgba(0,0,0,.08)}
th{background:#f3f4f6;text-align:left;padding:8px 10px;font-size:12px;color:#4b5563}
td{padding:6px 10px;border-top:1px solid #f1f2f4;vertical-align:top}
.k{color:#9ca3af;font-size:11px;font-family:ui-monospace,Consolas,monospace}
.new{color:#065f46;font-weight:600}
.same{color:#9ca3af}
.fix{background:#eef2ff;color:#4338ca;border-radius:4px;padding:0 5px;font-size:11px}
.dup{background:#fef3c7;color:#92400e;border-radius:4px;padding:0 5px;font-size:11px}
"""


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(ingredients)")]
    if "display_name" not in cols:
        print("• ingredients.display_name 칼럼 추가")
        if apply:
            cur.execute("ALTER TABLE ingredients ADD COLUMN display_name TEXT")
            c.commit()
        elif "--apply" not in sys.argv:
            print("  (미리보기라 칼럼은 안 만든다)")

    # 🔴 **전부** 채운다. 처음엔 "쓰이는 것만" 골랐는데 그 판정이 틀려서
    #    `뫼루니 베이직 치킨용파우더 5kg` 이 6개 메뉴 화면에 그대로 나갔다(2026-07-27).
    #    화면에 나올지 안 나올지를 여기서 판정할 이유가 없다 — 표시명은 있어도 해가 없다.
    rows = [dict(r) for r in cur.execute("""
        SELECT i.ingredient_key k, i.name,
               (SELECT COUNT(*) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=i.ingredient_key AND b.published=1) nm,
               (SELECT COUNT(*) FROM dish_ingredients d
                WHERE d.ingredient_key=i.ingredient_key) nd
        FROM ingredients i ORDER BY i.name""")]

    out, changed = [], 0
    for r in rows:
        fixed = r["k"] in FIXED
        dn = FIXED[r["k"]] if fixed else build(r["name"])
        r["dn"], r["fixed"] = dn, fixed
        if dn != r["name"]:
            changed += 1
        out.append(r)

    # 표시명이 겹치는 것 = 의도한 통일인지 확인용
    from collections import Counter
    cnt = Counter(r["dn"] for r in out)

    print("쓰이는 재료 %d종 · 표시명이 달라지는 것 %d종" % (len(out), changed))
    print()
    print("── 표시명이 2개 이상 재료에 겹치는 것 (통일된 것) ──")
    for dn, n in sorted(cnt.items(), key=lambda x: -x[1]):
        if n < 2:
            continue
        ks = [r for r in out if r["dn"] == dn]
        print("  %-22s %d개  %s" % (dn, n, " / ".join(x["name"][:22] for x in ks)))

    # ── 페이지 주소(슬러그)도 여기서 정한다 ────────────────────────────────
    #  🔴 주소도 화면이다. 옛날엔 생성기가 `name` 으로 만들어서
    #     `price_뫼루니바사삭닭강정파우더5kg.html` 같은 주소가 됐고, 형제 재료 링크를 타고
    #     그 상표가 26개 페이지에 퍼졌다(2026-07-27).
    #  🔴 그리고 **한 곳에서 정해 DB 에 넣어야** 한다 — 생성기 두 개가 각자 계산하면
    #     `gen_prices_page` 의 링크와 `gen_ingredient_pages` 의 파일명이 어긋난다.
    #     표시명이 겹치는 재료(치킨파우더 4종)는 뒤에 번호를 붙여 파일이 덮이지 않게 한다.
    keep = re.compile(r"[^0-9A-Za-z가-힣]+")
    seen_slug, nslug = {}, 0
    for r in sorted(out, key=lambda x: x["k"]):        # 키 순서 = 실행마다 같은 결과
        base = keep.sub("", r["dn"] or "") or keep.sub("", r["name"] or "")
        if not base:
            r["slug"] = None
            continue
        if base in seen_slug:
            seen_slug[base] += 1
            base = "%s%d" % (base, seen_slug[base])
        else:
            seen_slug[base] = 1
        r["slug"] = "price_" + base
        nslug += 1

    if "page_slug" not in cols:
        print("• ingredients.page_slug 칼럼 추가")
        if apply:
            cur.execute("ALTER TABLE ingredients ADD COLUMN page_slug TEXT")
            c.commit()

    if apply:
        for r in out:
            cur.execute("UPDATE ingredients SET display_name=?, page_slug=? "
                        "WHERE ingredient_key=?", (r["dn"], r.get("slug"), r["k"]))
        c.commit()
        print()
        print("✅ DB 반영 %d종 (주소 %d개)" % (len(out), nslug))

    P = ["<!doctype html><meta charset='utf-8'><title>재료 표시명</title>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<style>%s</style>" % CSS,
         "<h1>재료 표시명 — 화면에 나갈 이름</h1>",
         "<p class='sub'>상표·용량·상품명을 뗀다. DB 의 원래 이름은 그대로 남는다(가격 재검증용). "
         "<span class='fix'>손</span> 은 손으로 정한 것, <span class='dup'>통일</span> 은 "
         "여러 재료가 같은 이름으로 모인 것.</p>",
         "<table><tr><th>화면에 나갈 이름</th><th>DB 이름(그대로 둔다)</th>"
         "<th>쓰임</th><th></th></tr>"]
    for r in sorted(out, key=lambda x: (x["dn"] != x["name"] and 0 or 1, x["dn"])):
        tags = []
        if r["fixed"]:
            tags.append("<span class='fix'>손</span>")
        if cnt[r["dn"]] > 1:
            tags.append("<span class='dup'>통일 %d</span>" % cnt[r["dn"]])
        same = r["dn"] == r["name"]
        P.append("<tr><td class='%s'>%s</td><td>%s<div class='k'>%s</div></td>"
                 "<td class='k'>메뉴 %d · 요리 %d</td><td>%s</td></tr>"
                 % ("same" if same else "new", r["dn"], r["name"], r["k"],
                    r["nm"], r["nd"], " ".join(tags)))
    P.append("</table>")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(P))
    print()
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
