// ================= 계정 탈퇴 (단일 진입점) =================
// 회신20 §3-3·§5 · 정본 §4 · 계약 §2.1
//
// 🔴 **계정을 파기하는 경로는 이 파일 하나뿐이다.** `data_children.js`와 같은 원칙 —
//    흩어놓으면 표가 늘 때 한 곳을 빠뜨리고, 그러면 "전부 삭제했습니다"가 거짓말이 된다.
//
// 층이 다르다: `deleteChildCascade`는 **자녀 단위**, 여기는 **계정 단위**다.
// 계정 탈퇴는 자녀 연쇄를 전부 돌린 뒤 그 위에 계정·인증·연락을 얹어 파기한다.
//
// ── 파기 원칙 (회신20 §3-3) ────────────────────────────────
//   · 신원·인증·연락  → **완전 파기**  (accounts PII · auth_methods · users ·
//                                       notif_settings · push_subscriptions · free_trials)
//   · 결제·신고 이력  → **익명 보존**  (payments · orders · community_reports · info_reports)
//                       법정 보존·남용 대응 때문에 행은 남기고 **사람과의 연결만 끊는다.**
//
// ── 왜 accounts 행을 지우지 않고 비우는가 ───────────────────
// `orders.account_id`가 **NOT NULL REFERENCES accounts(id)** 이다. 행을 지우면
//   (a) FOREIGN KEY 위반으로 탈퇴 자체가 실패하거나
//   (b) 주문 이력을 함께 지워야 하는데, 그건 "결제 이력 보존" 원칙에 정면으로 어긋난다.
// 스키마가 이미 `accounts.status = active | suspended | withdrawn` 을 두고 있다 —
// **묘비(tombstone)로 남기는 게 원래 설계된 모양이다.**
// 남는 건 껍데기다: 이름·이메일·전화·생년은 NULL, 로그인 수단은 전멸, owner_token은 회전.
//
// 이건 2026-07-24에 두 번 데인 교훈의 일반형이다 —
// **"보존하기로 한 표가 FK로 물려 있으면 '안 지운다'만으로는 안 끝난다. 연결을 끊어야 끝난다."**
// (자녀 삭제의 `orders.child_id` FK 500, `community_reports.post_id` FK 500)

import { deleteChildCascade } from "./data_children.js";

// 완전 파기 대상 중 owner_token으로 매달린 표들.
// ⚠️ 새 표를 만들며 owner_token을 넣었다면 **여기 아니면 아래 익명보존 목록 둘 중 하나**에 반드시 넣어라.
//    어느 쪽인지 정하지 못하겠으면 그건 아직 그 표의 성격을 안 정한 것이다.
const PURGE_BY_OWNER_TOKEN = [
  "users",              // 소셜 로그인 이력(구 회원 표)
  "notif_settings",     // 알림 on/off — 연락 설정
  "push_subscriptions", // 웹푸시 엔드포인트 — 기기 식별자다. 남기면 탈퇴자에게 알림이 간다
  // free_trials — 무료체험 사용 이력.
  // ⚠️ 이걸 지우면 **탈퇴 → 재가입으로 무료체험을 반복**할 수 있다. 그래도 지금은 파기가 맞다:
  //    이 표의 열쇠가 `owner_token`이라 **남겨둬도 새 토큰으로 재가입하면 어차피 못 막는다.**
  //    막지도 못하는 데이터를 파기 의무를 어기면서까지 붙들 이유가 없고, 무료체험 남용은
  //    돈이 나가지 않아 저위험이다(2026-07-24 확정).
  // 📌 전환 조건: **휴대폰 본인인증이 붙는 시점**에 "휴대폰 단방향 해시 마커로 재체험 방지"를
  //    별도 설계하고, 그때 이 표를 완전파기 → **익명 마커 보존**으로 옮긴다.
  //    (인증이 없으면 어차피 못 막으므로 그 전에 미리 옮기는 건 의미가 없다.)
  "free_trials",
];

// 익명 보존 대상. owner_token이 NOT NULL이라 NULL을 못 넣으므로 **익명 토큰으로 덮어쓴다.**
// 지우지 않는 이유: 결제는 법정·분쟁 대비, 신고는 남용 대응 때문에 사실 자체는 남아야 한다.
const ANONYMIZE_BY_OWNER_TOKEN = [
  "payments",           // 구 결제 이력(동결됨, 계약 §7.3-②)
  "community_reports",  // 신고 이력 — 신고자와의 연결만 끊는다(대상 글은 그대로)
];

// 계정 하나를 파기한다. 반환: { ok:true, purged:{...} } | { ok:false, error }
//
// account가 null일 수 있다(쿠키만 있고 accounts 행이 없는 레거시 사용자).
// 그 경우에도 owner_token에 매달린 데이터는 **똑같이 파기한다** — 계정이 없다고 데이터가
// 안 지워지면 그게 더 나쁘다.
export async function withdrawAccount(db, env, ownerToken, account = null) {
  if (!ownerToken) return { ok: false, error: "no_owner_token" };

  // 1) 자녀부터. R2 원본이 여기서 지워진다 — 실패하면 **중단**한다(고아 사진 방지).
  //    계정을 먼저 비우면 자녀를 찾을 열쇠를 잃는다. 순서가 곧 안전이다.
  const { results: kids } = await db
    .prepare("SELECT id FROM children WHERE owner_token = ?")
    .bind(ownerToken)
    .all();
  for (const k of kids) {
    const r = await deleteChildCascade(db, env, k.id);
    if (!r.ok) return { ok: false, error: r.error, stage: "children", child_id: k.id };
  }

  // 2) 이력은 사람과의 연결만 끊는다. **계정을 비우기 전에** 해야 한다 —
  //    owner_token을 회전한 뒤엔 어느 행이 이 사람 것이었는지 알 수 없다.
  // 계정 껍데기와 보존 이력이 **같은** 익명 토큰을 쓴다. 일부러 그렇게 뒀다 —
  // 껍데기엔 사람을 식별할 값이 하나도 안 남으므로 연결돼 있어도 익명이고,
  // 대신 "이 결제들과 이 신고들이 같은(누군지 모를) 사람 것"이라는 사실은 남아 남용 대응에 쓸 수 있다.
  // 옛 owner_token은 어디에도 안 남는다 = 사용자의 옛 쿠키로는 아무것도 못 찾는다.
  const anonToken = `withdrawn-${crypto.randomUUID()}`;
  const stmts = ANONYMIZE_BY_OWNER_TOKEN.map((t) =>
    db.prepare(`UPDATE ${t} SET owner_token = ? WHERE owner_token = ?`).bind(anonToken, ownerToken)
  );
  // info_reports.owner_token은 nullable이라 아예 비운다(익명 신고와 같은 모양이 된다).
  stmts.push(db.prepare("UPDATE info_reports SET owner_token = NULL WHERE owner_token = ?").bind(ownerToken));

  // 3) 신원·인증·연락 완전 파기
  for (const t of PURGE_BY_OWNER_TOKEN) {
    stmts.push(db.prepare(`DELETE FROM ${t} WHERE owner_token = ?`).bind(ownerToken));
  }

  if (account) {
    // 로그인 수단 전멸 — 이게 실질적인 탈퇴다. 소셜·아이디·휴대폰 어느 것으로도 못 들어온다.
    stmts.push(db.prepare("DELETE FROM auth_methods WHERE account_id = ?").bind(account.id));
    stmts.push(db.prepare("DELETE FROM revoked_tokens WHERE account_id = ?").bind(account.id));
    // 주문은 계정 껍데기에 매달아 둔다(FK NOT NULL). 사람을 식별할 값이 껍데기에 안 남으면 익명이다.
    stmts.push(
      db
        .prepare(
          `UPDATE accounts
              SET status = 'withdrawn',
                  display_name = NULL, email = NULL, phone = NULL,
                  phone_verified = 0, birth_ymd = NULL,
                  owner_token = ?,          -- 회전: 옛 쿠키가 이 계정에 다시 닿지 못하게
                  last_login_at = NULL
            WHERE id = ?`
        )
        .bind(anonToken, account.id)
    );
  }

  await db.batch(stmts);
  return {
    ok: true,
    purged: { children: kids.length, account: account ? account.id : null },
  };
}
