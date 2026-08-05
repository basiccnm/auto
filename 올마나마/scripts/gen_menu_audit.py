# -*- coding: utf-8 -*-
# 메뉴 재료 전수 감사 HTML (_preview/_menu_audit.html)
#  - 371개 메뉴의 재료·양·단가와 의심 플래그(🔴단백질 오매핑 / 🟠메인 누락)를 한눈에.
import sqlite3, os, html, re
BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_menu_audit.html")
CATNAME = {"chicken":"치킨","pizza":"피자","burger":"버거","bunsik":"분식","jokbal":"족발/보쌈",
           "hansik":"한식","jungsik":"중식/아시안","ilsik":"일식","salad":"샐러드/포케","gopchang":"곱창",
           "pub":"포차","cafe":"카페","bakery":"베이커리"}
def esc(s): return html.escape(str(s)) if s is not None else ""
VEGKEYS = {"vegetables_fresh","salad_greens","rice_uncooked"}
# 메인으로 인정 안 하는 부재료(소스·기름·튀김옷·곁들임·채소·쌀). 이 외 재료가 있으면 '메인 있음'.
NONMAIN = VEGKEYS | {"sauce_normal","sauce_honey","malatang_base","pizza_sauce","jajang_paste",
    "frying_oil","frying_powder","sidedish_set","side_pickles_moo","soup_base_korean"}

# 메뉴명 → 기대 단백질군
def name_protein(nm):
    kinds=set()
    if re.search(r'곱창|대창|막창|양구이|특양|염통|오돌뼈|닭발', nm): kinds.add('곱창/특수')
    if re.search(r'한우|소고기|우삼겹|차돌|양지|불고기|스테이크|큐브|소불|소대창|육회|소곱창', nm): kinds.add('소')
    if re.search(r'돼지|삼겹|족발|보쌈|제육|등심|돈까스|카츠|목살|항정|수육|순대|반미|분짜|바싹', nm): kinds.add('돼지')
    if re.search(r'닭|치킨|콤보|순살|파닭|윙|봉', nm): kinds.add('닭')
    if re.search(r'새우|연어|광어|초밥|스시|회|오징어|문어|낙지|해물|해산물|참치|장어|포케|사시미', nm): kinds.add('해산물')
    return kinds

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
menus = con.execute("""SELECT m.id,m.name,b.name bn,c.slug cs FROM menus m
    JOIN brands b ON m.brand_id=b.id JOIN categories c ON b.category_id=c.id
    ORDER BY c.slug,b.name,m.id""").fetchall()

from collections import OrderedDict
by=OrderedDict(); flag_cnt={'red':0,'org':0}
for m in menus: by.setdefault(m['cs'],[]).append(m)

def ings_of(mid):
    return con.execute("""SELECT i.ingredient_key,i.name,i.class,mi.amount,mi.unit,mi.line_cost
        FROM menu_ingredients mi JOIN ingredients i ON mi.ingredient_key=i.ingredient_key
        WHERE mi.menu_id=? ORDER BY mi.sort_order""",(mid,)).fetchall()

parts=[f"""<!doctype html><meta charset=utf-8><title>메뉴 재료 전수감사 · 얼마남아</title>
<style>
body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f5f6f8;color:#1a1d21;margin:0;padding:20px;line-height:1.5}}
.wrap{{max-width:1000px;margin:0 auto}} h1{{font-size:20px}} .sum{{color:#555;font-size:13px;margin-bottom:16px}}
h2{{font-size:16px;margin:22px 0 8px;padding:6px 10px;background:#1a56b0;color:#fff;border-radius:8px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:13px}}
th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #eee;vertical-align:top}}
th{{background:#eef2f7;font-size:12px;color:#555}}
td.n{{color:#999;font-size:11px;white-space:nowrap}} td.b{{font-weight:700;white-space:nowrap}} td.m{{white-space:nowrap;font-weight:600}}
.red{{background:#fdeaea}} .org{{background:#fff5e6}}
.fl{{font-size:11px;font-weight:700;padding:1px 6px;border-radius:5px;white-space:nowrap}}
.fl.r{{background:#dc2626;color:#fff}} .fl.o{{background:#f59e0b;color:#fff}}
.ing{{color:#333}} .ing b{{color:#b00}} .amt{{color:#888}}
tr:hover{{background:#fafcff}}
</style><div class=wrap><h1>🧾 메뉴 재료 전수 감사</h1>
<div class=sum id=sum>__SUM__</div>"""]

rows_html=[]
for cs,items in by.items():
    seg=[f'<h2>{esc(CATNAME.get(cs,cs))} ({len(items)})</h2><table><tr><th>#</th><th>브랜드</th><th>메뉴</th><th>재료 구성 (양)</th><th>플래그</th></tr>']
    for m in items:
        ings=ings_of(m['id'])
        keys={r['ingredient_key'] for r in ings}
        has_main=any(r['ingredient_key'] not in NONMAIN for r in ings)
        want=name_protein(m['name'])
        flags=[]; cls=''
        if 'pork_loin_tangsuyuk' in keys and want and '돼지' not in want:
            flags.append('<span class="fl r">🔴 단백질 오매핑</span>'); cls='red'; flag_cnt['red']+=1
        elif want and not has_main and cs not in ('pizza','cafe','bakery') and not re.search(r'떡볶이|피자|김밥|커피|라떼|아메리카노|빙수|디저트',m['name']):
            flags.append('<span class="fl o">🟠 메인 확인</span>'); cls='org'; flag_cnt['org']+=1
        ing_txt=' · '.join(
            (f'<b>{esc(r["name"])}</b>' if (r['ingredient_key']=='pork_loin_tangsuyuk' and 'red' in cls) else esc(r["name"]))
            +f'<span class=amt>({r["amount"]:g}{esc(r["unit"])})</span>' for r in ings)
        seg.append(f'<tr class="{cls}"><td class=n>{m["id"]}</td><td class=b>{esc(m["bn"])}</td><td class=m>{esc(m["name"])}</td><td class=ing>{ing_txt}</td><td>{"".join(flags)}</td></tr>')
    seg.append('</table>')
    rows_html.append('\n'.join(seg))

parts.append('\n'.join(rows_html)); parts.append('</div>')
htmlout='\n'.join(parts).replace('__SUM__',
    f'총 {len(menus)}개 메뉴 · <b style="color:#dc2626">🔴 단백질 오매핑 {flag_cnt["red"]}</b> · <b style="color:#f59e0b">🟠 메인 확인필요 {flag_cnt["org"]}</b>. 플래그된 것 위주로 보시고 고칠 메뉴 번호+올바른 재료를 알려주세요.')
open(OUT,'w',encoding='utf-8').write(htmlout)
print('생성:',OUT); print('🔴',flag_cnt['red'],'🟠',flag_cnt['org'])
con.close()
