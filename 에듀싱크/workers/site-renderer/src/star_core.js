// ============ 스타코인 원장 · 리그 점수 (2026-08-08, 기획서 v2 §02) ============
//
// 이 파일이 존재하는 이유 — **여기가 경제의 유일한 출입구다.**
//   «얼마를 줄 수 있나»가 화면에 흩어지면 앱을 껐다 켜서 우회되고, 파일마다 세면 반드시 어긋난다.
//   ⚠ 여태 `addStars` 가 api_mission.js·api_reward.js 두 곳에 복사돼 있었다 — 그래서 합쳤다.
//
// ── v2 에서 바뀐 것 (v1 의 「하루 30 리밋」 폐기) ──────────────────────────
//   리밋 하나로 막으면 **성실하게 다 한 아이가 손해**를 본다 — 「했는데 안 준다」.
//   그래서 축을 둘로 쪼갠다.
//
//     스타코인 ★  … 상점·재도전에 쓴다. 하루 상한 60(+히든 5). 리셋 없음
//     리그 점수    … 아무 데도 못 쓴다(순위만).  **상한 없음.** 매월 1일 리셋
//
//   코인 상한에 도달한 뒤에도 코인을 태워 재도전하면 **리그 점수만** 오른다.
//   → 모으는 아이와 경쟁하는 아이가 진짜로 갈린다. 코인 가치도 안 무너진다.
//
// ⚠ **쓰는 것(음수)은 상한을 안 탄다.** 상한은 «하루에 벌 수 있는 양»이지 잔액 제한이 아니다.
// ⚠ 「오늘」은 **KST**. UTC 로 세면 밤 9시 이후 수입이 다음 날로 넘어간다.

const KST = 9 * 3600 * 1000;
const nowIso = () => new Date().toISOString();

/* 하루에 «미션·퀴즈로» 벌 수 있는 상한. 🔴 대표님 확정 대기(60 제안).
   바꿀 때는 상점 가격표와 재도전 값표(§02)를 같이 봐야 한다. */
export const DAILY_COIN_LIMIT = 60;

/* 히든 주머니 — 출석·연속·깜짝 이벤트처럼 **우리가 주는 것**.
   기본 주머니와 따로 세는 이유: 부모가 미션을 아무리 늘려도 60 을 못 넘고,
   **히든은 부모가 못 건드린다.** 「오늘 뭔가 더 있을지도」가 남는다. */
export const DAILY_HIDDEN_LIMIT = 5;

export const BUCKET = { BASE: "base", HIDDEN: "hidden" };

/* 보너스도 여기 모아 둔다 — 화면이 각자 알고 있으면 값이 갈린다 */
export const BONUS = {
  quizPerfect: 5,   // 오늘의 미션 10문제 만점
  setComplete: 2,   // 미션 세트 완주
};

/* 재도전 값표 (기획서 v2 §02.2) — 1회는 무료, 그 뒤로는 배로 뛴다.
   배로 안 뛰면 「쉬운 문제 나올 때까지 돌리기」가 되어 무거운 미션이 영영 안 걸린다.
   🔴 대표님 확정 대기. */
export const RETRY_COST = [0, 3, 6, 12, 24, 48];
export const RETRY_MAX = RETRY_COST.length;      // 하루 6판(무료 1 + 유료 5)

export function retryCost(attempt) {
  // attempt 는 1부터. 표를 넘어가면 마지막 값을 쓴다(무료로 새지 않게)
  const i = Math.max(1, Math.round(attempt)) - 1;
  return RETRY_COST[Math.min(i, RETRY_COST.length - 1)];
}

export function ymdKst(d) {
  const t = new Date((d ? d.getTime() : Date.now()) + KST);
  return t.toISOString().slice(0, 10).replace(/-/g, "");
}

/* 리그 시즌 = KST 기준 YYYYMM. 매월 1일에 갈린다 */
export function seasonKst(d) {
  return ymdKst(d).slice(0, 6);
}

// 잔액 — 원장 전체 합. 상점 결제(음수)까지 포함한 «지금 가진 것»
export async function starsOf(db, childId) {
  const r = await db.prepare("SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id = ?")
    .bind(childId).first();
  return (r && r.n) || 0;
}

/* 오늘 «번» 양 — 양수만, 주머니별로 센다.
   ⚠ 잔액이 아니다. 오늘 60 을 벌고 60 을 썼어도 오늘 수입은 60 이라 더 못 번다.
      안 그러면 벌고-쓰고를 반복해 상한이 무의미해진다. */
export async function earnedToday(db, childId, bucket) {
  let sql = "SELECT COALESCE(SUM(delta),0) n FROM star_ledger " +
            "WHERE child_id = ? AND delta > 0 AND date(created_at, '+9 hours') = date(?, '+9 hours')";
  const args = [childId, nowIso()];
  if (bucket) { sql += " AND bucket = ?"; args.push(bucket); }
  const r = await db.prepare(sql).bind(...args).first();
  return (r && r.n) || 0;
}

function limitOf(bucket) {
  return bucket === BUCKET.HIDDEN ? DAILY_HIDDEN_LIMIT : DAILY_COIN_LIMIT;
}

/* 코인을 준다. **상한을 넘으면 넘는 만큼만 깎아서** 준다(요청을 통째로 거절하지 않는다).
   → 「59/60 인데 퀴즈 5개 맞음」이면 1개만 받고 끝난다. 0 을 주면 버그로 읽힌다.
   돌려주는 값으로 화면이 «오늘은 여기까지예요»를 말할 수 있다. */
export async function grantStars(db, childId, want, reason, bucket) {
  const b = bucket === BUCKET.HIDDEN ? BUCKET.HIDDEN : BUCKET.BASE;
  const limit = limitOf(b);
  const earned = await earnedToday(db, childId, b);
  const room = Math.max(0, limit - earned);
  const granted = Math.max(0, Math.min(Math.round(want), room));

  if (granted > 0) {
    await db.prepare(
      "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES (?,?,?,?,?)"
    ).bind(childId, granted, reason, b, nowIso()).run();
  }
  return {
    granted,
    bucket: b,
    capped: granted < Math.round(want),   // 상한에 걸려 깎였나
    earned_today: earned + granted,
    limit,
    stars: await starsOf(db, childId),
  };
}

/* 되돌려 준다(환불). **상한을 안 탄다** — 이게 grantStars 와 다른 점이고, 중요하다.
   grantStars 로 환불하면 «상한에 걸린 아이는 환불을 못 받는» 사고가 난다.
   낸 돈을 돌려주는 것은 «버는 것»이 아니므로 상한을 태우면 안 된다. */
export async function refundStars(db, childId, amount, reason) {
  const a = Math.round(Math.abs(amount));
  if (a <= 0) return { refunded: 0, stars: await starsOf(db, childId) };
  await db.prepare(
    "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES (?,?,?,?,?)"
  ).bind(childId, a, "refund:" + reason, BUCKET.BASE, nowIso()).run();
  return { refunded: a, stars: await starsOf(db, childId) };
}

/* 코인을 뺀다(상점 결제 · 재도전 · 되돌리기). **상한을 안 탄다.**
   ⚠ 잔액 검사는 부르는 쪽 책임이다 — 상점은 «모자라면 왜 모자란지»를 말해야 하므로
     여기서 조용히 막으면 그 문구를 만들 수 없다. */
export async function spendStars(db, childId, amount, reason) {
  const a = Math.round(Math.abs(amount));
  if (a <= 0) return { spent: 0, stars: await starsOf(db, childId) };
  await db.prepare(
    "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES (?,?,?,?,?)"
  ).bind(childId, -a, reason, BUCKET.BASE, nowIso()).run();
  return { spent: a, stars: await starsOf(db, childId) };
}

// ════════════════════════════════════════════════════════════════════
//  리그 점수 — 상한이 없다. 매월 1일에 리셋된다.
//
//  ⚠ **STAGE 1(리그를 끄고 출시하는 동안)에도 이미 쌓는다.**
//    STAGE 2 에서 켤 때 「먼저 가입한 애가 유리」가 생기지 않으려면 처음부터 세고 있어야 하고,
//    어차피 첫 시즌은 그 달 1일에 리셋되므로 손해 볼 것이 없다.
//  ⚠ 화면에는 STAGE 2 전까지 **안 보인다** — 켜는 것은 API 쪽 판단이다.
// ════════════════════════════════════════════════════════════════════

export async function addPoints(db, childId, points) {
  const p = Math.max(0, Math.round(points || 0));
  if (p <= 0) return { points: 0, season: seasonKst() };
  const season = seasonKst();
  // (child_id, season) 이 PK 라 UPSERT 가 «시즌이 바뀌면 새 줄»을 자동으로 만든다
  await db.prepare(
    "INSERT INTO league_standing (child_id, season, points, updated_at) VALUES (?,?,?,?) " +
    "ON CONFLICT(child_id, season) DO UPDATE SET points = points + ?, updated_at = ?"
  ).bind(childId, season, p, nowIso(), p, nowIso()).run();
  return { points: p, season };
}

export async function pointsOf(db, childId, season) {
  const s = season || seasonKst();
  const r = await db.prepare(
    "SELECT points, tier, group_no, final_rank FROM league_standing WHERE child_id = ? AND season = ?"
  ).bind(childId, s).first();
  return {
    season: s,
    points: (r && r.points) || 0,
    tier: (r && r.tier) || "bronze",
    group_no: (r && r.group_no) || null,
    final_rank: (r && r.final_rank) || null,
  };
}

// ════════════════════════════════════════════════════════════════════
//  레벨 — **해낸 미션 수**로 오른다. 누적 코인이 아니다.
//  코인 기준이면 퀴즈 잘 푸는 애만 빨리 오르지만, 미션 수면 꾸준한 애는 무조건 오른다.
//  경쟁은 리그에서 하니 레벨까지 실력을 반영할 필요가 없다. **리셋 없음.**
// ════════════════════════════════════════════════════════════════════

/* 레벨 구간 — 앞은 촘촘하고 뒤로 갈수록 벌어진다.
   처음 며칠에 두세 번 올라야 «이거 오르는 거구나»가 몸에 남는다. */
export function levelOf(missionsDone) {
  const n = Math.max(0, missionsDone || 0);
  let lv = 1, need = 3, acc = 0;
  while (acc + need <= n && lv < 99) { acc += need; lv++; need = Math.round(need * 1.35) + 1; }
  return { level: lv, done: n, into: n - acc, need, next: acc + need };
}

export async function bumpLevel(db, childId, by) {
  const n = Math.max(1, Math.round(by || 1));
  await db.prepare("UPDATE children SET level_missions = level_missions + ? WHERE id = ?")
    .bind(n, childId).run();
}

// 화면 머리에 띄우는 «오늘 18/60» 한 줄 + 레벨 + (아직 안 보이는) 리그 점수
export async function coinState(db, childId) {
  const base = await earnedToday(db, childId, BUCKET.BASE);
  const hidden = await earnedToday(db, childId, BUCKET.HIDDEN);
  const c = await db.prepare("SELECT level_missions, streak_days FROM children WHERE id = ?")
    .bind(childId).first();
  const lv = levelOf(c && c.level_missions);
  return {
    stars: await starsOf(db, childId),
    earned_today: base,
    limit: DAILY_COIN_LIMIT,
    room: Math.max(0, DAILY_COIN_LIMIT - base),
    hidden_today: hidden,
    hidden_limit: DAILY_HIDDEN_LIMIT,
    level: lv.level,
    level_into: lv.into,
    level_need: lv.need,
    streak: (c && c.streak_days) || 0,
  };
}
