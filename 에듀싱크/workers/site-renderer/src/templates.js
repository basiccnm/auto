// 아이서랍(구 에듀싱크) 무료 공개 페이지 템플릿 — Claude Design "에듀싱크 학교 상세.dc.html" 이식(2026-07-12).
// 서버 렌더링(Cloudflare Worker)이라 디자인의 클라이언트 상태(DCLogic)는 링크/쿼리파라미터/최소 JS로 대체.
// 결제 미연동이라 공개 페이지는 항상 "무료(비회원)" 버전 렌더 — 시간표·학사일정 잠금, 급식 당일만.

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---- 공통 색/헬퍼 ----
const C = {
  ink: "#16233B", inkSoft: "#2B3648", muted: "#8A94A6", muted2: "#6B7688",
  green: "#2E7D5B", greenDark: "#256A4C", greenBg: "#E7F1EC", greenBd: "#CFE6DA",
  bg: "#F3F5F8", card: "#fff", border: "#E6E9EF",
};
// 학교 표준 서식 기능 스위치 — 2026-07-19 내림(지시서 v4 7절).
// 학교마다 양식이 달라 우리가 제공한 서식이 반려될 수 있어(오사용 리스크) 노출만 껐다.
// forms.js·/forms 라우트·핸들러는 그대로 살아 있으므로 true로 바꾸면 즉시 복구된다.
// 대신 학교 상세에 "학교 홈페이지 바로가기" 카드가 그 자리를 채운다.
const FEATURE_FORMS = false;

const EVENT_COLORS = {
  "방학": ["#2E7D5B", "#E7F1EC"],
  "공휴일": ["#C0392B", "#FBE9E7"],
  "학사": ["#2A4A7F", "#EAF1FA"],
  "행사": ["#A9761B", "#FBF1DC"],
};

// 이달의 행사 — 학사일정 API에 중요도 필드가 없어 키워드로 중요 일정 자동 분류(§지시서).
// "토요휴업일"처럼 매주 반복되는 정기 휴업일은 알림 가치 없어 제외.
const IMPORTANT_EVENT_KEYWORDS = [
  ["방학·개학", "🏖️", ["방학식", "개학식", "종업식", "방학선언"]], // 단순 방학 "기간"은 제외 — 식(式)만
  ["시험", "📝", ["중간고사", "기말고사", "지필평가", "학력평가", "고사", "시험"]],
  ["입학·졸업", "🎓", ["입학식", "졸업식"]],
  ["체험학습", "🚌", ["수학여행", "현장학습", "체험학습", "소풍", "수련활동", "수련회"]],
  ["행사", "🎉", ["운동회", "학예회", "축제", "발표회", "체육대회", "한마당"]],
  ["참여수업", "🙋", ["공개수업", "학부모공개", "참여수업", "수업공개", "공개 수업", "학부모 공개"]],
  ["개교기념", "🏫", ["개교기념"]],
  ["재량휴업", "🏠", ["재량휴업"]],
  ["상담", "💬", ["학부모상담", "상담주간", "학부모 상담"]],
];
// 중요 일정만 골라내는 단일 기준(타임라인 목록·이달의 행사·개요 카드에서 공통 사용).
// 토요휴업일과 단순 방학 "기간"은 완전히 제외, 공휴일은 휴업유형으로 판별.
function classifyImportantEvent(name, closureType) {
  const n = name || "";
  if (n.includes("토요휴업일")) return null; // 매주 반복 정기휴업 제외
  if ((closureType || "").includes("공휴일")) return { category: "공휴일", icon: "🎌" };
  for (const [cat, icon, kws] of IMPORTANT_EVENT_KEYWORDS) {
    if (kws.some((k) => n.includes(k))) return { category: cat, icon };
  }
  return null;
}
// schedules(오늘 이후 날짜순)에서 중요 일정만, 같은 이름은 최초 1건만.
function importantEventsFrom(schedules) {
  const seen = new Set();
  const out = [];
  for (const s of schedules || []) {
    const cls = classifyImportantEvent(s.event_name, s.closure_type);
    if (!cls || seen.has(s.event_name)) continue;
    seen.add(s.event_name);
    out.push({ ...s, ...cls });
  }
  return out;
}

// ---- 학사일정 탭: 월별 행사 달력. yearSchedules(올해 전체)를 클라이언트에 통째로 넘겨
// 이전/다음 달 이동 시 서버 재조회 없이 JS만으로 다시 그린다. 날짜 클릭 시 팝업(무료는 잠금 안내).
// 전국 공통 고정 일정 — 학교 학사일정(NEIS)에 없거나 학교마다 표기가 제각각이라, 모든 학교 달력에
// 강제로 표시해야 하는 국가 단위 일정. 매년 확정 발표되면 여기만 갱신하면 전 학교에 반영된다.
// (수능일 출처: 교육부/정책브리핑 — 2027학년도 수능 = 2026-11-19 목)
const NATIONAL_EVENTS = {
  "20261119": "🎓 수능 (2027학년도 대학수학능력시험)",
};

function eventCalendar(yearSchedules, todayYmd, paid, regUrl, personalEvents, editCtx, vapidPublic) {
  // 학사일정 달력 — 모바일 가독성 우선(크게) + 달력 아래 "읽을 수 있는 일정 목록" + 내 일정 추가/삭제(유료).
  // 날짜별 학교 이벤트: names(그날 전체) / important(주요 일정 여부) / holiday(공휴일). 토요휴업일만 제외.
  const dayInfo = {};
  for (const s of yearSchedules || []) {
    const name = s.event_name || "";
    if (name.includes("토요휴업일")) continue; // 매주 반복 노이즈 제외(토요일은 색으로 이미 구분)
    const info = dayInfo[s.event_date] || (dayInfo[s.event_date] = { holidayName: null, names: [], important: false });
    const nm = escapeHtml(name);
    // 방학 "기간"(여름방학 등)은 붉은 강조 대신 연한 "방학" 표시로 — 방학달에도 달력이 안 비게(2026-07-18).
    // 무료는 연한 음영만(이름 잠금), 유료는 방학 이름 노출.
    if (name.includes("방학") && !name.includes("식")) { info.vacation = true; if (!info.vacName) info.vacName = nm; continue; }
    // 공휴일명은 names(셀 필)와 분리 — 셀은 날짜 숫자 오른쪽에 빨간 이름으로 표시, 상세 헤더에도 표시.
    if ((s.closure_type || "").includes("공휴일")) { if (!info.holidayName) info.holidayName = nm; continue; }
    if (!info.names.includes(nm)) info.names.push(nm);
    const cls = classifyImportantEvent(name, s.closure_type);
    if (cls && cls.category !== "공휴일") info.important = true;
  }
  // 전국 공통 고정 일정(수능 등)을 모든 학교 달력에 주입 — 학교 무관하게 ★ 강조로 표시.
  // national=true인 이름은 무료 사용자에게도 노출한다(유료 잠금 대상인 학교 일정과 달리 국가 공통 정보).
  for (const [date, label] of Object.entries(NATIONAL_EVENTS)) {
    const info = dayInfo[date] || (dayInfo[date] = { holidayName: null, names: [], important: false });
    info.nationalNames = info.nationalNames || [];
    const nm = escapeHtml(label);
    if (!info.nationalNames.includes(nm)) info.nationalNames.push(nm);
    if (!info.names.includes(nm)) info.names.push(nm);
    info.important = true;
  }
  // 내 일정(개인 이벤트): 날짜 → [{id,label}].
  const mine = {};
  for (const e of personalEvents || []) {
    (mine[e.event_date] = mine[e.event_date] || []).push({ id: e.id, label: escapeHtml(e.label), detail: escapeHtml(e.detail || ""), remind_at: e.remind_at || "" });
  }
  const dataJson = JSON.stringify(dayInfo).replace(/</g, "\\u003c");
  const mineJson = JSON.stringify(mine).replace(/</g, "\\u003c");
  const initYear = Number((todayYmd || "").slice(0, 4)) || new Date().getFullYear();
  const initMonth = Number((todayYmd || "").slice(4, 6)) || 1;
  const canEdit = !!(paid && editCtx && editCtx.childId);

  return `
  <div id="calCapture" style="background:#fff;border:1px solid ${C.border};border-radius:18px;padding:14px 12px 16px;margin-bottom:12px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding:0 4px">
      <button type="button" id="calPrev" style="width:38px;height:38px;border-radius:11px;border:1px solid ${C.border};background:#fff;color:${C.inkSoft};font-size:19px;font-weight:800;cursor:pointer">‹</button>
      <span id="calLabel" style="font-size:clamp(17px, 14.5px + 0.7vw, 20px);font-weight:800;color:${C.ink}"></span>
      <button type="button" id="calNext" style="width:38px;height:38px;border-radius:11px;border:1px solid ${C.border};background:#fff;color:${C.inkSoft};font-size:19px;font-weight:800;cursor:pointer">›</button>
    </div>
    <div id="calGrid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px"></div>
    <div style="margin-top:12px;display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:11px;color:${C.muted};padding:0 4px">
      <span style="background:${C.greenBg};color:${C.greenDark};border:1.5px solid #E23B34;border-radius:3px;padding:1px 6px;font-weight:700"><span style="color:#F5A623">★</span> 학교 일정</span>
      <span style="background:#EFEAFB;color:#6B4E9E;border-radius:3px;padding:1px 6px;font-weight:700">내 일정</span>
      <span style="color:#E23B34;font-weight:800;background:#FBE9E7;border-radius:3px;padding:1px 6px">공휴일(빨간 글씨)</span>
      <span style="color:${C.muted}">· 날짜를 누르면 상세·추가</span>
    </div>
  </div>
  <button type="button" onclick="captureImg('calCapture','학사일정')" style="width:100%;padding:12px;border:1px solid ${C.border};border-radius:12px;background:#fff;color:${C.ink};font-size:13.5px;font-weight:800;cursor:pointer;font-family:inherit;margin-bottom:12px">🖼️ 이 달 일정 이미지로 저장</button>

  <!-- 날짜 클릭 시 화면 중앙에 뜨는 팝업: 그날 일정 보기 + 내 일정 추가, 일정 이름 클릭 시 하단에서 상세내용 입력 -->
  <div id="calModal" style="display:none;position:fixed;inset:0;z-index:1000;background:rgba(15,26,48,.5);align-items:center;justify-content:center;padding:16px;box-sizing:border-box">
    <div style="background:#fff;width:100%;max-width:460px;border-radius:20px;padding:18px 18px 20px;max-height:82vh;overflow-y:auto;box-shadow:0 12px 40px rgba(0,0,0,.28);-webkit-overflow-scrolling:touch">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;gap:10px">
        <div id="calModalHead" style="flex:1;min-width:0;font-size:clamp(17px, 15px + 0.5vw, 20px);font-weight:800;color:${C.ink};line-height:1.3"></div>
        <button type="button" id="calModalClose" style="flex:none;width:36px;height:36px;border-radius:50%;border:none;background:#F1F3F6;color:${C.muted};font-size:18px;font-weight:800;cursor:pointer">✕</button>
      </div>
      <div id="calModalBody"></div>
      ${canEdit ? `<div id="calFoot" style="margin-top:14px;padding-top:14px;border-top:1px dashed ${C.border}"></div>` : ""}
    </div>
  </div>

  <script>(function(){
    var DATA=${dataJson}, MINE=${mineJson}, PAID=${paid ? "true" : "false"}, CANEDIT=${canEdit ? "true" : "false"};
    var REG=${JSON.stringify(regUrl)}, TODAY=${JSON.stringify(todayYmd || "")}, CHILD=${JSON.stringify(editCtx && editCtx.childId ? String(editCtx.childId) : "")};
    var VAPID=${JSON.stringify(vapidPublic || "")};
    // 이 기기 알림 구독 상태(브라우저 권한 기준). 켜져 있으면 알림 설정칸에 "알림 켜짐" 표시.
    function notifReady(){ return ('Notification' in window) && Notification.permission==='granted'; }
    function b64u8(b){ b=b.replace(/-/g,'+').replace(/_/g,'/'); var p='='.repeat((4-b.length%4)%4); var raw=atob(b+p); var a=new Uint8Array(raw.length); for(var i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i); return a; }
    async function enableNotif(){
      if(!('serviceWorker' in navigator)||!('PushManager' in window)){ alert('이 브라우저는 웹푸시를 지원하지 않아요. 아이폰은 홈 화면에 추가(설치) 후 다시 시도해 주세요.'); return false; }
      if(!VAPID){ alert('알림 설정이 준비되지 않았어요.'); return false; }
      try{
        var perm=await Notification.requestPermission();
        if(perm!=='granted'){ alert('알림 권한이 허용되지 않았어요. 브라우저 설정에서 허용해 주세요.'); return false; }
        var reg=await navigator.serviceWorker.register('/sw.js'); await navigator.serviceWorker.ready;
        var sub=await reg.pushManager.getSubscription();
        if(!sub){ sub=await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:b64u8(VAPID)}); }
        var r=await fetch('/api/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)});
        if(r.ok){ return true; } alert('알림 등록 저장에 실패했어요.'); return false;
      }catch(e){ alert('알림 켜기에 실패했어요: '+e); return false; }
    }
    // 알림 설정칸 안의 "이 기기 알림 켜기/켜짐" 표시. 안 켜져 있으면 켜기 버튼, 켜져 있으면 확인 표시.
    function renderNotifCtl(){
      var el=document.getElementById('calNotifCtl'); if(!el) return;
      if(notifReady()){ el.innerHTML='<div style="font-size:12px;font-weight:800;color:#2E7D5B">✅ 이 기기에서 알림 켜짐</div>'; return; }
      el.innerHTML='<button type="button" id="calNotifBtn" style="width:100%;padding:11px;border:1px solid #CDE7DA;border-radius:10px;background:#EAF6EF;color:#2E7D5B;font-size:13px;font-weight:800;cursor:pointer">🔔 이 기기에서 알림 켜기 <span style="font-weight:600;color:#5B9E7E">(먼저 켜야 받아요)</span></button>';
      document.getElementById('calNotifBtn').addEventListener('click',async function(){
        this.textContent='켜는 중…'; this.disabled=true;
        var ok=await enableNotif(); renderNotifCtl(); if(ok) { var b=document.getElementById('calNotifBtn'); if(b) b.textContent='✅ 켜짐'; }
      });
    }
    var RED='#E23B34', BLUE='#2A6FDB', GREEN='${C.green}', MINEC='#7C5CE0', STAR='#F5A623';
    var WD=['일','월','화','수','목','금','토'];
    var y=${initYear}, m=${initMonth};
    var sel='';           // 팝업으로 열려 있는 날(YYYYMMDD)
    var footId=null;      // 하단이 "상세 입력 모드"로 여는 내 일정 id(null이면 "새 일정 추가 모드")
    var grid=document.getElementById('calGrid'), label=document.getElementById('calLabel');
    var modal=document.getElementById('calModal'), mHead=document.getElementById('calModalHead'), mBody=document.getElementById('calModalBody');
    var foot=document.getElementById('calFoot');
    function pad(n){return String(n).padStart(2,'0');}
    function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
    function attr(s){return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}
    function findEv(id){ var a=MINE[sel]||[]; for(var i=0;i<a.length;i++) if(String(a[i].id)===String(id)) return a[i]; return null; }
    function renderGrid(){
      label.textContent=y+'년 '+m+'월';
      var first=new Date(y,m-1,1), startDow=first.getDay(), last=new Date(y,m,0).getDate();
      var html='';
      WD.forEach(function(w,wi){ var c=wi===0?RED:(wi===6?BLUE:'#9AA4B2'); html+='<div style="text-align:center;font-size:13px;font-weight:800;color:'+c+';padding:6px 0">'+w+'</div>'; });
      for(var i=0;i<startDow;i++) html+='<div></div>';
      for(var d=1;d<=last;d++){
        var ymd=''+y+pad(m)+pad(d);
        var info=DATA[ymd], hasSchool=info&&info.names&&info.names.length, isHoliday=info&&!!info.holidayName, hasMine=MINE[ymd]&&MINE[ymd].length, isVac=info&&info.vacation;
        var dow=new Date(y,m-1,d).getDay(), isToday=(ymd===TODAY);
        var numColor=(isHoliday||dow===0)?RED:(dow===6?BLUE:'${C.ink}');
        // 학교 자체 일정(방학식·운동회 등)이 있는 날은 셀을 빨간 테두리로 강조 + 날짜 옆 노란 ★.
        // 공휴일은 "빨간 글씨"라 서로 구분된다(테두리=학교일정 / 글씨=공휴일).
        // 오늘은 초록 테두리 + 연한 초록 배경 — 테두리만으론 회색과 구분이 안 돼(#CFE6DA가 너무 창백)
        // 진한 초록(C.green)과 배경을 함께 준다. 학교일정과 겹치면 빨간 테두리가 우선(더 중요한 정보).
        var ring=hasSchool?'1.5px solid '+RED:(isToday?'2px solid '+GREEN:(isVac?'1px solid #F0E3C8':'1px solid #EEF0F3'));
        var cellBg=(isToday&&!hasSchool)?'${C.greenBg}':(isVac&&!hasSchool?'#FBF6EC':'#fff');
        // 상단: 날짜 숫자(왼쪽) + 공휴일 이름(숫자 오른쪽, 빨강). 학교/내 일정은 아래에 필로.
        var pills=[];
        if(hasSchool && PAID) info.names.forEach(function(nm){ pills.push({t:nm, bg: info.important?'#FBF1DC':'${C.greenBg}', c: info.important?'#A9761B':'${C.greenDark}'}); });
        else if(hasSchool && !PAID){
          // 무료: 학교 일정 이름은 가리되(잠금), 국가 공통 일정(수능 등)은 그대로 이름 노출.
          (info.nationalNames||[]).forEach(function(nm){ pills.push({t:nm, bg:'#FBF1DC', c:'#A9761B'}); });
          var schoolOnly = info.names.filter(function(nm){ return (info.nationalNames||[]).indexOf(nm)<0; });
          if(schoolOnly.length) pills.push({t:'학교 일정', bg:'${C.greenBg}', c:'${C.greenDark}'});
        }
        if(isVac) pills.push({t:'방학중', bg:'#FBF1DC', c:'#A9761B'}); // 방학중: 무료·유료 모두 표시
        if(hasMine) MINE[ymd].forEach(function(ev){ pills.push({t:ev.label, bg:'#EFEAFB', c:'#6B4E9E'}); });
        var shown=pills.slice(0,2), more=pills.length-shown.length;
        var pillHtml=shown.map(function(p){ return '<div style="font-size:10.5px;line-height:1.3;font-weight:700;background:'+p.bg+';color:'+p.c+';border-radius:4px;padding:2px 4px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left">'+p.t+'</div>'; }).join('');
        if(more>0) pillHtml+='<div style="font-size:10px;color:${C.muted};font-weight:700;margin-top:2px;text-align:left;padding-left:3px">+'+more+'개</div>';
        var topRow='<div style="display:flex;align-items:baseline;gap:2px">'
          +'<span style="flex:none;font-size:17px;font-weight:'+((hasSchool||hasMine||isHoliday)?'800':'700')+';color:'+numColor+';line-height:1">'+d+'</span>'
          +(hasSchool?'<span style="flex:none;font-size:10px;font-weight:900;color:'+STAR+';line-height:1">★</span>':'')
          +(isHoliday?'<span style="flex:1;min-width:0;font-size:9.5px;font-weight:800;color:'+RED+';line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+info.holidayName+'</span>':'')
          +'</div>';
        html+='<div class="calDay" data-ymd="'+ymd+'" style="min-height:90px;display:flex;flex-direction:column;padding:6px 4px;border-radius:11px;border:'+ring+';background:'+cellBg+';cursor:pointer;overflow:hidden">'
          +topRow+pillHtml+'</div>';
      }
      grid.innerHTML=html;
      grid.querySelectorAll('.calDay').forEach(function(c){ c.addEventListener('click',function(){ openDay(c.dataset.ymd); }); });
    }
    // 날짜 클릭 → 팝업 열기(항상 새 일정 추가 모드로 시작)
    function openDay(ymd){ sel=ymd; footId=null; fillModal(); modal.style.display='flex'; document.body.style.overflow='hidden'; }
    function closeDay(){ modal.style.display='none'; document.body.style.overflow=''; sel=''; footId=null; }
    function fillModal(){
      if(!sel) return;
      var d=new Date(+sel.slice(0,4),+sel.slice(4,6)-1,+sel.slice(6,8));
      var di=DATA[sel], mi=MINE[sel]||[], rows=[];
      var dowc=((di&&di.holidayName)||d.getDay()===0)?RED:(d.getDay()===6?BLUE:'${C.muted}');
      mHead.innerHTML=Number(sel.slice(4,6))+'월 '+Number(sel.slice(6,8))+'일 <span style="font-size:.8em;font-weight:700;color:'+dowc+'">('+WD[d.getDay()]+')</span>'
        +((di&&di.holidayName)?' <span style="font-size:.78em;font-weight:800;color:'+RED+'">🎌 '+di.holidayName+'</span>':'');
      // 공휴일은 헤더(요일 옆)에만 표시하고 목록에는 중복 노출하지 않음.
      // 학교 일정 행(유료만 이름 공개)
      // 국가 공통 일정(수능 등)은 유·무료 모두 이름 공개.
      (di&&di.nationalNames||[]).forEach(function(nm){ rows.push('<div style="display:flex;align-items:flex-start;gap:9px;padding:11px 0;border-bottom:1px solid #F4F6F8"><span style="flex:none;font-size:16px">🏫</span><span style="flex:1;font-size:16px;color:${C.ink};line-height:1.45;font-weight:600"><span style="color:'+STAR+';font-weight:800">★ </span>'+nm+'</span></div>'); });
      var schoolNames=(di&&di.names||[]).filter(function(nm){ return (di.nationalNames||[]).indexOf(nm)<0; });
      if(schoolNames.length){
        if(!PAID){ rows.push('<div style="padding:11px 0;font-size:15px;color:${C.muted}">🔒 학교 일정 이름은 <a href="'+REG+'" style="color:${C.green};font-weight:700">자녀 등록</a> 후 확인할 수 있어요.</div>'); }
        else schoolNames.forEach(function(nm){ rows.push('<div style="display:flex;align-items:flex-start;gap:9px;padding:11px 0;border-bottom:1px solid #F4F6F8"><span style="flex:none;font-size:16px">'+(di.important?'🏫':'📅')+'</span><span style="flex:1;font-size:16px;color:${C.ink};line-height:1.45;font-weight:500">'+(di.important?'<span style="color:'+STAR+';font-weight:800">★ </span>':'')+nm+'</span></div>'); });
      }
      // 방학 기간: "방학중" 표시(모두 동일).
      if(di&&di.vacation){ rows.push('<div style="display:flex;align-items:flex-start;gap:9px;padding:11px 0;border-bottom:1px solid #F4F6F8"><span style="flex:none;font-size:16px">🏖️</span><span style="flex:1;font-size:16px;color:${C.ink};line-height:1.45;font-weight:500">방학중</span></div>'); }
      // 내 일정 행 — 이름을 누르면 하단이 그 일정의 "상세 입력"으로 열린다. 상세내용이 있으면 아래에 작게 표시.
      mi.forEach(function(ev){
        var active=String(ev.id)===String(footId);
        rows.push('<div class="calMine" data-id="'+ev.id+'" style="display:flex;align-items:flex-start;gap:9px;padding:11px 0;border-bottom:1px solid #F4F6F8;cursor:'+(CANEDIT?'pointer':'default')+';'+(active?'background:#F7F3FF;border-radius:9px;padding:11px 8px;':'')+'">'
          +'<span style="flex:none;font-size:16px">📌</span>'
          +'<span style="flex:1;min-width:0"><span style="font-size:16px;color:${C.ink};line-height:1.4;font-weight:600">'+ev.label+'</span>'
          +(ev.detail?'<span style="display:block;font-size:13.5px;color:${C.muted};line-height:1.4;margin-top:2px;white-space:pre-wrap">'+ev.detail+'</span>':(CANEDIT&&!active?'<span style="display:block;font-size:12.5px;color:#B9AED6;margin-top:2px">눌러서 상세내용 입력 ›</span>':''))+'</span>'
          +(CANEDIT?'<button type="button" class="calDel" data-id="'+ev.id+'" style="flex:none;font-size:13px;font-weight:700;background:none;border:none;color:#C4808A;cursor:pointer;padding:2px 6px">삭제</button>':'')+'</div>');
      });
      mBody.innerHTML=rows.length?rows.join(''):'<div style="padding:18px 0;text-align:center;color:${C.muted};font-size:15px">이 날은 일정이 없어요.'+(CANEDIT?'<br>아래에서 일정을 추가해보세요.':'')+'</div>';
      if(CANEDIT){
        mBody.querySelectorAll('.calMine').forEach(function(r){ r.addEventListener('click',function(e){ if(e.target.classList.contains('calDel')) return; footId=r.dataset.id; renderFoot(); var t=foot.querySelector('#calFDetail'); if(t){ t.focus(); } }); });
        mBody.querySelectorAll('.calDel').forEach(function(b){ b.addEventListener('click',function(e){ e.stopPropagation(); delEvent(b.dataset.id); }); });
      }
      renderFoot();
    }
    // 하단: footId 없으면 "새 일정 추가", 있으면 그 일정의 "이름+상세내용" 입력(일정 추가창은 감춤).
    function renderFoot(){
      if(!CANEDIT) return;
      if(footId==null){
        foot.innerHTML='<div style="display:flex;gap:7px">'
          +'<input type="text" id="calAddLabel" maxlength="40" placeholder="일정 입력 (예: 가족여행)" style="flex:1;min-width:0;padding:13px;border:1px solid #DCD3EE;border-radius:11px;font-size:15px;font-family:inherit;box-sizing:border-box">'
          +'<button type="button" id="calAddBtn" style="flex:none;padding:13px 18px;border:none;border-radius:11px;background:#6B4E9E;color:#fff;font-size:15px;font-weight:800;cursor:pointer">추가</button></div>';
        var inp=foot.querySelector('#calAddLabel'), btn=foot.querySelector('#calAddBtn');
        btn.addEventListener('click',function(){ addEvent(inp.value); });
        inp.addEventListener('keydown',function(e){ if(e.key==='Enter'){ e.preventDefault(); addEvent(inp.value); } });
      } else {
        var ev=findEv(footId);
        if(!ev){ footId=null; return renderFoot(); }
        // 알림 프리필: remind_at(UTC ISO) → KST 날짜/시간. 없으면 이 일정 날짜 + 기본 08:00.
        var rDate=sel.slice(0,4)+'-'+sel.slice(4,6)+'-'+sel.slice(6,8), rTime='08:00';
        if(ev.remind_at){ var k=new Date(new Date(ev.remind_at).getTime()+9*3600000); rDate=k.getUTCFullYear()+'-'+pad(k.getUTCMonth()+1)+'-'+pad(k.getUTCDate()); rTime=pad(k.getUTCHours())+':'+pad(k.getUTCMinutes()); }
        foot.innerHTML='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:9px"><span style="font-size:13px;font-weight:800;color:#6B4E9E">📌 일정 상세</span>'
          +'<button type="button" id="calFClose" style="border:none;background:none;color:${C.muted};font-size:13px;font-weight:700;cursor:pointer;padding:2px 4px">＋ 새 일정</button></div>'
          +'<input type="text" id="calFLabel" maxlength="40" value="'+attr(ev.label)+'" style="width:100%;padding:12px;border:1px solid #DCD3EE;border-radius:11px;font-size:15px;font-weight:700;font-family:inherit;box-sizing:border-box;margin-bottom:8px">'
          +'<textarea id="calFDetail" maxlength="300" rows="3" placeholder="상세내용 (예: 제주도 여행 3인)" style="width:100%;padding:12px;border:1px solid #DCD3EE;border-radius:11px;font-size:15px;font-family:inherit;box-sizing:border-box;resize:vertical;line-height:1.5">'+esc(ev.detail||'')+'</textarea>'
          +'<div style="margin-top:12px;padding-top:12px;border-top:1px solid #EEE">'
          +'<label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="calFRemindOn" '+(ev.remind_at?'checked':'')+' style="width:17px;height:17px;accent-color:#6B4E9E"><span style="font-size:14px;font-weight:800;color:#6B4E9E">🔔 알림 받기</span></label>'
          +'<div id="calFRemindBox" style="display:'+(ev.remind_at?'flex':'none')+';gap:7px;margin-top:9px">'
          +'<input type="date" id="calFRemindDate" value="'+rDate+'" style="flex:1;min-width:0;padding:10px;border:1px solid #DCD3EE;border-radius:10px;font-size:14px;font-family:inherit;box-sizing:border-box">'
          +'<input type="time" id="calFRemindTime" value="'+rTime+'" style="flex:none;width:112px;padding:10px;border:1px solid #DCD3EE;border-radius:10px;font-size:14px;font-family:inherit;box-sizing:border-box">'
          +'</div>'
          +'<div id="calNotifCtl" style="margin-top:9px"></div>'
          +'<div style="margin-top:8px;font-size:11.5px;color:${C.muted};line-height:1.55;background:#FBFAFE;border:1px solid #EFEAFB;border-radius:9px;padding:9px 11px">ℹ️ 지정한 시각 무렵 알림이 도착해요(보통 1~2분 내). 단, <b>휴대폰이 꺼져 있거나 인터넷이 끊긴 경우</b> 늦게 오거나 오지 않을 수 있어요. 아이폰은 <b>홈 화면에 추가(앱 설치) 후 알림 허용</b>해야 받을 수 있습니다.</div>'
          +'</div>'
          +'<button type="button" id="calFSave" style="width:100%;margin-top:11px;padding:13px;border:none;border-radius:11px;background:#6B4E9E;color:#fff;font-size:15px;font-weight:800;cursor:pointer">저장</button>';
        foot.querySelector('#calFClose').addEventListener('click',function(){ footId=null; fillModal(); });
        renderNotifCtl();
        foot.querySelector('#calFRemindOn').addEventListener('change',function(){ foot.querySelector('#calFRemindBox').style.display=this.checked?'flex':'none'; });
        foot.querySelector('#calFSave').addEventListener('click',function(){
          var on=foot.querySelector('#calFRemindOn').checked;
          saveDetail(footId, foot.querySelector('#calFLabel').value, foot.querySelector('#calFDetail').value, on, foot.querySelector('#calFRemindDate').value, foot.querySelector('#calFRemindTime').value);
        });
      }
    }
    function addEvent(val){
      var lab=(val||'').trim(); if(!lab){ var i=foot.querySelector('#calAddLabel'); if(i) i.focus(); return; }
      fetch('/calendar/event/add',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({child_id:CHILD,date:sel,label:lab})})
        .then(function(r){return r.json();}).then(function(res){
          if(res&&res.ok){ (MINE[res.date]=MINE[res.date]||[]).push({id:res.id,label:esc(res.label),detail:''}); footId=res.id; renderGrid(); fillModal(); }
          else alert('추가 실패: '+((res&&res.error)||'오류'));
        });
    }
    function saveDetail(id, labVal, detVal, remindOn, rDate, rTime){
      var lab=(labVal||'').trim(); if(!lab){ return; }
      var det=(detVal||'').trim();
      var params={id:id,label:lab,detail:det};
      // 알림: 켜져 있고 날짜·시간이 있으면 remind_date(YYYYMMDD)+remind_time(HH:MM) 전송, 아니면 해제.
      if(remindOn && rDate && rTime){ params.remind_date=rDate.replace(/-/g,''); params.remind_time=rTime; }
      else { params.remind_off='1'; }
      fetch('/calendar/event/edit',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(params)})
        .then(function(r){return r.json();}).then(function(res){
          if(res&&res.ok){ var e=findEv(id); if(e){ e.label=esc(res.label); e.detail=esc(res.detail||''); e.remind_at=res.remind_at||''; } footId=null; renderGrid(); fillModal(); }
          else alert('저장 실패: '+((res&&res.error)||'오류'));
        });
    }
    function delEvent(id){
      uiConfirmCb('이 일정을 삭제할까요?', function(){
        fetch('/calendar/event/delete',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({id:id})})
          .then(function(r){return r.json();}).then(function(res){ if(res&&res.ok){ for(var k in MINE){ MINE[k]=(MINE[k]||[]).filter(function(e){return String(e.id)!==String(id);}); if(!MINE[k].length) delete MINE[k]; } if(String(footId)===String(id)) footId=null; renderGrid(); fillModal(); } else alert('삭제 실패'); });
      }, '삭제하기');
    }
    document.getElementById('calModalClose').addEventListener('click',closeDay);
    modal.addEventListener('click',function(e){ if(e.target===modal) closeDay(); }); // 바깥 탭하면 닫기
    document.getElementById('calPrev').addEventListener('click',function(){ m--; if(m<1){m=12;y--;} renderGrid(); });
    document.getElementById('calNext').addEventListener('click',function(){ m++; if(m>12){m=1;y++;} renderGrid(); });
    renderGrid();
  })();</script>`;
}

function normCoedu(v) {
  return (v || "").replace("남여", "남녀");
}
// 학교명이 이미 "…초등학교/중학교/고등학교"로 끝나 뱃지에 학교급 전체를 또 쓰면 중복 →
// 짧은 급 라벨로 표기(초등/중등/고등). 홈 필터칩과 동일 표기.
function shortKind(kind) {
  return { "초등학교": "초등", "중학교": "중등", "고등학교": "고등" }[kind] || kind || "";
}
// 학교명 줄바꿈 규칙(표시 전용, DB 미변경) — 두 줄로 넘어갈 때 학교급 접미사(초등학교/중학교/고등학교)
// 단위로 끊어지게 한다. 고유 이름과 접미사를 각각 nowrap으로 묶고 그 사이에만 <wbr>(줄바꿈 기회)을 둬서,
// 한 줄에 들어가면 안 끊고 넘칠 때만 접미사가 통째로 둘째 줄로 내려간다. 예: 서울숭미 / 초등학교.
const SCHOOL_KIND_SUFFIXES = ["초등학교", "중학교", "고등학교"];
function schoolNameHtml(name) {
  const n = (name || "").trim();
  for (const suf of SCHOOL_KIND_SUFFIXES) {
    if (n.length > suf.length && n.endsWith(suf)) {
      const prefix = n.slice(0, n.length - suf.length);
      return `<span style="white-space:nowrap">${escapeHtml(prefix)}</span><wbr><span style="white-space:nowrap">${escapeHtml(suf)}</span>`;
    }
  }
  return escapeHtml(n);
}
// 시간표 셀에서 긴 과목명이 지저분하게 줄바뀜되는 것 방지 — 자주 나오는 초등 과목만 축약.
// 편집 시엔 원래 전체 이름을 쓰도록 셀 data-full에 원본을 따로 보관한다.
const SUBJ_ABBR = { "슬기로운생활": "슬.생", "즐거운생활": "즐.생", "바른생활": "바.생", "안전한생활": "안전", "창의적체험활동": "창.체" };
function shortSubject(name) {
  if (!name) return "";
  if (SUBJ_ABBR[name]) return SUBJ_ABBR[name];
  if (name.includes("·")) return name.split("·").map((x) => escapeHtml(x)).join("<br>"); // 자율·자치활동 → 자율/자치활동 줄바꿈
  return escapeHtml(name);
}
// 학교급별 학년 범위(초1~6 / 중·고1~3). 자녀 등록·수정 드롭다운에 사용.
function maxGradeOf(kind) {
  return kind === "초등학교" ? 6 : 3;
}
const SELECT_STYLE = "flex:1;min-width:0;width:100%;padding:13px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px;background:#fff;color:#16233B;appearance:none;-webkit-appearance:none";
function gradeSelect(kind, name, selected, extraAttr = "") {
  const opts = ['<option value="">학년</option>']
    .concat(Array.from({ length: maxGradeOf(kind) }, (_, i) => i + 1)
      .map((g) => `<option value="${g}"${String(selected) === String(g) ? " selected" : ""}>${g}학년</option>`))
    .join("");
  return `<select name="${name}" required style="${SELECT_STYLE}" ${extraAttr}>${opts}</select>`;
}
// maxClass = 그 학년의 실제 학급수(모르면 15까지 폴백). 등록 폼은 학년 선택 후 JS가 다시 채우므로
// 여기선 초기 표기만 담당 — placeholder를 주면 "학년 먼저 선택" 상태로 비활성 렌더한다.
function classSelect(name, selected, extraAttr = "", maxClass = 15, placeholder = "") {
  if (placeholder) {
    return `<select name="${name}" style="${SELECT_STYLE}" disabled ${extraAttr}><option value="">${escapeHtml(placeholder)}</option></select>`;
  }
  const opts = ['<option value="">반</option>']
    .concat(Array.from({ length: Math.max(1, maxClass) }, (_, i) => i + 1)
      .map((c) => `<option value="${c}"${String(selected) === String(c) ? " selected" : ""}>${c}반</option>`))
    .join("");
  return `<select name="${name}" style="${SELECT_STYLE}" ${extraAttr}>${opts}</select>`;
}
function foundedYear(ymd) {
  return ymd && ymd.length >= 4 ? ymd.slice(0, 4) : null;
}
function fmtDate(ymd) {
  // YYYYMMDD -> MM.DD
  if (!ymd || ymd.length < 8) return escapeHtml(ymd || "");
  return `${ymd.slice(4, 6)}.${ymd.slice(6, 8)}`;
}
function kcalNum(calInfo) {
  if (!calInfo) return null;
  const m = String(calInfo).match(/([\d.]+)/);
  return m ? Math.round(Number(m[1])) : null;
}
function classifyEvent(name, closureType) {
  if ((name || "").includes("방학")) return "방학";
  if ((closureType || "").includes("공휴일")) return "공휴일";
  if ((closureType || "").includes("휴업")) return "학사";
  return "행사";
}
function ddayText(todayYmd, ymd) {
  if (!ymd || ymd.length < 8) return "";
  const t = new Date(`${todayYmd.slice(0, 4)}-${todayYmd.slice(4, 6)}-${todayYmd.slice(6, 8)}`);
  const e = new Date(`${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`);
  const diff = Math.round((e - t) / 86400000);
  return diff <= 0 ? "D-DAY" : `D-${diff}`;
}

// 전역 footer(전 페이지 공통) — 서비스소개·마이페이지·약관·개인정보 + 사업자정보.
function siteFooter() {
  const lnk = (href, t) => `<a href="${href}" style="color:rgba(255,255,255,.78)">${t}</a>`;
  return `<div style="background:#0F1A30;color:rgba(255,255,255,.55);padding:22px 22px 30px;font-size:11.5px;line-height:1.7">
    <div style="display:flex;flex-wrap:wrap;gap:10px 16px;font-weight:700">
      ${lnk("/about", "서비스 소개")} ${lnk("/mypage", "마이페이지")} ${lnk("/terms", "이용약관")} ${lnk("/privacy", "개인정보처리방침")}
    </div>
    <div style="margin-top:14px;color:rgba(255,255,255,.42);font-weight:500">
      상호 <b style="color:rgba(255,255,255,.6)">베이직씨엔엠</b> · 사업자등록번호 746-21-02507<br>
      대표자·주소·고객센터: (준비 중)<br>
      <span style="opacity:.85">ⓒ 2026 아이서랍 · NEIS·학교알리미 공공데이터 기반</span>
    </div>
  </div>`;
}

// 앱 디자인 톤에 맞춘 커스텀 확인 모달 — 네이티브 confirm() 대체(디자인 일관성 + 자동화 QA 도구가
// 네이티브 다이얼로그에서 멈추는 문제 해결). layout()에서 모든 페이지에 1회 주입한다.
// 사용법:
//   폼 제출:  <form ... onsubmit="return uiConfirm(event, '메시지')">
//   콜백:     uiConfirmCb('메시지', function(){ ...확인 시 실행... }[, '확인버튼라벨'])
//   안내만:   uiAlert('메시지')  — 확인 버튼 하나만(취소 없음). 입력값 안내에 사용.
function confirmModal() {
  return `<div id="uiConfirmModal" style="display:none;position:fixed;inset:0;z-index:200;background:rgba(15,25,45,.55);align-items:center;justify-content:center;padding:24px" onclick="if(event.target===this)uiConfirmClose()">
    <div style="background:#fff;border-radius:18px;padding:22px 20px;width:320px;max-width:100%;box-shadow:0 20px 50px rgba(0,0,0,.3)">
      <div id="uiConfirmMsg" style="font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:700;color:${C.ink};line-height:1.55;text-align:center;white-space:pre-line"></div>
      <div style="margin-top:20px;display:flex;gap:8px">
        <button type="button" id="uiConfirmNo" onclick="uiConfirmClose()" style="flex:1;padding:13px;border-radius:12px;background:#F0F2F5;border:none;color:${C.muted2};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:700;cursor:pointer;font-family:inherit">취소</button>
        <button type="button" id="uiConfirmYes" style="flex:1;padding:13px;border-radius:12px;background:${C.green};border:none;color:#fff;font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;cursor:pointer;font-family:inherit">확인</button>
      </div>
    </div>
  </div>
  <script>(function(){
    var m=document.getElementById('uiConfirmModal'), msg=document.getElementById('uiConfirmMsg'), yes=document.getElementById('uiConfirmYes'), no=document.getElementById('uiConfirmNo'), cb=null;
    window.uiConfirmClose=function(){ m.style.display='none'; cb=null; no.style.display=''; };
    window.uiConfirmCb=function(message, fn, yesLabel){ msg.textContent=message; yes.textContent=yesLabel||'확인'; no.style.display=''; cb=fn; m.style.display='flex'; };
    // 안내 전용 — 취소 버튼 숨기고 확인만. 브라우저 기본 검증 문구("목록에서 항목을 선택하세요") 대신 쓴다.
    window.uiAlert=function(message){ msg.textContent=message; yes.textContent='확인'; no.style.display='none'; cb=null; m.style.display='flex'; };
    window.uiConfirm=function(e, message, yesLabel){ e.preventDefault(); var form=e.target; window.uiConfirmCb(message, function(){ form.submit(); }, yesLabel); return false; };
    yes.addEventListener('click', function(){ var f=cb; window.uiConfirmClose(); if(f) f(); });
    document.addEventListener('keydown', function(e){ if(e.key==='Escape' && m.style.display==='flex') uiConfirmClose(); });
  })();</script>`;
}

// 공유 미리보기(OG) 기본값 — 카톡·페북 등이 링크를 카드로 보여줄 때 쓰는 값.
// og:image는 절대 URL이어야 해서 배포 도메인을 상수로 둔다(커스텀 도메인 붙이면 여기만 교체).
const SITE_ORIGIN = "https://eduthink-site-renderer.dndmotor1.workers.dev";
const OG_DEFAULT_DESC = "학교 이름만 검색하면 급식·시간표·학사일정을 한 곳에서. 자녀를 등록하면 우리 반 기준으로 매일 자동으로 챙겨드려요.";

// noShare: 공유 FAB를 빼는 페이지용. 목업의 업로드 FAB와 좌표(우하단)가 정확히 겹치고,
// 자녀 기록 화면은 애초에 남에게 공유할 성격이 아니다(개인정보 화면).
function layout({ title, body, dark, noFooter, desc, canonical, noShare }) {
  const ogDesc = desc || OG_DEFAULT_DESC;
  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<meta name="description" content="${escapeHtml(ogDesc)}">
<meta name="google-site-verification" content="ce6_IhdlrvMdGe99K-01PoYsmQ9ILrewt2TU-cYDiDI">
<meta name="naver-site-verification" content="46bf453d37e3f96c7b2ec03be8e9f8996ae4932d">
${canonical ? `<link rel="canonical" href="${escapeHtml(canonical)}">` : ""}
<meta property="og:type" content="website">
<meta property="og:site_name" content="아이서랍">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(ogDesc)}">
<meta property="og:image" content="${SITE_ORIGIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${escapeHtml(title)}">
<meta name="twitter:description" content="${escapeHtml(ogDesc)}">
<meta name="twitter:image" content="${SITE_ORIGIN}/og.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/icon-512.png">
<meta name="theme-color" content="#2E7D5B">
<link rel="manifest" href="/manifest.json">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
  *{box-sizing:border-box}
  /* 탭 전환 시 세로 스크롤바 유무가 바뀌며 중앙정렬이 좌우로 흔들리는 문제 방지 — 스크롤바 항상 확보 */
  html{overflow-y:scroll;scrollbar-gutter:stable}
  body{margin:0;background:#DEE1E7;font-family:"Pretendard","Pretendard Variable",system-ui,sans-serif;-webkit-font-smoothing:antialiased;color:${C.ink}}
  a{color:${C.green};text-decoration:none}
  /* 유동 확장 레이아웃(2026-07-13 원칙1): 모바일은 거의 꽉 채우고, 큰 화면일수록 컨테이너를 넓힘.
     모바일 ~480px 폭까지는 지금처럼 꽉, 태블릿 720px, 데스크톱 960px에서 상한. 무한정은 안 늘림. */
  .wrap{width:100%;max-width:480px;margin:0 auto;min-height:100vh;background:${dark ? "#132445" : C.bg};box-shadow:0 0 60px rgba(16,25,46,.12);position:relative;overflow:hidden}
  @media (min-width:768px){ .wrap{max-width:720px} }
  @media (min-width:1024px){ .wrap{max-width:960px} }
  .hscroll::-webkit-scrollbar{height:0;width:0;display:none}
  .hscroll{scrollbar-width:none}
  button,input,select{font-family:inherit}
</style>
</head>
<body>
<div class="wrap">
${body}
${noFooter ? "" : siteFooter()}
</div>
${noShare ? "" : shareFab()}
${captureScript()}
${confirmModal()}
</body>
</html>`;
}

// 전 페이지 공통 "공유하기" 플로팅 버튼 — Web Share(모바일 카톡·사진 등) → 없으면 링크 복사.
function shareFab() {
  return `<button type="button" onclick="__shareThis()" aria-label="이 페이지 공유하기" style="position:fixed;right:16px;bottom:18px;z-index:40;display:inline-flex;align-items:center;gap:6px;background:${C.green};color:#fff;border:none;border-radius:24px;padding:11px 15px;font-size:13px;font-weight:800;box-shadow:0 6px 18px rgba(46,125,91,.38);cursor:pointer;font-family:inherit">🔗 공유</button>
<script>window.__shareThis=function(){var u=location.href,t=document.title;if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});}else if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(u).then(function(){alert('링크가 복사됐어요!');},function(){prompt('이 링크를 복사하세요',u);});}else{prompt('이 링크를 복사하세요',u);}};</script>`;
}

// 시간표·학사일정 달력을 PNG 이미지로 저장/공유 — html2canvas를 클릭 시에만 지연 로드(평소 로드 비용 0).
function captureScript() {
  return `<script>
    window.__imgToast=function(msg){
      var t=document.createElement('div');
      t.textContent=msg;
      t.style.cssText='position:fixed;left:50%;bottom:88px;transform:translateX(-50%);z-index:1200;background:#16233B;color:#fff;font-size:13px;font-weight:700;padding:11px 18px;border-radius:22px;box-shadow:0 8px 24px rgba(0,0,0,.3)';
      document.body.appendChild(t);
      setTimeout(function(){ t.remove(); },2200);
    };
    window.captureImg=function(elId,name){
      var el=document.getElementById(elId); if(!el){ alert('저장할 화면을 찾지 못했어요.'); return; }
      function run(){
        window.html2canvas(el,{scale:2,backgroundColor:'#ffffff',useCORS:true,logging:false}).then(function(canvas){
          canvas.toBlob(function(blob){
            if(!blob){ alert('이미지 생성에 실패했어요.'); return; }
            var fname=(name||'이미지')+'.png';
            // 다운로드 폴백 — 공유 시트가 없거나(PC), 비동기 후라 사용자 제스처가 만료돼 공유가 거부돼도(모바일)
            // 파일이 반드시 남도록 한다. 예전엔 공유 실패를 삼켜서 "아무 일도 안 일어남"이었다.
            function dl(){
              var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=fname;
              document.body.appendChild(a); a.click(); document.body.removeChild(a);
              setTimeout(function(){ URL.revokeObjectURL(a.href); },1500);
              __imgToast('이미지를 저장했어요');
            }
            try{ var file=new File([blob],fname,{type:'image/png'});
              if(navigator.canShare&&navigator.canShare({files:[file]})){
                navigator.share({files:[file],title:name||''}).catch(function(){ dl(); }); return;
              }
            }catch(e){}
            dl();
          },'image/png');
        }).catch(function(){ alert('이미지 저장에 실패했어요. 잠시 후 다시 시도해 주세요.'); });
      }
      if(window.html2canvas){ run(); return; }
      var s=document.createElement('script'); s.src='https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
      s.onload=run; s.onerror=function(){ alert('이미지 저장 기능을 불러오지 못했어요(네트워크). 잠시 후 다시 시도해 주세요.'); };
      document.head.appendChild(s);
    };
  </script>`;
}

// ---- 광고 블록(디자인의 하드코딩 슬롯 이식; 추후 admin banners 테이블로 교체 가능) ----
// 베타 기간엔 실제 광고가 없어 "반응형 배너 슬롯" 플레이스홀더만 보이므로 전부 숨긴다.
// 광고 붙일 때 이 플래그만 false로 하면 전 페이지(홈·검색·학교상세)에서 한 번에 다시 켜진다.
const ADS_HIDDEN = true;
function ad(kind, onDark) {
  if (ADS_HIDDEN) return "";
  const dashLight = "border:1px dashed #CDD4DE;border-radius:14px;background:#F7F9FB";
  const dashDark = "border:1px dashed rgba(255,255,255,.2);border-radius:16px;background:rgba(255,255,255,.05)";
  if (kind === "adsense") {
    return `<div style="${onDark ? dashDark : dashLight};min-height:88px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;text-align:center;padding:16px">
      <span style="font-size:9px;font-weight:800;letter-spacing:.12em;color:${onDark ? "rgba(255,255,255,.4)" : "#AEB6C2"}">AD · GOOGLE ADSENSE</span>
      <span style="font-size:11.5px;color:${onDark ? "rgba(255,255,255,.35)" : "#B4BCC8"};font-weight:500">반응형 배너 슬롯 · 자동 크기</span>
    </div>`;
  }
  if (kind === "hagwon") {
    return `<a href="#" style="display:flex;border-radius:14px;background:linear-gradient(135deg,#1E7A8C,#155E82);color:#fff;padding:15px 16px;align-items:center;gap:12px">
      <div style="width:36px;height:36px;flex:none;border-radius:10px;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-size:clamp(18px, 15px + 0.8vw, 22px)">🎒</div>
      <div style="flex:1"><div style="font-size:9px;font-weight:800;letter-spacing:.1em;color:rgba(255,255,255,.6)">AD · 우리아이학원찾기</div><div style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700;margin-top:2px;color:#fff">우리 동네 학원, 실시간 후기까지 한눈에</div></div>
      <span style="font-size:13px;font-weight:700;color:#fff">→</span>
    </a>`;
  }
  if (kind === "kitchen") {
    return `<a href="#" style="display:flex;border-radius:14px;background:linear-gradient(135deg,#E8834A,#D96A34);color:#fff;padding:16px;align-items:center;gap:13px">
      <div style="width:38px;height:38px;flex:none;border-radius:11px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:19px">🍳</div>
      <div style="flex:1"><div style="font-size:9px;font-weight:800;letter-spacing:.1em;color:rgba(255,255,255,.62)">AD · 방구석 조리실</div><div style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700;margin-top:2px;color:#fff">오늘 급식 메뉴, 집에서도 만들어봐요</div></div>
      <span style="font-size:13px;font-weight:700;color:#fff">→</span>
    </a>`;
  }
  if (kind === "coupang") {
    return `<a href="#" style="display:flex;border:1px dashed #E3C9B3;border-radius:14px;background:linear-gradient(120deg,#FBF0E7,#FDF8F3);padding:15px 16px;align-items:center;gap:12px">
      <div style="width:36px;height:36px;flex:none;border-radius:10px;background:#F3DFCB;display:flex;align-items:center;justify-content:center;font-size:clamp(17px, 14.5px + 0.7vw, 20px)">🛒</div>
      <div style="flex:1"><div style="font-size:9px;font-weight:800;letter-spacing:.1em;color:#C08A5A">AD · 쿠팡 파트너스</div><div style="font-size:13px;font-weight:700;color:#8A5A2E;margin-top:2px">우리 아이 영양 간식 · 알레르기 프리 상품</div></div>
      <span style="font-size:13px;color:#C08A5A;font-weight:700">→</span>
    </a>`;
  }
  if (kind === "b2b") {
    return `<a href="#" style="display:flex;border:1px solid #E3D9C4;border-radius:14px;background:linear-gradient(120deg,#FBF6EA,#FDFBF4);padding:15px 16px;align-items:center;gap:12px">
      <div style="width:36px;height:36px;flex:none;border-radius:10px;background:#EFE3C6;display:flex;align-items:center;justify-content:center;font-size:clamp(17px, 14.5px + 0.7vw, 20px)">📣</div>
      <div style="flex:1"><div style="font-size:9px;font-weight:800;letter-spacing:.1em;color:#B79A54">AD · 학원 광고</div><div style="font-size:13px;font-weight:700;color:#7A6526;margin-top:2px">우리 학원, 이 자리에 노출하세요</div></div>
      <span style="font-size:11px;color:#B79A54;font-weight:700;white-space:nowrap">광고 문의 →</span>
    </a>`;
  }
  return "";
}

// ================= 홈 =================
export function homePage() {
  const chips = [
    ["", "전체"], ["elem", "초등"], ["mid", "중등"], ["high", "고등"],
  ].map(([lv, label]) =>
    `<a href="/search?level=${lv}" style="padding:8px 15px;border-radius:20px;font-size:13px;font-weight:700;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.13);color:rgba(255,255,255,.72)">${label}</a>`
  ).join("");

  // 기능 소개(글래스 카드) — 검색창과 광고 사이에서 가치 전달.
  const feat = (icon, title, desc) => `
    <div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:15px 14px">
      <div style="font-size:21px;line-height:1">${icon}</div>
      <div style="margin-top:9px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:#fff;letter-spacing:-.01em">${title}</div>
      <div style="margin-top:4px;font-size:11.5px;color:rgba(255,255,255,.58);line-height:1.5;font-weight:500">${desc}</div>
    </div>`;
  const featureGrid = `
    <div style="margin-top:34px">
      <div style="font-size:11px;font-weight:800;letter-spacing:.12em;color:rgba(255,255,255,.38)">이런 걸 볼 수 있어요</div>
      <div style="margin-top:13px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        ${feat("🍚", "오늘의 급식", "메뉴 · 알레르기 · 칼로리까지 한눈에")}
        ${feat("📅", "학사일정 +", "방학 · 시험 · 행사에 우리 가족 연간 스케줄까지")}
        ${feat("📖", "우리 반 시간표 +", "매일 자동으로, 방과후 · 학원 스케줄까지 관리")}
        ${feat("🔔", "챙길 일정 알림", "날짜 · 시간 정해두면 그때 알려드려요")}
      </div>
    </div>`;

  const adStack = ["hagwon", "adsense", "kitchen", "adsense", "b2b"].map((k) => ad(k, true)).join("");

  const body = `
  <div style="min-height:100vh;background:linear-gradient(170deg,#132445 0%,#14274A 52%,#1C3B69 100%);color:#fff;display:flex;flex-direction:column;padding:0 24px">
    <div style="display:flex;align-items:center;gap:9px;height:24px;padding-top:20px">
      <div style="width:24px;height:24px;border-radius:8px;background:${C.green};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px">학</div>
      <span style="font-weight:800;font-size:clamp(16px, 14px + 0.6vw, 19px);letter-spacing:-.02em">아이서랍</span>
      <span style="font-size:10px;font-weight:800;letter-spacing:.04em;color:#132445;background:#7FE0B4;padding:2px 6px;border-radius:5px;line-height:1">BETA</span>
      <div style="margin-left:auto;display:flex;align-items:center;gap:7px">
        <a href="/login" style="display:inline-flex;align-items:center;gap:5px;background:${C.green};border:1px solid ${C.green};color:#fff;font-size:12.5px;font-weight:800;padding:6px 13px;border-radius:20px">로그인 / 가입</a>
        <a href="/mypage" style="display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:20px">👤 마이</a>
        <button type="button" onclick="__shareThis()" style="display:inline-flex;align-items:center;gap:4px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:20px;cursor:pointer;font-family:inherit">🔗 공유</button>
      </div>
    </div>
    <!-- 무료 개방 안내(1/3) — 홈 상단 얇은 배너. 전략 회신 2026-07-19 Q4.
         가격(3,500원)은 개방 기간 중 어디에도 노출하지 않는다 — 전환일에 체험 재부여와 함께 공개. -->
    <div style="margin-top:16px;display:flex;align-items:center;gap:8px;background:rgba(127,224,180,.14);border:1px solid rgba(127,224,180,.3);border-radius:12px;padding:10px 13px">
      <span style="font-size:15px;flex:none">🎁</span>
      <span style="font-size:12.5px;font-weight:700;color:#BFF3DA;line-height:1.5">개학 전까지 전 기능 무료 개방 중이에요</span>
    </div>
    <div style="margin-top:6vh">
      <div style="font-size:13px;font-weight:700;color:#7FE0B4;letter-spacing:.02em">NEIS 공공데이터 기반 · 초·중·고</div>
      <h1 style="margin:14px 0 0;font-size:30px;font-weight:800;line-height:1.28;letter-spacing:-.03em">매달 학교 홈페이지<br>뒤지지 마세요</h1>
      <p style="margin:14px 0 0;font-size:15px;color:rgba(255,255,255,.72);line-height:1.6;font-weight:500">학교 이름만 검색하면 급식·시간표·학사일정을<br>한 곳에서 바로 확인할 수 있어요.</p>
    </div>
    <form action="/search" method="get" style="margin-top:28px">
      <div style="display:flex;gap:8px">
        <div style="flex:1;position:relative">
          <span style="position:absolute;left:15px;top:50%;transform:translateY(-50%);font-size:clamp(16px, 14px + 0.6vw, 19px);opacity:.5">🔎</span>
          <input name="q" placeholder="학교 이름을 입력하세요" style="width:100%;padding:15px 15px 15px 42px;border:none;border-radius:14px;font-size:15px;color:${C.ink};outline:none;background:#fff" required>
        </div>
        <button type="submit" style="flex:none;padding:0 20px;border:none;border-radius:14px;background:${C.green};color:#fff;font-size:15px;font-weight:700;cursor:pointer">검색</button>
      </div>
      <div style="margin-top:12px;display:flex;gap:7px">${chips}</div>
    </form>
    <div style="margin-top:16px;display:inline-flex;align-self:flex-start;align-items:center;gap:6px;background:rgba(127,224,180,.14);border:1px solid rgba(127,224,180,.28);color:#9FE3C1;font-size:11.5px;font-weight:700;padding:6px 12px;border-radius:20px">✓ 매일 급식 확인 무료 · 회원가입 시 1주일 체험</div>
    ${featureGrid}
    <a href="/feedback" style="margin-top:20px;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:14px 15px">
      <span style="font-size:19px;flex:none">💬</span>
      <div style="flex:1;min-width:0"><div style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15px);font-weight:800;color:#fff">베타 의견 보내기</div><div style="font-size:11.5px;color:rgba(255,255,255,.55);margin-top:1px">불편한 점·있으면 하는 기능, 편하게 들려주세요</div></div>
      <span style="color:rgba(255,255,255,.4);font-size:18px;flex:none">›</span>
    </a>
    ${ADS_HIDDEN ? "" : `<div style="margin-top:34px;margin-bottom:20px;display:flex;flex-direction:column;gap:16px">
      <div style="font-size:10px;font-weight:800;letter-spacing:.14em;color:rgba(255,255,255,.32)">광고 · 협찬</div>
      ${adStack}
    </div>`}
    <div style="margin-top:${ADS_HIDDEN ? "34px" : "0"};margin-bottom:26px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11.5px;color:rgba(255,255,255,.4)">
      <a href="/about" style="color:rgba(255,255,255,.5)">서비스 소개</a>
      <a href="/terms" style="color:rgba(255,255,255,.5)">이용약관</a>
      <a href="/privacy" style="color:rgba(255,255,255,.5)">개인정보처리방침</a>
      <a href="/feedback" style="color:rgba(255,255,255,.5)">의견 보내기</a>
    </div>
  </div>`;

  return layout({ title: "아이서랍 — 학교 급식·시간표·학사일정", body, dark: true });
}

// ================= 검색결과 =================
export function searchResultsPage(query, level, schools) {
  const chips = [
    ["", "전체"], ["elem", "초등"], ["mid", "중등"], ["high", "고등"],
  ].map(([lv, label]) => {
    const active = lv === (level || "");
    const style = active
      ? "background:#2E7D5B;color:#fff"
      : "background:rgba(255,255,255,.14);color:rgba(255,255,255,.65)";
    const href = `/search?q=${encodeURIComponent(query || "")}&level=${lv}`;
    return `<a href="${href}" style="padding:8px 15px;border-radius:20px;font-size:13px;font-weight:700;${style}">${label}</a>`;
  }).join("");

  const badge = (kind) => `<span style="background:#EAF1FA;color:#2A4A7F;font-size:11px;font-weight:700;padding:3px 8px;border-radius:7px">${escapeHtml(shortKind(kind))}</span>`;
  const KIND_ICON = { "초등학교": "🧒", "중학교": "📗", "고등학교": "🎓" };

  const cards = schools.map((s) => `
    <a href="/school/${encodeURIComponent(s.slug)}/" style="display:flex;align-items:center;gap:13px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:15px 16px">
      <div style="flex:none;width:42px;height:42px;border-radius:12px;background:${C.greenBg};display:flex;align-items:center;justify-content:center;font-size:20px">${KIND_ICON[s.school_kind] || "🏫"}</div>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-size:clamp(16px, 14px + 0.6vw, 19px);font-weight:800;color:${C.ink};letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(s.name)}</span>
          ${badge(s.school_kind)}
        </div>
        <div style="margin-top:7px;display:flex;align-items:center;gap:6px;font-size:12.5px;color:${C.green};font-weight:700">
          <span style="width:5px;height:5px;border-radius:50%;background:${C.green};flex:none"></span>${escapeHtml(s.jurisdiction_office || s.office_name)}
        </div>
        <div style="margin-top:4px;font-size:12.5px;color:${C.muted};font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(s.address_road || "")}</div>
      </div>
      <span style="flex:none;color:#C4CBD6;font-size:20px">›</span>
    </a>`).join("");

  const label = (query && query.trim()) || (level ? { elem: "초등", mid: "중등", high: "고등" }[level] : "전체") || "전체";

  const resultsBlock = schools.length
    ? `<div style="display:flex;flex-direction:column;gap:10px">${cards}</div>
       ${ADS_HIDDEN ? "" : `<div style="margin-top:20px;display:flex;flex-direction:column;gap:12px">
         <div style="font-size:10px;font-weight:800;letter-spacing:.14em;color:#B4BCC8">광고 · 협찬</div>
         ${ad("hagwon")}${ad("adsense")}${ad("adsense")}
       </div>`}`
    : `<div style="padding:56px 20px;text-align:center">
        <div style="font-size:44px">🏫</div>
        <div style="margin-top:14px;font-size:15px;font-weight:700;color:#41506A">'${escapeHtml(label)}'에 해당하는<br>결과가 없습니다</div>
        <div style="margin-top:8px;font-size:13px;color:#98A2B3;line-height:1.5">학교 이름의 일부만 입력해도 찾을 수 있어요.</div>
      </div>`;

  const body = `
  <div style="min-height:100vh;background:${C.bg}">
    <div style="background:#14274A;padding:18px 20px 20px;color:#fff">
      <form action="/search" method="get" style="display:flex;align-items:center;gap:12px">
        <a href="/" style="flex:none;width:30px;height:30px;display:flex;align-items:center;justify-content:center;border-radius:9px;background:rgba(255,255,255,.12);color:#fff;font-size:clamp(17px, 14.5px + 0.7vw, 20px)">‹</a>
        <input type="hidden" name="level" value="${escapeHtml(level || "")}">
        <div style="flex:1;position:relative">
          <span style="position:absolute;left:13px;top:50%;transform:translateY(-50%);font-size:15px;opacity:.5">🔎</span>
          <input name="q" value="${escapeHtml(query || "")}" placeholder="학교 이름 검색" style="width:100%;padding:12px 13px 12px 38px;border:none;border-radius:12px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);color:${C.ink};outline:none;background:#fff">
        </div>
      </form>
      <div style="margin-top:12px;display:flex;gap:7px">${chips}</div>
    </div>
    <div style="padding:16px">
      <div style="font-size:13px;color:${C.muted2};font-weight:600;margin-bottom:12px"><b style="color:${C.ink}">${escapeHtml(label)}</b> 검색결과 ${schools.length}건</div>
      ${resultsBlock}
    </div>
  </div>`;

  return layout({ title: `${label} 검색결과 — 아이서랍`, body });
}

// ---- 상세: 탭바. paid면 시간표/학사일정 자물쇠 제거(이미 잠금 해제됨) ----
// "개요"+"학생현황"은 "학교정보"로 통합, 순서: 학교정보/학사일정/급식/시간표/커뮤니티.
// 커뮤니티 탭은 초등학교에서만 노출(§지시서2 — 초등 학부모 대상).
function tabBar(slug, activeTab, hasDetail, paid = false, isElementary = false) {
  const tabs = [
    ["overview", "학교정보", false],
    ["schedule", "일정", !paid],
    ["timetable", "시간표", !paid],
    ["meal", "급식", false],
  ];
  if (isElementary) tabs.push(["community", "커뮤니티", false]);
  const items = tabs.map(([key, label, locked]) => {
    const active = key === activeTab;
    const style = `flex:1;padding:14px 2px;text-align:center;font-size:13px;font-weight:${active ? "800" : "600"};color:${active ? C.ink : "#98A2B3"};border-bottom:2.5px solid ${active ? C.green : "transparent"}`;
    const lock = locked ? `<span style="margin-left:2px;font-size:10px;opacity:.6">🔒</span>` : "";
    return `<a href="/school/${encodeURIComponent(slug)}/?tab=${key}" style="${style}">${label}${lock}</a>`;
  }).join("");
  return `<div style="position:sticky;top:0;z-index:20;background:${C.bg};padding-top:2px">
    <div style="display:flex;padding:0 6px;background:#fff;border-top:1px solid #EDEFF3;border-bottom:1px solid #EAEDF1">${items}</div>
  </div>`;
}

// ---- 방과후학교 요약 카드(시간표 탭 하단). 집계치(프로그램수/참여학생/돌봄여부) + 무료는 잠금 ----
// paid 인자로 잠금 해제(현재 공개 페이지는 무료라 항상 잠금). 데이터 없으면 카드 미출력.
function afterschoolCard(details, paid = false, regUrl = "/register-child") {
  if (!details || details.afterschool_program_count == null) return "";
  // 돌봄교실은 초등 개념 — 운영할 때(Y)만 배지 표시. 미운영/중고에는 표시하지 않음.
  const careBadge = details.care_class_yn === "Y"
    ? `<span style="display:inline-block;background:${C.greenBg};color:${C.greenDark};font-size:11px;font-weight:700;padding:3px 9px;border-radius:7px">돌봄교실 운영중</span>`
    : "";
  const prog = escapeHtml(details.afterschool_program_count);
  const stud = details.afterschool_student_count != null ? escapeHtml(details.afterschool_student_count) : "-";
  const blur = paid ? "" : "filter:blur(4px);";
  const summary = `방과후 프로그램 <b style="color:${C.green}">${prog}개</b> 운영 중 · 참여 학생 <b style="color:${C.green}">${stud}명</b>`;

  const lockNote = paid ? "" : `<div style="margin-top:10px;font-size:11.5px;color:${C.muted}">🔒 자세한 방과후 정보는 <a href="${regUrl}" style="color:${C.green};font-weight:700">자녀 등록</a> 후 확인할 수 있어요.</div>`;

  return `<div style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
      <span style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink}">방과후학교</span>${careBadge}
    </div>
    <div style="margin-top:11px;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:${C.inkSoft};font-weight:500;${blur}">${summary}</div>
    ${lockNote}
  </div>`;
}

// ---- 유료: 자녀 스위처(헤더). 등록 자녀 칩 + 활성 강조. 클릭 시 그 자녀 학교 페이지로 이동. ----
// 헤더 우측 상단 자녀 프로필 — 칩(활성=누르면 정보수정, 그 외=자녀 전환) + "+" + 이용만료.
// 자녀별 구분 색(1번=그린/2번=블루/3번=퍼플) — 번호(①②③, 노란색)는 왼쪽, 별명은 오른쪽 끝.
const CHILD_PALETTE = ["127,224,180", "122,178,255", "214,164,255"];
const CHILD_NUM = ["①", "②", "③"];
function childSwitcher(siblings, active, currentSlug) {
  const kids = siblings || [];
  // 자녀 칩 — 버튼(누르면 3개 메뉴 팝업: 시간표 보기 / 프로필 편집 / 취소). idx로 번호·색 결정.
  // pos = 그리드 좌표(예: "grid-column:2;grid-row:2") — 자녀 수와 무관하게 슬롯 위치를 절대 고정.
  // (빈 문자열로 칸을 건너뛰면 자동 배치가 밀려 자녀1이 엉뚱한 위치에 가는 버그가 있었음)
  const chip = (c, idx, pos) => {
    const on = active && c.id === active.id; // 현재 보고 있는 자녀(강조만)
    const cls = `${escapeHtml(c.grade)}학년${c.class_name ? " " + escapeHtml(c.class_name) + "반" : ""}`;
    const rgb = CHILD_PALETTE[idx] || CHILD_PALETTE[0];
    const style = `${pos};display:flex;flex-direction:column;align-items:stretch;gap:1px;padding:7px 11px;border-radius:12px;border:1px solid ${on ? `rgba(${rgb},.55)` : "rgba(255,255,255,.16)"};background:${on ? `rgba(${rgb},.28)` : "rgba(255,255,255,.07)"};color:${on ? "#EAFBF2" : "rgba(255,255,255,.72)"};font-size:12px;cursor:pointer;font-family:inherit;text-align:left`;
    const nameRow = `<span style="display:flex;width:100%;align-items:center;justify-content:space-between;gap:8px"><span style="font-size:13px;font-weight:800;color:#FFD54F">${CHILD_NUM[idx] || idx + 1}</span><span style="font-weight:800">${escapeHtml(c.nickname)}</span></span>`;
    return `<button type="button" class="child-chip" data-name="${escapeHtml(c.nickname)}" data-view="/school/${encodeURIComponent(c.school_slug)}/?child=${escapeHtml(c.id)}&tab=timetable" data-edit="/child/edit?id=${escapeHtml(c.id)}" onclick="openChildMenu(this)" style="${style}">${nameRow}<span style="display:block;text-align:right;opacity:.85;font-weight:600">${cls}</span></button>`;
  };
  // 2×2 그리드 좌표 고정: (1,1)=항상 빈칸, (1,2)=자녀등록 버튼(3명 미만) 또는 3번 자녀, (2,1)=2번 자녀, (2,2)=1번 자녀(항상 고정).
  const child1 = kids[0] ? chip(kids[0], 0, "grid-column:2;grid-row:2") : "";
  const child2 = kids[1] ? chip(kids[1], 1, "grid-column:1;grid-row:2") : "";
  const child3 = kids[2] ? chip(kids[2], 2, "grid-column:2;grid-row:1") : "";

  // "+" 대신 "자녀 등록" 버튼 — 최대 3명 미만일 때만 표시(3명이면 그 자리에 자녀3). 무료 1명 제한은 등록 제출 시 처리.
  // 등록은 "지금 보고 있는 학교"로 연결(자녀 없는 학교에서도 그 학교로 바로 등록되게). 없으면 활성 자녀 학교, 그것도 없으면 검색.
  const addHref = currentSlug ? `/register-child?school=${encodeURIComponent(currentSlug)}`
    : (active && active.school_slug) ? `/register-child?school=${encodeURIComponent(active.school_slug)}` : "/register-child";
  const addBtn = kids.length < 3
    ? `<a href="${addHref}" style="grid-column:2;grid-row:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:7px 8px;border-radius:12px;border:1px dashed rgba(255,255,255,.32);background:none;color:rgba(255,255,255,.72);font-size:11.5px;font-weight:800;text-decoration:none;line-height:1.25">＋ 자녀<br>등록</a>`
    : "";

  const topRight = kids.length >= 3 ? child3 : addBtn;
  // 각 항목이 자기 좌표(grid-column/row)를 갖고 있어 빈 슬롯이 있어도 위치가 밀리지 않는다.
  const grid = `<div style="display:grid;grid-template-columns:repeat(2,minmax(80px,1fr));gap:6px">${topRight}${child2}${child1}</div>`;

  // 이용 만료(테스트 계정 제외) — 프로필 위, 우측 정렬. 만료 임박/만료 시 연장 CTA.
  let expiry = "";
  if (active && !active.is_test && active.trial_expires_at) {
    const ms = new Date(active.trial_expires_at).getTime() - Date.now();
    const days = Math.ceil(ms / 86400000);
    const dateStr = fmtDate(active.trial_expires_at.slice(0, 10).replace(/-/g, ""));
    const extend = `<a href="/subscribe" style="flex:none;font-size:11px;font-weight:800;color:#0F1E38;background:#7FE0B4;padding:5px 11px;border-radius:8px">연장</a>`;
    if (ms <= 0) {
      expiry = `<div style="display:flex;align-items:center;gap:7px;justify-content:flex-end"><span style="font-size:11px;color:#FFD2D2;font-weight:600">이용 만료됨</span>${extend}</div>`;
    } else if (days <= 2) {
      expiry = `<div style="display:flex;align-items:center;gap:7px;justify-content:flex-end"><span style="font-size:11px;color:#FFE3B0;font-weight:600">${days}일 남음 (${dateStr})</span>${extend}</div>`;
    } else {
      expiry = `<span style="font-size:10.5px;color:rgba(255,255,255,.5);font-weight:600">이용 ~${dateStr} · ${days}일</span>`;
    }
  }

  // 자녀 클릭 시 3개 루트 팝업.
  const modal = `<div id="childMenu" style="display:none;position:fixed;inset:0;z-index:60;background:rgba(15,25,45,.55);align-items:center;justify-content:center;padding:24px" onclick="if(event.target===this)this.style.display='none'">
    <div style="background:#fff;border-radius:18px;padding:20px;width:300px;max-width:100%;box-shadow:0 20px 50px rgba(0,0,0,.3)">
      <div id="cmName" style="font-size:clamp(16px, 14px + 0.6vw, 19px);font-weight:800;color:${C.ink};text-align:center;margin-bottom:16px"></div>
      <a id="cmView" href="#" style="display:block;text-align:center;padding:14px;border-radius:12px;background:${C.green};color:#fff;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;margin-bottom:9px">📅 시간표 보기</a>
      <a id="cmEdit" href="#" style="display:block;text-align:center;padding:14px;border-radius:12px;background:#fff;border:1px solid ${C.border};color:${C.inkSoft};font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;margin-bottom:9px">✏️ 프로필 편집</a>
      <button type="button" onclick="document.getElementById('childMenu').style.display='none'" style="display:block;width:100%;padding:13px;border-radius:12px;background:none;border:none;color:${C.muted};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:700;cursor:pointer;font-family:inherit">취소</button>
    </div>
  </div>`;
  const script = `<script>function openChildMenu(el){var m=document.getElementById('childMenu');document.getElementById('cmName').textContent=el.dataset.name;document.getElementById('cmView').href=el.dataset.view;document.getElementById('cmEdit').href=el.dataset.edit;m.style.display='flex';}</script>`;

  return `<div style="flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:6px">
    ${expiry}
    ${grid}
  </div>${modal}${script}`;
}

// ---- 상세: 잠금 오버레이(무료). regUrl = 무료 등록(1주일 체험) 링크 ----
function lockOverlay(text, regUrl = "/register-child") {
  return `<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px;background:linear-gradient(180deg,rgba(243,245,248,.4),rgba(243,245,248,.75))">
    <div style="width:46px;height:46px;border-radius:14px;background:#14274A;color:#fff;display:flex;align-items:center;justify-content:center;font-size:clamp(22px, 18px + 1.1vw, 27px)">🔒</div>
    <div style="margin-top:12px;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink};line-height:1.45;max-width:250px">${text}</div>
    <a href="${regUrl}" style="margin-top:14px;display:inline-block;padding:12px 22px;border-radius:12px;background:${C.green};color:#fff;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700">자녀 등록하기</a>
    <div style="margin-top:8px;font-size:11px;color:${C.muted}">지금 등록하면 1주일 무료</div>
  </div>`;
}

// 표준 벨스케줄(학교마다 실제와 다를 수 있음) — 초 40분·중 45분·고 50분 수업, 9시 시작.
// NEIS 시간표엔 교시별 시각이 없어 학교급 표준으로 계산해 안내(고지 문구 병기).
function bellSchedule(kind) {
  const spec = {
    "초등학교": { dur: 40, brk: 10, lunch: 50, lunchAfter: 4 },
    "중학교": { dur: 45, brk: 10, lunch: 60, lunchAfter: 4 },
    "고등학교": { dur: 50, brk: 10, lunch: 60, lunchAfter: 4 },
  }[kind] || { dur: 45, brk: 10, lunch: 60, lunchAfter: 4 };
  const pad = (n) => String(n).padStart(2, "0");
  const toStr = (m) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
  const periods = {};
  let t = 9 * 60; // 09:00 시작
  for (let p = 1; p <= 8; p++) {
    const s = t, e = t + spec.dur;
    periods[p] = { s: toStr(s), e: toStr(e) };
    t = e + spec.brk;
    if (p === spec.lunchAfter) {
      periods.lunch = { s: toStr(e), e: toStr(e + spec.lunch) };
      t = e + spec.lunch;
    }
  }
  return { periods, lunchAfter: spec.lunchAfter };
}

// 표준 벨스케줄 위에 자녀 개인 설정(settings)을 덮어씀 — 없으면 표준 그대로.
function effectiveBell(kind, settings) {
  const std = bellSchedule(kind);
  if (!settings || !settings.periods) return std;
  const periods = { ...std.periods };
  for (const p of Object.keys(settings.periods)) {
    const t = settings.periods[p];
    if (t && t.s && t.e) periods[p] = { s: t.s, e: t.e };
  }
  let lunchAfter = std.lunchAfter;
  if (settings.lunch && settings.lunch.s && settings.lunch.e) {
    periods.lunch = { s: settings.lunch.s, e: settings.lunch.e };
    lunchAfter = settings.lunch.after || std.lunchAfter;
  }
  return { periods, lunchAfter };
}

function sampleGrid() {
  const days = ["월", "화", "수", "목", "금"];
  const subs = ["국어", "수학", "영어", "과학", "사회", "체육", "음악", "미술"];
  const head = `<div style="display:grid;grid-template-columns:34px repeat(5,1fr);gap:4px;margin-bottom:4px"><div></div>${days.map((d) => `<div style="text-align:center;font-size:11.5px;font-weight:700;color:${C.muted};padding:3px 0">${d}</div>`).join("")}</div>`;
  let rows = "";
  for (let p = 1; p <= 6; p++) {
    const cells = [0, 1, 2, 3, 4].map((di) => {
      const s = subs[(p * 3 + di) % subs.length];
      return `<div style="display:flex;align-items:center;justify-content:center;height:40px;border-radius:8px;font-size:11px;font-weight:700;color:${C.inkSoft};background:#EEF1F5">${s}</div>`;
    }).join("");
    rows += `<div style="display:grid;grid-template-columns:34px repeat(5,1fr);gap:4px;margin-bottom:4px"><div style="display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#A0A9B8">${p}교시</div>${cells}</div>`;
  }
  return head + rows;
}

// 유료 실제 시간표 그리드 — timetable(오늘 이후) 행을 날짜(열)×교시(행)로. 가까운 5개 수업일만.
// edit={slug,grade,className} 전달 시 각 칸을 탭해서 수정 가능(반 단위 공개 오버라이드).
// 시간표가 빈 경우 원인별 안내(§신규버그: 미등록/방학/학기말 구분).
// 학교급·학년별 표준 교시 수 — NEIS 데이터가 없을 때 빈 격자를 몇 줄 깔지 정한다.
// 초등은 저학년일수록 적음(1~2학년 5교시, 3~4학년 6, 5~6학년 6), 중·고는 7교시가 표준.
// 실제와 다르면 사용자가 칸을 비우거나 채우면 되므로 "대략 맞는 크기"면 충분하다.
function standardPeriods(kind, grade) {
  const g = Number(grade) || 0;
  if (kind === "초등학교") return g > 0 && g <= 2 ? 5 : 6;
  return 7; // 중·고(및 학교급 불명)
}

function emptyTimetableNotice(reason) {
  const map = {
    vacation: ["🏖️", "방학 중이에요", "방학 기간이라 시간표가 없어요. 개학하면 자동으로 다시 채워집니다."],
    break: ["🗓️", "학기 시간표가 아직 없어요", "학기가 끝났거나 새 학기 시간표가 아직 올라오지 않았어요. 준비되면 자동 반영됩니다."],
    none: ["📭", "아직 시간표가 제공되지 않아요", "이 학교·학년·반은 아직 시간표 데이터가 없어요. 학교에서 공개하면 자동으로 채워집니다."],
  };
  const [icon, title, desc] = map[reason] || map.none;
  return `<div style="padding:34px 16px;text-align:center">
    <div style="font-size:34px">${icon}</div>
    <div style="margin-top:10px;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink}">${title}</div>
    <div style="margin-top:6px;font-size:12.5px;color:${C.muted};line-height:1.55">${desc}</div>
  </div>`;
}

const TT_BADGE = `display:inline-block;margin-top:2px;font-size:8px;font-weight:800;color:#B0417A;background:#FCF2F2;padding:0 4px;border-radius:5px;line-height:1.5`;
function realTimetableGrid(rows, edit) {
  const editable = !!(edit && edit.slug);
  rows = rows || [];
  // 요일(월~금) 고정 컬럼 — 시간표는 주 단위로 반복되므로 날짜가 아니라 "요일"로 배치.
  const WD = [null, "월", "화", "수", "목", "금"];
  // 저장 자체가 요일 단위(weekday 1~5)로 축약돼 있으므로 그대로 요일→교시 맵으로 배치.
  const byWeekday = {}; // 요일(1~5) → { 교시(number) → row }
  for (const r of rows) {
    const w = Number(r.weekday);
    if (w < 1 || w > 5) continue; // 주말 제외(안전장치)
    (byWeekday[w] = byWeekday[w] || {})[Number(r.period)] = r;
  }
  const weekdays = [1, 2, 3, 4, 5];
  const filledPeriods = rows.filter((r) => r.subject && String(r.subject).trim()).map((r) => Number(r.period) || 0);
  // NEIS가 시간표를 안 주는 학교(경복초 등)도 쓸 수 있게, 데이터가 없으면 "미제공" 안내 대신
  // 학교급 표준 교시만큼 빈 격자를 깔아 사용자가 직접 채우게 한다(유료=편집 가능일 때만).
  // 학년별 실제 교시 수는 학교마다 달라 표준값으로 깔고, 남는 칸은 비워두면 그만이다.
  const stdMax = editable ? standardPeriods(edit && edit.kind, edit && edit.grade) : 0;
  const schoolMax = Math.max(...(filledPeriods.length ? filledPeriods : [0]), 0, stdMax);
  const hasSchool = schoolMax > 0;
  const bell = effectiveBell(edit && edit.kind, edit && edit.settings);
  const gridCols = `66px repeat(5,1fr)`;
  const head = `<div style="display:grid;grid-template-columns:${gridCols};gap:4px;margin-bottom:4px"><div></div>${weekdays.map((w) => {
    // 날짜(예: 07.13)는 표시하지 않고 요일만 고정 노출 — 시간표는 주 단위로 반복되는 고정 패턴이라 날짜가 오히려 혼동을 줌.
    return `<div style="text-align:center;font-size:12.5px;font-weight:800;color:${C.inkSoft};padding:3px 0">${WD[w]}</div>`;
  }).join("")}</div>`;

  // 개인 일정(본인만) 맵.
  const personal = (edit && edit.personal) || [];
  const pmap = {};
  let personalMax = 0;
  for (const it of personal) { pmap[`${it.weekday}|${it.period}`] = it.label; if (it.period > personalMax) personalMax = it.period; }

  let body = "";
  if (hasSchool) {
    for (let p = 1; p <= schoolMax; p++) {
      const cells = weekdays.map((w) => {
        const cell = byWeekday[w] ? byWeekday[w][p] : null;
        const subj = cell ? cell.subject : "";
        const badge = ""; // "수정됨" 배지 제거 — 편집은 저장/공유되되 화면엔 표시 안 함(사용자 요청).
        const base = `display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:48px;border-radius:8px;font-size:12.5px;font-weight:700;color:${C.inkSoft};background:${subj ? "#EEF3EE" : "#F7F9FB"};text-align:center;line-height:1.2;padding:3px`;
        if (editable) {
          return `<div class="tt-cell" data-weekday="${w}" data-period="${escapeHtml(String(p))}" data-full="${escapeHtml(subj)}" style="${base}"><span class="tt-subj">${shortSubject(subj)}</span>${badge}</div>`;
        }
        return `<div style="${base}"><span>${shortSubject(subj)}</span>${badge}</div>`;
      }).join("");
      const t = bell.periods[p] || {};
      // 교시 칸 전체를 큰 탭 영역으로(편집 가능하면 연보라 배경으로 "누르면 바뀜" 표시).
      const label = editable
        ? `<div class="tt-time" data-target="${p}" data-s="${escapeHtml(t.s || "")}" data-e="${escapeHtml(t.e || "")}" style="display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.25;border-radius:8px;padding:3px 1px"><span style="font-size:12.5px;font-weight:800;color:#6B5FA0">${p}교시</span><span class="tt-timeval" style="font-size:10.5px;font-weight:700;color:#9084C2;margin-top:1px">${t.s ? `${t.s}<br>${t.e}` : "--:--<br>--:--"}</span></div>`
        : `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.25"><span style="font-size:12.5px;font-weight:800;color:#7A8494">${p}교시</span><span style="font-size:10.5px;font-weight:700;color:#A6AEBC;margin-top:1px">${t.s ? `${t.s}<br>${t.e}` : ""}</span></div>`;
      body += `<div style="display:grid;grid-template-columns:${gridCols};gap:4px;margin-bottom:4px">${label}${cells}</div>`;
      if (p === bell.lunchAfter && bell.periods.lunch) {
        const lu = bell.periods.lunch;
        const lunchInner = editable
          ? `<div class="tt-time tt-lunch" data-target="lunch" data-s="${escapeHtml(lu.s || "")}" data-e="${escapeHtml(lu.e || "")}" data-after="${escapeHtml(String(bell.lunchAfter))}" data-max-period="${escapeHtml(String(schoolMax))}" style="grid-column:span 5;display:flex;align-items:center;justify-content:center;gap:7px;border-radius:8px;min-height:40px;font-size:13px;font-weight:800;color:#B07E2E">🍚 점심시간 <span class="tt-timeval" style="font-weight:700;color:#C79A3E">${bell.lunchAfter}교시 후 · ${lu.s}~${lu.e}</span> <span class="tt-editmark" style="font-size:11px;font-weight:700;color:#D9B26A">✎ 변경</span></div>`
          : `<div style="grid-column:span 5;display:flex;align-items:center;justify-content:center;gap:6px;background:#FFF6E9;border-radius:8px;min-height:36px;font-size:12px;font-weight:700;color:#B07E2E">🍚 점심시간 <span style="font-weight:600;color:#C79A3E">${lu.s}~${lu.e}</span></div>`;
        body += `<div style="display:grid;grid-template-columns:${gridCols};gap:4px;margin-bottom:4px"><div style="display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#C79A3E">점심</div>${lunchInner}</div>`;
      }
    }
  } else {
    // 여기까지 오는 건 비편집(무료) + 데이터 없음뿐 — 편집 가능하면 위에서 표준 교시로 빈 격자를 깐다.
    body += `<div style="grid-column:1/-1">${emptyTimetableNotice(edit && edit.emptyReason)}</div>`;
  }

  // 무료(비편집)면 학교 시간표만.
  if (!editable) return head + body;

  // ---- 개인 일정(하교 후, 나만 보기) 섹션 — 기본 1줄, 최대 4줄까지 "+ 줄 추가" ----
  const startP = (hasSchool ? schoolMax : 6) + 1;
  const MAX_PERSONAL_ROWS = 4;
  // 내용이 있는 마지막 줄까지는 항상 보이고, 그 다음 빈 줄 1개까지 기본 노출(최소 1줄).
  let contentRows = 0;
  for (let i = 0; i < MAX_PERSONAL_ROWS; i++) {
    if (weekdays.some((w) => pmap[`${w}|${startP + i}`])) contentRows = i + 1;
  }
  const initialVisible = Math.min(MAX_PERSONAL_ROWS, Math.max(1, contentRows + (contentRows < MAX_PERSONAL_ROWS ? 1 : 0)));
  let personalBody = `<div style="margin:12px 0 6px;display:flex;align-items:center;gap:7px"><span style="font-size:12px;font-weight:800;color:#6B4E9E">✏️ 하교 후 개인 일정</span><span style="font-size:10px;font-weight:700;color:#9B86C4;background:#F1ECFA;padding:2px 7px;border-radius:6px">나만 보기</span></div>`;
  for (let i = 0; i < MAX_PERSONAL_ROWS; i++) {
    const p = startP + i;
    const hidden = i >= initialVisible;
    const cells = weekdays.map((w) => {
      const lab = pmap[`${w}|${p}`] || "";
      const base = `display:flex;align-items:center;justify-content:center;min-height:44px;border-radius:8px;font-size:12.5px;font-weight:700;text-align:center;line-height:1.15;padding:2px;cursor:pointer;border:1px dashed ${lab ? "#C9B8EC" : "#E4E7EE"};background:${lab ? "#F4EFFB" : "#FCFCFE"};color:${lab ? "#6B4E9E" : "#C4CBD6"}`;
      return `<div class="tt-personal" data-weekday="${w}" data-period="${p}" style="${base}"><span class="tt-plabel">${lab ? escapeHtml(lab) : '<span class="tt-plus">+</span>'}</span></div>`;
    }).join("");
    // 개인 줄 왼쪽은 "시간만" 표기(개인N 글자 제거). 눌러서 학원·방과후 시간 직접 입력.
    const pt = bell.periods[p] || {};
    const label = `<div class="tt-time" data-target="${p}" data-s="${escapeHtml(pt.s || "")}" data-e="${escapeHtml(pt.e || "")}" style="display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.25;border-radius:8px;padding:2px 1px"><span class="tt-timeval" style="font-size:10.5px;font-weight:700;color:#9084C2">${pt.s ? `${pt.s}<br>${pt.e}` : "시간<br>입력"}</span></div>`;
    personalBody += `<div class="tt-prow" data-idx="${i}" style="display:grid;grid-template-columns:${gridCols};gap:4px;margin-bottom:4px${hidden ? ";display:none" : ""}">${label}${cells}</div>`;
  }
  personalBody += `<div class="tt-editonly" style="justify-content:space-between;align-items:center;gap:8px;margin-top:2px">
    <span style="font-size:10.5px;color:${C.muted};line-height:1.4">칸을 눌러 학원·방과후 등을 넣으세요 (나만 보임 · 최대 4줄)</span>
    <div style="flex:none;display:flex;gap:6px">
      <button type="button" id="ttDelRow" style="font-size:11px;font-weight:800;color:${C.muted2};background:#F0F2F5;border:none;border-radius:8px;padding:6px 10px;cursor:pointer">− 줄 삭제</button>
      <button type="button" id="ttAddRow" style="font-size:11px;font-weight:800;color:#6B4E9E;background:#F1ECFA;border:none;border-radius:8px;padding:6px 11px;cursor:pointer">+ 줄 추가</button>
    </div>
  </div>
  <form class="tt-editonly" method="post" action="/schedule/settings" style="margin-top:12px" onsubmit="return uiConfirm(event, '시간표(교시 시간·바꾼 과목)를 원래대로 되돌릴까요?', '되돌리기')">
    <input type="hidden" name="child_id" value="${escapeHtml(edit.childId || "")}">
    <input type="hidden" name="school_slug" value="${escapeHtml(edit.slug || "")}">
    <input type="hidden" name="action" value="reset">
    <button type="submit" style="width:100%;padding:11px;border:1px solid ${C.border};border-radius:11px;background:#fff;color:${C.muted2};font-size:12.5px;font-weight:700;cursor:pointer">🔄 시간표를 원래대로 초기화 (시간·과목)</button>
  </form>`;

  // 수정 모드 토글 — 평소엔 보기 전용, "시간표 수정"을 눌러야 편집 가능(누르면 바뀌는 표시가 켜짐).
  const styleBlock = `<style>
    #ttGrid .tt-editonly{display:none}
    #ttGrid.editing .tt-editonly{display:flex}
    #ttGrid .tt-plus{visibility:hidden}
    #ttGrid.editing .tt-plus{visibility:visible}
    #ttGrid .tt-time{background:#fff;border:1px solid transparent;cursor:default}
    #ttGrid.editing .tt-time{background:#F4F1FB;border:1px solid #E4DFF5;cursor:pointer}
    #ttGrid .tt-time.tt-lunch{background:#FFF6E9;border:1px solid transparent}
    #ttGrid.editing .tt-time.tt-lunch{background:#FFF3DE;border:1px solid #F0DDB4}
    #ttGrid.editing .tt-cell{cursor:pointer}
    #ttGrid.editing .tt-personal{cursor:pointer}
    #ttGrid .tt-editmark{visibility:hidden}
    #ttGrid.editing .tt-editmark{visibility:visible}
  </style>`;
  const toggleRow = `<div style="display:flex;justify-content:flex-end;margin-bottom:8px"><button type="button" id="ttEditToggle" style="font-size:12px;font-weight:800;color:#6B4E9E;background:#F1ECFA;border:1px solid #E4DFF5;border-radius:9px;padding:7px 13px;cursor:pointer">✏️ 시간표 수정</button></div>`;
  // 학교가 시간표를 안 올려 빈 격자로 깔린 경우 — 왜 비어 있는지 + 직접 채우면 된다는 안내.
  const blankNotice = filledPeriods.length === 0
    ? `<div style="margin-bottom:9px;background:#FBF4E9;border:1px solid #F0E3C8;border-radius:11px;padding:11px 13px;font-size:12px;color:#9A7B36;line-height:1.55">
        <b>이 학교는 시간표를 공개하지 않아요.</b> 아래 빈 칸을 눌러 직접 채워 넣으시면 돼요.<br>
        나중에 학교가 올리면 자동으로 채워집니다.
      </div>`
    : "";
  const grid = `<div id="ttGrid" data-slug="${escapeHtml(edit.slug)}" data-grade="${escapeHtml(edit.grade)}" data-class="${escapeHtml(edit.className || "")}" data-child="${escapeHtml(edit.childId || "")}">${styleBlock}${toggleRow}${blankNotice}${head}${body}${personalBody}</div>`;
  const script = `<script>(function(){
    var g=document.getElementById('ttGrid'); if(!g) return;
    var BADGE=${JSON.stringify(TT_BADGE)};
    function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
    function editInline(cell, cur, onSave){
      if(cell.querySelector('input')) return;
      var orig=cell.innerHTML; var done=false;
      cell.innerHTML='<input type="text" maxlength="20" style="width:100%;box-sizing:border-box;border:1px solid #9B86C4;border-radius:6px;padding:4px;font-size:11px;text-align:center;font-weight:700">';
      var inp=cell.querySelector('input'); inp.value=cur; inp.focus(); inp.select();
      function restore(){cell.innerHTML=orig;}
      function fin(){ if(done) return; done=true; var v=inp.value.trim(); if(v===cur){restore();return;} onSave(v, restore); }
      inp.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();fin();}else if(e.key==='Escape'){done=true;restore();}});
      inp.addEventListener('blur',fin);
    }
    g.querySelectorAll('.tt-cell').forEach(function(cell){
      cell.addEventListener('click',function(){
        if(!g.classList.contains('editing')) return;
        var cur=cell.dataset.full||'';
        editInline(cell, cur, function(v, restore){
          if(!v){restore();return;}
          var b=new URLSearchParams({school_slug:g.dataset.slug,grade:g.dataset.grade,class_name:g.dataset.class,weekday:cell.dataset.weekday,period:cell.dataset.period,subject:v});
          fetch('/timetable/edit',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b}).then(function(r){return r.json();}).then(function(res){
            if(res&&res.ok){cell.dataset.full=res.subject;cell.innerHTML='<span class="tt-subj">'+esc(res.subject)+'</span>';cell.style.background='#EEF3EE';}
            else{alert('수정 권한이 없거나 저장에 실패했어요.');restore();}
          }).catch(function(){alert('저장에 실패했어요.');restore();});
        });
      });
    });
    g.querySelectorAll('.tt-personal').forEach(function(cell){
      cell.addEventListener('click',function(){
        if(!g.classList.contains('editing')) return;
        var labEl=cell.querySelector('.tt-plabel'); var cur=labEl&&labEl.textContent!=='+'?labEl.textContent:'';
        editInline(cell, cur, function(v, restore){
          var b=new URLSearchParams({child_id:g.dataset.child,weekday:cell.dataset.weekday,period:cell.dataset.period,label:v});
          fetch('/schedule/personal',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b}).then(function(r){return r.json();}).then(function(res){
            if(res&&res.ok){
              var has=!!res.label;
              cell.innerHTML='<span class="tt-plabel">'+(has?esc(res.label):'<span class="tt-plus">+</span>')+'</span>';
              cell.style.background=has?'#F4EFFB':'#FCFCFE'; cell.style.color=has?'#6B4E9E':'#C4CBD6'; cell.style.border='1px dashed '+(has?'#C9B8EC':'#E4E7EE');
            } else {alert('저장에 실패했어요.');restore();}
          }).catch(function(){alert('저장에 실패했어요.');restore();});
        });
      });
    });
    // 개인 줄 표시 헬퍼 — 인라인 style.display 로 판정(서버·JS 모두 'none'으로 통일).
    function prows(){ return Array.prototype.slice.call(g.querySelectorAll('.tt-prow')); }
    function hiddenRows(){ return prows().filter(function(r){return r.style.display==='none';}); }
    function visRows(){ return prows().filter(function(r){return r.style.display!=='none';}); }
    function syncAddBtn(){ if(addBtn) addBtn.style.display = hiddenRows().length? '' : 'none'; }
    // 개인 일정 "+ 줄 추가" — 숨긴 다음 줄을 하나씩 노출, 다 열리면 버튼만 숨김(다시 삭제하면 재노출).
    var addBtn=g.querySelector('#ttAddRow');
    if(addBtn){ addBtn.addEventListener('click',function(){
      var h=hiddenRows(); if(h.length){ h[0].style.display='grid'; } syncAddBtn();
    });}
    // "− 줄 삭제" — 마지막으로 보이는 빈 줄을 숨김(내용 있으면 막기, 최소 1줄 유지).
    var delBtn=g.querySelector('#ttDelRow');
    if(delBtn){ delBtn.addEventListener('click',function(){
      var vis=visRows(); if(vis.length<=1) return;
      var last=vis[vis.length-1];
      var hasContent=Array.prototype.some.call(last.querySelectorAll('.tt-plabel'),function(l){return l.textContent&&l.textContent!=='+';});
      if(hasContent){ alert('내용이 있는 줄이에요. 칸을 비운 뒤 삭제해 주세요.'); return; }
      last.style.display='none'; syncAddBtn();
    });}
    // 시간표 수정 모드 토글 — 수정하겠습니까? / 수정 완료? 커스텀 모달 확인 후 편집 on/off.
    var editBtn=g.querySelector('#ttEditToggle');
    if(editBtn){ editBtn.addEventListener('click',function(){
      if(g.classList.contains('editing')){
        uiConfirmCb('시간표 수정이 완료 되셨나요?', function(){ g.classList.remove('editing'); editBtn.textContent='✏️ 시간표 수정'; }, '완료');
      } else {
        uiConfirmCb('시간표를 수정하겠습니까?', function(){ g.classList.add('editing'); editBtn.textContent='✅ 수정 완료'; }, '수정하기');
      }
    });}
    // 교시/점심 시간 인라인 편집 — 칸 전체를 눌러 시작·끝 시각 직접 변경(교시 번호는 유지, 시간부만 교체).
    // 점심은 추가로 "몇 교시 뒤로 배치할지"(after) 드롭다운도 함께 편집.
    g.querySelectorAll('.tt-time').forEach(function(cell){
      cell.addEventListener('click',function(){
        if(!g.classList.contains('editing')) return;
        if(cell.dataset.editing) return; cell.dataset.editing='1';
        var tgt=cell.dataset.target, s0=cell.dataset.s||'', e0=cell.dataset.e||'', isLunch=(tgt==='lunch');
        var after0=cell.dataset.after||'4', maxPeriod=parseInt(cell.dataset.maxPeriod,10)||8;
        var val=cell.querySelector('.tt-timeval'); if(!val){cell.dataset.editing='';return;} var orig=val.innerHTML;
        var st='font-size:12px;width:70px;border:1px solid #9B86C4;border-radius:5px;padding:3px;box-sizing:border-box';
        var selHtml='';
        if(isLunch){
          var opts=''; for(var i=1;i<=maxPeriod;i++){ opts+='<option value="'+i+'"'+(String(i)===String(after0)?' selected':'')+'>'+i+'교시 후</option>'; }
          selHtml='<select class="ta" style="'+st+';width:auto">'+opts+'</select>';
        }
        val.innerHTML='<span style="display:inline-flex;flex-direction:'+(isLunch?'row':'column')+';gap:3px;vertical-align:middle">'+selHtml+'<input type="time" class="ts" value="'+s0+'" style="'+st+'"><input type="time" class="te" value="'+e0+'" style="'+st+'"></span>';
        var si=val.querySelector('.ts'), ei=val.querySelector('.te'), ai=val.querySelector('.ta'); si.focus();
        var done=false;
        function finish(){ if(done) return; setTimeout(function(){
          if(document.activeElement===si||document.activeElement===ei||document.activeElement===ai) return; done=true;
          var s=si.value,e=ei.value,after=ai?ai.value:after0;
          if(!s||!e||(s===s0&&e===e0&&after===after0)){ val.innerHTML=orig; cell.dataset.editing=''; return; }
          var body={child_id:g.dataset.child,target:tgt,s:s,e:e};
          if(isLunch) body.after=after;
          var b=new URLSearchParams(body);
          fetch('/schedule/time',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b}).then(function(r){return r.json();}).then(function(res){
            if(res&&res.ok){ cell.dataset.s=s; cell.dataset.e=e; if(isLunch){ cell.dataset.after=after; val.innerHTML=after+'교시 후 · '+s+'~'+e; window.location.reload(); } else { val.innerHTML=s+'<br>'+e; } }
            else{ alert('저장 실패'); val.innerHTML=orig; }
            cell.dataset.editing='';
          }).catch(function(){alert('저장 실패');val.innerHTML=orig;cell.dataset.editing='';});
        },120); }
        si.addEventListener('blur',finish); ei.addEventListener('blur',finish);
        if(ai) ai.addEventListener('change',finish);
      });
    });
  })();</script>`;
  return grid + script;
}


// NEIS 알레르기 유발 식품 19종
const ALLERGY_ITEMS = [
  [1, "난류(계란)"], [2, "우유"], [3, "메밀"], [4, "땅콩"], [5, "대두"], [6, "밀"],
  [7, "고등어"], [8, "게"], [9, "새우"], [10, "돼지고기"], [11, "복숭아"], [12, "토마토"],
  [13, "아황산류"], [14, "호두"], [15, "닭고기"], [16, "쇠고기"], [17, "오징어"],
  [18, "조개류(굴·전복·홍합)"], [19, "잣"],
];

function mealCard(meal, showAllergyLegend) {
  if (!meal) return `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px;color:${C.muted};font-size:13px">등록된 급식 정보가 없습니다.</div>`;
  let dishes = [];
  try { dishes = JSON.parse(meal.dishes_parsed || "[]"); } catch { dishes = []; }
  // 알레르기 번호 집계는 (이름 유무와 무관하게) 원문 전체 기준 — 범례에는 다 나오게.
  const allAllergens = new Set();
  dishes.forEach((d) => (d.allergens || []).forEach((a) => allAllergens.add(a)));
  const activeNums = [...allAllergens].sort((a, b) => a - b);

  // 이름이 비어있는(파싱 오류로 알레르기 번호만 남은) 항목은 목록에서 제외 — "(1.2.3)" 단독 노출 방지(§지시서5).
  // 해당 번호는 위 activeNums에 이미 집계돼 하단 범례로 안내되므로 정보 손실 없음.
  const namedDishes = dishes.filter((d) => d && d.name && String(d.name).trim());
  const dishBullets = namedDishes.map((d) => `
    <div style="display:flex;align-items:center;gap:9px;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);color:${C.inkSoft};font-weight:500">
      <span style="width:5px;height:5px;border-radius:50%;background:${C.green};flex:none"></span>${escapeHtml(d.name)}${(d.allergens && d.allergens.length) ? `<span style="font-size:11px;color:${C.muted}">(${d.allergens.join(".")})</span>` : ""}
    </div>`).join("") || `<div style="color:${C.muted};font-size:13px">등록된 메뉴가 없습니다.</div>`;

  const kcal = kcalNum(meal.calorie_info);
  const chips = activeNums.map((n) => `<span style="min-width:28px;height:28px;padding:0 8px;display:inline-flex;align-items:center;justify-content:center;border:1px solid ${C.greenBd};background:${C.greenBg};color:${C.greenDark};border-radius:8px;font-size:12.5px;font-weight:700">${n}</span>`).join("");

  const legend = ALLERGY_ITEMS.map(([num, label]) => {
    const on = activeNums.includes(num);
    const style = on
      ? `background:${C.greenBg};color:#1F6B4C;font-weight:700`
      : "background:#fff;color:#8A94A6;font-weight:500;border:1px solid #EDF0F4";
    return `<div style="display:flex;align-items:center;font-size:12px;padding:5px 8px;border-radius:7px;${style}"><span style="display:inline-block;min-width:17px;font-weight:800">${num}</span>${escapeHtml(label)}</div>`;
  }).join("");

  const legendBlock = showAllergyLegend ? `
    <details style="margin-top:12px">
      <summary style="list-style:none;cursor:pointer;font-size:12px;font-weight:700;color:${C.green}">성분 번호 안내 ⌄</summary>
      <div style="margin-top:10px;background:#F7F9FB;border:1px solid #EDF0F4;border-radius:12px;padding:13px 14px">
        <div style="font-size:11.5px;font-weight:700;color:#41506A;margin-bottom:10px">NEIS 알레르기 유발 식품 19종 <span style="color:${C.muted};font-weight:500">· 초록색은 이 메뉴에 포함</span></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 10px">${legend}</div>
      </div>
    </details>` : "";

  return `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700;color:${C.ink}">${fmtDate(meal.meal_date)} ${escapeHtml(meal.meal_type_name)}</span>
      ${kcal ? `<span style="background:${C.greenBg};color:${C.greenDark};font-size:11.5px;font-weight:700;padding:4px 9px;border-radius:8px">${kcal} kcal</span>` : ""}
    </div>
    <div style="margin-top:13px;display:flex;flex-direction:column;gap:10px">${dishBullets}</div>
    ${activeNums.length ? `<div style="margin-top:14px;padding-top:13px;border-top:1px dashed #E1E5EB">
      <span style="font-size:12px;color:${C.muted};font-weight:600">알레르기 유발 성분</span>
      <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px">${chips}</div>
      ${legendBlock}
    </div>` : ""}
  </div>`;
}

// 정보 오류 신고(상세정보 탭) — 공시값이 실제와 다를 때 사용자 제보. JS 없이 표준 폼 POST.
function reportBlock(school, reported) {
  if (reported) {
    return `<div style="margin-top:14px;background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:12px;padding:13px 15px;font-size:12.5px;color:${C.greenDark};line-height:1.55">✅ 신고가 접수됐어요. 제보해 주셔서 감사합니다 — 확인 후 반영하겠습니다.</div>`;
  }
  const cats = ["학급수", "학생수", "시간표", "급식", "기타"];
  return `
    <details style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:12px;padding:13px 15px">
      <summary style="font-size:12.5px;font-weight:700;color:${C.inkSoft};cursor:pointer;list-style:none">ℹ️ 정보가 실제와 다른가요? <span style="color:${C.green}">신고하기</span></summary>
      <p style="margin:10px 0 0;font-size:11.5px;color:${C.muted};line-height:1.6">공시 시점과 실제 편성 사이 시차로 값이 다를 수 있어요. 실제와 다른 부분을 알려주시면 확인하겠습니다. (개인정보는 받지 않아요)</p>
      <form method="post" action="/report" style="margin-top:11px">
        <input type="hidden" name="school_slug" value="${escapeHtml(school.slug)}">
        <select name="category" style="width:100%;padding:11px;border:1.5px solid #DFE3EA;border-radius:10px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);background:#fff;color:${C.ink}">
          ${cats.map((c) => `<option value="${c}">${c}</option>`).join("")}
        </select>
        <textarea name="message" required maxlength="500" placeholder="예) 2학년은 실제로 3개 반이에요." style="margin-top:8px;width:100%;box-sizing:border-box;min-height:72px;padding:11px;border:1.5px solid #DFE3EA;border-radius:10px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);line-height:1.5;resize:vertical"></textarea>
        <button type="submit" style="margin-top:8px;width:100%;padding:12px;border:none;border-radius:11px;background:${C.ink};color:#fff;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700">신고 보내기</button>
      </form>
    </details>`;
}

// PWA 설치·알림 안내(스크린샷 없이 텍스트+아이콘 단계). "미리 만들되 숨김" — FEATURE_PWA_GUIDE 플래그로만 노출.
function pwaInstallGuide() {
  const step = (n, icon, title, desc) => `
    <div style="display:flex;gap:11px;align-items:flex-start;padding:11px 0;border-bottom:1px solid #F0F2F5">
      <div style="flex:none;width:30px;height:30px;border-radius:9px;background:${C.greenBg};color:${C.greenDark};display:flex;align-items:center;justify-content:center;font-size:15px">${icon}</div>
      <div><div style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:800;color:${C.ink}">${n}. ${title}</div><div style="margin-top:2px;font-size:12px;color:${C.muted};line-height:1.5">${desc}</div></div>
    </div>`;
  return `
    <div style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px 18px">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-size:clamp(18px, 15px + 0.8vw, 22px)">📲</span>
        <div style="font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink}">홈 화면에 추가하고 알림 받기</div>
      </div>
      <p style="margin:8px 0 4px;font-size:12px;color:${C.muted};line-height:1.55">앱처럼 홈 화면에서 바로 열고, 오늘 급식·시간표·챙길 일정을 알림으로 받아보세요.</p>
      ${step("1", "⋮", "브라우저 메뉴 열기", "주소창 옆 메뉴(⋮ 또는 공유 버튼)를 눌러요.")}
      ${step("2", "🏠", "‘홈 화면에 추가’ 선택", "메뉴에서 ‘홈 화면에 추가’를 눌러 설치해요.")}
      ${step("3", "🔔", "알림 ‘허용’ 선택", "알림 권한을 허용하면 매일 자동으로 챙겨드려요.")}
      <div style="margin-top:11px;font-size:11px;color:${C.muted};line-height:1.5">· 버튼 위치는 기기·브라우저에 따라 조금씩 달라요.<br>· 알림 발송 기능은 준비 중입니다.</div>
    </div>`;
}

// ================= 학교 상세 =================
export function schoolDetailPage(ctx) {
  const { school, details, tab, todayYmd, upcoming, eventsRest, schedules,
          yearSchedules = [], communityPosts = [],
          allMeals = [], mealType = "",
          paid = false, child = null, siblings = [], timetable = [], todayActs = [],
          timetableEmptyReason = null, reported = false, warmed = false, pwaGuide = false, vapidPublic = "" } = ctx;
  // 온디맨드 워밍 로더 — 콘텐츠가 아직 캐시 안 됐을 때 스피너 표시 + /api/school-warm 호출 후 ?w=1로 새로고침.
  // 서버가 NEIS를 기다리며 페이지를 멈추는 대신, 페이지는 즉시 뜨고 콘텐츠만 뒤이어 채운다.
  const warmLoader = (kind, extra) => {
    const qs = "slug=" + encodeURIComponent(school.slug) + "&kind=" + kind + (extra || "");
    return `<div style="padding:44px 16px;text-align:center">
      <div style="width:34px;height:34px;border:3px solid #E4E9F0;border-top-color:${C.green};border-radius:50%;margin:0 auto;animation:wspin .8s linear infinite"></div>
      <div style="margin-top:14px;font-size:13.5px;color:${C.muted2};font-weight:600">학교 정보를 불러오는 중이에요…</div>
      <style>@keyframes wspin{to{transform:rotate(360deg)}}</style>
      <script>fetch('/api/school-warm?${qs}').then(function(r){return r.json();}).catch(function(){}).finally(function(){var u=new URL(location.href);u.searchParams.set('w','1');location.replace(u.toString());});</script>
    </div>`;
  };
  // 급식 3끼(조식/중식/석식) 처리. 기숙사형(조식·석식 제공) 판별.
  const MEAL_ORDER = { "조식": 0, "중식": 1, "석식": 2 };
  const MEAL_KOR = { "조식": "아침", "중식": "점심", "석식": "저녁" };
  const mealTypesAvail = [...new Set(allMeals.map((m) => m.meal_type_name))]
    .sort((a, b) => (MEAL_ORDER[a] ?? 9) - (MEAL_ORDER[b] ?? 9));
  const isBoarding = mealTypesAvail.includes("조식") || mealTypesAvail.includes("석식");
  // 유료(자녀 등록/관리자 테스트)면 광고 미노출. 무료는 기존대로 광고 표시.
  const A = (kind, dark) => (paid ? "" : ad(kind, dark));
  // "자녀 등록하기" = 무료 등록(1주일 체험) → 결제(/subscribe) 아니라 등록 폼으로.
  const regUrl = `/register-child?school=${encodeURIComponent(school.slug)}`;
  // 학년별 breakdown이 있어야 상세정보 탭 노출.
  let breakdown = [];
  try { breakdown = details && details.grade_breakdown ? JSON.parse(details.grade_breakdown) : []; } catch { breakdown = []; }
  const hasDetail = breakdown.length > 0;
  // 커뮤니티는 초등학교만(§지시서2). 비초등에서 ?tab=community 접근 시 학교정보로 폴백.
  const isElementary = (school.school_kind || "").includes("초등");
  const validTabs = ["overview", "meal", "timetable", "schedule"].concat(isElementary ? ["community"] : []);
  const activeTab = validTabs.includes(tab) ? tab : "overview";
  // 지금이 방학 기간인지 — yearSchedules에 오늘~2주 내 "방학" 일정이 있으면 방학으로 본다(급식 없음 안내용).
  const _vcBase = (todayYmd && todayYmd.length === 8) ? todayYmd : "20260101";
  const _vcD = new Date(+_vcBase.slice(0, 4), +_vcBase.slice(4, 6) - 1, +_vcBase.slice(6, 8) + 14);
  const _vcCut = `${_vcD.getFullYear()}${String(_vcD.getMonth() + 1).padStart(2, "0")}${String(_vcD.getDate()).padStart(2, "0")}`;
  const onVacation = (yearSchedules || []).some((s) => {
    const nm = s.event_name || "";
    return nm.includes("방학") && !nm.includes("식") && s.event_date >= _vcBase && s.event_date <= _vcCut;
  });

  const levelLabel = shortKind(school.school_kind);
  const subtitleParts = [school.est_type, normCoedu(school.coedu)].filter(Boolean);
  const fy = foundedYear(school.founded_ymd);
  if (fy) subtitleParts.push(`${fy}년 개교`);
  const subtitle = subtitleParts.join(" · ");
  const office = school.jurisdiction_office || school.office_name;

  // 스탯: 4칸 단일 행(디자인 2026-07-12 개정) — 전교생/학급수/교원수/개교.
  // 설립구분·남녀공학은 헤더 요약줄("공립 · 남녀공학 · 1981년 개교")에 이미 있어 중복이라 제거.
  // 전교생/학급수/교원수는 학교알리미(details) 미연동이면 자동 생략 → 개교만 남으면 1칸.
  const stats = [];
  if (details && details.student_count != null) stats.push([`${details.student_count}명`, "전교생"]);
  if (details && details.class_count != null) stats.push([`${details.class_count}개`, "학급 수"]);
  if (details && details.teacher_count != null) stats.push([`${details.teacher_count}명`, "교원 수"]);
  if (fy) stats.push([`${fy}년`, "개교"]);
  const statCols = stats.length || 1;
  const statCells = stats.map(([v, l], i) => {
    const border = i !== stats.length - 1 ? "border-right:1px solid #F0F2F5;" : "";
    return `<div style="padding:15px 6px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;${border}"><div style="font-size:clamp(18px, 15px + 0.8vw, 22px);font-weight:800;color:${C.ink};letter-spacing:-.02em;white-space:nowrap">${escapeHtml(v)}</div><div style="font-size:10.5px;color:${C.muted};margin-top:3px;font-weight:600;white-space:nowrap">${escapeHtml(l)}</div></div>`;
  }).join("");

  // ---- 탭별 본문 ----
  // 중요 일정(이달의 행사) — 학사일정 탭의 "이번 달 챙길 일정" 요약·달력에서 사용.
  const importantEvents = importantEventsFrom(schedules || (upcoming ? [upcoming, ...(eventsRest || [])] : []));
  const thisMonth = (todayYmd || "").slice(0, 6);
  const monthImportant = importantEvents.filter((e) => (e.event_date || "").slice(0, 6) === thisMonth);

  let content = "";

  if (activeTab === "overview") {
    // "학교정보" = 개요(연락처) + 학생현황(학년별 현황) 통합. 중요일정·오늘의 급식은 각각 학사일정·급식 탭에 있어 여기선 제거.
    const contactBlock = `
      <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px">
        <div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink};margin-bottom:12px">연락처</div>
        <div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #F0F2F5">
          <span style="width:52px;flex:none;font-size:12px;color:${C.muted};font-weight:600">주소</span>
          <span style="font-size:13px;color:${C.inkSoft};font-weight:500;line-height:1.5">${escapeHtml(school.address_road || "")}</span>
        </div>
        <div style="display:flex;gap:12px;padding:9px 0${school.homepage ? ";border-bottom:1px solid #F0F2F5" : ""}">
          <span style="width:52px;flex:none;font-size:12px;color:${C.muted};font-weight:600">전화</span>
          <span style="font-size:13px;color:${C.inkSoft};font-weight:600">${escapeHtml(school.phone || "-")}</span>
        </div>
        ${school.homepage ? `<div style="display:flex;gap:12px;padding:9px 0">
          <span style="width:52px;flex:none;font-size:12px;color:${C.muted};font-weight:600">홈페이지</span>
          <a href="${escapeHtml(school.homepage)}" target="_blank" rel="noopener noreferrer" style="font-size:12.5px;color:${C.green};font-weight:700;word-break:break-all;line-height:1.5">${escapeHtml(String(school.homepage).replace(/^https?:\/\//, ""))} ↗</a>
        </div>` : ""}
        ${school.phone ? `<a href="tel:${escapeHtml(school.phone)}" style="margin-top:12px;display:block;text-align:center;padding:13px;border-radius:12px;background:${C.greenBg};color:${C.greenDark};font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700">전화 걸기</a>` : ""}
      </div>`;

    // 학생현황: 학년별 학급수·학생수(+성별) 브레이크다운(학교알리미, 무료 공개). 데이터 없으면 섹션 생략.
    let studentStatusBlock = "";
    if (hasDetail) {
      const hasGender = breakdown.some((g) => g.male != null || g.female != null);
      const totMale = breakdown.reduce((a, g) => a + (g.male || 0), 0);
      const totFemale = breakdown.reduce((a, g) => a + (g.female || 0), 0);
      const rows = breakdown.map((g) => {
        const avg = (g.students && g.classes) ? Math.round(g.students / g.classes) : null;
        const genderInline = (hasGender && (g.male != null || g.female != null))
          ? `<div style="font-size:10.5px;color:#4E7D66;font-weight:700;margin-top:1px">남 ${g.male != null ? escapeHtml(g.male) : "-"} · 여 ${g.female != null ? escapeHtml(g.female) : "-"}</div>`
          : "";
        const classList = g.classes ? Array.from({ length: g.classes }, (_, i) => i + 1) : [];
        const expand = classList.length ? `
          <div style="padding:2px 2px 12px">
            <div style="display:grid;grid-template-columns:repeat(${Math.min(classList.length, 5)},1fr);gap:6px">
              ${classList.map((n) => `<div style="text-align:center;background:#F5F8FB;border:1px solid #E7EDF3;border-radius:8px;padding:8px 2px"><div style="font-size:13px;font-weight:800;color:${C.ink}">${n}반</div><div style="font-size:9.5px;color:${C.muted};font-weight:600;margin-top:1px">평균 ${avg != null ? avg : "-"}명</div></div>`).join("")}
            </div>
            <div style="margin-top:8px;font-size:10.5px;color:${C.muted};line-height:1.45">※ 반별 개별 인원은 공시되지 않아 <b>학급당 평균</b>(${escapeHtml(g.students ?? "-")}명 ÷ ${escapeHtml(g.classes ?? "-")}반)으로 표시합니다.</div>
          </div>` : "";
        return `
        <details style="border-bottom:1px solid #F0F2F5">
          <summary style="list-style:none;cursor:pointer;display:flex;align-items:stretch;gap:8px;padding:11px 0">
            <div style="width:40px;flex:none;display:flex;align-items:center;font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink}">${escapeHtml(g.grade)}학년</div>
            <div style="flex:1;text-align:center;background:#EEF2FB;border-radius:10px;padding:9px;display:flex;flex-direction:column;align-items:center;justify-content:center"><div style="font-size:clamp(17px, 14.5px + 0.7vw, 20px);font-weight:800;color:#2A4A7F;letter-spacing:-.02em">${g.classes != null ? escapeHtml(g.classes) : "-"}</div><div style="font-size:10px;color:#5A6B8C;font-weight:600">학급</div></div>
            <div style="flex:2;background:${C.greenBg};border-radius:10px;padding:8px 12px;display:flex;flex-direction:column;align-items:center;justify-content:center">
              <div><span style="font-size:clamp(18px, 15px + 0.8vw, 22px);font-weight:800;color:${C.green};letter-spacing:-.02em">${g.students != null ? escapeHtml(g.students) : "-"}</span><span style="font-size:10.5px;color:#5C8A73;font-weight:700;margin-left:2px">명</span></div>
              ${genderInline}
            </div>
            <div style="flex:none;display:flex;align-items:center;color:#B7C2CF;font-size:11px">▾</div>
          </summary>
          ${expand}
        </details>`;
      }).join("");
      const sumMale = details.male_count ?? (hasGender ? totMale : null);
      const sumFemale = details.female_count ?? (hasGender ? totFemale : null);
      const genderSummary = (sumMale != null || sumFemale != null) ? ` · 남 ${escapeHtml(sumMale ?? "-")}명 · 여 ${escapeHtml(sumFemale ?? "-")}명` : "";
      // 학년별 현황은 기본 접힘(§지시서9) — 헤더 클릭 시 펼쳐짐. 요약줄에 전교생·학급수를 미리 노출.
      studentStatusBlock = `
      <details style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:16px;overflow:hidden">
        <summary style="list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:15px 16px">
          <span style="display:flex;align-items:baseline;gap:8px">
            <span style="font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">학년별 현황</span>
            ${details.disclosure_round ? `<span style="font-size:11px;font-weight:700;color:${C.muted};background:#EEF1F5;padding:2px 8px;border-radius:6px">${escapeHtml(details.disclosure_round)} 공시</span>` : ""}
          </span>
          <span style="flex:none;font-size:12px;color:${C.muted};font-weight:600">전교생 ${escapeHtml(details.student_count ?? "-")}명 · ${escapeHtml(details.class_count ?? "-")}학급 ▾</span>
        </summary>
        <div style="padding:0 16px 4px">${rows}</div>
        <div style="padding:12px 16px 16px;font-size:11.5px;color:${C.muted};line-height:1.5">전교생 ${escapeHtml(details.student_count ?? "-")}명 · ${escapeHtml(details.class_count ?? "-")}학급 · 교원 ${escapeHtml(details.teacher_count ?? "-")}명${genderSummary} (학교알리미 ${escapeHtml(details.disclosure_round || "")} 공시 기준. 반별 인원은 공시되지 않아 학년 단위로만 제공)</div>
      </details>
      ${reportBlock(school, reported)}`;
    }

    // 연간 수업일수·주당 수업시수(학교알리미, 무료 공개) — 연락처 바로 아래 배치(2026-07-18 학사일정 탭에서 이동).
    const schoolDaysCard = details && details.school_days ? `
      <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px;margin-top:12px">
        <div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink};margin-bottom:12px">연간 수업일수</div>
        <div style="display:flex;gap:10px">
          <div style="flex:1;text-align:center;padding:12px;background:${C.greenBg};border-radius:12px">
            <div style="font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.green};letter-spacing:-.02em">${escapeHtml(details.school_days)}일</div>
            <div style="font-size:11px;color:#5C8A73;font-weight:600;margin-top:2px">연간 수업일수</div>
          </div>
          ${details.week_class_hours ? `<div style="flex:1;text-align:center;padding:12px;background:#F4F1FA;border-radius:12px">
            <div style="font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:#6B4E9E;letter-spacing:-.02em">${escapeHtml(details.week_class_hours)}시수</div>
            <div style="font-size:11px;color:#8672AE;font-weight:600;margin-top:2px">주당 총 수업시수</div>
          </div>` : ""}
        </div>
        <div style="margin-top:10px;font-size:11px;color:${C.muted};line-height:1.5">학교알리미 공시 기준. 학교 사정에 따라 변경될 수 있습니다.</div>
      </div>` : "";

    // 월별 일정 & 다이어리 안내(2026-07-18) — 학교정보 탭에서 일정 탭(월별 달력 + 내 일정/다이어리)으로 유도.
    const diaryGuide = `
      <a href="/school/${encodeURIComponent(school.slug)}/?tab=schedule" style="display:flex;align-items:center;gap:12px;background:linear-gradient(135deg,#EAF6EF,#F3FAF6);border:1px solid ${C.greenBd};border-radius:16px;padding:15px 16px;margin-top:12px">
        <span style="font-size:22px;flex:none">📅</span>
        <div style="flex:1;min-width:0"><div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink}">월별 일정 &amp; 다이어리</div><div style="font-size:12px;color:${C.muted2};margin-top:2px;line-height:1.5">학사일정을 달력으로 보고, 우리 가족 일정도 함께 적어둘 수 있어요.</div></div>
        <span style="color:${C.green};font-size:20px;flex:none">›</span>
      </a>`;

    // 학교 표준 서식 — 2026-07-19 내림(FEATURE_FORMS 플래그). 코드는 보존(삭제 아님).
    // 사유: 학교마다 양식이 달라 우리가 준 서식을 내면 반려될 수 있다(오사용 리스크).
    // 대신 공식 출처인 학교 홈페이지로 보낸다. 플래그를 켜면 예전 카드가 그대로 돌아온다.
    const formsCard = (FEATURE_FORMS && isElementary) ? `
      <a href="/forms?school=${encodeURIComponent(school.slug)}" style="display:flex;align-items:center;gap:12px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:15px 16px;margin-top:12px">
        <span style="font-size:22px;flex:none">📄</span>
        <div style="flex:1;min-width:0"><div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink}">학교 서식 (상담·체험학습·결석·조퇴)</div><div style="font-size:12px;color:${C.muted2};margin-top:2px;line-height:1.5">${escapeHtml(school.name)} 이름이 채워진 서식을 바로 인쇄·PDF 저장</div></div>
        <span style="color:${C.green};font-size:20px;flex:none">›</span>
      </a>` : "";

    // 서식 자리를 대체하는 홈페이지 카드. NEIS 학교기본정보의 HMPG_ADRES(schools.homepage) 사용 —
    // 전국 12,563개교 중 12,504개(99.5%) 보유. 값이 없는 학교에서는 카드 자체를 숨긴다.
    // http:// 주소가 섞여 있어 값은 그대로 쓰고, 새 탭 + rel="noopener"로 연다.
    const hp = (school.homepage || "").trim();
    const homepageCard = hp ? `
      <div style="background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:16px;padding:15px 16px;margin-top:12px">
        <div style="display:flex;align-items:flex-start;gap:12px">
          <span style="font-size:22px;flex:none">🏫</span>
          <div style="flex:1;min-width:0">
            <div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.greenDark};line-height:1.45">서식·가정통신문은<br>학교 홈페이지에서 받으세요</div>
            <div style="font-size:12px;color:${C.greenDark};opacity:.82;margin-top:6px;line-height:1.55">학교마다 양식이 달라서, 우리 학교 공식 서식을 쓰시는 게 정확해요.</div>
          </div>
        </div>
        <a href="${escapeHtml(hp)}" target="_blank" rel="noopener noreferrer" style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:12px;padding:12px;border-radius:12px;background:${C.green};color:#fff;font-size:13.5px;font-weight:800">홈페이지 바로가기 ↗</a>
      </div>` : "";

    content = `${A("adsense")}${paid ? "" : '<div style="height:14px"></div>'}${contactBlock}${schoolDaysCard}${diaryGuide}${formsCard}${homepageCard}${studentStatusBlock}${paid ? "" : `<div style="margin-top:14px">${A("b2b")}</div>`}`;
  }

  if (activeTab === "meal" && allMeals.length === 0 && !warmed) {
    content = warmLoader("meal");
  } else if (activeTab === "meal") {
    // 급식 3끼(조식/중식/석식) 탭 — 기숙사형 고교는 아침·점심·저녁 다 볼 수 있게.
    const selType = mealTypesAvail.includes(mealType) ? mealType : (mealTypesAvail.includes("중식") ? "중식" : mealTypesAvail[0]);

    // 날짜 탭은 끼니(조식/중식/석식) 종류와 무관하게 공통 — 전체 끼니에 걸친 날짜 합집합(가까운 5일).
    // 끼니별로 제공일이 다를 수 있어(예: 기숙사형 고교 조식은 4일만) 끼니별로 따로 날짜 목록을 만들면
    // 같은 인덱스(d=2)가 조식/중식/석식마다 다른 날짜를 가리키게 되어 탭 전환 시 선택 날짜가 바뀌는 버그가 생김.
    const weekDates = [...new Set(allMeals.map((m) => m.meal_date))].sort().slice(0, 5);
    const mealByDateType = new Map();
    for (const m of allMeals) {
      const key = `${m.meal_date}|${m.meal_type_name}`;
      if (!mealByDateType.has(key)) mealByDateType.set(key, m);
    }

    const selIdx = paid ? Math.min(Math.max(ctx.mealDay || 0, 0), Math.max(weekDates.length - 1, 0)) : 0;
    // 급식 링크 생성 헬퍼(§지시서C 7·8·9): 끼니 탭·날짜 탭 모두 mt·d·child를 함께 유지해야
    // 탭 전환 시 날짜가 0으로 리셋되거나 child가 소실돼 무료 화면으로 튕기는 문제를 막는다.
    const childParam = child ? `&child=${encodeURIComponent(child.id)}` : "";
    const mealHref = (mt, d) => `/school/${encodeURIComponent(school.slug)}/?tab=meal&mt=${encodeURIComponent(mt)}&d=${d}${childParam}`;

    // 끼니 탭 — 현재 날짜(selIdx)·child 유지, 현재 선택 끼니 하이라이트(on).
    const typeTabs = mealTypesAvail.length > 1 ? `
      <div style="display:flex;gap:6px;margin-bottom:12px">${mealTypesAvail.map((t) => {
        const on = t === selType;
        return `<a href="${mealHref(t, selIdx)}" style="flex:1;text-align:center;padding:9px 0;border-radius:11px;font-size:13px;font-weight:800;${on ? `background:${C.green};color:#fff` : `background:#fff;border:1px solid #EAEDF1;color:${C.muted}`}">${MEAL_KOR[t] || t}</a>`;
      }).join("")}</div>` : "";

    const dayTabs = weekDates.map((d, i) => {
      const active = paid ? i === selIdx : (i === 0);
      const locked = !paid && !active;
      const style = active
        ? `border:1px solid ${C.green};background:${C.green};color:#fff`
        : locked
          ? `border:1px solid #EEF1F5;background:#F7F9FB;color:#C4CBD6;cursor:not-allowed`
          : `border:1px solid #EAEDF1;background:#fff;color:${C.muted}`;
      const inner = `<span style="font-size:13px;font-weight:700">${dowLabel(d)}</span>
        <span style="font-size:10.5px;margin-top:2px">${fmtDate(d)}</span>${locked ? `<span style="font-size:9px">🔒</span>` : ""}`;
      return paid
        ? `<a href="${mealHref(selType, i)}" style="display:flex;flex-direction:column;align-items:center;padding:9px 0;border-radius:11px;${style}">${inner}</a>`
        : `<div style="display:flex;flex-direction:column;align-items:center;padding:9px 0;border-radius:11px;${style}">${inner}</div>`;
    }).join("");
    const shownDate = paid ? weekDates[selIdx] : weekDates[0];
    const shownMeal = shownDate ? (mealByDateType.get(`${shownDate}|${selType}`) || null) : null;
    const freeDayLabel = weekDates[0] ? `${dowLabel(weekDates[0])} ${fmtDate(weekDates[0])}` : "";

    if (weekDates.length === 0) {
      // 급식이 아예 없음(방학 등) — 깨진 그리드 대신 안내 카드.
      content = `
        <h2 style="margin:0 0 12px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">급식</h2>
        <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:34px 20px;text-align:center">
          <div style="font-size:34px">${onVacation ? "🏖️" : "🍽️"}</div>
          <div style="margin-top:12px;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink}">${onVacation ? "방학 기간이라 급식이 없어요" : "지금은 표시할 급식이 없어요"}</div>
          <div style="margin-top:6px;font-size:13px;color:${C.muted};line-height:1.6">${onVacation ? "개학하면 다시 채워드려요." : "학교 사정으로 급식이 없거나 아직 공개 전일 수 있어요."}</div>
        </div>
        <div style="margin-top:14px">${A("coupang")}</div>`;
    } else {
    content = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <h2 style="margin:0;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">주간 급식</h2>
        ${isBoarding ? `<span style="font-size:11px;font-weight:700;color:#7A6526;background:#FBF4E9;border:1px solid #F0E3C8;padding:2px 8px;border-radius:6px">아침·점심·저녁</span>` : ""}
      </div>
      ${typeTabs}
      <div style="display:grid;grid-template-columns:repeat(${Math.max(weekDates.length, 1)},1fr);gap:6px">${dayTabs || `<div style="color:${C.muted};font-size:13px">이 끼니의 급식 정보가 없습니다.</div>`}</div>
      ${paid ? "" : `<div style="margin-top:10px;background:#FBF4E9;border:1px solid #F0E3C8;border-radius:12px;padding:11px 13px;font-size:12px;color:#9A7B36;line-height:1.5">가까운 급식일(${escapeHtml(freeDayLabel)}) 메뉴만 무료로 제공돼요. 전체 주간 급식은 <a href="${regUrl}" style="color:#7A6526;font-weight:800;text-decoration:underline">자녀 등록</a> 후 확인 가능합니다.</div>`}
      <div style="margin-top:14px">${mealCard(shownMeal, true)}</div>
      <div style="margin-top:14px">${A("coupang")}</div>
      ${paid ? "" : `<div style="margin-top:12px">${A("kitchen")}</div><div style="margin-top:12px">${A("adsense")}</div>`}`;
    }
  }

  if (activeTab === "timetable") {
    if (paid && timetable.length === 0 && !warmed) {
      // 시간표 아직 캐시 안 됨 → 워밍(학년·반 파라미터 포함) 후 새로고침.
      content = warmLoader("timetable", `&grade=${encodeURIComponent(child.grade)}&class=${encodeURIComponent(child.class_name || "")}`);
    } else if (paid) {
      const clsLabel = `${escapeHtml(child.grade)}학년${child.class_name ? ` ${escapeHtml(child.class_name)}반` : ""}`;
      const editCtx = { slug: school.slug, grade: child.grade, className: child.class_name, kind: school.school_kind, childId: child.id, personal: ctx.personalSchedule || [], settings: ctx.scheduleSettings, emptyReason: timetableEmptyReason };
      content = `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px">
        <h2 style="margin:0;font-size:clamp(17px, 14.5px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">시간표</h2>
        <span style="flex:none;font-size:13px;color:${C.green};font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(child.nickname)} · ${clsLabel}</span>
      </div>
      <div id="ttCapture" style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:13px">${realTimetableGrid(timetable, editCtx)}</div>
      <button type="button" onclick="captureImg('ttCapture','시간표')" style="margin-top:10px;width:100%;padding:12px;border:1px solid ${C.greenBd};border-radius:12px;background:#fff;color:${C.greenDark};font-size:13.5px;font-weight:800;cursor:pointer;font-family:inherit">🖼️ 시간표 이미지로 저장</button>
      <div style="margin-top:10px;background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:12px;padding:13px 15px;font-size:12px;color:${C.greenDark}">
        <div style="font-weight:800;font-size:12.5px;margin-bottom:8px">시간표 직접 수정하는 법</div>
        <div style="margin-bottom:6px;line-height:1.5">① 오른쪽 위 <b>✏️ 시간표 수정</b>을 누르면 편집이 켜져요.</div>
        <div style="margin-bottom:6px;line-height:1.5">② <b>과목 · 교시 시간 · 점심 시간 · 개인일정</b> 칸을 눌러 바꿔요.</div>
        <div style="margin-bottom:10px;line-height:1.5">③ 다 되면 <b>✅ 수정 완료</b>를 누르세요.</div>
        <div style="padding-top:9px;border-top:1px dashed ${C.greenBd};color:${C.muted2};line-height:1.5">· 교시 시간 기본값은 학교급 표준(초 40 · 중 45 · 고 50분)이에요.<br>· 바꾼 과목은 <b>같은 반</b>에 공유되고, 개인일정은 <b>나만</b> 보여요.</div>
      </div>
      ${todayActivityLine(todayActs, child)}
      ${pwaGuide ? pwaInstallGuide() : ""}
      ${afterschoolCard(details, true, regUrl)}`;
    } else {
      content = `
      <h2 style="margin:0 0 13px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">시간표</h2>
      <div style="display:flex;gap:8px;opacity:.55;pointer-events:none">
        <div style="flex:1;padding:11px 12px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);color:${C.muted};background:#fff">1학년</div>
        <div style="flex:1;padding:11px 12px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);color:${C.muted};background:#fff">1반</div>
      </div>
      <div style="position:relative;margin-top:14px;border-radius:16px;overflow:hidden">
        <div style="filter:blur(5px);pointer-events:none;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:13px">${sampleGrid()}</div>
        ${lockOverlay("자녀를 등록하면 매일 자동으로<br>우리 반 시간표를 보여드려요", regUrl)}
      </div>
      ${afterschoolCard(details, false, regUrl)}
      <div style="margin-top:14px">${A("hagwon")}</div>`;
    }
  }

  if (activeTab === "schedule" && (yearSchedules || []).length === 0 && !warmed) {
    content = `<h2 style="margin:0 0 13px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">일정</h2>${warmLoader("schedule")}`;
  } else if (activeTab === "schedule") {
    // 이달의 행사(중요 일정 자동분류) — 무료는 개수+카테고리 티저 + 잠금, 날짜/상세는 자녀 등록 후(§지시서).
    const monthLabel = thisMonth.length === 6 ? `${thisMonth.slice(0, 4)}년 ${Number(thisMonth.slice(4, 6))}월` : "";
    const cats = [...new Set(monthImportant.map((e) => e.category))];
    const catChips = cats.map((c) => {
      const icon = monthImportant.find((e) => e.category === c).icon;
      return `<span style="display:inline-flex;align-items:center;gap:4px;background:#fff;border:1px solid ${C.greenBd};color:${C.greenDark};font-size:12px;font-weight:700;padding:5px 10px;border-radius:9px">${icon} ${escapeHtml(c)}</span>`;
    }).join("");
    // 유료: 이달의 행사 상세 리스트(날짜+D-day). 무료: 개수+카테고리 티저 + 잠금.
    const monthDetailRows = monthImportant.map((e) => {
      const [c, b] = EVENT_COLORS[classifyEvent(e.event_name, e.closure_type)];
      return `<div style="display:flex;align-items:center;gap:11px;padding:9px 0;border-bottom:1px solid #E4EFE8">
        <span style="font-size:15px">${e.icon}</span>
        <span style="flex:1;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:600;color:${C.inkSoft}">${escapeHtml(e.event_name)}</span>
        <span style="font-size:12px;color:${C.muted};font-weight:600">${fmtDate(e.event_date)}</span>
        <span style="font-size:11px;font-weight:700;color:${c};min-width:38px;text-align:right">${ddayText(todayYmd, e.event_date)}</span>
      </div>`;
    }).join("");
    const monthEventsSection = monthImportant.length ? `
      <div style="background:linear-gradient(135deg,#EAF6EF,#F3FAF6);border:1px solid ${C.greenBd};border-radius:16px;padding:16px;margin-bottom:12px">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink}">이달의 행사</span>
          <span style="font-size:11.5px;color:${C.greenDark};font-weight:600">${monthLabel}</span>
        </div>
        <div style="margin-top:10px;font-size:15px;color:${C.inkSoft};font-weight:600">이번 달 챙길 중요 일정 <b style="color:${C.green};font-size:clamp(18px, 15px + 0.8vw, 22px)">${monthImportant.length}건</b></div>
        ${paid
          ? `<div style="margin-top:8px">${monthDetailRows}</div>`
          : `<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px">${catChips}</div>
             <div style="margin-top:12px;padding-top:11px;border-top:1px dashed ${C.greenBd};font-size:12px;color:${C.muted};line-height:1.5">🔒 날짜·상세는 <a href="${regUrl}" style="color:${C.green};font-weight:700">자녀 등록</a> 후 확인하고, 임박하면 알림도 받을 수 있어요.</div>`}
      </div>` : "";

    content = `
      <h2 style="margin:0 0 13px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">일정</h2>
      ${monthEventsSection}
      ${eventCalendar(yearSchedules, todayYmd, paid, regUrl, ctx.personalEvents || [], paid && child ? { slug: school.slug, childId: child.id } : null, vapidPublic)}`;
    if (!paid) {
      // 미로그인·무료 → 달력을 "볼 수만 없는" 게 아니라 아예 못 쓰게 잠근다(시간표와 동일 패턴).
      // 클릭·월이동·이미지저장 전부 차단 + 실제 일정 데이터(행사명 JSON)를 내려보내지 않아 소스 노출도 막는다.
      content = `
      <h2 style="margin:0 0 13px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">일정</h2>
      <div style="position:relative;border-radius:16px;overflow:hidden">
        <div style="filter:blur(5px);pointer-events:none;user-select:none">${eventCalendar([], todayYmd, false, regUrl, [], null, "")}</div>
        ${lockOverlay("로그인하고 자녀를 등록하면<br>학사일정 달력을 볼 수 있어요", regUrl)}
      </div>
      <div style="margin-top:12px">${A("b2b")}</div>`;
    }
  }

  if (activeTab === "community") {
    // 커뮤니티(§지시서D): 고정 닉네임(30일 잠금)·학년/반 박제·도배방지·필터·시:분 표시·컴팩트 행.
    const guideBlock = `
      <div style="background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:14px;padding:12px 14px;font-size:11.5px;color:${C.greenDark};line-height:1.55;margin-bottom:12px">
        <b>📋 작성 시 안내</b> · 1~3줄만(이미지·링크 불가) · 댓글 없음(나열만) · 욕설 자동 가림 · 신고 3회 시 자동 숨김 · 연속 2개까지(도배 방지)
      </div>`;

    // 닉네임 상태(고정, 30일 잠금). child.community_nickname / community_nickname_changed_at는 siblings 쿼리에 포함.
    const curNick = (child && child.community_nickname || "").trim();
    let nickLockedDays = 0;
    if (child && child.community_nickname_changed_at) {
      const elapsed = Date.now() - new Date(child.community_nickname_changed_at).getTime();
      if (elapsed < 30 * 86400000) nickLockedDays = Math.ceil((30 * 86400000 - elapsed) / 86400000);
    }
    const nickBlock = paid ? `
      <form method="post" action="/community/nickname" style="background:#fff;border:1px solid ${C.border};border-radius:14px;padding:12px 13px;margin-bottom:10px;display:flex;gap:8px;align-items:center">
        <input type="hidden" name="school_slug" value="${escapeHtml(school.slug)}">
        <span style="flex:none;font-size:12px;font-weight:800;color:${C.muted2}">닉네임</span>
        <input type="text" name="nickname" maxlength="12" value="${escapeHtml(curNick)}" placeholder="비우면 익명" ${nickLockedDays ? "readonly" : ""} style="flex:1;min-width:0;border:1px solid #DFE3EA;border-radius:9px;padding:9px 10px;font-size:13px;font-family:inherit;box-sizing:border-box;${nickLockedDays ? "background:#F5F6F8;color:" + C.muted : ""}">
        ${nickLockedDays
          ? `<span style="flex:none;font-size:10.5px;color:${C.muted};font-weight:600">🔒 ${nickLockedDays}일 후 변경</span>`
          : `<button type="submit" style="flex:none;padding:9px 13px;border:none;border-radius:9px;background:${C.greenBg};color:${C.greenDark};font-size:12px;font-weight:800;cursor:pointer">저장</button>`}
      </form>
      <div style="font-size:10.5px;color:${C.muted};margin:-4px 2px 10px;line-height:1.5">· 닉네임은 한 번 저장하면 <b>30일간 변경할 수 없어요</b>. 비워두면 익명으로 표시됩니다.</div>` : "";

    const postForm = paid ? `
      <form method="post" action="/community/post" style="background:#fff;border:1px solid ${C.border};border-radius:14px;padding:13px;margin-bottom:14px">
        <input type="hidden" name="school_slug" value="${escapeHtml(school.slug)}">
        <textarea name="body" maxlength="90" rows="2" placeholder="짧은 후기를 남겨주세요 (최대 90자, ${curNick ? escapeHtml(curNick) : "익명"}으로 등록)" required style="width:100%;border:1px solid #DFE3EA;border-radius:10px;padding:10px;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-family:inherit;resize:none;box-sizing:border-box"></textarea>
        <button type="submit" style="margin-top:8px;width:100%;padding:12px;border:none;border-radius:11px;background:${C.green};color:#fff;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:800;cursor:pointer">등록하기</button>
      </form>` : `
      <div style="position:relative;border-radius:14px;overflow:hidden;margin-bottom:14px;min-height:190px">
        <div style="filter:blur(4px);pointer-events:none;background:#fff;border:1px solid ${C.border};border-radius:14px;padding:13px"><div style="height:170px;background:#F7F9FB;border-radius:10px"></div></div>
        ${lockOverlay("자녀를 등록하면 글을<br>작성할 수 있어요", regUrl)}
      </div>`;

    // 필터: 이 학교 최대 학급수(학생현황 breakdown)로 반 옵션 구성. 학년은 초등 1~6 고정.
    const maxClass = Math.max(1, ...breakdown.map((g) => Number(g.classes) || 0));
    const classOpts = Array.from({ length: maxClass }, (_, i) => `<option value="${i + 1}">${i + 1}반</option>`).join("");
    const filterBlock = `
      <div style="display:flex;gap:7px;margin-bottom:10px">
        <select id="cmFilterGrade" style="flex:1;padding:9px;border:1px solid #DFE3EA;border-radius:10px;font-size:12.5px;background:#fff;font-family:inherit"><option value="">전체 학년</option>${[1,2,3,4,5,6].map((g)=>`<option value="${g}">${g}학년</option>`).join("")}</select>
        <select id="cmFilterClass" style="flex:1;padding:9px;border:1px solid #DFE3EA;border-radius:10px;font-size:12.5px;background:#fff;font-family:inherit"><option value="">전체 반</option>${classOpts}</select>
      </div>`;

    // 게시글 행 — 컴팩트(§지시서D15): 패딩 7px, 아바타 24px, gap·line-height 축소. 시:분 표시(§D14). 학년/반 박제 data 속성(§D13).
    const postRows = (communityPosts || []).map((p) => {
      const ymd = (p.created_at || "").slice(0, 10).replace(/-/g, "");
      const hm = (p.created_at || "").slice(11, 16); // "HH:MM"
      const gc = [p.author_grade ? `${escapeHtml(p.author_grade)}학년` : "", p.author_class ? `${escapeHtml(p.author_class)}반` : ""].filter(Boolean).join(" ");
      return `
      <div class="cmPost" data-grade="${escapeHtml(p.author_grade || "")}" data-class="${escapeHtml(p.author_class || "")}" style="display:flex;gap:8px;padding:8px 0;border-bottom:1px solid #F2F4F6">
        <div style="width:24px;height:24px;flex:none;border-radius:50%;background:${C.greenBg};color:${C.greenDark};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800">${escapeHtml((p.author_nickname || "익").slice(0, 1))}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;line-height:1.2">
            <span style="font-size:12px;font-weight:700;color:${C.inkSoft};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(p.author_nickname || "익명")}${gc ? `<span style="font-weight:500;color:${C.muted};font-size:10.5px"> · ${gc}</span>` : ""}</span>
            <span style="flex:none;font-size:10px;color:${C.muted}">${fmtDate(ymd)}${hm ? " " + hm : ""}</span>
          </div>
          <div style="margin-top:2px;font-size:13px;color:${C.ink};line-height:1.4;white-space:pre-wrap;word-break:break-word">${escapeHtml(p.body)}</div>
          <button type="button" class="cmReportBtn" data-id="${escapeHtml(p.id)}" style="margin-top:2px;font-size:10px;color:${C.muted};background:none;border:none;cursor:pointer;padding:0;font-family:inherit">🚩 신고</button>
        </div>
      </div>`;
    }).join("");

    content = `
      <h2 style="margin:0 0 13px;font-size:clamp(16.5px, 14px + 0.7vw, 20px);font-weight:800;color:${C.ink};letter-spacing:-.02em">커뮤니티</h2>
      ${guideBlock}
      ${nickBlock}
      ${postForm}
      ${filterBlock}
      <div id="cmList" style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:0 14px">${postRows || `<div style="padding:28px 0;text-align:center;color:${C.muted};font-size:13px">아직 등록된 글이 없어요.</div>`}</div>
      <div id="cmEmpty" style="display:none;padding:24px 0;text-align:center;color:${C.muted};font-size:13px">조건에 맞는 글이 없어요.</div>
      ${paid ? "" : `<div style="margin-top:14px">${A("adsense")}</div>`}
      <script>(function(){
        // 학년/반 필터(§D13) — 박제된 data-grade/data-class로 클라이언트 필터. 정렬은 서버가 최신순.
        var fg=document.getElementById('cmFilterGrade'), fc=document.getElementById('cmFilterClass'), empty=document.getElementById('cmEmpty');
        function applyFilter(){
          if(!fg) return; var g=fg.value, c=fc.value, shown=0;
          document.querySelectorAll('.cmPost').forEach(function(el){
            var ok=(!g||el.dataset.grade===g)&&(!c||el.dataset.class===c);
            el.style.display=ok?'flex':'none'; if(ok)shown++;
          });
          if(empty) empty.style.display=shown?'none':'block';
        }
        if(fg){ fg.addEventListener('change',applyFilter); fc.addEventListener('change',applyFilter); }
        document.querySelectorAll('.cmReportBtn').forEach(function(btn){
          btn.addEventListener('click',function(){
            uiConfirmCb('이 글을 신고하시겠어요?', function(){
              var b=new URLSearchParams({post_id:btn.dataset.id});
              fetch('/community/report',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b})
                .then(function(r){return r.json();})
                .then(function(res){ if(res&&res.ok){ btn.textContent='신고 접수됨'; btn.disabled=true; } else { alert('신고 처리에 실패했어요.'); } });
            }, '신고하기');
          });
        });
      })();</script>`;
  }

  const body = `
  <div data-tab="${activeTab}">
    <div style="background:linear-gradient(165deg,#132445 0%,#14274A 46%,#1C3B69 100%);color:#fff;padding:0 0 66px">
      <div style="padding:16px 22px 0">
        <div style="display:flex;align-items:center;gap:10px;height:24px">
          <a href="javascript:history.back()" style="flex:none;color:rgba(255,255,255,.8);font-size:clamp(22px, 18px + 1.1vw, 27px);line-height:1">‹</a>
          <a href="/" style="display:flex;align-items:center;gap:8px;margin-left:14px;color:#fff">
            <div style="width:22px;height:22px;border-radius:7px;background:${C.green};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:11.5px">학</div>
            <span style="font-weight:700;font-size:clamp(14px, 12.5px + 0.4vw, 16px)">아이서랍</span>
          </a>
          <a href="/mypage" style="margin-left:auto;display:inline-flex;align-items:center;gap:4px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12px;font-weight:700;padding:5px 11px;border-radius:20px">👤 마이</a>
          <button type="button" onclick="__shareThis()" style="display:inline-flex;align-items:center;gap:3px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12px;font-weight:700;padding:5px 10px;border-radius:20px;cursor:pointer;font-family:inherit">🔗 공유</button>
        </div>
        <div style="margin-top:20px;display:flex;align-items:flex-end;justify-content:space-between;gap:12px">
          <div style="min-width:0;flex:1">
            <div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap">
              <div style="display:inline-flex;align-items:center;background:rgba(46,125,91,.24);border:1px solid rgba(90,200,150,.4);color:#9FE3C1;padding:4px 11px;border-radius:20px;font-size:11.5px;font-weight:700">${escapeHtml(levelLabel)}</div>
              ${isBoarding ? `<div style="display:inline-flex;align-items:center;gap:3px;background:rgba(255,209,138,.18);border:1px solid rgba(255,209,138,.4);color:#FFD98A;padding:4px 11px;border-radius:20px;font-size:11.5px;font-weight:700">🏠 기숙사형</div>` : ""}
            </div>
            <h1 style="margin:12px 0 0;font-size:clamp(27px, 21px + 1.6vw, 33px);font-weight:800;letter-spacing:-.03em;line-height:1.15">${schoolNameHtml(school.name)}</h1>
            <div style="margin-top:9px;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:rgba(255,255,255,.72);font-weight:500">${escapeHtml(subtitle)}</div>
            <div style="margin-top:12px;display:flex;align-items:center;gap:6px;font-size:12.5px;color:rgba(255,255,255,.6)">
              <span style="width:5px;height:5px;border-radius:50%;background:#5AC896"></span>${escapeHtml(office)}
            </div>
          </div>
          ${(siblings && siblings.length) ? childSwitcher(siblings, child, school.slug) : `<a href="${regUrl}" style="flex:none;display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:12px;background:${C.green};color:#fff;font-size:12.5px;font-weight:700"><span style="font-size:clamp(14px, 12.5px + 0.4vw, 16px)">＋</span>자녀 등록</a>`}
        </div>
      </div>
    </div>

    ${statCells ? `<div style="margin:-50px 16px 0;background:#fff;border:1px solid ${C.border};border-radius:20px;padding:6px;box-shadow:0 10px 28px rgba(20,39,74,.1);display:grid;grid-template-columns:repeat(${statCols},1fr);position:relative;z-index:2">${statCells}</div>` : ""}

    <div style="margin-top:18px">${tabBar(school.slug, activeTab, hasDetail, paid, isElementary)}</div>

    <div style="padding:16px 16px 36px;min-height:60vh">${content}</div>
  </div>`;

  const titleSuffix = { meal: " 급식", timetable: " 시간표", schedule: " 일정·학사정보", overview: " 학교정보", community: " 커뮤니티" }[activeTab] || " 급식·시간표·식단표·학사정보";
  // 탭(?tab=)은 같은 학교의 변형 주소라, 검색엔진이 기본 주소 하나로 합치도록 canonical을 고정한다.
  return layout({
    title: `${school.name}${titleSuffix} — 아이서랍`,
    body,
    canonical: `${SITE_ORIGIN}/school/${encodeURIComponent(school.slug)}/`,
  });
}

// 급식 첫 요리 몇 개를 ' · '로
function mealLineOf(meal) {
  try {
    const dishes = JSON.parse(meal.dishes_parsed || "[]").filter((d) => d && d.name && String(d.name).trim());
    return dishes.slice(0, 4).map((d) => d.name).join(" · ");
  } catch { return ""; }
}
function dowLabel(ymd) {
  if (!ymd || ymd.length < 8) return "";
  const d = new Date(`${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`);
  return ["일", "월", "화", "수", "목", "금", "토"][d.getUTCDay()];
}

// ================= 자녀 등록(무료 + 자동 1주일 체험) =================
// "자녀 등록하기" → 결제 없이 학교+학년+반만 입력 → 즉시 1주일 전체 잠금 해제(§백엔드지시서).
// isPaid=false(무료회원)면 "자녀 1명까지" 기준으로 안내. 유료만 최대 3명 안내.
// ── 보호자 동의 컴포넌트 (독립 분리 — 회신3 지침) ──────────────────
// 만14세 미만 확인 수단(문자·이메일·카드·본인인증)이 무엇으로 정해지든 **이 컴포넌트에 한 단계만
// 끼워 넣으면** 되도록 분리해 둔다. 지금은 체크박스(동의 표시) + children.consent_at·consent_method 기록.
// ⚠️ 법 제22조의2는 "동의 확인"까지를 의무로 두고, 시행령 제17조의2가 확인 방법을 7가지로 한정 열거한다.
//    체크박스는 동의 '표시'이지 '확인 수단'이 아니다 — 확인 수단은 미결(사장님 결정 대기).
function consentBlock() {
  return `
  <div style="margin-top:14px;background:${C.greenBg};border:1.5px solid ${C.greenBd};border-radius:14px;padding:14px 15px">
    <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer">
      <input type="checkbox" name="consent" value="1" required style="margin-top:2px;width:18px;height:18px;accent-color:${C.green};flex:none">
      <span style="font-size:12.5px;font-weight:700;color:${C.greenDark};line-height:1.55">본인은 <b>보호자</b>이며 자녀 기록의 등록·보관에 동의합니다. <b>(필수)</b></span>
    </label>
    <div style="margin-top:10px;font-size:11.5px;color:${C.greenDark};opacity:.85;line-height:1.7">
      · 이름은 <b>기록과 분리해서</b> 보관합니다<br>
      · 광고는 자녀 데이터에 접근할 수 없습니다<br>
      · 언제든 <b>원본까지 전부 삭제</b>할 수 있습니다
    </div>
    <a href="/privacy" style="margin-top:9px;display:inline-block;font-size:11.5px;font-weight:800;color:${C.green}">개인정보처리방침 ›</a>
  </div>`;
}

// freeOpen: 이 학교가 아직 개학 전인가. 문구가 갈린다(회신4 Q3) — 개방 중엔 "1주일 체험"이 사실과 다르다.
export function registerChildPage(school, gradeClassMap = {}, isPaid = false, freeOpen = false, openUntil = "", recordsOn = false) {
  const badge = freeOpen
    ? `🎁 개학 전까지 무료`
    : `🎁 지금 등록하면 1주일 무료`;
  // ⚠️ 예전 문구는 "이름은 받지 않아요"였다 — 이름 입력칸을 바로 아래 두면서 그 문구를 남겨두면
  //    화면 자체가 거짓말이 된다(회신4 Q1으로 이름 수집이 확정됨). 2026-07-19 정정.
  const lead = `${school ? `<b>${schoolNameHtml(school.name)}</b> · ` : ""}자녀 정보를 입력하면 <b>결제 없이 바로</b> 시간표·학사일정·전체 급식이 열리고 광고가 사라져요.`;
  // ⚠ 체험 기간은 코드가 정본이다(TRIAL_DAYS = 7, api_records.js). 약관 제5조도 7일.
  //    2026-08-10 대표님 확정으로 14일 → **7일**. 앱·웹·약관·FAQ 를 한 번에 맞췄다.
  //    여기만 「1주일」이라 화면과 실제가 어긋나 있었다 — 2026-08-01 맞춤.
  const cta = freeOpen ? "무료로 시작하기" : "7일 무료로 시작하기";
  const footNote = freeOpen
    ? `· <b>${school ? schoolNameHtml(school.name) : "우리 아이 학교"} 개학(${fmtDate(openUntil)})</b> 전까지 모든 기능이 무료예요. 그 뒤에는 7일 무료 체험이 이어집니다.`
    : `· 7일 후 자동으로 다시 잠기며, <b>자동 결제되지 않아요</b>. 계속 쓰려면 그때 직접 결제하시면 됩니다.`;

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px;max-width:100%;margin:0 auto">
    <a href="javascript:history.back()" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <div style="margin-top:8px;display:inline-flex;align-items:center;gap:6px;background:${C.greenBg};color:${C.greenDark};font-size:12px;font-weight:800;padding:5px 11px;border-radius:20px">${badge}</div>
    <h1 style="margin:12px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">자녀 등록</h1>
    <p style="margin:8px 0 0;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:${C.muted2};line-height:1.6">${lead}</p>
    <form method="post" action="/register-child" style="margin-top:20px">
      <input type="hidden" name="school_slug" value="${school ? escapeHtml(school.slug) : ""}">
      ${school ? "" : `<div style="margin-bottom:10px"><input type="text" name="school_slug_manual" placeholder="학교 검색이 필요해요 (홈에서 학교를 먼저 찾아주세요)" style="width:100%;padding:13px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px" readonly></div>`}
      <div style="display:flex;gap:8px">
        ${gradeSelect(school && school.school_kind, "grade", "", "id=\"regGrade\"")}
        ${classSelect("class_name", "", "id=\"regClass\"", 15, "학년 먼저 선택")}
      </div>
      <!-- 이름과 별명을 분리한다(회신4 Q1=A / B-9 결정).
           · 이름(name)  → identifiers 테이블에만 저장. 기록 타임라인·업로드 화면에서만 조인 표시.
           · 별명(nickname) → children에 저장. 헤더 스위처·커뮤니티 표시용. "첫째/둘째/셋째" 자동 채움.
           목업 ④는 이름 칸 하나만 그렸으나 그건 목업이 B-9 결정을 빠뜨린 것 — 절대 규칙이 목업에 우선한다. -->
      ${recordsOn ? `<div style="margin-top:8px"><input type="text" name="name" placeholder="자녀 이름 (예: 김서준)" required maxlength="20" style="width:100%;padding:13px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px"></div>
      <div style="margin-top:5px;font-size:11.5px;color:${C.muted};line-height:1.55">자녀 이름은 기록 화면에서만 보이고, 다른 학부모에게는 별명으로 표시됩니다. 기록과 분리해 안전하게 보관합니다.</div>` : ""}
      <div style="margin-top:8px"><input type="text" name="nickname" id="regNick" placeholder="별명 (예: 첫째)" required maxlength="20" style="width:100%;padding:13px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px"></div>
      ${recordsOn ? consentBlock() : ""}
      <button type="submit" style="margin-top:16px;width:100%;padding:15px;border:none;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:700">${cta}</button>
    </form>
    <script>(function(){
      // 학년별 실제 학급수(학교알리미 데이터). 학년 선택 시 반 옵션을 그 학년 학급수로 제한.
      var MAP=${JSON.stringify(gradeClassMap)};
      var gsel=document.getElementById('regGrade'), csel=document.getElementById('regClass');
      if(!gsel||!csel) return;
      function rebuild(){
        var g=gsel.value, cur=csel.value;
        // 학년 미선택이면 반을 못 정한다 — 예전엔 MAP[''] 미스로 폴백 15가 떠서 "모든 학교가 1~15반"으로 보였다.
        if(!g){ csel.innerHTML='<option value="">학년 먼저 선택</option>'; csel.disabled=true; return; }
        csel.disabled=false;
        // 그 학년의 실제 학급수(학교알리미 → 없으면 NEIS classInfo). 둘 다 없을 때만 15까지 폴백.
        var max=MAP[g]||15;
        var html='<option value="">반</option>';
        for(var i=1;i<=max;i++){ html+='<option value="'+i+'"'+(String(cur)===String(i)?' selected':'')+'>'+i+'반</option>'; }
        csel.innerHTML=html;
      }
      gsel.addEventListener('change', rebuild);
      rebuild();
      // 별명 자동 채움 — 사용자가 비워두면 "첫째/둘째/셋째"가 들어간다(회신4 Q1=A).
      // 이름을 별명으로 쓰면 실명이 헤더·커뮤니티에 노출돼 식별자 분리 원칙이 깨진다.
      var nick=document.getElementById('regNick');
      if(nick && !nick.value){ nick.value=${JSON.stringify(["첫째", "둘째", "셋째"])}[Math.min(2, ${Number(isPaid ? 0 : 0)})] || '첫째'; }
    })();</script>
    <a href="/" style="margin-top:10px;display:block;text-align:center;padding:12px;border-radius:12px;background:#fff;border:1px solid ${C.border};color:${C.inkSoft};font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700">🔎 다른 학교 찾기</a>
    <div style="margin-top:12px;font-size:11.5px;color:${C.muted};line-height:1.6">${footNote}<br>· <b>이용권 하나로 자녀 3명까지</b> 등록할 수 있어요.</div>
  </div>`;
  return layout({ title: "자녀 등록 — 아이서랍", body, noShare: true });
}

// ================= 온보딩 (자녀 등록 완료 직후) =================
// 등록완료 → 알림 받기(권한요청+저장) → PWA 설치 안내 → 학교로. "나중에"면 바로 학교로.
export function onboardingPage(school) {
  const schoolHref = school ? `/school/${encodeURIComponent(school.slug)}/` : "/mypage";
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:30px 20px;max-width:100%;margin:0 auto">
    <div id="obStep1">
      <div style="text-align:center"><div style="font-size:52px">🎉</div><h1 style="margin:12px 0 0;font-size:23px;font-weight:800;color:${C.ink}">등록 완료!</h1><p style="margin:8px 0 0;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:${C.muted2};line-height:1.6">${school ? `<b>${schoolNameHtml(school.name)}</b> 급식·시간표가 열렸습니다.` : ""}</p></div>
      <!-- 무료 개방 안내(2/3) — 등록 직후가 기대 설정의 최적 시점(전략 회신 Q4). -->
      <div style="margin-top:16px;background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:14px;padding:14px 16px;text-align:center">
        <div style="font-size:14px;font-weight:800;color:${C.greenDark};line-height:1.5">🎁 개학 전까지 모든 기능이 무료예요</div>
        <div style="margin-top:5px;font-size:12.5px;color:${C.greenDark};opacity:.85;line-height:1.6">방학 동안 우리 아이 기록을 쌓아보세요.</div>
      </div>
      <div style="margin-top:24px;background:#fff;border:1px solid ${C.border};border-radius:18px;padding:20px;text-align:center">
        <div style="font-size:30px">🔔</div>
        <div style="margin-top:8px;font-size:15.5px;font-weight:800;color:${C.ink}">매일 아침 알림 받으실래요?</div>
        <div style="margin-top:6px;font-size:12.5px;color:${C.muted};line-height:1.6">오늘 급식·시간표·챙길 일정을 아침에 자동으로 보내드려요.</div>
        <button type="button" onclick="obEnableNotif()" style="margin-top:16px;width:100%;padding:14px;border:none;border-radius:12px;background:${C.green};color:#fff;font-size:15px;font-weight:800;cursor:pointer">네, 알림 받을래요</button>
        <a href="${schoolHref}" style="margin-top:9px;display:block;text-align:center;padding:13px;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700;color:${C.muted2}">나중에 할게요</a>
      </div>
    </div>
    <div id="obStep2" style="display:none">
      <div style="text-align:center"><div style="font-size:48px">📲</div><h1 style="margin:12px 0 0;font-size:21px;font-weight:800;color:${C.ink}">홈 화면에 추가하면 끝!</h1><p style="margin:8px 0 0;font-size:13px;color:${C.muted2};line-height:1.6">알림을 받으려면 홈 화면에 추가(앱 설치)가 필요해요.</p></div>
      ${pwaInstallGuide()}
      <a href="${schoolHref}" style="margin-top:16px;display:block;text-align:center;padding:15px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800">시작하기 →</a>
    </div>
  </div>
  <script>
    function obEnableNotif(){
      function go(){ fetch('/mypage/notifications',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'action=on'}).finally(function(){ document.getElementById('obStep1').style.display='none'; document.getElementById('obStep2').style.display='block'; window.scrollTo(0,0); }); }
      if(typeof Notification==='undefined'||Notification.permission==='granted'){ go(); return; }
      if(Notification.permission==='denied'){ alert('브라우저에서 알림이 차단돼 있어요. 나중에 설정 → 알림에서 허용할 수 있어요.'); go(); return; }
      Notification.requestPermission().then(function(){ go(); });
    }
  </script>`;
  return layout({ title: "등록 완료 — 아이서랍", body });
}

// 간단 안내(팝업형) — 무료체험 1명 제한 등. backHref로 돌아가기.
// cta(선택): {href, label} — 주면 초록 주버튼이 cta로 가고, backHref는 아래 보조 텍스트 링크("돌아가기")가 된다.
export function noticePage(title, desc, backHref = "/", icon = "ℹ️", cta = null) {
  const buttons = cta
    ? `<a href="${cta.href}" style="margin-top:18px;display:block;padding:14px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800">${escapeHtml(cta.label)}</a>
       <a href="${backHref}" style="margin-top:9px;display:block;padding:10px;font-size:13px;font-weight:600;color:${C.muted2}">돌아가기</a>`
    : `<a href="${backHref}" style="margin-top:18px;display:block;padding:14px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:700">확인</a>`;
  const body = `
  <div style="min-height:100vh;background:${C.bg};display:flex;align-items:center;justify-content:center;padding:24px;max-width:100%;margin:0 auto">
    <div style="background:#fff;border:1px solid ${C.border};border-radius:20px;padding:26px 22px;text-align:center;box-shadow:0 10px 30px rgba(20,39,74,.08);width:100%">
      <div style="font-size:38px">${icon}</div>
      <h1 style="margin:12px 0 0;font-size:19px;font-weight:800;color:${C.ink};letter-spacing:-.02em">${escapeHtml(title)}</h1>
      <p style="margin:9px 0 0;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:${C.muted2};line-height:1.6">${desc}</p>
      ${buttons}
    </div>
  </div>`;
  return layout({ title: `${title} — 아이서랍`, body });
}

// ================= 자녀 등록 이중 확인(요약 → 재확인) =================
// 학교·학년·반이 정확해야 유료 시간표 공유가 올바르게 매칭됨 → 등록 전 요약 재확인.
export function registerConfirmPage(school, data) {
  const { grade, className, nickname, ordinal, name, consent } = data;
  // 이번에 등록하는 자녀가 몇 번째인지(자녀1/2/3). 확인 문구에 노출.
  const childLabel = ordinal >= 1 ? `자녀${ordinal}` : "자녀";
  const row = (label, value) => `
    <div style="display:flex;gap:12px;padding:13px 0;border-bottom:1px solid #F0F2F5">
      <span style="width:60px;flex:none;font-size:13px;color:${C.muted};font-weight:600">${label}</span>
      <span style="font-size:15px;color:${C.ink};font-weight:700">${value}</span>
    </div>`;
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px;max-width:100%;margin:0 auto">
    <a href="javascript:history.back()" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <div style="margin-top:12px;display:inline-flex;align-items:center;gap:6px;background:${C.greenBg};color:${C.greenDark};font-size:12px;font-weight:800;padding:5px 11px;border-radius:20px">👶 ${childLabel} 등록</div>
    <h1 style="margin:8px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">이 정보가 맞나요?</h1>
    <p style="margin:8px 0 0;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);color:${C.muted2};line-height:1.6">등록 후 <b>학교·학년·반은 잠기고 별명만 수정</b>할 수 있어요. 우리 반 시간표·급식이 정확히 매칭되도록 다시 한 번 확인해 주세요.</p>
    <div style="margin-top:18px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:4px 18px">
      ${row("학교", schoolNameHtml(school.name))}
      ${row("학년", `${escapeHtml(grade)}학년`)}
      ${row("반", className ? `${escapeHtml(className)}반` : '<span style="color:'+C.muted+';font-weight:500">미입력</span>')}
      ${name ? row("이름", escapeHtml(name)) : ""}
      <div style="display:flex;gap:12px;padding:13px 0">
        <span style="width:60px;flex:none;font-size:13px;color:${C.muted};font-weight:600">별명</span>
        <span style="font-size:15px;color:${C.ink};font-weight:700">${escapeHtml(nickname)}</span>
      </div>
    </div>
    <form method="post" action="/register-child" style="margin-top:18px" onsubmit="return uiConfirm(event, '${childLabel}을 등록하시겠습니까?\\n${escapeHtml(school.name)} · ${escapeHtml(grade)}학년${className ? " " + escapeHtml(className) + "반" : ""}\\n등록 후 학교·학년·반은 변경할 수 없어요.', '등록하기')">
      <input type="hidden" name="school_slug" value="${escapeHtml(school.slug)}">
      <input type="hidden" name="grade" value="${escapeHtml(grade)}">
      <input type="hidden" name="class_name" value="${escapeHtml(className || "")}">
      <input type="hidden" name="nickname" value="${escapeHtml(nickname)}">
      <!-- 1단계에서 받은 이름·동의를 2단계로 이어 넘긴다. 빠뜨리면 확인 화면을 거치는 순간
           실명과 동의 기록이 통째로 유실된다(2026-07-19 검증 중 발견). -->
      <input type="hidden" name="name" value="${escapeHtml(name || "")}">
      <input type="hidden" name="consent" value="${consent ? "1" : ""}">
      <input type="hidden" name="confirmed" value="1">
      <button type="submit" style="width:100%;padding:15px;border:none;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:700">네, 이 정보로 등록할게요</button>
    </form>
    <a href="/register-child?school=${encodeURIComponent(school.slug)}" style="margin-top:10px;display:block;text-align:center;padding:13px;border-radius:13px;background:#fff;border:1px solid ${C.border};color:${C.inkSoft};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:700">← 다시 입력하기</a>
  </div>`;
  return layout({ title: "등록 정보 확인 — 아이서랍", body });
}

// ================= 자녀 정보 수정(별명 자유 / 학교·학년·반 잠금) =================
// gradeClassMap = 그 학교의 학년별 실제 학급수({"1":4,...}). 진급 폼의 반 선택을 다음 학년 실제 학급수로 제한.
export function childEditPage(child, gradeClassMap = {}) {
  const maxGrade = maxGradeOf(child.school_kind);
  const nextGrade = Number(child.grade) + 1;
  // 새 학년도 전환: 다음 학년만, 1회만. 이미 썼거나 최고학년이면 안내로 대체.
  let promoteSection;
  if (child.grade_promoted) {
    promoteSection = `<div style="margin-top:18px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px 18px;font-size:12.5px;color:${C.muted};line-height:1.6">✅ 이미 새 학년(${escapeHtml(child.grade)}학년)으로 변경했어요. 학년 전환은 자녀당 1회만 가능합니다.</div>`;
  } else if (nextGrade > maxGrade) {
    promoteSection = `<div style="margin-top:18px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px 18px;font-size:12.5px;color:${C.muted};line-height:1.6">현재 최고 학년이라 학년 전환 대상이 아니에요. 상급학교 진학 시 새로 등록해 주세요.</div>`;
  } else {
    promoteSection = `
    <details style="margin-top:18px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:14px 18px">
      <summary style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:700;color:${C.inkSoft};cursor:pointer;list-style:none">새 학년이 됐나요? (${escapeHtml(child.grade)}학년 → ${nextGrade}학년)</summary>
      <p style="margin:10px 0 0;font-size:12px;color:${C.muted};line-height:1.6">진급하면 <b>바로 다음 학년</b>으로만 바꿀 수 있고, <b>1회만</b> 가능합니다. 새 학년의 <b>반을 반드시 선택</b>해 주세요(진급하면 반 편성이 새로 되기 때문에 기본값을 비워뒀어요).</p>
      <form method="post" action="/child/edit" style="margin-top:12px" onsubmit="return promoteSubmit(event)">
        <input type="hidden" name="id" value="${escapeHtml(child.id)}">
        <input type="hidden" name="action" value="promote">
        <input type="hidden" name="nickname" value="${escapeHtml(child.nickname)}">
        <input type="hidden" name="grade" value="${nextGrade}">
        <div style="display:flex;gap:8px;align-items:center">
          <div style="flex:1;min-width:0;padding:12px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px;background:#F5F8FB;color:${C.ink};font-weight:700;text-align:center">${nextGrade}학년</div>
          ${classSelect("class_name", "", "id=\"promoteClass\"", gradeClassMap[String(nextGrade)] || 15)}
        </div>
        <button type="submit" style="margin-top:12px;width:100%;padding:13px;border:1px solid #E0B4B4;border-radius:12px;background:#FCF2F2;color:#B0417A;font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:800">${nextGrade}학년으로 변경하기</button>
      </form>
      <script>
        // 반 미선택 시 브라우저 기본 문구("목록에서 항목을 선택하세요")는 왜 필요한지 설명을 못 해
        // 앱 톤의 커스텀 안내로 대체(required 미사용). 선택했으면 1회성 작업이라 확인 모달로 재확인.
        function promoteSubmit(e){
          var sel=document.getElementById('promoteClass');
          if(!sel.value){
            e.preventDefault();
            uiAlert('새 학년의 반을 선택해 주세요.\\n진급하면 반 편성이 새로 되기 때문에 꼭 골라야 해요.');
            try{ sel.focus(); }catch(_){}
            return false;
          }
          return uiConfirm(e, '${escapeHtml(child.nickname)} 자녀를 ${nextGrade}학년 ' + sel.value + '반으로 변경할까요?\\n학년 전환은 1회만 가능해요.', '변경하기');
        }
      </script>
    </details>`;
  }
  const lockedRow = (label, value) => `
    <div style="display:flex;gap:12px;padding:13px 0;border-bottom:1px solid #F0F2F5;align-items:center">
      <span style="width:52px;flex:none;font-size:13px;color:${C.muted};font-weight:600">${label}</span>
      <span style="flex:1;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);color:${C.ink};font-weight:700">${value}</span>
      <span style="flex:none;font-size:15px;color:#B7BFCC">🔒</span>
    </div>`;
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
      <a href="/school/${encodeURIComponent(child.school_slug)}/?child=${escapeHtml(child.id)}" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
      <div style="display:flex;gap:8px">
        <a href="/mypage/children" style="font-size:12.5px;font-weight:800;color:${C.muted2};background:#fff;border:1px solid ${C.border};padding:8px 12px;border-radius:11px">자녀 관리</a>
        <a href="/school/${encodeURIComponent(child.school_slug)}/?child=${escapeHtml(child.id)}" style="font-size:12.5px;font-weight:800;color:${C.green};background:${C.greenBg};border:1px solid ${C.greenBd};padding:8px 13px;border-radius:11px">시간표 보기 →</a>
      </div>
    </div>
    <h1 style="margin:12px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">자녀 정보 수정</h1>
    <p style="margin:8px 0 0;font-size:13px;color:${C.muted2};line-height:1.6">학교·학년·반은 정확한 시간표 매칭을 위해 잠겨 있어요. 별명은 자유롭게 바꿀 수 있습니다.</p>

    <div style="margin-top:16px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:4px 18px">
      ${lockedRow("학교", escapeHtml(child.school_name))}
      ${lockedRow("학년", `${escapeHtml(child.grade)}학년`)}
      ${lockedRow("반", child.class_name ? `${escapeHtml(child.class_name)}반` : '<span style="color:'+C.muted+';font-weight:500">미입력</span>')}
    </div>

    <form method="post" action="/child/edit" style="margin-top:16px">
      <input type="hidden" name="id" value="${escapeHtml(child.id)}">
      <label style="font-size:13px;color:${C.muted};font-weight:700">별명</label>
      <input type="text" name="nickname" value="${escapeHtml(child.nickname)}" required maxlength="20" style="margin-top:6px;width:100%;padding:13px;border:1.5px solid #DFE3EA;border-radius:12px;font-size:15px">
      <button type="submit" style="margin-top:14px;width:100%;padding:15px;border:none;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:700">별명 저장</button>
    </form>

    ${promoteSection}
  </div>`;
  return layout({ title: "자녀 정보 수정 — 아이서랍", body });
}

// 기간별 가격(원) — 2026-07-19 단일가화. 인원별 추가 과금 폐지 → 이용권 하나로 자녀 3명까지.
// index.js의 PAY_PRICES와 같은 값을 유지할 것(표시=서버 계산 일치).
const PAY_PRICE = { 1: 3500, 3: 9500, 6: 16800, 12: 29400 };
const PAY_DISCOUNT = { 1: "", 3: "10% 할인", 6: "20% 할인", 12: "30% 할인" };

// ================= 결제 페이지 (자녀수·기간·수단 선택 + 총액 자동계산 + 확인) =================
export function subscribePage(childCount = 1) {
  const cc = Math.min(3, Math.max(1, childCount || 1));
  // 라디오는 시각적으로 숨기고 옆의 스타일드 span이 라벨 역할 — span 텍스트(o.t)는 항상 보이고,
  // 접근성/자동화 도구를 위해 input에도 aria-label(HTML 태그 제거한 순수 텍스트)을 붙인다.
  const seg = (name, opts, sel) => opts.map((o) => {
    const plain = String(o.t).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    return `<label style="flex:1"><input type="radio" name="${name}" value="${o.v}" aria-label="${escapeHtml(plain)}" ${String(o.v) === String(sel) ? "checked" : ""} style="display:none" onchange="calcPay()"><span class="seg" style="display:block;text-align:center;padding:11px 4px;border-radius:11px;border:1.5px solid ${C.border};background:#fff;font-size:13px;font-weight:800;color:${C.muted2};cursor:pointer;line-height:1.3">${o.t}</span></label>`;
  }).join("");
  const periodOpts = [1, 3, 6, 12].map((m) => ({ v: m, t: `${m}개월${PAY_DISCOUNT[m] ? `<br><span style='font-size:9.5px;color:${C.green}'>${PAY_DISCOUNT[m]}</span>` : ""}` }));
  const methodOpts = [{ v: "card", t: "카드" }, { v: "phone", t: "휴대폰" }, { v: "vbank", t: "가상계좌" }];

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <a href="javascript:history.back()" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <h1 style="margin:12px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">이용권 결제</h1>
    <p style="margin:8px 0 0;font-size:13px;color:${C.muted2};line-height:1.6"><b>이용권 하나로 자녀 3명까지</b> 쓸 수 있어요. 기간이 길수록 저렴합니다.</p>
    <div style="margin-top:16px;background:linear-gradient(135deg,#EAF6EF,#E0F0E8);border:1px solid ${C.greenBd};border-radius:14px;padding:14px 16px">
      <div style="font-size:13.5px;font-weight:800;color:${C.greenDark}">🎉 베타 기간 — 모든 기능 무료</div>
      <div style="margin-top:5px;font-size:12px;color:${C.muted2};line-height:1.6">지금은 베타 서비스라 <b>결제 없이 전 기능을 무료</b>로 쓰실 수 있어요. 아래 요금은 정식 오픈 시 적용될 <b>예정 가격</b>이에요.</div>
    </div>
    <form method="post" action="/pay" onsubmit="return confirmPay(event)">
      <!-- 자녀 수 선택 제거(2026-07-19) — 인원별 추가 과금 폐지로 가격이 인원과 무관해졌다.
           서버가 child_count를 계속 기록하므로(이력 통계용) 현재 등록 자녀 수를 hidden으로 넘긴다. -->
      <input type="hidden" name="child_count" value="${cc}">
      <div style="margin-top:18px;background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:12px;padding:12px 14px;font-size:12.5px;color:${C.greenDark};font-weight:700;line-height:1.55">👨‍👩‍👧‍👦 이용권 하나로 <b>자녀 3명까지</b> — 인원이 늘어도 추가 요금이 없어요</div>
      <div style="margin-top:16px;font-size:12.5px;font-weight:800;color:${C.ink}">기간</div>
      <div style="margin-top:8px;display:flex;gap:7px">${seg("months", periodOpts, 1)}</div>
      <div style="margin-top:16px;font-size:12.5px;font-weight:800;color:${C.ink}">결제 수단</div>
      <div style="margin-top:8px;display:flex;gap:7px">${seg("method", methodOpts, "card")}</div>
      <label style="margin-top:14px;display:flex;align-items:center;gap:8px;font-size:12.5px;color:${C.inkSoft};font-weight:600"><input type="checkbox" name="auto_renew" value="1" style="width:16px;height:16px"> 자동 구독 신청(만료 시 자동 결제) · 선택</label>

      <div style="margin-top:18px;background:#14274A;border-radius:16px;padding:18px;color:#fff;display:flex;align-items:center;justify-content:space-between">
        <div><div style="font-size:12px;color:rgba(255,255,255,.6);font-weight:600">총 결제 금액</div><div id="payTotal" style="font-size:26px;font-weight:800;letter-spacing:-.02em;margin-top:2px">3,500원</div></div>
        <div id="payDesc" style="font-size:11.5px;color:rgba(255,255,255,.6);text-align:right;line-height:1.5">1개월 · 자녀 3명까지</div>
      </div>
      <button type="button" disabled style="margin-top:14px;width:100%;padding:15px;border:none;border-radius:13px;background:#C4CBD6;color:#fff;font-size:15px;font-weight:800;cursor:not-allowed">베타 기간에는 결제가 필요 없어요</button>
    </form>
    <div style="margin-top:12px;font-size:11px;color:${C.muted};line-height:1.6">· 베타 기간에는 <b>결제 없이</b> 모든 기능이 열려 있어요. 정식 결제(카드 등)는 정식 오픈 때 제공됩니다.<br>· 위 금액은 정식 오픈 시 <b>예정 가격</b>이며, 변동될 수 있어요.</div>
  </div>
  <script>
    var PRICE=${JSON.stringify(PAY_PRICE)};
    function calcPay(){
      var m=+(document.querySelector('input[name=months]:checked')||{}).value||1;
      var amt=PRICE[m]||0;
      document.getElementById('payTotal').textContent=amt.toLocaleString()+'원';
      document.getElementById('payDesc').textContent=m+'개월 · 자녀 3명까지';
      document.querySelectorAll('.seg').forEach(function(s){var i=s.previousElementSibling;if(i&&i.checked){s.style.borderColor='${C.green}';s.style.background='${C.greenBg}';s.style.color='${C.greenDark}';}else{s.style.borderColor='${C.border}';s.style.background='#fff';s.style.color='${C.muted2}';}});
    }
    function confirmPay(e){e.preventDefault();var t=document.getElementById('payTotal').textContent;var f=e.target;uiConfirmCb('총 '+t+' 결제하시겠어요?', function(){ f.submit(); }, '결제하기');return false;}
    calcPay();
  </script>`;
  return layout({ title: "이용권 결제 — 아이서랍", body });
}

// ================= 베타 의견 보내기 =================
// 특정 학교와 무관한 서비스 전반 의견(불편·제안·칭찬) 접수 — POST /feedback → beta_feedback 테이블.
export function feedbackPage(sent = false) {
  const catOpts = ["불편·버그", "기능 제안", "칭찬", "기타"].map(
    (c, i) => `<label style="flex:1"><input type="radio" name="category" value="${c}" ${i === 0 ? "checked" : ""} style="display:none"><span class="fbseg" style="display:block;text-align:center;padding:11px 4px;border-radius:11px;border:1.5px solid ${C.border};background:#fff;font-size:12.5px;font-weight:800;color:${C.muted2};cursor:pointer">${c}</span></label>`
  ).join("");
  const inner = sent
    ? `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:34px 20px;text-align:center">
        <div style="font-size:44px">💌</div>
        <div style="margin-top:12px;font-size:16px;font-weight:800;color:${C.ink}">의견이 접수됐어요!</div>
        <div style="margin-top:6px;font-size:13px;color:${C.muted};line-height:1.6">보내주신 의견은 하나하나 읽고<br>서비스 개선에 반영할게요. 고맙습니다.</div>
        <div style="margin-top:18px;display:flex;gap:8px;justify-content:center">
          <a href="/feedback" style="padding:12px 18px;border-radius:12px;background:${C.greenBg};border:1px solid ${C.greenBd};color:${C.greenDark};font-size:13.5px;font-weight:800">한 건 더 보내기</a>
          <a href="/" style="padding:12px 18px;border-radius:12px;background:${C.green};color:#fff;font-size:13.5px;font-weight:800">홈으로</a>
        </div>
      </div>`
    : `<form method="post" action="/feedback">
        <div style="font-size:12.5px;font-weight:800;color:${C.ink}">어떤 의견인가요?</div>
        <div style="margin-top:8px;display:flex;gap:7px">${catOpts}</div>
        <div style="margin-top:16px;font-size:12.5px;font-weight:800;color:${C.ink}">내용</div>
        <textarea name="message" required maxlength="1000" rows="6" placeholder="예) 시간표에서 ○○이 불편해요 / 이런 기능이 있으면 좋겠어요" style="margin-top:8px;width:100%;box-sizing:border-box;padding:13px 14px;border:1.5px solid ${C.border};border-radius:13px;font-size:clamp(14px, 12.5px + 0.4vw, 16px);color:${C.ink};line-height:1.6;font-family:inherit;outline:none;resize:vertical;background:#fff"></textarea>
        <button type="submit" style="margin-top:14px;width:100%;padding:15px;border:none;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800;cursor:pointer;font-family:inherit">의견 보내기</button>
        <div style="margin-top:10px;font-size:11px;color:${C.muted};line-height:1.6">· 이름·연락처는 받지 않아요. 답장이 필요한 문의는 서비스 안정화 후 고객센터에서 받을 예정이에요.</div>
      </form>
      <script>
        document.querySelectorAll('input[name=category]').forEach(function(i){ i.addEventListener('change', paintFb); });
        function paintFb(){ document.querySelectorAll('.fbseg').forEach(function(s){ var i=s.parentElement.querySelector('input'); if(i.checked){ s.style.borderColor='${C.green}'; s.style.background='${C.greenBg}'; s.style.color='${C.greenDark}'; } else { s.style.borderColor='${C.border}'; s.style.background='#fff'; s.style.color='${C.muted2}'; } }); }
        paintFb();
      </script>`;
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <a href="javascript:history.back()" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <h1 style="margin:12px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">베타 의견 보내기</h1>
    <p style="margin:8px 0 18px;font-size:13px;color:${C.muted2};line-height:1.6">지금은 <b>베타 기간</b>이에요. 불편한 점, 있었으면 하는 기능, 뭐든 편하게 들려주세요.</p>
    ${inner}
  </div>`;
  return layout({ title: "베타 의견 보내기 — 아이서랍", body });
}

// ================= 홍보 페이지 (서비스 소개 랜딩) =================
export function aboutPage() {
  const priceRows = [1, 3, 6, 12].map((m) => `
    <tr style="border-bottom:1px solid ${C.border}">
      <td style="padding:11px 8px;font-weight:800;color:${C.ink};font-size:13px">${m}개월${PAY_DISCOUNT[m] ? `<div style="font-size:10px;color:${C.green};font-weight:700">${PAY_DISCOUNT[m]}</div>` : ""}</td>
      <td style="padding:11px 8px;text-align:right;color:${C.inkSoft};font-size:12.5px;font-weight:700">${PAY_PRICE[m].toLocaleString()}원</td>
    </tr>`).join("");
  const cmp = (label, free, paid) => `<tr style="border-bottom:1px solid ${C.border}"><td style="padding:10px 8px;font-size:12.5px;color:${C.inkSoft};font-weight:600">${label}</td><td style="padding:10px 8px;text-align:center;font-size:13px">${free}</td><td style="padding:10px 8px;text-align:center;font-size:13px;background:${C.greenBg}">${paid}</td></tr>`;
  const body = `
  <div>
    <div style="background:linear-gradient(170deg,#132445 0%,#14274A 52%,#1C3B69 100%);color:#fff;padding:26px 24px 34px">
      <div style="font-size:13px;font-weight:700;color:#7FE0B4">NEIS·학교알리미 공공데이터 기반</div>
      <h1 style="margin:12px 0 0;font-size:clamp(27px, 21px + 1.6vw, 33px);font-weight:800;line-height:1.28;letter-spacing:-.03em">매달 학교 홈페이지<br>뒤지지 마세요</h1>
      <p style="margin:14px 0 0;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);color:rgba(255,255,255,.75);line-height:1.6">급식·시간표·학사일정을 <b style="color:#fff">매일 자동으로</b> 챙겨드려요. 자녀만 등록하면 우리 반 기준으로 딱 맞춰서.</p>
      <a href="/" style="margin-top:20px;display:inline-block;padding:13px 24px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800">학교 검색하고 시작하기</a>
    </div>
    <div style="max-width:100%;margin:0 auto;padding:22px 18px">
      <h2 style="margin:0;font-size:clamp(17px, 14.5px + 0.7vw, 20px);font-weight:800;color:${C.ink}">무료로 먼저 써보세요</h2>
      <p style="margin:6px 0 12px;font-size:13px;color:${C.muted2};line-height:1.6">자녀 등록하면 <b>7일 무료 체험</b>. 자동 결제 없어요.</p>
      <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">
          <tr style="background:#F7F9FB"><th style="padding:9px 8px;text-align:left;font-size:11px;color:${C.muted}">항목</th><th style="padding:9px 8px;font-size:11px;color:${C.muted}">무료</th><th style="padding:9px 8px;font-size:11px;color:${C.greenDark};background:${C.greenBg}">유료</th></tr>
          ${cmp("오늘 급식", "○", "○")}
          ${cmp("주간 전체 급식", "✕", "○")}
          ${cmp("우리 반 시간표", "잠금", "○ + 개인일정")}
          ${cmp("학사일정 전체", "티저", "○ + 알림")}
          ${cmp("광고", "있음", "제거")}
        </table>
      </div>
      <h2 style="margin:24px 0 6px;font-size:clamp(17px, 14.5px + 0.7vw, 20px);font-weight:800;color:${C.ink}">이용권 가격 <span style="font-size:12px;font-weight:800;color:${C.greenDark};background:${C.greenBg};padding:2px 8px;border-radius:6px;vertical-align:middle">정식 오픈 예정가</span></h2>
      <p style="margin:0 0 12px;font-size:13px;color:${C.muted2}"><b style="color:${C.greenDark}">지금은 베타라 전부 무료</b>예요. 아래는 정식 오픈 시 적용될 예정 가격이며 변동될 수 있어요. <b>이용권 하나로 자녀 3명까지</b> 쓸 수 있어요.</p>
      <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">
          <tr style="background:#F7F9FB"><th style="padding:9px 8px;text-align:left;font-size:11px;color:${C.muted}">기간</th><th style="padding:9px 8px;text-align:right;font-size:11px;color:${C.muted}">금액 (자녀 3명까지)</th></tr>
          ${priceRows}
        </table>
      </div>
      <a href="/" style="margin-top:20px;display:block;text-align:center;padding:15px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800">지금 시작하기</a>
    </div>
  </div>`;
  return layout({ title: "아이서랍 — 서비스 소개", body });
}

/* ================= 고객센터 (공개) =================
   플레이 스토어 등록에는 **누구나 볼 수 있는 지원 URL**이 필요하다 — 로그인 뒤에 숨은 화면은 못 쓴다.
   ⚠ 문안은 앱(app/www/app.js FAQ)과 **같은 것**이다. 한쪽만 고치면 두 곳이 다른 말을 한다.
   답이 전부 «지금 앱이 실제로 하는 일»이어야 한다는 규칙도 같다. */
const FAQ_WEB = [
  ["시작하기", [
    ["자녀는 어떻게 등록하나요?", "내 정보 → 자녀 추가에서 학교 이름을 검색하고 학년·반을 고르면 됩니다. 전국 초·중·고를 이름 일부만으로 찾을 수 있어요."],
    ["자녀를 여러 명 등록할 수 있나요?", "네. 홈 위쪽 자녀 이름을 눌러 바꿉니다. 앱을 켰을 때 먼저 열릴 자녀는 홈 편집에서 정할 수 있어요."],
    ["학년이 올라가면 어떻게 하나요?", "새 학년이 되면 앱이 먼저 물어봅니다. 확인만 누르면 학년이 올라가고, 반은 내 정보에서 고칩니다."],
  ]],
  ["급식·시간표·일정", [
    ["급식이 실제와 달라요.", "급식·시간표·학사일정은 학교가 공공데이터(NEIS)에 올린 자료를 그대로 보여줍니다. 학교 사정으로 바뀌면 앱 쪽 반영이 늦을 수 있어요. 화면의 오류 신고로 알려주시면 확인합니다."],
    ["시간표가 비어 있어요.", "방학이거나 학교가 아직 올리지 않은 경우입니다. 개학 뒤에도 비어 있으면 문의해 주세요. 칸을 눌러 직접 채워 넣을 수도 있습니다."],
    ["공휴일이 일정에 뜨는 게 거슬려요.", "홈 편집 → 「일정에 공휴일」을 끄면 홈에서 사라집니다. 학교탭 달력에는 그대로 남아요."],
    ["일정 알림은 어떻게 켜나요?", "일정을 넣을 때 알림 시각을 함께 고르면 됩니다(정시·10분 전·30분 전·1시간 전·전날). 지난 시각은 알림이 가지 않아요."],
  ]],
  ["기록(서랍)", [
    ["기록한 사진은 어디에 저장되나요?", "저희 서버에 보관합니다. 통신은 전 구간 암호화하고, 올리신 사진을 광고 등 다른 목적으로 쓰지 않습니다."],
    ["실수로 지운 기록을 되살릴 수 있나요?", "되살릴 수 없습니다. 지우기 전에 한 번 더 확인 창이 뜨는 이유예요."],
    ["「서버에 안 올라갔어요」가 떴어요.", "사진을 올리는 도중 통신이 끊긴 경우입니다. 기록은 폰에 남아 있으니 서랍 위 「다시 올리기」를 누르면 이어서 올라갑니다."],
    ["예전 기록을 찾고 싶어요.", "서랍 오른쪽 위 「검색」에서 제목·종류·학년·학기로 찾을 수 있습니다."],
  ]],
  ["자녀 폰 연결", [
    ["자녀 폰은 어떻게 연결하나요?", "내 정보 → 자녀폰에서 코드를 발급하고, 자녀 폰의 앱에 그 코드를 넣으면 됩니다. 코드는 한 번만 쓸 수 있어요."],
    ["자녀 폰은 몇 대까지 되나요?", "자녀 1명당 1대입니다. 새 폰을 연결하면 이전 폰은 자동으로 끊깁니다."],
    ["자녀 폰에서 뭘 볼 수 있나요?", "준비물과 대화만 볼 수 있습니다. 기록·결제·보호자 정보는 자녀 폰에서 열리지 않습니다."],
    ["연결을 끊고 싶어요.", "내 정보 → 자녀폰 → 끊기를 누르면 그 즉시 자녀 폰에서 접속이 끊깁니다."],
  ]],
  ["이용권·결제", [
    ["무료로 얼마나 써볼 수 있나요?", "자녀를 등록하면 7일 동안 모든 기능을 무료로 쓸 수 있습니다. 자동으로 결제되지 않아요."],
    ["결제는 자녀별인가요?", "네. 이용권은 자녀 1명 기준이라 자녀가 늘면 이용권도 따로 필요합니다."],
    ["환불하고 싶어요.", "앱 결제는 Google Play를 통해 이뤄집니다. Play 스토어 → 결제 및 정기 결제 → 주문 내역에서 환불을 신청할 수 있고, 진행이 어려우면 문의해 주세요."],
    ["이용권이 남았는데 연장하면 어떻게 되나요?", "남은 기간 뒤에 이어 붙습니다. 남은 날짜가 사라지지 않아요."],
  ]],
  ["계정·보안", [
    ["비밀번호를 잊었어요.", "로그인 화면의 「비밀번호 찾기」에서 가입할 때 쓴 이메일로 본인 확인 후 새로 정할 수 있습니다."],
    ["앱에 잠금을 걸 수 있나요?", "내 정보 → 앱 잠금을 켜면 앱을 열 때 지문으로 확인합니다."],
    ["탈퇴하면 자료는 어떻게 되나요?", "탈퇴 후 3개월 동안 보관했다가 완전히 파기합니다. 그 안에 다시 로그인하시면 자료가 그대로 살아납니다."],
    ["광고 메일·문자를 그만 받고 싶어요.", "내 정보 → 알림·수신 설정에서 언제든 끌 수 있습니다. 끄셔도 서비스 이용에는 아무 영향이 없습니다."],
  ]],
];

export function helpPage() {
  // <details>로 접는다 — 자바스크립트 없이도 열린다(심사자가 스크립트 막고 볼 수도 있다)
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 30px">
    <a href="/" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <h1 style="margin:12px 0 4px;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">고객센터</h1>
    <p style="margin:0 0 18px;font-size:12.5px;color:${C.muted}">아이서랍 · 궁금한 것을 먼저 찾아보시고, 없으면 메일로 물어보세요.</p>

    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px;margin-bottom:20px">
      <div style="font-size:14px;font-weight:800;color:${C.ink};margin-bottom:8px">문의하기</div>
      <div style="font-size:13px;color:${C.inkSoft};line-height:1.8">
        메일 <a href="mailto:dndmotor1@gmail.com" style="color:${C.greenDark};font-weight:700">dndmotor1@gmail.com</a><br>
        평일 10:00~18:00 (점심 12:00~13:00 · 주말·공휴일 휴무)<br>
        보통 1~2 영업일 안에 답을 드립니다.<br>
        <span style="color:${C.muted}">앱을 쓰고 계시면 내 정보 → 고객센터에서 문의하시면 앱 안에서 답변을 보실 수 있어요.</span>
      </div>
    </div>

    ${FAQ_WEB.map(([sec, rows]) => `
      <div style="font-size:12.5px;color:${C.muted};margin:0 2px 8px">${escapeHtml(sec)}</div>
      <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;overflow:hidden;margin-bottom:18px">
        ${rows.map(([q, a], i) => `
          <details style="${i ? `border-top:1px solid ${C.border};` : ""}">
            <summary style="padding:14px 16px;font-size:14px;font-weight:700;color:${C.ink};cursor:pointer;list-style:none">${escapeHtml(q)}</summary>
            <div style="padding:0 16px 14px;font-size:13px;color:${C.inkSoft};line-height:1.75">${escapeHtml(a)}</div>
          </details>`).join("")}
      </div>`).join("")}

    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px">
      <div style="font-size:13px;color:${C.inkSoft};line-height:1.8">
        베이직씨엔엠 · 사업자등록번호 746-21-02507<br>
        <a href="/terms" style="color:${C.greenDark}">이용약관</a> · <a href="/privacy" style="color:${C.greenDark}">개인정보처리방침</a>
      </div>
    </div>
  </div>`;
  return layout({ title: "고객센터 — 아이서랍", body });
}

// ================= 약관 / 개인정보처리방침 (기본 문안) =================
function legalPage(title, sections, effective = "2026-08-01") {
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 30px;max-width:100%;margin:0 auto">
    <a href="javascript:history.back()" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <h1 style="margin:12px 0 4px;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">${escapeHtml(title)}</h1>
    <p style="margin:0 0 16px;font-size:11.5px;color:${C.muted}">시행일 ${effective}</p>
    ${sections.map(([h, t]) => `<div style="margin-bottom:16px"><div style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;color:${C.ink};margin-bottom:6px">${escapeHtml(h)}</div><div style="font-size:12.5px;color:${C.inkSoft};line-height:1.7">${t}</div></div>`).join("")}
  </div>`;
  return layout({ title: `${title} — 아이서랍`, body });
}
/* 2026-07-31 전면 개정 — 옛 문안은 웹(회원가입 없음·이름 미수집) 기준이라 앱 현실과 정반대였다.
   앱은 계정(이메일·이름·생년월일)·자녀 정보·기록 사진까지 다루고 스토어 심사가 이 페이지 URL을 본다.
   ⚠ 앱 안(#terms·#policy)에도 같은 문안이 있다 — 여기를 고치면 app/www/app.js LEGAL도 같이 고칠 것. */
export function termsPage() {
  return legalPage("이용약관", [
    ["제1조 (목적)", "본 약관은 베이직씨엔엠(이하 '회사')이 제공하는 '아이서랍' 서비스(웹 및 모바일 앱, 이하 '서비스')의 이용 조건과 회사·이용자의 권리, 의무를 정합니다."],
    ["제2조 (서비스 내용)", "서비스는 ① NEIS·학교알리미 등 공공데이터 기반의 급식·시간표·학사일정 안내 ② 자녀 기록(상장·통지표 등) 보관 ③ 교외체험학습 신청서·결석신고서 등 서식 작성 도움 ④ 준비물·일정 관리와 알림 ⑤ 자녀 기기 연결 기능을 제공합니다."],
    ["제3조 (정보의 성격)", "급식·시간표·학사일정은 공공데이터 공시 시점 기준이며 학교 사정으로 실제와 다를 수 있습니다. 서식은 일반적인 양식을 기준으로 하며 학교마다 다를 수 있으므로 제출 전 학교 안내를 확인해야 합니다. 서비스가 제공하는 정보는 참고용입니다."],
    ["제4조 (계정)", "가입은 보호자 본인이 해야 하며, 계정·비밀번호 관리 책임은 이용자에게 있습니다. 만 14세 미만 아동은 직접 가입할 수 없고, 자녀 기기 연결은 보호자가 발급한 코드로만 가능합니다."],
    ["제5조 (이용권과 결제)", "서비스는 무료 체험 기간(자녀 등록 후 7일) 후 유료 이용권으로 이용합니다. 결제는 Google Play 인앱 결제로 처리되며, 가격·기간은 결제 화면에 표시된 내용을 따릅니다. 이용권은 자녀 1명 기준이며 자녀 추가 시 별도 이용권이 필요합니다."],
    ["제6조 (환불)", "환불은 Google Play 환불 정책과 전자상거래 등에서의 소비자보호에 관한 법률에 따릅니다."],
    ["제7조 (이용자 콘텐츠)", "이용자가 올린 기록(사진·메모 등)의 권리는 이용자에게 있으며, 회사는 보관·표시 목적 범위에서만 처리합니다. 회사는 이용자 콘텐츠를 광고 등 다른 목적에 쓰지 않습니다."],
    ["제8조 (금지행위)", "타인의 계정 도용, 서비스의 비정상적 이용(자동화 수집, 서버 공격 등), 법령 위반 목적의 이용을 금지합니다."],
    ["제9조 (서비스 변경·중단)", "회사는 서비스 내용을 변경하거나 중단할 수 있으며, 유료 이용자에게 불리한 중대한 변경은 사전에 알립니다."],
    ["제10조 (책임의 한계)", "회사는 공공데이터 원본의 오류·지연, 천재지변, 이용자 귀책으로 인한 손해에 대해 책임을 지지 않습니다."],
    ["제11조 (해지·탈퇴)", "이용자는 앱의 내정보에서 언제든 탈퇴할 수 있습니다. 탈퇴 시 데이터는 개인정보처리방침에 따라 3개월 보관 후 파기됩니다."],
    ["제12조 (준거법)", "본 약관은 대한민국 법률에 따르며, 분쟁은 민사소송법상 관할 법원에 제기합니다."],
    ["문의", "베이직씨엔엠 (사업자등록번호 746-21-02507) · dndmotor1@gmail.com"],
  ]);
}
/* ── 계정 삭제 안내 (2026-08-08) ─────────────────────────────────────────
   **구글 플레이 필수 요구사항**이다. 앱을 깔지 않은 사람도 웹에서 삭제를 요청할 수 있어야 하고,
   스토어 「앱 콘텐츠 → 데이터 보안」 양식에 이 URL 을 적는다.
   심사가 보는 것은 셋이다: ①무엇이 지워지나 ②얼마나 보관하나 ③어떻게 요청하나.
   ⚠ 여기서 «즉시 삭제»라고 쓰면 안 된다 — 실제 동작은 3개월 유예 뒤 파기다(api_auth.js withdrawMe).
     문서와 코드가 어긋나면 그게 심사 반려 사유이자 거짓말이다. */
export function accountDeletePage() {
  return legalPage("계정 · 데이터 삭제", [
    ["앱에서 바로 지우기 (가장 빠릅니다)",
      "아이서랍 앱 → <b>내 정보 · 설정</b> → <b>회원 탈퇴</b> 를 누르면 그 자리에서 탈퇴됩니다. " +
      "탈퇴하면 즉시 로그인할 수 없게 되고, 아래 보관 기간이 지나면 완전히 파기됩니다."],
    ["앱 없이 요청하기",
      "앱을 지웠거나 로그인할 수 없다면 아래로 메일을 보내 주세요.<br>" +
      "· 받는 곳: <b>dndmotor1@gmail.com</b><br>" +
      "· 제목: <b>계정 삭제 요청</b><br>" +
      "· 본문: 가입에 쓴 <b>아이디 또는 이메일</b><br>" +
      "본인 확인 후 <b>영업일 기준 3일 이내</b>에 처리하고 회신드립니다. 별도 비용은 없습니다."],
    ["무엇이 지워지나요",
      "· 계정 정보: 아이디·비밀번호·보호자 이름·생년월일·이메일·휴대폰 번호·카카오 연결 정보<br>" +
      "· 자녀 정보: 별명·이름·학교/학년/반·프로필 사진<br>" +
      "· 이용자가 저장한 것: 기록 사진과 메모, 준비물, 개인 일정, 서식 작성 내용<br>" +
      "· 자녀 앱 연결과 알림 토큰, 미션·별도장 기록<br>" +
      "사진 원본은 저장소에서 함께 삭제됩니다."],
    ["얼마나 보관하나요",
      "탈퇴 시점부터 <b>3개월</b> 보관한 뒤 완전히 파기합니다. " +
      "실수로 탈퇴한 경우 이 기간 안에 문의하시면 복구할 수 있고, 기간이 지나면 복구할 수 없습니다.<br>" +
      "다만 <b>전자상거래 등에서의 소비자보호에 관한 법률</b>에 따라 결제·거래 기록은 " +
      "<b>5년</b> 동안 따로 보관해야 합니다(주문번호·상품·일시). 이 기록은 다른 목적에 쓰지 않습니다."],
    ["결제 중인 이용권이 있다면",
      "탈퇴해도 Google Play 정기결제는 자동으로 해지되지 않습니다. " +
      "<b>Google Play → 프로필 → 결제 및 정기 결제</b> 에서 먼저 해지해 주세요. " +
      "환불은 Google Play 환불 정책을 따릅니다."],
    ["문의", "베이직씨엔엠 (사업자등록번호 746-21-02507) · dndmotor1@gmail.com"],
  ], "2026-08-08");
}
export function privacyPage() {
  return legalPage("개인정보처리방침", [
    ["1. 수집하는 개인정보", `서비스 제공에 필요한 최소한만 수집합니다.<br>
      · <b>계정</b>: 아이디, 비밀번호(암호화 저장), 보호자 이름, 생년월일, 이메일, 휴대폰 번호(선택), 카카오 로그인 시 카카오 회원번호·닉네임<br>
      · <b>자녀</b>: 별명, 자녀 이름(선택 — 서식 작성용, 분리 보관하며 화면에 표시하지 않음), 학교·학년·반, 프로필 사진(선택)<br>
      · <b>이용자가 저장하는 내용</b>: 기록 사진·메모, 준비물, 개인 일정, 출결 서식 작성 내용<br>
      · <b>자동 수집</b>: 접속 기록, 기기 알림 토큰<br>
      · <b>결제</b>: Google Play 주문 정보(상품·일시·주문번호). 카드번호 등 결제수단 정보는 Google이 처리하며 회사는 보관하지 않습니다.`],
    ["2. 이용 목적", "서비스 제공(급식·시간표·학사일정 안내, 기록 보관, 서식 작성, 알림), 계정 식별과 데이터 복원, 이용권·결제 관리, 고지사항 전달, 부정 이용 방지에 씁니다. 광고성 정보 전송은 별도로 동의한 경우에만 합니다."],
    ["3. 보유 기간", `<b>회원 탈퇴 후 3개월간 보관한 뒤 파기합니다</b>(실수 탈퇴 문의·분쟁 대응 목적. 이 기간에도 로그인은 되지 않습니다). 즉시 파기를 원하면 문의해 주세요.<br>
      법령이 따로 정한 것은 그 기간을 따릅니다: 계약·결제 기록 5년, 소비자 불만·분쟁 처리 기록 3년(전자상거래법), 접속 기록 3개월(통신비밀보호법).`],
    ["4. 처리 위탁과 국외 이전", `서비스 운영을 위해 아래에 처리를 맡깁니다.<br>
      · Cloudflare, Inc.(미국) — 서버 운영·데이터 보관. 이전 항목: 제1항의 정보 전부, 이전 시점: 서비스 이용 시 상시, 보유 기간: 위 제3항과 같음<br>
      · Google LLC(미국) — 결제 처리, 앱 알림 발송<br>
      · 주식회사 카카오 — 간편 로그인<br>
      이용자는 국외 이전을 거부할 수 있으나 이 경우 서비스 이용이 불가능합니다.`],
    ["5. 제3자 제공", "법령에 따른 경우를 제외하고 개인정보를 제3자에게 제공하지 않습니다."],
    ["6. 아동의 개인정보", "자녀 정보는 보호자(법정대리인)가 직접 입력하고 그 수집·이용에 동의합니다. 만 14세 미만 아동은 직접 가입할 수 없으며, 자녀 기기 연결은 보호자가 발급한 코드로만 가능합니다. 자녀 이름은 분리 보관하고 앱 화면에 표시하지 않습니다."],
    ["7. 파기 방법", "보유 기간이 지난 정보는 지체 없이 파기합니다. 전자 파일은 복구할 수 없는 방법으로 삭제하고, 사진 원본(저장소)도 함께 삭제합니다."],
    ["8. 이용자의 권리", "이용자는 언제든 자기 정보의 열람·정정·삭제·처리정지를 요구하고 동의를 철회할 수 있습니다. 앱의 내정보 또는 아래 연락처로 요청하면 지체 없이 처리합니다."],
    ["9. 광고성 정보 수신", "광고성 정보(혜택·소식)는 가입 시 또는 이후에 <b>선택 동의</b>한 경우에만 이메일·문자·전화로 보냅니다. 앱의 내정보에서 채널별로 언제든 철회할 수 있으며, 동의하지 않아도 서비스 이용에 제한이 없습니다."],
    ["10. 안전성 확보 조치", "비밀번호 일방향 암호화, 전 구간 통신 암호화(HTTPS), 자녀 이름 분리 보관, 접근 권한 최소화, 로그인 시도 제한을 적용합니다."],
    ["11. 개인정보 보호책임자", "베이직씨엔엠 대표 (사업자등록번호 746-21-02507) · dndmotor1@gmail.com — 개인정보 관련 문의·불만·피해 구제를 처리합니다. 그 밖에 개인정보침해 신고는 한국인터넷진흥원 개인정보침해신고센터(118)로 할 수 있습니다."],
    ["12. 고지", "이 방침을 바꾸면 시행 7일 전(이용자에게 불리한 변경은 30일 전) 앱 공지로 알립니다."],
  ]);
}

// ================= 결제 완료 (영수증 요약) =================
export function payCompletePage(info) {
  const row = (k, v) => `<div style="display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #F0F2F5"><span style="font-size:13px;color:${C.muted};font-weight:600">${k}</span><span style="font-size:clamp(14px, 12.5px + 0.4vw, 16px);color:${C.ink};font-weight:700">${v}</span></div>`;
  const methodKor = { card: "카드", phone: "휴대폰", vbank: "가상계좌" }[info.method] || info.method;
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:40px 18px;max-width:100%;margin:0 auto">
    <div style="text-align:center"><div style="font-size:52px">✅</div><h1 style="margin:12px 0 0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink}">결제가 완료됐어요</h1><p style="margin:8px 0 0;font-size:13px;color:${C.muted2}">이용기간이 연장되어 전체 기능이 열렸어요.</p></div>
    <div style="margin-top:22px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:6px 18px">
      ${row("결제 금액", `<b style="color:${C.green}">${info.amount.toLocaleString()}원</b>`)}
      ${row("이용 기간", `${info.months}개월 · 자녀 ${info.childCount}명`)}
      ${row("결제 수단", methodKor)}
      ${row("이용 만료일", fmtDate((info.newExpiry || "").slice(0, 10).replace(/-/g, "")) + "까지")}
      ${info.autoRenew ? row("자동 구독", "신청됨") : ""}
    </div>
    <a href="/mypage" style="margin-top:18px;display:block;text-align:center;padding:15px;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800">마이페이지로</a>
    <div style="margin-top:10px;text-align:center;font-size:11px;color:${C.muted}">테스트 결제입니다(실제 청구 없음). 영수증·환불 문의는 마이페이지 → 결제 내역에서.</div>
  </div>`;
  return layout({ title: "결제 완료 — 아이서랍", body });
}

// ================= 결제 내역 (마이페이지 하위) =================
export function paymentsHistoryPage(payments) {
  const ps = payments || [];
  const methodKor = { card: "카드", phone: "휴대폰", vbank: "가상계좌" };
  const cards = ps.map((p) => `
    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:15px 16px;margin-bottom:11px${p.status === "refunded" ? ";opacity:.6" : ""}">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-size:clamp(16px, 14px + 0.6vw, 19px);font-weight:800;color:${C.ink}">${Number(p.amount).toLocaleString()}원</div>
        <span style="font-size:11px;font-weight:800;padding:3px 9px;border-radius:7px;${p.status === "refunded" ? "background:#FBE9E7;color:#C0392B" : "background:" + C.greenBg + ";color:" + C.greenDark}">${p.status === "refunded" ? "환불됨" : "결제완료"}</span>
      </div>
      <div style="margin-top:8px;font-size:12.5px;color:${C.muted2};line-height:1.7">
        ${p.months}개월 · 자녀 ${p.child_count}명 · ${methodKor[p.method] || escapeHtml(p.method)}${p.auto_renew ? " · 자동구독" : ""}<br>
        결제일 ${escapeHtml(String(p.created_at).slice(0, 10))}${p.new_expiry ? ` · 이용 ${escapeHtml(String(p.new_expiry).slice(0, 10))}까지` : ""}
      </div>
    </div>`).join("");
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 30px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;gap:10px"><a href="/mypage" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a><h1 style="margin:0;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">결제 내역</h1></div>
    <p style="margin:8px 0 16px;font-size:12.5px;color:${C.muted2}">최신순. 지금은 테스트 결제 기록입니다.</p>
    ${cards || `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:34px 20px;text-align:center;color:${C.muted};font-size:13px">아직 결제 내역이 없어요.</div>`}
    <div style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:14px;padding:14px 16px;font-size:12px;color:${C.muted2};line-height:1.7">
      <b style="color:${C.ink}">환불 문의</b><br>전자상거래법에 따른 청약철회·환불은 고객센터로 문의해 주세요. (베이직씨엔엠 · 고객센터 준비 중)
    </div>
  </div>`;
  return layout({ title: "결제 내역 — 아이서랍", body });
}

// ================= 알림 설정 (마이페이지 하위) — 실제 웹푸시 구독/발송 =================
export function notificationsPage(enabled, vapidPublic = "") {
  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 30px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;gap:10px"><a href="/mypage" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a><h1 style="margin:0;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">알림 설정</h1></div>
    <p style="margin:8px 0 16px;font-size:12.5px;color:${C.muted2};line-height:1.6">매일 아침 <b>오늘 급식·시간표·챙길 일정</b>을 웹푸시로 받아보세요. <b>홈 화면 추가(PWA 설치)</b> 후 이용하면 가장 잘 됩니다.</p>
    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:18px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
        <div><div style="font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink}">아침 알림</div><div id="notifState" style="font-size:12px;color:${C.muted};margin-top:2px">현재 <b style="color:${enabled ? C.green : C.muted2}">${enabled ? "켜짐" : "꺼짐"}</b> · 오전 7시경 발송(예정)</div></div>
        <span id="notifIcon" style="font-size:clamp(22px, 18px + 1.1vw, 27px)">${enabled ? "🔔" : "🔕"}</span>
      </div>
      <div id="notifBtns" style="margin-top:14px">
        <button type="button" id="btnOn" style="display:${enabled ? "none" : "block"};width:100%;padding:14px;border:none;border-radius:12px;background:${C.green};color:#fff;font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;cursor:pointer">🔔 알림 받기</button>
        <button type="button" id="btnTest" style="display:${enabled ? "block" : "none"};width:100%;padding:13px;border:1px solid ${C.greenBd};border-radius:12px;background:${C.greenBg};color:${C.greenDark};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;cursor:pointer;margin-bottom:8px">🔔 테스트 알림 받아보기</button>
        <button type="button" id="btnOff" style="display:${enabled ? "block" : "none"};width:100%;padding:13px;border:1px solid ${C.border};border-radius:12px;background:#fff;color:${C.muted2};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800;cursor:pointer">알림 해제</button>
      </div>
    </div>
    <div style="margin-top:12px;font-size:11.5px;color:${C.muted};line-height:1.6">· "알림 받기"를 누르면 브라우저 권한을 요청하고 이 기기를 알림 대상으로 등록해요.<br>· "테스트 알림"으로 지금 바로 받아볼 수 있어요(매일 아침 자동 발송은 준비 중).<br>· iOS는 <b>홈 화면에 추가한 뒤(PWA)</b>에만 알림이 됩니다.</div>
  </div>
  <script>
    var VAPID='${vapidPublic}';
    function u8(b){ b=b.replace(/-/g,'+').replace(/_/g,'/'); var p='='.repeat((4-b.length%4)%4); var raw=atob(b+p); var a=new Uint8Array(raw.length); for(var i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i); return a; }
    var $=function(id){return document.getElementById(id);};
    function setState(on){ $('btnOn').style.display=on?'none':'block'; $('btnTest').style.display=on?'block':'none'; $('btnOff').style.display=on?'block':'none'; $('notifIcon').textContent=on?'🔔':'🔕'; $('notifState').innerHTML='현재 <b style="color:'+(on?'${C.green}':'${C.muted2}')+'">'+(on?'켜짐':'꺼짐')+'</b> · 오전 7시경 발송(예정)'; }
    async function enableNotif(){
      if(!('serviceWorker' in navigator)||!('PushManager' in window)){ alert('이 브라우저는 웹푸시를 지원하지 않아요. 홈 화면에 추가(설치) 후 다시 시도해 주세요.'); return; }
      var perm=await Notification.requestPermission();
      if(perm!=='granted'){ alert('알림 권한이 허용되지 않았어요. 브라우저 설정에서 허용해 주세요.'); return; }
      var reg=await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;
      var sub=await reg.pushManager.getSubscription();
      if(!sub){ sub=await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:u8(VAPID)}); }
      var r=await fetch('/api/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)});
      if(r.ok){ setState(true); alert('알림이 신청됐어요! "테스트 알림"으로 확인해 보세요.'); } else { alert('신청 저장에 실패했어요.'); }
    }
    async function testNotif(){ var r=await fetch('/api/push/test',{method:'POST'}); var j=await r.json().catch(function(){return{};}); if(j&&j.ok){ alert('발송했어요('+j.sent+'/'+j.subs+'). 잠시 후 알림이 오는지 확인해 주세요.'); } else { alert('발송 실패: '+(j&&j.error||'오류')); } }
    function offNotif(){ uiConfirmCb('알림을 해제하시겠어요?', function(){ fetch('/mypage/notifications',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'action=off'}).finally(function(){ setState(false); }); }, '해제하기'); }
    if($('btnOn')) $('btnOn').addEventListener('click',enableNotif);
    if($('btnTest')) $('btnTest').addEventListener('click',testNotif);
    if($('btnOff')) $('btnOff').addEventListener('click',offNotif);
  </script>`;
  return layout({ title: "알림 설정 — 아이서랍", body });
}

// ================= 로그인(소셜) =================
// providers = env에 키가 등록된 제공자만(auth.js providersFrom). 키가 도착하는 순서대로 버튼이 열린다.
// 이메일·전화번호는 받지 않는다(가입 절차·비용 0). 로그인 = 기기 간 데이터 유지가 목적.
export function loginPage(providers = [], account = null) {
  const BTN = {
    kakao: { label: "카카오로 시작하기", bg: "#FEE500", color: "#191919", border: "none", icon: "💬" },
    naver: { label: "네이버로 시작하기", bg: "#03C75A", color: "#fff", border: "none", icon: "N" },
    google: { label: "Google로 시작하기", bg: "#fff", color: "#3C4043", border: `1px solid ${C.border}`, icon: "G" },
  };
  const order = ["kakao", "naver", "google"].filter((p) => providers.includes(p));
  const buttons = order.map((p) => {
    const b = BTN[p];
    return `<a href="/auth/${p}" style="display:flex;align-items:center;justify-content:center;gap:9px;width:100%;padding:15px;border-radius:13px;background:${b.bg};color:${b.color};border:${b.border};font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;margin-bottom:10px;box-sizing:border-box"><span style="font-weight:900">${b.icon}</span>${b.label}</a>`;
  }).join("");

  const inner = account
    ? `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:26px 20px;text-align:center">
        <div style="font-size:36px">✅</div>
        <div style="margin-top:10px;font-size:16px;font-weight:800;color:${C.ink}">이미 로그인되어 있어요</div>
        <div style="margin-top:6px;font-size:13px;color:${C.muted}">${escapeHtml(account.nickname || "회원")}님, 자녀 정보가 계정에 안전하게 연결돼 있어요.</div>
        <a href="/mypage" style="margin-top:16px;display:inline-block;padding:13px 24px;border-radius:12px;background:${C.green};color:#fff;font-size:15px;font-weight:800">마이페이지로</a>
      </div>`
    : (order.length
      ? `${buttons}
        <div style="margin-top:14px;font-size:11.5px;color:${C.muted};line-height:1.7;background:#fff;border:1px solid ${C.border};border-radius:12px;padding:12px 14px">
          · 이름·이메일·전화번호는 받지 않아요. 로그인은 <b>기기가 바뀌어도 자녀 정보를 유지</b>하기 위한 용도예요.<br>
          · 지금 이 기기에서 쓰던 자녀·일정은 로그인하는 순간 계정에 <b>자동으로 이어집니다</b>.
        </div>`
      : `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:30px 20px;text-align:center">
          <div style="font-size:34px">🔧</div>
          <div style="margin-top:10px;font-size:15px;font-weight:800;color:${C.ink}">로그인 준비 중이에요</div>
          <div style="margin-top:6px;font-size:12.5px;color:${C.muted};line-height:1.6">간편 로그인을 준비하고 있어요.<br>지금은 로그인 없이 모든 기능을 쓸 수 있습니다.</div>
        </div>`);

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;gap:10px"><a href="/mypage" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a><h1 style="margin:0;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">로그인</h1></div>
    <p style="margin:8px 0 18px;font-size:13px;color:${C.muted2};line-height:1.6">간편 로그인 한 번이면 <b>폰을 바꾸거나 다른 기기에서 접속해도</b> 자녀·일정이 그대로 유지돼요.</p>
    ${inner}
  </div>`;
  return layout({ title: "로그인 — 아이서랍", body });
}

// ================= 마이페이지 허브 =================
// 마이페이지용 자녀 칩 — 목업 ① 최상단 스위처.
// 헤더의 childSwitcher()는 초록 배경 위 흰 글씨 전용이라 밝은 배경에선 안 보인다. 그래서 별도로 둔다.
// 자녀별 구분 색은 헤더와 동일(1=그린 2=블루 3=퍼플)해서 두 화면 사이에 인지가 이어지게 한다.
const CHILD_COLORS = ["#2E7D5B", "#2A4A7F", "#6B4E9E"];
function childSwitcherPlain(kids) {
  const chips = kids.slice(0, 3).map((c, i) => {
    const col = CHILD_COLORS[i] || CHILD_COLORS[0];
    return `<a href="/school/${encodeURIComponent(c.school_slug)}/?child=${escapeHtml(c.id)}"
      style="flex:1;min-width:0;display:flex;align-items:center;gap:6px;background:#fff;border:1.5px solid ${col}33;border-radius:12px;padding:9px 11px;text-decoration:none">
      <span style="width:17px;height:17px;flex:none;border-radius:5px;background:${col};color:#fff;font-size:10px;font-weight:900;display:flex;align-items:center;justify-content:center">${i + 1}</span>
      <span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12.5px;font-weight:800;color:${C.ink}">${escapeHtml(c.nickname)}</span>
    </a>`;
  }).join("");
  return `<div style="display:flex;gap:7px;margin-bottom:12px">${chips}</div>`;
}

// payEnabled: PG 연동 전에는 결제 진입점(이용권 연장)을 숨긴다(v4 1-1). 서버 PAYMENTS_DISABLED와 한 값을 쓴다.
export function mypagePage(children, todayYmd, account = null, providers = [], payEnabled = false, recordsOn = false) {
  const kids = children || [];
  // 계정(소셜 로그인) 카드 — 로그인됨: 제공자·닉네임 + 로그아웃 / 미로그인: 연결 유도(제공자 키가 하나라도 있을 때만).
  const PROVIDER_KO = { kakao: "카카오", google: "Google", naver: "네이버", id: "아이디" }; // id = 아이디/비번 가입(웹 게이트 통합 2026-07-24)
  const accountCard = account
    ? `<div style="background:#fff;border:1px solid ${C.border};border-radius:14px;padding:14px 16px;display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <span style="font-size:20px;flex:none">🔐</span>
        <div style="flex:1;min-width:0"><div style="font-size:13.5px;font-weight:800;color:${C.ink}">${escapeHtml(PROVIDER_KO[account.provider] || account.provider)}로 로그인됨</div><div style="font-size:12px;color:${C.muted};margin-top:1px">${escapeHtml(account.nickname || "회원")} · 다른 기기에서도 이 계정으로 로그인하면 자녀 정보가 그대로 보여요</div></div>
        <a href="/logout" onclick="return confirm('이 기기에서 로그아웃할까요? 데이터는 계정에 안전하게 보관됩니다.')" style="flex:none;font-size:12px;font-weight:800;color:${C.muted2};background:#F1F3F6;padding:8px 12px;border-radius:10px">로그아웃</a>
      </div>`
    : (providers.length
      ? `<a href="/login" style="display:flex;align-items:center;gap:12px;background:linear-gradient(135deg,#F4F9F6,#EDF5F0);border:1px solid ${C.greenBd};border-radius:14px;padding:14px 16px;margin-bottom:12px">
          <span style="font-size:20px;flex:none">🔐</span>
          <div style="flex:1"><div style="font-size:13.5px;font-weight:800;color:${C.ink}">로그인하고 자녀 정보 지키기</div><div style="font-size:12px;color:${C.muted};margin-top:1px">폰을 바꾸거나 다른 기기에서도 자녀·일정이 유지돼요</div></div>
          <span style="color:${C.green};font-size:20px">›</span>
        </a>`
      : "");
  // 만료 임박(2일 이내) 배너 — 무료 개방 중인 자녀는 제외한다.
  // 개방 중엔 만료일이 지나도 실제로 잠기지 않으므로, 배너를 띄우면 있지도 않은 불안을 만든다.
  // PG 미연동 동안엔 연장할 방법 자체가 없으므로 배너를 아예 띄우지 않는다(막다른 안내 방지).
  const expiringSoon = payEnabled && kids.find((c) => {
    if (c.is_test || c._freeOpen || !c.trial_expires_at) return false;
    const days = Math.ceil((new Date(c.trial_expires_at).getTime() - Date.now()) / 86400000);
    return days <= 2;
  });
  const expiryBanner = expiringSoon ? `
    <div style="background:linear-gradient(135deg,#FFF3DE,#FDEBCE);border:1px solid #F0DDB4;border-radius:16px;padding:15px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px">
      <div><div style="font-size:clamp(13.5px, 12.5px + 0.3vw, 15.5px);font-weight:800;color:#8A5A2E">이용권이 곧 끝나요</div><div style="font-size:12px;color:#9A7B36;margin-top:2px">계속 이용하려면 이용권을 연장해 주세요.</div></div>
      <a href="/subscribe" style="flex:none;font-size:13px;font-weight:800;color:#fff;background:${C.green};padding:10px 15px;border-radius:11px">연장하기</a>
    </div>` : "";

  const menu = (icon, label, desc, href) => `
    <a href="${href}" style="display:flex;align-items:center;gap:13px;background:#fff;border:1px solid ${C.border};border-radius:14px;padding:15px 16px">
      <span style="font-size:20px;flex:none">${icon}</span>
      <div style="flex:1"><div style="font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:${C.ink}">${label}</div><div style="font-size:12px;color:${C.muted};margin-top:1px">${desc}</div></div>
      <span style="color:#C4CBD6;font-size:20px">›</span>
    </a>`;

  const cards = kids.map((c) => {
    const cls = `${escapeHtml(c.grade)}학년${c.class_name ? " " + escapeHtml(c.class_name) + "반" : ""}`;
    const days = (!c.is_test && c.trial_expires_at) ? Math.ceil((new Date(c.trial_expires_at).getTime() - Date.now()) / 86400000) : null;
    // 무료 개방 중이면 만료일 대신 "우리 아이 학교 개학 전까지 무료"를 개인화해 보여준다(회신 Q4 3번째 위치).
    // 개방 중엔 trial_expires_at이 지났어도 실제로 안 잠기므로, 만료 문구를 띄우면 거짓말이 된다.
    const expiry = c.is_test ? '<span style="color:#B79A54">테스트 계정</span>'
      : c._freeOpen ? `<span style="color:${C.greenDark};font-weight:700">🎁 ${schoolNameHtml(c.school_name)} 개학(${fmtDate(c._openUntil)}) 전까지 무료</span>`
      : (days != null ? (days <= 0 ? '<span style="color:#C0392B;font-weight:700">이용 만료됨</span>' : `이용 ${fmtDate((c.trial_expires_at || "").slice(0, 10).replace(/-/g, ""))}까지 · ${days}일 남음`) : "");
    const meal = c._meal ? escapeHtml(mealLineOf(c._meal)) : "";
    const ev = importantEventsFrom(c._events || [])[0];
    return `
    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px;margin-bottom:12px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
        <div style="min-width:0"><div style="font-size:clamp(16px, 14px + 0.6vw, 19px);font-weight:800;color:${C.ink}">${escapeHtml(c.nickname)}</div><div style="font-size:12.5px;color:${C.muted};margin-top:2px">${schoolNameHtml(c.school_name)} · ${cls}</div></div>
        <a href="/school/${encodeURIComponent(c.school_slug)}/?child=${escapeHtml(c.id)}&tab=timetable" style="flex:none;font-size:12px;font-weight:800;color:${C.green};background:${C.greenBg};border:1px solid ${C.greenBd};padding:8px 12px;border-radius:10px">시간표 →</a>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px">
        <div style="flex:1;background:#F7F9FB;border-radius:11px;padding:10px 12px"><div style="font-size:10.5px;color:${C.muted};font-weight:700">🍚 오늘 급식</div><div style="margin-top:3px;font-size:12.5px;color:${C.inkSoft};font-weight:600;line-height:1.4">${meal || "오늘은 급식이 없어요"}</div></div>
      </div>
      ${ev ? `<div style="margin-top:8px;display:flex;align-items:center;gap:8px;background:${C.greenBg};border-radius:11px;padding:9px 12px"><span style="font-size:13px;font-weight:800;color:${C.green}">${ddayText(todayYmd, ev.event_date)}</span><span style="font-size:12.5px;font-weight:600;color:${C.inkSoft}">${ev.icon} ${escapeHtml(ev.event_name)}</span></div>` : ""}
      <div style="margin-top:10px;font-size:11.5px;color:${C.muted}">${expiry}</div>
    </div>`;
  }).join("");

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <h1 style="margin:0;font-size:clamp(22px, 18px + 1.1vw, 27px);font-weight:800;color:${C.ink};letter-spacing:-.02em">마이페이지</h1>
      <a href="/" style="font-size:13px;font-weight:700;color:${C.muted2}">홈</a>
    </div>
    <p style="margin:6px 0 16px;font-size:13px;color:${C.muted2}">우리 아이 급식·시간표·일정을 한눈에.</p>
    ${kids.length > 1 ? childSwitcherPlain(kids) : ""}
    ${accountCard}
    ${expiryBanner}
    ${kids.length ? cards : `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:40px 20px;text-align:center"><div style="font-size:38px">📭</div><div style="margin-top:12px;font-size:15px;font-weight:800;color:${C.ink}">등록된 자녀가 없어요</div><div style="margin-top:6px;font-size:13px;color:${C.muted};line-height:1.5">학교를 검색해 자녀를 등록하면<br>급식·시간표를 자동으로 챙겨드려요.</div><a href="/" style="margin-top:16px;display:inline-block;padding:13px 22px;border-radius:12px;background:${C.green};color:#fff;font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800">학교 검색하기</a></div>`}
    <div style="margin-top:8px;display:flex;flex-direction:column;gap:9px">
      ${recordsOn && kids.length ? menu("📚", "기록 보관함", "상장·통지표·활동 사진을 학년별로", "/records") : ""}
      ${recordsOn && kids.length ? menu("🎒", "방과후 · 활동", "학원·방과후 일정을 주간 표로", "/activities") : ""}
      ${menu("👶", "자녀 관리", "추가 · 별명/학년 수정 · 삭제", "/mypage/children")}
      ${menu("🔔", "알림 설정", "매일 아침 급식·일정 알림", "/mypage/notifications")}
      ${payEnabled ? menu("🎟️", "이용권 연장", "이용권 하나로 자녀 3명까지", "/subscribe") : ""}
      ${payEnabled ? menu("💳", "결제 내역", "이용권 결제·영수증", "/mypage/payments") : ""}
      ${menu("💬", "베타 의견 보내기", "불편한 점·있으면 하는 기능 알려주세요", "/feedback")}
      ${menu("🔒", "개인정보처리방침", "수집 항목·보관 기간·파기", "/privacy")}
      ${(kids.length || account) ? `
      <!-- 자녀가 없어도 계정이 있으면 보여야 한다(2026-07-24). 예전엔 kids.length로만 걸어서
           **자녀를 등록하지 않은 회원은 탈퇴할 방법 자체가 없었다.** -->
      <a href="/mypage/purge" style="display:flex;align-items:center;gap:13px;background:#fff;border:1px solid #F0C9C3;border-radius:14px;padding:15px 16px">
        <span style="font-size:20px;flex:none">🗑️</span>
        <div style="flex:1"><div style="font-size:clamp(14.5px, 13px + 0.4vw, 16.5px);font-weight:800;color:#C0392B">회원 탈퇴</div><div style="font-size:12px;color:${C.muted};margin-top:1px">계정·자녀·원본 사진까지 즉시 파기 · 복구 불가</div></div>
        <span style="color:#E0A9A0;font-size:20px">›</span>
      </a>` : ""}
    </div>
  </div>`;
  return layout({ title: "마이페이지 — 아이서랍", body, noShare: true });
}

// ================= 자녀 관리 (CRUD) =================
// maxChildren = 회원 등급별 한도(무료 1 / 유료 3). isPaid=false면 한도 도달 시 구독 유도 CTA를 띄운다.
export function childrenManagePage(children, maxChildren, isPaid = false) {
  const kids = children || [];
  const cards = kids.map((c) => {
    const cls = `${escapeHtml(c.grade)}학년${c.class_name ? " " + escapeHtml(c.class_name) + "반" : ""}`;
    const days = (!c.is_test && c.trial_expires_at) ? Math.ceil((new Date(c.trial_expires_at).getTime() - Date.now()) / 86400000) : null;
    const expiry = c.is_test ? "테스트 계정" : (days != null ? (days <= 0 ? "이용 만료됨" : `이용 ${fmtDate((c.trial_expires_at || "").slice(0, 10).replace(/-/g, ""))}까지`) : "");
    return `
    <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:15px 16px;margin-bottom:11px">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
        <div style="min-width:0"><div style="font-size:15.5px;font-weight:800;color:${C.ink}">${escapeHtml(c.nickname)}${c.is_test ? ' <span style="font-size:9px;font-weight:800;color:#B79A54;background:#FBF4E9;padding:1px 6px;border-radius:5px">테스트</span>' : ""}</div><div style="font-size:12.5px;color:${C.muted};margin-top:2px">${schoolNameHtml(c.school_name)} · ${cls}</div><div style="font-size:11.5px;color:${C.muted};margin-top:4px">${expiry}</div></div>
      </div>
      <div style="margin-top:12px;display:flex;gap:7px">
        <a href="/child/edit?id=${escapeHtml(c.id)}" style="flex:1;text-align:center;padding:11px;border-radius:11px;background:${C.greenBg};border:1px solid ${C.greenBd};color:${C.greenDark};font-size:13px;font-weight:800">별명·학년 수정</a>
        <!-- 커뮤니티 글 경고(2026-07-24 승인) — 자녀를 지우면 그 자녀 명의로 쓴 학교 커뮤니티 글도
             함께 사라진다. 계정 탈퇴가 아니라 자녀 1명만 지워도 그렇게 되므로 누르기 전에 알려야 한다. -->
        <form method="post" action="/child/delete" onsubmit="return uiConfirm(event, '${escapeHtml(c.nickname)} 자녀를 삭제할까요?\\n이 자녀 이름으로 쓴 학교 커뮤니티 글도 함께 지워집니다.\\n남은 이용기간은 환불되지 않습니다.', '삭제하기')" style="flex:none">
          <input type="hidden" name="id" value="${escapeHtml(c.id)}">
          <button type="submit" style="padding:11px 16px;border-radius:11px;background:#fff;border:1px solid #E9D2D2;color:#C0392B;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit">삭제</button>
        </form>
      </div>
    </div>`;
  }).join("");

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <div style="display:flex;align-items:center;gap:10px">
      <a href="/mypage" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
      <h1 style="margin:0;font-size:21px;font-weight:800;color:${C.ink};letter-spacing:-.02em">자녀 관리</h1>
      <span style="margin-left:auto;font-size:12.5px;font-weight:700;color:${C.muted};background:#EEF1F5;padding:4px 10px;border-radius:8px">${kids.length}/${maxChildren}명</span>
    </div>
    <p style="margin:8px 0 16px;font-size:12.5px;color:${C.muted2}">별명·학년은 수정, 학교·반은 잠금입니다. ${isPaid ? `자녀는 최대 ${maxChildren}명까지.` : `무료회원은 자녀 ${maxChildren}명까지.`}</p>
    ${cards || `<div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:34px 20px;text-align:center;color:${C.muted};font-size:13px">아직 등록된 자녀가 없어요.</div>`}
    ${kids.length < maxChildren
      ? `<a href="/" style="margin-top:6px;display:flex;align-items:center;justify-content:center;gap:6px;padding:14px;border-radius:13px;background:#fff;border:1.5px dashed ${C.greenBd};color:${C.greenDark};font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800">＋ 자녀 추가 (학교 검색)</a>`
      : isPaid
        ? `<div style="margin-top:6px;text-align:center;font-size:12px;color:${C.muted}">자녀는 최대 ${maxChildren}명까지 등록할 수 있어요.</div>`
        : `<div style="margin-top:6px;background:#fff;border:1px solid ${C.greenBd};border-radius:14px;padding:16px;text-align:center">
            <div style="font-size:13.5px;font-weight:800;color:${C.ink}">무료로는 자녀 ${maxChildren}명까지예요</div>
            <div style="margin-top:5px;font-size:12px;color:${C.muted};line-height:1.6">자녀를 더 추가하려면 이용권이 필요해요.<br><b>이용권 하나로 자녀 3명까지</b> 쓸 수 있어요.</div>
            <a href="/subscribe" style="margin-top:11px;display:block;padding:13px;border-radius:12px;background:${C.green};color:#fff;font-size:clamp(14px, 12.5px + 0.4vw, 16px);font-weight:800">이용권으로 자녀 추가하기</a>
          </div>`}
  </div>`;
  return layout({ title: "자녀 관리 — 아이서랍", body, noShare: true });
}

// [삭제됨 2026-07-19] mypageChildrenPage — 위 handleMypageChildren 전용 옛 테스트 폼. 정식 화면은 childrenManagePage.

// (유치원 상세는 검색에서 제외됐지만 라우팅 잔존 — 최소 유지)
export function kinderDetailPage(kinder) {
  const body = `<div style="max-width:100%;margin:0 auto;padding:16px">
    <h1>${escapeHtml(kinder.name)}</h1>
    <div style="color:${C.muted}">유치원은 현재 서비스 범위에서 제외되었습니다.</div>
    <a href="/">홈으로</a>
  </div>`;
  return layout({ title: escapeHtml(kinder.name), body });
}

// ================= 자녀·데이터 전체 삭제 (목업 ⑥) =================
// 지시서 v4 6절 "삭제 기능(기록 단건 + 자녀 전체) 구현 포함" / 1-13 파기 범위.
// 복구 불가 작업이라 **이중 확인**: ①지워지는 것을 수량으로 명시 ②확인 문구 정확 입력 시에만 버튼 활성.
// 추상적으로 "모든 데이터"라고 쓰면 실감이 안 나서, 실제 건수를 세어 보여준다.
export function purgeAllPage(stats) {
  const s = stats || {};
  const rows = [
    [`자녀 <b>${s.children || 0}명</b>의 프로필과 이름`, true],
    [`업로드한 기록 <b>${s.records || 0}건</b> — <b>원본 사진 포함</b>`, (s.records || 0) > 0],
    [`방과후·활동 일정 <b>${s.schedules || 0}개</b>`, (s.schedules || 0) > 0],
    // 커뮤니티 글도 실제로 함께 지워진다(deleteChildCascade) — 목록에서 빠져 있으면
    // "지워질 것을 수량으로 보여준다"는 이 화면의 약속이 거짓이 된다(2026-07-24).
    [`학교 커뮤니티에 쓴 글 <b>${s.posts || 0}건</b>`, (s.posts || 0) > 0],
    [`시간표 개인 설정·개인일정 전부`, true],
    // 계정 탈퇴로 확정(2026-07-24). 자녀 데이터만 지우는 화면이 아니라는 걸 여기서 말해야 한다 —
    // 이 줄이 없으면 사용자는 "자녀만 지우고 계정은 남는다"고 오해한 채 누른다.
    [`<b>계정과 로그인 정보</b> — 다시 로그인할 수 없습니다`, true],
    [`알림 설정·푸시 등록 등 연락 수단 전부`, true],
  ].filter(([, show]) => show).map(([t]) => `<li style="margin-top:5px">${t}</li>`).join("");

  const body = `
  <div style="min-height:100vh;background:${C.bg};padding:20px 18px 40px;max-width:100%;margin:0 auto">
    <a href="/mypage" style="font-size:clamp(22px, 18px + 1.1vw, 27px);color:${C.muted2}">‹</a>
    <h1 style="margin:12px 0 0;font-size:clamp(21px, 17px + 1.1vw, 26px);font-weight:800;color:#C0392B;letter-spacing:-.02em;line-height:1.4">정말 탈퇴할까요?<br>되돌릴 수 없어요</h1>

    <div style="margin-top:16px;background:#FBE9E7;border:1px solid #F0C9C3;border-radius:16px;padding:16px 18px">
      <div style="font-size:13px;font-weight:800;color:#8C2F23">아래가 즉시 영구 삭제됩니다</div>
      <ul style="margin:9px 0 0;padding-left:17px;font-size:12.5px;color:#8C2F23;line-height:1.7">${rows}</ul>
    </div>

    <!-- 화면과 실제가 일치해야 한다(2026-07-24). 결제·신고 이력은 법령·남용대응 때문에 실제로 남으므로
         "전부 지웁니다"라고만 쓰면 그 자체가 거짓말이다. 남는 것을 남는다고 먼저 말한다. -->
    <div style="margin-top:10px;background:#fff;border:1px solid ${C.border};border-radius:14px;padding:14px 16px">
      <div style="font-size:12.5px;font-weight:800;color:${C.ink}">이건 남습니다</div>
      <div style="margin-top:5px;font-size:12px;color:${C.muted};line-height:1.7">
        결제·신고 이력은 법령에 따라 보관해야 해서 지우지 않습니다.
        대신 <b>누구인지 알 수 없도록 계정과의 연결을 끊어</b> 보관합니다.
      </div>
    </div>

    <form method="post" action="/mypage/purge" onsubmit="return confirmPurge(event)" style="margin-top:14px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:16px 18px">
      <div style="font-size:12.5px;font-weight:800;color:${C.muted2}">확인을 위해 <b style="color:#C0392B">전체삭제</b> 를 입력해 주세요</div>
      <input type="text" name="confirm" id="pgIn" autocomplete="off" placeholder="전체삭제" oninput="pgCheck()"
             style="margin-top:7px;width:100%;padding:13px;border:1px solid #E8B4AC;border-radius:11px;font-size:15px;font-family:inherit;box-sizing:border-box">
      <button type="submit" id="pgBtn" disabled
              style="margin-top:12px;width:100%;padding:15px;border:none;border-radius:13px;background:#D9D9DE;color:#fff;font-size:15px;font-weight:800;cursor:not-allowed;font-family:inherit">영구 삭제하기</button>
      <div style="margin-top:8px;text-align:center;font-size:11.5px;color:${C.muted}">문구가 정확히 일치해야 버튼이 켜져요</div>
    </form>

    <a href="/mypage" style="margin-top:12px;display:block;text-align:center;padding:14px;border-radius:13px;background:#fff;border:1px solid ${C.border};color:${C.ink};font-size:14px;font-weight:800">취소하고 돌아가기</a>

    <!-- 회신4 Q2: "내려받아 주세요"는 없는 기능 안내였다(내보내기는 Non-goals). 원본 뷰어에서
         브라우저 기본 저장이 되므로 그 경로를 안내한다 — 백업 수단 전무의 가혹함도 해소된다. -->
    <div style="margin-top:14px;font-size:11.5px;color:${C.muted};line-height:1.7;padding:0 3px">※ 삭제 후에는 고객센터로도 복구할 수 없습니다. 필요한 사진은 삭제 전에 <b>원본 화면에서 길게 눌러</b> 저장해 두세요.</div>
  </div>
  <script>
    function pgCheck(){
      var ok=document.getElementById('pgIn').value.trim()==='전체삭제';
      var b=document.getElementById('pgBtn');
      b.disabled=!ok;
      b.style.background=ok?'#C0392B':'#D9D9DE';
      b.style.cursor=ok?'pointer':'not-allowed';
    }
    function confirmPurge(e){
      e.preventDefault();
      var f=e.target;
      uiConfirmCb('마지막 확인입니다. 자녀 정보와 사진 원본이 모두 영구 삭제됩니다.', function(){ f.submit(); }, '영구 삭제');
      return false;
    }
  </script>`;
  return layout({ title: "자녀·데이터 전체 삭제 — 아이서랍", body, noShare: true });
}

// ================= 기록 타임라인 + 업로드 (목업 ②·②b) =================
const REC_CATS = [
  ["award", "상장", "🏅"], ["report_card", "통지표", "📄"], ["grade_sheet", "성적표", "📊"],
  ["certificate", "자격증", "📜"], ["activity", "활동", "🎨"], ["other", "기타", "📎"],
];
const REC_ICON = Object.fromEntries(REC_CATS.map(([k, , i]) => [k, i]));
const REC_KO = Object.fromEntries(REC_CATS.map(([k, n]) => [k, n]));
function gradeLabel(code) {
  if (code === 0) return "유치원";
  if (code <= 6) return `초${code}`;
  if (code <= 9) return `중${code - 6}`;
  return `고${code - 9}`;
}

export function recordsPage({ kids, child, childName, records, cat, q, used, limit, defaultSemester, defaultSchoolYear }) {
  const full = used >= limit;
  const qs = (over) => {
    const p = new URLSearchParams({ child: String(child.id) });
    const c = over && "cat" in over ? over.cat : cat;
    if (c) p.set("cat", c);
    const qq = over && "q" in over ? over.q : q;
    if (qq) p.set("q", qq);
    return "/records?" + p.toString();
  };

  const switcher = kids.length > 1 ? `<div style="display:flex;gap:7px;padding:0 13px 10px">${kids.slice(0, 3).map((k, i) => {
    const on = k.id === child.id;
    const col = ["#2E7D5B", "#2A4A7F", "#6B4E9E"][i] || "#2E7D5B";
    return `<a href="/records?child=${escapeHtml(k.id)}" style="flex:1;min-width:0;display:flex;align-items:center;gap:6px;background:${on ? col : "#fff"};border:1.5px solid ${on ? col : C.border};border-radius:12px;padding:9px 11px;text-decoration:none">
      <span style="width:16px;height:16px;flex:none;border-radius:5px;background:${on ? "rgba(255,255,255,.28)" : col};color:#fff;font-size:10px;font-weight:900;display:flex;align-items:center;justify-content:center">${i + 1}</span>
      <span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12.5px;font-weight:800;color:${on ? "#fff" : C.ink}">${escapeHtml(k.nickname)}</span></a>`;
  }).join("")}</div>` : "";

  const chips = [["", "전체"], ...REC_CATS.map(([k, n]) => [k, n])].map(([k, n]) =>
    `<a href="${qs({ cat: k })}" class="fc${cat === k ? " on" : ""}">${n}</a>`).join("");

  // 학년·학기 섹션으로 묶기. 최신이 위(정렬은 SQL에서 이미 끝남).
  const groups = [];
  for (const r of records) {
    const key = `${r.school_year}-${r.semester}`;
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(r);
    else groups.push({ key, sy: r.school_year, sem: r.semester, items: [r] });
  }
  const timeline = groups.map((g) => `
    <div style="display:flex;align-items:center;gap:8px;margin:18px 2px 9px">
      <b style="font-size:13.5px;font-weight:800;color:${C.ink}">${gradeLabel(g.sy)} ${g.sem}학기</b>
      <em style="font-style:normal;font-size:11.5px;color:${C.muted}">${g.items.length}건</em>
      <i style="flex:1;height:1px;background:${C.border}"></i>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
      ${g.items.map((r) => `
        <div style="position:relative;aspect-ratio:3/4;border-radius:10px;overflow:hidden;background:#DDE3EC">
          <a href="/records/${escapeHtml(r.id)}/img" target="_blank" rel="noopener" style="display:block;width:100%;height:100%">
            <img src="/records/${escapeHtml(r.id)}/img/t" alt="${escapeHtml(r.title)}" loading="lazy"
                 style="width:100%;height:100%;object-fit:cover;display:block">
          </a>
          <span style="position:absolute;left:4px;bottom:4px;padding:2px 6px;border-radius:6px;background:rgba(22,35,59,.78);color:#fff;font-size:9.5px;font-weight:800;pointer-events:none">${REC_ICON[r.category] || ""} ${REC_KO[r.category] || ""}</span>
          <button type="button" onclick="recDel(${escapeHtml(r.id)}, this)" aria-label="삭제"
            style="position:absolute;right:3px;top:3px;width:24px;height:24px;border:0;border-radius:8px;background:rgba(22,35,59,.62);color:#fff;font-size:12px;line-height:1;cursor:pointer;font-family:inherit;padding:0">✕</button>
        </div>`).join("")}
    </div>`).join("");

  // 빈 상태에는 본문에 큰 주 버튼을 둔다 — 우하단 FAB만으로는 첫 사용자가 못 찾는다(회신14, 실사용 발견).
  // "버튼이 있냐"가 아니라 "처음 온 부모가 3초 안에 첫 사진을 올리냐"의 문제다.
  // 기록이 1건이라도 있으면 이 버튼은 숨기고 FAB만 남긴다(중복 방지 — 쌓인 뒤엔 FAB가 맞다).
  const empty = `<div style="margin-top:26px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:38px 20px;text-align:center">
      <div style="font-size:38px">📦</div>
      <div style="margin-top:12px;font-size:15px;font-weight:800;color:${C.ink}">${q || cat ? "찾는 기록이 없어요" : "아직 기록이 없어요"}</div>
      <div style="margin-top:6px;font-size:13px;color:${C.muted};line-height:1.6">${q || cat ? "다른 종류나 검색어로 찾아보세요." : "상장·통지표·활동 사진을 올려두면<br>학년별로 정리해 드려요."}</div>
      ${(q || cat || full) ? "" : `<button type="button" onclick="recPick()" style="margin-top:18px;width:100%;max-width:260px;padding:15px;border:0;border-radius:13px;background:${C.green};color:#fff;font-size:15px;font-weight:800;cursor:pointer;font-family:inherit">＋ 첫 기록 올리기</button>
      <div style="margin-top:9px;font-size:11.5px;color:${C.muted};line-height:1.55">사진을 고르고 종류만 누르면 끝이에요</div>`}
    </div>`;

  const body = `
  <div style="position:sticky;top:0;z-index:20;background:${C.green};color:#fff;padding:11px 14px;display:flex;align-items:center;gap:9px;margin:-20px -18px 0">
    <a href="/mypage" style="font-size:17px;color:rgba(255,255,255,.9)">‹</a>
    <span style="font-size:15px;font-weight:800;letter-spacing:-.02em">${escapeHtml(childName || child.nickname)}의 기록</span>
    <span style="margin-left:auto;font-size:12px;opacity:.9">${used}/${limit >= 1000 ? "무제한" : limit}</span>
  </div>
  ${switcher ? `<div style="margin:0 -18px;background:${C.bg}">${switcher}</div>` : ""}
  <div style="position:sticky;top:41px;z-index:15;background:${C.bg};border-bottom:1px solid ${C.border};padding-bottom:11px;margin:0 -18px;box-shadow:0 2px 8px rgba(22,35,59,.05)">
    <div style="display:flex;gap:6px;overflow-x:auto;padding:10px 13px 0;scrollbar-width:none">${chips}<span style="flex:none;width:3px"></span></div>
    <form method="get" action="/records" style="margin:9px 13px 0;position:relative">
      <input type="hidden" name="child" value="${escapeHtml(child.id)}">
      ${cat ? `<input type="hidden" name="cat" value="${escapeHtml(cat)}">` : ""}
      <span style="position:absolute;left:11px;top:50%;transform:translateY(-50%);font-size:13px;opacity:.5">🔍</span>
      <input name="q" value="${escapeHtml(q)}" placeholder="제목으로 검색" style="width:100%;padding:11px 12px 11px 34px;border:1px solid ${C.border};border-radius:11px;font-size:13.5px;font-family:inherit;box-sizing:border-box">
    </form>
  </div>

  ${full ? `<div style="margin-top:12px;background:#FBF4E9;border:1px solid #F0E3C8;border-radius:12px;padding:11px 12px;font-size:11.5px;color:#8A6516;line-height:1.6">🔒 무료로는 기록 <b>${limit}건</b>까지 올릴 수 있어요. <b>이미 올린 기록은 언제든 보고 지울 수 있어요</b> — 새로 올리기만 잠깁니다.</div>` : ""}
  ${records.length ? timeline : empty}
  <div style="height:70px"></div>

  <button type="button" onclick="${full ? "recLimit()" : "recPick()"}"
    style="position:fixed;right:16px;bottom:18px;z-index:30;width:56px;height:56px;border-radius:18px;border:0;cursor:pointer;font-family:inherit;background:${full ? "#94A0B2" : C.green};color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 6px 18px ${full ? "rgba(148,160,178,.4)" : "rgba(46,125,91,.42)"};font-size:21px">
    ${full ? "🔒" : "＋"}<small style="font-size:8.5px;font-weight:800;margin-top:-2px">기록</small>
  </button>
  <input type="file" id="recFiles" accept="image/jpeg,image/png,image/webp" multiple style="display:none">

  <div id="recDim" style="display:none;position:fixed;inset:0;background:rgba(22,35,59,.34);z-index:39" onclick="recClose()"></div>
  <div id="recSheet" style="display:none;position:fixed;left:0;right:0;bottom:0;z-index:40;background:#fff;border-radius:20px 20px 0 0;padding:18px 16px 20px;box-shadow:0 -8px 26px rgba(22,35,59,.18);max-height:88vh;overflow-y:auto">
    <div style="width:36px;height:4px;border-radius:99px;background:#DDE2EA;margin:0 auto 13px"></div>
    <div id="recTitle" style="font-size:15.5px;font-weight:800;letter-spacing:-.02em;color:${C.ink}">사진을 올려요</div>
    <div style="margin-top:4px;font-size:11.5px;color:${C.muted2};line-height:1.6">종류만 골라주시면 나머지는 자동으로 채워드려요</div>
    <div id="recPrev" style="display:flex;gap:6px;margin-top:13px;overflow-x:auto"></div>

    <div style="margin-top:15px;font-size:12px;font-weight:800;color:${C.muted2};margin-bottom:6px">종류</div>
    <div id="recCats" style="display:flex;gap:6px;flex-wrap:wrap">
      ${REC_CATS.map(([k, n], i) => `<button type="button" class="fc${i === 0 ? " on" : ""}" data-cat="${k}" onclick="recCat(this)" style="cursor:pointer;font-family:inherit">${n}</button>`).join("")}
    </div>
    <div style="margin-top:7px;font-size:11.5px;color:${C.muted};line-height:1.55">종류가 다른 사진은 나눠서 올려주세요</div>

    <div style="margin-top:15px;font-size:12px;font-weight:800;color:${C.muted2};margin-bottom:6px">시기 <span style="font-weight:600;color:${C.muted}">— 고른 사진 전체에 같이 적용돼요</span></div>
    <div style="display:flex;gap:6px">
      <select id="recSY" style="flex:1;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14.5px;font-family:inherit;background:#fff">
        ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((c) => `<option value="${c}"${c === defaultSchoolYear ? " selected" : ""}>${gradeLabel(c)}</option>`).join("")}
      </select>
      <select id="recSem" style="flex:1;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14.5px;font-family:inherit;background:#fff">
        <option value="1"${defaultSemester === 1 ? " selected" : ""}>1학기</option>
        <option value="2"${defaultSemester === 2 ? " selected" : ""}>2학기</option>
      </select>
    </div>
    <div id="recAuto" style="margin-top:7px;font-size:11.5px;color:${C.muted};line-height:1.55"></div>

    <button type="button" id="recGo" onclick="recUpload()" style="margin-top:15px;width:100%;padding:14px;border:0;border-radius:12px;background:${C.green};color:#fff;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit">저장하기</button>
    <button type="button" onclick="recClose()" style="margin-top:8px;width:100%;padding:13px;border:1px solid ${C.border};border-radius:12px;background:#fff;color:${C.inkSoft};font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit">취소</button>
  </div>

  <style>
    .fc{flex:none;padding:7px 12px;border-radius:999px;border:1px solid ${C.border};background:#fff;font-size:12px;font-weight:700;color:${C.muted2};text-decoration:none;white-space:nowrap}
    .fc.on{background:${C.ink};color:#fff;border-color:${C.ink}}
  </style>
  <script>${recordsScript(child.id, Math.max(0, limit - used))}</script>`;

  return layout({ title: "기록 — 아이서랍", body, noShare: true });
}

// 업로드 클라이언트 — 브라우저에서 리사이즈까지 끝낸다(v4 1-10).
// Workers엔 이미지 처리가 없으므로 업로드 시점의 canvas가 유일한 기회다.
function recordsScript(childId, room) {
  const GREEN = C.green;
  return `
  var REC_CHILD=${JSON.stringify(String(childId))}, REC_ROOM=${Number(room)}, recCatV='award', recFilesArr=[];
  function recPick(){ document.getElementById('recFiles').click(); }
  function recLimit(){ if(window.__imgToast) __imgToast('무료 한도를 다 쓰셨어요. 기록은 계속 보고 지울 수 있어요.'); }
  function recClose(){ document.getElementById('recDim').style.display='none'; document.getElementById('recSheet').style.display='none'; }
  function recCat(b){
    recCatV=b.getAttribute('data-cat');
    Array.prototype.forEach.call(document.querySelectorAll('#recCats .fc'), function(x){ x.classList.remove('on'); });
    b.classList.add('on');
    recAutoText();
  }
  function recAutoText(){
    var sy=document.getElementById('recSY'), sem=document.getElementById('recSem');
    var on=document.querySelector('#recCats .fc.on');
    document.getElementById('recAuto').textContent='제목은 "'+sy.selectedOptions[0].text+' '+sem.value+'학기 '+(on?on.textContent:'')+'"로 자동 저장돼요';
  }
  document.getElementById('recFiles').addEventListener('change', function(e){
    var fs=Array.prototype.slice.call(e.target.files||[]);
    if(!fs.length) return;
    if(REC_ROOM>0 && fs.length>REC_ROOM){ if(window.__imgToast) __imgToast(REC_ROOM+'장까지만 더 올릴 수 있어요'); fs=fs.slice(0,REC_ROOM); }
    recFilesArr=fs;
    document.getElementById('recTitle').textContent='사진 '+fs.length+'장을 올려요';
    var prev=document.getElementById('recPrev'); prev.innerHTML='';
    fs.slice(0,6).forEach(function(f){
      var u=URL.createObjectURL(f);
      prev.insertAdjacentHTML('beforeend','<div style="width:58px;height:77px;flex:none;border-radius:9px;overflow:hidden;background:#DDE3EC"><img src="'+u+'" style="width:100%;height:100%;object-fit:cover"></div>');
    });
    recAutoText();
    document.getElementById('recDim').style.display='block';
    document.getElementById('recSheet').style.display='block';
    e.target.value='';
  });
  document.getElementById('recSY').addEventListener('change', recAutoText);
  document.getElementById('recSem').addEventListener('change', recAutoText);

  // 긴 변 2000px / JPEG 0.85 + 썸네일 480px / 0.7.
  // imageOrientation:'from-image'를 빼면 아이폰 세로 사진이 눕는다.
  // canvas를 거치며 EXIF가 통째로 사라진다 — 위치정보 제거가 공짜로 딸려온다(부작용 아니라 기능).
  function recShrink(file, maxSide, quality){
    return createImageBitmap(file, {imageOrientation:'from-image'}).then(function(bm){
      var r=Math.min(1, maxSide/Math.max(bm.width, bm.height));
      var w=Math.round(bm.width*r), h=Math.round(bm.height*r);
      var cv=document.createElement('canvas'); cv.width=w; cv.height=h;
      cv.getContext('2d').drawImage(bm,0,0,w,h);
      if(bm.close) bm.close();
      return new Promise(function(res){ cv.toBlob(function(b){ res(b||file); }, 'image/jpeg', quality); });
    }).catch(function(){ return file; });
  }

  // 기록 단건 삭제 — 원본+썸네일이 R2에서 함께 지워진다(서버 r2KeysOf).
  // 되돌릴 수 없으므로 확인 한 번. 성공하면 그 칸만 사라지게 하고 페이지는 새로고침하지 않는다.
  function recDel(id, btn){
    uiConfirmCb('이 기록을 삭제할까요?\n원본 사진까지 함께 지워지고 되돌릴 수 없어요.', function(){
      var fd=new FormData(); fd.append('id', id);
      fetch('/records/delete', {method:'POST', body:fd})
        .then(function(r){ return r.json(); })
        .then(function(j){
          if(j.ok){ location.reload(); return; }
          if(window.__imgToast) __imgToast('삭제에 실패했어요. 다시 시도해 주세요.');
        })
        .catch(function(){ if(window.__imgToast) __imgToast('삭제에 실패했어요. 다시 시도해 주세요.'); });
    }, '삭제하기');
  }

  function recUpload(){
    if(!recFilesArr.length) return;
    var btn=document.getElementById('recGo');
    btn.disabled=true; btn.textContent='저장 중…'; btn.style.background='#9FB5AB';
    var fd=new FormData();
    fd.append('child_id', REC_CHILD);
    fd.append('category', recCatV);
    fd.append('school_year', document.getElementById('recSY').value);
    fd.append('semester', document.getElementById('recSem').value);
    Promise.all(recFilesArr.map(function(f){
      return Promise.all([recShrink(f,2000,0.85), recShrink(f,480,0.7)]).then(function(p){
        fd.append('files', p[0], 'r.jpg');
        fd.append('files_t', p[1], 't.jpg');
      });
    })).then(function(){
      return fetch('/records/upload', {method:'POST', body:fd});
    }).then(function(r){ return r.json(); }).then(function(j){
      if(j.ok){ location.href='/records?child='+encodeURIComponent(REC_CHILD); return; }
      if(window.__imgToast) __imgToast(j.error==='limit' ? '한도를 다 쓰셨어요' : '저장에 실패했어요. 다시 시도해 주세요.');
      btn.disabled=false; btn.textContent='저장하기'; btn.style.background='${GREEN}';
    }).catch(function(){
      if(window.__imgToast) __imgToast('저장에 실패했어요. 다시 시도해 주세요.');
      btn.disabled=false; btn.textContent='저장하기'; btn.style.background='${GREEN}';
    });
  }`;
}

// ================= 방과후·활동 (목업 ③) =================
const ACT_META = {
  academy: ["학원", "#2E7D5B"],
  afterschool: ["방과후", "#2A4A7F"],
  activity: ["활동", "#6B4E9E"],
};
const DOW_KO = ["", "월", "화", "수", "목", "금", "토", "일"];

function hhmmToMin(t) {
  const m = /^(\d{2}):(\d{2})$/.exec(String(t || ""));
  return m ? (+m[1]) * 60 + (+m[2]) : 0;
}
function ymdDash(y) {
  const s = String(y || "");
  return s.length === 8 ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : "";
}

export function activitiesPage({ kids, child, acts, today }) {
  // 시간축 자동 확장 — 기본 14~22시. 등록된 일정이 범위를 벗어나면 축을 넓힌다.
  // (목업 주석의 "토요일 9시 축구교실" 사례. 안 넓히면 그 블록이 화면 밖으로 잘린다.)
  let from = 14, to = 22;
  for (const a of acts) {
    const s = Math.floor(hhmmToMin(a.start_time) / 60);
    const e = Math.ceil(hhmmToMin(a.end_time) / 60);
    if (s < from) from = s;
    if (e > to) to = e;
  }
  if (to <= from) to = from + 1;
  const ROW = 30; // 셀 높이(px) = 1시간

  const switcher = kids.length > 1 ? `<div style="display:grid;grid-template-columns:repeat(${Math.min(3, kids.length)},1fr);gap:7px;padding:0 13px 11px">${kids.slice(0, 3).map((k, i) => {
    const on = k.id === child.id;
    const col = ["#2E7D5B", "#2A4A7F", "#6B4E9E"][i] || "#2E7D5B";
    return `<a href="/activities?child=${escapeHtml(k.id)}" style="display:flex;align-items:center;gap:6px;min-width:0;background:${on ? "rgba(255,255,255,.22)" : "rgba(255,255,255,.10)"};border:1px solid rgba(255,255,255,${on ? ".55" : ".2"});border-radius:12px;padding:8px 10px;text-decoration:none">
      <span style="width:16px;height:16px;flex:none;border-radius:5px;background:${col};color:#fff;font-size:10px;font-weight:900;display:flex;align-items:center;justify-content:center">${i + 1}</span>
      <span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12.5px;font-weight:800;color:#fff">${escapeHtml(k.nickname)}</span></a>`;
  }).join("")}</div>` : "";

  // 주간 그리드 — 26px(시간축) + 7열. 블록은 셀 위에 absolute로 얹는다.
  const header = `<div style="text-align:center;padding:5px 0;font-weight:800;color:${C.muted2};border-bottom:1px solid ${C.border};font-size:9.5px"></div>` +
    [1, 2, 3, 4, 5, 6, 7].map((d) => `<div style="text-align:center;padding:5px 0;font-weight:800;color:${d >= 6 ? "#C0392B" : C.muted2};border-bottom:1px solid ${C.border};font-size:9.5px">${DOW_KO[d]}</div>`).join("");

  const rows = [];
  for (let h = from; h < to; h++) {
    rows.push(`<div style="color:${C.muted};text-align:right;padding-right:4px;line-height:${ROW}px;height:${ROW}px;font-size:9px">${h}</div>`);
    for (let d = 1; d <= 7; d++) {
      // 이 칸에서 시작하는 일정만 그린다(블록은 여러 시간을 덮으므로 시작 칸에서 한 번만).
      const here = acts.filter((a) => {
        const days = String(a.days_of_week || "").split(",").map((x) => parseInt(x, 10));
        return days.includes(d) && Math.floor(hhmmToMin(a.start_time) / 60) === h;
      });
      const blocks = here.map((a) => {
        const sMin = hhmmToMin(a.start_time), eMin = hhmmToMin(a.end_time);
        const top = ((sMin - h * 60) / 60) * ROW;
        const height = Math.max(18, ((eMin - sMin) / 60) * ROW - 2);
        const [, col] = ACT_META[a.type] || ACT_META.academy;
        return `<button type="button" onclick="actEdit(${escapeHtml(a.id)})" style="position:absolute;left:1px;right:1px;top:${top}px;height:${height}px;border:0;border-radius:5px;padding:3px;background:${col};color:#fff;font-size:8.5px;font-weight:800;line-height:1.2;overflow:hidden;cursor:pointer;font-family:inherit;text-align:left">${escapeHtml(a.name)}<br>${escapeHtml(a.start_time)}~${escapeHtml(a.end_time)}</button>`;
      }).join("");
      rows.push(`<div style="border-left:1px solid #F0F2F6;border-bottom:1px solid #F4F6F9;height:${ROW}px;position:relative">${blocks}</div>`);
    }
  }

  const legend = Object.entries(ACT_META).map(([, [ko, col]]) =>
    `<span style="font-size:10.5px;color:${C.muted2}"><i style="display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:3px;vertical-align:-1px;background:${col}"></i>${ko}</span>`).join("");

  // 등록된 일정 리스트 — 종료일 D-day pill.
  const list = acts.length ? acts.map((a) => {
    const [ko, col] = ACT_META[a.type] || ACT_META.academy;
    const days = String(a.days_of_week || "").split(",").map((x) => DOW_KO[parseInt(x, 10)] || "").filter(Boolean).join("·");
    const dd = ddayText(today, a.end_date);
    const soon = dd && dd.startsWith("D-") && parseInt(dd.slice(2), 10) <= 14;
    return `
    <div style="display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid ${C.border}">
      <i style="width:9px;height:9px;border-radius:3px;background:${col};flex:none"></i>
      <div style="flex:1;min-width:0">
        <div style="font-size:13.5px;font-weight:800;color:${C.ink};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(a.name)}</div>
        <div style="font-size:11.5px;color:${C.muted};margin-top:2px">${ko} · ${days} ${escapeHtml(a.start_time)}~${escapeHtml(a.end_time)} · ~${fmtDate(a.end_date)}</div>
      </div>
      <span style="flex:none;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:800;${soon ? "background:#FBF1DC;color:#8A6516" : `background:${C.greenBg};color:${C.greenDark}`}">${soon ? dd : "진행중"}</span>
      <button type="button" onclick="actEdit(${escapeHtml(a.id)})" style="flex:none;padding:7px 10px;border-radius:9px;border:1px solid ${C.border};background:#fff;color:${C.muted2};font-size:11.5px;font-weight:800;cursor:pointer;font-family:inherit">수정</button>
    </div>`;
  }).join("") : `<div style="padding:30px 10px;text-align:center;color:${C.muted};font-size:13px;line-height:1.6">아직 등록된 일정이 없어요.<br>학원·방과후·활동을 등록하면 주간 표에 자동으로 채워져요.</div>`;

  const body = `
  <div style="background:${C.green};margin:-20px -18px 0;padding:11px 14px 0">
    <div style="display:flex;align-items:center;gap:9px;padding-bottom:11px">
      <a href="/mypage" style="font-size:17px;color:rgba(255,255,255,.9)">‹</a>
      <span style="font-size:15px;font-weight:800;color:#fff;letter-spacing:-.02em">방과후 · 활동</span>
    </div>
    ${switcher}
  </div>

  <div style="margin-top:13px;background:#fff;border:1px solid ${C.border};border-radius:16px;padding:11px 9px">
    <div style="display:grid;grid-template-columns:26px repeat(7,1fr);font-size:9.5px">${header}${rows.join("")}</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:9px">${legend}</div>
    ${from < 14 || to > 22 ? `<div style="margin-top:8px;padding-top:8px;border-top:1px dashed ${C.border};font-size:11px;color:${C.muted};line-height:1.55">범위 밖 일정이 있어 시간축을 <b>${from}~${to}시</b>로 넓혔어요.</div>` : ""}
  </div>

  <div style="margin:17px 2px 9px;font-size:12px;font-weight:800;color:${C.muted2}">등록된 일정</div>
  <div style="background:#fff;border:1px solid ${C.border};border-radius:16px;padding:4px 15px">${list}</div>

  <div style="margin-top:11px;background:${C.greenBg};border:1px solid ${C.greenBd};border-radius:12px;padding:11px 13px;font-size:11.5px;color:${C.greenDark};line-height:1.6">📅 <b>유효기간이 지나면 자동으로 사라져요.</b> 방학 특강도 학기 학원과 똑같이 등록하시면 됩니다.</div>

  <button type="button" onclick="actNew()" style="margin-top:12px;width:100%;padding:14px;border:0;border-radius:13px;background:${C.green};color:#fff;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit">＋ 일정 등록</button>
  <div style="height:20px"></div>

  <!-- 등록·수정 시트 -->
  <div id="actDim" style="display:none;position:fixed;inset:0;background:rgba(22,35,59,.34);z-index:39" onclick="actClose()"></div>
  <div id="actSheet" style="display:none;position:fixed;left:0;right:0;bottom:0;z-index:40;background:#fff;border-radius:20px 20px 0 0;padding:18px 16px 20px;box-shadow:0 -8px 26px rgba(22,35,59,.18);max-height:90vh;overflow-y:auto">
    <div style="width:36px;height:4px;border-radius:99px;background:#DDE2EA;margin:0 auto 13px"></div>
    <div id="actTitle" style="font-size:15.5px;font-weight:800;color:${C.ink};letter-spacing:-.02em">일정 등록</div>
    <form method="post" action="/activities/save" style="margin-top:14px">
      <input type="hidden" name="child_id" value="${escapeHtml(child.id)}">
      <input type="hidden" name="id" id="actId" value="">

      <div style="font-size:12px;font-weight:800;color:${C.muted2};margin-bottom:6px">이름</div>
      <input name="name" id="actName" required maxlength="40" placeholder="예) 수학학원" style="width:100%;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14.5px;font-family:inherit;box-sizing:border-box">

      <div style="font-size:12px;font-weight:800;color:${C.muted2};margin:14px 0 6px">유형</div>
      <div style="display:flex;gap:7px">
        ${Object.entries(ACT_META).map(([k, [ko, col]], i) => `
        <label style="flex:1"><input type="radio" name="type" value="${k}" ${i === 0 ? "checked" : ""} style="display:none" onchange="actSeg()">
          <span class="actseg" data-c="${col}" style="display:block;text-align:center;padding:11px 4px;border-radius:11px;border:1.5px solid ${C.border};background:#fff;font-size:13px;font-weight:800;color:${C.muted2};cursor:pointer">${ko}</span></label>`).join("")}
      </div>

      <div style="font-size:12px;font-weight:800;color:${C.muted2};margin:14px 0 6px">요일 <span style="font-weight:600;color:${C.muted}">— 여러 개 고를 수 있어요</span></div>
      <div style="display:flex;gap:5px">
        ${[1, 2, 3, 4, 5, 6, 7].map((d) => `
        <label style="flex:1"><input type="checkbox" name="days" value="${d}" style="display:none" onchange="actDow(this)">
          <span class="actdow" style="display:block;text-align:center;padding:10px 0;border-radius:10px;border:1.5px solid ${C.border};background:#fff;font-size:12.5px;font-weight:800;color:${d >= 6 ? "#C0392B" : C.muted2};cursor:pointer">${DOW_KO[d]}</span></label>`).join("")}
      </div>

      <div style="display:flex;gap:8px;margin-top:14px">
        <div style="flex:1"><div style="font-size:12px;font-weight:800;color:${C.muted2};margin-bottom:6px">시작</div>
          <input type="time" name="start_time" id="actST" required value="16:00" style="width:100%;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14.5px;font-family:inherit;box-sizing:border-box"></div>
        <div style="flex:1"><div style="font-size:12px;font-weight:800;color:${C.muted2};margin-bottom:6px">종료</div>
          <input type="time" name="end_time" id="actET" required value="18:00" style="width:100%;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14.5px;font-family:inherit;box-sizing:border-box"></div>
      </div>

      <div style="font-size:12px;font-weight:800;color:${C.muted2};margin:14px 0 6px">유효기간 <span style="font-weight:600;color:${C.muted}">— 이 기간에만 표에 나와요</span></div>
      <div style="display:flex;gap:8px;align-items:center">
        <input type="date" name="start_date" id="actSD" required style="flex:1;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14px;font-family:inherit;box-sizing:border-box">
        <span style="color:${C.muted};font-size:13px">~</span>
        <input type="date" name="end_date" id="actED" required style="flex:1;padding:12px;border:1px solid ${C.border};border-radius:11px;font-size:14px;font-family:inherit;box-sizing:border-box">
      </div>

      <button type="submit" style="margin-top:16px;width:100%;padding:14px;border:0;border-radius:12px;background:${C.green};color:#fff;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit">저장하기</button>
    </form>
    <form method="post" action="/activities/delete" id="actDelForm" style="display:none;margin-top:8px" onsubmit="return uiConfirm(event, '이 일정을 삭제할까요?', '삭제하기')">
      <input type="hidden" name="id" id="actDelId">
      <button type="submit" style="width:100%;padding:13px;border:1px solid #E9D2D2;border-radius:12px;background:#fff;color:#C0392B;font-size:13.5px;font-weight:800;cursor:pointer;font-family:inherit">삭제</button>
    </form>
    <button type="button" onclick="actClose()" style="margin-top:8px;width:100%;padding:13px;border:1px solid ${C.border};border-radius:12px;background:#fff;color:${C.inkSoft};font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit">취소</button>
  </div>

  <script>
    var ACTS=${jsonAttrSafe(acts)};
    function actSeg(){
      Array.prototype.forEach.call(document.querySelectorAll('.actseg'), function(s){
        var i=s.previousElementSibling;
        if(i&&i.checked){ s.style.borderColor=s.getAttribute('data-c'); s.style.background=s.getAttribute('data-c'); s.style.color='#fff'; }
        else { s.style.borderColor='${C.border}'; s.style.background='#fff'; s.style.color='${C.muted2}'; }
      });
    }
    function actDow(inp){
      var s=inp.nextElementSibling;
      if(inp.checked){ s.style.borderColor='${C.green}'; s.style.background='${C.greenBg}'; s.style.color='${C.greenDark}'; }
      else { s.style.borderColor='${C.border}'; s.style.background='#fff'; s.style.color='${C.muted2}'; }
    }
    function actOpen(){ document.getElementById('actDim').style.display='block'; document.getElementById('actSheet').style.display='block'; }
    function actClose(){ document.getElementById('actDim').style.display='none'; document.getElementById('actSheet').style.display='none'; }
    function actReset(){
      document.getElementById('actId').value='';
      document.getElementById('actName').value='';
      document.getElementById('actST').value='16:00';
      document.getElementById('actET').value='18:00';
      document.querySelectorAll('input[name=days]').forEach(function(c){ c.checked=false; actDow(c); });
      document.querySelectorAll('input[name=type]')[0].checked=true; actSeg();
      document.getElementById('actDelForm').style.display='none';
    }
    function actNew(){
      actReset();
      document.getElementById('actTitle').textContent='일정 등록';
      // 기본 유효기간: 오늘 ~ 학기말(대략 6개월). 방학 특강이면 사용자가 줄이면 된다.
      var t=new Date(), e=new Date(Date.now()+180*86400000);
      document.getElementById('actSD').value=t.toISOString().slice(0,10);
      document.getElementById('actED').value=e.toISOString().slice(0,10);
      actOpen();
    }
    function actEdit(id){
      var a=null; for(var i=0;i<ACTS.length;i++){ if(String(ACTS[i].id)===String(id)) a=ACTS[i]; }
      if(!a) return;
      actReset();
      document.getElementById('actTitle').textContent='일정 수정';
      document.getElementById('actId').value=a.id;
      document.getElementById('actName').value=a.name;
      document.getElementById('actST').value=a.start_time;
      document.getElementById('actET').value=a.end_time;
      document.getElementById('actSD').value=String(a.start_date).replace(/^(\\d{4})(\\d{2})(\\d{2})$/,'$1-$2-$3');
      document.getElementById('actED').value=String(a.end_date).replace(/^(\\d{4})(\\d{2})(\\d{2})$/,'$1-$2-$3');
      String(a.days_of_week||'').split(',').forEach(function(d){
        var c=document.querySelector('input[name=days][value="'+d+'"]');
        if(c){ c.checked=true; actDow(c); }
      });
      var t=document.querySelector('input[name=type][value="'+a.type+'"]');
      if(t){ t.checked=true; actSeg(); }
      document.getElementById('actDelId').value=a.id;
      document.getElementById('actDelForm').style.display='block';
      actOpen();
    }
    actSeg();
  </script>`;

  return layout({ title: "방과후 · 활동 — 아이서랍", body, noShare: true });
}

// 스크립트에 데이터를 심을 때 </script>·U+2028/2029로 파싱이 깨지지 않게 이스케이프한다.
// (admin_templates의 jsonAttr과 같은 사고를 방지 — 실제로 한 번 당했다.)
function jsonAttrSafe(obj) {
  return JSON.stringify(obj)
    .replace(/</g, "\\u003c")
    .replace(new RegExp(String.fromCharCode(0x2028), "g"), "\\u2028")
    .replace(new RegExp(String.fromCharCode(0x2029), "g"), "\\u2029");
}

// 시간표 탭 하단 읽기전용 한 줄 — "오늘의 방과후: 수학학원 16:00~18:00"
// 방과후 페이지로 가는 두 번째 진입점(설계 ⑤). 오늘 일정이 없으면 아무것도 그리지 않는다.
function todayActivityLine(acts, child) {
  if (!acts || !acts.length || !child) return "";
  const first = acts[0];
  const [, col] = (ACT_META[first.type] || ACT_META.academy);
  const more = acts.length > 1 ? ` 외 ${acts.length - 1}개` : "";
  return `
  <a href="/activities?child=${escapeHtml(child.id)}" style="display:flex;align-items:center;gap:10px;margin-top:10px;background:#fff;border:1px solid ${C.border};border-radius:12px;padding:12px 14px;text-decoration:none">
    <i style="width:9px;height:9px;border-radius:3px;background:${col};flex:none"></i>
    <div style="flex:1;min-width:0">
      <div style="font-size:11px;color:${C.muted};font-weight:700">오늘의 방과후</div>
      <div style="margin-top:2px;font-size:13px;font-weight:800;color:${C.ink};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(first.name)} ${escapeHtml(first.start_time)}~${escapeHtml(first.end_time)}${more}</div>
    </div>
    <span style="color:#C4CBD6;font-size:18px;flex:none">›</span>
  </a>`;
}
