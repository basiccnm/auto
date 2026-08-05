export function esc(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function comma(n) {
  if (n === null || n === undefined) return "";
  return Number(n).toLocaleString("ko-KR");
}

export function formatDate(ymd) {
  if (!ymd) return "";
  const s = String(ymd);
  if (/^\d{8}$/.test(s)) return `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6, 8)}`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.replace(/-/g, ".");
  return s;
}

function telLink(phone, className) {
  if (!phone) return "";
  const digits = String(phone).replace(/[^0-9]/g, "");
  if (digits.length < 8) return "";
  return `<a href="tel:${esc(digits)}" class="${className || ""}">${esc(phone)}</a>`;
}

// 과목 그룹의 링크 생성. 예체능은 단일 키워드로 못 잡아서(학원+도장 전체 결합) subject= 파라미터로 별도 처리.
// g.q가 빈 문자열이면 카테고리 페이지(gita)로 보내는 특수 케이스(기타 그룹)로, 호출부에서 개별 처리.
function subjectHref(g, { sido, sigungu, dong } = {}) {
  const params = [];
  if (sido) params.push(`sido=${encodeURIComponent(sido)}`);
  if (sigungu) params.push(`sigungu=${encodeURIComponent(sigungu)}`);
  if (dong) params.push(`dong=${encodeURIComponent(dong)}`);
  params.push(`subject=${encodeURIComponent(g.key)}`);
  return `/search?${params.join("&")}`;
}

export const SITE_NAME = "우리아이학원정보";
// 수강료 등록/변경 요청 수신 메일 — 실제 운영 메일 확정되면 이 한 줄만 교체
export const FEE_REQUEST_EMAIL = "hardbar@naver.com";

// 하우스 광고(방구석 약국). 우선 홈 URL, 추후 "수험생 영양제" 글 URL로 교체 예정 — 이 상수만 바꾸면 됨.
const HOUSE_AD = {
  url: "https://bangpharmacy.blogspot.com/2026/07/2_0780808016.html",
  title: "우리 아이 집중력, 뭘 먹여야 할까?",
  sub: "수험생 영양제 총정리 · 방구석 약국",
};

// 광고 슬롯 컴포넌트. 지금은 하우스 배너/자리표시만, 추후 슬롯별로 애드센스·쿠팡 코드로 교체 가능.
// kind: 'house' | 'adsense' | 'coupang' | 'personal', area: grid-area 클래스(banner/ad/'')
function adxHtml(kind, { area = "", label = "" } = {}) {
  const areaCls = area ? ` ${area}` : "";
  if (kind === "house") {
    return `<a href="${esc(HOUSE_AD.url)}" target="_blank" rel="noopener sponsored" class="adx house${areaCls}">
      <span class="h-left">
        <span class="h-tag"><i class="ph-fill ph-pill"></i> 광고 · 방구석 약국</span>
        <span class="h-title">${esc(HOUSE_AD.title)}</span>
        <span class="h-sub">${esc(HOUSE_AD.sub)}</span>
      </span>
      <span class="h-cta">자세히 보기 <i class="ph ph-arrow-right"></i></span>
    </a>`;
  }
  // 애드센스/쿠팡 등은 실제 광고가 붙기 전까지 빈 "광고 자리" 박스를 노출하지 않는다.
  return "";
}

const CSS = `
:root{
  --blue:#3b5bdb; --blue-hover:#2f49b0; --navy:#16213e; --header-navy:#1a2a52;
  --slate-700:#48507a; --slate-500:#6b74a0; --slate-400:#9aa0c4; --muted-2:#c2c8e0;
  --border:#e5e8f4; --border-2:#dfe3f3; --divider:#eef1f7; --bg:#f2f4fb; --hero-bg:#eef1fb; --white:#fff;
  --green-bg:#e8f5ee; --green-text:#1f8a5b; --green-dot:#1f8a5b;
  --gray-badge-bg:#eef1f7; --gray-badge-text:#7c84ab;
  --info-bg:#f5c518; --info-text:#4a3a00; --pin:#e8556b;
  --star-gold:#f5b800; --star-empty:#d3d8ea;
  --chip-bg:#eef1fb; --chip-text:#3b5bdb;
  --ad-border:#d6dbec; --ad-text:#9aa0c4;
}
*{box-sizing:border-box}
body{font-family:Pretendard,"Malgun Gothic",-apple-system,BlinkMacSystemFont,sans-serif;margin:0;line-height:1.6;color:var(--slate-700);background:var(--bg)}
a{color:inherit}
.page{max-width:520px;margin:0 auto;background:var(--bg);min-height:100vh}
header.site{position:sticky;top:0;z-index:5;background:var(--white);border-bottom:1px solid var(--border);padding:12px 18px}
header.site .row{display:flex;align-items:center;justify-content:space-between;margin-bottom:11px}
header.site.home .row{margin-bottom:0}
.brand{display:flex;align-items:center;gap:8px;text-decoration:none}
.brand .logo{width:34px;height:34px;border-radius:10px;background:var(--blue);display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0}
.brand .logo i{font-size:20px}
.brand .name{font-size:16px;font-weight:800;color:var(--navy)}
.home-link{font-size:14px;font-weight:600;color:var(--slate-500);text-decoration:none}
.search-form{display:flex;flex-direction:column;gap:6px}
.search-form .row{display:flex;gap:6px;flex-wrap:wrap}
.search-form .row select{flex:1 1 90px;min-width:80px}
.search-form select{border:1px solid #e0e6f0;border-radius:10px;padding:8px 8px;font-size:12.5px;color:var(--navy);background:var(--bg);flex:1;min-width:0}
.search-form input[type=text]{border:1px solid #e0e6f0;border-radius:10px;padding:8px 10px;font-size:13px;color:var(--navy);background:var(--bg);flex:1;min-width:0;outline:none}
.search-form button{border:none;background:var(--blue);color:#fff;font-size:13px;font-weight:700;padding:8px 14px;border-radius:10px;cursor:pointer;white-space:nowrap}
.hero{padding:38px 22px 30px;background:linear-gradient(#eaf0fd,var(--bg))}
.hero.minimal{padding:72px 24px 84px}
.hero.minimal h1{font-size:27px}
.hero.minimal p{margin-bottom:28px}
.quiet-links{font-size:12px;color:var(--slate-400);line-height:2;margin:4px 0}
.quiet-links .quiet-label{color:var(--slate-500);font-weight:600;margin-right:8px}
.quiet-links a{color:var(--slate-400);text-decoration:none}
.quiet-links a:hover{color:var(--blue);text-decoration:underline}
.hero h1{font-size:25px;line-height:1.32;font-weight:800;color:var(--navy);margin:0 0 6px;letter-spacing:-0.02em}
.hero p{font-size:14px;color:var(--slate-500);margin:0 0 20px}
.hero .search-form{background:#fff;border:1.5px solid var(--blue);border-radius:14px;padding:14px;box-shadow:0 8px 20px -8px rgba(29,78,216,.35);gap:8px}
.hero .search-form select{padding:11px 10px;font-size:13.5px;background:var(--bg)}
.hero .search-form input[type=text]{padding:11px 12px;font-size:14px;background:var(--bg)}
.hero .search-form button{padding:11px 18px;font-size:14px}
.body-pad{padding:16px 18px 28px}
.body-pad.home{padding:6px 22px 30px}
h2.section{font-size:15px;font-weight:800;color:var(--navy);margin:22px 0 12px}
.region-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.region-btn{border:1px solid var(--border);background:#fff;color:var(--slate-700);font-size:13.5px;font-weight:600;padding:12px 0;border-radius:11px;text-decoration:none;text-align:center;display:block}
.region-btn.all{border-color:var(--border);background:var(--chip-bg);color:var(--blue);font-size:13px;font-weight:700}
.cat-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.cat-card{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid var(--border);border-radius:14px;padding:14px 16px;text-decoration:none}
.cat-card .icon{width:38px;height:38px;border-radius:11px;background:var(--chip-bg);color:var(--blue);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;flex-shrink:0}
.cat-card .label{font-size:14.5px;font-weight:700;color:var(--navy);display:block}
.cat-card .sub{font-size:11.5px;color:var(--slate-400);display:block}
.cat-groups{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
/* 분야 카드 그리드 (시군구 허브). 정사각형 대신 컴팩트하게 — 아이콘 소형 + 낮은 높이. */
.subject-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.subject-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;padding:13px 10px;background:#fff;border:1px solid var(--border);border-radius:12px;text-decoration:none}
.subject-btn .s-icon{width:44px;height:44px;border-radius:12px;background:var(--chip-bg);color:var(--blue);display:flex;align-items:center;justify-content:center;font-weight:800}
.subject-btn .s-icon i{font-size:24px}
.subject-btn .s-name{font-size:13.5px;font-weight:700;color:var(--navy);text-align:center}
.subject-btn .s-count{font-size:17px;font-weight:800;color:var(--blue)}
.subject-btn.active{background:var(--blue);border-color:var(--blue)}
.subject-btn.active .s-icon{background:rgba(255,255,255,.18);color:#fff}
.subject-btn.active .s-name,.subject-btn.active .s-count{color:#fff}
@media (max-width:560px){
  .subject-grid{grid-template-columns:repeat(3,1fr);gap:8px}
  .subject-btn{padding:7px;gap:5px}
  .subject-btn .s-icon{width:40px;height:40px;border-radius:11px}
  .subject-btn .s-icon i{font-size:23px}
  .subject-btn .s-name{font-size:11.5px;line-height:1.2}
  .subject-btn .s-count{font-size:15px}
  .subject-grid .subject-btn:last-child:nth-child(10){grid-column:2}
}
.chip-row{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px}
.chip-row a{background:var(--chip-bg);color:var(--chip-text);font-size:12.5px;font-weight:600;padding:5px 11px;border-radius:999px;text-decoration:none}
.chip-row a.active{background:var(--blue);color:#fff}
/* 목록 페이지 상단 카테고리 필터 바 (시안: 웹 10칸, 모바일 5열×2 + 개수 배지) */
.cat-bar{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;margin-bottom:18px}
.cat-bar a{display:flex;flex-direction:column;align-items:center;gap:6px;padding:9px 4px;background:#fff;border:1px solid var(--border);border-radius:12px;text-decoration:none}
.cat-bar a .cb-icon{width:32px;height:32px;border-radius:9px;background:var(--chip-bg);color:var(--blue);font-weight:800;display:flex;align-items:center;justify-content:center}
.cat-bar a .cb-icon i{font-size:19px}
.cat-bar a .cb-name{font-weight:700;font-size:11px;color:var(--navy);line-height:1.2;text-align:center;min-height:26px;display:flex;align-items:center;justify-content:center}
.cat-bar a .cb-count{font-size:12px;font-weight:800;color:var(--blue)}
.cat-bar a.active{background:var(--blue);border-color:var(--blue)}
.cat-bar a.active .cb-icon{background:rgba(255,255,255,.18);color:#fff}
.cat-bar a.active .cb-name{color:#fff}
.cat-bar a.active .cb-count{color:rgba(255,255,255,.9)}
@media (max-width:560px){
  .cat-bar{grid-template-columns:repeat(5,1fr);gap:12px 6px;padding-top:12px}
  .cat-bar a{position:relative;padding:8px 4px}
  .cat-bar a .cb-icon{width:28px;height:28px;border-radius:8px}
  .cat-bar a .cb-icon i{font-size:16px}
  .cat-bar a .cb-name{font-size:10px;min-height:24px}
  .cat-bar a .cb-count{position:absolute;top:-5px;right:-3px;background:var(--header-navy);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:999px;box-shadow:0 0 0 2px var(--bg)}
  .cat-bar a.active .cb-count{background:var(--blue)}
}
.cat-group{background:#fff;border:1px solid var(--border);border-radius:14px;overflow:hidden}
.cat-group summary{display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;list-style:none}
.cat-group summary::-webkit-details-marker{display:none}
.cat-group summary .icon{width:38px;height:38px;border-radius:11px;background:var(--chip-bg);color:var(--blue);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;flex-shrink:0}
.cat-group summary .label{font-size:14.5px;font-weight:700;color:var(--navy);display:block}
.cat-group summary .sub{font-size:11.5px;color:var(--slate-400);display:block}
.cat-group .sub-list{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 14px;border-top:1px solid #eef1f7;margin-top:0}
.cat-group .sub-list a{background:var(--chip-bg);color:var(--chip-text);font-size:12.5px;font-weight:600;padding:5px 11px;border-radius:999px;text-decoration:none;margin-top:12px}
footer.site{margin-top:28px;padding-top:20px;border-top:1px solid var(--border);text-align:center}
footer.site .name{font-size:14px;font-weight:800;color:var(--navy);margin-bottom:8px}
footer.site .links{display:flex;justify-content:center;gap:14px;font-size:12.5px;color:var(--slate-400)}
footer.site .links a{text-decoration:none;color:var(--slate-500);font-weight:600}
footer.site .contact{font-size:12px;color:var(--slate-400);margin-top:10px}
footer.site .contact a{color:var(--slate-500);font-weight:600;text-decoration:none}
footer.site .copyright{font-size:11.5px;color:#b6bfd2;margin-top:10px}
.breadcrumb{font-size:12.5px;color:var(--slate-400);margin-bottom:14px;display:flex;gap:6px;flex-wrap:wrap}
.breadcrumb a{text-decoration:none;color:var(--slate-400)}
.breadcrumb .current{color:var(--slate-500);font-weight:600}
.page-title{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:6px;gap:8px}
.page-title h1{font-size:19px;font-weight:800;color:var(--navy);margin:0}
.page-title .count{font-size:13px;color:var(--slate-400);font-weight:600;white-space:nowrap}
.intro{font-size:13px;color:var(--slate-500);margin:0 0 14px}
.card-list{display:grid;grid-template-columns:1fr;gap:10px}
.a-card{display:block;background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px 18px;text-decoration:none;position:relative;overflow:hidden}
.a-card.provided{background:#f7f9ff;border-color:#b9c6f2}
.a-card .ribbon-info{position:absolute;bottom:14px;right:-30px;transform:rotate(-45deg);background:var(--info-bg);color:var(--info-text);font-size:10px;font-weight:800;letter-spacing:.5px;padding:4px 34px;box-shadow:0 1px 3px rgba(0,0,0,.15);display:inline-flex;align-items:center;gap:3px}
.a-card .ribbon-info i{font-size:11px}
.a-card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:7px;min-width:0}
.a-card .a-name{font-size:15.5px;font-weight:700;color:var(--navy);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1}
.badge-fee{flex:0 0 auto;font-size:12px;font-weight:600;padding:5px 10px;border-radius:999px}
.badge-fee.yes{color:var(--green-text);background:var(--green-bg)}
.badge-fee.no{color:var(--gray-badge-text);background:var(--gray-badge-bg)}
.a-card .a-right{flex:0 0 auto;display:flex;flex-direction:column;align-items:flex-end;gap:3px}
.a-card .price-inline{font-size:14px;font-weight:800;color:var(--blue);white-space:nowrap}
.a-card .price-inline .won-unit{font-size:12px;font-weight:700}
.a-card .noinfo{font-size:11px;font-weight:600;color:#b3b9d4}
.card-status{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;color:var(--green-text);margin-right:6px}
.card-status .dot{width:5px;height:5px;border-radius:50%;background:var(--green-dot);display:inline-block}
.card-status.closed{color:#c5221f}
.card-status.closed .dot{background:#c5221f}
.a-card .meta{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.stars{color:var(--star-gold);font-size:13px;letter-spacing:1px}
.stars .empty{color:var(--star-empty)}
.rating-num{font-size:13px;font-weight:700;color:var(--navy)}
.rating-sub{font-size:12px;color:var(--slate-400)}
.price-line{font-size:13px;color:var(--slate-700);font-weight:600}
.price-line .won{color:var(--blue);font-weight:800}
.ad-slot{margin-top:16px}
.ad-slot .ad-label{font-size:10px;color:#b6bfd2;letter-spacing:.06em;margin:0 0 4px 2px}
.ad-slot .placeholder{height:100px;border-radius:12px;border:1px dashed var(--ad-border);background:repeating-linear-gradient(135deg,#fff,#fff 9px,#f1f4fa 9px,#f1f4fa 18px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}
.ad-slot.small .placeholder{height:90px}
.ad-slot.large .placeholder{height:250px}
.ad-slot .placeholder span{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--ad-text)}
.ad-slot .placeholder span.sub{font-size:10px;color:#b6bfd2}
.ad-slot img{width:100%;border-radius:12px;display:block}
.pagination{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:24px}
.pagination a,.pagination span{width:36px;height:36px;border:1px solid #e0e6f0;background:#fff;color:var(--slate-700);border-radius:9px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:flex;align-items:center;justify-content:center}
.pagination .current{border:none;background:var(--blue);color:#fff;font-weight:700}
.info-card{background:#fff;border:1px solid var(--border);border-radius:18px;padding:20px;box-shadow:0 1px 3px rgba(20,30,60,.04)}
.status-badge{display:inline-flex;align-items:center;gap:5px;background:var(--green-bg);color:var(--green-text);font-size:12.5px;font-weight:700;padding:4px 9px;border-radius:999px}
.status-badge.closed{background:#fce8e6;color:#c5221f}
.status-badge .dot{width:6px;height:6px;border-radius:50%;background:var(--green-dot)}
.status-badge.closed .dot{background:#c5221f}
.type-label{font-size:12.5px;color:var(--slate-400);font-weight:500;margin-left:8px}
.info-card h1{font-size:22px;line-height:1.3;font-weight:800;color:var(--navy);margin:8px 0 10px;letter-spacing:-0.02em}
.info-card .rating-row{display:flex;align-items:center;gap:8px;margin-bottom:14px}
.info-card .rating-row .stars{font-size:17px;letter-spacing:2px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:var(--chip-bg);color:var(--chip-text);font-size:12.5px;font-weight:600;padding:5px 11px;border-radius:999px;text-decoration:none}
.phone-cta{margin-top:14px;display:flex;align-items:center;justify-content:center;gap:10px;background:var(--blue);color:#fff;text-decoration:none;padding:17px;border-radius:16px;box-shadow:0 10px 22px -8px rgba(29,78,216,.6)}
.phone-cta .icon{font-size:20px}
.phone-cta .label{font-size:12.5px;font-weight:600;opacity:.85;display:block}
.phone-cta .num{font-size:20px;font-weight:800;letter-spacing:.01em;display:block}
.notice{background:#fff8e1;border:1px solid #ffe082;padding:12px;border-radius:12px;margin:16px 0;font-size:13.5px}
.fee-table{background:#fff;border:1px solid var(--border);border-radius:16px;overflow:hidden}
.fee-table .head{display:flex;justify-content:space-between;padding:11px 16px;background:var(--gray-badge-bg);font-size:12.5px;font-weight:700;color:var(--slate-500)}
.fee-table .row{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-top:1px solid #eef1f7}
.fee-table .course{font-size:15px;font-weight:600;color:#1e293b}
.fee-table .price{font-size:16px;font-weight:800;color:var(--navy)}
.fee-table .price .won{font-size:12px;font-weight:600;color:var(--slate-400)}
/* 컴팩트 수강료 그리드 (과정 여러 개를 한 줄 2~3개로) */
.fee-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.fee-grid .fg-item{background:#fff;border:1px solid var(--border);border-radius:12px;padding:10px 12px;min-width:0}
.fee-grid .fg-course{font-size:12.5px;font-weight:600;color:var(--slate-500);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fee-grid .fg-price{font-size:15px;font-weight:800;color:var(--navy);margin-top:2px}
.fee-grid .fg-price .won{font-size:11px;font-weight:600;color:var(--slate-400)}
@media (min-width:640px){.fee-grid{grid-template-columns:repeat(3,1fr)}}
/* PC 상세 2단 레이아웃: 좌(정보카드/전화/수강료) + 우(기본정보/지도) */
.detail-cols{display:flex;flex-direction:column;gap:16px}
@media (min-width:900px){
  .detail-cols{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;align-items:start}
}
/* 상세 상단 2박스(프로필 | 기본정보) + 배너/광고 (시안) */
.top-row{display:grid;grid-template-columns:1fr;grid-template-areas:'profile' 'banner' 'ad' 'info';gap:14px;margin-bottom:16px}
@media (min-width:900px){
  .top-row{grid-template-columns:1.5fr 1fr;grid-template-areas:'profile info' 'banner banner' 'ad ad';gap:20px;align-items:stretch}
}
.prof-box{grid-area:profile;background:#fff;border:1px solid var(--border);border-radius:14px;padding:22px;position:relative;display:flex;flex-direction:column}
.prof-box .prof-seal{position:absolute;top:16px;right:16px;display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:800;color:var(--info-text);background:var(--info-bg);padding:4px 10px;border-radius:999px}
.prof-box .op{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:700;color:var(--green-text);margin-bottom:10px}
.prof-box .op .dot{width:7px;height:7px;border-radius:50%;background:var(--green-text)}
.prof-box .op.closed{color:#c5221f}.prof-box .op.closed .dot{background:#c5221f}
.prof-box h1{font-size:25px;font-weight:800;color:var(--navy);margin:0;line-height:1.25;flex-shrink:0}
.prof-box .title-row{display:flex;align-items:center;flex-wrap:wrap;gap:6px 10px;margin:0 0 10px}
.prof-box .title-row .share-btn{flex-shrink:0;padding:5px 10px;font-size:11px;gap:4px}
.prof-box .title-row .share-btn i{font-size:13px}
.prof-box .tags{display:flex;flex-wrap:wrap;gap:7px}
.prof-box .tags .chip{font-size:12.5px;font-weight:700;color:var(--blue);background:var(--chip-bg);padding:5px 11px;border-radius:999px;text-decoration:none}
.report-link{background:none;border:none;color:var(--slate-400);font-size:11.5px;text-decoration:underline;cursor:pointer;padding:5px 2px}
.prof-box .prof-foot{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-top:16px}
.prof-box .prof-foot .stars{font-size:16px}
.info-box{grid-area:info;background:#fff;border:1px solid var(--border);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.info-box .ib-head{padding:14px 16px;border-bottom:1px solid var(--divider);font-size:16px;font-weight:800;color:var(--navy)}
.info-box .ib-row{display:flex;gap:14px;padding:15px 16px;border-bottom:1px solid var(--divider)}
.info-box .ib-row .k{flex-shrink:0;width:44px;font-size:13px;color:var(--slate-400)}
.info-box .ib-row .v{font-size:13.5px;color:var(--navy);line-height:1.5}
.info-box .ib-row .v a{color:var(--blue);font-weight:700}
.info-box .ib-cta{display:flex;flex-direction:column;align-items:center;gap:2px;margin-top:auto;padding:16px;border:none;background:var(--blue);color:#fff;cursor:pointer;text-decoration:none}
.info-box .ib-cta .lbl{font-size:12.5px;font-weight:600;opacity:.85}
.info-box .ib-cta .num{display:flex;align-items:center;gap:8px;font-size:20px;font-weight:800}
.map-box2{position:relative;background:var(--divider);border:1px solid var(--border);border-radius:12px;flex:1;min-height:170px;margin-top:16px;display:flex;align-items:center;justify-content:center}
.map-box2 .pin{font-size:30px;color:var(--pin)}
.map-box2 .mbtn{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:6px;padding:9px 18px;border:1px solid var(--border);border-radius:999px;background:#fff;color:var(--navy);font-weight:700;font-size:13px;cursor:pointer;box-shadow:0 2px 8px rgba(30,40,80,.1)}
/* 상세 광고/배너 슬롯 (하우스/쿠팡/애드센스 공용 컴포넌트) */
.adx{display:flex;align-items:center;justify-content:center;border:1px dashed var(--ad-border);border-radius:12px;background:repeating-linear-gradient(45deg,#eef1f7,#eef1f7 10px,#f6f8fc 10px,#f6f8fc 20px);text-align:center;font-family:ui-monospace,monospace;font-size:12px;color:var(--ad-text);text-decoration:none;padding:26px}
.adx.banner{grid-area:banner;height:124px}
.adx.house.banner{height:auto;min-height:124px;justify-content:center}
.adx.ad{grid-area:ad}
.adx.tall{min-height:143px}
.adx.house{background:var(--navy);border:none;color:#fff;font-family:inherit;flex-direction:row;justify-content:space-between;align-items:center;gap:16px;padding:18px 22px;text-align:left}
.adx.house .h-left{display:flex;flex-direction:column;gap:4px;min-width:0}
.adx.house .h-tag{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.14);color:#dfe7fb;font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;align-self:flex-start}
.adx.house .h-title{font-size:16px;font-weight:800;color:#fff;line-height:1.35;margin-top:4px}
.adx.house .h-sub{font-size:12.5px;color:#aebbdc}
.adx.house .h-cta{flex-shrink:0;display:inline-flex;align-items:center;gap:6px;background:var(--blue);color:#fff;font-size:12.5px;font-weight:700;padding:9px 15px;border-radius:9px;white-space:nowrap}
@media (max-width:560px){.adx.house{flex-direction:column;align-items:flex-start}.adx.house .h-cta{align-self:stretch;justify-content:center}}
.ad-label{font-size:10px;color:#b6bfd2;letter-spacing:.06em;margin:0 0 4px 2px}
.related-list .r-badges{display:flex;align-items:center;gap:6px}
.badge-verify{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:800;color:var(--info-text);background:var(--info-bg);padding:3px 8px;border-radius:999px}
.badge-feecheck{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:700;color:var(--green-text);background:var(--green-bg);padding:3px 8px;border-radius:999px}
/* 정보 등록 폼 */
.reg-form .fg-row{display:flex;gap:8px;margin-bottom:8px}
.reg-form .fg-row input{flex:1;min-width:0;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13.5px}
.reg-form .fg-row button.rm{flex:0 0 auto;width:38px;border:1px solid var(--border);background:#fff;color:var(--slate-400);border-radius:8px;cursor:pointer;font-size:16px}
.reg-form label{display:block;font-size:12.5px;font-weight:700;color:var(--slate-500);margin:14px 0 6px}
.reg-form input.full{width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13.5px}
.reg-form .add-course{background:#eef2fb;border:1px dashed #c9d3e8;color:var(--blue);font-size:12.5px;font-weight:700;padding:8px;border-radius:8px;cursor:pointer;width:100%;margin-top:2px}
.reg-form .reg-guide{background:#e8f5ee;border:1px solid #b6e0c8;color:#155e3a;padding:11px;border-radius:10px;font-size:12.5px;line-height:1.6;margin-top:14px}
.reg-form .reg-guide.err{background:#fdecec;border-color:#f5c2c2;color:#a3312f}
.reg-form select.full{width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13.5px;background:#fff}
.modal-box.wide{max-width:520px;max-height:86vh;overflow-y:auto}
.info-cta{width:100%;margin-top:10px;background:#eef2fb;border:1px solid #c9d3e8;color:var(--blue);font-size:13px;font-weight:700;padding:11px;border-radius:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px}
.fee-request-btn{width:100%;margin-top:10px;background:#fff;border:1px solid #c9d3e8;color:var(--blue);font-size:13.5px;font-weight:700;padding:12px;border-radius:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px}
.info-list{background:#fff;border:1px solid var(--border);border-radius:16px;padding:4px 16px}
.info-list .row{display:flex;gap:14px;padding:12px 0;border-top:1px solid #eef1f7}
.info-list .row:first-child{border-top:none}
.info-list .label{width:52px;flex:0 0 auto;font-size:13.5px;color:var(--slate-400);font-weight:600}
.info-list .value{font-size:14px;color:#1e293b;line-height:1.5}
.info-list .value a{color:var(--blue);font-weight:700;text-decoration:none}
.map-widget{margin-top:14px;height:150px;border-radius:16px;overflow:hidden;border:1px solid var(--border);position:relative;background:linear-gradient(135deg,#e8eef8,#eef2fb)}
.map-widget .map-box{width:100%;height:100%}
.map-toggle-btn{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);border:none;background:#fff;color:var(--blue);font-size:13px;font-weight:700;padding:9px 18px;border-radius:999px;box-shadow:0 3px 10px rgba(20,30,60,.15);cursor:pointer}
.map-pin{position:absolute;top:50%;left:50%;transform:translate(-50%,-100%);font-size:26px;pointer-events:none}
.map-unavailable{color:var(--slate-400);font-size:13px;margin-top:14px}
.related-list{background:#fff;border:1px solid var(--border);border-radius:16px;overflow:hidden}
.related-list a{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;text-decoration:none;border-top:1px solid #eef1f7}
.related-list a:first-child{border-top:none}
.related-list .r-name{font-size:14px;font-weight:600;color:#1e293b}
.related-list .r-fee{font-size:11px;color:var(--green-dot);font-weight:600}
.related-list .r-arrow{font-size:16px;color:#c4ccdd}
.rating-widget{margin-top:14px;padding:14px;background:#fff;border:1px solid var(--border);border-radius:16px}
.rating-widget .rating-stars{font-size:26px;letter-spacing:2px;cursor:pointer}
.rating-widget .rating-stars .star{color:var(--star-empty)}
.rating-widget .rating-stars .star.filled{color:var(--star-gold)}
.rating-widget .rating-summary{font-size:13px;color:var(--slate-500);margin-top:6px}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(15,30,68,.45);z-index:50;align-items:center;justify-content:center;padding:20px}
.modal-overlay.open{display:flex}
.modal-box{background:#fff;border-radius:18px;padding:24px;max-width:380px;width:100%}
.modal-box h3{font-size:17px;font-weight:800;color:var(--navy);margin:0 0 10px}
.modal-box p{font-size:13.5px;color:var(--slate-500);margin:0 0 16px;line-height:1.6}
.modal-box .modal-actions{display:flex;gap:8px;margin-top:18px}
.modal-box .btn-primary{flex:1;background:var(--blue);color:#fff;border:none;padding:12px;border-radius:10px;font-size:14px;font-weight:700;text-align:center;text-decoration:none;cursor:pointer}
.modal-box .btn-secondary{flex:1;background:#fff;color:var(--slate-500);border:1px solid var(--border);padding:12px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer}
.search-results{display:flex;flex-direction:column;gap:10px}
.search-result-type{font-size:11px;color:var(--slate-400);font-weight:700;margin:18px 0 8px}
.share-btn{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid var(--border);color:var(--slate-700);font-size:12.5px;font-weight:700;padding:8px 13px;border-radius:10px;cursor:pointer;white-space:nowrap}
.share-btn i{font-size:15px}
.share-btn:active{background:var(--bg)}
.page-title-row{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:var(--navy);color:#fff;font-size:13px;font-weight:600;padding:10px 18px;border-radius:999px;box-shadow:0 4px 16px rgba(0,0,0,.25);z-index:100;opacity:0;pointer-events:none;transition:opacity .25s}
.toast.show{opacity:1}
@media (min-width:900px){
  .page{max-width:900px}
  .card-list{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  .search-results{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
}
`;

function widgetsScript(env) {
  return `<script>
window.__KAKAO_JS_KEY = ${JSON.stringify(env.KAKAO_JS_KEY)};
window.__TIPOFF_API_BASE = ${JSON.stringify(env.TIPOFF_API_BASE)};
window.__REGION_MAP = ${JSON.stringify(env.REGION_MAP || {})};

function initRegionForm(form) {
  var sidoSel = form.querySelector(".region-sido");
  var sigunguSel = form.querySelector(".region-sigungu");
  var dongSel = form.querySelector(".region-dong");
  var presetSido = form.querySelector(".region-sido-preset");
  var presetSigungu = form.querySelector(".region-sigungu-preset");
  var presetDong = form.querySelector(".region-dong-preset");
  presetSido = presetSido ? presetSido.value : "";
  presetSigungu = presetSigungu ? presetSigungu.value : "";
  presetDong = presetDong ? presetDong.value : "";

  Object.keys(window.__REGION_MAP).forEach(function (sido) {
    var opt = document.createElement("option");
    opt.value = sido; opt.textContent = sido;
    if (sido === presetSido) opt.selected = true;
    sidoSel.appendChild(opt);
  });

  function fillSigungu(sido, presetVal) {
    sigunguSel.innerHTML = '<option value="">시군구 전체</option>';
    if (dongSel) dongSel.innerHTML = '<option value="">읍면동 전체</option>';
    var map = window.__REGION_MAP[sido] || {};
    Object.keys(map).forEach(function (sg) {
      var opt = document.createElement("option");
      opt.value = sg; opt.textContent = sg;
      if (sg === presetVal) opt.selected = true;
      sigunguSel.appendChild(opt);
    });
  }

  function fillDong(sido, sigungu, presetVal) {
    if (!dongSel) return;
    dongSel.innerHTML = '<option value="">읍면동 전체</option>';
    var list = (window.__REGION_MAP[sido] || {})[sigungu] || [];
    list.forEach(function (d) {
      var opt = document.createElement("option");
      opt.value = d; opt.textContent = d;
      if (d === presetVal) opt.selected = true;
      dongSel.appendChild(opt);
    });
  }

  if (presetSido) fillSigungu(presetSido, presetSigungu);
  if (presetSido && presetSigungu) fillDong(presetSido, presetSigungu, presetDong);

  sidoSel.addEventListener("change", function () { fillSigungu(sidoSel.value, ""); });
  sigunguSel.addEventListener("change", function () { fillDong(sidoSel.value, sigunguSel.value, ""); });
}

document.querySelectorAll(".region-search-form").forEach(initRegionForm);

// 카드 이름이 길면 말줄임표 대신 폰트를 줄여서 한 줄에 맞춘다.
document.querySelectorAll(".a-card .a-name").forEach(function (el) {
  var size = 16;
  el.style.fontSize = size + "px";
  while (el.scrollWidth > el.clientWidth && size > 11) {
    size -= 0.5;
    el.style.fontSize = size + "px";
  }
});

function getVoterToken() {
  var key = "academy_site_voter_token";
  var token = localStorage.getItem(key);
  if (!token) {
    token = Array.from(crypto.getRandomValues(new Uint8Array(16))).map(function(b){return b.toString(16).padStart(2,"0");}).join("");
    localStorage.setItem(key, token);
  }
  return token;
}

document.addEventListener("click", function (ev) {
  var openBtn = ev.target.closest("[data-open-modal]");
  if (openBtn) {
    var modal = document.getElementById(openBtn.getAttribute("data-open-modal"));
    if (modal) modal.classList.add("open");
    return;
  }
  var closeBtn = ev.target.closest("[data-close-modal]");
  if (closeBtn) {
    var modal2 = closeBtn.closest(".modal-overlay");
    if (modal2) modal2.classList.remove("open");
    return;
  }
  if (ev.target.classList && ev.target.classList.contains("modal-overlay")) {
    ev.target.classList.remove("open");
  }

  var star = ev.target.closest(".rating-stars .star");
  if (star) return handleRatingClick(star);

  var shareBtn = ev.target.closest("[data-share]");
  if (shareBtn) return handleShareClick(shareBtn);

  // 정보 등록 폼: 과정 행 추가/삭제
  var addBtn = ev.target.closest(".reg-form .add-course");
  if (addBtn) {
    var rows = addBtn.previousElementSibling; // .course-rows
    var first = rows.querySelector(".fg-row");
    var clone = first.cloneNode(true);
    clone.querySelectorAll("input").forEach(function (i) { i.value = ""; });
    rows.appendChild(clone);
    return;
  }
  var rmBtn = ev.target.closest(".reg-form .fg-row .rm");
  if (rmBtn) {
    var rowsWrap = rmBtn.closest(".course-rows");
    if (rowsWrap.querySelectorAll(".fg-row").length > 1) rmBtn.closest(".fg-row").remove();
    return;
  }
});

document.addEventListener("submit", function (ev) {
  if (ev.target.id === "search-form") return; // 기본 GET 제출 사용
  if (ev.target.classList.contains("tipoff-form")) {
    ev.preventDefault();
    return handleTipoffSubmit(ev.target);
  }
  if (ev.target.classList.contains("reg-form")) {
    ev.preventDefault();
    return handleRegSubmit(ev.target);
  }
});

function handleRegSubmit(form) {
  function val(n) { var el = form.querySelector('[name="' + n + '"]'); return el ? el.value.trim() : ""; }
  var mode = form.getAttribute("data-mode") || "edit";
  var guide = form.querySelector(".reg-guide");
  guide.style.display = "block";

  // 분류 오류 신고: 대상 slug + 신고 내용만 필수, 나머지 필드 없음(사업자 아니어도 제출 가능).
  if (mode === "correction") {
    var note = val("classification_note");
    if (!note) { guide.className = "reg-guide err"; guide.innerHTML = "신고 내용을 입력해 주세요."; return; }
    submitReg(form, guide, {
      mode: "correction",
      entity_type: form.getAttribute("data-entity-type") || "academy",
      entity_slug: form.getAttribute("data-slug") || null,
      name: form.getAttribute("data-name") || null,
      classification_note: note,
      reply_email: val("email") || null,
    }, "신고가 접수되었습니다. 확인 후 반영하겠습니다.");
    return;
  }

  var courses = [];
  var ok = true;
  form.querySelectorAll(".course-rows .fg-row").forEach(function (row) {
    var c = row.querySelector('[name="course"]').value.trim();
    var p = row.querySelector('[name="price"]').value.trim();
    if (!c || !p) ok = false;
    else courses.push({ course: c, price: p });
  });
  var address = val("address"), phone = val("phone"), email = val("email");
  var need = !ok || !courses.length || !address || !phone || !email;
  var name = mode === "new" ? val("name") : form.getAttribute("data-name");
  var sido = val("sido"), sigungu = val("sigungu"), dong = val("dong");
  if (mode === "new" && (!name || !sido || !sigungu)) need = true;
  if (need) { guide.className = "reg-guide err"; guide.innerHTML = "모든 항목을 입력해 주세요. 부분 등록은 불가합니다."; return; }

  var payload = {
    mode: mode,
    entity_type: form.getAttribute("data-entity-type") || "academy",
    entity_slug: form.getAttribute("data-slug") || null,
    name: name, sido: sido || null, sigungu: sigungu || null, dong: dong || null,
    address: address, phone: phone, category: val("category") || null,
    courses: courses, reply_email: email,
  };
  var doneMsg = "신청이 접수되었습니다. <b>사업자등록증</b>을 <b>" + form.getAttribute("data-email") + "</b>로 보내주시면 확인 후 사이트에 반영됩니다. (승인 전까지는 노출되지 않습니다)";
  submitReg(form, guide, payload, doneMsg);
}

function submitReg(form, guide, payload, doneMsg) {
  var btn = form.querySelector('button[type="submit"]');
  if (btn) btn.disabled = true;
  guide.className = "reg-guide";
  guide.innerHTML = "제출 중...";
  fetch(window.__TIPOFF_API_BASE + "/info-submit", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  })
    .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
    .then(function (res) {
      if (!res.ok) { guide.className = "reg-guide err"; guide.innerHTML = (res.d && res.d.error) || "제출 실패"; if (btn) btn.disabled = false; return; }
      form.querySelectorAll("input").forEach(function (i) { i.disabled = true; });
      guide.className = "reg-guide";
      guide.innerHTML = doneMsg;
    })
    .catch(function () { guide.className = "reg-guide err"; guide.innerHTML = "네트워크 오류, 잠시 후 다시 시도해주세요."; if (btn) btn.disabled = false; });
}

// 지도는 클릭 없이 페이지 진입 시 자동 로드(item4). 같은 페이지에 여러 지도가 있어도 SDK는 한 번만 불러옴.
function initAutoMaps() {
  var wraps = document.querySelectorAll(".map-widget.auto");
  if (!wraps.length) return;
  function renderAll() {
    wraps.forEach(function (wrap) {
      var box = wrap.querySelector(".map-box");
      var lat = parseFloat(wrap.dataset.lat);
      var lng = parseFloat(wrap.dataset.lng);
      var name = wrap.dataset.name;
      var center = new kakao.maps.LatLng(lat, lng);
      var map = new kakao.maps.Map(box, { center: center, level: 3 });
      new kakao.maps.Marker({ map: map, position: center, title: name });
    });
  }
  if (window.kakao && window.kakao.maps) return renderAll();
  var script = document.createElement("script");
  script.src = "https://dapi.kakao.com/v2/maps/sdk.js?appkey=" + window.__KAKAO_JS_KEY + "&autoload=false";
  script.onload = function () { kakao.maps.load(renderAll); };
  document.head.appendChild(script);
}
initAutoMaps();

function handleTipoffSubmit(form) {
  var section = form.closest(".tipoff-section");
  var statusEl = form.querySelector(".tipoff-status");
  statusEl.textContent = "제출 중...";
  fetch(window.__TIPOFF_API_BASE + "/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entity_type: section.dataset.entityType,
      entity_slug: section.dataset.slug,
      entity_name: section.dataset.name,
      phone: form.phone.value,
      submitter_type: form.submitter_type.value,
    }),
  })
    .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
    .then(function () {
      statusEl.textContent = "제출됐습니다. 검토 후 반영됩니다.";
      form.querySelector("button[type=submit]").disabled = true;
    })
    .catch(function () { statusEl.textContent = "제출 실패, 잠시 후 다시 시도해주세요."; });
}

function handleRatingClick(starEl) {
  var widget = starEl.closest(".rating-widget");
  var score = Number(starEl.dataset.score);
  var stars = widget.querySelectorAll(".star");
  stars.forEach(function (s) { s.classList.toggle("filled", Number(s.dataset.score) <= score); });
  var summary = widget.querySelector(".rating-summary");
  summary.textContent = "제출 중...";
  fetch(window.__TIPOFF_API_BASE + "/rate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entity_type: widget.dataset.entityType,
      entity_slug: widget.dataset.slug,
      score: score,
      voter_token: getVoterToken(),
    }),
  })
    .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
    .then(function (data) {
      summary.textContent = "평균 " + Number(data.average).toFixed(1) + "점 (" + data.count + "명 참여) · 내 별점: " + score + "점";
    })
    .catch(function () { summary.textContent = "별점 등록 실패, 잠시 후 다시 시도해주세요."; });
}

function showToast(msg) {
  var el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  requestAnimationFrame(function () { el.classList.add("show"); });
  setTimeout(function () {
    el.classList.remove("show");
    setTimeout(function () { el.remove(); }, 300);
  }, 1800);
}

function handleShareClick(btn) {
  var shareTitle = btn.getAttribute("data-share-title") || document.title;
  var shareUrl = location.href;
  if (navigator.share) {
    navigator.share({ title: shareTitle, url: shareUrl }).catch(function () {});
    return;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(shareUrl)
      .then(function () { showToast("링크가 복사되었습니다"); })
      .catch(function () { window.prompt("아래 링크를 복사하세요", shareUrl); });
    return;
  }
  window.prompt("아래 링크를 복사하세요", shareUrl);
}
</script>`;
}

function searchFormHtml({ selectedSido, selectedSigungu, selectedDong, q } = {}) {
  return `<form class="search-form region-search-form" action="/search" method="get">
    <div class="row">
      <select name="sido" class="region-sido">
        <option value="">시도 선택</option>
      </select>
      <select name="sigungu" class="region-sigungu">
        <option value="">시군구 전체</option>
      </select>
      <select name="dong" class="region-dong">
        <option value="">읍면동 전체</option>
      </select>
    </div>
    <div class="row">
      <input type="text" name="q" placeholder="과목이나 학원명" value="${esc(q || "")}">
      <button type="submit">검색</button>
    </div>
    <input type="hidden" class="region-sido-preset" value="${esc(selectedSido || "")}">
    <input type="hidden" class="region-sigungu-preset" value="${esc(selectedSigungu || "")}">
    <input type="hidden" class="region-dong-preset" value="${esc(selectedDong || "")}">
  </form>`;
}

function headerHtml({ home, selectedSido, selectedSigungu, selectedDong, q }) {
  return `<header class="site${home ? " home" : ""}">
    <div class="row">
      <a class="brand" href="/"><span class="logo"><i class="ph ph-magnifying-glass"></i></span><span class="name">${SITE_NAME}</span></a>
    </div>
    ${home ? "" : searchFormHtml({ selectedSido, selectedSigungu, selectedDong, q })}
  </header>`;
}

// 모바일에서는 navigator.share로 카톡 포함 기기 공유창을 그대로 띄우고, 미지원 환경(주로 데스크톱)에서는 링크 복사로 대체.
function shareBtnHtml(title) {
  return `<button type="button" class="share-btn" data-share data-share-title="${esc(title)}"><i class="ph ph-share-network"></i>공유하기</button>`;
}

function footerHtml() {
  const year = new Date().getFullYear();
  return `<footer class="site">
    <div class="name">${SITE_NAME}</div>
    <div class="links"><a href="/register/">우리 학원 등록하기</a> · <a href="/privacy/">개인정보처리방침</a></div>
    <div class="contact">문의 <a href="mailto:${FEE_REQUEST_EMAIL}">${FEE_REQUEST_EMAIL}</a></div>
    <div class="copyright">© ${year} ${SITE_NAME}</div>
  </footer>`;
}

function adSlotHtml(slotNum, banner, size) {
  const sizeClass = size === "small" ? " small" : size === "large" ? " large" : "";
  if (banner) {
    return `<div class="ad-slot${sizeClass}">
      <div class="ad-label">광고</div>
      <a href="${esc(banner.link_url)}" target="_blank" rel="noopener sponsored">
        <img src="${esc(banner.image_url)}" alt="${esc(banner.alt_text)}">
      </a>
    </div>`;
  }
  // 실제 배너가 없으면 "광고 자리" 빈 박스를 노출하지 않는다.
  return "";
}

function mapWidgetHtml(lat, lng, name) {
  if (!lat || !lng) {
    return `<p class="map-unavailable">지도를 표시할 좌표 정보가 없습니다.</p>`;
  }
  return `<div class="map-widget" data-lat="${esc(lat)}" data-lng="${esc(lng)}" data-name="${esc(name)}">
    <div class="map-box"></div>
    <div class="map-pin">📍</div>
    <button type="button" class="map-toggle-btn">지도 보기</button>
  </div>`;
}

function tipoffSectionHtml(entityType, slug, name, phone) {
  if (phone) return "";
  const label = entityType === "academy" ? "학원" : "체육관";
  return `<div class="tipoff-section" data-entity-type="${esc(entityType)}" data-slug="${esc(slug)}" data-name="${esc(name)}" style="margin-top:20px;padding:14px;background:#fff;border:1px solid var(--border);border-radius:16px;">
    <p style="margin:0 0 8px;font-size:13.5px;color:var(--slate-500);">이 ${label} 관계자이신가요? 정보 등록을 요청해주세요.</p>
    <button type="button" class="fee-request-btn" data-open-modal="tipoff-modal-${esc(slug)}">전화번호 정보 등록 요청</button>
    <div class="modal-overlay" id="tipoff-modal-${esc(slug)}">
      <div class="modal-box">
        <h3>정보 등록 요청</h3>
        <form class="tipoff-form">
          <div style="margin-bottom:10px;">
            <input type="tel" name="phone" placeholder="전화번호" required pattern="[0-9\\-]+" style="width:100%;padding:10px;box-sizing:border-box;border:1px solid var(--border);border-radius:8px;font-size:14px;">
          </div>
          <div style="margin-bottom:8px;font-size:13.5px;">
            <label style="margin-right:12px;"><input type="radio" name="submitter_type" value="관계자" required> 관계자</label>
            <label><input type="radio" name="submitter_type" value="이용자"> 이용자</label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" data-close-modal>취소</button>
            <button type="submit" class="btn-primary" style="border:none;">제출</button>
          </div>
          <span class="tipoff-status" style="display:block;margin-top:8px;font-size:13px;"></span>
        </form>
      </div>
    </div>
  </div>`;
}

// 통합 정보 등록 요청 폼 (학원/도장 공용). 부분 등록 불가 — 과정+수강료, 기본정보, 회신메일 전체 필수.
// 추후 통합 학원정보 등록 페이지로 교체 예정이므로 폼을 독립 컴포넌트로 분리.
function infoRegisterModalHtml(entityType, slug, name, presetAddress, presetPhone) {
  const label = entityType === "academy" ? "학원" : "도장";
  return `<div class="modal-overlay" id="reg-modal-${esc(slug)}">
    <div class="modal-box wide">
      <h3>${esc(label)} 정보 등록 요청</h3>
      <p>아래 항목을 <b>모두</b> 입력해 주세요. 부분 등록은 불가합니다. 승인되면 목록에 '정보제공' 뱃지가 표시됩니다.</p>
      <form class="reg-form" data-mode="edit" data-entity-type="${esc(entityType)}" data-slug="${esc(slug)}" data-name="${esc(name)}" data-email="${esc(FEE_REQUEST_EMAIL)}">
        <label>교육과정 · 월 수강료 (여러 개 입력 가능)</label>
        <div class="course-rows">
          <div class="fg-row">
            <input name="course" placeholder="과정명 (예: 초등수학)">
            <input name="price" placeholder="월 수강료(원)" inputmode="numeric">
            <button type="button" class="rm" title="삭제">×</button>
          </div>
        </div>
        <button type="button" class="add-course">+ 과정 추가</button>
        <label>주소</label>
        <input class="full" name="address" value="${esc(presetAddress || "")}" placeholder="도로명 주소">
        <label>전화번호</label>
        <input class="full" name="phone" value="${esc(presetPhone || "")}" placeholder="02-000-0000">
        <label>회신용 이메일</label>
        <input class="full" name="email" type="email" placeholder="you@example.com">
        <div class="modal-actions">
          <button type="button" class="btn-secondary" data-close-modal>취소</button>
          <button type="submit" class="btn-primary" style="border:none;">제출</button>
        </div>
        <div class="reg-guide" style="display:none;"></div>
      </form>
    </div>
  </div>`;
}

// 분류(종목) 오류 제보용 경량 모달. 사업자 본인이 아니어도(부분 등록 없이) 제출 가능 —
// 대상 slug + 신고 내용만 필수, 나머지 필드 없음.
function correctionModalHtml(entityType, slug, name) {
  return `<div class="modal-overlay" id="correction-modal-${esc(slug)}">
    <div class="modal-box">
      <h3>분류(종목) 오류 신고</h3>
      <p>실제와 다른 분류로 등록된 것 같으면 알려주세요. 확인 후 반영합니다.</p>
      <form class="reg-form" data-mode="correction" data-entity-type="${esc(entityType)}" data-slug="${esc(slug)}" data-name="${esc(name)}">
        <label>어떤 분류가 맞나요?</label>
        <input class="full" name="classification_note" placeholder="예: 태권도가 아니라 종합 체육관입니다">
        <label>회신용 이메일 (선택)</label>
        <input class="full" name="email" type="email" placeholder="you@example.com">
        <div class="modal-actions">
          <button type="button" class="btn-secondary" data-close-modal>취소</button>
          <button type="submit" class="btn-primary" style="border:none;">신고</button>
        </div>
        <div class="reg-guide" style="display:none;"></div>
      </form>
    </div>
  </div>`;
}

// 프로필 박스용 지도. 클릭 없이 페이지 진입 시 자동 로드(트래픽 적은 현재 단계는 사용자 편의 우선).
function mapBox2Html(lat, lng, name) {
  if (!lat || !lng) {
    return `<div class="map-box2"><span style="color:var(--slate-400);font-size:13px;">지도 정보 없음</span></div>`;
  }
  return `<div class="map-widget map-box2 auto" data-lat="${esc(lat)}" data-lng="${esc(lng)}" data-name="${esc(name)}">
    <div class="map-box" style="position:absolute;inset:0;border-radius:12px;"></div>
  </div>`;
}

// 수강료 그리드 본문(값만). 상세 수강료 섹션에서 사용.
function feeGridBody(entity) {
  if (entity.has_fee_data && entity.fee_parsed) {
    const items = JSON.parse(entity.fee_parsed);
    return `<div class="fee-grid">${items
      .map((it) => `<div class="fg-item"><div class="fg-course">${esc(it.course)}</div><div class="fg-price">${comma(it.price)}<span class="won">원</span></div></div>`)
      .join("")}</div>`;
  }
  return `<div class="notice">등록된 수강료 정보가 없습니다.${entity.phone ? ` 전화(${telLink(entity.phone)})로 직접 문의하세요.` : ""}</div>`;
}

// 상세 페이지: 수강료 섹션 + 요청 진입점(공용)
function feeSectionHtml(entity, entityType) {
  const isAcademy = entityType === "academy";
  const hasFee = isAcademy && entity.has_fee_data && entity.fee_parsed;
  let feeBody;
  if (hasFee) {
    const items = JSON.parse(entity.fee_parsed);
    feeBody = `<div class="fee-grid">${items
      .map((it) => `<div class="fg-item"><div class="fg-course">${esc(it.course)}</div><div class="fg-price">${comma(it.price)}<span class="won">원</span></div></div>`)
      .join("")}</div>`;
  } else {
    feeBody = `<div class="notice">등록된 수강료 정보가 없습니다.${entity.phone ? ` 전화(${telLink(entity.phone)})로 직접 문의하세요.` : ""}</div>`;
  }
  return `<h2 class="section">수강료</h2>
  ${feeBody}
  <button type="button" class="fee-request-btn" data-open-modal="reg-modal-${esc(entity.slug)}"><span>✎</span>수강료·정보 등록 요청</button>`;
}

function ratingWidgetHtml(entityType, slug, stats) {
  const avg = stats.count > 0 ? Number(stats.average) : 0;
  const stars = [1, 2, 3, 4, 5]
    .map((n) => `<span class="star${n <= Math.round(avg) ? " filled" : ""}" data-score="${n}">★</span>`)
    .join("");
  const summary = stats.count > 0
    ? `평균 ${avg.toFixed(1)}점 (${stats.count}명 참여)`
    : "아직 별점이 없습니다. 첫 별점을 남겨보세요.";
  return `<div class="rating-widget" data-entity-type="${esc(entityType)}" data-slug="${esc(slug)}">
    <div class="rating-stars">${stars}</div>
    <div class="rating-summary">${esc(summary)}</div>
  </div>`;
}

function starsInline(average, count) {
  const rounded = Math.round(Number(average) || 0);
  let stars = "";
  for (let i = 1; i <= 5; i++) stars += i <= rounded ? "★" : `<span class="empty">★</span>`;
  if (count > 0) {
    return `<span class="stars">${stars}</span><span class="rating-num">${Number(average).toFixed(1)}</span>`;
  }
  return `<span class="stars">${stars}</span>`;
}

// 목록 카드용: 별점이 없으면 아예 표시하지 않음 (빈 별 5개가 어색해 보이는 것 방지)
function starsListCard(average, count) {
  if (!count) return "";
  const rounded = Math.round(Number(average) || 0);
  let stars = "";
  for (let i = 1; i <= 5; i++) stars += i <= rounded ? "★" : `<span class="empty">★</span>`;
  return `<span class="stars">${stars}</span><span class="rating-num">${Number(average).toFixed(1)}</span>`;
}

// 학원명/과정명/수강료 과정으로 실제 과목 라벨 판별 (보습 같은 뭉뚱그린 표기 대신). 매칭 없으면 null.
const CARD_SUBJECT_RULES = [
  ["국어·논술", ["국어", "논술", "독서논술", "문해"]],
  ["수학", ["수학", "수리", "사고력수학"]],
  ["영어", ["영어", "잉글리시", "english"]],
  ["과학", ["과학", "물리", "화학", "생물", "지구과학"]],
  ["미술", ["미술", "그림", "회화", "디자인"]],
  ["음악", ["음악", "피아노", "성악", "바이올린", "실용음악", "드럼"]],
  ["체육", ["체육", "무용", "발레", "태권", "축구", "농구", "수영"]],
  ["외국어", ["어학원", "외국어", "중국어", "일본어", "일어", "중어"]],
  ["독서실·스터디카페", ["독서실", "스터디카페", "스터디룸"]],
];
function matchSubjectText(text) {
  const t = (text || "").toLowerCase();
  if (!t) return null;
  for (const [label, kws] of CARD_SUBJECT_RULES) {
    if (kws.some((k) => t.includes(k.toLowerCase()))) return label;
  }
  return null;
}
// 학원명 우선 → 교습과정 → 수강료 과정명 순으로 판별. 학원명이 명확하면(예: "919수학교습소")
// course_name의 원천 등록값("보습·논술" 등)이 엉뚱하게 앞서 매칭되는 걸 방지.
function academySubjectLabel(it) {
  const byName = matchSubjectText(it.name);
  if (byName) return byName;
  const byCourse = matchSubjectText(it.course_name);
  if (byCourse) return byCourse;
  if (it.fee_parsed) {
    try {
      const courses = JSON.parse(it.fee_parsed).map((c) => c.course || "").join(" ");
      const byFee = matchSubjectText(courses);
      if (byFee) return byFee;
    } catch {}
  }
  return null;
}

// 학원/도장 카드 (목록·읍면동·검색 공용). 정보제공=노란 리본, 미제공=회색 "정보 미제공" 라벨(시안).
// showGu=true면 위치에 시군구 포함(시군구 전체 검색 시), false면 동만.
function itemCardHtml(it, showGu) {
  const loc = showGu
    ? `${esc(it.sigungu)}${it.dong ? " " + esc(it.dong) : ""}`
    : (it.dong ? esc(it.dong) : esc(it.sigungu));
  const subject = it.type === "academy" ? (academySubjectLabel(it) || esc(it.course_name || "")) : esc(it.sport_name || it.category_name || "");
  const isAcademy = it.type === "academy";
  // 가격 자리에는 가격/수강료 정보만. 운영상태("운영중")는 별도 슬롯으로 분리(item1 버그 수정).
  const priceSlot = isAcademy
    ? (it.min_price
        ? `<span class="price-inline">${comma(it.min_price)}<span class="won-unit">원~</span></span>`
        : `<span class="badge-fee no">수강료 미확인</span>`)
    : `<span class="badge-fee no">전화 문의</span>`;
  const statusDot = !isAcademy
    ? `<span class="card-status${it.is_open === false ? " closed" : ""}"><span class="dot"></span>${it.is_open === false ? "운영종료" : "운영중"}</span>`
    : "";
  const noInfo = isAcademy && !it.info_provided ? `<span class="noinfo">정보 미제공</span>` : "";
  const ribbon = it.info_provided ? `<span class="ribbon-info"><i class="ph-fill ph-seal-check"></i>정보확인</span>` : "";
  return `<a class="a-card${it.info_provided ? " provided" : ""}" href="/${esc(it.sido)}/${esc(it.sigungu)}/${esc(it.slug)}/">
    ${ribbon}
    <div class="top">
      <span class="a-name">${esc(it.name)}</span>
      <div class="a-right">${priceSlot}${noInfo}</div>
    </div>
    <div class="meta">
      ${statusDot}
      <span class="rating-sub">${loc}${subject ? " · " + subject : ""}</span>
    </div>
  </a>`;
}

function breadcrumbJsonLd(items) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: it.name,
      item: it.url,
    })),
  };
}

function pageShell({ title, description, path, robotsNoindex, jsonLd, body, env, home, selectedSido, selectedSigungu, selectedDong, q }) {
  const canonicalUrl = env.SITE_ORIGIN + path;
  const jsonLdList = Array.isArray(jsonLd) ? jsonLd : jsonLd ? [jsonLd] : [];
  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-BKZ84P1ML7"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-BKZ84P1ML7');
</script>
<!-- 네이버 애널리틱스 -->
<script type="text/javascript" src="//wcs.pstatic.net/wcslog.js"></script>
<script type="text/javascript">
if(!wcs_add) var wcs_add = {};
wcs_add["wa"] = "24f170daab8c240";
if(window.wcs) {
  wcs_do();
}
</script>
<meta name="google-site-verification" content="ce6_IhdlrvMdGe99K-01PoYsmQ9ILrewt2TU-cYDiDI" />
<meta name="naver-site-verification" content="577d35d1177fd8c2d7aa123751939006cc0aa554" />
<meta name="naver-site-verification" content="62ec7c372ec937ed57003d3ae38c8d01d8fa8f19" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%233b5bdb'/%3E%3Ccircle cx='27' cy='27' r='11' fill='none' stroke='white' stroke-width='5'/%3E%3Cline x1='35' y1='35' x2='46' y2='46' stroke='white' stroke-width='5.5' stroke-linecap='round'/%3E%3C/svg%3E">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<link rel="canonical" href="${esc(canonicalUrl)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(SITE_NAME)}">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(description)}">
<meta property="og:url" content="${esc(canonicalUrl)}">
<meta property="og:image" content="${esc(env.SITE_ORIGIN)}/og-image.svg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${esc(env.SITE_ORIGIN)}/og-image.svg">
${env.SITE_INDEXABLE !== "true" || robotsNoindex ? '<meta name="robots" content="noindex">' : ""}
${jsonLdList.map((ld) => `<script type="application/ld+json">${JSON.stringify(ld)}</script>`).join("\n")}
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css">
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/fill/style.css">
<style>${CSS}</style>
</head>
<body>
<div class="page">
${headerHtml({ home, selectedSido, selectedSigungu, selectedDong, q })}
${body}
</div>
${widgetsScript(env)}
</body>
</html>`;
}

export function homePage(env, sidoList, subjectGroups) {
  const body = `
  <div class="hero minimal">
    <h1>우리 아이에게 맞는 학원,<br>수강료까지 한눈에</h1>
    <p>지역을 선택하고 과목이나 학원명으로 검색하세요.</p>
    ${searchFormHtml({})}
  </div>
  <div class="body-pad home">
    <div class="quiet-links">
      <span class="quiet-label">지역</span>
      ${sidoList.map((s) => `<a href="/${esc(s)}/">${esc(s)}</a>`).join(" · ")}
    </div>
    <div class="quiet-links">
      <span class="quiet-label">분야</span>
      ${subjectGroups.map((g) => `<a href="${subjectHref(g)}">${esc(g.name)}</a>`).join(" · ")}
    </div>
    <div style="margin-top:14px;">${shareBtnHtml(SITE_NAME + " — 우리 아이에게 맞는 학원, 수강료까지 한눈에")}</div>
    <h2 class="section">${SITE_NAME} 소개</h2>
    <p class="intro">${SITE_NAME}는 전국 학원·교습소·체육도장의 위치, 연락처, 수강료 정보를 지역과 분야별로 한눈에 찾아볼 수 있는 서비스입니다. 공공데이터포털 및 행정안전부에서 제공하는 공공데이터를 기반으로 정보를 안내하며, 학원 운영자가 직접 수강료·정보를 등록·수정 요청할 수 있어 최신 정보를 지속적으로 반영합니다. 아이 학원을 고를 때 여러 사이트를 오가며 검색하는 수고를 덜고, 동네 학원의 수강료와 후기를 한 곳에서 비교해보세요.</p>
    ${footerHtml()}
  </div>`;
  return pageShell({
    title: `${SITE_NAME} — 우리 아이에게 맞는 학원, 수강료까지 한눈에`,
    description: "전국 학원·교습소 수강료 정보와 태권도·검도·유도 등 체육도장 정보를 지역별로 검색하세요.",
    path: "/",
    robotsNoindex: false,
    body,
    env,
    home: true,
  });
}

export function academyDetailPage(env, academy, related, ratingStats, banners) {
  const path = `/${academy.sido}/${academy.sigungu}/${academy.slug}/`;
  const isClosed = academy.status !== "개원";
  const presetAddr = `${academy.address_road || ""} ${academy.address_detail || ""}`.trim();

  const phoneDigits = academy.phone ? String(academy.phone).replace(/[^0-9]/g, "") : "";
  // "보습학원" 같은 뭉뚱그린 표기 대신 실제 과목(국어·논술/수학/영어 등)으로 노출.
  const subjectLabel = academySubjectLabel(academy) || academy.category_name;
  const body = `<div class="body-pad">
  <nav class="breadcrumb">
    <a href="/">홈</a><span>›</span>
    <a href="/${esc(academy.sido)}/">${esc(academy.sido)}</a><span>›</span>
    <a href="/${esc(academy.sido)}/${esc(academy.sigungu)}/">${esc(academy.sigungu)}</a><span>›</span>
    <a href="/${esc(academy.sido)}/${esc(academy.sigungu)}/${esc(academy.category_slug)}/" class="current">${esc(subjectLabel)}</a>
  </nav>

  <div class="top-row">
    <div class="prof-box">
      ${academy.info_provided ? `<span class="prof-seal"><i class="ph-fill ph-seal-check"></i>정보확인</span>` : ""}
      <span class="op${isClosed ? " closed" : ""}"><span class="dot"></span>${isClosed ? "운영종료" : "운영중"}</span>
      <div class="title-row">
        <h1>${esc(academy.name)}</h1>
        ${shareBtnHtml(`${academy.name} 수강료·정보 | ${academy.sigungu} ${academy.category_name}`)}
      </div>
      <div class="tags">
        <a class="chip" href="/${esc(academy.sido)}/${esc(academy.sigungu)}/${esc(academy.category_slug)}/">${esc(subjectLabel)}</a>
        <button type="button" class="report-link" data-open-modal="correction-modal-${esc(academy.slug)}">분류가 잘못됐나요?</button>
      </div>
      ${mapBox2Html(academy.lat, academy.lng, academy.name)}
      <div class="prof-foot">
        <div>${starsInline(ratingStats.average, ratingStats.count)}</div>
        <button type="button" class="info-cta" style="width:auto;margin:0;" data-open-modal="reg-modal-${esc(academy.slug)}"><i class="ph ph-pencil-simple"></i>정보 등록·수정 요청</button>
      </div>
    </div>

    <div class="info-box">
      <div class="ib-head">기본 정보</div>
      <div class="ib-row"><span class="k">주소</span><span class="v">${esc(presetAddr)}</span></div>
      ${academy.phone ? `<div class="ib-row"><span class="k">전화</span><span class="v"><a href="tel:${esc(phoneDigits)}">${esc(academy.phone)}</a></span></div>` : ""}
      <div class="ib-row"><span class="k">분야</span><span class="v">${esc(academy.category_name)} · ${esc(subjectLabel)}</span></div>
      ${academy.capacity_total ? `<div class="ib-row"><span class="k">정원</span><span class="v">${comma(academy.capacity_total)}명${academy.capacity_hourly ? ` <span style="color:var(--slate-400)">(시간당 ${comma(academy.capacity_hourly)}명)</span>` : ""}</span></div>` : ""}
      <div class="ib-row"><span class="k">등록일</span><span class="v">${formatDate(academy.reg_date)}</span></div>
      ${academy.phone ? `<a class="ib-cta" href="tel:${esc(phoneDigits)}"><span class="lbl">지금 전화 문의</span><span class="num"><i class="ph-fill ph-phone"></i>${esc(academy.phone)}</span></a>` : ""}
    </div>

    ${adxHtml("house", { area: "banner" })}
    ${adxHtml("adsense", { area: "ad", label: "광고 · Google AdSense" })}
  </div>

  ${isClosed ? '<div class="notice">이 학원은 운영이 종료되었습니다. 아래 같은 지역·분야의 다른 학원을 확인해보세요.</div>' : ""}
  ${tipoffSectionHtml("academy", academy.slug, academy.name, academy.phone)}

  <div class="detail-cols">
    <div style="display:flex;flex-direction:column;gap:16px;">
      ${adxHtml("coupang")}
      <div style="background:#fff;border:1px solid var(--border);border-radius:14px;padding:20px;">
        <h2 style="font-size:17px;font-weight:800;color:var(--navy);margin:0 0 14px;">수강료</h2>
        ${feeGridBody(academy)}
        <button type="button" class="fee-request-btn" data-open-modal="reg-modal-${esc(academy.slug)}"><i class="ph ph-pencil-simple"></i>수강료·정보 등록 요청</button>
      </div>
      ${adxHtml("adsense", { label: "광고 · Google AdSense (888×280)" })}
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;">
      ${adxHtml("coupang", { area: "" })}
    </div>
  </div>

  ${infoRegisterModalHtml("academy", academy.slug, academy.name, presetAddr, academy.phone)}
  ${correctionModalHtml("academy", academy.slug, academy.name)}

  ${related.length ? `
  <div style="display:flex;align-items:baseline;justify-content:space-between;margin:28px 0 12px;">
    <h2 class="section" style="margin:0;">${esc(academy.sigungu)}의 다른 ${esc(subjectLabel)}</h2>
    ${academy.dong ? `<a href="/${esc(academy.sido)}/${esc(academy.sigungu)}/${esc(academy.dong)}/" style="font-size:13px;font-weight:700;color:var(--blue);">${esc(academy.dong)} 더보기 ›</a>` : ""}
  </div>
  <div class="related-list">
    ${related.map((r) => `<a href="/${esc(r.sido)}/${esc(r.sigungu)}/${esc(r.slug)}/"><span class="r-name">${esc(r.name)}</span><span class="r-badges">${r.info_provided ? '<span class="badge-verify"><i class="ph-fill ph-seal-check"></i>정보확인</span>' : ""}${r.has_fee_data ? '<span class="badge-feecheck">수강료<i class="ph ph-check"></i></span>' : ""}<span class="r-arrow">›</span></span></a>`).join("")}
  </div>` : ""}
  ${footerHtml()}
  </div>`;

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "LocalBusiness",
      name: academy.name,
      address: {
        "@type": "PostalAddress",
        streetAddress: `${academy.address_road || ""} ${academy.address_detail || ""}`.trim(),
        addressLocality: academy.sigungu,
        addressRegion: academy.sido,
        postalCode: academy.zipcode,
        addressCountry: "KR",
      },
      ...(academy.phone ? { telephone: academy.phone } : {}),
      ...(ratingStats.count >= 3 ? {
        aggregateRating: {
          "@type": "AggregateRating",
          ratingValue: Number(ratingStats.average).toFixed(1),
          reviewCount: ratingStats.count,
        },
      } : {}),
    },
    breadcrumbJsonLd([
      { name: academy.sido, url: env.SITE_ORIGIN + `/${academy.sido}/` },
      { name: academy.sigungu, url: env.SITE_ORIGIN + `/${academy.sido}/${academy.sigungu}/` },
      { name: academy.category_name, url: env.SITE_ORIGIN + `/${academy.sido}/${academy.sigungu}/${academy.category_slug}/` },
      { name: academy.name, url: env.SITE_ORIGIN + path },
    ]),
  ];

  return pageShell({
    title: `${academy.name} 수강료·정보 | ${academy.sigungu} ${academy.category_name}`,
    description: `${academy.sigungu} ${academy.category_name} '${academy.name}' ${academy.has_fee_data ? "수강료, " : ""}주소, 전화번호, 정원 정보.`,
    path,
    robotsNoindex: isClosed,
    jsonLd,
    body,
    env,
    selectedSido: academy.sido,
    selectedSigungu: academy.sigungu,
  });
}

export function dojoDetailPage(env, dojo, related, ratingStats, banners) {
  const path = `/${dojo.sido}/${dojo.sigungu}/${dojo.slug}/`;
  const isClosed = !dojo.is_open;

  const dojoAddr = dojo.address_road || dojo.address_lot || "";

  const phoneDigits = dojo.phone ? String(dojo.phone).replace(/[^0-9]/g, "") : "";
  const body = `<div class="body-pad">
  <nav class="breadcrumb">
    <a href="/">홈</a><span>›</span>
    <a href="/${esc(dojo.sido)}/">${esc(dojo.sido)}</a><span>›</span>
    <a href="/${esc(dojo.sido)}/${esc(dojo.sigungu)}/">${esc(dojo.sigungu)}</a><span>›</span>
    <a href="/${esc(dojo.sido)}/${esc(dojo.sigungu)}/${esc(dojo.category_slug)}/" class="current">${esc(dojo.category_name)}</a>
  </nav>

  <div class="top-row">
    <div class="prof-box">
      ${dojo.info_provided ? `<span class="prof-seal"><i class="ph-fill ph-seal-check"></i>정보확인</span>` : ""}
      <span class="op${isClosed ? " closed" : ""}"><span class="dot"></span>${isClosed ? "운영종료" : "운영중"}</span>
      <div class="title-row">
        <h1>${esc(dojo.name)}</h1>
        ${shareBtnHtml(`${dojo.name} 정보 | ${dojo.sigungu} ${dojo.category_name}`)}
      </div>
      <div class="tags">
        <a class="chip" href="/search?subject=pe&sido=${encodeURIComponent(dojo.sido)}&sigungu=${encodeURIComponent(dojo.sigungu)}">체육</a>
        <a class="chip" href="/${esc(dojo.sido)}/${esc(dojo.sigungu)}/${esc(dojo.category_slug)}/">${esc(dojo.category_name)}</a>
        <button type="button" class="report-link" data-open-modal="correction-modal-${esc(dojo.slug)}">분류가 잘못됐나요?</button>
      </div>
      ${mapBox2Html(dojo.lat, dojo.lng, dojo.name)}
      <div class="prof-foot">
        <div>${starsInline(ratingStats.average, ratingStats.count)}</div>
        <button type="button" class="info-cta" style="width:auto;margin:0;" data-open-modal="reg-modal-${esc(dojo.slug)}"><i class="ph ph-pencil-simple"></i>정보 등록·수정 요청</button>
      </div>
    </div>

    <div class="info-box">
      <div class="ib-head">기본 정보</div>
      <div class="ib-row"><span class="k">종목</span><span class="v">${esc(dojo.sport_name)}</span></div>
      <div class="ib-row"><span class="k">주소</span><span class="v">${esc(dojoAddr)}</span></div>
      ${dojo.phone ? `<div class="ib-row"><span class="k">전화</span><span class="v"><a href="tel:${esc(phoneDigits)}">${esc(dojo.phone)}</a></span></div>` : ""}
      ${dojo.leader_count ? `<div class="ib-row"><span class="k">지도자</span><span class="v">${comma(dojo.leader_count)}명</span></div>` : ""}
      ${dojo.member_capacity ? `<div class="ib-row"><span class="k">정원</span><span class="v">${comma(dojo.member_capacity)}명</span></div>` : ""}
      <div class="ib-row"><span class="k">인허가일</span><span class="v">${formatDate(dojo.license_ymd)}</span></div>
      ${dojo.phone ? `<a class="ib-cta" href="tel:${esc(phoneDigits)}"><span class="lbl">지금 전화 문의</span><span class="num"><i class="ph-fill ph-phone"></i>${esc(dojo.phone)}</span></a>` : ""}
    </div>

    ${adxHtml("house", { area: "banner" })}
    ${adxHtml("adsense", { area: "ad", label: "광고 · Google AdSense" })}
  </div>

  ${isClosed ? '<div class="notice">이 도장은 운영이 종료되었습니다. 아래 같은 지역·종목의 다른 도장을 확인해보세요.</div>' : ""}
  ${tipoffSectionHtml("dojo", dojo.slug, dojo.name, dojo.phone)}

  <div class="detail-cols">
    <div style="display:flex;flex-direction:column;gap:16px;">
      ${adxHtml("coupang")}
      <div style="background:#fff;border:1px solid var(--border);border-radius:14px;padding:20px;">
        <h2 style="font-size:17px;font-weight:800;color:var(--navy);margin:0 0 14px;">수강료</h2>
        <div class="notice">등록된 수강료 정보가 없는 도장입니다.${dojo.phone ? ` 전화(${telLink(dojo.phone)})로 직접 문의하세요.` : ""}</div>
        <button type="button" class="fee-request-btn" data-open-modal="reg-modal-${esc(dojo.slug)}"><i class="ph ph-pencil-simple"></i>수강료·정보 등록 요청</button>
      </div>
      ${adxHtml("adsense", { label: "광고 · Google AdSense (888×280)" })}
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;">
      ${adxHtml("coupang")}
    </div>
  </div>

  ${infoRegisterModalHtml("dojo", dojo.slug, dojo.name, dojoAddr, dojo.phone)}
  ${correctionModalHtml("dojo", dojo.slug, dojo.name)}

  ${related.length ? `
  <div style="display:flex;align-items:baseline;justify-content:space-between;margin:28px 0 12px;">
    <h2 class="section" style="margin:0;">${esc(dojo.sigungu)}의 다른 ${esc(dojo.category_name)}</h2>
    ${dojo.dong ? `<a href="/${esc(dojo.sido)}/${esc(dojo.sigungu)}/${esc(dojo.dong)}/?subject=pe" style="font-size:13px;font-weight:700;color:var(--blue);">${esc(dojo.dong)} 더보기 ›</a>` : ""}
  </div>
  <div class="related-list">
    ${related.map((r) => `<a href="/${esc(r.sido)}/${esc(r.sigungu)}/${esc(r.slug)}/"><span class="r-name">${esc(r.name)}</span><span class="r-arrow">›</span></a>`).join("")}
  </div>` : ""}
  ${footerHtml()}
  </div>`;

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "SportsActivityLocation",
      name: dojo.name,
      address: {
        "@type": "PostalAddress",
        streetAddress: dojo.address_road || dojo.address_lot,
        addressLocality: dojo.sigungu,
        addressRegion: dojo.sido,
        addressCountry: "KR",
      },
      ...(dojo.phone ? { telephone: dojo.phone } : {}),
      ...(ratingStats.count >= 3 ? {
        aggregateRating: {
          "@type": "AggregateRating",
          ratingValue: Number(ratingStats.average).toFixed(1),
          reviewCount: ratingStats.count,
        },
      } : {}),
    },
    breadcrumbJsonLd([
      { name: dojo.sido, url: env.SITE_ORIGIN + `/${dojo.sido}/` },
      { name: dojo.sigungu, url: env.SITE_ORIGIN + `/${dojo.sido}/${dojo.sigungu}/` },
      { name: dojo.category_name, url: env.SITE_ORIGIN + `/${dojo.sido}/${dojo.sigungu}/${dojo.category_slug}/` },
      { name: dojo.name, url: env.SITE_ORIGIN + path },
    ]),
  ];

  return pageShell({
    title: `${dojo.name} 정보 | ${dojo.sigungu} ${dojo.category_name}`,
    description: `${dojo.sigungu} ${dojo.category_name} '${dojo.name}' 영업상태, 주소, 전화번호 정보.`,
    path,
    robotsNoindex: isClosed,
    jsonLd,
    body,
    env,
    selectedSido: dojo.sido,
    selectedSigungu: dojo.sigungu,
  });
}

export function categoryListPage(env, sido, sigungu, categorySlug, categoryName, academies, dojos, page, hasMore, totalCount, banner, sort) {
  const items = [
    ...academies.map((a) => ({ ...a, type: "academy" })),
    ...dojos.map((d) => ({ ...d, type: "dojo" })),
  ];
  const pageQuery = page > 1 ? `page=${page}` : "";
  const sortQuery = sort ? `sort=${sort}` : "";
  const qs = [pageQuery, sortQuery].filter(Boolean).join("&");
  const path = `/${sido}/${sigungu}/${categorySlug}/` + (qs ? `?${qs}` : "");

  const withParam = (params) => {
    const merged = { page: String(page), sort: sort || "" , ...params };
    const parts = [];
    if (merged.page && merged.page !== "1") parts.push(`page=${merged.page}`);
    if (merged.sort) parts.push(`sort=${merged.sort}`);
    return parts.length ? `?${parts.join("&")}` : "?";
  };

  const cardHtml = itemCardHtml;

  const half = Math.ceil(items.length / 2);
  const firstHalf = items.slice(0, half || items.length);
  const secondHalf = items.slice(half || items.length);

  const body = `<div class="body-pad">
  <nav class="breadcrumb">
    <a href="/">홈</a><span>›</span>
    <a href="/${esc(sido)}/">${esc(sido)}</a><span>›</span>
    <a href="/${esc(sido)}/${esc(sigungu)}/">${esc(sigungu)}</a><span>›</span>
    <span class="current">${esc(categoryName)}</span>
  </nav>
  <div class="page-title">
    <h1>${esc(sigungu)} ${esc(categoryName)}</h1>
    <span class="count">총 ${comma(totalCount)}개</span>
  </div>
  <p class="intro">${esc(sigungu)}에 등록 확인된 ${esc(categoryName)} ${comma(totalCount)}개의 수강료·연락처·평점을 확인하세요. 정보제공·수강료 확인 학원이 먼저 표시됩니다.</p>
  <div style="margin:-6px 0 14px;">${shareBtnHtml(`${sigungu} ${categoryName} 목록`)}</div>

  <div class="card-list">
    ${firstHalf.map(cardHtml).join("") || "<p>등록된 정보가 없습니다.</p>"}
  </div>

  ${items.length > 3 ? adSlotHtml(1, banner, "small") : ""}

  ${secondHalf.length ? `<div class="card-list" style="margin-top:10px;">${secondHalf.map(cardHtml).join("")}</div>` : ""}

  <div class="pagination">
    ${page > 1 ? `<a href="${withParam({ page: String(page - 1) })}">‹</a>` : `<span style="opacity:.3">‹</span>`}
    <span class="current">${page}</span>
    ${hasMore ? `<a href="${withParam({ page: String(page + 1) })}">›</a>` : `<span style="opacity:.3">›</span>`}
  </div>
  ${footerHtml()}
  </div>`;

  return pageShell({
    title: `${sigungu} ${categoryName} 목록${page > 1 ? ` - ${page}페이지` : ""}`,
    description: `${sigungu} ${categoryName} 전체 목록. 수강료, 주소, 전화번호를 확인하세요.`,
    path,
    robotsNoindex: false,
    body,
    env,
    selectedSido: sido,
    selectedSigungu: sigungu,
  });
}

// 분야 아이콘 타일 내용 (glyph 문자 또는 Phosphor 아이콘). small=true면 작은 필터바 타일용으로 글리프 축소.
function subjectIconInner(g, small) {
  if (g.icon) return `<i class="ph ${esc(g.icon)}"></i>`;
  if (g.glyph) {
    // 글리프별 크기(글자 수 반영). 소형 필터바는 더 축소. 절대 줄바꿈 안 되게 nowrap.
    const size = small ? Math.max(9, Math.round((g.glyphSize || 21) * 0.72)) : (g.glyphSize || 21);
    return `<span style="font-size:${size}px;letter-spacing:-0.5px;line-height:1;white-space:nowrap;">${esc(g.glyph)}</span>`;
  }
  return esc(g.name.slice(0, 2));
}

// 분야 정사각형 카드 그리드 (시군구 허브 = 검색결과 시안). 아이콘 → 과목명 → 개수.
function subjectButtonGridHtml(subjectGroups, counts, hrefFn, activeKey) {
  return `<div class="subject-grid">
    ${subjectGroups.map((g) => {
      const cnt = counts ? counts[g.key] || 0 : null;
      const isActive = activeKey && activeKey === g.key;
      return `<a class="subject-btn${isActive ? " active" : ""}" href="${hrefFn(g)}">
        <span class="s-icon">${subjectIconInner(g)}</span>
        <span class="s-name">${esc(g.name)}</span>
        ${cnt !== null ? `<span class="s-count">${comma(cnt)}</span>` : ""}
      </a>`;
    }).join("")}
  </div>`;
}

// 목록 페이지 상단 카테고리 필터 바 (10칸). activeKey 강조, 각 버튼은 hrefFn(g)로 이동.
function catFilterBarHtml(subjectGroups, counts, hrefFn, activeKey) {
  return `<div class="cat-bar">
    ${subjectGroups.map((g) => {
      const cnt = counts ? counts[g.key] || 0 : null;
      const isActive = activeKey && activeKey === g.key;
      return `<a class="${isActive ? "active" : ""}" href="${hrefFn(g)}">
        <span class="cb-icon">${subjectIconInner(g, true)}</span>
        <span class="cb-name">${esc(g.name)}</span>
        ${cnt !== null ? `<span class="cb-count">${comma(cnt)}</span>` : ""}
      </a>`;
    }).join("")}
  </div>`;
}

// 분야 아이콘 그리드 허브 (시군구 or 시도 전체). sigungu=null이면 시도 범위.
export function sigunguHubPage(env, sido, sigungu, subjectGroups, counts, totalCount) {
  const scope = sigungu || sido;
  const path = sigungu ? `/${sido}/${sigungu}/` : `/${sido}/`;
  const hrefFn = (g) => subjectHref(g, { sido, sigungu });
  const crumb = sigungu
    ? `<a href="/">홈</a><span>›</span><a href="/${esc(sido)}/">${esc(sido)}</a><span>›</span><span class="current">${esc(sigungu)}</span>`
    : `<a href="/">홈</a><span>›</span><span class="current">${esc(sido)}</span>`;
  const body = `<div class="body-pad">
  <nav class="breadcrumb">${crumb}</nav>
  <div class="page-title-row">
    <h1 style="font-size:24px;font-weight:800;color:var(--navy);margin:0 0 20px;">${esc(scope)} 학원 총 ${comma(totalCount)}개</h1>
    ${shareBtnHtml(`${scope} 학원 총 ${comma(totalCount)}개`)}
  </div>
  ${subjectButtonGridHtml(subjectGroups, counts, hrefFn)}
  ${footerHtml()}
  </div>`;
  return pageShell({
    title: `${scope} 학원 총 ${comma(totalCount)}개`,
    description: `${scope}의 학원, 교습소, 체육도장 정보를 분야별로 확인하세요.`,
    path,
    robotsNoindex: false,
    jsonLd: breadcrumbJsonLd(
      sigungu
        ? [{ name: sido, url: env.SITE_ORIGIN + `/${sido}/` }, { name: sigungu, url: env.SITE_ORIGIN + path }]
        : [{ name: sido, url: env.SITE_ORIGIN + path }]
    ),
    body,
    env,
    selectedSido: sido,
    selectedSigungu: sigungu || undefined,
  });
}

export function sidoHubPage(env, sido, sigunguList) {
  const path = `/${sido}/`;
  const body = `<div class="body-pad">
  <nav class="breadcrumb"><span class="current">${esc(sido)}</span></nav>
  <h1 style="font-size:19px;font-weight:800;color:var(--navy);margin:0 0 14px;">${esc(sido)} 학원 찾기 — 지역을 선택하세요</h1>
  <div class="region-grid" style="grid-template-columns:repeat(3,1fr);">
    ${sigunguList.map((s) => `<a class="region-btn" href="/${esc(sido)}/${esc(s)}/">${esc(s)}</a>`).join("")}
  </div>
  ${footerHtml()}
  </div>`;
  return pageShell({
    title: `${sido} 학원 찾기 — 지역을 선택하세요`,
    description: `${sido} 시군구별 학원, 교습소, 체육도장 정보.`,
    path,
    robotsNoindex: false,
    body,
    env,
    selectedSido: sido,
  });
}

// 읍면동 페이지: 분야 버튼(개수 포함)만 먼저 보여주고, 클릭 시 같은 페이지에서 목록을 아래에 출력(?subject=). 예체능은 세부 칩으로 좁히기 가능.
export function dongHubPage(env, sido, sigungu, dong, subjectGroups, counts, totalCount, subjectKey, chipQ, list) {
  const path = `/${sido}/${sigungu}/${dong}/`;
  const hrefFn = (g) => `${path}?subject=${encodeURIComponent(g.key)}`;
  const activeGroup = subjectKey ? subjectGroups.find((g) => g.key === subjectKey) : null;

  const items = list
    ? [...list.academies.map((a) => ({ ...a, type: "academy" })), ...list.dojos.map((d) => ({ ...d, type: "dojo" }))]
    : [];

  // "쌍문동 태권도" 처럼 동+분야 조합 키워드 검색에 잡히도록 chip(가장 구체적) > 분야명 순으로 제목에 반영.
  const keywordLabel = chipQ || (activeGroup ? activeGroup.name : null);
  // 결과가 전부 도장이면 "도장", 전부 학원이면 "학원", 섞이면 "학원·도장" — 태권도 등은 실제 도장이라 "학원"이라 부르면 어색함.
  const allDojo = items.length > 0 && items.every((it) => it.type === "dojo");
  const allAcademy = items.length > 0 && items.every((it) => it.type === "academy");
  const entityWord = allDojo ? "도장" : allAcademy ? "학원" : "학원·도장";

  const chipsHtml = activeGroup && activeGroup.chips
    ? `<div class="chip-row">
        ${activeGroup.chips.map((c) => `<a class="${chipQ === c.q ? "active" : ""}" href="${path}?subject=${esc(subjectKey)}&chip=${encodeURIComponent(c.q)}">${esc(c.name)}</a>`).join("")}
      </div>`
    : "";

  const listHtml = activeGroup
    ? `<h2 class="section" style="margin-top:18px;">${esc(activeGroup.name)} ${comma(items.length)}개</h2>
       ${chipsHtml}
       <div class="card-list">
         ${items.map(itemCardHtml).join("") || "<p>등록된 정보가 없습니다.</p>"}
       </div>`
    : "";

  const pageTitleText = keywordLabel
    ? `${dong} ${keywordLabel} ${entityWord} 총 ${comma(items.length)}개`
    : `${dong} 학원 총 ${comma(totalCount)}개`;

  const body = `<div class="body-pad">
  <nav class="breadcrumb">
    <a href="/">홈</a><span>›</span>
    <a href="/${esc(sido)}/">${esc(sido)}</a><span>›</span>
    <a href="/${esc(sido)}/${esc(sigungu)}/">${esc(sigungu)}</a><span>›</span>
    <span class="current">${esc(dong)}</span>
  </nav>
  <div class="page-title-row">
    <h1 style="font-size:19px;font-weight:800;color:var(--navy);margin:0 0 14px;">${esc(dong)} ${keywordLabel ? esc(keywordLabel) + " " + entityWord : "학원"} 총 ${comma(keywordLabel ? items.length : totalCount)}개</h1>
    ${shareBtnHtml(pageTitleText)}
  </div>
  ${subjectButtonGridHtml(subjectGroups, counts, hrefFn, subjectKey)}
  ${listHtml}
  ${footerHtml()}
  </div>`;

  return pageShell({
    title: pageTitleText,
    description: keywordLabel
      ? `${sigungu} ${dong}의 ${keywordLabel} ${entityWord} ${comma(items.length)}곳의 수강료·연락처·평점을 확인하세요.`
      : `${sigungu} ${dong}의 학원, 교습소, 체육도장 정보를 분야별로 확인하세요.`,
    path: subjectKey ? `${path}?subject=${encodeURIComponent(subjectKey)}${chipQ ? `&chip=${encodeURIComponent(chipQ)}` : ""}` : path,
    // 동+분야 조합은 실제 결과가 있을 때만 색인 허용 (빈 페이지는 계속 noindex로 저품질 색인 방지)
    robotsNoindex: !!subjectKey && items.length === 0,
    jsonLd: breadcrumbJsonLd([
      { name: sido, url: env.SITE_ORIGIN + `/${sido}/` },
      { name: sigungu, url: env.SITE_ORIGIN + `/${sido}/${sigungu}/` },
      { name: dong, url: env.SITE_ORIGIN + path },
    ]),
    body,
    env,
    selectedSido: sido,
    selectedSigungu: sigungu,
    selectedDong: dong,
  });
}

export function searchResultsPage(env, query, academies, dojos, sido, sigungu, dong, subject, subjectGroups, counts, totalCount, page, hasMore) {
  const group = subject && subjectGroups ? subjectGroups.find((g) => g.key === subject) : null;
  const scope = dong || sigungu || sido || "";
  const scopeLabel = [sigungu, dong].filter(Boolean).join(" ");
  // 실제 표시 개수는 페이지네이션 전 총건수(totalCount) 기준. 미지정 시(구버전 호출 호환) 현재 페이지 항목 수로 대체.
  const items = [
    ...academies.map((a) => ({ ...a, type: "academy" })),
    ...dojos.map((d) => ({ ...d, type: "dojo" })),
  ];
  const count = totalCount != null ? totalCount : items.length;

  // 검색어가 특정 과목이면 해당 카테고리 버튼 활성 (#11)
  let activeKey = subject;
  if (!activeKey && query && subjectGroups) {
    const g = subjectGroups.find((gg) => gg.name.includes(query) || query.includes(gg.name.replace(/·.*/, "")));
    if (g) activeKey = g.key;
  }

  // 제목(순수 텍스트, <title>/<meta description>에 그대로 씀 — HTML 태그 절대 섞지 않음)
  const titleText = query
    ? `${scopeLabel ? scopeLabel + " " : ""}${query} 검색 결과 (${comma(count)}개)`
    : group
      ? `${scopeLabel ? scopeLabel + " " : ""}${group.name} (${comma(count)}개)`
      : `${scope} 학원 총 ${comma(count)}개`;
  // 화면 표시용 H1은 개수만 별도 span으로 스타일링
  const headingMain = query
    ? `${scopeLabel ? esc(scopeLabel) + " " : ""}${esc(query)} 검색 결과`
    : group
      ? `${scopeLabel ? esc(scopeLabel) + " " : ""}${esc(group.name)}`
      : `${esc(scope)} 학원 총`;
  const heading = `${headingMain} <span style="font-size:15px;font-weight:700;color:var(--slate-400);">${comma(count)}개</span>`;

  // 시군구가 지정된 경우 카드 위치에 구 생략, 전체(시도만)면 구 포함
  const showGu = !sigungu;

  const barHtml = counts && sido
    ? catFilterBarHtml(subjectGroups, counts, (g) => {
        const p = [`sido=${encodeURIComponent(sido)}`];
        if (sigungu) p.push(`sigungu=${encodeURIComponent(sigungu)}`);
        if (dong) p.push(`dong=${encodeURIComponent(dong)}`);
        p.push(`subject=${encodeURIComponent(g.key)}`);
        return `/search?${p.join("&")}`;
      }, activeKey)
    : "";

  const crumb = sido
    ? `<nav class="breadcrumb"><a href="/">홈</a><span>›</span><a href="/${esc(sido)}/">${esc(sido)}</a>${sigungu ? `<span>›</span><a href="/${esc(sido)}/${esc(sigungu)}/">${esc(sigungu)}</a>` : ""}${dong ? `<span>›</span><span class="current">${esc(dong)}</span>` : ""}</nav>`
    : "";

  const baseQs = [
    sido && `sido=${encodeURIComponent(sido)}`,
    sigungu && `sigungu=${encodeURIComponent(sigungu)}`,
    dong && `dong=${encodeURIComponent(dong)}`,
    query && `q=${encodeURIComponent(query)}`,
    subject && `subject=${encodeURIComponent(subject)}`,
  ].filter(Boolean);
  const pageUrl = (p) => `/search?${[...baseQs, p > 1 ? `page=${p}` : null].filter(Boolean).join("&")}`;
  const curPage = page || 1;
  const paginationHtml = (curPage > 1 || hasMore)
    ? `<div class="pagination">
        ${curPage > 1 ? `<a href="${pageUrl(curPage - 1)}">‹</a>` : `<span style="opacity:.3">‹</span>`}
        <span class="current">${curPage}</span>
        ${hasMore ? `<a href="${pageUrl(curPage + 1)}">›</a>` : `<span style="opacity:.3">›</span>`}
      </div>`
    : "";

  const body = `<div class="body-pad">
  ${crumb}
  <div class="page-title-row">
    <h1 style="font-size:24px;font-weight:800;color:var(--navy);margin:0 0 16px;">${heading}</h1>
    ${shareBtnHtml(titleText)}
  </div>
  ${barHtml}
  ${items.length
    ? `<div class="card-list">${items.map((it) => itemCardHtml(it, showGu)).join("")}</div>`
    : `<p class="intro">결과가 없습니다. 지역이나 분야를 바꿔 다시 검색해보세요.</p>`}
  ${paginationHtml}
  ${footerHtml()}
  </div>`;
  const qs = [...baseQs, curPage > 1 ? `page=${curPage}` : null].filter(Boolean).join("&");
  return pageShell({
    title: `${titleText} | ${SITE_NAME}`,
    description: titleText,
    path: `/search${qs ? "?" + qs : ""}`,
    robotsNoindex: true,
    body,
    env,
    selectedSido: sido,
    selectedSigungu: sigungu,
    selectedDong: dong,
    q: query,
  });
}

// 신규 학원 등록 페이지 (빈 폼). 제출 → info_submissions 대기 저장 → 관리자 승인 후 반영.
export function registerPage(env, subjectGroups) {
  const body = `<div class="body-pad">
  <nav class="breadcrumb"><a href="/">홈</a><span>›</span><span class="current">우리 학원 등록</span></nav>
  <h1 style="font-size:20px;font-weight:800;color:var(--navy);margin:0 0 6px;">우리 학원 등록하기</h1>
  <p class="intro">아래 정보를 모두 입력해 신청해 주세요. 승인 후 사이트에 노출되며, '정보확인' 배지가 표시됩니다.</p>
  <div style="background:#fff;border:1px solid var(--border);border-radius:14px;padding:20px;">
    <form class="reg-form region-search-form" data-mode="new" data-entity-type="academy" data-email="${esc(FEE_REQUEST_EMAIL)}">
      <label>학원명</label>
      <input class="full" name="name" placeholder="학원 이름">
      <label>지역 (시도 / 시군구 / 읍면동)</label>
      <div class="row" style="display:flex;gap:8px;">
        <select class="full region-sido" name="sido"><option value="">시도 선택</option></select>
        <select class="full region-sigungu" name="sigungu"><option value="">시군구</option></select>
        <select class="full region-dong" name="dong"><option value="">읍면동</option></select>
      </div>
      <label>분야</label>
      <select class="full" name="category">
        ${subjectGroups.map((g) => `<option value="${esc(g.name)}">${esc(g.name)}</option>`).join("")}
      </select>
      <label>교육과정 · 월 수강료 (여러 개 입력 가능)</label>
      <div class="course-rows">
        <div class="fg-row"><input name="course" placeholder="과정명 (예: 초등수학)"><input name="price" placeholder="월 수강료(원)" inputmode="numeric"><button type="button" class="rm" title="삭제">×</button></div>
      </div>
      <button type="button" class="add-course">+ 과정 추가</button>
      <label>주소</label>
      <input class="full" name="address" placeholder="도로명 주소">
      <label>전화번호</label>
      <input class="full" name="phone" placeholder="02-000-0000">
      <label>회신용 이메일</label>
      <input class="full" name="email" type="email" placeholder="you@example.com">
      <div style="margin-top:16px;"><button type="submit" class="btn-primary" style="border:none;width:100%;padding:13px;border-radius:10px;">등록 신청</button></div>
      <div class="reg-guide" style="display:none;"></div>
    </form>
  </div>
  <input type="hidden" class="region-sido-preset" value="">
  <input type="hidden" class="region-sigungu-preset" value="">
  <input type="hidden" class="region-dong-preset" value="">
  ${footerHtml()}
  </div>`;
  return pageShell({
    title: `우리 학원 등록하기 | ${SITE_NAME}`,
    description: "학원 정보를 직접 등록하고 수강료를 노출하세요.",
    path: "/register/",
    robotsNoindex: true,
    body,
    env,
  });
}

export function privacyPage(env) {
  const body = `<div class="body-pad">
  <h1 style="font-size:19px;font-weight:800;color:var(--navy);margin:0 0 6px;">개인정보처리방침</h1>
  <p class="intro">시행일: 2026.07.10</p>
  <p>${SITE_NAME}(이하 "사이트")는 공공데이터포털 및 행정안전부에서 제공하는 공공데이터를 활용하여 학원·체육시설 정보를 안내합니다.</p>
  <h2 class="section">1. 수집하는 개인정보 항목</h2>
  <p>사이트는 회원가입을 받지 않으며, 별점 등록 및 정보 등록 요청(제보) 기능 이용 시 아래 정보가 수집될 수 있습니다.</p>
  <ul>
    <li>정보 등록 요청(제보) 시: 입력하신 전화번호, 제보자 구분(관계자/이용자), 제출 시각, IP 주소(어뷰징 방지 목적, 해시 처리 후 저장)</li>
    <li>별점 등록 시: 브라우저에 저장되는 임의의 식별 토큰(개인 식별 불가, 해시 처리되어 저장), 별점 점수, 제출 시각, IP 주소(어뷰징 방지 목적, 해시 처리 후 저장)</li>
  </ul>
  <h2 class="section">2. 개인정보의 이용 목적</h2>
  <p>수집된 정보는 학원·체육시설 정보의 정확성을 높이고, 중복·어뷰징 제출을 방지하는 목적으로만 사용됩니다.</p>
  <h2 class="section">3. 쿠키 및 광고</h2>
  <p>본 사이트는 Google AdSense를 통해 광고를 게재할 수 있으며, Google 등 광고 제공업체는 쿠키를 사용하여 사용자의 관심사에 기반한 광고를 제공할 수 있습니다. 사용자는 Google 광고 설정 페이지에서 맞춤 광고를 거부할 수 있습니다.</p>
  <p>본 사이트는 Google Analytics를 이용해 방문자 수, 유입 경로 등 서비스 이용 현황을 분석하며, 이 과정에서 쿠키가 사용될 수 있습니다. 수집된 정보는 통계 목적으로만 사용되며 개인을 식별하지 않습니다.</p>
  <p>이 사이트는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p>
  <h2 class="section">4. 보유 및 이용 기간</h2>
  <p>제보 및 별점 정보는 서비스 운영 목적 달성 시까지 보관하며, 관련 법령에 따라 보존이 필요한 경우를 제외하고 지체 없이 파기합니다.</p>
  <h2 class="section">5. 문의</h2>
  <p>개인정보 관련 문의는 ${FEE_REQUEST_EMAIL}로 접수해 주시기 바랍니다.</p>
  ${footerHtml()}
  </div>`;
  return pageShell({
    title: `개인정보처리방침 | ${SITE_NAME}`,
    description: `${SITE_NAME} 개인정보처리방침`,
    path: "/privacy/",
    robotsNoindex: false,
    body,
    env,
  });
}
