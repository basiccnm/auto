/* ================= 감사 기록 (admin_audit) =================
   「누가·언제·무엇을·대상·사유」(대표님 요구 §4, 2026-08-10).
   ⚠ **지우는 길을 만들지 않는다.** 관리자가 자기 흔적을 지울 수 있으면 감사 로그가 아니다.
   ⚠ 사유가 빈 줄은 붉게 띄운다 — 사유 없이 통과한 길이 아직 남아 있다는 뜻이다. */
const AUDIT_KO = {
  pass_adjust: "이용권 조정", order_confirm: "주문 확인", order_cancel: "주문 취소",
  member_delete: "회원 삭제", child_delete: "자녀 삭제",
};
export function adminAuditPage(rows, { q = "" } = {}, badges) {
  const list = rows || [];
  const body = `
    <div class="hd"><h2>기록</h2>
      <form method="get" style="display:flex;gap:8px">
        <input class="btn" style="cursor:text;min-width:200px" name="q" value="${esc(q)}" placeholder="사유·대상·관리자">
        <button class="btn pri" type="submit">찾기</button>
      </form>
    </div>
    <p class="sub" style="margin:0 0 14px">이용권을 손으로 주거나 회수한 일, 주문을 확인·취소한 일, 지운 일이 남습니다. <b>지울 수 없습니다.</b></p>
    <div class="card">
      ${!list.length ? `<div class="empty" style="padding:28px">기록이 없습니다</div>` : list.map((r) => `
        <div class="trow" style="padding:12px 14px;align-items:flex-start">
          <span style="width:132px;font-size:13px;color:#6b7280">${esc(r.atF)}</span>
          <span style="width:96px;font-size:13.5px;font-weight:700">${esc(AUDIT_KO[r.action] || r.action)}</span>
          <span style="flex:1;min-width:0">
            <div style="font-size:14px">${esc(r.detail || "")}</div>
            <div style="font-size:13px;color:${r.reason ? "#6b7280" : "#b91c1c"};margin-top:2px">
              ${r.reason ? "사유 " + esc(r.reason) : "사유 없음"}</div>
          </span>
          <span style="width:150px;font-size:12.5px;color:#6b7280;text-align:right">
            ${esc(r.targetKind || "")} ${esc(r.targetShort || "")}<br>${esc(r.actor)} · ${esc(r.ip || "")}
          </span>
        </div>`).join("")}
    </div>`;
  return adminLayout({ title: "기록", active: "audit", body, badges });
}

