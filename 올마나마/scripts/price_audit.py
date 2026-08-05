# -*- coding: utf-8 -*-
"""전체 브랜드 **판매가 검증 현황** — 홀가/배달가 구분까지. 2026-07-27

🔴 대표 지시: *"오매칭 안된게 해서 전체 가격 철저히 알아봐 배달가랑 홀가랑 섞이지 않게"*

판매가 기준은 **홀 매장가**다. 배달앱 가격에는 배달비가 얹혀 있어 그걸 분모로 쓰면
원가율이 실제보다 낮게 나온다(교촌 허니콤보 홀 23,000 / 배달 26,000 — 도매율 46% vs 41%).

가격 출처를 4단계로 판정한다:
   ✅ 공식일치   우리 값 = 공식 홈페이지 수집분 → 홀가로 확정
   ❗ 값다름     둘 다 있는데 어긋남 → 사람이 확인 (사이즈 차이 / 배달가 혼입 / 순살가 혼입)
   ⚠️ 미검증     공식 수집분에 그 메뉴가 없다 → 홈페이지를 다시 읽어야 한다
   🚫 수집없음   그 브랜드 수집분 자체가 없다(0쪽 = SPA 또는 접속 실패)

    python scripts/price_audit.py
    python scripts/price_audit.py --html
"""
import io
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "price_audit.html")
sys.stdout.reconfigure(encoding="utf-8")

RX_SIZE = re.compile(r"\b[LMRSF]\b|라지|미디엄|레귤러|패밀리|파티|스몰|오리지널|씬|thin|"
                     r"x\s*\d+|\(\s*[\d,]+\s*원\s*\)|[\d,]+원|\d+\s*p\b|\(\d+p\)|"
                     r"한마리|반마리|곱빼기|\d+인용|\d+cm", re.I)
RX_GENERIC = re.compile(r"피자|치킨|버거|초밥|도시락|떡볶이|세트|단품|반상|한상")
# 배달가 의심 — 브랜드 자체 주문몰·배달앱 도메인
RX_DELIVERY = re.compile(r"wmpoplus|order|delivery|baemin|yogiyo|coupangeats|shop\.|mall\.", re.I)
# 순살·변형 규격
RX_VARIANT = re.compile(r"순살|가슴살|윙|봉|스틱|콤보|반반|곱빼기|세트|박스|\d+pcs|패밀리|파티", re.I)


def norm(s):
    return re.sub(r"[\s·,\-_.()\[\]/™®]+", "", (s or "")).lower()


def core(s):
    return norm(RX_GENERIC.sub(" ", RX_SIZE.sub(" ", s or "")))


CSS = """body{font:14px/1.7 -apple-system,'Malgun Gothic',sans-serif;margin:0;padding:22px;
background:#f6f7f9;color:#1a1d21}h1{font-size:21px;margin:0 0 4px}
.sub{color:#6b7280;margin:0 0 18px}
.sum{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:16px}
.card{background:#fff;border-radius:8px;padding:9px 13px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card b{display:block;font-size:19px;line-height:1.2}.card span{color:#6b7280;font-size:12px}
h2{font-size:16px;margin:26px 0 6px;padding-top:14px;border-top:2px solid #e5e7eb}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden;
box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:6px}
th{background:#f3f4f6;text-align:left;padding:7px 9px;font-size:12px;color:#4b5563;white-space:nowrap}
td{padding:6px 9px;border-top:1px solid #f1f2f4;vertical-align:top;font-size:13px}
td.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.ok{color:#059669}.bad{color:#dc2626;font-weight:600}.warn{color:#d97706}
.k{color:#9ca3af;font-size:11px}
.b{background:#eef2ff;color:#4338ca;border-radius:4px;padding:0 5px;font-size:11px}
"""


def main():
    html = "--html" in sys.argv
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row

    brands = [dict(r) for r in c.execute("""
        SELECT b.id, b.name, b.homepage_url hu, b.frcs_cnt fc,
               (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) nm,
               (SELECT COUNT(*) FROM brand_menu_official o
                 WHERE o.brand_id=b.id AND o.price>0) no,
               (SELECT COUNT(*) FROM menu_verified v JOIN menus m ON m.id=v.menu_id
                 WHERE m.brand_id=b.id) nv
        FROM brands b WHERE b.published=1 AND
              (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY b.frcs_cnt DESC""")]

    rows, cnt = [], {"ok": 0, "diff": 0, "none": 0, "nocol": 0}
    for b in brands:
        offs = [dict(r) for r in c.execute(
            "SELECT name, price, detail_url FROM brand_menu_official "
            "WHERE brand_id=? AND price>0", (b["id"],))]
        for m in c.execute("""SELECT m.id, m.name, m.sell_price sp,
                                     (SELECT COUNT(*) FROM menu_verified v WHERE v.menu_id=m.id) vf
                              FROM menus m WHERE m.brand_id=? ORDER BY m.id""", (b["id"],)):
            sp = m["sp"] or 0
            hit = next((o for o in offs if norm(o["name"]) == norm(m["name"])), None)
            if not hit and sp:
                cn = core(m["name"])
                near = [o for o in offs if sp * 0.65 <= o["price"] <= sp * 1.35]
                cand = [o for o in near if cn and (core(o["name"]) == cn
                                                   or cn in core(o["name"]))]
                hit = cand[0] if len(cand) == 1 else None
            # 변형 규격 중 우리 값과 같은 가격이 있나 — 순살가·패밀리가 혼입 신호
            var = next((o["name"] for o in offs
                        if o["price"] == sp and RX_VARIANT.search(o["name"])), None)
            deliv = bool(hit and RX_DELIVERY.search(hit.get("detail_url") or ""))
            if not offs:
                st, why = "nocol", "그 브랜드 수집분이 없다(0쪽 — SPA 또는 접속 실패)"
            elif not hit:
                st, why = "none", ("공식에 같은 이름이 없다" +
                                   (" · 변형 규격에 같은 값이 있다 → «%s»" % var if var else ""))
            elif hit["price"] == sp:
                st, why = "ok", ("공식 «%s» 와 일치" % hit["name"][:26])
            else:
                st, why = "diff", ("공식 «%s» = %s원" % (hit["name"][:22], format(hit["price"], ",")) +
                                   (" · 우리 값은 변형 규격 «%s» 가격" % var if var else ""))
            if deliv:
                why += " ⚠️ 출처가 주문·배달몰이라 배달가일 수 있다"
            cnt[st] += 1
            rows.append(dict(b=b, m=dict(m), sp=sp, hit=hit, st=st, why=why,
                             var=var, deliv=deliv))

    print("=" * 104)
    print("전체 판매가 검증 — 공개 브랜드 %d곳 · 메뉴 %d개" % (len(brands), len(rows)))
    print("=" * 104)
    print("  ✅ 공식일치 %d · ❗ 값다름 %d · ⚠️ 미검증 %d · 🚫 수집없음 %d"
          % (cnt["ok"], cnt["diff"], cnt["none"], cnt["nocol"]))
    print()
    mark = {"ok": "✅", "diff": "❗", "none": "⚠️", "nocol": "🚫"}
    for st in ("diff", "none", "nocol", "ok"):
        sel = [r for r in rows if r["st"] == st]
        if not sel:
            continue
        print("── %s %s %d건 ──" % (mark[st], {"ok": "공식일치", "diff": "값다름",
                                            "none": "미검증", "nocol": "수집없음"}[st], len(sel)))
        for r in sel[:40 if st != "ok" else 12]:
            print("  %-13s %-20s %7s원  %s" % (r["b"]["name"][:13], r["m"]["name"][:20],
                                             format(r["sp"], ","), r["why"][:64]))
        if len(sel) > (40 if st != "ok" else 12):
            print("     … 외 %d건" % (len(sel) - (40 if st != "ok" else 12)))
        print()

    if not html:
        return
    P = ["<!doctype html><meta charset='utf-8'><title>판매가 검증</title>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<style>%s</style>" % CSS,
         "<h1>전체 판매가 검증</h1>",
         "<p class='sub'>기준은 <b>홀 매장가</b>다. 배달앱 가격에는 배달비가 얹혀 있어 "
         "원가율이 실제보다 낮게 나온다. 2026-07-27 · 가격은 시세라 날마다 달라진다.</p>",
         "<div class='sum'>"]
    for k, lab in (("ok", "공식일치"), ("diff", "값다름"), ("none", "미검증"), ("nocol", "수집없음")):
        P.append("<div class='card'><b class='%s'>%d</b><span>%s</span></div>"
                 % ("ok" if k == "ok" else "bad", cnt[k], lab))
    P.append("</div>")
    for st, lab in (("diff", "❗ 값이 다르다 — 확인 대상"), ("none", "⚠️ 미검증 — 공식에 같은 이름이 없다"),
                    ("nocol", "🚫 수집분 없음 — 홈페이지를 못 읽었다"), ("ok", "✅ 공식과 일치")):
        sel = [r for r in rows if r["st"] == st]
        if not sel:
            continue
        P.append("<h2>%s <span class='b'>%d</span></h2>" % (lab, len(sel)))
        P.append("<table><tr><th>브랜드</th><th>가맹점</th><th>메뉴</th><th>우리 판매가</th>"
                 "<th>판정</th><th>도장</th></tr>")
        for r in sel:
            P.append("<tr><td>%s</td><td class='r k'>%s</td><td>%s</td>"
                     "<td class='r'>%s원</td><td>%s</td><td>%s</td></tr>"
                     % (r["b"]["name"], format(r["b"]["fc"] or 0, ","), r["m"]["name"],
                        format(r["sp"], ","), r["why"], "✅" if r["m"]["vf"] else ""))
        P.append("</table>")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(P))
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
