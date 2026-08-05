# -*- coding: utf-8 -*-
# 다크/라이트 테마 — **단일 출처** (2026-07-18)
#
# 🔴 왜 모듈로: 색이 gen_preview_html·gen_dishes·gen_prices_page 세 곳에 각각 박혀 있다.
#    여기서 세 생성기가 CSS_VARS/HEAD_SCRIPT/BTN/TOGGLE_JS 넷만 가져다 쓴다.
#    (재료 4분류·배포주소·도매라인가에서 이미 겪은 "같은 값 두 곳=어긋남"의 반복 방지)
#
# 규칙: 특수 박스(노랑 팁/초록 절약/빨강 원가율/파랑 밀키트/오렌지 소프트)는 하드코딩 색 대신
#       아래 **시맨틱 토큰**을 쓴다. 그래야 다크에서 흰 박스·안 보이는 글자가 안 생긴다.

# <style> 안에 그대로 넣는 CSS 변수(라이트 기본 + 다크 오버라이드).
# 🎨 2026-08-02 «2구역 규칙» 리디자인 — 대표 승인분
#  ■ 브랜드 존(캐릭터·크림·모눈·검은고딕 허용) = 홈 히어로 / 로고·파비콘 / 레시피 카드 썸네일
#                                        / 빈 상태·404·면책 옆 한 컷 / 배지·칩·활성탭 포인트
#  ■ 데이터 존(만화 요소 전면 금지)       = 표·가격·시세·원가율·본문 / 네비·검색 / 카드 골격
#  ⛔ 기본 배경(--bg)은 현행 유지. 크림·모눈은 **히어로 안에서만**.
#  ⛔ 굵은 검정 테두리 + 오프셋 그림자 금지(전 구역).
#  값 출처: _shorts/업로드/채널브랜딩/유튜브_배너_2048x1152.png · 유튜브_프로필_1080.png 실측.
#  ⚠️ 임의로 새 색을 만들지 말 것 — 위 원본에서 뽑은 값만 쓴다.
CSS_VARS = """:root{
--ink:#191f28;--muted:#6b7280;--faint:#9aa2ad;--line:#eceef1;--bg:#f7f8fa;--card:#fff;
--accent:#DA5372;--accent2:#F0A6BE;--blue:#1a56b0;
/* 브랜드 존 전용 — 히어로·로고·빈상태 밖에서 쓰지 말 것 */
--bz-cream:#F8E2D5;--bz-grid:#E6B0B9;--bz-pink:#F0A6BE;--bz-cheek:#F7C6D4;
--bz-ribbon:#F5638F;--bz-yellow:#F5DD78;--bz-cheekY:#F0B080;
--shadow-soft:0 1px 2px rgba(25,31,40,.04),0 4px 12px -4px rgba(25,31,40,.08);
--header:rgba(255,255,255,.97);
--good:#16a34a;--goodbg:#e7f6ec;--bad:#dc2626;--badbg:#fdeaea;--up:#e5484d;--dn:#2f6fed;
--green:var(--good);--greenbg:var(--goodbg);--red:var(--bad);--redbg:var(--badbg);
--warnbg:#fffbeb;--warnline:#fde68a;--warntext:#78530b;
--infobg:#eef7ff;--infoline:#bfdcff;--infotext:#1a56b0;
--softbg:#FDEFF3;--softline:#F6CBD8;--hover:#FDF4F7;--panel:#fafbfc;
--track:#eceef1;--seg:#eceef2;--accentsoft:#FDEFF3;--herofrom:#F8E2D5;--heroto:#F8E2D5;
--grad:linear-gradient(135deg,#DA5372,#F0A6BE)}
:root[data-theme=dark]{
--ink:#eef1f5;--muted:#9aa1ac;--line:#262b32;--bg:#0f1216;--card:#1a1e24;--accent:#FF8FAE;--blue:#7ab0ff;
/* 브랜드 존 다크 — 크림 모눈의 «먹지 톤» 판. 본문은 건드리지 않는다 */
--bz-cream:#1A2340;--bz-grid:#3A4A7A;
--shadow-soft:0 1px 2px rgba(0,0,0,.3),0 4px 14px -4px rgba(0,0,0,.5);
--header:rgba(15,18,22,.92);
--good:#4ade80;--goodbg:#13291d;--bad:#f87171;--badbg:#33191a;--up:#f87171;--dn:#7ab0ff;
--warnbg:#2a2410;--warnline:#4d431a;--warntext:#e7c65a;
--infobg:#122232;--infoline:#26456b;--infotext:#7ab0ff;
--softbg:#2A1720;--softline:#4A2733;--hover:#241A1E;--panel:#161a20;
--faint:#7d8593;--accent2:#F0A6BE;
--track:#262b32;--seg:#0f1216;--accentsoft:#2A1720;--herofrom:#1A2340;--heroto:#1A2340;
--grad:linear-gradient(135deg,#FF8FAE,#F0A6BE)}
/* 헤더 아이콘 버튼 — 이모지(🔗🌙) 대신 인라인 SVG (2026-07-24 지시서 §3-1).
   이모지는 OS마다 모양이 달라 브랜드 톤이 안 잡히고, 크기·정렬도 제각각이라 낡아 보였다. */
.tbtn,.sbtn{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;
width:34px;height:34px;border:1px solid var(--line);background:var(--card);color:var(--muted);
border-radius:10px;padding:0;cursor:pointer;font-family:inherit;line-height:1}
.tbtn:hover,.sbtn:hover{color:var(--accent);border-color:var(--accent)}
.tbtn svg,.sbtn svg{width:17px;height:17px;display:block}
.tbtn{margin-left:6px} .sbtn{margin-left:auto}
/* 테마 아이콘 전환은 CSS로 — JS가 textContent를 건드리면 SVG가 날아간다 */
.ico-sun{display:none}
:root[data-theme=dark] .ico-moon{display:none}
:root[data-theme=dark] .ico-sun{display:block}
.sharebtm{display:block;width:100%;margin:20px 0 2px;padding:14px;border:1px solid var(--line);border-radius:13px;
background:var(--card);color:var(--ink);font-size:14px;font-weight:800;cursor:pointer;font-family:inherit;text-align:center}
.xtoast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:80;background:#1a1d21;color:#fff;
font-size:13px;font-weight:700;padding:11px 18px;border-radius:22px;box-shadow:0 8px 24px -8px rgba(0,0,0,.5);white-space:nowrap}
@media(max-width:430px){.logo small{display:none}}
.logo{display:inline-flex;align-items:center;gap:8px}
/* 🎨 로고 = 핑크 올마(주인공). 옛 주황 사각 배지는 이 규칙으로 덮인다.
   ⚠️ `.lbadge` 를 쓰는 생성기가 여러 곳이라 요소를 지우지 않고 **캐릭터로 칠한다**. */
.lbadge{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;
border-radius:0;background:none;color:transparent;font-size:0;flex-shrink:0;
background-image:url("data:image/svg+xml;utf8,\
<svg xmlns='http://www.w3.org/2000/svg' viewBox='28 14 144 180'>\
<circle cx='100' cy='108' r='66' fill='%23F0A6BE' stroke='%23111' stroke-width='7'/>\
<ellipse cx='68' cy='130' rx='13' ry='8' fill='%23F7C6D4'/>\
<ellipse cx='132' cy='130' rx='13' ry='8' fill='%23F7C6D4'/>\
<ellipse cx='82' cy='106' rx='14' ry='17' fill='%23fff' stroke='%23111' stroke-width='5'/>\
<ellipse cx='118' cy='106' rx='14' ry='17' fill='%23fff' stroke='%23111' stroke-width='5'/>\
<circle cx='83' cy='108' r='7' fill='%233D2B12'/><circle cx='119' cy='108' r='7' fill='%233D2B12'/>\
<g stroke='%23111' stroke-width='4' stroke-linecap='round'>\
<path d='M66 92 l-8 -7'/><path d='M70 86 l-5 -9'/><path d='M76 82 l-2 -10'/>\
<path d='M134 92 l8 -7'/><path d='M130 86 l5 -9'/><path d='M124 82 l2 -10'/></g>\
<path d='M86 138 q14 13 28 0' stroke='%23111' stroke-width='6' fill='none' stroke-linecap='round'/>\
<g transform='translate(52,50)'>\
<path d='M0 8 q-14 -14 -2 -20 q12 -5 16 12 z' fill='%23F5638F' stroke='%23111' stroke-width='5'/>\
<path d='M18 0 q16 -8 20 4 q3 13 -14 12 z' fill='%23F5638F' stroke='%23111' stroke-width='5'/>\
<circle cx='15' cy='9' r='7' fill='%23F5638F' stroke='%23111' stroke-width='5'/></g></svg>");
background-size:contain;background-repeat:no-repeat;background-position:center}
/* 🎨 브랜드 글꼴 — 이 클래스가 붙은 곳에만. ⛔ 표·본문·네비에 쓰지 말 것 */
.bz-type{font-family:"Black Han Sans",sans-serif;font-weight:400;letter-spacing:-.02em}
/* 🎨 브랜드 존 배경 — 크림 + 모눈. 히어로·빈상태에만 쓴다(`.bz-bg`) */
.bz-bg{background-color:var(--bz-cream);background-image:
repeating-linear-gradient(0deg,transparent 0 55px,color-mix(in srgb,var(--bz-grid) 28%,transparent) 55px 56px),
repeating-linear-gradient(90deg,transparent 0 55px,color-mix(in srgb,var(--bz-grid) 28%,transparent) 55px 56px)}
/* 숫자 컬럼 정렬 — 지시서 §2. 자릿수가 흔들리면 표가 지저분해 보인다 */
.tnum,td.r,.pr,.hv,.v{font-variant-numeric:tabular-nums}
/* 계정 버튼 (2026-07-27 회원 도입) — .tbtn/.sbtn 과 같은 헤더 버튼이라 여기 둔다.
   🔴 order:7 로 **오른쪽 묶음의 맨 끝**에 붙인다. 앞(order:4)에 넣으면
      `.sbtn{margin-left:auto}` 가 묶음의 첫 원소에 걸려 있어서 계정 버튼만 왼쪽에 남는다.
      맨 끝에 두면 auto 규칙을 손대지 않아도 되고, 계정 버튼이 없는 페이지도 그대로 동작한다. */
.abtn{order:7;flex:0 0 auto;display:inline-flex;align-items:center;height:34px;margin-left:6px;
padding:0 11px;border:1px solid var(--line);background:var(--card);color:var(--muted);
border-radius:10px;font-size:13px;font-weight:800;text-decoration:none;white-space:nowrap;
max-width:112px;overflow:hidden;text-overflow:ellipsis;font-family:inherit;cursor:pointer}
.abtn:hover{color:var(--accent);border-color:var(--accent)}
.abtn.on{color:var(--ink);border-color:var(--line)}
.themed,body,.card,header.top,.tile,.mrow{transition:background-color .25s ease,color .25s ease,border-color .25s ease}"""

# <head>에서 CSS보다 먼저 실행 — 저장된 테마를 즉시 적용해 흰 화면 깜빡임(FOUC) 방지.
HEAD_SCRIPT = ("<script>try{var t=localStorage.getItem('em-theme');"
               "if(t)document.documentElement.dataset.theme=t;}catch(e){}</script>")

# ── 글꼴·타이포 — **단일 출처** (2026-07-24 지시서 §2) ────────────────────
#  🔴 생성기 4곳이 body{font-family:...}를 각자 박고 있었다. 폭·색과 같은 이유로 여기로 모은다.
#     생성기는 body 선언에 이 상수를 넣고, font-family를 직접 쓰지 말 것.
#  Pretendard CDN 링크는 HEAD_TAGS에 있다(둘은 세트 — 하나만 바꾸면 폴백으로 떨어진다).
FONT_STACK = ("'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,"
              "'Apple SD Gothic Neo','Malgun Gothic',sans-serif")
BODY_CSS = ("body{font-family:" + FONT_STACK + ";background:var(--bg);color:var(--ink);"
            "line-height:1.6;font-size:clamp(15px,14px+0.3vw,17px);"
            "-webkit-font-smoothing:antialiased;letter-spacing:-.01em}")
# h1 등 공통 타이포 (지시서 §2: 모바일 22/800 · PC 26/900, 보조 라벨 하한 12.5px)
TYPO_CSS = """h1{font-size:22px;font-weight:800;letter-spacing:-.02em;line-height:1.3}
@media(min-width:840px){h1{font-size:26px;font-weight:900}}
small,.sub,.cap,.note,.srcn,.disc{font-size:12.5px}"""

# ── 본문 폭(레이아웃) — **단일 출처** (2026-07-24) ──────────────────────
# 🔴 왜 모듈로: .wrap / .top .in 의 max-width가 생성기 4곳에 각각 박혀 있어서 전부 달랐다.
#    모바일은 520으로 같았는데 PC가 960(메뉴·시세) / 1060(레시피) / 700(마라탕)으로 제각각 →
#    페이지를 옮길 때마다 가로폭이 튀고, GNAV(여기 GNAV_CSS는 520→960)만 본문보다 넓게 삐져나왔다.
#    색(CSS_VARS)·네비(GNAV)와 같은 이유로 여기 하나로 모은다. 폭을 바꾸려면 **여기만** 고칠 것.
#
# 규칙: 생성기는 .wrap / .top .in 의 max-width를 직접 쓰지 말고 이 상수를 <style>에 넣는다.
#       생성기별 추가 규칙(레시피 2단 .dpc, 시세 바텀시트 .psheet 등)은 각자의 미디어쿼리에 두되
#       **폭은 건드리지 않는다**. 브레이크포인트는 840px로 통일(GNAV_CSS와 같은 값).
WRAP_CSS = """.wrap{max-width:520px;margin:0 auto;padding:0 14px 60px}
.top .in{max-width:520px;margin:0 auto;padding:12px 14px;display:flex;align-items:center;gap:10px}
@media(min-width:840px){.wrap{max-width:960px;padding:0 24px 60px}
 .top .in{max-width:960px;height:60px;padding:0 24px;gap:22px}}"""

# ── PC 2단 레이아웃 — **단일 출처** (2026-07-24 지시서 §3-2) ──────────────
#  본문이 PC에서 오른쪽 절반을 비워두고 있었다. 840px부터 본문 + 320px 사이드 2단으로 채운다.
#  쓰는 쪽은 <div class="p2"><div>본문</div><aside class="side">…</aside></div> 형태.
#  ⚠️ 폭 자체(520/960)는 WRAP_CSS가 정한다. 여기서 max-width를 다시 쓰지 말 것.
P2_CSS = """.p2{display:block}
.side{display:flex;flex-direction:column;gap:14px;margin-top:18px}
@media(min-width:840px){
 .p2{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:22px;align-items:start}
 .side{position:sticky;top:16px;margin-top:0}
}"""

# 전역 네비게이션 (2026-07-20, 점검지시서 B-4) — 헤더 아래 한 줄.
#  ★ 생성기(gen_preview_html·gen_dishes·gen_prices_page)마다 헤더 HTML이 따로라
#    한 곳에만 넣으면 요리사전·요리상세·시세 페이지가 통째로 빠진다(실제로 빠져 있었다).
#  2026-07-24: "마라탕" 5번째 항목 추가 — 올마나마 유튜브가 마라탕 콘텐츠를 올리는 중이라
#  거기서 들어오는 트래픽을 바로 malatang-price.html로 보내기 위해 상위 메뉴에 얹었다(사용자 지시).
#  다른 4개는 전체 카테고리(레시피 전체·브랜드 전체·시세 전체·순위 전체)인데 이것만 특정 요리라
#  나중에 캠페인이 끝나면 빼거나 위치를 재검토할 것.
#  2026-07-24 지시서 §3-1:
#   · "마라탕 재료원가" → "마라탕 단가표"로 축약(모바일 pill 스크롤이 너무 길어짐)
#   · **현재 위치 표시** — 생성기가 자기 페이지 종류를 gnav(here=...)로 넘기면 그 항목에 .on
#   · PC(≥840)에서는 flex:1을 빼고 좌측 정렬 (전폭으로 펴면 헤더가 비어 보인다)
#  2026-07-24 §B1: "정보" 코너 추가.
#  2026-07-24(후속, 대표 지시): **"마라탕 단가표"를 네비에서 뺐다.**
#   → 이제 정보 코너('원가' 갈래) 카드로만 들어간다. 네비는 전체 카테고리 5개로 정리.
#   🔴 URL `/malatang-price` 는 **그대로 유지**한다 — 이미 색인·공유된 주소라 바꾸면 안 된다.
#      페이지 자체는 살아 있고 진입 경로만 정보 코너로 옮긴 것.
#  2026-07-28 (대표 결정 · `메뉴판-SEO-뼈대-2026-07-28.md`):
#   **"순위" 자리를 "식자재마트"로 바꿨다.** 네이버 검색광고 키워드도구 실측이 근거다:
#     원가율순위 10 · 치킨원가율순위 10 · 프랜차이즈원가 10   ← 우리 콘텐츠를 설명하는 말
#     식자재마트 54,090 · 부산식자재마트 1,190 · 대구 1,060   ← 사람들이 실제로 치는 말
#   같은 자리에 놓으면 100배 차이다.
#   🔴 `ranking.html` 은 **지우지 않는다** — 순위 데이터는 내부 순환(브랜드·메뉴로 보내기)에
#      쓸모가 있다. 진입 경로만 네비에서 뺀 것이고 주소는 살아 있다(색인된 주소를 깨지 않는다).
#  2026-07-31 (대표 지시): **「브랜드」→「메뉴판」으로 이름을 바꾸고 맨 앞으로.**
#   메뉴판이 사이트의 메인이 됐다. «브랜드» 는 우리 내부 분류 이름이지 사람들이 찾는 말이 아니다.
#   검색 실측상 사람들은 «원가» 나 «레시피» 가 아니라 **브랜드+메뉴명**으로 찾는다
#   (교촌허니콤보 19,720 · 버거킹와퍼 18,740 vs 마라탕원가 460).
#   ⚠️ 이 목록을 고치면 **생성기를 전부 다시 돌려야 한다**(파일 상단 «전체 재생성» 참고) —
#      일부만 돌리면 페이지마다 네비가 달라 보인다(2026-07-28에 415장이 그렇게 남았다).
#  2026-08-01: 「시세」→「재료 가격」. 재료 페이지의 title·h1 은 이미 «가격» 으로 바꿨는데
#   상단 메뉴만 옛 이름으로 남아 있었다. 검색 실측도 «가격» 이 «시세» 보다 크다.
_NAV_ITEMS = [("categories", "메뉴판"), ("dishes", "레시피"), ("prices", "재료 가격"),
              ("areas", "식자재마트"), ("info", "정보")]

def gnav(here=""):
    """here = 현재 페이지 종류 키. 없으면 아무것도 활성화하지 않는다."""
    # f-string 안에 백슬래시를 못 쓰는 파이썬 버전이 있어 클래스는 밖에서 만든다
    parts = []
    for h, t in _NAV_ITEMS:
        cls = ' class="on"' if h == here else ''
        parts.append('<a href="%s"%s>%s</a>' % (h, cls, t))
    return '<nav class="gnav">%s</nav>' % "".join(parts)

# 하위호환 — here를 안 넘기는 호출부가 남아 있어도 동작하게 (활성 표시만 없음)
GNAV = gnav()

#  네비는 이제 .in **안**에 있다(2026-07-24). 모바일에선 둘째 줄로 내려가고, PC에선 로고 옆에 붙어
#  헤더가 한 줄(60px)이 된다. 그래서 gnav 자체에는 max-width를 두지 않는다 — .in이 이미 잡는다.
#  order 값 주의: 모바일은 gnav가 마지막(둘째 줄), PC는 로고 바로 다음이어야 한다.
#  .sbtn{margin-left:auto}가 버튼들을 오른쪽 끝으로 미는데, gnav가 그 뒤에 오면 같이 밀려간다.
GNAV_CSS = """.top .in{flex-wrap:wrap}
.sbtn{order:5} .tbtn{order:6}
.gnav{display:flex;gap:4px;order:9;width:100%;padding:2px 0 6px;overflow-x:auto;
-webkit-overflow-scrolling:touch;scrollbar-width:none}
.gnav::-webkit-scrollbar{display:none}
.gnav a{flex:1;text-align:center;white-space:nowrap;padding:8px 14px;font-size:13.5px;font-weight:700;
color:var(--muted);text-decoration:none;border-radius:999px}
.gnav a:hover{background:var(--hover);color:var(--accent)}
/* 현재 위치 — 배경 ink / 글자 흰색 pill (지시서 §3-1) */
.gnav a.on{background:var(--ink);color:var(--card)}
.gnav a.on:hover{background:var(--ink);color:var(--card)}
@media(min-width:840px){
 .top .in{flex-wrap:nowrap}
 /* 로고 바로 오른쪽에 좌측정렬. 공유·다크 버튼은 .sbtn{margin-left:auto}가 오른쪽 끝으로 민다 */
 .gnav{order:1;width:auto;flex:0 0 auto;padding:0;overflow:visible}
 .gnav a{flex:0 0 auto;padding:8px 13px}
}"""

# 헤더 오른쪽 토글 버튼(HTML). 2026-07-24: 이모지 → 인라인 SVG(달 아이콘).
#  달·해 SVG를 둘 다 담고 CSS(.ico-moon/.ico-sun)가 테마에 따라 하나만 보여준다.
BTN = ('<button class="tbtn" onclick="__tt()" aria-label="다크/라이트 전환">'
       '<svg class="ico-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
       'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
       '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
       '<svg class="ico-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
       'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
       '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
       'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>')

# 헤더 공유 버튼 + 본문 하단 공유 버튼 (사용자 지시 2026-07-18: 헤더·하단 둘 다)
SHARE_BTN = ('<button class="sbtn" onclick="__share()" aria-label="이 페이지 공유">'
             '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
             '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
             '</svg></button>')
SHARE_BTM = '<button class="sharebtm" onclick="__share()">이 페이지 공유하기</button>'

# 헤더 계정 버튼 (2026-07-27 회원 도입) — BTN·SHARE_BTN 과 같은 패턴.
#  🔴 생성기는 **항상 비로그인 상태로 굽는다.** 로그인 여부는 AUTH_JS 가 /api/me 로 확인해
#     이 버튼의 글자·링크만 바꾼다.
#     정적 HTML 을 개인화하면 943페이지가 캐시 불가가 되고, 그 순간 모든 요청이 워커로 쏟아져
#     2026-07-25 의 error 1015(레이트리밋)가 그대로 재발한다.
AUTH_BTN = '<a class="abtn" id="__auth" href="login">로그인</a>'

# 공공데이터 출처 표시 배너 (2026-07-19) — 소개·문의 링크 바로 위, 전 페이지.
#  ★ 링크는 걸지 않는다(사용자 지시). 외부로 새는 링크를 만들지 않기 위함.
#  ★ 기관 로고(CI) 이미지는 쓰지 않고 기관명 텍스트 뱃지로 표기한다.
#     로고는 기관마다 사용 규정이 따로 있어 임의로 가져다 붙이면 그 자체가 위반이 될 수 있다.
#     공공누리 제1유형은 "출처표시"가 요건이라 기관명 표기로 요건을 충족한다.
# 2026-07-25: 축평원·참가격은 실제 미사용이 되어 뺐다(육류=도매시장 조사, 채소=도매시장 조사).
#   KAMIS·가맹사업정보는 계속 쓰므로 남긴다. 안 쓰는 기관을 출처로 걸면 과대표시가 된다.
SOURCES = ('<div class="srcbar"><div class="srct">데이터 출처</div><div class="srcs">'
           '<span>농산물유통정보 KAMIS</span><span>한국농수산식품유통공사</span>'
           '<span>공정거래위원회 가맹사업정보</span><span>공공데이터포털</span></div>'
           '<div class="srcn">본 저작물은 위 기관에서 제공한 공공데이터를 이용하였으며, '
           '<b>공공누리 제1유형(출처표시)</b> 조건에 따라 이용합니다. 그 밖의 시세는 도매시장·'
           '온라인 식자재몰의 업소용 판매가를 조사해 반영합니다. 제3자 권리가 포함될 수 있습니다.</div></div>')
SOURCES_CSS = """.srcbar{margin:20px 0 4px;padding:12px 13px;background:var(--panel);
border:1px solid var(--line);border-radius:12px}
.srcbar .srct{font-size:13px;font-weight:800;color:var(--muted);margin-bottom:7px}
.srcbar .srcs{display:flex;flex-wrap:wrap;gap:5px}
.srcbar .srcs span{font-size:12.5px;font-weight:700;color:var(--ink);background:var(--card);
border:1px solid var(--line);border-radius:7px;padding:4px 8px}
.srcbar .srcn{margin-top:8px;font-size:12px;color:var(--muted);line-height:1.6}"""

# 푸터 상시 링크 (사용자 지시 2026-07-19: 개인정보처리방침·소개·문의 전 페이지 노출 — 애드센스 필수)
#  + 이용약관(2026-07-19) — 카카오 애드핏 매체 심사가 푸터 링크 노출을 봄
FOOTER_LINKS = ('<div class="flinks">'
                '<a href="about.html">소개</a><span>·</span>'
                '<a href="about.html#contact">문의</a><span>·</span>'
                '<a href="terms.html">이용약관</a><span>·</span>'
                '<a href="privacy.html">개인정보처리방침</a></div>'
                # 운영자 정보 상시 노출 (2026-07-20, 애드핏 심사보류 대응):
                #  애드핏 계정 명의(사업자 베이직씨엔엠)와 동일하게. 개인정보처리방침 §5와 일치.
                '<div class="fowner">운영자: 베이직씨엔엠 · '
                '<a href="mailto:dndmotor1@gmail.com">dndmotor1@gmail.com</a></div>')
FOOTER_CSS = """.flinks{display:flex;justify-content:center;gap:10px;margin:18px 0 4px;font-size:12.5px}
.flinks a{color:var(--muted);text-decoration:none;font-weight:700}
.flinks a:hover{color:var(--accent)} .flinks span{color:var(--line)}
.fowner{text-align:center;margin:2px 0 6px;font-size:13px;color:var(--muted)}
.fowner a{color:var(--muted);text-decoration:none}"""

# 카카오 애드핏 — 본문 하단 배너, 반응형 2단위 (2026-07-19)
#   모바일 320x100 = DAN-gKspnAypqcdGzXYm · PC 728x90 = DAN-FYWd2CPUtaM18PaF
#  ★ 세 생성기의 FOOT 맨 앞에 들어간다 = 콘텐츠 끝 · 공유버튼 위. 애드센스와 병행 게재.
#  ★ CSS로 숨기지 않고 **ba.min.js가 뜨기 전에 안 맞는 ins를 DOM에서 제거**한다.
#     display:none으로만 가리면 안 보이는 배너에 노출(임프레션)이 잡혀 무효 트래픽이 될 수 있다.
#  ★ 스크립트(ba.min.js)는 페이지당 1번, async라 렌더를 막지 않는다.
#  ★ "광고" 라벨 필수(2026-07-19): 라벨 없이 카드 사이에 끼우면 우리 콘텐츠로 오인된다.
#     애드센스 정책이 광고를 콘텐츠와 혼동되게 배치하는 걸 금지하므로 심사 리스크이기도 하다.
#  ── 컨테이너 표시 정책의 이력 (되돌리기 전에 반드시 읽을 것) ──────────────
#  ① 최초: `.adfit{display:none}` + 광고가 실제로 뜨면 `.on`을 켜는 방식
#  ② 2026-07-20 심사 반려("광고를 설치한 이후 심사 진행이 가능합니다"):
#     **승인 전에는 카카오가 광고를 안 내려보낸다** → ins가 계속 display:none →
#     컨테이너도 계속 display:none → 검수 봇이 "광고 미설치"로 판정 → 반려.
#     닭-달걀이라 영원히 통과할 수 없어서 **항상 보이게** 바꿨다(빈 라벨은 감수).
#  ③ 2026-07-24 ①로 되돌렸다가 **같은 날 실패 확인 → ④로 재수정.**
#     `.adfit{display:none}`으로 바꾼 직후 라이브에서 **광고가 전혀 안 나왔다.**
#     ba.min.js·쿠키동기화는 로드되는데 **광고 요청이 아예 안 나감** — 숨긴 컨테이너는
#     레이아웃 박스가 없어 광고 스크립트가 그 자리를 건너뛴다. `.on`은 광고가 떠야
#     붙으니 영원히 안 붙는 구조였다. ②의 닭-달걀은 **승인 문제가 아니라 CSS 문제**였다.
#  ④ 2026-07-24 최종: **컨테이너는 항상 display:flex.** 미충전일 때만
#     테두리·배경·패딩·라벨을 죽여 시각적으로 비운다 → 빈 라벨 안 보이고 광고도 정상.
# 🔴 **같은 광고단위를 한 페이지에 두 번 넣으면 안 된다**(2026-07-25 실제로 넣었다가 발견).
#    애드핏은 동일 단위 중복 게재를 허용하지 않아 하나만 나오거나 둘 다 안 나온다.
#    → 자리마다 **별도 단위**를 발급받아 쓴다. 아래 표가 정본이다.
#
#      자리   모바일 320x100          PC 728x90
#      하단   DAN-gKspnAypqcdGzXYm    DAN-FYWd2CPUtaM18PaF
#      상단   DAN-LnZFmGJZTUctfBIA    DAN-4lLT1TPzjzsGBqNB
#      중간   DAN-p6NkaahVj9snUgHN    DAN-INj1DhKHjlVWnveb
AD_UNITS = {
    "bottom": ("DAN-gKspnAypqcdGzXYm", "DAN-FYWd2CPUtaM18PaF"),
    "top": ("DAN-LnZFmGJZTUctfBIA", "DAN-4lLT1TPzjzsGBqNB"),
    "mid": ("DAN-p6NkaahVj9snUgHN", "DAN-INj1DhKHjlVWnveb"),
}


def adfit(slot="bottom"):
    """자리별 애드핏 배너. 단위가 없는 자리는 **빈 문자열**을 준다(중복 게재 방지)."""
    m, p = AD_UNITS.get(slot, (None, None))
    if not m or not p:
        return ""
    return ADFIT_TPL.replace("__M__", m).replace("__P__", p)


ADFIT_TPL = ('<div class="adfit"><span class="adlbl">광고</span>'
         '<ins class="kakao_ad_area adf-m" style="display:none;"'
         ' data-ad-unit="__M__" data-ad-width="320" data-ad-height="100"></ins>'
         '<ins class="kakao_ad_area adf-p" style="display:none;"'
         ' data-ad-unit="__P__" data-ad-width="728" data-ad-height="90"></ins>'
         '<script>(function(){var b=document.currentScript.parentNode,'
         'pc=window.innerWidth>=768,x=b.querySelector(pc?".adf-m":".adf-p");if(x)x.remove();'
         # 박스 폭은 CSS 미디어쿼리가 아니라 **이 판정 결과**를 따라야 한다(2026-07-20).
         #  둘을 따로 두면 로드 후 창 크기가 바뀔 때 "박스=모바일폭인데 배너=PC"로 어긋난다.
         'b.classList.toggle("adpc",pc);'
         'var ins=b.querySelector(".kakao_ad_area");if(!ins)return;'
         'new MutationObserver(function(){b.classList.toggle("on",'
         'getComputedStyle(ins).display!=="none");})'
         '.observe(ins,{attributes:true,attributeFilter:["style"]});})();</script>'
         '<script type="text/javascript" src="//t1.kakaocdn.net/kas/static/ba.min.js" async></script>'
         '</div>')

# 기존 코드 호환 — ADFIT 은 **하단** 자리를 뜻한다
ADFIT = adfit("bottom")
ADFIT_TOP = adfit("top")
ADFIT_MID = adfit("mid")
# 박스는 광고에 딱 붙게(2026-07-20 사용자 지시): 배너 자체 크기(320x100/728x90)는 카카오가 정하므로
#  우리가 줄일 수 있는 건 여백·라벨뿐이다. 패딩/갭/마진을 최소로 하고 라벨은 배너 폭에 맞춰 왼쪽 정렬.
# ⚠️ width:fit-content 금지(2026-07-20 실패): ins가 로드 전 display:none이라 폭이 0으로 잡혀
#    박스가 14px로 찌그러졌다. 배너 규격(320/728)에 맞춘 **고정폭**으로 간다.
# 좁은 컬럼(요리상세 우측 고정열 등) 전용 — **항상 모바일 320x100 유닛**만 쓴다.
#  ADFIT은 창 너비로 PC/모바일을 고르는데, 사이드바는 290~340px라 PC 728px가 화면을 뚫는다
#  (2026-07-20 실측: body scrollWidth 1584 > 뷰포트 1280).
#  🔴 2026-07-24: 여기에도 **.on 감시 스크립트가 반드시 있어야 한다.**
#     ADFIT_CSS가 `.adfit{display:none}` + `.adfit.on{display:flex}`로 바뀌었는데
#     이 사이드 배너에는 옵저버가 없어서, 넣지 않으면 영영 안 뜬다(실제로 빠뜨릴 뻔했다).
ADFIT_SIDE = ('<div class="adfit adside">'
              '<span class="adlbl">광고</span>'
              '<ins class="kakao_ad_area" style="display:none;"'
              ' data-ad-unit="DAN-gKspnAypqcdGzXYm" data-ad-width="320" data-ad-height="100"></ins>'
              '<script>(function(){var b=document.currentScript.parentNode,'
              'ins=b.querySelector(".kakao_ad_area");if(!ins)return;'
              'new MutationObserver(function(){b.classList.toggle("on",'
              'getComputedStyle(ins).display!=="none");})'
              '.observe(ins,{attributes:true,attributeFilter:["style"]});})();</script>'
              '<script type="text/javascript" src="//t1.kakaocdn.net/kas/static/ba.min.js" async></script>'
              '</div>')

# 🔴🔴 컨테이너에 display:none 을 절대 쓰지 말 것 (2026-07-24 실제 사고)
#    §4-4대로 `.adfit{display:none}` + `.adfit.on{display:flex}` 로 바꿨더니
#    **광고가 아예 안 나왔다.** ba.min.js와 쿠키동기화(ct2.html)는 로드되는데
#    광고 요청 자체가 안 나갔다 — 숨겨진 컨테이너는 레이아웃 박스가 없어서
#    광고 스크립트가 그 자리를 건너뛴다. `.on`은 광고가 떠야 붙으므로 영원히 안 붙는다.
#    (승인 여부와 무관한 문제였다. "승인됐으니 괜찮다"는 판단이 틀렸다.)
#
#    → 지금 방식: **컨테이너는 항상 display:flex**(광고 스크립트가 자리를 인식하게).
#      대신 광고가 안 채워졌을 때(`:not(.on)`) **테두리·배경·패딩·라벨을 전부 죽여** 시각적으로
#      아무것도 없게 만든다. ins는 원래 display:none으로 시작하므로 높이도 0에 수렴한다.
#      = 빈 "광고" 라벨/박스는 안 보이고(§4-4 의도 충족), 광고 요청은 정상으로 나간다.
ADFIT_CSS = (""".adfit{display:flex;flex-direction:column;gap:2px;margin:16px auto 4px;
padding:5px 6px 6px;background:var(--panel);border:1px solid var(--line);border-radius:9px;
width:332px;max-width:100%;box-sizing:border-box}
/* 광고 미충전 상태 — 자리는 살려두되 눈에는 안 보이게 */
.adfit:not(.on){padding:0;border:0;background:none;margin:0;gap:0}
.adfit:not(.on) .adlbl{display:none}
.adfit.adpc{width:740px}
.adfit.adside{width:100%;max-width:332px;margin:0 auto}   /* 좁은 컬럼 전용 */
.adlbl{font-size:9.5px;font-weight:700;color:var(--muted);letter-spacing:.04em;line-height:1}""")

# 쿠팡 파트너스 검색 위젯 (2026-07-19) — 재료 '복사' 버튼과 한 세트로 동작한다.
#   재료명 복사 → 바로 아래 검색창에 붙여넣기 → 쿠팡에서 검색. 안내문 없으면 그냥 배너로 보고 지나친다.
CPSEARCH = ('<div class="cpsearch"><div class="cpst">재료명을 <b>복사</b>해서 아래 검색창에 붙여넣어 보세요</div>'
            '<iframe src="https://coupa.ng/coatLJ" width="100%" height="75" frameborder="0"'
            ' scrolling="no" referrerpolicy="unsafe-url" browsingtopics></iframe>'
            '<div class="cpsn">쿠팡 파트너스 활동의 일환으로 수수료를 제공받습니다</div></div>')
CPSEARCH_CSS = """.cpsearch{margin:14px 0 4px;padding:12px 12px 8px;background:var(--panel);
border:1px solid var(--line);border-radius:13px}
.cpsearch .cpst{font-size:12.5px;font-weight:700;margin-bottom:8px}
.cpsearch .cpsn{font-size:12px;color:var(--muted);margin-top:4px}"""

# 🔴 olmanama.com의 전역 <head> 태그는 전부 여기 하나에 모은다. 세 생성기가 이 상수를 import해 주입한다.
#    (gen_dishes / gen_preview_html / gen_prices_page)
#  들어있는 것: 파비콘(gen_og.py 산출물) · 네이버 서치어드바이저 소유확인(2026-07-19)
#              · 구글 애드센스(2026-07-19, ca-pub-9423286569078244)
#              · 구글 애널리틱스 GA4(2026-07-21, G-SZ4HE98GLC — 쇼츠→사이트 유입 측정용)
#
#  ⚠️ olmanama.com은 루트에 index.html이 없다. 이 생성기가 만든 _dist를 site-renderer 워커가 서빙한다.
#     2026-07-21에 옆 프로젝트(얼마남아-web)의 index.html에 GA를 넣고 배포한 사고가 있었다.
#     그래서 상수 이름도 FAVICON → HEAD_TAGS로 바꿨다(옛 이름은 검색으로 안 걸렸음). 그 폴더는 이후 삭제됨.
# 🎨 캐릭터 SVG — 2026-08-02 «브랜드 존» 전용 (홈 히어로 · 빈 상태 · 404 · 면책 옆)
#  원본: _shorts/업로드/채널브랜딩/유튜브_프로필_1080.png 실측(납작 만화풍, 굵은 검정 외곽선).
#  ⛔ 데이터 존(표·가격·시세·본문·네비)에 넣지 말 것.
#  쓰는 법: 페이지 어딘가에 CHAR_DEFS 를 한 번 넣고, 필요한 자리에
#          <svg viewBox="28 14 144 180"><use href="#ch-olma"/></svg>
CHAR_DEFS = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
    # 올마(핑크 손님) — 주인공. 리본 + 속눈썹
    '<g id="ch-olma">'
    '<ellipse cx="100" cy="180" rx="50" ry="8" fill="#000" opacity=".12"/>'
    '<circle cx="100" cy="108" r="66" fill="var(--bz-pink)" stroke="#111" stroke-width="7"/>'
    '<ellipse cx="68" cy="130" rx="13" ry="8" fill="var(--bz-cheek)"/>'
    '<ellipse cx="132" cy="130" rx="13" ry="8" fill="var(--bz-cheek)"/>'
    '<ellipse cx="82" cy="106" rx="14" ry="17" fill="#fff" stroke="#111" stroke-width="5"/>'
    '<ellipse cx="118" cy="106" rx="14" ry="17" fill="#fff" stroke="#111" stroke-width="5"/>'
    '<circle cx="83" cy="108" r="7" fill="#3D2B12"/><circle cx="119" cy="108" r="7" fill="#3D2B12"/>'
    '<g stroke="#111" stroke-width="4" stroke-linecap="round">'
    '<path d="M66 92 l-8 -7"/><path d="M70 86 l-5 -9"/><path d="M76 82 l-2 -10"/>'
    '<path d="M134 92 l8 -7"/><path d="M130 86 l5 -9"/><path d="M124 82 l2 -10"/></g>'
    '<path d="M86 138 q14 13 28 0" stroke="#111" stroke-width="6" fill="none" stroke-linecap="round"/>'
    '<g transform="translate(52,50)">'
    '<path d="M0 8 q-14 -14 -2 -20 q12 -5 16 12 z" fill="var(--bz-ribbon)" stroke="#111" stroke-width="5" stroke-linejoin="round"/>'
    '<path d="M18 0 q16 -8 20 4 q3 13 -14 12 z" fill="var(--bz-ribbon)" stroke="#111" stroke-width="5" stroke-linejoin="round"/>'
    '<circle cx="15" cy="9" r="7" fill="var(--bz-ribbon)" stroke="#111" stroke-width="5"/></g></g>'
    # 사장님(노랑) — 보조. 구름형 주방모자
    '<g id="ch-boss">'
    '<ellipse cx="100" cy="180" rx="50" ry="8" fill="#000" opacity=".12"/>'
    '<circle cx="100" cy="108" r="66" fill="var(--bz-yellow)" stroke="#111" stroke-width="7"/>'
    '<ellipse cx="70" cy="128" rx="13" ry="8" fill="var(--bz-cheekY)" opacity=".75"/>'
    '<ellipse cx="130" cy="128" rx="13" ry="8" fill="var(--bz-cheekY)" opacity=".75"/>'
    '<ellipse cx="82" cy="104" rx="14" ry="17" fill="#fff" stroke="#111" stroke-width="5"/>'
    '<ellipse cx="118" cy="104" rx="14" ry="17" fill="#fff" stroke="#111" stroke-width="5"/>'
    '<circle cx="83" cy="106" r="7" fill="#3D2B12"/><circle cx="119" cy="106" r="7" fill="#3D2B12"/>'
    '<path d="M66 79 Q82 70 96 78" stroke="#111" stroke-width="8" fill="none" stroke-linecap="round"/>'
    '<path d="M104 78 Q118 70 134 79" stroke="#111" stroke-width="8" fill="none" stroke-linecap="round"/>'
    '<path d="M86 136 q14 13 28 0" stroke="#111" stroke-width="6" fill="none" stroke-linecap="round"/>'
    '<path d="M60 58 q-14 -20 6 -28 q2 -20 22 -16 q12 -16 24 -4 q16 -10 26 6 q20 2 14 22 q14 10 2 20 z"'
    ' fill="#fff" stroke="#111" stroke-width="6" stroke-linejoin="round"/>'
    '<rect x="58" y="52" width="84" height="19" rx="9" fill="#fff" stroke="#111" stroke-width="6"/>'
    '<text x="100" y="67" text-anchor="middle" font-size="14" fill="#111"'
    ' font-family="\'Black Han Sans\',sans-serif">사장님</text></g>'
    '</defs></svg>')
CHAR = '<svg viewBox="28 14 144 180" aria-hidden="true"><use href="#ch-%s"/></svg>'

HEAD_TAGS = (
           # Pretendard (2026-07-24 지시서 §2) — 체감 개선 1순위.
           #  기존엔 맑은고딕 폴백이라 낡아 보이는 주범이었다. 동적 서브셋이라 필요한 글자만 받는다.
           #  preconnect를 먼저 둬야 CSS 요청이 DNS·TLS를 기다리지 않는다.
           '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>'
           '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9'
           '/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
           # 🎨 브랜드 글꼴 — **히어로 카피·로고 워드마크에만** 쓴다(`.bz-type`). 본문 금지.
           #  ⚠️ 잘난체 CDN(projectnoonnu/noonfonts_2107)은 404 다 — 쓰지 마라.
           #     2026-08-02 시안에서 「잘난체」로 보이던 건 폴백(일반 고딕)이었다(폭 실측으로 확인).
           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
           'family=Black+Han+Sans&display=swap">'
           '<script async src="https://www.googletagmanager.com/gtag/js?id=G-SZ4HE98GLC"></script>'
           '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
           "gtag('js',new Date());gtag('config','G-SZ4HE98GLC');</script>"
           '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9423286569078244" crossorigin="anonymous"></script>'
           '<meta name="google-adsense-account" content="ca-pub-9423286569078244">'
           '<meta name="naver-site-verification" content="e69810b5c120510163f997719155bbe86cec5d2e">'
           # 네이버 애널리틱스(2026-07-24) — 사이트 등록만 해두고 스크립트를 안 붙여
           #  "연결 안 됨"으로 떠 있었다. GA4와 별개로 네이버 유입을 봐야 해서 둘 다 둔다.
           #  wcs.pstatic.net 은 프로토콜 상대경로(//)로 주는 게 네이버 표준 스니펫이다.
           '<script src="//wcs.pstatic.net/wcslog.js"></script>'
           '<script>if(!window.wcs_add)var wcs_add={};wcs_add["wa"]="17cbc88968b2c80";'
           'if(window.wcs)wcs_do();</script>'
           '<link rel="icon" href="/favicon.ico" sizes="any">'
           '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">'
           '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">'
           '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')

# </body> 앞에 넣는 토글 스크립트(클릭 → data-theme 전환 + localStorage 저장 + 아이콘 갱신).
#  🔴 2026-07-24: 예전엔 __ti()가 b.textContent에 이모지(🌙/☀️)를 써넣었다. 버튼을 인라인 SVG로
#     바꾸면서 그 코드가 **SVG를 통째로 지워버리는** 문제가 생겨, 아이콘 전환을 CSS로 옮겼다.
#     달·해 SVG를 둘 다 넣어두고 data-theme에 따라 CSS가 하나만 보여준다(JS는 상태만 바꾼다).
TOGGLE_JS = ("<script>"
             "function __tt(){var d=document.documentElement,n=d.dataset.theme==='dark'?'light':'dark';"
             "d.dataset.theme=n;try{localStorage.setItem('em-theme',n);}catch(e){}}"
             # 공유: 모바일은 기기 기본 공유창(Web Share API), PC는 링크 복사 폴백
             "function __toast(m){var t=document.createElement('div');t.className='xtoast';"
             "t.textContent=m;document.body.appendChild(t);setTimeout(function(){t.remove();},1700);}"
             "function __share(){var d={title:document.title,url:location.href};"
             "if(navigator.share){navigator.share(d).catch(function(){});}"
             "else if(navigator.clipboard){navigator.clipboard.writeText(location.href)"
             ".then(function(){__toast('링크가 복사됐어요');},function(){__toast('복사 실패');});}"
             "else{__toast(location.href);}}</script>")

# 로그인 상태 표시 (2026-07-27) — 헤더 계정 버튼의 글자·링크만 바꾼다.
#  · 낙관적 렌더: localStorage 힌트로 먼저 그리고 /api/me 로 확정 → 깜빡임 방지
#    (HEAD_SCRIPT 가 테마 FOUC 를 막는 것과 같은 패턴)
#  · cache:'no-store' 필수. 워커도 private,no-store 를 붙이지만 양쪽에서 막는다
#  · 실패해도 조용히 넘어간다 — 로그인 확인이 안 된다고 페이지가 깨질 이유는 없다
AUTH_JS = ("<script>(function(){var e=document.getElementById('__auth');if(!e)return;"
           "function set(n){if(n){e.textContent=n;e.setAttribute('href','mypage');e.className='abtn on';}"
           "else{e.textContent='로그인';e.setAttribute('href','login');e.className='abtn';}}"
           "try{var h=localStorage.getItem('olma_u');if(h)set(h);}catch(x){}"
           "fetch('/api/me',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){"
           "if(j&&j.login){var n=(j.user&&j.user.nickname)||'내 정보';set(n);"
           "try{localStorage.setItem('olma_u',n);}catch(x){}}"
           "else{set(null);try{localStorage.removeItem('olma_u');}catch(x){}}"
           "}).catch(function(){});})();</script>")

# 🔴 의도적으로 TOGGLE_JS 에 이어붙인다.
#    생성기 7곳이 이미 TOGGLE_JS 를 </body> 앞에 넣고 있으므로, 여기 붙이면
#    **스크립트는 7곳을 다시 고치지 않아도 전 페이지에 실린다.**
#    (버튼 HTML(AUTH_BTN)은 헤더 위치가 제각각이라 어쩔 수 없이 7곳에 넣어야 한다)
TOGGLE_JS = TOGGLE_JS + AUTH_JS
