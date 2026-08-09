// 관리자 페이지(/admin) 템플릿 — Claude Design "우리아이 관리자.dc.html" 이식(2026-07-18).
// 블루/슬레이트 톤·Pretendard·카드형 표·행 클릭 모달·상태 pill. 서버 렌더(멀티 라우트)라
// 각 탭은 자기 라우트에서 해당 pane만 그린다(디자인의 클라이언트 탭전환 → 서버 라우트 네비로 대체).
// 데이터는 실제 D1. 파괴적 동작(삭제·환불·원복)은 커스텀 확인 다이얼로그 → POST 폼 제출.

function escapeHtml(str) {
  if (str == null) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function jsonAttr(obj) {
  // <script> 안 JSON 임베드 — </script> 조기종료·유니코드 라인구분자 방지.
  return JSON.stringify(obj).replace(/</g, "\u003c").replace(new RegExp(String.fromCharCode(0x2028),"g"),"\u2028").replace(new RegExp(String.fromCharCode(0x2029),"g"),"\u2029");
}
const fmtDT = (iso) => (iso ? escapeHtml(String(iso).slice(0, 16).replace("T", " ")) : "-");
const fmtD = (iso) => (iso ? escapeHtml(String(iso).slice(0, 10)) : "-");
const won = (n) => Number(n || 0).toLocaleString("ko-KR") + "원";
const METHOD_KO = { card: "카드", phone: "휴대폰", vbank: "가상계좌" };
const PROV_KO = { kakao: "카카오", naver: "네이버", google: "Google" };

function daysLeft(iso) { return Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000); }
// 이용상태 pill(디자인 규칙): 이용중 D-n(초록) / 곧 만료(노랑) / 만료(빨강) / 테스트(보라) / 무기한(회색).
// 그룹(부모) pill은 **실제 게이팅 판정과 일치**해야 한다 — 2026-07-19 수정.
// 게이팅(index.js valid()): 자녀 하나라도 (is_test || trial_expires_at > now)이면 그 계정은 잠금 해제.
//   · 예전엔 테스트 자녀를 계산에서 빼고 남은 자녀의 **최소** 잔여일을 썼다 → 방금 등록한 테스트 자녀가
//     있어도 옛날 만료 자녀 때문에 "만료"로 뜨고, 행을 펼치면 자녀는 "테스트"라 서로 어긋나 보였다.
//   · 이제 **최대** 잔여일 기준(하나라도 유효하면 쓸 수 있으므로) + 테스트 자녀도 유효로 인정한다.
// trial_expires_at이 NULL이면 게이팅상 "잠김"이다(무기한 아님) → "미이용"으로 표시.
function statePill(kids) {
  const all = kids || [];
  if (!all.length) return { cls: "pill-mut", text: "자녀 없음" };
  if (all.every((c) => c.is_test)) return { cls: "pill-test", text: "테스트" };
  const real = all.filter((c) => !c.is_test);
  let max = null;
  for (const c of real) {
    if (!c.trial_expires_at) continue;
    const d = daysLeft(c.trial_expires_at);
    if (max === null || d > max) max = d;
  }
  // 실제 자녀가 전부 만료/미개시여도 테스트 자녀가 있으면 화면은 열린다 → 그 사실을 pill에 반영.
  const hasTest = all.some((c) => c.is_test);
  if (max === null) return hasTest ? { cls: "pill-test", text: "테스트" } : { cls: "pill-mut", text: "미이용" };
  if (max < 0) return hasTest ? { cls: "pill-test", text: "테스트" } : { cls: "pill-expired", text: "만료" };
  if (max <= 2) return { cls: "pill-soon", text: max === 0 ? "곧 만료 오늘" : `곧 만료 D-${max}` };
  return { cls: "pill-active", text: `이용중 D-${max}` };
}
function childPill(c) {
  if (c.is_test) return { cls: "pill-test", text: "테스트" };
  if (!c.trial_expires_at) return { cls: "pill-mut", text: "무기한" };
  const d = daysLeft(c.trial_expires_at);
  if (d < 0) return { cls: "pill-expired", text: "만료" };
  if (d <= 2) return { cls: "pill-soon", text: d === 0 ? "오늘 만료" : `D-${d}` };
  return { cls: "pill-active", text: `이용중 D-${d}` };
}

function adminLayout({ title, active, body, badges = {} }) {
  const TABS = [
    ["monitor", "모니터링", "/admin"],
    ["banners", "배너 관리", "/admin/banners"],
    ["correct", "데이터 보정", "/admin/correct"],
    ["members", "유료 회원", "/admin/members"],
    ["orders", "앱 주문", "/admin/orders"],
    ["payments", "결제 관리", "/admin/payments"],
    ["inquiries", "문의", "/admin/inquiries"],
    ["flags", "대화 신고", "/admin/community"],
    ["reports", "오류 신고", "/admin/reports"],
    ["feedback", "베타 의견", "/admin/feedback"],
    ["data", "데이터", "/admin/data"],
  ];
  const badgeOf = (key) => {
    const n = key === "reports" ? badges.reports : key === "feedback" ? badges.feedback
      : key === "orders" ? badges.orders : key === "inquiries" ? badges.inquiries
      : key === "flags" ? badges.flags : 0;
    return n ? `<span class="tabbadge">${n}</span>` : "";
  };
  const nav = TABS.map(([key, label, href]) =>
    `<a class="tab${key === active ? " on" : ""}" href="${href}">${label}${badgeOf(key)}</a>`
  ).join("");

  return `<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)} · 아이서랍 관리자</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
<style>
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  body{margin:0;background:#dfe3ea;color:#111827;font-family:'Pretendard',-apple-system,'Malgun Gothic',sans-serif;font-size:14px;line-height:1.5}
  a{color:#2563eb;text-decoration:none}
  input,button,textarea,select{font-family:inherit}
  .tnum{font-variant-numeric:tabular-nums}
  @keyframes popIn{from{transform:scale(.96) translateY(6px);opacity:0}to{transform:none;opacity:1}}
  @keyframes fadeIn{from{opacity:0}to{opacity:1}}
  .adm-scroll::-webkit-scrollbar{width:10px;height:10px}
  .adm-scroll::-webkit-scrollbar-thumb{background:#d1d5db;border-radius:6px;border:2px solid #fff}
  .adm-scroll::-webkit-scrollbar-track{background:transparent}
  /* ⚠ 2026-08-09: 「보기 어렵다」 지적을 숫자로 재서 고쳤다 —
     · #9ca3af 회색 글씨가 흰 배경에서 **2.54:1** 이었다(기준 4.5) → #6b7280 (4.83:1)
     · 글자가 11~13px 라 작았다 → 한 단계씩 키움
     · max-width 를 1360px 로 고정해 창이 좁으면 가로로 밀렸다 → min(1360px, 100%)
     ⚠ 관리자도 «읽는 화면»이다. 정보가 많다고 글씨를 줄이면 아무도 안 읽는다. */
  .wrap{padding:32px 24px 80px;max-width:min(1360px, 100%);margin:0 auto;display:flex;flex-direction:column;gap:20px}
  .eyebrow{font-size:13.5px;font-weight:800;letter-spacing:.14em;color:#2563eb;text-transform:uppercase}
  .apptitle{margin:5px 0 3px;font-size:25px;font-weight:900;letter-spacing:-.02em}
  .appdesc{margin:0;font-size:14px;color:#6b7280}
  .app{background:#f3f4f6;border:1px solid #cbd2dc;border-radius:16px;overflow:hidden;box-shadow:0 30px 70px -30px rgba(17,24,39,.4)}
  .topbar{background:#111827;padding:11px 22px;display:flex;align-items:center;gap:12px}
  .logo{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:7px;background:#2563eb;color:#fff;font-weight:900;font-size:14px}
  .topbar .nm{font-size:14px;font-weight:800;color:#fff}.topbar .nm span{color:#9aa3b2;font-weight:600}
  .topbar .env{margin-left:auto;display:inline-flex;align-items:center;gap:6px;font-size:13.5px;color:#9aa3b2}
  .topbar .dot{width:7px;height:7px;border-radius:50%;background:#22c55e}
  .topbar .who{font-size:13.5px;color:#cbd2dc;border-left:1px solid #374151;padding-left:12px}
  nav.tabs{background:#fff;border-bottom:1px solid #e5e7eb;padding:0 14px;display:flex;gap:2px;overflow-x:auto}
  .tab{padding:13px 16px;font-size:14px;font-weight:600;color:#6b7280;white-space:nowrap;border-bottom:2px solid transparent;margin-bottom:-1px}
  .tab:hover{color:#374151}
  .tab.on{color:#2563eb;font-weight:800;border-bottom-color:#2563eb}
  .tabbadge{margin-left:7px;display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#dc2626;color:#fff;font-size:13.5px;font-weight:800;vertical-align:middle}
  .pane{padding:24px 26px 30px;display:flex;flex-direction:column;gap:20px}
  .h2{margin:0;font-size:17px;font-weight:800;color:#111827}
  .sub{font-size:13.5px;color:#6b7280}
  .hrow{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
  .hleft{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:13px;overflow:hidden}
  .thead{display:flex;align-items:center;padding:11px 18px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-size:13.5px;font-weight:800;color:#6b7280}
  .trow{display:flex;align-items:center;padding:13px 18px;border-bottom:1px solid #f3f4f6}
  .trow.click{cursor:pointer}.trow.click:hover{background:#f9fafb}
  .ell{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
  .pill{display:inline-flex;align-items:center;font-size:13.5px;font-weight:800;border-radius:20px;padding:3px 10px;white-space:nowrap}
  .pill-active{color:#15803d;background:#dcfce7}.pill-soon{color:#b45309;background:#fef3c7}
  .pill-expired{color:#b91c1c;background:#fee2e2}.pill-test{color:#6d28d9;background:#ede9fe}
  .pill-mut{color:#6b7280;background:#f3f4f6}.pill-blue{color:#1d4ed8;background:#dbeafe}
  .prov{display:inline-flex;align-items:center;justify-content:center;padding:2px 8px;border-radius:6px;font-size:13.5px;font-weight:800}
  .prov-kakao{background:#fee500;color:#3c1e1e}.prov-naver{background:#03c75a;color:#fff}
  .prov-google{background:#fff;border:1px solid #e5e7eb;color:#374151}.prov-none{background:#f3f4f6;color:#6b7280}
  .search{display:flex;align-items:center;gap:7px;background:#fff;border:1px solid #e5e7eb;border-radius:9px;padding:8px 12px}
  .search input{flex:1;border:none;outline:none;background:transparent;font-size:14px;color:#111827}
  .btn{padding:9px 15px;border-radius:9px;border:1px solid #e5e7eb;background:#fff;color:#374151;font-size:14px;font-weight:700;cursor:pointer}
  .btn:hover{border-color:#c7cdd6}
  .btn.pri{background:#2563eb;border-color:#2563eb;color:#fff}.btn.pri:hover{filter:brightness(1.06)}
  .btn.dng{border-color:#fecaca;color:#dc2626}.btn.warn{border-color:#fed7aa;color:#c2410c}
  .btn.sm{padding:6px 11px;font-size:13.5px}
  .code{font-family:ui-monospace,Menlo,monospace;font-size:14px;background:#f3f4f6;color:#6b7280;padding:1px 6px;border-radius:5px}
  .empty{padding:40px;text-align:center;color:#6b7280;font-size:14px}
  .note{font-size:13.5px;color:#6b7280;line-height:1.5}
  .note.ok{color:#15803d;background:#dcfce7;padding:10px 14px;border-radius:9px;font-weight:700}
  /* 데이터 화면(2026-07-28) — 표를 골라 넣고·고치고·지운다 */
  .inp{padding:9px 12px;border:1px solid #e5e7eb;border-radius:9px;background:#fff;font-size:14px;font-family:inherit;color:#111827;width:100%}
  .fl{display:block;margin:12px 0 4px;font-size:13.5px;font-weight:700;color:#374151}
  .fl .mut{font-weight:400}
  .mut{color:#6b7280}
  .row{display:flex;flex-wrap:wrap}
  .tblwrap{background:#fff;border:1px solid #e5e7eb;border-radius:13px}
  .tbl{width:100%;border-collapse:collapse;font-size:13.5px;white-space:nowrap}
  .tbl th{position:sticky;top:0;background:#f9fafb;text-align:left;padding:10px 12px;font-size:13.5px;font-weight:800;color:#6b7280;border-bottom:1px solid #e5e7eb}
  .tbl td{padding:10px 12px;border-bottom:1px solid #f3f4f6;max-width:260px;overflow:hidden;text-overflow:ellipsis}
  .tbl tbody tr:hover{background:#f9fafb}
  #box form{padding:0 20px 20px}
  #box h3{padding:18px 20px 0}
  /* modal */
  #ov{position:fixed;inset:0;z-index:50;background:rgba(17,24,39,.5);display:none;align-items:center;justify-content:center;padding:40px;animation:fadeIn .18s ease}
  #ov.on{display:flex}
  #box{width:560px;max-width:100%;max-height:84vh;background:#fff;border-radius:16px;overflow:hidden;display:flex;flex-direction:column;animation:popIn .22s ease;box-shadow:0 30px 60px -20px rgba(0,0,0,.4)}
  #box .mh{padding:18px 22px;border-bottom:1px solid #e5e7eb;display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
  #box .mh h3{margin:0;font-size:17px;font-weight:900;color:#111827}
  #box .mh .x{cursor:pointer;font-size:20px;color:#6b7280;line-height:1;background:none;border:none}
  #box .mb{padding:20px 22px;overflow-y:auto}
  #box .mf{padding:14px 22px;border-top:1px solid #e5e7eb;background:#f9fafb;display:flex;gap:8px;flex-wrap:wrap}
  .krow{display:flex;justify-content:space-between;padding:10px 14px;background:#f9fafb;border-radius:9px;font-size:14px}
  .kstat{flex:1;min-width:110px;background:#f9fafb;border-radius:9px;padding:10px 12px}
  .kstat .l{font-size:13.5px;color:#6b7280}.kstat .v{font-size:14px;font-weight:700;color:#111827}
  .seclabel{font-size:14px;font-weight:800;color:#6b7280;margin-bottom:8px}
  /* confirm + toast */
  #cf{position:fixed;inset:0;z-index:60;background:rgba(17,24,39,.55);display:none;align-items:center;justify-content:center;padding:40px;animation:fadeIn .18s ease}
  #cf.on{display:flex}
  #cf .cbox{width:380px;max-width:100%;background:#fff;border-radius:16px;padding:24px;animation:popIn .2s ease;box-shadow:0 30px 60px -20px rgba(0,0,0,.4)}
  #cf .ct{font-size:17px;font-weight:900;margin-bottom:8px}#cf .cbd{font-size:14px;color:#6b7280;line-height:1.6;margin-bottom:20px}
  #cf .cbtns{display:flex;gap:10px;justify-content:flex-end}
  #toast{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);z-index:70;background:#111827;color:#fff;font-size:14px;font-weight:700;padding:12px 20px;border-radius:24px;box-shadow:0 10px 30px -8px rgba(0,0,0,.5);display:none;animation:popIn .2s ease}
  #toast.on{display:block}
  /* school-search dropdown */
  .sbox{position:relative;max-width:460px}
  .sres{position:absolute;top:52px;left:0;right:0;z-index:5;background:#fff;border:1px solid #e5e7eb;border-radius:10px;box-shadow:0 12px 30px -10px rgba(0,0,0,.2);overflow:hidden;display:none}
  .sres.on{display:block}
  .sres .it{cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:11px 14px;border-bottom:1px solid #f3f4f6}
  .sres .it:hover{background:#eff6ff}.sres .it .nm{font-size:14px;font-weight:700;color:#111827}.sres .it .mt{font-size:13.5px;color:#6b7280}
  @media(max-width:640px){.pane{padding:18px 14px 24px}.wrap{padding:20px 12px 60px}}
</style>
</head><body>
${adminSharedScript()}
<div class="wrap">
  <div>
    <div class="eyebrow">관리자 대시보드</div>
    <h1 class="apptitle">아이서랍 — 운영 관리자</h1>
    <p class="appdesc">${escapeHtml(title)}</p>
  </div>
  <div class="app">
    <div class="topbar">
      <span class="logo">우</span>
      <span class="nm">아이서랍 <span>관리자</span></span>
      <span class="env"><span class="dot"></span>eduthink-site-renderer</span>
      <span class="who">대표 · Basic Auth</span>
    </div>
    <nav class="tabs">${nav}</nav>
    <div class="pane">${body}</div>
  </div>
</div>
<div id="ov" onclick="if(event.target===this)closeModal()"><div id="box"></div></div>
<div id="cf" onclick="if(event.target===this)cfCancel()"><div class="cbox"><div class="ct" id="cft"></div><div class="cbd" id="cfb"></div><div class="cbtns"><button class="btn" onclick="cfCancel()">취소</button><button class="btn" id="cfok"></button></div></div></div>
<div id="toast"></div>
</body></html>`;
}

// 공통 스크립트 — body 상단에서 먼저 정의(모달/검색 헬퍼가 페이지 스크립트보다 먼저 있어야 함).
function adminSharedScript() {
  return `<script>
    window.openModal=function(h){document.getElementById('box').innerHTML=h;document.getElementById('ov').classList.add('on');};
    window.closeModal=function(){document.getElementById('ov').classList.remove('on');};
    var _cf=null;
    window.uiConfirmCb=function(title,body,fn,okLabel,danger){document.getElementById('cft').textContent=title;document.getElementById('cfb').textContent=body||'';var b=document.getElementById('cfok');b.textContent=okLabel||'확인';b.className='btn '+(danger?'dng':'pri');_cf=fn;document.getElementById('cf').classList.add('on');};
    window.cfCancel=function(){document.getElementById('cf').classList.remove('on');_cf=null;};
    document.getElementById&&document.addEventListener('click',function(e){if(e.target&&e.target.id==='cfok'){var f=_cf;cfCancel();if(f)f();}});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeModal();cfCancel();}});
    var _tt=null;
    window.showToast=function(m){var t=document.getElementById('toast');t.textContent=m;t.classList.add('on');if(_tt)clearTimeout(_tt);_tt=setTimeout(function(){t.classList.remove('on');},1800);};
    window.postForm=function(action,fields){var f=document.createElement('form');f.method='post';f.action=action;if(fields)for(var k in fields){var i=document.createElement('input');i.type='hidden';i.name=k;i.value=fields[k];f.appendChild(i);}document.body.appendChild(f);f.submit();};
    window.esc=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');};
    // 학교 이름 자동완성 — onPick(name,slug).
    window.attachSchoolSearch=function(input,box,onPick){var t=null;
      input.addEventListener('input',function(){var q=input.value.trim();clearTimeout(t);if(!q){box.classList.remove('on');return;}
        t=setTimeout(function(){fetch('/admin/school-search?q='+encodeURIComponent(q)).then(function(r){return r.json();}).then(function(list){
          if(!list.length){box.innerHTML='<div class="it"><span class="mt">검색 결과 없음</span></div>';box.classList.add('on');return;}
          box.innerHTML=list.map(function(s){return '<div class="it" data-slug="'+esc(s.slug)+'" data-name="'+esc(s.name)+'"><span class="nm">'+esc(s.name)+'</span><span class="mt">'+esc(s.kind)+' · '+esc(s.region)+'</span></div>';}).join('');
          box.classList.add('on');
          Array.prototype.forEach.call(box.querySelectorAll('.it[data-slug]'),function(it){it.addEventListener('click',function(){onPick(it.getAttribute('data-name'),it.getAttribute('data-slug'));box.classList.remove('on');});});
        }).catch(function(){});},180);});
      document.addEventListener('click',function(e){if(!box.contains(e.target)&&e.target!==input)box.classList.remove('on');});
    };
  </script>`;
}

// ================= 모니터링 =================
export function adminMonitorPage({ schoolCounts, lastSync, recentErrors, latestRun, totals = {}, badges }) {
  const kind = {}; (schoolCounts || []).forEach((c) => { kind[c.school_kind] = c.cnt; });
  const schools = totals.schools || 0;
  const pct = (n) => schools ? Math.round((n / schools) * 1000) / 10 : 0;
  const covCard = (label, n, color) => {
    const p = pct(n);
    return `<div class="card" style="padding:18px 20px;display:flex;flex-direction:column">
      <div style="font-size:13.5px;font-weight:700;color:#6b7280">${label}</div>
      <div style="font-size:30px;font-weight:900;letter-spacing:-.02em;margin:2px 0">${Number(n).toLocaleString()}</div>
      <div class="sub" style="margin-bottom:auto">전체의 ${p}%</div>
      <div style="height:7px;background:#f3f4f6;border-radius:4px;overflow:hidden;margin-top:12px"><div style="height:100%;background:${color};border-radius:4px;width:${p}%"></div></div>
    </div>`;
  };

  const syncFmt = (v) => v ? `<span style="color:#16a34a">${escapeHtml(String(v).slice(0, 10))}</span>` : `<span style="color:#6b7280">없음</span>`;
  const syncRows = (lastSync || []).map((s) => `<div class="trow" data-nm="${escapeHtml(s.name)}" style="padding:11px 16px">
    <div class="ell" style="flex:1"><div style="font-size:14px;font-weight:700;color:#111827" class="ell">${escapeHtml(s.name)}</div><div class="sub">${escapeHtml((s.school_kind || "").replace("학교", ""))}</div></div>
    <span style="width:56px;font-size:13.5px">${syncFmt(s.last_meal)}</span>
    <span style="width:56px;font-size:13.5px">${syncFmt(s.last_timetable)}</span>
    <span style="width:64px;font-size:13.5px">${syncFmt(s.last_schedule)}</span>
  </div>`).join("");

  const errRows = (recentErrors || []).map((e) => `<div style="padding:12px 16px;border-bottom:1px solid #f3f4f6">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px"><span style="font-size:13.5px;font-weight:800;color:#b91c1c;background:#fef2f2;border-radius:5px;padding:2px 7px">${escapeHtml(e.source)}</span><span class="sub tnum">${escapeHtml(String(e.occurred_at || "").slice(0, 16).replace("T", " "))}</span></div>
    <div style="font-size:13.5px;font-weight:700;color:#374151">${escapeHtml(e.school_name || e.target_school_id || "(전체)")}</div>
    <div style="font-size:13.5px;color:#6b7280;line-height:1.4">${escapeHtml(e.error_message)}</div>
  </div>`).join("");

  const runBlock = latestRun ? `
    <div class="card" style="padding:18px 20px;display:flex;align-items:center;gap:24px;flex-wrap:wrap">
      <div style="min-width:200px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="font-size:15px;font-weight:800">${escapeHtml(latestRun.job_name)}</span><span class="pill ${latestRun.status === "done" ? "pill-active" : latestRun.status === "failed" ? "pill-expired" : "pill-blue"}">${escapeHtml(latestRun.status)}</span></div><div class="sub">시작 ${escapeHtml(latestRun.started_at || "-")} · 종료 ${escapeHtml(latestRun.finished_at || "—")}</div></div>
      <div style="flex:1;min-width:200px"><div style="display:flex;justify-content:space-between;font-size:13.5px;color:#6b7280;margin-bottom:6px"><span>처리 진행률</span><span style="font-weight:800;color:#111827">${escapeHtml(latestRun.completed)} / ${escapeHtml(latestRun.total ?? "?")}</span></div><div style="height:10px;background:#f3f4f6;border-radius:5px;overflow:hidden"><div style="height:100%;background:linear-gradient(90deg,#2563eb,#3b82f6);width:${latestRun.total ? Math.round((latestRun.completed / latestRun.total) * 100) : 0}%"></div></div></div>
    </div>` : `<div class="card" style="padding:18px 20px"><span class="sub">아직 배치 실행 기록이 없습니다.</span></div>`;

  const body = `
    <div><div class="hleft" style="margin-bottom:12px"><h2 class="h2">적재 현황</h2><span class="sub">전국 데이터 채움 상태</span></div>
      <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:14px">
        <div class="card" style="padding:18px 20px">
          <div style="font-size:13.5px;font-weight:700;color:#6b7280">전체 학교</div>
          <div style="font-size:30px;font-weight:900;letter-spacing:-.02em;margin:2px 0 12px">${Number(schools).toLocaleString()}<span style="font-size:15px;font-weight:700;color:#6b7280">개교</span></div>
          <div style="display:flex;gap:8px">
            <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:8px 10px"><div style="font-size:13.5px;color:#6b7280">초등</div><div style="font-size:15px;font-weight:800">${Number(kind["초등학교"] || 0).toLocaleString()}</div></div>
            <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:8px 10px"><div style="font-size:13.5px;color:#6b7280">중학</div><div style="font-size:15px;font-weight:800">${Number(kind["중학교"] || 0).toLocaleString()}</div></div>
            <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:8px 10px"><div style="font-size:13.5px;color:#6b7280">고교</div><div style="font-size:15px;font-weight:800">${Number(kind["고등학교"] || 0).toLocaleString()}</div></div>
          </div>
        </div>
        ${covCard("학사일정 적재", totals.schedules || 0, "#16a34a")}
        ${covCard("학교 상세정보", totals.details || 0, "#2563eb")}
        ${covCard("급식 적재", totals.meals || 0, "#16a34a")}
      </div>
    </div>
    <div><div class="hleft" style="margin-bottom:12px"><h2 class="h2">ETL 진행 상황</h2><span class="sub">최근 배치 1건</span></div>${runBlock}</div>
    <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:22px;align-items:start">
      <div>
        <div class="hrow" style="margin-bottom:12px"><div class="hleft"><h2 class="h2">학교별 최근 갱신일</h2><span class="sub">최근 ${(lastSync || []).length}개교</span></div>
          <div class="search" style="width:220px"><span style="font-size:14px;color:#6b7280">🔍</span><input id="monq" placeholder="학교명 필터" oninput="monFilt()"></div></div>
        <div class="card">
          <div class="thead"><span style="flex:1">학교</span><span style="width:56px">급식</span><span style="width:56px">시간표</span><span style="width:64px">학사일정</span></div>
          <div class="adm-scroll" style="max-height:300px;overflow-y:auto" id="monbody">${syncRows || `<div class="empty">데이터 없음</div>`}</div>
        </div>
      </div>
      <div>
        <div class="hleft" style="margin-bottom:12px"><h2 class="h2">최근 API 실패 로그</h2><span class="sub" style="color:#dc2626;font-weight:700">${(recentErrors || []).length}건</span></div>
        <div class="card"><div class="adm-scroll" style="max-height:349px;overflow-y:auto">${errRows || `<div class="empty">실패 기록 없음</div>`}</div></div>
      </div>
    </div>
    <script>
      (function(){var rows=Array.prototype.slice.call(document.querySelectorAll('#monbody .trow[data-nm]'));
        window.monFilt=function(){var q=(document.getElementById('monq').value||'').trim();rows.forEach(function(r){r.style.display=(!q||r.getAttribute('data-nm').indexOf(q)>=0)?'':'none';});};});
    </script>`;
  return adminLayout({ title: "모니터링", active: "monitor", body, badges });
}

// ================= 유료 회원 (부모 중심 + 상세 모달) =================
export function adminMembersPage(groups, subscriber = false, maxChildren = 3, badges) {
  const gs = groups || [];
  const repOf = (g) => (g.account && g.account.nickname) ? g.account.nickname : (g.kids[0] ? g.kids[0].nickname : "-");
  const provClass = (p) => p ? `prov-${p}` : "prov-none";
  const provLabel = (p) => p ? (PROV_KO[p] || p) : "토큰";

  const rows = gs.map((g, i) => {
    const st = statePill(g.kids);
    const paid = (g.payments || []).some((p) => p.status !== "refunded");
    const school = g.kids.length ? `${escapeHtml(g.kids[0].school_name)}${g.kids.length > 1 ? ` 외 ${g.kids.length - 1}` : ""}` : "-";
    return `<div class="trow click" data-i="${i}">
      <div style="flex:1.6;display:flex;align-items:center;gap:9px;min-width:0"><span class="prov ${provClass(g.account && g.account.provider)}">${escapeHtml(provLabel(g.account && g.account.provider))}</span><span class="ell" style="font-size:14px;font-weight:700">${escapeHtml(repOf(g))}</span></div>
      <span style="width:70px;font-size:14px;color:#374151">${g.kids.length}명</span>
      <span class="ell" style="flex:1.2;font-size:14px;color:#374151">${school}</span>
      <span style="width:150px"><span class="pill ${st.cls}">${st.text}</span></span>
      <span style="width:80px"><span class="pill ${paid ? "pill-active" : "pill-mut"}">${paid ? "있음" : "없음"}</span></span>
    </div>`;
  }).join("");

  // 모달 build용 데이터.
  const data = gs.map((g) => ({
    token: String(g.token).slice(0, 8),
    prov: (g.account && g.account.provider) ? (PROV_KO[g.account.provider] || g.account.provider) : "토큰",
    provCls: provClass(g.account && g.account.provider),
    rep: repOf(g),
    joined: g.account ? fmtD(g.account.created_at) : "-",
    lastLogin: g.account ? fmtDT(g.account.last_login_at) : "-",
    notif: g.notif ? "신청" : "미신청",
    trial: g.trial ? "사용" : "미사용",
    ownerToken: String(g.token),
    kids: g.kids.map((c) => { const p = childPill(c); return {
      id: c.id, nickname: c.nickname, school: c.school_name, slug: c.school_slug,
      gradeClass: `${c.grade}학년${c.class_name ? " " + c.class_name + "반" : ""}`,
      community: c.community_nickname || "-", pillCls: p.cls, pillText: p.text,
      grade: c.grade, className: c.class_name || "",
    }; }),
    payments: (g.payments || []).map((p) => ({
      date: fmtD(p.created_at), amountF: won(p.amount), months: p.months, children: p.child_count,
      method: METHOD_KO[p.method] || p.method, refunded: p.status === "refunded",
    })),
  }));

  const body = `
    <div class="hrow"><div class="hleft"><h2 class="h2">유료 회원</h2><span class="sub">부모 1명 = 1행 · ${gs.length}명 · 행을 누르면 자녀·결제·계정 전체</span></div>
      <div class="search" style="width:240px"><span style="font-size:14px;color:#6b7280">🔍</span><input id="mq" placeholder="닉네임·자녀 별명 검색" oninput="mFilt()"></div></div>
    <div class="card">
      <div class="thead"><span style="flex:1.6">대표</span><span style="width:70px">자녀 수</span><span style="flex:1.2">학교</span><span style="width:150px">이용 상태</span><span style="width:80px">결제</span></div>
      <div class="adm-scroll" style="max-height:440px;overflow-y:auto" id="mbody">${rows || `<div class="empty">등록된 회원이 없습니다.</div>`}</div>
    </div>
    <div class="card" style="background:#fafbfc">
      <div style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:13px 16px" onclick="var d=document.getElementById('devbox');d.style.display=d.style.display==='none'?'block':'none'"><span style="font-size:14px;font-weight:700;color:#6b7280">🧰 개발/QA 보조 도구 (유료모드 토글 · 테스트 자녀 등록)</span><span class="sub">⌄</span></div>
      <div id="devbox" style="display:none;padding:0 16px 16px;display:none">
        <form method="post" action="/admin/members/subscriber" style="display:inline"><input type="hidden" name="action" value="${subscriber ? "off" : "on"}"><button class="btn ${subscriber ? "dng" : ""}">${subscriber ? "유료모드 끄기" : "이 브라우저 유료 가입자로 켜기"}</button></form>
        <!-- QA 계정 연결 — 로그인 게이트(users 행 유무)를 통과시켜 /mypage·/register-child 등을 검증 가능하게 한다.
             admin Basic Auth + DEV_TOOLS 이중 잠금 뒤에만 존재(회신2 Q4 조건). 운영 배포 시 DEV_TOOLS=false로 차단. -->
        <form method="post" action="/admin/members/dev-account" style="display:inline;margin-left:8px"><button class="btn">이 브라우저 로그인 상태로 만들기(QA)</button></form>
        <!-- dev-account는 쿠키가 없으면 매번 새 빈 계정을 만든다. 그래서 검수자가 채워진 화면을 못 보는 일이 반복됐다.
             이 버튼으로 지금 계정에 자녀·기록7건·방과후4건을 한 번에 심는다. -->
        <form method="post" action="/admin/members/dev-seed" style="display:inline;margin-left:8px"><button class="btn">QA 계정 + 데모 데이터 한 번에</button></form>
        <div style="margin-top:12px"><div class="seclabel">테스트 자녀 등록 (학교 이름 검색)</div>
          <form method="post" action="/admin/members/add-test-child">
            <div class="sbox"><div class="search"><span style="font-size:14px;color:#6b7280">🏫</span><input id="tcq" placeholder="학교명 입력" autocomplete="off"></div><div class="sres" id="tcres"></div></div>
            <input type="hidden" name="school_slug" id="tcslug" required>
            <div id="tcpick" style="font-size:13.5px;color:#16a34a;font-weight:700;margin:6px 0"></div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
              <input class="btn" style="cursor:text" name="grade" placeholder="학년" required>
              <input class="btn" style="cursor:text" name="class_name" placeholder="반(선택)">
              <input class="btn" style="cursor:text" name="nickname" placeholder="별명" required>
              <button class="btn pri" type="submit">등록 + 잠금해제</button>
            </div>
          </form>
        </div>
      </div>
    </div>
    <script>
      var MEMBERS=${jsonAttr(data)};
      (function(){
        var rows=Array.prototype.slice.call(document.querySelectorAll('#mbody .trow[data-i]'));
        rows.forEach(function(r){r.addEventListener('click',function(){memModal(+r.getAttribute('data-i'));});});
        window.mFilt=function(){var q=(document.getElementById('mq').value||'').trim().toLowerCase();
          rows.forEach(function(r){var m=MEMBERS[+r.getAttribute('data-i')];var hit=!q||m.rep.toLowerCase().indexOf(q)>=0||m.kids.some(function(k){return k.nickname.toLowerCase().indexOf(q)>=0;});r.style.display=hit?'':'none';});};
        var inp=document.getElementById('tcq'),box=document.getElementById('tcres');
        if(inp)attachSchoolSearch(inp,box,function(name,slug){document.getElementById('tcslug').value=slug;inp.value=name;document.getElementById('tcpick').textContent='선택됨: '+name;});
      })();
      window.memModal=function(i){var m=MEMBERS[i];
        var kids=m.kids.map(function(c,ci){return '<div style="border:1px solid #e5e7eb;border-radius:11px;padding:12px 14px">'
          +'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px"><span style="font-size:14px;font-weight:800">'+esc(c.nickname)+'</span><span class="pill '+c.pillCls+'">'+esc(c.pillText)+'</span></div>'
          +'<div style="font-size:13.5px;color:#6b7280;margin-bottom:8px">'+esc(c.school)+' · '+esc(c.gradeClass)+' · 커뮤니티 '+esc(c.community)+'</div>'
          +'<div style="display:flex;gap:8px"><button class="btn sm" onclick="editChild('+i+','+ci+')">수정</button>'
          +'<a class="btn sm" style="color:#2563eb" href="/school/'+encodeURIComponent(c.slug)+'/?child='+c.id+'" target="_blank">화면 보기 ↗</a>'
          +'<button class="btn sm dng" onclick="delChild('+i+','+ci+')">삭제</button></div></div>';}).join('');
        var pays=m.payments.length?m.payments.map(function(p){return '<div class="trow" style="padding:11px 14px"><span style="width:84px;font-size:13.5px;color:#6b7280">'+esc(p.date)+'</span><span style="flex:1;font-size:14px;font-weight:700">'+esc(p.amountF)+'</span><span style="font-size:13.5px;color:#6b7280;margin-right:10px">'+p.months+'개월·'+p.children+'명·'+esc(p.method)+'</span><span class="pill '+(p.refunded?'pill-expired':'pill-active')+'">'+(p.refunded?'환불':'완료')+'</span></div>';}).join(''):'<div class="empty" style="padding:16px">결제 내역 없음</div>';
        openModal('<div class="mh"><div style="display:flex;align-items:center;gap:10px"><span class="prov '+m.provCls+'">'+esc(m.prov)+'</span><div><h3>'+esc(m.rep)+'</h3><div class="sub">토큰 '+esc(m.token)+'… · 가입 '+esc(m.joined)+'</div></div></div><button class="x" onclick="closeModal()">✕</button></div>'
          +'<div class="mb adm-scroll">'
          +'<div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap"><div class="kstat"><div class="l">최근 로그인</div><div class="v">'+esc(m.lastLogin)+'</div></div><div class="kstat"><div class="l">알림 신청</div><div class="v">'+esc(m.notif)+'</div></div><div class="kstat"><div class="l">무료체험</div><div class="v">'+esc(m.trial)+'</div></div></div>'
          +'<div class="seclabel">자녀 '+m.kids.length+'명</div><div style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">'+kids+'</div>'
          +'<div class="seclabel">결제 내역 '+m.payments.length+'건</div><div class="card" style="margin-bottom:20px">'+pays+'</div>'
          +'<div style="background:#f9fafb;border-radius:11px;padding:14px"><div class="seclabel">부모 단위 액션</div>'
          +'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap"><span style="font-size:13.5px;color:#6b7280">이용기간</span>'
          +'<button class="btn sm" onclick="adjM('+i+',-30)">-30일</button><button class="btn sm" onclick="adjM('+i+',-7)">-7일</button><button class="btn sm" onclick="adjM('+i+',7)">+7일</button><button class="btn sm pri" onclick="adjM('+i+',30)">+30일</button></div>'
          +'<button class="btn dng" style="width:100%" onclick="delMember('+i+')">회원(부모) 전체 삭제</button></div>'
          +'</div>');
      };
      window.adjM=function(i,days){postForm('/admin/members/adjust',{owner_token:MEMBERS[i].ownerToken,days:days});};
      window.delChild=function(i,ci){var c=MEMBERS[i].kids[ci];uiConfirmCb('자녀 삭제','"'+c.nickname+'" 자녀를 삭제합니다. 되돌릴 수 없습니다.',function(){postForm('/admin/members/'+c.id+'/delete');},'삭제',true);};
      window.delMember=function(i){var m=MEMBERS[i];uiConfirmCb('회원 전체 삭제','"'+m.rep+'"(부모)의 모든 자녀를 삭제합니다. 계정·결제 기록은 보존됩니다.',function(){postForm('/admin/members/token-delete',{owner_token:m.ownerToken});},'삭제',true);};
      window.editChild=function(i,ci){var c=MEMBERS[i].kids[ci];
        openModal('<div class="mh"><h3>자녀 정보 수정</h3><button class="x" onclick="closeModal()">✕</button></div>'
          +'<form method="post" action="/admin/members/'+c.id+'/edit"><div class="mb"><div style="display:flex;flex-direction:column;gap:10px">'
          +'<label style="font-size:13.5px;color:#6b7280">별명<br><input class="btn" style="cursor:text;width:100%;margin-top:4px" name="nickname" value="'+esc(c.nickname)+'" required></label>'
          +'<label style="font-size:13.5px;color:#6b7280">학년<br><input class="btn" style="cursor:text;width:100%;margin-top:4px" name="grade" value="'+esc(c.grade)+'" required></label>'
          +'<label style="font-size:13.5px;color:#6b7280">반<br><input class="btn" style="cursor:text;width:100%;margin-top:4px" name="class_name" value="'+esc(c.className)+'" placeholder="비우면 없음"></label>'
          +'</div></div><div class="mf"><span style="flex:1"></span><button type="button" class="btn" onclick="closeModal()">취소</button><button type="submit" class="btn pri">저장</button></div></form>');
      };
    </script>`;
  return adminLayout({ title: "유료 회원", active: "members", body, badges });
}

/* ================= 앱 주문 (orders) =================
   「결제 관리」 탭은 옛 웹 더미결제(payments 표)를 본다. 앱에서 일어나는 결제는 **orders** 표에 쌓이는데
   여태 관리자 화면이 없었다 — 무통장 입금을 확인해 줄 자리가 없으면 그 결제수단은 사실상 죽은 것이다.
   그래서 표를 따로 둔다. 두 표를 한 화면에 섞으면 «환불»과 «입금확인»이 같은 줄에 붙어 서로 오조작한다. */
const ORDER_STATUS = {
  pending:          { ko: "대기",     cls: "pill-mut" },
  awaiting_deposit: { ko: "입금대기", cls: "pill-soon" },
  confirmed:        { ko: "입금확인", cls: "pill-blue" },
  active:           { ko: "이용중",   cls: "pill-active" },
  expired:          { ko: "만료",     cls: "pill-expired" },
  cancelled:        { ko: "취소",     cls: "pill-mut" },
};
const ORDER_METHOD = { mock: "모의결제", bank_transfer: "무통장", pg: "카드(PG)", google_iap: "구글 인앱" };

export function adminOrdersPage(orders, { q = "", status = "" } = {}, badges) {
  const os = orders || [];
  const st = (s) => ORDER_STATUS[s] || { ko: s, cls: "pill-mut" };
  const rows = os.map((o, i) => `<div class="trow click" data-i="${i}"${o.status === "cancelled" || o.status === "expired" ? ' style="opacity:.55"' : ""}>
    <span style="width:96px;font-size:13.5px;color:#6b7280" class="tnum">${fmtD(o.created_at)}</span>
    <span class="ell" style="flex:1;font-size:14px;font-weight:700">${escapeHtml(o.parent_name || "(이름 없음)")}</span>
    <span class="ell" style="width:110px;font-size:13.5px;color:#374151">${escapeHtml(o.child_nickname || "(삭제된 자녀)")}</span>
    <span style="width:70px;font-size:13.5px;color:#374151">${o.months}개월</span>
    <span style="width:86px;text-align:right;font-size:14px;font-weight:800" class="tnum">${won(o.amount)}</span>
    <span style="width:92px;font-size:13.5px;color:#374151">${escapeHtml(ORDER_METHOD[o.method] || o.method)}</span>
    <span style="width:86px"><span class="pill ${st(o.status).cls}">${st(o.status).ko}</span></span>
    <span style="width:88px;font-size:13.5px;color:#6b7280" class="tnum">${fmtD(o.expires_at)}</span>
  </div>`).join("");

  // 「이 달에 실제로 들어온 돈」이 아니라 «유효 이용권 합계»다 — 취소·만료는 뺀다.
  const live = os.filter((o) => o.status === "active" || o.status === "confirmed");
  const total = live.reduce((a, o) => a + Number(o.amount), 0);
  const waiting = os.filter((o) => o.status === "awaiting_deposit").length;

  const FILTERS = [["", "전체"], ["awaiting_deposit", "입금대기"], ["active", "이용중"], ["cancelled", "취소"], ["expired", "만료"]];
  const chips = FILTERS.map(([k, label]) =>
    `<a class="btn sm${k === status ? " pri" : ""}" href="/admin/orders?s=${k}${q ? `&q=${encodeURIComponent(q)}` : ""}">${label}</a>`).join("");

  const data = os.map((o) => ({
    id: o.id, date: fmtDT(o.created_at), parent: o.parent_name || "(이름 없음)",
    child: o.child_nickname || "(삭제된 자녀)", months: o.months, amountF: won(o.amount),
    method: ORDER_METHOD[o.method] || o.method, statusKo: st(o.status).ko, status: o.status,
    payer: o.payer_name || "", token: o.provider_token ? String(o.provider_token).slice(0, 16) + "…" : "",
    confirmed: fmtDT(o.confirmed_at), activated: fmtDT(o.activated_at), expires: fmtD(o.expires_at),
  }));

  const body = `
    <div class="hrow"><div class="hleft"><h2 class="h2">앱 주문</h2>
      <span class="sub">유효 합계</span><span style="font-size:15px;font-weight:900;color:#2563eb">${won(total)}</span>
      ${waiting ? `<span class="pill pill-soon">입금대기 ${waiting}건</span>` : ""}</div>
      <form method="get" action="/admin/orders" class="search" style="width:220px"><span style="font-size:14px;color:#6b7280">🔍</span>
        <input type="hidden" name="s" value="${escapeHtml(status)}"><input name="q" value="${escapeHtml(q)}" placeholder="부모·자녀 이름 검색"></form></div>
    <div style="display:flex;gap:6px;margin-bottom:12px">${chips}</div>
    <div class="card">
      <div class="thead"><span style="width:96px">주문일</span><span style="flex:1">부모</span><span style="width:110px">자녀</span><span style="width:70px">기간</span><span style="width:86px;text-align:right">금액</span><span style="width:92px">수단</span><span style="width:86px">상태</span><span style="width:88px">이용 만료</span></div>
      <div class="adm-scroll" style="max-height:460px;overflow-y:auto" id="obody">${rows || `<div class="empty">주문이 없습니다.</div>`}</div>
    </div>
    <div class="note">※ 입금확인을 누르면 그 자리에서 이용권이 켜지고 자녀 만료일이 연장됩니다(남은 기간에 이어붙임). 되돌리려면 취소가 아니라 만료일을 직접 조정하세요.</div>
    <script>
      var ORDERS=${jsonAttr(data)};
      (function(){Array.prototype.slice.call(document.querySelectorAll('#obody .trow[data-i]')).forEach(function(r){r.addEventListener('click',function(){orderModal(+r.getAttribute('data-i'));});});})();
      window.orderModal=function(i){var o=ORDERS[i];
        var canConfirm=(o.status==='awaiting_deposit'||o.status==='confirmed'||o.status==='pending');
        var canCancel=(o.status==='pending'||o.status==='awaiting_deposit');
        openModal('<div class="mh"><div><h3>'+esc(o.parent)+' · '+esc(o.child)+'</h3><div class="sub">주문 '+esc(o.date)+' · #'+o.id+'</div></div><button class="x" onclick="closeModal()">✕</button></div>'
          +'<div class="mb"><div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px"><span style="font-size:14px;color:#6b7280">'+o.months+'개월</span><span style="font-size:26px;font-weight:900">'+esc(o.amountF)+'</span></div>'
          +'<div style="display:flex;flex-direction:column;gap:8px">'
          +'<div class="krow"><span>상태</span><b>'+esc(o.statusKo)+'</b></div>'
          +'<div class="krow"><span>수단</span><b>'+esc(o.method)+'</b></div>'
          +(o.payer?'<div class="krow"><span>입금자명</span><b>'+esc(o.payer)+'</b></div>':'')
          +(o.token?'<div class="krow"><span>구매 토큰</span><b style="font-size:13.5px">'+esc(o.token)+'</b></div>':'')
          +'<div class="krow"><span>입금확인</span><b>'+esc(o.confirmed)+'</b></div>'
          +'<div class="krow"><span>이용 시작</span><b>'+esc(o.activated)+'</b></div>'
          +'<div class="krow"><span>이용 만료</span><b>'+esc(o.expires)+'</b></div>'
          +'</div></div>'
          +'<div class="mf">'+(canConfirm?'<button type="button" class="btn pri" onclick="confirmOrder('+o.id+')">입금확인 · 이용권 켜기</button>':'')
          +'<span style="flex:1"></span>'+(canCancel?'<button type="button" class="btn dng" onclick="cancelOrder('+o.id+')">주문 취소</button>':'')+'</div>');
      };
      window.confirmOrder=function(id){uiConfirmCb('입금확인','이 주문을 확인 처리하고 자녀 이용권을 연장합니다.',function(){postForm('/admin/orders/'+id+'/confirm');},'확인');};
      window.cancelOrder=function(id){uiConfirmCb('주문 취소','이 주문을 취소 상태로 바꿉니다. 이용권은 켜지지 않습니다.',function(){postForm('/admin/orders/'+id+'/cancel');},'취소',true);};
    </script>`;
  return adminLayout({ title: "앱 주문", active: "orders", body, badges });
}

// ================= 결제 관리 =================
export function adminPaymentsPage(payments, q, nameMap = {}, badges) {
  const ps = payments || [];
  const nameOf = (p) => p.payer_name || nameMap[p.owner_token] || (String(p.owner_token).slice(0, 8) + "…");
  const rows = ps.map((p, i) => `<div class="trow click" data-i="${i}"${p.status === "refunded" ? ' style="opacity:.55"' : ""}>
    <span style="width:96px;font-size:13.5px;color:#6b7280" class="tnum">${fmtD(p.created_at)}</span>
    <span class="ell" style="flex:1;font-size:14px;font-weight:700">${escapeHtml(nameOf(p))}${p.payer_name ? "" : ' <span class="code">토큰</span>'}</span>
    <span style="width:90px;text-align:right;font-size:14px;font-weight:800" class="tnum">${won(p.amount)}</span>
    <span style="width:96px;font-size:13.5px;color:#374151">${p.months}개월·${p.child_count}명</span>
    <span style="width:120px;font-size:13.5px;color:#374151">${escapeHtml(METHOD_KO[p.method] || p.method)}${p.auto_renew ? " · 자동" : ""}</span>
    <span style="width:80px"><span class="pill ${p.status === "refunded" ? "pill-expired" : "pill-active"}">${p.status === "refunded" ? "환불됨" : "결제완료"}</span></span>
  </div>`).join("");
  const total = ps.filter((p) => p.status !== "refunded").reduce((a, p) => a + Number(p.amount), 0);

  const data = ps.map((p) => ({
    id: p.id, date: fmtDT(p.created_at), name: nameOf(p), payer_name: p.payer_name || "",
    accountName: nameMap[p.owner_token] || "", token: String(p.owner_token).slice(0, 8),
    amountF: won(p.amount), amount: Number(p.amount), months: p.months, children: p.child_count,
    method: METHOD_KO[p.method] || p.method, auto: !!p.auto_renew, refunded: p.status === "refunded",
    expire: p.new_expiry ? fmtD(p.new_expiry) : "-",
  }));

  const body = `
    <div class="hrow"><div class="hleft"><h2 class="h2">결제 관리</h2><span class="sub">유효 합계</span><span style="font-size:15px;font-weight:900;color:#2563eb">${won(total)}</span></div>
      <form method="get" action="/admin/payments" class="search" style="width:220px"><span style="font-size:14px;color:#6b7280">🔍</span><input name="q" value="${escapeHtml(q || "")}" placeholder="이름·토큰 검색"></form></div>
    <div class="card">
      <div class="thead"><span style="width:96px">결제일</span><span style="flex:1">이름</span><span style="width:90px;text-align:right">금액</span><span style="width:96px">기간·자녀</span><span style="width:120px">수단</span><span style="width:80px">상태</span></div>
      <div class="adm-scroll" style="max-height:440px;overflow-y:auto" id="pbody">${rows || `<div class="empty">결제 내역이 없습니다.</div>`}</div>
    </div>
    <div class="note">※ 현재 베타(더미 결제). PG 연동 시 payer_name 자동 채움 + 영수증·승인번호 컬럼 추가 예정.</div>
    <script>
      var PAYS=${jsonAttr(data)};
      (function(){var rows=Array.prototype.slice.call(document.querySelectorAll('#pbody .trow[data-i]'));rows.forEach(function(r){r.addEventListener('click',function(){payModal(+r.getAttribute('data-i'));});});})();
      window.payModal=function(i){var p=PAYS[i];
        openModal('<div class="mh"><div><h3>'+esc(p.name)+'</h3><div class="sub">결제 '+esc(p.date)+' · 토큰 '+esc(p.token)+'…</div></div><button class="x" onclick="closeModal()">✕</button></div>'
          +'<form method="post" action="/admin/payments/'+p.id+'/edit"><div class="mb">'
          +'<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px"><span style="font-size:14px;color:#6b7280">결제 금액</span><span style="font-size:26px;font-weight:900">'+esc(p.amountF)+'</span></div>'
          +'<div style="display:flex;flex-direction:column;gap:8px">'
          +'<label class="krow"><span>결제자 이름</span><input name="payer_name" value="'+esc(p.payer_name)+'" placeholder="'+(p.accountName?('계정: '+esc(p.accountName)):'PG 연동 후 자동')+'" style="border:1px solid #e5e7eb;border-radius:7px;padding:5px 8px;text-align:right"></label>'
          +'<label class="krow"><span>금액(수정)</span><input name="amount" type="number" value="'+p.amount+'" style="width:120px;border:1px solid #e5e7eb;border-radius:7px;padding:5px 8px;text-align:right"></label>'
          +'<div class="krow"><span>기간 · 자녀</span><b>'+p.months+'개월 · '+p.children+'명</b></div>'
          +'<div class="krow"><span>수단</span><b>'+esc(p.method)+(p.auto?' · 자동구독':'')+'</b></div>'
          +'<div class="krow"><span>이용 만료</span><b>'+esc(p.expire)+'</b></div>'
          +'</div></div>'
          +'<div class="mf"><button type="submit" class="btn pri">수정 저장</button>'+(p.refunded?'':'<button type="button" class="btn warn" onclick="refundPay('+p.id+")\\">환불</button>")+'<span style="flex:1"></span><button type="button" class="btn dng" onclick="delPay('+p.id+')">삭제</button></div></form>');
      };
      window.refundPay=function(id){uiConfirmCb('환불 처리','이 결제를 환불 처리합니다(상태만 환불됨으로).',function(){postForm('/admin/payments/'+id+'/refund');},'환불');};
      window.delPay=function(id){uiConfirmCb('결제 삭제','이 결제 기록을 완전히 삭제합니다.',function(){postForm('/admin/payments/'+id+'/delete');},'삭제',true);};
    </script>`;
  return adminLayout({ title: "결제 관리", active: "payments", body, badges });
}

// ================= 데이터 보정 =================
export function adminCorrectPage(school, meals, schedules, editLog = [], badges) {
  const searchBox = `
    <div class="sbox">
      <div class="search" style="padding:10px 14px"><span style="font-size:14px;color:#6b7280">🏫</span><input id="cq" placeholder="학교명 입력 (예: 대치, 반포) — 코드·번호 몰라도 됩니다" autocomplete="off" style="font-size:14px"></div>
      <div class="sres" id="cres"></div>
    </div>
    <script>(function(){var inp=document.getElementById('cq'),box=document.getElementById('cres');if(inp)attachSchoolSearch(inp,box,function(name,slug){location.href='/admin/correct?school_slug='+encodeURIComponent(slug);});})();</script>`;

  const logRows = (editLog || []).map((l) => `<div style="padding:12px 14px;border-bottom:1px solid #f3f4f6">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px"><span class="sub">${escapeHtml(String(l.edited_at).slice(0, 16).replace("T", " "))} · ${escapeHtml(l.field_name)}</span>
      <form method="post" action="/admin/correct/undo" style="display:inline" onsubmit="return cfUndo(event,this)"><input type="hidden" name="log_id" value="${l.id}"><button class="btn sm" style="padding:2px 8px;border:none;color:#2563eb;background:none">원복</button></form></div>
    <div style="font-size:13.5px;color:#374151"><span style="text-decoration:line-through;color:#6b7280">${escapeHtml((l.old_value || "").slice(0, 40))}</span> → <b>${escapeHtml((l.new_value || "").slice(0, 40))}</b></div>
  </div>`).join("");
  const logCard = `<div class="seclabel">🕘 수정 이력 (최근 ${(editLog || []).length}건)</div><div class="card"><div class="adm-scroll" style="max-height:420px;overflow-y:auto">${logRows || `<div class="empty">수정 이력이 없습니다.</div>`}</div></div><div class="note" style="margin-top:10px">⚠ NEIS 재적재 시 수동 수정이 덮어써질 수 있습니다(이력으로 추적).</div>`;

  let selBlock = `<div class="empty">위에서 학교를 검색해 선택하면 급식·학사일정 보정 화면이 나타납니다.</div>`;
  if (school) {
    const mealRows = (meals || []).map((m) => `<div class="trow" style="padding:11px 14px;gap:12px">
      <span style="width:52px;font-size:13.5px;color:#6b7280">${escapeHtml(m.meal_date)}</span>
      <form method="post" action="/admin/correct/meals/${m.id}" style="flex:1;display:flex;gap:8px"><input class="btn" style="cursor:text;flex:1;text-align:left" name="dishes" value="${escapeHtml(m.dishes)}"><button class="btn sm pri" type="submit">저장</button></form>
    </div>`).join("");
    const schRows = (schedules || []).map((s) => `<div class="trow" style="padding:11px 14px;gap:12px">
      <span style="width:52px;font-size:13.5px;color:#6b7280">${escapeHtml(s.event_date)}</span>
      <form method="post" action="/admin/correct/schedules/${s.id}" style="flex:1;display:flex;gap:8px"><input class="btn" style="cursor:text;flex:1;text-align:left" name="event_name" value="${escapeHtml(s.event_name)}"><button class="btn sm pri" type="submit">저장</button></form>
    </div>`).join("");
    selBlock = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start">
      <div>
        <div class="hleft" style="margin-bottom:12px"><span style="font-size:15px;font-weight:800">${escapeHtml(school.name)}</span><span class="sub">${escapeHtml(shortKind(school.school_kind))} · ${escapeHtml(school.sido || "")}</span></div>
        <div class="seclabel">🍚 급식 보정 (최근 ${(meals || []).length}건)</div><div class="card" style="margin-bottom:18px">${mealRows || `<div class="empty">데이터 없음</div>`}</div>
        <div class="seclabel">📅 학사일정 보정 (최근 ${(schedules || []).length}건)</div><div class="card">${schRows || `<div class="empty">데이터 없음</div>`}</div>
      </div>
      <div>${logCard}</div>
    </div>`;
  }

  const body = `
    <div class="hleft"><h2 class="h2">데이터 보정</h2><span class="sub">학교 이름으로 찾아 급식·학사일정 수동 수정 · 이력 원복</span></div>
    ${searchBox}
    ${selBlock}
    ${school ? "" : `<div style="max-width:640px">${logCard}</div>`}
    <script>window.cfUndo=function(e,f){e.preventDefault();uiConfirmCb('원복하시겠어요?','이 수정을 원본값으로 되돌립니다.',function(){f.submit();},'원복');return false;};</script>`;
  return adminLayout({ title: "데이터 보정", active: "correct", body, badges });
}
function shortKind(k) { return (k || "").replace("학교", ""); }

// ================= 배너 관리 =================
export function adminBannersPage(banners, badges) {
  const TYPE_KO = { adsense: "애드센스", coupang: "쿠팡", house: "하우스", b2b: "B2B 학원" };
  const rows = (banners || []).map((b) => `<div class="trow" style="align-items:center">
    <span style="width:50px;font-size:14px;font-weight:900;color:#2563eb">${escapeHtml(b.slot)}</span>
    <span style="width:90px;font-size:13.5px;color:#374151">${escapeHtml(TYPE_KO[b.banner_type] || b.banner_type)}</span>
    <span class="ell" style="flex:1;font-size:14px;font-weight:700">${escapeHtml(b.advertiser_name || "-")}</span>
    <span style="width:130px;font-size:13.5px;color:#6b7280">${escapeHtml(b.region_office_code || "전체")}</span>
    <span style="width:120px;font-size:13.5px;color:#6b7280">${escapeHtml(b.starts_at || "-")}~${escapeHtml(b.ends_at || "-")}</span>
    <span style="width:60px"><span class="pill ${b.paid ? "pill-active" : "pill-soon"}">${b.paid ? "완료" : "미납"}</span></span>
    <span style="width:210px;display:flex;align-items:center;justify-content:flex-end;gap:8px">
      <span class="pill ${b.active ? "pill-blue" : "pill-mut"}">${b.active ? "게시중" : "숨김"}</span>
      <form method="post" action="/admin/banners/${b.id}/toggle" style="display:inline"><button class="btn sm" style="border:none;background:none;color:#2563eb;padding:2px 4px">${b.active ? "숨기기" : "게시"}</button></form>
      <a class="btn sm" style="border:none;padding:2px 4px;color:#6b7280" href="#edit-${b.id}">수정</a>
      <form method="post" action="/admin/banners/${b.id}/delete" style="display:inline" onsubmit="return cfDel(event,this)"><button class="btn sm" style="border:none;background:none;color:#dc2626;padding:2px 4px">삭제</button></form>
    </span>
  </div>`).join("");

  // 수정 폼(앵커 열림) + 등록 폼.
  const editForms = (banners || []).map((b) => `<div id="edit-${b.id}" style="display:none;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-top:8px" class="bedit">
    <div class="seclabel">슬롯 ${escapeHtml(b.slot)} 수정</div>
    <form method="post" action="/admin/banners/${b.id}/edit" style="display:flex;flex-direction:column;gap:8px">
      <input class="btn" style="cursor:text" name="advertiser_name" value="${escapeHtml(b.advertiser_name || "")}" placeholder="광고주">
      <input class="btn" style="cursor:text" name="image_url" value="${escapeHtml(b.image_url || "")}" placeholder="이미지 URL">
      <input class="btn" style="cursor:text" name="link_url" value="${escapeHtml(b.link_url || "")}" placeholder="링크 URL">
      <input class="btn" style="cursor:text" name="alt_text" value="${escapeHtml(b.alt_text || "")}" placeholder="문구">
      <input class="btn" style="cursor:text" name="region_office_code" value="${escapeHtml(b.region_office_code || "")}" placeholder="노출지역(교육청코드)">
      <div style="display:flex;gap:8px"><input class="btn" style="cursor:text;flex:1" name="starts_at" value="${escapeHtml(b.starts_at || "")}" placeholder="시작"><input class="btn" style="cursor:text;flex:1" name="ends_at" value="${escapeHtml(b.ends_at || "")}" placeholder="종료"></div>
      <textarea class="btn" style="cursor:text;min-height:52px" name="code_snippet" placeholder="코드 스니펫">${escapeHtml(b.code_snippet || "")}</textarea>
      <label style="font-size:13.5px;color:#6b7280"><input type="checkbox" name="paid" ${b.paid ? "checked" : ""}> 결제완료</label>
      <div><button class="btn pri" type="submit">저장</button></div>
    </form>
  </div>`).join("");

  const body = `
    <div class="hrow"><div class="hleft"><h2 class="h2">배너 관리</h2><span class="sub">광고 7슬롯 · 애드센스·쿠팡·하우스·B2B</span></div>
      <button class="btn pri" onclick="document.getElementById('newbanner').style.display='block'">+ 배너 등록</button></div>
    <div class="card">
      <div class="thead"><span style="width:50px">슬롯</span><span style="width:90px">종류</span><span style="flex:1">광고주</span><span style="width:130px">노출지역</span><span style="width:120px">기간</span><span style="width:60px">결제</span><span style="width:210px;text-align:right">상태·액션</span></div>
      ${rows || `<div class="empty">등록된 배너가 없습니다.</div>`}
    </div>
    ${editForms}
    <div id="newbanner" style="display:none;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px">
      <div class="seclabel">배너 등록 <span class="sub">(슬롯 1·2 애드센스 / 3 쿠팡 / 4·5 하우스 / 6·7 B2B)</span></div>
      <form method="post" action="/admin/banners" style="display:flex;flex-direction:column;gap:8px">
        <div style="display:flex;gap:8px"><input class="btn" style="cursor:text;width:110px" name="slot" type="number" min="1" max="7" placeholder="슬롯 1~7" required>
          <select class="btn" name="banner_type" required><option value="adsense">애드센스</option><option value="coupang">쿠팡</option><option value="house">하우스</option><option value="b2b">B2B 학원</option></select></div>
        <textarea class="btn" style="cursor:text;min-height:52px" name="code_snippet" placeholder="코드 스니펫(애드센스/쿠팡)"></textarea>
        <input class="btn" style="cursor:text" name="image_url" placeholder="이미지 URL(하우스/B2B)">
        <input class="btn" style="cursor:text" name="link_url" placeholder="링크 URL">
        <input class="btn" style="cursor:text" name="alt_text" placeholder="대체 텍스트">
        <input class="btn" style="cursor:text" name="advertiser_name" placeholder="광고주명(B2B)">
        <input class="btn" style="cursor:text" name="region_office_code" placeholder="노출지역 교육청코드(비우면 전체)">
        <div style="display:flex;gap:8px"><input class="btn" style="cursor:text;flex:1" type="date" name="starts_at"><input class="btn" style="cursor:text;flex:1" type="date" name="ends_at"></div>
        <label style="font-size:13.5px;color:#6b7280"><input type="checkbox" name="paid" value="1"> 결제완료</label>
        <div><button class="btn pri" type="submit">등록</button></div>
      </form>
    </div>
    <script>
      window.cfDel=function(e,f){e.preventDefault();uiConfirmCb('배너 삭제','이 배너를 삭제합니다.',function(){f.submit();},'삭제',true);return false;};
      Array.prototype.forEach.call(document.querySelectorAll('a[href^="#edit-"]'),function(a){a.addEventListener('click',function(e){e.preventDefault();var el=document.getElementById(a.getAttribute('href').slice(1));if(el)el.style.display=el.style.display==='block'?'none':'block';});});
    </script>`;
  return adminLayout({ title: "배너 관리", active: "banners", body, badges });
}

/* ================= 문의 (고객센터) =================
   오류 신고·베타 의견과 달리 **답이 돌아간다.** 그래서 목록이 아니라 «처리할 일 목록»으로 짠다:
   미답변이 위, 행을 누르면 원문과 답변 칸이 함께 뜬다. 답을 저장하면 앱에 안 읽은 배지가 붙는다. */
const INQ_CAT = { data: "학교정보", record: "기록", payment: "결제", account: "계정", bug: "오류", other: "기타" };
const INQ_CAT_CLS = { data: "pill-blue", record: "pill-test", payment: "pill-soon", account: "pill-blue", bug: "pill-expired", other: "pill-mut" };
const INQ_STATUS = { open: { ko: "미답변", cls: "pill-soon" }, answered: { ko: "답변함", cls: "pill-active" }, closed: { ko: "종료", cls: "pill-mut" } };

export function adminInquiriesPage(items, { q = "", status = "" } = {}, badges) {
  const list = items || [];
  const stOf = (s) => INQ_STATUS[s] || INQ_STATUS.open;
  const rows = list.map((r, i) => `<div class="trow click" data-i="${i}"${r.status === "closed" ? ' style="opacity:.55"' : ""}>
    <span style="width:96px;font-size:13.5px;color:#6b7280" class="tnum">${fmtD(r.created_at)}</span>
    <span style="width:78px"><span class="pill ${INQ_CAT_CLS[r.category] || "pill-mut"}">${escapeHtml(INQ_CAT[r.category] || "기타")}</span></span>
    <span class="ell" style="flex:1;font-size:14px;font-weight:700">${escapeHtml(r.title)}</span>
    <span class="ell" style="width:120px;font-size:13.5px;color:#374151">${escapeHtml(r.parent_name || "(이름 없음)")}</span>
    <span style="width:78px"><span class="pill ${stOf(r.status).cls}">${stOf(r.status).ko}</span></span>
    <span style="width:70px;font-size:13.5px;color:#6b7280">${r.status === "answered" && !r.seen_at ? "안 읽음" : r.seen_at ? "읽음" : ""}</span>
  </div>`).join("");

  const open = list.filter((r) => r.status === "open").length;
  const FILTERS = [["", "전체"], ["open", "미답변"], ["answered", "답변함"], ["closed", "종료"]];
  const chips = FILTERS.map(([k, label]) =>
    `<a class="btn sm${k === status ? " pri" : ""}" href="/admin/inquiries?s=${k}${q ? `&q=${encodeURIComponent(q)}` : ""}">${label}</a>`).join("");

  const data = list.map((r) => ({
    id: r.id, date: fmtDT(r.created_at), cat: INQ_CAT[r.category] || "기타",
    title: r.title, body: r.body, answer: r.answer || "",
    parent: r.parent_name || "(이름 없음)", email: r.contact_email || "",
    child: r.child_nickname || "", meta: r.meta || "", status: r.status,
    answered: fmtDT(r.answered_at), seen: r.seen_at ? fmtDT(r.seen_at) : "",
  }));

  const body = `
    <div class="hrow"><div class="hleft"><h2 class="h2">문의</h2>
      <span class="sub">미답변 ${open} / 전체 ${list.length} · 미답변 우선</span></div>
      <form method="get" action="/admin/inquiries" class="search" style="width:220px"><span style="font-size:14px;color:#6b7280">🔍</span>
        <input type="hidden" name="s" value="${escapeHtml(status)}"><input name="q" value="${escapeHtml(q)}" placeholder="제목·내용·이름 검색"></form></div>
    <div style="display:flex;gap:6px;margin-bottom:12px">${chips}</div>
    <div class="card">
      <div class="thead"><span style="width:96px">접수일</span><span style="width:78px">종류</span><span style="flex:1">제목</span><span style="width:120px">보낸 사람</span><span style="width:78px">상태</span><span style="width:70px">읽음</span></div>
      <div class="adm-scroll" style="max-height:520px;overflow-y:auto" id="ibody">${rows || `<div class="empty">접수된 문의가 없습니다.</div>`}</div>
    </div>
    <div class="note">※ 답을 저장하면 앱에 「답변 도착」 배지가 뜹니다. 답을 고치면 읽음이 풀려 다시 알립니다.</div>
    <script>
      var INQ=${jsonAttr(data)};
      (function(){Array.prototype.slice.call(document.querySelectorAll('#ibody .trow[data-i]')).forEach(function(r){r.addEventListener('click',function(){inqModal(+r.getAttribute('data-i'));});});})();
      window.inqModal=function(i){var q=INQ[i];
        openModal('<div class="mh"><div><h3>'+esc(q.title)+'</h3><div class="sub">'+esc(q.cat)+' · '+esc(q.parent)+(q.child?' · 자녀 '+esc(q.child):'')+' · '+esc(q.date)+'</div></div><button class="x" onclick="closeModal()">✕</button></div>'
          +'<form method="post" action="/admin/inquiries/'+q.id+'/answer"><div class="mb">'
          +'<div style="white-space:pre-wrap;font-size:14px;line-height:1.6;color:#374151;background:#f9fafb;border-radius:8px;padding:12px;margin-bottom:12px">'+esc(q.body)+'</div>'
          +(q.meta?'<div class="sub" style="margin-bottom:10px;word-break:break-all">'+esc(q.meta)+'</div>':'')
          +(q.email?'<div class="krow" style="margin-bottom:10px"><span>회신 메일</span><b>'+esc(q.email)+'</b></div>':'')
          +'<label style="font-size:13.5px;color:#6b7280">답변<br><textarea class="btn" style="cursor:text;width:100%;min-height:120px;margin-top:4px;text-align:left" name="answer" required>'+esc(q.answer)+'</textarea></label>'
          +(q.answered!=='-'?'<div class="sub" style="margin-top:8px">답변 '+esc(q.answered)+(q.seen?' · 읽음 '+esc(q.seen):' · 아직 안 읽음')+'</div>':'')
          +'</div><div class="mf"><button type="submit" class="btn pri">답변 저장</button><span style="flex:1"></span>'
          +(q.status!=='closed'?'<button type="button" class="btn" onclick="closeInq('+q.id+')">종료</button>':'')+'</div></form>');
      };
      window.closeInq=function(id){uiConfirmCb('문의 종료','더 주고받을 것이 없으면 종료합니다. 사용자는 계속 볼 수 있습니다.',function(){postForm('/admin/inquiries/'+id+'/close');},'종료');};
    </script>`;
  return adminLayout({ title: "문의", active: "inquiries", body, badges });
}

/* ================= 대화 신고 (커뮤니티) =================
   앱에서는 신고 1건이면 **신고한 사람 눈에서만** 가려지고, 서로 다른 3명이 신고해야 모두에게서 내려간다.
   내려간 글은 여기서 **사람이 확인**한다 — 자동으로 지우지 않는다. 자동 삭제는 악용되고,
   확인할 자리가 없으면 그건 「신고 기능이 있다」고 말만 하는 것이다(구글 UGC 정책이 보는 지점).

   조치는 셋: 되살리기 / 완전 삭제 / 작성자 대화 정지.
   ⚠ 정지는 **대화만** 막는다. 급식·기록·서식은 돈 내고 쓰는 기능이라 같이 끊으면 환불 사유가 된다. */
export function adminCommunityPage(rows, bans, badges) {
  const list = rows || [];
  const body = `
    <div class="hleft"><h2 class="h2">대화 신고</h2>
      <span class="sub">신고 3건이면 자동으로 내려갑니다 · 내려간 글은 여기서 확인하고 처리해요</span></div>

    <div class="seclabel">🚩 신고된 대화 (${list.length}건)</div>
    <div class="card" style="margin-bottom:22px">
      <div class="adm-scroll" style="max-height:520px;overflow-y:auto">
      ${list.length ? list.map((r) => `
        <div style="display:flex;align-items:flex-start;gap:14px;padding:14px 18px;border-bottom:1px solid #f3f4f6${r.hidden ? "" : ";opacity:.72"}">
          <span class="pill ${r.hidden ? "pill-expired" : "pill-soon"}" style="flex-shrink:0">신고 ${r.reports}</span>
          <div style="flex:1;min-width:0">
            <div style="font-size:14px;color:#111827;line-height:1.5;word-break:break-all">${escapeHtml(r.body)}</div>
            <div class="sub" style="margin-top:4px">
              ${escapeHtml(r.school_name || "학교 미상")} ${escapeHtml(r.author_grade || "?")}학년 ${escapeHtml(r.author_class || "?")}반
              · ${escapeHtml(r.parent_name || "이름 없음")} · ${fmtDT(r.created_at)}
              ${r.hidden ? ` · <b style="color:#dc2626">내려감</b>` : ""}
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
            <button class="btn sm" onclick="restorePost(${r.id})">되살리기</button>
            <button class="btn sm" style="color:#dc2626" onclick="dropPost(${r.id})">삭제</button>
            <button class="btn sm" style="color:#b45309" onclick="banUser('${escapeHtml(r.owner_token)}')">작성자 정지</button>
          </div>
        </div>`).join("")
      : `<div class="empty">신고된 대화가 없습니다.</div>`}
      </div>
    </div>

    <div class="seclabel">⛔ 대화 정지 중 (${(bans || []).length}명)</div>
    <div class="card">
      ${(bans || []).length ? (bans || []).map((b) => `
        <div class="trow" style="align-items:center">
          <span class="ell" style="flex:1;font-size:14px;font-weight:700">${escapeHtml(b.parent_name || "(이름 없음)")}
            <span class="code">${escapeHtml(String(b.owner_token).slice(0, 8))}</span></span>
          <span style="width:150px;font-size:13.5px;color:#6b7280">${b.until ? fmtD(b.until) + "까지" : "무기한"}</span>
          <span class="ell" style="width:160px;font-size:13.5px;color:#6b7280">${escapeHtml(b.reason || "")}</span>
          <form method="post" action="/admin/community/unban" style="display:inline">
            <input type="hidden" name="owner_token" value="${escapeHtml(b.owner_token)}">
            <button class="btn sm" style="border:none;color:#2563eb;background:none">풀기</button>
          </form>
        </div>`).join("")
      : `<div class="empty">정지 중인 사용자가 없습니다.</div>`}
    </div>

    <div class="note">※ 정지는 <b>대화만</b> 막습니다. 급식·시간표·기록·서식은 그대로 쓸 수 있어요 — 유료 기능을 같이 끊으면 환불 사유가 됩니다.</div>

    <script>
      window.restorePost=function(id){uiConfirmCb('되살리기','신고를 무시하고 이 대화를 다시 보이게 합니다.',function(){postForm('/admin/community/'+id+'/restore');},'되살리기');};
      window.dropPost=function(id){uiConfirmCb('완전 삭제','이 대화를 영구히 지웁니다. 되돌릴 수 없습니다.',function(){postForm('/admin/community/'+id+'/delete');},'삭제',true);};
      window.banUser=function(tok){uiConfirmCb('작성자 대화 정지','이 사람의 <b>대화 쓰기</b>를 7일간 막습니다. 급식·기록 같은 다른 기능은 그대로예요.',function(){postForm('/admin/community/ban',{owner_token:tok,days:'7'});},'7일 정지',true);};
    </script>`;
  return adminLayout({ title: "대화 신고", active: "flags", body, badges });
}

// ================= 오류 신고 / 베타 의견 (공통 큐 레이아웃) =================
function catClass(cat) {
  const map = { "급식": "pill-soon", "시간표": "pill-blue", "학급수": "pill-blue", "학생수": "pill-blue", "학사일정": "pill-test", "버그": "pill-expired", "불편·버그": "pill-expired", "기능 제안": "pill-blue", "기능제안": "pill-blue", "불편": "pill-soon", "칭찬": "pill-active" };
  return map[cat] || "pill-mut";
}
function queuePage({ title, active, sub, items, isReports, badges }) {
  const rows = (items || []).map((r) => {
    const done = r.status !== "open";
    const meta = `${fmtDT(r.created_at)}${r.school_name ? " · " + escapeHtml(r.school_name) : ""}`;
    const resolveAction = isReports ? `/admin/reports/${r.id}/resolve` : `/admin/feedback/${r.id}/resolve`;
    return `<div style="display:flex;align-items:flex-start;gap:14px;padding:14px 18px;border-bottom:1px solid #f3f4f6${done ? ";opacity:.6" : ""}">
      <span class="pill ${catClass(r.category)}" style="flex-shrink:0">${escapeHtml(r.category || "기타")}</span>
      <div style="flex:1;min-width:0"><div style="font-size:14px;color:#374151;line-height:1.5">${escapeHtml(r.message)}</div><div class="sub" style="margin-top:3px">${meta}</div></div>
      <span class="pill ${done ? "pill-mut" : "pill-soon"}">${done ? "처리됨" : "미처리"}</span>
      <div style="display:flex;align-items:center;gap:10px">
        ${isReports && r.school_slug ? `<a class="btn sm" style="border:none;color:#6b7280" href="/school/${encodeURIComponent(r.school_slug)}/?tab=overview" target="_blank">화면 보기 ↗</a>` : ""}
        ${done ? "" : `<form method="post" action="${resolveAction}" style="display:inline"><button class="btn sm" style="border:none;background:none;color:#2563eb;padding:2px 4px">처리완료</button></form>`}
      </div>
    </div>`;
  }).join("");
  const body = `
    <div class="hleft"><h2 class="h2">${title}</h2><span class="sub">${sub}</span></div>
    <div class="card"><div class="adm-scroll" style="max-height:520px;overflow-y:auto">${rows || `<div class="empty">${isReports ? "접수된 신고가 없습니다." : "접수된 의견이 없습니다."}</div>`}</div></div>`;
  return adminLayout({ title, active, body, badges });
}
export function adminReportsPage(reports, badges) {
  const open = (reports || []).filter((r) => r.status === "open").length;
  return queuePage({ title: "오류 신고", active: "reports", sub: `학교정보 오류 제보 · 미처리 ${open} / 전체 ${(reports || []).length} · 미처리 우선`, items: reports, isReports: true, badges });
}
export function adminFeedbackPage(items, badges) {
  const open = (items || []).filter((r) => r.status === "open").length;
  return queuePage({ title: "베타 의견", active: "feedback", sub: `서비스 전반 의견 · 미처리 ${open} / 전체 ${(items || []).length} · 미처리 우선`, items, isReports: false, badges });
}


/* ================= 데이터 (2026-07-28) =================
   표를 골라서 보고 **넣고·고치고·지운다.** 화면마다 전용 편집기를 만들면
   표가 늘 때마다 화면을 또 만들어야 해서, 표 이름만 바꿔 쓰는 한 판으로 만들었다.

   ⚠ 안전장치 (실서버 D1 을 직접 건드리는 화면이다)
     ① 표 이름은 **화이트리스트**로만 받는다. 넘어온 문자열을 SQL 에 그대로 넣지 않는다
     ② 컬럼도 PRAGMA 로 읽은 실제 목록과 대조한 것만 쓴다
     ③ 지우기·고치기는 **id 하나**만 대상으로 한다. WHERE 없는 UPDATE/DELETE 를 만들 길이 없다
     ④ 지우기는 확인 창을 거친다 */
export function adminDataPage({ table, tables, cols, rows, total, page, per, q, msg, badges }) {
  const head = cols.map((c) => `<th>${escapeHtml(c.name)}</th>`).join("");
  const cell = (v) => {
    if (v == null) return `<span class="mut">·</span>`;
    const t = String(v);
    return escapeHtml(t.length > 60 ? t.slice(0, 60) + "…" : t);
  };
  const body = rows.length ? rows.map((r) => `
    <tr onclick='dEdit(${jsonAttr(r)})' style="cursor:pointer">
      ${cols.map((c) => `<td>${cell(r[c.name])}</td>`).join("")}
    </tr>`).join("") : `<tr><td colspan="${cols.length || 1}" class="mut" style="padding:22px;text-align:center">없음</td></tr>`;

  const pages = Math.max(1, Math.ceil(total / per));
  const pageLink = (n, label) =>
    `<a class="btn${n === page ? " pri" : ""}" href="/admin/data?t=${encodeURIComponent(table)}&p=${n}&q=${encodeURIComponent(q || "")}">${label}</a>`;

  return adminLayout({ title: "데이터", active: "data", badges, body: `
    ${msg ? `<div class="note ok">${escapeHtml(msg)}</div>` : ""}
    <form class="row" method="get" action="/admin/data" style="gap:8px;align-items:center;flex-wrap:wrap">
      <select name="t" onchange="this.form.submit()" class="inp" style="max-width:220px">
        ${tables.map((t) => `<option value="${escapeHtml(t)}"${t === table ? " selected" : ""}>${escapeHtml(t)}</option>`).join("")}
      </select>
      <input class="inp" name="q" value="${escapeHtml(q || "")}" placeholder="아무 칸이나 검색" style="max-width:260px">
      <button class="btn pri" type="submit">찾기</button>
      <button class="btn" type="button" onclick="dNew()">＋ 새로 넣기</button>
      <span class="mut">${total.toLocaleString("ko-KR")}행 · ${page}/${pages}쪽</span>
    </form>

    <div class="tblwrap" style="margin-top:14px;overflow:auto">
      <table class="tbl"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    </div>
    <p class="mut" style="margin-top:8px">줄을 누르면 고치거나 지울 수 있어요.</p>

    <div class="row" style="gap:6px;margin-top:12px">
      ${page > 1 ? pageLink(page - 1, "‹ 이전") : ""}
      ${page < pages ? pageLink(page + 1, "다음 ›") : ""}
    </div>

    <script>
      var DTABLE = ${jsonAttr(table)};
      var DCOLS = ${jsonAttr(cols)};
      function dForm(row){
        var isNew = !row;
        var h = '<h3 style="margin:0 0 4px">' + (isNew ? '새로 넣기' : '고치기') + ' · ' + esc(DTABLE) + '</h3>';
        h += '<form method="post" action="/admin/data/save">';
        h += '<input type="hidden" name="t" value="' + esc(DTABLE) + '">';
        h += '<input type="hidden" name="mode" value="' + (isNew ? 'insert' : 'update') + '">';
        if (!isNew) h += '<input type="hidden" name="id" value="' + esc(row.id) + '">';
        DCOLS.forEach(function(c){
          var v = row ? (row[c.name] == null ? '' : row[c.name]) : '';
          // id·자동값은 새로 넣을 때 비워둔다(SQLite 가 매긴다)
          var lock = (c.name === 'id' && !isNew);
          h += '<label class="fl">' + esc(c.name) + ' <span class="mut">' + esc(c.type || '') + (c.notnull ? ' · 필수' : '') + '</span></label>';
          h += '<input class="inp" name="f_' + esc(c.name) + '" value="' + esc(v) + '"' + (lock ? ' readonly' : '') + '>';
        });
        h += '<div class="row" style="margin-top:14px;gap:8px">';
        if (!isNew) h += '<button class="btn dng" type="button" onclick="dDel(' + esc(row.id) + ')">지우기</button>';
        h += '<button class="btn" type="button" onclick="closeModal()">취소</button>';
        h += '<button class="btn pri" type="submit">저장</button></div></form>';
        openModal(h);
      }
      function dNew(){ dForm(null); }
      function dEdit(row){ dForm(row); }
      function dDel(id){
        uiConfirmCb('이 줄을 지울까요?', DTABLE + ' · id ' + id + ' — 되돌릴 수 없습니다.', function(){
          postForm('/admin/data/del', { t: DTABLE, id: id });
        }, '지우기', true);
      }
    </script>` });
}
