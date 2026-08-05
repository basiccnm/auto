# -*- coding: utf-8 -*-
"""소매 원가계산기 생성 — `_preview/calc.html` (2026-07-26 신설)

설계서 `계산기설계-2026-07-25.md` §0 의 **소매 계산기**(무료·미끼·서버 불필요).

  요리를 고르면 표준 레시피가 채워지고, g을 조절하면 집에서 만드는 값이 나온다.
  재료마다 **쿠팡 최소 구매단위·가격·구매링크**가 붙는다 → 파트너스 수익 지점.

🔴 심는 데이터 규칙
  · **소매가만 심는다.** 도매가는 우리 조사 자산이라 페이지에 넣지 않는다
    (2026-07-24에 prices.html 에서 도매·소매를 통째로 뺐던 것과 같은 이유).
    소매는 쿠팡 공개가라 유출 문제가 없다 — 설계서 §1 에 명시.
  · 쿠팡 상품 링크는 파트너스 추적 링크(link.coupang.com)를 그대로 쓴다.
    검색 API 가 이미 추적 링크를 준다(2026-07-26 확인).
"""
import io
import json
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
# 🔴 `_` 로 시작하면 build_dist 가 배포에서 제외한다(검수용 규칙).
#    계산기는 아직 검수 중이라 라이브에 올리지 않는다(대표 지시 2026-07-26).
#    공개할 때 이 파일명을 `calc.html` 로 바꾸고 GNAV·사이트맵을 함께 손보면 된다.
OUT = os.path.join(BASE, "_preview", "_calc.html")
import sys
sys.path.insert(0, os.path.join(BASE, "scripts"))
from theme import CSS_VARS, HEAD_TAGS, GNAV_CSS, WRAP_CSS, BODY_CSS, TYPO_CSS, gnav, FOOTER_LINKS, FOOTER_CSS, AUTH_BTN, AUTH_JS  # noqa

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ── 재료: 소매가 있는 것만 ────────────────────────────────────────
#  ingredient_retail 에 사람이 고른 쿠팡 상품이 있으면 그 정보(최소단위·가격·링크)를 같이 싣는다.
# 재료를 세 갈래로 나눈다 — 주재료 / 부재료 / 양념.
#  요리 페이지(gen_dishes)의 그룹 판정과 같은 기준을 쓴다. 계산기는 양념을 **별도 화면**으로
#  분리한다(대표 지시 2026-07-26): 양념은 종류가 많고 소량이라 주재료와 섞으면 화면이 흐려진다.
# ⚠️ 키워드를 넓게 잡으면 **조리용 가루가 양념으로 빨려간다** — "가루"만 보고 걸렀더니
#    밀가루·튀김가루·빵가루가 양념이 돼서 재료 탭에서 못 넣게 됐다(2026-07-26 시뮬에서 발견).
#    그래서 양념은 **맛을 내는 것만** 명시적으로 나열한다.
_SEASON = ("소스", "양념", "조미", "다대기", "설탕", "시럽", "올리고당", "물엿",
           "식초", "소금", "후추", "드레싱", "시즈닝", "케첩", "마요",
           "간장", "고추장", "된장", "쌈장", "춘장", "굴소스", "액젓", "다시다",
           "참기름", "들기름", "고춧가루", "후춧가루", "카레", "미원", "맛술", "청주")
# 조리용이라 양념이 아닌 것 — 위 키워드에 걸려도 부재료로 되돌린다
_NOT_SEASON = ("밀가루", "튀김가루", "빵가루", "전분", "부침가루", "박력", "중력", "강력",
               "식용유", "올리브블랜딩유", "전용유", "카레용")
_MAIN_TAIL = ("면·떡", "두부·묵", "곡물", "육가공", "햄·소시지", "수산가공")


def grp_of(subcat, name):
    s = subcat or ""
    nm = name or ""
    top = s.split("/")[0]
    tail = s.split("/")[-1]
    if any(w in nm for w in _NOT_SEASON):
        return "sub"
    if any(w in s or w in nm for w in _SEASON):
        return "season"
    if top in ("축산물", "수산물") or tail in _MAIN_TAIL:
        return "main"
    return "sub"


ING = {}
for r in c.execute("""
    SELECT i.ingredient_key k, i.name, i.manual_price m, i.base_unit bu, i.subcat,
           p.qty pk, p.label plabel,
           r.name pname, r.price pprice, r.url purl, r.rocket, r.status rstatus,
           (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) uses
    FROM ingredients i
    LEFT JOIN ingredient_pack p ON p.ingredient_key = i.ingredient_key
    LEFT JOIN ingredient_retail r ON r.ingredient_key = i.ingredient_key
    WHERE i.manual_price > 0
      AND (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) > 0
"""):
    # 매장 전용(치킨무·포장류)은 집에서 안 사므로 계산기에서 뺀다
    if r["rstatus"] == "store":
        continue
    ING[r["k"]] = {
        "n": r["name"], "m": round(r["m"]), "u": r["bu"],
        "g": grp_of(r["subcat"], r["name"]),
        "c": (r["subcat"] or "").split("/")[-1],
        "pk": r["pk"], "pl": r["plabel"],
        "buy": ({"n": r["pname"], "p": round(r["pprice"] or 0), "u": r["purl"],
                 "r": 1 if r["rocket"] else 0} if r["pname"] and r["purl"] else None),
        "uses": r["uses"],
    }

# 🔴 요리 자동 채우기는 넣지 않는다(대표 지시 2026-07-26: "기본 재료 넣지마 이게 더 머리 아퍼").
#    빈 화면에서 **직접 재료를 넣는** 게 계산기의 본래 쓰임이다.
#    요리별 표준 레시피는 요리 페이지(dish_*)가 이미 보여준다 — 계산기가 그걸 또 할 필요 없다.
from collections import Counter
_gc = Counter(v["g"] for v in ING.values())
print("계산기 데이터: 재료 %d종 (주재료 %d · 부재료 %d · 양념 %d)"
      % (len(ING), _gc["main"], _gc["sub"], _gc["season"]))

PAYLOAD = json.dumps({"ing": ING}, ensure_ascii=False, separators=(",", ":"))

CSS = """
.calc{max-width:560px;margin:0 auto}
.cbox{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:11px}
.csel{width:100%;border:1px solid var(--line);border-radius:10px;padding:11px 12px;font-size:15px;
font-weight:700;font-family:inherit;background:var(--card);color:var(--ink)}
.chd{font-size:13px;font-weight:800;color:var(--muted);margin:14px 2px 8px}
.irow{display:flex;align-items:center;gap:8px;padding:9px 0;border-bottom:1px solid var(--line)}
.irow:last-of-type{border-bottom:0}
.irow .inm{flex:1;min-width:0;font-weight:700;font-size:14px;line-height:1.35}
.irow .inm small{display:block;color:var(--muted);font-weight:400;font-size:11.5px;margin-top:1px}
.irow .amt{width:76px;position:relative;flex:none}
.irow .amt input{width:100%;border:1.5px solid var(--accent);border-radius:8px;padding:7px 22px 7px 7px;
text-align:right;font-weight:800;font-size:14px;background:var(--accentsoft);color:var(--ink);font-family:inherit}
.irow .amt em{position:absolute;right:7px;top:50%;transform:translateY(-50%);font-size:11px;
color:var(--accent);font-weight:700;font-style:normal;pointer-events:none}
.irow .ic{width:66px;text-align:right;font-weight:800;font-size:13.5px;flex:none;font-variant-numeric:tabular-nums}
.irow .ix{color:var(--faint);font-size:17px;cursor:pointer;padding:0 1px;flex:none;background:none;border:0}
.buy{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);padding:0 0 9px 0;
margin-top:-4px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.buy:last-of-type{border-bottom:0}
.buy a{color:#2f6fed;text-decoration:none;font-weight:700}
.buy a:hover{text-decoration:underline}
.buy .rk{font-size:10px;font-weight:800;color:#2f6fed}
.tot{position:sticky;bottom:0;background:var(--card);border:1px solid var(--accent);
border-radius:14px;padding:13px 15px;margin-top:12px;box-shadow:0 -2px 12px rgba(0,0,0,.05)}
.tot .tr{display:flex;justify-content:space-between;align-items:baseline}
.tot .tk{font-size:13px;color:var(--muted);font-weight:700}
.tot .tv{font-size:25px;font-weight:900;font-variant-numeric:tabular-nums}
.tot .ts{font-size:12.5px;color:var(--muted);margin-top:3px}
.tot .shop{font-size:12.5px;margin-top:8px;padding-top:8px;border-top:1px solid var(--line);color:var(--muted)}
.tot .shop b{color:var(--ink);font-variant-numeric:tabular-nums}
.cnote{font-size:12px;color:var(--muted);line-height:1.6;margin:10px 2px 0}
.addwrap{display:flex;gap:6px;margin-top:8px}
.addwrap select{flex:1;min-width:0}
.addbtn{border:1.5px solid var(--accent);background:var(--accentsoft);border-radius:9px;padding:9px 16px;
color:var(--accent);font-weight:800;font-size:13.5px;cursor:pointer;font-family:inherit;white-space:nowrap}
.quick{display:flex;gap:5px;flex-wrap:wrap;margin-top:10px}
.qb{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:6px 11px;
font-size:12.5px;font-weight:700;color:var(--ink);cursor:pointer;font-family:inherit}
.qb:hover{border-color:var(--accent);color:var(--accent)}
.tabs{display:flex;gap:6px;margin-bottom:11px}
.tb{flex:1;border:1px solid var(--line);background:var(--card);border-radius:10px;padding:11px;
font-size:14px;font-weight:800;color:var(--muted);cursor:pointer;font-family:inherit}
.tb.on{border-color:var(--accent);color:var(--accent);background:var(--accentsoft)}
.cnt{font-weight:800;color:var(--accent);font-size:12px;margin-left:4px;font-variant-numeric:tabular-nums}
.cap{font-size:11.5px;color:var(--muted);margin-top:9px}
.empty{color:var(--muted);font-size:13px;padding:4px 0}
.irow .qty{flex:none;display:flex;align-items:center;gap:2px;font-size:12px;color:var(--muted);font-weight:700}
.irow .qty input{width:40px;border:1px solid var(--line);border-radius:7px;padding:7px 4px;
text-align:center;font-weight:800;font-size:13px;font-family:inherit;color:var(--ink);background:var(--card)}
"""

HTML = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>원가 계산기 — 집에서 만들면 얼마? | 올마나마</title>
<!-- 🔴 설명에 「쿠팡」을 쓰지 않는다 — 파트너스 약관상 제목·설명·도메인에 상표 사용 금지.
     본문에서 사실 서술("조사한 상품은 모두 로켓배송입니다")은 괜찮다. 머리말만 안 된다.
     검사: python scripts/check_trademark.py  (배포 전 publish.py 가 자동으로 돌린다) --><meta name="description" content="요리를 고르고 재료 양만 바꾸면 집에서 만드는 재료비가 바로 나옵니다. 재료별 최소 구매단위와 가격도 함께 보여줍니다.">
__HEAD__
<style>__CSSVARS____BODY____TYPO____WRAP____GNAV____FOOTER____CALC__</style>

<header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>__AUTHBTN____GNAVHTML__</div></header>

<div class="wrap calc">
  <div class="crumb"><a href="index.html">홈</a> › 계산기</div>
  <h1>원가 계산기</h1>
  <p class="sub">재료를 넣고 <b>양만 적으면</b> 재료비가 바로 나옵니다.</p>

  <div class="tabs">
    <button class="tb on" data-t="food" onclick="tab('food')">재료 계산</button>
    <button class="tb" data-t="season" onclick="tab('season')">양념 계산</button>
  </div>

  <div class="cbox">
    <div class="addwrap">
      <input class="csel" id="q" list="iglist" placeholder="재료 검색 (예: 양파, 닭)"
             autocomplete="off" onkeydown="if(event.key==='Enter')addIng()">
      <button class="addbtn" onclick="addIng()">넣기</button>
    </div>
    <datalist id="iglist"></datalist>
    <div class="quick" id="quick"></div>
    <div class="cap" id="cap"></div>
  </div>

  <div id="sec_main">
    <div class="chd">주재료 <span class="cnt" id="n_main"></span></div>
    <div class="cbox" id="list_main"></div>
  </div>
  <div id="sec_sub">
    <div class="chd">부재료 <span class="cnt" id="n_sub"></span></div>
    <div class="cbox" id="list_sub"></div>
  </div>
  <div id="sec_season">
    <div class="chd">양념 <span class="cnt" id="n_season"></span></div>
    <div class="cbox" id="list_season"></div>
  </div>

  <div class="tot">
    <div class="tr"><span class="tk">집에서 만들면</span><span class="tv" id="tv">0원</span></div>
    <div class="ts" id="ts">재료를 고르면 계산됩니다</div>
    <div class="shop" id="shop"></div>
  </div>

  <p class="cnote">
    표시 가격은 <b>쿠팡 소매가</b> 기준이며 조사 시점 값입니다. 지역·용량·시기에 따라 실제 가격은 다를 수 있습니다.<br>
    양념·기름처럼 한 번 사서 오래 쓰는 재료는 <b>이번 요리에 쓴 양만큼만</b> 계산합니다.<br>
    이 페이지는 쿠팡 파트너스 활동의 일환으로, 구매 시 일정액의 수수료를 제공받습니다.
  </p>
</div>
__FOOTERHTML__

<script>
var D = __PAYLOAD__;
var ING = D.ing, ROWS = [];
var NAME2KEY = {};

function won(n){ return Math.round(n).toLocaleString() + '원'; }
function unitOf(k){ var u = ING[k].u; return (u === '개' || u === '세트') ? u : (u === 'L' ? 'ml' : 'g'); }
// 1인분 사용량 × 단가. kg/L 단위는 g·ml 기준으로 1000으로 나눈다.
function lineCost(k, a){
  var g = ING[k];
  return (g.u === 'kg' || g.u === 'L') ? g.m * a / 1000 : g.m * a;
}

var ORDER = Object.keys(ING).sort(function(x, y){ return ING[y].uses - ING[x].uses; });
// 무료 한도 (대표 지시 2026-07-26): 주재료 2 + 부재료 3 = 5. 양념은 별도 화면에서 5.
var LIMIT = {main:2, sub:3, season:5};
var LABEL = {main:'주재료', sub:'부재료', season:'양념'};
var TAB = 'food';

function tab(t){
  TAB = t;
  [].forEach.call(document.querySelectorAll('.tb'), function(b){
    b.classList.toggle('on', b.dataset.t === t);
  });
  document.getElementById('sec_main').style.display   = (t === 'food') ? '' : 'none';
  document.getElementById('sec_sub').style.display    = (t === 'food') ? '' : 'none';
  document.getElementById('sec_season').style.display = (t === 'season') ? '' : 'none';
  document.getElementById('q').placeholder = (t === 'season')
    ? '양념 검색 (예: 간장, 고추장)' : '재료 검색 (예: 양파, 닭)';
  fillPick();
  render();
}

function allowed(g){ return (TAB === 'season') ? (g === 'season') : (g !== 'season'); }

function fillPick(){
  var dl = document.getElementById('iglist');
  var ks = ORDER.filter(function(k){ return allowed(ING[k].g); });
  dl.innerHTML = '';
  NAME2KEY = {};
  ks.forEach(function(k){
    NAME2KEY[ING[k].n] = k;
    var o = document.createElement('option'); o.value = ING[k].n; dl.appendChild(o);
  });
  document.getElementById('quick').innerHTML = ks.slice(0, 10).map(function(k){
    return '<button class="qb" onclick="put(\\'' + k + '\\')">' + ING[k].n + '</button>';
  }).join('');
}

function countIn(g){ return ROWS.filter(function(r){ return ING[r.k].g === g; }).length; }

function put(k){
  if(!ING[k]) return;
  var g = ING[k].g;
  if(!allowed(g)){
    alert(ING[k].n + '은(는) ' + LABEL[g] + '예요. ' + (g === 'season' ? '양념 계산' : '재료 계산') + ' 탭에서 넣어주세요.');
    return;
  }
  if(ROWS.some(function(r){ return r.k === k; })) return;
  if(countIn(g) >= LIMIT[g]){
    alert(LABEL[g] + '는 ' + LIMIT[g] + '개까지 넣을 수 있어요.\\n\\n더 넣으려면 회원가입 후 메뉴 계산기를 쓰시면 됩니다.');
    return;
  }
  ROWS.push({k:k, a: (ING[k].u === '개' || ING[k].u === '세트') ? 1 : 100, q:1});
  render();
}
function addIng(){
  var box = document.getElementById('q'), v = (box.value || '').trim();
  if(!v) return;
  var k = NAME2KEY[v];
  if(!k){   // 정확히 안 맞으면 포함하는 것 중 첫 번째
    k = ORDER.filter(function(x){ return allowed(ING[x].g) && ING[x].n.indexOf(v) >= 0; })[0];
  }
  if(!k){ box.select(); return; }
  put(k);
  box.value = '';
}
function setQ(i, v){ ROWS[i].q = Math.max(1, parseInt(v) || 1); total(); }
function rm(i){ ROWS.splice(i, 1); render(); }
function setA(i, v){ ROWS[i].a = parseFloat(v) || 0; total(); }

function render(){
  var buf = {main:'', sub:'', season:''};
  ROWS.forEach(function(r, i){
    var g = ING[r.k], h = '';
    h += '<div class="irow"><div class="inm">' + g.n
       + (g.c ? '<small>' + g.c + '</small>' : '')
       + '</div>'
       + '<span class="amt"><input type="number" min="0" step="1" value="' + r.a
       + '" oninput="setA(' + i + ',this.value)"><em>' + unitOf(r.k) + '</em></span>'
       + '<span class="qty">×<input type="number" min="1" step="1" value="' + (r.q || 1)
       + '" oninput="setQ(' + i + ',this.value)"></span>'
       + '<span class="ic" id="c' + i + '"></span>'
       + '<button class="ix" onclick="rm(' + i + ')" aria-label="빼기">×</button></div>';
    if(g.buy){
      h += '<div class="buy">최소 구매 ' + (g.pl || '') + ' <b>' + won(g.buy.p) + '</b>'
         + (g.buy.r ? ' <span class="rk">로켓</span>' : '')
         + ' · <a href="' + g.buy.u + '" target="_blank" rel="nofollow sponsored noopener">쿠팡에서 보기 ↗</a></div>';
    }
    buf[g.g] += h;
  });
  ['main', 'sub', 'season'].forEach(function(g){
    var el = document.getElementById('list_' + g);
    el.innerHTML = buf[g] || '<div class="empty">' + LABEL[g] + '를 검색해서 넣어주세요.</div>';
    document.getElementById('n_' + g).textContent = countIn(g) + ' / ' + LIMIT[g];
  });
  document.getElementById('cap').textContent = (TAB === 'season')
    ? ('양념 ' + LIMIT.season + '개까지 · 수량(×)은 몇 인분인지예요')
    : ('무료로 주재료 ' + LIMIT.main + '개 + 부재료 ' + LIMIT.sub + '개까지 계산됩니다');
  total();
}

function total(){
  var t = 0, shop = 0, nbuy = 0;
  ROWS.forEach(function(r, i){
    // 지금 탭에 안 보이는 줄은 합계에서 뺀다 — 재료 계산과 양념 계산은 별도 화면이다
    if(!allowed(ING[r.k].g)) return;
    var c = lineCost(r.k, r.a) * (r.q || 1);
    t += c;
    var el = document.getElementById('c' + i);
    if(el) el.textContent = won(c);
    var g = ING[r.k];
    if(g.buy){ shop += g.buy.p; nbuy++; }
  });
  var nshow = ROWS.filter(function(r){ return allowed(ING[r.k].g); }).length;
  document.getElementById('tv').textContent = won(t);
  document.getElementById('ts').textContent = nshow
    ? ((TAB === 'season' ? '양념' : '재료') + ' ' + nshow + '가지 · 쓴 양만큼만 계산')
    : ((TAB === 'season' ? '양념을' : '재료를') + ' 넣으면 계산됩니다');
  document.getElementById('shop').innerHTML = nbuy
    ? ('재료 ' + nbuy + '가지를 쿠팡에서 다 사면 <b>' + won(shop) + '</b>'
       + ' <span style="font-size:11.5px">— 남는 건 다음에도 씁니다</span>')
    : '';
}
fillPick();
tab('food');
</script>
"""

html = (HTML
        .replace("__HEAD__", HEAD_TAGS)
        .replace("__CSSVARS__", CSS_VARS).replace("__BODY__", BODY_CSS)
        .replace("__TYPO__", TYPO_CSS).replace("__WRAP__", WRAP_CSS)
        .replace("__GNAV__", GNAV_CSS).replace("__FOOTER__", FOOTER_CSS)
        .replace("__CALC__", CSS)
        .replace("__GNAVHTML__", gnav("calc"))
        .replace("__AUTHBTN__", AUTH_BTN)
        .replace("__FOOTERHTML__", FOOTER_LINKS)
        .replace("__PAYLOAD__", PAYLOAD)
        # 이 페이지는 TOGGLE_JS 를 안 쓰므로(다크토글·공유 버튼이 없다) AUTH_JS 를 직접 붙인다.
        # 다른 6개 생성기는 TOGGLE_JS 에 이어붙여 자동으로 실린다.
        + AUTH_JS)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("생성: _preview/calc.html  (%.1fKB)" % (len(html) / 1024))
