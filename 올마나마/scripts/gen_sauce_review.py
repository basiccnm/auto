# -*- coding: utf-8 -*-
# 소스 배합 전수 검수용 HTML 생성 (_preview/_sauce_review.html)
#  - 카테고리→브랜드별로 모든 소스 메뉴와 현재 배합을 한눈에. 숨김/미표시도 표시.
import sqlite3, os, html
BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_sauce_review.html")
SAUCE = ('sauce_honey', 'sauce_normal', 'malatang_base', 'pizza_sauce', 'jajang_paste')
CATNAME = {"chicken":"치킨","pizza":"피자","burger":"버거","bunsik":"분식","jokbal":"족발/보쌈",
           "hansik":"한식","jungsik":"중식/아시안","ilsik":"일식","salad":"샐러드/포케","gopchang":"곱창",
           "pub":"포차","cafe":"카페","bakery":"베이커리"}
def esc(s): return html.escape(str(s)) if s is not None else ""

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
rows = con.execute(f"""SELECT m.id menu_id, m.name mname, b.name bn, c.slug cs, mi.composition comp
    FROM menu_ingredients mi JOIN menus m ON mi.menu_id=m.id JOIN brands b ON m.brand_id=b.id
    JOIN categories c ON b.category_id=c.id
    WHERE mi.ingredient_key IN ({','.join('?'*len(SAUCE))})
    ORDER BY c.slug, b.name, m.name""", SAUCE).fetchall()

from collections import defaultdict, OrderedDict
by = OrderedDict()
for r in rows:
    by.setdefault(r["cs"], []).append(r)

total = len(rows); shown = sum(1 for r in rows if r["comp"])
parts = [f"""<!doctype html><meta charset=utf-8><title>소스 배합 전수검수 · 얼마남아</title>
<style>
body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f5f6f8;color:#1a1d21;margin:0;padding:20px;line-height:1.5}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font-size:20px}} .sum{{color:#555;font-size:13px;margin-bottom:16px}}
h2{{font-size:16px;margin:22px 0 8px;padding:6px 10px;background:#1a56b0;color:#fff;border-radius:8px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee;vertical-align:top}}
th{{background:#eef2f7;font-size:12px;color:#555}}
td.b{{font-weight:700;white-space:nowrap;color:#333}} td.m{{white-space:nowrap;color:#111}}
td.s{{color:#1a56b0}} .hide{{color:#b00;font-weight:600}}
tr:hover{{background:#fafcff}}
.num{{color:#999;font-size:11px}}
</style>
<div class=wrap><h1>🧂 소스·양념 배합 전수 검수</h1>
<div class=sum>총 {total}줄 · 배합표시 {shown} · 숨김 {total-shown}. 아래를 보시고 <b>고칠 메뉴의 번호와 올바른 배합</b>을 알려주세요.</div>"""]
for cs, items in by.items():
    parts.append(f'<h2>{esc(CATNAME.get(cs,cs))} ({len(items)})</h2><table><tr><th>#</th><th>브랜드</th><th>메뉴</th><th>소스·양념 배합</th></tr>')
    for r in items:
        if r["comp"]:
            s = f'<td class=s>{esc(r["comp"])}</td>'
        else:
            s = '<td class="s hide">— (배합 미표시 / 일반 재료행)</td>'
        parts.append(f'<tr><td class=num>{r["menu_id"]}</td><td class=b>{esc(r["bn"])}</td><td class=m>{esc(r["mname"])}</td>{s}</tr>')
    parts.append('</table>')
parts.append('</div>')
open(OUT, "w", encoding="utf-8").write("\n".join(parts))
print("생성:", OUT, f"({total}줄)")
con.close()
