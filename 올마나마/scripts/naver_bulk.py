# -*- coding: utf-8 -*-
"""대용량·업소용 상품 펼침표 — 식봄과 동일 브랜드로 대보기 위한 표 (2026-07-20)

왜 따로 만드나: naver_compare.py는 중앙값이라 **브랜드가 안 보인다.**
대표님이 식봄과 맞춰보시려면 "같은 브랜드 · 같은 규격"이 필요하다.
   "대용량가격이랑 식봄가격이랑 비교해보면 되지 동일 브랜드로"

집밥 축(소포장·가정용)은 여기서 안 다룬다 — 식봄에 없고 정가 근처라 검증할 게 없다는
대표님 판단(2026-07-20)에 따라 **대용량·업소용만** 뽑는다.

  python scripts/naver_bulk.py           콘솔
  python scripts/naver_bulk.py --html    _preview/_naver_bulk.html
"""
import argparse
import html
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_naver_bulk.html")

# 식자재에서 자주 보이는 제조사. 상품명 앞이 판매처명인 경우가 많아
# 제조사가 뒤에 숨어 있어도 잡아낸다.
BRANDS = ("CJ제일제당", "제일제당", "백설", "청정원", "대상", "오뚜기", "샘표", "해표",
          "사조", "동원", "롯데웰푸드", "롯데", "풀무원", "대림선", "목우촌", "하림",
          "진주햄", "삼립", "SPC", "면사랑", "오양", "매일", "서울우유", "남양",
          "곰표", "대한제분", "삼양", "농심", "팔도", "이금기", "미원", "백설표",
          "곰곰", "노브랜드", "프레시지", "아워홈", "신송", "몽고", "오뚜기몰")


def brand_of(title):
    t = re.sub(r"[\[\]()]", " ", title or "")
    for b in BRANDS:
        if b in t:
            return b
    # 못 찾으면 대괄호 안 판매처 или 첫 단어
    m = re.match(r"\s*\[([^\]]{2,12})\]", title or "")
    if m:
        return m.group(1)
    w = (title or "").split()
    return w[0][:10] if w else "—"


def load():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT o.ingredient_key k, i.name inm, i.manual_price mp,
        i.wholesale_price wp, i.base_unit bu,
        o.title, o.mall, o.price, o.pack_qty q, o.pack_unit u, o.per_unit per,
        o.tier, o.rank_sim, o.link
        FROM naver_offer o JOIN ingredients i USING(ingredient_key)
        WHERE o.tier IN ('대용량','업소용')
        ORDER BY i.name, o.per_unit""").fetchall()
    con.close()
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    rs = load()
    if not rs:
        print("대용량 데이터가 없습니다 — python scripts/naver_shop.py --limit 30"); return

    if not a.html:
        cur = None
        for r in rs:
            if r["inm"] != cur:
                cur = r["inm"]
                print(f'\n■ {cur}   현재 소매 {(r["mp"] or 0):,}원/{r["bu"]}  도매 {r["wp"] or 0:,}원')
            print(f'   {r["tier"]}  {r["q"]:>5g}{r["u"]:<2} {r["price"]:>8,}원  '
                  f'= {round(r["per"]):>7,}원/{r["u"]}  [{brand_of(r["title"])}] '
                  f'{r["title"][:40]}')
        print(f"\n총 {len(rs)}건")
        return

    tr = ""
    cur = None
    for r in rs:
        if r["inm"] != cur:
            cur = r["inm"]
            tr += (f'<tr class="g"><td colspan="8"><b>{html.escape(cur)}</b>'
                   f'<span class="m"> — 현재 소매 {(r["mp"] or 0):,}원/{html.escape(r["bu"] or "")}'
                   f' · 현재 도매 {r["wp"] or 0:,}원</span></td></tr>')
        est = round(r["per"] * 0.85)
        tr += (f'<tr><td class="m">{html.escape(r["tier"])}</td>'
               f'<td><b>{html.escape(brand_of(r["title"]))}</b></td>'
               f'<td class="n">{r["q"]:g}{html.escape(r["u"])}</td>'
               f'<td class="n">{r["price"]:,}원</td>'
               f'<td class="n"><b>{round(r["per"]):,}</b></td>'
               f'<td class="n" style="color:#06c">{est:,}</td>'
               f'<td class="sb"></td>'
               f'<td class="s"><a href="{html.escape(r["link"] or "#")}" target="_blank">'
               f'{html.escape(r["title"][:56])}</a>'
               f'<div class="m">{html.escape(r["mall"] or "")}</div></td></tr>')

    doc = f"""<!doctype html><meta charset="utf-8"><title>대용량 시세 — 식봄 대조용</title>
<style>body{{font-family:'Malgun Gothic',sans-serif;margin:22px;background:#fafafa;color:#222}}
h1{{font-size:19px;margin:0 0 6px}}p{{color:#666;font-size:12.5px;line-height:1.75;margin:0 0 14px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:12.5px}}
th,td{{border:1px solid #e5e5e5;padding:6px 9px;text-align:left;vertical-align:top}}
th{{background:#f2f2f2;position:sticky;top:0;font-size:11.5px;line-height:1.35}}
tr.g td{{background:#eef4fb;border-top:2px solid #b9d3ee}}
.n{{text-align:right;white-space:nowrap}}.m{{color:#999;font-size:10.5px;font-weight:400}}
.s{{font-size:11.5px}}.s a{{color:#333;text-decoration:none}}.s a:hover{{text-decoration:underline}}
.sb{{background:#fffbe6;min-width:80px}}</style>
<h1>대용량·업소용 — 식봄 대조용</h1>
<p>같은 재료를 <b>브랜드·규격별로 전부</b> 펼쳤습니다. 식봄에서 <b>같은 브랜드 같은 규격</b>을 찾아
노란 칸에 적어놓고 대보시면 됩니다.<br>
<b>원/kg</b>이 비교 기준입니다 — 규격이 달라도 이 값끼리는 비교됩니다.<br>
<span style="color:#06c">파란 값</span> = 원/kg × 0.85 (대표님 실측 0.8~0.9의 가운데) =
<b>매장 매입가 추정</b>. 이 숫자가 식봄과 얼마나 맞는지가 관건입니다.</p>
<table><tr><th>구간</th><th>브랜드</th><th>규격</th><th>판매가</th><th>원/kg</th>
<th>×0.85<br>매장추정</th><th>식봄값<br>(적어보세요)</th><th>상품명</th></tr>{tr}</table>"""
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"생성: {OUT}  ({len(rs)}건)")


if __name__ == "__main__":
    main()
