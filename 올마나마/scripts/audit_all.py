# -*- coding: utf-8 -*-
"""전수 검수 — 무엇이 잘못됐는지 유형별로 뽑는다. 2026-07-27

🔴 **읽기만 한다.** 고치지 않는다. 사람이 보고 결정한다.

왜 필요한가 — 세션이 바뀔 때마다 "다 했습니다" 뒤에 절반이 틀려 있었다.
그래서 **잘못된 것을 세는 코드**를 먼저 둔다. 이 스크립트의 숫자가 0 이 되는 게 목표다.

⚠️ 개수를 셀 때 `pack_g IS NOT NULL` 로 세지 말 것 — 0 인 값이 섞여 **부풀려 보고하게 된다**
   (2026-07-27 실제로 94종을 197종으로 잘못 보고했다). `pack_g > 0` 으로 센다.

    python scripts/audit_all.py            # 콘솔 요약
    python scripts/audit_all.py --html     # 검수표 HTML
"""
import io
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "audit_all.html")

sys.stdout.reconfigure(encoding="utf-8")

# ── 이름 규칙 ──────────────────────────────────────────────────────────────
# 🔴 재료명은 **손님이 복사해 쿠팡에 붙여넣는 검색어**다(사이트에 복사 버튼이 있다).
#    그래서 ①상표가 없어야 하고 ②실제로 검색되는 말이어야 한다.
#    `시판용 뿌링클 튀김파우더` 는 둘 다 어긋난다 — 그런 상품명이 세상에 없어서 0건이 나온다.
MAKERS = (
    "곰표", "사조오양", "오뚜기", "백설", "청정원", "대상", "CJ", "다담", "샘표", "쉐프원",
    "썬리취", "동원", "비셰프", "금양", "상경", "선인", "이지마요", "나비촌", "요리스케치",
    "아이엠소스", "어나더소스", "첫맛", "태원", "곰곰", "밀락", "무화당", "해표", "큐원",
    "움트리", "뫼루니", "미트박스", "덴마크", "앵커", "시타", "가마로", "놀부", "백채",
    "보승회관", "미스사이공", "본죽", "설빙", "던킨", "청우", "삼양", "농심", "풀무원",
)
# 지어낸 이름 — 음식 재료가 아니거나, 무엇인지 알 수 없는 말
FAKE_WORDS = (
    "부재료", "가공부재료", "전용유", "콤보육", "속재료", "김밥재료", "기본겉절이",
    "매운고기", "마늘양파", "샐러드용 채소", "세트", "믹스시럽퓨레", "시럽퓨레",
    "판어묵피", "설탕설팅", "머리고기순대돈족", "돈족/머리고기", "김말이어묵",
)
# 이름에 남은 용량·규격 (상표를 빼도 이게 남으면 검색이 어긋난다)
RX_PACK = re.compile(r"[\(（]?\s*\d[\d,.]*\s*(kg|g|l|ml|L|ML|개|입|팩|봉|매)\b", re.I)
RX_PAREN = re.compile(r"[\(（][^)）]{2,}[\)）]")
# 검색 안 되는 접두·수식어
BAD_PREFIX = ("시판용", "업소용", "대용량", "소포장", "가정용", "시판")
# 브랜드 전용이어야 하는 재료 종류 — 이게 여러 브랜드에 걸리면 원가가 같아진다
RX_BRANDSPEC = re.compile(r"(파우더|튀김가루|시즈닝|소스|양념|배터|브레딩|드레싱|시럽)")

CSS = """
body{font:14px/1.7 -apple-system,'Malgun Gothic',sans-serif;margin:0;padding:24px;
 background:#f6f7f9;color:#1a1d21}
h1{font-size:22px;margin:0 0 6px}
.sub{color:#6b7280;margin:0 0 22px}
h2{font-size:17px;margin:30px 0 4px;padding-top:16px;border-top:2px solid #e5e7eb}
h2 .n{background:#ef4444;color:#fff;border-radius:11px;padding:1px 9px;font-size:13px;
 margin-left:8px;vertical-align:2px}
h2 .n.ok{background:#10b981}
.why{color:#6b7280;font-size:13px;margin:2px 0 12px}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden;
 box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:6px}
th{background:#f3f4f6;text-align:left;padding:7px 10px;font-size:12px;color:#4b5563;
 font-weight:600;white-space:nowrap}
td{padding:6px 10px;border-top:1px solid #f1f2f4;vertical-align:top}
td.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.k{color:#9ca3af;font-size:11px;font-family:ui-monospace,Consolas,monospace}
.bad{color:#dc2626;font-weight:600}
.warn{color:#d97706}
.ok{color:#059669}
.tag{display:inline-block;background:#eef2ff;color:#4338ca;border-radius:4px;
 padding:0 6px;font-size:11px;margin-right:4px}
.sum{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:8px}
.card{background:#fff;border-radius:8px;padding:10px 14px;box-shadow:0 1px 3px rgba(0,0,0,.08);
 min-width:120px}
.card b{display:block;font-size:20px;line-height:1.2}
.card span{color:#6b7280;font-size:12px}
.none{color:#059669;background:#fff;padding:10px 14px;border-radius:8px}
"""


def rows(c, sql, args=()):
    return [dict(r) for r in c.execute(sql, args)]


def main():
    html = "--html" in sys.argv
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row
    S = []                      # (제목, 왜, 컬럼목록, 행목록)

    # 재료별 사용 현황 — 공개 브랜드 메뉴 + 요리
    use = {}
    for r in c.execute("""SELECT mi.ingredient_key k, b.name bn, m.name mn
                          FROM menu_ingredients mi
                          JOIN menus m ON m.id=mi.menu_id
                          JOIN brands b ON b.id=m.brand_id
                          WHERE b.published=1"""):
        use.setdefault(r["k"], []).append((r["bn"], r["mn"]))

    ing = rows(c, """SELECT i.*,
                       (SELECT name FROM ingredient_retail x WHERE x.ingredient_key=i.ingredient_key) rname,
                       (SELECT price FROM ingredient_retail x WHERE x.ingredient_key=i.ingredient_key) rprice,
                       (SELECT pack_g FROM ingredient_retail x WHERE x.ingredient_key=i.ingredient_key) rpack,
                       (SELECT status FROM ingredient_retail x WHERE x.ingredient_key=i.ingredient_key) rstatus
                     FROM ingredients i""")
    for r in ing:
        r["brands"] = sorted(set(b for b, _ in use.get(r["ingredient_key"], [])))
        r["nuse"] = len(use.get(r["ingredient_key"], []))

    used = [r for r in ing if r["nuse"] > 0]

    # ① 검색이 안 되는 이름 ─────────────────────────────────────────────
    bad = []
    for r in used:
        n = r["name"] or ""
        why = []
        if any(n.startswith(p) for p in BAD_PREFIX):
            why.append("검색 안 되는 접두어")
        for mk in MAKERS:
            if mk in n:
                why.append("상표 «%s»" % mk)
                break
        if RX_PACK.search(n):
            why.append("이름에 용량")
        if RX_PAREN.search(n):
            why.append("괄호 안 상품표기")
        if why:
            bad.append(dict(r, why=why))
    S.append(("① 검색이 안 되는 재료명",
              "재료명은 손님이 <b>복사해서 쿠팡에 붙여넣는 검색어</b>다. 상표·용량·«시판용» 이 붙으면 "
              "검색 결과가 0건이 되고, 그러면 배너를 눌러도 물건이 안 나온다.",
              ("재료", "문제", "붙어있는 소매 상품", "쓰는 브랜드"),
              [(("<b>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"])),
                " ".join("<span class='tag'>%s</span>" % w for w in r["why"]),
                (r["rname"] or "<span class='warn'>없음</span>"),
                ", ".join(r["brands"][:4]) + (" +%d" % (len(r["brands"]) - 4) if len(r["brands"]) > 4 else ""))
               for r in sorted(bad, key=lambda x: -x["nuse"])]))

    # ② 지어낸 이름 ─────────────────────────────────────────────────────
    fake = [r for r in used if any(w in (r["name"] or "") for w in FAKE_WORDS)]
    S.append(("② 음식 재료가 아닌 이름",
              "«부재료»·«속재료»·«김밥재료» 처럼 <b>무엇인지 알 수 없는 말</b>은 재료가 아니다. "
              "AI 가 채운 것이고 대표가 여러 번 지우라고 했다.",
              ("재료", "도매가", "근거", "쓰는 곳"),
              [("<b class='bad'>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                format(r["wholesale_price"] or 0, ","),
                (r["wholesale_basis"] or "")[:50],
                "%d곳: %s" % (r["nuse"], ", ".join(r["brands"][:3])))
               for r in sorted(fake, key=lambda x: -x["nuse"])]))

    # ③ 추측 근거 ───────────────────────────────────────────────────────
    RX_GUESS = re.compile(r"coef|research|naver|비공개|추정|×0\.\d")
    guess = [r for r in used if RX_GUESS.search(r["wholesale_basis"] or "")]
    S.append(("③ 도매가 근거가 추측인 재료",
              "«coef080»(도매×0.8) · «research2» · «naver» · «출처 비공개» 는 <b>실제 상품이 아니다</b>. "
              "식봄(도매)·미트박스(고기) 실제 상품으로 바꿔야 원가를 주장할 수 있다.",
              ("재료", "도매가", "근거", "쓰는 곳"),
              [("<b>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                format(r["wholesale_price"] or 0, ","),
                "<span class='bad'>%s</span>" % (r["wholesale_basis"] or "")[:46],
                "%d곳: %s" % (r["nuse"], ", ".join(r["brands"][:3])))
               for r in sorted(guess, key=lambda x: -x["nuse"])]))

    # ④ 소매 용량 없음 ──────────────────────────────────────────────────
    nopack = [r for r in used
              if (r["rprice"] or 0) > 0 and not (r["rpack"] or 0) > 0
              and (r["rstatus"] or "") not in ("store", "none")]
    S.append(("④ 소매 상품에 용량이 없음",
              "용량(<code>pack_g</code>)이 없으면 <b>단위당 단가를 못 낸다</b>. "
              "그러면 원가 계산이 옛 <code>manual_price</code> 로 조용히 넘어가서 "
              "쿠팡 상품을 바꿔도 원가가 안 바뀐다. 폰 크롬으로 읽어야 한다.",
              ("재료", "소매 상품", "가격", "쓰는 곳"),
              [("<b>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                (r["rname"] or "")[:44],
                "<span class='bad'>%s원 / ?g</span>" % format(round(r["rprice"] or 0), ","),
                "%d곳: %s" % (r["nuse"], ", ".join(r["brands"][:3])))
               for r in sorted(nopack, key=lambda x: -x["nuse"])]))

    # ⑤ 소매가 도매보다 지나치게 높음 ───────────────────────────────────
    odd = []
    for r in used:
        w, p, g = r["wholesale_price"] or 0, r["rprice"] or 0, r["rpack"] or 0
        if not (w > 0 and p > 0 and g > 0):
            continue
        b = (r["base_unit"] or "").lower()
        unit = p / (g / 1000.0) if b in ("kg", "l") else (p / g if b in ("g", "ml") else 0)
        if unit and unit > w * 3:
            odd.append(dict(r, unit=unit, ratio=unit / w))
    S.append(("⑤ 소매 단가가 도매의 3배를 넘음",
              "소매가 도매보다 비싼 건 정상이지만 <b>3배가 넘으면 상품을 잘못 잡은 것</b>이다 — "
              "필요량보다 큰 규격을 통째로 넣었거나 다른 물건이다.",
              ("재료", "도매", "소매 단가", "배수", "소매 상품"),
              [("<b>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                "%s/%s" % (format(r["wholesale_price"], ","), r["base_unit"]),
                "<span class='bad'>%s</span>" % format(round(r["unit"]), ","),
                "<b class='bad'>%.1f배</b>" % r["ratio"],
                "%s <span class='k'>%s원/%gg</span>" % ((r["rname"] or "")[:30],
                                                        format(round(r["rprice"]), ","), r["rpack"]))
               for r in sorted(odd, key=lambda x: -x["ratio"])]))

    # ⑥ 브랜드 공유 재료 ────────────────────────────────────────────────
    shared = [r for r in used
              if len(r["brands"]) >= 2 and RX_BRANDSPEC.search(r["name"] or "")]
    S.append(("⑥ 맛을 가르는 재료가 여러 브랜드에 공유됨",
              "파우더·시즈닝·소스·양념은 <b>브랜드마다 맛이 다르다</b>. 하나를 공유하면 "
              "두 브랜드 원가가 같아지고, 붙일 쿠팡 링크도 1개뿐이라 레퍼럴이 깎인다.",
              ("재료", "브랜드 수", "쓰는 브랜드", "도매가"),
              [("<b>%s</b><div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                "<b class='bad'>%d곳</b>" % len(r["brands"]),
                ", ".join(r["brands"]),
                format(r["wholesale_price"] or 0, ","))
               for r in sorted(shared, key=lambda x: -len(x["brands"]))]))

    # ⑦ composition 이 원물·기름·파우더에 붙음 ──────────────────────────
    RX_NOTSAUCE = re.compile(r"(고추|대파|마늘|양파|당근|양배추|파우더|튀김가루|기름|유$|육수|"
                             r"닭|돼지|소고기|치즈|밀가루|설탕|소금|후추|무$|쌀|떡|면)")
    comp = rows(c, """SELECT mi.id, b.name bn, m.name mn, i.name iname, mi.ingredient_key k,
                             mi.composition
                      FROM menu_ingredients mi
                      JOIN menus m ON m.id=mi.menu_id
                      JOIN brands b ON b.id=m.brand_id
                      JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
                      WHERE b.published=1 AND COALESCE(mi.composition,'')<>''""")
    compbad = [r for r in comp if RX_NOTSAUCE.search(r["iname"] or "")]
    S.append(("⑦ 원물·기름·파우더에 «양념·소스 구성» 이 붙음",
              "화면에서 <code>composition</code> 이 있으면 그 줄이 통째로 <b>양념·소스 블록</b>으로 바뀌고 "
              "«가정용 배합 예시» 문구가 붙는다. 집에서 배합할 수 있는 <b>소스에만</b> 넣어야 한다.",
              ("브랜드", "메뉴", "재료", "붙어있는 구성"),
              [(r["bn"], r["mn"], "<b class='bad'>%s</b>" % r["iname"],
                (r["composition"] or "")[:60]) for r in compbad]))

    # ⑧ 원가율 이상 ─────────────────────────────────────────────────────
    ratio = rows(c, """SELECT b.name bn, m.name mn, m.sell_price sp, m.est_cost ec,
                              m.cost_ratio cr, m.store_cost sc, m.store_ratio sr,
                              (SELECT COUNT(*) FROM menu_verified v WHERE v.menu_id=m.id) vf
                       FROM menus m JOIN brands b ON b.id=m.brand_id
                       WHERE b.published=1 AND (m.cost_ratio>60 OR m.store_ratio<15
                                                OR m.cost_ratio IS NULL OR m.store_ratio IS NULL)
                       ORDER BY COALESCE(m.cost_ratio,999) DESC""")
    S.append(("⑧ 원가율이 말이 안 되는 메뉴",
              "소매 <b>60% 초과</b>는 상품을 크게 잡았거나 재료가 틀린 것. "
              "도매 <b>15% 미만</b>은 재료가 빠진 것(대표: «원가율 낮으면 누락 신호»). "
              "값이 <b>비어 있는</b> 것은 계산이 아예 안 된 것.",
              ("브랜드", "메뉴", "판매가", "소매", "소매율", "도매", "도매율", "도장"),
              [(r["bn"], r["mn"], format(r["sp"] or 0, ","),
                format(round(r["ec"] or 0), ","),
                ("<b class='bad'>%.1f%%</b>" % r["cr"]) if r["cr"] else "<span class='bad'>없음</span>",
                format(round(r["sc"] or 0), ","),
                ("<b class='warn'>%.1f%%</b>" % r["sr"]) if r["sr"] else "<span class='bad'>없음</span>",
                "✅" if r["vf"] else "")
               for r in ratio]))

    # ⑨ 공식 메뉴가 부실한 브랜드 ───────────────────────────────────────
    off = rows(c, """SELECT b.name bn, b.frcs_cnt fc, b.homepage_url hu,
                            (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) nm,
                            (SELECT COUNT(*) FROM brand_menu_official o WHERE o.brand_id=b.id) no,
                            (SELECT COUNT(*) FROM brand_menu_official o WHERE o.brand_id=b.id AND o.price>0) np
                     FROM brands b WHERE b.published=1
                     ORDER BY b.frcs_cnt DESC""")
    offbad = [r for r in off if r["nm"] > 0 and r["np"] == 0]
    S.append(("⑨ 공식 메뉴·판매가를 아직 못 모은 브랜드",
              "공식 판매가가 없으면 <b>원가율을 주장할 수 없다</b>. 홈페이지 목록 페이지 또는 "
              "SPA 브랜드는 자체 API 로 읽는다.",
              ("브랜드", "가맹점", "우리 메뉴", "공식 적재", "공식 가격", "홈페이지"),
              [(r["bn"], format(r["fc"] or 0, ","), r["nm"],
                r["no"] or "<span class='bad'>0</span>",
                "<span class='bad'>0</span>",
                "<span class='k'>%s</span>" % ((r["hu"] or "없음")[:44]))
               for r in offbad]))

    # ⑩ 미사용 재료 ─────────────────────────────────────────────────────
    unused = [r for r in ing if r["nuse"] == 0
              and not rows(c, "SELECT 1 FROM dish_ingredients WHERE ingredient_key=? LIMIT 1",
                           (r["ingredient_key"],))]
    S.append(("⑩ 어디에도 안 쓰이는 재료",
              "메뉴·요리 어느 쪽에도 안 붙은 재료. 지워도 되는지 확인 대상 "
              "(<b>지우지 말고 목록만</b> — 나중에 쓸 수 있다는 대표 지시).",
              ("재료", "도매가", "근거"),
              [("%s<div class='k'>%s</div>" % (r["name"], r["ingredient_key"]),
                format(r["wholesale_price"] or 0, ","), (r["wholesale_basis"] or "")[:46])
               for r in sorted(unused, key=lambda x: x["name"] or "")]))

    # ── 출력 ────────────────────────────────────────────────────────────
    print("=" * 74)
    print("올마나마 전수 검수  —  잘못된 것만 센다")
    print("=" * 74)
    for title, _, _, rr in S:
        mark = "  " if not rr else ("🔴" if len(rr) > 20 else "⚠️ ")
        print("%s %-46s %4d건" % (mark, re.sub(r"<[^>]+>", "", title), len(rr)))
    print("=" * 74)

    if not html:
        return

    P = ["<!doctype html><meta charset='utf-8'><title>올마나마 전수 검수</title>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<style>%s</style>" % CSS,
         "<h1>올마나마 전수 검수</h1>",
         "<p class='sub'>2026-07-27 · 읽기만 한 결과다. 아무것도 고치지 않았다. "
         "가격은 시세라 날마다 달라진다.</p>",
         "<div class='sum'>"]
    for title, _, _, rr in S:
        t = re.sub(r"<[^>]+>", "", title)
        P.append("<div class='card'><b class='%s'>%d</b><span>%s</span></div>"
                 % ("ok" if not rr else "bad", len(rr), t[2:].strip()))
    P.append("</div>")

    for title, why, cols, rr in S:
        P.append("<h2>%s<span class='n%s'>%d</span></h2>" % (title, " ok" if not rr else "", len(rr)))
        P.append("<p class='why'>%s</p>" % why)
        if not rr:
            P.append("<div class='none'>✅ 없음</div>")
            continue
        P.append("<table><tr>" + "".join("<th>%s</th>" % h for h in cols) + "</tr>")
        for row in rr:
            P.append("<tr>" + "".join("<td>%s</td>" % (v if v is not None else "") for v in row) + "</tr>")
        P.append("</table>")

    io.open(OUT, "w", encoding="utf-8").write("\n".join(P))
    print()
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
