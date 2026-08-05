# -*- coding: utf-8 -*-
"""🛒 소매 계산기 관리자 — 대표메뉴·재료매칭·고객요청·가격갱신. 2026-07-31 신설

    실행:  python admin_rc.py       주소: http://127.0.0.1:8803

설계 정본: `소매계산기-설계-2026-07-31.md`

⛔ **처음부터 CRUD 완비** (대표 지시 2026-07-31) — 입력만 되는 반쪽으로 만들어
   두세 번 고치는 일이 반복됐다. 모든 목록에 등록·수정·삭제·새로고침이 다 있다.

🔴 규칙 (사고 이력에서 나온 것)
   · debug/reloader 금지 — 자동리로더가 남의 파일 변경에 반응해 서버가 튕겼다(2026-07-17)
   · 배포 버튼 없음 — 검수 안 된 게 나간다. 명령어만 안내한다
   · 삭제는 확인창 + 딸린 행까지 함께
   · 사람이 고른 상품(picked_by='human')은 자동 갱신이 덮지 않는다
   · 쿠팡 검색은 **분당 50회** — 갱신 잡이 스스로 지킨다
"""
import json
import os
import sqlite3
import sys
import threading
import time
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import coupang_api as ca                    # noqa: E402
import rc_store as rc                       # noqa: E402
import rc_candidates                        # noqa: E402

# ⛔ `coupang_search` 를 import 하지 말 것 — 파일 끝에 `sys.exit(main())` 이 있어
#    import 만으로 **서버가 죽는다**(2026-07-31 실제 발생). 공용 핵심은 `coupang_api`.

PORT = 8803
app = Flask(__name__)

JOB = {"running": False, "what": None, "log": [], "state": "idle", "done": 0, "total": 0}


def jlog(m):
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m)
    JOB["log"].append(line)
    print(line, flush=True)


def db():
    c = rc.connect()
    rc.ensure(c)
    return c


# ── 화면 ─────────────────────────────────────────────────────────
CSS = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Malgun Gothic',-apple-system,sans-serif;background:#f5f6f8;color:#1a1d21;padding:0 0 70px}
a{color:#1a56b0;text-decoration:none}
header{background:#1a1d21;color:#fff;padding:11px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
header b{font-size:15px}
header nav a{color:#ffb08a;font-size:13px;margin-right:12px}
header nav a.on{color:#fff;font-weight:700}
.wrap{max-width:1240px;margin:0 auto;padding:16px}
h2{font-size:15px;margin:18px 0 9px;display:flex;align-items:center;gap:9px}
.card{background:#fff;border:1px solid #e8eaed;border-radius:12px;padding:13px 15px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;color:#6b7280;padding:7px 8px;border-bottom:1px solid #e8eaed;white-space:nowrap}
td{padding:7px 8px;border-bottom:1px solid #f1f2f4;vertical-align:middle}
tr:last-child td{border-bottom:0}
.badge{display:inline-block;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:6px}
.ok{background:#e7f6ec;color:#16a34a}.warn{background:#fffbeb;color:#a16207}
.bad{background:#fdeaea;color:#dc2626}.mut{background:#f1f2f4;color:#6b7280}
.btn{display:inline-block;padding:6px 11px;border:1px solid #d4d7dc;border-radius:8px;background:#fff;
color:#1a1d21;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit}
.btn:hover{background:#f7f8fa}.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.pri{background:#ff6b35;border-color:#ff6b35;color:#fff}
.btn.del{color:#dc2626;border-color:#f0c4c4}
.btn.sm{padding:3px 8px;font-size:11.5px}
input,select,textarea{font-family:inherit;font-size:12.5px;padding:6px 8px;border:1px solid #d4d7dc;
border-radius:7px;background:#fff}
input:focus,select:focus,textarea:focus{outline:2px solid #ffd0bd;border-color:#ff6b35}
.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.note{background:#eef7ff;border:1px solid #bfdcff;color:#1a56b0;border-radius:9px;
padding:9px 12px;font-size:12.5px;line-height:1.6;margin-bottom:11px}
.note.warn{background:#fffbeb;border-color:#fde68a;color:#78530b}
#joblog{background:#12151a;color:#a8e6a0;font-family:Consolas,monospace;font-size:11.5px;
padding:10px 12px;border-radius:9px;height:150px;overflow-y:auto;white-space:pre-wrap;line-height:1.5}
.bar{height:6px;background:#eceef1;border-radius:99px;overflow:hidden;margin:7px 0}
.bar i{display:block;height:100%;background:#ff6b35}
.mini{font-size:11px;color:#6b7280}
</style>"""


def nav(cur):
    items = [("/", "대표메뉴"), ("/candidates", "후보"), ("/requests", "고객요청"),
             ("/prices", "가격갱신")]
    h = "".join('<a href="%s" class="%s">%s</a>' % (u, "on" if u == cur else "", t)
                for u, t in items)
    return ('<header><b>🛒 소매 계산기 관리</b><nav>%s</nav>'
            '<span class="mini" style="color:#9aa1ac;margin-left:auto">'
            '배포는 여기서 안 한다 — publish.py --apply</span></header>' % h)


INDEX = CSS + """{{nav|safe}}<div class="wrap">
<h2>대표메뉴 {{rows|length}}개
  <button class="btn sm" onclick="location.reload()">새로고침</button></h2>

<div class="card">
  <div class="row">
    <input id="nGrp" placeholder="묶음 (냉면)" style="width:120px">
    <input id="nKind" placeholder="종류 (함흥냉면)" style="width:140px">
    <input id="nVar" placeholder="갈래 (물냉면)" style="width:120px">
    <input id="nName" placeholder="화면 제목 (함흥 물냉면)" style="width:190px">
    <input id="nG" placeholder="1인분 g" style="width:80px">
    <button class="btn pri" onclick="addDish()">＋ 메뉴 등록</button>
  </div>
  <p class="mini" style="margin-top:7px">제목을 비우면 「종류 갈래」 로 자동으로 만든다.
  없는 메뉴는 여기서 바로 만들고, 재료는 편집 화면에서 넣는다.</p>
</div>

<div class="card"><table>
<tr><th>묶음</th><th>종류</th><th>갈래</th><th>제목</th><th>재료</th><th>상품붙음</th>
<th>공개</th><th>수정</th><th style="width:150px"></th></tr>
{% for r in rows %}<tr>
<td class="mini">{{r.grp}}</td><td>{{r.kind}}</td><td>{{r.variant}}</td>
<td><b>{{r.name}}</b><div class="mini">{{r.slug}}</div></td>
<td>{{r.n_ing}}</td>
<td>{% if r.n_ing and r.n_pick==r.n_ing %}<span class="badge ok">{{r.n_pick}}/{{r.n_ing}}</span>
{% elif r.n_pick %}<span class="badge warn">{{r.n_pick}}/{{r.n_ing}}</span>
{% else %}<span class="badge mut">0</span>{% endif %}</td>
<td><button class="btn sm" onclick="pub({{r.id}},{{0 if r.published else 1}})">
{% if r.published %}<span class="badge ok">공개</span>{% else %}<span class="badge mut">비공개</span>{% endif %}</button></td>
<td class="mini">{{r.updated_at or ''}}</td>
<td><a class="btn sm" href="/dish/{{r.id}}">편집 →</a>
<button class="btn sm del" onclick="delDish({{r.id}},'{{r.name}}')">삭제</button></td>
</tr>{% endfor %}
{% if not rows %}<tr><td colspan="9" class="mini" style="padding:18px;text-align:center">
아직 없다. 위에서 등록하거나 <a href="/candidates">후보</a>에서 가져온다.</td></tr>{% endif %}
</table></div>
</div>
<script>
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify(b||{})});return await r.json();}
async function addDish(){
 const v=id=>document.getElementById(id).value.trim();
 if(!v('nGrp')||!v('nKind')){alert('묶음과 종류는 필수');return;}
 const r=await post('/api/dish',{grp:v('nGrp'),kind:v('nKind'),variant:v('nVar'),
  name:v('nName'),serving_g:v('nG')});
 if(r.ok)location.href='/dish/'+r.id; else alert(r.error);
}
async function pub(id,v){const r=await post('/api/dish/'+id+'/pub',{v:v});
 if(r.ok)location.reload(); else alert(r.error);}
async function delDish(id,nm){
 if(!confirm(nm+' 을(를) 지웁니다.\\n재료·붙은 상품까지 함께 지워지고 되돌릴 수 없습니다.'))return;
 const r=await post('/api/dish/'+id+'/del');if(r.ok)location.reload(); else alert(r.error);}
</script>"""


DISH = CSS + """{{nav|safe}}<div class="wrap">
<h2>{{d.name}}
  <span class="mini">{{d.grp}} · {{d.kind}} · {{d.variant}}</span>
  <button class="btn sm" onclick="location.reload()">새로고침</button>
  <a class="btn sm" href="/">← 목록</a></h2>

<div class="card">
  <div class="row">
    <input id="eGrp" value="{{d.grp}}" style="width:110px" placeholder="묶음">
    <input id="eKind" value="{{d.kind}}" style="width:130px" placeholder="종류">
    <input id="eVar" value="{{d.variant}}" style="width:110px" placeholder="갈래">
    <input id="eName" value="{{d.name}}" style="width:180px" placeholder="제목">
    <input id="eG" value="{{d.serving_g or ''}}" style="width:80px" placeholder="1인분 g">
    <input id="eMin" value="{{d.minutes or ''}}" style="width:70px" placeholder="분">
    <button class="btn" onclick="saveDish()">저장</button>
  </div>
  <div class="row" style="margin-top:8px">
    <input id="eSrc" value="{{d.source_url or ''}}" style="flex:1;min-width:240px"
      placeholder="참고 레시피 주소">
    <input id="eN" value="{{d.source_n or ''}}" style="width:110px" placeholder="참고 개수">
  </div>
  <textarea id="eHow" rows="5" style="width:100%;margin-top:8px"
    placeholder="만드는 법 — 한 줄에 한 단계. 우리 문장으로 다시 쓴다(본문 복제 금지)">{{d.how_to or ''}}</textarea>
</div>

<h2>재료 {{ings|length}}줄</h2>
<div class="card">
  <div class="row">
    <input id="iName" placeholder="표시명 (냉면 육수(봉지))" style="width:190px">
    <input id="iAmt" placeholder="양" style="width:70px">
    <input id="iUnit" value="g" style="width:60px">
    <input id="iKw" placeholder="쿠팡 검색어 (동치미 냉면육수)" style="width:210px">
    <label class="mini"><input type="checkbox" id="iMain"> 메인</label>
    <button class="btn pri" onclick="addIng()">＋ 재료</button>
  </div>
  <p class="mini" style="margin-top:7px">🔴 검색어는 <b>종류마다 다르게</b> — 함흥 육수와 평양 육수는 다른 상품이다.
  「육수」 처럼 넓은 말로 검색하면 엉뚱한 게 잡힌다.</p>
</div>

<div class="card"><table>
<tr><th style="width:170px">재료</th><th>필요량</th><th>우리 재료</th><th>검색어</th>
<th>쿠팡 상품 (최소용량)</th><th>가격</th><th>커버</th><th style="width:190px"></th></tr>
{% for g in ings %}<tr>
<td><b>{{g.name}}</b>{% if g.is_main %} <span class="badge warn">메인</span>{% endif %}</td>
<td class="mini">{{g.need_amount or '-'}}{{g.need_unit}}</td>
<td class="mini">{{g.ing_name or '—'}}</td>
<td class="mini">{{g.match_kw or '—'}}</td>
<td>{% if g.title %}<a href="{{g.url}}" target="_blank">{{g.title}}</a>
  <div class="mini">{% if g.picked_by=='human' %}<span class="badge ok">사람 확정</span>
  {% else %}<span class="badge mut">자동</span>{% endif %}
  {% if g.fresh %}<span class="badge ok">로켓프레시</span>{% elif g.rocket %}<span class="badge ok">로켓</span>{% endif %}
  {% if g.pack_amount %} · {{g.pack_amount}}{{g.pack_unit}}{% endif %}</div>
{% else %}<span class="badge bad">없음</span>{% endif %}</td>
<td class="mini">{% if g.price %}{{'{:,}'.format(g.price|int)}}원{% else %}-{% endif %}</td>
<td class="mini">{% if g.unit_bad %}<span class="badge bad">단위 불일치</span>
  <div class="mini">{{g.need_unit}} ↔ {{g.pack_unit}}</div>
{% elif g.cover %}{{g.cover}}인분{% else %}<span class="badge warn">?</span>{% endif %}</td>
<td><button class="btn sm" onclick="find({{g.id}})">쿠팡 찾기</button>
<button class="btn sm" onclick="paste({{g.id}})">주소 붙여넣기</button>
{% if g.title %}<button class="btn sm" onclick="fix({{g.id}})">용량·가격 고치기</button>{% endif %}
<button class="btn sm" onclick="editIng({{g.id}})">수정</button>
<button class="btn sm del" onclick="delIng({{g.id}},'{{g.name}}')">삭제</button></td>
</tr>
<tr id="cand{{g.id}}" style="display:none"><td colspan="8" style="background:#fafbfc"></td></tr>
{% endfor %}
{% if not ings %}<tr><td colspan="8" class="mini" style="padding:18px;text-align:center">
재료가 없다. 위에서 넣는다.</td></tr>{% endif %}
</table></div>
<h2>작업 로그</h2><div id="joblog"></div>
</div>
<script>
const DID={{d.id}};
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify(b||{})});return await r.json();}
const v=id=>document.getElementById(id).value.trim();
async function saveDish(){
 const r=await post('/api/dish/'+DID,{grp:v('eGrp'),kind:v('eKind'),variant:v('eVar'),
  name:v('eName'),serving_g:v('eG'),minutes:v('eMin'),source_url:v('eSrc'),
  source_n:v('eN'),how_to:document.getElementById('eHow').value});
 if(r.ok)location.reload(); else alert(r.error);}
async function addIng(){
 if(!v('iName')){alert('표시명은 필수');return;}
 const r=await post('/api/ing',{dish_id:DID,name:v('iName'),need_amount:v('iAmt'),
  need_unit:v('iUnit'),match_kw:v('iKw'),is_main:document.getElementById('iMain').checked?1:0});
 if(r.ok)location.reload(); else alert(r.error);}
async function delIng(id,nm){
 if(!confirm(nm+' 재료를 지웁니다. 붙은 상품도 함께 지워집니다.'))return;
 const r=await post('/api/ing/'+id+'/del');if(r.ok)location.reload(); else alert(r.error);}
async function editIng(id){
 const nm=prompt('표시명');if(nm===null)return;
 const am=prompt('필요량 (숫자)');const un=prompt('단위','g');const kw=prompt('쿠팡 검색어');
 const r=await post('/api/ing/'+id,{name:nm,need_amount:am,need_unit:un,match_kw:kw});
 if(r.ok)location.reload(); else alert(r.error);}
async function find(id){
 const tr=document.getElementById('cand'+id);const td=tr.firstElementChild;
 tr.style.display='';td.innerHTML='<span class="mini">쿠팡에서 찾는 중…</span>';
 const r=await post('/api/ing/'+id+'/find');
 if(!r.ok){td.innerHTML='<span class="badge bad">'+r.error+'</span>';return;}
 if(!r.items.length){td.innerHTML='<span class="mini">결과 없음 — 검색어를 바꿔보세요</span>';return;}
 td.innerHTML='<div class="mini" style="margin-bottom:6px">검색어: <b>'+r.kw+
  '</b> · 필요단위 <b>'+r.need_unit+'</b> 와 맞는 것부터, 그 다음 싼 순서</div>'+
  r.items.map(function(x,i){return '<div class="row" style="padding:4px 0;border-top:1px solid #eee">'+
   '<button class="btn sm pri" onclick="pick('+id+','+i+')">이걸로</button>'+
   '<span>'+x.title+'</span>'+
   '<span class="mini">'+x.price.toLocaleString()+'원'+
   (x.pack_amount?(' · '+x.pack_amount+x.pack_unit):' · 용량 못읽음')+
   (x.fresh?' <span class="badge ok">로켓프레시</span>':(x.rocket?' <span class="badge ok">로켓</span>':''))+
   (x.opt_n>1?(' <span class="badge warn">옵션 '+x.opt_n+'개 — 용량 확인</span>'):'')+
   (x.name_ok?'':' <span class="badge bad">다른 물건?</span>')+
   (x.unit_ok?'':' <span class="badge warn">단위 다름</span>')+
   (x.done_product?' <span class="badge warn">완성품?</span>':'')+'</span></div>';}).join('');
 window['_c'+id]=r.items;}
async function fix(id){
 const pa=prompt('실제 용량 숫자 (상품 페이지에서 본 값)');if(pa===null)return;
 const pu=prompt('단위 (g / ml / 개)','g');
 const pr=prompt('가격 (비우면 그대로)')||'';
 const r=await post('/api/ing/'+id+'/pickfix',{pack_amount:pa,pack_unit:pu,price:pr});
 if(r.ok)location.reload(); else alert(r.error);}
async function paste(id){
 const u=prompt('쿠팡 상품 주소를 붙여넣으세요 (웹에서 직접 찾은 더 싼 상품)');
 if(!u)return;
 const ti=prompt('상품명 (용량이 들어가게 그대로 복사)')||'';
 const pr=prompt('가격 (숫자만)')||'';
 const r=await post('/api/ing/'+id+'/paste',{url:u,title:ti,price:pr});
 if(r.ok)location.reload(); else alert(r.error);}
async function pick(id,i){
 const it=window['_c'+id][i];
 const r=await post('/api/ing/'+id+'/pick',it);
 if(r.ok)location.reload(); else alert(r.error);}
setInterval(async()=>{const r=await(await fetch('/api/joblog')).json();
 const el=document.getElementById('joblog');if(el){el.textContent=r.log.join('\\n');
 el.scrollTop=el.scrollHeight;}},2500);
</script>"""


CAND = CSS + """{{nav|safe}}<div class="wrap">
<div class="note">여러 브랜드가 <b>같은 이름</b>으로 파는 메뉴 = 시장 표준 메뉴다.
한 곳에만 있는 시그니처(뿌링클 등)는 자동으로 빠진다.
⚠️ 빈도만 보면 카페 음료가 위를 다 차지한다 — <b>집에서 해먹는 메뉴</b>를 골라야 한다.
없는 메뉴(냉면·순대국 등)는 <a href="/">대표메뉴</a>에서 직접 등록한다.</div>
<h2>후보 {{rows|length}}종
  <button class="btn sm" onclick="location.reload()">새로고침</button></h2>
<div class="card"><table>
<tr><th>업종</th><th>이름</th><th>브랜드 수</th><th>중앙 판매가</th><th>파는 곳</th><th style="width:110px"></th></tr>
{% for r in rows %}<tr>
<td class="mini">{{r.cat}}</td><td><b>{{r.name}}</b></td>
<td>{{r.n_brand}}곳</td>
<td class="mini">{% if r.mid_price %}{{'{:,}'.format(r.mid_price|int)}}원{% else %}-{% endif %}</td>
<td class="mini">{{r.brands[:5]|join(', ')}}{% if r.brands|length>5 %} 외 {{r.brands|length-5}}{% endif %}</td>
<td>{% if r.have %}<span class="badge ok">등록됨</span>
{% else %}<button class="btn sm" onclick="mk('{{r.name}}','{{r.cat}}')">＋ 등록</button>{% endif %}</td>
</tr>{% endfor %}
</table></div></div>
<script>
async function mk(name,cat){
 const grp=prompt('묶음(검색 그룹)',name);if(grp===null)return;
 const kind=prompt('종류',name);if(kind===null)return;
 const va=prompt('갈래 (없으면 비움)','')||'';
 const r=await fetch('/api/dish',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({grp:grp,kind:kind,variant:va,name:''})});
 const j=await r.json();if(j.ok)location.href='/dish/'+j.id; else alert(j.error);}
</script>"""


REQ = CSS + """{{nav|safe}}<div class="wrap">
<div class="note">손님이 「이 메뉴 넣어주세요」 로 남긴 것이다. <b>요청이 많은 순서로 만들면 된다.</b>
익명으로 넣을 수 있다(댓글은 로그인만).</div>
<h2>요청 {{rows|length}}건
  <button class="btn sm" onclick="location.reload()">새로고침</button></h2>
<div class="card">
  <div class="row"><input id="rN" placeholder="직접 추가할 메뉴 이름" style="width:220px">
  <button class="btn" onclick="add()">＋ 추가</button></div>
</div>
<div class="card"><table>
<tr><th>메뉴</th><th>요청</th><th>상태</th><th>처음</th><th>마지막</th><th style="width:230px"></th></tr>
{% for r in rows %}<tr>
<td><b>{{r.name}}</b></td><td>{{r.cnt}}회</td>
<td><span class="badge {{ {'new':'warn','doing':'mut','done':'ok','drop':'bad'}[r.status] }}">{{r.status}}</span></td>
<td class="mini">{{(r.created_at or '')[:10]}}</td><td class="mini">{{(r.last_at or '')[:10]}}</td>
<td>
<button class="btn sm" onclick="st({{r.id}},'doing')">작업중</button>
<button class="btn sm" onclick="st({{r.id}},'done')">완료</button>
<button class="btn sm" onclick="st({{r.id}},'drop')">보류</button>
<button class="btn sm del" onclick="rm({{r.id}},'{{r.name}}')">삭제</button></td>
</tr>{% endfor %}
{% if not rows %}<tr><td colspan="6" class="mini" style="padding:18px;text-align:center">
아직 요청이 없다.</td></tr>{% endif %}
</table></div></div>
<script>
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify(b||{})});return await r.json();}
async function add(){const n=document.getElementById('rN').value.trim();if(!n)return;
 const r=await post('/api/request',{name:n});if(r.ok)location.reload();else alert(r.error);}
async function st(id,s){const r=await post('/api/request/'+id,{status:s});
 if(r.ok)location.reload();else alert(r.error);}
async function rm(id,nm){if(!confirm(nm+' 요청을 지웁니다.'))return;
 const r=await post('/api/request/'+id+'/del');if(r.ok)location.reload();else alert(r.error);}
</script>"""


PRICE = CSS + """{{nav|safe}}<div class="wrap">
<div class="note warn">쿠팡 검색은 <b>분당 50회</b> 한도다. 갱신 잡이 스스로 지키며 천천히 돈다.
<b>오래된 순서로</b> 돌기 때문에 중간에 멈춰도 다음에 이어서 하면 된다.<br>
⛔ 사람이 고른 상품(사람 확정)은 자동 갱신이 <b>덮지 않는다.</b></div>

<div class="card">
  <h2 style="margin-top:0">쿠팡 (소매 — 손님에게 보이는 값)</h2>
  <p class="mini">계산기에 붙은 재료 {{n_pick}}개 · 가장 오래된 갱신 {{oldest or '없음'}}</p>
  <div class="row" style="margin-top:9px">
    <input id="cN" value="30" style="width:70px"> 개씩
    <button class="btn pri" onclick="run('coupang')">쿠팡 가격 갱신</button>
  </div>
</div>

<div class="card">
  <h2 style="margin-top:0">식봄 (도매 — 계산은 하되 이 사이트엔 안 보인다)</h2>
  <p class="mini">재료 {{n_ing}}종 · 도매가 있는 것 {{n_wh}}종</p>
  <div class="row" style="margin-top:9px">
    <button class="btn" onclick="run('sikbom')">식봄 도매가 갱신</button>
  </div>
</div>

<div class="card">
  <div class="row"><b id="jw" style="font-size:13px">대기 중</b>
  <span class="mini" id="jc"></span>
  <button class="btn sm" style="margin-left:auto" onclick="location.reload()">새로고침</button></div>
  <div class="bar"><i id="jb" style="width:0%"></i></div>
  <div id="joblog"></div>
</div>
</div>
<script>
async function run(what){
 const n=document.getElementById('cN').value||30;
 if(!confirm(what+' 갱신을 시작합니다. 오래된 순으로 '+n+'개를 돕니다.'))return;
 const r=await fetch('/api/refresh/'+what,{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({n:n})});const j=await r.json();if(!j.ok)alert(j.error);}
setInterval(async()=>{const r=await(await fetch('/api/joblog')).json();
 const el=document.getElementById('joblog');el.textContent=r.log.join('\\n');
 el.scrollTop=el.scrollHeight;
 document.getElementById('jw').textContent=r.running?('실행 중 — '+r.what):'대기 중';
 document.getElementById('jc').textContent=r.total?(r.done+' / '+r.total):'';
 document.getElementById('jb').style.width=r.total?(r.done*100/r.total)+'%':'0%';},2000);
</script>"""


# ── 라우트: 화면 ──────────────────────────────────────────────────
@app.route("/")
def index():
    c = db()
    rows = c.execute("""SELECT d.*,
        (SELECT count(*) FROM rc_ing g WHERE g.dish_id=d.id) n_ing,
        (SELECT count(*) FROM rc_ing g JOIN rc_pick p ON p.ing_id=g.id
           WHERE g.dish_id=d.id) n_pick
        FROM rc_dish d ORDER BY d.grp, d.sort_order, d.id""").fetchall()
    return render_template_string(INDEX, nav=nav("/"), rows=rows)


@app.route("/dish/<int:did>")
def dish(did):
    c = db()
    full = rc.dish_full(c, did)
    if not full:
        return "없는 메뉴", 404
    ings = []
    for g in full["ings"]:
        d = dict(g)
        d["cover"] = rc.cover_of(g["need_amount"], g["need_unit"],
                                 g["pack_amount"], g["pack_unit"])
        # 단위가 어긋나면 커버를 못 센다 — 화면에 대놓고 표시해 사람이 고치게 한다
        d["unit_bad"] = bool(g["pack_amount"]) and not rc.unit_ok(g["need_unit"],
                                                                 g["pack_unit"])
        ings.append(d)
    return render_template_string(DISH, nav=nav("/"), d=full["dish"], ings=ings)


@app.route("/candidates")
def candidates():
    import brand_menu_store as bs
    rows = rc_candidates.scan(bs.connect())
    c = db()
    have = {r[0] for r in c.execute("SELECT kind FROM rc_dish")}
    for r in rows:
        r["have"] = r["name"] in have
    return render_template_string(CAND, nav=nav("/candidates"), rows=rows)


@app.route("/requests")
def requests_page():
    c = db()
    rows = c.execute("""SELECT * FROM rc_request
                        ORDER BY (status='new') DESC, cnt DESC, id DESC""").fetchall()
    return render_template_string(REQ, nav=nav("/requests"), rows=rows)


@app.route("/prices")
def prices():
    c = db()
    n_pick = c.execute("SELECT count(*) FROM rc_pick").fetchone()[0]
    oldest = c.execute("SELECT min(picked_at) FROM rc_pick").fetchone()[0]
    n_ing = c.execute("SELECT count(*) FROM ingredients").fetchone()[0]
    n_wh = c.execute("SELECT count(*) FROM ingredients "
                     "WHERE wholesale_price IS NOT NULL").fetchone()[0]
    return render_template_string(PRICE, nav=nav("/prices"), n_pick=n_pick,
                                  oldest=(oldest or "")[:16], n_ing=n_ing, n_wh=n_wh)


# ── 라우트: CRUD ─────────────────────────────────────────────────
def body():
    return request.get_json(force=True, silent=True) or {}


def num(v):
    try:
        return float(v) if str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


@app.route("/api/dish", methods=["POST"])
def api_dish_new():
    b = body()
    grp, kind = (b.get("grp") or "").strip(), (b.get("kind") or "").strip()
    if not grp or not kind:
        return jsonify({"ok": False, "error": "묶음과 종류는 필수"})
    var = (b.get("variant") or "").strip()
    name = (b.get("name") or "").strip() or ("%s %s" % (kind, var)).strip()
    c = db()
    slug = rc.slugify(name)
    if c.execute("SELECT 1 FROM rc_dish WHERE slug=?", (slug,)).fetchone():
        slug += "-%d" % int(time.time() % 10000)
    cur = c.execute("""INSERT INTO rc_dish(grp,kind,variant,name,slug,serving_g,
                       created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (grp, kind, var, name, slug, num(b.get("serving_g")), rc.now(), rc.now()))
    c.commit()
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/dish/<int:did>", methods=["POST"])
def api_dish_edit(did):
    b = body()
    c = db()
    name = (b.get("name") or "").strip() or ("%s %s" % (b.get("kind", ""),
                                                        b.get("variant", ""))).strip()
    c.execute("""UPDATE rc_dish SET grp=?,kind=?,variant=?,name=?,serving_g=?,minutes=?,
                 source_url=?,source_n=?,how_to=?,updated_at=? WHERE id=?""",
              ((b.get("grp") or "").strip(), (b.get("kind") or "").strip(),
               (b.get("variant") or "").strip(), name, num(b.get("serving_g")),
               num(b.get("minutes")), (b.get("source_url") or "").strip() or None,
               int(num(b.get("source_n")) or 0), (b.get("how_to") or "").strip() or None,
               rc.now(), did))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/dish/<int:did>/pub", methods=["POST"])
def api_dish_pub(did):
    c = db()
    c.execute("UPDATE rc_dish SET published=?, updated_at=? WHERE id=?",
              (1 if body().get("v") else 0, rc.now(), did))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/dish/<int:did>/del", methods=["POST"])
def api_dish_del(did):
    c = db()
    # 딸린 행부터 — 상품 → 재료 → 메뉴
    c.execute("""DELETE FROM rc_pick WHERE ing_id IN
                 (SELECT id FROM rc_ing WHERE dish_id=?)""", (did,))
    c.execute("DELETE FROM rc_ing WHERE dish_id=?", (did,))
    c.execute("DELETE FROM rc_dish WHERE id=?", (did,))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/ing", methods=["POST"])
def api_ing_new():
    b = body()
    if not (b.get("name") or "").strip():
        return jsonify({"ok": False, "error": "표시명은 필수"})
    c = db()
    nxt = c.execute("SELECT COALESCE(max(sort_order),0)+1 FROM rc_ing WHERE dish_id=?",
                    (b.get("dish_id"),)).fetchone()[0]
    try:
        c.execute("""INSERT INTO rc_ing(dish_id,name,need_amount,need_unit,match_kw,
                     is_main,sort_order) VALUES(?,?,?,?,?,?,?)""",
                  (b.get("dish_id"), b["name"].strip(), num(b.get("need_amount")),
                   (b.get("need_unit") or "g").strip(),
                   (b.get("match_kw") or "").strip() or None,
                   1 if b.get("is_main") else 0, nxt))
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "같은 이름의 재료가 이미 있다"})
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/ing/<int:gid>", methods=["POST"])
def api_ing_edit(gid):
    b = body()
    c = db()
    c.execute("""UPDATE rc_ing SET name=?,need_amount=?,need_unit=?,match_kw=? WHERE id=?""",
              ((b.get("name") or "").strip(), num(b.get("need_amount")),
               (b.get("need_unit") or "g").strip(),
               (b.get("match_kw") or "").strip() or None, gid))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/ing/<int:gid>/del", methods=["POST"])
def api_ing_del(gid):
    c = db()
    c.execute("DELETE FROM rc_pick WHERE ing_id=?", (gid,))
    c.execute("DELETE FROM rc_ing WHERE id=?", (gid,))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/ing/<int:gid>/find", methods=["POST"])
def api_ing_find(gid):
    """쿠팡에서 후보를 찾아 **싼 순서**로 준다 — 소매는 최저가가 곧 최소용량이다."""
    c = db()
    g = c.execute("SELECT * FROM rc_ing WHERE id=?", (gid,)).fetchone()
    if not g:
        return jsonify({"ok": False, "error": "없는 재료"})
    kw = (g["match_kw"] or g["name"]).strip()
    ak, sk = ca.keys()
    if not ak or not sk:
        return jsonify({"ok": False, "error": ".env 에 쿠팡 키가 없다"})
    try:
        res = ca.search(kw, ak, sk)
    except Exception as e:
        return jsonify({"ok": False, "error": "쿠팡 검색 실패: %s" % str(e)[:90]})
    if not ca.ok(res):
        return jsonify({"ok": False, "error": "쿠팡 응답 오류 rCode=%s" % res.get("rCode")})
    items = []
    for p in ca.items(res):
        title = p.get("productName") or ""
        pack_a, pack_u = parse_pack(title)
        items.append({
            "product_id": str(p.get("productId") or ""),
            "title": title, "price": float(p.get("productPrice") or 0),
            "url": p.get("productUrl") or "", "image": p.get("productImage") or "",
            "item_id": ca.item_id_of(p.get("productUrl") or ""),
            "rocket": 1 if p.get("isRocket") else 0,
            "fresh": 1 if ca.is_fresh(title) else 0,
            "pack_amount": pack_a, "pack_unit": pack_u,
            # 🔴 완성품은 재료가 아니다 — 뒤로 민다(둥지냉면 사고)
            "done_product": bool(rc.DONE_PRODUCT.search(title)),
        })
    items = [x for x in items if x["price"] > 0]
    # 🔴 «필요 단위와 같은 단위로 읽힌 것» 을 먼저 보여준다.
    #    계란을 「개」 로 세는데 1.56kg 상품이 1순위로 오면 사람이 그걸 누르게 되고,
    #    그 순간 커버 계산이 막힌다(단위 불일치). 순서로 미리 막는다.
    for x in items:
        x["unit_ok"] = rc.unit_ok(g["need_unit"], x["pack_unit"] or "")
        # 🔴 이름이 안 맞으면 아예 다른 물건이다 (바나나가 오이 자리에 붙은 사고)
        x["name_ok"] = rc.name_hit([g["name"], kw], x["title"])
    # 🔴 소매는 **최저가가 곧 최소용량**이다 (대표 방침, coupang_minbuy.py 와 같은 규칙).
    #    *"그냥 최소가격을 찾으라고 / 상한을 정하지 말라고 가정용은"*
    #    ⚠️ 2026-07-31 사고 — 단위를 못 읽었다는 이유로 4,350원 오이·3,990원 계란을 뒤로 밀었더니
    #       12,190원 15개들이·7,500원 20구가 붙어 「74인분·40인분」 이 됐다.
    #       집에서 1~2인분 해먹는 사람에게 15개들이 오이를 사게 하면 안 된다.
    #    용량은 «몇 인분 덮나» 를 알려주는 참고일 뿐, 고르는 기준이 아니다.
    ca.group_options(items)
    # 🔴 옵션 상품은 **상품명의 용량을 믿으면 안 된다** (2026-07-31 대표 지적).
    #    「면사랑 함흥면사리(2kg)」 가 1,250원·5,200원 두 옵션으로 오는데,
    #    상품명은 둘 다 같다. 2kg 은 큰 옵션 이름일 뿐이라 1,250원짜리에 붙이면 틀린다.
    #    같은 상품 안에서 **싼 쪽이 작은 수량**인 건 맞지만, 그게 몇 g 인지는 API 가 안 준다.
    #    → 용량을 비우고 「옵션 N개」 로 표시해 사람이 페이지 보고 넣게 한다.
    for x in items:
        if x["opt_n"] > 1:
            x["pack_amount"], x["pack_unit"] = None, None
    items.sort(key=lambda x: (not x["name_ok"], x["done_product"], x["price"]))
    return jsonify({"ok": True, "kw": kw, "need_unit": g["need_unit"],
                    "items": items[:8]})


# 용량 파싱은 공용 모듈(coupang_api.parse_pack) — 배수 규칙을 한 곳에서만 고친다
parse_pack = ca.parse_pack


@app.route("/api/ing/<int:gid>/pick", methods=["POST"])
def api_ing_pick(gid):
    b = body()
    c = db()
    c.execute("""INSERT INTO rc_pick(ing_id,product_id,item_id,title,price,pack_amount,
                 pack_unit,url,image,rocket,fresh,picked_by,picked_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,'human',?)
                 ON CONFLICT(ing_id) DO UPDATE SET product_id=excluded.product_id,
                 item_id=excluded.item_id, title=excluded.title, price=excluded.price,
                 pack_amount=excluded.pack_amount, pack_unit=excluded.pack_unit,
                 url=excluded.url, image=excluded.image, rocket=excluded.rocket,
                 fresh=excluded.fresh, picked_by='human', picked_at=excluded.picked_at""",
              (gid, b.get("product_id"), b.get("item_id"), b.get("title"),
               num(b.get("price")), num(b.get("pack_amount")), b.get("pack_unit"),
               b.get("url"), b.get("image"), 1 if b.get("rocket") else 0,
               1 if b.get("fresh") else 0, rc.now()))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/ing/<int:gid>/paste", methods=["POST"])
def api_ing_paste(gid):
    """쿠팡 웹에서 **직접 찾은 상품**을 주소로 붙인다.

    🔴 검색 API 는 상위 10개뿐이고 호출마다 결과가 바뀐다(2026-07-31 확인).
       웹에서 더 싼 걸 봤으면 그 주소를 여기 붙이면 된다 — 제휴 링크로 바꿔서 저장한다.
    """
    b = body()
    url = (b.get("url") or "").strip()
    if "coupang.com" not in url:
        return jsonify({"ok": False, "error": "쿠팡 상품 주소가 아니다"})
    ak, sk = ca.keys()
    try:
        res = ca.deeplink(url, ak, sk)
    except Exception as e:
        return jsonify({"ok": False, "error": "딥링크 실패: %s" % str(e)[:90]})
    if not ca.ok(res) or not (res.get("data") or []):
        return jsonify({"ok": False, "error": "딥링크 응답 오류 rCode=%s" % res.get("rCode")})
    d = res["data"][0]
    link = d.get("shortenUrl") or d.get("landingUrl")
    title = (b.get("title") or "").strip() or "직접 고른 상품"
    pa, pu = ca.parse_pack(title)
    if b.get("pack_amount"):
        pa, pu = num(b.get("pack_amount")), (b.get("pack_unit") or "g").strip()
    c = db()
    c.execute("""INSERT INTO rc_pick(ing_id,product_id,title,price,pack_amount,pack_unit,
                 url,image,picked_by,picked_at) VALUES(?,?,?,?,?,?,?,?,'human',?)
                 ON CONFLICT(ing_id) DO UPDATE SET product_id=excluded.product_id,
                 title=excluded.title, price=excluded.price,
                 pack_amount=excluded.pack_amount, pack_unit=excluded.pack_unit,
                 url=excluded.url, image=excluded.image,
                 picked_by='human', picked_at=excluded.picked_at""",
              (gid, ca.product_id_of(url), title, num(b.get("price")), pa, pu,
               link, None, rc.now()))
    c.commit()
    return jsonify({"ok": True, "url": link})


@app.route("/api/ing/<int:gid>/pickfix", methods=["POST"])
def api_pick_fix(gid):
    """붙은 상품의 **용량·가격·이름을 손으로 고친다.**

    🔴 옵션 상품은 상품명만 봐선 몇 g 인지 모른다(면사랑 함흥면사리 사고).
       사람이 페이지를 보고 실제 용량을 적어 넣는 길이 반드시 있어야 한다.
    """
    b = body()
    c = db()
    if not c.execute("SELECT 1 FROM rc_pick WHERE ing_id=?", (gid,)).fetchone():
        return jsonify({"ok": False, "error": "붙은 상품이 없다"})
    c.execute("""UPDATE rc_pick SET title=COALESCE(NULLIF(?,''),title),
                 price=COALESCE(?,price), pack_amount=COALESCE(?,pack_amount),
                 pack_unit=COALESCE(NULLIF(?,''),pack_unit),
                 picked_by='human', picked_at=? WHERE ing_id=?""",
              ((b.get("title") or "").strip(), num(b.get("price")),
               num(b.get("pack_amount")), (b.get("pack_unit") or "").strip(),
               rc.now(), gid))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/request", methods=["POST"])
def api_request_new():
    n = (body().get("name") or "").strip()
    if not n:
        return jsonify({"ok": False, "error": "이름 없음"})
    c = db()
    c.execute("""INSERT INTO rc_request(name,cnt,created_at,last_at) VALUES(?,1,?,?)
                 ON CONFLICT(name) DO UPDATE SET cnt=cnt+1, last_at=excluded.last_at""",
              (n, rc.now(), rc.now()))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/request/<int:rid>", methods=["POST"])
def api_request_edit(rid):
    c = db()
    c.execute("UPDATE rc_request SET status=? WHERE id=?",
              (body().get("status", "new"), rid))
    c.commit()
    return jsonify({"ok": True})


@app.route("/api/request/<int:rid>/del", methods=["POST"])
def api_request_del(rid):
    c = db()
    c.execute("DELETE FROM rc_request WHERE id=?", (rid,))
    c.commit()
    return jsonify({"ok": True})


# ── 가격 갱신 잡 ─────────────────────────────────────────────────
@app.route("/api/joblog")
def api_joblog():
    return jsonify({"running": JOB["running"], "state": JOB["state"], "what": JOB["what"],
                    "done": JOB["done"], "total": JOB["total"], "log": JOB["log"][-160:]})


@app.route("/api/refresh/<what>", methods=["POST"])
def api_refresh(what):
    if JOB["running"]:
        return jsonify({"ok": False, "error": "다른 갱신이 실행 중이다"})
    n = int(num(body().get("n")) or 30)
    JOB.update(running=True, what=what, log=[], state="running", done=0, total=0)
    threading.Thread(target=lambda: refresh_worker(what, n), daemon=True).start()
    return jsonify({"ok": True})


def refresh_worker(what, n):
    try:
        if what == "coupang":
            refresh_coupang(n)
        else:
            jlog("식봄 갱신은 scripts/foodspring_collect.py 로 돈다 — 아직 버튼에 안 붙였다")
        JOB["state"] = "done"
    except Exception as e:
        jlog("❌ 실패: %s" % e)
        JOB["state"] = "error"
    finally:
        JOB["running"] = False


def refresh_coupang(n):
    """오래된 순으로 상품을 다시 찾는다. **사람 확정은 건드리지 않는다.**"""
    ak, sk = ca.keys()
    if not ak or not sk:
        raise RuntimeError(".env 에 쿠팡 키가 없다")
    c = db()
    rows = c.execute("""SELECT g.id, g.name, g.match_kw, p.picked_at, p.picked_by
                        FROM rc_ing g LEFT JOIN rc_pick p ON p.ing_id=g.id
                        WHERE p.picked_by IS NULL OR p.picked_by<>'human'
                        ORDER BY COALESCE(p.picked_at,'') LIMIT ?""", (n,)).fetchall()
    JOB["total"] = len(rows)
    jlog("쿠팡 갱신 %d건 — 오래된 순 · 분당 50회를 지켜 천천히 돈다" % len(rows))
    for i, g in enumerate(rows, 1):
        kw = (g["match_kw"] or g["name"]).strip()
        try:
            res = ca.search(kw, ak, sk)
            if not ca.ok(res):
                jlog("  %s → 쿠팡 응답 오류 rCode=%s" % (kw, res.get("rCode")))
                JOB["done"] = i
                time.sleep(1.3)
                continue
            pool = []
            for p in ca.items(res):
                pool.append({"product_id": str(p.get("productId") or "")})
            ca.group_options(pool)
            optn = {}
            for k, pp in enumerate(ca.items(res)):
                optn[k] = pool[k]["opt_n"]
            best = None
            for k, p in enumerate(ca.items(res)):
                title = p.get("productName") or ""
                price = float(p.get("productPrice") or 0)
                # 자동은 **이름이 맞는 것만** 붙인다 — 아니면 비워두고 사람이 본다
                if price <= 0 or rc.DONE_PRODUCT.search(title):
                    continue
                if not rc.name_hit([g["name"], kw], title):
                    continue
                if best is None or price < best[1]:
                    pa, pu = parse_pack(title)
                    if optn.get(k, 1) > 1:      # 옵션 상품 → 용량은 모른다
                        pa, pu = None, None
                    best = (title, price, p, pa, pu)
            if best:
                title, price, p, pa, pu = best
                c.execute("""INSERT INTO rc_pick(ing_id,product_id,title,price,pack_amount,
                    pack_unit,url,image,picked_by,picked_at) VALUES(?,?,?,?,?,?,?,?,'auto',?)
                    ON CONFLICT(ing_id) DO UPDATE SET product_id=excluded.product_id,
                    title=excluded.title, price=excluded.price,
                    pack_amount=excluded.pack_amount, pack_unit=excluded.pack_unit,
                    url=excluded.url, image=excluded.image, picked_at=excluded.picked_at
                    WHERE rc_pick.picked_by<>'human'""",
                          (g["id"], str(p.get("productId") or ""), title, price, pa, pu,
                           p.get("productUrl") or "", p.get("productImage") or "", rc.now()))
                c.commit()
                jlog("  %s → %s %s원" % (kw, title[:30], format(int(price), ",")))
            else:
                jlog("  %s → 쓸 만한 게 없다(완성품만 나옴)" % kw)
        except Exception as e:
            jlog("  %s → 실패: %s" % (kw, str(e)[:70]))
        JOB["done"] = i
        time.sleep(1.3)          # 분당 50회 한도 — 넉넉히 지킨다
    jlog("✅ 끝. 계산기에 반영하려면: python scripts/publish.py --apply")


if __name__ == "__main__":
    c = rc.connect()
    rc.ensure(c)
    c.close()
    print("소매 계산기 관리 → http://127.0.0.1:%d" % PORT)
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:%d" % PORT)).start()
    # ⚠️ debug/reloader 금지 — 자동리로더 사고(2026-07-17) + 긴 갱신 작업이 리로드로 죽는다
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)
