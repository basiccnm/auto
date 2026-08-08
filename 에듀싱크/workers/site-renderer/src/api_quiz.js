// ============ 🧠 오늘의 미션 (2026-08-08, 기획서 v2 §02.2·§05) ============
//
// 4지선다 10문제 · 문제당 5초 · **하루 6판(무료 1 + 코인 5)** · 맞힌 만큼 코인 · 만점 보너스.
//
// ⚠ 용어 — 화면에는 「도전」이 아니라 **「오늘의 미션」**. 아이에겐 부모가 준 것이든
//   우리가 낸 것이든 다 미션이다. 서버 필드명(quiz_*)은 안 바꾼다 — 출력 단에서만 갈아입힌다.
//
// 이 파일이 지키는 규칙 — 화면이 아니라 여기서 지켜야 우회가 안 된다:
//   ① **정답을 절대 내려보내지 않는다.** 채점은 서버가 한다.
//      내려보내면 개발자도구로 다 보인다 — 「못 속이는 미션」인 이유가 사라진다.
//   ② **하루 판 수**는 quiz_session 의 PK(child_id, ymd, attempt) 가 강제한다.
//      세는 로직을 또 쓰지 않는다 — INSERT 가 먹으면 그 판은 처음이다.
//   ③ **코인·점수는 star_core 로만.** 상한을 여기서 다시 세지 않는다.
//   ④ 채점은 «낸 문제»(session.codes)로만 한다. 클라이언트가 보낸 code 를 믿지 않는다.
//   ⑥ **한 문제씩 채점하고 그 자리에서 답을 알려 준다**(대표님 지시 08-08 — 「답안지 주지 말고
//      바로 문제 풀고 답이 나오게」). 답이 안 새는 이유는 **이미 잠근 문제의 답만** 주기 때문이다.
//      잠금은 quiz_answer_log 의 UNIQUE(child_id, ymd, attempt, code) 가 강제한다 —
//      «틀린 걸 알고 다시 내는» 길이 DB 수준에서 막힌다.
//   ⑤ **재도전 값은 서버가 매긴다.** 클라이언트가 보낸 값으로 결제하지 않는다.
//
// ── 왜 재도전이 «퀴즈만» 인가 (기획서 v2 §02.2) ──────────────────────────
//   급식·친구·수업은 하루에 한 번뿐인 사실이고 아침도 두 번 오지 않는다.
//   **반복이 자연스러운 건 문제 푸는 것뿐이다.**
//   그리고 부모 미션이 리셋되면 **부모가 아이와 한 약속을 아이가 코인으로 지워버리는 셈**이라
//   말이 안 된다.

import { apiOk, apiErr, readJson } from "./api_core.js";
import { resolveAuth } from "./auth_core.js";
import {
  grantStars, spendStars, refundStars, addPoints, coinState, ymdKst, BONUS,
  retryCost, RETRY_MAX, bumpLevel,
} from "./star_core.js";

const nowIso = () => new Date().toISOString();
const QUIZ_N = 10;          // 한 판 문제 수

function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

// api_reward.js·api_mission.js 의 gate() 와 **같은 규칙**이다. 한쪽만 고치면 구멍이 난다.
async function gate(request, db, env, childId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  const child = await db.prepare(
    "SELECT id, grade, owner_token FROM children WHERE id = ? AND owner_token = ?"
  ).bind(childId, auth.ownerToken).first();
  if (!child) return { err: apiErr("NOT_FOUND") };
  if (auth.role === "child" && String(auth.childId) !== String(child.id)) return { err: apiErr("FORBIDDEN") };
  return { child, auth };
}

const bandOf = (grade) => (+grade <= 2) ? "low" : (+grade <= 4) ? "mid" : "high";

/* 저학년은 어려운 문제를 아예 안 본다 — 표의 인지도 등급(tier)으로 자른다.
   「부르키나파소 수도」가 1학년에게 나오면 그날을 통째로 포기한다. */
const tierCapOf = (band) => (band === "low") ? 1 : (band === "mid") ? 2 : 3;

/* 문제를 뽑는다 — **8분야에서 고루, 진짜 랜덤으로**(대표님 지시 08-08).
   한 분야만 쏟아지면 «나는 수학 못해서 오늘 망함»이 되어 그날을 포기한다.
   ⚠ 한때 날짜로 만든 씨앗을 썼는데, 그러면 **같은 학년 아이들이 같은 날 같은 문제**를 받고
     내일 무엇이 나올지도 정해져 있다. RANDOM() 이 정본이다.
   ⚠ 2판째부터는 **틀렸던 문제를 먼저** 채운다(기획서 v2 §02.2).
      재출제가 「우려먹기」가 아니라 오답노트가 되고, 문제 재고 압박도 준다. */
async function pickQuestions(db, child, band, attempt) {
  const picked = [];
  const seen = new Set();
  const tierCap = tierCapOf(band);

  if (attempt > 1) {
    // 틀린 적 있고 그 뒤로 맞힌 적 없는 문제 — 오래 틀린 것부터
    const { results } = await db.prepare(
      `SELECT q.code, q.field FROM quiz_questions q
         JOIN (SELECT code, MAX(correct) mx, COUNT(*) n FROM quiz_answer_log
                WHERE child_id = ? GROUP BY code) l ON l.code = q.code
        WHERE l.mx = 0 AND q.active = 1 AND q.tier <= ?
          AND (q.band = 'all' OR q.band = ?)
          AND q.pack_id IN (SELECT id FROM packs WHERE active = 1)
        ORDER BY l.n DESC LIMIT ?`
    ).bind(child.id, tierCap, band, QUIZ_N).all();
    for (const r of (results || [])) { picked.push(r); seen.add(r.code); }
  }

  const fields = ["kor", "math", "sci", "world", "proverb", "life", "sports", "ent"];
  for (const f of fields) {
    if (picked.length >= QUIZ_N) break;
    const { results } = await db.prepare(
      `SELECT q.code, q.field FROM quiz_questions q
        WHERE q.active = 1 AND q.field = ? AND q.tier <= ?
          AND (q.band = 'all' OR q.band = ?)
          AND q.pack_id IN (SELECT id FROM packs WHERE active = 1)
        ORDER BY RANDOM() LIMIT 3`
    ).bind(f, tierCap, band).all();
    for (const r of (results || [])) {
      /* ⚠ 여기서 «넘치게 담고 뒤에서 자르면» 안 된다.
         한때 그렇게 짰다가, 일부러 앞에 넣은 **오답노트 문제가 잘려 나갔다**(2026-08-08 실측).
         빈자리만큼만 담는다. */
      if (picked.length >= QUIZ_N) break;
      if (!seen.has(r.code)) { picked.push(r); seen.add(r.code); }
    }
  }

  /* 순서도 진짜로 섞는다 — «항상 국어부터»가 안 되게.
     ⚠ 개수는 이미 QUIZ_N 이하라 버릴 것이 없다(넘치게 담고 자르면 오답노트가 잘려 나간다). */
  for (let i = picked.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [picked[i], picked[j]] = [picked[j], picked[i]];
  }
  return picked;
}

/* 오늘 판을 다 읽는다 — 마지막 판이 «지금 판»이다 */
async function sessionsToday(db, childId, ymd) {
  const { results } = await db.prepare(
    "SELECT * FROM quiz_session WHERE child_id = ? AND ymd = ? ORDER BY attempt"
  ).bind(childId, ymd).all();
  return results || [];
}

async function makeSession(db, child, ymd, attempt, paid) {
  const band = bandOf(child.grade);
  const qs = await pickQuestions(db, child, band, attempt);
  if (qs.length < QUIZ_N) return null;
  await db.prepare(
    "INSERT INTO quiz_session (child_id, ymd, attempt, codes, paid, created_at) VALUES (?,?,?,?,?,?)"
  ).bind(child.id, ymd, attempt, qs.map((q) => q.code).join(","), paid, nowIso()).run();
  return db.prepare("SELECT * FROM quiz_session WHERE child_id = ? AND ymd = ? AND attempt = ?")
    .bind(child.id, ymd, attempt).first();
}

/* 세션에 적힌 문제를 «세션 순서대로» 낸다. ⚠ 응답에 answer 가 없다. 있으면 안 된다. */
async function itemsOf(db, ses) {
  const codes = String(ses.codes).split(",");
  const holes = codes.map(() => "?").join(",");
  const { results } = await db.prepare(
    `SELECT code, field, kind, sec, image_url, q, a1, a2, a3, a4 FROM quiz_questions WHERE code IN (${holes})`
  ).bind(...codes).all();
  const byCode = new Map((results || []).map((r) => [r.code, r]));
  return codes.map((c) => byCode.get(c)).filter(Boolean).map((r) => ({
    code: r.code, field: r.field, kind: r.kind, sec: r.sec,
    // ⚠ 그림 문제는 **다 받은 뒤에** 타이머를 켜야 한다 — 아니면 「안 늦었는데 틀렸다」가 된다
    image: r.image_url || null,
    q: r.q,
    options: r.kind === "ox" ? [r.a1, r.a2] : [r.a1, r.a2, r.a3, r.a4],
  }));
}

function stateOf(sessions) {
  const cur = sessions.length ? sessions[sessions.length - 1] : null;
  const used = sessions.length;                       // 오늘 연 판 수
  const openable = used < RETRY_MAX;                  // 더 열 수 있나
  return { cur, used, openable, nextCost: openable ? retryCost(used + 1) : null };
}

/* GET /api/v1/children/{id}/quiz — 오늘 판을 받는다(첫 판은 무료로 자동 생성) */
async function getQuiz(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  let sessions = await sessionsToday(db, child.id, ymd);
  if (!sessions.length) {
    const made = await makeSession(db, child, ymd, 1, 0);
    if (!made) return apiErr("SERVER", null, "오늘 낼 문제가 모자라요. 잠시 후 다시 해 주세요.");
    sessions = [made];
  }

  const { cur, used, openable, nextCost } = stateOf(sessions);
  return apiOk({
    ymd,
    attempt: cur.attempt,
    total: QUIZ_N,
    done: !!cur.finished_at,
    answered: cur.answered, correct: cur.correct, coins: cur.coins, points: cur.points,
    perfect_bonus: BONUS.quizPerfect,
    items: cur.finished_at ? [] : await itemsOf(db, cur),   // 끝낸 판은 문제를 다시 안 준다
    // 재도전 — 값은 **서버가** 말한다
    retry: { used, max: RETRY_MAX, can: openable && !!cur.finished_at, cost: nextCost },
    coin: await coinState(db, child.id),
  });
}

/* POST /api/v1/children/{id}/quiz/retry — 코인을 내고 한 판 더 연다
   ⚠ 값은 서버가 매긴다. 클라이언트가 보낸 금액을 쓰지 않는다. */
async function retryQuiz(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  const sessions = await sessionsToday(db, child.id, ymd);
  const { cur, used, openable, nextCost } = stateOf(sessions);

  if (!cur) return apiErr("VALIDATION", null, "오늘 미션을 먼저 받아 주세요.");
  if (!cur.finished_at) {
    return apiErr("VALIDATION", { attempt: cur.attempt }, "지금 판을 먼저 끝내 주세요.");
  }
  if (!openable) {
    return apiErr("LIMIT_EXCEEDED", { used, max: RETRY_MAX },
      "오늘 몫은 다 썼어요. 내일 또 만나요!");
  }

  const st = await coinState(db, child.id);
  if (st.stars < nextCost) {
    return apiErr("VALIDATION", { need: nextCost, have: st.stars },
      "★" + nextCost + "개가 필요해요. 지금 " + st.stars + "개 있어요.");
  }

  const attempt = used + 1;
  await spendStars(db, child.id, nextCost, "quiz-retry:" + ymd + ":" + attempt);
  const made = await makeSession(db, child, ymd, attempt, nextCost);
  if (!made) {
    /* 문제 재고가 모자라 판을 못 열었다 → **받은 코인을 돌려준다.**
       ⚠ grantStars 가 아니라 refundStars 다 — grantStars 는 하루 상한을 타서
         상한에 걸린 아이는 환불을 «못 받는» 사고가 난다. 아이 돈으로 우리 재고 부족을 메우지 않는다. */
    await refundStars(db, child.id, nextCost, "quiz-retry:" + ymd + ":" + attempt);
    return apiErr("SERVER", null, "낼 문제가 모자라요. 코인은 돌려드렸어요.");
  }

  return apiOk({
    ymd, attempt, paid: nextCost, total: QUIZ_N,
    items: await itemsOf(db, made),
    retry: { used: attempt, max: RETRY_MAX, can: false, cost: attempt < RETRY_MAX ? retryCost(attempt + 1) : null },
    coin: await coinState(db, child.id),
  });
}

/* ⚠ 한때 있던 «10개를 한 번에 내는» POST /quiz 는 **없앴다**(2026-08-08).
   화면이 한 문제씩 내고 그 자리에서 답을 받는 방식으로 바뀌었고, 그 판을 한 번에 내면
   quiz_answer_log 의 UNIQUE(child_id, ymd, attempt, code) 와도 어긋난다.
   지금 채점 경로는 answerOne() 하나뿐이다 — 길이 둘이면 한쪽만 고쳐서 반드시 어긋난다. */

/* POST /api/v1/children/{id}/quiz/answer — **한 문제**를 내고 그 자리에서 답을 받는다
   body: { code, picked }   picked 는 1~4(OX 는 1~2), 시간초과면 null

   ⚠ 여기서만 답이 나간다. **그 문제를 이미 잠근 뒤**다.
   ⚠ 두 번 답할 수 없다 — UNIQUE 인덱스가 막고, 여기서도 먼저 확인해 친절한 문구를 준다.
   ⚠ 마지막 문제를 답하면 그 자리에서 판을 마감하고 코인·점수를 준다(final). */
async function answerOne(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  const sessions = await sessionsToday(db, child.id, ymd);
  const { cur, used, openable, nextCost } = stateOf(sessions);
  if (!cur) return apiErr("VALIDATION", null, "오늘 미션을 먼저 받아 주세요.");
  if (cur.finished_at) {
    return apiErr("LIMIT_EXCEEDED", { retry: { used, max: RETRY_MAX, cost: nextCost } },
      openable ? "이 판은 이미 끝냈어요. 한 판 더 할 수 있어요!" : "오늘 몫은 다 썼어요. 내일 또 만나요!");
  }

  const b = await readJson(request);
  const code = String(b?.code || "");
  const codes = String(cur.codes).split(",");
  if (codes.indexOf(code) < 0) return apiErr("VALIDATION", null, "이 판에 없는 문제예요.");

  const dup = await db.prepare(
    "SELECT 1 x FROM quiz_answer_log WHERE child_id = ? AND ymd = ? AND attempt = ? AND code = ?"
  ).bind(child.id, ymd, cur.attempt, code).first();
  if (dup) return apiErr("VALIDATION", null, "이미 답한 문제예요.");

  const row = await db.prepare(
    "SELECT code, field, q, answer, hint, points, a1, a2, a3, a4 FROM quiz_questions WHERE code = ?"
  ).bind(code).first();
  if (!row) return apiErr("NOT_FOUND");

  const p = parseInt(b?.picked, 10);
  const picked = (p >= 1 && p <= 4) ? p : null;
  const ok = picked === row.answer;

  await db.prepare(
    "INSERT INTO quiz_answer_log (child_id, ymd, attempt, code, field, picked, correct, created_at) " +
    "VALUES (?,?,?,?,?,?,?,?)"
  ).bind(child.id, ymd, cur.attempt, code, row.field, picked, ok ? 1 : 0, nowIso()).run();

  const answered = cur.answered + 1;
  const correct = cur.correct + (ok ? 1 : 0);
  const opts = [row.a1, row.a2, row.a3, row.a4];

  const out = {
    code, ok, answered, total: codes.length,
    answer: row.answer, answer_text: opts[row.answer - 1],
    picked, picked_text: picked ? opts[picked - 1] : null,
    hint: row.hint || null,
  };

  if (answered < codes.length) {
    await db.prepare("UPDATE quiz_session SET answered = ?, correct = ? WHERE child_id = ? AND ymd = ? AND attempt = ?")
      .bind(answered, correct, child.id, ymd, cur.attempt).run();
    return apiOk(out);
  }

  // ── 마지막 문제였다 → 판을 마감한다 ──────────────────────────────
  out.final = await finishAttempt(db, child, ymd, cur, codes, correct);
  return apiOk(out);
}

/* 판 마감 — 코인·리그 점수를 주고 세션을 닫는다.
   ⚠ **리그 점수는 «그 문제를 처음 맞혔을 때»에만** 준다.
     답을 그 자리에서 알려 주므로, 안 그러면 「답 보고 → 코인 내고 재도전 → 외운 답으로 만점」이
     점수 자판기가 된다. 코인은 그대로 준다(반복 학습의 보상). */
async function finishAttempt(db, child, ymd, ses, codes, correct) {
  const holes = codes.map(() => "?").join(",");
  // 이 판보다 «먼저» 맞힌 적이 있는 문제
  const { results: had } = await db.prepare(
    `SELECT DISTINCT code FROM quiz_answer_log
      WHERE child_id = ? AND correct = 1 AND code IN (${holes})
        AND NOT (ymd = ? AND attempt = ?)`
  ).bind(child.id, ...codes, ymd, ses.attempt).all();
  const seen = new Set((had || []).map((r) => r.code));

  // 이 판에서 맞힌 문제 중 «처음» 맞힌 것만 점수
  const { results: mine } = await db.prepare(
    `SELECT l.code, q.points FROM quiz_answer_log l JOIN quiz_questions q ON q.code = l.code
      WHERE l.child_id = ? AND l.ymd = ? AND l.attempt = ? AND l.correct = 1`
  ).bind(child.id, ymd, ses.attempt).all();
  let points = 0;
  for (const r of (mine || [])) if (!seen.has(r.code)) points += (r.points || 5);

  const perfect = correct === codes.length;
  const wantCoin = correct + (perfect ? BONUS.quizPerfect : 0);
  const g = await grantStars(db, child.id, wantCoin, "quiz:" + ymd + ":" + ses.attempt);
  const pt = await addPoints(db, child.id, points);

  await db.prepare(
    "UPDATE quiz_session SET answered = ?, correct = ?, coins = ?, points = ?, finished_at = ? " +
    "WHERE child_id = ? AND ymd = ? AND attempt = ?"
  ).bind(codes.length, correct, g.granted, points, nowIso(), child.id, ymd, ses.attempt).run();

  if (correct > 0) await bumpLevel(db, child.id, 1);   // 레벨은 «해낸 미션 수»

  const sessions = await sessionsToday(db, child.id, ymd);
  const { used, openable, nextCost } = stateOf(sessions);
  return {
    attempt: ses.attempt, total: codes.length, correct, perfect,
    coins: g.granted, capped: g.capped,
    points, season: pt.season,
    perfect_bonus: perfect ? BONUS.quizPerfect : 0,
    retry: { used, max: RETRY_MAX, can: openable, cost: openable ? nextCost : null },
    coin: await coinState(db, child.id),
  };
}

/* GET /api/v1/children/{id}/quiz/stats — 분야별 정답률 (박사 뱃지의 근거) */
async function quizStats(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const { results } = await db.prepare(
    `SELECT field, COUNT(*) n, SUM(correct) c FROM quiz_answer_log
      WHERE child_id = ? GROUP BY field ORDER BY (SUM(correct)*1.0/COUNT(*)) DESC`
  ).bind(child.id).all();
  const rows = (results || []).map((r) => ({
    field: r.field, tried: r.n, correct: r.c,
    rate: r.n ? Math.round((r.c / r.n) * 100) : 0,
  }));
  return apiOk({ fields: rows, best: rows[0]?.field || null });
}

// ════════════════════════════════════════════════════════════════════
//  라우터
//  ⚠ index.js 접두어 화이트리스트에 안 넣으면 여기까지 오지도 못하고 HTML 404 로 샌다.
// ════════════════════════════════════════════════════════════════════
export async function handleQuizApi(request, db, env, url) {
  const p = url.pathname, m = request.method;
  let x;

  // ⚠ 더 긴 경로를 먼저 잡는다
  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/stats$/);
  if (x && m === "GET") return quizStats(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/retry$/);
  if (x && m === "POST") return retryQuiz(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/answer$/);
  if (x && m === "POST") return answerOne(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/?$/);
  if (x) {
    if (m === "GET") return getQuiz(request, db, env, x[1]);
    // POST /quiz(한 번에 10개)는 폐기됐다 — /quiz/answer 로 한 문제씩 낸다
    return apiErr("VALIDATION", null, "문제는 하나씩 내 주세요.");
  }
  return null;
}
