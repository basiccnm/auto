# -*- coding: utf-8 -*-
"""계산기 4층 목업 생성 — `_preview/_menucalc.html` (2026-07-27 신설)

설계서 `계산기설계-2026-07-25.md` §0 의 4층을 **한 화면에서 눌러볼 수 있게** 만든 것.
대표가 글로 결정하기 어려워해서(2026-07-27 "기획을 해야 하는데 머리가 안 돈다")
기획을 문서가 아니라 화면으로 낸다.

    소매   무료·비회원        소매가(쿠팡)          ← 이미 gen_calc.py 로 존재
    도매   회원가입           우리 조사 도매가        ← 여기서 처음 보이는 것
    메뉴   구독 or 건당       1g 단위·양념분리·반찬    ← 진짜 도구
    배달   구독 or 건당       + 포장재·수수료         ← 제일 값나감

★ 디자인 방침 (2026-07-27)
  · 색·글꼴·폭은 theme.py 토큰을 그대로 쓴다. 계산기만 다른 팔레트를 쓰면
    나중에 사이트에 붙일 때 이질감이 생기고, 다크모드를 두 벌 관리하게 된다.
  · 더한 것은 **의미색**뿐 — 원가율 30%↓ good / 30~40 warn / 40↑ bad.
  · 4층은 서로 배타적인 탭이 아니라 **누적 해금**이다(소매⊂도매⊂메뉴⊂배달).
    그래서 탭이 아니라 게이지로 그린다.
  · 잠금은 blur 가 아니라 **숫자만 가린다.** 재료 구성과 비중 막대는 그대로 보인다 —
    "무엇으로 이루어졌는지는 알겠는데 얼마인지를 모르는" 상태가 훨씬 궁금하다.
  · PC 2단은 프로젝트에 이미 있는 P2_CSS 를 쓴다(왼쪽 조작 · 오른쪽 결과 sticky).

🔴 `_` 접두어라 build_dist 가 배포에서 제외한다. 라이브에 안 올라간다.
   확정되면 파일명에서 `_` 를 떼고 GNAV·사이트맵을 함께 손보면 된다(gen_calc.py 와 같은 규칙).

🔴 도매가가 화면에 나온다. 이건 우리 조사 자산이라 공개 페이지에 그냥 두면 안 된다.
   실제 배포 시에는 **로그인 + 과금을 통과한 뒤 서버가 값을 내려주는** 구조여야 한다.
   지금은 목업이라 전부 심어두고 잠금만 흉내 낸다.
"""
import io
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from theme import (CSS_VARS, HEAD_SCRIPT, HEAD_TAGS, BTN, SHARE_BTN, AUTH_BTN,  # noqa
                   TOGGLE_JS, GNAV_CSS, WRAP_CSS, BODY_CSS, TYPO_CSS, gnav,
                   P2_CSS, FOOTER_LINKS, FOOTER_CSS)

DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_menucalc.html")

# 목업에 심을 메뉴 — 재료가 잘 채워진 것들로 갈래별 하나씩
MENU_IDS = [23, 549, 45, 535, 86, 358, 34, 22, 547, 48]

c = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
c.row_factory = sqlite3.Row

menus = []
for mid in MENU_IDS:
    m = c.execute(
        "SELECT m.id,m.name,m.sell_price,b.name AS brand FROM menus m "
        "JOIN brands b ON b.id=m.brand_id WHERE m.id=?", (mid,)).fetchone()
    if not m:
        continue
    lines = []
    for r in c.execute(
        "SELECT mi.ingredient_key,mi.amount,mi.unit,mi.line_cost,mi.wholesale_cost,"
        "       mi.composition,i.name "
        "  FROM menu_ingredients mi JOIN ingredients i ON i.ingredient_key=mi.ingredient_key "
        " WHERE mi.menu_id=? ORDER BY mi.sort_order", (mid,)
    ):
        amt = float(r["amount"] or 0)
        if amt <= 0:
            continue
        # 🔴 단가는 라인원가÷양으로 되돌린다. 양을 바꾸면 다시 곱해 쓴다.
        #    (DB 는 라인원가만 들고 있고, 계산기는 양을 바꿔야 하므로 단가가 필요하다)
        retail = float(r["line_cost"] or 0)
        whl = float(r["wholesale_cost"] or 0) or retail
        # 최소 주문단위 — 설계서 §4. "삼겹 100g 640원"만 보여주면 현실과 어긋난다
        pk = c.execute(
            "SELECT pack_kg,bulk_only,bulk_note FROM ingredient_price "
            " WHERE ingredient_key=? AND tier IN ('도매','도소매') "
            " ORDER BY is_default DESC, price ASC LIMIT 1", (r["ingredient_key"],)).fetchone()
        # 양념 갈래 분리 — composition 이 있으면 '양념'으로 본다(설계서 §2 "양념 별도")
        kind = "sauce" if (r["composition"] or "").strip() else "main"
        lines.append({
            "k": r["ingredient_key"], "n": r["name"], "amt": round(amt, 1), "u": r["unit"],
            "ur": round(retail / amt, 4), "uw": round(whl / amt, 4),
            "kind": kind, "comp": (r["composition"] or "").strip(),
            "pack": (pk["pack_kg"] if pk else None),
            "bulk": (pk["bulk_note"] if pk and pk["bulk_only"] else None),
        })
    if lines:
        menus.append({"id": m["id"], "brand": m["brand"], "name": m["name"],
                      "sell": m["sell_price"], "lines": lines})

DATA = json.dumps(menus, ensure_ascii=False, separators=(",", ":"))

CSS = """.mc{padding-bottom:96px}
@media(min-width:840px){.mc{padding-bottom:60px}}
.lead{color:var(--muted);margin:2px 0 0}

/* ── 해금 게이지 ─────────────────────────────────────────────
   4층은 배타적 탭이 아니라 누적이다. 그래서 채워지는 레일 위에 단계를 얹는다. */
.lad{margin:18px 0 20px}
.ladbar{position:relative;height:3px;border-radius:2px;background:var(--track);overflow:hidden}
.ladbar i{position:absolute;inset:0 auto 0 0;background:var(--grad);border-radius:2px;
transition:width .35s cubic-bezier(.4,0,.2,1)}
.lad ol{list-style:none;display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:0;padding:10px 0 0}
.step{position:relative;width:100%;padding:10px 6px 11px;border:1px solid var(--line);border-radius:12px;
background:var(--card);cursor:pointer;font-family:inherit;text-align:left;color:inherit;
transition:border-color .15s,background .15s}
.step:hover{border-color:var(--accent)}
.step:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.step em{display:block;font-style:normal;font-size:10.5px;font-weight:800;letter-spacing:.06em;
color:var(--muted);text-transform:uppercase}
.step b{display:block;margin-top:3px;font-size:15px;font-weight:900;letter-spacing:-.02em}
.step span{display:block;margin-top:2px;font-size:11px;color:var(--faint);font-weight:700;line-height:1.35}
.step.open em{color:var(--good)}
.step.on{border-color:var(--accent);background:var(--accentsoft)}
.step.on b{color:var(--accent)}
.step.shut b,.step.shut span{opacity:.5}
.step .lk{position:absolute;top:9px;right:8px;width:13px;height:13px;opacity:.5}

/* ── 메뉴 고르기 ──────────────────────────────────────────── */
.pick{display:flex;gap:8px;align-items:center}
.pick select{flex:1;height:46px;padding:0 12px;border:1px solid var(--line);border-radius:12px;
background:var(--card);color:var(--ink);font-family:inherit;font-size:14.5px;font-weight:800}
.pick select:focus-visible{outline:2px solid var(--accent);outline-offset:1px}

/* ── 옵션 칩 ─────────────────────────────────────────────── */
.opt{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 0}
.opt label{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:800;
padding:9px 11px;border:1px solid var(--line);border-radius:10px;background:var(--card);cursor:pointer}
.opt input[type=number]{width:56px;height:28px;text-align:right;border:1px solid var(--line);border-radius:7px;
background:var(--bg);color:var(--ink);font-family:inherit;font-weight:800;font-variant-numeric:tabular-nums}
.opt select{border:0;background:transparent;font:inherit;font-weight:900;color:var(--accent);cursor:pointer}

/* ── 재료 줄 ─────────────────────────────────────────────── */
.grp{margin-top:20px}
.grp h3{display:flex;align-items:baseline;gap:7px;margin:0 0 2px;font-size:11px;font-weight:900;
letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
.grp h3 u{text-decoration:none;font-size:11px;font-weight:800;color:var(--faint);letter-spacing:0}
.ln{display:grid;grid-template-columns:1fr auto auto;align-items:center;column-gap:10px;
padding:11px 0 9px;border-bottom:1px solid var(--line)}
.ln .nm{min-width:0}
.ln .nm b{display:block;font-size:14px;font-weight:800;letter-spacing:-.01em;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ln .nm small{display:block;color:var(--faint);font-size:11px;margin-top:2px;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ln .qty{display:flex;align-items:center;gap:5px}
.ln input{width:70px;height:36px;text-align:right;padding:0 8px;border:1px solid var(--line);border-radius:9px;
background:var(--bg);color:var(--ink);font-family:inherit;font-size:14px;font-weight:800;
font-variant-numeric:tabular-nums}
.ln input:focus-visible{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
.ln .fix{width:70px;text-align:right;font-size:14px;font-weight:800;font-variant-numeric:tabular-nums;
color:var(--muted)}
.ln .un{width:22px;font-size:11.5px;color:var(--faint);font-weight:800}
.ln .cost{min-width:76px;text-align:right;font-size:14.5px;font-weight:900;font-variant-numeric:tabular-nums}
.ln .cost.hid{color:var(--faint);letter-spacing:.12em}
/* 비중 막대 — 어느 재료가 원가를 먹는지가 이 도구의 핵심 정보다.
   잠긴 층에서도 이건 보여준다(값은 가리고 구조는 보여준다). */
.ln .bar{grid-column:1/-1;height:3px;margin-top:7px;border-radius:2px;background:var(--track);overflow:hidden}
.ln .bar i{display:block;height:100%;border-radius:2px;background:var(--accent);opacity:.75;
transition:width .25s ease}
.ln.sauce .bar i{background:var(--blue);opacity:.6}

/* ── 결과 카드 ───────────────────────────────────────────── */
.res{border:1px solid var(--line);border-radius:16px;background:var(--card);padding:16px 15px 14px}
.res .cap{font-size:11px;font-weight:900;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
.res .big{display:flex;align-items:baseline;gap:6px;margin:5px 0 2px}
.res .big b{font-size:32px;font-weight:900;letter-spacing:-.03em;font-variant-numeric:tabular-nums;
line-height:1.05}
.res .big span{font-size:15px;font-weight:800;color:var(--muted)}
.res .big.hid b{color:var(--faint);letter-spacing:.06em}
.rate{display:inline-flex;align-items:baseline;gap:5px;margin-top:9px;padding:5px 10px;border-radius:999px;
font-size:12.5px;font-weight:900;font-variant-numeric:tabular-nums}
.rate.good{background:var(--goodbg);color:var(--good)}
.rate.warn{background:var(--warnbg);color:var(--warntext)}
.rate.bad{background:var(--badbg);color:var(--bad)}
.brk{margin-top:14px;padding-top:12px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:1px}
.brk .r{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:5px 0;font-size:13.5px}
.brk .r span{color:var(--muted);font-weight:700}
.brk .r b{font-weight:900;font-variant-numeric:tabular-nums}
.brk .r.em{margin-top:6px;padding-top:9px;border-top:1px solid var(--line);font-size:15px}
.brk .r.em b{color:var(--accent)}
.brk .r b.hid{color:var(--faint);letter-spacing:.1em}
.note{margin-top:12px;font-size:11.5px;color:var(--faint);line-height:1.7}
.note b{color:var(--muted)}

/* ── 잠금 안내 ───────────────────────────────────────────── */
.gate{margin:-6px 0 18px;padding:14px 15px;border:1px solid var(--accent);border-radius:14px;
background:var(--accentsoft)}
.gate .gt{font-size:14.5px;font-weight:900;letter-spacing:-.01em}
.gate .gs{margin-top:5px;font-size:12.5px;color:var(--muted);line-height:1.65}
.gate .ga{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}
.gate button{flex:1;min-width:120px;padding:11px 14px;border-radius:11px;font-size:13.5px;font-weight:900;
font-family:inherit;cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.gate button.pri{background:var(--accent);border-color:var(--accent);color:#fff}
.gate button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}

/* ── 모바일 하단 고정 요약 ───────────────────────────────── */
.dock{position:fixed;left:0;right:0;bottom:0;z-index:40;display:flex;align-items:center;gap:12px;
padding:11px 16px calc(11px + env(safe-area-inset-bottom));background:var(--card);
border-top:1px solid var(--line);box-shadow:0 -8px 24px -18px rgba(0,0,0,.6)}
.dock .dl{font-size:11px;font-weight:900;letter-spacing:.06em;color:var(--muted);text-transform:uppercase}
.dock .dv{font-size:20px;font-weight:900;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.dock .dv.hid{color:var(--faint);letter-spacing:.08em}
.dock .sp{flex:1}
@media(min-width:840px){.dock{display:none}}

/* ── 정할 것 ─────────────────────────────────────────────── */
.todo{margin:26px 0 0;padding:15px 16px;border:1px solid var(--warnline);border-radius:14px;background:var(--warnbg)}
.todo b.t{display:block;font-size:13px;font-weight:900;color:var(--warntext);margin-bottom:8px}
.todo ol{margin:0;padding-left:19px;font-size:13px;color:var(--warntext);line-height:1.9}
.todo li{padding-left:2px}"""

BODY = """<div class="crumb"><a href="index.html">홈</a> › 계산기(목업)</div>
<h1>원가 계산기</h1>
<p class="lead">재료를 1g 단위로 넣으면 원가가 바로 나옵니다. 아래 <b>4단계는 위로 갈수록 열립니다.</b></p>

<div class="lad">
  <div class="ladbar"><i id="ladfill" style="width:25%"></i></div>
  <ol id="lad"></ol>
</div>

<!-- 🔴 잠금 안내는 **벽에 부딪힌 자리**에 있어야 한다.
     결과 카드 안에만 두면 좁은 화면에서 재료 목록 한참 아래로 밀려 못 찾는다. -->
<div id="gate"></div>

<div class="p2">
  <div>
    <div class="pick"><select id="menu" aria-label="메뉴 고르기"></select></div>
    <div id="opts"></div>
    <div id="lines"></div>
  </div>
  <aside class="side"><div id="side"></div></aside>
</div>

<div class="todo">
  <b class="t">여기서 정할 것 — 화면 보면서 고르시면 됩니다</b>
  <ol>
    <li>잠긴 층에서 지금은 <b>재료 구성과 비중 막대는 보여주고 금액만 가립니다.</b>
        이게 맞는지, 아니면 통째로 감출지</li>
    <li>메뉴 계산기 <b>건당 100원</b>이 맞는지 (설계서 값)</li>
    <li>배달 계산기를 <b>건당으로도</b> 팔지, 구독 전용으로 둘지</li>
    <li>양념을 <b>한 줄로 묶을지</b>(소매층) 재료별로 펼칠지(유료층) — 지금은 층에 따라 다릅니다</li>
    <li>반찬 기본 35g 가정을 <b>메뉴 종류별로</b> 다르게 할지</li>
    <li><b>배달 계산기의 정체</b> — 지금은 "손익분기선"입니다. 마라떡볶이가 7,000원으로 나오는데
        실제 판매가는 16,000원입니다. 인건비·임대료가 안 들어가서 그렇습니다.
        ① 이대로 "최소선"으로 갈지 ② 인건비·임대료도 입력받아 진짜 권장가를 낼지 —
        ②로 가면 도구는 훨씬 값나가지만 입력이 늘어 이탈이 생깁니다.</li>
  </ol>
</div>"""

JS = """<script>
/* ══════════════════════════════════════════════════════════════
   ★ 자주 바꿀 값은 전부 여기 모아뒀습니다. 숫자만 고치면 화면이 따라갑니다.
   ══════════════════════════════════════════════════════════════ */

// 층 정의 — 위로 갈수록 누적으로 열린다
var 층 = [
  {id:'retail', 이름:'소매', 조건:'무료',   설명:'집에서 만들면',   가격:0,   잠금:null},
  {id:'whole',  이름:'도매', 조건:'회원',   설명:'업소용 도매가',   가격:10,  잠금:'login'},
  {id:'menu',   이름:'메뉴', 조건:'유료',   설명:'1g 단위·양념·반찬', 가격:100, 잠금:'pay'},
  {id:'deliv',  이름:'배달', 조건:'유료',   설명:'포장·배달 수수료',  가격:300, 잠금:'pay'}
];

// 배달앱 중개수수료 — ⚠️ 아래는 자리표시용 숫자입니다. 실제 요율로 바꿔야 합니다.
//   자동수집 안 합니다(잘 안 바뀌고, 바뀌면 뉴스로 압니다). 설계서 §3.
var 배달앱 = {
  '배민 배민1': {중개:0.068},
  '쿠팡이츠':   {중개:0.098},
  '요기요':     {중개:0.128}
};

var 반찬기본g   = 35;    // 백반·국밥은 반찬이 원가의 큰 부분 (설계서 §2)
var 반찬단가    = 3.2;   // 원/g — ⚠️ 어림값. 반찬 레시피가 생기면 실제 원가로 바꿀 것
var 포장재기본  = 350;   // 배달 1건당 용기+봉투. 식봄 포장 카테고리에서 가져올 값
var 원가율기준  = {좋음:30, 보통:40};   // % — 이 위로는 빨강

var MENUS = __DATA__;
/* ════════════════════════════════════════════════════════════ */

var LOCK = '<svg class="lk" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '+
  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+
  '<rect x="4" y="10.5" width="16" height="10" rx="2.2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/></svg>';

var state = {tier:'retail', menu:MENUS[0].id, amt:{}, 반찬:false, 앱:'배민 배민1', 로그인:false, 잔액:0};

function won(n){return Math.round(n).toLocaleString('ko-KR');}
function cur(){for(var i=0;i<MENUS.length;i++)if(MENUS[i].id===state.menu)return MENUS[i];return MENUS[0];}
function tierAt(id){for(var i=0;i<층.length;i++)if(층[i].id===id)return 층[i];return 층[0];}
function tier(){return tierAt(state.tier);}
function amtOf(l){var k=state.menu+'|'+l.k;return state.amt[k]!==undefined?state.amt[k]:l.amt;}
function unit(l){return state.tier==='retail'?l.ur:l.uw;}  /* 소매층만 소매가, 나머지는 도매가 */

/* 그 층을 열 수 있는가 — null 이면 열림, 아니면 막힌 이유 */
function lockOf(id){
  var t=tierAt(id);
  if(t.잠금==='login')return state.로그인?null:'login';
  if(t.잠금==='pay')return !state.로그인?'login':(state.잔액<t.가격?'pay':null);
  return null;
}
function locked(){return lockOf(state.tier);}

function drawLadder(){
  var openCount=0;
  층.forEach(function(t){if(!lockOf(t.id))openCount++;});
  document.getElementById('ladfill').style.width=(openCount/층.length*100)+'%';
  document.getElementById('lad').innerHTML=층.map(function(t){
    var shut=!!lockOf(t.id), on=t.id===state.tier;
    return '<li><button class="step'+(on?' on':'')+(shut?' shut':' open')+'" data-t="'+t.id+'"'+
      (on?' aria-current="true"':'')+'>'+(shut?LOCK:'')+
      '<em>'+t.조건+(t.가격?' '+t.가격+'원':'')+'</em>'+
      '<b>'+t.이름+'</b><span>'+t.설명+'</span></button></li>';
  }).join('');
  [].forEach.call(document.querySelectorAll('.step'),function(b){
    b.onclick=function(){state.tier=b.dataset.t;draw();};});
}

function drawOpts(){
  var o=document.getElementById('opts'),t=state.tier;
  if(t!=='menu'&&t!=='deliv'){o.innerHTML='';return;}
  var h='<div class="opt"><label><input type="checkbox" id="bc"'+(state.반찬?' checked':'')+'> 반찬 포함'+
    ' <input type="number" id="bg" value="'+반찬기본g+'" min="0" step="5" aria-label="반찬 그램">g</label>';
  if(t==='deliv'){
    h+='<label>배달앱 <select id="ap">'+Object.keys(배달앱).map(function(k){
      return '<option'+(k===state.앱?' selected':'')+'>'+k+'</option>';}).join('')+'</select></label>';
  }
  o.innerHTML=h+'</div>';
  var bc=document.getElementById('bc'); if(bc)bc.onchange=function(){state.반찬=bc.checked;draw();};
  var bg=document.getElementById('bg'); if(bg)bg.oninput=function(){반찬기본g=+bg.value||0;draw();};
  var ap=document.getElementById('ap'); if(ap)ap.onchange=function(){state.앱=ap.value;draw();};
}

function calc(){
  var m=cur(),재료=0,양념=0;
  m.lines.forEach(function(l){
    var v=amtOf(l)*unit(l);
    if(l.kind==='sauce')양념+=v;else 재료+=v;
  });
  var 반찬=(state.반찬&&(state.tier==='menu'||state.tier==='deliv'))?반찬기본g*반찬단가:0;
  var o={재료:재료,양념:양념,반찬:반찬,원가:재료+양념+반찬,판매:m.sell};
  o.율 = o.판매 ? o.원가/o.판매*100 : 0;
  if(state.tier==='deliv'){
    var a=배달앱[state.앱];
    o.포장=포장재기본;
    o.중개=m.sell*a.중개;
    o.최소=(o.원가+포장재기본)/(1-a.중개);
  }
  return o;
}

/* 잠긴 층에서는 금액만 가린다. 재료 구성과 비중 막대는 그대로 보인다. */
function money(v,lock){return lock?'•••••':won(v)+'원';}

function drawLines(){
  var m=cur(),t=state.tier,lock=locked(),o=calc();
  var 세밀=(t==='menu'||t==='deliv');            /* 1g 단위 조절은 유료층부터 */
  var main=m.lines.filter(function(l){return l.kind==='main';});
  var sauce=m.lines.filter(function(l){return l.kind==='sauce';});
  var max=0; m.lines.forEach(function(l){max=Math.max(max,amtOf(l)*unit(l));});

  function row(l){
    var a=amtOf(l),cst=a*unit(l);
    var sub=[];
    if(l.pack)sub.push('최소 '+l.pack+'kg 단위');
    if(l.bulk)sub.push(l.bulk);
    if(l.comp&&t!=='retail')sub.push(l.comp);
    return '<div class="ln'+(l.kind==='sauce'?' sauce':'')+'">'+
      '<div class="nm"><b>'+l.n+'</b>'+(sub.length?'<small>'+sub.join(' · ')+'</small>':'')+'</div>'+
      '<div class="qty">'+
        (세밀?'<input type="number" data-k="'+l.k+'" value="'+a+'" step="1" min="0" aria-label="'+l.n+' 양">'
             :'<span class="fix">'+a+'</span>')+
        '<span class="un">'+l.u+'</span></div>'+
      '<div class="cost'+(lock?' hid':'')+'">'+money(cst,lock)+'</div>'+
      '<div class="bar"><i style="width:'+(max?Math.max(2,cst/max*100):0)+'%"></i></div></div>';
  }

  var h='<div class="grp"><h3>주재료 <u>'+main.length+'종</u></h3>'+main.map(row).join('')+'</div>';
  if(sauce.length){
    h+='<div class="grp"><h3>양념 <u>'+sauce.length+'종</u></h3>';
    h+=(t==='retail'
      ? '<div class="ln sauce"><div class="nm"><b>양념 일체</b><small>유료층에서 재료별로 펼쳐집니다</small></div>'+
        '<div class="qty"><span class="fix">—</span><span class="un"></span></div>'+
        '<div class="cost'+(lock?' hid':'')+'">'+money(o.양념,lock)+'</div>'+
        '<div class="bar"><i style="width:'+(max?Math.min(100,o.양념/max*100):0)+'%"></i></div></div>'
      : sauce.map(row).join(''))+'</div>';
  }
  document.getElementById('lines').innerHTML=h;

  [].forEach.call(document.querySelectorAll('.ln input[data-k]'),function(i){
    i.oninput=function(){state.amt[state.menu+'|'+i.dataset.k]=+i.value||0;drawLines();drawSide();drawDock();};
  });
}

function rateClass(r){return r<=원가율기준.좋음?'good':(r<=원가율기준.보통?'warn':'bad');}

function drawSide(){
  var t=state.tier,lock=locked(),o=calc();
  var h='<div class="res"><div class="cap">'+(t==='retail'?'집에서 만들 때':'업소용 도매 기준')+' 재료원가</div>'+
    '<div class="big'+(lock?' hid':'')+'"><b>'+(lock?'•••••':won(o.원가))+'</b><span>'+(lock?'':'원')+'</span></div>';
  if(!lock)h+='<div class="rate '+rateClass(o.율)+'">원가율 '+o.율.toFixed(1)+'%</div>';

  h+='<div class="brk">';
  h+='<div class="r"><span>주재료</span><b'+(lock?' class="hid"':'')+'>'+money(o.재료,lock)+'</b></div>';
  h+='<div class="r"><span>양념</span><b'+(lock?' class="hid"':'')+'>'+money(o.양념,lock)+'</b></div>';
  if(o.반찬>0)h+='<div class="r"><span>반찬 '+반찬기본g+'g</span><b'+(lock?' class="hid"':'')+'>'+money(o.반찬,lock)+'</b></div>';
  if(t==='deliv'){
    h+='<div class="r"><span>포장용기</span><b'+(lock?' class="hid"':'')+'>'+money(o.포장,lock)+'</b></div>';
    h+='<div class="r"><span>'+state.앱+' 수수료</span><b'+(lock?' class="hid"':'')+'>'+money(o.중개,lock)+'</b></div>';
    h+='<div class="r em"><span>손익분기선</span><b'+(lock?' class="hid"':'')+'>'+
       (lock?'•••••':won(Math.ceil(o.최소/100)*100)+'원')+'</b></div>';
    h+='<div class="r"><span>실제 판매가</span><b>'+won(o.판매)+'원</b></div>';
  }else{
    h+='<div class="r em"><span>판매가</span><b>'+won(o.판매)+'원</b></div>';
  }
  h+='</div>';

  if(t==='deliv'){
    /* 🔴 이 숫자를 "이 가격에 파세요"라고 부르면 안 된다.
       인건비·임대료·공과금이 하나도 안 들어가 있어서, 그대로 따르면 가게가 망한다.
       실제 판매가(16,000)와 계산값(7,000)이 2배 넘게 벌어지는 게 그 증거다. */
    h+='<div class="note"><b>손익분기선은 "이 가격에 파세요"가 아닙니다.</b> 재료·포장·배달앱 수수료만 넣은, '+
       '여기 아래로는 팔면 안 되는 선입니다. 인건비·임대료·공과금은 들어 있지 않습니다.</div>';
  }
  h+='<div class="note">'+(t==='retail'?'쿠팡 소매가':'업소용 도매가')+' 기준 · '+
     '가격은 조사 시점 기준이라 <b>날마다 달라집니다.</b> 지역·거래처에 따라 실제가는 다릅니다.</div>';
  h+='</div>';

  document.getElementById('side').innerHTML=h;

  /* 잠금 안내는 게이지 바로 아래(=벽에 부딪힌 자리)에 그린다 */
  var g=document.getElementById('gate');
  g.innerHTML=lock?gate(lock):'';
  var b=g.querySelector('.pri');  if(b)b.onclick=(lock==='login'?__login:__charge);
  var b2=g.querySelector('.sec'); if(b2)b2.onclick=__sub;
}

function drawDock(){
  var lock=locked(),o=calc();
  document.getElementById('dock').innerHTML=
    '<div><div class="dl">'+tier().이름+' 재료원가</div>'+
    '<div class="dv'+(lock?' hid':'')+'">'+(lock?'•••••':won(o.원가)+'원')+'</div></div>'+
    '<div class="sp"></div>'+
    (lock?'':'<div class="rate '+rateClass(o.율)+'">원가율 '+o.율.toFixed(1)+'%</div>');
}

function gate(kind){
  var t=tier();
  if(kind==='login')return '<div class="gate"><div class="gt">도매가는 회원에게만 보여드립니다</div>'+
    '<div class="gs">저희가 시장을 직접 돌며 조사한 자료라 아무에게나 열어두지 않습니다. 가입은 무료, 3초 걸립니다.</div>'+
    '<div class="ga"><button class="pri">카카오로 3초 가입</button></div></div>';
  return '<div class="gate"><div class="gt">'+t.이름+' 계산기 · 한 번에 '+t.가격+'원</div>'+
    '<div class="gs">충전해두고 쓸 때마다 '+t.가격+'원씩 빠집니다. 자주 쓰시면 월정액이 쌉니다.</div>'+
    '<div class="ga"><button class="pri">1만원 충전</button><button class="sec">월정액 보기</button></div></div>';
}

/* 목업용 — 실제로는 /auth/kakao/start · /api/charge 로 갑니다 */
function __login(){state.로그인=true;draw();}
function __charge(){state.로그인=true;state.잔액=10000;draw();}
function __sub(){alert('구독 화면은 아직 없습니다. 건당/월정액 중 뭘 기본으로 보여줄지 정해주세요.');}

function draw(){drawLadder();drawOpts();drawLines();drawSide();drawDock();}

document.getElementById('menu').innerHTML=MENUS.map(function(m){
  return '<option value="'+m.id+'">'+m.brand+' · '+m.name+' ('+m.sell.toLocaleString('ko-KR')+'원)</option>';}).join('');
document.getElementById('menu').onchange=function(){state.menu=+this.value;draw();};
draw();
</script>"""

html = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>원가 계산기 목업 | 올마나마</title>
<meta name="robots" content="noindex,nofollow">
{head_script}{head_tags}
<style>{v}{b}{t}{w}{g}{p2}{f}{css}</style>
</head><body>
<header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{share}{btn}{auth}{nav}</div></header>
<div class="wrap mc">
{body}
{footer}
</div>
<div class="dock" id="dock"></div>
{toggle}{js}
</body></html>""".format(
    head_script=HEAD_SCRIPT, head_tags=HEAD_TAGS,
    v=CSS_VARS, b=BODY_CSS, t=TYPO_CSS, w=WRAP_CSS, g=GNAV_CSS, p2=P2_CSS, f=FOOTER_CSS, css=CSS,
    share=SHARE_BTN, btn=BTN, auth=AUTH_BTN, nav=gnav(""),
    body=BODY, footer=FOOTER_LINKS, toggle=TOGGLE_JS,
    js=JS.replace("__DATA__", DATA))

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("생성: _preview/_menucalc.html  (%.1fKB · 메뉴 %d개 · 재료줄 %d개)"
      % (len(html) / 1024, len(menus), sum(len(m["lines"]) for m in menus)))
