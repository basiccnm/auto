# -*- coding: utf-8 -*-
"""로그인·마이페이지 생성 — `_preview/login.html`, `_preview/mypage.html` (2026-07-27 신설)

★ 왜 워커가 렌더하지 않고 파이썬 생성기가 굽는가
  workers/site-renderer/wrangler.toml 주석의 경고 그대로다 —
  "렌더러를 JS로 포팅하면 파이썬 렌더러와 JS 렌더러 **둘을 영원히 동기화**해야 한다."
  실제로 2026-07-17 하루에 그 이중화로 사고가 두 번 났다.
  여기서 구우면 헤더·다크모드·본문폭·푸터가 943페이지와 **자동으로** 같아진다.

★ 껍데기만 굽고 내용은 JS가 채운다
  로그인 상태는 /api/me 로 확인한다. 정적 HTML 을 개인화하면 캐시가 무력화되고,
  그 순간 모든 요청이 워커로 쏟아져 2026-07-25 의 error 1015 가 재발한다.

배포 후: python scripts/cf_purge.py login mypage    (전체 퍼지 금지)
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from theme import (CSS_VARS, HEAD_SCRIPT, HEAD_TAGS, BTN, SHARE_BTN, AUTH_BTN,  # noqa
                   TOGGLE_JS, GNAV_CSS, WRAP_CSS, BODY_CSS, TYPO_CSS, gnav,
                   FOOTER_LINKS, FOOTER_CSS)

OUT_DIR = os.path.join(BASE, "_preview")

CSS = """.acard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 18px;margin-top:16px}
.acard h1{margin:0 0 6px} .acard .sub{color:var(--muted);margin:0 0 18px}
.pbtn{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;height:50px;margin-bottom:10px;
border:1px solid var(--line);border-radius:12px;font-size:15px;font-weight:800;text-decoration:none;
font-family:inherit;cursor:pointer;background:var(--card);color:var(--ink)}
.pbtn.kakao{background:#FEE500;color:#191600;border-color:#FEE500}
.pbtn.google{background:#fff;color:#1f1f1f;border-color:#dadce0}
.pbtn.naver{background:#03C75A;color:#fff;border-color:#03C75A}
.pbtn[aria-disabled=true]{opacity:.45;pointer-events:none}
.pbtn .soon{font-size:12px;font-weight:700;opacity:.75}
.aerr{display:none;margin:0 0 14px;padding:11px 12px;border-radius:10px;font-size:13.5px;font-weight:700;
background:var(--badbg);color:var(--bad);border:1px solid var(--line)}
.anote{margin-top:16px;font-size:12.5px;color:var(--muted);line-height:1.7}
.anote a{color:var(--muted)}
.arow{display:flex;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid var(--line)}
.arow:last-child{border-bottom:0}
.arow .k{color:var(--muted);font-size:13.5px;font-weight:700;flex:0 0 auto}
.arow .v{font-weight:800;text-align:right;word-break:break-all}
.chip{display:inline-block;margin:0 4px 4px 0;padding:5px 9px;border-radius:8px;font-size:12.5px;font-weight:800;
background:var(--panel);border:1px solid var(--line)}
.lout{margin-top:18px;width:100%;height:44px;border:1px solid var(--line);border-radius:11px;background:var(--card);
color:var(--muted);font-size:14px;font-weight:800;font-family:inherit;cursor:pointer}
.lout:hover{color:var(--bad);border-color:var(--bad)}"""


def page(title, desc, here, body, extra_js=""):
    return """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | 올마나마</title>
<meta name="description" content="{desc}">
<!-- 로그인·마이페이지는 검색 노출 대상이 아니다. sitemap 에서도 뺀다(gen_sitemap.py) -->
<meta name="robots" content="noindex,nofollow">
{head_script}{head_tags}
<style>{css_vars}{body_css}{typo}{wrap}{gnav_css}{footer_css}{css}</style>
</head><body>
<header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{share}{btn}{auth}{nav}</div></header>
<div class="wrap">
{body}
{footer}
</div>
{toggle_js}{extra_js}
</body></html>""".format(
        title=title, desc=desc, head_script=HEAD_SCRIPT, head_tags=HEAD_TAGS,
        css_vars=CSS_VARS, body_css=BODY_CSS, typo=TYPO_CSS, wrap=WRAP_CSS,
        gnav_css=GNAV_CSS, footer_css=FOOTER_CSS, css=CSS,
        share=SHARE_BTN, btn=BTN, auth=AUTH_BTN, nav=gnav(here),
        body=body, footer=FOOTER_LINKS, toggle_js=TOGGLE_JS, extra_js=extra_js)


# ── 로그인 ────────────────────────────────────────────────────────
#  provider 버튼은 /api/me 의 providers 배열을 보고 켠다.
#  → 3단계에서 구글·네이버를 워커에 추가하면 **이 페이지를 다시 굽지 않아도** 버튼이 열린다.
LOGIN_BODY = """<div class="acard">
  <h1>로그인</h1>
  <p class="sub">소셜 계정으로 3초면 시작합니다. 비밀번호는 만들지 않습니다.</p>
  <div class="aerr" id="err"></div>
  <a class="pbtn kakao" id="p-kakao" href="#" aria-disabled="true">카카오로 시작하기 <span class="soon">준비 중</span></a>
  <a class="pbtn google" id="p-google" href="#" aria-disabled="true">구글로 시작하기 <span class="soon">준비 중</span></a>
  <a class="pbtn naver" id="p-naver" href="#" aria-disabled="true">네이버로 시작하기 <span class="soon">준비 중</span></a>
  <p class="anote">가입하면 <a href="terms.html">이용약관</a>과 <a href="privacy.html">개인정보처리방침</a>에 동의하는 것으로 봅니다.<br>
  받는 정보는 소셜 계정의 <b>고유번호와 닉네임</b>뿐입니다. 이메일은 선택이고, 동의하지 않아도 가입됩니다.</p>
</div>"""

LOGIN_JS = """<script>(function(){
var q=new URLSearchParams(location.search);
var next=q.get('next')||'/';
if(next.charAt(0)!=='/'||next.slice(0,2)==='//')next='/';
var MSG={CANCELED:'로그인을 취소했습니다.',STATE_MISMATCH:'보안 확인에 실패했습니다. 다시 시도해 주세요.',
STATE_EXPIRED:'시간이 지나 만료됐습니다. 다시 시도해 주세요.',STATE_NOT_FOUND:'요청을 찾을 수 없습니다. 다시 시도해 주세요.',
PROVIDER_ERROR:'소셜 로그인 서버와 통신하지 못했습니다.',ALREADY_LINKED:'이미 다른 계정에 연결된 소셜 계정입니다.',
LOGIN_REQUIRED:'먼저 로그인해 주세요.',NO_PROFILE:'프로필을 가져오지 못했습니다.',BAD_REQUEST:'잘못된 요청입니다.'};
var e=q.get('err');
if(e){var b=document.getElementById('err');b.textContent=MSG[e]||('로그인에 실패했습니다. ('+e+')');b.style.display='block';}
fetch('/api/me',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
  if(j&&j.login){location.replace(next);return;}
  (j&&j.providers||[]).forEach(function(p){
    var el=document.getElementById('p-'+p); if(!el)return;
    el.setAttribute('href','/auth/'+p+'/start?next='+encodeURIComponent(next));
    el.removeAttribute('aria-disabled');
    var s=el.querySelector('.soon'); if(s)s.remove();
  });
}).catch(function(){});
})();</script>"""

# ── 마이페이지 ────────────────────────────────────────────────────
MYPAGE_BODY = """<div class="acard">
  <h1>내 정보</h1>
  <p class="sub" id="hello">불러오는 중…</p>
  <div id="rows"></div>
  <button class="lout" id="lo">로그아웃</button>
  <p class="anote">연결한 소셜 계정마다 <b>별도의 회원</b>입니다. 같은 이메일이어도 자동으로 합치지 않습니다 —
  이메일만으로 계정을 합치면 이메일이 도용됐을 때 계정까지 넘어가기 때문입니다.</p>
</div>"""

MYPAGE_JS = """<script>(function(){
var NAME={kakao:'카카오',google:'구글',naver:'네이버'};
function row(k,v){return '<div class="arow"><span class="k">'+k+'</span><span class="v">'+v+'</span></div>';}
fetch('/api/me',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
  if(!j||!j.login){location.replace('/login?next=%2Fmypage');return;}
  var u=j.user||{};
  document.getElementById('hello').textContent=(u.nickname||'회원')+'님, 안녕하세요.';
  var linked=(j.linked||[]).map(function(p){return '<span class="chip">'+(NAME[p]||p)+'</span>';}).join('');
  var rest=(j.providers||[]).filter(function(p){return (j.linked||[]).indexOf(p)<0;})
    .map(function(p){return '<a class="chip" href="/auth/'+p+'/link?next=%2Fmypage">+ '+(NAME[p]||p)+' 연결</a>';}).join('');
  document.getElementById('rows').innerHTML=
    row('닉네임',u.nickname||'-')+
    row('이메일',u.email||'<span style="color:var(--muted);font-weight:700">미제공</span>')+
    row('연결된 계정',linked||'-')+
    (rest?row('추가 연결',rest):'');
}).catch(function(){});
document.getElementById('lo').onclick=function(){
  fetch('/api/logout',{method:'POST'}).then(function(){
    try{localStorage.removeItem('olma_u');}catch(x){}
    location.replace('/');
  });
};
})();</script>"""


def write(name, html):
    p = os.path.join(OUT_DIR, name)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("생성: _preview/%s  (%.1fKB)" % (name, len(html) / 1024))


if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

write("login.html", page("로그인", "소셜 계정으로 올마나마에 로그인합니다.", "", LOGIN_BODY, LOGIN_JS))
write("mypage.html", page("내 정보", "올마나마 회원 정보와 연결된 소셜 계정.", "", MYPAGE_BODY, MYPAGE_JS))
