// ================= 스타코인 원장 · 하루 리밋 (2026-08-08) =================
// 기획서 `docs/기획-스타코인-v1.md` §02.
//
// 이 파일이 존재하는 이유 — **리밋이 이 시스템의 심장이다.**
//   리밋이 화폐 가치를 정하고, 그게 상점 가격표를 정한다(★10,000 짜리가 성립하는 근거).
//   그래서 «얼마를 줄 수 있나»는 화면이 아니라 **여기 한 곳**에서만 정해져야 한다.
//   화면이 세면 앱을 껐다 켜서 우회되고, 파일마다 세면 반드시 어긋난다.
//
// ⚠ 여태 `addStars` 가 api_mission.js·api_reward.js **두 곳에 복사돼** 있었다.
//   리밋을 한쪽에만 걸면 다른 쪽으로 새므로 둘 다 이 파일을 쓰게 바꿨다.
// ⚠ **쓰는 것(음수)은 리밋을 안 탄다.** 리밋은 «하루에 벌 수 있는 양»이지 잔액 제한이 아니다.
// ⚠ 「오늘」은 **KST** 다. UTC 로 세면 밤 9시 이후 수입이 다음 날로 넘어간다.

const KST = 9 * 3600 * 1000;
const nowIso = () => new Date().toISOString();

/* 하루에 벌 수 있는 스타코인 상한.
   기획서 §02 제안값 30 — 벌 수 있는 총량(~40)보다 낮게 두어
   **아이가 «무엇으로 채울지» 고르게** 만드는 것이 이 숫자의 목적이다.
   🔴 대표님 확정 대기. 바꿀 때는 상점 가격표(§02)도 같이 봐야 한다. */
export const DAILY_COIN_LIMIT = 30;

/* 만점·완주 보너스도 여기 모아 둔다 — 화면이 각자 알고 있으면 값이 갈린다 */
export const BONUS = {
  quizPerfect: 5,   // 데일리 퀴즈 10문제 만점
  setComplete: 2,   // 미션 세트 완주
};

export function ymdKst(d) {
  const t = new Date((d ? d.getTime() : Date.now()) + KST);
  return t.toISOString().slice(0, 10).replace(/-/g, "");
}

// 잔액 — 원장 전체 합. 상점 결제(음수)까지 포함한 «지금 가진 것»
export async function starsOf(db, childId) {
  const r = await db.prepare("SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id = ?")
    .bind(childId).first();
  return (r && r.n) || 0;
}

/* 오늘 «번» 양 — 양수만 센다.
   ⚠ 잔액이 아니다. 오늘 30을 벌고 30을 썼어도 오늘 수입은 30이라 더 못 번다.
      안 그러면 벌고-쓰고를 반복해 리밋이 무의미해진다. */
export async function earnedToday(db, childId) {
  const r = await db.prepare(
    "SELECT COALESCE(SUM(delta),0) n FROM star_ledger " +
    "WHERE child_id = ? AND delta > 0 AND date(created_at, '+9 hours') = date(?, '+9 hours')"
  ).bind(childId, nowIso()).first();
  return (r && r.n) || 0;
}

/* 코인을 준다. **리밋을 넘으면 넘는 만큼만 깎아서** 준다(요청을 통째로 거절하지 않는다).
   → 아이가 «29/30 인데 퀴즈 5개 맞음» 이면 1개만 받고 끝난다. 0을 주면 버그로 읽힌다.
   돌려주는 값으로 화면이 «오늘은 여기까지예요» 를 말할 수 있다. */
export async function grantStars(db, childId, want, reason) {
  const limit = DAILY_COIN_LIMIT;
  const earned = await earnedToday(db, childId);
  const room = Math.max(0, limit - earned);
  const granted = Math.max(0, Math.min(Math.round(want), room));

  if (granted > 0) {
    await db.prepare("INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES (?,?,?,?)")
      .bind(childId, granted, reason, nowIso()).run();
  }
  return {
    granted,
    capped: granted < Math.round(want),   // 리밋에 걸려 깎였나
    earned_today: earned + granted,
    limit,
    stars: await starsOf(db, childId),
  };
}

/* 코인을 뺀다(상점 결제·되돌리기). **리밋을 안 탄다.**
   ⚠ 잔액 검사는 부르는 쪽 책임이다 — 상점은 «모자라면 왜 모자란지»를 말해야 하므로
     여기서 조용히 막으면 그 문구를 만들 수 없다. */
export async function spendStars(db, childId, amount, reason) {
  const a = Math.round(Math.abs(amount));
  if (a <= 0) return { spent: 0, stars: await starsOf(db, childId) };
  await db.prepare("INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES (?,?,?,?)")
    .bind(childId, -a, reason, nowIso()).run();
  return { spent: a, stars: await starsOf(db, childId) };
}

// 화면 머리에 띄우는 «오늘 23/30» 한 줄
export async function coinState(db, childId) {
  const earned = await earnedToday(db, childId);
  return {
    stars: await starsOf(db, childId),
    earned_today: earned,
    limit: DAILY_COIN_LIMIT,
    room: Math.max(0, DAILY_COIN_LIMIT - earned),
  };
}
