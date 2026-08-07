// ================= 🧠 데일리 퀴즈 (2026-08-08) =================
// 기획서 `docs/기획-스타코인-v1.md` §04.
//
// 4지선다 10문제 · 문제당 5초 · 하루 1세트 · 맞힌 만큼 코인 · 만점 보너스.
//
// 이 파일이 지키는 규칙 — 화면이 아니라 여기서 지켜야 우회가 안 된다:
//   ① **정답을 절대 내려보내지 않는다.** 채점은 서버가 한다.
//      내려보내면 개발자도구로 다 보인다 — 퀴즈가 «못 속이는 미션»인 이유가 사라진다.
//   ② **하루 한 세트**는 quiz_session 의 PRIMARY KEY(child_id, ymd) 가 강제한다.
//      세는 로직을 또 쓰지 않는다 — INSERT 가 먹으면 오늘 처음이다.
//   ③ **코인은 star_core 로만** 준다. 하루 리밋을 여기서 다시 세지 않는다.
//   ④ 채점은 «낸 문제»(session.codes)로만 한다. 클라이언트가 보낸 code 를 믿지 않는다.

import { apiOk, apiErr, readJson } from "./api_core.js";
import { resolveAuth } from "./auth_core.js";
import { grantStars, coinState, ymdKst, BONUS } from "./star_core.js";

const nowIso = () => new Date().toISOString();
const QUIZ_N = 10;          // 한 세트 문제 수
const SEC_PER_Q = 5;        // 문제당 제한 시간(초) — 화면이 쓰는 값도 여기서 내려준다

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

/* 문제를 뽑는다 — **8분야에서 고루**. 한 분야만 쏟아지면
   «나는 수학 못해서 오늘 망함»이 되어 그날을 통째로 포기한다. */
async function pickQuestions(db, band, seed) {
  const fields = ["kor", "math", "sci", "world", "proverb", "life", "sports", "ent"];
  const picked = [];
  for (const f of fields) {
    const { results } = await db.prepare(
      `SELECT code, field FROM quiz_questions
        WHERE active = 1 AND field = ? AND (band = 'all' OR band = ?)
        ORDER BY (id * 31 + ?) % 997 LIMIT 2`
    ).bind(f, band, seed).all();
    for (const r of (results || [])) picked.push(r);
  }
  // 8분야 × 2 = 16 중 10개만. 순서도 섞어서 «항상 국어부터»가 안 되게 한다
  picked.sort((a, b) => ((a.code.length * 7 + seed) % 13) - ((b.code.length * 7 + seed) % 13));
  return picked.slice(0, QUIZ_N);
}

/* GET /api/v1/children/{id}/quiz — 오늘 세트를 받는다(없으면 만든다)
   ⚠ 응답에 answer 가 없다. 있으면 안 된다. */
async function getQuiz(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  let ses = await db.prepare("SELECT * FROM quiz_session WHERE child_id = ? AND ymd = ?")
    .bind(child.id, ymd).first();

  if (!ses) {
    const band = (+child.grade <= 2) ? "low" : (+child.grade <= 4) ? "mid" : "high";
    const qs = await pickQuestions(db, band, parseInt(ymd, 10) % 997);
    if (qs.length < QUIZ_N) {
      return apiErr("SERVER", null, "오늘 낼 문제가 모자라요. 잠시 후 다시 해 주세요.");
    }
    await db.prepare(
      "INSERT INTO quiz_session (child_id, ymd, codes, answered, correct, coins, created_at) VALUES (?,?,?,0,0,0,?)"
    ).bind(child.id, ymd, qs.map((q) => q.code).join(","), nowIso()).run();
    ses = await db.prepare("SELECT * FROM quiz_session WHERE child_id = ? AND ymd = ?")
      .bind(child.id, ymd).first();
  }

  const codes = String(ses.codes).split(",");
  const holes = codes.map(() => "?").join(",");
  const { results } = await db.prepare(
    `SELECT code, field, q, a1, a2, a3, a4 FROM quiz_questions WHERE code IN (${holes})`
  ).bind(...codes).all();
  // DB 순서가 아니라 **세션에 적힌 순서**로 낸다(매번 같은 순서를 보장)
  const byCode = new Map((results || []).map((r) => [r.code, r]));
  const items = codes.map((c) => byCode.get(c)).filter(Boolean).map((r) => ({
    code: r.code, field: r.field, q: r.q, options: [r.a1, r.a2, r.a3, r.a4],
  }));

  return apiOk({
    ymd, total: QUIZ_N, sec_per_q: SEC_PER_Q,
    done: !!ses.finished_at,
    answered: ses.answered, correct: ses.correct, coins: ses.coins,
    perfect_bonus: BONUS.quizPerfect,
    items: ses.finished_at ? [] : items,      // 이미 끝냈으면 문제를 다시 안 준다
    coin: await coinState(db, child.id),
  });
}

/* POST /api/v1/children/{id}/quiz — 10개 답을 한 번에 제출하고 채점받는다
   body: { answers: [{code, picked}] }  picked 는 1~4, 시간초과면 null
   ⚠ 한 문제씩 채점하지 않는다 — 매 문제 정답이 오가면 «틀린 걸 알고 다시 내는» 길이 열린다. */
async function submitQuiz(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  const ses = await db.prepare("SELECT * FROM quiz_session WHERE child_id = ? AND ymd = ?")
    .bind(child.id, ymd).first();
  if (!ses) return apiErr("VALIDATION", null, "오늘 퀴즈를 먼저 받아 주세요.");
  if (ses.finished_at) {
    return apiErr("LIMIT_EXCEEDED", { correct: ses.correct, coins: ses.coins },
      "오늘 퀴즈는 이미 풀었어요. 내일 또 만나요!");
  }

  const b = await readJson(request);
  const sent = new Map();
  for (const a of (b?.answers || [])) {
    const p = parseInt(a?.picked, 10);
    sent.set(String(a?.code), (p >= 1 && p <= 4) ? p : null);
  }

  // 채점은 **세션에 적힌 문제**로만. 클라이언트가 보낸 code 목록을 믿지 않는다
  const codes = String(ses.codes).split(",");
  const holes = codes.map(() => "?").join(",");
  const { results } = await db.prepare(
    `SELECT code, field, answer, hint, a1, a2, a3, a4 FROM quiz_questions WHERE code IN (${holes})`
  ).bind(...codes).all();
  const byCode = new Map((results || []).map((r) => [r.code, r]));

  let correct = 0;
  const review = [];
  for (const c of codes) {
    const row = byCode.get(c);
    if (!row) continue;
    const picked = sent.has(c) ? sent.get(c) : null;
    const ok = picked === row.answer;
    if (ok) correct++;
    await db.prepare(
      "INSERT INTO quiz_answer_log (child_id, ymd, code, field, picked, correct, created_at) VALUES (?,?,?,?,?,?,?)"
    ).bind(child.id, ymd, c, row.field, picked, ok ? 1 : 0, nowIso()).run();
    /* 틀린 문제는 **정답을 알려 준다** — «아 이거였구나»가 남아야 학습이다(기획서 §04).
       맞힌 문제는 안 보낸다(응답을 가볍게, 그리고 답 유출 면적을 줄인다). */
    if (!ok) {
      review.push({ code: c, answer: row.answer,
        answer_text: [row.a1, row.a2, row.a3, row.a4][row.answer - 1], hint: row.hint || null });
    }
  }

  const perfect = correct === codes.length;
  const want = correct + (perfect ? BONUS.quizPerfect : 0);
  const g = await grantStars(db, child.id, want, `quiz:${ymd}`);

  await db.prepare(
    "UPDATE quiz_session SET answered = ?, correct = ?, coins = ?, finished_at = ? WHERE child_id = ? AND ymd = ?"
  ).bind(codes.length, correct, g.granted, nowIso(), child.id, ymd).run();

  return apiOk({
    total: codes.length, correct, perfect,
    coins: g.granted,
    capped: g.capped,        // 리밋에 걸려 깎였으면 화면이 «오늘은 여기까지»를 말한다
    perfect_bonus: perfect ? BONUS.quizPerfect : 0,
    review,
    coin: await coinState(db, child.id),
  });
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

// ════════════════════════════════════════════════════════════
//  라우터
//  ⚠ index.js 접두어 화이트리스트에 안 넣으면 여기까지 오지도 못하고 HTML 404 로 샌다.
// ════════════════════════════════════════════════════════════
export async function handleQuizApi(request, db, env, url) {
  const p = url.pathname, m = request.method;
  let x;

  // ⚠ 더 긴 경로(/quiz/stats)를 먼저 잡는다
  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/stats$/);
  if (x && m === "GET") return quizStats(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/quiz\/?$/);
  if (x) {
    if (m === "GET") return getQuiz(request, db, env, x[1]);
    if (m === "POST") return submitQuiz(request, db, env, x[1]);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  return null;
}
