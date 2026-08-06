// 학교 표준 서식(초등) — 학부모가 자주 쓰는 4종을 학교명(+등록 자녀 정보) 채워서 인쇄/PDF 저장.
// 원본 HWP는 바이너리(HWP 5.0)라 학교명만 안전하게 바꿔 재생성할 수 없어서, 같은 항목을 웹 서식으로 재현했다.
// 학교마다 양식이 조금씩 달라 "표준 서식"으로 안내하고, 학교가 별도 양식을 요구하면 그걸 쓰도록 문구를 넣는다.
// (2026-07-18, 사용자가 제공한 초등 서식 4종 기준)

function esc(s) {
  if (s == null) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const FORMS = {
  counsel: { title: "학부모 상담 신청서", icon: "💬", desc: "담임 선생님과 상담 희망 일시·방법을 신청" },
  field: { title: "교외체험학습 신청서 · 보고서", icon: "🚌", desc: "가족여행·체험학습 사전 신청과 사후 보고서" },
  absence: { title: "결석신고서", icon: "📝", desc: "질병·경조사 등 결석 사유와 증빙 제출" },
  earlyleave: { title: "조퇴 · 외출증", icon: "🏃", desc: "조퇴·외출 시 담임 확인용(작은 양식)" },
};

const PRINT_CSS = `
  @page { size: A4; margin: 14mm; }
  *{box-sizing:border-box}
  body{margin:0;background:#EEF1F5;font-family:"Malgun Gothic","맑은 고딕",-apple-system,sans-serif;color:#111}
  .sheet{background:#fff;max-width:820px;margin:16px auto;padding:26px 30px 34px;box-shadow:0 2px 18px rgba(0,0,0,.12)}
  h1{font-size:24px;text-align:center;margin:0 0 4px;letter-spacing:-.02em}
  .school{text-align:center;font-size:14px;color:#444;margin-bottom:18px;font-weight:700}
  table{width:100%;border-collapse:collapse;margin-bottom:14px}
  th,td{border:1px solid #333;padding:9px 10px;font-size:13.5px;vertical-align:middle}
  th{background:#F2F4F7;width:110px;text-align:center;font-weight:700}
  td.fill{height:34px}
  .tall td{height:150px;vertical-align:top}
  .note{border:1px solid #999;background:#FAFBFC;padding:12px 14px;font-size:12px;line-height:1.7;margin-bottom:14px}
  .note b{display:block;margin-bottom:5px}
  .sign{margin-top:26px;text-align:right;font-size:14px;line-height:2.2}
  .cut{border-top:2px dashed #999;margin:26px 0 20px;text-align:center;font-size:11px;color:#888}
  .chk{display:inline-block;width:13px;height:13px;border:1px solid #333;margin-right:5px;vertical-align:-2px}
  .bar{position:sticky;top:0;background:#16233B;color:#fff;padding:12px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .bar a,.bar button{font-family:inherit;font-size:13.5px;font-weight:800;border-radius:9px;padding:9px 14px;cursor:pointer;border:none}
  .bar .back{background:rgba(255,255,255,.14);color:#fff}
  .bar .pdf{background:#2E7D5B;color:#fff}
  .bar .tip{font-size:12px;color:#B9C6DA;font-weight:500}
  @media print { .bar{display:none} body{background:#fff} .sheet{box-shadow:none;margin:0;max-width:none;padding:0} }
`;

function shell(title, school, inner) {
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} — ${esc(school.name)}</title>
<style>${PRINT_CSS}</style></head><body>
<div class="bar">
  <a class="back" href="/forms?school=${encodeURIComponent(school.slug)}">‹ 서식 목록</a>
  <button class="pdf" onclick="window.print()">📄 PDF로 저장 / 인쇄</button>
  <span class="tip">인쇄 창에서 <b>대상: PDF로 저장</b>을 고르면 파일로 저장됩니다</span>
</div>
${inner}
</body></html>`;
}

// 학년·반·이름 미리 채움(로그인+해당 학교 자녀가 있을 때). 없으면 빈칸.
function pre(child, key) {
  if (!child) return "";
  if (key === "name") return esc(child.nickname || "");
  if (key === "grade") return esc(child.grade || "");
  if (key === "class") return esc(child.class_name || "");
  return "";
}

export function formsListPage(school, child) {
  const card = (type) => {
    const f = FORMS[type];
    return `<a href="/forms?school=${encodeURIComponent(school.slug)}&type=${type}" style="display:flex;align-items:center;gap:13px;background:#fff;border:1px solid #E6E9EF;border-radius:14px;padding:15px 16px;text-decoration:none;color:inherit">
      <span style="font-size:24px;flex:none">${f.icon}</span>
      <span style="flex:1"><span style="display:block;font-size:15px;font-weight:800;color:#16233B">${f.title}</span>
      <span style="display:block;font-size:12.5px;color:#6B7688;margin-top:2px">${f.desc}</span></span>
      <span style="color:#C4CBD6;font-size:20px">›</span></a>`;
  };
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>학교 서식 — ${esc(school.name)}</title>
<style>body{margin:0;background:#F3F5F8;font-family:"Pretendard","Malgun Gothic",-apple-system,sans-serif;color:#16233B}
.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#F3F5F8;padding:18px 16px 40px}
@media(min-width:768px){.wrap{max-width:720px}}</style></head><body>
<div class="wrap">
  <a href="/school/${encodeURIComponent(school.slug)}/" style="font-size:22px;color:#6B7688;text-decoration:none">‹</a>
  <h1 style="margin:10px 0 2px;font-size:23px;font-weight:800;letter-spacing:-.02em">학교 서식</h1>
  <p style="margin:0 0 4px;font-size:14px;color:#2E7D5B;font-weight:800">${esc(school.name)}</p>
  <p style="margin:0 0 18px;font-size:12.5px;color:#6B7688;line-height:1.6">학교명이 채워진 서식을 인쇄하거나 PDF로 저장할 수 있어요.${child ? " 등록한 자녀의 학년·반도 채워집니다." : ""}</p>
  <div style="display:flex;flex-direction:column;gap:10px">${Object.keys(FORMS).map(card).join("")}</div>
  <div style="margin-top:18px;background:#FBF4E9;border:1px solid #F0E3C8;border-radius:12px;padding:13px 15px;font-size:12px;color:#8A6D2F;line-height:1.65">
    ⚠️ 학교마다 양식이 조금씩 다를 수 있어요. <b>학교에서 배부한 서식이 따로 있으면 그것을 사용</b>해 주세요. 여기 서식은 일반적인 표준 양식입니다.
  </div>
</div></body></html>`;
}

export function formPage(school, type, child) {
  const f = FORMS[type];
  if (!f) return null;
  const S = esc(school.name);
  const head = (t) => `<h1>${t}</h1><div class="school">${S}</div>`;

  if (type === "counsel") {
    return shell(f.title, school, `<div class="sheet">
      ${head("2026학년도 학부모 상담 신청서")}
      <table>
        <tr><th>학생 이름</th><td class="fill">${pre(child, "name")}</td><th>학년 · 반</th><td class="fill">${pre(child, "grade")}${child && child.grade ? "학년 " : ""}${pre(child, "class")}${child && child.class_name ? "반" : ""}</td></tr>
        <tr><th>보호자 성함</th><td class="fill"></td><th>학생과의 관계</th><td class="fill"></td></tr>
        <tr><th>보호자 연락처</th><td class="fill" colspan="3"></td></tr>
        <tr><th>희망 일시</th><td class="fill" colspan="3">　　　　월　　　　일 (　　　시　　　분)</td></tr>
        <tr><th>상담 방법</th><td class="fill" colspan="3"><span class="chk"></span> 대면 상담　　　<span class="chk"></span> 비대면(전화) 상담</td></tr>
        <tr class="tall"><th>상담 내용<br>(희망 주제)</th><td colspan="3"></td></tr>
      </table>
      <div class="note"><b>상담 안내</b>
        · 상담 가능 시간은 학년별로 다르며, 자세한 시간은 담임 선생님 안내를 따릅니다.<br>
        · 학교 안전 관리를 위해 <b>야간 상담은 운영하지 않습니다.</b><br>
        · 신청 후 담임 선생님이 일정을 확정해 알려드립니다.
      </div>
      <div class="sign">위와 같이 상담을 신청합니다.<br>2026년　　　월　　　일<br>보호자 　　　　　　　　　 (서명 또는 인)</div>
      <div class="cut">— 아래는 학교(담임) 작성란 —</div>
      <table>
        <tr><th>상담 일정</th><td class="fill">　　　월　　　일 (　　시　　분)</td><th>상담 장소</th><td class="fill"></td></tr>
      </table>
      <div class="sign">보호자님의 상담 일정이 위와 같이 확정되었음을 알려드립니다.<br>2026년　　　월　　　일<br>담임교사 　　　　　　　　　 (인)</div>
    </div>`);
  }

  if (type === "field") {
    return shell(f.title, school, `<div class="sheet">
      ${head("2026학년도 교외체험학습 신청서")}
      <table>
        <tr><th>성명</th><td class="fill">${pre(child, "name")}</td><th>학년 - 반</th><td class="fill">${pre(child, "grade")}${child && child.grade ? " - " : ""}${pre(child, "class")}</td></tr>
        <tr><th>주소</th><td class="fill" colspan="3"></td></tr>
        <tr><th>기간</th><td class="fill" colspan="3">2026년　　월　　일 ~ 2026년　　월　　일　( 총　　　일간 )</td></tr>
        <tr><th>장소</th><td class="fill" colspan="3"></td></tr>
        <tr><th>보호자 동행</th><td class="fill"><span class="chk"></span> 동행　<span class="chk"></span> 미동행 (동행자: 　　　　　)</td><th>비상 연락처</th><td class="fill"></td></tr>
        <tr class="tall"><th>학습 계획<br>(학습할 내용)</th><td colspan="3"><span style="font-size:11.5px;color:#777">※ 교육활동 내용이 드러나도록 구체적으로 상세하게 작성</span></td></tr>
      </table>
      <div class="note"><b>교외체험학습 안내</b>
        · 총 허용 일수는 <b>전체 수업일수의 10% 이내</b>입니다.<br>
        · 1회 <b>연속 10일 이내</b>(재량휴업일·토요일·공휴일 제외)로 신청할 수 있습니다.<br>
        · <b>연속 5일을 초과</b>해 실시하는 경우, 안전을 위해 <b>기간 중 1회 이상 학생이 담임교사에게 연락</b>해야 합니다.<br>
        · 신청서는 <b>출발 3일 전까지</b> 제출해 주세요. (반일 체험학습은 조퇴 또는 등교 시간을 기록)<br>
        · 감염병 위기경보 '심각' 단계인 경우에 한해 '가정학습'을 승인 사유로 인정합니다.
      </div>
      <div class="sign">위와 같이 교외체험학습을 신청합니다.<br>2026년　　　월　　　일<br>보호자 　　　　　　　　　 (서명 또는 인)</div>
      <div class="cut">— 체험학습 종료 후 아래 보고서를 작성해 제출합니다 —</div>
      ${head("교외체험학습 보고서")}
      <table>
        <tr><th>기간</th><td class="fill">2026년　　월　　일 ~ 　　월　　일</td><th>장소</th><td class="fill"></td></tr>
        <tr class="tall"><th>학습한 내용<br>및 느낀 점</th><td colspan="3"></td></tr>
      </table>
      <div class="sign">2026년　　　월　　　일<br>학생 　　　　　　　 　 보호자 　　　　　　　　　 (서명 또는 인)</div>
    </div>`);
  }

  if (type === "absence") {
    return shell(f.title, school, `<div class="sheet">
      ${head("2026학년도 결석신고서")}
      <table>
        <tr><th>학생명</th><td class="fill">${pre(child, "name")}</td><th>학년 · 반</th><td class="fill">${pre(child, "grade")}${child && child.grade ? "학년 " : ""}${pre(child, "class")}${child && child.class_name ? "반" : ""}</td></tr>
        <tr><th>기간</th><td class="fill">2026년　　월　　일 ~ 　　월　　일</td><th>일수</th><td class="fill">　　　일간</td></tr>
        <tr><th>결석 구분</th><td class="fill" colspan="3"><span class="chk"></span> 질병　　<span class="chk"></span> 출석인정(경조사 등)　　<span class="chk"></span> 기타 (　　　　　　)</td></tr>
        <tr class="tall"><th>사유</th><td colspan="3"></td></tr>
        <tr><th>증빙 서류</th><td class="fill" colspan="3"><span class="chk"></span> 진단서　<span class="chk"></span> 소견서　<span class="chk"></span> 진료확인서　<span class="chk"></span> 청첩장·부고장 등　<span class="chk"></span> 기타</td></tr>
      </table>
      <div class="note"><b>증빙 서류 안내</b>
        · <b>인정되는 서류</b>: 의사의 진단서 또는 의견서, 병명·진료기간이 기록된 소견서, 진료확인서 등<br>
        · <b>인정되지 않는 서류</b>: 처방전, 약봉투 (단, 학교 규정에 따라 담임 확인으로 갈음하는 경우가 있습니다)<br>
        · <b>출석 인정 결석(경조사)</b> 예시 — 부모 사망 등 가족 경조사는 학교 규정에서 정한 일수만큼 인정됩니다.<br>
        · 감염병(학교보건법 제8조)으로 인한 결석은 출석으로 인정될 수 있습니다.
      </div>
      <div class="sign">위와 같이 결석을 신고합니다.<br>2026년　　　월　　　일<br>보호자 　　　　　　　　　 (서명 또는 인)</div>
      <table style="margin-top:18px"><tr><th>담임 확인</th><td class="fill"></td><th>확인일</th><td class="fill">2026년　　월　　일</td></tr></table>
    </div>`);
  }

  if (type === "earlyleave") {
    const slip = () => `<div style="border:1.5px solid #333;padding:16px 18px;margin-bottom:18px">
      <div style="text-align:center;font-size:19px;font-weight:800;margin-bottom:12px">${S}) 조퇴 · 외출증</div>
      <table style="margin-bottom:0">
        <tr><th>학생명</th><td class="fill">${pre(child, "name")}</td><th>학년 · 반</th><td class="fill">${pre(child, "grade")}${child && child.grade ? "학년 " : ""}${pre(child, "class")}${child && child.class_name ? "반" : ""}</td></tr>
        <tr><th>구분</th><td class="fill"><span class="chk"></span> 조퇴　　<span class="chk"></span> 외출</td><th>시각</th><td class="fill">　　시　　분</td></tr>
        <tr><th>사유</th><td class="fill" colspan="3"></td></tr>
        <tr><th>담임 확인</th><td class="fill" colspan="3">담임교사 　　　　　　　 (인)　　　2026년　　월　　일</td></tr>
      </table>
    </div>`;
    return shell(f.title, school, `<div class="sheet">
      <div style="font-size:12px;color:#666;margin-bottom:12px">※ 아래 두 장을 잘라서 사용하세요(1장은 학생 소지, 1장은 학교 보관).</div>
      ${slip()}${slip()}
    </div>`);
  }
  return null;
}
