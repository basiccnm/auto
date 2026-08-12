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

// ════════════════════════════════════════════════════════════════════
//  ⚙️ 경제 정본 ECON — **숫자를 고치려면 여기만 고친다**
//
//  🔴 이 객체는 `GET /api/v1/children/{id}/econ` 으로 **앱에 그대로 내려간다.**
//     앱은 자기 안에 값을 안 들고 있다(들고 있는 것은 서버가 아직 답을 안 줬을 때의
//     임시 기본값뿐). 그래서 **값을 바꾸면 워커 배포 한 번으로 즉시 반영된다** —
//     APK 를 다시 만들 필요도, 스토어 심사를 기다릴 필요도 없다(2026-08-12 대표님 지시:
//     «업데이트보다 우리가 수정하면 바로 작업 들어갈 수 있게»).
//     ⚠ 그러므로 새 숫자를 만들 때는 **여기 넣고 econ 응답에 실어라.** 화면에 상수로 박지 마라.
// ════════════════════════════════════════════════════════════════════
export const ECON = {
  /* 「별 라인」 — 부모가 정하는 **하루 별 예산**. 미션 배정도 상한도 전부 이 하나에서 나온다.
     v2 까지는 「하루 3개 · 상한 60」이었는데 실측하니 저학년이 다 해도 15~20 밖에 못 벌었다
     (미션 3개 = 별 4 · 세트 4 · 학교 2 · 기록 3 · 퀴즈 15). 60 은 벽이 아니라 **안 닿는 천장**이라
     아무 일도 안 하고 있었다. 개수가 아니라 «별»로 배정해야 학년이 올라도 값이 안 어긋난다. */
  /* 🔴 **다이얼의 모든 눈금은 «닿을 수 있어야» 한다.** 이번 작업의 시작이 그것이었다 —
     옛 상한 60 은 아무리 해도 안 닿는 천장이라 아무 일도 안 하고 있었다.
     그래서 최대값을 카탈로그 실측으로 정했다(2026-08-12, 로컬 D1 전수):
       · (밴드×시즌) 후보가 15~21 개뿐이고, 사진(review)을 빼면 9~14 개다
       · 하루 8 개까지 배정하면 의뢰 미션으로 벌 수 있는 건 **저학년 ~10 · 중고학년 ~13**
       · 미션 밖 수입 최대 29 (퀴즈 만점 15 + 세트 4 + 학교 2 + 기록 3 + 부모 칭찬 5)
       → 저학년 기준 하루 최대 ≈ 39. 그래서 **35 를 최대**로 둔다. 그 위는 또 천장이 된다.
     ⚠ 카탈로그가 두꺼워지면(미션을 더 넣으면) 이 최대값을 같이 올려라. 지금은 재고가 벽이다. */
  starLineDefault: 25,
  starLineMin: 10,
  starLineMax: 35,
  starLineStep: 5,

  /* 🔑 **별 라인이 곧 하루 상한이다.** 따로 배율을 두지 않는다.
     한때 「라인 × 1.5」로 뒀다가 지웠다 — 부모에게 「20 으로 정했는데 왜 30 까지 들어와요」를
     설명할 방법이 없었다. 부모가 정한 숫자가 화면의 숫자와 같아야 손잡이로 쓸 수 있다.
     기본 30 인 근거: 퀴즈 만점 15 + 세트 6 + 기록 3 + 부모 칭찬 5 = 29 가 미션 밖에서 들어온다.
     여기에 미션 몫을 얹으면 «열심히 한 날은 채워지고, 대충 한 날은 안 채워진다» — 그게 상한이다. */

  /* 의뢰 미션이 맡는 몫. 나머지는 퀴즈·세트·기록·부모 칭찬이 채운다.
     ⚠ 1.0 으로 두면 미션만으로 라인을 채우려다 하루 8개가 배정된다 — 그건 숙제다. */
  missionShare: 0.4,

  /* 히든 주머니 — 출석·연속·깜짝 이벤트처럼 **우리가 주는 것**.
     기본 주머니와 따로 세는 이유: 부모가 라인을 아무리 올려도 이건 안 늘고,
     **히든은 부모가 못 건드린다.** 「오늘 뭔가 더 있을지도」가 남는다. */
  hiddenLimit: 5,

  /* 미션 한 개의 «바라는 크기». 배정 개수를 이걸로 역산한다 — 몫 ÷ 2.5 개쯤.
     ⚠ 없으면 1점짜리로 예산을 채워서 «★1 짜리 7개»가 나온다(2026-08-12 실측).
        할 일이 일곱 줄이면 아이는 목록을 보고 시작하기도 전에 진다. 적고 굵게. */
  avgStarTarget: 2.5,

  /* 하루에 배정하는 미션 «개수»의 안전선 — 별 라인을 채우다 보면 1점짜리로 20개가 될 수 있다.
     아이 화면이 목록이 되면 그건 미션이 아니라 숙제다. */
  maxPerDay: 8,
  minPerDay: 2,

  /* ✅ 즉시 통과 — `instant` 미션은 아이가 누르면 **그 자리에서 별이 나온다**.
     2026-08-02 에 의뢰 미션을 전부 부모 확인형으로 바꿨는데, 그래서 「자동으로 되는 것이
     하나도 없는」 상태가 됐다. 부모가 안 눌러주면 별이 안 나오니 부모 숙제가 된 것이다.
     🔑 «무조건 통과»를 막는 것은 이제 확인이 아니라 **별 라인**이다 —
        아무리 눌러도 하루 총량이 부모가 정한 선을 못 넘는다.
     되돌리기는 그대로 남는다(`revert`) — 부모의 «이건 아니야» 한 번이면 별까지 회수된다. */
  autoPassInstant: true,

  /* 보너스도 여기 모아 둔다 — 화면이 각자 알고 있으면 값이 갈린다 */
  bonus: {
    quizPerfect: 5,   // 오늘의 미션 10문제 만점
    setComplete: 2,   // 미션 세트 완주
  },

  /* 재도전 값표 (기획서 v2 §02.2) — 1회는 무료, 그 뒤로는 배로 뛴다.
     배로 안 뛰면 「쉬운 문제 나올 때까지 돌리기」가 되어 무거운 미션이 영영 안 걸린다. */
  retryCost: [0, 3, 6, 12, 24, 48],
};

/* 아래 셋은 **옛 이름**이다. 부르는 곳이 여럿이라 지우지 않고 ECON 을 가리키게만 뒀다.
   새로 쓸 때는 ECON 을 직접 봐라. */
export const DAILY_HIDDEN_LIMIT = ECON.hiddenLimit;
export const BONUS = ECON.bonus;
export const RETRY_COST = ECON.retryCost;

/* 별 라인을 안 정한 집(0/NULL)은 기본값을 쓴다. 범위를 벗어난 값은 잘라낸다 —
   DB 에 이상한 값이 들어가도 경제가 안 무너지게. */
export function clampLine(v) {
  const n = Math.round(Number(v) || 0);
  if (!n) return ECON.starLineDefault;
  return Math.max(ECON.starLineMin, Math.min(ECON.starLineMax, n));
}

export async function starLineOf(db, childId) {
  const r = await db.prepare("SELECT star_line FROM children WHERE id = ?").bind(childId).first();
  return clampLine(r && r.star_line);
}

/* 하루 상한 = 별 라인 **그 자체**. 옛 상수 60 자리를 이게 대신한다.
   함수로 남겨 두는 이유: 부르는 곳이 여럿이라, 나중에 셈이 바뀌어도 여기 한 줄만 고치면 된다. */
export function coinLimitOf(line) {
  return clampLine(line);
}

// 의뢰 미션에 배정할 별 목표 — 라인의 일부만 맡는다(나머지는 퀴즈·세트·기록)
export function missionBudgetOf(line) {
  return Math.max(1, Math.round(clampLine(line) * ECON.missionShare));
}

export const BUCKET = { BASE: "base", HIDDEN: "hidden" };

export const RETRY_MAX = ECON.retryCost.length;      // 하루 6판(무료 1 + 유료 5)

export function retryCost(attempt) {
  // attempt 는 1부터. 표를 넘어가면 마지막 값을 쓴다(무료로 새지 않게)
  const i = Math.max(1, Math.round(attempt)) - 1;
  return ECON.retryCost[Math.min(i, ECON.retryCost.length - 1)];
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

/* 상한은 이제 **아이마다 다르다** — 부모가 정한 별 라인에서 나온다.
   히든은 부모가 못 건드리므로 라인과 무관하게 고정이다. */
async function limitOf(db, childId, bucket) {
  if (bucket === BUCKET.HIDDEN) return ECON.hiddenLimit;
  return coinLimitOf(await starLineOf(db, childId));
}

/* 코인을 준다. **상한을 넘으면 넘는 만큼만 깎아서** 준다(요청을 통째로 거절하지 않는다).
   → 「59/60 인데 퀴즈 5개 맞음」이면 1개만 받고 끝난다. 0 을 주면 버그로 읽힌다.
   돌려주는 값으로 화면이 «오늘은 여기까지예요»를 말할 수 있다. */
export async function grantStars(db, childId, want, reason, bucket) {
  const b = bucket === BUCKET.HIDDEN ? BUCKET.HIDDEN : BUCKET.BASE;
  const limit = await limitOf(db, childId, b);
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
  const c = await db.prepare("SELECT level_missions, streak_days, star_line FROM children WHERE id = ?")
    .bind(childId).first();
  const lv = levelOf(c && c.level_missions);
  const line = clampLine(c && c.star_line);
  const limit = coinLimitOf(line);
  return {
    stars: await starsOf(db, childId),
    earned_today: base,
    star_line: line,          // 부모가 정한 하루 별 예산 — 화면이 이 값을 보여준다
    limit,
    room: Math.max(0, limit - base),
    hidden_today: hidden,
    hidden_limit: ECON.hiddenLimit,
    level: lv.level,
    level_into: lv.into,
    level_need: lv.need,
    streak: (c && c.streak_days) || 0,
  };
}
