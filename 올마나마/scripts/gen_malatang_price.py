# -*- coding: utf-8 -*-
# 마라탕 셀프바 재료 단가표 — _preview/malatang-price.html (2026-07-24)
#  올마나마 유튜브에서 마라탕 콘텐츠를 올리는 중이라 유입이 몰릴 걸 대비해 만든 전용 페이지.
#  그래서 GNAV(상위 메인 메뉴)에도 5번째로 넣는다(theme.py의 GNAV 참고).
#
#  ⚠️ 데이터는 DB 실시간 조인이 아니라 **아래 MALATANG_ITEMS 리터럴**이다(dish_data.py DISHES와 같은 패턴).
#     이유: 62종 각각을 ingredient_key로 정확히 지목하려 했더니 DB에 같은 재료명의 후보가
#     여러 개(예: 분모자 16종·피쉬볼 23종) 있어서 이름만으로는 어느 SKU가 "그 재료"인지 특정이 안 됐다.
#     반면 세션인계 문서(마라탕-재료목록-2026-07-23.md)의 100g당 가격·근거는 대표님이 실제 앱에서
#     확인해 확정한 값이라 이걸 그대로 옮기는 게 더 정확하다. 나중에 가격이 바뀌면 이 리터럴을 손으로 고친다.
import os, html
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE, clean_urls
from theme import (CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, SHARE_BTM, HEAD_TAGS,
                    FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_CSS, SOURCES, SOURCES_CSS, GNAV, GNAV_CSS, BODY_CSS, TYPO_CSS, gnav, P2_CSS,
                    WRAP_CSS)

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
OUT = os.path.join(BASE, "_preview", "malatang-price.html")
def esc(s): return html.escape(str(s)) if s is not None else ""

# 마라탕-재료목록-2026-07-23.md 그대로. (카테고리, [(재료명, 100g당 원, 근거), ...])
MALATANG_ITEMS = [
    ("채소", [
        ("양배추", 113, "실거래 중간값 확정 · 184개 메뉴 사용"),
        ("얼갈이배추", 284, "마켓봄 실거래(상,500g/EA)"),
        ("청경채", 239, "도매앱 실거래(상,4kg/BOX)"),
        ("알배기배추", 118, "도매앱 실거래(실속 12~16입,7kg/BOX)"),
        ("고수", 1615, "도매앱 실거래(200g/EA)"),
        ("쑥갓", 620, "도매앱 실거래(500g)"),
        ("연근", 480, "녹지푸드 자숙연근(슬라이스,1kg/EA)"),
        ("숙주나물", 143, "마켓봄 실거래(프레시원,3.5kg/BOX)"),
        ("죽순", 660, "뤄한죽순(罗汉笋) · 마켓봄"),
        ("큐브감자", 268, "냉동 감자 1.5cm(10kg/BOX)"),
    ]),
    ("버섯", [
        ("팽이버섯", 157, "도매앱 실거래(국내산 34개입 5kg/BOX)"),
        ("표고버섯(생, 실속)", 736, "도매앱 실거래(실속,1kg/EA) — 마켓봄 마른/통조림 표고와 다름"),
        ("느타리버섯", 323, "도매앱 실거래(이츠웰 친환경 2kg/BOX)"),
        ("새송이버섯", 362, "도매앱 실거래(상,2kg/BOX)"),
        ("목이버섯(흑목이)", 223, "마켓봄, 마른 상태 구매가에 불림 8배 적용(불린기준)"),
        ("백목이버섯(흰목이)", 300, "마켓봄, 마른 상태 구매가에 불림 5배 적용(불린기준)"),
    ]),
    ("두부류", [
        ("유부", 1133, "유부_두솔 기준 · 마켓봄"),
        ("두부튀김", 875, "마켓봄"),
        ("넓은두유피", 1300, "두유피_문풍 · 마켓봄"),
        ("냉동두부", 300, "코리아_냉동두부 기준 · 마켓봄"),
        ("푸주", 750, "보화 푸주 기준 · 마켓봄"),
        ("두부피", 280, "인조두부 · 마켓봄"),
        ("건두부", 375, "냉동건두부채 기준 · 마켓봄"),
        ("유부모찌(유부주머니)", 1100, "대표 실측(1kg 11,000원)"),
    ]),
    ("완자·피쉬볼", [
        ("날치알주머니(대만)", 1630, "대만 하이단보우(海胆包) · 마켓봄"),
        ("피쉬볼(생선모양)", 725, "코리아④ 생선볼 · 마켓봄"),
        ("새우피쉬볼", 775, "코리아⑤ 새우완자 · 마켓봄"),
        ("랍스터피쉬볼", 925, "코리아⑦ 룽샤피쉬볼 · 마켓봄"),
        ("갑오징어피쉬볼", 775, "코리아② · 마켓봄"),
        ("문어피쉬볼", 775, "코리아① · 마켓봄"),
        ("펭귄피쉬볼", 1480, "마켓봄(40알 이상)"),
        ("참돔치즈볼", 1630, "대만 즈신보우(台湾芝心丸子) · 마켓봄"),
        ("두부피쉬볼", 1160, "랜시_두부모양피쉬볼 · 마켓봄"),
        ("스위티콘치즈볼", 460, "스위트콘치즈볼 · 마켓봄"),
    ]),
    ("어묵·가공육", [
        ("게맛살", 480, "오양 실속"),
        ("어묵", 600, "사조대림 종합어묵 기준"),
        ("스모크햄", 440, "식자재왕(1kg 4,400원)"),
        ("옥수수콘소시지", 620, "도나우 · 마켓봄"),
        ("비엔나", 490, "칼집 비엔나(크레잇 만능) 기준"),
        ("청양고추소세지", 760, "사조오양(100g×10,1kg/EA) · 마켓봄"),
        ("메추리알", 750, "오밀오밀 깐메추리알(무항생제 원란,1kg/EA)"),
    ]),
    ("떡류·만두·수제비", [
        ("왕치즈떡", 520, "로스트롱치즈떡(떡안애·长芝士年糕,1kg×8)"),
        ("치즈떡", 480, "떡안애"),
        ("고구마떡", 420, "떡안애 찰고구마떡"),
        ("수제비", 360, "수제비_송학 기준"),
        ("물만두", 559, "오양 물만두 기준 · 국내"),
    ]),
    ("면류·당면", [
        ("넙적뉴진면", 700, "냉동_넙적뉴진맨 · 마켓봄"),
        ("원형뉴진면", 700, "가위바위보뉴진면(石头剪子布) · 마켓봄"),
        ("뉴진면", 800, "냉동 뉴진맨 기준 · 마켓봄"),
        ("쌀국수", 310, "王仁和 궈쵸미샌(过桥米线) · 마켓봄"),
        ("수정당면", 571, "수정넙적당면 · 마켓봄"),
        ("중화당면", 340, "오토_중화당면 · 마켓봄"),
        ("중국당면", 325, "조양 중화당면 · 마켓봄"),
        ("옥수수면", 280, "阿田七嘻 기준 · 마켓봄"),
        ("팬더분모자", 700, "熊猫분모자"),
        ("연근모양분모자", 400, "藕片모양분모자"),
        ("분모자", 456, "화이트분모자 기준"),
        ("넙적분모자", 347, "다원_넙적분모자"),
        ("곤약말이", 300, "魔芋小结"),
    ]),
    ("고기·해물", [
        ("우삼겹", 1200, "매장 표기명 · 마켓봄 우샤브(牛肉片) 실거래"),
        ("양고기(어깨살)", 1980, "호주산 · 마켓봄"),
        ("솔방울오징어", 500, "솔방울모양 오징어 · 마켓봄"),
    ]),
]
TOTAL_CNT = sum(len(v) for _, v in MALATANG_ITEMS)

# 근거(출처 텍스트)는 데이터로는 갖고 있지만 화면엔 안 낸다(2026-07-24 사용자 지시:
#  "그냥 가격이랑 재료만 나오게") — 재료명·100g당 가격 2열만 보여준다.
# 기본 선택 카테고리(2026-07-24 사용자 지시: "기본을 채소로 해놔 전체 말고") —
#  처음 열었을 때부터 이 카테고리만 보이고 나머지는 숨긴 채로 렌더링한다(전체를 기본으로 두면
#  8개가 한번에 쌓여 PC에서도 레이아웃이 옆으로 늘어져 보였다).
DEFAULT_CAT = "채소"

catcards = ""
for cat, items in MALATANG_ITEMS:
    rows = "".join(
        f'<tr><td class="ing">{esc(name)}</td><td class="pr">{price:,}원</td></tr>'
        for name, price, basis in items)
    hidden = '' if cat == DEFAULT_CAT else ' style="display:none"'
    catcards += (f'<div class="catcard" data-c="{esc(cat)}"{hidden}><h2 class="sect2">{esc(cat)} <span class="cnt">{len(items)}종</span></h2>'
                 f'<div class="tblwrap"><table class="ptbl"><thead><tr>'
                 f'<th class="l">재료</th><th class="r">100g당</th>'
                 f'</tr></thead><tbody>{rows}</tbody></table></div></div>')
sections_html = f'<div class="catgrid">{catcards}</div>'

# 카테고리 칩 필터 (2026-07-24 사용자 지시: "채소 같은 카테고리 선택하게 해줘 —
#  지금 다 한번에 넣으면 너무 길어"). dishes.html의 dchip 패턴과 같은 방식.
def _chip(cat):
    cls = "mchip on" if cat == DEFAULT_CAT else "mchip"
    return f'<button class="{cls}" data-c="{esc(cat)}">{esc(cat)}</button>'
chips_html = ('<div class="mchips">' + _chip("전체")
              + "".join(_chip(cat) for cat, _ in MALATANG_ITEMS) + '</div>')
# 카드가 하나만 보일 때는 .catgrid에 .solo를 붙인다 → PC에서 그 카드가 전폭을 쓰고
#  재료 목록이 2열로 흐른다(지시서 §3-2: "채소 탭이 왼쪽 절반만 쓴다"는 지적).
chips_js = """<script>
(function(){
  var grid = document.querySelector('.catgrid');
  function sync(){
    var vis = [].filter.call(document.querySelectorAll('.catcard'),
                             function(c){return c.style.display !== 'none';});
    grid.classList.toggle('solo', vis.length === 1);
  }
  document.querySelector('.mchips').addEventListener('click', function(e){
    var b = e.target.closest('.mchip'); if(!b) return;
    document.querySelectorAll('.mchip').forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');
    var c = b.dataset.c;
    document.querySelectorAll('.catcard').forEach(function(card){
      card.style.display = (c === '전체' || card.dataset.c === c) ? '' : 'none';
    });
    sync();
  });
  sync();
})();
</script>"""

# 별도결제(새우·라면사리·우동사리) 섹션은 2026-07-24 사용자 지시로 뺐다("별도결제는 지워버려").

# "제외 확정" 섹션은 2026-07-24 사용자 지시로 뺐다("제외확정 셀프바에서 안씀 지우고").

title = f"마라탕 재료 단가표 · 올마나마"
desc = f"마라탕 셀프바 재료 {TOTAL_CNT}종의 100g당 원가를 채소·버섯·두부류·완자·어묵·떡류·면류·고기 8개 카테고리로 정리했습니다. 실거래가 기준."

STYLE = f"""<style>{CSS_VARS}
{FOOTER_CSS}{ADFIT_CSS}{SOURCES_CSS}{GNAV_CSS}
*{{box-sizing:border-box;margin:0;padding:0}}
{BODY_CSS}
{TYPO_CSS}
{WRAP_CSS}
{P2_CSS}
header.top{{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}}
.logo{{font-weight:800;font-size:18px;color:var(--ink);text-decoration:none}}
.logo small{{color:var(--muted);font-weight:500;font-size:12px;margin-left:8px;padding-left:8px;border-left:1px solid var(--line)}}
.crumb{{font-size:12px;color:var(--muted);padding:12px 0 0}}
.crumb a{{color:var(--muted);text-decoration:none}}
h1{{margin:8px 0 3px}}
.lead{{font-size:13px;color:var(--muted);margin:2px 0 4px}}
.sect2{{font-size:16px;font-weight:800;margin:0 0 8px;display:flex;align-items:baseline;gap:6px}}
.sect2 .cnt{{font-size:12px;font-weight:700;color:var(--muted)}}
.catgrid{{display:flex;flex-direction:column;gap:22px;margin-top:22px}}
.catcard{{min-width:0}}
.tblwrap{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.ptbl{{width:100%;border-collapse:collapse;font-size:13.5px}}
.ptbl th{{background:var(--panel);color:var(--muted);font-weight:700;font-size:12px;padding:8px 10px;
text-align:left;white-space:nowrap;border-bottom:1px solid var(--line)}}
.ptbl th.r{{text-align:right}}
.ptbl td{{padding:9px 10px;border-bottom:1px solid var(--line)}}
.ptbl tr:last-child td{{border-bottom:0}}
.ptbl td.ing{{font-weight:700}}
.ptbl td.pr{{text-align:right;font-weight:800;color:var(--ink);white-space:nowrap;font-variant-numeric:tabular-nums}}
/* 가로 스크롤 대신 줄바꿈(2026-07-24 사용자 지시: "완자피쉬볼까지 보이고 옆으로 옮겨졌네 —
   밑으로 붙여") — 칩이 9개라 한 줄에 다 안 들어가면 다음 줄로 내려간다. */
.mchips{{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}}
.mchip{{flex:0 0 auto;border:1px solid var(--line);background:var(--card);border-radius:20px;padding:7px 13px;
font-size:13px;font-weight:700;color:var(--muted);cursor:pointer;white-space:nowrap;font-family:inherit}}
.mchip.on{{background:var(--grad);color:#fff;border-color:transparent;font-weight:800}}
.disc{{margin:18px 0 4px;font-size:11.5px;color:var(--muted);line-height:1.6}}
/* 폭(.wrap/.top .in)은 theme.py WRAP_CSS 단일 출처가 정한다 — 여기서 다시 쓰지 말 것.
   ⚠️ auto-fit + minmax(220,320)을 쓰면 912px 컨테이너에서 2열(640px)만 잡혀 오른쪽 250px이
   빈 채로 남았다(2026-07-24). 고정 3열로 간다 — 필터로 카드가 1개만 남아도 첫 칸 폭만 쓰므로
   옆으로 늘어나지 않는다. */
@media(min-width:840px){{
  .catgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px 22px;align-items:start}}
  /* 한 카테고리만 보일 때(칩 필터 기본값 '채소') — 카드가 전폭을 쓰고 목록은 2열로 흐른다.
     tbody를 grid로 만들면 tr이 셀 하나처럼 배치돼 열 나누기가 된다. */
  .catgrid.solo{{grid-template-columns:1fr}}
  .catgrid.solo .ptbl thead{{display:none}}
  .catgrid.solo .ptbl,.catgrid.solo .ptbl tbody{{display:block}}
  .catgrid.solo .ptbl tbody{{display:grid;grid-template-columns:1fr 1fr;column-gap:26px}}
  .catgrid.solo .ptbl tr{{display:flex;align-items:baseline;gap:10px;
    padding:9px 12px;border-bottom:1px solid var(--line)}}
  .catgrid.solo .ptbl td{{padding:0;border:0}}
  .catgrid.solo .ptbl td.pr{{margin-left:auto}}
}}
</style>"""

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:image" content="{SITE}/og/share.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/og/share.png">
<link rel="canonical" href="{SITE}/malatang-price.html">
{HEAD_TAGS}{HEAD_SCRIPT}{STYLE}</head>
<body><header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{SHARE_BTN}{BTN}{AUTH_BTN}{gnav("info")}</div></header>
<div class="wrap">
<div class="crumb"><a href="index.html">홈</a> › <a href="info.html">정보</a> › 마라탕 재료 단가표</div>
<h1>마라탕 셀프바 재료 {TOTAL_CNT}종 단가표</h1>
{chips_html}
{sections_html}
{ADFIT}
<div class="disc">※ 위 단가는 매장이 식자재 도매몰에서 구매하는 <b>도매 공급가</b>이며, 실제 거래처·물량에 따라 달라질 수 있습니다. 소비자가 마트에서 사는 소매가와는 다릅니다.</div>
{SOURCES}
{FOOTER_LINKS}
</div>{TOGGLE_JS}{chips_js}</body></html>"""

open(OUT, "w", encoding="utf-8").write(clean_urls(page))
print(f"생성: _preview/malatang-price.html — 마라탕 재료 {TOTAL_CNT}종")
